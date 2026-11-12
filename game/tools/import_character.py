#!/usr/bin/env python3
"""Copy the Mixamo character and the rifle into the game.

    python3 game/tools/import_character.py
    godot --headless --path game --import
    python3 game/tools/import_character.py      # again: adjusts the import settings Godot just wrote
    godot --headless --path game --import

Reads projects/03-character/mixamo/ and writes game/assets/character/. Godot
can only load files inside the project folder, which is why they are copied.
The rifle is copied whether or not the Mixamo files are there yet.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "projects" / "03-character" / "mixamo"
RIFLE = ROOT / "projects" / "03-character" / "export" / "rifle.glb"
TARGET = ROOT / "game" / "assets" / "character"

REQUIRED = ("character.fbx", "idle.fbx")
OPTIONAL = ("walk.fbx", "run.fbx", "rifle_aim.fbx", "fire.fbx", "jump.fbx")


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RIFLE, TARGET / "rifle.glb")
    print("  + rifle.glb")
    found = {path.name.lower(): path for path in SOURCE.glob("*.fbx")} if SOURCE.is_dir() else {}
    for name in REQUIRED + OPTIONAL:
        if name in found:
            shutil.copy2(found[name], TARGET / name)
            print(f"  + {name}")
        else:
            kind = "REQUIRED" if name in REQUIRED else "optional, falls back to idle"
            print(f"  ! {name} is not in {SOURCE.relative_to(ROOT)} ({kind})")
    # Godot drops animation tracks that never change. A held pose such as an
    # aim is nothing but such tracks, so that option is switched off.
    changed = 0
    for settings in TARGET.glob("*.fbx.import"):
        text = settings.read_text()
        fixed = text.replace("animation/remove_immutable_tracks=true", "animation/remove_immutable_tracks=false")
        if fixed != text:
            settings.write_text(fixed)
            changed += 1
    if changed:
        print(f"  ~ import settings changed for {changed} files: run the Godot import again")
    if all(name in found for name in REQUIRED):
        print("The character will replace the capsule. Now run: godot --headless --path game --import")
    else:
        print("The game will keep the capsule player until the required files are added.")


if __name__ == "__main__":
    main()
