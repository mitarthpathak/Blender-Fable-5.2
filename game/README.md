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
| Right / left mouse | Aim / fire (only once the character is installed, see below) |
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
- **Player**: `scripts/player.gd`, a capsule on a spring-arm camera. When
  the Mixamo files are in `assets/character/` (put them in
  `projects/03-character/mixamo/`, then run `tools/import_character.py` as
  that folder's README says), `scripts/character.gd` replaces the capsule
  with the animated human: an AnimationTree blending idle, walk and run by
  speed, an upper-body aim blend, fire and jump one-shots, and the rifle
  (`assets/character/rifle.glb`) on the right-hand bone. Without those
  files the game runs with the capsule exactly as before.
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
each room (hall, living room, kitchen, landing, bedroom, bathroom, utility
cupboard) and four
dim fill lights (`FillLiving`, `FillKitchen`, `FillBedroom`, `FillBathroom`).
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
| `presets/clear_day.tres` | **Clear Day**: a low late-autumn sun, a blue-grey sky, only a little haze. Added so the town can be checked (and filmed) without fog; F2 reaches it after Dusk. |

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

### The town world

![Junction on High, Night](screenshots/town/junction_night_high.png)

`world_town.tscn` is the house in its town (see `docs/TOWN.md`): Ashgrove
Street, the T-junction with Mill Road, five closed neighbouring houses and a
vacant lot. `main.tscn` and `world.tscn` are unchanged and still the default.

```bash
godot --path game -- --world=town                     # play the town from the editor build
build_town/HaldenRidge.exe                            # the town export (needs HaldenRidge.pck beside it)
```

The player starts in the hall as before; **E** opens the front door and the
screen door, and the path leads down to the street. Neighbours' porches can be
walked on; their doors are locked.

`scripts/town.gd` (on the root of `world_town.tscn`) sets the scene up in
code, like `main.gd` does for the house:

- **House pieces replaced, not edited.** The house's own `yard_ground`,
  `yard_paths`, `street_road`, `fence_picket`, `mailbox`, `telephone_pole`
  and `light_street_sodium` are removed by name when the town loads; the
  town model has its own at the same heights.
- **Collision.** Trimesh for ground, houses, fences, cars and barriers;
  cylinders for trees, poles, trash cans and the hydrant; none for mailboxes,
  leaf piles, grass, signs, wires or decals. The town model carries
  collision-only wedges (`-convcolonly` in Blender) for every curb and every
  flight of porch steps, because the player capsule cannot climb a 13 cm
  step by itself, and four invisible walls on the edge of the playable area.
  (The two wedges that used to carry the player over a board across the
  house's front doorway are dropped at load: the house no longer has it.)
- **Instancing.** 199 repeated props (grass clumps, leaf piles, trees, poles,
  lamp heads, mailboxes, cans, manholes) are folded into 15 `MultiMesh`
  nodes at load. The five houses are one mesh each and share their materials.
- **Lights.** Six sodium street lights (`street_sodium_P*`), one of them
  flickering, one more broken and dark; a dim warm light behind one window
  of 16 Ashgrove Street. All follow the lighting presets (street lights go
  off in Foggy Overcast Day).
- **Distance.** Street lights fade out past 55 m; small props fade between
  45 and 80 m. Fog hides them sooner.

The export preset **Halden Ridge Town** sets the feature tag `town`, which
makes the town the default world in that build only. `build_town/` holds a
`.gdignore`, so neither preset packs the other's build.

#### Presets outdoors

Every preset has an **Outdoors (town world only)** group: key light energy,
how much the key light and the street lights light the fog, fog density,
ambient and exposure. `world_town.tscn` is in the group `outdoor_world`, and
`LightingPresets` then reads those values instead of the indoor ones and
stops SDFGI from reading sky light. The house world never reads them, so
Night there is still exactly the original. Night's indoor fog values light
the whole street's fog at once (the moon alone turned it white), which is
why the town needs its own.

#### Baking lightmaps for the town

`world_town.tscn` has its own `LightmapGI` node, not baked yet (Godot bakes
only from the editor). `assets/town/town.gltf` imports with lightmap UVs
(`meshes/light_baking=2`, texel size 0.25 m). To bake:

1. Open `world_town.tscn`. `town.gd` is a tool script: in the editor it
   hides the replaced house pieces and gives the lights their game settings.
2. Select `LightmapGI` and press **Bake Lightmaps**. It is set to medium
   quality, 3 bounces, an 8192 atlas limit and a custom environment colour
   equal to the night fog colour, so the bake does not need a
   `WorldEnvironment` in the scene.
3. Commit the `.lmbake` file and the textures it writes.

The moon and the street lights are `BAKE_DYNAMIC`: direct light and shadows
stay live (so the presets can change them) and only their bounce is baked.
The flickering lamp is `BAKE_DISABLED`. The `MultiMesh` props are dynamic
and take their light from the lightmap's probes. `world.tscn`'s bake is
separate: bake both scenes if you use both.

#### Performance

Measured on the Low target itself, an Intel HD Graphics 620 (i5-7300U),
1600x900, with `-- --world=town --town-perf`:

| View | Low (58 % scale) | High | Draw calls (Low) | Triangles drawn (Low) |
| --- | --- | --- | --- | --- |
| Front door, looking out | 34 FPS | 2 FPS | 655 | 238 k |
| Junction | 43 FPS | 4 FPS | 483 | 210 k |
| Mill Road | 50 FPS | 6 FPS | 379 | 197 k |

These are after the second detail pass (car interiors, window interiors and
lit rooms, hero facades, single leaves, the gas station, the mill). Through
the passes the same views ran at 32 / 45 / 52, then 36 / 45 / 52, now
34 / 43 / 50 FPS, while draw calls doubled and triangles rose by a quarter:
this GPU is bound by pixels, and the added detail is small on screen, fades
with distance and is instanced where it repeats.

Draw calls and triangles include the shadow passes. The town model is about
209,000 triangles in 372 objects (84 unique meshes); with the house hidden
the main pass is 117 draw calls and 83,000 triangles.

That GPU is limited by pixels, not triangles: an empty scene runs at 70 FPS
and the house alone, from its own front door, at 23. So on Low the town:

- gives the street lights no shadows and a 16 m reach (the moon keeps its shadow),
- uses the cheapest soft-shadow filter,
- renders at 58 % scale with FSR instead of `main.gd`'s 77 % (`LOW_SCALE` in
  `town.gd`; `--scale=0.77` overrides it for a run),
- keeps the town's textures VRAM-compressed (texture memory 1.1 GB, down
  from 2.1 GB uncompressed; most of what is left is the house).

