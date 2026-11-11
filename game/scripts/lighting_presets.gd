class_name LightingPresets
extends Node
## Time-of-day / weather presets and a brightness setting, applied on top of
## what main.gd sets up. Each preset is a LightingPreset resource in
## res://presets/; edit the .tres files in the inspector to retune them.
##
## main.gd creates this node with LightingPresets.attach(self) and calls
## apply() at the end of set_quality(), so a preset survives a quality change.
##
## Keys: F2 cycles the presets, F4 opens a small settings panel (preset and
## brightness). Both are kept in user://settings.cfg, section [lighting].
## Command line: --preset=<id> picks one for this run, and --preset-shots
## renders the hallway and the porch in every preset, then quits.

const PRESETS := {
	"night": "res://presets/night.tres",
	"foggy_day": "res://presets/foggy_day.tres",
	"dusk": "res://presets/dusk.tres",
}
const ORDER := ["night", "foggy_day", "dusk"]
const SETTINGS_FILE := "user://settings.cfg"
const SECTION := "lighting"
const BRIGHTNESS_MIN := 0.5
const BRIGHTNESS_MAX := 2.0

## Fixed views for --preset-shots, in Godot axes (Blender x, z, -y).
const SHOT_VIEWS := {
	"hallway": [Vector3(1.20, 1.60, -0.45), Vector3(1.20, 1.35, -7.5)],
	"porch": [Vector3(2.60, 1.45, 6.2), Vector3(1.75, 1.0, 0.0)],
}

var main: Node
var presets := {}
var current := "night"
var brightness := 1.0
## True in a world that is mostly outdoors (the town sets it): SDFGI then reads
## no sky light, whatever the preset says, so the street does not flood with
## the fog colour on High.
var outdoor := false

var _model_key_basis := Basis.IDENTITY
var _lamp_base := {}            # Light3D -> energy it had before any preset
var _emissive_base := {}        # BaseMaterial3D -> emission multiplier before any preset
var _toast: Label
var _toast_time := 0.0
var _panel: PanelContainer
var _option: OptionButton
var _slider: HSlider
var _value_label: Label
var _mouse_before := Input.MOUSE_MODE_CAPTURED


## Create the node under `main_node`, remember the scene's own light levels,
## load the saved choice and apply it.
static func attach(main_node: Node) -> LightingPresets:
	var node := LightingPresets.new()
	node.name = "LightingPresets"
	node.main = main_node
	main_node.add_child(node)
	return node


func _ready() -> void:
	for id in ORDER:
		presets[id] = load(PRESETS[id])
	_setup_input()
	_capture_base()
	outdoor = not get_tree().get_nodes_in_group("outdoor_world").is_empty()
	_load_settings()
	_build_ui()
	var check := "--preset-check" in OS.get_cmdline_user_args()
	var before := _snapshot() if check else {}
	if check:
		current = "night"
		brightness = 1.0
	apply()
	if check:
		_report_check(before, _snapshot())
	if "--preset-shots" in OS.get_cmdline_user_args():
		_preset_shots.call_deferred()


## Every value a preset touches, for --preset-check.
func _snapshot() -> Dictionary:
	var env: Environment = main.world_env.environment
	var snap := {}
	for prop in ["background_color", "ambient_light_color", "ambient_light_energy", "volumetric_fog_density",
			"volumetric_fog_albedo", "volumetric_fog_emission", "volumetric_fog_anisotropy", "volumetric_fog_length",
			"volumetric_fog_gi_inject", "fog_light_color", "fog_density", "fog_sky_affect", "tonemap_exposure",
			"tonemap_white", "glow_intensity", "glow_bloom", "adjustment_saturation", "adjustment_contrast", "sdfgi_energy", "sdfgi_read_sky_light"]:
		snap["env." + prop] = env.get(prop)
	var key: DirectionalLight3D = main.moon
	if key:
		for prop in ["light_color", "light_energy", "light_angular_distance", "shadow_enabled",
				"light_volumetric_fog_energy", "global_basis"]:
			snap["moon." + prop] = key.get(prop)
	for light in _lamp_base:
		snap["lamp.%s.energy" % light.name] = light.light_energy
		snap["lamp.%s.visible" % light.name] = light.visible
	for probe in _all_of(main, "ReflectionProbe"):
		snap["probe.%s" % probe.name] = [probe.ambient_color, probe.ambient_color_energy]
	return snap


