class_name CharacterRig
extends Node3D
## The animated player character, built from Mixamo files if they are there.
##
## Expected in res://assets/character/ (copied in by tools/import_character.py
## from projects/03-character/mixamo/):
##
##   character.fbx   the rigged human, "With Skin"
##   idle.fbx walk.fbx run.fbx rifle_aim.fbx fire.fbx jump.fbx   "Without Skin"
##   rifle.glb       the carbine
##
## `CharacterRig.create()` returns null when character.fbx or idle.fbx is
## missing, and the player stays a capsule. walk, run, rifle_aim, fire and
## jump are optional: a missing one falls back to idle.
##
## The animation tree:
##
##   locomotion (idle / walk / run by speed) ─┐
##   rifle_aim ───────────── aim_blend (upper body) ── fire (one shot, upper
##   body) ── jump (one shot) ── output

const DIR := "res://assets/character/"
const MODEL := DIR + "character.fbx"
const RIFLE := DIR + "rifle.glb"
## Clip name: does it loop?
const CLIPS := {"idle": true, "walk": true, "run": true, "rifle_aim": true, "fire": false, "jump": false}
const HEIGHT := 1.80
const WALK_SPEED := 1.6          # the player's walk and run (player.gd); the clips are sped up to match
const RUN_SPEED := 4.2
## The ground speed each clip was made for, measured from how fast its planted
## foot slides back (tools/anim_measure.gd). Playing a clip at any other speed
## makes the feet skate, so the clips are played faster or slower to match.
const WALK_CLIP_SPEED := 1.17
const RUN_CLIP_SPEED := 3.28
## The jump clip crouches for most of a second before the feet leave the
## ground; the player jumps the moment the key goes down. Only its airborne
## part is used, from the end of the crouch to the landing, slowed to fit the
## time the player spends in the air.
const JUMP_FROM := 0.84
const JUMP_TO := 1.95
const JUMP_RATE := 0.95
const TURN_RATE := 10.0          # how fast the body turns to face where it is going

## Where the rifle sits in the right hand, in the hand bone's own space and in
## metres. Measured from the character's aiming pose by tools/rifle_fit.gd:
## the pistol grip in the right palm, the fore grip in the left. Run that tool
## again if the character or its clips change.
const RIFLE_BASIS := Basis(Vector3(-0.2758, -0.1736, 0.9454), Vector3(0.9605, -0.0879, 0.2640), Vector3(0.0373, 0.9809, 0.1910))
const RIFLE_OFFSET := Vector3(0.0896, 0.1321, 0.0387)

var model: Node3D
var skeleton: Skeleton3D
var rifle: Node3D
var aiming := false
var aim_yaw := 0.0               # where the camera looks, relative to the player: the body turns to it to aim
var _fire_hold := 0.0            # after a shot from the hip the body faces the target for a moment

var _player: AnimationPlayer
var _tree: AnimationTree
var _aim_amount := 0.0
var _speed := 0.0


static func available() -> bool:
	return ResourceLoader.exists(MODEL) and ResourceLoader.exists(DIR + "idle.fbx")


## The rig, ready to add to the player, or null if the files are not there
## or do not hold what is expected.
static func create() -> CharacterRig:
	if not available():
		return null
	var rig := CharacterRig.new()
	rig.name = "CharacterRig"
	if not rig._build():
		push_warning("CharacterRig: the files in %s could not be used; staying a capsule." % DIR)
		rig.free()
		return null
	return rig


