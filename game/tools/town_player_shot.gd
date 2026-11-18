extends SceneTree
## Screenshots of the player as the game shows it: the town, the third-person
## camera over the shoulder, the character walking and aiming.
##
##   godot --path game --script res://tools/town_player_shot.gd -- --world=town
##
## Writes res://screenshots/player_town_<n>.png. Needs a window: it renders.

const SPOTS := [
	# name, player position (Godot space), yaw, aim, actions held, seconds
	["porch", Vector3(1.78, 0.05, 1.6), PI, false, [], 1.5],
	["street_walk", Vector3(3.0, -0.4, 9.2), PI / 2.0, false, ["move_forward"], 1.2],
	["walk_left", Vector3(4.5, -0.5, 14.0), PI, false, ["move_left"], 1.4],
	["walk_back", Vector3(-4.0, -0.5, 14.0), PI, false, ["move_back"], 1.4],
	["run", Vector3(-10.0, -0.5, 14.0), -PI / 2.0, false, ["move_forward", "run"], 1.2],
	["diag_wa", Vector3(10.0, -0.5, 14.0), PI, false, ["move_forward", "move_left"], 1.4],
	["diag_wd", Vector3(-14.0, -0.5, 14.0), PI, false, ["move_forward", "move_right"], 1.4],
	["junction", Vector3(3.5, -0.5, 18.0), PI, false, [], 1.0],
]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
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
		player.global_position = spot[1]
		player.rotation.y = spot[2]
		player.velocity = Vector3.ZERO
		var rig = player.get("rig")
		for action in spot[4]:
			Input.action_press(action)
		var until := Time.get_ticks_msec() + int(spot[5] * 1000.0)
		while Time.get_ticks_msec() < until:
			if spot[3]:
				rig.aiming = true
			await process_frame
		for action in spot[4]:
			Input.action_release(action)
		await RenderingServer.frame_post_draw
		var path := "res://screenshots/player_town_%s.png" % spot[0]
		root.get_viewport().get_texture().get_image().save_png(path)
		print("SHOT ", path, " at ", player.global_position)
		rig.aiming = false
	quit()
