"""Render stills or the camera move from film.blend, headless.

    blender -b film.blend --python render.py -- --scene 1000_clear --cams all
    blender -b film.blend --python render.py -- --scene 0300_foggy --cams cam_2_porch --samples 512 --res 1920x1080
    blender -b film.blend --python render.py -- --scene 0300_foggy --move --samples 16 --res 640x360

Options: --scene (one of the eight), --cams (comma list or "all"), --samples,
--res WxH, --prefix (file name prefix, default "test"), --device CPU|GPU,
--move (render the 120-frame approach as PNG frames into renders/move_<scene>/).
Interior cameras are opened up by the scene's `indoors_stops`, as a camera
operator would between an exterior and an interior. Output goes to renders/.
"""

import sys
import time
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent


def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def use_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            return kind
    return None


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    scene = bpy.data.scenes[option(args, "--scene", "1000_clear")]
    bpy.context.window.scene = scene
    samples = int(option(args, "--samples", "24"))
    width, height = (int(v) for v in option(args, "--res", "960x540").split("x"))
    prefix = option(args, "--prefix", "test")
    scene.cycles.samples = samples
    scene.render.resolution_x, scene.render.resolution_y = width, height
    if option(args, "--device", "CPU") == "GPU":
        kind = use_gpu()
        scene.cycles.device = "GPU" if kind else "CPU"
        print("DEVICE", kind or "CPU (no GPU found)")
    out = HERE / "renders"
    out.mkdir(exist_ok=True)
    base = scene.view_settings.exposure

    if "--move" in args:
        cam = bpy.data.objects["cam_move_approach"]
        scene.camera = cam
        folder = out / f"move_{scene.name}"
        folder.mkdir(exist_ok=True)
        scene.render.filepath = str(folder / "frame_")
        started = time.time()
        bpy.ops.render.render(animation=True, scene=scene.name)
        print(f"RENDERED move {scene.name}: {scene.frame_end - scene.frame_start + 1} frames in {time.time() - started:.0f}s", flush=True)
        return

    wanted = option(args, "--cams", "all")
    cams = [o for o in bpy.data.objects if o.type == "CAMERA" and o.name.startswith("cam_") and "move" not in o.name]
    if wanted != "all":
        cams = [bpy.data.objects[n] for n in wanted.split(",")]
    for cam in sorted(cams, key=lambda o: o.name):
        started = time.time()
        scene.camera = cam
        scene.view_settings.exposure = base + (float(scene.get("indoors_stops", 0.0)) if cam.get("indoors") else 0.0)
        path = out / f"{prefix}_{scene.name}_{cam.name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        print(f"RENDERED {path.name} in {time.time() - started:.0f}s", flush=True)
    scene.view_settings.exposure = base


main()
