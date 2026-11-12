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

Filled in after the fixes: see the end of this file.