## Call every physics frame with the player's velocity.
func update(velocity: Vector3, on_floor: bool, delta: float) -> void:
	var flat := Vector2(velocity.x, velocity.z).length()
	_speed = lerpf(_speed, flat if on_floor else _speed, clampf(delta * 10.0, 0.0, 1.0))
	_aim_amount = move_toward(_aim_amount, 1.0 if aiming else 0.0, delta * 6.0)
	_tree.set("parameters/locomotion/blend_position", _speed)
	_tree.set("parameters/aim_blend/blend_amount", _aim_amount)
	_tree.set("parameters/loco_rate/scale", _rate(_speed))
	# Not aiming, the body turns to face the way it is moving; aiming, it faces
	# where the camera looks and the legs walk on under it.
	_fire_hold = maxf(_fire_hold - delta, 0.0)
	var facing_target := aiming or _fire_hold > 0.0
	var want := aim_yaw
	if not facing_target and flat > 0.3:
		var body := (get_parent() as Node3D).global_transform.basis if get_parent() is Node3D else Basis.IDENTITY
		var local := body.inverse() * Vector3(velocity.x, 0.0, velocity.z)
		want = atan2(-local.x, -local.z)
	elif not facing_target:
		want = rotation.y
	rotation.y = lerp_angle(rotation.y, want, clampf(delta * TURN_RATE, 0.0, 1.0))


## How fast to play the walk/run blend at a speed, so the feet do not skate:
## the speed over the ground speed of whatever mix of the two clips is playing.
func _rate(speed: float) -> float:
	if speed <= WALK_SPEED:
		return WALK_SPEED / WALK_CLIP_SPEED
	var t := clampf((speed - WALK_SPEED) / (RUN_SPEED - WALK_SPEED), 0.0, 1.0)
	return speed / lerpf(WALK_CLIP_SPEED, RUN_CLIP_SPEED, t)


