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
