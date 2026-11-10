# Blender-Fable-5.2

Blender projects built by Claude, and the tooling that lets Claude drive
Blender from a cloud session.

![Smoke-test render: a gold Suzanne inside a glowing ring](projects/00-hello/renders/hello.png)

## What is set up

- **Blender 5.2.3 LTS**, downloaded from blender.org and checksum-verified,
  running on a virtual display so it works on a machine with no screen.
- **[MCP for Blender](https://github.com/ahujasid/blender-mcp) 2.2.7**
  (`mcp-for-blender` on PyPI), registered for Claude Code in `.mcp.json` as
  the server `blender`. Its telemetry is switched off.
- **Poly Haven** asset search and import (free CC0 HDRIs, textures and
  models), on by default.
- **Cycles** rendering on the CPU.

A Claude Code cloud session on this repository loads the `blender` server from
`.mcp.json`; the server installs Blender on a fresh machine (about 30 seconds)
and starts it. If Claude Code asks whether to trust the project's `blender`
MCP server, approve it.

## Layout

```
projects/     one folder per project: build scripts, the .blend, renders
assets/       files shared between projects
scripts/      install, start and stop Blender; MCP entry point; CLI client
CLAUDE.md     how Claude works in this repository
```

`projects/00-hello` is the smoke test: one script that builds a scene, saves
it and renders the image above.

## Running it yourself

```bash
scripts/blender-up.sh                                # install if needed, start Blender
scripts/bmcp.py call get_addon_status                # is the bridge healthy?
scripts/bmcp.py code projects/00-hello/build.py      # build, save and render the smoke test
scripts/blender-down.sh --all                        # stop everything
```

Needs Linux x64 with `uv`, `Xvfb` and Mesa. To use Blender on your own
computer instead, run `uvx mcp-for-blender setup` there; that is the upstream
installer and it configures your local Blender and MCP clients.
