@tool
extends Node3D
## The house with its baked-lighting nodes. A tool script, so the lights are
## set up in the editor exactly as in the game: open world.tscn, select the
## LightmapGI node and press "Bake Lightmaps".
##
## In the running game it also looks after the Low preset's fog. Low has no
## volumetric fog, so outdoors it gets a cheap depth and height fog that is
## thick and pale enough to see; indoors it falls back to a thin dark one.
## The High preset (volumetric fog on) is left exactly as main.gd sets it.
##
## The `night_fill` lights are moonlight bounced round the upstairs rooms. On
## High, SDFGI replaces the flat ambient light and those rooms go black
## without them; on Low the ambient light is still there, so they are turned
## well down. They cast no shadows and are not baked: once the lightmaps are
## baked they are switched off (FILL_WITH_LIGHTMAPS).

## The house's footprint in Godot space, with a small margin: x0, z0, x1, z1.
const INDOORS := Rect2(-0.5, -8.5, 8.3, 9.0)

const FILL_HIGH := 1.0
const FILL_LOW := 0.25
const FILL_WITH_LIGHTMAPS := 0.0

var _environment: Environment
var _fills := {}                 # light -> its energy in the scene file
var _outside := 0.0


func _ready() -> void:
	if has_node("House"):
		HouseLights.apply($House)
	for child in get_children():
		if child is Light3D and child.is_in_group("night_fill"):
			_fills[child] = (child as Light3D).light_energy


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return
	if _environment == null:
		var found := get_tree().root.find_children("*", "WorldEnvironment", true, false)
		if found.is_empty():
			return
		_environment = (found[0] as WorldEnvironment).environment
	var high := _environment.volumetric_fog_enabled or not _environment.fog_enabled
	var baked := has_node("LightmapGI") and ($LightmapGI as LightmapGI).light_data != null
	var level := FILL_WITH_LIGHTMAPS if baked else (FILL_HIGH if high else FILL_LOW)
	for light in _fills:
		(light as Light3D).light_energy = _fills[light] * level
	if high:
		return                                    # High: the fog is main.gd's
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var at := camera.global_position
	var target := 0.0 if INDOORS.has_point(Vector2(at.x, at.z)) else 1.0
	_outside = move_toward(_outside, target, delta * 1.5)
	HouseLights.apply_low_fog(_environment, _outside)
