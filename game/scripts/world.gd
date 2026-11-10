@tool
extends Node3D
## The house with its baked-lighting nodes. A tool script, so the lights are
## set up in the editor exactly as in the game: open world.tscn, select the
## LightmapGI node and press "Bake Lightmaps".


func _ready() -> void:
	if has_node("House"):
		HouseLights.apply($House)
