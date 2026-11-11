"""Make every town texture VRAM-compressed in Godot.

Godot only switches a texture to VRAM compression by itself when it sees it
used in 3D inside the editor. A headless import leaves new textures
uncompressed (about four times the video memory), so after importing new
textures run this, then import again:

    godot --headless --path game --import
    python projects/03-town/godot_imports.py
    godot --headless --path game --import
"""

from __future__ import annotations

import re
from pathlib import Path

TEXTURES = Path(__file__).resolve().parents[2] / "game" / "assets" / "town" / "textures"


def main() -> None:
    changed = 0
    for path in sorted(TEXTURES.glob("*.import")):
        text = path.read_text(encoding="utf-8")
        new = re.sub(r"^compress/mode=0$", "compress/mode=2", text, flags=re.M)
        if "_nor" in path.name:
            new = re.sub(r"^compress/normal_map=0$", "compress/normal_map=1", new, flags=re.M)
        if new != text:
            path.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
    print(f"{changed} texture import files set to VRAM compression")


if __name__ == "__main__":
    main()
