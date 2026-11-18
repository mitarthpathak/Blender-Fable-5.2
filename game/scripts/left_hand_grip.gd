class_name LeftHandGrip
extends SkeletonModifier3D
## Puts the left hand on the rifle's fore grip, after the animation has played.
##
## Mixamo's rifle clips leave the left hand open under the weapon, and in the
## idle and walk clips it does not quite reach it. This modifier, a child of
## the Skeleton3D, runs after the AnimationTree has posed it:
##
##   1. turns the left hand so the palm faces the fore grip from the left,
##      fingers forward round the front of it;
##   2. bends the arm (an analytic two-bone IK, keeping the elbow on the side
##      the clip put it) so that palm lands on GRIP_AT;
##   3. curls the four fingers round the grip.
##
## `weight` (0..1) is set by CharacterRig every frame: full while aiming,
## standing and walking, none at a run, where the clip carries the rifle in
## one hand.

## rifle.glb's own space: +Z muzzle, +Y up (tools/rifle_fit.gd has how it
## relates to rifle.py's gun space). The fore grip is a 35 mm post hanging
## under the handguard at z 0.306, from y 0.022 down to -0.054.
const GRIP_AT := Vector3(-0.031, -0.014, 0.300)     # the middle of the palm, against the fore grip's left side
const FINGERS := Vector3(0.12, -0.12, 1.0)          # where the fingers point: forward, round the front of the post
const PALM_FACES := Vector3(1.0, 0.0, 0.0)          # right, onto the post
## Curl of each finger joint in radians, base to tip: enough to close round the post.
const CURL := [0.95, 1.15, 0.75]
const FINGER_NAMES := ["Index", "Middle", "Ring", "Pinky"]

var rifle: Node3D
var weight := 0.0
var last_error := INF            # metres from the palm to GRIP_AT after the last solve (the pose is
                                 # only modified inside the modification, so measure it there)

var _arm := -1
var _fore := -1
var _hand := -1
var _right_hand := -1
var _fingers: Array[PackedInt32Array] = []


## Find the bones. False if the skeleton is not a Mixamo-style human.
func setup(skeleton: Skeleton3D, held: Node3D) -> bool:
	rifle = held
	_arm = _bone(skeleton, "LeftArm")
	_fore = _bone(skeleton, "LeftForeArm")
	_hand = _bone(skeleton, "LeftHand")
	_right_hand = _bone(skeleton, "RightHand")
	_fingers.clear()
	for finger in FINGER_NAMES:
		var chain := PackedInt32Array()
		for joint in 3:
			chain.append(_bone(skeleton, "LeftHand%s%d" % [finger, joint + 1]))
		_fingers.append(chain)
	return _arm != -1 and _fore != -1 and _hand != -1 and _right_hand != -1 and not -1 in _fingers[0] \
		and not -1 in _fingers[3]


static func _bone(skeleton: Skeleton3D, suffix: String) -> int:
	for bone in skeleton.get_bone_count():
		var n := skeleton.get_bone_name(bone)
		if n.ends_with(suffix) and (n.length() == suffix.length() or n[n.length() - suffix.length() - 1] in [":", "_"]):
			return bone
	return -1


## Orthonormal frame with x along `forward` and z as close to `normal` as it can be.
static func _frame(forward: Vector3, normal: Vector3) -> Basis:
	var x := forward.normalized()
	var z := (normal - x * normal.dot(x)).normalized()
	return Basis(x, z.cross(x), z)


## The middle of the palm: between the wrist and the knuckles, nearer the knuckles.
func _palm(sk: Skeleton3D) -> Vector3:
	var wrist := sk.get_bone_global_pose(_hand).origin
	var knuckles := Vector3.ZERO
	for chain in _fingers:
		knuckles += sk.get_bone_global_pose(chain[0]).origin
	return wrist.lerp(knuckles / 4.0, 0.62)


## The hand's own frame: fingers, and the way the palm faces (for a left hand
## the palm is on the side of -(fingers x index-to-pinky)).
func _hand_frame(sk: Skeleton3D) -> Basis:
	var wrist := sk.get_bone_global_pose(_hand).origin
	var fingers := sk.get_bone_global_pose(_fingers[1][0]).origin - wrist
	var across := sk.get_bone_global_pose(_fingers[3][0]).origin - sk.get_bone_global_pose(_fingers[0][0]).origin
	return _frame(fingers, -fingers.cross(across))


## Where the palm is, against where it should be, in metres of rifle space: for checks.
func palm_error() -> float:
	return last_error


func _process_modification() -> void:
	var sk := get_skeleton()
	if sk == null or rifle == null or _hand == -1 or weight <= 0.001:
		return
	# The rifle, in skeleton space: it rides on the right hand.
	var rifle_t := sk.get_bone_global_pose(_right_hand) * rifle.transform
	var rifle_rot := rifle_t.basis.orthonormalized()

	# 1. The turn that brings the hand from the clip's pose onto the handguard.
	var hand := sk.get_bone_global_pose(_hand)
	var want := _frame(rifle_rot * FINGERS, rifle_rot * PALM_FACES)
	var turn := Quaternion.IDENTITY.slerp(Quaternion(want * _hand_frame(sk).inverse()), weight)
	var palm_offset := _palm(sk) - hand.origin
	var goal := rifle_t * GRIP_AT - Basis(turn) * palm_offset
	goal = hand.origin.lerp(goal, weight)

	# 2. Two-bone IK: shoulder to elbow to wrist, the elbow kept on its side.
	var upper := sk.get_bone_global_pose(_arm)
	var root := upper.origin
	var elbow := sk.get_bone_global_pose(_fore).origin
	var la := root.distance_to(elbow)
	var lb := elbow.distance_to(hand.origin)
	var to_goal := goal - root
	var reach := clampf(to_goal.length(), absf(la - lb) + 1e-4, la + lb - 1e-4)
	var aim := to_goal.normalized()
	var bend := elbow - root
	var pole := bend - aim * bend.dot(aim)
	if pole.length_squared() < 1e-8:
		pole = upper.basis.x
	pole = pole.normalized()
	var cos_a := clampf((la * la + reach * reach - lb * lb) / (2.0 * la * reach), -1.0, 1.0)
	var new_elbow := root + aim * la * cos_a + pole * la * sqrt(1.0 - cos_a * cos_a)
	var new_wrist := root + aim * reach

	upper.basis = Basis(Quaternion((elbow - root).normalized(), (new_elbow - root).normalized())) * upper.basis
	sk.set_bone_global_pose(_arm, upper)
	var fore := sk.get_bone_global_pose(_fore)
	var wrist_now := sk.get_bone_global_pose(_hand).origin
	fore.basis = Basis(Quaternion((wrist_now - fore.origin).normalized(), (new_wrist - fore.origin).normalized())) * fore.basis
	sk.set_bone_global_pose(_fore, fore)
	var placed := sk.get_bone_global_pose(_hand)
	placed.basis = Basis(turn) * hand.basis
	sk.set_bone_global_pose(_hand, placed)

	# 3. Close the fingers: each joint turns the finger towards the palm.
	var frame := _hand_frame(sk)
	var axis := frame.x.cross(frame.z).normalized()
	for chain in _fingers:
		for joint in 3:
			if chain[joint] == -1:
				continue
			var pose := sk.get_bone_global_pose(chain[joint])
			pose.basis = Basis(axis, CURL[joint] * weight) * pose.basis
			sk.set_bone_global_pose(chain[joint], pose)
	last_error = (rifle_t.affine_inverse() * _palm(sk)).distance_to(GRIP_AT)
