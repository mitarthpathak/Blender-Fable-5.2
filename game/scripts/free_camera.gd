extends Camera3D
## A noclip fly camera for screenshots and for framing film shots. F6 (handled
## in lighting_presets.gd) creates it at the current view and removes it again;
## the player stays where they were.
##
## Mouse looks. W A S D fly, Q down, E up, Shift fast, Ctrl slow, mouse wheel
## changes the speed, + and - change the lens (field of view).

const SENSITIVITY := 0.0025

var speed := 4.0
var _yaw := 0.0
var _pitch := 0.0


func _ready() -> void:
	near = 0.05
	var e := global_transform.basis.get_euler()
	_pitch = e.x
	_yaw = e.y


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_yaw -= event.relative.x * SENSITIVITY
		_pitch = clampf(_pitch - event.relative.y * SENSITIVITY, -1.55, 1.55)
		rotation = Vector3(_pitch, _yaw, 0.0)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			speed = minf(speed * 1.25, 60.0)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			speed = maxf(speed / 1.25, 0.2)
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventKey and event.pressed:
		if event.physical_keycode == KEY_EQUAL or event.physical_keycode == KEY_KP_ADD:
			fov = maxf(fov - 4.0, 12.0)
		elif event.physical_keycode == KEY_MINUS or event.physical_keycode == KEY_KP_SUBTRACT:
			fov = minf(fov + 4.0, 110.0)
		elif event.physical_keycode == KEY_ESCAPE:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _process(delta: float) -> void:
	var move := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W):
		move.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S):
		move.z += 1.0
	if Input.is_physical_key_pressed(KEY_A):
		move.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D):
		move.x += 1.0
	if Input.is_physical_key_pressed(KEY_E):
		move.y += 1.0
	if Input.is_physical_key_pressed(KEY_Q):
		move.y -= 1.0
	if move == Vector3.ZERO:
		return
	var rate := speed
	if Input.is_physical_key_pressed(KEY_SHIFT):
		rate *= 4.0
	if Input.is_physical_key_pressed(KEY_CTRL):
		rate *= 0.25
	global_position += global_transform.basis * move.normalized() * rate * delta
