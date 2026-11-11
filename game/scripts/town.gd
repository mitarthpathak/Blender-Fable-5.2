@tool
extends Node3D
## The town world (world_town.tscn): the player's house plus the Halden Ridge
## streets from projects/03-town, a LightmapGI node and the room probes.
##
## Everything is set up in code from the two imported models, so re-exporting
## either one from Blender needs no hand edits here:
##
## - the house's own yard, road, fence, mailbox, pole and street light are
##   removed by name (the town replaces them); the house files are not edited;
## - collision for the town's ground, houses, fences, cars and barriers, simple
##   cylinders for trees and poles, none for small clutter;
## - repeated props become MultiMesh instances (one draw call per material);
## - small props fade out with distance; street lights fade and only the
##   nearest few cast shadows;
## - sodium street lights, one flickering, and one dimly lit window.
##
## A tool script, like world.gd, so the lights are right in the editor when
## the LightmapGI node is baked.
##
## Command line (after `--`, with `--world=town`):
##   --town-selftest   walk out of the front door to the street, test curbs,
##                     a porch and an edge wall; prints TEST lines and quits
##   --town-perf       FPS, draw calls and triangles from three viewpoints

## The house's own exterior objects that the town replaces (projects/03-town/plan.py).
const HOUSE_HIDE := ["yard_ground", "yard_paths", "street_road", "fence_picket", "mailbox", "telephone_pole", "street_sodium"]
## Town meshes that get trimesh collision.
const TRIMESH_PREFIXES := ["ground_", "house_", "fence_", "car_", "barrier_", "jersey_", "fallen_tree_stump", "sign_road_closed", "bench_"]
## Flat or thin things that should not cast shadows.
const NO_SHADOW_PREFIXES := ["puddles", "decals_", "detail_", "road_markings", "road_patches", "grass", "weed", "wires", "manhole", "leaf_pile", "ground_", "backdrop"]
## Repeated props drawn as MultiMesh instances.
const INSTANCED_PREFIXES := ["grass_", "weed_", "leaf_pile_", "manhole_", "mailbox_", "trash_can_", "tree_", "edgetree_", "pole_P", "streetlamp_P"]
## Simple cylinder colliders: name prefix -> [radius, height].
const CYLINDERS := {"tree_": [0.26, 4.0], "pole_P": [0.17, 8.0], "trash_can_": [0.31, 0.9], "hydrant_": [0.14, 0.75]}
## Small props that fade out with distance (metres). Fog hides them sooner.
## Decals and street detail come from Blender in 24 m sectors ("decals_3_7"), so
## each sector is culled and faded on its own.
const FADE_PREFIXES := {"hydrant_": 45.0, "sign_": 55.0, "barrier_": 60.0, "jersey_": 60.0, "car_": 80.0, "wires": 70.0,
	"decals_": 46.0, "detail_": 48.0}

const SODIUM := Color(1.0, 0.55, 0.20)
const WINDOW_WARM := Color(1.0, 0.62, 0.34)

## Fixed views for screenshots and performance checks: position, target (Godot axes).
const VIEWS := {
	"front_door": [Vector3(1.70, 1.62, -0.45), Vector3(2.8, 0.9, 18.0)],
	"junction": [Vector3(9.5, 1.65, 9.4), Vector3(2.0, 1.4, 24.0)],
	"side_street": [Vector3(5.6, 1.65, 27.0), Vector3(1.2, 1.6, 50.0)],
}

var _street_lights: Array[OmniLight3D] = []
var _flicker: Array[OmniLight3D] = []
var _flicker_material: StandardMaterial3D
var _flicker_emission := 1.0
var _noise := FastNoiseLite.new()
var _time := 0.0
var _quality := ""
var _shadow_timer := 0.0


func _enter_tree() -> void:
	add_to_group("outdoor_world")       # LightingPresets: no SDFGI sky light out here


