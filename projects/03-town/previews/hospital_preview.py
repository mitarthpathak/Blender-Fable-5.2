"""Preview of the Halden Ridge Community Hospital (tk/hospital.py) on its own.

Builds the hospital as the town will (plan.house_frame), on a plain ground
plane with the sidewalk and Ashgrove Street in front, a stand-in for the
fallen tree's stump, the lead's front path and the collision wedges, then
renders proof views into .scratch/agents/hospital/ and prints triangle counts.

    nice -n 10 blender45 -b --factory-startup -P projects/03-town/previews/hospital_preview.py -- \\
        [--samples 32] [--res 960x540] [--only 1,2,3] [--wedges]

Views: 1 three-quarter, 2 sidewalk (eye 1.6 m, 24 mm), 3 entrance, 4 emergency bay,
5 the sidewalk view in the town's own daylight (sun from the WSW: the north front in shade),
6 night (the lit window), 7 the roof from above, 8 the west end, 9 the back.
Views 1-4 and 7-9 light the front with a low north-west sun so it can be judged.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

TOWN = Path(__file__).resolve().parent.parent
ROOT = TOWN.parent.parent
if str(TOWN) not in sys.path:
    sys.path.insert(0, str(TOWN))

import plan  # noqa: E402
from tk import core, hospital, house_kit, street_kit  # noqa: E402

OUT = ROOT / ".scratch" / "agents" / "hospital"
G = plan.GROUND
STUMP = (36.4, -20.2)


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = {"samples": 32, "res": (960, 540), "only": None, "wedges": False}
    for i, v in enumerate(a):
        if v == "--samples":
            o["samples"] = int(a[i + 1])
        elif v == "--res":
            w, h = a[i + 1].split("x")
            o["res"] = (int(w), int(h))
        elif v == "--only":
            o["only"] = set(a[i + 1].split(","))
        elif v == "--wedges":
            o["wedges"] = True
    return o


def hospital_lot():
    house = plan.KitHouse(width=22.0, depth=13.0, facing="n", origin=(33.0, -23.5), roof="flat", porch="entry",
                          paint="putty", trim="trim_grey", wear=0.75, door_at=9.5)
    return plan.Lot("H", "21 Ashgrove Street", (8.6, -40.0, 38.5, -19.7),
                    "Halden Ridge Community Hospital, closed in 1995.", house=house)


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def ground():
    """Lawn, the south sidewalk and Ashgrove Street, at the town's heights."""
    mb = core.MeshBuilder()
    mb.box((-5.0, -60.0, G - 0.3), (60.0, -19.7, G), "lawn_dead", skip="-z")
    sw = plan.SIDEWALK_Z
    rd = plan.ROAD_Z
    mb.box((-5.0, -19.7, G - 0.3), (60.0, -18.1, sw), "sidewalk", skip="-z", color=(0.85, 0.85, 0.82))
    mb.box((-5.0, -18.1, rd - 0.3), (60.0, -10.2, rd), "road", skip="-z")
    mb.box((-5.0, -10.2, G - 0.3), (60.0, -8.6, sw), "sidewalk", skip="-z", color=(0.85, 0.85, 0.82))
    mb.box((-5.0, -8.6, G - 0.3), (60.0, 20.0, G), "lawn_dead", skip="-z")
    mb.build("preview_ground", "ground")
    # the fallen tree's stump (stand-in), splintered
    st = core.MeshBuilder()
    x, y = STUMP
    st.cylinder((x, y, G - 0.1), (0, 0, 0.9), 0.38, "bark", segments=12, radius_top=0.33, caps="none")
    for k in range(6):
        a = k * 1.05
        st.tube([(x + math.cos(a) * 0.25, y + math.sin(a) * 0.25, G + 0.75),
                 (x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, G + 0.95 + 0.25 * (k % 3))], 0.06, "bark", segments=4)
    st.build("stump_standin", "ground")


