class_name LightingPresets
extends Node
## Time of day and weather for free roam, applied on top of what main.gd sets
## up. Four times (03:00, 06:00, 10:00, 17:00) by two weathers (clear, foggy)
## make eight looks, each a LightingPreset resource in res://presets/ that can
## be tuned by hand in the inspector. docs/TIME_WEATHER.md describes them.
##
## main.gd creates this node with LightingPresets.attach(self) and calls
## apply() at the end of set_quality(), so the look survives a quality change.
##
## - A change of time or weather cross-fades over FADE_SECONDS.
## - With the clock running (FREEZE TIME off) one game hour takes two real
##   minutes, and the look is blended between the two nearest times.
## - F4 opens the World menu (time, weather, brightness, graphics, freeze).
##   F2 steps to the next time. F6 is a free camera (scripts/free_camera.gd).
## - Everything is kept in the build's settings file, section [lighting].
##
## "03:00 Foggy" holds exactly the values main.gd and house_lights.gd use by
## themselves; `-- --preset-check` proves it.
##
## Command line: --preset=1000_clear (or --time=10 --weather=clear),
## --brightness=1.2, --clock (start with time running), --preset-check,
## --preset-shots [--views=a,b] [--presets=id,id] [--out=dir] [--frames=n],
## --env=prop:value,... to override Environment properties for experiments.

const TIMES := [3.0, 6.0, 10.0, 17.0]
const TIME_IDS := ["0300", "0600", "1000", "1700"]
const TIME_LABELS := ["03:00", "06:00", "10:00", "17:00"]
const WEATHERS := ["clear", "foggy"]
## Looks from before the matrix, still accepted from old settings files and command lines.
const ALIASES := {"night": "0300_foggy", "foggy_day": "1000_foggy", "dusk": "1700_foggy", "clear_day": "1000_clear"}
const CHECK_LOOK := "0300_foggy"
const SECTION := "lighting"
const BRIGHTNESS_MIN := 0.5
const BRIGHTNESS_MAX := 2.0
const FADE_SECONDS := 4.0
## Real seconds per game hour while the clock runs.
const SECONDS_PER_HOUR := 120.0

## Fixed views for --preset-shots, in Godot axes (Blender x, z, -y).
const SHOT_VIEWS := {
	"hallway": [Vector3(1.20, 1.60, -0.45), Vector3(1.20, 1.35, -7.5)],
	"porch": [Vector3(2.60, 1.45, 6.2), Vector3(1.75, 1.0, 0.0)],
	"living_room": [Vector3(3.05, 1.55, -0.55), Vector3(6.6, 1.1, -3.6)],
}

var main: Node
var presets := {}                # "1000_clear" -> LightingPreset
var time_hours := 3.0
var weather := "foggy"
var frozen := true
var brightness := 1.0
## True in a world that is mostly outdoors (the town sets it): the presets'
## Outdoors values are used, and SDFGI reads no sky light.
var outdoor := false
var free_camera: Camera3D

var _model_key_basis := Basis.IDENTITY
var _lamp_base := {}            # Light3D -> energy it had before any preset
var _emissive_base := {}        # BaseMaterial3D -> emission multiplier before any preset
var _shown: LightingPreset      # what is on screen now (a preset, or a blend of two)
var _shown_basis := Basis.IDENTITY
var _fade_from: LightingPreset
var _fade_from_basis := Basis.IDENTITY
var _fade := 1.0                # 0..1; 1 = no cross-fade running
var _clock_tick := 0.0
var _sky: Sky
var _toast: Label
var _toast_time := 0.0
var _panel: PanelContainer
var _time_buttons: Array[Button] = []
var _weather_buttons: Array[Button] = []
var _quality_buttons: Array[Button] = []
var _freeze: CheckBox
var _clock_label: Label
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
	for t in TIME_IDS:
		for w in WEATHERS:
			presets["%s_%s" % [t, w]] = load("res://presets/%s_%s.tres" % [t, w])
	_setup_input()
	_capture_base()
	outdoor = not get_tree().get_nodes_in_group("outdoor_world").is_empty()
	_set_look_id(BuildFlavor.default_preset())
	_load_settings()
	_build_ui()
	var check := "--preset-check" in OS.get_cmdline_user_args()
	var before := _snapshot() if check else {}
	if check:
		_set_look_id(CHECK_LOOK)
		frozen = true
		brightness = 1.0
	_show_target()
	print("look: %s, quality %s, brightness %d%%, %s build, clock %s" % [
		look_id(), main.quality, roundi(brightness * 100.0), BuildFlavor.name(), "frozen" if frozen else "running"])
	if check:
		_report_check(before, _snapshot())
	if "--preset-shots" in OS.get_cmdline_user_args():
		_preset_shots.call_deferred()
	elif "--look-selftest" in OS.get_cmdline_user_args():
		_look_selftest.call_deferred()


