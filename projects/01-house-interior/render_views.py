"""Render named preview views of a saved scene, headless.

    blender -b house.blend --python render_views.py -- \
        --views axon_0,axon_1,hall --prefix 03_structure [--rig work|scene] \
        [--samples 48] [--res 1600x900] [--exposure 0]

Views: axon_0 and axon_1 are cutaways of the ground and first floor; any
camera saved in the scene can be named without its "cam_" prefix (the hero
shots are hero_hallway, hero_stairs and hero_bedroom); the rest are the
eye-level views named in hb/preview.py. `--rig scene` keeps the scene's own
lighting and render settings. Output goes to renders/.
"""

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hb import preview  # noqa: E402


def option(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    views = option(args, "--views", "axon_0,axon_1").split(",")
    prefix = option(args, "--prefix", "preview")
    rig = option(args, "--rig", "work")
    samples = int(option(args, "--samples", "48"))
    width, height = (int(v) for v in option(args, "--res", "1600x900").split("x"))
    exposure = option(args, "--exposure", None)
    exposure = float(exposure) if exposure is not None else None
    out = HERE / "renders"
    out.mkdir(exist_ok=True)
    for view in views:
        started = time.time()
        path = out / f"{prefix}_{view}.png"
        preview.render(view, path, rig=rig, samples=samples, resolution=(width, height), exposure=exposure)
        print(f"RENDERED {path.name} in {time.time() - started:.0f}s", flush=True)


main()
