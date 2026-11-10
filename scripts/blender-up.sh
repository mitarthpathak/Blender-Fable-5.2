#!/usr/bin/env bash
# Make sure a Blender with the MCP addon is running and listening.
#
# The addon only serves from a Blender that has a window (its commands run on
# the UI event loop), so on a machine with no screen Blender is started on an
# Xvfb virtual display with Mesa's software renderer. Safe to run repeatedly
# and from several processes at once.
#
#   scripts/blender-up.sh [file.blend]     # optional .blend to open on first start
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
. "$here/env.sh"

log() { printf '[blender-up] %s\n' "$*" >&2; }
listening() { (exec 3<>"/dev/tcp/127.0.0.1/${BLENDER_PORT}") 2>/dev/null; }

if listening; then
  log "already listening on ${BLENDER_HOST}:${BLENDER_PORT}"
  exit 0
fi

mkdir -p "$BLENDER_STATE_DIR"
exec 9>"$BLENDER_STATE_DIR/up.lock"
flock 9
# Someone else may have brought it up while we waited for the lock.
if listening; then
  log "already listening on ${BLENDER_HOST}:${BLENDER_PORT}"
  exit 0
fi

# A Blender that is running but not listening can no longer be reached: the
# addon was unloaded (`read_factory_settings` does that) or it is hung. Nothing
# can talk to it, so replace it rather than start a second one beside it.
if [ -n "$(blender_pids)" ]; then
  log "Blender is running but not listening on port ${BLENDER_PORT}; restarting it"
  "$here/blender-down.sh"
fi

if [ ! -x "$BLENDER_BIN" ] || [ ! -f "$HOME/.config/blender/${BLENDER_VERSION%.*}/config/userpref.blend" ]; then
  log "Blender is not installed yet; installing"
  "$here/install-blender.sh"
fi

display_num="${BLENDER_DISPLAY#:}"
if [ ! -S "/tmp/.X11-unix/X${display_num}" ]; then
  log "starting Xvfb on ${BLENDER_DISPLAY}"
  # Detached from this shell (setsid) and from the lock (9>&-) so it outlives us.
  setsid nohup Xvfb "$BLENDER_DISPLAY" -screen 0 "$BLENDER_SCREEN" -nolisten tcp \
    >"$BLENDER_STATE_DIR/xvfb.log" 2>&1 </dev/null 9>&- &
  for _ in $(seq 1 50); do
    [ -S "/tmp/.X11-unix/X${display_num}" ] && break
    sleep 0.1
  done
fi

geometry="${BLENDER_SCREEN%x*}"   # 1920x1080x24 -> 1920x1080
log "starting Blender ${BLENDER_VERSION} (log: $BLENDER_STATE_DIR/blender.log)"
# Blender tries Wayland before X11. An empty runtime dir makes that attempt
# fail quietly instead of printing a backtrace at the top of every log. The
# addon's update check is off because its version is pinned in env.sh.
mkdir -p "$BLENDER_STATE_DIR/runtime" && chmod 700 "$BLENDER_STATE_DIR/runtime"
env -u WAYLAND_DISPLAY \
  DISPLAY="$BLENDER_DISPLAY" \
  XDG_RUNTIME_DIR="$BLENDER_STATE_DIR/runtime" \
  LIBGL_ALWAYS_SOFTWARE=1 \
  BLENDERMCP_NO_UPDATE_CHECK=1 \
  setsid nohup "$BLENDER_BIN" \
    --no-window-focus \
    --window-geometry 0 0 "${geometry%x*}" "${geometry#*x}" \
    "$@" \
    --python "$here/blender/startup.py" \
  >"$BLENDER_STATE_DIR/blender.log" 2>&1 </dev/null 9>&- &
echo $! >"$BLENDER_STATE_DIR/blender.pid"

for _ in $(seq 1 120); do
  if listening; then
    log "ready on ${BLENDER_HOST}:${BLENDER_PORT}"
    exit 0
  fi
  if ! kill -0 "$(cat "$BLENDER_STATE_DIR/blender.pid")" 2>/dev/null; then
    log "ERROR: Blender exited during startup. Last log lines:"
    tail -n 20 "$BLENDER_STATE_DIR/blender.log" >&2 || true
    exit 1
  fi
  sleep 0.5
done

log "ERROR: Blender is running but the addon never opened port ${BLENDER_PORT}. Last log lines:"
tail -n 20 "$BLENDER_STATE_DIR/blender.log" >&2 || true
exit 1
