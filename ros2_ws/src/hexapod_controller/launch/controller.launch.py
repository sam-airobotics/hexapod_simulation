import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("hexapod_controller")
    controller_config = os.path.join(pkg, "config", "controllers.yaml")

    return LaunchDescription([
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "joint_state_broadcaster",
                "--controller-manager",
                "/controller_manager",
            ],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=[
                "hexapod_position_controller",
                "--controller-manager",
                "/controller_manager",
            ],
            output="screen",
        ),
        Node(
            package="hexapod_controller",
            executable="tripod_gait_controller",
            output="screen",
        ),
    ])
