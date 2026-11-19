extends CharacterBody3D
## Third-person test player: a capsule, with the camera on a spring arm so it
## pulls in instead of clipping through walls in the narrow hallway.
##
## If the Mixamo character files are in res://assets/character/ the capsule is
## replaced by the animated human holding the rifle (scripts/character.gd):
## hold the right mouse button to aim, click the left to fire. Without those
## files nothing changes.
##
## V switches between this over-the-shoulder camera and first person: the
## camera at the character's eyes (its head hidden), the body always facing
## where the camera looks, the spine following the camera up and down, a dot
## in the middle of the screen, and a closer view while aiming.

const WALK_SPEED := CharacterRig.WALK_SPEED      # matched to the character's walk and run clips
const RUN_SPEED := CharacterRig.RUN_SPEED
const JUMP_VELOCITY := 2.9                        # about 0.6 s in the air: as long as the jump clip's flight
const MOUSE_SENSITIVITY := 0.0025
const ACCELERATION := 12.0
const ARM_LENGTH := 1.9
const ARM_LENGTH_AIMING := 1.15
const SHOULDER := Vector3(0.32, 0.0, 0.0)          # the third-person camera, over the right shoulder
const PIVOT_HEIGHT := 1.5
const FOV_THIRD := 72.0
const FOV_FIRST := 75.0
const FOV_FIRST_AIMING := 58.0
const EYE_HEIGHT := 1.62                           # first person without the character (the capsule)
const EYE_SMOOTHING := 14.0                        # the first-person camera follows the eyes, less their bob
## First person with the rifle: the camera rides with the sight, so the
## weapon sits steady in the view. Aiming, the eye is on the line of sight
## this far behind the reticle dot; at the ready it is further back, above
## and to the left, which puts the rifle low on the right of the screen.
const EYE_RELIEF := 0.085
const READY_BACK := 0.20
const READY_UP := 0.075
const READY_LEFT := 0.075

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _pivot: Node3D
var _arm: SpringArm3D
var _body_mesh: MeshInstance3D
var camera: Camera3D
var flashlight: SpotLight3D
var rig: CharacterRig            # null while the player is a capsule
var force_aim := false           # tools and tests: aim as if the right mouse button were held
var first_person := false        # V: the camera at the eyes instead of over the shoulder

var _eye := Vector3(0.0, EYE_HEIGHT, 0.0)   # first-person camera, relative to the player (world axes)
var _crosshair: Control
var _ads := 0.0                  # first person: 0 at the ready, 1 looking through the sight


func _ready() -> void:
	floor_max_angle = deg_to_rad(46.0)      # the stair ramp is 31 degrees
	floor_snap_length = 0.35                # stay on the ramp going down
	collision_layer = 2
	collision_mask = 1

	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.28
	capsule.height = 1.75
	shape.shape = capsule
	shape.position.y = 0.875
	add_child(shape)

	_body_mesh = MeshInstance3D.new()
	var mesh := CapsuleMesh.new()
	mesh.radius = 0.28
	mesh.height = 1.75
	_body_mesh.mesh = mesh
	_body_mesh.position.y = 0.875
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.22, 0.25, 0.24)
	mat.roughness = 0.8
	_body_mesh.material_override = mat
	add_child(_body_mesh)

	rig = CharacterRig.create()
	if rig:
		add_child(rig)
		_body_mesh.visible = false

	_pivot = Node3D.new()
	_pivot.position = Vector3(0.0, 1.5, 0.0)
	# The body moves in physics steps and is drawn in between them (physics
	# interpolation, project.godot), so walking looks even at any frame rate.
	# The mouse turns the camera between steps: that must show at once, not be
	# smoothed over a step, so the pivot (and the arm and camera on it) are
	# not interpolated themselves; they ride on the body's drawn position.
	_pivot.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(_pivot)

	_arm = SpringArm3D.new()
	_arm.spring_length = ARM_LENGTH
	_arm.margin = 0.12
	_arm.collision_mask = 1
	_arm.position = SHOULDER
	var probe := SphereShape3D.new()
	probe.radius = 0.14
	_arm.shape = probe
	_arm.add_excluded_object(get_rid())
	_pivot.add_child(_arm)

	camera = Camera3D.new()
	camera.fov = FOV_THIRD
	camera.near = 0.05
	_arm.add_child(camera)
	camera.make_current()

	# Flashlight: off for now. It will be the player's main light later.
	flashlight = SpotLight3D.new()
	flashlight.name = "Flashlight"
	flashlight.light_color = Color(1.0, 0.96, 0.88)
	flashlight.light_energy = 6.0
	flashlight.spot_range = 18.0
	flashlight.spot_angle = 24.0
	flashlight.spot_angle_attenuation = 0.7
	flashlight.shadow_enabled = true
	flashlight.light_volumetric_fog_energy = 1.5
	flashlight.visible = false
	camera.add_child(flashlight)

	# First person: a small dot in the middle of the screen.
	var layer := CanvasLayer.new()
	add_child(layer)
	_crosshair = Control.new()
	_crosshair.set_anchors_preset(Control.PRESET_CENTER)
	_crosshair.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_crosshair)
	for ring in [[6.0, Color(0, 0, 0, 0.5)], [4.0, Color(0.95, 0.95, 0.9, 0.9)]]:
		var dot := ColorRect.new()
		dot.size = Vector2(ring[0], ring[0])
		dot.position = -dot.size / 2.0
		dot.color = ring[1]
		dot.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_crosshair.add_child(dot)
	_crosshair.visible = false


