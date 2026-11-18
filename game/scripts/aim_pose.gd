class_name AimPose
extends SkeletonModifier3D
## The character's look up and down, after the animation has played:
##
##   - `pitch` (radians, + is up) is where the rifle should point: the body's
##     forward, raised by `pitch`. The three spine bones turn, a third each,
##     until the muzzle points there (by `weight`). It is measured, not
##     assumed: the clip's own lean, the hips swinging under a walk and the
##     aim clip's bladed stance are all taken out, so the rifle stays on the
##     line of sight while aiming or in first person;
##   - `hide_head` collapses the head bone (and the hair, eyes and lashes
##     skinned to it) for the first-person camera, which sits where the eyes
##     were;
##   - `eye` is where the eyes are after both, in skeleton space, for the
##     first-person camera to follow.
##
## A child of the Skeleton3D, before LeftHandGrip: the grip reads the rifle
## from the right hand after the spine has moved.

const SPINE := ["Spine", "Spine1", "Spine2"]
## The eyes from the head bone's origin (the base of the skull), in the
## body's own frame: up and forward, metres.
const EYE_UP := 0.085
const EYE_FORWARD := 0.105

var pitch := 0.0
var rifle: Node3D                # on the right hand (its transform is in the hand bone's space)
var weight := 0.0
var hide_head := false
var eye := Vector3.ZERO          # skeleton space, updated every modification
var body: Node3D                 # the rig: its basis gives the body's right and forward

var _spine: PackedInt32Array = []
var _head := -1
var _right_hand := -1


func setup(skeleton: Skeleton3D, rig: Node3D) -> bool:
	body = rig
	_spine.clear()
	for bone in SPINE:
		var index := LeftHandGrip._bone(skeleton, bone)
		if index != -1:
			_spine.append(index)
	_head = LeftHandGrip._bone(skeleton, "Head")
	_right_hand = LeftHandGrip._bone(skeleton, "RightHand")
	return _head != -1 and not _spine.is_empty()


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or body == null or _head == -1:
		return
	# The body's frame, in skeleton space (the model inside is turned to face -Z).
	var to_skeleton := sk.global_transform.basis.orthonormalized().inverse() * body.global_transform.basis.orthonormalized()
	var right := (to_skeleton * Vector3.RIGHT).normalized()
	var up := (to_skeleton * Vector3.UP).normalized()
	var forward := (to_skeleton * Vector3.FORWARD).normalized()

	var bend := clampf(pitch, -1.2, 1.2)
	var wanted := Basis(right, bend) * forward
	if weight > 0.001:
		# The muzzle now, and the turn that brings it onto `wanted`. Each spine
		# bone takes a third; directions below them turn by the whole of it.
		var aim_now := wanted
		if rifle and _right_hand != -1:
			aim_now = ((sk.get_bone_global_pose(_right_hand) * rifle.transform).basis.orthonormalized() * Vector3.BACK).normalized()
		else:
			aim_now = forward
		var turn := Quaternion.IDENTITY.slerp(Quaternion(aim_now, wanted), weight)
		var step := Basis(Quaternion.IDENTITY.slerp(turn, 1.0 / float(_spine.size())))
		for bone in _spine:
			var pose := sk.get_bone_global_pose(bone)
			pose.basis = step * pose.basis
			sk.set_bone_global_pose(bone, pose)

	var head := sk.get_bone_global_pose(_head)
	var look := Basis(right, bend * weight)
	eye = head.origin + look * (up * EYE_UP + forward * EYE_FORWARD)
	if hide_head:
		head.basis = head.basis.scaled(Vector3.ONE * 0.001)
		sk.set_bone_global_pose(_head, head)
