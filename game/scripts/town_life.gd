class_name TownLife
extends Node3D
## Small life in the town, for the town world (scripts/town.gd adds it):
##
## - moths round every street light that is on: a few pale specks that dart
##   about under the lamp head, and fade with the light (and its flicker);
## - on clear days, a loose flock of crows circling over the junction,
##   flapping and gliding; gone at night and in fog.
##
## Both are cheap: one small particle system per lit lamp, seen only within
## MOTH_RANGE, and nine small meshes for the crows.

const MOTH_COUNT := 12
const MOTH_RANGE := 35.0
const CROWS := 9
const CROW_CENTRE := Vector3(4.0, 0.0, 24.0)    # over the junction of Ashgrove and Mill Road

var _moths := {}                  # OmniLight3D -> GPUParticles3D
var _crows: Node3D                # one MeshInstance3D per crow (TAA needs each one's motion)
var _crow_material: ShaderMaterial
var _crow_paths: Array = []       # per crow: [radius, height, speed, phase, wobble]
var _time := 0.0


## `lamps`: the street lights (town.gd's list).
func setup(lamps: Array[OmniLight3D]) -> void:
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	for lamp in lamps:
		var p := GPUParticles3D.new()
		p.name = "moths_" + String(lamp.name)
		p.amount = MOTH_COUNT
		p.lifetime = 5.0
		p.preprocess = 5.0
		p.randomness = 0.6
		p.fixed_fps = 30
		p.process_material = _moth_process()
		p.draw_pass_1 = _moth_mesh()      # its own material: each lamp's moths dim with that lamp
		p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		p.visibility_range_end = MOTH_RANGE
		p.visibility_range_end_margin = 4.0
		p.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		p.custom_aabb = AABB(Vector3(-2.0, -2.0, -2.0), Vector3(4.0, 4.0, 4.0))
		p.position = lamp.position + Vector3(0.0, -0.35, 0.0)    # under the lamp head
		p.emitting = false
		p.visible = false
		lamp.get_parent().add_child(p)
		_moths[lamp] = p
	_make_crows()


## Every frame: moths follow their lamp; crows fly while it is day.
## `daylight`: 0 at night, 1 in full day (the preset's sun disc).
func update(delta: float, daylight: float) -> void:
	_time += delta
	for lamp in _moths:
		var p: GPUParticles3D = _moths[lamp]
		var full: float = maxf(lamp.get_meta("preset_energy", 0.0), 0.001)
		var level: float = lamp.light_energy / full if lamp.visible else 0.0
		var on: bool = lamp.visible and lamp.get_meta("preset_scale", 0.0) > 0.3
		if on != p.emitting:
			p.emitting = on
		p.visible = on or p.emitting
		if p.visible:
			# the specks are lit by the lamp: they dim with it and vanish in a blackout
			var m: StandardMaterial3D = (p.draw_pass_1 as QuadMesh).material
			m.albedo_color.a = clampf(level, 0.0, 1.0)
	_fly_crows(daylight)


# --- Moths ---------------------------------------------------------------------

func _moth_mesh() -> QuadMesh:
	var quad := QuadMesh.new()
	quad.size = Vector2(0.035, 0.035)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.albedo_color = Color(1.0, 0.86, 0.62, 1.0)       # pale wings in sodium light
	m.disable_receive_shadows = true
	m.disable_fog = true          # lit by the lamp right there, not seen through the street's fog
	quad.material = m
	return quad


func _moth_process() -> ParticleProcessMaterial:
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.7
	pm.gravity = Vector3.ZERO
	pm.direction = Vector3(0.0, 1.0, 0.0)
	pm.spread = 180.0
	pm.initial_velocity_min = 0.3
	pm.initial_velocity_max = 0.9
	# erratic darting about the light, held near it by the damping
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 6.0
	pm.turbulence_noise_scale = 1.2
	pm.turbulence_noise_speed_random = 1.0
	pm.turbulence_influence_min = 0.35
	pm.turbulence_influence_max = 0.7
	pm.damping_min = 0.6
	pm.damping_max = 1.4
	pm.scale_min = 0.6
	pm.scale_max = 1.3
	return pm


# --- Crows ---------------------------------------------------------------------

