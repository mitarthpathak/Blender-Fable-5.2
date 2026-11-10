"""Build an original third-person-shooter soldier and rifle.

    blender -b --python projects/02-soldier/build.py

The body is grown from a stick figure with Blender's Skin modifier, so it is
one connected surface in a clean T-pose, which is what Mixamo's auto-rigger
wants. Gear is modelled on top and joined in. All colour, roughness and
surface relief are then baked to one 2K texture set.

Outputs, next to this file:
    soldier.blend                 the scene
    export/soldier_tpose.fbx      character, T-pose, textures embedded
    export/rifle.fbx              the rifle, separate
    textures/soldier_*.png        2K base colour, roughness, normal
    renders/soldier_{front,side,back}.png
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TEX = HERE / "textures"
TARGET_TRIS = 26000
TEXTURE_SIZE = 2048


# --- helpers ----------------------------------------------------------------

def mat(name, color, rough=0.7, metal=0.0, camo=None, weave=0.0):
    """A flat or camouflaged material. These exist only to be baked."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    base = (*color, 1.0)
    if camo:
        noise = t.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 9.0
        noise.inputs["Detail"].default_value = 2.5
        ramp = t.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        stops = [(0.0, camo[0]), (0.44, color), (0.56, camo[1]), (0.66, color)]
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (*stops[0][1], 1)
        ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = stops[1][0], (*stops[1][1], 1)
        for pos, col in stops[2:]:
            e = ramp.color_ramp.elements.new(pos)
            e.color = (*col, 1)
        t.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        t.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = base
    if weave:
        fine = t.nodes.new("ShaderNodeTexNoise")
        fine.inputs["Scale"].default_value = 260.0
        bump = t.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = weave
        bump.inputs["Distance"].default_value = 0.002
        t.links.new(fine.outputs["Fac"], bump.inputs["Height"])
        t.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def new_object(name, bm, material, smooth=True):
    mesh = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    if smooth:
        mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box(name, lo, hi, material, bevel=0.0, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    lo, hi = Vector(lo), Vector(hi)
    size, centre = hi - lo, (lo + hi) / 2
    for v in bm.verts:
        v.co = Vector((v.co.x * size.x, v.co.y * size.y, v.co.z * size.z)) + centre
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1, affect="EDGES")
    return new_object(name, bm, material, smooth)


def ellipsoid(name, centre, radii, material, u=16, v=10, cut_below=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    for vert in bm.verts:
        vert.co = Vector((vert.co.x * radii[0], vert.co.y * radii[1], vert.co.z * radii[2])) + Vector(centre)
    if cut_below is not None:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, cut_below),
                               plane_no=(0, 0, -1), clear_outer=True)
    return new_object(name, bm, material)


def cylinder(name, a, b, radius, material, segments=10, radius_b=None):
    a, b = Vector(a), Vector(b)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius,
                          radius2=radius if radius_b is None else radius_b, depth=(b - a).length)
    rot = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(a + b) / 2, verts=bm.verts)
    return new_object(name, bm, material)


def mirror_x(obj):
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = obj.name + "_L"
    for v in copy.data.vertices:
        v.co.x = -v.co.x
    copy.data.flip_normals()
    bpy.context.scene.collection.objects.link(copy)
    return copy


def join(objects, name):
    objects = [o for o in objects if o]
    base = objects[0]
    with bpy.context.temp_override(active_object=base, object=base, selected_objects=objects,
                                   selected_editable_objects=objects):
        bpy.ops.object.join()
    base.name = name
    base.data.name = name
    return base


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# --- the body ---------------------------------------------------------------

