# 03 Town: Halden Ridge

The streets around the player's house: Ashgrove Street, the T-junction with
Mill Road, five closed neighbouring houses and a vacant lot, built from a
modular kit to the art bible (`docs/ART_BIBLE.md`). The layout and the
reasoning are in `docs/TOWN.md`; the Godot side is in `game/README.md`.

![Junction](renders/03_junction.png)

| | |
| --- | --- |
| ![Out of the front door](renders/03_front_door.png) | ![Mill Road](renders/03_side_street.png) |
| ![Town plan](renders/01_town_plan.png) | ![A kit house](renders/02_kit_house_sample.png) |

## Files

| File | What it is |
| --- | --- |
| `plan.py` | Every town dimension, pure data, in the house's axes. Edit this to move things. |
| `layout.py` | Draws `renders/01_town_plan.png` from the plan (matplotlib, no Blender). |
| `assets.py` | The Poly Haven (CC0) texture manifest; running it downloads what is missing. |
| `derive.py` | Makes the neutral paint maps and draws the decal textures (PIL, numpy). |
| `tk/core.py` | Mesh builder and the shared PBR materials. |
| `tk/house_kit.py` | The house kit: clapboard, windows, doors, porches, roofs, gutters, chimneys. |
| `tk/street_kit.py` | The street kit: ground, roads with real pothole dips, weeds and moss, poles and wires, lights, fences, props, trees, blockers, collision helpers. |
| `tk/cars.py` | The cars: a lofted sedan, station wagon and pickup. |
| `tk/detail.py` | Street detail, the story on each lot, single leaves, and the fog ends. |
| `tk/facade.py` | Close-up dressing: window interiors and lit rooms, shutters, brackets, plaques, lanterns, porch furniture. |
| `tk/store.py` | Ridge Gas & Grocery at the end of Mill Road, and the Halden mill in the distance. |
| `detail_maps.py` | Detail-pass decals, flat-material texture sets, and a normal + ORM map for every generated decal (run by `derive.py`). |
| `godot_imports.py` | Sets VRAM compression on newly imported town textures in `game/`. |
| `build.py` | Blender entry point: `kit`, `town` and `stills` stages. |
| `kit.blend` | The kit catalogue laid out for inspection. |
| `town.blend` | The assembled town (textures as files beside it, not packed). |
| `textures/` | Poly Haven sets, `derived/` neutral maps, `decals/` generated maps. |

## Rebuilding

```bash
python projects/03-town/assets.py                              # fetch textures (once)
python projects/03-town/derive.py                              # derived maps and decals
python projects/03-town/layout.py                              # the plan drawing
blender -b --factory-startup -P projects/03-town/build.py -- kit      # kit.blend + renders/02_kit_*.png
blender -b --factory-startup -P projects/03-town/build.py -- town     # town.blend + game/assets/town/town.gltf
blender -b --factory-startup -P projects/03-town/build.py -- stills   # renders/03_*.png (64 samples, about 5 min each)
```

This part was built with Blender 4.5 on Windows in background mode, because
the MCP for Blender bridge in `scripts/` is Linux-only and did not connect
here. The scripts use nothing newer than 4.5 and `town.blend` opens in 5.2.

## How it is made

- **One material per surface type, colour in the vertices.** Siding, trim,
  doors and car paint use near-white "neutral" albedo maps derived from the
  Poly Haven sets; each house's paint colour, its grime towards the ground
  and its stripped boards are vertex colours that multiply the map. Five
  houses in five colours share one siding material. Every textured material
  has albedo, normal and an ARM map (occlusion, roughness, metalness).
- **Real clapboard.** Each board is geometry with a 22 mm step, cut round
  the openings, so the rows catch light at grazing angles.
- **Wear** comes from the plan's `wear` value per house: more grime, boards
  with the paint gone, missing balusters, a tin porch roof, a sagging porch
  post, boarded and broken windows.
