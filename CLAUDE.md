# Blender-Fable-5.2

Storage and tooling for Blender projects that Claude builds through the
[MCP for Blender](https://github.com/ahujasid/blender-mcp) server. Everything
worth keeping lives in this repository: the container Blender runs in is
thrown away when the session ends.

## How Blender runs here

Cloud sessions have no screen and no GPU. `scripts/blender-up.sh` starts a real
Blender 5.2 LTS on an Xvfb virtual display with Mesa's software renderer, and
the MCP for Blender addon inside it listens on `localhost:9876`.

`.mcp.json` registers the MCP server as `blender`. Its entry point,
`scripts/mcp-server.sh`, starts Blender in the background (installing it first
on a fresh container, about 30 seconds) and then runs the pinned server.

| Script | What it does |
| --- | --- |
| `scripts/install-blender.sh` | Download Blender (checksum-verified), install and enable the addon |
| `scripts/blender-up.sh [file.blend]` | Start Blender if it is not listening; replaces one that is stuck |
| `scripts/blender-down.sh [--all]` | Stop Blender (`--all` also stops Xvfb) |
| `scripts/bmcp.py` | Call the MCP tools from the shell |
| `scripts/env.sh` | Pinned versions, port, display. The one place to change them |

Logs: `~/.local/state/blender-mcp/` (`blender.log`, `up.log`, `xvfb.log`).

## Talking to Blender

Use the `mcp__blender__*` tools when they are in the tool list:
`get_addon_status`, `get_scene_info`, `execute_blender_code`, `look`,
`search_assets`, `import_asset`, `generate_3d`.

If they are not listed (the server was registered after the session started,
or is waiting for approval), `scripts/bmcp.py` reaches the same server:

```bash
scripts/bmcp.py tools
scripts/bmcp.py call get_scene_info
scripts/bmcp.py code projects/00-hello/build.py     # run a file inside Blender
scripts/bmcp.py --out .scratch/view.png look        # save what `look` sees
```

A tool call that fails with a connection error right after session start means
Blender is still coming up: run `scripts/blender-up.sh` and try again.

When a session is restored after sitting idle, its processes are gone and
Blender starts again **empty**. Check `get_scene_info` before continuing work,
and reopen the project's .blend with `bpy.ops.wm.open_mainfile(filepath=...)`.
Anything that was never saved is gone.

Leave every tool's `user_prompt` argument empty. It exists only to feed the
vendor's telemetry, which is switched off here.

## Rules that keep the bridge alive

- **Never call `bpy.ops.wm.read_factory_settings()`.** It unloads every addon,
  the bridge included, and Blender goes deaf. To start from an empty file use
  `bpy.ops.wm.read_homefile(use_empty=True)`.
- **After loading a file inside a script** (`read_homefile`, `open_mainfile`)
  `bpy.context` has no window, so `bpy.context.object` and most operators
  fail. Either do the load in its own tool call, or run the rest inside
  `with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]):`
  as `projects/00-hello/build.py` does.
- **One tool call may run for at most 180 seconds.** After that the call
  errors while Blender carries on, and nothing else can reach Blender until it
  finishes. Split long work into several calls.
- **Renders that will take longer than about two minutes go in their own
  process**, which also leaves the live Blender free:

  ```bash
  blender -b projects/x/x.blend -o //renders/frame_#### -f 1             # one frame
  blender -b projects/x/x.blend -o //renders/frame_#### -s 1 -e 120 -a   # animation
  ```

  Save the .blend first: the background process renders what is on disk.
- Run project scripts by path (`scripts/bmcp.py code file.py`, or
  `runpy.run_path(path, run_name="__main__")` through `execute_blender_code`)
  so `__file__` is set and tracebacks name the file.

## Rendering on this machine

4 CPU cores, 15 GB RAM, no GPU.

- **Use Cycles on the CPU with denoising on.** 1280x720 at 64 samples takes
  about 22 seconds for a simple scene, with real reflections and bounce light.
- EEVEE works through the software rasteriser but is slower here (about 32
  seconds for the same frame) and flatter. Use it only when asked for.
- Work at low samples and resolution while iterating; raise them for finals.
- `look` is a viewport capture: fast, and right for checking layout and
  framing. Judge lighting and materials from a real render.

## Where things go

```
projects/<nn-name>/
    build.py            script(s) that build the scene
    <name>.blend        the saved scene
    renders/            finished images and animations
    assets/             files only this project uses
assets/                 files shared between projects
assets/cache/           re-downloadable source files (not committed)
.scratch/               throwaway captures and test renders (not committed)
```

- Keep the script that builds a scene next to its .blend whenever the scene
  can be built by script; hand edits made through `execute_blender_code` are
  only in the .blend, so save it.
- Save with `bpy.ops.wm.save_as_mainfile(filepath=..., compress=True, relative_remap=True)`.
- A .blend must stand on its own: `import_asset` packs what it downloads;
  for anything else run `bpy.ops.file.pack_all()` before saving.
- **.blend, image, .glb and video files are stored in Git LFS**
  (`.gitattributes`). A new clone needs `git lfs install --local` once, and
  `git lfs ls-files` shows what is tracked. Every changed version of an LFS
  file is stored in full, so a .blend with packed textures costs its whole
  size on each commit: while a project is in progress keep textures as files
  beside the .blend (stored once) and pack them only for the final save.
- Keep HDRIs at 2k (4k at most), and check the size of a .blend before
  committing it.
- **Save, commit and push before finishing a piece of work.** Whatever is only
  in the running Blender is lost with the container.

## Asset libraries and generators

Poly Haven (CC0 HDRIs, textures, models) needs no account and is switched on
at startup by `scripts/blender/startup.py`. Sketchfab, Poly Pizza and the 3D
generators (Hyper3D, Tripo, Hunyuan3D, Meshy) need the user's own API keys:
ask for them, and never write a key into this repository.

## Privacy

`DISABLE_TELEMETRY=1` is set in `scripts/env.sh` and `.mcp.json`, and the
addon's telemetry consent is pinned off in `scripts/blender/enable_addon.py`.
Upstream otherwise reports usage to a third party. Keep all three as they are.

## Updating versions

Edit `scripts/env.sh` (for Blender, the version and the matching SHA-256 from
download.blender.org), then:

```bash
scripts/blender-down.sh
scripts/install-blender.sh
scripts/blender-up.sh
scripts/bmcp.py call get_addon_status     # "up_to_date": true
```

Read the upstream changelog before moving the `mcp-for-blender` pin: the
server runs with full access to this machine.
