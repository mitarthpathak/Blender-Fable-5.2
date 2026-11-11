"""Build Halden Ridge in Blender from plan.py.

Runs in Blender (4.5 or later), in the background:

    blender -b -P projects/03-town/build.py -- kit       # part 3: the kit, laid out and rendered
    blender -b -P projects/03-town/build.py -- town      # part 4: town.blend and game/assets/town/town.glb
    blender -b -P projects/03-town/build.py -- stills    # part 4: three Cycles stills (needs town.blend)

Options after the stage: --samples N, --res WxH, --only name (stills).

Run derive.py and assets.py first (plain Python) so the textures exist.
"""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import assets  # noqa: E402
import plan  # noqa: E402
import tk.core  # noqa: E402
import tk.house_kit  # noqa: E402
import tk.street_kit  # noqa: E402

for mod in (plan, assets, tk.core, tk.house_kit, tk.street_kit):
    importlib.reload(mod)
from tk import core, house_kit, street_kit  # noqa: E402

BLEND = HERE / "town.blend"
KIT_BLEND = HERE / "kit.blend"
GLB = ROOT / "game" / "assets" / "town" / "town.glb"
HOUSE_GLB = ROOT / "projects" / "01-house-interior" / "house.glb"
RENDERS = HERE / "renders"


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"stage": a[0] if a else "town", "samples": 64, "res": (1280, 720), "only": None}
    for i, v in enumerate(a):
        if v == "--samples":
            opts["samples"] = int(a[i + 1])
        elif v == "--res":
            w, h = a[i + 1].split("x")
            opts["res"] = (int(w), int(h))
        elif v == "--only":
            opts["only"] = a[i + 1]
    return opts


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    core._cache.clear()
    street_kit._meshes.clear()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return scene


def render_setup(scene, samples, res):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"


def camera(name, loc, target, lens=24.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start = 0.05
    cam.clip_end = 400
    obj = bpy.data.objects.new(name, cam)
    obj.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    core.collection("cameras").objects.link(obj)
    return obj


def world_night(scene, strength=1.0, fog=True):
    """Night sky colour and a volume fog in the world, as in Godot."""
    world = bpy.data.worlds.new("night")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.020, 0.026, 0.036, 1)
    bg.inputs["Strength"].default_value = strength
    if fog:
        vol = nt.nodes.new("ShaderNodeVolumePrincipled")
        vol.inputs["Density"].default_value = 0.035
        vol.inputs["Color"].default_value = (0.75, 0.8, 0.88, 1)
        vol.inputs["Anisotropy"].default_value = 0.4
        nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
    scene.cycles.volume_step_rate = 4.0
    scene.cycles.volume_max_steps = 256


def moon(strength=0.35):
    data = bpy.data.lights.new("moon", "SUN")
    data.energy = strength
    data.color = (0.55, 0.68, 1.0)
    data.angle = math.radians(1.0)
    obj = bpy.data.objects.new("moon", data)
    obj.rotation_euler = (math.radians(55), 0, math.radians(200))
    core.collection("lights").objects.link(obj)
    return obj


# --- Stages ---------------------------------------------------------------------

def build_town():
    scene = fresh()
    houses = house_kit.kit_houses("houses")
    curbs = street_kit.ground("ground")
    street_kit.house_paths(houses, "ground")
    street_kit.road_damage("ground_detail")
    tops, lamps = street_kit.poles("poles")
    street_kit.wires(tops, "poles")
    street_kit.fences("fences")
    street_kit.props("props")
    street_kit.trees("trees")
    street_kit.cars("cars")
    street_kit.blockers("blockers")
    street_kit.collision(curbs, houses, "collision")
    house_kit.kit_reference("kit")
    # the glowing window in L3 and its porch light
    for o in bpy.data.objects:
        if o.name.startswith("lit_window_"):
            o.data.energy = 12.0
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.name.startswith("street_sodium"):
            o.data.energy = 250.0
    scene["town_plan"] = "projects/03-town/plan.py"
    return scene, houses


def save_and_export(scene):
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=True)
    GLB.parent.mkdir(parents=True, exist_ok=True)
    # export everything except the kit catalogue
    for o in bpy.data.objects:
        o.select_set(False)
    keep = [o for o in bpy.data.objects if not any(c.name == "kit" for c in o.users_collection)]
    for o in keep:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True, export_apply=False,
        export_lights=True, export_cameras=False, export_extras=True, export_yup=True,
        export_image_format="AUTO", export_vertex_color="ACTIVE", export_all_vertex_colors=False,
        export_texcoords=True, export_normals=True, export_materials="EXPORT",
    )
    print("exported", GLB, GLB.stat().st_size // 1024, "KB")


def stats():
    tris = 0
    meshes = set()
    objs = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or any(c.name in ("kit", "collision") for c in o.users_collection):
            continue
        objs += 1
        if o.data.name not in meshes:
            meshes.add(o.data.name)
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"STATS objects={objs} unique_meshes={len(meshes)} triangles={tris} materials={len(bpy.data.materials)}")