- **Wires** are true catenaries (`_catenary` solves the curve for the sag).
- **Instancing.** Poles, lamp heads, mailboxes, trash cans, manholes, trees,
  leaf piles, grass clumps and barriers are one mesh each, placed as linked
  duplicates; Godot draws them as MultiMeshes. Each house is merged into one
  object so it costs one draw call per material.
- **Albedo range.** Paints are 11 to 42 % linear; nothing is below 4 % or
  above 80 % except the emissive lamp and window materials.

Numbers: 372 objects, 84 unique meshes, 74 materials, about 209,000
triangles.

## Detail pass

- **Cars** are lofted bodies: a seven-point cross-section swept along the
  car, with the hood, windshield, roof and trunk coming from how high the
  greenhouse stands at each station. Wheel arches are cut into the sides
  with a dark liner behind; bumpers, lamps, grille, mirrors, door shuts,
  handles and wipers are added; wheels are sound, flat or missing; rust
  sits on the sills and arches; dirt and wet leaves lie on the flat tops.
  The sedan is on flat tyres, the wagon on blocks, the pickup crashed.
- **Potholes** are cut into the road mesh as 7.5 cm dips with a broken rim
  and standing water.
- **Weeds and moss** grow from sidewalk cracks, slab joints and both sides
  of every curb.
- **Every generated texture has a normal and an ORM map** now, and glass,
  chrome, wire and the plastics have small tiling sets instead of flat
  colours. Still flat on purpose: the black behind windows and under cars
  (`interior_dark`), the two emissive materials and the screen-door mesh.
- **Street detail**: wet leaves in the gutters, storm drains, no-parking
  signs, a bus stop and bench, three transformers, glass under the dead
  lamp, uncollected trash, a shopping cart, a bicycle, flyers on the poles
  (a missing cat, a town meeting about the mill, a yard sale), tyre marks
  and oil.
- **Lot stories**: 14 the player's hose and unread paper; 12 the yard sale
  from the flyer, left out; 16 a porch swing, pumpkins and a sheet ghost;
  15 a ball, wagon, tricycle and sandbox in the long grass; 17 the sale
  sign and the dead sedan; 3 Mill Road an empty dog house and chain; 4 the
  wagon on blocks, tyres, pallets and a mattress.
- **Fog ends**: dead trees and a dark tree line beyond each closed street
  end, so the view dissolves instead of stopping at a fence.

## Detail pass 2 (film close-ups)

- **Cars**: interiors (seats with a split seam, dashboard, steering wheel,
  gear lever, parcel shelf, papers, a cup, a bag; the wagon's radio gone and
  its wires hanging) behind see-through glass with dust and streaks, and an
  inner skin so the cabin is closed.
- **Windows**: see-through glass over curtains with folds, blinds, sheets or
  a dark recess; three lit windows show a room (`tk/facade.py`).
- **Hero facades**: shutters, eave and post brackets, gable vents, number
  plaques, lanterns, kick plates and letter slots; rocking chairs, side
  tables, doormats and hanging baskets on the porches.
- **Street**: a transformer with leads on every pole and a service drop to
  every building; the failing lamp is the one at the junction; pointed
  pickets, capped posts, the player's gate; detailed mailboxes; galvanised
  bins; trees rebuilt with a leader, side limbs and drooping twigs.
- **Leaves** in three layers: flat decals, about 3,500 single leaves, piles.
- **Ridge Gas & Grocery** and **the Halden mill** (`tk/store.py`).
- **Daylight**: the backdrop is bark-coloured instead of black, plastics are
  sun-faded, and `build.py -- stills --light day` renders under a real sky.
- A fix: since detail pass 1 the plain-colour materials (the dark behind
  windows, lamp faces, the screen-door mesh) had lost their colour and were
  mid-grey. They are right again.

Still flat colours on purpose: `interior_dark`, the emissive lamp, tube and
window materials, and the screen-door mesh.

