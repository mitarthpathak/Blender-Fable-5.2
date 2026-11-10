"""Phase 5: build the house up to the props phase."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("build.py")), init_globals={"PHASE": "props"}, run_name="__main__")
