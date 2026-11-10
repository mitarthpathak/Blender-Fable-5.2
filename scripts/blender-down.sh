#!/usr/bin/env bash
# Stop the Blender started by blender-up.sh. Unsaved scene changes are lost,
# so save the .blend first (see CLAUDE.md).
#
#   scripts/blender-down.sh           # stop Blender, leave the virtual display
#   scripts/blender-down.sh --all     # also stop Xvfb
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
. "$here/env.sh"

log() { printf '[blender-down] %s\n' "$*" >&2; }

# Stop one process: ask politely, then insist.
stop() {
  local pid="$1" name="$2"
  kill -0 "$pid" 2>/dev/null || return 0
  log "stopping $name (pid $pid)"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 50); do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 0.1
  done
  kill -9 "$pid" 2>/dev/null || true
}

pidfile="$BLENDER_STATE_DIR/blender.pid"
if [ -f "$pidfile" ]; then
  stop "$(cat "$pidfile")" "Blender"
  rm -f "$pidfile"
fi
# Anything else running this Blender build (e.g. one started by hand).
for pid in $(blender_pids); do
  stop "$pid" "Blender"
done

if [ "${1:-}" = "--all" ]; then
  for pid in $(pgrep -f "^Xvfb ${BLENDER_DISPLAY} " || true); do
    stop "$pid" "Xvfb"
  done
fi
