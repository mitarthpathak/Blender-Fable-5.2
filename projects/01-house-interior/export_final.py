"""Final deliverables from house.blend: a self-contained .blend and a .glb.

    blender -b house.blend --python export_final.py

- house_packed.blend: every texture and the HDRI packed inside the file.
- house.glb: geometry, materials with their textures, and the lights, for
  Godot. The render-only haze and the lamp markers are left out.
"""

from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PACKED = HERE / "house_packed.blend"
GLB = HERE / "house.glb"


def main():
    scene = bpy.context.scene
    skip = {o for o in scene.objects if o.get("export") is False or o.name.startswith("lightpoint_")}
    for obj in scene.objects:
        obj.select_set(obj not in skip)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB), export_format="GLB", use_selection=True, export_apply=True,
        export_extras=True, export_lights=True, export_cameras=True, export_yup=True,
        export_image_format="AUTO",
    )
    meshes = [o for o in scene.objects if o.type == "MESH" and o not in skip]
    tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
    print(f"EXPORT {GLB.name}: {GLB.stat().st_size / 1e6:.1f} MB, {len(meshes)} meshes, {tris:,} triangles, "
          f"{len([o for o in scene.objects if o.type == 'LIGHT'])} lights")

    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(PACKED), compress=True, copy=True)
    print(f"EXPORT {PACKED.name}: {PACKED.stat().st_size / 1e6:.1f} MB")


main()
