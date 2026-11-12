"""Bring Poly Haven furniture into the scene.

Each model is imported once from its glTF, joined into a single object with
its origin on the floor at the centre of its base, optionally thinned, and
then reused: further copies share the same mesh, so they cost a game engine
one mesh however many times they appear.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix

import assets
from . import core

# The compass direction each model's front points as delivered, in degrees.
# Almost all face -Y (-90).
NATIVE_FRONT = {"standing_picture_frame_02": 0.0}

# Fraction of triangles to keep for models far denser than a prop needs.
DECIMATE = {
    "book_encyclopedia_set_01": 0.08, "brass_vase_01": 0.12, "cardboard_box_01": 0.22,
    "ceramic_vase_01": 0.2, "desk_lamp_arm_01": 0.22, "fancy_picture_frame_02": 0.1,
    "hanging_picture_frame_03": 0.12, "mantel_clock_01": 0.15, "plastic_crate_03": 0.1,
    "potted_plant_02": 0.15, "potted_plant_04": 0.35, "wine_bottles_01": 0.12, "wooden_stool_01": 0.25,
    "hanging_picture_frame_02": 0.45, "standing_picture_frame_02": 0.5,
    "side_table_tall_01": 0.6, "vintage_grandfather_clock_01": 0.7, "ArmChair_01": 0.8,
}

_templates: dict[str, bpy.types.Object] = {}


def _import(model_id: str):
    path = assets.model_file(model_id)
    if not path.exists():
        print(f"model {model_id} is not on disk; run assets.py")
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        return None

    ratio = DECIMATE.get(model_id)
    if ratio:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in meshes:
            if len(obj.data.polygons) < 300:
                continue
            mod = obj.modifiers.new("thin", "DECIMATE")
            mod.ratio = ratio
            depsgraph.update()
            thinned = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
            obj.modifiers.remove(mod)
            old = obj.data
            obj.data = thinned
            bpy.data.meshes.remove(old)

    # Bake each part's placement into its vertices, then merge into one mesh.
    for obj in meshes:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.data.transform(world)
        obj.matrix_world = Matrix.Identity(4)
    base = meshes[0]
    leftovers = [o.name for o in new if o.type != "MESH"]      # names: join deletes the other objects
    if len(meshes) > 1:
        with bpy.context.temp_override(active_object=base, object=base, selected_objects=meshes,
                                       selected_editable_objects=meshes):
            bpy.ops.object.join()
    for name in leftovers:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(base.users_collection):
        coll.objects.unlink(base)
    base.data.name = "mesh_" + model_id
    fixed = assets.model_diffuse_fix(model_id)
    if fixed and fixed.exists():                       # a corrected colour map (assets.MODEL_FIXES)
        for slot in base.material_slots:
            if not slot.material or not slot.material.node_tree:
                continue
            for node in slot.material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image and "_diff_" in node.image.filepath:
                    node.image = bpy.data.images.load(str(fixed), check_existing=True)
    return base


def place(model_id: str, name: str, location, facing: float = -90.0, scale: float = 1.0,
          coll: str = "props", tilt=(0.0, 0.0)):
    """Put a copy of a model in the scene. `facing` is the compass direction
    its front points, in degrees: 0 is +X (east), 90 is +Y (north). `tilt`
    leans it about its own X and Y axes, for things knocked over."""
    template = _templates.get(model_id)
    if template is None:
        template = _import(model_id)
        if template is None:
            return None
        _templates[model_id] = template
        obj = template
    else:
        obj = template.copy()
    obj.name = name
    obj.rotation_mode = "XYZ"                 # glTF imports arrive in quaternion mode
    native = NATIVE_FRONT.get(model_id, -90.0)
    obj.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), math.radians(facing - native))
    obj.location = location
    obj.scale = (scale, scale, scale)
    obj["polyhaven_id"] = model_id
    return core.link(obj, coll)


def reset():
    _templates.clear()
