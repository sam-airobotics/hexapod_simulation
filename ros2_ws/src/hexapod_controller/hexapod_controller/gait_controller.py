#!/usr/bin/env python3
"""
Tripod-gait controller for the hexapod_description robot.

The controller is deliberately joint-space for the first simulation stage:
- Tripod A: L1, R2, L3
- Tripod B: R1, L2, R3

Each leg has 3 actuated joints:
  hip/coxal yaw, knee, ankle.

It publishes position commands to a ros2_control
ForwardCommandController.

This is a gait generator, not a full whole-body dynamic controller. Tune the
neutral joint angles and gait amplitudes against the actual CAD/URDF geometry
before using hardware.
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray


class TripodGaitController(Node):
    JOINTS = [
        "L1_Hip_Joint", "L1_Knee_Joint", "L1_Ankle_Joint",
        "L2_Hip_Joint", "L2_Knee_Joint", "L2_Ankle_Joint",
        "L3_Hip_Joint", "L3_Knee_Joint", "L3_Ankle_Joint",
        "R1_Hip_Joint", "R1_Knee_Joint", "R1_Ankle_Joint",
        "R2_Hip_Joint", "R2_Knee_Joint", "R2_Ankle_Joint",
        "R3_Hip_Joint", "R3_Knee_Joint", "R3_Ankle_Joint",
    ]

    # Standard alternating tripod for a 3-leg-per-side hexapod.
    TRIPOD_A = ("L1", "R2", "L3")
    TRIPOD_B = ("R1", "L2", "R3")

    def __init__(self):
        super().__init__("tripod_gait_controller")

        self.declare_parameter("command_topic",
                               "/hexapod_position_controller/commands")
        self.declare_parameter("update_rate", 100.0)
        self.declare_parameter("gait_frequency", 0.65)
        self.declare_parameter("duty_factor", 0.62)
        self.declare_parameter("stride", 0.22)
        self.declare_parameter("lift", 0.28)
        self.declare_parameter("neutral_hip", 0.0)
        self.declare_parameter("neutral_knee", 0.37)
        self.declare_parameter("neutral_knee_right", 0.30)
        self.declare_parameter("neutral_ankle", 0.39)
        self.declare_parameter("neutral_ankle_right", 0.35)
        self.declare_parameter("max_linear_speed", 0.20)
        self.declare_parameter("deadband", 0.03)
        self.declare_parameter("start_walking", False)

        topic = self.get_parameter("command_topic").value
        rate = float(self.get_parameter("update_rate").value)

        self.publisher = self.create_publisher(Float64MultiArray, topic, 10)
        self.cmd_sub = self.create_subscription(
            Twist, "/cmd_vel", self.cmd_vel_callback, 10
        )

        self.gait_frequency = float(
            self.get_parameter("gait_frequency").value)
        self.duty_factor = float(self.get_parameter("duty_factor").value)
        self.stride = float(self.get_parameter("stride").value)
        self.lift = float(self.get_parameter("lift").value)
        self.neutral_hip = float(self.get_parameter("neutral_hip").value)
        self.neutral_knee = float(
            self.get_parameter("neutral_knee").value)
        self.neutral_knee_right = float(
            self.get_parameter("neutral_knee_right").value)
        self.neutral_ankle = float(
            self.get_parameter("neutral_ankle").value)
        self.neutral_ankle_right = float(
            self.get_parameter("neutral_ankle_right").value)
        self.max_linear_speed = float(
            self.get_parameter("max_linear_speed").value)
        self.deadband = float(self.get_parameter("deadband").value)

        self.walking = bool(self.get_parameter("start_walking").value)
        self.command_x = 0.0
        self.command_y = 0.0
        self.command_yaw = 0.0

        self.start_time = self.get_clock().now()
        self.last_log_time = self.start_time

        period = 1.0 / max(rate, 1.0)
        self.timer = self.create_timer(period, self.update)

        self.get_logger().info(
            "Tripod gait controller started. "
            "A={%s}; B={%s}" %
            (", ".join(self.TRIPOD_A), ", ".join(self.TRIPOD_B))
        )

    def cmd_vel_callback(self, msg: Twist):
        self.command_x = max(
            -self.max_linear_speed,
            min(self.max_linear_speed, msg.linear.x)
        )
        self.command_y = max(
            -self.max_linear_speed,
            min(self.max_linear_speed, msg.linear.y)
        )
        self.command_yaw = max(-1.0, min(1.0, msg.angular.z))

        if (
            abs(self.command_x) > self.deadband
            or abs(self.command_y) > self.deadband
            or abs(self.command_yaw) > self.deadband
        ):
            self.walking = True
        else:
            self.walking = False

    @staticmethod
    def smoothstep(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)

    def gait_leg(self, leg: str, phase: float):
        """
        Return [hip, knee, ankle] for one leg.

        phase=0..1:
          0..duty       = stance
          duty..1       = swing

        The right-side joints use mirrored exported frames; the commanded
        signs below are calibrated from the actual URDF kinematics.
        """
        left = leg.startswith("L")
        side_sign = 1.0 if left else -1.0

        duty = max(0.50, min(0.85, self.duty_factor))

        # Walking speed controls how much of the nominal stride is requested.
        speed = math.hypot(self.command_x, self.command_y)
        speed_scale = min(1.0, speed / max(self.max_linear_speed, 1e-6))
        if speed_scale < 0.05:
            speed_scale = 0.0

        # Forward/backward component. Positive x = forward.
        direction = 1.0 if self.command_x >= 0.0 else -1.0
        if abs(self.command_x) < self.deadband:
            direction = 1.0

        # The right hip is geometrically mirrored, so its joint command uses
        # the opposite sign to create the same physical foot displacement.
        if phase < duty:
            s = phase / duty
            u = self.smoothstep(s)
            hip_path = direction * self.stride * speed_scale * (1.0 - 2.0 * u)
            lift = 0.0
        else:
            s = (phase - duty) / (1.0 - duty)
            u = self.smoothstep(s)
            hip_path = direction * self.stride * speed_scale * (-1.0 + 2.0 * u)
            lift = math.sin(math.pi * s) * self.lift * max(speed_scale, 0.25)

        lateral = self.command_y * 0.8
        # Yaw is differential: left and right legs receive opposite
        # corrections because their hip axes are mirrored.
        yaw_term = self.command_yaw * 0.30 * side_sign
        hip = self.neutral_hip + side_sign * (hip_path + lateral) + yaw_term

        # The exported URDF uses mirrored joint frames on the right side...
        # However, the right knee's physical motion that raises the foot is
        # still the positive joint direction after the joint-frame rotation...
        # Use the same physical lift on both sides...
        if left:
            knee = self.neutral_knee + lift
            ankle = self.neutral_ankle - 0.65 * lift
        else:
            knee = self.neutral_knee_right + lift
            ankle = self.neutral_ankle_right + 0.75 * lift

        return [hip, knee, ankle]

    def update(self):
        now = self.get_clock().now()
        elapsed = (now - self.start_time).nanoseconds * 1e-9

        if not self.walking:
            msg = Float64MultiArray()
            msg.data = self.standing_pose()
            self.publisher.publish(msg)
            return

        base_phase = (elapsed * self.gait_frequency) % 1.0

        # Tripod B is exactly half a gait cycle out of phase.
        phases = {
            "L1": base_phase,
            "R2": base_phase,
            "L3": base_phase,
            "R1": (base_phase + 0.5) % 1.0,
            "L2": (base_phase + 0.5) % 1.0,
            "R3": (base_phase + 0.5) % 1.0,
        }

        data = []
        for joint in self.JOINTS:
            leg = joint[0:2]  # L1, L2, ... R3
            values = self.gait_leg(leg, phases[leg])

            if "Hip" in joint:
                data.append(values[0])
            elif "Knee" in joint:
                data.append(values[1])
            else:
                data.append(values[2])

        msg = Float64MultiArray()
        msg.data = data
        self.publisher.publish(msg)

    def standing_pose(self):
        pose = []
        for joint in self.JOINTS:
            if "Hip" in joint:
                pose.append(self.neutral_hip)
            elif "Knee" in joint:
                leg = joint[0:2]
                pose.append(
                    self.neutral_knee_right
                    if leg.startswith("R")
                    else self.neutral_knee
                )
            else:
                leg = joint[0:2]
                pose.append(
                    self.neutral_ankle_right
                    if leg.startswith("R")
                    else self.neutral_ankle
                )
        return pose


def main(args=None):
    rclpy.init(args=args)
    node = TripodGaitController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
