# House review

A self-review of the house model against `docs/ART_BIBLE.md` and against what
a current big-budget game interior looks like (the level of Red Dead
Redemption 2 or Modern Warfare: every surface with a history, nothing
floating, nothing repeated where the eye can catch it).

## How it was judged

Every room, the porch and all four sides were rendered in Cycles at neutral
exposure, with the night lighting and haze switched off, so faults are not
hidden in the dark:

```bash
blender -b house.blend --python render_views.py -- --rig work --prefix 13_before --samples 64 --res 1280x720 \
    --views hall,hall_back,stairs,living,living_back,kitchen,kitchen_sink,kitchen_fridge,landing,bedroom,bedroom_back,bathroom,bathroom_sink,utility
blender -b house.blend --python render_views.py -- --rig day --prefix 13_before --samples 64 --res 1280x720 \
    --views ext_front,ext_back,ext_east,ext_west,ext_porch,ext_back_corner,ext_back_door
```

`--rig work` is an even lamp under each ceiling; `--rig day` (new) is an
overcast sky with a soft sun, for the outside. The stills are
`renders/13_before_*.png`.

No notes were supplied by the owner for this pass (the brief's "MY NOTES"
line was left as its placeholder), so the list below is the model's own.

## The top 15 problems, worst first

| # | Problem | Where it shows |
| --- | --- | --- |
| 1 | **The side walls are blank.** The east wall is 8.6 m of unbroken siding with no opening at all, the west wall has one stair window. From the town the house reads as a box, and a house with a fireplace has no chimney. | `ext_east`, `ext_west`, `ext_back_corner` |
| 2 | **The back of the house is unfinished.** The back door hangs 45 cm above the ground with no step. No light, no meter, no vent, no tap, no bins, nothing in the yard. The moss decal runs straight across the door. | `ext_back`, `ext_back_door` |
| 3 | **The house does not sit on the ground.** The plinth is a flat brown band that reads as soil, not masonry. No vents, no splash line, no dirt strip, weeds or leaves where the wall meets the yard, which is one flat plane. | every `ext_*` |
| 4 | **Crack textures at the wrong scale.** The plaster on the bedroom and bathroom walls has cracks 20 to 40 cm across, on every wall alike: it reads as dried mud. The wall textures repeat every 2.4 m. | `bedroom`, `bedroom_back`, `bathroom`, `bathroom_sink` |
| 5 | **Cloth that looks like stones, props that look like toys.** Laundry and towels are smooth ellipsoids (three in the bedroom, two in the bathroom). The vacuum cleaner is a cylinder on a box, the hot-water tank is faceted, the suitcase and the bathroom shelf's contents are bare primitives. | `bedroom`, `bathroom`, `utility` |
| 6 | **Bathroom surfaces.** The wall tiles are stretched to about 10 x 35 cm with heavy black grout; the roller blind is a thick slab standing off the wall like a board; the shelf unit is a blocky slab; the crack decals on the tiles read as hair. | `bathroom`, `bathroom_sink` |
| 7 | **Curtains pass through radiators.** Under the living-room and bedroom windows the radiator fins show through the curtain cloth. | `living_back`, `bedroom_back` |
| 8 | **Wallpaper peels look like cardboard.** Each is a stiff tan flap under a grey rectangle: the wrong colour (the face should be the paper's own pattern), too thick, too regular. | `hall`, `living`, `landing` |
| 9 | **Roof, eaves and porch are bare.** No chimney, no rake boards on the gables (the siding runs to a knife edge), no ridge cap or vent pipe. The porch roof is a 5 cm slab with no rafters, fascia or brackets; the deck is empty; the boards are oddly multi-coloured. | `ext_front`, `ext_porch`, `ext_east` |
| 10 | **Exterior weathering repeats.** Moss at one height and spacing all round, like a wallpaper border; three identical rectangular grime stamps with hard top edges under each eave; paint flecks sprinkled evenly. | every `ext_*` |
| 11 | **The under-stair wall is a blank plane.** Four metres of flat beige with no panelling or skirting, although the wall opposite is panelled. The cupboard door is a flat slab with no frame, panels or latch. | `hall_back`, `stairs` |
| 12 | **Floors: flat, clean, no contact dirt.** The kitchen floor is plain beige with no pattern and reads as sand. The hall lino is clean and saturated. Nowhere does dirt gather along skirtings, in corners or under furniture. | `kitchen`, `kitchen_fridge`, `hall` |
| 13 | **Kitchen cabinets read as new laminate.** Bright, clean orange wood print; the water mark under the sink is a regular scalloped wave across three doors, like a stencil. | `kitchen`, `kitchen_sink` |
| 14 | **Empty areas and a blank frame.** The bedroom's north-east corner and west wall, the kitchen's east wall, the front landing and the porch deck are bare. The frame over the living-room sofa is a black rectangle. | `bedroom`, `kitchen_fridge`, `living_back`, `ext_porch` |
| 15 | **Hard CG edges and paper-thin soft goods.** Rugs and the stair runner are zero-thickness quads with crisp edges (the runner bright red); every pendant shade is the same blank cone; ceilings are one clean white texture where the art bible asks for stains. | `landing`, `living`, `bedroom` |

## What is already at the level wanted

Worth saying so it is not disturbed: the front elevation's windows, casings
and clapboard; the living room as a whole (fireplace, bookcase, sofa, the
wood floor, the curtains); the hall's panelling and stair; the kitchen's
table, worktop clutter and fridge door; the printed graphics.

## Outcome

The "after" stills are `renders/14_after_*.png`, from the same cameras as
`renders/13_before_*.png` (40 samples; two new views, `ext_yard` and
`ext_chimney`, have no "before" because there was nothing there).

| # | State | What was done, or why not |
| --- | --- | --- |
| 1 | Fixed | Three side windows (`win_living_side`, `win_bedroom_side`, `win_landing_side`: openings only, the shell is where it was) with casings, sashes, curtains or a blind. A brick chimney stack on the east wall over the chimney breast, with shoulders, a crown, two pots and lead where it comes through the verge. |
| 2 | Fixed | Back steps with rails (three 15 cm risers), a bulkhead lamp, the meter and its conduit, a dryer vent, a cooker-hood louvre, a tap with a hose, two trash cans and bags, a window air conditioner in the bedroom's side window. Moss, mud and rain marks now skip every door and window. The lamp's bulb is dead on purpose: a new light would be a game change. |
| 3 | Fixed | Block plinth (texture), a mud splash band carried over the plinth and the bottom boards, air bricks in every side, a strip of bare earth under the walls, weed tufts and leaf litter. In the yard: a board-and-batten shed with a tin roof, a woodpile under a tarp, a chopping block, a clothesline. |
| 4 | Fixed | In the textures (earlier commit): striped bedroom paper, drawn bathroom tiles. |
| 5 | Mostly | Cloth heaps are rebuilt: an outline with corners and tongues, a thin hem, creases. They read as cloth at a glance but are still a mound, not simulated fabric. The vacuum cleaner, hot-water tank (32 sides, quilted jacket, lacing), suitcase (two lined shells) and bottles (moulded, with shoulders) have real shapes; toilet rolls have a hole. |
| 6 | Fixed | Square tiles (texture); a thin roller blind on a roller inside the reveal; a slatted steel shelf unit; crack decals taken off the tiles, and the crack image itself redrawn in straight broken runs. |
| 7 | Fixed | The living-room curtain is drawn back clear of the radiator; the bedroom curtains stop at the sill. |
| 8 | Fixed | A peel is now a narrow, ragged tongue of the room's own paper leaning off the wall, brown only on its back, with ragged bare plaster behind. |
| 9 | Fixed | Verges with rake boards on both gables, a ridge roll, a vent pipe, the chimney. Porch: rafters, ledger, fascia, barge boards, knee braces; a chair, a crate of empties, a plant, a mat, boots, newspapers, leaves on the deck. |
| 10 | Mostly | Moss in clumps of every size and spacing, most on the north wall; eaves grime replaced by soft-edged run-off, only under real eaves and sills. Not fixed: the evenly sprinkled paint flecks, which are in the clapboard photograph itself. |
| 11 | Fixed | The stair's hall side has a string board, skirting and dark matchboarding cut to the rake; the cupboard has an architrave and a two-panel door with butts and a thumb latch. |
| 12 | Fixed | Kitchen vinyl tiles and duller hall lino (textures); a contact-dirt decal along every skirting and a fan of dirt in every inside corner. Not done: dirt under individual pieces of furniture. |
| 13 | Fixed | In the cabinet-front sheet (earlier commit). |
| 14 | Fixed | Bedroom: a hamper and boxes in the north-east corner, a dressing mirror on the west wall. Kitchen: a sideboard, a shelf of tins and an apron on the bare wall. Front landing: a low bookcase, a lamp, a rug. Porch: see 9. The black frame over the sofa is replaced by a framed print (the model's own canvas is black). |
| 15 | Fixed | Rugs have a pile that rolls over at the edge, rucks, a lifted corner and a fringe. Five different pendant shades and two bare bulbs. Nicotine, water and mould stains added to every ceiling. |

### Cost

- About 241,600 triangles in 301 meshes (was 187,700 in 250).
- `house.glb` 316 MB (was 296), `house_packed.blend` 303 MB (was 286).
- `game/tools/texture_policy.py` was not edited. The new surface textures
  (`ext_foundation`, `metal_galv`, `metal_painted`, `bark`, `roof_tin`,
  `ground_dirt`, `shed_boards`, `ext_brick`) match none of its rules and fall
  to the 2048 cap; all but the brick are 1K at source, so the cap changes
  nothing. Naming them in its MEDIUM list would halve the brick only.
- Godot: import clean; `--selftest`, `--preset-check` and
  `--world=town --town-selftest` pass.

### Built on this machine

This pass was built and rendered with Blender 4.5 LTS (the only Blender on
the machine it was finished on), not 5.2. The scripts run unchanged on both.