## `-- --preset-check`: apply Night over what main.gd set up and list anything
## that changed. Night is meant to change nothing.
func _report_check(before: Dictionary, after: Dictionary) -> void:
	var diffs: PackedStringArray = []
	for k in before:
		var a = before[k]
		var b = after[k]
		var same: bool
		if a is float:
			same = is_equal_approx(a, b)
		elif a is Color:
			# Colour * float in main.gd also scales alpha, which no renderer reads.
			same = Color(a.r, a.g, a.b).is_equal_approx(Color(b.r, b.g, b.b))
		elif a is Basis:
			same = (a as Basis).is_equal_approx(b)
		else:
			same = a == b
		if not same:
			diffs.append("%s: %s -> %s" % [k, a, b])
	print("PRESET CHECK night matches main.gd: %s (%d values compared)" % [diffs.is_empty(), before.size()])
	for d in diffs:
		print("  DIFF ", d)
	get_tree().quit()


# --- Applying ------------------------------------------------------------------

func preset() -> LightingPreset:
	return presets[current]


func set_preset(id: String, save := true) -> void:
	if not presets.has(id):
		push_warning("unknown lighting preset '%s'" % id)
		return
	current = id
	apply()
	_show_toast(preset().display_name)
	if _option:
		_option.select(ORDER.find(id))
	if save:
		_save_settings()


