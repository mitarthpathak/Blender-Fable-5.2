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
    # Quality pass: the outside and the back yard
    "concrete_block_wall_02": 2.0,
    "rusty_metal_02": 1.0,
    "bark_brown_02": 1.0,
    "rusty_corrugated_iron": 2.0,
    "brown_mud_leaves_01": 1.3,
}

# Sets fetched below the usual 2K: things seen from across a yard.
SET_RES: dict[str, str] = {
    "concrete_block_wall_02": "1k", "rusty_metal_02": "1k", "bark_brown_02": "1k",
    "rusty_corrugated_iron": "1k", "brown_mud_leaves_01": "1k",
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
    gen: str = ""               # a generator in GENERATORS that draws the maps (see below)
    tile: float = 0.0           # size of one repeat in metres, when it is not the set's
    own: bool = False           # the generator makes normal and ARM maps too


PLASTER = "painted_plaster_wall"
WALNUT = "smoked_walnut_veneer"

SURFACES: dict[str, Surface] = {
    "wall_hall": Surface("decrepit_wallpaper", "#8a8570"),
    "wall_landing": Surface("decrepit_wallpaper", "#8a8570"),
    "wall_living": Surface("decrepit_wallpaper", "#7c7f6a"),
    # Bedroom: a striped paper drawn over the plaster photograph. (It was a
    # photograph of badly cracked paint, which at wall size read as dried mud.)
    "wall_bedroom": Surface(PLASTER, "#7f887c", gen="stripes"),
    "wall_kitchen": Surface(PLASTER, "#96937f"),
    "wall_bathroom": Surface(PLASTER, "#8a958d", rough=0.72),         # gloss paint; the peeling is in decals
    "wall_utility": Surface(PLASTER, "#98958a"),
    # Square glazed tiles, drawn (texgen.py): the photographed set is a modern
    # stack of long narrow tiles, wrong for the house.
    "tile_bathroom": Surface(PLASTER, "#a9b3a6", gen="square_tiles", tile=0.864, own=True, mould=0.35),
    "tile_bathroom_wet": Surface(PLASTER, "#a3ad9f", gen="square_tiles", tile=0.864, own=True, mould=1.0),
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
    "porch_boards": Surface("wood_floor_worn", "#6b665b", mono=True),     # one grey paint, not the pine's orange
    "ext_foundation": Surface("concrete_floor_worn_02", "#77756c", gen="blocks", tile=2.0, own=True),
    "ext_brick": Surface("red_brick", "#67483d"),
    "metal_galv": Surface("rusty_metal_02", "#6f716d", gen="dull_hard"),
    "metal_painted": Surface("rusty_metal_02", "#8a8676", gen="dull_hard"),
    "bark": Surface("bark_brown_02", "#4a4338", gen="dull"),
    "roof_tin": Surface("rusty_corrugated_iron", "#4f4239", gen="dull"),
    "ground_dirt": Surface("brown_mud_leaves_01", "#5d533f", gen="dull"),
    "shed_boards": Surface("wood_floor_worn", "#5c5b50", mono=True),         # bare grey boards
    "floor_hall": Surface("old_linoleum_flooring_01", "#74694f", gen="dull"),
    "floor_living": Surface("old_wooden_floor_02"),
    "floor_landing": Surface("dirty_carpet", "#5c5747"),
    "floor_bedroom": Surface("dirty_carpet", "#5c5747"),
    "floor_kitchen": Surface("linoleum_brown", gen="vinyl_tiles", tile=1.829, own=True),   # nine-inch tiles
    "floor_bathroom": Surface("checkered_pavement_tiles"),
    "floor_utility": Surface("linoleum_brown", "#6c6757"),
    "cabinet": Surface("kitchen_wood", "#6a573f"),
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
    "carpet_runner": Surface("dirty_carpet", "#4a3330"),
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


# Models whose own colour map needs correcting. The sofa's show-wood is a
# saturated orange varnish that glows against everything else in the house:
# it is taken down to the dark walnut of the other furniture.
MODEL_FIXES = {"sofa_02": "orange_wood"}


def model_diffuse_fix(model_id: str) -> Path | None:
    """The corrected colour map for a model, if it has one."""
    return TEXTURES / "derived" / f"model_{model_id}_diff.jpg" if model_id in MODEL_FIXES else None


def tile_of(key: str) -> float | None:
    surface = SURFACES.get(key)
    if surface is None:
        return None
    return surface.tile or SETS[surface.set]


def set_file(set_id: str, kind: str) -> Path:
    return TEXTURES / set_id / f"{set_id}_{kind}_{SET_RES.get(set_id, SURFACE_RES)}.jpg"


def surface_files(key: str) -> dict[str, Path] | None:
    """The diffuse, normal and ARM (AO, roughness, metal) images for a material."""
    surface = SURFACES.get(key)
    if surface is None:
        return None
    derived = TEXTURES / "derived"
    if surface.own:
        return {kind: derived / f"{key}_{kind}.jpg" for kind in ("diff", "nor", "arm")}
    diff = derived / f"{key}_diff.jpg" if surface.tint or surface.gen else set_file(surface.set, "diff")
    arm = derived / f"{key}_arm.jpg" if surface.rough != 1.0 else set_file(surface.set, "arm")
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
            if _download(entry[SET_RES.get(set_id, SURFACE_RES)]["jpg"]["url"], set_file(set_id, kind)):
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


# --- Cabinet fronts ---------------------------------------------------------------
# Kitchen doors and drawer fronts do not tile: each is mapped to its own cell
# of one sheet, so wear can be where wear really is. Cells are (x, y, w, h) in
# pixels on a 2048 x 1024 sheet. A door's cell has its hinge edge on the left
# and its handle at the top right.
FRONTS_SIZE = (2048, 1024)
FRONT_CELLS = {
    "door_a": (0, 0, 512, 640), "door_b": (512, 0, 512, 640), "door_c": (1024, 0, 512, 640),
    "door_sink": (1536, 0, 512, 640),
    "drawer_a": (0, 640, 512, 160), "drawer_b": (512, 640, 512, 160), "drawer_c": (1024, 640, 512, 160),
    "drawer_sink": (1536, 640, 512, 160),
}
FRONT_RAIL = 60 / 512           # width of a door's frame, as a fraction of the cell


def fronts_file(kind: str) -> Path:
    return TEXTURES / "derived" / f"cabinet_fronts_{kind}.jpg"


def front_uv(cell: str, fu: float, fv: float):
    """UV of a point on a front: fu from the hinge edge, fv up from the bottom, both 0 to 1."""
    x, y, w, h = FRONT_CELLS[cell]
    return ((x + 1 + fu * (w - 2)) / FRONTS_SIZE[0], 1.0 - (y + 1 + (1.0 - fv) * (h - 2)) / FRONTS_SIZE[1])


def derive_cabinet_fronts():
    """Draw the sheet: oak-effect rails, stiles and panels with the finish
    worn off the edges, grease where hands go, kick marks at the bottom, and
    under the sink the tide marks and lifted veneer of an old leak."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    source = set_file("kitchen_wood", "diff")
    if not source.exists() or fronts_file("diff").exists():
        return
    rng = np.random.default_rng(23)
    tint = np.array([int(SURFACES["cabinet"].tint.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    wood = np.asarray(Image.open(source).convert("RGB").resize((652, 652), Image.LANCZOS), dtype=np.float32)
    wood *= tint / wood.reshape(-1, 3).mean(axis=0)
    wood = np.tile(wood, (4, 4, 1))

    def grain(w, h, across=False):
        """A piece of the wood, grain running up the piece, or along it."""
        x, y = int(rng.integers(0, 600)), int(rng.integers(0, 600))
        if across:
            return np.rot90(wood[y:y + w, x:x + h]).copy()
        return wood[y:y + h, x:x + w].copy()

    def blotches(w, h, cell):
        small = (rng.random((h // cell + 2, w // cell + 2)) * 255).astype(np.uint8)
        return np.asarray(Image.fromarray(small).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0

    def soft(mask, radius):
        image = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
        return np.asarray(image.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0

    W, H = FRONTS_SIZE
    colour = np.zeros((H, W, 3), dtype=np.float32)
    colour[:] = wood[:H, :W]
    rough = np.full((H, W), 0.50, dtype=np.float32)
    height = np.zeros((H, W), dtype=np.float32)
    bare = np.array([150.0, 124.0, 92.0], dtype=np.float32)          # finish gone, wood showing
    grease = np.array([46.0, 38.0, 28.0], dtype=np.float32)
    tide = np.array([58.0, 46.0, 34.0], dtype=np.float32)

    for name, (x0, y0, w, h) in FRONT_CELLS.items():
        door = name.startswith("door")
        rail = 60 if door else 0
        tile = grain(w, h, across=not door)
        if door:
            tile[:rail, rail:w - rail] = grain(w - 2 * rail, rail, across=True)
            tile[h - rail:, rail:w - rail] = grain(w - 2 * rail, rail, across=True)
            panel = grain(w - 2 * rail, h - 2 * rail) * 0.92
            tile[rail:h - rail, rail:w - rail] = panel
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        edge = np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy])
        noise = blotches(w, h, 22) * 0.6 + blotches(w, h, 7) * 0.4

        # the finish rubbed through along the edges, most on the handle side and along the bottom
        reach = 8.0 + 30.0 * noise + 14.0 * (xx / w) + 22.0 * np.clip((yy - h * 0.8) / (h * 0.2), 0, 1)
        worn = np.clip(1.0 - edge / reach, 0.0, 1.0) ** 1.4
        if door:                                          # and round the raised edge of the panel
            inner = np.minimum.reduce([xx - rail, w - rail - 1 - xx, yy - rail, h - rail - 1 - yy])
            worn = np.maximum(worn, np.clip(1.0 - np.abs(inner + 3.0) / (2.0 + 5.0 * noise), 0, 1) * 0.6)
        # a few scratches
        marks = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(marks)
        for _ in range(7):
            ax, ay = rng.uniform(20, w - 20), rng.uniform(20, h - 20)
            md.line([ax, ay, ax + rng.uniform(-60, 60), ay + rng.uniform(-30, 30)], fill=int(rng.uniform(90, 200)), width=1)
        worn = np.maximum(worn, np.asarray(marks, dtype=np.float32) / 255.0 * 0.7)

        # hands: a dark greasy patch round the knob, dragged down from it
        hx, hy = (w - 38.0, 85.0) if door else (w / 2.0, h / 2.0)
        spread = np.exp(-(((xx - hx) / (70.0 if door else 120.0)) ** 2 + ((yy - hy - (30.0 if door else 0.0)) / 95.0) ** 2))
        hands = np.clip(spread * (0.65 + 0.7 * noise) - 0.18, 0.0, 1.0)
        if name.endswith("_c"):                           # the worst one: drips from the top as well
            drips = soft((blotches(w, h, 5) > 0.72) * (yy < h * 0.7) * 1.0, 1.0)
            hands = np.clip(hands + drips * 0.5 * (1.0 - yy / h), 0.0, 1.0)
        # dirt lying in the corners of the frame, and kicked up along the bottom
        dirt = np.zeros((h, w), dtype=np.float32)
        if door:
            dirt = np.clip(1.0 - np.abs(inner - 4.0) / 5.0, 0, 1) * (0.35 + 0.5 * noise)
        dirt = np.maximum(dirt, np.clip((yy - h * 0.86) / (h * 0.14), 0, 1) * noise * 0.8)

        tile = tile * (1.0 - dirt[..., None] * 0.55)
        tile = tile * (1.0 - hands[..., None]) + grease * hands[..., None]
        tile = tile * (1.0 - worn[..., None] * 0.85) + bare * worn[..., None] * 0.85
        local_rough = 0.50 + 0.28 * worn - 0.26 * hands + 0.15 * dirt
        local_height = -0.5 * worn

        if name.endswith("sink"):
            # an old leak: the bottom third stained in tide lines, bleached above them, the veneer lifting
            # (the line wanders on noise alone: a sine here read as a stencilled wave)
            line = h * (0.74 + 0.16 * (blotches(w, h, 150) - 0.5) + 0.07 * (blotches(w, h, 40) - 0.5))
            below = np.clip((yy - line) / 40.0, 0.0, 1.0) * (0.55 + 0.45 * blotches(w, h, 30))
            broken = np.clip(blotches(w, h, 18) * 1.8 - 0.5, 0.0, 1.0)
            marks_ = (np.clip(1.0 - np.abs(yy - line) / 3.0, 0, 1)
                      + 0.5 * np.clip(1.0 - np.abs(yy - line - 44) / 2.5, 0, 1)) * broken
            bleach = np.clip(1.0 - np.abs(yy - line + 30) / 50.0, 0, 1) * 0.14
            tile = tile * (1.0 + bleach[..., None])
            tile = tile * (1.0 - below[..., None] * 0.34) + tide * below[..., None] * 0.34
            tile = tile * (1.0 - np.clip(marks_, 0, 1)[..., None] * 0.40)
            blister = soft((blotches(w, h, 13) > 0.80) * below, 2.0)
            tile = tile * (1.0 - blister[..., None] * 0.55) + bare * 0.9 * blister[..., None] * 0.55
            local_rough = local_rough + 0.30 * below + 0.2 * blister
            local_height = local_height + 0.9 * blister - 0.3 * below
        if door:                                          # the joints where rails meet stiles
            for jx in (rail, w - rail):
                tile[:, jx - 1:jx + 1] *= 0.62
            for jy in (rail, h - rail):
                tile[jy - 1:jy + 1, rail:w - rail] *= 0.62
        colour[y0:y0 + h, x0:x0 + w] = tile
        rough[y0:y0 + h, x0:x0 + w] = local_rough
        height[y0:y0 + h, x0:x0 + w] = local_height

    out = TEXTURES / "derived"
    Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8)).save(fronts_file("diff"), quality=93)
    arm = np.dstack((np.full((H, W), 255.0), np.clip(rough, 0.1, 1.0) * 255.0, np.zeros((H, W))))
    Image.fromarray(arm.astype(np.uint8)).save(fronts_file("arm"), quality=92)
    # normal map: the wood's own figure plus the worn and lifted places
    lum = colour.mean(axis=2) / 255.0
    fine = lum - np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.0)),
                            dtype=np.float32) / 255.0
    field = fine * 1.4 + soft(height * 0.5 + 0.5, 1.5) * 0.5
    dx = (np.roll(field, -1, axis=1) - np.roll(field, 1, axis=1)) * 6.0
    dy = (np.roll(field, -1, axis=0) - np.roll(field, 1, axis=0)) * 6.0
    normal = np.dstack((-dx, dy, np.ones_like(field)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    Image.fromarray(((normal * 0.5 + 0.5) * 255.0).astype(np.uint8)).save(fronts_file("nor"), quality=93)
    for kind in ("diff", "arm", "nor"):
        print(f"  ~ {fronts_file(kind).relative_to(HERE)}")


def _fix_orange_wood(image):
    """Darken and desaturate strongly orange pixels; leave the rest alone."""
    import numpy as np
    from PIL import Image

    pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    orange = np.clip((r - b) * 3.2 - 0.25, 0.0, 1.0) * np.clip((r - g) * 6.0, 0.0, 1.0)
    grey = pixels.mean(axis=2, keepdims=True)
    walnut = (grey * 0.55 + pixels * 0.45) * np.array([0.42, 0.36, 0.32], dtype=np.float32)
    out = pixels * (1.0 - orange[..., None]) + walnut * orange[..., None]
    return Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))


def derive():
    from PIL import Image, ImageStat

    out = TEXTURES / "derived"
    out.mkdir(parents=True, exist_ok=True)
    derive_cabinet_fronts()
    for model_id in MODEL_FIXES:
        source = MODELS / model_id / "textures" / f"{model_id}_diff_{MODEL_RES}.jpg"
        target = model_diffuse_fix(model_id)
        if source.exists() and not target.exists():
            _fix_orange_wood(Image.open(source)).save(target, quality=92)
            print(f"  ~ {target.relative_to(HERE)}")
    for key, surface in SURFACES.items():
        if surface.gen:
            import texgen
            source, target = set_file(surface.set, "diff"), out / f"{key}_diff.jpg"
            if source.exists() and not target.exists():
                maps = texgen.GENERATORS[surface.gen](Image.open(source), surface)
                for kind, image in maps.items():
                    image.save(out / f"{key}_{kind}.jpg", quality=92)
                    print(f"  ~ textures/derived/{key}_{kind}.jpg")
        elif surface.tint:
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
