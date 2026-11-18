extends SceneTree
## Measure the character's clips, for matching the player to them.
##
##   godot --headless --path game --script res://tools/anim_measure.gd
##
## For walk, run, the strafes and the backward walk: how fast the planted
## foot slides under the body, which is the speed the clip is made for (in
## place, the ground would move at that speed), and which way the body would
## travel (the character faces -Z: forward is z -1). For jump: the height of the hips through the clip, to find
## where the feet leave the ground and where they land.

func _initialize() -> void:
	_run.call_deferred()


func _bone(sk: Skeleton3D, suffix: String) -> int:
	for b in sk.get_bone_count():
		var n := sk.get_bone_name(b)
		if n.ends_with(suffix) and (n.length() == suffix.length() or n[n.length() - suffix.length() - 1] in [":", "_"]):
			return b
	return -1


func _run() -> void:
	var rig := CharacterRig.create()
	if rig == null:
		print("MEASURE FAIL: no character")
		quit(1)
		return
	root.add_child(rig)
	var tree := rig.model.get_node("AnimationTree") as AnimationTree
	tree.active = false
	var player := rig.model.get_node("Clips") as AnimationPlayer
	var sk := rig.skeleton
	var feet := [_bone(sk, "LeftFoot"), _bone(sk, "RightFoot"), _bone(sk, "LeftToeBase"), _bone(sk, "RightToeBase")]
	var hips := _bone(sk, "Hips")
	for clip in ["walk", "run", "strafe_left", "strafe_right", "walk_back"]:
		if not player.has_animation(clip):
			continue
		var anim := player.get_animation(clip)
		var steps := 120
		var dt := anim.length / steps
		var slide := Vector2.ZERO           # the planted foot's slide over the ground, summed
		var travelled := 0.0
		var last := {}
		for i in steps + 1:
			player.play(clip)
			player.seek(i * dt, true)
			player.advance(0.0)
			var pos := {}
			for f in feet:
				pos[f] = (sk.global_transform * sk.get_bone_global_pose(f)).origin
			# the planted foot: whichever toe is lowest
			var planted: int = feet[2] if pos[feet[2]].y < pos[feet[3]].y else feet[3]
			if i > 0 and last.has(planted):
				var d := Vector2(pos[planted].x - last[planted].x, pos[planted].z - last[planted].z)
				slide += d
				travelled += d.length()
			last = pos
		# The ground moves the way the planted foot slides; the body goes the other way.
		var heading := -slide.normalized()
		print("MEASURE %s: %.2f s cycle, foot slides %.2f m, speed %.2f m/s, travel direction (x %.2f, z %.2f)" % [
			clip, anim.length, travelled, travelled / anim.length, heading.x, heading.y])
	var jump := player.get_animation("jump")
	var line := ""
	for i in 24:
		var t := jump.length * i / 23.0
		player.play("jump")
		player.seek(t, true)
		player.advance(0.0)
		var hy := (sk.global_transform * sk.get_bone_global_pose(hips)).origin.y
		var fy := minf((sk.global_transform * sk.get_bone_global_pose(feet[2])).origin.y, (sk.global_transform * sk.get_bone_global_pose(feet[3])).origin.y)
		line += " %.2f:%.2f/%.2f" % [t, hy, fy]
	print("MEASURE jump %.2f s, t:hips/feet%s" % [jump.length, line])
	quit()
