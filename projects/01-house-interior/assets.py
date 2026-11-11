"""Everything this project takes from Poly Haven (CC0), and how each surface
material is made from it. No bpy: this file is the manifest, and running it
downloads the files and prepares the tinted variants.

    python3 projects/01-house-interior/assets.py            # fetch what is missing
    python3 projects/01-house-interior/assets.py --derive   # only rebuild tinted variants

Layout on disk, all inside this project and stored in Git LFS:

    textures/<set>/<set>_{diff,nor_gl,arm}_2k.jpg    surfaces, 2K
    textures/derived/<material>_{diff,arm}.jpg       tinted or re-glossed copies
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
    # Halden Ridge pass (docs/ART_BIBLE.md)
    "white_planks_clean": 1.8,
    "roof_slates_02": 3.0,
    "leafy_grass": 2.0,
    "asphalt_02": 3.0,
    "concrete_floor_worn_02": 2.0,
    "dark_paneled_wood": 1.4,
    "old_linoleum_flooring_01": 1.99,
    "ceiling_interior": 2.0,
    "peeling_painted_wall": 1.8,
    "moss_wood": 1.0,
    # Kitchen and bathroom
    "long_white_tiles": 2.54,          # photographed at 1.27 m; doubled so a tile is 7.5 x 15 cm
    "checkered_pavement_tiles": 1.5,   # photographed at 2 m; scaled so a square is 15 cm
    "linoleum_brown": 2.0,
    "kitchen_wood": 0.6,
    "terrazzo_tiles": 2.0,
    "rounded_square_tiled_wall": 2.0,
    "terry_cloth": 0.37,
    "gingham_check": 0.45,
}


@dataclass(frozen=True)
class Surface:
    """How a material key gets its textures. `tint` recolours the diffuse map
    to that average colour, keeping its stains and variation. `rough` scales
    the roughness map (below 1 is glossier). `normal` is the bump strength."""

    set: str
    tint: str | None = None
    rough: float = 1.0
    normal: float = 1.0
    mono: bool = False          # tint from the grey image: one paint colour, no second hue
    laps: int = 0               # clapboard: this many boards up the image, each shaded under the next
    mould: float = 0.0          # tiles: how far mould has taken the grout, 0 to 1


PLASTER = "painted_plaster_wall"
WALNUT = "smoked_walnut_veneer"

SURFACES: dict[str, Surface] = {
    "wall_hall": Surface("decrepit_wallpaper", "#8a8570"),
    "wall_landing": Surface("decrepit_wallpaper", "#8a8570"),
    "wall_living": Surface("decrepit_wallpaper", "#7c7f6a"),
    "wall_bedroom": Surface("peeling_painted_wall", "#7d877f"),
    "wall_kitchen": Surface(PLASTER, "#9c9577"),
    "wall_bathroom": Surface("peeling_painted_wall", "#869089", mono=True),
    "tile_bathroom": Surface("long_white_tiles", "#a7b0a3", mono=True, mould=0.45),
    "tile_bathroom_wet": Surface("long_white_tiles", "#a0a99c", mono=True, mould=1.0),   # round the bath
    "tile_kitchen": Surface("rounded_square_tiled_wall", "#a89f88", mono=True),
    "panel_wood": Surface("dark_paneled_wood", "#3b2b21"),
    "ceiling": Surface("ceiling_interior", "#a5a297", normal=0.7),
    "ext_siding": Surface("white_planks_clean", "#6c7167"),
    "ext_clapboard": Surface("peeling_painted_wall", "#6c7167", normal=0.8, mono=True, laps=16),
    "ext_trim": Surface("white_planks_clean", "#8f8d82", normal=0.4),
    "roof": Surface("roof_slates_02"),
    "foundation": Surface("concrete_floor_worn_02"),
    "ground_grass": Surface("leafy_grass"),
    "ground_path": Surface("concrete_floor_worn_02"),
    "ground_road": Surface("asphalt_02"),
    "porch_boards": Surface("wood_floor_worn", "#6b665b"),
    "floor_hall": Surface("old_linoleum_flooring_01", "#7d6c4c"),
    "floor_living": Surface("old_wooden_floor_02"),
    "floor_landing": Surface("dirty_carpet", "#5c5747"),
    "floor_bedroom": Surface("dirty_carpet", "#5c5747"),
    "floor_kitchen": Surface("linoleum_brown", "#7d6f52"),
    "floor_bathroom": Surface("checkered_pavement_tiles"),
    "cabinet": Surface("kitchen_wood", "#7c6444"),
    "counter": Surface("terrazzo_tiles", "#8b8474", mono=True, rough=0.7),
    "enamel": Surface(PLASTER, "#b4b1a4", rough=0.42, normal=0.06),
    "enamel_almond": Surface(PLASTER, "#b0a688", rough=0.45, normal=0.06),
    "porcelain": Surface(PLASTER, "#b9b7ac", rough=0.32, normal=0.04),
    "hob": Surface(PLASTER, "#2b2a28", rough=0.5, normal=0.1),
    "towel": Surface("terry_cloth", "#77695a", mono=True),
    "gingham": Surface("gingham_check"),
    "shower_curtain": Surface("rough_linen", "#8f9a97", rough=0.6, normal=0.25),
    "hearth_tile": Surface("dirty_tiles"),
    "trim_paint": Surface(PLASTER, "#b3ae9a", rough=0.55, normal=0.1),
    "door_paint": Surface(PLASTER, "#a8a38e", rough=0.55, normal=0.1),
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

def _shade_laps(image, count):
    """Darken the top of each board, where the one above overhangs it, and
    lift its bottom edge a little. V runs up the image."""
    import numpy as np
    from PIL import Image

    pixels = np.asarray(image, dtype=np.float32)
    height = pixels.shape[0]
    f = ((height - 1 - np.arange(height)) / height * count) % 1.0     # 0 at a board's bottom edge, 1 at its top
    shade = np.ones(height, dtype=np.float32)
    top = f > 0.80
    shade[top] = 1.0 - 0.72 * ((f[top] - 0.80) / 0.20) ** 1.6
    low = f < 0.06
    shade[low] = 1.0 + 0.10 * (1.0 - f[low] / 0.06)
    return Image.fromarray(np.clip(pixels * shade[:, None, None], 0, 255).astype(np.uint8))


def _mould_grout(image, amount):
    """Blacken the grout lines in patches, and dull the tiles round them.
    Grout is found as the pixels darker than their surroundings, so the
    mould follows the real joints of whichever tile photograph this is."""
    import numpy as np
    from PIL import Image, ImageFilter

    pixels = np.asarray(image, dtype=np.float32)
    lum = pixels.mean(axis=2)
    around = np.asarray(image.convert("L").filter(ImageFilter.GaussianBlur(9)), dtype=np.float32)
    grout = np.clip((around * 0.97 - lum) / 14.0, 0.0, 1.0)
    rng = np.random.default_rng(7)
    height, width = lum.shape

    def blotches(cell):
        small = (rng.random((height // cell + 2, width // cell + 2)) * 255).astype(np.uint8)
        return np.asarray(Image.fromarray(small).resize((width, height), Image.BICUBIC), dtype=np.float32) / 255.0

    patch = np.clip((blotches(160) * 0.6 + blotches(48) * 0.4 - (0.72 - 0.42 * amount)) * 4.0, 0.0, 1.0)
    cover = (grout * patch * (0.55 + 0.45 * amount))[..., None]
    film = (patch * 0.16 * amount)[..., None]
    mould = np.array([34.0, 38.0, 30.0], dtype=np.float32)
    out = pixels * (1.0 - film) * (1.0 - cover) + mould * cover
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def derive():
    from PIL import Image, ImageStat

    out = TEXTURES / "derived"
    out.mkdir(parents=True, exist_ok=True)
    for key, surface in SURFACES.items():
        if surface.tint:
            source, target = set_file(surface.set, "diff"), out / f"{key}_diff.jpg"
            if source.exists() and not target.exists():
                image = Image.open(source).convert("RGB")
                if surface.mono:
                    image = image.convert("L").convert("RGB")
                mean = ImageStat.Stat(image).mean
                want = [int(surface.tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
                bands = [band.point(lambda v, s=want[i] / max(mean[i], 1.0): min(255, int(v * s + 0.5)))
                         for i, band in enumerate(image.split())]
                image = Image.merge("RGB", bands)
                if surface.laps:
                    image = _shade_laps(image, surface.laps)
                if surface.mould:
                    image = _mould_grout(image, surface.mould)
                image.save(target, quality=92)
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
        print("models")
        fetch_models()
    print("derived")
    derive()


if __name__ == "__main__":
    main()
