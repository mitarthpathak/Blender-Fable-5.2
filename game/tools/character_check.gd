extends SceneTree
## Look at the Mixamo character on its own: one picture per animation, from
## the front and the side, with the rifle in its hand.
##
##   godot --path game --script res://tools/character_check.gd
##
## Writes res://screenshots/character_<clip>_<view>.png and prints CHECK
## lines: how tall the character came in, which clips loaded, where the rifle
## ended up and how close the left palm is to the handguard. Needs a window
## (not --headless): it renders. `-- --only=aim,idle` for some clips only.

const OUT := "res://screenshots"
const SHOTS := [
	# name, locomotion speed, aim, one-shot to fire, seconds to let it play
	["idle", 0.0, false, "", 0.6],
	["walk", 2.6, false, "", 0.5],
	["run", 4.6, false, "", 0.4],
	["aim", 0.0, true, "", 0.8],
	["fire", 0.0, true, "fire", 0.25],
	["jump", 0.0, false, "jump", 0.45],
]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.32, 0.34, 0.36)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.62, 0.66)
	env.environment.ambient_light_energy = 0.7
	env.environment.tonemap_mode = Environment.TONE_MAPPER_AGX
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 30, 0)
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	world.add_child(sun)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(8, 8)
	floor_mesh.mesh = plane
	world.add_child(floor_mesh)

	var rig := CharacterRig.create()
	if rig == null:
		print("CHECK FAIL: CharacterRig.create() returned null (files missing or unusable)")
		quit(1)
		return
	world.add_child(rig)
	var tree := rig.get_node("%s/AnimationTree" % rig.get_path_to(rig.model)) as AnimationTree
	var clips := (rig.model.get_node("Clips") as AnimationPlayer).get_animation_list()
	print("CHECK clips loaded: ", clips)
	print("CHECK model scale: ", rig.model.scale.x)

	var cam := Camera3D.new()
	cam.fov = 40.0
	world.add_child(cam)
	cam.make_current()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))

	var only := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.get_slice("=", 1)
	for shot in SHOTS:
		if only != "" and not shot[0] in only.split(","):
			continue
		var speed: float = shot[1]
		tree.set("parameters/locomotion/blend_position", speed)
		tree.set("parameters/aim_blend/blend_amount", 1.0 if shot[2] else 0.0)
		if shot[3] != "":
			tree.set("parameters/%s/request" % shot[3], AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
		if rig.grip:                # as CharacterRig.update sets it: both hands on, except at a run
			rig.grip.weight = 1.0 if shot[2] or speed <= CharacterRig.WALK_SPEED * 1.7 else 0.0
		var until := Time.get_ticks_msec() + int(shot[4] * 1000.0)
		while Time.get_ticks_msec() < until:
			await process_frame
		var hands := rig.rifle.global_position if rig.rifle else Vector3(0, 1.1, 0)
		for view in [["front", Vector3(0.6, 1.25, -3.4), Vector3(0, 0.95, 0), 40.0],
				["side", Vector3(3.4, 1.25, -0.3), Vector3(0, 0.95, 0), 40.0],
				# close-ups of the hands and the rifle: right side, left side, from above
				["hands_right", hands + Vector3(0.9, 0.15, -0.35), hands, 30.0],
				["hands_left", hands + Vector3(-0.9, 0.15, -0.45), hands, 30.0],
				["hands_top", hands + Vector3(0.05, 0.95, -0.25), hands, 32.0],
				["hands_under", hands + Vector3(-0.55, -0.55, -0.35), hands + Vector3(-0.05, 0.0, -0.15), 34.0]]:
			cam.fov = view[3]
			cam.look_at_from_position(view[1], view[2])
			await process_frame
			await RenderingServer.frame_post_draw
			var image := root.get_viewport().get_texture().get_image()
			var path := "%s/character_%s_%s.png" % [OUT, shot[0], view[0]]
			image.save_png(path)
		var top := -INF
		var bottom := INF
		var sk := rig.skeleton
		for bone in sk.get_bone_count():
			var y := (sk.global_transform * sk.get_bone_global_pose(bone)).origin.y
			top = maxf(top, y)
			bottom = minf(bottom, y)
		var muzzle := rig.rifle.global_transform * Vector3(0, 0, 0.6) if rig.rifle else Vector3.ZERO
		if rig.grip and rig.grip.weight > 0.0:
			print("CHECK %-5s left hand: grip weight %.1f, palm %.1f cm from the handguard point" % [
				shot[0], rig.grip.weight, rig.grip.palm_error() * 100.0])
		print("CHECK %-5s bones y %.2f..%.2f  rifle at %s  muzzle points %s" % [shot[0], bottom, top,
			rig.rifle.global_position if rig.rifle else "none", muzzle - (rig.rifle.global_position if rig.rifle else Vector3.ZERO)])
	quit()
