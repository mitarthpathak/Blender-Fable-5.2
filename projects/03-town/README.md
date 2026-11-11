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
| `tk/street_kit.py` | The street kit: ground, roads, poles and wires, lights, fences, props, trees, cars, blockers, collision helpers. |
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

Numbers: 232 objects, 44 unique meshes, 46 materials, about 116,000
triangles.

## Export

`game/assets/town/town.gltf` + `town.bin` + `textures/`, not a single `.glb`.
A `.glb` embeds the 145 MB of textures, and Git LFS would store all of it
again on every re-export; as separate files the textures are byte-identical
to the ones in `textures/` here, so LFS stores them once.

## Known shortfalls

- The cars are simple boxy shapes; fine in fog at a few metres, not hero props.
- Potholes are dark patches with a puddle, not real depressions.
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
