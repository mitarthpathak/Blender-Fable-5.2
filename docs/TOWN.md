# Halden Ridge: the town

The playable town around the player's house: one stretch of **Ashgrove
Street**, the street the house already faces, and **Mill Road**, a side street
that meets it in a T-junction right opposite the front door. Small on purpose:
seven lots, each worth looking at, in fog that hides everything past 20 to 30
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
| L4 | 15 Ashgrove Street | Corner house on the south side, hip roof, wrap-around porch, putty grey. Closed up. |
| L5 | 17 Ashgrove Street | Corner house, front gable, faded mustard, chain-link fence and a sale sign. Empty. An abandoned sedan with flat tyres sits at the curb in front. |
| L6 | 3 Mill Road | Faces Mill Road. Oxblood paint, side-gable, boarded throughout. |
| L7 | 4 Mill Road | Vacant lot behind chain-link: a dead station wagon on blocks, weeds, leaves, a bare tree. |

Only the player's house opens. Every other house has a walkable porch, a
locked front door (and a screen door), sash windows with casings, gutters and
downpipes; some windows are boarded or broken, as listed in `plan.py`.

## Street furniture

- **Telephone poles** P1 to P7 with sagging wires between them (true
  catenary curves) and service drops to the houses.
- **Sodium streetlights** on P1, P2, P3, P5 and P7. **P4 is broken** (dark, its
  glass gone); **P6 on Mill Road flickers**.
- Manhole covers, a hydrant, mailboxes, trash cans (one knocked over),
  leaf piles, puddles on the road and sidewalks, potholes and patches.
- Bare trees in the yards.

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
collision wall stands on each edge (`plan.WALK`):

| Edge | What blocks it |
| --- | --- |
| Ashgrove, west (x ≈ -29) | a car crashed into the corner, sawhorse road barriers, a tall fence behind |
| Ashgrove, east (x ≈ 36) | a fallen tree lying across the road, a tall fence behind |
| Mill Road, south (y ≈ -56) | concrete jersey barriers, a ROAD CLOSED sign, a car crashed into them, a fence |
| Behind the north lots (y ≈ 18.4) | a tall board fence |
| West and east of the south lots | tall board fences |

## Detail budget

Detail goes where the player looks: the junction, the street in front of
the house, and the porches. Far ends of the streets get fewer props, and
anything small fades out with distance (Godot visibility ranges); the fog
closes the view well before the edges.
