extends SceneTree
## Look at the town from fixed cameras, the player hidden: for checking the
## build. Positions are in Godot space (x, up, z = -plan y).
##
##   godot --path game --script res://tools/town_views.gd -- --world=town [--day] [--only=name,name]
##
## Writes res://screenshots/town_<name>.png.

const VIEWS := {
	# name: [camera position, look at, fov]
	"map_top": [Vector3(4.0, 120.0, 22.0), Vector3(4.0, 0.0, 22.0), 50.0],
	"map_north": [Vector3(4.0, 55.0, -45.0), Vector3(4.0, 0.0, 22.0), 60.0],
	"south_houses": [Vector3(4.0, 3.0, 9.0), Vector3(4.0, 2.0, 30.0), 75.0],
	"house_l4": [Vector3(-2.0, 2.5, 15.0), Vector3(-10.0, 2.0, 27.0), 70.0],
	"house_l5": [Vector3(10.0, 2.5, 15.0), Vector3(18.0, 2.0, 27.0), 70.0],
	"car_sedan": [Vector3(14.5, 1.6, 12.5), Vector3(18.5, 0.6, 16.9), 60.0],
	"car_wagon": [Vector3(11.0, 1.8, 40.0), Vector3(15.6, 0.6, 44.0), 60.0],
	"car_crashed": [Vector3(-1.5, 1.7, 49.0), Vector3(2.4, 0.6, 54.6), 60.0],
	"car_west": [Vector3(-23.0, 1.7, 7.0), Vector3(-28.0, 0.6, 10.9), 60.0],
	"west_end": [Vector3(-18.0, 2.0, 14.0), Vector3(-31.0, 1.5, 14.0), 70.0],
	"east_end": [Vector3(24.0, 2.0, 14.0), Vector3(38.0, 1.5, 14.0), 70.0],
	"back_fence": [Vector3(4.0, 3.0, -12.0), Vector3(4.0, 1.5, -18.4), 80.0],
	"sedan_close": [Vector3(15.8, 1.3, 15.0), Vector3(18.5, 0.7, 16.9), 50.0],
	"sedan_side": [Vector3(18.6, 1.2, 12.6), Vector3(18.5, 0.7, 16.9), 55.0],
	"wagon_close": [Vector3(13.0, 1.4, 41.0), Vector3(15.6, 0.7, 44.0), 50.0],
	"crashed_close": [Vector3(0.0, 1.4, 51.0), Vector3(2.4, 0.7, 54.6), 50.0],
	"west_car_close": [Vector3(-24.5, 1.4, 8.6), Vector3(-28.0, 0.7, 10.9), 50.0],
	"l4_fence": [Vector3(-1.0, 2.0, 24.0), Vector3(-6.4, 1.2, 28.5), 70.0],
	"l4_fence_w": [Vector3(-20.0, 2.0, 24.0), Vector3(-14.8, 1.2, 28.5), 70.0],
	"l5_fence": [Vector3(8.0, 2.0, 24.0), Vector3(13.0, 1.2, 27.7), 70.0],
	"l5_fence_e": [Vector3(26.0, 2.0, 23.0), Vector3(20.4, 1.2, 27.7), 70.0],
}


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	change_scene_to_file("res://main.tscn")
	for i in 150:
		await process_frame
	var main := current_scene
	var only: PackedStringArray = []
	var views := VIEWS.duplicate()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.get_slice("=", 1).split(",")
		elif arg == "--survey":
			views = _survey()
	for n in ["_hud", "_prompt", "player"]:
		var node = main.get(n)
		if node:
			node.visible = false
	var cam := Camera3D.new()
	cam.far = 600.0
	main.add_child(cam)
	cam.make_current()
	for view in views:
		if not only.is_empty() and not only.has(view):
			continue
		var spec: Array = views[view]
		cam.fov = spec[2]
		var up := Vector3.UP if absf((spec[1] - spec[0]).normalized().y) < 0.99 else Vector3(0, 0, -1)
		cam.look_at_from_position(spec[0], spec[1], up)
		for i in 30:
			await process_frame
		await RenderingServer.frame_post_draw
		var path := "res://screenshots/town_%s.png" % view
		root.get_viewport().get_texture().get_image().save_png(path)
		print("VIEW ", path)
	quit()


## Eye-height views every few metres along both streets, looking at each
## side and along the street, for walking the whole town in pictures.
func _survey() -> Dictionary:
	var out := {}
	var eye := 1.65
	var k := 0
	for x in [-26.0, -16.0, -6.0, 4.0, 14.0, 24.0, 33.0]:
		for side in [["n", 9.4, -1.0], ["s", 18.9, 1.0]]:     # standing on each sidewalk, looking at the lots
			var at := Vector3(x, eye - 0.4, side[1])
			out["s%02d_%s_%d" % [k, side[0], int(x)]] = [at, at + Vector3(0, -0.4, side[2] * 10.0), 70.0]
		k += 1
	for z in [24.0, 32.0, 40.0, 48.0, 54.0]:
		for side in [["w", 0.8, -1.0], ["e", 6.2, 1.0]]:
			var at := Vector3(side[1], eye - 0.4, z)
			out["s%02d_%s_%d" % [k, side[0], int(z)]] = [at, at + Vector3(side[2] * 10.0, -0.4, 0), 70.0]
		k += 1
	out["s90_ash_west"] = [Vector3(-8.0, eye - 0.5, 14.2), Vector3(-30.0, 1.0, 14.2), 65.0]
	out["s91_ash_east"] = [Vector3(14.0, eye - 0.5, 14.2), Vector3(38.0, 1.0, 14.2), 65.0]
	out["s92_mill_south"] = [Vector3(3.5, eye - 0.5, 20.0), Vector3(3.5, 1.0, 57.0), 65.0]
	out["s93_mill_north"] = [Vector3(3.5, eye - 0.5, 50.0), Vector3(3.5, 1.0, 10.0), 65.0]
	return out
