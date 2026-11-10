extends Node3D
## Loads the house exported from Blender and makes it walkable: collision,
## lighting, a night environment, doors, a player and a quality setting.
##
## Everything is set up in code from the imported scene, so re-exporting
## house.glb from Blender needs no hand edits here.

const HOUSE_SCENE := "res://assets/house/house.glb"
const SKY_HDR := "res://assets/house/night_street.hdr"
const SETTINGS_FILE := "user://settings.cfg"

## Meshes that should not block the player: flat decals, soft furnishings,
## wires and small loose things. The stair steps are left out because the
## ramp collider stands in for them.
const NO_COLLISION_PREFIXES := [
	"decals_", "electrics_", "curtain_", "coat_", "mail_", "clutter_", "fog_", "plant_",
	"rug_", "runner_", "doormat_", "lamp_broken", "stairs_balustrade", "shade_",
]
const NO_COLLISION_NAMES := ["stairs"]

## How far each door swings, in degrees about its hinge, if the model does
## not say. Blender's Z rotation is Godot's Y.
const DOOR_SWING_DEFAULT := {"door_front": -95.0}

const WARM := Color(1.0, 0.62, 0.34)
const MOONLIGHT := Color(0.50, 0.66, 1.0)
const TV_COLOR := Color(0.55, 0.70, 1.0)
## The television's glow, where the Blender scene had an area light.
const TV_POSITION := Vector3(6.75, 0.78, -0.92)

var house: Node3D
var player: CharacterBody3D
var world_env: WorldEnvironment
var moon: DirectionalLight3D
var quality := "high"

var _doors: Array[Node3D] = []
var _door_open := {}
var _door_tweens := {}
var _fps: Label
var _flicker_lights: Array[Light3D] = []
var _flicker_base := {}
var _lamp_lights: Array[OmniLight3D] = []
var _noise := FastNoiseLite.new()
var _time := 0.0
var _hud: Label
var _prompt: Label


func _ready() -> void:
	_setup_input()
	var started := Time.get_ticks_msec()
	house = (load(HOUSE_SCENE) as PackedScene).instantiate()
	add_child(house)
	var stats := _setup_collision()
	_setup_lights()
	_setup_environment()
	_setup_hud()
	_spawn_player()
	_load_quality()
	print("house ready in %d ms: %d collision bodies, %d doors, %d lights" % [
		Time.get_ticks_msec() - started, stats, _doors.size(), _lamp_lights.size() + 2])

	var args := OS.get_cmdline_user_args()
	if "--shots" in args:
		await _take_screenshots(args)
	elif "--selftest" in args:
		await _self_test()
	else:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


# --- Input ------------------------------------------------------------------