## `-- --look-selftest`: fade through all eight looks, run the clock, toggle the
## free camera and the menu. Prints TEST lines and quits; needs no rendering.
func _look_selftest() -> void:
	var ok := true
	for tid in TIME_IDS:
		for w in WEATHERS:
			var id := "%s_%s" % [tid, w]
			set_weather(w, false)
			set_time(TIMES[TIME_IDS.find(tid)], false)
			var mid_fade := false
			var deadline := Time.get_ticks_msec() + int(FADE_SECONDS * 1000.0) + 3000
			while Time.get_ticks_msec() < deadline:
				await get_tree().process_frame
				if _fade > 0.3 and _fade < 0.7:
					mid_fade = true
				if _fade >= 1.0:
					break
			var want: LightingPreset = presets[id]
			var key: DirectionalLight3D = main.moon
			var energy := want.outdoor_key_energy if outdoor else want.key_energy
			var good := _shown == want and is_equal_approx(key.light_energy, energy) and mid_fade
			ok = ok and good
			print("TEST look %s: reached %s, faded %s, key %.2f, street lights %s, lamps x%.1f" % [
				id, _shown == want, mid_fade, key.light_energy, "on" if want.street_lights_on else "off", want.lamp_energy_scale])
	var start := time_hours
	set_frozen(false, false)
	await get_tree().create_timer(2.0).timeout
	set_frozen(true, false)
	print("TEST clock: %.3f -> %.3f game hours in 2 seconds (running %s), now %s" % [start, time_hours, time_hours > start, clock_text()])
	toggle_free_camera()
	await get_tree().process_frame
	var flying := free_camera != null and get_viewport().get_camera_3d() == free_camera
	toggle_free_camera()
	await get_tree().process_frame
	await get_tree().process_frame
	var back := free_camera == null and get_viewport().get_camera_3d() != null
	print("TEST free camera: on %s, back to the player %s" % [flying, back])
	toggle_panel()
	var open := _panel.visible
	toggle_panel()
	print("TEST world menu: opens %s, closes %s" % [open, not _panel.visible])
	print("TEST look-selftest passed: ", ok and time_hours > start and flying and back and open)
	get_tree().quit()


# --- The look -------------------------------------------------------------------

## The id of the nearest time in the current weather, e.g. "1000_clear".
func look_id() -> String:
	return "%s_%s" % [TIME_IDS[_nearest_time()], weather]


func _nearest_time() -> int:
	var best := 0
	var best_d := 99.0
	for i in TIMES.size():
		var d := absf(fposmod(time_hours - TIMES[i] + 12.0, 24.0) - 12.0)
		if d < best_d:
			best_d = d
			best = i
	return best


func _set_look_id(id: String) -> bool:
	id = ALIASES.get(id, id)
	if not presets.has(id):
		push_warning("unknown look '%s'" % id)
		return false
	time_hours = TIMES[TIME_IDS.find(id.get_slice("_", 0))]
	weather = id.get_slice("_", 1)
	return true


## The look on screen now: one of the eight presets, or a blend while fading
## or while the clock runs. (world.gd reads its fog values from this.)
func preset() -> LightingPreset:
	return _shown if _shown else presets[look_id()]


func _basis_of(p: LightingPreset) -> Basis:
	return _model_key_basis if p.use_model_angle else p.key_basis()


## The look for the current clock time and weather: one of the eight presets
## exactly on the hour, a blend of the two nearest in between.
func _target() -> Array:
	var n := TIMES.size()
	for i in n:
		var t0: float = TIMES[i]
		var t1: float = TIMES[(i + 1) % n]
		var span := fposmod(t1 - t0, 24.0)
		var into := fposmod(time_hours - t0, 24.0)
		if into < span:
			var a: LightingPreset = presets["%s_%s" % [TIME_IDS[i], weather]]
			if into < 0.0005:
				return [a, _basis_of(a)]
			var b: LightingPreset = presets["%s_%s" % [TIME_IDS[(i + 1) % n], weather]]
			return _mix(a, _basis_of(a), b, _basis_of(b), into / span)
	var p: LightingPreset = presets[look_id()]
	return [p, _basis_of(p)]


