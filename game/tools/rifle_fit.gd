extends SceneTree
## Work out where the rifle sits in the right hand, from the character's own
## aiming pose, and print the two constants for scripts/character.gd.
##
##   godot --path game --script res://tools/rifle_fit.gd
##
## In the aim clip both hands are on the weapon: the right fist round the
## pistol grip, the left hand under the handguard. The rifle is turned so the
## line from its pistol grip to its fore grip runs from the right palm to the
## left palm, kept upright, and moved so the pistol grip is in the right palm.
## That placement, measured in the right hand's own space, is what every clip
## then uses: Mixamo's rifle clips all hold the weapon the same way.

## Points on the rifle (scripts/character.gd's rifle space: +Z muzzle, +Y up,
## origin at the top of the pistol grip), from projects/03-character/rifle.py.
const GRIP := Vector3(0.0, -0.105, -0.090)      # the middle of the pistol grip, where the fist closes
const FORE := Vector3(0.0, -0.070, 0.225)       # the middle of the fore grip
## The clip was made for a rifle with a lower stock than ours: held exactly
## grip to grip, our stock goes through the cheek. So the fist slides this far
## up the grip (the rifle drops) and the muzzle comes up this many degrees,
## which brings the stock down onto the shoulder.
const DROP := 0.022
const PITCH := 6.0
## And the muzzle turns this many degrees towards the left hand, which swings
## the stock out from under the face onto the right shoulder.
const YAW := 9.0


func _initialize() -> void:
	_run.call_deferred()


func _palm(sk: Skeleton3D, side: String) -> Vector3:
	var points: Array[Vector3] = []
	for bone in ["%sHand" % side, "%sHandIndex1" % side, "%sHandMiddle1" % side, "%sHandRing1" % side]:
		var index := _bone(sk, bone)
		if index != -1:
			points.append((sk.global_transform * sk.get_bone_global_pose(index)).origin)
	var sum := Vector3.ZERO
	for p in points:
		sum += p
	# the hand bone is the wrist: weigh the knuckles more, that is where the fist closes
	var wrist := points[0]
	var knuckles := (sum - wrist) / float(points.size() - 1)
	return wrist.lerp(knuckles, 0.62)


func _bone(sk: Skeleton3D, suffix: String) -> int:
	for bone in sk.get_bone_count():
		var n := sk.get_bone_name(bone)
		if n.ends_with(suffix) and (n.length() == suffix.length() or n[n.length() - suffix.length() - 1] in [":", "_"]):
			return bone
	return -1


func _frame(forward: Vector3, up: Vector3) -> Basis:
	var x := up.cross(forward).normalized()
	var y := forward.cross(x).normalized()
	return Basis(x, y, forward.normalized())


func _run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var rig := CharacterRig.create()
	if rig == null:
		print("FIT FAIL: no character")
		quit(1)
		return
	world.add_child(rig)
	var tree := rig.model.get_node("AnimationTree") as AnimationTree
	tree.set("parameters/aim_blend/blend_amount", 1.0)
	for i in 40:
		await process_frame
	var sk := rig.skeleton
	var right := _palm(sk, "Right")
	var left := _palm(sk, "Left")
	print("FIT palms right %s left %s, %.3f m apart (rifle grips are %.3f m apart)" % [right, left,
		right.distance_to(left), GRIP.distance_to(FORE)])

	# rifle space -> world: the grip-to-fore-grip line onto palm-to-palm, kept upright
	var rifle_frame := _frame(FORE - GRIP, Vector3.UP)
	var world_frame := _frame(left - right, Vector3.UP)
	var basis := world_frame * rifle_frame.inverse()
	basis = Basis(world_frame.x, deg_to_rad(-PITCH)) * basis          # muzzle up about the grip
	basis = Basis(Vector3.UP, deg_to_rad(YAW)) * basis                # stock out to the shoulder
	var grip := GRIP + Vector3(0.0, DROP, 0.0)
	var origin := right - basis * grip
	var wanted := Transform3D(basis, origin)

	var attachment := rig.rifle.get_parent() as Node3D
	var local := attachment.global_transform.affine_inverse() * wanted
	var s: float = rig.skeleton.global_transform.basis.get_scale().x
	var b := local.basis.orthonormalized()
	var o := local.origin * maxf(s, 0.0001)
	print("FIT const RIFLE_BASIS := Basis(Vector3(%.4f, %.4f, %.4f), Vector3(%.4f, %.4f, %.4f), Vector3(%.4f, %.4f, %.4f))" % [
		b.x.x, b.x.y, b.x.z, b.y.x, b.y.y, b.y.z, b.z.x, b.z.y, b.z.z])
	print("FIT const RIFLE_OFFSET := Vector3(%.4f, %.4f, %.4f)" % [o.x, o.y, o.z])
	quit()
