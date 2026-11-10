"""Everything this project takes from Poly Haven (CC0), and how each surface
material is made from it. No bpy: this file is the manifest, and running it
downloads the files and prepares the tinted variants.

    python3 projects/01-house-interior/assets.py            # fetch what is missing
    python3 projects/01-house-interior/assets.py --derive   # only rebuild tinted variants

Layout on disk, all inside this project and stored in Git LFS:

    textures/<set>/<set>_{diff,nor_gl,arm}_2k.jpg    surfaces, 2K
    textures/derived/<material>_{diff,arm}.jpg       tinted or re-glossed copies
    hdri/<id>_4k.hdr                                 the night sky
    models/<id>/                                     furniture as glTF with 1K textures
"""

from __future__ import annotations

import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTURES = HERE / "textures"
MODELS = HERE / "models"
HDRI_DIR = HERE / "hdri"
API = "https://api.polyhaven.com/files/"
AGENT = {"User-Agent": "blender-house-builder"}

SURFACE_RES = "2k"
MODEL_RES = "1k"

# Texture sets and the real-world size of one repeat, in metres.
SETS: dict[str, float] = {
    "painted_plaster_wall": 2.0,
    "decrepit_wallpaper": 2.5,
    "old_wooden_floor_02": 2.03,
    "wood_floor_worn": 2.0,
    "floor_tiles_06": 1.5,      # photographed at 3 m; halved so a tile is a real 0.37 m
    "dirty_tiles": 2.26,
    "red_brick": 1.4,
    "smoked_walnut_veneer": 1.0,
    "wood_peeling_paint_weathered": 0.762,
    "rough_linen": 0.27,
    "fabric_pattern_05": 0.5,
    "fabric_leather_02": 0.5,
    "dirty_carpet": 0.6,
}

HDRI = "cobblestone_street_night"
HDRI_RES = "4k"


@dataclass(frozen=True)
class Surface:
    """How a material key gets its textures. `tint` recolours the diffuse map
    to that average colour, keeping its stains and variation. `rough` scales
    the roughness map (below 1 is glossier). `normal` is the bump strength."""

    set: str
    tint: str | None = None
    rough: float = 1.0
    normal: float = 1.0


PLASTER = "painted_plaster_wall"
WALNUT = "smoked_walnut_veneer"

SURFACES: dict[str, Surface] = {
    "wall_hall": Surface(PLASTER, "#b4ad9b"),
    "wall_landing": Surface(PLASTER, "#b4ad9b"),
    "wall_living": Surface(PLASTER, "#8b968a"),
    "wall_bedroom": Surface(PLASTER, "#8690a0"),
    "wall_boxroom": Surface("decrepit_wallpaper"),
    "ceiling": Surface(PLASTER, "#cfccc3", normal=0.6),
    "ext_brick": Surface("red_brick"),
    "floor_hall": Surface("floor_tiles_06"),
    "floor_living": Surface("old_wooden_floor_02"),
    "floor_landing": Surface("wood_floor_worn"),
    "floor_bedroom": Surface("wood_floor_worn"),
    "floor_boxroom": Surface("wood_floor_worn"),
    "hearth_tile": Surface("dirty_tiles"),
    "trim_paint": Surface(PLASTER, "#d6d2c6", rough=0.5, normal=0.08),
    "door_paint": Surface(PLASTER, "#cfcaba", rough=0.5, normal=0.08),
    "front_door_paint": Surface(PLASTER, "#27333b", rough=0.45, normal=0.08),
    "door_worn": Surface(PLASTER, "#2c3a31", rough=0.7, normal=0.35),
    "stone_sill": Surface(PLASTER, "#8d8a82"),
    "wood_stair": Surface(WALNUT, "#4b3424", rough=0.85),
    "wood_mid": Surface(WALNUT, "#5c4129"),
    "wood_dark": Surface(WALNUT, "#2f2119", rough=0.8),
    "fabric_curtain": Surface("rough_linen", "#6d685b"),
    "fabric_plaid": Surface("fabric_pattern_05"),
    "fabric_bed": Surface("rough_linen", "#8f8a7c"),
    "fabric_pillow": Surface("rough_linen", "#c9c5b8"),
    "leather": Surface("fabric_leather_02"),
    "carpet": Surface("dirty_carpet"),
    "carpet_runner": Surface("dirty_carpet", "#5a2f2a"),
}

# Furniture and props. Unknown ids are skipped with a warning, so the list can
# name candidates.
MODEL_IDS = [
    "sofa_02", "ArmChair_01", "small_wooden_table_01", "WoodenTable_03", "Shelf_01",
    "wooden_table_02", "painted_wooden_chair_01", "side_table_tall_01", "side_table_01",
    "ClassicNightstand_01", "painted_wooden_nightstand", "television_02", "desk_lamp_arm_01",
    "fancy_picture_frame_01", "fancy_picture_frame_02", "hanging_picture_frame_02",
    "hanging_picture_frame_03", "standing_picture_frame_02",
    "potted_plant_01", "potted_plant_02", "potted_plant_04", "cardboard_box_01",
    "book_encyclopedia_set_01", "wine_bottles_01", "vintage_wooden_drawer_01",
    "mantel_clock_01", "vintage_grandfather_clock_01", "ceramic_vase_01", "brass_vase_01",
    "Ottoman_01", "wooden_stool_01", "plastic_crate_03",
]


