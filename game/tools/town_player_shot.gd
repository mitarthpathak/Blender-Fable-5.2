extends SceneTree
## Screenshots of the player as the game shows it: the town, the third-person
## camera over the shoulder, the character walking and aiming.
##
##   godot --path game --script res://tools/town_player_shot.gd -- --world=town [--only=a,b]
##
## Writes res://screenshots/player_town_<name>.png. Needs a window: it renders.
## For each shot it also prints which way the player moved and faced, against
## where the camera looks, so the controls can be checked in numbers as well.

const SPOTS := [
	# name, player position (Godot space), body yaw, camera turn from behind the body,
	# aim, actions held, seconds
	["porch", Vector3(1.78, 0.05, 1.6), PI, 0.0, false, [], 1.5],
	["street_walk", Vector3(3.0, -0.4, 9.2), PI / 2.0, 0.0, false, ["move_forward"], 1.2],
	["walk_left", Vector3(4.5, -0.5, 14.0), PI, 0.0, false, ["move_left"], 1.4],
	["walk_back", Vector3(-4.0, -0.5, 14.0), PI, 0.0, false, ["move_back"], 1.4],
	["run", Vector3(-10.0, -0.5, 14.0), -PI / 2.0, 0.0, false, ["move_forward", "run"], 1.2],
	["diag_wa", Vector3(10.0, -0.5, 14.0), PI, 0.0, false, ["move_forward", "move_left"], 1.4],
	["diag_wd", Vector3(-14.0, -0.5, 14.0), PI, 0.0, false, ["move_forward", "move_right"], 1.4],
	# The body faces south, the camera is turned a quarter turn to look east,
	# then W: the player must walk east, away from the camera, not south.
	["cam_turn", Vector3(-8.0, -0.5, 14.2), PI, PI / 2.0, false, ["move_forward"], 1.6],
	# The same camera, aiming while standing: the body turns from south to east.
	["cam_turn_aim", Vector3(14.0, -0.5, 14.2), PI, PI / 2.0, true, [], 1.0],
	# Aiming and walking left: the body stays on the camera, the legs go sideways.
	["aim_strafe", Vector3(20.0, -0.5, 14.2), PI, 0.0, true, ["move_left"], 1.2],
	["junction", Vector3(3.5, -0.5, 18.0), PI, 0.0, false, [], 1.0],
]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var only: PackedStringArray = []
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.get_slice("=", 1).split(",")
	change_scene_to_file("res://main.tscn")
	for i in 120:                                # the town builds itself over the first frames
		await process_frame
	var main := current_scene
	var player := main.get("player") as CharacterBody3D
	if player == null or player.get("rig") == null:
		print("SHOT FAIL: no player, or the player is still a capsule")
		quit(1)
		return
	print("SHOT player is the character: ", player.get("rig") != null)
	for spot in SPOTS:
		if not only.is_empty() and not only.has(spot[0]):
			continue
		player.global_position = spot[1]
		player.velocity = Vector3.ZERO
		player.face(spot[2])
		player.turn_camera(spot[3])
		player.force_aim = spot[4]
		for i in 6:
			await physics_frame
		var start := player.global_position
		for action in spot[5]:
			Input.action_press(action)
		# Game time, not wall time: the same on a slow software renderer as on a GPU.
		for i in int(spot[6] * Engine.physics_ticks_per_second):
			await physics_frame
		for action in spot[5]:
			Input.action_release(action)
		await RenderingServer.frame_post_draw
		var path := "res://screenshots/player_town_%s.png" % spot[0]
		root.get_viewport().get_texture().get_image().save_png(path)
		var moved: Vector3 = player.global_position - start
		var view: float = player.view_yaw()
		var line := "SHOT %s at %s" % [path, player.global_position]
		if Vector2(moved.x, moved.z).length() > 0.3:
			line += ", moved %.1f deg left of the view" % rad_to_deg(angle_difference(view, atan2(-moved.x, -moved.z)))
		line += ", body %.1f deg left of the view" % rad_to_deg(angle_difference(view, player.body_yaw()))
		print(line)
		player.force_aim = false
	quit()
