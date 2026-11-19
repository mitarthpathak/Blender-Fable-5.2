extends SceneTree
## How evenly the camera moves from one drawn frame to the next while the
## player walks and the mouse turns the view, with the frame rate held below
## the 60 Hz physics rate (as on a laptop GPU). Uneven steps are what reads
## as judder.
##
##   godot --headless --path game --script res://tools/smooth_check.gd -- --world=town [--fps=37]
##
## Prints SMOOTH lines: the camera's step per frame (mean, and spread as a
## share of the mean; 0 is perfectly even), for walking and for turning, in
## third and first person, and how far the rifle drifts from the right hand
## between frames.

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var fps := 37
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--fps="):
			fps = int(arg.get_slice("=", 1))
	change_scene_to_file("res://main.tscn")
	for i in 60:
		await physics_frame
	var player := current_scene.get("player") as CharacterBody3D
	Engine.max_fps = fps
	print("SMOOTH physics interpolation: %s, %d fps drawn, %d Hz physics" % [
		ProjectSettings.get_setting("physics/common/physics_interpolation"), fps, Engine.physics_ticks_per_second])
	for first in [false, true]:
		player.call("set_first_person", first)
		player.global_position = Vector3(-6.0, -0.5, 14.2)
		player.call("face", PI / 2.0)          # along the street, west
		player.velocity = Vector3.ZERO
		for i in 30:
			await physics_frame
		var cam: Camera3D = player.camera
		# walking: the camera's position, frame to frame
		Input.action_press("move_forward")
		for i in 30:
			await process_frame
		var steps: Array[float] = []
		var grip: Array[float] = []
		var last := cam.get_global_transform_interpolated().origin
		for i in 90:
			await process_frame
			var now := cam.get_global_transform_interpolated().origin
			steps.append(Vector2(now.x - last.x, now.z - last.z).length())
			last = now
			var gap := _rifle_gap(player)
			if gap >= 0.0:
				grip.append(gap)
		Input.action_release("move_forward")
		_report("%s walk" % ("first person" if first else "third person"), steps, "m")
		if not grip.is_empty():
			print("SMOOTH %-20s rifle mount to right hand: %.1f to %.1f mm as drawn" % [
				("first person" if first else "third person"), grip.min() * 1000.0, grip.max() * 1000.0])
		# turning: the view's yaw, frame to frame, at a steady mouse speed
		for i in 30:
			await physics_frame
		var turn: Array[float] = []
		var lag: Array[float] = []
		var yaw := _yaw(cam)
		for i in 90:
			player.call("turn_camera", 0.02)
			await process_frame
			var y := _yaw(cam)
			turn.append(absf(angle_difference(yaw, y)))
			yaw = y
			var rig = player.get("rig")
			if rig and rig.rifle:
				lag.append(rad_to_deg(angle_difference(_yaw(rig.rifle), y)))
		_report("%s turn" % ("first person" if first else "third person"), turn, "rad")
		if first and not lag.is_empty():
			# relative to the first frame (the rifle's own axes need not point where the view does)
			var rel: Array[float] = []
			for a in lag:
				rel.append(rad_to_deg(angle_difference(deg_to_rad(lag[0]), deg_to_rad(a))))
			print("SMOOTH first person turn    rifle against the view: moves %.2f deg (the sway while turning)" % [rel.max() - rel.min()])
	quit()


## Where the rifle's mount is drawn against where the right hand is drawn.
func _rifle_gap(player: Node) -> float:
	var rig = player.get("rig")
	if rig == null or rig.rifle == null:
		return -1.0
	var skeleton: Skeleton3D = rig.skeleton
	var mount := skeleton.get_node_or_null("RightHandAttachment") as BoneAttachment3D
	if mount == null:
		return -1.0
	var bone := skeleton.find_bone(mount.bone_name)
	var hand := skeleton.get_global_transform_interpolated() * skeleton.get_bone_global_pose(bone)
	return hand.origin.distance_to(mount.get_global_transform_interpolated().origin)


func _yaw(node: Node3D) -> float:
	var f := -node.get_global_transform_interpolated().basis.z
	return atan2(f.x, -f.z)


func _report(what: String, steps: Array[float], unit: String) -> void:
	var mean := 0.0
	for s in steps:
		mean += s
	mean /= steps.size()
	var spread := 0.0
	for s in steps:
		spread += (s - mean) * (s - mean)
	spread = sqrt(spread / steps.size())
	print("SMOOTH %-20s step %.4f %s, spread %3d%% of it (min %.4f, max %.4f)" % [
		what, mean, unit, roundi(100.0 * spread / maxf(mean, 1e-6)), steps.min(), steps.max()])