func _ready() -> void:
	if has_node("House"):
		_strip_house($House)
		HouseLights.apply($House)
	if has_node("Town"):
		_setup_lights($Town)
	if Engine.is_editor_hint():
		return
	var town: Node3D = $Town
	var stats := _setup_town(town)
	_add_view_cameras()
	_noise.frequency = 1.0
	print("town ready: %d collision bodies, %d meshes kept, %d instanced into %d multimeshes, %d street lights" % [
		stats["bodies"], stats["meshes"], stats["instanced"], stats["multimeshes"], _street_lights.size()])
	var args := OS.get_cmdline_user_args()
	if "--preset-shots" in args or "--town-perf" in args:
		_open_front_doors()
	if "--town-selftest" in args:
		_self_test.call_deferred()
	elif "--town-perf" in args:
		_perf.call_deferred()


# --- House ------------------------------------------------------------------------

## Take out the house's own yard, road, fence, mailbox, pole and street light.
## At run time they are freed at once, before main.gd gives the house its
## collision; in the editor they are only hidden.
func _strip_house(house: Node) -> void:
	for child in house.get_children():
		var n := String(child.name)
		if n in HOUSE_HIDE or n.trim_prefix("light_") in HOUSE_HIDE:
			if Engine.is_editor_hint():
				(child as Node3D).visible = false
			else:
				house.remove_child(child)
				child.free()


func _open_front_doors() -> void:
	for pair in [["door_front", -95.0], ["door_screen", -105.0]]:
		var door := get_node_or_null("House/" + pair[0]) as Node3D
		if door:
			door.rotation.y = deg_to_rad(pair[1])


# --- Lights ---------------------------------------------------------------------------

func _setup_lights(town: Node) -> void:
	_street_lights.clear()
	_flicker.clear()
	for child in town.get_children():
		if not child is OmniLight3D:
			continue
		var lamp := child as OmniLight3D
		var n := String(lamp.name)
		if n.contains("sodium"):
			# The house's own street light had energy 3; out on the street the lamps
			# have to hold their pools against the moon, so they are stronger.
			lamp.light_color = SODIUM
			lamp.light_energy = 9.0
			lamp.omni_range = 24.0
			lamp.omni_attenuation = 1.1
			lamp.light_volumetric_fog_energy = 3.0
			lamp.shadow_enabled = true
			lamp.omni_shadow_mode = OmniLight3D.SHADOW_DUAL_PARABOLOID   # two shadow passes, not six
			lamp.shadow_bias = 0.06
			lamp.shadow_blur = 1.6
			lamp.light_size = 0.15
			lamp.distance_fade_enabled = true
			lamp.distance_fade_begin = 55.0
			lamp.distance_fade_length = 12.0
			lamp.distance_fade_shadow = 40.0
			lamp.light_bake_mode = Light3D.BAKE_DYNAMIC        # direct light live, bounce baked
			_street_lights.append(lamp)
			if n.contains("flicker"):
				lamp.light_bake_mode = Light3D.BAKE_DISABLED   # it changes, so it cannot be baked
				_flicker.append(lamp)
		elif n.begins_with("lit_window"):
			lamp.light_color = WINDOW_WARM
			lamp.light_energy = 0.35
			lamp.omni_range = 4.5
			lamp.omni_attenuation = 1.4
			lamp.shadow_enabled = false
			lamp.light_volumetric_fog_energy = 0.5
			lamp.light_bake_mode = Light3D.BAKE_DYNAMIC


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return
	_time += delta
	for i in _flicker.size():
		# A failing lamp: long steady stretches, buzzing dips, the odd blackout.
		var lamp := _flicker[i]
		var base: float = lamp.get_meta("preset_energy", 9.0)
		var slow := _noise.get_noise_2d(_time * 0.9, 300.0 + i * 17.0)
		var fast := _noise.get_noise_2d(_time * 26.0, 500.0 + i * 31.0)
		var level := 1.0 - 0.15 * absf(fast)
		if slow > 0.12:
			level *= 0.2 + 0.8 * absf(fast)
		if fast > 0.38 and slow > 0.0:
			level = 0.03
		lamp.light_energy = base * level
		if _flicker_material:
			_flicker_material.emission_energy_multiplier = _flicker_emission * level * lamp.get_meta("preset_scale", 1.0)
	# Follow main.gd's quality setting, and keep shadows on the nearest street lights only.
	var main := get_parent()
	if main and "quality" in main:
		_shadow_timer -= delta
		if main.quality != _quality:
			_quality = main.quality
			_apply_quality(_quality == "high")
			_shadow_timer = 0.0
		if _shadow_timer <= 0.0:
			_shadow_timer = 0.5
			_update_shadows(main)


