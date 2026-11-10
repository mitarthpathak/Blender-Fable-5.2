"""Phase 2: build the grey blockout and save it as blockout.blend."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("build.py")), init_globals={"PHASE": "blockout"}, run_name="__main__")
