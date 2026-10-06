#!/usr/bin/env python3
"""Simple terminal teleop for the hexapod.

Keys:
  w / s : forward / backward
  a / d : strafe left / right
  q / e : rotate left / right
  x     : stop
  Ctrl-C: quit

The node publishes standard geometry_msgs/Twist on /cmd_vel, so it works with
both the ROS controller and the Gazebo -> ROS bridge in this package.
"""

import sys
import select
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class HexapodTeleop(Node):
    def __init__(self):
        super().__init__("hexapod_teleop")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.linear_speed = 0.12
        self.angular_speed = 0.60
        self.timer = self.create_timer(0.08, self.publish_keepalive)
        self.current = Twist()
        self.get_logger().info(
            "w/s=forward/back | a/d=left/right | q/e=rotate | x=stop | Ctrl-C=quit"
        )

    def publish_keepalive(self):
        self.publisher.publish(self.current)


def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    ready, _, _ = select.select([sys.stdin], [], [], 0.10)
    key = sys.stdin.read(1) if ready else ""
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def main(args=None):
    rclpy.init(args=args)
    node = HexapodTeleop()
    settings = termios.tcgetattr(sys.stdin)

    try:
        while rclpy.ok():
            key = get_key(settings)

            if key == "w":
                node.current.linear.x = node.linear_speed
                node.current.linear.y = 0.0
            elif key == "s":
                node.current.linear.x = -node.linear_speed
                node.current.linear.y = 0.0
            elif key == "a":
                node.current.linear.x = 0.0
                node.current.linear.y = node.linear_speed
            elif key == "d":
                node.current.linear.x = 0.0
                node.current.linear.y = -node.linear_speed
            elif key == "q":
                node.current.linear.x = 0.0
                node.current.linear.y = 0.0
                node.current.angular.z = node.angular_speed
            elif key == "e":
                node.current.linear.x = 0.0
                node.current.linear.y = 0.0
                node.current.angular.z = -node.angular_speed
            elif key == "x" or key == " ":
                node.current = Twist()
            elif key == "\x03":
                break

            rclpy.spin_once(node, timeout_sec=0.0)
    except KeyboardInterrupt:
        pass
    finally:
        node.current = Twist()
        node.publisher.publish(node.current)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
