#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${PROJECT_ROOT}/ros2_ws"
BASHRC="${HOME}/.bashrc"
BEGIN_MARKER="# >>> HEXAPOD_SIMULATION_ENV >>>"
END_MARKER="# <<< HEXAPOD_SIMULATION_ENV <<<"

if [[ ! -f /etc/os-release ]]; then echo 'ERROR: Cannot determine OS.'; exit 1; fi
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "ERROR: This installer requires Ubuntu 24.04 LTS. Detected: ${PRETTY_NAME:-unknown}"; exit 1
fi
ARCH="$(dpkg --print-architecture)"
[[ "$ARCH" == amd64 || "$ARCH" == arm64 ]] || { echo "ERROR: Unsupported architecture: $ARCH"; exit 1; }

echo '[1/8] Installing system tools...'
sudo apt update
sudo apt install -y curl wget gnupg lsb-release ca-certificates software-properties-common build-essential git python3-pip python3-venv python3-colcon-common-extensions python3-rosdep python3-vcstool
sudo add-apt-repository universe -y

 echo '[2/8] Configuring ROS 2 repository...'
sudo mkdir -p /etc/apt/keyrings
sudo curl -L https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /etc/apt/keyrings/ros-archive-keyring.gpg
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

echo '[3/8] Configuring Gazebo Harmonic repository...'
sudo mkdir -p /usr/share/keyrings
sudo curl -L https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable noble main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
sudo apt update

echo '[4/8] Installing ROS 2 Jazzy...'
sudo apt install -y ros-jazzy-desktop
source /opt/ros/jazzy/setup.bash

echo '[5/8] Installing Gazebo Harmonic and ROS-Gazebo integration...'
sudo apt install -y gz-harmonic ros-jazzy-ros-gz ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge ros-jazzy-gz-ros2-control

echo '[6/8] Installing project dependencies...'
sudo apt install -y \
  ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher ros-jazzy-rviz2 \
  ros-jazzy-geometry-msgs ros-jazzy-sensor-msgs ros-jazzy-std-msgs ros-jazzy-nav-msgs \
  ros-jazzy-tf2 ros-jazzy-tf2-ros ros-jazzy-tf2-geometry-msgs ros-jazzy-rosgraph-msgs \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers ros-jazzy-controller-manager \
  ros-jazzy-forward-command-controller ros-jazzy-joint-state-broadcaster \
  ros-jazzy-robot-localization ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-slam-toolbox ros-jazzy-cartographer ros-jazzy-cartographer-ros \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-nav2-amcl ros-jazzy-nav2-map-server \
  ros-jazzy-nav2-planner ros-jazzy-nav2-controller ros-jazzy-nav2-bt-navigator ros-jazzy-nav2-behaviors \
  ros-jazzy-nav2-waypoint-follower ros-jazzy-nav2-smoother ros-jazzy-nav2-velocity-smoother \
  ros-jazzy-nav2-collision-monitor ros-jazzy-nav2-lifecycle-manager ros-jazzy-nav2-route \
  ros-jazzy-nav2-mppi-controller ros-jazzy-opennav-docking

echo '[7/8] Resolving workspace dependencies with rosdep...'
if [[ -d "${WORKSPACE}/src" ]]; then
  if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then sudo rosdep init 2>/dev/null || true; fi
  rosdep update
  rosdep install --from-paths "${WORKSPACE}/src" --ignore-src --rosdistro jazzy -r -y || true
else
  echo "WARNING: ${WORKSPACE}/src not found; skipping rosdep workspace scan."
fi

echo '[8/8] Updating ~/.bashrc...'
if grep -qF "$BEGIN_MARKER" "$BASHRC" 2>/dev/null; then
  tmp="$(mktemp)"
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '$0==begin{skip=1;next} $0==end{skip=0;next} !skip{print}' "$BASHRC" > "$tmp"
  mv "$tmp" "$BASHRC"
fi
cat >> "$BASHRC" <<EOF_BASH

$BEGIN_MARKER
source /opt/ros/jazzy/setup.bash
export HEXAPOD_SIM_ROOT="$PROJECT_ROOT"
export HEXAPOD_WS="\${HEXAPOD_SIM_ROOT}/ros2_ws"
if [[ -d "\${HEXAPOD_WS}/src" ]]; then export GZ_SIM_RESOURCE_PATH="\${HEXAPOD_WS}/src\${GZ_SIM_RESOURCE_PATH:+:\${GZ_SIM_RESOURCE_PATH}}"; fi
if [[ -d "\${HEXAPOD_WS}/install" ]]; then export GZ_SIM_RESOURCE_PATH="\${HEXAPOD_WS}/install\${GZ_SIM_RESOURCE_PATH:+:\${GZ_SIM_RESOURCE_PATH}}"; fi
if [[ -f "\${HEXAPOD_WS}/install/setup.bash" ]]; then source "\${HEXAPOD_WS}/install/setup.bash"; fi
$END_MARKER
EOF_BASH
source "$BASHRC"

if [[ -d "${WORKSPACE}/src" ]]; then
  cd "$WORKSPACE"
  colcon build --symlink-install
fi

echo
echo '============================================================'
echo ' INSTALLATION COMPLETE'
echo '============================================================'
echo "ROS 2: $(echo "${ROS_DISTRO:-unknown}" | tr '[:lower:]' '[:upper:]')"
echo 'Gazebo: Harmonic'
echo "Project: ${PROJECT_ROOT}"
echo
echo 'Next: source ~/.bashrc'
echo 'Then:  ros2 launch hexapod_description sim.launch.py'
