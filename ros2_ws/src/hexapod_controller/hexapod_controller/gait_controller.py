#!/usr/bin/env python3
"""Velocity-driven tripod gait controller for the simulated hexapod.

The CAD export is rotated relative to the ROS base frame:
    ROS +X = robot forward  -> model +Y
    ROS +Y = robot left     -> model +X

The hip joints sweep the feet around the hip.  The controller therefore
projects the requested body velocity (and yaw velocity) onto each leg's
actual hip tangent instead of treating X/Y as independent joint angles.
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

    TRIPOD_A = ("L1", "R2", "L3")
    TRIPOD_B = ("R1", "L2", "R3")

    def __init__(self):
        super().__init__("tripod_gait_controller")

        self.declare_parameter("command_topic", "/hexapod_position_controller/commands")
        self.declare_parameter("cmd_vel_timeout", 0.35)
        self.declare_parameter("update_rate", 100.0)
        self.declare_parameter("gait_frequency", 0.70)
        self.declare_parameter("duty_factor", 0.62)
        self.declare_parameter("stride", 0.26)
        self.declare_parameter("lift", 0.28)
        self.declare_parameter("neutral_hip", 0.0)
        self.declare_parameter("neutral_knee", 0.37)
        self.declare_parameter("neutral_knee_right", 0.30)
        self.declare_parameter("neutral_ankle", 0.39)
        self.declare_parameter("neutral_ankle_right", 0.35)
        self.declare_parameter("max_linear_speed", 0.20)
        self.declare_parameter("max_yaw_speed", 1.0)
        self.declare_parameter("deadband", 0.02)

        topic = self.get_parameter("command_topic").value
        rate = float(self.get_parameter("update_rate").value)

        self.publisher = self.create_publisher(Float64MultiArray, topic, 10)
        self.cmd_sub = self.create_subscription(Twist, "/cmd_vel", self.cmd_vel_callback, 20)

        self.cmd_vel_timeout = float(self.get_parameter("cmd_vel_timeout").value)
        self.gait_frequency = float(self.get_parameter("gait_frequency").value)
        self.duty_factor = float(self.get_parameter("duty_factor").value)
        self.stride = float(self.get_parameter("stride").value)
        self.lift = float(self.get_parameter("lift").value)
        self.neutral_hip = float(self.get_parameter("neutral_hip").value)
        self.neutral_knee = float(self.get_parameter("neutral_knee").value)
        self.neutral_knee_right = float(self.get_parameter("neutral_knee_right").value)
        self.neutral_ankle = float(self.get_parameter("neutral_ankle").value)
        self.neutral_ankle_right = float(self.get_parameter("neutral_ankle_right").value)
        self.max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self.max_yaw_speed = float(self.get_parameter("max_yaw_speed").value)
        self.deadband = float(self.get_parameter("deadband").value)

        self.command_x = 0.0       # ROS +X = forward
        self.command_y = 0.0       # ROS +Y = left
        self.command_yaw = 0.0     # ROS +Z = CCW
        self.last_cmd_time = self.get_clock().now()
        self.start_time = self.get_clock().now()

        self.timer = self.create_timer(1.0 / max(rate, 1.0), self.update)

        self.get_logger().info(
            "Velocity gait ready: ROS +X=forward, +Y=left, +Z=yaw. "
            "Commands arrive on /cmd_vel."
        )

    def cmd_vel_callback(self, msg: Twist):
        self.command_x = self._clamp(msg.linear.x, -self.max_linear_speed, self.max_linear_speed)
        self.command_y = self._clamp(msg.linear.y, -self.max_linear_speed, self.max_linear_speed)
        self.command_yaw = self._clamp(msg.angular.z, -self.max_yaw_speed, self.max_yaw_speed)
        self.last_cmd_time = self.get_clock().now()

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, float(value)))

    @staticmethod
    def smoothstep(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)

    def command_active(self):
        age = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
        if age > self.cmd_vel_timeout:
            return False
        return (
            abs(self.command_x) > self.deadband
            or abs(self.command_y) > self.deadband
            or abs(self.command_yaw) > self.deadband
        )

    def leg_tangent(self, leg):
        # Finite-difference calibration from the exported URDF at the neutral pose.
        # Left legs:  [ +0.304, +0.953 ]
        # Right legs: [ -0.300, -0.954 ]
        if leg.startswith("L"):
            return (0.3044, 0.9525)
        return (-0.3003, -0.9539)

    def hip_velocity_projection(self, leg):
        """Project body motion onto the leg's actual hip sweep direction.

        The CAD export has robot-forward along model +Y, while ROS +X is forward.
        We therefore transform ROS velocity [x forward, y left] into model [x,y]
        and add the tangential velocity caused by yaw.
        """
        # ROS body velocity -> exported model coordinates.
        model_vx = self.command_y
        model_vy = self.command_x

        # Approximate hip location relative to the body centre in model coordinates.
        row = int(leg[1]) - 1
        model_hy = (-0.003 + row * 0.098)
        model_hx = 0.145 if leg.startswith("L") else -0.015

        # v = omega x r for body rotation.
        yaw_vx = -self.command_yaw * model_hy
        yaw_vy = self.command_yaw * model_hx

        vx = model_vx + yaw_vx
        vy = model_vy + yaw_vy

        tx, ty = self.leg_tangent(leg)
        return vx * tx + vy * ty

    def gait_leg(self, leg, phase, active):
        left = leg.startswith("L")
        duty = max(0.50, min(0.85, self.duty_factor))

        if not active:
            return self.standing_leg(leg)

        projection = self.hip_velocity_projection(leg)
        speed = math.sqrt(self.command_x ** 2 + self.command_y ** 2)
        yaw_fraction = abs(self.command_yaw) / max(self.max_yaw_speed, 1e-6)
        activity = min(1.0, max(speed / max(self.max_linear_speed, 1e-6), yaw_fraction))
        amplitude = self.stride * max(activity, 0.35)

        # The projection sign naturally mirrors left/right legs.  During stance
        # the foot moves backward relative to the body; during swing it moves forward.
        sign = 1.0 if projection >= 0.0 else -1.0
        magnitude = min(1.0, abs(projection) / max(self.max_linear_speed * 0.95, 1e-6))
        amplitude *= max(magnitude, 0.35)

        if phase < duty:
            u = self.smoothstep(phase / duty)
            hip_path = sign * amplitude * (1.0 - 2.0 * u)
            lift = 0.0
        else:
            u = self.smoothstep((phase - duty) / (1.0 - duty))
            hip_path = sign * amplitude * (-1.0 + 2.0 * u)
            lift = math.sin(math.pi * ((phase - duty) / (1.0 - duty))) * self.lift

        # Keep yaw/translation unified: projection already includes both.
        hip = self.neutral_hip + hip_path

        if left:
            knee = self.neutral_knee + lift
            ankle = self.neutral_ankle - 0.65 * lift
        else:
            knee = self.neutral_knee_right + lift
            ankle = self.neutral_ankle_right + 0.75 * lift

        return [hip, knee, ankle]

    def standing_leg(self, leg):
        left = leg.startswith("L")
        knee = self.neutral_knee if left else self.neutral_knee_right
        ankle = self.neutral_ankle if left else self.neutral_ankle_right
        return [self.neutral_hip, knee, ankle]

    def update(self):
        active = self.command_active()
        elapsed = (self.get_clock().now() - self.start_time).nanoseconds * 1e-9
        phase = (elapsed * self.gait_frequency) % 1.0

        phases = {
            "L1": phase,
            "R2": phase,
            "L3": phase,
            "R1": (phase + 0.5) % 1.0,
            "L2": (phase + 0.5) % 1.0,
            "R3": (phase + 0.5) % 1.0,
        }

        data = []
        for joint in self.JOINTS:
            leg = joint[:2]
            hip, knee, ankle = self.gait_leg(leg, phases[leg], active)
            if "Hip" in joint:
                data.append(hip)
            elif "Knee" in joint:
                data.append(knee)
            else:
                data.append(ankle)

        self.publisher.publish(Float64MultiArray(data=data))


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
