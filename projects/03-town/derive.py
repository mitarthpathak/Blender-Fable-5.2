"""Derived and generated textures for the town (plain Python: PIL + numpy).

    python projects/03-town/derive.py

- textures/derived/*_neutral_diff.jpg: Poly Haven albedo maps turned into
  near-white, colourless versions that keep every stain and grain. The
  vertex colour of each surface then supplies the paint colour, so one
  siding material serves every house.
- textures/decals/*.png: small RGBA maps drawn here: faded road paint,
  chain-link, grass tufts, puddles, oil stains and two signs. The grime,
  moss and crack decals are copied from the player's house project.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
TEX = HERE / "textures"
DERIVED = TEX / "derived"
DECALS = TEX / "decals"
RNG = np.random.default_rng(7)

# Linear mean the neutral maps are pulled to. Vertex colour = wanted albedo / this.
NEUTRAL_MEAN = 0.75


def srgb_to_lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def neutral(src: Path, dst: Path, contrast: float = 1.0, keep_chroma: float = 0.0):
    a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32) / 255.0
    lin = srgb_to_lin(a)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    rel = lum / max(lum.mean(), 1e-4)
    rel = 1.0 + (rel - 1.0) * contrast
    out = np.clip(rel * NEUTRAL_MEAN, 0.04, 1.0)[..., None].repeat(3, axis=2)
    if keep_chroma > 0:
        chroma = lin / np.maximum(lum[..., None], 1e-4)
        out = out * (1 - keep_chroma + keep_chroma * chroma)
    img = Image.fromarray((lin_to_srgb(out) * 255).astype(np.uint8))
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, quality=92)
    print("derived", dst.relative_to(HERE))


def noise(size: int, scale: int, octaves: int = 4) -> np.ndarray:
    """Tileable value noise in 0..1."""
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = scale * 2 ** o
        grid = RNG.random((n, n)).astype(np.float32)
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        # wrap: blend with a rolled copy so edges tile
        layer = np.asarray(img, np.float32) / 255.0
        out += amp * layer
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / max(out.max() - out.min(), 1e-6)


def save_rgba(arr: np.ndarray, name: str):
    DECALS.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGBA").save(DECALS / f"{name}.png")
    print("decal", name)


def marking(name: str, rgb):
    """Worn road paint: a strip 1 m long of paint with gaps worn through."""
    w, h = 64, 512
    n = noise(512, 6)[:, :w]
    n2 = noise(512, 40, 2)[:, :w]
    alpha = ((n * 0.65 + n2 * 0.35) > 0.42).astype(np.float32)
    col = np.ones((h, w, 3), np.float32) * np.array(rgb, np.float32)
    col *= (0.85 + 0.15 * n2)[..., None]
    save_rgba(np.dstack([col, alpha]), name)


def chainlink():
    """Diamond wire mesh, 5 cm diamonds, 1 m per repeat, galvanised grey with rust."""
    s = 512
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    step = s // 20
    for k in range(-20, 41):
        x = k * step
        d.line([(x, 0), (x + s, s)], fill=(150, 150, 145, 255), width=3)
        d.line([(x, s), (x + s, 0)], fill=(150, 150, 145, 255), width=3)
    a = np.asarray(img, np.float32) / 255.0
    rust = noise(s, 5)
    a[..., 0] *= 0.75 + 0.35 * rust
    a[..., 1] *= 0.72 + 0.20 * rust
    a[..., 2] *= 0.70 + 0.10 * rust
    save_rgba(a, "chainlink")


def grass_tuft():
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(11)
    for _ in range(140):
        x0 = rng.uniform(10, s - 10)
        hgt = rng.uniform(0.35, 0.98) * s
        lean = rng.uniform(-0.35, 0.35) * hgt
        dry = rng.random()
        g = (int(70 + 60 * dry), int(78 + 40 * dry), int(42 + 20 * dry), 255)
        pts = [(x0 + lean * (t / 6) ** 1.5, s - hgt * t / 6) for t in range(7)]
        d.line(pts, fill=g, width=int(rng.uniform(2, 4)))
    img = img.filter(ImageFilter.SMOOTH)
    save_rgba(np.asarray(img, np.float32) / 255.0, "grass_tuft")


def puddle():
    s = 256
    y, x = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(x ** 2 + y ** 2)
    n = noise(s, 4)
    edge = 0.62 + 0.28 * (n - 0.5) * 2
    alpha = np.clip((edge - r) / 0.22, 0, 1) * 0.72
    col = np.ones((s, s, 3), np.float32) * np.array([0.085, 0.09, 0.10])
    save_rgba(np.dstack([col, alpha]), "puddle")


def oil_stain():
    s = 256
    y, x = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt((x * 0.8) ** 2 + y ** 2)
    n = noise(s, 5)
    alpha = np.clip((0.75 + 0.3 * (n - 0.5) - r) / 0.3, 0, 1) * 0.75
    col = np.ones((s, s, 3), np.float32) * np.array([0.03, 0.03, 0.028])
    save_rgba(np.dstack([col, alpha]), "oil_stain")


def _font(size):
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def sign(name, lines, bg, fg, size=(512, 256)):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, size[0] - 9, size[1] - 9], outline=fg, width=8)
    font = _font(int(size[1] / (len(lines) + 1.2)))
    total = len(lines)
    for i, line in enumerate(lines):
        w = d.textlength(line, font=font)
        d.text(((size[0] - w) / 2, size[1] * (i + 0.6) / (total + 0.4) - font.size * 0.45), line, fill=fg, font=font)
    a = np.asarray(img, np.float32) / 255.0
    grime = noise(size[0], 6)[: size[1], : size[0]]
    a *= (0.72 + 0.28 * grime)[..., None]
    save_rgba(np.dstack([a, np.ones(a.shape[:2], np.float32)]), name)


def lawn_rough():
    """The leafy grass map, drier and patchier, for lawns nobody has cut."""
    a = np.asarray(Image.open(TEX / "leafy_grass/leafy_grass_diff_2k.jpg").convert("RGB"), np.float32) / 255.0
    lin = srgb_to_lin(a)
    n = noise(a.shape[0], 5)[..., None]
    dry = lin * np.array([1.08, 0.95, 0.72], np.float32)
    out = lin * (1 - 0.55 * n) + dry * (0.55 * n)
    out *= 0.85 + 0.25 * noise(a.shape[0], 12)[..., None]
    DERIVED.mkdir(parents=True, exist_ok=True)
    Image.fromarray((lin_to_srgb(out) * 255).astype(np.uint8)).save(DERIVED / "lawn_rough_diff.jpg", quality=92)
    print("derived lawn_rough")


def leaf_litter():
    """Scattered fallen leaves on transparent ground, for roads and sidewalks."""
    s = 512
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(23)
    for _ in range(260):
        x, y = rng.uniform(0, s, 2)
        r = rng.uniform(5, 13)
        a = rng.uniform(0, np.pi)
        tone = rng.uniform(0.0, 1.0)
        col = (int(78 + 52 * tone), int(60 + 38 * tone), int(38 + 20 * tone), 255)       # damp browns, not red
        pts = [(x + np.cos(a + t) * r * (1.0 if k % 2 == 0 else 0.45), y + np.sin(a + t) * r * (1.0 if k % 2 == 0 else 0.45))
               for k, t in enumerate(np.linspace(0, 2 * np.pi, 9)[:-1])]
        d.polygon(pts, fill=col)
    a = np.asarray(img.filter(ImageFilter.SMOOTH), np.float32) / 255.0
    # fade towards the edges so cards do not show their square
    yy, xx = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    a[..., 3] *= np.clip((1.0 - np.sqrt(xx ** 2 + yy ** 2)) / 0.35, 0, 1)
    save_rgba(a, "leaf_litter")


def main():
    neutral(TEX / "weathered_plank_siding/weathered_plank_siding_diff_2k.jpg", DERIVED / "siding_neutral_diff.jpg",
            contrast=0.8)
    neutral(TEX / "white_planks_clean/white_planks_clean_diff_2k.jpg", DERIVED / "trim_neutral_diff.jpg",
            contrast=1.3)
    neutral(TEX / "distressed_painted_planks/distressed_painted_planks_diff_2k.jpg", DERIVED / "door_neutral_diff.jpg",
            contrast=1.0, keep_chroma=0.35)
    neutral(TEX / "rusty_painted_metal/rusty_painted_metal_diff_1k.jpg", DERIVED / "metal_neutral_diff.jpg",
            contrast=0.9, keep_chroma=0.15)
    neutral(TEX / "rusty_metal_02/rusty_metal_02_diff_1k.jpg", DERIVED / "carpaint_neutral_diff.jpg",
            contrast=0.8, keep_chroma=0.7)
    lawn_rough()
    marking("marking_yellow", (0.62, 0.50, 0.20))
    marking("marking_white", (0.68, 0.67, 0.62))
    chainlink()
    grass_tuft()
    puddle()
    leaf_litter()
    oil_stain()
    sign("sign_road_closed", ["ROAD", "CLOSED"], (176, 70, 30), (232, 226, 210))
    sign("sign_for_sale", ["FOR SALE", "HALDEN REALTY"], (210, 205, 190), (120, 30, 25))


if __name__ == "__main__":
    main()
