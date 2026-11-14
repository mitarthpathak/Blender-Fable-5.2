"""Build film.blend: the house and the town together, lit for film.

    blender -b --python projects/04-halden-ridge-film/build.py

Nothing is copied. The house (projects/01-house-interior/house.blend) and the
town (projects/03-town/town.blend) are LINKED as libraries, by relative path,
one collection at a time; a fix saved in either file shows up here the next
time film.blend is opened. Neither source file is touched.

What is left out of each library:

  house.blend   lot          the seven yard and street objects the town replaces,
                             and the house's own streetlight
                atmosphere   its moon and its render-only haze
                lightpoints, cameras, colliders, preview
  town.blend    collision, kit

The file holds eight scenes, one per lighting setup: 06:00, 10:00, 17:00 and
03:00, each Clear and Foggy. All eight show the same linked collections; each
has its own sky, sun or moon, fog and exposure. Lamps (the house's and the
street's) are one collection, switched off in the two 10:00 scenes.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
HOUSE = "//../01-house-interior/house.blend"
TOWN = "//../03-town/town.blend"
HOUSE_SKIP = {"lot", "atmosphere", "lightpoints", "cameras", "colliders", "preview"}
TOWN_SKIP = {"collision", "kit"}
LAMP_COLLECTIONS = {"lights"}                      # in either library: the lamps

# Halden Ridge is nowhere, but it is somewhere like this.
LATITUDE, LONGITUDE = 42.5, -72.5
MONTH, DAY, UTC_OFFSET = 10, 25, -4                # late October, Eastern Daylight Time
F1 = 3.06

TIMES = {"0600": 6.0, "1000": 10.0, "1700": 17.0, "0300": 3.0}
WEATHER = ("clear", "foggy")

# Six cameras with real lenses (35 mm full frame), an aperture, and what each focuses on.
CAMERAS = {
    "cam_1_street": dict(at=(-4.6, -18.6, 1.7), to=(3.4, -0.5, 3.0), lens=35, fstop=5.6, focus=(1.8, -1.0, 2.0)),
    "cam_2_porch": dict(at=(2.35, -7.6, 1.55), to=(1.85, -0.6, 1.45), lens=28, fstop=4.0, focus=(1.8, -1.2, 1.3)),
    "cam_3_front_door": dict(at=(1.72, 3.3, 1.50), to=(1.78, 0.0, 1.25), lens=32, fstop=2.8, focus=(1.78, 0.05, 1.2),
                             indoors=True),
    "cam_4_hallway": dict(at=(1.86, 0.5, 1.46), to=(1.0, 5.2, 1.25), lens=24, fstop=2.8, focus=(1.2, 3.2, 1.2),
                          indoors=True),
    "cam_5_kitchen": dict(at=(2.85, 4.92, 1.50), to=(6.3, 7.2, 1.0), lens=24, fstop=2.8, focus=(4.45, 6.0, 0.8),
                          indoors=True),
    "cam_6_landing": dict(at=(1.95, 7.5, F1 + 1.50), to=(1.35, 1.0, F1 + 1.15), lens=24, fstop=2.8,
                          focus=(1.2, 3.0, F1 + 1.0), indoors=True),
}
MOVE = dict(name="cam_move_approach", start=(2.6, -10.6, 1.62), end=(1.95, -3.4, 1.56), to=(1.8, -0.4, 1.5),
            lens=28, fstop=4.0, frames=120)       # five seconds at 24 fps: up the path to the porch


# --- The sun ------------------------------------------------------------------

def sun_position(hour_local: float):
    """Elevation and azimuth (clockwise from north) of the sun, in degrees,
    by the NOAA approximation. Good to a fraction of a degree."""
    day = sum((31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[:MONTH - 1]) + DAY
    hour_utc = hour_local - UTC_OFFSET
    g = 2.0 * math.pi / 365.0 * (day - 1 + (hour_utc - 12.0) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    minutes = hour_utc * 60.0 + eqtime + 4.0 * LONGITUDE
    hour_angle = math.radians(minutes / 4.0 - 180.0)
    lat = math.radians(LATITUDE)
    cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)
    zenith = math.acos(max(-1.0, min(1.0, cos_zenith)))
    azimuth = math.degrees(math.atan2(math.sin(hour_angle), math.cos(hour_angle) * math.sin(lat)
                                      - math.tan(decl) * math.cos(lat))) + 180.0
    return 90.0 - math.degrees(zenith), azimuth % 360.0


def direction_to(elevation_deg, azimuth_deg) -> Vector:
    """Unit vector towards a point in the sky. +Y is north, +X east."""
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    return Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))


def sky_type() -> str:
    """The physical sky model this Blender has: read from the node's own
    enum, since its name changed between versions."""
    items = [i.identifier for i in bpy.types.ShaderNodeTexSky.bl_rna.properties["sky_type"].enum_items]
    for wanted in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        if wanted in items:
            return wanted
    return items[0]


# --- Linking ------------------------------------------------------------------

def link_library(path: str, skip: set[str]):
    """Link every top-level collection of a .blend except those in `skip`.
    Returns {name: collection}."""
    absolute = bpy.path.abspath(path)
    with bpy.data.libraries.load(absolute, link=True, relative=True) as (src, dst):
        scene_names = list(src.scenes)
        dst.collections = list(src.collections)
    linked = {c.name: c for c in dst.collections if c is not None}
    children = {child.name for c in linked.values() for child in c.children}
    top = {name: c for name, c in linked.items() if name not in children and name not in skip}
    return top, scene_names


def group(name: str, members) -> bpy.types.Collection:
    coll = bpy.data.collections.new(name)
    for member in members:
        coll.children.link(member)
    return coll


# --- Rigs ---------------------------------------------------------------------

def make_world(name, hour, weather, kind):
    elevation, azimuth = sun_position(hour)
    world = bpy.data.worlds.new("sky_" + name)
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputWorld")
    bg = tree.nodes.new("ShaderNodeBackground")
    tree.links.new(bg.outputs["Background"], out.inputs["Surface"])
    night = elevation < -18.0
    if night:
        # No sun, no twilight: starlight and the glow of a town, which in fog is all there is.
        bg.inputs["Color"].default_value = (0.020, 0.028, 0.045, 1.0) if weather == "clear" else (0.040, 0.046, 0.058, 1.0)
        bg.inputs["Strength"].default_value = 0.012 if weather == "clear" else 0.02
    else:
        sky = tree.nodes.new("ShaderNodeTexSky")
        sky.sky_type = kind
        # The sky model gives nothing below the horizon; before sunrise it is held
        # just under it and dimmed, which is what twilight looks like.
        shown = max(elevation, -4.0)
        for prop, value in (("sun_elevation", math.radians(shown)), ("sun_rotation", -math.radians(azimuth)),
                            ("sun_disc", False), ("altitude", 250.0), ("air_density", 1.0),
                            ("dust_density", 1.0 if weather == "clear" else 4.0), ("aerosol_density", 1.0 if weather == "clear" else 4.0),
                            ("ozone_density", 1.0)):
            if hasattr(sky, prop):
                try:
                    setattr(sky, prop, value)
                except (TypeError, ValueError):
                    pass
        tree.links.new(sky.outputs["Color"], bg.inputs["Color"])
        twilight = 1.0 if elevation > 0 else max(0.06, 1.0 + (elevation + 4.0 - 0.0) / 14.0 if elevation < -4.0 else 1.0)
        if elevation < -4.0:
            twilight = max(0.3, 1.0 - (-4.0 - elevation) / 14.0)
        bg.inputs["Strength"].default_value = 0.08 * twilight * (0.75 if weather == "foggy" else 1.0)
    world["sun_elevation"], world["sun_azimuth"] = elevation, azimuth
    return world, elevation, azimuth


def make_sun(name, elevation, azimuth, weather, coll):
    """The sun as a lamp, in the direction the sky has it: the sky texture's
    own disc is off, so shadows and fog beams come from this. At night it is
    the moon: cool, dim, high in the south-west."""
    data = bpy.data.lights.new("sun_" + name, "SUN")
    if elevation < -18.0:
        elevation, azimuth = 38.0, 232.0
        data.color = (0.55, 0.68, 1.0)
        data.energy = 0.035 if weather == "clear" else 0.02
        data.angle = math.radians(0.6)
        label = "moon"
    elif elevation <= 0.5:
        data.energy = 0.0                                   # below the horizon: the sky does the work
        data.angle = math.radians(1.0)
        elevation = 1.0
        label = "sun"
    else:
        # Warmer and weaker the lower it stands: more air in the way.
        air = 1.0 / max(math.sin(math.radians(elevation)), 0.05)
        t = min(1.0, (air - 1.0) / 9.0)
        data.color = (1.0, 0.94 - 0.36 * t, 0.86 - 0.62 * t)
        data.energy = 4.2 * math.exp(-0.16 * (air - 1.0)) * (0.45 if weather == "foggy" else 1.0)
        data.angle = math.radians(0.53 if weather == "clear" else 6.0)
        label = "sun"
    obj = bpy.data.objects.new(f"{label}_{name}", data)
    obj.rotation_euler = (-direction_to(elevation, azimuth)).to_track_quat("-Z", "Y").to_euler()
    obj.location = direction_to(elevation, azimuth) * 60.0
    coll.objects.link(obj)
    return obj


def make_fog(name, hour, coll):
    """Ground fog as a bounded box of thin volume over the whole town: thick
    enough to close the street at 30 m, shallow enough that the sky still
    lights it. (A world volume would be infinitely deep and black.)"""
    mesh = bpy.data.meshes.new("fog_" + name)
    lo, hi = Vector((-48.0, -70.0, -0.6)), Vector((56.0, 30.0, 13.0))
    verts = [(x, y, z) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    mat = bpy.data.materials.new("fog_" + name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    vol = tree.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.03 if hour < 5.0 else 0.045     # thinner at night: the lamps would white it out
    vol.inputs["Anisotropy"].default_value = 0.4
    vol.inputs["Color"].default_value = (0.82, 0.85, 0.88, 1.0)
    tree.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new("fog_" + name, mesh)
    obj.display_type = "WIRE"
    obj.visible_shadow = False
    coll.objects.link(obj)
    return obj


EXPOSURE = {("0600", "clear"): 4.2, ("0600", "foggy"): 3.4, ("1000", "clear"): 0.0, ("1000", "foggy"): 0.3,
            ("1700", "clear"): 0.6, ("1700", "foggy"): 1.0, ("0300", "clear"): 3.6, ("0300", "foggy"): 1.8}
INDOORS_STOPS = {"0600": -0.6, "1000": 5.0, "1700": 2.6, "0300": 0.4 }     # opening up for an interior


def render_settings(scene, samples=96, resolution=(1920, 1080)):
    scene.render.engine = "CYCLES"
    c = scene.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 8, 4, 4
    c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 6, 1, 16
    c.sample_clamp_indirect = 8.0
    c.caustics_reflective = c.caustics_refractive = False
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_motion_blur = False
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Base Contrast", "Base Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue


def make_cameras():
    coll = bpy.data.collections.new("cameras")
    made = {}
    for name, spec in CAMERAS.items():
        data = bpy.data.cameras.new(name)
        data.lens, data.sensor_width = spec["lens"], 36.0
        data.clip_start, data.clip_end = 0.05, 400.0
        data.dof.use_dof = True
        data.dof.aperture_fstop = spec["fstop"]
        data.dof.focus_distance = (Vector(spec["focus"]) - Vector(spec["at"])).length
        obj = bpy.data.objects.new(name, data)
        obj.location = spec["at"]
        obj.rotation_euler = (Vector(spec["to"]) - Vector(spec["at"])).to_track_quat("-Z", "Y").to_euler()
        obj["indoors"] = bool(spec.get("indoors", False))
        coll.objects.link(obj)
        made[name] = obj
    # the move: a slow push up the path, eased at both ends
    data = bpy.data.cameras.new(MOVE["name"])
    data.lens, data.sensor_width = MOVE["lens"], 36.0
    data.clip_start, data.clip_end = 0.05, 400.0
    data.dof.use_dof = True
    data.dof.aperture_fstop = MOVE["fstop"]
    obj = bpy.data.objects.new(MOVE["name"], data)
    obj["indoors"] = False
    coll.objects.link(obj)
    target = Vector(MOVE["to"])
    for frame in range(1, MOVE["frames"] + 1):
        t = (frame - 1) / (MOVE["frames"] - 1)
        ease = t * t * (3.0 - 2.0 * t)
        obj.location = Vector(MOVE["start"]).lerp(Vector(MOVE["end"]), ease)
        obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
        obj.keyframe_insert("location", frame=frame)
        obj.keyframe_insert("rotation_euler", frame=frame)
        data.dof.focus_distance = (target - obj.location).length
        data.dof.keyframe_insert("focus_distance", frame=frame)
    made[MOVE["name"]] = obj
    return coll, made


def exclude(scene, collection_name, value=True):
    """Switch a collection off in every view layer of a scene."""
    def walk(layer):
        if layer.collection.name == collection_name:
            layer.exclude = value
        for child in layer.children:
            walk(child)
    for view_layer in scene.view_layers:
        walk(view_layer.layer_collection)


def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    target = HERE / "film.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(target))       # so "//" means this folder from the start

    house, _ = link_library(HOUSE, HOUSE_SKIP)
    town, _ = link_library(TOWN, TOWN_SKIP)
    lamps = [c for libs in (house, town) for n, c in libs.items() if n in LAMP_COLLECTIONS]
    g_house = group("house", [c for n, c in house.items() if n not in LAMP_COLLECTIONS])
    g_town = group("town", [c for n, c in town.items() if n not in LAMP_COLLECTIONS])
    g_lamps = group("lamps", lamps)
    g_cams, cams = make_cameras()
    kind = sky_type()

    first = bpy.context.scene
    scenes = []
    for clock, hour in TIMES.items():
        for weather in WEATHER:
            name = f"{clock}_{weather}"
            scene = first if not scenes else bpy.data.scenes.new(name)
            scene.name = name
            for coll in (g_house, g_town, g_lamps, g_cams):
                scene.collection.children.link(coll)
            rig = bpy.data.collections.new("rig_" + name)
            scene.collection.children.link(rig)
            world, elevation, azimuth = make_world(name, hour, weather, kind)
            scene.world = world
            make_sun(name, elevation, azimuth, weather, rig)
            if weather == "foggy":
                make_fog(name, hour, rig)
            if clock == "1000":
                exclude(scene, "lamps")                      # nobody has a light on at ten in the morning
            render_settings(scene)
            scene.view_settings.exposure = EXPOSURE[clock, weather]
            scene["indoors_stops"] = INDOORS_STOPS[clock]
            scene["clock"], scene["weather"] = clock, weather
            scene.camera = cams["cam_1_street"]
            scene.frame_start, scene.frame_end = 1, MOVE["frames"]
            scene.unit_settings.system = "METRIC"
            scenes.append(scene)
            print(f"RIG {name}: sun elevation {elevation:6.1f}, azimuth {azimuth:6.1f}, sky model {kind}")

    bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True, relative_remap=True)
    for lib in bpy.data.libraries:                           # forward slashes: the file must open on any system
        lib.filepath = lib.filepath.replace("\\", "/")
    bpy.ops.wm.save_mainfile(compress=True, relative_remap=False)
    print("LIBRARIES", [lib.filepath for lib in bpy.data.libraries])
    print(f"saved {target} ({target.stat().st_size / 1e6:.2f} MB), {len(scenes)} scenes, "
          f"{len([o for o in bpy.data.objects if o.library])} linked objects")


main()