func _make_crows() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 6113
	var mesh := _crow_mesh()
	_crows = Node3D.new()
	_crows.name = "Crows"
	_crows.position = CROW_CENTRE
	_crows.visible = false
	add_child(_crows)
	for i in CROWS:
		# radius, height, angular speed (some circle the other way), phase, wobble
		var dir := -1.0 if rng.randf() < 0.3 else 1.0
		_crow_paths.append([rng.randf_range(10.0, 26.0), rng.randf_range(11.0, 19.0),
			dir * rng.randf_range(0.10, 0.18), rng.randf() * TAU, rng.randf() * TAU])
		# Separate nodes, not a multimesh: each gets its own motion vectors, so
		# TAA follows a crow across the sky instead of smearing it away.
		var crow := MeshInstance3D.new()
		crow.name = "crow_%d" % i
		crow.mesh = mesh
		crow.material_override = _crow_material
		crow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		crow.set_instance_shader_parameter("phase", rng.randf() * TAU)
		crow.set_instance_shader_parameter("beats", rng.randf_range(7.0, 10.0))
		_crows.add_child(crow)


## A crow seen from below: a body and two swept wings, about 0.9 m across.
## The wings flap in the shader (the further from the body, the more they move).
func _crow_mesh() -> ArrayMesh:
	var v := PackedVector3Array()
	# body (a thin diamond, nose at -z)
	v.append_array([Vector3(0, 0, -0.26), Vector3(0.05, 0, 0), Vector3(0, 0, 0.22),
		Vector3(0, 0, -0.26), Vector3(0, 0, 0.22), Vector3(-0.05, 0, 0)])
	# tail fan
	v.append_array([Vector3(0, 0, 0.12), Vector3(0.07, 0, 0.32), Vector3(-0.07, 0, 0.32)])
	for s in [1.0, -1.0]:
		# inner wing, then the outer wing with its fingered tip swept back
		v.append_array([Vector3(0.04 * s, 0, -0.06), Vector3(0.24 * s, 0, -0.05), Vector3(0.04 * s, 0, 0.09)])
		v.append_array([Vector3(0.24 * s, 0, -0.05), Vector3(0.24 * s, 0, 0.1), Vector3(0.04 * s, 0, 0.09)])
		v.append_array([Vector3(0.24 * s, 0, -0.05), Vector3(0.46 * s, 0, 0.04), Vector3(0.24 * s, 0, 0.1)])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = v
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_crow_material = ShaderMaterial.new()
	_crow_material.shader = _crow_shader()
	return mesh


func _crow_shader() -> Shader:
	var s := Shader.new()
	s.code = """
shader_type spatial;
render_mode cull_disabled, unshaded, shadows_disabled, fog_disabled;
uniform float flap_time = 0.0;
instance uniform float phase = 0.0;
instance uniform float beats = 8.0;
void vertex() {
	// each crow: its own phase and wingbeat rate; flap in bursts, then glide
	float t = flap_time + phase;
	float burst = smoothstep(-0.2, 0.4, sin(t * 0.35));
	float beat = sin(t * beats) * burst + 0.12 * (1.0 - burst);
	float reach = abs(VERTEX.x);
	VERTEX.y += beat * reach * 0.85;
	VERTEX.x *= 1.0 - 0.15 * abs(beat) * step(0.2, reach);
}
void fragment() {
	ALBEDO = vec3(0.025, 0.025, 0.03);
}
"""
	return s


func _fly_crows(daylight: float) -> void:
	# Clear days only: in fog they would be lost anyway, and they draw without fog
	# (fog_disabled) so they stay black against a hazy sky.
	var show := daylight > 0.5
	_crows.visible = show
	if not show:
		return
	_crow_material.set_shader_parameter("flap_time", _time)
	for i in CROWS:
		var c: Array = _crow_paths[i]
		var a: float = c[3] + _time * c[2]
		var r: float = c[0] * (1.0 + 0.15 * sin(_time * 0.07 + c[4]))
		var h: float = c[1] + 2.5 * sin(_time * 0.11 + c[4])
		var pos := Vector3(cos(a) * r, h, sin(a) * r)
		var ahead := Vector3(cos(a + 0.05 * signf(c[2])) * r, h, sin(a + 0.05 * signf(c[2])) * r)
		var basis := Basis.looking_at(ahead - pos, Vector3.UP)
		# bank into the turn
		basis = basis * Basis(Vector3(0, 0, 1), -0.35 * signf(c[2]))
		(_crows.get_child(i) as Node3D).transform = Transform3D(basis.scaled(Vector3.ONE * 1.25), pos)