def body(materials):
    """A T-posed figure from a stick skeleton. +X is the character's left,
    -Y is forward, Z is up; feet on the ground at Z=0."""
    # name: (position, radius, parent)
    J = {
        "pelvis": ((0, 0.01, 0.96), 0.150, None),
        "waist": ((0, 0.01, 1.10), 0.145, "pelvis"),
        "chest": ((0, 0.0, 1.30), 0.178, "waist"),
        "collar": ((0, 0.0, 1.44), 0.120, "chest"),
        "neck": ((0, 0.0, 1.535), 0.068, "collar"),
        "head": ((0, -0.01, 1.645), 0.112, "neck"),
    }
    for s, tag in ((1, "L"), (-1, "R")):
        J.update({
            f"hip{tag}": ((s * 0.100, 0.01, 0.88), 0.108, "pelvis"),
            f"knee{tag}": ((s * 0.108, 0.0, 0.50), 0.078, f"hip{tag}"),
            f"ankle{tag}": ((s * 0.110, 0.02, 0.10), 0.062, f"knee{tag}"),
            f"toe{tag}": ((s * 0.115, -0.17, 0.05), 0.052, f"ankle{tag}"),
            f"shoulder{tag}": ((s * 0.215, 0.0, 1.435), 0.088, "collar"),
            f"elbow{tag}": ((s * 0.475, 0.0, 1.435), 0.062, f"shoulder{tag}"),
            f"wrist{tag}": ((s * 0.725, 0.0, 1.435), 0.044, f"elbow{tag}"),
            f"palm{tag}": ((s * 0.795, -0.004, 1.435), 0.036, f"wrist{tag}"),
            f"thumb1{tag}": ((s * 0.790, -0.060, 1.428), 0.014, f"palm{tag}"),
            f"thumb2{tag}": ((s * 0.825, -0.092, 1.424), 0.011, f"thumb1{tag}"),
        })
        # four fingers, fanned slightly apart
        for k, y in enumerate((-0.036, -0.012, 0.012, 0.036)):
            length = (0.082, 0.092, 0.086, 0.068)[k]
            J[f"f{k}a{tag}"] = ((s * 0.845, y * 1.05, 1.435), 0.0115, f"palm{tag}")
            J[f"f{k}b{tag}"] = ((s * (0.845 + length), y * 1.65, 1.435), 0.0095, f"f{k}a{tag}")

    names = list(J)
    mesh = bpy.data.meshes.new("body")
    mesh.from_pydata([J[n][0] for n in names], [(names.index(J[n][2]), i) for i, n in enumerate(names) if J[n][2]], [])
    obj = bpy.data.objects.new("body", mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("skin", "SKIN")
    for i, n in enumerate(names):
        r = J[n][1]
        data = mesh.skin_vertices[0].data[i]
        flat = 0.62 if n.startswith("palm") else (0.82 if n in ("chest", "waist", "pelvis") else 1.0)
        data.radius = (r, r * flat) if not n.startswith("palm") else (r * flat, r)
        data.use_root = n == "pelvis"
    skin.use_smooth_shade = True
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.levels = 3
    deps = bpy.context.evaluated_depsgraph_get()
    deps.update()
    final = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    obj.modifiers.clear()
    obj.data = final
    final.shade_smooth()

    # Paint the body by region: balaclava, uniform, gloves, boots.
    for key in ("uniform", "black", "boots"):
        final.materials.append(materials[key])
    for poly in final.polygons:
        c = poly.center
        if c.z > 1.51 or abs(c.x) > 0.715:
            poly.material_index = 1                    # head and hands
        elif c.z < 0.27:
            poly.material_index = 2
        else:
            poly.material_index = 0
    return obj


# --- gear -------------------------------------------------------------------

def gear(m):
    parts = []
    add = parts.append

    # Helmet: high-cut shell, side rails, shroud, strap. Head top is about 1.75.
    add(ellipsoid("helmet", (0, 0.0, 1.672), (0.132, 0.146, 0.132), m["helmet"], u=18, v=12, cut_below=1.655))
    for s in (1, -1):
        add(box("helmet_rail", (s * 0.122, -0.07, 1.668), (s * 0.140, 0.07, 1.698), m["black"], bevel=0.004))
        add(ellipsoid("ear_cup", (s * 0.124, 0.01, 1.625), (0.022, 0.04, 0.048), m["black"], u=10, v=6))
        add(box("chin_strap", (s * 0.098, -0.03, 1.56), (s * 0.106, -0.012, 1.67), m["gear"]))
    add(box("nvg_shroud", (-0.03, -0.158, 1.725), (0.03, -0.13, 1.77), m["black"], bevel=0.004))
    add(box("helmet_patch", (-0.035, 0.132, 1.69), (0.035, 0.146, 1.73), m["gear"]))
    # Goggles over the balaclava: no face visible.
    add(ellipsoid("goggles", (0, -0.098, 1.628), (0.092, 0.04, 0.036), m["visor"], u=14, v=8))
    add(box("goggle_frame_top", (-0.096, -0.132, 1.654), (0.096, -0.08, 1.664), m["black"], bevel=0.003))
    add(box("goggle_frame_bot", (-0.096, -0.132, 1.592), (0.096, -0.08, 1.602), m["black"], bevel=0.003))
    for s in (1, -1):
        add(box("goggle_strap", (s * 0.098, -0.09, 1.615), (s * 0.118, 0.10, 1.642), m["black"]))

    # Plate carrier.
    add(box("plate_front", (-0.165, -0.215, 1.13), (0.165, -0.14, 1.43), m["gear"], bevel=0.018))
    add(box("plate_back", (-0.165, 0.125, 1.13), (0.165, 0.195, 1.44), m["gear"], bevel=0.018))
    for s in (1, -1):
        add(box("cummerbund", (s * 0.165, -0.15, 1.14), (s * 0.20, 0.14, 1.29), m["gear"], bevel=0.01))
        add(box("shoulder_strap", (s * 0.075, -0.15, 1.42), (s * 0.135, 0.14, 1.505), m["gear"], bevel=0.012))
        add(box("side_pouch", (s * 0.198, -0.06, 1.15), (s * 0.245, 0.05, 1.27), m["gear"], bevel=0.008))
    for k, x in enumerate((-0.098, 0.0, 0.098)):           # three magazine pouches
        add(box(f"mag_pouch_{k}", (x - 0.045, -0.262, 1.14), (x + 0.045, -0.213, 1.285), m["gear"], bevel=0.006))
        add(box(f"mag_{k}", (x - 0.03, -0.254, 1.285), (x + 0.03, -0.222, 1.315), m["black"], bevel=0.003))
    add(box("admin_pouch", (-0.10, -0.245, 1.31), (0.10, -0.213, 1.40), m["gear"], bevel=0.006))
    add(box("radio", (0.08, 0.193, 1.26), (0.135, 0.238, 1.42), m["black"], bevel=0.006))
    add(cylinder("antenna", (0.108, 0.215, 1.42), (0.108, 0.215, 1.62), 0.005, m["black"], segments=6))
    add(box("hydration", (-0.10, 0.193, 1.17), (0.055, 0.228, 1.41), m["gear"], bevel=0.012))

    # Belt line.
    add(box("belt_front", (-0.18, -0.15, 1.0), (0.18, -0.118, 1.06), m["gear"], bevel=0.005))
    add(box("belt_back", (-0.18, 0.13, 1.0), (0.18, 0.16, 1.06), m["gear"], bevel=0.005))
    for s in (1, -1):
        add(box("belt_side", (s * 0.158, -0.14, 1.0), (s * 0.19, 0.15, 1.06), m["gear"], bevel=0.005))
    add(box("holster", (-0.245, -0.07, 0.78), (-0.19, 0.03, 0.99), m["black"], bevel=0.01))
    add(box("pistol_grip", (-0.24, -0.02, 0.985), (-0.2, 0.03, 1.07), m["black"], bevel=0.008))
    add(box("dump_pouch", (0.19, 0.0, 0.84), (0.25, 0.11, 1.0), m["gear"], bevel=0.012))
    add(box("belt_pouch", (0.05, -0.19, 0.99), (0.125, -0.148, 1.07), m["gear"], bevel=0.006))

    # Pads and boots.
    for s in (1, -1):
        add(ellipsoid("knee_pad", (s * 0.108, -0.066, 0.50), (0.076, 0.045, 0.09), m["black"], u=12, v=8))
        add(ellipsoid("elbow_pad", (s * 0.475, 0.05, 1.435), (0.066, 0.036, 0.06), m["black"], u=10, v=6))
        add(box("boot_sole", (s * 0.115 - 0.06, -0.235, 0.0), (s * 0.115 + 0.06, 0.09, 0.03), m["black"], bevel=0.008))
        add(box("boot_cuff", (s * 0.110 - 0.072, -0.055, 0.21), (s * 0.110 + 0.072, 0.095, 0.28), m["boots"], bevel=0.012))
        add(box("glove_cuff", (s * 0.69, -0.05, 1.388), (s * 0.735, 0.05, 1.482), m["black"], bevel=0.008))
        add(box("thigh_pocket", (s * 0.175, -0.05, 0.62), (s * 0.215, 0.06, 0.78), m["uniform"], bevel=0.008))
    return parts


# --- the rifle --------------------------------------------------------------

def rifle(m):
    """An original carbine: boxy upper, slotted handguard, folding-style
    skeleton stock, angled magazine, compact optic. Along -Y, grip at origin."""
    p = []
    add = p.append
    add(box("receiver", (-0.022, -0.16, 0.03), (0.022, 0.13, 0.105), m["gun"], bevel=0.005))
    add(box("lower", (-0.02, -0.10, -0.01), (0.02, 0.10, 0.035), m["gun"], bevel=0.004))
    add(box("handguard", (-0.026, -0.46, 0.035), (0.026, -0.16, 0.10), m["gun_dark"], bevel=0.006))
    for k in range(6):                                              # lightening slots as raised ribs
        y = -0.43 + k * 0.045
        for s in (1, -1):
            add(box("hg_rib", (s * 0.026, y, 0.052), (s * 0.030, y + 0.028, 0.083), m["gun"]))
    add(box("top_rail", (-0.011, -0.45, 0.105), (0.011, 0.12, 0.117), m["gun_dark"]))
    add(cylinder("barrel", (0, -0.16, 0.068), (0, -0.60, 0.068), 0.0095, m["gun_dark"], segments=10))
    add(cylinder("muzzle", (0, -0.60, 0.068), (0, -0.69, 0.068), 0.016, m["gun_dark"], segments=10))
    add(box("gas_block", (-0.014, -0.50, 0.055), (0.014, -0.47, 0.095), m["gun_dark"], bevel=0.003))
    grip = box("grip", (-0.017, 0.045, -0.115), (0.017, 0.092, 0.0), m["polymer"], bevel=0.007)
    grip.data.transform(__import__("mathutils").Matrix.Shear("YZ", 4, (0, 0)) if False else __import__("mathutils").Matrix.Identity(4))
    for v in grip.data.vertices:
        v.co.y += (0.0 - v.co.z) * 0.28                              # rake the grip back
    add(grip)
    mag = box("magazine", (-0.013, -0.075, -0.20), (0.013, -0.015, 0.0), m["polymer"], bevel=0.004)
    for v in mag.data.vertices:
        v.co.y -= (0.0 - v.co.z) * 0.22                              # angle the magazine forward
    add(mag)
    add(box("trigger_guard", (-0.006, -0.012, -0.045), (0.006, 0.05, -0.037), m["gun_dark"]))
    add(box("trigger", (-0.004, 0.012, -0.034), (0.004, 0.02, -0.006), m["gun_dark"]))
    add(box("stock_tube", (-0.012, 0.13, 0.055), (0.012, 0.36, 0.085), m["gun_dark"], bevel=0.004))
    add(box("stock_lower", (-0.010, 0.20, -0.005), (0.010, 0.36, 0.012), m["gun_dark"], bevel=0.003))
    add(box("stock_butt", (-0.019, 0.355, -0.03), (0.019, 0.385, 0.105), m["polymer"], bevel=0.006))
    add(box("cheek_rest", (-0.016, 0.17, 0.085), (0.016, 0.31, 0.102), m["polymer"], bevel=0.005))
    add(box("optic_body", (-0.019, -0.10, 0.117), (0.019, -0.02, 0.165), m["gun"], bevel=0.006))
    add(box("optic_lens", (-0.014, -0.103, 0.125), (0.014, -0.099, 0.158), m["visor"]))
    add(box("fore_grip", (-0.014, -0.33, -0.045), (0.014, -0.295, 0.035), m["polymer"], bevel=0.006))
    add(box("charging_handle", (0.022, -0.06, 0.075), (0.036, -0.035, 0.09), m["gun_dark"], bevel=0.003))
    obj = join(p, "rifle")
    return obj


# --- baking -----------------------------------------------------------------

def unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake(obj, prefix):
    """Bake every material on the object into one base colour, roughness and
    normal image, then swap the object over to a single material using them."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    TEX.mkdir(exist_ok=True)
    images = {}
    passes = (("basecolor", "DIFFUSE", {"COLOR"}), ("roughness", "ROUGHNESS", None), ("normal", "NORMAL", None))
    for kind, bake_type, filt in passes:
        image = bpy.data.images.new(f"{prefix}_{kind}", TEXTURE_SIZE, TEXTURE_SIZE, alpha=False,
                                    is_data=kind != "basecolor")
        images[kind] = image
        for material in obj.data.materials:
            node = material.node_tree.nodes.new("ShaderNodeTexImage")
            node.name = "bake_target"
            node.image = image
            material.node_tree.nodes.active = node
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        kwargs = dict(type=bake_type, margin=8, use_clear=True)
        if filt:
            kwargs["pass_filter"] = filt
        bpy.ops.object.bake(**kwargs)
        image.filepath_raw = str(TEX / f"{prefix}_{kind}.png")
        image.file_format = "PNG"
        image.save()
        for material in obj.data.materials:
            material.node_tree.nodes.remove(material.node_tree.nodes["bake_target"])

    final = bpy.data.materials.new(prefix)
    final.use_nodes = True
    t = final.node_tree
    bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    col = t.nodes.new("ShaderNodeTexImage")
    col.image = images["basecolor"]
    rgh = t.nodes.new("ShaderNodeTexImage")
    rgh.image = images["roughness"]
    nor = t.nodes.new("ShaderNodeTexImage")
    nor.image = images["normal"]
    nmap = t.nodes.new("ShaderNodeNormalMap")
    t.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    t.links.new(rgh.outputs["Color"], bsdf.inputs["Roughness"])
    t.links.new(nor.outputs["Color"], nmap.inputs["Color"])
    t.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    obj.data.materials.clear()
    obj.data.materials.append(final)
    for poly in obj.data.polygons:
        poly.material_index = 0
    return final


# --- renders ----------------------------------------------------------------

def studio():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.21, 0.23, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    for name, loc, energy in (("key", (-2.5, -3.5, 3.2), 900), ("fill", (3.0, -2.5, 2.0), 350),
                              ("rim", (1.5, 3.5, 3.0), 700)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size = energy, 2.5
        light = bpy.data.objects.new(name, data)
        light.location = loc
        light.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(light)
    floor = box("studio_floor", (-6, -6, -0.02), (6, 6, 0.0), mat("studio_floor", (0.16, 0.165, 0.17), 0.9))
    floor.hide_select = True
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1400
    scene.view_settings.view_transform = "Standard"
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam, floor


def render_views(cam):
    scene = bpy.context.scene
    (HERE / "renders").mkdir(exist_ok=True)
    target = Vector((0, 0, 0.92))
    for name, direction in (("front", (0, -1, 0.06)), ("side", (1, 0, 0.06)), ("back", (0, 1, 0.06))):
        cam.location = target + Vector(direction).normalized() * 6.4
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(HERE / "renders" / f"soldier_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDER", scene.render.filepath)
    # The rifle on its own, from its right side.
    soldier, gun = bpy.data.objects["soldier"], bpy.data.objects["rifle"]
    soldier.hide_render, gun.hide_render = True, False
    target = Vector((0, -0.15, 1.0))
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    cam.data.lens = 85
    cam.location = target + Vector((1, -0.25, 0.12)).normalized() * 2.6
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(HERE / "renders" / "rifle.png")
    bpy.ops.render.render(write_still=True)
    print("RENDER", scene.render.filepath)
    soldier.hide_render = False


# --- main -------------------------------------------------------------------

def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    random.seed(4)
    olive, tan, dark = (0.055, 0.068, 0.04), (0.105, 0.09, 0.058), (0.022, 0.028, 0.02)
    m = {
        "uniform": mat("uniform", olive, 0.9, camo=(dark, tan), weave=0.5),
        "gear": mat("gear", (0.082, 0.07, 0.046), 0.85, weave=0.7),
        "black": mat("black", (0.018, 0.018, 0.02), 0.75, weave=0.3),
        "boots": mat("boots", (0.06, 0.045, 0.03), 0.7, weave=0.2),
        "helmet": mat("helmet", (0.05, 0.06, 0.038), 0.65, camo=(dark, (0.075, 0.075, 0.05))),
        "visor": mat("visor", (0.01, 0.012, 0.016), 0.08, metal=0.6),
        "gun": mat("gun", (0.03, 0.03, 0.032), 0.45, metal=0.8),
        "gun_dark": mat("gun_dark", (0.012, 0.012, 0.014), 0.55, metal=0.7),
        "polymer": mat("polymer", (0.022, 0.022, 0.022), 0.7),
    }

    figure = body(m)
    body_tris = tri_count(figure)
    parts = gear(m)
    for part in list(parts):
        if part.name in {"ear_cup", "chin_strap", "helmet_rail", "goggle_strap", "cummerbund", "shoulder_strap",
                         "side_pouch", "belt_side", "knee_pad", "elbow_pad", "boot_sole", "boot_cuff",
                         "glove_cuff", "thigh_pocket"}:
            continue                                   # already made for both sides
    gear_tris = sum(tri_count(p) for p in parts)

    # Thin the body so the whole character lands on budget.
    keep = max(0.05, min(1.0, (TARGET_TRIS - gear_tris) / body_tris))
    if keep < 1.0:
        mod = figure.modifiers.new("thin", "DECIMATE")
        mod.ratio = keep
        deps = bpy.context.evaluated_depsgraph_get()
        deps.update()
        thinned = bpy.data.meshes.new_from_object(figure.evaluated_get(deps))
        figure.modifiers.clear()
        figure.data = thinned
        thinned.shade_smooth()
    soldier = join([figure] + parts, "soldier")
    soldier.data.shade_smooth()
    angle = soldier.modifiers.new("smooth_by_angle", "NODES") if False else None
    print(f"STATS soldier: {tri_count(soldier):,} triangles (body {body_tris:,} before thinning, gear {gear_tris:,})")
    zs = [v.co.z for v in soldier.data.vertices]
    xs = [v.co.x for v in soldier.data.vertices]
    print(f"STATS height {max(zs) - min(zs):.3f} m, arm span {max(xs) - min(xs):.3f} m, feet at z={min(zs):.3f}")

    gun = rifle(m)
    gun.location = (0.0, 0.0, 1.0)
    print(f"STATS rifle: {tri_count(gun):,} triangles, length "
          f"{max(v.co.y for v in gun.data.vertices) - min(v.co.y for v in gun.data.vertices):.2f} m")

    for obj, prefix in ((soldier, "soldier"), (gun, "rifle")):
        unwrap(obj)
        bake(obj, prefix)
        print("BAKED", prefix)

    # Exports: the character alone in a T-pose for Mixamo, the rifle alone at the origin.
    (HERE / "export").mkdir(exist_ok=True)
    for obj, name in ((soldier, "soldier_tpose"), (gun, "rifle")):
        bpy.ops.object.select_all(action="DESELECT")
        saved = obj.location.copy()
        obj.location = (0, 0, 0)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_scene.fbx(filepath=str(HERE / "export" / f"{name}.fbx"), use_selection=True,
                                 apply_scale_options="FBX_SCALE_ALL", path_mode="COPY", embed_textures=True,
                                 mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
                                 axis_forward="-Z", axis_up="Y")
        obj.location = saved
        print("EXPORT", name, f"{(HERE / 'export' / (name + '.fbx')).stat().st_size / 1e6:.1f} MB")

    gun.hide_render = True                 # the character views show the soldier alone
    cam, _ = studio()
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "soldier.blend"), compress=True, relative_remap=True)
    render_views(cam)


main()