def build(opts):
    lot = hospital_lot()
    mb, m, ramps, lit_points, steps = hospital.build_hospital(lot, random.Random(103))
    world = core.MeshBuilder()
    world.extend(mb, m)
    obj = world.build("house_H", "houses")
    # the lead's front path from the steps to the lot front (street_kit.house_paths)
    sx0, sx1, sy = steps
    a = m @ Vector(((sx0 + sx1) / 2, sy, 0))
    b = Vector((a.x, lot.rect[3], 0))
    pm = core.MeshBuilder()
    pm.box((a.x - 0.6, min(a.y, b.y), G), (a.x + 0.6, max(a.y, b.y), G + 0.025), "concrete", skip="-z",
           color=(0.78, 0.76, 0.72))
    pm.build("ground_paths", "ground")
    # collision wedges, as street_kit.collision makes them
    col = core.collection("collision")
    for j, (lo, hi) in enumerate(ramps):
        wm = core.MeshBuilder()
        street_kit.wedge(wm, lo, hi, "+y")
        w = core.MeshBuilder()
        w.extend(wm, m)
        wo = w.build(f"steps_ramp_H_{j}-convcolonly", "collision")
        print("WEDGE", j, [tuple(round(c, 2) for c in v) for v in (lo, hi)])
    col.hide_render = not opts["wedges"]
    lights = []
    for k, p in enumerate(lit_points):
        lights.append(core.light(f"lit_window_H_{k}", m @ p, "point", 18.0, (1.0, 0.62, 0.32), coll="lights", radius=0.2))
    # footprint and apron check: below 2.4 m above the yard everything must be inside the
    # footprint plus the apron (local y -3.6..0); above it the apron may be overhung by 0.5 m
    h = lot.house
    low = [v for v in mb.verts if v.z < G + 2.4]
    high = [v for v in mb.verts if v.z >= G + 2.4]
    side = max(max(0.0, -v.x, v.x - h.width) for v in low)
    back = max(max(0.0, v.y - h.depth) for v in low)
    front = max(max(0.0, -3.6 - v.y) for v in low)
    hfront = max(max(0.0, -3.6 - v.y) for v in high)
    hside = max(max(0.0, -v.x, v.x - h.width) for v in high)
    worst = max(low, key=lambda v: max(0.0, -v.x, v.x - h.width))
    print("WIDEST_LOW", tuple(round(c, 3) for c in worst))
    print(f"FOOTPRINT_CHECK below 2.4 m: past the sides {side:.3f} m, past the back {back:.3f} m, "
          f"past the apron {front:.3f} m; above: past the apron {hfront:.3f} m, past the sides {hside:.3f} m")
    wx = [m @ Vector(v) for v in mb.verts]
    near = min((Vector((p.x, p.y)) - Vector(STUMP)).length for p in wx)
    print(f"STUMP nearest vertex {near:.2f} m from the stump")
    print(f"STEPS {steps} -> world {tuple(round(c, 2) for c in a)}  LIT {[tuple(round(c, 2) for c in m @ p) for p in lit_points]}")
    return obj, lights


def kit_house_tris():
    lot = plan.HOUSES[1]
    mb, *_ = house_kit.build_house(lot, random.Random(101))
    o = mb.build("kit_house_ref", "ref")
    n = tris(o)
    bpy.data.objects.remove(o, do_unlink=True)
    return lot.key, n


