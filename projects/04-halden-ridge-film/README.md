# 04 Halden Ridge: the film scene

The house and the town in one Blender scene, lit eight ways, with six
cameras. Blender only: nothing here goes to the game.

`film.blend` is 0.2 MB. It holds no geometry of its own apart from fog boxes,
lamps and cameras: the house and the town are **linked** from

- `../01-house-interior/house.blend`
- `../03-town/town.blend`

by relative path, one collection at a time. Save a fix in either file and it
is in `film.blend` the next time it is opened. Neither source file is edited.

## Build

```bash
cd projects/04-halden-ridge-film
blender -b --python build.py                          # writes film.blend
blender -b film.blend --python check_seams.py         # how the house sits on its lot
blender -b film.blend --python render.py -- --scene 1000_clear --cams all
```

`build.py` is the whole scene: run it again after changing a camera or a rig.

## What is left out of each library

| Library | Collection | Why |
| --- | --- | --- |
| house | `lot` | The seven yard and street objects the town replaces (`yard_ground`, `yard_paths`, `street_road`, `fence_picket`, `mailbox`, `telephone_pole`, and the `street_sodium` light) |
| house | `atmosphere` | The house's own moon and its render-only `fog_volume` |
| house | `lightpoints`, `cameras`, `colliders` | Markers, the house's own hero cameras, the game's stair collider |
| town | `collision`, `kit` | Game colliders, and the kit pieces the houses are instanced from |

The house's night world is not linked either: a world belongs to a scene.

## Lighting: eight scenes

One scene per setup, all showing the same linked collections.

| Scene | Sun | What lights it |
| --- | --- | --- |
| `0600_clear`, `0600_foggy` | 14° below the horizon, due east | Twilight sky; street and house lamps on |
| `1000_clear`, `1000_foggy` | 25° up, south-east | Sun and sky; **lamps off** |
| `1700_clear`, `1700_foggy` | 8° up, west-south-west | Low warm sun; lamps on |
| `0300_clear`, `0300_foggy` | 46° below the horizon | A cool dim sun lamp as the moon; lamps on |

- **Where and when**: 42.5° N, 72.5° W, 25 October, Eastern Daylight Time
  (UTC-4). `build.py` computes the sun's elevation and azimuth for each hour
  (NOAA approximation) and prints them.
- **Sky**: Blender's physical sky texture. The model's name is read from the
  node's own enum (`NISHITA` in 4.5, multiple scattering in 5.x). Its sun
  disc is off; a sun lamp stands in the same direction, so shadows and fog
  beams are clean. Before sunrise the sky is held 4° under the horizon and
  dimmed.
- **Fog** (the four Foggy scenes): a box of thin volume over the whole town,
  13 m deep, not a world volume (which would be infinitely deep and black).
- **Lamps**: the house's and the street's lamps are one collection, `lamps`,
  excluded from the view layer in the two 10:00 scenes. Lampshades and bulbs
  that glow by their material still glow at 10:00: that is in the house
  file.
- **Colour**: AgX, base contrast, no grade. Exposure is set per scene, and
  `render.py` opens up by the scene's `indoors_stops` for the four interior
  cameras. Some rooms are darker than others
  at a given hour (the hall and the front door face north, away from the
  10:00 sun; the landing has no lamp of its own at 03:00), so `CAM_STOPS` in
  `build.py` adds stops per camera and hour on top (scene property
  `cam_stops`).

## Cameras

35 mm full-frame lenses, depth of field on.

| Camera | Lens | f | Shot |
| --- | --- | --- | --- |
| `cam_1_street` | 35 mm | 5.6 | Establishing: the house from across Ashgrove Street (east of pole P2, which stays out of frame) |
| `cam_2_porch` | 28 mm | 4 | Up the path to the porch |
| `cam_3_front_door` | 32 mm | 2.8 | The front door from inside the hall |
| `cam_4_hallway` | 24 mm | 2.8 | The hall and the stair |
| `cam_5_kitchen` | 24 mm | 2.8 | The kitchen from its doorway |
| `cam_6_landing` | 24 mm | 2.8 | The upstairs landing |
| `cam_move_approach` | 28 mm | 4 | The move: five seconds (120 frames at 24 fps) up the path, focus pulled on the door |