Dynamic resolution was tried first and dropped: changing the render scale
every half second hung the Intel driver after a few dozen changes.

High is not meant for that machine (2 to 6 FPS there); it needs a discrete GPU.

![Low: Night, Foggy Overcast Day, Dusk](screenshots/town/contact_sheet_low.jpg)
![High: Night, Foggy Overcast Day, Dusk](screenshots/town/contact_sheet_high.jpg)

#### Night fog on Low

Low has no volumetric fog. Outdoors at night it uses the distance fog from
Night's **Outdoors** group, a blue-grey that hides houses by about 30 m, and
`town.gd` draws a soft additive halo round each street light
(`outdoor_street_halo_low` sets its strength per preset). Colours in the
`.tres` files are sRGB, as everywhere in Godot: a fog colour of 0.1 is nearly
black on screen.

![Low after the detail pass: Night and Foggy Overcast Day](screenshots/town/detail_pass_low.jpg)

#### The mill on Low

The mill is 70 to 110 m away. High's volumetric fog leaves a faint shape of
it by itself; Low's distance fog would erase it, so in thick fog on Low
`town.gd` draws it unshaded and unfogged, a few percent darker than the fog
colour. In Clear Day it is drawn with its real materials.

#### Town checks

```bash
godot --headless --path game -- --world=town --town-selftest     # front door to the road, curbs, a porch, both ends
godot --path game -- --world=town --town-perf --quality=low      # FPS, draw calls, triangles
godot --path game -- --world=town --preset-shots --views=front_door,junction,side_street --out=res://screenshots/town
godot --headless --path game --export-release "Halden Ridge Town" build_town/HaldenRidge.exe
```

After importing new town textures headless, run
`python projects/03-town/godot_imports.py` and import again, so they are
VRAM-compressed.

## Halden Ridge Day (free-roam build)

The export preset **Halden Ridge Day** sets the feature tags `town` and
`dayroam`. `scripts/build_flavor.gd` reads them and gives that build its
defaults; the other two presets are unchanged.

| | Windows Desktop | Halden Ridge Town | Halden Ridge Day |
| --- | --- | --- | --- |
| World | the house alone | the town | the town |
| Player starts | inside the front door | inside the front door | inside the front door |
| Look on first start | Night | Night | Foggy Overcast Day |
| Quality on first start | High | High | Low |
| Settings file | `user://settings.cfg` | `user://settings.cfg` | `user://settings_day.cfg` |

They are first-start defaults only. F1 (quality), F2 (look) and F4 (settings
panel) work as in the other builds, and what the player picks is saved. The
day build keeps its own settings file so a Night or High saved by an older
build cannot override its first start.

```bash
godot --path game -- --flavor=day                                  # the day build's defaults, from source
godot --headless --path game -- --flavor=day --town-selftest
godot --headless --path game --export-release "Halden Ridge Day" build/day/HaldenRidgeDay.exe
godot --headless --main-pack game/build/day/HaldenRidgeDay.pck -- --selftest         # tests on the export
godot --headless --main-pack game/build/day/HaldenRidgeDay.pck -- --town-selftest
godot --headless --main-pack game/build/day/HaldenRidgeDay.pck -- --world=house --preset-check
```

`--preset-check` compares Night with the house world's own values, so on
this build it needs `--world=house`; in the town world the presets use their
outdoor values and the check lists those differences.

### Builds are not committed

`game/build/` and `game/build_town/` are in `.gitignore`. A build is
published as a GitHub Release on this repository (tag such as
`v0.1-dayroam`) with the `.exe` and the `.pck` as release assets; the `.pck`
must sit beside the `.exe`. The two `HouseInterior` files already tracked in
`build/` are from before this rule and are out of date.
