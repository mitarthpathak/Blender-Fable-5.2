extends SceneTree
## Drop the player every 2 m over the whole town and see where it lands.
##
##   godot --headless --path game --script res://tools/town_sweep.gd -- --world=town
##
## At each spot (outside the house footprints) the player is put 1.2 m up and
## left to fall for 1 s. It should end on the ground: road -0.53, lawn about
## -0.45, sidewalk -0.40, a porch 0.0. Printed:
##   SWEEP FELL   x z  the player went below -0.8: a hole in the collision
##   SWEEP HIGH   x z  it stands above 0.25 m: on top of something (a car, a fence)
##   SWEEP AIR    x z  it is not on the floor after the fall
## and a SWEEP summary. Positions are Godot x and z (plan y = -z).

## Kit house footprints and the player's house, plan x0, y0, x1, y1 (projects/03-town/plan.py).
## (Inside one the player falls: the walls are a shell with no floor, and the
## player cannot get in.) L4 is the cottage, L5 the hospital, L9 the shop and
## L10 the villa.
const HOUSES := [
	[-7.8, -127.0, -3.6, -122.8], [-44.0, -184.0, 38.0, -137.0],
	[-0.6, -0.6, 7.9, 8.6], [-16.9, -0.9, -8.7, 8.7], [14.7, -0.1, 24.5, 8.3], [-12.5, -31.9, -4.9, -24.7],
	[10.7, -36.8, 33.3, -23.2], [-14.1, -53.7, -5.9, -44.3], [-29.5, -1.1, -21.9, 7.9], [28.7, 0.1, 37.7, 10.7],
	[-29.7, -34.5, -16.7, -22.9], [8.0, 14.4, 11.4, 17.7],
]


func _initialize() -> void:
	_run.call_deferred()


func _inside_house(x: float, y: float) -> bool:
	for r in HOUSES:
		if x > r[0] and x < r[2] and y > r[1] and y < r[3]:
			return true
	return false


func _run() -> void:
	change_scene_to_file("res://main.tscn")
	for i in 30:
		await physics_frame
	var player := current_scene.get("player") as CharacterBody3D
	var spots := 0
	var fell := 0
	var high := 0
	var air := 0
	var x := -30.0
	while x <= 38.0:
		var y := -137.0
		while y <= 18.0:
			var in_yard := y < -121.0 and x >= -9 and x <= 19
			var in_road := y >= -121.0 and x >= -1.6 and x <= 9
			if (y >= -57 or in_yard or in_road) and not _inside_house(x, y):
				var grade := -0.045 * clampf(-62.0-y, 0.0, 59.0)
				player.global_position = Vector3(x, 1.2 + grade, -y)
				player.velocity = Vector3.ZERO
				for i in 60:
					await physics_frame
				var p := player.global_position
				spots += 1
				if p.y < grade - (1.05 if y < -62 else 0.8):
					fell += 1
					print("SWEEP FELL   %6.1f %6.1f  ended at y %.2f" % [x, y, p.y])
				elif p.y > 0.25:
					high += 1
					var under := ""
					for c in player.get_slide_collision_count():
						var hit := player.get_slide_collision(c)
						under = String((hit.get_collider() as Node).name)
					print("SWEEP HIGH   %6.1f %6.1f  standing at y %.2f on %s" % [x, y, p.y, under])
				elif not player.is_on_floor():
					air += 1
					print("SWEEP AIR    %6.1f %6.1f  at y %.2f" % [x, y, p.y])
			y += 2.0
		x += 2.0
	print("SWEEP %d spots: %d fell through, %d on top of something, %d not on the floor" % [spots, fell, high, air])
	quit()
