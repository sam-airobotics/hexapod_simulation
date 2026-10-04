# Hexapod Simulation

A ROS 2 + Gazebo Harmonic simulation of an 18-DOF hexapod using a joint-space alternating tripod gait.

## Architecture

```text
/cmd_vel
   |
   v
tripod_gait_controller
   |
   | Float64MultiArray (18 joint positions)
   v
/hexapod_position_controller
   |
   v
gz_ros2_control
   |
   v
Gazebo Harmonic
```

The gait is divided into two alternating tripods:

- **Tripod A:** `L1`, `R2`, `L3`
- **Tripod B:** `R1`, `L2`, `R3`

Each leg has three joints:

`Hip -> Knee -> Ankle`

## Packages

### `hexapod_description`

Contains the robot model and simulation environment.

| Path | Purpose |
|---|---|
| `urdf/hexapod.xacro` | Main robot model, joints, inertial data, Gazebo properties and `ros2_control` interfaces |
| `urdf/hexapod.urdf` | Generated/static URDF representation |
| `urdf/materials.xacro` | Material definitions |
| `meshes/*.stl` | CAD-derived visual/collision meshes |
| `launch/sim.launch.py` | Full Gazebo + RViz + bridge + EKF + controllers + gait launch |
| `launch/display.launch.py` | RViz-only robot visualization with joint-state publisher |
| `config/bridge_config.yaml` | Gazebo <-> ROS 2 topic bridges |
| `config/ekf.yaml` | `robot_localization` EKF configuration |
| `rviz/hexapod.rviz` | RViz configuration |

### `hexapod_controller`

Contains the gait and ros2_control configuration.

| Path | Purpose |
|---|---|
| `hexapod_controller/gait_controller.py` | Generates the alternating tripod gait and consumes `/cmd_vel` |
| `config/controllers.yaml` | Defines the joint-state broadcaster and 18-joint position controller |
| `launch/controller.launch.py` | Spawns controllers when a controller manager already exists |
| `setup.py` | Installs the Python controller and ROS 2 entry point |

## Requirements

Tested project structure targets:

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- `ros_gz_sim`
- `ros_gz_bridge`
- `gz_ros2_control`
- `robot_localization`
- `controller_manager`

## Build

From the workspace:

```bash
cd ~/hexapod_simulation/ros2_ws

source /opt/ros/jazzy/setup.bash

rm -rf build install log
colcon build --symlink-install

source install/setup.bash
```

## Launch the full simulation

This is the main launch command:

```bash
ros2 launch hexapod_description sim.launch.py
```

The launch file starts:

1. Gazebo Harmonic
2. `robot_state_publisher`
3. The hexapod entity
4. ROS-Gazebo topic bridges
5. `robot_localization` EKF
6. `joint_state_broadcaster`
7. `hexapod_position_controller`
8. `tripod_gait_controller`
9. RViz2

The robot starts in its standing pose.

## Move the hexapod

The gait controller listens to `/cmd_vel`.

### Forward

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.15}}"
```

### Backward

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: -0.15}}"
```

### Stop

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
"{}"
```

A command close to zero activates the standing pose.

## Check that the gait controller is running

```bash
ros2 node list
```

You should see:

```text
/tripod_gait_controller
/robot_state_publisher
/ekf_filter_node
```

Check the position controller:

```bash
ros2 control list_controllers
```

Expected active controllers include:

```text
joint_state_broadcaster
hexapod_position_controller
```

Check the gait command topic:

```bash
ros2 topic echo /hexapod_position_controller/commands
```

You should see arrays containing **18 joint positions**.

Check joint feedback:

```bash
ros2 topic echo /joint_states
```

## Verify the tripod gait

The controller uses a normalized gait phase from `0.0` to `1.0`.

- Tripod A uses `phase`
- Tripod B uses `(phase + 0.5) % 1.0`

Therefore the two tripods are always **180° out of phase**.

Default gait parameters:

| Parameter | Default |
|---|---:|
| Update rate | 100 Hz |
| Gait frequency | 0.8 Hz |
| Duty factor | 0.60 |
| Stride | 0.35 rad |
| Lift | 0.25 rad |
| Neutral knee | 0.75 rad |
| Neutral ankle | 0.39 rad |
| Maximum linear speed | 0.20 m/s |

The controller is intentionally a **joint-space gait generator**, not a full inverse-kinematics or whole-body dynamic controller. The stride and lift values should therefore be tuned against the actual hexapod geometry before hardware use.

## Lightweight gait check

The repository includes a ROS-independent sanity check:

```bash
cd ~/hexapod_simulation/ros2_ws
python3 ../tests/test_tripod_gait.py
```

It verifies:

- Tripod membership
- 180° phase separation
- Gait phase wrapping
- Stride limits
- Lift limits

## Useful topics

| Topic | Direction | Purpose |
|---|---|---|
| `/cmd_vel` | ROS -> controller | Walking command |
| `/hexapod_position_controller/commands` | controller -> ros2_control | 18 joint position commands |
| `/joint_states` | simulation -> ROS | Joint feedback |
| `/odom` | Gazebo -> ROS | Odometry |
| `/imu` | Gazebo -> ROS | IMU |
| `/scan` | Gazebo -> ROS | LiDAR |
| `/camera/image_raw` | Gazebo -> ROS | Camera |
| `/clock` | Gazebo -> ROS | Simulation time |

## RViz-only visualization

For checking the URDF without Gazebo:

```bash
ros2 launch hexapod_description display.launch.py
```

This uses `joint_state_publisher` and RViz2. It is useful for checking the model and TF structure, but it does **not** run the Gazebo controller.

## Controller-only launch

`controller.launch.py` is intended to be used only when `/controller_manager` has already been created by Gazebo / `gz_ros2_control`.

For normal use, prefer:

```bash
ros2 launch hexapod_description sim.launch.py
```

## Troubleshooting

### Robot does not move

Check:

```bash
ros2 control list_controllers
```

Make sure `hexapod_position_controller` is active.

Then check:

```bash
ros2 topic echo /hexapod_position_controller/commands
```

If commands change but joints do not move, the issue is below the gait generator: controller activation, `gz_ros2_control`, joint interfaces, or Gazebo physics.

### Gait controller is running but no movement command is generated

Check:

```bash
ros2 topic echo /cmd_vel
```

The controller uses a deadband of `0.03`. A command inside this deadband causes the controller to return to its standing pose.

### Gazebo starts but controllers fail to spawn

The controller manager is created by `gz_ros2_control` after the robot is spawned. The full simulation launch intentionally waits before starting the controller spawners.

### Custom world argument

The simulation launch supports:

```bash
ros2 launch hexapod_description sim.launch.py world:=<world_file>
```

If no world is supplied, Gazebo starts with `empty.sdf`.

## Project structure

```text
hexapod_simulation/
├── README.md
├── assets/
│   └── images/
│       ├── hexapod_gazebo.png
│       └── hexapod_rviz.png
└── ros2_ws/
    └── src/
        ├── hexapod_description/
        │   ├── config/
        │   ├── launch/
        │   ├── meshes/
        │   ├── rviz/
        │   └── urdf/
        └── hexapod_controller/
            ├── config/
            ├── hexapod_controller/
            ├── launch/
            └── setup.py
```

## Current controller scope

The current controller is suitable for **simulation-stage tripod-gait development**.

It does not yet implement:

- Foot-space inverse kinematics
- Contact-state estimation
- Body attitude stabilization
- Terrain adaptation
- Closed-loop force control
- Dynamic gait adaptation

These are the natural next steps toward a research-grade legged-robot controller.