## Low is aimed at Intel UHD 620 class graphics, where the street costs per
## pixel, not per triangle (an empty scene runs at about 70 FPS there, the
## house alone at 23 from its own front door). So in the town, Low also:
## - gives the street lights a shorter reach and no shadows (the moon keeps its shadow),
## - uses the cheapest soft-shadow filter,
## - renders at LOW_SCALE instead of main.gd's 0.77.
## The scale is set once per quality change. Changing it every few frames
## (dynamic resolution) was tried and hung the Intel driver after a few dozen
## changes, so it is fixed.
const LOW_SCALE := 0.58

var fixed_scale := false           # set by --scale=


func _apply_quality(high: bool) -> void:
	for lamp in _street_lights:
		lamp.omni_range = 24.0 if high else 16.0
	var filter := RenderingServer.SHADOW_QUALITY_SOFT_HIGH if high else RenderingServer.SHADOW_QUALITY_SOFT_VERY_LOW
	RenderingServer.directional_soft_shadow_filter_set_quality(filter)
	RenderingServer.positional_soft_shadow_filter_set_quality(filter)
	if not high and not fixed_scale:
		get_viewport().scaling_3d_scale = LOW_SCALE


func _update_shadows(main: Node) -> void:
	var eye := Vector3.ZERO
	var cam := get_viewport().get_camera_3d()
	if cam:
		eye = cam.global_position
	var lights := _street_lights.filter(func(l: OmniLight3D) -> bool: return l.visible)
	lights.sort_custom(func(a: OmniLight3D, b: OmniLight3D) -> bool:
		return a.global_position.distance_squared_to(eye) < b.global_position.distance_squared_to(eye))
	var budget := 3 if _quality == "high" else 0
	for i in lights.size():
		lights[i].shadow_enabled = i < budget


# --- Town ----------------------------------------------------------------------------------

func _starts(n: String, prefixes: Array) -> bool:
	for p in prefixes:
		if n.begins_with(p):
			return true
	return false


func _setup_town(town: Node3D) -> Dictionary:
	var stats := {"bodies": 0, "meshes": 0, "instanced": 0, "multimeshes": 0}
	var groups := {}                     # Mesh -> Array of MeshInstance3D
	for child in town.get_children():
		if child is StaticBody3D:
			stats["bodies"] += 1         # curb ramps, step ramps, edge walls ("-convcolonly" in Blender)
			continue
		if not child is MeshInstance3D:
			continue
		var mi := child as MeshInstance3D
		var n := String(mi.name)
		if _starts(n, NO_SHADOW_PREFIXES):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if _starts(n, TRIMESH_PREFIXES):
			mi.create_trimesh_collision()
			stats["bodies"] += 1
		for prefix in CYLINDERS:
			if n.begins_with(prefix) and not n.contains("transformer") and absf(mi.rotation.x) < 0.5:
				_add_cylinder(town, mi, CYLINDERS[prefix][0], CYLINDERS[prefix][1])
				stats["bodies"] += 1
		for prefix in FADE_PREFIXES:
			if n.begins_with(prefix):
				mi.visibility_range_end = FADE_PREFIXES[prefix]
				mi.visibility_range_end_margin = 6.0
				mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		if n == "streetlamp_P6":
			_make_flicker_lamp(mi)       # its own material, so only this lamp head flickers
		elif _starts(n, INSTANCED_PREFIXES):
			if not groups.has(mi.mesh):
				groups[mi.mesh] = []
			groups[mi.mesh].append(mi)
			continue
		stats["meshes"] += 1
	for mesh in groups:
		var list: Array = groups[mesh]
		if list.size() < 2:
			stats["meshes"] += 1
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = list.size()
		for i in list.size():
			mm.set_instance_transform(i, (list[i] as MeshInstance3D).transform)
		var node := MultiMeshInstance3D.new()
		var first := list[0] as MeshInstance3D
		node.name = "mm_" + String(first.name).rstrip("0123456789").trim_suffix("_")
		node.multimesh = mm
		node.cast_shadow = first.cast_shadow
		town.add_child(node)
		for mi in list:
			mi.queue_free()
		stats["instanced"] += list.size()
		stats["multimeshes"] += 1
	return stats


