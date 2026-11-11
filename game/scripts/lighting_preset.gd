@tool
class_name LightingPreset
extends Resource
## One time-of-day / weather look: the key light (moon or sun), the sky and
## ambient colour, fog and exposure. Saved as .tres files in res://presets/
## so each look can be tweaked by hand in the Godot inspector.
##
## LightingPresets (scripts/lighting_presets.gd) applies a preset on top of
## what main.gd sets up. The Night preset holds exactly the values main.gd and
## house_lights.gd used before presets existed, so it changes nothing.

@export var display_name := "Night"

@export_group("Key light (moon or sun)")
@export var key_color := Color(0.50, 0.66, 1.0)
@export_range(0.0, 8.0, 0.01) var key_energy := 1.6
## Softness of the shadow edge: the apparent size of the moon or sun, in degrees.
@export_range(0.0, 20.0, 0.1) var key_angular_distance := 0.6
@export var key_shadows := true
@export_range(0.0, 8.0, 0.01) var key_volumetric_fog_energy := 2.2
## Keep the direction the light has in the model (house.glb). Night does, so
## the moonlight through the windows stays where the house was lit for it.
@export var use_model_angle := true
## Height of the light above the horizon, degrees. Ignored with use_model_angle.
@export_range(-10.0, 90.0, 0.5) var key_elevation_deg := 35.0
## Compass direction the light comes from: 0 north, 90 east, 180 south (the street side).
@export_range(0.0, 360.0, 0.5) var key_azimuth_deg := 200.0

@export_group("Sky and ambient")
## In thick fog the sky is just the fog's own colour.
@export var background_color := Color(0.035, 0.045, 0.060)
@export var ambient_color := Color(0.20, 0.25, 0.34)
@export_range(0.0, 4.0, 0.01) var ambient_energy := 0.55
## Ambient colour the room reflection probes add indoors (world.tscn probes).
@export var probe_ambient_color := Color(0.105, 0.13, 0.175)
@export_range(0.0, 4.0, 0.01) var probe_ambient_energy := 1.0

@export_group("Fog")
## High quality: volumetric fog.
@export_range(0.0, 0.3, 0.001) var volumetric_fog_density := 0.045
@export var volumetric_fog_albedo := Color(0.80, 0.84, 0.90)
## Light the fog gives off by itself. Night uses the fog colour x 0.6.
@export var volumetric_fog_emission := Color(0.021, 0.027, 0.036)
@export_range(-0.9, 0.9, 0.01) var volumetric_fog_anisotropy := 0.45
@export_range(1.0, 200.0, 0.5) var volumetric_fog_length := 48.0
@export_range(0.0, 4.0, 0.01) var volumetric_fog_gi_inject := 0.6
## Low quality: cheap distance fog. Night uses the fog colour x 3.2.
@export var distance_fog_color := Color(0.112, 0.144, 0.192)
@export_range(0.0, 0.3, 0.001) var distance_fog_density := 0.055
@export_range(0.0, 1.0, 0.01) var distance_fog_sky_affect := 1.0

@export_group("Exposure and grade")
@export_range(0.1, 6.0, 0.01) var exposure_high := 1.5
@export_range(0.1, 6.0, 0.01) var exposure_low := 1.25
@export_range(1.0, 16.0, 0.1) var tonemap_white := 6.0
@export_range(0.0, 4.0, 0.01) var glow_intensity := 0.5
@export_range(0.0, 1.0, 0.01) var glow_bloom := 0.05
@export_range(0.0, 2.0, 0.01) var saturation := 0.92
@export_range(0.0, 2.0, 0.01) var contrast := 1.06
@export_range(0.0, 4.0, 0.01) var sdfgi_energy := 1.0
## High only. SDFGI adds the background colour as sky light everywhere it sees
## the sky, which floods outdoor areas. Night keeps the original (on); the
## town world turns it off for every preset (see LightingPresets.outdoor).
@export var sdfgi_read_sky_light := true

@export_group("Practical lights")
## Multiplier on the indoor lamps (table lamps, porch light, flicker bulb, TV).
@export_range(0.0, 4.0, 0.01) var lamp_energy_scale := 1.0
## Street lights (any light whose name contains "sodium").
@export var street_lights_on := true
@export_range(0.0, 4.0, 0.01) var street_energy_scale := 1.0
## Windows that glow from inside other houses (materials named "*window_lit*").
@export_range(0.0, 4.0, 0.01) var window_glow_scale := 1.0


## Direction the key light travels, in Godot axes (+X east, +Y up, -Z north).
func key_basis() -> Basis:
	var el := deg_to_rad(key_elevation_deg)
	var az := deg_to_rad(key_azimuth_deg)
	var from := Vector3(sin(az) * cos(el), sin(el), -cos(az) * cos(el))
	var up := Vector3.UP if absf(from.y) < 0.999 else Vector3.FORWARD
	return Basis.looking_at(-from, up)
