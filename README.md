# Hexapod Simulation 🕷️

An **18-DOF hexapod simulation** built with **ROS 2 Jazzy** and **Gazebo Harmonic**. The project uses an alternating tripod gait, `ros2_control`, `gz_ros2_control`, Gazebo↔ROS 2 bridging, EKF state estimation, SLAM, and Nav2.

> **Target environment:** Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic.

---

## 1. Features

- 18-DOF hexapod: 6 legs × 3 joints.
- Alternating tripod gait controller.
- ROS 2 `/cmd_vel` velocity input.
- Gazebo-native `/model/hexapod/cmd_vel` bridge.
- `ros2_control` position control.
- `gz_ros2_control` integration with Gazebo Harmonic.
- RViz2 visualization.
- LiDAR, camera and IMU sensor bridges.
- EKF state estimation using `robot_localization`.
- SLAM using `slam_toolbox`.
- Cartographer launch support.
- Nav2 localization/navigation configuration.
- OpenNav Docking integration.
- Custom Gazebo terrain/world model.

---

## 2. System architecture

```mermaid
flowchart TD
    K[Teleop] --> V[/cmd_vel]
    V --> T[Tripod Gait Controller]
    T --> P[hexapod_position_controller]
    P --> C[gz_ros2_control]
    C --> G[Gazebo Harmonic]

    G --> B[ros_gz_bridge]
    B --> JS[/joint_states]
    B --> I[/imu]
    B --> L[/scan]
    B --> CAM[/camera/image_raw]

    JS --> E[robot_localization EKF]
    I --> E
    E --> O[/odom]

    L --> S[slam_toolbox / Cartographer]
    S --> M[/map]

    M --> N[Nav2]
    O --> N
    L --> N
    N --> V
```

---

# 3. Requirements

### Operating system

- Ubuntu 24.04 LTS

### Robotics software

- ROS 2 Jazzy
- Gazebo Harmonic
- `ros_gz_sim`
- `ros_gz_bridge`
- `gz_ros2_control`
- `ros2_control`
- Nav2
- `slam_toolbox`
- Cartographer
- `robot_localization`

### Hardware

The simulation can run without physical hardware. A discrete NVIDIA GPU is not required, although Gazebo/RViz performance depends on the system's graphics capability.

---

# 4. Install ALL dependencies 🚀

The repository contains a single dependency installer at the **root of `hexapod_simulation`**:

```text
hexapod_simulation/
├── README.md
├── install_dependencies.sh    ← dependency installer
├── assets/
└── ros2_ws/
```

## Step 1 — Clone/download the project

For a Git repository:

```bash
git clone <YOUR_REPOSITORY_URL>
cd hexapod_simulation
```

If you already have the project:

```bash
cd ~/hexapod_simulation
```

## Step 2 — Make the installer executable

```bash
chmod +x install_dependencies.sh
```

## Step 3 — Install dependencies

Run:

```bash
./install_dependencies.sh
```

The script installs the project's required:

- ROS 2 Jazzy packages
- Gazebo Harmonic integration
- `ros_gz_sim`
- `ros_gz_bridge`
- `gz_ros2_control`
- `ros2_control`
- controller packages
- `robot_localization`
- `slam_toolbox`
- Cartographer
- Nav2
- OpenNav Docking
- teleoperation
- build/colcon/rosdep tools

It also runs `rosdep` against:

```text
ros2_ws/src
```

to catch additional package dependencies.

---

# 5. What the installer adds to `.bashrc`

`install_dependencies.sh` automatically adds a managed environment block to:

```text
~/.bashrc
```

It sources:

```bash
source /opt/ros/jazzy/setup.bash
```

and defines:

```bash
export HEXAPOD_SIM_ROOT="..."
export HEXAPOD_WS="${HEXAPOD_SIM_ROOT}/ros2_ws"
```

It also configures Gazebo resource lookup:

```bash
export GZ_SIM_RESOURCE_PATH="${HEXAPOD_WS}/src:${GZ_SIM_RESOURCE_PATH}"
export GZ_SIM_RESOURCE_PATH="${HEXAPOD_WS}/install:${GZ_SIM_RESOURCE_PATH}"
```

This is important for the project's Gazebo resources, especially:

```text
package://hexapod_description/world/meshes/ground_rocks_18.obj
```

After installation, reload the shell:

```bash
source ~/.bashrc
```

---

# 6. Build the workspace

After installing dependencies:

```bash
cd ~/hexapod_simulation/ros2_ws
```

Clean previous build artifacts if they exist:

```bash
rm -rf build install log
```

Build:

```bash
colcon build --symlink-install
```

Source the workspace:

```bash
source install/setup.bash
```

Verify the packages:

```bash
ros2 pkg list | grep hexapod
```

Expected packages include:

```text
hexapod_controller
hexapod_description
hexapod_nav
hexapod_slam
```

---

# 7. Launch the simulation

Start the complete Gazebo simulation:

```bash
ros2 launch hexapod_description sim.launch.py
```

The launch file starts:

- Gazebo Harmonic
- custom hexapod world
- robot state publisher
- hexapod model
- `ros_gz_bridge`
- RViz2
- `gz_ros2_control`
- joint-state broadcaster
- position controller
- tripod gait controller
- `robot_localization` EKF

---

# 8. Teleoperation

The project uses ROS 2 `geometry_msgs/msg/Twist` on:

```text
/cmd_vel
```

Start teleoperation from another terminal:

```bash
source ~/.bashrc
cd ~/hexapod_simulation/ros2_ws
source install/setup.bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Standard controls:

| Key       | Action                  |
| --------- | ----------------------- |
| `i`     | Forward                 |
| `,`     | Backward                |
| `j`     | Rotate left             |
| `l`     | Rotate right            |
| `u`     | Forward + rotate left   |
| `o`     | Forward + rotate right  |
| `m`     | Backward + rotate left  |
| `.`     | Backward + rotate right |
| `k`     | Stop                    |
| `q / z` | Speed                   |

> **Note:** Standard `teleop_twist_keyboard` does not provide dedicated A/D strafe keys. The custom controller supports `linear.y`, but the default keyboard teleop does not directly expose it.

---

# 9. Custom Gazebo teleoperation

The project also contains:

```text
ros2_ws/src/hexapod_description/scripts/gazebo_teleop.sh
```

It publishes directly to:

```text
/model/hexapod/cmd_vel
```

Run:

```bash
ros2 run hexapod_description gazebo_teleop.sh
```

or, if required:

```bash
bash ~/hexapod_simulation/ros2_ws/src/hexapod_description/scripts/gazebo_teleop.sh
```

The configured bridge converts the Gazebo command into:

```text
/cmd_vel
```

---

# 10. Verify the ROS ↔ Gazebo bridge

Check the bridge:

```bash
ros2 node list | grep bridge
```

Inspect the main topics:

```bash
ros2 topic list
```

Important topics:

| Topic                 | Purpose                 |
| --------------------- | ----------------------- |
| `/clock`            | Gazebo simulation clock |
| `/cmd_vel`          | Body velocity command   |
| `/joint_states`     | Joint states            |
| `/odom`             | EKF/odometry            |
| `/imu`              | IMU                     |
| `/scan`             | LiDAR                   |
| `/camera/image_raw` | Camera                  |
| `/tf`               | TF                      |
| `/tf_static`        | Static TF               |

---

# 11. Verify ros2_control

Check controllers:

```bash
ros2 control list_controllers
```

Expected active controllers:

```text
joint_state_broadcaster
hexapod_position_controller
```

Check gait-controller output:

```bash
ros2 topic echo /hexapod_position_controller/commands
```

The gait controller publishes **18 joint-position targets**.

---

# 12. SLAM

The project includes `slam_toolbox`:

```bash
ros2 launch hexapod_slam online_async_launch.py
```

The default configuration is:

```text
ros2_ws/src/hexapod_slam/config/mapper_params_online_async.yaml
```

The SLAM node uses the simulated LiDAR topic:

```text
/scan
```

and the simulation clock:

```text
/clock
```

---

# 13. Cartographer

Cartographer launch support is included:

```bash
ros2 launch hexapod_slam cartographer.launch.py
```

> **Important:** Inspect `cartographer.launch.py` before using this launch path if your package has been renamed. The current file contains a legacy package-share reference to `bot_slam`; this should match the actual package name (`hexapod_slam`) before relying on the Cartographer launch file.

---

# 14. Nav2

Nav2 configuration is located at:

```text
ros2_ws/src/hexapod_nav/
├── config/
│   └── nav2_params.yaml
└── launch/
    ├── localization_launch.py
    └── navigation_launch.py
```

Localization:

```bash
ros2 launch hexapod_nav localization_launch.py
```

Navigation:

```bash
ros2 launch hexapod_nav navigation_launch.py
```

The configuration includes:

- AMCL
- Map Server
- Planner Server
- Controller Server
- MPPI Controller
- Behavior Server
- BT Navigator
- Waypoint Follower
- Smoother
- Velocity Smoother
- Collision Monitor
- Route Server
- OpenNav Docking

---

# 15. Project structure

```text
hexapod_simulation/
├── README.md
├── install_dependencies.sh
├── assets/
│
└── ros2_ws/
    └── src/
        ├── hexapod_description/
        │   ├── config/
        │   │   ├── bridge_config.yaml
        │   │   └── ekf.yaml
        │   ├── launch/
        │   │   ├── display.launch.py
        │   │   ├── sim.launch.py
        │   │   └── teleop.launch.py
        │   ├── meshes/
        │   ├── rviz/
        │   ├── scripts/
        │   ├── urdf/
        │   └── world/
        │       └── model.sdf
        │
        ├── hexapod_controller/
        │   ├── config/
        │   ├── launch/
        │   └── hexapod_controller/
        │       ├── gait_controller.py
        │       └── teleop.py
        │
        ├── hexapod_slam/
        │   ├── config/
        │   └── launch/
        │
        └── hexapod_nav/
            ├── config/
            └── launch/