func _add_cylinder(town: Node3D, mi: MeshInstance3D, radius: float, height: float) -> void:
	var body := StaticBody3D.new()
	body.name = "col_" + String(mi.name)
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = radius * mi.scale.x
	cyl.height = height
	shape.shape = cyl
	shape.position.y = height / 2.0
	body.add_child(shape)
	body.position = mi.position
	town.add_child(body)


func _make_flicker_lamp(mi: MeshInstance3D) -> void:
	for s in mi.mesh.get_surface_count():
		var mat := mi.mesh.surface_get_material(s) as StandardMaterial3D
		if mat and mat.resource_name.contains("sodium_on"):
			_flicker_material = mat.duplicate()
			_flicker_material.resource_name = "street_flicker_glow"   # not a preset-managed name
			_flicker_emission = _flicker_material.emission_energy_multiplier
			mi.set_surface_override_material(s, _flicker_material)


func _add_view_cameras() -> void:
	for view in VIEWS:
		var cam := Camera3D.new()
		cam.name = "cam_preset_" + view
		cam.fov = 72.0
		cam.near = 0.05
		add_child(cam)
		cam.look_at_from_position(VIEWS[view][0], VIEWS[view][1], Vector3.UP)


# --- Checks ------------------------------------------------------------------------------------

func _walk(player: CharacterBody3D, yaw: float, seconds: float, stop: Callable = Callable()) -> void:
	player.rotation.y = yaw
	Input.action_press("move_forward")
	for i in int(seconds * 60.0):
		await get_tree().physics_frame
		if stop.is_valid() and stop.call():
			break
	Input.action_release("move_forward")
	for i in 10:
		await get_tree().physics_frame