def stage_kit(opts):
    scene = fresh()
    # the kit catalogue, visible this time, plus one of every street prop
    house_kit.kit_reference("kit")
    kit = bpy.data.collections["kit"]
    kit.hide_render = False
    kit.hide_viewport = False
    for i, o in enumerate(sorted(kit.objects, key=lambda o: o.name)):
        o.location = (0.0, 0.0, 0.0)
        row, col = divmod(i, 5)
        o.location = (col * 11.0, row * 11.0, 0.45)
    # one full kit house, built as in the town
    lot = plan.HOUSES[1]
    mb, m, *_ = house_kit.build_house(lot, __import__("random").Random(101))
    o = mb.build("kit_house_sample", "kit")
    o.location = (-14.0, 2.0, 0.45)
    sk = street_kit
    row = -12.0
    items = [
        ("pole", sk._pole_mesh), ("lamp_on", lambda: sk._lamp_mesh("on")), ("lamp_broken", lambda: sk._lamp_mesh("broken")),
        ("mailbox", sk._mailbox), ("trash_can", sk._trash_can), ("hydrant", sk._hydrant), ("sawhorse", sk._sawhorse),
        ("jersey", sk._jersey), ("leaf_pile", lambda: sk._leaf_pile(1)), ("tree", lambda: sk._tree(201)),
        ("grass", lambda: sk._grass_clump(1)), ("manhole", sk._manhole),
    ]
    for i, (name, fn) in enumerate(items):
        ob = fn().build("kit_" + name, "kit")
        ob.location = (i * 3.2, row, 0.45 if name in ("trash_can", "hydrant", "sawhorse", "jersey", "leaf_pile", "grass",
                                                      "manhole", "pole", "lamp_on", "lamp_broken") else 0.0)
    for i, (kind, paint, state) in enumerate((("sedan", (0.30, 0.31, 0.33), "abandoned"),
                                              ("wagon", (0.33, 0.24, 0.16), "on_blocks"),
                                              ("sedan", (0.18, 0.22, 0.27), "crashed"))):
        ob = sk.car_mesh(kind, core.mul(paint, 1 / 0.75), 10 + i, crashed=state == "crashed",
                         flat=state != "on_blocks", on_blocks=state == "on_blocks").build(f"kit_car_{state}", "kit")
        ob.location = (i * 6.0, -20.0, 0.0)
    fm = core.MeshBuilder()
    rng = __import__("random").Random(2)
    sk.picket_run(fm, (20.0, -20.0), (26.0, -20.0), rng, gap=(23.0, -20.0))
    sk.chainlink_run(fm, (20.0, -23.0), (26.0, -23.0))
    sk.tall_fence_run(fm, (20.0, -26.0), (26.0, -26.0), rng)
    fm.build("kit_fences", "kit")
    gm = core.MeshBuilder()
    gm.box((-24, -32, -0.5), (60, 40, 0.0), "lawn_overgrown", skip="-z")
    gm.build("kit_floor", "kit")

    render_setup(scene, opts["samples"], opts["res"])
    world = bpy.data.worlds.new("overcast")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.5
    sun.angle = math.radians(8)
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(50), 0, math.radians(35))
    core.collection("lights").objects.link(so)
    shots = {
        "02_kit_houses": ((22, -14, 15), (22, 8, 3), 24),
        "02_kit_house_sample": ((-2, -14, 5), (-10.5, 3, 4.5), 28),
        "02_kit_street": ((14, -36, 6), (14, -15, 1.5), 26),
    }
    RENDERS.mkdir(exist_ok=True)
    for name, (loc, tgt, lens) in shots.items():
        cam = camera("cam_" + name, loc, tgt, lens)
        scene.camera = cam
        scene.render.filepath = str(RENDERS / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", name)
    bpy.ops.wm.save_as_mainfile(filepath=str(KIT_BLEND), compress=True, relative_remap=True)


def stage_town(opts):
    scene, houses = build_town()
    stats()
    save_and_export(scene)


STILLS = {
    # camera position, target (Blender axes), lens
    "front_door": ((1.78, 0.6, 1.6), (2.6, -18.0, 0.9), 20),
    "junction": ((9.5, -9.4, 1.65), (2.0, -24.0, 1.4), 22),
    "side_street": ((5.6, -27.0, 1.65), (1.2, -50.0, 1.6), 24),
}


def stage_stills(opts):
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    with bpy.context.temp_override(window=bpy.context.window_manager.windows[0]) if bpy.context.window_manager.windows \
            else _null():
        bpy.ops.import_scene.gltf(filepath=str(HOUSE_GLB))
    # the house's own yard, road, fence, pole and lamp are replaced by the town
    for o in list(bpy.data.objects):
        base = o.name.split(".")[0]
        if base in plan.HOUSE_HIDE or o.name.startswith("cam_hero"):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.data.objects:
        if any(c.name in ("collision", "kit") for c in o.users_collection):
            o.hide_render = True
    render_setup(scene, opts["samples"], opts["res"])
    world_night(scene)
    moon()
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.name.startswith("street_sodium"):
            o.data.energy = 900.0
            o.data.shadow_soft_size = 0.2
    RENDERS.mkdir(exist_ok=True)
    for name, (loc, tgt, lens) in STILLS.items():
        if opts["only"] and opts["only"] != name:
            continue
        cam = camera("cam_still_" + name, loc, tgt, lens)
        scene.camera = cam
        scene.render.filepath = str(RENDERS / f"03_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", name)


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


if __name__ == "__main__":
    o = args()
    {"kit": stage_kit, "town": stage_town, "stills": stage_stills}[o["stage"]](o)