def tile_of(key: str) -> float | None:
    surface = SURFACES.get(key)
    return SETS[surface.set] if surface else None


def set_file(set_id: str, kind: str) -> Path:
    return TEXTURES / set_id / f"{set_id}_{kind}_{SURFACE_RES}.jpg"


def surface_files(key: str) -> dict[str, Path] | None:
    """The diffuse, normal and ARM (AO, roughness, metal) images for a material."""
    surface = SURFACES.get(key)
    if surface is None:
        return None
    diff = TEXTURES / "derived" / f"{key}_diff.jpg" if surface.tint else set_file(surface.set, "diff")
    arm = TEXTURES / "derived" / f"{key}_arm.jpg" if surface.rough != 1.0 else set_file(surface.set, "arm")
    return {"diff": diff, "nor": set_file(surface.set, "nor_gl"), "arm": arm}


def hdri_file() -> Path:
    return HDRI_DIR / f"{HDRI}_{HDRI_RES}.hdr"


def model_file(model_id: str) -> Path:
    return MODELS / model_id / f"{model_id}_{MODEL_RES}.gltf"


# --- Downloading ------------------------------------------------------------

def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=120) as r:
        return r.read()


def _download(url: str, path: Path) -> bool:
    if path.exists() and path.stat().st_size > 0:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(_get(url))
    tmp.rename(path)
    return True


def _listing(asset_id: str) -> dict | None:
    try:
        data = json.loads(_get(API + asset_id))
    except Exception as error:            # unknown id or network trouble
        print(f"  ! {asset_id}: {error}")
        return None
    return data if isinstance(data, dict) and data else None


def fetch_textures():
    for set_id in SETS:
        wanted = {"diff": ("Diffuse", "diff", "Color", "col_01", "col_1", "coll1"), "nor_gl": ("nor_gl",),
                  "arm": ("arm",)}
        if all(set_file(set_id, kind).exists() for kind in wanted):
            continue
        listing = _listing(set_id)
        if not listing:
            continue
        for kind, names in wanted.items():
            entry = next((listing[n] for n in names if n in listing), None)
            if not entry:
                print(f"  ! {set_id}: no {kind} map")
                continue
            if _download(entry[SURFACE_RES]["jpg"]["url"], set_file(set_id, kind)):
                print(f"  + {set_file(set_id, kind).relative_to(HERE)}")


def fetch_hdri():
    if hdri_file().exists():
        return
    listing = _listing(HDRI)
    if listing and _download(listing["hdri"][HDRI_RES]["hdr"]["url"], hdri_file()):
        print(f"  + {hdri_file().relative_to(HERE)}")


def fetch_models():
    for model_id in MODEL_IDS:
        target = model_file(model_id)
        if target.exists():
            continue
        listing = _listing(model_id)
        if not listing or "gltf" not in listing:
            print(f"  ! {model_id}: not a Poly Haven model, skipped")
            continue
        entry = listing["gltf"][MODEL_RES]["gltf"]
        for relative, item in entry.get("include", {}).items():
            _download(item["url"], target.parent / relative)
        _download(entry["url"], target)
        print(f"  + models/{model_id}/")


# --- Tinted and re-glossed variants -----------------------------------------

def derive():
    from PIL import Image, ImageStat

    out = TEXTURES / "derived"
    out.mkdir(parents=True, exist_ok=True)
    for key, surface in SURFACES.items():
        if surface.tint:
            source, target = set_file(surface.set, "diff"), out / f"{key}_diff.jpg"
            if source.exists() and not target.exists():
                image = Image.open(source).convert("RGB")
                mean = ImageStat.Stat(image).mean
                want = [int(surface.tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
                bands = [band.point(lambda v, s=want[i] / max(mean[i], 1.0): min(255, int(v * s + 0.5)))
                         for i, band in enumerate(image.split())]
                Image.merge("RGB", bands).save(target, quality=92)
                print(f"  ~ {target.relative_to(HERE)}")
        if surface.rough != 1.0:
            source, target = set_file(surface.set, "arm"), out / f"{key}_arm.jpg"
            if source.exists() and not target.exists():
                r, g, b = Image.open(source).convert("RGB").split()
                g = g.point(lambda v, s=surface.rough: min(255, int(v * s + 0.5)))
                Image.merge("RGB", (r, g, b)).save(target, quality=92)
                print(f"  ~ {target.relative_to(HERE)}")


def main():
    if "--derive" not in sys.argv:
        print("textures")
        fetch_textures()
        print("hdri")
        fetch_hdri()
        print("models")
        fetch_models()
    print("derived")
    derive()


if __name__ == "__main__":
    main()
