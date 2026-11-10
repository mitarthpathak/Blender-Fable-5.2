"""Build the house scene from plan.py, up to a chosen phase, and save it.

The scene is always rebuilt from nothing, so house.blend is reproducible
from the scripts in this folder.

Inside the live Blender:

    scripts/bmcp.py code projects/01-house-interior/build.py          # latest phase
    scripts/bmcp.py code projects/01-house-interior/p2_blockout.py    # a specific phase

Or headless, which has no time limit:

    blender -b --python projects/01-house-interior/build.py -- --phase structure
"""

import sys
import time
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
PHASES = ("blockout", "structure", "materials", "props", "lighting")
CURRENT = "lighting"          # the phase built when none is asked for


def chosen_phase():
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if "--phase" in args:
            return args[args.index("--phase") + 1]
    return globals().get("PHASE") or CURRENT


def load_modules():
    """Import the builder fresh: Blender keeps modules alive between runs."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    for name in [m for m in sys.modules if m in ("plan", "assets", "hb") or m.startswith("hb.")]:
        del sys.modules[name]
    import plan
    import hb.core
    return plan, hb


def build(phase):
    plan, hb = load_modules()
    from hb import blockout, core, shell, stairs

    problems = plan.check()
    if problems:
        raise SystemExit("plan.py has problems:\n  " + "\n  ".join(problems))
    upto = PHASES.index(phase)

    scene = bpy.context.scene
    scene.name = "house"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    if phase == "blockout":
        grey = "blockout"
        shell.build_walls(override=grey)
        shell.build_floors(override=grey)
        shell.build_ceilings(override=grey)
        stairs.build(detail=False, override=grey)
        blockout.build_furniture()
        blockout.build_door_leaves()
        blockout.build_figure(1.78, 4.3, 0.0)
        blockout.build_figure(1.80, 4.6, plan.FFL[1], name="scale_figure_1m80_landing")
        return

    shell.build_walls()
    shell.build_floors()
    shell.build_ceilings()
    shell.build_envelope()
    stairs.build(detail=True)
    from hb import joinery
    joinery.build()
    from hb import exterior
    exterior.build()

    if upto >= PHASES.index("materials"):
        from hb import materials
        materials.build()
    if upto >= PHASES.index("props"):
        from hb import props
        props.build()
    if upto >= PHASES.index("lighting"):
        from hb import lighting
        lighting.build()


def main():
    phase = chosen_phase()
    if phase not in PHASES:
        raise SystemExit(f"unknown phase {phase!r}; choose from {', '.join(PHASES)}")
    started = time.time()

    bpy.ops.wm.read_homefile(use_empty=True)
    window = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
    target = HERE / ("blockout.blend" if phase == "blockout" else "house.blend")

    def run():
        build(phase)
        from hb import core
        bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True, relative_remap=True)
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        print(f"phase {phase}: {len(meshes)} mesh objects, {core.tri_count():,} triangles, "
              f"{time.time() - started:.1f}s")
        print(f"saved {target}")

    if window is not None:
        with bpy.context.temp_override(window=window):
            run()
    else:
        run()


main()
