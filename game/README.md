# House Interior Test (Godot 4.7.2)

A third-person walkthrough of `projects/01-house-interior`.

![Hallway in Godot](screenshots/hallway_high.png)

## Run

Open `game/` in Godot 4.7.2, or run the Windows build in `build/`
(`HouseInterior.exe` needs `HouseInterior.pck` beside it).

| Key | Action |
| --- | --- |
| W A S D | Move |
| Shift / Space | Run / jump |
| Mouse | Look (Esc frees the pointer, click recaptures) |
| E | Open or close the nearest door |
| F1 | Graphics quality: High or Low (remembered) |

## How it is put together

`scripts/main.gd` instantiates `assets/house/house.glb` and sets everything
up in code, so a fresh export from Blender needs no hand edits:

- **Collision**: trimesh collision for walls, floors and furniture. The stair
  steps get none; the player walks the convex ramp the importer builds from
  `stairs_ramp-convcolonly`. Decals, curtains, rugs, cables and loose clutter
  are left out.
- **Doors**: every door keeps its hinge pivot and swings by the
  `opens_degrees` the model carries.
- **Lighting**: a cool moon, warm lamps, a scripted failing-bulb flicker on
  `light_hall_flicker`, and a television glow added as a light.
- **Environment**: night-street sky, cool ambient light, AgX tone mapping.

## Graphics settings

| | High | Low |
| --- | --- | --- |
| Volumetric fog | on | off (cheap distance fog) |
| SDFGI, SSR, SSAO, SSIL, glow | on | off |
| Render scale | 100% | 60% |
| MSAA | 2x | off |
| Shadows | 4096 atlas, all lamps | 1024 atlas, moon and one lamp |

Low is aimed at Intel UHD 620 class graphics. If it is still too slow there,
start the game with `--rendering-method gl_compatibility`.

## Checks

```bash
godot --headless --path game -- --selftest            # floor, stairs, front door
godot --path game -- --shots --quality=high           # screenshots from the hero cameras
godot --headless --path game --export-release "Windows Desktop" build/HouseInterior.exe
```