![Out of the front door, day](renders/04_front_door_day.png)
![The junction, day](renders/04_junction_day.png)
![16 Ashgrove's porch at night](renders/03_porch_16.png)

![Cars](renders/02_kit_cars.png)
![Curb detail](renders/03_detail_curb.png)

## Export

`game/assets/town/town.gltf` + `town.bin` + `textures/`, not a single `.glb`.
A `.glb` embeds the 145 MB of textures, and Git LFS would store all of it
again on every re-export; as separate files the textures are byte-identical
to the ones in `textures/` here, so LFS stores them once.

## Known shortfalls

- The cars are mid-poly lofts; the interiors are simple shapes, right for a
  look through the glass, not for a shot from inside.
- Lit rooms are three walls, a floor and a few pieces of furniture: sets, not interiors.
- The mill is distant geometry (about 600 triangles); it cannot be approached.
- Flyers and signs are legible up close only; their text is 384 px wide.
- The catalogue renders (`02_kit_houses.png`) show porches and roofs without
  walls under them: it is a parts sheet, not a scene.
- Lightmaps are not baked (editor only); see `game/README.md`.

## Merge notes: existing files touched

Everything else on this branch is a new file.

| Existing file | Change | Why |
| --- | --- | --- |
| `game/scripts/main.gd` | +16 lines, 1 line changed. A `TOWN_SCENE` constant and `_world_scene()`; `_ready()` loads `_world_scene()` instead of `WORLD_SCENE` and calls `LightingPresets.attach(self)` after `_load_quality()`; `set_quality()` ends by re-applying the preset; `_save_quality()` loads `settings.cfg` before writing. | World selection (`--world=town` or the `town` feature tag); presets must survive a quality change; saving quality must not wipe the new `[lighting]` section. No existing behaviour, constant or key changed. |
| `game/export_presets.cfg` | Appended `[preset.1]` "Halden Ridge Town" and `[preset.1.options]`. `[preset.0]` is byte-for-byte as it was. | The new build in `game/build_town/`. |
| `game/README.md` | One section appended at the end: "Halden Ridge town and lighting presets (town-v1)". | Documentation. |
| `game/.gitignore` | Two lines appended: a comment and `build_town/`. | Windows builds are made locally and no longer committed. |

Not touched: `projects/00-hello`, `projects/01-house-interior`,
`projects/02-soldier`, `game/assets/house/**`, `game/build/**`,
`game/world.tscn`, `game/main.tscn`, `game/project.godot`,
`game/scripts/player.gd`, `house_lights.gd`, `world.gd`, the root
`README.md`, `CLAUDE.md`, `.gitattributes`, `.mcp.json`, `scripts/**`,
`docs/ART_BIBLE.md`, and every existing `.blend`, `.glb` and image.

Things a merge should know:

- Opening the project in Godot on Windows rewrites the line endings of the
  `.import` files under `game/assets/house/` and `game/screenshots/`. Those
  rewrites were discarded before every commit here (`git checkout --`).
- No Windows build of the town is on this branch. One was committed locally
  before builds were stopped; it was never pushed and is parked on the local
  branch `town-v1-build`. Export locally with the command in `game/README.md`.
- The existing "Windows Desktop" preset exports all resources, so if it is
  re-exported after the merge its `.pck` will also contain the town assets
  (about 150 MB more). The preset itself was not changed.
- The house has a fault the town works round without touching it: the
  water-table board of `exterior_trim` runs across the front doorway, 14 cm
  above the floor, so the player could not walk out. The town model adds two
  collision-only wedges over it (`door_sill_ramp_*`). The proper fix is in
  `projects/01-house-interior/hb/exterior.py` (`trim()` should skip the door
  opening on the south face).
- The character branch should not conflict: nothing here edits `player.gd`.
  If that branch also edits `main.gd`'s `_ready()`, the two edits are on
  neighbouring lines.
