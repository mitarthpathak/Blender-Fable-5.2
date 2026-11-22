"""Preview of Ridge Stationery & Books (tk/shop.py) on a plain ground plane.

    nice -n 10 blender45 -b --factory-startup -P projects/03-town/previews/shop_preview.py -- [--samples N]
        [--res WxH] [--only name[,name]] [--no-render] [--save]

Builds the shop on lot L9 exactly as the town will (shop.build_shop, then the
local->world matrix), measures it against one kit house, checks that nothing
at ground level leaves the footprint and its apron, and renders daylight
Cycles views to .scratch/agents/shop/.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent.parent          # projects/03-town
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import plan  # noqa: E402
from tk import core, house_kit, shop  # noqa: E402

OUT = ROOT / ".scratch" / "agents" / "shop"
G = plan.GROUND

LOT = plan.Lot(
    "L9", "18 Ashgrove Street", (28.0, -8.6, 38.5, 18.0), "Ridge Stationery & Books, the flat above.",
    plan.KitHouse(width=8.4, depth=10.0, facing="s", origin=(29.0, 0.4), roof="gable_front", porch="entry",
                  paint="dusty_blue", trim="trim_grey", wear=0.6, door_at=3.7))


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"samples": 32, "res": (960, 540), "only": None, "render": True, "save": False}
    for i, v in enumerate(a):
        if v == "--samples":
            o["samples"] = int(a[i + 1])
        elif v == "--res":
            w, h = a[i + 1].split("x")
            o["res"] = (int(w), int(h))
        elif v == "--only":
            o["only"] = a[i + 1].split(",")
        elif v == "--no-render":
            o["render"] = False
        elif v == "--save":
            o["save"] = True
    return o


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def check_footprint(mb, h):
    """Ground-level geometry must stay inside the footprint plus the apron; above 2.4 m
    it may reach 0.5 m further over the apron. Wall-mounted bits (downpipes, foundation
    lip, trim, the gas meter) may stand up to 0.22 m proud, less than on the kit houses."""
    W, D = h.width, h.depth
    tol = 0.22
    low, high = [], []
    for v in mb.verts:
        if v.z < G + 2.4:
            if not (-tol <= v.x <= W + tol and -shop.APRON_D - 1e-3 <= v.y <= D + tol):
                low.append(v)
        else:
            if v.y < -shop.APRON_D - 0.5 - 1e-3:
                high.append(v)
    xs = [v.x for v in mb.verts]
    ys = [v.y for v in mb.verts]
    zs = [v.z for v in mb.verts]
    print(f"BOUNDS local x {min(xs):.2f}..{max(xs):.2f}  y {min(ys):.2f}..{max(ys):.2f}  z {min(zs):.2f}..{max(zs):.2f}")
    low_x = [v.x for v in mb.verts if v.z < G + 2.4]
    low_y = [v.y for v in mb.verts if v.z < G + 2.4]
    print(f"BOUNDS below 2.4 m: x {min(low_x):.2f}..{max(low_x):.2f}  y {min(low_y):.2f}..{max(low_y):.2f}")
    print(f"FOOTPRINT_CHECK ground-level vertices outside: {len(low)}; overhang beyond apron+0.5: {len(high)}")
    for v in (low + high)[:12]:
        print("   outside:", tuple(round(c, 3) for c in v))


def world_day(scene):
    world = bpy.data.worlds.new("day")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "NISHITA"
    except TypeError:
        pass
    sky.sun_elevation = math.radians(24)
    sky.sun_rotation = math.radians(200)
    try:
        sky.air_density, sky.dust_density, sky.ozone_density = 1.4, 2.0, 1.0
        sky.sun_disc = False
    except AttributeError:
        pass
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.16
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.color = (1.0, 0.94, 0.86)
    sun.angle = math.radians(2.0)
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(64), 0.0, math.radians(-62))      # as build.py's day stills
    core.collection("lights").objects.link(so)
    scene.view_settings.exposure = 0.5


def ground(m, steps):
    mb = core.MeshBuilder()
    mb.box((18.0, -8.6, G - 0.3), (48.0, 26.0, G), "lawn_overgrown", skip="-z")
    side = core.MeshBuilder()
    side.box((18.0, -10.2, G - 0.3), (48.0, -8.6, plan.SIDEWALK_Z), "sidewalk", skip="-z")
    road = core.MeshBuilder()
    road.box((18.0, -18.1, G - 0.3), (48.0, -10.2, plan.ROAD_Z), "road", skip="-z")
    sx0, sx1, sy = steps
    a = m @ Vector(((sx0 + sx1) / 2, sy, 0))
    side.box((a.x - 0.6, -8.6, G), (a.x + 0.6, a.y, G + 0.025), "concrete", skip="-z", color=(0.78, 0.76, 0.72))
    mb.build("ground_lawn", "ground")
    side.build("ground_sidewalk", "ground")
    road.build("ground_road", "ground")


def camera(name, loc, target, lens):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.05
    cam.clip_end = 300
    obj = bpy.data.objects.new(name, cam)
    obj.location = Vector(loc)
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    core.collection("cameras").objects.link(obj)
    return obj


EYE = plan.SIDEWALK_Z + 1.6
SHOTS = {
    # name: camera, target, lens (world coordinates; the shop's front is y 0.4, x 29.0..37.4)
    "1_three_quarter": ((21.0, -10.5, 5.2), (33.0, 3.5, 3.7), 26),
    "2_sidewalk": ((33.2, -9.4, EYE), (33.2, 0.4, 2.9), 24),
    "3_entrance": ((33.0, -3.0, G + 1.6), (33.2, 1.4, 0.9), 26),
    "4_west_advert": ((24.5, -5.0, 2.2), (29.0, 3.0, 4.4), 26),
    "5_back_stair": ((24.5, 16.5, 4.2), (33.0, 9.6, 2.4), 26),
    "6_awning_sign": ((36.4, -4.2, G + 1.6), (36.0, 0.4, 2.9), 26),
}


def main():
    o = args()
    t0 = time.time()
    bpy.ops.wm.read_homefile(use_empty=True)
    core._cache.clear()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"

    # the shop, built and placed as kit_houses() does it
    mb, m, ramps, lit_points, steps = shop.build_shop(LOT, random.Random(108))
    check_footprint(mb, LOT.house)
    world = core.MeshBuilder()
    world.extend(mb, m)
    obj = world.build("house_L9", "houses")
    n_shop = tris(obj)
    mats = sorted({s.material.name for s in obj.material_slots})
    # one kit house for the budget, as the brief asks (plan.HOUSES[1])
    kit_lot = plan.HOUSES[1]
    kmb, *_ = house_kit.build_house(kit_lot, random.Random(101))
    kobj = kmb.build("kit_reference", "reference")
    n_kit = tris(kobj)
    bpy.data.objects.remove(kobj, do_unlink=True)
    print(f"TRIS shop={n_shop} kit_house({kit_lot.key})={n_kit} ratio={n_shop / n_kit:.2f} (budget 2.5)")
    print(f"MATERIALS {len(mats)}: {', '.join(mats)}")
    print(f"RAMPS {ramps}")
    print(f"STEPS {steps}  LIT {len(lit_points)}")
    print(f"WORLD weatherhead (service drop end) {tuple(round(c, 2) for c in (m @ Vector((3.03, -0.08, 5.70))))}")
    for j, (lo, hi) in enumerate(ramps):
        r = core.MeshBuilder()
        from tk.street_kit import wedge
        wedge(r, lo, hi, "+y")
        w = core.MeshBuilder()
        w.extend(r, m)
        ro = w.build(f"steps_ramp_L9_{j}-convcolonly", "collision")
        ro.hide_render = True
    print(f"BUILD {time.time() - t0:.1f}s")

    ground(m, steps)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = o["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 16
    scene.render.resolution_x, scene.render.resolution_y = o["res"]
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    world_day(scene)
    OUT.mkdir(parents=True, exist_ok=True)
    if o["save"]:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "shop_preview.blend"), compress=True)
    if not o["render"]:
        return
    for name, (loc, tgt, lens) in SHOTS.items():
        if o["only"] and not any(k in name for k in o["only"]):
            continue
        t1 = time.time()
        scene.camera = camera("cam_" + name, loc, tgt, lens)
        scene.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"RENDER {name} {time.time() - t1:.1f}s")
    print(f"DONE {time.time() - t0:.1f}s")


main()