def render_setup(scene, opts):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = opts["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 32
    scene.render.resolution_x, scene.render.resolution_y = opts["res"]
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"


def sky(scene, strength=0.16):
    world = bpy.data.worlds.get("day") or bpy.data.worlds.new("day")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    s = nt.nodes.get("sky") or nt.nodes.new("ShaderNodeTexSky")
    s.name = "sky"
    s.sky_type = "NISHITA"
    s.sun_elevation = math.radians(24)
    s.sun_rotation = math.radians(200)
    s.air_density = 1.4
    s.dust_density = 2.0
    s.sun_disc = False
    nt.links.new(s.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    scene.view_settings.exposure = 0.5


def night(scene):
    world = bpy.data.worlds.get("night") or bpy.data.worlds.new("night")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.010, 0.013, 0.024, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.view_settings.exposure = 1.0


def sun(direction, energy=3.2, colour=(1.0, 0.94, 0.86)):
    o = bpy.data.objects.get("sun")
    if o is None:
        d = bpy.data.lights.new("sun", "SUN")
        o = bpy.data.objects.new("sun", d)
        core.collection("lights").objects.link(o)
    o.data.energy = energy
    o.data.color = colour
    o.data.angle = math.radians(2.0)
    o.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return o


def emission(on):
    for name in ("window_lit_lamp", "window_lit", "sodium_on"):
        mat = bpy.data.materials.get(name)
        if mat and mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    n.inputs["Emission Strength"].default_value = core.MATS[name]["emit_strength"] if on else 0.0


def camera(name, loc, target, lens):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.05
    cam.clip_end = 400
    obj = bpy.data.objects.new(name, cam)
    obj.location = Vector(loc)
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    core.collection("cameras").objects.link(obj)
    return obj


EYE = plan.SIDEWALK_Z + 1.6
# name: (location, target, lens, light)   light: "show" (a north-west sun on the front), "town", "night"
SHOTS = {
    "1_three_quarter": ((46.0, -7.5, 10.5), (21.5, -29.5, 3.2), 28, "show"),
    "2_sidewalk": ((15.5, -18.9, EYE), (24.0, -24.0, 3.2), 24, "show"),
    "3_entrance": ((24.6, -19.4, G + 1.6), (22.3, -23.6, 1.5), 28, "show"),
    "4_emergency": ((26.4, -14.6, EYE), (31.0, -23.0, 2.6), 28, "show"),
    "5_town_daylight": ((26.0, -18.9, EYE), (17.5, -24.5, 3.3), 24, "town"),
    "6_night": ((14.5, -12.0, EYE), (16.5, -23.5, 4.6), 30, "night"),
    "7_roof": ((5.0, -8.0, 22.0), (21.0, -30.5, 6.0), 30, "show"),
    "8_west_end": ((3.5, -17.5, EYE), (14.0, -26.0, 3.0), 24, "show"),
    "9_back": ((44.0, -50.0, 6.0), (24.0, -32.0, 3.0), 28, "show"),
}


def main():
    opts = args()
    bpy.ops.wm.read_homefile(use_empty=True)
    core._cache.clear()
    scene = bpy.context.scene
    OUT.mkdir(parents=True, exist_ok=True)
    key, kit_n = kit_house_tris()
    ground()
    obj, lit = build(opts)
    n = tris(obj)
    print(f"TRIANGLES hospital={n} kit_house_{key}={kit_n} ratio={n / kit_n:.2f} (budget 2.5)")
    print("MATERIALS", len(obj.data.materials), sorted(m.name for m in obj.data.materials))
    render_setup(scene, opts)
    street = core.light("street_sodium_P3", (15.0, -11.0, plan.SIDEWALK_Z + plan.LAMP_HEIGHT), "point", 650.0,
                        (1.0, 0.55, 0.22), radius=0.2)
    moon = None
    for name, (loc, tgt, lens, light) in SHOTS.items():
        if opts["only"] and name.split("_")[0] not in opts["only"]:
            continue
        if light == "night":
            night(scene)
            sun((-0.3, 0.5, -0.8), energy=0.06, colour=(0.6, 0.7, 1.0))
            emission(True)
            for o in lit:
                o.hide_render = False
            street.hide_render = False
        else:
            sky(scene)
            if light == "show":
                sun((0.55, -0.62, -0.56))                 # low, from the north-west, onto the front
            else:
                sun((0.794, 0.422, -0.438))               # build.py stills: low, from the west-south-west
            emission(False)
            for o in lit:
                o.hide_render = True
            street.hide_render = True
        cam = camera("cam_" + name, loc, tgt, lens)
        scene.camera = cam
        scene.render.filepath = str(OUT / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", name)


main()
