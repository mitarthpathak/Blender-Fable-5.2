# 01 House interior

A two-storey house interior for a third-person shooter. Night. The target is
AAA tactical-shooter realism: grounded, lived-in, tense.

![Hallway at night](renders/06_lighting_hero_hallway.png)

![Floor plan](renders/01_layout_plan.png)

## Status

| Phase | State | Preview |
| --- | --- | --- |
| 1. Layout | Approved | `renders/01_layout_plan.png` |
| 2. Blockout | Done | `renders/02_blockout_*.png` |
| 3. Structure | Done | `renders/03_structure_*.png` |
| 4. Materials | Done | `renders/04_materials_*.png` |
| 5. Props | Done | `renders/05_props_*.png` |
| 6. Lighting | Done | `renders/06_lighting_hero_*.png` |
| Final | Done | `house_packed.blend`, `house.glb`, three hero shots |

The layout was approved as drawn: real-world scale, a box room upstairs
and the through living / dining room.

## Brief

**Layout**
- Ground floor: living room, and a hallway leading to the front door. The
  player will later open that door and walk out to a street, so it is a
  separate hinged object with its pivot on the hinge line.
- A staircase to a first-floor landing with one or two rooms off it.

**Game-ready rules**
- Real-world scale in metres. Ceilings about 2.7 m, doors about 2.1 m.
- Stairs at walkable game dimensions (about 17 cm rise, 28 cm tread) with a
  simple invisible ramp collider object alongside.
- Separate, sensibly named objects (walls, floor, stairs, door, props) that
  import cleanly into Godot.
- Efficient geometry: bevels and detail where the camera sees them, normal
  maps rather than millions of polygons.

**Detail**
- Poly Haven textures at 2K (wood floors, plaster, tiles, worn paint) and a
  night HDRI visible through the windows.
- Props: furniture, shelves, pictures, cables, clutter, a broken lamp,
  curtains, trim, skirting boards, light switches, wall damage and grime.
- Lighting: moonlight through the windows, a couple of warm practical lamps,
  one flicker-ready light, light fog or dust in the air.

**Process**
- Phases: layout, blockout, structure, materials, props, lighting. A preview
  render, a commit and a push after each one.
- .blend and image files go in Git LFS.
- At the end: the .blend saved with textures packed, a .glb exported for
  Godot, and three hero shots (hallway, stairs, upstairs room).

## The plan

All dimensions live in `plan.py`; nothing else hard-codes them.

- Footprint 7.90 x 8.60 m outside, 7.30 x 8.00 m inside. Exterior walls
  0.30 m, partitions 0.14 m.
- Ceilings 2.70 m. Floor to floor 3.06 m, which is 18 risers of 0.17 m.
- One straight stair along the west wall: 1.05 m wide, 0.28 m treads, 4.76 m
  run, open to the hallway, with a cupboard under its upper half.
- Ground floor: hallway 2.40 x 8.00 m (1.25 m clear beside the stair) and a
  through living / dining room 4.76 x 8.00 m with two ways in from the hall.
- First floor: landing and corridor around the stairwell, a front bedroom
  4.76 x 4.40 m and a rear box room / study 4.76 x 3.46 m.
- Front door 0.95 x 2.10 m in the south wall, opening inwards, street to the
  south. Other doors 0.90 x 2.10 m.

## Files

| File | Purpose |
| --- | --- |
| `plan.py` | The floor plan as data, plus sanity checks. No bpy |
| `layout.py` | Phase 1: draws and renders the plan from `plan.py` |
| `layout.blend` | The plan drawing. Not the house scene |
| `build.py` | Builds the scene from nothing, up to a chosen phase |
| `hb/` | The builder: shell, stair, joinery, materials, props, lighting |
| `render_views.py` | Headless preview renders: cutaways and eye-level views |
| `blockout.blend` | Phase 2 result: grey massing with furniture stand-ins |
| `house.blend` | The house scene, rebuilt by `build.py` at each later phase |
| `assets.py` | Manifest of everything taken from Poly Haven; running it downloads and tints |
| `decals.py` | Generates the grime and damage decal textures |
| `textures/`, `hdri/`, `models/` | The downloaded assets (CC0), in Git LFS |

Build and render headless, which has no time limit:

```bash
cd projects/01-house-interior
blender -b --python build.py -- --phase blockout
blender -b blockout.blend --python render_views.py -- --views axon_0,axon_1,hall --prefix 02_blockout
```

## Materials

Surfaces use Poly Haven texture sets at 2K: a base colour, a normal map and
one AO / roughness / metal image each. Every material is a single Principled
BSDF fed directly by those images, which is the form glTF carries, so Godot
receives the same materials. Texture scale is in the UVs (metres divided by
the texture's real size), not in a mapping node.

One plaster set serves all the painted walls, the ceiling and the joinery:
`assets.py` recolours its base colour per room and makes a glossier copy of
its roughness for paint, keeping the original stains and wear.

All Poly Haven assets are CC0.

## Lighting

- **Moon**: `light_moon`, a cool directional light from the south-west. It
  comes through the front windows and the tall stair window.
- **Street**: a night HDRI of a lamp-lit street, kept dim; it is what you see
  through the glass.
- **Practicals**: warm lamps on the hall table, the sideboard and the bedside.
- **Flicker-ready**: `light_hall_flicker` (the hall pendant) and
  `light_tv_flicker` carry a `flicker` custom property. In Blender the pendant
  has a noise modifier on its power; in an engine, drive the energy yourself.
- **Haze**: `fog_volume` is a render-only box of thin fog that turns the
  moonlight into beams. It is not exported; use the engine's volumetric fog.

Three cameras are saved in the scene: `cam_hero_hallway`, `cam_hero_stairs`
and `cam_hero_bedroom`.

## Deliverables

| File | What it is |
| --- | --- |
| `house_packed.blend` | The finished scene with every texture and the HDRI packed inside |
| `house.glb` | For Godot: meshes, materials with textures, point and directional lights, cameras |
| `renders/06_lighting_hero_*.png` | The three hero shots, 1920x1080 |

Rebuild everything from the scripts:

```bash
cd projects/01-house-interior
python3 assets.py && python3 decals.py
blender -b --python build.py -- --phase lighting
blender -b house.blend --python render_views.py -- --rig scene --samples 160 --res 1920x1080 \
    --views hero_hallway,hero_stairs,hero_bedroom --prefix 06_lighting
blender -b house.blend --python export_final.py
```

About 170,000 triangles in 174 mesh objects. Repeated furniture shares one
mesh per model.

## For Godot

- Every object is named for what it is (`wall_ext_south`, `floor_living`,
  `stairs`, `door_front`), one object per wall, floor and door.
- `stairs_ramp-convcolonly` is the stair collider: a convex wedge over the
  steps. Godot's importer reads the `-convcolonly` suffix, makes a convex
  collision shape from it and drops the visible mesh.
- Doors have their origin on the hinge line at floor level, so rotating a
  door about its own Z axis opens it (Y in Godot, which is Y-up). Each door
  carries `opens_degrees`, the turn that swings it fully open. `door_front`
  is shut; the wardrobe and cupboard doors are separate objects too.
- Glass and the decals use alpha blending. The television's glow is an area
  light, which glTF cannot carry: add it in the engine.
- The house has no exterior beyond its walls yet, and no collision apart
  from the stair ramp; let Godot generate trimesh collision for the shell.