## Test renders

In `renders/`, low sample counts, made on a laptop CPU:

- `test_1000_clear_cam_*.png` and `test_0300_foggy_cam_*.png`: every camera
  at 10:00 Clear and at 03:00 Foggy.
- `move_0300_foggy/frame_0001.png` to `frame_0120.png`: the approach.

## Seams (for the town session)

From `check_seams.py`, run again after the town gained lots L8 to L11, yards
and the moved tree. No house file was changed.

- Ground heights round the house all match `docs/TOWN.md`: lawn -0.45,
  sidewalk -0.40, road -0.53. No gaps under the porch steps, the back steps
  or anywhere in the lot.
- The town's path reaches the foot of the porch steps on `ground_sidewalks`
  at -0.425 (2.5 cm above the lawn, as the house's own path was).
- **`tree_9`** (L1's back yard) moved 2.8 m north-west to (3.2, 14.2): it is
  clear of the back steps, the hose and the trash cans now. Its crown still
  overhangs the woodpile (the check reports the boxes overlapping), but the
  trunk is 1.2 m from the chopping block and the crown starts well above the
  0.8 m pile.
- `mprop_8_7` and `leaves_8_7` are reported against the doormat and the
  south wall: they are 21 m town sectors (props, leaf litter), whose
  bounding boxes cover the whole front of the lot. Nothing in them touches
  the house.
- The tall board fence is 0.29 m east of the shed (fence at x 11.49, shed to
  11.10 plus its roof overhang of 0.15) and 1.09 m north of it. Left as it
  is: the fence is the L1/L3 lot line, and the gap is narrower than the
  player, so nobody can get stuck in it.
- A ray east from the back yard at y 12 finds no fence within 24 m (the
  first thing is `tree_11` in L9), and one west finds a tree at x -18: the
  side fences between L1 and its neighbours do not run the full depth of
  the lot at that point.

## Final quality on a GPU machine

Nothing in the scene is CPU-only. On a machine with an RTX-class card:

```bash
cd projects/04-halden-ridge-film
blender -b film.blend --python render.py -- --scene 0300_foggy --cams all \
    --device GPU --samples 1024 --res 1920x1080 --prefix final
blender -b film.blend --python render.py -- --scene 0300_foggy --move \
    --device GPU --samples 512 --res 1920x1080
```

| Setting | Clear scenes | Foggy scenes |
| --- | --- | --- |
| Samples | 512 | 1024 (the fog is the noise) |
| Adaptive threshold | 0.01 | 0.01 |
| Denoiser | OptiX or OpenImageDenoise, albedo + normal | the same |
| Volume bounces | 0 | 1 (2 for the 03:00 lamps in fog) |
| Resolution | 1920 x 1080 (3840 x 2160 for stills) | the same |
| Motion blur | on for the move, shutter 0.5 | the same |

`render.py` sets samples, resolution and device; the others are scene
settings in `build.py` (`render_settings`).

**Time, estimated, not measured** (there is no GPU on the machine this was
built on. Measured there, on two CPU cores: 960 x 540 at 24 samples takes about 1 minute Clear and 2 minutes Foggy; the move at 480 x 270 and 6 samples took 29 minutes, 14 seconds a frame). For
an RTX 3060 to 4070 at 1920 x 1080: a Clear still 1 to 2 minutes, a Foggy
still 4 to 8 minutes; the 120-frame move 2 to 4 hours Clear, 8 to 16 hours
Foggy. All six stills in all eight scenes: about 4 hours. Render one frame
first and multiply.

Encode the move's frames with, for example:

```bash
ffmpeg -framerate 24 -i renders/move_0300_foggy/frame_%04d.png -c:v libx264 -crf 16 -pix_fmt yuv420p move.mp4
```

## Built with

Blender 4.5 LTS on the machine this was finished on; `build.py` has nothing
version-specific in it and reads the sky model's name from Blender itself.
