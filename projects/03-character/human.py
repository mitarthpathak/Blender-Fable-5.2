"""Build the base human with MPFB2 (MakeHuman for Blender) and export it for Mixamo.

    python3 projects/03-character/fetch.py        # once: add-on and CC0 asset pack
    python3 projects/03-character/textures.py     # once: 2K texture sets
    blender -b --python projects/03-character/human.py
    blender -b --python projects/03-character/human.py -- --no-render

Everything about the body, face and clothes comes from MakeHuman: the script
only chooses the settings, puts the arms into a T-pose with MakeHuman's own
rig, removes what can never be seen, and assigns game materials.

Writes human.blend, export/human_tpose.fbx (+ .glb) and renders/human_*.png.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

HERE = Path(__file__).resolve().parent
PACK = HERE.parents[1] / "assets" / "cache" / "mpfb" / "pack"
TEX = HERE / "textures"
EXPORT = HERE / "export"
RENDERS = HERE / "renders"

HEIGHT = 1.80                      # metres, standing in the boots
TRI_BUDGET = (20_000, 30_000)

# Average adult man, nothing pushed to an extreme.
MACRO = {"gender": 1.0, "age": 0.56, "muscle": 0.52, "weight": 0.50, "proportions": 0.5,
         "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}}

SKIN = "skins/middleage_caucasian_male/middleage_caucasian_male.mhmat"
ASSETS = [   # (MPFB asset type, .mhclo, material of the finished mesh)
    ("Eyes", "eyes/low-poly/low-poly.mhclo", "eyes"),
    ("Eyebrows", "eyebrows/eyebrow001/eyebrow001.mhclo", "lashes"),
    ("Eyelashes", "eyelashes/eyelashes01/eyelashes01.mhclo", "lashes"),
    ("Hair", "hair/short02/short02.mhclo", "hair"),
    ("Clothes", "clothes/male_casualsuit05/male_casualsuit05.mhclo", "outfit"),
    ("Clothes", "clothes/shoes03/shoes03.mhclo", "boots"),
]

# name: (diffuse, normal, roughness map or value, alpha, specular)
MATERIALS = {
    "skin": ("skin_diff.jpg", "skin_nor.jpg", "skin_rough.jpg", False, 0.4),
    "outfit": ("outfit_diff.jpg", "outfit_nor.jpg", "outfit_rough.jpg", False, 0.3),
    "boots": ("boots_diff.jpg", "boots_nor.jpg", "boots_rough.jpg", False, 0.5),
    "hair": ("hair_diff.png", "hair_nor.jpg", 0.55, True, 0.3),
    "eyes": ("eyes_diff.jpg", None, 0.12, False, 0.6),
    "lashes": ("lashes_diff.png", None, 0.7, True, 0.1),
}
NORMAL_STRENGTH = {"skin": 0.35, "outfit": 1.0, "boots": 0.8, "hair": 1.0}


def window():
    return bpy.context.temp_override(window=bpy.context.window_manager.windows[0])


def world_bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        for vertex in mesh.vertices:
            co = obj.matrix_world @ vertex.co
            lo = Vector(map(min, lo, co))
            hi = Vector(map(max, hi, co))
        evaluated.to_mesh_clear()
    return lo, hi


def remove(obj):
    for child in list(obj.children):
        remove(child)
    bpy.data.objects.remove(obj, do_unlink=True)


# --- The MakeHuman character -------------------------------------------------

def make_human(height_macro: float):
    macro = dict(MACRO, height=height_macro)
    base = HumanService.create_human(scale=0.1, macro_detail_dict=macro)       # 0.1: decimetres to metres
    return base


def body_height(height_macro: float) -> float:
    base = make_human(height_macro)
    lo, hi = world_bounds([base])
    remove(base)
    return hi.z - lo.z


def solve_height(sole: float) -> float:
    """The MakeHuman height setting that makes the figure HEIGHT tall in boots."""
    target, lo, hi = HEIGHT - sole, 0.3, 0.95
    for _ in range(9):
        mid = (lo + hi) / 2.0
        if body_height(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def dress(base):
    HumanService.set_character_skin(str(PACK / SKIN), base, skin_type="MAKESKIN")
    parts = []
    for asset_type, mhclo, material in ASSETS:
        obj = HumanService.add_mhclo_asset(str(PACK / mhclo), base, asset_type=asset_type,
                                           subdiv_levels=0, material_type="MAKESKIN")
        obj["game_material"] = material
        parts.append(obj)
    return parts


def t_pose(base, rig):
    """MakeHuman's own T-pose for this rig, then level the arms exactly."""
    pose_file = Path(LocationService.get_mpfb_data("poses")) / "default_fk" / "t-pose.json"
    rotations = json.loads(pose_file.read_text())["bone_rotations"]
    for name, euler in rotations.items():
        bone = rig.pose.bones.get(name)
        if bone and not name.startswith(("foot", "pelvis", "upperleg")):      # arms only: legs stay as built
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = euler

    def droop(side: str) -> float:
        bpy.context.view_layer.update()
        shoulder = rig.matrix_world @ rig.pose.bones[f"upperarm01.{side}"].head
        wrist = rig.matrix_world @ rig.pose.bones[f"wrist.{side}"].head
        return math.atan2(shoulder.z - wrist.z, abs(wrist.x - shoulder.x))

    for side, sign in (("L", 1.0), ("R", -1.0)):
        upper = rig.pose.bones[f"upperarm01.{side}"]
        for _ in range(6):
            upper.rotation_euler.z += sign * droop(side)
        # Palms face the ground and the fingers open a little, as auto-riggers expect.
        for finger, spread in ((2, 0.07), (4, -0.05), (5, -0.11)):
            bone = rig.pose.bones.get(f"finger{finger}-1.{side}")
            if bone:
                bone.rotation_mode = "XYZ"
                bone.rotation_euler.z += sign * spread
    bpy.context.view_layer.update()
    return {side: math.degrees(droop(side)) for side in "LR"}


