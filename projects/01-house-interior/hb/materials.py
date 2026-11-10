"""Materials: put the Poly Haven textures onto the materials the meshes use.

Every material stays a single Principled BSDF fed by image textures (base
colour, normal, and one AO/roughness/metal image), with no mapping or mixing
nodes. That is the shape glTF can carry, so Godot gets the same material.
Texture scale lives in the UVs, set when each mesh was built.
"""

from __future__ import annotations

import bpy

import assets
from . import core


def _image(path, non_color=False):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.filepath = bpy.path.relpath(str(path)) if bpy.data.filepath else str(path)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def texture_material(key: str):
    """Rebuild m_<key> around its texture set. Returns False when the key has
    no textures or the files are missing."""
    files = assets.surface_files(key)
    if not files or not all(p.exists() for p in files.values()):
        return False
    surface = assets.SURFACES[key]
    spec = core.spec(key)
    mat = core.material(key)
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    diff = tree.nodes.new("ShaderNodeTexImage")
    diff.image, diff.location = _image(files["diff"]), (-500, 300)
    tree.links.new(diff.outputs["Color"], bsdf.inputs["Base Color"])

    arm = tree.nodes.new("ShaderNodeTexImage")
    arm.image, arm.location = _image(files["arm"], non_color=True), (-700, 0)
    split = tree.nodes.new("ShaderNodeSeparateColor")
    split.location = (-400, 0)
    tree.links.new(arm.outputs["Color"], split.inputs["Color"])
    tree.links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    tree.links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])

    nor = tree.nodes.new("ShaderNodeTexImage")
    nor.image, nor.location = _image(files["nor"], non_color=True), (-700, -300)
    bump = tree.nodes.new("ShaderNodeNormalMap")
    bump.location = (-400, -300)
    bump.inputs["Strength"].default_value = surface.normal
    tree.links.new(nor.outputs["Color"], bump.inputs["Color"])
    tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    mat.diffuse_color = (*core.hex_rgb(surface.tint or spec.color), 1.0)
    return True


def tune_plain():
    """Materials with no texture: glass, metals, soot."""
    glass = core.material("glass")
    bsdf = next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.04
    bsdf.inputs["Alpha"].default_value = 0.16
    glass.use_backface_culling = False
    frosted = core.material("glass_frosted")
    frosted.use_backface_culling = False


def build():
    done, missing = [], []
    for key in assets.SURFACES:
        (done if texture_material(key) else missing).append(key)
    tune_plain()
    if missing:
        print("materials without textures on disk:", ", ".join(missing))
    print(f"textured {len(done)} materials")
    return done
