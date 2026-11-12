#!/usr/bin/env python3
"""Set how Godot imports the textures it extracts from house.glb.

    godot --headless --path game --import      # extracts the textures
    python3 game/tools/texture_policy.py       # this file
    godot --headless --path game --import      # re-imports with the settings

Every texture is VRAM-compressed with mipmaps. Sizes are capped by rule so the
build stays small without touching what the player looks at closely:

  2K   walls, floors, ceilings, wall and floor tiles, the clapboard, grass,
       the print sheet: colour and normal
  1K   roughness/AO maps of those; road, roof, paths; trim, doors, fabrics;
       cabinets, counters and the kitchen splashback; large furniture
  512  small props, plain enamel and porcelain, and the roughness/AO maps of
       everything at 1K

The rules only ever shrink a texture. Run with --clean to also delete
extracted textures that the current house.glb no longer uses: Godot numbers
some of them, so stale copies pile up when the model changes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HOUSE = Path(__file__).resolve().parents[1] / "assets" / "house"

# Sheets that hold many things at once (every cabinet front, every printed
# thing, every book spine): always full size, whatever else their name matches.
SHEETS = ("cabinet_fronts", "prints", "spines")
# Seen across a room or a street, or covering very little: 1K is plenty.
MEDIUM = ("asphalt_02", "roof_slates_02", "concrete_floor_worn_02", "dirty_tiles", "painted_plaster_wall",
          "rough_linen", "white_planks_clean", "ext_trim", "porch_boards", "trim_paint", "door_paint",
          "front_door_paint", "door_worn", "fabric_bed", "fabric_curtain", "fabric_pillow", "carpet_runner",
          "wood_mid", "wood_dark",
          # kitchen and bathroom: cabinet fronts, counters, the splashback and soft things
          "cabinet", "kitchen_wood", "counter", "terrazzo_tiles", "tile_kitchen", "rounded_square_tiled_wall",
          "towel", "terry_cloth", "gingham", "shower_curtain")
# Hidden behind the modelled boards, or a few centimetres across.
SMALL = ("ext_siding", "stone_sill",
         # plain enamel and porcelain: there is nothing in them for 1K to show
         "enamel", "porcelain", "hob")
# Furniture big enough to walk up to keeps its 1K maps; every other model drops to 512.
LARGE_MODELS = ("sofa_02", "ArmChair_01", "WoodenTable_03", "wooden_table_02", "Shelf_01", "television_02",
                "vintage_grandfather_clock_01", "vintage_wooden_drawer_01", "small_wooden_table_01",
                "ClassicNightstand_01", "painted_wooden_nightstand", "painted_wooden_chair_01")


def limit_for(name: str) -> int:
    """Largest side in pixels for an extracted texture, by its file name."""
    stem = name.removeprefix("house_")
    data_map = re.search(r"_(arm|rough|metal|ao)(_|\.)", stem) is not None
    if any(stem.startswith(key) for key in SHEETS):
        return 2048
    if re.search(r"_(1k|512)(_\d+)?\.(jpg|png)$", stem):                 # a furniture or prop model
        large = any(stem.startswith(model) for model in LARGE_MODELS)
        size = 1024 if large else 512
    elif any(stem.startswith(key) for key in SMALL):
        size = 512
    elif any(stem.startswith(key) for key in MEDIUM):
        size = 1024
    else:
        size = 2048
    return max(256, size // 2) if data_map else size


def apply(path: Path) -> int:
    text = path.read_text()
    limit = limit_for(path.name.removesuffix(".import"))
    text = re.sub(r"^compress/mode=\d+", "compress/mode=2", text, flags=re.M)
    text = re.sub(r"^mipmaps/generate=\w+", "mipmaps/generate=true", text, flags=re.M)
    text = re.sub(r"^process/size_limit=\d+", f"process/size_limit={limit}", text, flags=re.M)
    path.write_text(text)
    return limit


def used_images() -> set[str]:
    """Image names inside house.glb, read from its JSON chunk."""
    import json
    import struct
    with (HOUSE / "house.glb").open("rb") as handle:
        handle.seek(12)
        length, _ = struct.unpack("<II", handle.read(8))
        document = json.loads(handle.read(length))
    return {image.get("name", "") for image in document.get("images", [])}


def main():
    if "--clean" in sys.argv:
        names = used_images()
        for path in sorted(HOUSE.glob("house_*.*")):
            if path.suffix not in (".jpg", ".png"):
                continue
            base = re.sub(r"_\d+$", "", path.stem.removeprefix("house_"))
            if path.stem.removeprefix("house_") not in names and base not in names:
                print("  - stale", path.name)
                path.unlink()
                Path(str(path) + ".import").unlink(missing_ok=True)
    counts: dict[int, int] = {}
    for path in sorted(HOUSE.glob("house_*.import")):
        limit = apply(path)
        counts[limit] = counts.get(limit, 0) + 1
    print("size limits:", dict(sorted(counts.items(), reverse=True)))


if __name__ == "__main__":
    main()
