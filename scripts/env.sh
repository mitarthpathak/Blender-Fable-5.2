# Shared settings for the scripts in this folder. Sourced, never executed.
# Every value can be overridden from the environment.

# Blender build. The checksum is the official one published next to the tarball at
# https://download.blender.org/release/Blender5.2/blender-5.2.3.sha256
BLENDER_VERSION="${BLENDER_VERSION:-5.2.3}"
BLENDER_SHA256="${BLENDER_SHA256:-78486c018b4443efe5e75ab54c290ed8c15abafd249b862c2c9ce2530a918eec}"
BLENDER_HOME="${BLENDER_HOME:-/opt/blender-${BLENDER_VERSION}}"
BLENDER_BIN="${BLENDER_BIN:-${BLENDER_HOME}/blender}"

# MCP server + the Blender addon it bundles. Pinned on purpose: the server and
# the addon speak a versioned protocol, and a pin means a new upstream release
# is never run here before someone has looked at it.
MCP_PACKAGE="${MCP_PACKAGE:-mcp-for-blender==2.2.7}"
MCP_BIN="${MCP_BIN:-$HOME/.local/bin/mcp-for-blender}"

# Where the addon's socket listens, and the virtual display Blender draws on.
BLENDER_HOST="${BLENDER_HOST:-localhost}"
BLENDER_PORT="${BLENDER_PORT:-9876}"
BLENDER_DISPLAY="${BLENDER_DISPLAY:-:99}"
BLENDER_SCREEN="${BLENDER_SCREEN:-1920x1080x24}"

# Logs and pid files live outside the repository.
BLENDER_STATE_DIR="${BLENDER_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/blender-mcp}"

# The upstream package reports anonymous usage to a third party by default.
# Nothing about this project leaves the machine.
export DISABLE_TELEMETRY=1
export BLENDER_HOST BLENDER_PORT

# uv installs to ~/.local/bin, which a non-login shell may not have on PATH.
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH" ;; esac
export PATH

# PIDs of running processes whose executable is this Blender build, however
# they were started (full path, PATH lookup, or the /usr/local/bin symlink).
blender_pids() {
  local pid target
  target="$(readlink -f "$BLENDER_BIN" 2>/dev/null || true)"
  [ -n "$target" ] || return 0
  for pid in $(pgrep -x blender 2>/dev/null || true); do
    if [ "$(readlink -f "/proc/$pid/exe" 2>/dev/null || true)" = "$target" ]; then
      echo "$pid"
    fi
  done
}

# Install the pinned MCP server as a uv tool. Instant when that version is
# already installed. Doing this once, instead of `uvx` on every start, means
# the server launches without touching the network.
ensure_mcp_server() {
  uv tool install --quiet "$MCP_PACKAGE" >&2
  if [ ! -x "$MCP_BIN" ]; then
    MCP_BIN="$(uv tool dir --bin)/mcp-for-blender"
  fi
}
