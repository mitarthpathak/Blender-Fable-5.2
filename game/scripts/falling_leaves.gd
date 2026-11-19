class_name FallingLeaves
extends GPUParticles3D
## Dry leaves drifting down round the camera, a few at a time: the town has
## no wind (docs/ART_BIBLE.md), so they fall slowly and flutter, spinning,
## and never blow along. The emitter follows the active camera; the leaves,
## once let go, stay where they are in the world.
##
## Uses the town's leaf_sheet atlas (2 x 2 leaves), one leaf picked at random
## for each particle. Fewer on Low (set_quality).

const LIFETIME := 13.0
const AREA := 16.0                 # half the width of the box they start in, metres
const HEIGHT_ABOVE := 9.0          # how far above the camera they start

var _count_high := 150
var _count_low := 70


func _ready() -> void:
	lifetime = LIFETIME
	preprocess = LIFETIME              # the air is already full of them on the first frame
	amount = _count_high
	local_coords = false
	visibility_aabb = AABB(Vector3(-AREA * 2.0, -40.0, -AREA * 2.0), Vector3(AREA * 4.0, 60.0, AREA * 4.0))
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(AREA, 1.5, AREA)
	process.direction = Vector3(0.0, -1.0, 0.0)
	process.spread = 25.0
	process.gravity = Vector3.ZERO     # no acceleration: a leaf falls at its own slow, steady speed
	process.initial_velocity_min = 0.55
	process.initial_velocity_max = 0.95
	process.turbulence_enabled = true  # the flutter
	process.turbulence_noise_strength = 0.8
	process.turbulence_noise_scale = 3.0
	process.turbulence_influence_min = 0.05
	process.turbulence_influence_max = 0.14
	process.angle_min = -180.0
	process.angle_max = 180.0
	process.angular_velocity_min = -110.0
	process.angular_velocity_max = 110.0
	process.scale_min = 0.1
	process.scale_max = 0.17
	process.anim_offset_min = 0.0      # which of the four leaves
	process.anim_offset_max = 1.0
	var shrink := Curve.new()          # gone at the end of their life (by then under the ground anyway)
	shrink.add_point(Vector2(0.0, 1.0))
	shrink.add_point(Vector2(0.85, 1.0))
	shrink.add_point(Vector2(1.0, 0.0))
	var shrink_tex := CurveTexture.new()
	shrink_tex.curve = shrink
	process.scale_curve = shrink_tex
	process_material = process

	var mat := StandardMaterial3D.new()
	mat.albedo_texture = load("res://assets/town/textures/leaf_sheet.png")
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	mat.alpha_scissor_threshold = 0.5
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.billboard_keep_scale = true
	mat.particles_anim_h_frames = 2
	mat.particles_anim_v_frames = 2
	mat.particles_anim_loop = false
	mat.roughness = 0.85
	mat.albedo_color = Color(0.8, 0.72, 0.62)      # damp, and in shade most of the way down
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0, 1.0)
	quad.material = mat
	draw_pass_1 = quad


func set_quality(high: bool) -> void:
	amount = _count_high if high else _count_low


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam:
		global_position = cam.global_position + Vector3(0.0, HEIGHT_ABOVE, 0.0)
