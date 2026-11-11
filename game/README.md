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
| F | Flashlight |
| F1 | Graphics quality: High or Low (remembered) |
| F3 | FPS counter |

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
- **Environment**: plain night fog for a sky, cool ambient light, AgX tone
  mapping. `scripts/world.gd` thickens and pales the Low preset's fog when
  the camera is outdoors (`HouseLights.apply_low_fog`).
- **Exterior**: the clapboard is modelled, one leaning board per course
  (`clapboard_*`). The boards cast no shadows and the roof casts
  double-sided ones; both are set in `scripts/house_lights.gd`.

## Graphics settings

| | High | Low |
| --- | --- | --- |
| Volumetric fog | on | off (cheap depth and ground fog, thicker outdoors) |
| SDFGI, SSR, SSIL | on | off |
| SSAO, glow, normal maps, decals, mipmaps, probes | on | on |
| Render scale | 100% | 77% with FSR upscaling |
| MSAA | 2x | off |
| Shadows | 4096 atlas, all lamps | 2048 atlas, moon and one lamp |

Low is aimed at Intel UHD 620 class graphics. If it is still too slow there,
start the game with `--rendering-method gl_compatibility`.

## Baked lighting

`world.tscn` holds the house, a `LightmapGI` node and a reflection probe for
each room. The model imports with lightmap UVs (`light_baking` set to static
lightmaps), and `scripts/world.gd` is a tool script that configures the
lights in the editor exactly as the game does.

**The lightmaps are not baked yet.** Godot only bakes from the editor: there
is no script or command-line bake, and this project was built without one.
To bake: open `world.tscn`, select `LightmapGI`, press **Bake Lightmaps**,
and commit the `.lmbake` and texture files it writes. Until then, indirect
light indoors comes from the per-room reflection probes (both presets) and
SDFGI (High only).

The flashlight is a `SpotLight3D` on the player camera, off by default;
`F` toggles it.

## Checks

```bash
godot --headless --path game -- --selftest            # floor, stairs, front door
godot --path game -- --shots --quality=high           # screenshots from the hero cameras
godot --headless --path game --export-release "Windows Desktop" build/HouseInterior.exe
```
