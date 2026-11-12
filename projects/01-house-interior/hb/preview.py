"""Preview renders: cutaway views of each storey and eye-level interior views.

Nothing here is saved into the house scene. Cameras, work lights and the
cut-down walls of a cutaway are made for the render and belong to it.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

import plan
from . import core, shell

CENTRE = (plan.WIDTH / 2, plan.DEPTH / 2)

# Eye-level views. `at` and `to` are in metres; lens in millimetres.
INTERIOR = {
    "hall": dict(at=(1.82, 0.55, 1.55), to=(0.95, 5.2, 1.25), lens=17),
    "stairs": dict(at=(2.05, 7.25, 1.50), to=(0.55, 3.2, 1.45), lens=17),
    "living": dict(at=(2.95, 0.45, 1.55), to=(6.3, 3.6, 0.9), lens=17),
    "landing": dict(at=(1.95, 7.55, plan.FFL[1] + 1.55), to=(1.35, 1.0, plan.FFL[1] + 1.15), lens=17),
    "bedroom": dict(at=(3.55, 0.30, plan.FFL[1] + 1.55), to=(5.6, 3.9, plan.FFL[1] + 0.75), lens=17),
    "kitchen": dict(at=(2.80, 4.85, 1.55), to=(6.4, 7.2, 0.95), lens=16),
    "kitchen_sink": dict(at=(6.35, 5.35, 1.60), to=(4.3, 7.9, 0.85), lens=17),
    "kitchen_fridge": dict(at=(3.4, 7.2, 1.55), to=(6.9, 5.3, 0.95), lens=18),
    "bathroom_bath": dict(at=(4.6, 5.0, plan.FFL[1] + 1.6), to=(6.6, 7.7, plan.FFL[1] + 0.6), lens=17),
    "bathroom_sink": dict(at=(3.4, 7.5, plan.FFL[1] + 1.55), to=(5.9, 4.6, plan.FFL[1] + 1.0), lens=17),
    "bathroom": dict(at=(2.85, 6.62, plan.FFL[1] + 1.55), to=(6.6, 7.4, plan.FFL[1] + 0.8), lens=16),
    "utility": dict(at=(2.66, 5.02, plan.FFL[1] + 1.55), to=(4.0, 5.6, plan.FFL[1] + 0.9), lens=14),
}


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens=None, ortho=None, coll="preview"):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
        data.sensor_width = 36
    data.clip_start, data.clip_end = 0.05, 200
    obj = bpy.data.objects.new(name, data)
    obj.location = location
    core.link(obj, coll)
    look_at(obj, target)
    return obj


def axon_camera(storey, azimuth=-38.0, elevation=57.0, scale=15.6):
    """Looking down from the south-east, so the open side of the stair faces us."""
    az, el = math.radians(azimuth), math.radians(elevation)
    direction = Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    target = Vector((CENTRE[0] + 0.2, CENTRE[1] + 0.35, plan.FFL[storey] + 0.6))
    return camera(f"cam_axon_{storey}", target + direction * 40, target, ortho=scale)


def section(storey, cut=2.25):
    """Swap the walls for copies sliced off at `cut` above the storey's floor
    and hide everything above the slice. Returns a function that undoes it."""
    z_cut = plan.FFL[storey] + cut
    hidden = []
    wall_names = {w.name for w in plan.WALLS}
    for obj in bpy.data.objects:
        if obj.type not in {"MESH", "CURVE", "LIGHT"} or obj.hide_render:
            continue
        zs = [(obj.matrix_world @ Vector(c)).z for c in obj.bound_box] if obj.type != "LIGHT" \
            else [obj.matrix_world.translation.z]
        if obj.name in wall_names or min(zs) >= z_cut - 0.25:
            obj.hide_render = True
            hidden.append(obj)
    made = []
    for wall in plan.WALLS:
        obj = shell.build_wall(wall, coll="preview", name="section_" + wall.name, zclip=(-1.0, z_cut))
        if obj:
            made.append(obj)

    def undo():
        for obj in hidden:
            obj.hide_render = False
        for obj in made:
            bpy.data.objects.remove(obj, do_unlink=True)
    return undo


def work_world(strength=1.0, color=(0.78, 0.82, 0.9)):
    world = bpy.data.worlds.new("preview_world")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength
    return world


def work_lights(coll="preview"):
    """Even, neutral light for judging geometry before the real lighting exists:
    a sun for the cutaways, and a soft lamp under the ceiling of every room."""
    made = []
    sun_data = bpy.data.lights.new("preview_sun", "SUN")
    sun_data.energy, sun_data.angle = 3.0, math.radians(8)
    sun = bpy.data.objects.new("preview_sun", sun_data)
    sun.rotation_euler = (math.radians(38), 0, math.radians(-30))
    core.link(sun, coll)
    made.append(sun)
    for room in plan.ROOMS:
        for i, (x0, y0, x1, y1) in enumerate(room.rects):
            area = (x1 - x0) * (y1 - y0)
            if area < 2.0:
                continue
            data = bpy.data.lights.new(f"preview_{room.key}_{i}", "POINT")
            data.energy = 45 * area ** 0.75
            data.shadow_soft_size = 0.35
            data.color = (1.0, 0.95, 0.88)
            obj = bpy.data.objects.new(data.name, data)
            obj.location = ((x0 + x1) / 2, (y0 + y1) / 2, plan.FFL[room.storey] + plan.CEILING - 0.45)
            core.link(obj, coll)
            made.append(obj)
    return made


def setup_cycles(samples=48, resolution=(1600, 900)):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False


def render(view, path, rig="work", samples=48, resolution=(1600, 900), exposure=None):
    """Render one named view to `path`. `rig` is "work" for neutral preview
    lighting or "scene" to use whatever lighting the scene has."""
    scene = bpy.context.scene
    if rig == "work":
        setup_cycles(samples, resolution)
    else:                                      # keep the scene's own render settings
        scene.cycles.samples = samples
        scene.render.resolution_x, scene.render.resolution_y = resolution
    saved_world, saved_cam = scene.world, scene.camera
    undo = None
    temp = []
    own = bpy.data.objects.get("cam_" + view)
    if own is not None and own.type == "CAMERA":          # a camera saved in the scene
        cam = own
    elif view.startswith("axon_"):
        storey = int(view[-1])
        cam = axon_camera(storey)
        undo = section(storey)
    else:
        spec = INTERIOR[view]
        cam = camera("cam_" + view, spec["at"], spec["to"], lens=spec["lens"])
    if cam is not own:
        temp.append(cam)
    if rig == "work":
        scene.world = work_world(1.0 if view.startswith("axon_") else 0.25)
        lights = work_lights()
        temp += lights
        if not view.startswith("axon_"):
            lights[0].data.energy = 1.0              # sun only matters outside the windows
        scene.view_settings.exposure = 0.0
    scene.camera = cam
    if exposure is not None:
        scene.view_settings.exposure = exposure
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)

    if undo:
        undo()
    for obj in temp:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and data.users == 0:
            (bpy.data.cameras if isinstance(data, bpy.types.Camera) else bpy.data.lights).remove(data)
    scene.world, scene.camera = saved_world, saved_cam
    return path