def freeze(objects):
    """Bake shape keys, masks and the posed armature into plain meshes."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    frozen = []
    for obj in objects:
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
        mesh.transform(obj.matrix_world)
        copy = bpy.data.objects.new(obj.name + ".frozen", mesh)
        bpy.context.scene.collection.objects.link(copy)
        copy["game_material"] = obj.get("game_material", "skin")
        frozen.append(copy)
    return frozen


def strip_hidden(body):
    """Drop skin that clothes always cover: what is left of the legs, and the
    inside of the mouth is kept (it is needed if the jaw is ever animated)."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    doomed = [v for v in bm.verts if v.co.z < 1.0 and abs(v.co.x) < 0.45]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()


def remap_uv(obj, offset_u: float, scale_u: float):
    for layer in obj.data.uv_layers:
        for loop in layer.data:
            loop.uv.x = offset_u + loop.uv.x * scale_u


# --- Materials ---------------------------------------------------------------

def image(name: str, colour: bool):
    img = bpy.data.images.load(str(TEX / name), check_existing=True)
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def material(name: str):
    diffuse, normal, rough, alpha, specular = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = specular

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image(diffuse, True)
    tex.location = (-520, 300)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        mat.surface_render_method = "DITHERED"
    if normal:
        ntex = nodes.new("ShaderNodeTexImage")
        ntex.image = image(normal, False)
        ntex.location = (-760, -300)
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = NORMAL_STRENGTH.get(name, 1.0)
        nmap.location = (-300, -300)
        links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if isinstance(rough, str):
        rtex = nodes.new("ShaderNodeTexImage")
        rtex.image = image(rough, False)
        rtex.location = (-520, 0)
        links.new(rtex.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    if name == "skin":
        bsdf.inputs["Subsurface Weight"].default_value = 0.12
        bsdf.inputs["Subsurface Radius"].default_value = (0.012, 0.006, 0.004)
        bsdf.inputs["Subsurface Scale"].default_value = 1.0
    return mat


def assign(obj, name: str, cache: dict):
    obj.data.materials.clear()
    if name not in cache:
        cache[name] = material(name)
    obj.data.materials.append(cache[name])
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


# --- Build -------------------------------------------------------------------

def build():
    bpy.ops.wm.read_homefile(use_empty=True)
    with window():
        # Boots add their sole to the height, so measure it on a first figure.
        probe = make_human(0.5)
        shoes = HumanService.add_mhclo_asset(str(PACK / ASSETS[-1][1]), probe, asset_type="Clothes", subdiv_levels=0)
        sole = -world_bounds([shoes])[0].z
        remove(probe)
        height_macro = solve_height(sole)

        # The rig goes on before the clothes so that MPFB weights them to it.
        base = make_human(height_macro)
        rig = HumanService.add_builtin_rig(base, "default")
        parts = dress(base)
        droop = t_pose(base, rig)
        print(f"height setting {height_macro:.3f}, sole {sole * 100:.1f} cm, arm droop after posing {droop}")

        base["game_material"] = "skin"
        frozen = freeze([base] + parts)
        remove(rig)
        for obj in list(bpy.data.objects):
            if obj not in frozen:
                bpy.data.objects.remove(obj, do_unlink=True)

        body = frozen[0]
        strip_hidden(body)
        cache: dict = {}
        for obj in frozen:
            name = obj["game_material"]
            if obj.name.startswith("Human.eyebrow"):
                remap_uv(obj, 0.0, 0.5)
            elif obj.name.startswith("Human.eyelashes"):
                remap_uv(obj, 0.5, 0.5)
            for extra in list(obj.data.uv_layers)[1:]:
                obj.data.uv_layers.remove(extra)
            obj.data.uv_layers[0].name = "UVMap"
            assign(obj, name, cache)

        # One mesh, feet on the ground, centred, origin between the feet.
        for obj in bpy.data.objects:
            obj.select_set(obj in frozen)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()
        human = body
        human.name = human.data.name = "human"
        lo, hi = world_bounds([human])
        human.data.transform(Matrix.Translation((-(lo.x + hi.x) / 2.0, 0.0, -lo.z)))
        human.data.update()

        for stale in (bpy.data.materials, bpy.data.images, bpy.data.meshes):
            for block in list(stale):
                if block.users == 0:
                    stale.remove(block)
    return human


def report(human):
    mesh = human.data
    triangles = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo, hi = world_bounds([human])
    per_material = {}
    for polygon in mesh.polygons:
        key = mesh.materials[polygon.material_index].name
        per_material[key] = per_material.get(key, 0) + len(polygon.vertices) - 2
    hands = [v.co for v in mesh.vertices if abs(v.co.x) > 0.6]
    print(f"HUMAN triangles {triangles}  height {hi.z - lo.z:.3f} m  span {hi.x - lo.x:.3f} m  "
          f"hand height {min(c.z for c in hands):.3f}..{max(c.z for c in hands):.3f}")
    print("      by material", per_material)
    if not TRI_BUDGET[0] <= triangles <= TRI_BUDGET[1]:
        print(f"      ! outside the {TRI_BUDGET} triangle budget")
    return triangles, hi.z - lo.z


def export(human):
    EXPORT.mkdir(exist_ok=True)
    with window():
        bpy.ops.object.select_all(action="DESELECT")
        human.select_set(True)
        bpy.context.view_layer.objects.active = human
        bpy.ops.export_scene.fbx(
            filepath=str(EXPORT / "human_tpose.fbx"), use_selection=True, object_types={"MESH"},
            apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y",
            mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
            path_mode="COPY", embed_textures=True, bake_anim=False)
        bpy.ops.export_scene.gltf(
            filepath=str(EXPORT / "human_tpose.glb"), export_format="GLB", use_selection=True,
            export_apply=True, export_yup=True, export_image_format="JPEG", export_jpeg_quality=90)
    for name in ("human_tpose.fbx", "human_tpose.glb"):
        print(f"  + export/{name}  {(EXPORT / name).stat().st_size / 1e6:.1f} MB")


# --- Studio renders ----------------------------------------------------------

def studio():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1600
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"

    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.30, 0.31, 0.33, 1.0)
    background.inputs["Strength"].default_value = 0.35
    scene.world = world

    def area(name, location, energy, size, colour):
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size, light.color = energy, size, colour
        obj = bpy.data.objects.new(name, light)
        obj.location = location
        scene.collection.objects.link(obj)
        direction = Vector((0.0, 0.0, 1.1)) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return obj

    rig = bpy.data.objects.new("light_rig", None)
    scene.collection.objects.link(rig)
    for light in (area("key", (-2.6, -3.4, 3.0), 520.0, 2.4, (1.0, 0.96, 0.90)),
                  area("fill", (3.4, -2.4, 1.6), 170.0, 3.0, (0.85, 0.92, 1.0)),
                  area("rim", (1.2, 3.6, 3.2), 420.0, 1.6, (0.90, 0.95, 1.0))):
        light.parent = rig

    floor = bpy.data.meshes.new("floor")
    floor.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    floor_obj = bpy.data.objects.new("studio_floor", floor)
    grey = bpy.data.materials.new("studio_grey")
    grey.use_nodes = True
    bsdf = next(n for n in grey.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.20, 0.20, 0.21, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    floor.materials.append(grey)
    scene.collection.objects.link(floor_obj)

    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = 85.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    return rig, camera


def render(views=("front", "side", "back")):
    RENDERS.mkdir(exist_ok=True)
    rig, camera = studio()
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1500, 1500
    angles = {"front": 0.0, "side": 90.0, "back": 180.0}
    for view in views:
        angle = math.radians(angles[view])
        distance = 5.1
        camera.location = (math.sin(angle) * distance, -math.cos(angle) * distance, 0.96)
        camera.rotation_euler = (math.radians(90.0), 0.0, angle)
        rig.rotation_euler.z = angle                     # the lights follow the camera
        scene.render.filepath = str(RENDERS / f"human_{view}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  + renders/human_{view}.png")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    human = build()
    report(human)
    export(human)
    with window():
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "human.blend"), compress=True, relative_remap=True)
    if "--no-render" not in args:
        render()


if __name__ == "__main__":
    main()
