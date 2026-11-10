#!/usr/bin/env bash
# Entry point for the "blender" MCP server registered in .mcp.json.
#
# stdout and stdin belong to the MCP protocol from the first byte, so nothing
# here may print to stdout or read stdin.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
. "$here/env.sh"

# A few seconds on a machine that has never run this, instant afterwards.
ensure_mcp_server

# Bring Blender up alongside the server instead of before it: an MCP client
# gives a server only a short time to answer its first message, and a cold
# start (download + install) takes longer than that. The server connects to
# Blender lazily on the first tool call, by which time it is normally ready.
mkdir -p "$BLENDER_STATE_DIR"
setsid nohup "$here/blender-up.sh" >>"$BLENDER_STATE_DIR/up.log" 2>&1 </dev/null &

exec "$MCP_BIN" "$@"