func _setup_input() -> void:
	var keys := {
		"move_forward": [KEY_W, KEY_UP], "move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
		"jump": [KEY_SPACE], "run": [KEY_SHIFT], "interact": [KEY_E], "toggle_quality": [KEY_F1], "toggle_fps": [KEY_F3],
	}
	for action in keys:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in keys[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact"):
		var door := _nearest_door()
		if door:
			toggle_door(door)
	elif event.is_action_pressed("toggle_fps"):
		_fps.visible = not _fps.visible
	elif event.is_action_pressed("toggle_quality"):
		set_quality("low" if quality == "high" else "high")
		_save_quality()


# --- Collision ---------------------------------------------------------------

func _all_nodes(root: Node) -> Array[Node]:
	var out: Array[Node] = []
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		out.append(node)
		for child in node.get_children():
			stack.append(child)
	return out


func _wants_collision(node_name: String) -> bool:
	if node_name in NO_COLLISION_NAMES:
		return false
	for prefix in NO_COLLISION_PREFIXES:
		if node_name.begins_with(prefix):
			return false
	return true


func _is_door(node_name: String) -> bool:
	return (node_name.begins_with("door_") or node_name.ends_with("_door")) and not node_name.begins_with("frame_")


## Trimesh collision for the shell and the furniture. The stair ramp arrives
## from the importer already a StaticBody3D, made from the "-convcolonly" name.
func _setup_collision() -> int:
	var made := 0
	for node in _all_nodes(house):
		if node is MeshInstance3D:
			var mesh_node := node as MeshInstance3D
			if _is_door(mesh_node.name):
				_doors.append(mesh_node)
				# Every door is modelled shut at zero turn; some are left ajar.
				mesh_node.set_meta("closed_y", 0.0)
				_door_open[mesh_node] = absf(mesh_node.rotation.y) > 0.05
			var n := String(mesh_node.name)
			# Godot shadows a blended surface as if it were solid, so glass, decals and
			# the translucent lampshades cast none. Everything else shadows normally:
			# the shell is closed, and each lamp's base is separate from its shade.
			if n.begins_with("glass_") or n.begins_with("decals_") or n.begins_with("shade_"):
				mesh_node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			if _wants_collision(mesh_node.name) and mesh_node.mesh:
				mesh_node.create_trimesh_collision()
				made += 1
		elif node is StaticBody3D:
			made += 1
	return made


# --- Doors -------------------------------------------------------------------

func _door_swing(door: Node3D) -> float:
	var extras: Variant = door.get_meta("extras", {})
	if extras is Dictionary and extras.has("opens_degrees"):
		return float(extras["opens_degrees"])
	return DOOR_SWING_DEFAULT.get(String(door.name), 90.0)


func _nearest_door() -> Node3D:
	if not player:
		return null
	var best: Node3D = null
	var best_distance := 1.9
	for door in _doors:
		# Measure to the middle of the leaf, not the hinge.
		var centre := door.global_transform * (door as MeshInstance3D).get_aabb().get_center()
		var distance := Vector2(centre.x - player.global_position.x, centre.z - player.global_position.z).length()
		if distance < best_distance and absf(centre.y - (player.global_position.y + 1.0)) < 1.6:
			best_distance = distance
			best = door
	return best


func toggle_door(door: Node3D) -> void:
	# One press always changes the state the player can see. A door counts as
	# open if it stands away from its frame at all, so an ajar door closes.
	var closed: float = door.get_meta("closed_y")
	var is_open := absf(angle_difference(door.rotation.y, closed)) > 0.05
	var target := closed if is_open else closed + deg_to_rad(_door_swing(door))
	_door_open[door] = not is_open
	if _door_tweens.has(door) and is_instance_valid(_door_tweens[door]):
		(_door_tweens[door] as Tween).kill()
	var tween := create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_property(door, "rotation:y", target, 0.9)
	_door_tweens[door] = tween


# --- Lighting ----------------------------------------------------------------

func _setup_lights() -> void:
	for node in _all_nodes(house):
		if node is DirectionalLight3D:
			moon = node
			moon.light_color = MOONLIGHT
			moon.light_energy = 5.5
			moon.light_angular_distance = 0.6
			moon.shadow_enabled = true
			moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
			moon.directional_shadow_max_distance = 26.0
			moon.shadow_bias = 0.04
			moon.shadow_normal_bias = 1.2
			moon.light_volumetric_fog_energy = 2.2
		elif node is OmniLight3D:
			var lamp := node as OmniLight3D
			lamp.light_color = WARM
			lamp.omni_range = 3.8
			lamp.omni_attenuation = 1.6
			lamp.shadow_enabled = true
			lamp.shadow_bias = 0.06
			lamp.light_volumetric_fog_energy = 0.6
			lamp.light_energy = 0.6
			if String(lamp.name).contains("flicker"):
				lamp.light_energy = 0.5
				_add_flicker(lamp)
			_lamp_lights.append(lamp)

	var tv := OmniLight3D.new()
	tv.name = "light_tv_flicker"
	tv.position = TV_POSITION
	tv.light_color = TV_COLOR
	tv.light_energy = 1.6
	tv.omni_range = 4.0
	tv.omni_attenuation = 1.4
	tv.shadow_enabled = true
	tv.light_volumetric_fog_energy = 0.4
	add_child(tv)
	_add_flicker(tv)
	_noise.frequency = 1.0


func _add_flicker(light: Light3D) -> void:
	_flicker_lights.append(light)
	_flicker_base[light] = light.light_energy


func _process(delta: float) -> void:
	_time += delta
	for i in _flicker_lights.size():
		var light := _flicker_lights[i]
		var base: float = _flicker_base[light]
		if String(light.name).begins_with("light_tv"):
			# A television: restless, never dark.
			var n := _noise.get_noise_2d(_time * 7.0, 40.0 + i * 13.0)
			light.light_energy = base * (0.75 + 0.45 * n)
		else:
			# A failing bulb: mostly steady, with dips and the odd near blackout.
			var slow := _noise.get_noise_2d(_time * 1.3, i * 17.0)
			var fast := _noise.get_noise_2d(_time * 22.0, 90.0 + i * 31.0)
			var level := 1.0 - 0.18 * absf(fast)
			if slow > 0.22:
				level *= 0.25 + 0.75 * absf(fast)
			if fast > 0.42 and slow > 0.05:
				level = 0.04
			light.light_energy = base * level
	_update_prompt()
	if _fps and _fps.visible:
		_fps.text = "%d FPS  %.1f ms" % [Engine.get_frames_per_second(), 1000.0 / maxf(Engine.get_frames_per_second(), 1.0)]


# --- Environment ---------------------------------------------------------------

func _setup_environment() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var panorama := PanoramaSkyMaterial.new()
	panorama.panorama = load(SKY_HDR)
	panorama.energy_multiplier = 0.25
	sky.sky_material = panorama
	env.sky = sky
	env.sky_rotation = Vector3(0.0, deg_to_rad(205.0), 0.0)
	env.background_mode = Environment.BG_SKY
	# Cool ambient light rather than the street's sodium orange.
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.16, 0.23, 0.40)
	env.ambient_light_energy = 1.0
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.7
	env.tonemap_white = 6.0
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_bloom = 0.05
	env.adjustment_enabled = true
	env.adjustment_saturation = 0.92
	env.adjustment_contrast = 1.06
	world_env = WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)


