import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.conditions import IfCondition
import xacro

def generate_launch_description():
    # ========================================================================
    # 1. SETUP PATHS & FILES
    # ========================================================================
    pkg_name = 'hexapod_description'
    pkg_share = get_package_share_directory(pkg_name)
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Path to URDF (Xacro)
    xacro_file = os.path.join(pkg_share, 'urdf', 'hexapod.xacro')
    
    # Path to Bridge Config
    bridge_config_file = os.path.join(pkg_share, 'config', 'bridge_config.yaml')
    
    # Path to RViz Config
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'hexapod.rviz')

    # Path to EKF Config
    ekf_config_file = os.path.join(pkg_share, 'config', 'ekf.yaml')

    # === ADDED: Path to your custom world ===
    # world_file_name = 'model.sdf' # Change this if your world file has a different name
    world_file = 'empty.sdf'  # Default to empty world if the specified world file is not found
    # world_path = os.path.join(pkg_share, 'worlds', 'clean_world', world_file_name)

    # Process Xacro
    doc = xacro.process_file(xacro_file)
    robot_desc = doc.toxml()

    # ========================================================================
    # 2. DEFINE ARGUMENTS
    # ========================================================================
    
    #Declare the world argument
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Gazebo world file to load'
    )

    teleop_arg = DeclareLaunchArgument(
        'teleop',
        default_value='false',
        description='Start teleop_twist_keyboard with the simulation'
    )

    # ========================================================================
    # 3. DEFINE NODES
    # ========================================================================

    # A. Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True
        }]
    )

    # B. Gazebo Simulation
    # Modified to load the world file instead of empty.sdf
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': ['-r -v 4 ', LaunchConfiguration('world')]
        }.items()
    )

    # C. Spawn Entity
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'hexapod',
            '-z', '0.5',  # base_footprint is the world ground reference
        ],
        output='screen'
    )

    # D. Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_config_file,
            'use_sim_time': True
        }],
        output='screen'
    )

    # E. RViz2
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )


    # G. Start ros2_control controllers after Gazebo has spawned the robot.
    # The controller manager is created by gz_ros2_control when the entity appears.
    controller_spawners = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'joint_state_broadcaster',
                    '--controller-manager', '/controller_manager'
                ],
                output='screen'
            ),
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'hexapod_position_controller',
                    '--controller-manager', '/controller_manager'
                ],
                output='screen'
            ),
            Node(
                package='hexapod_controller',
                executable='tripod_gait_controller',
                output='screen',
                parameters=[{
                    'start_walking': False
                }]
            )
        ]
    )

    # H. Robot Localization Node (EKF)
    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_file]
    )

    # Optional custom keyboard teleop. For reliable terminal input, run
    # `ros2 launch hexapod_description teleop.launch.py` in a second terminal.
    keyboard_teleop = Node(
        package='hexapod_controller',
        executable='hexapod_teleop',
        name='hexapod_teleop',
        output='screen',
        emulate_tty=True,
        condition=IfCondition(LaunchConfiguration('teleop')),
    )


    # ========================================================================
    # 4. RETURN LAUNCH DESCRIPTION
    # ========================================================================
    return LaunchDescription([
        world_arg,
        teleop_arg,
        gazebo,
        robot_state_publisher,
        spawn_entity,
        bridge,
        robot_localization_node,
        controller_spawners,
        rviz,
        keyboard_teleop
    ])