func set_brightness(value: float, save := true) -> void:
	brightness = clampf(value, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	apply()
	if save:
		_save_settings()


func cycle() -> void:
	set_preset(ORDER[(ORDER.find(current) + 1) % ORDER.size()])


## Push the current preset into the environment, the key light, the lamps,
## the probes and the glowing materials. Safe to call any number of times.
func apply() -> void:
	if not main or not presets.has(current):
		return
	var p := preset()
	var high: bool = main.quality == "high"
	var env: Environment = main.world_env.environment
	env.background_color = p.background_color
	env.ambient_light_color = p.ambient_color
	env.ambient_light_energy = p.outdoor_ambient_energy if outdoor else p.ambient_energy
	env.volumetric_fog_density = p.outdoor_volumetric_fog_density if outdoor else p.volumetric_fog_density
	env.volumetric_fog_albedo = p.volumetric_fog_albedo
	env.volumetric_fog_emission = p.outdoor_volumetric_fog_emission if outdoor else p.volumetric_fog_emission
	env.volumetric_fog_anisotropy = p.volumetric_fog_anisotropy
	env.volumetric_fog_length = p.volumetric_fog_length
	env.volumetric_fog_gi_inject = p.volumetric_fog_gi_inject
	env.fog_light_color = p.outdoor_distance_fog_color if outdoor else p.distance_fog_color
	env.fog_density = p.outdoor_distance_fog_density if outdoor else p.distance_fog_density
	env.fog_sky_affect = p.distance_fog_sky_affect
	var exposure := (p.outdoor_exposure_high if high else p.outdoor_exposure_low) if outdoor 		else (p.exposure_high if high else p.exposure_low)
	env.tonemap_exposure = exposure * brightness
	env.tonemap_white = p.tonemap_white
	env.glow_intensity = p.glow_intensity
	env.glow_bloom = p.glow_bloom
	env.adjustment_saturation = p.saturation
	env.adjustment_contrast = p.contrast
	env.sdfgi_energy = p.sdfgi_energy
	env.sdfgi_read_sky_light = p.sdfgi_read_sky_light and not outdoor

	var key: DirectionalLight3D = main.moon
	if key:
		key.light_color = p.key_color
		key.light_energy = p.outdoor_key_energy if outdoor else p.key_energy
		key.light_angular_distance = p.key_angular_distance
		key.shadow_enabled = p.key_shadows
		key.light_volumetric_fog_energy = p.outdoor_key_volumetric_fog_energy if outdoor else p.key_volumetric_fog_energy
		key.global_basis = _model_key_basis if p.use_model_angle else p.key_basis()

	var flicker_base: Dictionary = main.get("_flicker_base") if main.get("_flicker_base") != null else {}
	for light in _lamp_base:
		if not is_instance_valid(light):
			continue
		var street := String(light.name).contains("sodium")
		var scale := p.street_energy_scale if street else p.lamp_energy_scale
		var energy: float = _lamp_base[light] * scale
		light.light_energy = energy
		light.set_meta("preset_energy", energy)      # for scripts that flicker a light themselves
		light.set_meta("preset_scale", (scale if p.street_lights_on else 0.0) if street else scale)
		if street:
			if outdoor:
				light.light_volumetric_fog_energy = p.outdoor_street_fog_energy
			light.visible = p.street_lights_on and not light.has_meta("broken")
		if flicker_base.has(light):
			flicker_base[light] = energy     # main.gd flickers around this level

	for probe in _all_of(main, "ReflectionProbe"):
		probe.ambient_color = p.probe_ambient_color
		probe.ambient_color_energy = p.probe_ambient_energy

	for mat in _emissive_base:
		var mname := (mat as Resource).resource_name
		var scale := p.window_glow_scale
		if mname.contains("sodium"):
			scale = p.street_energy_scale if p.street_lights_on else 0.0
		(mat as BaseMaterial3D).emission_energy_multiplier = _emissive_base[mat] * scale

	# Debugging aid: --env=prop:value,prop:value overrides Environment properties.
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--env="):
			for pair in arg.get_slice("=", 1).split(","):
				env.set(pair.get_slice(":", 0), str_to_var(pair.get_slice(":", 1)))

	var hud: Label = main.get("_hud")
	if hud and not hud.text.contains("F2"):
		hud.text += "   F2 look   F4 settings"


func _capture_base() -> void:
	if main.moon:
		_model_key_basis = (main.moon as Node3D).global_basis
	var flicker_base: Dictionary = main.get("_flicker_base") if main.get("_flicker_base") != null else {}
	for light in _all_of(main, "Light3D"):
		if light is DirectionalLight3D or String(light.name) == "Flashlight":
			continue
		_lamp_base[light] = flicker_base.get(light, light.light_energy)
	for mesh in _all_of(main, "MeshInstance3D"):
		var mi := mesh as MeshInstance3D
		if not mi.mesh:
			continue
		for s in mi.mesh.get_surface_count():
			var mat := mi.get_active_material(s)
			if mat is BaseMaterial3D and (mat as BaseMaterial3D).emission_enabled:
				var n := mat.resource_name
				if n.contains("sodium") or n.contains("window_lit"):
					_emissive_base[mat] = (mat as BaseMaterial3D).emission_energy_multiplier


func _all_of(root: Node, type: String) -> Array[Node]:
	var out: Array[Node] = []
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node.is_class(type):
			out.append(node)
		for child in node.get_children():
			stack.append(child)
	return out


# --- Settings --------------------------------------------------------------------

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load(SETTINGS_FILE) == OK:
		current = config.get_value(SECTION, "preset", current)
		brightness = clampf(float(config.get_value(SECTION, "brightness", brightness)), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--preset="):
			current = arg.get_slice("=", 1)
		elif arg.begins_with("--brightness="):
			brightness = clampf(float(arg.get_slice("=", 1)), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	if not presets.has(current):
		current = "night"


## Load what is there first, so the [graphics] section main.gd writes is kept.
func _save_settings() -> void:
	var config := ConfigFile.new()
	config.load(SETTINGS_FILE)
	config.set_value(SECTION, "preset", current)
	config.set_value(SECTION, "brightness", snappedf(brightness, 0.01))
	config.save(SETTINGS_FILE)


# --- Input and UI ------------------------------------------------------------------

func _setup_input() -> void:
	for pair in [["cycle_preset", KEY_F2], ["settings_panel", KEY_F4]]:
		if not InputMap.has_action(pair[0]):
			InputMap.add_action(pair[0])
			var event := InputEventKey.new()
			event.physical_keycode = pair[1]
			InputMap.action_add_event(pair[0], event)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cycle_preset"):
		cycle()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("settings_panel"):
		toggle_panel()
		get_viewport().set_input_as_handled()


func toggle_panel() -> void:
	_panel.visible = not _panel.visible
	if _panel.visible:
		_mouse_before = Input.mouse_mode
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_option.select(ORDER.find(current))
		_slider.set_value_no_signal(brightness)
		_value_label.text = "%d%%" % roundi(brightness * 100.0)
		_option.grab_focus()
	else:
		Input.mouse_mode = _mouse_before


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)

	_toast = Label.new()
	_toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_toast.position = Vector2(-120, 48)
	_toast.size = Vector2(240, 30)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.add_theme_font_size_override("font_size", 20)
	_toast.modulate.a = 0.0
	layer.add_child(_toast)

	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.custom_minimum_size = Vector2(340, 0)
	_panel.position = Vector2(-170, -90)
	_panel.visible = false
	layer.add_child(_panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 14)
	_panel.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	margin.add_child(box)

	var title := Label.new()
	title.text = "Settings"
	title.add_theme_font_size_override("font_size", 20)
	box.add_child(title)

	var row := HBoxContainer.new()
	var label := Label.new()
	label.text = "Look"
	label.custom_minimum_size.x = 90
	row.add_child(label)
	_option = OptionButton.new()
	_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for id in ORDER:
		_option.add_item((presets[id] as LightingPreset).display_name)
	_option.select(ORDER.find(current))
	_option.item_selected.connect(func(i: int) -> void: set_preset(ORDER[i]))
	row.add_child(_option)
	box.add_child(row)

	row = HBoxContainer.new()
	label = Label.new()
	label.text = "Brightness"
	label.custom_minimum_size.x = 90
	row.add_child(label)
	_slider = HSlider.new()
	_slider.min_value = BRIGHTNESS_MIN
	_slider.max_value = BRIGHTNESS_MAX
	_slider.step = 0.05
	_slider.value = brightness
	_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_value_label = Label.new()
	_value_label.custom_minimum_size.x = 48
	_value_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_value_label.text = "%d%%" % roundi(brightness * 100.0)
	_slider.value_changed.connect(func(v: float) -> void:
		_value_label.text = "%d%%" % roundi(v * 100.0)
		set_brightness(v))
	row.add_child(_slider)
	row.add_child(_value_label)
	box.add_child(row)

	var close := Button.new()
	close.text = "Close (F4)"
	close.pressed.connect(toggle_panel)
	box.add_child(close)


func _show_toast(text: String) -> void:
	if _toast:
		_toast.text = text
		_toast_time = 2.0


func _process(delta: float) -> void:
	if _toast_time > 0.0:
		_toast_time -= delta
		_toast.modulate.a = clampf(_toast_time / 0.5, 0.0, 1.0)


# --- Screenshots ---------------------------------------------------------------------

## `-- --preset-shots [--quality=low] [--out=dir] [--views=a,b] [--presets=night,dusk]`: render the
## fixed views in every preset and quit. Views can also come from cameras
## named cam_preset_<view> anywhere in the scene.
func _preset_shots() -> void:
	var args := OS.get_cmdline_user_args()
	var out := "res://screenshots/presets"
	var frames := 48
	var only: PackedStringArray = []
	var only_presets: PackedStringArray = []
	for arg in args:
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
		elif arg.begins_with("--frames="):
			frames = int(arg.get_slice("=", 1))
		elif arg.begins_with("--views="):
			only = arg.get_slice("=", 1).split(",")
		elif arg.begins_with("--presets="):
			only_presets = arg.get_slice("=", 1).split(",")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out))
	for n in ["_hud", "_prompt", "player"]:
		var item = main.get(n)
		if item:
			item.visible = false
	var views := SHOT_VIEWS.duplicate()
	for cam in _all_of(main, "Camera3D"):
		var cname := String(cam.name)
		if cname.begins_with("cam_preset_"):
			var t := (cam as Node3D).global_transform
			views[cname.trim_prefix("cam_preset_")] = [t.origin, t.origin - t.basis.z]
	var camera := Camera3D.new()
	camera.fov = 72.0
	camera.near = 0.05
	main.add_child(camera)
	camera.make_current()
	var quality: String = main.quality
	for id in ORDER:
		if not only_presets.is_empty() and not id in only_presets:
			continue
		set_preset(id, false)
		_toast.modulate.a = 0.0
		_toast_time = 0.0
		for view in views:
			if not only.is_empty() and not view in only:
				continue
			camera.global_position = views[view][0]
			camera.look_at(views[view][1], Vector3.UP)
			for i in frames:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			var image := get_viewport().get_texture().get_image()
			var path := "%s/%s_%s_%s.png" % [out, view, id, quality]
			image.save_png(path)
			print("SHOT ", path, " ", image.get_size())
	get_tree().quit()
