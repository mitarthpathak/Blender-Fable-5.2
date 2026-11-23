# Halden Ridge: the town

The playable town around the player's house: one stretch of **Ashgrove
Street**, the street the house already faces, and **Mill Road**, a side street
that meets it in a T-junction right opposite the front door. Small on purpose:
eleven lots, each worth looking at, in fog that hides everything past 20 to 30
metres (docs/ART_BIBLE.md).

![Town plan](../projects/03-town/renders/01_town_plan.png)

Every number lives in `projects/03-town/plan.py` (pure data, like the
house's plan). `projects/03-town/layout.py` draws the plan above from it;
the Blender build and the Godot town script read it too.

## Coordinates

The house's own: metres, +X east, +Y north, +Z up, origin at the inside
south-west corner of the player's house at ground-floor level. In Godot that
is (x, z, -y), as for the house.

| Surface | Height (Blender z) | Where |
| --- | --- | --- |
| Lawns, yards | -0.45 | everywhere off the street |
| Sidewalks | -0.40 | 1.6 m wide, both sides of both streets |
| Road | -0.53 | 13 cm below the sidewalk, behind a curb |

Ashgrove Street keeps the exact positions the house was built with: road
y -18.1..-10.2, north sidewalk y -10.2..-8.6. The house's own exterior pieces
(`yard_ground`, `yard_paths`, `street_road`, `fence_picket`, `mailbox`,
`telephone_pole`, `street_sodium`) are removed by name in the town scene and
rebuilt by the town at the same heights; the house files are never edited.
Its porch, steps, gutters, trim and porch light stay.

## Streets

| Street | Runs | Width | Notes |
| --- | --- | --- | --- |
| Ashgrove Street | east-west, y = -14.15 | 7.9 m kerb to kerb | faded double yellow centre line, patched and potholed |
| Mill Road | south from Ashgrove, x = 3.5 | 7.0 m | leads towards the closed mill; stop line at the junction; closed off at the south end |

The junction is the centre of the town: the first thing the player sees when
the front door opens, lit by the streetlight on pole P5.

## Lots

| Lot | Address | What it is |
| --- | --- | --- |
| L1 | 14 Ashgrove Street | **The player's house.** The only building with an inside. Picket fence, path to the porch, mailbox, two trash cans at the curb. |
| L2 | 12 Ashgrove Street | Abandoned since the mill closed. Front-gable, faded blue. Ground floor boarded, one upstairs window smashed. Dead lawn. |
| L3 | 16 Ashgrove Street | Side-gable with a full-width porch, sage green. **One upstairs window glows dimly** behind a blind. |
| L4 | 15 Ashgrove Street | A one-storey cottage on the corner of Mill Road, putty, a hooded stoop. Closed up, one window broken, yet a lamp burns in the front room (`tk/villa.py`, `build_cottage`). |
| L5 | 17 Ashgrove Street | **Halden Ridge Community Hospital**, closed: two storeys of buff brick and ribbon windows, chained glass doors under a canopy, the emergency bay with its red EMERGENCY panel at the east end. One ward lamp still burns upstairs (`tk/hospital.py`). It takes the old L5 and L11 together. An abandoned sedan with flat tyres sits at the curb in front. |
| L6 | 3 Mill Road | Faces Mill Road. Oxblood paint, side-gable, boarded throughout. |
| L7 | 4 Mill Road | Vacant lot behind chain-link: a dead station wagon on blocks, weeds, leaves, a bare tree. Its south half is the closed **Ridge Gas & Grocery**. |
| L8 | 10 Ashgrove Street | West end, north side. Narrow front-gable house, putty, every window boarded. |
| L9 | 18 Ashgrove Street | East end, north side, past the fallen tree. **Ridge Stationery & Books**: a false-fronted shop with a torn striped awning, books dim in the windows, a flat above with a stair at the back (`tk/shop.py`). |
| L10 | 13 Ashgrove Street | West end, south side. **The villa**: hip roof with a bracketed cornice, a portico of four columns carrying a balcony, a bay window, shutters hanging off. Closed up (`tk/villa.py`, `build_villa`). |

L8 to L10 and the hospital's east end fill the four corners at the ends of
Ashgrove, inside the edge fences, which were bare verge until the town was
finished. The hospital, the villa, the cottage and the shop have builders of
their own (`plan.KitHouse.kind`, `house_kit.BUILDERS`); the other houses come
from the kit. Each new builder has a preview in `projects/03-town/previews/`
that renders it alone.

Only the player's house opens. Every other house has a walkable porch, a
locked front door (and a screen door), sash windows with casings, gutters and
downpipes; some windows are boarded or broken, as listed in `plan.py`.

## Two places beyond the houses

**Ridge Gas & Grocery** stands where Mill Road ends, on the south half of the
vacant lot: a flat-roofed block store with its window boarded and a notice
in the door ("Closed. Thank you, Halden Ridge. 1964 - 1995"), a canopy over
two dead pumps, a price sign with digits missing, an ice chest, a pay phone
with the handset hanging, oil drums and a dumpster. One fluorescent tube
under the canopy still buzzes. The forecourt is open to the road and can be
walked on. The brand and the prices are our own.

**The Halden mill** is why the town exists and why it is emptying. It
stands 70 to 110 m past the end of Mill Road: a long brick weaving shed
under a sawtooth roof, a four-storey spinning block with a stair tower, a
water tank and a 46 m stack. It cannot be reached. In fog it is a shape at
the end of the street; in clear weather it is a building with rows of dark
windows. The flyer on the poles ("What happens to the Halden mill?") is
about it.

## Street furniture

- **Telephone poles** P1 to P7 with sagging wires between them (true
  catenary curves) and service drops to the houses.
- **Sodium streetlights** on P1, P2, P3, P5 and P7. **P4 is broken** (dark, its
  glass gone); **P6 on Mill Road flickers**.
- Manhole covers, a hydrant, mailboxes, trash cans (one knocked over),
  leaf piles, puddles on the road and sidewalks, potholes and patches.
- Bare trees in the yards.
- Storm drains, wet leaves banked in the gutters, weeds and moss in every
  joint, no-parking signs, a bus stop and bench on Ashgrove, uncollected
  trash, a shopping cart at the junction, a bicycle by the player's fence,
  tyre marks towards each wreck.
- Flyers on the poles, all our own: a missing cat (Toby), a town meeting
  about what happens to the Halden mill, a yard sale at 12 Ashgrove Street.

## Close up

The town is also used for film, so the hero areas (the player's lot, the
junction, the first 30 m of Mill Road) are built to be looked at from a
metre away, in daylight as well as fog:

- Every window has see-through, dirty glass and something behind it:
  curtains with folds, a venetian blind half down with a few slats askew, a
  sheet pinned up, or a bare dark room.
- Three windows are lit and show a real room (wallpaper, a floor, a lamp
  with a glowing shade, a bed or an armchair and a bookcase): upstairs and
  downstairs at 16 Ashgrove, where someone lives, and one bare bedroom at
  15, which is supposed to be closed up.
- The houses beside the player's and on the junction have louvred shutters
  (one hanging), brackets under the eaves and at the porch posts, a gable
  vent, a number plaque, a lantern by the door (lit at 16), a kick plate and
  a letter slot.
- Porches have a rocking chair, a side table with a mug and a paperback, a
  doormat and a hanging basket of something long dead.
- Mailboxes have a flag, a door with a latch and a tube for the paper;
  pickets are pointed and posts capped; the player's gate hangs open.
- Leaf litter is layered: flat wet leaves, then about 3,500 single curled
  leaves banked where the wind leaves them (gutters, fence lines, steps,
  porch corners), then the piles.
- The cars have interiors behind see-through glass.

## Street furniture added in the detail pass

Tar snakes over both roads, a worn crosswalk over Ashgrove by the junction,
four hydrants with yellow kerbs, litter in the gutters, a newspaper box,
cable-TV pedestals, cones at both road closures, TV aerials and dishes on
the roofs, window air conditioners, and dead plants on the porches. The
cars have trim strips, antennas, exhausts, steel wheels with lug nuts, a
roof rack on the wagon and a ticket and tow notice on the sedan.

## What each lot says

| Lot | Story |
| --- | --- |
| 14 Ashgrove (player) | A hose by the porch, the paper still on the path. |
| 12 Ashgrove | The yard sale from the flyer was never cleared away: a collapsed table, boxes, a lamp. |
| 16 Ashgrove | Lived in: a porch swing, pumpkins on the steps going soft, a sheet ghost left in the tree since Halloween. |
| 15 Ashgrove | A child lived here: a ball, a wagon, a tricycle and a sandbox lost in the long grass. |
| 17 Ashgrove | For sale, and nobody is buying; the sedan at the curb has sat on flat tyres for a long time. |
| 3 Mill Road | An empty dog house, a chain, a bowl, and a BEWARE OF DOG sign on the fence. |
| 4 Mill Road | The vacant lot: a station wagon on blocks, tyres, pallets, a mattress. |
| 10 Ashgrove | The boarding-up was never finished: spare plywood leaning on the front wall, a sawhorse still out, a ladder in the grass, a paint can on its side. |

## Where the player walks

The player starts in the hall of their house, walks out of the front door,
across the porch and down the path to Ashgrove Street. From there:

- along Ashgrove in both directions to the town's edges,
- across to the junction and down Mill Road to its closed south end,
- up onto any porch (the doors are locked), into front yards and the vacant
  lot.

Back yards and the gaps between houses are closed by tall board fences.

## Edges

The town ends where it would naturally be blocked, and an invisible
collision wall stands on each edge (`plan.WALK`). Beyond each closed street
end stand dead trees and a dark line of trees and roofs, so the street fades
into the fog rather than stopping:

| Edge | What blocks it |
| --- | --- |
| Ashgrove, west (x ≈ -29) | a car crashed into the corner, sawhorse road barriers, a tall fence behind |
| Ashgrove, east (x ≈ 35) | a fallen tree lying across the road, its crown on L9's flattened picket fence, a tall fence behind |
| Mill Road, south (y ≈ -56) | concrete jersey barriers, a ROAD CLOSED sign, a pickup crashed into them, a fence; the mill beyond |
| Behind the north lots (y ≈ 18.4) | a tall board fence |
| West and east of the south lots | tall board fences |

## Detail budget

Detail goes where the player looks: the junction, the street in front of
the house, and the porches. Far ends of the streets get fewer props, and
anything small fades out with distance (Godot visibility ranges); the fog
closes the view well before the edges.

## The road to the mill

Follow Mill Road past Ridge Gas & Grocery. The pickup still blocks the centre
of the barricade. At its east end the boards have parted and there is room
to pass on foot. Beyond the town pavement the road drops into the valley.
The checkpoint clock has stopped, the bus timetable ends in October 1995,
and the county has put up two notices for Elian Vale with different dates.
A failing lamp stands before the bend in the guardrail.

The north gate opens into the receiving yard. One leaf is still chained.
A fleet truck stands at the loading dock, and one upper pane catches light
at night. The gatehouse and mill are closed shells. The nearby dock facade
is separate from the distant mass used for the Low fog silhouette.
