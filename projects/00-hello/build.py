"""Smoke-test scene: a gold Suzanne inside a glowing ring.

Rebuilds the scene from nothing, saves it next to this file and renders one
frame. It exists to prove the whole chain works (MCP -> Blender -> Cycles ->
files in the repository) and to show the layout a project here follows.

Run it inside the live Blender:

    scripts/bmcp.py code projects/00-hello/build.py
"""

import math
import time
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
BLEND = HERE / "hello.blend"
RENDER = HERE / "renders" / "hello.png"


def reset_scene():
    """Empty the file without touching preferences.

    Never use bpy.ops.wm.read_factory_settings() here: it unloads every addon,
    including the MCP bridge this script is being run through.

    Loading a file from inside a script leaves bpy.context without a window,
    and with it bpy.context.object and most operators. The caller gets the
    window back and must run everything after this inside
    `bpy.context.temp_override(window=...)`.
    """
    bpy.ops.wm.read_homefile(use_empty=True)
    return bpy.context.window_manager.windows[0]


def principled(name, color, metallic=0.0, roughness=0.4, emission=None, strength=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return material


def build():
    scene = bpy.context.scene

    bpy.ops.mesh.primitive_plane_add(size=40)
    bpy.context.object.name = "Floor"
    bpy.context.object.data.materials.append(principled("Floor", (0.05, 0.05, 0.06), roughness=0.25))

    bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 1.1))
    suzanne = bpy.context.object
    suzanne.name = "Suzanne"
    bpy.ops.object.shade_smooth()
    subdivision = suzanne.modifiers.new("Subdivision", "SUBSURF")
    subdivision.levels = subdivision.render_levels = 2
    suzanne.data.materials.append(principled("Gold", (1.0, 0.72, 0.25), metallic=1.0, roughness=0.18))

    bpy.ops.mesh.primitive_torus_add(
        location=(0, 0, 1.1),
        rotation=(math.radians(70), 0, 0),
        major_radius=1.9,
        minor_radius=0.06,
    )
    bpy.context.object.name = "Ring"
    bpy.context.object.data.materials.append(
        principled("Glow", (0, 0, 0), emission=(0.1, 0.6, 1.0), strength=6.0)
    )

    bpy.ops.object.light_add(type="AREA", location=(4, -4, 6))
    key = bpy.context.object
    key.name = "Key"
    key.data.energy = 1500
    key.data.size = 4
    key.rotation_euler = (math.radians(45), 0, math.radians(45))

    bpy.ops.object.camera_add(location=(5.5, -6.5, 3.2))
    camera = bpy.context.object
    camera.name = "Camera"
    camera.constraints.new("TRACK_TO").target = suzanne
    scene.camera = camera

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.02, 0.02, 0.03, 1.0)
    scene.world = world


def configure_render():
    """Cycles on the CPU: this machine has no GPU, and Cycles gives real
    reflections and bounce light where EEVEE on a software rasteriser is both
    slower and flatter."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(RENDER)


def main():
    window = reset_scene()
    with bpy.context.temp_override(window=window):
        build()
        configure_render()

        RENDER.parent.mkdir(parents=True, exist_ok=True)
        # Save before rendering, so a render that runs out of memory or time
        # cannot take the scene with it.
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=True)

        started = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"saved  {BLEND}")
        print(f"render {RENDER} ({time.time() - started:.1f}s)")


main()