## `-- --world=town --town-selftest`: no rendering needed.
func _self_test() -> void:
	var main := get_parent()
	for i in 4:
		await get_tree().physics_frame
	var player: CharacterBody3D = main.player
	print("TEST house pieces removed: ", not has_node("House/yard_ground") and not has_node("House/light_street_sodium"),
		"  house porch kept: ", has_node("House/porch_deck"))
	_open_front_doors()
	for i in 30:
		await get_tree().physics_frame
	# Out of the front door, across the porch, down the steps and the path, to the middle of the road.
	var marks := {}
	var south := PI
	await _walk(player, south, 14.0, func() -> bool:
		var p := player.global_position
		for mark in [["porch", 1.4], ["yard", 5.0], ["sidewalk", 9.4], ["road", 13.5]]:
			if not marks.has(mark[0]) and p.z >= mark[1]:
				marks[mark[0]] = p.y
		return p.z >= 14.0)
	print("TEST walked out of the front door to z=%.1f (road centre is 14.2)" % player.global_position.z)
	if player.global_position.z < 13.5:
		Input.action_press("move_forward")
		for i in 5:
			await get_tree().physics_frame
		for i in player.get_slide_collision_count():
			var hit := player.get_slide_collision(i)
			var body := hit.get_collider() as Node
			print("TEST   blocked by %s (child of %s) at %s, normal %s" % [
				body.name, body.get_parent().name, hit.get_position(), hit.get_normal()])
		Input.action_release("move_forward")
	print("TEST heights  porch %.2f (0.00)  yard %.2f (-0.45)  sidewalk %.2f (-0.40)  road %.2f (-0.53)" % [
		marks.get("porch", NAN), marks.get("yard", NAN), marks.get("sidewalk", NAN), marks.get("road", NAN)])
	# Down Mill Road to the barriers.
	await _walk(player, south, 22.0, func() -> bool: return player.global_position.z >= 56.5)
	print("TEST Mill Road: stopped at z=%.1f (barriers at 55.8, edge wall at 57.0)" % player.global_position.z)
	# Up a curb from the road onto the sidewalk.
	player.global_position = Vector3(10.0, -0.5, 13.0)
	await _walk(player, 0.0, 3.5)
	print("TEST curb: from the road to y=%.2f at z=%.1f (sidewalk is -0.40, fence at 8.4)" % [
		player.global_position.y, player.global_position.z])
	# Onto a neighbour's porch (16 Ashgrove Street) and against its locked door.
	player.global_position = Vector3(19.4, -0.4, 7.5)
	await _walk(player, 0.0, 6.0)
	print("TEST neighbour porch: y=%.2f at z=%.1f (deck is -0.02, door at -0.2)" % [
		player.global_position.y, player.global_position.z])
	# Along Ashgrove to the east end.
	player.global_position = Vector3(30.0, -0.5, 14.2)
	await _walk(player, -PI / 2.0, 6.0)
	print("TEST east end: stopped at x=%.1f (fallen tree at 36, edge wall at 39)" % player.global_position.x)
	player.global_position = Vector3(-24.0, -0.5, 14.2)
	await _walk(player, PI / 2.0, 6.0)
	print("TEST west end: stopped at x=%.1f (barriers at -29, edge wall at -31)" % player.global_position.x)
	get_tree().quit()


## `-- --world=town --town-perf [--quality=low]`: average FPS, draw calls and
## triangles at the three fixed views, with vsync off.
func _perf() -> void:
	var main := get_parent()
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	for arg in OS.get_cmdline_user_args():
		# --hide=Town or --hide=House/porch_deck,Town/wires: see what a part of the scene costs
		if arg.begins_with("--hide="):
			for path in arg.get_slice("=", 1).split(","):
				var hidden := get_node_or_null(path) as Node3D
				if hidden:
					hidden.visible = false
		elif arg.begins_with("--street-range="):
			for lamp in _street_lights:
				lamp.omni_range = float(arg.get_slice("=", 1))
		elif arg.begins_with("--scale="):
			fixed_scale = true
			get_viewport().scaling_3d_scale = float(arg.get_slice("=", 1))
		elif arg == "--no-shadows":
			for light in find_children("*", "Light3D", true, false):
				(light as Light3D).shadow_enabled = false
			_shadow_timer = 1e9
	for n in ["_hud", "_prompt", "player"]:
		var item = main.get(n)
		if item:
			item.visible = false
	for i in 30:
		await get_tree().process_frame
	for view in VIEWS:
		var cam := get_node("cam_preset_" + view) as Camera3D
		cam.make_current()
		for i in 90:
			await get_tree().process_frame
		var started := Time.get_ticks_usec()
		var frames := 150
		var worst := 0.0
		var last := started
		for i in frames:
			await get_tree().process_frame
			var now := Time.get_ticks_usec()
			worst = maxf(worst, (now - last) / 1000.0)
			last = now
		var seconds := (Time.get_ticks_usec() - started) / 1e6
		print("PERF %s %s: %.1f FPS avg (worst frame %.1f ms), render scale %.2f, %d draw calls, %d triangles, %d objects" % [
			main.quality, view, frames / seconds, worst, get_viewport().scaling_3d_scale,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)])
	print("PERF video memory: %.0f MB (textures %.0f MB)" % [
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_VIDEO_MEM_USED) / 1048576.0,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED) / 1048576.0])
	get_tree().quit()