func fire() -> void:
	_fire_hold = 0.6
	_tree.set("parameters/fire/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func jump() -> void:
	_tree.set("parameters/jump/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


# --- Building ----------------------------------------------------------------

func _build() -> bool:
	var scene := load(MODEL) as PackedScene
	if scene == null:
		return false
	model = scene.instantiate() as Node3D
	if model == null:
		return false
	add_child(model)
	skeleton = _first(model, "Skeleton3D") as Skeleton3D
	if skeleton == null:
		return false
	# Mixamo characters face +Z; the player walks towards -Z.
	model.rotation.y = PI
	_fit_height()

	_player = AnimationPlayer.new()
	_player.name = "Clips"
	model.add_child(_player)
	var library := AnimationLibrary.new()
	for clip in CLIPS:
		var animation := _load_clip(DIR + clip + ".fbx")
		if animation == null:
			continue
		if clip == "jump":
			animation = _trim(animation, JUMP_FROM, JUMP_TO)
		animation.loop_mode = Animation.LOOP_LINEAR if CLIPS[clip] else Animation.LOOP_NONE
		library.add_animation(clip, animation)
	if not library.has_animation("idle"):
		return false
	_player.add_animation_library("", library)
	_build_tree(library)
	_attach_rifle()
	return true


func _first(root: Node, type: String) -> Node:
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var node: Node = stack.pop_back()
		if node.is_class(type):
			return node
		for child in node.get_children():
			stack.append(child)
	return null


func _relative(node: Node3D, ancestor: Node3D) -> Transform3D:
	var out := Transform3D.IDENTITY
	var at: Node = node
	while at != null and at != ancestor:
		if at is Node3D:
			out = (at as Node3D).transform * out
		at = at.get_parent()
	return out


## Scale the model to HEIGHT if the file came in at another size (FBX files
## are often in centimetres).
func _fit_height() -> void:
	var to_model := _relative(skeleton, model)
	var low := INF
	var high := -INF
	for bone in skeleton.get_bone_count():
		var y := (to_model * skeleton.get_bone_global_rest(bone).origin).y
		low = minf(low, y)
		high = maxf(high, y)
	var tall := high - low
	if tall > 0.001 and (tall < HEIGHT * 0.85 or tall > HEIGHT * 1.15):
		model.scale = Vector3.ONE * (HEIGHT / tall)


## The one animation inside an animation-only FBX, with its tracks pointed at
## this character's skeleton and any forward travel taken out of the hips, so
## a clip downloaded without "In Place" does not slide away from the capsule.
func _load_clip(path: String) -> Animation:
	if not ResourceLoader.exists(path):
		return null
	var scene := load(path) as PackedScene
	if scene == null:
		return null
	var instance := scene.instantiate()
	var source := _first(instance, "AnimationPlayer") as AnimationPlayer
	var animation: Animation = null
	if source:
		for clip_name in source.get_animation_list():
			if clip_name != "RESET":
				animation = source.get_animation(clip_name).duplicate(true)
				break
	instance.free()
	if animation == null:
		return null

	var skeleton_path := String(model.get_path_to(skeleton))
	for track in range(animation.get_track_count() - 1, -1, -1):
		var bone := _bone_named(animation.track_get_path(track).get_concatenated_subnames())
		if bone == "":
			animation.remove_track(track)
			continue
		animation.track_set_path(track, NodePath("%s:%s" % [skeleton_path, bone]))
		if animation.track_get_type(track) == Animation.TYPE_POSITION_3D and bone.ends_with("Hips"):
			var start: Vector3 = animation.track_get_key_value(track, 0)
			for key in animation.track_get_key_count(track):
				var value: Vector3 = animation.track_get_key_value(track, key)
				animation.track_set_key_value(track, key, Vector3(start.x, value.y, start.z))
	return animation


## This skeleton's name for a bone, however the file prefixed it
## ("mixamorig:Hips", "mixamorig_Hips", "Hips").
func _bone_named(wanted: String) -> String:
	if wanted == "":
		return ""
	if skeleton.find_bone(wanted) != -1:
		return wanted
	var short := wanted.get_slice(":", wanted.get_slice_count(":") - 1).trim_prefix("mixamorig_")
	for bone in skeleton.get_bone_count():
		var bone_name := skeleton.get_bone_name(bone)
		if bone_name == short or bone_name.ends_with(":" + short) or bone_name.ends_with("_" + short):
			return bone_name
	return ""


func _bone_ending(suffix: String) -> int:
	for bone in skeleton.get_bone_count():
		if skeleton.get_bone_name(bone).ends_with(suffix):
			return bone
	return -1


## A copy of an animation holding only the keys from t0 to t1, moved to start at 0.
func _trim(source: Animation, t0: float, t1: float) -> Animation:
	var out := Animation.new()
	out.length = t1 - t0
	for track in source.get_track_count():
		var kind := source.track_get_type(track)
		var index := out.add_track(kind)
		out.track_set_path(index, source.track_get_path(track))
		out.track_set_interpolation_type(index, source.track_get_interpolation_type(track))
		# a key on each end, so the trimmed clip starts and ends exactly where the source was then
		for t in [t0, t1]:
			match kind:
				Animation.TYPE_POSITION_3D:
					out.position_track_insert_key(index, t - t0, source.position_track_interpolate(track, t))
				Animation.TYPE_ROTATION_3D:
					out.rotation_track_insert_key(index, t - t0, source.rotation_track_interpolate(track, t))
				Animation.TYPE_SCALE_3D:
					out.scale_track_insert_key(index, t - t0, source.scale_track_interpolate(track, t))
		for key in source.track_get_key_count(track):
			var t := source.track_get_key_time(track, key)
			if t > t0 + 0.001 and t < t1 - 0.001:
				out.track_insert_key(index, t - t0, source.track_get_key_value(track, key))
	return out


func _build_tree(library: AnimationLibrary) -> void:
	var clip := func(wanted: String) -> AnimationNodeAnimation:
		var node := AnimationNodeAnimation.new()
		node.animation = wanted if library.has_animation(wanted) else "idle"
		return node

	var locomotion := AnimationNodeBlendSpace1D.new()
	locomotion.min_space = 0.0
	locomotion.max_space = RUN_SPEED
	locomotion.sync = true
	locomotion.add_blend_point(clip.call("idle"), 0.0, -1, "idle")
	locomotion.add_blend_point(clip.call("walk"), WALK_SPEED, -1, "walk")
	locomotion.add_blend_point(clip.call("run"), RUN_SPEED, -1, "run")

	# Aiming and firing take over the spine, arms and head; the legs keep walking.
	var upper: Array[NodePath] = []
	var skeleton_path := String(model.get_path_to(skeleton))
	var spine := _bone_ending("Spine")
	for bone in skeleton.get_bone_count():
		var at := bone
		while at != -1 and at != spine:
			at = skeleton.get_bone_parent(at)
		if spine != -1 and at == spine:
			upper.append(NodePath("%s:%s" % [skeleton_path, skeleton.get_bone_name(bone)]))

	var aim_blend := AnimationNodeBlend2.new()
	var fire_shot := AnimationNodeOneShot.new()
	fire_shot.fadein_time = 0.05
	fire_shot.fadeout_time = 0.12
	for node: AnimationNode in [aim_blend, fire_shot]:
		node.filter_enabled = not upper.is_empty()
		for path in upper:
			node.set_filter_path(path, true)
	var jump_shot := AnimationNodeOneShot.new()
	jump_shot.fadein_time = 0.08
	jump_shot.fadeout_time = 0.2

	var root := AnimationNodeBlendTree.new()
	root.add_node("locomotion", locomotion, Vector2(0, 0))
	root.add_node("loco_rate", AnimationNodeTimeScale.new(), Vector2(130, 0))
	var jump_rate := AnimationNodeTimeScale.new()
	root.add_node("jump_rate", jump_rate, Vector2(620, 300))
	root.add_node("aim_clip", clip.call("rifle_aim"), Vector2(0, 200))
	root.add_node("aim_blend", aim_blend, Vector2(260, 60))
	root.add_node("fire_clip", clip.call("fire"), Vector2(260, 260))
	root.add_node("fire", fire_shot, Vector2(500, 100))
	root.add_node("jump_clip", clip.call("jump"), Vector2(500, 300))
	root.add_node("jump", jump_shot, Vector2(740, 140))
	root.connect_node("loco_rate", 0, "locomotion")
	root.connect_node("aim_blend", 0, "loco_rate")
	root.connect_node("aim_blend", 1, "aim_clip")
	root.connect_node("fire", 0, "aim_blend")
	root.connect_node("fire", 1, "fire_clip")
	root.connect_node("jump", 0, "fire")
	root.connect_node("jump_rate", 0, "jump_clip")
	root.connect_node("jump", 1, "jump_rate")
	root.connect_node("output", 0, "jump")

	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	_tree.tree_root = root
	model.add_child(_tree)
	_tree.anim_player = _tree.get_path_to(_player)
	_tree.active = true
	_tree.set("parameters/jump_rate/scale", JUMP_RATE)
	_tree.set("parameters/loco_rate/scale", 1.0)


func _attach_rifle() -> void:
	var hand := _bone_ending("RightHand")
	if hand == -1 or not ResourceLoader.exists(RIFLE):
		return
	var scene := load(RIFLE) as PackedScene
	if scene == null:
		return
	var attachment := BoneAttachment3D.new()
	attachment.name = "RightHandAttachment"
	skeleton.add_child(attachment)
	attachment.bone_name = skeleton.get_bone_name(hand)
	rifle = scene.instantiate() as Node3D
	rifle.name = "Rifle"
	attachment.add_child(rifle)
	# The skeleton may be scaled (centimetre files); the rifle is in metres.
	var scale_here := (model.transform * _relative(skeleton, model)).basis.get_scale().x
	scale_here = maxf(scale_here, 0.0001)
	rifle.transform = Transform3D(RIFLE_BASIS.scaled(Vector3.ONE / scale_here), RIFLE_OFFSET / scale_here)
