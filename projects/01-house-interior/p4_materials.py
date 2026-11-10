"""Phase 4: build the house with its textured materials."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("build.py")), init_globals={"PHASE": "materials"}, run_name="__main__")