```

---

# 16. Dependency summary

The installer explicitly covers the dependencies used by the current source tree.

### ROS 2 core

```text
ros-jazzy-desktop
ros-jazzy-xacro
ros-jazzy-robot-state-publisher
ros-jazzy-joint-state-publisher
ros-jazzy-rviz2
```

### Gazebo Harmonic

```text
ros-jazzy-ros-gz
ros-jazzy-ros-gz-sim
ros-jazzy-ros-gz-bridge
ros-jazzy-gz-ros2-control
gz-harmonic
```

### ros2_control

```text
ros-jazzy-ros2-control
ros-jazzy-ros2-controllers
ros-jazzy-controller-manager
ros-jazzy-forward-command-controller
ros-jazzy-joint-state-broadcaster
```

### State estimation

```text
ros-jazzy-robot-localization
```

### SLAM

```text
ros-jazzy-slam-toolbox
ros-jazzy-cartographer
ros-jazzy-cartographer-ros
```

### Nav2

```text
ros-jazzy-navigation2
ros-jazzy-nav2-bringup
ros-jazzy-nav2-amcl
ros-jazzy-nav2-map-server
ros-jazzy-nav2-planner
ros-jazzy-nav2-controller
ros-jazzy-nav2-bt-navigator
ros-jazzy-nav2-behaviors
ros-jazzy-nav2-waypoint-follower
ros-jazzy-nav2-smoother
ros-jazzy-nav2-velocity-smoother
ros-jazzy-nav2-collision-monitor
ros-jazzy-nav2-lifecycle-manager
ros-jazzy-nav2-route
ros-jazzy-nav2-mppi-controller
```

### Docking / teleoperation

```text
ros-jazzy-opennav-docking
ros-jazzy-teleop-twist-keyboard
```

---

# 17. Troubleshooting

### Gazebo cannot find the terrain

Check:

```bash
echo $GZ_SIM_RESOURCE_PATH
```

It should contain the workspace source/install locations.

Then verify:

```bash
ls ~/hexapod_simulation/ros2_ws/src/hexapod_description/world/
```

and:

```bash
ls ~/hexapod_simulation/ros2_ws/src/hexapod_description/world/meshes/
```

---

### ROS package cannot be found

Run:

```bash
source /opt/ros/jazzy/setup.bash
source ~/hexapod_simulation/ros2_ws/install/setup.bash
```

Then:

```bash
ros2 pkg list | grep hexapod
```

---

### Controller does not spawn

Check:

```bash
ros2 control list_controllers
```

and:

```bash
ros2 node list | grep controller
```

The Gazebo robot must be spawned before the controller spawners can connect to the `gz_ros2_control` controller manager.

---

### `/cmd_vel` is not moving the robot

Check:

```bash
ros2 topic echo /cmd_vel
```

Then:

```bash
ros2 topic echo /hexapod_position_controller/commands
```

The expected pipeline is:

```text
/cmd_vel
   ↓
tripod_gait_controller
   ↓
/hexapod_position_controller/commands
   ↓
gz_ros2_control
   ↓
Gazebo
```

---

# 18. Important simulation limitation

The current gait controller is a **joint-space tripod gait**. It does not yet perform full foot-space inverse kinematics, force control, contact estimation, or body stabilization.

Therefore:

- body drift can occur;
- feet may not maintain ideal ground contact;
- turning may be asymmetric;
- strafing may not be physically accurate;
- the robot can rotate/circle under certain gait configurations.

For a research-grade legged robot, the next major upgrade should be:

```text
Body velocity
      ↓
Foot trajectory generation
      ↓
Inverse kinematics
      ↓
Joint targets
      ↓
ros2_control
      ↓
Gazebo
      ↑
Contact + IMU + joint feedback
      │
Closed-loop gait stabilization
```

These are directly relevant to **legged bionics and humanoid locomotion research**.

---

## 19. Quick start

For a fresh machine after ROS 2 Jazzy has been installed:

```bash
cd ~/hexapod_simulation
chmod +x install_dependencies.sh
./install_dependencies.sh

source ~/.bashrc

cd ros2_ws
rm -rf build install log
colcon build --symlink-install

source install/setup.bash

ros2 launch hexapod_description sim.launch.py
```

Then, in another terminal:

```bash
source ~/.bashrc
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

That's the complete installation and startup path.
