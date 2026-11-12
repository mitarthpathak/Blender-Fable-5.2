extends CharacterBody3D
## Third-person test player: a capsule, with the camera on a spring arm so it
## pulls in instead of clipping through walls in the narrow hallway.
##
## If the Mixamo character files are in res://assets/character/ the capsule is
## replaced by the animated human holding the rifle (scripts/character.gd):
## hold the right mouse button to aim, click the left to fire. Without those
## files nothing changes.

const WALK_SPEED := 2.6
const RUN_SPEED := 4.6
const JUMP_VELOCITY := 3.6
const MOUSE_SENSITIVITY := 0.0025
const ACCELERATION := 12.0
const ARM_LENGTH := 1.9
const ARM_LENGTH_AIMING := 1.15

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _pivot: Node3D
var _arm: SpringArm3D
var _body_mesh: MeshInstance3D
var camera: Camera3D
var flashlight: SpotLight3D
var rig: CharacterRig            # null while the player is a capsule


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
	add_child(_pivot)

	_arm = SpringArm3D.new()
	_arm.spring_length = ARM_LENGTH
	_arm.margin = 0.12
	_arm.collision_mask = 1
	_arm.position = Vector3(0.32, 0.0, 0.0)   # over the right shoulder
	var probe := SphereShape3D.new()
	probe.radius = 0.14
	_arm.shape = probe
	_arm.add_excluded_object(get_rid())
	_pivot.add_child(_arm)

	camera = Camera3D.new()
	camera.fov = 72.0
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


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * MOUSE_SENSITIVITY)
		_pivot.rotation.x = clampf(_pivot.rotation.x - event.relative.y * MOUSE_SENSITIVITY, -1.2, 0.9)
	elif event is InputEventMouseButton and event.pressed:
		if rig and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and event.button_index == MOUSE_BUTTON_LEFT:
			rig.fire()
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
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

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction := (transform.basis * Vector3(input.x, 0.0, input.y)).normalized()
	var speed := RUN_SPEED if Input.is_action_pressed("run") else WALK_SPEED
	var target := direction * speed
	velocity.x = move_toward(velocity.x, target.x, ACCELERATION * delta)
	velocity.z = move_toward(velocity.z, target.z, ACCELERATION * delta)
	move_and_slide()

	if rig:
		rig.aiming = Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT) and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
		rig.update(velocity, is_on_floor(), delta)
		var length := ARM_LENGTH_AIMING if rig.aiming else ARM_LENGTH
		_arm.spring_length = move_toward(_arm.spring_length, length, delta * 4.0)
