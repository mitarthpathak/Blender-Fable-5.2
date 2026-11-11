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
- **Environment**: night-street sky, cool ambient light, AgX tone mapping.

## Graphics settings

| | High | Low |
| --- | --- | --- |
| Volumetric fog | on | off (cheap distance fog) |
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

## Halden Ridge town and lighting presets (town-v1)

Added on the `town-v1` branch. Everything above still works as before.

### Lighting presets

![Presets: Night, Foggy Overcast Day, Dusk (rows: hallway and porch, High then Low)](screenshots/presets/contact_sheet.jpg)

Three looks, each a `LightingPreset` resource in `presets/`:

| File | Look |
| --- | --- |
| `presets/night.tres` | **Night** (default). Exactly the values `main.gd` and `house_lights.gd` used before presets existed. |
| `presets/foggy_day.tres` | **Foggy Overcast Day**: grey sky, heavy fog, soft shadowless light, street lights off. |
| `presets/dusk.tres` | **Dusk**: low warm sun from the west, violet fog, street lights just on. |

Open a `.tres` in the Godot inspector to tweak it: key light (moon or sun)
colour, energy, softness and angle; sky and ambient colour; room-probe
ambient; volumetric fog (High) and distance fog (Low); exposure for High and
Low; glow and grade; and multipliers for the lamps, street lights and lit
windows. `scripts/lighting_preset.gd` documents every field.

`scripts/lighting_presets.gd` applies the preset on top of what `main.gd`
sets up. `main.gd` only gained three hooks: it attaches the node after
loading the quality setting, re-applies the preset at the end of
`set_quality()`, and `_save_quality()` now loads `settings.cfg` before
writing so it keeps other sections.

| Key | Action |
| --- | --- |
| F2 | Cycle Night, Foggy Overcast Day, Dusk |
| F4 | Settings panel: preset dropdown and brightness slider (50 to 200 %) |

Both are saved in `user://settings.cfg` under a new `[lighting]` section
(`preset`, `brightness`); the `[graphics] quality` key is unchanged.
Brightness multiplies the preset's exposure, so 100 % is the preset as
authored.

Command line: `--preset=night|foggy_day|dusk`, `--brightness=1.2`,
`--preset-check` (applies Night over the original setup and lists any value
that changed; it reports 45 values, all identical, on High and Low), and
`--preset-shots [--quality=low] [--views=hallway,porch]`, which wrote the
screenshots above. `--env=prop:value,...` overrides Environment properties
for experiments.

**SDFGI sky light.** On High, SDFGI adds the background colour as light
wherever it sees the sky. Indoors that is right; outdoors it floods the
yard (the porch row of the Night column shows it: that is the original
game's look, kept on purpose). Foggy Day and Dusk turn
`sdfgi_read_sky_light` off; Night keeps it on to stay identical. The town
world turns it off for every preset, because there the player is outdoors.

### Presets and baked lightmaps

`world.tscn` keeps its `LightmapGI` node; the lightmaps are still to be
baked in the editor. The presets are built to work with that bake:

- The moon/sun stays **dynamic** (`BAKE_DYNAMIC`): its direct light and
  shadows are computed live, and only its bounce goes into the lightmap.
  That is why a preset can change its colour, energy and angle at run time.
- The **trade-off**: the baked bounce light is fixed at whatever preset was
  active in the editor when you baked (Night, with the tool script in
  `world.gd`). Under Foggy Day or Dusk the direct light is right, but the
  bounce in the lightmap is still Night's cool, dim bounce. Ambient, probe
  ambient, fog and exposure come from the preset and cover most of the
  difference, and on High SDFGI adds live bounce on top. Baking one
  lightmap per preset would fix it fully, at the cost of three times the
  lightmap memory and a swap on every preset change; it is not done here.
- Lamps that flicker are `BAKE_DISABLED` and stay fully live, as before.
