"""Preview of the villa (L10, 13 Ashgrove) and the cottage (L4, 15 Ashgrove).

Builds both with tk/villa.py at their real positions on a plain lot with the
town's materials, a sun and a sky; prints triangle counts against one kit
house and checks that nothing at ground level leaves the footprint and the
front apron; renders the views the brief asks for.

    nice -n 10 blender45 -b --factory-startup -P projects/03-town/previews/villa_preview.py -- \
        [--only 1_villa_34,7_both] [--samples 32] [--res 960x540] [--out .scratch/agents/villa] [--check]

--check builds and checks only, renders nothing.
"""

from __future__ import annotations

import dataclasses
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
from tk import core, house_kit, villa  # noqa: E402

G = plan.GROUND
SW = plan.SIDEWALK_Z


def opt(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def kit_house(**kw):
    """A plan.KitHouse with the fields this plan.py knows (kind and apron are new)."""
    names = {f.name for f in dataclasses.fields(plan.KitHouse)}
    return plan.KitHouse(**{k: v for k, v in kw.items() if k in names})


VILLA = plan.Lot("L10", "13 Ashgrove Street", (-30.5, -40.0, -15.5, -19.7), "The villa.",
                 kit_house(width=12.4, depth=11.0, facing="n", origin=(-17.0, -23.2), roof="hip", porch="entry",
                           paint="sage", trim="trim_cream", wear=0.5, door_at=5.7, chimney=0.3, kind="villa",
                           apron=(3.0, -2.8, 9.4, 0.0)))
COTTAGE = plan.Lot("L4", "15 Ashgrove Street", (-15.5, -40.0, -1.6, -19.7), "The cottage.",
                   kit_house(width=7.0, depth=6.6, facing="n", origin=(-5.2, -25.0), roof="gable_front", porch="entry",
                             paint="putty", trim="trim_cream", wear=0.7, door_at=2.9, storeys=1, kind="cottage",
                             apron=(1.9, -1.8, 4.8, 0.0)))
APRONS = {"L10": (3.0, -2.8, 9.4, 0.0), "L4": (1.9, -1.8, 4.8, 0.0)}

# camera position, look-at point, lens (world, Blender axes)
VIEWS = {
    "1_villa_34": ((-7.5, -12.0, 5.2), (-23.6, -29.0, 4.4), 26),
    "2_villa_sidewalk": ((-18.2, -18.7, SW + 1.6), (-23.6, -25.5, 3.6), 24),
    "3_villa_entrance": ((-20.6, -18.9, 1.45), (-23.3, -22.9, 1.2), 24),
    "4_cottage_34": ((0.6, -16.6, 3.4), (-8.4, -28.4, 2.3), 28),
    "5_cottage_sidewalk": ((-7.2, -18.9, SW + 1.6), (-8.7, -26.0, 2.0), 24),
    "6_cottage_entrance": ((-7.0, -20.5, 1.5), (-8.6, -25.0, 1.05), 26),
    "7_both": ((-9.0, -3.0, 6.8), (-17.0, -28.5, 2.8), 24),
    # the same street view at dusk: the one lamp still burning in the cottage
    "8_cottage_dusk": ((-6.4, -18.9, SW + 1.6), (-8.4, -26.0, 1.9), 26),
    # checks: the sides and backs the player can walk round to
    "c_villa_east": ((-14.2, -22.0, 1.9), (-17.6, -27.4, 2.4), 24),
    "c_villa_west": ((-34.5, -20.5, 3.0), (-29.0, -28.5, 3.5), 24),
    "c_villa_back": ((-16.0, -41.5, 3.0), (-23.2, -33.0, 4.0), 24),
    "c_cottage_mill": ((-0.6, -25.6, 1.7), (-5.2, -28.6, 1.6), 26),
    "c_cottage_back": ((-14.0, -36.5, 2.4), (-8.2, -30.5, 2.2), 24),
    "c_villa_roof": ((-12.0, -13.0, 13.0), (-23.2, -28.0, 8.0), 28),
    "c_villa_balcony": ((-21.0, -19.0, 4.3), (-23.2, -22.6, 4.3), 30),
}


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def check_bounds(lot, mb, tol_ground=0.13, over=0.5):
    """Vertices in the local frame: below 2.4 m above the yard they must lie in the footprint
    or the apron (give or take the trim on the walls); above, within `over` of them."""
    h = lot.house
    ax0, ay0, ax1, ay1 = APRONS[lot.key]

    def dist(x, y):
        def d(r):
            x0, y0, x1, y1 = r
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            return math.hypot(dx, dy)
        return min(d((0.0, 0.0, h.width, h.depth)), d((ax0, ay0, ax1, ay1)))

    worst_lo, worst_hi = (0.0, None), (0.0, None)
    n_lo = 0
    for v in mb.verts:
        e = dist(v.x, v.y)
        if v.z < G + 2.4:
            if e > tol_ground:
                n_lo += 1
            if e > worst_lo[0]:
                worst_lo = (e, tuple(round(c, 2) for c in v))
        elif e > worst_hi[0]:
            worst_hi = (e, tuple(round(c, 2) for c in v))
    print(f"BOUNDS {lot.key}: ground-level verts beyond {tol_ground} m: {n_lo}; worst low {worst_lo[0]:.3f} at {worst_lo[1]}; "
          f"worst high {worst_hi[0]:.3f} at {worst_hi[1]} (limit {over})")


def ground():
    mb = core.MeshBuilder()
    mb.box((-45.0, -50.0, G - 0.3), (-1.6, -19.7, G), "lawn_overgrown", skip="-z")
    mb.box((12.0, -50.0, G - 0.3), (20.0, -19.7, G), "lawn_overgrown", skip="-z")
    mb.box((-45.0, -8.6, G - 0.3), (20.0, 12.0, G), "lawn_overgrown", skip="-z")
    mb.build("ground_lawn", "ground")
    sw = core.MeshBuilder()
    for r in ((-45.0, -19.7, 0.0, -18.1), (-1.6, -50.0, 0.0, -19.7), (-45.0, -10.2, 20.0, -8.6), (7.0, -50.0, 8.6, -18.1)):
        sw.box((r[0], r[1], G - 0.3), (r[2], r[3], SW), "sidewalk", skip="-z", color=(0.85, 0.84, 0.8))
    sw.build("ground_sidewalks", "ground")
    rd = core.MeshBuilder()
    rd.box((-45.0, -50.0, plan.ROAD_Z - 0.3), (20.0, -10.2, plan.ROAD_Z), "road", skip="-z")
    rd.build("ground_road", "ground")


def path_to(lot, m, steps):
    sx0, sx1, sy = steps
    a = m @ Vector(((sx0 + sx1) / 2, sy, 0.0))
    mb = core.MeshBuilder()
    w = 0.6
    mb.box((a.x - w, min(a.y, lot.rect[3]), G - 0.2), (a.x + w, max(a.y, lot.rect[3]), G + 0.025), "concrete", skip="-z",
           color=(0.78, 0.76, 0.72))
    mb.build(f"path_{lot.key}", "ground")


def sky_and_sun(scene):
    world = bpy.data.worlds.new("day")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(24)
    sky.sun_rotation = math.radians(200)
    sky.air_density = 1.4
    sky.dust_density = 2.0
    sky.sun_disc = False
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.16
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.color = (1.0, 0.94, 0.86)
    sun.angle = math.radians(2.0)
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(62), 0.0, math.radians(-38))      # low, from the north-west of south, on the fronts
    core.collection("lights").objects.link(so)


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


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = (ROOT / opt(args, "--out", ".scratch/agents/villa")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    only = [s for s in opt(args, "--only", "").split(",") if s]
    samples = int(opt(args, "--samples", "32"))
    rw, rh = (int(v) for v in opt(args, "--res", "960x540").split("x"))
    t0 = time.time()

    bpy.ops.wm.read_homefile(use_empty=True)
    core._cache.clear()
    scene = bpy.context.scene

    # one kit house, for the budget
    ref = plan.HOUSES[1]
    mb, *_ = house_kit.build_house(ref, random.Random(101))
    ko = mb.build("ref_kit", "ref")
    kit_tris = tris(ko)
    bpy.data.objects.remove(ko, do_unlink=True)
    print(f"TRIS kit house {ref.key} (plan.HOUSES[1]): {kit_tris}")

    keys = [l.key for l in plan.HOUSES]
    for lot, fn in ((VILLA, villa.build_villa), (COTTAGE, villa.build_cottage)):
        seed = 100 + (keys.index(lot.key) if lot.key in keys else 20)
        mb, m, ramps, lit, steps = fn(lot, random.Random(seed))
        check_bounds(lot, mb)
        world = core.MeshBuilder()
        world.extend(mb, m)
        obj = world.build(f"house_{lot.key}", "houses")
        t = tris(obj)
        print(f"TRIS {lot.key} {fn.__name__}: {t} = {t / kit_tris:.2f} x the kit house (budget 2.5 x = {int(2.5 * kit_tris)})")
        print(f"MATERIALS {lot.key}: {sorted(set(mb.mats))}")
        print(f"CONTRACT {lot.key}: ramps={[(tuple(round(c, 3) for c in lo), tuple(round(c, 3) for c in hi)) for lo, hi in ramps]} "
              f"steps={tuple(round(c, 3) for c in steps)} lit_points={[tuple(round(c, 3) for c in p) for p in lit]}")
        print(f"WORLD {lot.key}: steps centre {tuple(round(c, 2) for c in m @ Vector(((steps[0] + steps[1]) / 2, steps[2], 0.0)))}, "
              f"lights {[tuple(round(c, 2) for c in m @ p) for p in lit]}")
        for k, p in enumerate(lit):
            core.light(f"lit_window_{lot.key}_{k}", m @ p, "point", 12.0, (1.0, 0.62, 0.32), coll="lights", radius=0.2)
        for j, (lo, hi) in enumerate(ramps):
            wm = core.MeshBuilder()
            from tk import street_kit
            street_kit.wedge(wm, lo, hi, "+y")
            wo = core.MeshBuilder()
            wo.extend(wm, m)
            ro = wo.build(f"steps_ramp_{lot.key}_{j}", "collision")
            ro.hide_render = True
        path_to(lot, m, steps)
    print(f"BUILD {time.time() - t0:.1f}s")
    if "--check" in args:
        return

    ground()
    sky_and_sun(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 16
    scene.render.resolution_x, scene.render.resolution_y = rw, rh
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.5
    scene.render.image_settings.file_format = "PNG"
    for name, (loc, tgt, lens) in VIEWS.items():
        if only and name not in only:
            continue
        if not only and name.startswith("c_"):
            continue
        dusk = name.endswith("_dusk")
        sun_obj = bpy.data.objects["sun"]
        sun_obj.data.energy = 0.08 if dusk else 3.2
        sun_obj.data.color = (0.6, 0.7, 1.0) if dusk else (1.0, 0.94, 0.86)
        scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.012 if dusk else 0.16
        for o in bpy.data.objects:
            if o.name.startswith("lit_window_"):
                o.data.energy = 12.0
        scene.camera = camera("cam_" + name, loc, tgt, lens)
        scene.render.filepath = str(out / f"{name}.png")
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"RENDER {name} {time.time() - t1:.0f}s -> {scene.render.filepath}")
    print(f"DONE {time.time() - t0:.0f}s")


main()
