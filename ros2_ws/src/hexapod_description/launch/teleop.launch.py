from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Launch the hexapod's explicit w/a/s/d teleop node."""
    return LaunchDescription([
        Node(
            package="hexapod_controller",
            executable="hexapod_teleop",
            name="hexapod_teleop",
            output="screen",
            emulate_tty=True,
        )
    ])
