"""Every texture the town takes from Poly Haven (CC0), and what it is for.
No bpy: this file is the manifest, and running it downloads what is missing.

    python projects/03-town/assets.py

Layout on disk (Git LFS):

    textures/<set>/<set>_{diff,nor_gl,arm}_<res>.jpg

Surfaces the player walks on or stands next to are 2K; small props are 1K.
`arm` packs ambient occlusion, roughness and metalness (R, G, B), so every
material has albedo + normal + roughness.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTURES = HERE / "textures"
API = "https://api.polyhaven.com/files/"
AGENT = {"User-Agent": "town-kit-builder"}

# set id: (resolution, real-world size of one repeat in metres, use)
SETS: dict[str, tuple[str, float, str]] = {
    "weathered_plank_siding": ("2k", 2.4, "clapboard siding on every kit house, tinted per house"),
    "distressed_painted_planks": ("2k", 1.6, "porch decks and steps"),
    "white_planks_clean": ("2k", 1.8, "trim boards, casings, porch posts (same set as the player's house)"),
    "grey_roof_01": ("2k", 3.0, "asphalt shingle roofs"),
    "roof_slates_02": ("2k", 3.0, "slate roofs (same set as the player's house)"),
    "rusty_corrugated_iron": ("1k", 1.5, "porch roofs, the shed in the vacant lot"),
    "worn_asphalt": ("2k", 2.5, "patches in the road (darker, coarser)"),
    "asphalt_02": ("2k", 3.0, "cracked asphalt on both streets (same set as the house road)"),
    "concrete_pavement": ("2k", 2.0, "sidewalk slabs"),
    "concrete_floor_worn_02": ("2k", 2.0, "curbs, paths, foundations (same set as the player's house)"),
    "leafy_grass": ("2k", 2.0, "kept lawns (same set as the player's house)"),
    "withered_grass": ("2k", 2.5, "dead lawns"),
    "brown_mud_leaves_01": ("2k", 2.5, "overgrown lawns and verges, leaf litter"),
    "forest_leaves_02": ("1k", 1.5, "leaf piles"),
    "bark_brown_02": ("1k", 1.2, "tree trunks, the fallen tree"),
    "plywood": ("1k", 1.2, "boards over windows"),
    "weathered_planks": ("1k", 1.5, "board fences, telephone poles' cross-arms"),
    "rusty_painted_metal": ("1k", 1.5, "car bodies (paint with rust coming through)"),
    "rusty_metal_02": ("1k", 1.2, "rusted car panels, trash cans, mailboxes"),
    "metal_plate": ("1k", 0.8, "manhole covers"),
    "dirty_concrete": ("1k", 2.0, "jersey barriers"),
    "rubber_tiles": ("1k", 0.6, "tyres"),
    "red_brick": ("2k", 1.4, "chimneys (same set as the player's house)"),
}

ALIASES = {"diff": ("Diffuse", "diff", "Color"), "nor_gl": ("nor_gl",), "arm": ("arm",)}


def tex(set_id: str, kind: str) -> Path:
    res = SETS[set_id][0]
    return TEXTURES / set_id / f"{set_id}_{kind}_{res}.jpg"


def tile(set_id: str) -> float:
    return SETS[set_id][1]


def _get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=180) as r:
        return r.read()


def fetch() -> None:
    for set_id, (res, _, _) in SETS.items():
        missing = [k for k in ALIASES if not tex(set_id, k).exists()]
        if not missing:
            continue
        listing = json.loads(_get(API + set_id))
        for kind in missing:
            entry = next((listing[a] for a in ALIASES[kind] if a in listing), None)
            if not entry:
                print("no", kind, "for", set_id)
                continue
            path = tex(set_id, kind)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_get(entry[res]["jpg"]["url"]))
            print("got", path.relative_to(HERE), path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    fetch()
    sys.exit(0)
