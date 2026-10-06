#!/usr/bin/env bash
# Gazebo-native teleop for the hexapod.
# w/s = forward/back, a/d = left/right, q/e = yaw, x = stop, Ctrl-C = quit.
set -u
TOPIC="/model/hexapod/cmd_vel"
RATE=10
PUB_PID=""

stop_publisher() {
  if [[ -n "$PUB_PID" ]]; then
    kill "$PUB_PID" 2>/dev/null || true
    wait "$PUB_PID" 2>/dev/null || true
    PUB_PID=""
  fi
}

start_publisher() {
  stop_publisher
  local payload="$1"
  gz topic -t "$TOPIC" -m gz.msgs.Twist -r "$RATE" -p "$payload" >/dev/null 2>&1 &
  PUB_PID=$!
}

stop() {
  stop_publisher
  gz topic -t "$TOPIC" -m gz.msgs.Twist -p \
    'linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}' >/dev/null 2>&1 || true
}

trap stop EXIT INT TERM
printf '%s\n' 'Gazebo teleop: w/s forward/back, a/d left/right, q/e rotate, x stop'
while IFS= read -r -n1 key; do
  case "$key" in
    w) start_publisher 'linear: {x: 0.12}' ;;
    s) start_publisher 'linear: {x: -0.12}' ;;
    a) start_publisher 'linear: {y: 0.12}' ;;
    d) start_publisher 'linear: {y: -0.12}' ;;
    q) start_publisher 'angular: {z: 0.60}' ;;
    e) start_publisher 'angular: {z: -0.60}' ;;
    x|' ') stop ;;
    $'\003') exit 0 ;;
  esac
done
