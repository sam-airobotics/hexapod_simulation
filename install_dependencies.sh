#!/usr/bin/env bash
set -euo pipefail

# Hexapod Simulation dependency installer
# Target platform: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
#
# Place this file at:
#   hexapod_simulation/install_dependencies.sh
#
# Run:
#   cd ~/hexapod_simulation
#   chmod +x install_dependencies.sh
#   ./install_dependencies.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${SCRIPT_DIR}/ros2_ws"
BASHRC="${HOME}/.bashrc"
MARKER_BEGIN="# >>> HEXAPOD_SIMULATION_ENV >>>"
MARKER_END="# <<< HEXAPOD_SIMULATION_ENV <<<"

echo "============================================================"
echo " Hexapod Simulation - ROS 2 Jazzy / Gazebo Harmonic Setup"
echo "============================================================"
echo
echo "Project root : ${SCRIPT_DIR}"
echo "ROS workspace: ${WORKSPACE}"
echo

# ---------------------------------------------------------------------------
# 1. Platform checks
# ---------------------------------------------------------------------------
if [[ ! -f /etc/os-release ]]; then
    echo "ERROR: Cannot determine the operating system."
    exit 1
fi

source /etc/os-release

if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    echo "ERROR: This project is configured for Ubuntu 24.04."
    echo "Detected: ${PRETTY_NAME:-unknown}"
    exit 1
fi

if [[ "$(dpkg --print-architecture)" != "amd64" && "$(dpkg --print-architecture)" != "arm64" ]]; then
    echo "WARNING: Unusual architecture detected: $(dpkg --print-architecture)"
fi

# ---------------------------------------------------------------------------
# 2. ROS 2 Jazzy must already be installed
# ---------------------------------------------------------------------------
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
    echo "ERROR: ROS 2 Jazzy is not installed at /opt/ros/jazzy."
    echo
    echo "Install ROS 2 Jazzy first using the official ROS 2 instructions:"
    echo "https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html"
    exit 1
fi

source /opt/ros/jazzy/setup.bash

# ---------------------------------------------------------------------------
# 3. Base system tools
# ---------------------------------------------------------------------------
echo "[1/5] Installing build and dependency tools..."
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool

# ---------------------------------------------------------------------------
# 4. ROS 2 + Gazebo + simulation dependencies
# ---------------------------------------------------------------------------
echo
echo "[2/5] Installing ROS 2 Jazzy / Gazebo Harmonic dependencies..."

ROS_PACKAGES=(
    # ROS 2 desktop/runtime
    ros-jazzy-desktop
    ros-jazzy-xacro
    ros-jazzy-robot-state-publisher
    ros-jazzy-joint-state-publisher
    ros-jazzy-rviz2

    # Messages / TF / launch
    ros-jazzy-geometry-msgs
    ros-jazzy-sensor-msgs
    ros-jazzy-std-msgs
    ros-jazzy-nav-msgs
    ros-jazzy-tf2
    ros-jazzy-tf2-ros
    ros-jazzy-tf2-geometry-msgs
    ros-jazzy-rosgraph-msgs

    # Gazebo Harmonic / ROS-Gazebo integration
    ros-jazzy-ros-gz
    ros-jazzy-ros-gz-sim
    ros-jazzy-ros-gz-bridge
    ros-jazzy-gz-ros2-control

    # ros2_control
    ros-jazzy-ros2-control
    ros-jazzy-ros2-controllers
    ros-jazzy-controller-manager
    ros-jazzy-forward-command-controller
    ros-jazzy-joint-state-broadcaster

    # State estimation
    ros-jazzy-robot-localization

    # Teleoperation
    ros-jazzy-teleop-twist-keyboard

    # SLAM
    ros-jazzy-slam-toolbox
    ros-jazzy-cartographer
    ros-jazzy-cartographer-ros

    # Nav2 core
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

    # Docking
    ros-jazzy-opennav-docking
)

sudo apt install -y "${ROS_PACKAGES[@]}"