## First person (true) or over the shoulder (false).
func set_first_person(on: bool) -> void:
	first_person = on
	if rig:
		rig.first_person = on
		# In first person the body turns with the view at once, like the camera
		# (see _ready), or the rifle would sway against the view while turning.
		rig.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF if on \
			else Node.PHYSICS_INTERPOLATION_MODE_INHERIT
	else:
		_body_mesh.visible = not on
	_arm.position = Vector3.ZERO if on else SHOULDER
	_arm.spring_length = 0.0 if on else ARM_LENGTH
	camera.near = 0.03 if on else 0.05
	camera.fov = FOV_FIRST if on else FOV_THIRD
	if on:
		_eye = _eye_target()
		_pivot.global_position = global_position + _eye
	else:
		_pivot.position = Vector3(0.0, PIVOT_HEIGHT, 0.0)
	_crosshair.visible = on


## Where the first-person camera wants to be, relative to the player: with
## the rifle, from its sight (see READY_*); without one, at the eyes.
func _eye_target() -> Vector3:
	if rig == null:
		return Vector3(0.0, EYE_HEIGHT, 0.0)
	if rig.rifle == null:
		return rig.eye_position() - global_position
	var view := camera.global_transform.basis.orthonormalized()
	var at_ready: Vector3 = view * Vector3(-READY_LEFT, READY_UP, READY_BACK)
	var aimed: Vector3 = view * Vector3(0.0, 0.0, EYE_RELIEF)
	return rig.reticle_position() + at_ready.lerp(aimed, _ads) - global_position


## Turn the player to `yaw`, with the camera behind it and the body facing the
## same way. Movement follows the camera (pivot) as well as the body, so a
## script that wants "W walks towards yaw" must reset both: the self-tests
## and the screenshot tools call this instead of setting rotation.y.
func face(yaw: float) -> void:
	rotation.y = yaw
	_pivot.rotation = Vector3.ZERO
	if rig:
		rig.rotation.y = 0.0
		rig.aim_yaw = 0.0


## Orbit the camera by `yaw` around the player, as the mouse does. Tools use it.
func turn_camera(yaw: float) -> void:
	_pivot.rotation.y += yaw


## Where the camera looks, as a world yaw (0 is -Z).
func view_yaw() -> float:
	return rotation.y + _pivot.rotation.y


## Where the body faces, as a world yaw: the rig's if there is one.
func body_yaw() -> float:
	return rotation.y + (rig.rotation.y if rig else 0.0)


## How far the spring arm let the camera out, against the length it wants.
func arm_lengths() -> Vector2:
	return Vector2(_arm.get_hit_length(), _arm.spring_length)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		# The camera orbits on its own; the body only turns when it moves or aims
		# (scripts/character.gd), as in a third-person action game.
		_pivot.rotation.y -= event.relative.x * MOUSE_SENSITIVITY
		_pivot.rotation.x = clampf(_pivot.rotation.x - event.relative.y * MOUSE_SENSITIVITY, -1.2, 0.9)
	elif event is InputEventMouseButton and event.pressed:
		if rig and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and event.button_index == MOUSE_BUTTON_LEFT:
			rig.fire()
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed("toggle_view"):
		set_first_person(not first_person)
	elif event.is_action_pressed("flashlight"):
		flashlight.visible = not flashlight.visible
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	elif Input.is_action_just_pressed("jump"):
		velocity.y = JUMP_VELOCITY
		if rig:
			rig.jump()

	# Movement is relative to where the camera looks: W+A goes forward and to
	# the left of the view, diagonally, whatever way the body is facing.
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var view := Basis(Vector3.UP, view_yaw())
	var direction := (view * Vector3(input.x, 0.0, input.y)).normalized()
	var speed := RUN_SPEED if Input.is_action_pressed("run") else WALK_SPEED
	var target := direction * speed
	velocity.x = move_toward(velocity.x, target.x, ACCELERATION * delta)
	velocity.z = move_toward(velocity.z, target.z, ACCELERATION * delta)
	move_and_slide()

	var aiming := force_aim or (Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT) and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED)
	if rig:
		rig.aiming = aiming
		rig.aim_yaw = _pivot.rotation.y
		rig.look_pitch = _pivot.rotation.x
		rig.update(velocity, is_on_floor(), delta)
	if first_person:
		# Follow the eyes: their sway with each step is smoothed out, the
		# player's own movement is not (the offset is relative to the player).
		_ads = move_toward(_ads, 1.0 if aiming else 0.0, delta * 5.0)
		_eye = _eye.lerp(_eye_target(), clampf(delta * EYE_SMOOTHING, 0.0, 1.0))
		_pivot.global_position = global_position + _eye
		camera.fov = move_toward(camera.fov, FOV_FIRST_AIMING if aiming else FOV_FIRST, delta * 90.0)
		_crosshair.visible = not aiming
	elif rig:
		var length := ARM_LENGTH_AIMING if rig.aiming else ARM_LENGTH
		_arm.spring_length = move_toward(_arm.spring_length, length, delta * 4.0)