## High: volumetric fog, SDFGI, screen-space reflections and occlusion.
## Low: none of those, cheaper shadows and a reduced render scale, aimed at
## integrated graphics such as Intel UHD 620.
func set_quality(level: String) -> void:
	quality = level
	var env := world_env.environment
	var high := level == "high"
	env.volumetric_fog_enabled = high
	env.volumetric_fog_density = 0.022
	env.volumetric_fog_albedo = Color(0.72, 0.80, 1.0)
	env.volumetric_fog_emission = Color(0.010, 0.016, 0.030)
	env.volumetric_fog_anisotropy = 0.45
	env.volumetric_fog_length = 22.0
	env.volumetric_fog_gi_inject = 0.6
	env.sdfgi_enabled = high
	env.sdfgi_use_occlusion = true
	env.sdfgi_cascades = 4
	env.sdfgi_min_cell_size = 0.1
	env.sdfgi_energy = 1.0
	env.ssr_enabled = high
	env.ssao_enabled = high
	env.ssil_enabled = high
	env.glow_enabled = high
	# Low keeps a little distance fog so the rooms do not go flat.
	env.fog_enabled = not high
	env.fog_light_color = Color(0.05, 0.08, 0.14)
	env.fog_density = 0.018
	env.ambient_light_energy = 1.0 if high else 1.6

	var viewport := get_viewport()
	viewport.scaling_3d_scale = 1.0 if high else 0.6
	viewport.msaa_3d = Viewport.MSAA_2X if high else Viewport.MSAA_DISABLED
	viewport.positional_shadow_atlas_size = 4096 if high else 1024
	RenderingServer.directional_shadow_atlas_set_size(4096 if high else 1024, true)
	if moon:
		moon.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS if high \
			else DirectionalLight3D.SHADOW_ORTHOGONAL
	for lamp in _lamp_lights:
		# On Low only the lamps the player walks past keep shadows.
		lamp.shadow_enabled = high or String(lamp.name).contains("hall_table")
	if _hud:
		_hud.text = "WASD move   Shift run   Space jump   Mouse look   E door   F1 quality: %s   F3 FPS   Esc free mouse" \
			% level.capitalize()


func _load_quality() -> void:
	var config := ConfigFile.new()
	var level := "high"
	if config.load(SETTINGS_FILE) == OK:
		level = config.get_value("graphics", "quality", "high")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--quality="):
			level = arg.get_slice("=", 1)
	set_quality(level)


