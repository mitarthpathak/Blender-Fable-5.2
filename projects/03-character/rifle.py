"""Build the carbine: the first-pass rifle's design, modelled properly.

    blender -b --python projects/03-character/rifle.py
    blender -b --python projects/03-character/rifle.py -- --no-render

An original design (it copies no real firearm): flat-top upper with a full
length accessory rail, slotted free-float handguard, skeleton stock, curved
magazine, compact reflex optic and a stubby fore grip. Sized like a real
5.56 carbine: 0.88 m overall, 0.35 m length of pull.

The parts are modelled in "gun space" (u forward along the bore, z up from the
bore, x to the shooter's left), chamfered, joined and unwrapped. Wear is not
painted by hand: Cycles bakes where the edges, cavities and materials are, and
`compose()` turns those masks into base colour, roughness and metallic maps.

Writes rifle.blend, export/rifle.fbx (+ .glb), textures/rifle_*.jpg and
renders/rifle_{side,detail}.png. The muzzle points along -Y, the origin is at
the top of the pistol grip.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
TEX = HERE / "textures"
EXPORT = HERE / "export"
RENDERS = HERE / "renders"
SIZE = 2048

BORE_Z = 0.058        # the bore is this far above the origin
GRIP_U = 0.080        # and the origin this far behind gun-space zero

# Material ids as baked into the mask map's blue channel.
IDS = {"alu": 0.0, "steel": 0.3, "polymer": 0.6, "grip": 0.6, "rubber": 0.8, "glass": 1.0}


def window():
    return bpy.context.temp_override(window=bpy.context.window_manager.windows[0])


def P(x: float, u: float, z: float) -> Vector:
    """Gun space to Blender space."""
    return Vector((x, -(u + GRIP_U), z + BORE_Z))


# --- Mesh helpers ------------------------------------------------------------

def _loft(bm, ring_a, ring_b):
    n = len(ring_a)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))


def prism(profile, half_width, centre=0.0):
    """A side profile [(u, z), ...] given thickness across the gun."""
    bm = bmesh.new()
    a = [bm.verts.new(P(centre - half_width, u, z)) for u, z in profile]
    b = [bm.verts.new(P(centre + half_width, u, z)) for u, z in profile]
    bm.faces.new(a)
    bm.faces.new(tuple(reversed(b)))
    _loft(bm, a, b)
    return bm


def box(u0, u1, z0, z1, x0, x1):
    return prism([(u0, z0), (u1, z0), (u1, z1), (u0, z1)], (x1 - x0) / 2.0, (x0 + x1) / 2.0)


def extrude(section, u0, u1, scale0=1.0, scale1=1.0):
    """A cross-section [(x, z), ...] run along the bore from u0 to u1."""
    bm = bmesh.new()
    a = [bm.verts.new(P(x * scale0, u0, z * scale0)) for x, z in section]
    b = [bm.verts.new(P(x * scale1, u1, z * scale1)) for x, z in section]
    bm.faces.new(a)
    bm.faces.new(tuple(reversed(b)))
    _loft(bm, a, b)
    return bm


def lathe(profile, segments=16, z=0.0, x=0.0):
    """Turned parts: [(u, radius), ...] around an axis parallel to the bore."""
    bm = bmesh.new()
    rings = []
    for u, radius in profile:
        rings.append([bm.verts.new(P(x + math.sin(t) * radius, u, z + math.cos(t) * radius))
                      for t in (2.0 * math.pi * k / segments for k in range(segments))])
    bm.faces.new(rings[0])
    bm.faces.new(tuple(reversed(rings[-1])))
    for ring_a, ring_b in zip(rings, rings[1:]):
        _loft(bm, ring_a, ring_b)
    return bm


def pin(u, z, radius, x0, x1, segments=10):
    """A cylinder across the gun: pins, buttons, knobs."""
    bm = bmesh.new()
    rings = [[bm.verts.new(P(x, u + math.sin(t) * radius, z + math.cos(t) * radius))
              for t in (2.0 * math.pi * k / segments for k in range(segments))] for x in (x0, x1)]
    bm.faces.new(rings[0])
    bm.faces.new(tuple(reversed(rings[1])))
    _loft(bm, rings[0], rings[1])
    return bm


class Gun:
    def __init__(self):
        self.parts = []
        self.materials = {name: bpy.data.materials.new(name) for name in ("alu", "steel", "polymer", "grip",
                                                                         "rubber", "glass")}
        for mat in self.materials.values():
            mat.use_nodes = True

    def _object(self, bm, name):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def add(self, name, bm, material, bevel=0.0010, segments=1, cut=()):
        obj = self._object(bm, name)
        if cut:
            obj = self._cut(obj, cut)
        if bevel:
            chamfer(obj, bevel, segments)
        sharpen(obj)
        obj.data.materials.clear()                 # a boolean can leave an empty slot behind
        obj.data.materials.append(self.materials[material])
        for polygon in obj.data.polygons:
            polygon.material_index = 0
        self.parts.append(obj)
        return obj

    def _cut(self, obj, cutters):
        """Boolean the cutter meshes out of the part."""
        merged = bmesh.new()
        for cutter in cutters:
            bmesh.ops.recalc_face_normals(cutter, faces=cutter.faces)
            scratch = bpy.data.meshes.new("cut")
            cutter.to_mesh(scratch)
            cutter.free()
            merged.from_mesh(scratch)
            bpy.data.meshes.remove(scratch)
        tool = self._object(merged, obj.name + ".cutter")
        modifier = obj.modifiers.new("cut", "BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.object = tool
        solvers = [item.identifier for item in modifier.bl_rna.properties["solver"].enum_items]
        modifier.solver = "EXACT" if "EXACT" in solvers else solvers[0]
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
        result = bpy.data.objects.new(obj.name, mesh)
        bpy.context.scene.collection.objects.link(result)
        for stale in (obj, tool):
            bpy.data.objects.remove(stale, do_unlink=True)
        return result


def chamfer(obj, width, segments):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(30.0)]
    bmesh.ops.bevel(bm, geom=edges, offset=width, offset_type="OFFSET", segments=segments, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    bm.to_mesh(obj.data)
    bm.free()


def sharpen(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for edge in bm.edges:
        edge.smooth = len(edge.link_faces) == 2 and edge.calc_face_angle(0.0) < math.radians(35.0)
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(obj.data)
    bm.free()


# --- The carbine -------------------------------------------------------------

def mag_front(z: float) -> float:
    """Front edge of the magazine: straight in the well, curving forward below it."""
    t = max(0.0, (-0.085 - z) / 0.165)
    return 0.084 + 0.004 * t + 0.020 * t * t


def build_gun() -> bpy.types.Object:
    g = Gun()

    # Upper receiver: flat top, ejection port cut into the right side (-x).
    upper = [(-0.100, -0.024), (0.095, -0.024), (0.095, 0.019), (0.088, 0.026), (-0.093, 0.026), (-0.100, 0.019)]
    g.add("upper", prism(upper, 0.0200), "alu", 0.0014,
          cut=[box(-0.004, 0.060, -0.010, 0.011, -0.0300, -0.0165)])
    g.add("bolt_carrier", box(-0.003, 0.059, -0.009, 0.010, -0.0172, -0.0160), "steel", 0.0)
    g.add("bolt_face", box(0.030, 0.050, -0.006, 0.007, -0.0180, -0.0165), "steel", 0.0005)
    g.add("dust_cover", box(-0.004, 0.060, -0.0235, -0.0115, -0.0222, -0.0200), "alu", 0.0006)
    g.add("deflector", prism([(-0.034, -0.012), (-0.010, -0.012), (-0.010, 0.014), (-0.026, 0.014)], 0.0035,
                             -0.0225), "alu", 0.0012)
    g.add("charging_handle", prism([(-0.126, 0.004), (-0.099, 0.004), (-0.099, 0.019), (-0.120, 0.019),
                                    (-0.126, 0.013)], 0.0250), "alu", 0.0010)

    # Lower receiver with the magazine well and the buffer tower.
    lower = [(0.090, -0.024), (0.094, -0.084), (0.022, -0.094), (0.018, -0.062), (-0.046, -0.062),
             (-0.052, -0.058), (-0.100, -0.058), (-0.122, -0.040), (-0.122, 0.024), (-0.100, 0.024),
             (-0.100, -0.024)]
    g.add("lower", prism(lower, 0.0172), "alu", 0.0014)
    g.add("magwell_flare", prism([(0.096, -0.074), (0.097, -0.088), (0.020, -0.098), (0.019, -0.086)], 0.0188),
          "alu", 0.0012)
    g.add("castle_nut", lathe([(-0.136, 0.0150), (-0.136, 0.0185), (-0.123, 0.0185), (-0.123, 0.0150)], 12),
          "steel", 0.0008)
    guard = [(0.022, -0.090), (0.012, -0.103), (-0.042, -0.103), (-0.055, -0.070),
             (-0.051, -0.070), (-0.040, -0.0995), (0.0105, -0.0995), (0.0185, -0.090)]
    g.add("trigger_guard", prism(guard, 0.0065), "alu", 0.0006)
    g.add("trigger", prism([(-0.013, -0.060), (-0.006, -0.060), (-0.008, -0.074), (-0.003, -0.090),
                            (-0.007, -0.092), (-0.014, -0.076)], 0.0032), "steel", 0.0006)
    for name, u, z in (("pin_front", 0.072, -0.036), ("pin_rear", -0.088, -0.030)):
        g.add(name, pin(u, z, 0.0040, -0.0184, 0.0184), "steel", 0.0005)
    g.add("selector_hub", pin(-0.062, -0.034, 0.0058, 0.0165, 0.0196), "steel", 0.0005)
    g.add("selector_lever", box(-0.066, -0.040, -0.0365, -0.0315, 0.0190, 0.0218), "steel", 0.0006)
    g.add("mag_release", box(0.024, 0.036, -0.046, -0.034, -0.0200, -0.0170), "steel", 0.0008)
    g.add("bolt_catch", prism([(0.034, -0.030), (0.047, -0.030), (0.047, -0.008), (0.040, -0.004),
                               (0.034, -0.010)], 0.0016, 0.0186), "steel", 0.0006)

    # Pistol grip, raked back, rounded for the hand.
    grip = [(-0.048, -0.060), (-0.058, -0.090), (-0.066, -0.116), (-0.082, -0.168), (-0.128, -0.162),
            (-0.119, -0.116), (-0.111, -0.082), (-0.108, -0.056)]
    g.add("grip", prism(grip, 0.0148), "grip", 0.0050, segments=2)

    # Magazine: follows mag_front(), with pressed ribs and a floor plate.
    levels = [-0.060, -0.085, -0.125, -0.165, -0.205, -0.246]
    body = [(mag_front(z), z) for z in levels] + [(mag_front(z) - 0.060, z - 0.004 * (z < -0.2)) for z in
                                                  reversed(levels)]
    g.add("magazine", prism(body, 0.0112), "polymer", 0.0016)
    for index, (near, far) in enumerate(((0.008, 0.016), (0.026, 0.034), (0.044, 0.052))):
        rib_levels = [-0.100, -0.140, -0.180, -0.215, -0.238]
        rib = [(mag_front(z) - near, z) for z in rib_levels] + [(mag_front(z) - far, z) for z in
                                                                reversed(rib_levels)]
        g.add(f"mag_rib_{index}", prism(rib, 0.0122), "polymer", 0.0008)
    plate_z = -0.246
    g.add("mag_floorplate", prism([(mag_front(plate_z) + 0.004, plate_z + 0.002),
                                   (mag_front(plate_z) + 0.003, plate_z - 0.010),
                                   (mag_front(plate_z) - 0.064, plate_z - 0.014),
                                   (mag_front(plate_z) - 0.065, plate_z - 0.002)], 0.0130), "polymer", 0.0016)

    # Handguard: an eight-sided free-float tube with slots on three faces.
    w, top, bottom, c = 0.0215, 0.026, -0.028, 0.0110
    section = [(-w + c, top), (w - c, top), (w, top - c), (w, bottom + c), (w - c, bottom), (-w + c, bottom),
               (-w, bottom + c), (-w, top - c)]
    slots = []
    for k in range(6):
        u = 0.128 + k * 0.043
        slots.append(box(u, u + 0.031, -0.0045, 0.0030, w - 0.0040, w + 0.01))
        slots.append(box(u, u + 0.031, -0.0045, 0.0030, -w - 0.01, -w + 0.0040))
        slots.append(box(u, u + 0.031, bottom - 0.01, bottom + 0.0040, -0.0037, 0.0037))
    g.add("handguard", extrude(section, 0.097, 0.400), "alu", 0.0012, cut=slots)
    g.add("barrel_nut", extrude(section, 0.093, 0.106, 1.06, 1.06), "alu", 0.0012)
    g.add("handguard_cap", extrude(section, 0.400, 0.406, 1.0, 0.86), "alu", 0.0006)

    # Accessory rail along the whole top: a crenellated profile.
    rail, u = [(-0.098, 0.0255), (0.398, 0.0255)], 0.398
    while u > -0.094:
        rail += [(u, 0.0355), (u - 0.0048, 0.0355), (u - 0.0048, 0.0325), (u - 0.0100, 0.0325)]
        u -= 0.0100
    rail += [(-0.098, 0.0325)]
    g.add("rail", prism(rail, 0.0106), "alu", 0.0)

    # Barrel and muzzle device.
    g.add("barrel", lathe([(0.380, 0.0092), (0.474, 0.0092)], 16), "steel", 0.0)
    hider = [(0.470, 0.0118), (0.478, 0.0118), (0.480, 0.0106), (0.514, 0.0106), (0.516, 0.0114),
             (0.522, 0.0114), (0.522, 0.0062), (0.490, 0.0062)]
    vents = []
    for angle in (-100.0, -50.0, 0.0, 50.0, 100.0):
        vent = box(0.484, 0.510, 0.0080, 0.0200, -0.0016, 0.0016)
        bmesh.ops.rotate(vent, verts=vent.verts, cent=P(0.0, 0.0, 0.0),
                         matrix=Matrix.Rotation(math.radians(angle), 3, "Y"))
        vents.append(vent)
    g.add("flash_hider", lathe(hider, 16), "steel", 0.0006, cut=vents)

    # Skeleton stock on a buffer tube.
    g.add("buffer_tube", lathe([(-0.300, 0.0145), (-0.123, 0.0145)], 14), "alu", 0.0)
    g.add("stock_top", prism([(-0.166, 0.027), (-0.330, 0.027), (-0.346, 0.019), (-0.346, -0.022),
                              (-0.166, -0.022)], 0.0190), "polymer", 0.0030, segments=2)
    g.add("stock_strut", prism([(-0.186, -0.020), (-0.212, -0.020), (-0.334, -0.092), (-0.334, -0.114)], 0.0105),
          "polymer", 0.0020)
    g.add("stock_butt", prism([(-0.328, 0.031), (-0.352, 0.031), (-0.356, -0.040), (-0.350, -0.120),
                               (-0.328, -0.120)], 0.0210), "polymer", 0.0030, segments=2)
    g.add("butt_pad", prism([(-0.3515, 0.031), (-0.360, 0.027), (-0.364, -0.040), (-0.358, -0.117),
                             (-0.3495, -0.120), (-0.3555, -0.040)], 0.0210), "rubber", 0.0016)
    g.add("stock_latch", prism([(-0.200, -0.022), (-0.252, -0.022), (-0.247, -0.035), (-0.206, -0.031)], 0.0075),
          "polymer", 0.0014)

    # Compact reflex optic: clamp, hooded window, two lenses.
    g.add("optic_base", prism([(-0.046, 0.0355), (0.020, 0.0355), (0.020, 0.044), (0.014, 0.048),
                               (-0.040, 0.048), (-0.046, 0.044)], 0.0130), "alu", 0.0010)
    g.add("optic_clamp", box(-0.022, -0.004, 0.0365, 0.0455, 0.0130, 0.0195), "steel", 0.0012)
    hood = [(-0.042, 0.047), (0.014, 0.047), (0.010, 0.086), (0.002, 0.092), (-0.036, 0.092), (-0.042, 0.086)]
    g.add("optic_hood", prism(hood, 0.0175), "alu", 0.0018,
          cut=[box(-0.080, 0.060, 0.0545, 0.0850, -0.0130, 0.0130)])
    g.add("optic_lens_rear", box(-0.0360, -0.0345, 0.0540, 0.0855, -0.0135, 0.0135), "glass", 0.0)
    g.add("optic_lens_front", box(0.0050, 0.0065, 0.0540, 0.0855, -0.0135, 0.0135), "glass", 0.0)
    g.add("optic_turret", pin(-0.016, 0.070, 0.0065, -0.0215, -0.0175), "steel", 0.0006)
    g.add("optic_dial", box(-0.024, -0.008, 0.092, 0.096, -0.0080, 0.0080), "alu", 0.0010)

    # Folded back-up sights.
    for name, u0, u1 in (("sight_front", 0.360, 0.392), ("sight_rear", -0.094, -0.062)):
        g.add(name, prism([(u0, 0.0355), (u1, 0.0355), (u1, 0.0420), (u1 - 0.004, 0.0455), (u0 + 0.004, 0.0455),
                           (u0, 0.0420)], 0.0100), "alu", 0.0008)

    # Stubby fore grip clamped under the handguard.
    g.add("foregrip_clamp", box(0.200, 0.252, -0.0370, -0.0275, -0.0150, 0.0150), "alu", 0.0010)
    g.add("foregrip", prism([(0.206, -0.036), (0.246, -0.036), (0.242, -0.062), (0.238, -0.108),
                             (0.212, -0.108), (0.209, -0.062)], 0.0135), "grip", 0.0045, segments=2)

    with window():
        bpy.ops.object.select_all(action="DESELECT")
        for part in g.parts:
            part.select_set(True)
        bpy.context.view_layer.objects.active = g.parts[0]
        bpy.ops.object.join()
    rifle = g.parts[0]
    rifle.name = rifle.data.name = "rifle"
    return rifle


def unwrap(obj):
    with window():
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.004)
        bpy.ops.object.mode_set(mode="OBJECT")


# --- Baking ------------------------------------------------------------------

def _mask_nodes(tree, ident):
    """R: worn convex edges. G: cavities where dirt gathers. B: material id."""
    n, link = tree.nodes, tree.links.new
    bevel = n.new("ShaderNodeBevel")
    bevel.samples = 8
    bevel.inputs["Radius"].default_value = 0.0022
    geometry = n.new("ShaderNodeNewGeometry")
    dot = n.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    link(bevel.outputs["Normal"], dot.inputs[0])
    link(geometry.outputs["True Normal"], dot.inputs[1])
    edge = n.new("ShaderNodeMapRange")
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.995, 0.86
    link(dot.outputs["Value"], edge.inputs["Value"])

    near = n.new("ShaderNodeAmbientOcclusion")
    near.samples, near.only_local = 8, False
    near.inputs["Distance"].default_value = 0.006
    convex = n.new("ShaderNodeMapRange")
    convex.inputs["From Min"].default_value, convex.inputs["From Max"].default_value = 0.72, 0.94
    link(near.outputs["AO"], convex.inputs["Value"])
    wear = n.new("ShaderNodeMath")
    wear.operation = "MULTIPLY"
    link(edge.outputs["Result"], wear.inputs[0])
    link(convex.outputs["Result"], wear.inputs[1])

    far = n.new("ShaderNodeAmbientOcclusion")
    far.samples = 12
    far.inputs["Distance"].default_value = 0.035
    cavity = n.new("ShaderNodeMapRange")
    cavity.inputs["From Min"].default_value, cavity.inputs["From Max"].default_value = 0.95, 0.35
    link(far.outputs["AO"], cavity.inputs["Value"])

    combine = n.new("ShaderNodeCombineColor")
    link(wear.outputs["Value"], combine.inputs[0])
    link(cavity.outputs["Result"], combine.inputs[1])
    combine.inputs[2].default_value = ident
    return combine.outputs["Color"]


def _noise_nodes(tree):
    """R: broad blotches. G: fine scratches along the gun. B: grain."""
    n, link = tree.nodes, tree.links.new
    coords = n.new("ShaderNodeTexCoord")
    channels = []
    for scale, stretch, detail, lo, hi in ((16.0, (1, 1, 1), 5.0, 0.30, 0.70),
                                           (420.0, (1.0, 0.07, 1.0), 2.0, 0.67, 0.75),
                                           (1400.0, (1, 1, 1), 2.0, 0.25, 0.75)):
        mapping = n.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = stretch
        link(coords.outputs["Object"], mapping.inputs["Vector"])
        noise = n.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = detail
        link(mapping.outputs["Vector"], noise.inputs["Vector"])
        ramp = n.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = lo, hi
        link(noise.outputs["Fac"], ramp.inputs["Value"])
        channels.append(ramp.outputs["Result"])
    combine = n.new("ShaderNodeCombineColor")
    for index, channel in enumerate(channels):
        link(channel, combine.inputs[index])
    return combine.outputs["Color"]


def _surface_nodes(tree, name):
    """What the normal map records: rounded edges plus each material's texture."""
    n, link = tree.nodes, tree.links.new
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bevel = n.new("ShaderNodeBevel")
    bevel.samples = 8
    bevel.inputs["Radius"].default_value = 0.0012 if name != "glass" else 0.0
    coords = n.new("ShaderNodeTexCoord")
    strength = {"alu": 0.10, "steel": 0.14, "polymer": 0.30, "grip": 0.55, "rubber": 0.5, "glass": 0.0}[name]
    if name in ("grip", "rubber"):
        height = n.new("ShaderNodeTexVoronoi")           # moulded stipple
        height.inputs["Scale"].default_value = 520.0 if name == "grip" else 300.0
        source = height.outputs["Distance"]
    else:
        height = n.new("ShaderNodeTexNoise")             # bead-blast or mould grain
        height.inputs["Scale"].default_value = 1800.0 if name != "polymer" else 1100.0
        height.inputs["Detail"].default_value = 2.0
        source = height.outputs["Fac"]
    link(coords.outputs["Object"], height.inputs["Vector"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0003
    link(source, bump.inputs["Height"])
    link(bevel.outputs["Normal"], bump.inputs["Normal"])
    link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bsdf.outputs["BSDF"]


def bake_maps(obj):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    images = {}
    for kind in ("masks", "noise", "normal"):
        image = bpy.data.images.new(f"bake_{kind}", SIZE, SIZE, alpha=False, is_data=True)
        images[kind] = image
        for material in obj.data.materials:
            tree = material.node_tree
            tree.nodes.clear()
            output = tree.nodes.new("ShaderNodeOutputMaterial")
            if kind == "normal":
                tree.links.new(_surface_nodes(tree, material.name), output.inputs["Surface"])
            else:
                colour = _mask_nodes(tree, IDS[material.name]) if kind == "masks" else _noise_nodes(tree)
                emission = tree.nodes.new("ShaderNodeEmission")
                tree.links.new(colour, emission.inputs["Color"])
                tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
            target = tree.nodes.new("ShaderNodeTexImage")
            target.image = image
            tree.nodes.active = target
        with window():
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.bake(type="NORMAL" if kind == "normal" else "EMIT", margin=6, use_clear=True)
        print(f"  ~ baked {kind}")
    return images


def pixels(image) -> np.ndarray:
    data = np.empty(SIZE * SIZE * 4, dtype=np.float32)
    image.pixels.foreach_get(data)
    return data.reshape(SIZE, SIZE, 4)


def write(name: str, data: np.ndarray, colour: bool):
    """Save an (H, W) or (H, W, 3) array of display values as a JPEG."""
    if data.ndim == 2:
        data = np.repeat(data[..., None], 3, axis=2)
    rgba = np.concatenate((np.clip(data, 0.0, 1.0), np.ones((SIZE, SIZE, 1), np.float32)), axis=2)
    image = bpy.data.images.new(name, SIZE, SIZE, alpha=False, is_data=not colour)
    image.pixels.foreach_set(rgba.astype(np.float32).ravel())
    image.filepath_raw = str(TEX / f"{name}.jpg")
    image.file_format = "JPEG"
    image.save(quality=93)
    bpy.data.images.remove(image)
    print(f"  ~ textures/{name}.jpg")


def lerp(a, b, t):
    t = t[..., None] if (np.ndim(a) == 3 or np.ndim(b) == 1) and np.ndim(t) == 2 else t
    return a + (b - a) * t


def compose(images):
    """Masks to PBR maps. Colours are sRGB display values."""
    TEX.mkdir(exist_ok=True)
    masks, noise = pixels(images["masks"]), pixels(images["noise"])
    edge, cavity, ident = masks[..., 0], masks[..., 1], masks[..., 2]
    blotch, scratch, grain = noise[..., 0], noise[..., 1], noise[..., 2]
    alu, steel = ident < 0.15, (ident >= 0.15) & (ident < 0.45)
    polymer, rubber, glass = (ident >= 0.45) & (ident < 0.7), (ident >= 0.7) & (ident < 0.9), ident >= 0.9
    metal_part = alu | steel

    # How much of the finish is gone: edges first, then scratches and rubbed patches.
    # Thresholded, so the finish chips and scuffs instead of fading like fog.
    rubbed = np.clip((blotch - 0.80) * 4.0, 0.0, 1.0)
    raw = edge * (0.30 + 1.0 * blotch) + scratch * 0.42 * (blotch > 0.45) + rubbed * 0.30 * grain
    wear = np.clip((raw - 0.22) / 0.30, 0.0, 1.0)
    wear = wear * wear * (3.0 - 2.0 * wear)

    def rgb(r, g, b):
        return np.array([r, g, b], dtype=np.float32)

    base = np.zeros((SIZE, SIZE, 3), np.float32)
    rough = np.zeros((SIZE, SIZE), np.float32)
    metallic = np.zeros((SIZE, SIZE), np.float32)

    tone = (0.90 + 0.20 * blotch)[..., None]
    for mask, coat, bare, coat_rough, bare_rough in (
            (alu, rgb(0.185, 0.188, 0.200), rgb(0.70, 0.70, 0.72), 0.50, 0.30),      # anodised aluminium
            (steel, rgb(0.250, 0.248, 0.250), rgb(0.62, 0.61, 0.59), 0.60, 0.34)):    # phosphated steel
        base[mask] = lerp(coat * tone, bare, wear)[mask]
        rough[mask] = (coat_rough + (bare_rough - coat_rough) * wear + (grain - 0.5) * 0.10)[mask]
        metallic[mask] = 1.0

    worn = np.clip(wear * 0.8 + rubbed * 0.4, 0.0, 1.0)
    base[polymer] = lerp(rgb(0.098, 0.097, 0.095) * tone, rgb(0.190, 0.185, 0.178), worn * 0.7)[polymer]
    rough[polymer] = (0.64 - 0.26 * worn + (grain - 0.5) * 0.08)[polymer]
    base[rubber] = (rgb(0.085, 0.085, 0.085) * tone)[rubber]
    rough[rubber] = 0.88
    base[glass] = rgb(0.16, 0.30, 0.27)
    rough[glass] = 0.05
    metallic[glass] = 1.0

    # Rust blooms on the steel, never on aluminium or plastic.
    rust = steel * np.clip((blotch - 0.62) * 3.5, 0.0, 1.0) * np.clip(grain * 1.6 - 0.2, 0.0, 1.0) * 0.75
    base = lerp(base, rgb(0.36, 0.20, 0.12) * (0.7 + 0.6 * grain[..., None]), rust)
    rough = rough + (0.86 - rough) * rust
    metallic = metallic * (1.0 - rust * 0.9)

    # Dust and old oil in the recesses.
    dirt = np.clip(cavity * 1.5 - 0.2, 0.0, 1.0) * (0.45 + 0.55 * blotch) * (~glass)
    base = lerp(base, rgb(0.30, 0.265, 0.22), dirt * 0.55)
    rough = rough + (0.90 - rough) * dirt * 0.7
    metallic = metallic * (1.0 - dirt * 0.6)

    write("rifle_basecolor", base, True)
    write("rifle_roughness", np.clip(rough, 0.04, 1.0), False)
    write("rifle_metallic", metallic, False)
    write("rifle_normal", pixels(images["normal"])[..., :3], False)
    for image in images.values():
        bpy.data.images.remove(image)
    return {"wear": float(wear[metal_part].mean()), "dirt": float(dirt.mean())}


def final_material(obj):
    mat = bpy.data.materials.new("rifle")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")

    def texture(name, colour, y):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(TEX / f"rifle_{name}.jpg"), check_existing=False)
        node.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        node.location = (-620, y)
        return node

    links.new(texture("basecolor", True, 420).outputs["Color"], bsdf.inputs["Base Color"])
    links.new(texture("metallic", False, 140).outputs["Color"], bsdf.inputs["Metallic"])
    links.new(texture("roughness", False, -140).outputs["Color"], bsdf.inputs["Roughness"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-300, -420)
    links.new(texture("normal", False, -420).outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

    old = list(obj.data.materials)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
    for material in old:
        bpy.data.materials.remove(material)


def report(obj):
    mesh = obj.data
    triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
    xs, ys, zs = zip(*(tuple(v.co) for v in mesh.vertices))
    print(f"RIFLE triangles {triangles}  length {max(ys) - min(ys):.3f} m  height {max(zs) - min(zs):.3f} m  "
          f"width {max(xs) - min(xs):.3f} m")


def export(obj):
    EXPORT.mkdir(exist_ok=True)
    with window():
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.fbx(
            filepath=str(EXPORT / "rifle.fbx"), use_selection=True, object_types={"MESH"},
            apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y", mesh_smooth_type="EDGE",
            path_mode="COPY", embed_textures=True, bake_anim=False)
        bpy.ops.export_scene.gltf(
            filepath=str(EXPORT / "rifle.glb"), export_format="GLB", use_selection=True, export_apply=True,
            export_yup=True, export_image_format="JPEG", export_jpeg_quality=92)
    for name in ("rifle.fbx", "rifle.glb"):
        print(f"  + export/{name}  {(EXPORT / name).stat().st_size / 1e6:.1f} MB")


# --- Renders -----------------------------------------------------------------

def render(obj):
    RENDERS.mkdir(exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 160
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"

    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.22, 0.23, 0.25, 1.0)
    background.inputs["Strength"].default_value = 0.5
    scene.world = world

    backdrop = bpy.data.meshes.new("backdrop")
    backdrop.from_pydata([(-6, -6, -0.42), (6, -6, -0.42), (6, 6, -0.42), (-6, 6, -0.42)], [], [(0, 1, 2, 3)])
    grey = bpy.data.materials.new("studio_grey")
    grey.use_nodes = True
    bsdf = next(n for n in grey.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.16, 0.16, 0.17, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    backdrop.materials.append(grey)
    scene.collection.objects.link(bpy.data.objects.new("backdrop", backdrop))

    centre = Vector((0.0, -0.16, 0.02))

    def aim(target_obj, target):
        target_obj.rotation_euler = (target - target_obj.location).to_track_quat("-Z", "Y").to_euler()

    lights = []
    for name, location, energy, size, colour in (
            ("key", (-1.6, -1.2, 1.9), 150.0, 1.6, (1.0, 0.96, 0.90)),
            ("fill", (-1.2, 1.6, 0.6), 60.0, 2.0, (0.85, 0.92, 1.0)),
            ("rim", (1.4, 0.4, 1.5), 130.0, 1.2, (0.90, 0.95, 1.0)),
            ("strip", (-0.4, -0.3, 2.2), 90.0, 2.6, (1.0, 1.0, 1.0))):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size, data.color = energy, size, colour
        light = bpy.data.objects.new(name, data)
        light.location = location
        scene.collection.objects.link(light)
        aim(light, centre)
        lights.append(light)

    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera

    # 1: the right side, square on.
    camera.data.lens = 110.0
    camera.location = (-3.2, -0.165, 0.0)
    aim(camera, Vector((0.0, -0.165, 0.0)))
    scene.render.resolution_x, scene.render.resolution_y = 2000, 900
    scene.render.filepath = str(RENDERS / "rifle_side.png")
    bpy.ops.render.render(write_still=True)
    print("  + renders/rifle_side.png")

    # 2: three-quarter view from the front left, close on the receiver and optic.
    camera.data.lens = 70.0
    camera.location = (0.62, -0.88, 0.34)
    aim(camera, Vector((0.0, -0.20, 0.03)))
    lights[0].location = (1.5, -1.4, 1.8)
    aim(lights[0], centre)
    lights[2].location = (-1.4, 0.5, 1.4)
    aim(lights[2], centre)
    scene.render.resolution_x, scene.render.resolution_y = 1800, 1100
    scene.render.filepath = str(RENDERS / "rifle_detail.png")
    bpy.ops.render.render(write_still=True)
    print("  + renders/rifle_detail.png")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_homefile(use_empty=True)
    rifle = build_gun()
    report(rifle)
    unwrap(rifle)
    stats = compose(bake_maps(rifle))
    print(f"  finish worn away on {stats['wear'] * 100:.0f}% of the metal, dirt on {stats['dirt'] * 100:.0f}%")
    final_material(rifle)
    export(rifle)
    with window():
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "rifle.blend"), compress=True, relative_remap=True)
    if "--no-render" not in args:
        render(rifle)


if __name__ == "__main__":
    main()
