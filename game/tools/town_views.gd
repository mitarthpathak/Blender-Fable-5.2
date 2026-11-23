extends SceneTree
## Look at the town from fixed cameras, the player hidden: for checking the
## build. Positions are in Godot space (x, up, z = -plan y).
##
##   godot --path game --script res://tools/town_views.gd -- --world=town [--day] [--only=name,name]
##
## Writes res://screenshots/town_<name>.png.

const VIEWS := {
	"mill_breach": [Vector3(5.2, 1.24, 51.0), Vector3(7.2, 0.65, 60.0), 69.0],
	"mill_road_mid": [Vector3(5.0, 0.63, 79.0), Vector3(3.6, -0.4, 102.0), 68.0],
	"mill_checkpoint": [Vector3(4.9, 0.96, 67.0), Vector3(0, 0.8, 74.0), 63.0],
	"mill_gate": [Vector3(4.2, -0.96, 114.0), Vector3(3.0, 0.55, 123.0), 68.0],
	"mill_yard": [Vector3(8.2, -1.35, 125.5), Vector3(-1.5, -0.2, 136.0), 72.0],
	"mill_road_back": [Vector3(2.2, -0.18, 97.0), Vector3(4.0, 1.5, 60.0), 65.0],
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
	# trees: one close, from under it; one at street distance; the edge trees against the sky
	"tree_close": [Vector3(-5.5, 1.6, 9.5), Vector3(-9.0, 4.5, 5.5), 70.0],
	"tree_street": [Vector3(-2.0, 1.6, 15.5), Vector3(-9.0, 4.0, 5.5), 60.0],
	"tree_base": [Vector3(-7.4, 1.3, 7.2), Vector3(-9.0, 0.4, 5.5), 60.0],
	"tree_edge": [Vector3(-20.0, 1.7, 14.2), Vector3(-34.0, 6.0, 12.0), 65.0],
	"leaves_fall": [Vector3(-3.0, 1.6, 12.0), Vector3(-7.0, 2.4, 6.0), 55.0],
	# house and car details: plates, meter side, the condenser side, the cracked windshield
	"sedan_rear": [Vector3(22.6, 1.25, 15.6), Vector3(20.8, 0.55, 16.9), 45.0],
	"house_l3_meter": [Vector3(26.6, 1.6, -2.6), Vector3(24.2, 1.1, -5.0), 70.0],
	"house_l3_ac": [Vector3(12.4, 1.6, -2.4), Vector3(15.0, 0.6, -5.0), 70.0],
	"crashed_glass": [Vector3(4.4, 1.9, 52.2), Vector3(2.4, 1.2, 54.6), 50.0],
	# the fallen tree across Ashgrove: the picket fence it came down on, and the whole tree from the road
	"fallen_fence": [Vector3(32.6, 1.6, 11.2), Vector3(36.4, 0.1, 7.6), 60.0],
	"fallen_tree": [Vector3(27.0, 2.0, 17.5), Vector3(36.0, 0.8, 11.5), 70.0],
	"fallen_stump": [Vector3(35.0, 1.4, 18.2), Vector3(36.4, -0.05, 20.2), 55.0],
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
		elif arg == "--lots":
			views = _lots()
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



## Two views of every lot with a house, for checking the fences against the
## houses: from the street (the side yards and the fences returning to the
## house) and from inside the back yard (the house and both side fences).
## Lots as in projects/03-town/plan.py: x0, y0, x1, y1 in Blender plan space
## (Godot z = -y), and which way the front faces.
const LOTS := [
	["l1", -4.5, -8.6, 11.5, 18.0, "s"], ["l2", -21.0, -8.6, -4.5, 18.0, "s"], ["l3", 11.5, -8.6, 28.0, 18.0, "s"],
	["l4", -15.5, -40.0, -1.6, -19.7, "n"], ["l5", 8.6, -40.0, 38.5, -19.7, "n"], ["l6", -20.0, -58.0, -1.6, -40.0, "e"],
	["l8", -30.5, -8.6, -21.0, 18.0, "s"], ["l9", 28.0, -8.6, 38.5, 18.0, "s"], ["l10", -30.5, -40.0, -15.5, -19.7, "n"],
]


func _lots() -> Dictionary:
	var out := {}
	for lot in LOTS:
		var x0: float = lot[1]
		var y0: float = lot[2]
		var x1: float = lot[3]
		var y1: float = lot[4]
		var cx := (x0 + x1) / 2.0
		var cy := (y0 + y1) / 2.0
		var front: Vector3
		var front_at: Vector3
		var back: Vector3
		var back_at: Vector3
		match lot[5]:
			"s":
				front = Vector3(cx, 2.6, -(y0 - 2.5))
				front_at = Vector3(cx, 0.5, -(y0 + 9.0))
				back = Vector3(cx, 2.0, -(y1 - 0.8))
				back_at = Vector3(cx, 1.2, -cy)
			"n":
				front = Vector3(cx, 2.6, -(y1 + 2.5))
				front_at = Vector3(cx, 0.5, -(y1 - 9.0))
				back = Vector3(cx, 2.0, -(y0 + 0.8))
				back_at = Vector3(cx, 1.2, -cy)
			_:
				front = Vector3(x1 + 2.5, 2.6, -cy)
				front_at = Vector3(x1 - 9.0, 0.5, -cy)
				back = Vector3(x0 + 0.8, 2.0, -cy)
				back_at = Vector3(cx, 1.2, -cy)
		out["lot_%s_front" % lot[0]] = [front, front_at, 80.0]
		out["lot_%s_back" % lot[0]] = [back, back_at, 85.0]
	return out