func _save_quality() -> void:
	var config := ConfigFile.new()
	config.set_value("graphics", "quality", quality)
	config.save(SETTINGS_FILE)


# --- Player and HUD ----------------------------------------------------------

func _spawn_player() -> void:
	player = CharacterBody3D.new()
	player.set_script(load("res://scripts/player.gd"))
	player.name = "Player"
	add_child(player)
	# Just inside the front door, looking down the hall. Blender (x, y, z) is Godot (x, z, -y).
	player.position = Vector3(1.78, 0.05, -0.95)
	player.rotation.y = 0.0


func _setup_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_hud = Label.new()
	_hud.position = Vector2(16, 12)
	_hud.add_theme_font_size_override("font_size", 14)
	_hud.modulate = Color(1, 1, 1, 0.55)
	layer.add_child(_hud)
	_fps = Label.new()
	_fps.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_fps.position = Vector2(-150, 12)
	_fps.add_theme_font_size_override("font_size", 16)
	_fps.visible = false
	layer.add_child(_fps)
	_prompt = Label.new()
	_prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.position = Vector2(-90, -90)
	_prompt.add_theme_font_size_override("font_size", 20)
	layer.add_child(_prompt)


func _update_prompt() -> void:
	if not _prompt:
		return
	var door := _nearest_door()
	_prompt.text = ("E  %s door" % ("close" if _door_open[door] else "open")) if door else ""


# --- Screenshots and self-test -------------------------------------------------

## `-- --shots [--quality=low]`: render the three hero cameras saved in the
## model and quit. Used to check the scene without anyone at the keyboard.
func _take_screenshots(args: PackedStringArray) -> void:
	_hud.visible = false
	_prompt.visible = false
	player.visible = false
	var out := "res://screenshots"
	for arg in args:
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
	var frames := 48
	for arg in args:
		if arg.begins_with("--frames="):
			frames = int(arg.get_slice("=", 1))
	for node in _all_nodes(house):
		if node is Camera3D and String(node.name).begins_with("cam_hero_"):
			var cam := node as Camera3D
			cam.fov = 72.0
			cam.make_current()
			for i in frames:            # let global illumination and fog settle
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			var image := get_viewport().get_texture().get_image()
			var path := "%s/%s_%s.png" % [out, String(cam.name).trim_prefix("cam_hero_"), quality]
			image.save_png(path)
			print("SHOT ", path, " ", image.get_size())
	get_tree().quit()


## `-- --selftest`: walk the player up the stairs and open the front door,
## with no rendering needed. Prints what happened and quits.
func _self_test() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	var front: Node3D = null
	for door in _doors:
		if String(door.name) == "door_front":
			front = door
	print("TEST front door found: ", front != null, "  nearest at spawn: ",
		_nearest_door().name if _nearest_door() else "none")
	if front:
		var before := front.rotation.y
		toggle_door(front)
		await get_tree().create_timer(1.2).timeout
		print("TEST front door turned %.1f degrees" % rad_to_deg(front.rotation.y - before))

	for door in _doors:
		if String(door.name) == "door_living":
			var was := rad_to_deg(door.rotation.y)
			toggle_door(door)
			await get_tree().create_timer(1.2).timeout
			print("TEST ajar door: %.1f -> %.1f degrees in one press" % [was, rad_to_deg(door.rotation.y)])
			toggle_door(door)
			await get_tree().create_timer(1.2).timeout
			print("TEST then opens to %.1f" % rad_to_deg(door.rotation.y))
	# Settle on the hall floor, then walk to the foot of the stairs and up.
	for i in 30:
		await get_tree().physics_frame
	print("TEST standing on floor: ", player.is_on_floor(), " at y=%.2f" % player.global_position.y)
	player.global_position = Vector3(0.52, 0.05, -1.2)
	player.rotation.y = 0.0
	Input.action_press("move_forward")
	var top := 0.0
	for i in 60 * 9:
		await get_tree().physics_frame
		top = maxf(top, player.global_position.y)
	Input.action_release("move_forward")
	print("TEST after climbing: y=%.2f (first floor is 3.06), position %s, on floor: %s" % [
		player.global_position.y, player.global_position, player.is_on_floor()])
	get_tree().quit()