# Gazebo Harmonic command-line/runtime packages. ROS Jazzy's ros-gz stack
# targets Gazebo Harmonic.
echo
echo "[3/5] Verifying Gazebo Harmonic..."
if command -v gz >/dev/null 2>&1; then
    gz sim --versions 2>/dev/null || true
else
    echo "WARNING: 'gz' was not found after ROS package installation."
    echo "Installing the Gazebo Harmonic metapackage..."
    sudo apt install -y gz-harmonic
fi

# ---------------------------------------------------------------------------
# 5. rosdep for any dependency not covered explicitly above
# ---------------------------------------------------------------------------
echo
echo "[4/5] Running rosdep against the workspace..."

if [[ -d "${WORKSPACE}/src" ]]; then
    if command -v rosdep >/dev/null 2>&1; then
        if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
            sudo rosdep init 2>/dev/null || true
        fi
        rosdep update
        rosdep install \
            --from-paths "${WORKSPACE}/src" \
            --ignore-src \
            --rosdistro jazzy \
            -r -y || true
    fi
else
    echo "WARNING: ${WORKSPACE}/src does not exist yet."
fi

# ---------------------------------------------------------------------------
# 6. Add persistent environment variables to ~/.bashrc
# ---------------------------------------------------------------------------
echo
echo "[5/5] Updating ~/.bashrc..."

# Remove a previous installer-managed block, then add the current one.
if grep -qF "${MARKER_BEGIN}" "${BASHRC}" 2>/dev/null; then
    TMP_BASHRC="$(mktemp)"
    awk -v begin="${MARKER_BEGIN}" -v end="${MARKER_END}" '
        $0 == begin {skip=1; next}
        $0 == end   {skip=0; next}
        !skip       {print}
    ' "${BASHRC}" > "${TMP_BASHRC}"
    mv "${TMP_BASHRC}" "${BASHRC}"
fi

cat >> "${BASHRC}" <<EOF

${MARKER_BEGIN}
# ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash

# Hexapod Simulation workspace
export HEXAPOD_SIM_ROOT="${SCRIPT_DIR}"
export HEXAPOD_WS="\${HEXAPOD_SIM_ROOT}/ros2_ws"

# Gazebo Harmonic resource lookup.
# The parent directories are intentional: package://hexapod_description/...
# resolves the package directory through GZ_SIM_RESOURCE_PATH.
if [[ -d "\${HEXAPOD_WS}/src" ]]; then
    export GZ_SIM_RESOURCE_PATH="\${HEXAPOD_WS}/src\${GZ_SIM_RESOURCE_PATH:+:\${GZ_SIM_RESOURCE_PATH}}"
fi

if [[ -d "\${HEXAPOD_WS}/install" ]]; then
    export GZ_SIM_RESOURCE_PATH="\${HEXAPOD_WS}/install\${GZ_SIM_RESOURCE_PATH:+:\${GZ_SIM_RESOURCE_PATH}}"
fi

# Source the workspace if it has already been built.
if [[ -f "\${HEXAPOD_WS}/install/setup.bash" ]]; then
    source "\${HEXAPOD_WS}/install/setup.bash"
fi
${MARKER_END}
EOF

# Apply the same environment to this installer process.
source "${BASHRC}"

echo
echo "============================================================"
echo " Dependency installation complete."
echo "============================================================"
echo
echo "ROS_DISTRO          : ${ROS_DISTRO:-unknown}"
echo "Hexapod root        : ${HEXAPOD_SIM_ROOT:-${SCRIPT_DIR}}"
echo "Hexapod workspace   : ${HEXAPOD_WS:-${WORKSPACE}}"
echo "GZ_SIM_RESOURCE_PATH:"
echo "${GZ_SIM_RESOURCE_PATH:-<not set>}"
echo
echo "Next steps:"
echo "  1. source ~/.bashrc"
echo "  2. cd \"${WORKSPACE}\""
echo "  3. rm -rf build install log"
echo "  4. colcon build --symlink-install"
echo "  5. source install/setup.bash"
echo "  6. ros2 launch hexapod_description sim.launch.py"
echo
