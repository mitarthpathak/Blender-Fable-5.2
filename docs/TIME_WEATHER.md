# Time of day and weather

Free roam has four times and two weathers: eight looks. Each is one
`LightingPreset` file in `game/presets/` that can be opened in the Godot
inspector and tuned by hand; `game/scripts/lighting_preset.gd` documents
every field. `game/scripts/lighting_presets.gd` applies them.

![All eight looks on Low: front door, junction, living room](../game/screenshots/time_weather/sheet_all.jpg)

(In each pair of rows: 03:00 Clear, 03:00 Foggy, 06:00 Clear, 06:00 Foggy,
then 10:00 Clear, 10:00 Foggy, 17:00 Clear, 17:00 Foggy.)

## Where and when

Halden Ridge is in the north-eastern United States, about 42.5° north. The
date is late October, still on daylight time: sunrise about 07:10, sunset
about 17:50. That fixes the sun:

| Time | Sun | What lights the scene |
| --- | --- | --- |
| 03:00 | far below the horizon | the moon |
| 06:00 | 14° below the horizon, in the east (azimuth 92°): an hour before sunrise | the first grey-blue glow of the eastern sky |
| 10:00 | 27° up, in the south-east (azimuth 138°) | the sun |
| 17:00 | 9° up, in the west-south-west (azimuth 243°): the last hour before sunset | a low orange sun |

Azimuth is the compass direction the light comes from (0 north, 90 east,
180 south: the street side of the house). The presets store it as
`key_elevation_deg` and `key_azimuth_deg`.

One directional light does all of this. It is the moon at night and the
sun by day, always dynamic, with live shadows. At 06:00 the sun is still
below the horizon, so the key light stands in for the glow of the sky: low
in the east (10° up), weak, very soft, no shadows.

At 03:00 the moon keeps the direction it has in the house model (high in
the south, through the front windows), because the interior was lit for it
and 03:00 Foggy must stay exactly the old Night.

## The eight looks

| File | Sky | Fog | Key light | Street lights | Porch lights | Lamps in the house | Neighbours' lit windows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `0300_clear` | deep blue-black gradient, a visible moon | thin: you see the whole street | moon, cold blue, sharp shadows | on | on | on | on |
| `0300_foggy` | the fog's own colour | thick: 20 to 30 m | moon, cold blue, soft in the fog | on, each in a halo | on | on | on |
| `0600_clear` | dark blue above, a pale band on the horizon | thin | pre-dawn sky glow, no shadows | on | on | on | on |
| `0600_foggy` | grey-blue, flat | thick, lifting to grey | pre-dawn sky glow, no shadows | on, in halos | on | on | on |
| `1000_clear` | blue, paler at the horizon | a little haze | sun, warm white, clear shadows | off | off | off | off (a trace) |
| `1000_foggy` | pale grey, flat | heavy: the classic foggy-town day | sun through fog: soft, shadowless | off | off | off | off (a trace) |
| `1700_clear` | blue above, orange on the horizon | a little warm haze | low orange sun, long shadows | on | on | on | on |
| `1700_foggy` | violet-brown, flat | medium, violet | low sun, weaker, warm | on | on | on | on |

**03:00 Foggy is the old Night.** It holds exactly the values `main.gd` and
`house_lights.gd` use by themselves. `-- --preset-check` applies it over the
untouched scene and compares 64 values; all must be identical, on High and
Low. The old Foggy Overcast Day became 10:00 Foggy, Dusk became 17:00
Foggy and Clear Day became 10:00 Clear; the old names are still accepted in
settings files and on the command line.

### Which lights are on

Street lights, porch lights and house lamps are on at 03:00, 06:00 and
17:00 and off at 10:00. Each preset decides, with these fields:

| Field | Lights |
| --- | --- |
| `street_lights_on`, `street_energy_scale` | every light named `*sodium*` or `street_*`, and the lamp heads' glow |
| `porch_lights_on`, `porch_energy_scale` | every light named `*porch*` |
| `lamp_energy_scale` | the lamps inside the player's house (0 at 10:00) |
| `window_glow_scale` | the neighbours' lit windows and the lamps behind them |

When a look changes, lights do not snap: their energy fades with everything
else.

## Changing the look

- **F4** opens the World menu: the four times, Clear / Foggy, brightness,
  graphics Low / High, and FREEZE TIME.
- **F2** steps to the next time.
- A change cross-fades over 4 seconds: sky, fog, ambient, exposure, the
  key light's colour, strength and direction, and every lamp.
- **The clock.** With FREEZE TIME off, one game hour takes two real minutes
  (a day in 48 minutes). Between two of the four times the look is a blend
  of them, so morning arrives gradually. The clock is frozen by default.
- **F6** is a free camera for screenshots and film framing: it starts from
  the current view and flies through anything. W A S D move, Q and E go down
  and up, Shift is fast, Ctrl slow, the mouse wheel changes speed, + and -
  change the lens. F6 again returns to the player, who has not moved.
- Time, weather, frozen and brightness are kept in the build's settings
  file under `[lighting]`; graphics quality stays under `[graphics]`.

Command line: `--preset=1000_clear`, or `--time=10 --weather=clear`;
`--clock` starts with time running; `--look-selftest` fades through all
eight looks, runs the clock and toggles the camera and the menu.

## Indoors and outdoors

Every preset has two sets of fog, key-light, ambient and exposure values.
The house world uses the plain ones. The town world (`world_town.tscn`)
uses the **Outdoors** group, because values that suit a room light the
whole street's fog at once. That is why 03:00 Foggy can be exactly the old
Night indoors and still be tuned for the street.

Clear weather uses a gradient sky (`sky_gradient`, `sky_top_color`,
`sky_horizon_color`); foggy weather uses the flat `background_color`,
because in thick fog the sky is the fog. Colours in the files are sRGB.

## Lightmaps

The sun and the moon are one dynamic light (`BAKE_DYNAMIC`): direct light
and shadows are computed live, which is what lets the time change. Only
what does not change should be baked: the bounce light of the fixed lamps
and the shape of the rooms. The trade-off is the same as before, and
bigger now that there are eight looks: a bake holds the bounce of one
moment (the editor bakes with 03:00 Foggy's lights), so at 10:00 Clear the
direct sun is right but the baked bounce is still the night's. The presets'
ambient colour, the room probes' ambient and, on High, SDFGI carry the
difference. A lightmap per time would fix it at four times the memory and a
swap on every change; it is not done.

## Tuning a look

Open the `.tres` in the inspector, change a value, run the game with
`-- --world=town --preset=<id>`. To see all eight side by side:

```bash
godot --path game -- --world=town --preset-shots --quality=low --views=front_door,junction,living_room --out=res://screenshots/time_weather
```
