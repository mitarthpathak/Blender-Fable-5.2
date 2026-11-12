"""Turn the MakeHuman CC0 maps into game texture sets for the human.

    python3 projects/03-character/textures.py

No bpy. Reads assets/cache/mpfb/pack (see fetch.py) and writes
projects/03-character/textures/:

    skin_{diff,nor,rough}.jpg       2K
    outfit_{diff,nor,rough}.jpg     2K   jacket, shirt and jeans
    boots_{diff,nor,rough}.jpg      2K
    hair_diff.png, hair_nor.jpg     2K   alpha in the diffuse
    eyes_diff.jpg                   1K
    lashes_diff.png                 1K   eyebrows (left half) and eyelashes (right half)

MakeHuman ships colour only for skin and boots, so their normal and roughness
maps are derived from the colour map: fine surface detail, not sculpted form.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
PACK = HERE.parents[1] / "assets" / "cache" / "mpfb" / "pack"
OUT = HERE / "textures"
SIZE = 2048

SKIN = PACK / "skins/middleage_caucasian_male/middleage_lightskinned_male_diffuse.png"
SUIT = PACK / "clothes/male_casualsuit05"
BOOTS = PACK / "clothes/shoes03/shoes03_diffuse.png"
HAIR = PACK / "hair/short02"
EYES = PACK / "eyes/materials/brown_eye.png"
BROWS = PACK / "eyebrows/eyebrow001/eyebrow001.png"
LASHES = PACK / "eyelashes/eyelashes01/eyelashes01.png"


def load(path: Path, size: int = SIZE, mode: str = "RGB") -> Image.Image:
    image = Image.open(path).convert(mode)
    return image if image.size == (size, size) else image.resize((size, size), Image.LANCZOS)


def arr(image: Image.Image) -> np.ndarray:
    return np.asarray(image, dtype=np.float32) / 255.0


def img(a: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))


def save(a: np.ndarray, name: str):
    target = OUT / name
    image = img(a)
    if name.endswith(".jpg"):
        image.convert("L" if a.ndim == 2 else "RGB").save(target, quality=92)
    else:
        image.save(target, optimize=True)
    print(f"  ~ textures/{name}")


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def blur(a: np.ndarray, radius: float) -> np.ndarray:
    return arr(img(a).filter(ImageFilter.GaussianBlur(radius)))


def noise(seed: int, cell: int, size: int = SIZE) -> np.ndarray:
    """Smooth value noise in 0..1, `cell` pixels across."""
    rng = np.random.default_rng(seed)
    small = rng.random((size // cell + 2, size // cell + 2), dtype=np.float32)
    big = Image.fromarray((small * 255).astype(np.uint8)).resize((size + 2 * cell,) * 2, Image.BICUBIC)
    return arr(big)[:size, :size]


def fbm(seed: int, size: int = SIZE) -> np.ndarray:
    total = sum(noise(seed + i, cell, size) * weight
                for i, (cell, weight) in enumerate(((256, 0.5), (96, 0.25), (32, 0.15), (8, 0.10))))
    return total


def normal_from_height(height: np.ndarray, strength: float) -> np.ndarray:
    """Tangent-space normal map (OpenGL, +Y up) from a height field."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    n = np.dstack((-dx, dy, np.ones_like(height)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def detail_height(rgb: np.ndarray, fine: float, coarse: float) -> np.ndarray:
    """Band-passed luminance: the pores, weave and creases that are in the photo."""
    lum = luminance(rgb)
    return blur(lum, fine) - blur(lum, coarse)


def hsv(rgb: np.ndarray):
    hi, lo = rgb.max(axis=2), rgb.min(axis=2)
    delta = hi - lo
    sat = np.where(hi > 1e-5, delta / np.maximum(hi, 1e-5), 0.0)
    safe = np.maximum(delta, 1e-5)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hue = np.where(hi == r, ((g - b) / safe) % 6.0, np.where(hi == g, (b - r) / safe + 2.0, (r - g) / safe + 4.0))
    return hue / 6.0, sat, hi


def desaturate(rgb: np.ndarray, amount: np.ndarray | float) -> np.ndarray:
    grey = luminance(rgb)[..., None]
    amount = amount[..., None] if isinstance(amount, np.ndarray) else amount
    return rgb + (grey - rgb) * amount


# --- Sets -------------------------------------------------------------------

def skin():
    rgb = arr(load(SKIN))
    rgb = desaturate(rgb, 0.10) * np.array([0.97, 0.97, 0.99], dtype=np.float32)   # a little colder, less pink
    save(rgb, "skin_diff.jpg")
    pores = (noise(11, 2) - 0.5) * 0.35 + (noise(12, 5) - 0.5) * 0.25
    height = detail_height(rgb, 1.0, 5.0) * 1.2 + pores * 0.012
    save(normal_from_height(height, 9.0), "skin_nor.jpg")
    lum = luminance(rgb)
    rough = 0.50 + (blur(lum, 6.0) - 0.55) * 0.25 + (noise(13, 3) - 0.5) * 0.06
    save(np.clip(rough, 0.34, 0.72), "skin_rough.jpg")


