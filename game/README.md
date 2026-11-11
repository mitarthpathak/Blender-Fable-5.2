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
| Upstairs fill lights | full | a quarter |

Low is aimed at Intel UHD 620 class graphics. If it is still too slow there,
start the game with `--rendering-method gl_compatibility`.

## Baked lighting

`world.tscn` holds the house, a `LightmapGI` node, a reflection probe for
each room and two dim fill lights upstairs (`FillBedroom`, `FillBoxroom`).
The model imports with lightmap UVs (`light_baking` set to static
lightmaps), and `scripts/world.gd` is a tool script that configures the
lights in the editor exactly as the game does.

**The lightmaps are not baked yet.** Godot only bakes from the editor, on a
machine with a GPU: there is no script or command-line bake. Until it is
done, indirect light indoors comes from the probes and fill lights (both
presets) and SDFGI (High only).

### Baking, step by step

1. Open the `game/` folder in the Godot 4.7.2 editor and wait for the import
   bar at the bottom to finish.
2. In the FileSystem dock double-click `world.tscn`.
3. In the Scene dock click the `LightmapGI` node.
4. In the toolbar above the 3D view press **Bake Lightmaps**. If it asks
   where to save, keep the suggested `res://world.lmbake`.
5. Wait for the progress bar. Do not switch scenes while it runs.
6. Press Ctrl+S to save `world.tscn` (it now points at the bake).
7. Run the game with F5 and walk the house on both presets (F1).

What is already set for you, so nothing needs changing first:

| Setting | Value | Why |
| --- | --- | --- |
| Quality | Medium | a balance; see below if it is slow |
| Bounces | 3 | enough for moonlight to reach the back of a room |
| Max texture size | 4096 | keeps the result small |
| Interior | on | the house is closed, so the sky adds nothing indoors |
| Environment | custom colour, the night ambient | `main.gd` makes its sky at run time, where the baker cannot see it |
| Probes | subdivision 8 | lights the player and the doors, which move |
| Moon and lamps | bake mode Dynamic | their direct light and shadows stay live; only the bounce is baked |
| Flickering hall light, television | not baked | they change |
| Doors | dynamic, lit by the probes | they move |
| Decals, glass, lampshades | left out | they have no lightmap |

Once a bake exists, `world.gd` switches the two fill lights off by itself:
the lightmap does their job.

### What to commit afterwards

```bash
git add game/world.tscn game/world.lmbake game/world.lmbake.import game/world.exr game/world.exr.import
git commit -m "Bake the house lightmaps"
```

Godot writes either a single `world.lmbake` or that plus `world.exr`
textures, depending on the bake; add whichever of those files exist. Both
kinds are stored in Git LFS. Then rebuild the Windows export so the `.pck`
contains the bake.

### If the bake is too slow (Intel UHD 620)

The baker runs on the GPU, and on integrated graphics it can take a very
long time or run out of memory. In order of how much each helps:

1. Select `LightmapGI` and set **Quality** to **Low**.
2. Set **Texel Scale** to `0.5` (a quarter of the pixels to compute).
3. Set **Bounces** to `2` and **Max Texture Size** to `2048`.
4. Turn **Use Denoiser** off, then on again for the final bake only.
5. If it still fails, bake on any PC with a dedicated GPU: the bake is saved
   in the files above and works on every machine afterwards.

To undo a bake, select `LightmapGI`, clear its **Light Data** property in
the Inspector and save the scene.

The flashlight is a `SpotLight3D` on the player camera, off by default;
`F` toggles it.

## Checks

After copying a new `house.glb` into `assets/house/`, import it, apply the
texture rules (`tools/texture_policy.py`: VRAM compression, mipmaps and a
size cap per texture; `--clean` also deletes textures the model no longer
uses) and import again:

```bash
godot --headless --path game --import
python3 game/tools/texture_policy.py --clean
godot --headless --path game --import
```

```bash
godot --headless --path game -- --selftest            # floor, stairs, front door
godot --path game -- --shots --quality=high           # screenshots from the hero cameras
godot --headless --path game --export-release "Windows Desktop" build/HouseInterior.exe
```
