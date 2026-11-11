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

## The house's footprint in Godot space, with a small margin: x0, z0, x1, z1.
const INDOORS := Rect2(-0.5, -8.5, 8.3, 9.0)

var _environment: Environment
var _outside := 0.0


func _ready() -> void:
	if has_node("House"):
		HouseLights.apply($House)


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return
	if _environment == null:
		var found := get_tree().root.find_children("*", "WorldEnvironment", true, false)
		if found.is_empty():
			return
		_environment = (found[0] as WorldEnvironment).environment
	if _environment.volumetric_fog_enabled or not _environment.fog_enabled:
		return                                    # High: nothing to do
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var at := camera.global_position
	var target := 0.0 if INDOORS.has_point(Vector2(at.x, at.z)) else 1.0
	_outside = move_toward(_outside, target, delta * 1.5)
	HouseLights.apply_low_fog(_environment, _outside)