## Blend two looks. Numbers and colours are interpolated; lights fade by
## energy instead of popping; the key light turns the short way between its
## two directions.
func _mix(a: LightingPreset, basis_a: Basis, b: LightingPreset, basis_b: Basis, f: float) -> Array:
	var m := LightingPreset.new()
	for info in a.get_property_list():
		if not (info["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE):
			continue
		var prop: String = info["name"]
		var va = a.get(prop)
		var vb = b.get(prop)
		if va is float or va is int:
			m.set(prop, lerpf(va, vb, f))
		elif va is Color:
			m.set(prop, (va as Color).lerp(vb, f))
		else:
			m.set(prop, va if f < 0.5 else vb)
	# A gradient sky stays on while either side has one (a flat sky has both colours equal).
	m.sky_gradient = a.sky_gradient or b.sky_gradient
	m.key_shadows = a.key_shadows or b.key_shadows
	# Lamps that are off count as zero energy, so switching is a fade.
	m.street_energy_scale = lerpf(a.street_energy_scale if a.street_lights_on else 0.0,
		b.street_energy_scale if b.street_lights_on else 0.0, f)
	m.street_lights_on = m.street_energy_scale > 0.002
	m.porch_energy_scale = lerpf(a.porch_energy_scale if a.porch_lights_on else 0.0,
		b.porch_energy_scale if b.porch_lights_on else 0.0, f)
	m.porch_lights_on = m.porch_energy_scale > 0.002
	m.display_name = b.display_name if f >= 0.5 else a.display_name
	var q := Quaternion(basis_a.orthonormalized()).slerp(Quaternion(basis_b.orthonormalized()), f)
	return [m, Basis(q)]


func _show_target() -> void:
	var t := _target()
	_shown = t[0]
	_shown_basis = t[1]
	_fade = 1.0
	_push(_shown, _shown_basis)


func _start_fade() -> void:
	if not _shown:
		_show_target()
		return
	_fade_from = _shown
	_fade_from_basis = _shown_basis
	_fade = 0.0


## Jump to one of the four times (cross-faded).
func set_time(hours: float, save := true) -> void:
	_start_fade()
	time_hours = fposmod(hours, 24.0)
	_toast_look()
	_sync_ui()
	if save:
		_save_settings()


func set_weather(w: String, save := true) -> void:
	if not w in WEATHERS:
		return
	_start_fade()
	weather = w
	_toast_look()
	_sync_ui()
	if save:
		_save_settings()


func set_frozen(value: bool, save := true) -> void:
	frozen = value
	_sync_ui()
	if save:
		_save_settings()


## Show one of the eight looks at once, with no fade (screenshots, checks).
func set_preset(id: String, save := true) -> void:
	if not _set_look_id(id):
		return
	_show_target()
	_sync_ui()
	if save:
		_save_settings()


func set_brightness(value: float, save := true) -> void:
	brightness = clampf(value, BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	apply()
	if save:
		_save_settings()


func next_time() -> void:
	set_time(TIMES[(_nearest_time() + 1) % TIMES.size()])


## Re-apply what is showing. main.gd calls this after a quality change.
func apply() -> void:
	if _shown:
		_push(_shown, _shown_basis)


func clock_text() -> String:
	var minutes := int(round(time_hours * 60.0)) % 1440
	return "%02d:%02d" % [minutes / 60, minutes % 60]


func _process(delta: float) -> void:
	if _toast_time > 0.0:
		_toast_time -= delta
		_toast.modulate.a = clampf(_toast_time / 0.5, 0.0, 1.0)
	if not _shown:
		return
	var running := not frozen
	if running:
		time_hours = fposmod(time_hours + delta / SECONDS_PER_HOUR, 24.0)
	if _fade < 1.0:
		_fade = minf(1.0, _fade + delta / FADE_SECONDS)
		var t := _target()
		if _fade >= 1.0:
			_shown = t[0]
			_shown_basis = t[1]
		else:
			var mixed := _mix(_fade_from, _fade_from_basis, t[0], t[1], smoothstep(0.0, 1.0, _fade))
			_shown = mixed[0]
			_shown_basis = mixed[1]
		_push(_shown, _shown_basis)
	elif running:
		_clock_tick -= delta
		if _clock_tick <= 0.0:
			_clock_tick = 0.1
			var t := _target()
			_shown = t[0]
			_shown_basis = t[1]
			_push(_shown, _shown_basis)
			if _clock_label and _panel.visible:
				_clock_label.text = clock_text()
			if fmod(time_hours * 60.0, 60.0) < 0.06:
				_save_settings()


## Push a look into the environment, the key light, the lamps, the probes and
## the glowing materials. Safe to call any number of times.
func _push(p: LightingPreset, key_basis: Basis) -> void:
	if not main:
		return
	var high: bool = main.quality == "high"
	var env: Environment = main.world_env.environment
	env.background_color = p.background_color
	if p.sky_gradient:
		if not _sky:
			_sky = Sky.new()
			_sky.sky_material = ProceduralSkyMaterial.new()
			_sky.radiance_size = Sky.RADIANCE_SIZE_64
		var sky_mat := _sky.sky_material as ProceduralSkyMaterial
		sky_mat.sky_top_color = p.sky_top_color
		sky_mat.sky_horizon_color = p.sky_horizon_color
		sky_mat.ground_horizon_color = p.sky_horizon_color
		sky_mat.ground_bottom_color = p.sky_horizon_color.darkened(0.4)
		sky_mat.sky_curve = 0.12
		sky_mat.sun_angle_max = 6.0
		env.sky = _sky
		env.background_mode = Environment.BG_SKY
	else:
		env.background_mode = Environment.BG_COLOR
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
	var exposure := (p.outdoor_exposure_high if high else p.outdoor_exposure_low) if outdoor \
		else (p.exposure_high if high else p.exposure_low)
	env.tonemap_exposure = exposure * brightness
	env.tonemap_white = p.tonemap_white
	env.glow_intensity = p.glow_intensity
	env.glow_bloom = p.glow_bloom
	env.adjustment_saturation = p.saturation
	env.adjustment_contrast = p.contrast
	env.sdfgi_energy = p.sdfgi_energy
	env.sdfgi_read_sky_light = p.sdfgi_read_sky_light and not outdoor

	# The key light is the sun by day and the moon at night: always dynamic.
	var key: DirectionalLight3D = main.moon
	if key:
		key.light_color = p.key_color
		key.light_energy = p.outdoor_key_energy if outdoor else p.key_energy
		key.light_angular_distance = p.key_angular_distance
		key.shadow_enabled = p.key_shadows
		key.light_volumetric_fog_energy = p.outdoor_key_volumetric_fog_energy if outdoor else p.key_volumetric_fog_energy
		key.global_basis = key_basis

	var flicker_base: Dictionary = main.get("_flicker_base") if main.get("_flicker_base") != null else {}
	for light in _lamp_base:
		if not is_instance_valid(light):
			continue
		var lname := String(light.name)
		var street := lname.contains("sodium") or lname.begins_with("street_")
		var scale := p.lamp_energy_scale                 # lamps inside the player's house
		if street:
			scale = p.street_energy_scale if p.street_lights_on else 0.0
		elif lname.contains("porch"):
			scale = p.porch_energy_scale if p.porch_lights_on else 0.0
		elif lname.begins_with("lit_window"):
			scale = minf(p.window_glow_scale, 1.0)        # the neighbours' lamps follow their windows
		var energy: float = _lamp_base[light] * scale
		light.light_energy = energy
		light.set_meta("preset_energy", energy)      # for scripts that flicker a light themselves
		light.set_meta("preset_scale", scale)
		if street:
			if outdoor:
				light.light_volumetric_fog_energy = p.outdoor_street_fog_energy
				light.set_meta("preset_halo", p.outdoor_street_halo_low * minf(scale, 1.0))
			light.visible = scale > 0.002 and not light.has_meta("broken")
		if flicker_base.has(light):
			flicker_base[light] = energy     # main.gd flickers around this level

	for probe in _all_of(main, "ReflectionProbe"):
		probe.ambient_color = p.probe_ambient_color
		probe.ambient_color_energy = p.probe_ambient_energy

	for mat in _emissive_base:
		var mname := (mat as Resource).resource_name
		var scale := p.window_glow_scale
		if mname.contains("sodium") or mname.contains("tube_on"):
			scale = p.street_energy_scale if p.street_lights_on else 0.0
		(mat as BaseMaterial3D).emission_energy_multiplier = _emissive_base[mat] * scale

	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--env="):
			for pair in arg.get_slice("=", 1).split(","):
				env.set(pair.get_slice(":", 0), str_to_var(pair.get_slice(":", 1)))

	var hud: Label = main.get("_hud")
	if hud and not hud.text.contains("F2"):
		hud.text += "   F2 time   F4 world   F6 free cam"


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
				if n.contains("sodium") or n.contains("window_lit") or n.contains("tube_on"):
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


# --- The check -------------------------------------------------------------------

## Every value a look touches, for --preset-check.
func _snapshot() -> Dictionary:
	var env: Environment = main.world_env.environment
	var snap := {}
	for prop in ["background_mode", "background_color", "ambient_light_color", "ambient_light_energy", "volumetric_fog_density",
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


## `-- --preset-check`: apply 03:00 Foggy (the old Night) over what main.gd set
## up and list anything that changed. It is meant to change nothing.
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


# --- Settings --------------------------------------------------------------------

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load(BuildFlavor.settings_file()) == OK:
		if config.has_section_key(SECTION, "time"):
			time_hours = fposmod(float(config.get_value(SECTION, "time", time_hours)), 24.0)
			var w := String(config.get_value(SECTION, "weather", weather))
			weather = w if w in WEATHERS else weather
		elif config.has_section_key(SECTION, "preset"):
			_set_look_id(String(config.get_value(SECTION, "preset", "")))      # a file from before the matrix
		frozen = bool(config.get_value(SECTION, "frozen", frozen))
		brightness = clampf(float(config.get_value(SECTION, "brightness", brightness)), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	var args := OS.get_cmdline_user_args()
	for arg in args:
		if arg.begins_with("--preset="):
			_set_look_id(arg.get_slice("=", 1))
			frozen = true
		elif arg.begins_with("--time="):
			time_hours = fposmod(float(arg.get_slice("=", 1)), 24.0)
			frozen = true
		elif arg.begins_with("--weather=") and arg.get_slice("=", 1) in WEATHERS:
			weather = arg.get_slice("=", 1)
		elif arg == "--clock":
			frozen = false
		elif arg.begins_with("--brightness="):
			brightness = clampf(float(arg.get_slice("=", 1)), BRIGHTNESS_MIN, BRIGHTNESS_MAX)
	if "--preset-shots" in args or "--town-perf" in args or "--selftest" in args or "--town-selftest" in args:
		frozen = true              # tests and screenshots never run the clock


## Load what is there first, so the [graphics] section main.gd writes is kept.
func _save_settings() -> void:
	var config := ConfigFile.new()
	config.load(BuildFlavor.settings_file())
	config.set_value(SECTION, "time", snappedf(time_hours, 0.01))
	config.set_value(SECTION, "weather", weather)
	config.set_value(SECTION, "frozen", frozen)
	config.set_value(SECTION, "preset", look_id())
	config.set_value(SECTION, "brightness", snappedf(brightness, 0.01))
	config.save(BuildFlavor.settings_file())


# --- Input and UI ------------------------------------------------------------------

func _setup_input() -> void:
	for pair in [["cycle_preset", KEY_F2], ["settings_panel", KEY_F4], ["free_camera", KEY_F6]]:
		if not InputMap.has_action(pair[0]):
			InputMap.add_action(pair[0])
			var event := InputEventKey.new()
			event.physical_keycode = pair[1]
			InputMap.action_add_event(pair[0], event)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cycle_preset"):
		next_time()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("settings_panel"):
		toggle_panel()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("free_camera"):
		toggle_free_camera()
		get_viewport().set_input_as_handled()


## F6: leave the player where they stand and fly a camera; F6 again goes back.
func toggle_free_camera() -> void:
	var player: Node3D = main.get("player")
	if free_camera:
		free_camera.queue_free()
		free_camera = null
		if player:
			player.set_physics_process(true)
			player.set_process_unhandled_input(true)
			var cam := player.get("camera") as Camera3D
			if cam:
				cam.make_current()
		_show_toast("Back to the player")
		return
	var from := get_viewport().get_camera_3d()
	free_camera = Camera3D.new()
	free_camera.set_script(load("res://scripts/free_camera.gd"))
	free_camera.name = "FreeCamera"
	main.add_child(free_camera)
	if from:
		free_camera.global_transform = from.global_transform
		free_camera.fov = from.fov
	free_camera.make_current()
	if player:
		player.set_physics_process(false)
		player.set_process_unhandled_input(false)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_show_toast("Free camera: WASD, Q/E down/up, Shift fast, wheel speed, F6 back")


func toggle_panel() -> void:
	_panel.visible = not _panel.visible
	if _panel.visible:
		_mouse_before = Input.mouse_mode
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_sync_ui()
	else:
		Input.mouse_mode = _mouse_before


func _toast_look() -> void:
	_show_toast("%s  %s" % [TIME_LABELS[_nearest_time()], weather.capitalize()])


func _sync_ui() -> void:
	if not _panel:
		return
	var nearest := _nearest_time()
	for i in _time_buttons.size():
		_time_buttons[i].set_pressed_no_signal(i == nearest)
	for i in _weather_buttons.size():
		_weather_buttons[i].set_pressed_no_signal(WEATHERS[i] == weather)
	for i in _quality_buttons.size():
		_quality_buttons[i].set_pressed_no_signal(["low", "high"][i] == main.quality)
	_freeze.set_pressed_no_signal(frozen)
	_clock_label.text = clock_text()
	_slider.set_value_no_signal(brightness)
	_value_label.text = "%d%%" % roundi(brightness * 100.0)


func _row(box: VBoxContainer, text: String) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	var label := Label.new()
	label.text = text
	label.custom_minimum_size.x = 96
	row.add_child(label)
	box.add_child(row)
	return row


func _toggle_button(row: HBoxContainer, text: String, pressed: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.toggle_mode = true
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.pressed.connect(pressed)
	row.add_child(b)
	return b


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)

	_toast = Label.new()
	_toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_toast.position = Vector2(-300, 48)
	_toast.size = Vector2(600, 30)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.add_theme_font_size_override("font_size", 20)
	_toast.modulate.a = 0.0
	layer.add_child(_toast)

	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_CENTER)
	_panel.custom_minimum_size = Vector2(430, 0)
	_panel.position = Vector2(-215, -170)
	_panel.visible = false
	layer.add_child(_panel)
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 14)
	_panel.add_child(margin)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	margin.add_child(box)

	var head := HBoxContainer.new()
	var title := Label.new()
	title.text = "World"
	title.add_theme_font_size_override("font_size", 20)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(title)
	_clock_label = Label.new()
	_clock_label.add_theme_font_size_override("font_size", 20)
	head.add_child(_clock_label)
	box.add_child(head)

	var row := _row(box, "Time")
	for i in TIMES.size():
		_time_buttons.append(_toggle_button(row, TIME_LABELS[i], set_time.bind(TIMES[i])))

	row = _row(box, "Weather")
	for w in WEATHERS:
		_weather_buttons.append(_toggle_button(row, w.capitalize(), set_weather.bind(w)))

	row = _row(box, "Clock")
	_freeze = CheckBox.new()
	_freeze.text = "FREEZE TIME   (running: 1 hour = 2 minutes)"
	_freeze.toggled.connect(func(on: bool) -> void: set_frozen(on))
	row.add_child(_freeze)

	row = _row(box, "Brightness")
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
	_slider.value_changed.connect(func(v: float) -> void:
		_value_label.text = "%d%%" % roundi(v * 100.0)
		set_brightness(v))
	row.add_child(_slider)
	row.add_child(_value_label)

	row = _row(box, "Graphics")
	for level in ["low", "high"]:
		_quality_buttons.append(_toggle_button(row, level.capitalize(), func() -> void:
			main.set_quality(level)
			main._save_quality()
			_sync_ui()))

	var hint := Label.new()
	hint.text = "F2 next time    F6 free camera    F1 graphics    F3 FPS"
	hint.modulate = Color(1, 1, 1, 0.6)
	hint.add_theme_font_size_override("font_size", 13)
	box.add_child(hint)

	var close := Button.new()
	close.text = "Close (F4)"
	close.pressed.connect(toggle_panel)
	box.add_child(close)
	_sync_ui()


func _show_toast(text: String) -> void:
	if _toast:
		_toast.text = text
		_toast_time = 2.5


# --- Screenshots ---------------------------------------------------------------------

## `-- --preset-shots [--quality=low] [--out=dir] [--views=a,b] [--presets=1000_clear,...]`:
## render the fixed views in every look and quit. Views can also come from
## cameras named cam_preset_<view> anywhere in the scene.
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
	for tid in TIME_IDS:
		for w in WEATHERS:
			var id := "%s_%s" % [tid, w]
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
