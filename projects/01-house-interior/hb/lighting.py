"""Phase 6: night lighting.

Three kinds of light, in order of strength:

1. Moonlight: a cool sun from the south-west, through the front windows and
   the stair window. This is the key light and the source of the shafts.
2. The street: the sodium streetlight outside, in plain night fog. There is
   no sky image.
3. Practicals: a warm lamp wherever the props phase left a `lightpoint_*`
   marker, the hall pendant set up to flicker, and a cold flicker from the
   television.

A thin, even haze fills the house so the moonlight reads as beams.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

import plan
from . import core
from .core import MeshBuilder

WARM = (1.0, 0.63, 0.32)         # an old tungsten bulb
COOL_TV = (0.55, 0.70, 1.0)
MOON = (0.42, 0.58, 1.0)

# Light travels this way: from just west of south, coming down at 24 degrees.
MOON_DIRECTION = Vector((0.15, 0.95, 0.0)).normalized() * math.cos(math.radians(24)) \
    + Vector((0, 0, -math.sin(math.radians(24))))

HERO = {
    "hero_porch": dict(at=(6.4, -7.6, 1.25), to=(1.7, -0.6, 1.75), lens=24),
    "hero_hallway": dict(at=(1.86, 0.42, 1.48), to=(1.02, 5.0, 1.22), lens=18),
    "hero_stairs": dict(at=(1.72, 1.02, 1.30), to=(0.42, 4.75, 2.55), lens=19),
    "hero_living": dict(at=(2.95, 0.42, 1.50), to=(6.2, 3.4, 0.85), lens=17),
    "hero_kitchen": dict(at=(2.80, 4.88, 1.52), to=(6.4, 7.2, 0.95), lens=16),
    "hero_bathroom": dict(at=(2.86, 6.66, plan.FFL[1] + 1.55), to=(6.6, 7.5, plan.FFL[1] + 0.75), lens=15),
    "hero_utility": dict(at=(2.68, 5.00, plan.FFL[1] + 1.55), to=(4.0, 5.6, plan.FFL[1] + 0.95), lens=14),
    "hero_landing": dict(at=(1.95, 7.55, plan.FFL[1] + 1.52), to=(1.35, 1.0, plan.FFL[1] + 1.15), lens=17),
    "hero_bedroom": dict(at=(3.55, 0.30, plan.FFL[1] + 1.50), to=(5.55, 3.85, plan.FFL[1] + 0.72), lens=18),
}


FOG = (0.044, 0.052, 0.064)       # the night fog, as in the game (docs/ART_BIBLE.md)


def world(strength=0.5):
    """No sky photograph: in thick fog at night there is only the fog."""
    w = bpy.data.worlds.new("night_fog")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*FOG, 1.0)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w
    return w


def moon(strength=9.0):
    data = bpy.data.lights.new("moon", "SUN")
    data.energy = strength
    data.color = MOON
    data.angle = math.radians(1.2)
    obj = bpy.data.objects.new("light_moon", data)
    obj.rotation_euler = MOON_DIRECTION.to_track_quat("-Z", "Y").to_euler()
    obj.location = (-3.0, -5.0, 9.0)
    obj["note"] = "moonlight; a directional light in the engine"
    # With the haze, in "atmosphere": the night itself, which a scene that
    # links this file and brings its own sky can leave out.
    return core.link(obj, "atmosphere")


def practicals():
    """A light for every lamp marker the props phase left."""
    made = []
    for marker in [o for o in bpy.data.objects if o.name.startswith("lightpoint_")]:
        kind, watts = marker.get("kind", "warm"), float(marker.get("watts", 40.0))
        name = marker.name[len("lightpoint_"):]
        if kind == "tv":
            data = bpy.data.lights.new("tv_glow", "AREA")
            data.shape, data.size, data.size_y = "RECTANGLE", 0.30, 0.22
            data.energy, data.color = watts, COOL_TV
            obj = bpy.data.objects.new("light_tv_flicker", data)
            obj.location = marker.location
            aim = Vector((4.3, 2.3, 0.6)) - Vector(marker.location)          # towards the sofa
            obj.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
            obj["flicker"] = True
        else:
            data = bpy.data.lights.new("lamp_" + name, "POINT")
            data.color = WARM
            data.shadow_soft_size = 0.035
            # Blender's watts are radiant power: roughly a quarter of a tungsten bulb's rating.
            data.energy = watts * (0.07 if kind == "flicker" else 0.11)
            if kind == "sodium":                 # a streetlight: orange, broad and strong
                data.color = (1.0, 0.52, 0.16)
                data.energy = watts * 0.22
                data.shadow_soft_size = 0.15
            if "colour" in marker:
                data.color = tuple(marker["colour"])
            flicker = kind == "flicker"
            obj = bpy.data.objects.new(f"light_{name}_flicker" if flicker else f"light_{name}", data)
            obj.location = marker.location
            if flicker:
                obj["flicker"] = True
                _flicker(data, data.energy)
        obj["kind"] = kind
        obj.visible_volume_scatter = bool(marker.get("haze", True))
        made.append(core.link(obj, "lot" if kind == "sodium" else "lights"))   # the streetlight goes with the street
    return made


def _flicker(light_data, base):
    """Make a light gutter: a noise modifier on its power. The still frames
    are rendered at a dim moment. A game engine drives this itself; the
    `flicker` custom property marks which lights should."""
    light_data.energy = base
    light_data.keyframe_insert("energy", frame=1)
    action = light_data.animation_data.action if light_data.animation_data else None
    if not action:
        return
    curves = []
    try:
        curves = list(action.fcurves)
    except AttributeError:                       # layered actions
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    for curve in curves:
        noise = curve.modifiers.new("NOISE")
        noise.strength = base * 1.1
        noise.scale = 2.2
        noise.phase = 3.0
        noise.offset = 0.0


def haze(density=0.012):
    """Dust and fog in the air: thin, even haze outdoors and in the rooms the
    moon shines into, so its light reads as beams."""
    mb = MeshBuilder()
    e, m = plan.EXT_T + 0.05, 0.02
    w, d, top = plan.WIDTH, plan.DEPTH, 11.0
    f1 = plan.FFL[1]
    boxes = [
        # outdoors: four slabs round the house and one over it
        ((-15.0, -17.0, -0.44), (-e, 16.0, top)), ((w + e, -17.0, -0.44), (22.0, 16.0, top)),
        ((-e, -17.0, -0.44), (w + e, -e, top)), ((-e, d + e, -0.44), (w + e, 16.0, top)),
        ((-e, -e, 8.7), (w + e, d + e, top)),
        # indoors, only where the moon reaches: the front rooms, the hall and the stairwell.
        # The kitchen and bathroom are lit by their own lamps; haze there adds
        # nothing but noise that the denoiser turns into blotches.
        ((plan.PART_X1 + m, m, m), (w - m, plan.DIVIDER_Y0 - m, plan.CEILING - m)),                 # living room
        ((plan.PART_X1 + m, m, f1 + m), (w - m, plan.DIVIDER_Y0 - m, plan.ROOF_Z - m)),             # bedroom
        ((m, m, m), (plan.PART_X0 - m, d - m, plan.CEILING - m)),                                   # hall
        ((m, m, f1 + m), (plan.PART_X0 - m, plan.VOID_Y0 - m, plan.ROOF_Z - m)),                    # front landing
        ((m, plan.VOID_Y0 + m, plan.CEILING + m), (plan.VOID_X1 - m, plan.VOID_Y1 - m, plan.ROOF_Z - m)),   # stairwell
    ]
    for lo, hi in boxes:
        mb.box(lo, hi, "haze")
    obj = mb.build("fog_volume", "atmosphere", recalc=True)
    mat = core.material("haze")
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    vol = tree.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.35
    vol.inputs["Color"].default_value = (0.86, 0.88, 0.92, 1.0)
    tree.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    obj.display_type = "WIRE"
    obj.visible_shadow = False
    obj["export"] = False
    obj["note"] = "render-only haze; use the engine's volumetric fog instead"
    return obj


def cameras():
    made = []
    for name, spec in HERO.items():
        data = bpy.data.cameras.new(name)
        data.lens, data.sensor_width = spec["lens"], 36
        data.clip_start, data.clip_end = 0.05, 100
        obj = bpy.data.objects.new("cam_" + name, data)
        obj.location = spec["at"]
        obj.rotation_euler = (Vector(spec["to"]) - Vector(spec["at"])).to_track_quat("-Z", "Y").to_euler()
        made.append(core.link(obj, "cameras"))
    bpy.context.scene.camera = made[0]
    return made


def render_settings(samples=220, resolution=(1920, 1080), exposure=3.3):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    c = scene.cycles
    c.device = "CPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.012          # dark rooms need the samples: looser than this leaves blotches
    c.use_denoising = True
    for name, value in (("denoising_prefilter", "ACCURATE"), ("denoising_input_passes", "RGB_ALBEDO_NORMAL")):
        try:
            setattr(c, name, value)
        except (AttributeError, TypeError):
            pass
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 7, 4, 3
    c.transmission_bounces, c.volume_bounces, c.transparent_max_bounces = 4, 0, 12
    c.sample_clamp_indirect = 6.0
    c.caustics_reflective = c.caustics_refractive = False
    c.volume_step_rate = 1.0
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    view = scene.view_settings
    view.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            view.look = look
            break
        except TypeError:                        # the name differs between versions
            continue
    view.exposure = exposure


def build():
    world()
    moon()
    practicals()
    haze()
    cameras()
    render_settings()