def outfit():
    rgb = arr(load(SUIT / "male_casualsuit05_diffuse.png"))
    ao = arr(load(SUIT / "male_casualsuit05_ao.png", mode="L"))
    hue, sat, value = hsv(rgb)
    covered = blur((value > 0.02).astype(np.float32), 3.0)

    # The shirt's stripes are a loud pink-red: take them down to a washed-out brick.
    red = (((hue < 0.06) | (hue > 0.88)) & (sat > 0.35)).astype(np.float32)
    red = blur(red, 1.2)
    rgb = desaturate(rgb, red * 0.55) * (1.0 - red[..., None] * 0.25)
    # Denim: less saturated and a touch darker, like jeans that have been worn for years.
    blue = blur((((hue > 0.5) & (hue < 0.72)) & (sat > 0.2)).astype(np.float32), 1.5)
    rgb = desaturate(rgb, blue * 0.30) * (1.0 - blue[..., None] * 0.12)

    # Ground-in dirt: broad blotches everywhere, heavier at the trouser hems.
    blotch = np.clip((fbm(21) - 0.50) * 3.2, 0.0, 1.0)
    rows = np.linspace(0.0, 1.0, SIZE, dtype=np.float32)[:, None]
    hems = np.clip((rows - 0.88) / 0.10, 0.0, 1.0) * blue * np.clip(fbm(22) * 1.6, 0.0, 1.0)
    dirt = np.clip(blotch * 0.22 + hems * 0.55, 0.0, 0.6)[..., None]
    rgb = rgb * (1.0 - dirt) + rgb * np.array([0.42, 0.36, 0.28], dtype=np.float32) * dirt
    rgb *= (0.72 + 0.28 * ao)[..., None]                    # contact shadow in folds and under flaps
    save(rgb, "outfit_diff.jpg")

    nor = arr(load(SUIT / "male_casualsuit05_normal.png"))
    weave = normal_from_height(detail_height(rgb, 0.7, 3.0) * 1.6, 10.0)
    mixed = np.dstack((nor[..., 0] + weave[..., 0] - 0.5, nor[..., 1] + weave[..., 1] - 0.5, nor[..., 2]))
    save(mixed, "outfit_nor.jpg")

    rough = 0.86 - blue * 0.06 + (noise(23, 4) - 0.5) * 0.08 + dirt[..., 0] * 0.08
    save(np.clip(rough, 0.6, 0.98) * np.clip(covered + 0.6, 0.0, 1.0), "outfit_rough.jpg")


def boots():
    rgb = arr(load(BOOTS))
    lum = luminance(rgb)[..., None]
    rgb = rgb * 0.85 + lum * 0.15
    scuff = np.clip((fbm(31) - 0.52) * 4.0, 0.0, 1.0)[..., None]
    rgb = rgb * (1.0 - scuff * 0.5) + np.array([0.20, 0.17, 0.14], dtype=np.float32) * scuff * 0.5
    save(rgb, "boots_diff.jpg")
    height = detail_height(rgb, 1.2, 8.0) * 2.5 + (noise(32, 3) - 0.5) * 0.012
    save(normal_from_height(height, 16.0), "boots_nor.jpg")
    rough = 0.50 + scuff[..., 0] * 0.32 + (noise(33, 6) - 0.5) * 0.12 - blur(luminance(rgb), 3.0) * 0.15
    save(np.clip(rough, 0.3, 0.92), "boots_rough.jpg")


def hair():
    rgba = arr(load(HAIR / "short02_diffuse.png", mode="RGBA"))
    rgba[..., :3] = desaturate(rgba[..., :3], 0.15) * 0.82
    save(rgba, "hair_diff.png")
    save(arr(load(HAIR / "short02_normal.png")), "hair_nor.jpg")


def eyes():
    rgba = arr(load(EYES, 1024, "RGBA"))
    white = np.array([0.80, 0.78, 0.76], dtype=np.float32)
    rgb = rgba[..., :3] * rgba[..., 3:] + white * (1.0 - rgba[..., 3:])
    # The iris is a saturated red-brown in the source: bring it to an ordinary dark brown.
    hue, sat, value = hsv(rgb)
    iris = blur((sat > 0.45).astype(np.float32), 2.0)
    rgb = desaturate(rgb, iris * 0.45) * (1.0 - iris[..., None] * 0.30)
    rgb = rgb * (1.0 - iris[..., None]) + rgb * np.array([1.0, 0.95, 0.72], dtype=np.float32) * iris[..., None]
    save(rgb, "eyes_diff.jpg")


def lashes():
    sheet = np.zeros((512, 1024, 4), dtype=np.float32)
    sheet[:, :512] = arr(load(BROWS, 512, "RGBA"))
    sheet[:, 512:] = arr(load(LASHES, 512, "RGBA"))
    save(sheet, "lashes_diff.png")


def main():
    if not PACK.is_dir():
        raise SystemExit("Run fetch.py first: the MakeHuman asset pack is missing.")
    OUT.mkdir(exist_ok=True)
    for step in (skin, outfit, boots, hair, eyes, lashes):
        step()


if __name__ == "__main__":
    main()
