#!/usr/bin/env bash
# Install Blender and the "MCP for Blender" addon. Safe to run repeatedly:
# each step is skipped when it is already done.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
. "$here/env.sh"

log() { printf '[install-blender] %s\n' "$*" >&2; }

# --- 1. Blender -------------------------------------------------------------
if [ -x "$BLENDER_BIN" ]; then
  log "Blender already installed at $BLENDER_HOME"
else
  series="${BLENDER_VERSION%.*}"
  url="https://download.blender.org/release/Blender${series}/blender-${BLENDER_VERSION}-linux-x64.tar.xz"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  log "Downloading $url"
  curl -fsSL --retry 4 --retry-delay 2 -o "$tmp/blender.tar.xz" "$url"
  log "Verifying checksum"
  echo "${BLENDER_SHA256}  $tmp/blender.tar.xz" | sha256sum -c - >&2
  log "Extracting to $BLENDER_HOME"
  mkdir -p "$tmp/extract"
  tar -xJf "$tmp/blender.tar.xz" -C "$tmp/extract" --strip-components=1
  mkdir -p "$(dirname "$BLENDER_HOME")"
  rm -rf "$BLENDER_HOME"
  mv "$tmp/extract" "$BLENDER_HOME"
fi

# Put `blender` on PATH when we are allowed to.
if [ -w /usr/local/bin ] && [ "$(readlink -f /usr/local/bin/blender 2>/dev/null)" != "$BLENDER_BIN" ]; then
  ln -sf "$BLENDER_BIN" /usr/local/bin/blender
fi

# Blender is a desktop application; say plainly what is missing rather than
# failing later with a cryptic loader error.
missing="$(ldd "$BLENDER_BIN" 2>/dev/null | awk '/not found/ {print $1}' | sort -u | tr '\n' ' ')"
if [ -n "$missing" ]; then
  log "ERROR: system libraries missing for Blender: $missing"
  exit 1
fi
for tool in Xvfb uv; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    log "ERROR: '$tool' is required but not installed"
    exit 1
  fi
done

# --- 2. MCP server and addon ------------------------------------------------
series="$("$BLENDER_BIN" --version | awk '/^Blender/ {split($2, v, "."); print v[1] "." v[2]; exit}')"
addons_dir="${BLENDER_USER_ADDONS:-$HOME/.config/blender/${series}/scripts/addons}"
log "Installing $MCP_PACKAGE and its addon into $addons_dir"
ensure_mcp_server
"$MCP_BIN" install-addon --addons-dir "$addons_dir" >&2

# --- 3. Enable it and save preferences --------------------------------------
# The addon cannot serve from `blender -b`, but enabling it there is fine:
# the preference is saved and takes effect when Blender starts with a display.
"$BLENDER_BIN" --background --python "$here/blender/enable_addon.py" >&2

log "Done: Blender ${BLENDER_VERSION} + $MCP_PACKAGE"
