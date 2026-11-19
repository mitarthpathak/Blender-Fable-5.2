"""Quick Cycles views of single lots in town.blend, for before/after checks.

    blender -b projects/03-town/town.blend --python projects/03-town/lot_views.py -- \
        --out .scratch/lots_after [--only l8,l9] [--samples 24] [--res 960x540]

Lit by a plain daylight sun and sky, so what is in a yard can be seen; this
is not the town's look. Writes <out>/<name>.png.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

# name: camera position, look-at point, lens (Blender space, metres)
VIEWS = {
    "l8_front": ((-21.0, -13.0, 1.7), (-25.0, -3.0, 0.6), 30),
    "l9_front": ((30.0, -13.0, 1.7), (33.2, -5.6, 0.4), 30),
    "l9_garden": ((37.6, -8.0, 2.4), (33.6, -5.4, 0.0), 28),
    "l10_front": ((-23.0, -14.0, 1.7), (-25.2, -22.0, 0.2), 32),
    "l10_back": ((-20.6, -39.4, 2.0), (-25.4, -37.4, 1.0), 26),
    "l11_front": ((32.0, -14.0, 1.8), (31.0, -24.0, 0.4), 28),
    "l11_side": ((28.6, -20.2, 1.9), (28.2, -26.6, 0.2), 30),
    "l1_back": ((10.5, 17.2, 3.2), (3.0, 9.0, 1.2), 22),
    # cars
    "car_sedan": ((15.6, -14.6, 1.4), (18.5, -16.9, 0.7), 28),
    "car_wagon": ((12.6, -40.8, 1.5), (15.6, -44.0, 0.7), 28),
    "car_crashed": ((-0.2, -50.6, 1.5), (2.4, -54.6, 0.7), 28),
    "car_west": ((-24.0, -8.8, 1.5), (-28.0, -10.9, 0.6), 28),
    "car_sedan_in": ((17.3, -16.0, 1.25), (18.9, -17.2, 0.85), 24),
    # streets
    "street_west": ((-8.0, -14.2, 1.6), (-30.0, -14.2, 1.0), 26),
    "street_east": ((14.0, -14.2, 1.6), (38.0, -14.2, 1.0), 26),
    "street_mill": ((3.5, -20.0, 1.6), (3.5, -57.0, 1.0), 26),
    "street_kerb": ((5.5, -9.4, 1.5), (9.5, -11.4, 0.0), 26),
    "street_corner": ((-1.0, -20.5, 1.6), (6.0, -12.0, 0.4), 22),
    "car_sedan_rear": ((22.6, -15.6, 1.25), (20.8, -16.9, 0.55), 30),
    "car_west_front": ((-25.6, -13.6, 2.3), (-28.0, -10.9, 0.9), 28),
    "car_sedan_side": ((18.5, -13.2, 1.3), (18.5, -16.9, 0.8), 30),
    "house_l2_west": ((-19.6, -1.6, 1.7), (-16.6, 4.5, 0.9), 26),
    "house_l2_east": ((-6.0, 1.8, 1.6), (-9.0, 4.6, 1.0), 22),
    "house_l3_back": ((19.6, 14.5, 2.0), (19.6, 8.0, 1.4), 26),
    "house_l3_roof": ((19.6, 17.5, 8.5), (19.6, 6.0, 6.0), 30),
    "house_l4_side": ((-3.0, -29.2, 1.6), (-6.4, -31.6, 1.0), 22),
    "house_l3_side": ((26.6, 2.6, 1.6), (24.2, 5.0, 1.1), 22),
    "street_crosswalk": ((-4.4, -21.5, 1.7), (-4.4, -12.0, -0.4), 24),
    # houses: roofs along the north side, L3 with its dish and air conditioner
    "roofs_north": ((2.0, -17.5, 7.5), (-6.0, 2.0, 7.0), 24),
    "house_l3": ((26.0, -11.5, 2.2), (19.5, 0.5, 3.8), 26),
    "house_l9": ((31.0, -12.0, 2.0), (33.2, 0.5, 3.5), 26),
    # placement fixes: things that went through fences or floated
    "fix_bags_n": ((5.6, -12.2, 1.5), (6.9, -8.7, -0.1), 30),
    "fix_bike": ((-0.2, -10.8, 1.6), (-1.6, -7.5, -0.3), 30),
    "fix_cart": ((7.6, -16.2, 1.5), (9.6, -18.9, -0.1), 30),
    "fix_mailbox": ((-10.6, -11.4, 1.4), (-12.0, -8.6, 0.3), 30),
    "fix_tricycle": ((-5.0, -17.4, 1.4), (-7.0, -20.9, -0.3), 32),
    "fix_fallen_fence": ((32.6, -11.2, 1.6), (36.4, -7.6, 0.1), 24),
    "fix_fallen_stump": ((35.0, -18.2, 1.4), (36.4, -20.2, -0.05), 28),
}


def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(option(args, "--out", ".scratch/lots")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    only = option(args, "--only", "")
    names = [n for n in VIEWS if not only or n in only.split(",")]
    w, h = (int(v) for v in option(args, "--res", "960x540").split("x"))

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(option(args, "--samples", "24"))
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 64       # the tree crowns are many alpha cards deep
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    for light in [o for o in scene.objects if o.type == "LIGHT"]:
        light.hide_render = True
    for obj in scene.objects:                       # game colliders: invisible in Godot
        if "colonly" in obj.name or obj.name.endswith("-col"):
            obj.hide_render = True

    world = bpy.data.worlds.new("lot_views_sky")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.55, 0.65, 0.8, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.world = world
    sun_data = bpy.data.lights.new("lot_views_sun", "SUN")
    sun_data.energy = 3.5
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("lot_views_sun", sun_data)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(150))
    scene.collection.objects.link(sun)

    cam_data = bpy.data.cameras.new("lot_views_cam")
    cam = bpy.data.objects.new("lot_views_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for name in names:
        at, to, lens = VIEWS[name]
        cam.location = at
        cam.rotation_euler = (Vector(to) - Vector(at)).to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = lens
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("LOTVIEW", scene.render.filepath, flush=True)


main()
