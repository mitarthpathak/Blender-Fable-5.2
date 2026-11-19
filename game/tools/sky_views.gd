extends SceneTree
## The town's sky in every look, from a few places in the street: for tuning
## scripts/sky.gdshader and the presets' Sky values.
##
##   godot --path game --script res://tools/sky_views.gd -- --world=town [--looks=1000_clear,0300_foggy] [--quality=low]
##
## Writes res://screenshots/sky_<look>_<view>.png.

const VIEWS := {
	# name: [camera position, look at, fov] in Godot space
	"street": [Vector3(-8.0, 1.6, 14.2), Vector3(-30.0, 4.5, 14.2), 70.0],
	"up": [Vector3(4.0, 1.6, 14.0), Vector3(14.0, 9.0, 4.0), 75.0],
	"light": [Vector3(4.0, 1.6, 14.0), Vector3(4.0, 1.6, 14.0), 70.0],     # looking at the sun or moon
}


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	change_scene_to_file("res://main.tscn")
	for i in 150:
		await process_frame
	var main := current_scene
	for n in ["_hud", "_prompt", "player"]:
		var node = main.get(n)
		if node:
			node.visible = false
	var presets := main.get_node("LightingPresets")
	var looks: PackedStringArray = []
	for t in LightingPresets.TIME_IDS:
		for w in LightingPresets.WEATHERS:
			looks.append("%s_%s" % [t, w])
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--looks="):
			looks = arg.get_slice("=", 1).split(",")
	var cam := Camera3D.new()
	cam.far = 600.0
	main.add_child(cam)
	cam.make_current()
	for look in looks:
		presets.call("_set_look_id", look)
		presets.call("_show_target")
		var key: DirectionalLight3D = main.get("moon")
		for view in VIEWS:
			var spec: Array = VIEWS[view]
			var at: Vector3 = spec[1]
			if view == "light" and key:
				# towards the light, a little below it so the street is in the frame too
				var to_light := key.global_transform.basis.z.normalized()
				at = spec[0] + to_light * 10.0 - Vector3(0, 1.5, 0)
			cam.fov = spec[2]
			cam.look_at_from_position(spec[0], at, Vector3.UP)
			for i in 40:
				await process_frame
			await RenderingServer.frame_post_draw
			var path := "res://screenshots/sky_%s_%s.png" % [look, view]
			root.get_viewport().get_texture().get_image().save_png(path)
			print("SKY ", path)
	quit()
