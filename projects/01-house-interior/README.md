# 01 House interior

A two-storey house interior for a third-person shooter. Night. The target is
AAA tactical-shooter realism: grounded, lived-in, tense.

![Floor plan](renders/01_layout_plan.png)

## Status

| Phase | State | Preview |
| --- | --- | --- |
| 1. Layout | Approved | `renders/01_layout_plan.png` |
| 2. Blockout | Done | `renders/02_blockout_*.png` |
| 3. Structure | Not started | |
| 4. Materials | Not started | |
| 5. Props | Not started | |
| 6. Lighting | Not started | |
| Final | Not started | packed .blend, .glb for Godot, 3 hero shots |

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

Build and render headless, which has no time limit:

```bash
cd projects/01-house-interior
blender -b --python build.py -- --phase blockout
blender -b blockout.blend --python render_views.py -- --views axon_0,axon_1,hall --prefix 02_blockout
```

## For Godot

- Every object is named for what it is (`wall_ext_south`, `floor_living`,
  `stairs`, `door_front`), one object per wall, floor and door.
- `stairs_ramp-convcolonly` is the stair collider: a convex wedge over the
  steps. Godot's importer reads the `-convcolonly` suffix, makes a convex
  collision shape from it and drops the visible mesh.
- Doors have their origin on the hinge line at floor level, so rotating a
  door about its own Z axis opens it.
