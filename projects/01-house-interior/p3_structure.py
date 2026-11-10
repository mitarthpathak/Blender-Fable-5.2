"""Phase 3: build the structure (shell, stair, joinery) and save house.blend."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("build.py")), init_globals={"PHASE": "structure"}, run_name="__main__")
