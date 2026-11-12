"""Generate the grime and damage decal textures. Plain Python with Pillow,
seeded, so the same images come out every time.

    python3 projects/01-house-interior/decals.py

Each decal is an RGBA PNG in textures/decals/. In the scene they sit on thin
planes a millimetre or two off the wall, blended over the paint.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "textures" / "decals"
BRICK = HERE / "textures" / "red_brick" / "red_brick_diff_2k.jpg"


def _blob(size, rng, points=14, jitter=0.35, radius=0.36):
    """An irregular filled shape as an L mask."""
    w, h = size
    mask = Image.new("L", size, 0)
    cx, cy = w / 2, h / 2
    poly = []
    for i in range(points):
        a = 2 * math.pi * i / points
        r = radius * (1 + rng.uniform(-jitter, jitter))
        poly.append((cx + math.cos(a) * r * w, cy + math.sin(a) * r * h))
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    return mask


def _solid(size, color, alpha):
    image = Image.new("RGBA", size, color + (0,))
    image.putalpha(alpha)
    return image


def grime_streaks(seed=1, size=(512, 1024)):
    """Dirt washed down a wall: dense at the top, thinning as it falls."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(46):
        x = rng.uniform(0.04, 0.96) * size[0]
        length = rng.uniform(0.25, 0.95) * size[1]
        width = rng.uniform(2, 14)
        strength = rng.randint(40, 150)
        steps = 24
        for k in range(steps):
            y0, y1 = length * k / steps, length * (k + 1) / steps
            fade = int(strength * (1 - k / steps) ** 1.6)
            wobble = math.sin(k * 0.6 + x) * 2
            draw.line([(x + wobble, y0), (x + wobble, y1)], fill=fade, width=int(width * (1 - 0.5 * k / steps)) + 1)
    band = Image.new("L", size, 0)
    ImageDraw.Draw(band).rectangle([0, 0, size[0], size[1] * 0.06], fill=120)
    alpha = ImageChops.lighter(alpha, band).filter(ImageFilter.GaussianBlur(5))
    edge = Image.linear_gradient("L").resize(size).point(lambda v: 255 - v)       # fade out downward
    sides = Image.new("L", size, 0)
    ImageDraw.Draw(sides).rectangle([size[0] * 0.06, 0, size[0] * 0.94, size[1]], fill=255)
    alpha = ImageChops.multiply(ImageChops.multiply(alpha, edge), sides.filter(ImageFilter.GaussianBlur(18)))
    return _solid(size, (38, 31, 24), alpha.point(lambda v: int(v * 0.9)))


def floor_grime(seed=2, size=(1024, 256)):
    """Scuffs and dirt along the bottom of a wall, heaviest at the skirting."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(140):
        x = rng.uniform(0, size[0])
        y = size[1] * (1 - rng.random() ** 2.2 * 0.9)
        w, h = rng.uniform(10, 90), rng.uniform(2, 12)
        draw.ellipse([x - w, y - h, x + w, y + h], fill=rng.randint(30, 120))
    for _ in range(26):                                   # darker scuff strokes
        x, y = rng.uniform(0, size[0]), size[1] * rng.uniform(0.35, 0.95)
        draw.line([(x, y), (x + rng.uniform(30, 160), y + rng.uniform(-6, 6))], fill=rng.randint(90, 170),
                  width=rng.randint(2, 5))
    alpha = alpha.filter(ImageFilter.GaussianBlur(6))
    rise = Image.linear_gradient("L").resize(size)                              # 0 at top, 255 at bottom
    alpha = ImageChops.multiply(alpha, rise.point(lambda v: min(255, int(v * 1.25))))
    return _solid(size, (30, 26, 22), alpha)


def water_stain(seed=3, size=(1024, 1024)):
    """A dried leak: a pale brown patch with darker tide marks."""
    rng = random.Random(seed)
    rgb = Image.new("RGB", size, (96, 74, 44))
    alpha = Image.new("L", size, 0)
    for k, (radius, strength) in enumerate(((0.40, 70), (0.31, 55), (0.22, 60))):
        blob = _blob(size, rng, points=30, jitter=0.10, radius=radius).filter(ImageFilter.GaussianBlur(26))
        blob = blob.point(lambda v: 255 if v > 110 else 0).filter(ImageFilter.GaussianBlur(9))
        inner = blob.filter(ImageFilter.GaussianBlur(26)).point(lambda v: 255 if v > 150 else 0)
        ring = ImageChops.subtract(blob, inner.filter(ImageFilter.GaussianBlur(14)))
        layer = ImageChops.lighter(ring.point(lambda v, s=strength: int(v * s / 255 * 1.6)),
                                   blob.point(lambda v, s=strength: int(v * s / 255 * 0.45)))
        alpha = ImageChops.lighter(alpha, layer)
    return _solid(size, rgb.getpixel((0, 0)), alpha.filter(ImageFilter.GaussianBlur(3)))


def crack(seed=4, size=(1024, 1024)):
    """A crack wandering across plaster, with a few branches."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)

    def walk(x, y, angle, length, width, depth=0):
        steps = int(length / 9)
        for k in range(steps):
            angle += rng.uniform(-0.45, 0.45)
            nx, ny = x + math.cos(angle) * 9, y + math.sin(angle) * 9
            w = max(1, int(width * (1 - k / steps) + 0.5))
            draw.line([(x, y), (nx, ny)], fill=230, width=w)
            if depth < 2 and rng.random() < 0.07:
                walk(nx, ny, angle + rng.choice((-1, 1)) * rng.uniform(0.5, 1.1), length * 0.45, max(1, width - 1),
                     depth + 1)
            x, y = nx, ny

    walk(size[0] * 0.12, size[1] * 0.1, math.radians(52), size[0] * 1.15, 4)
    soft = alpha.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * 0.35))
    alpha = ImageChops.lighter(alpha.filter(ImageFilter.GaussianBlur(0.7)), soft)
    return _solid(size, (22, 19, 17), alpha)


def _noise(size, rng, scale):
    """Soft random blotches, 0-255, for breaking up clean edges."""
    small = Image.new("L", (max(2, size[0] // scale), max(2, size[1] // scale)))
    small.putdata([rng.randint(0, 255) for _ in range(small.size[0] * small.size[1])])
    return small.resize(size, Image.BICUBIC)


def plaster_damage(seed=5, size=(1024, 1024)):
    """Plaster broken away to the brick behind. The break is ragged: the
    outline is roughened at two scales, the plaster round it is crumbled and
    stained, and hairline cracks run out from it."""
    rng = random.Random(seed)
    soft = _blob(size, rng, points=26, jitter=0.22, radius=0.27).filter(ImageFilter.GaussianBlur(28))
    rough = ImageChops.add(soft, ImageChops.add(_noise(size, rng, 48), _noise(size, rng, 12), scale=2.0), scale=2.0)
    hole = rough.point(lambda v: 255 if v > 118 else 0).filter(ImageFilter.GaussianBlur(1.0))
    hole = hole.point(lambda v: 255 if v > 128 else 0)
    # crumbled zone: a wider, patchier area where the skim coat has gone
    crumb = ImageChops.add(soft, _noise(size, rng, 9).point(lambda v: int(v * 0.42))).point(
        lambda v: 255 if v > 150 else 0)
    crumb = ImageChops.subtract(crumb, hole)
    if BRICK.exists():
        brick = Image.open(BRICK).convert("RGB").crop((300, 300, 1324, 1324)).resize(size)
        brick = brick.point(lambda v: int(v * 0.55))
    else:
        brick = Image.new("RGB", size, (92, 54, 42))
    under = Image.merge("RGB", [_noise(size, rng, 6).point(lambda v, b=b: int(b + (v - 128) * 0.18))
                                for b in (150, 142, 126)])               # bare undercoat
    image = Image.composite(brick, under, hole)
    depth = ImageChops.subtract(hole, hole.filter(ImageFilter.MinFilter(31))).filter(ImageFilter.GaussianBlur(7))
    image = Image.composite(Image.new("RGB", size, (22, 16, 13)), image, depth.point(lambda v: int(v * 0.8)))
    # hairline cracks out of the break
    cracks = Image.new("L", size, 0)
    draw = ImageDraw.Draw(cracks)
    for _ in range(7):
        ang = rng.uniform(0, 2 * math.pi)
        x, y = size[0] / 2 + math.cos(ang) * size[0] * 0.24, size[1] / 2 + math.sin(ang) * size[1] * 0.24
        for k in range(rng.randint(14, 30)):
            ang += rng.uniform(-0.4, 0.4)
            nx, ny = x + math.cos(ang) * 9, y + math.sin(ang) * 9
            draw.line([(x, y), (nx, ny)], fill=200, width=2 if k < 8 else 1)
            x, y = nx, ny
    stain = soft.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.22))
    alpha = ImageChops.lighter(ImageChops.lighter(hole, crumb.point(lambda v: int(v * 0.92))),
                               ImageChops.lighter(cracks.filter(ImageFilter.GaussianBlur(0.6)), stain))
    dark = Image.new("RGB", size, (40, 34, 28))
    outside = ImageChops.lighter(hole, crumb)
    image = Image.composite(image, dark, outside)
    image.putalpha(alpha)
    return image


def smudge(seed=6, size=(512, 512)):
    """Hand marks: the grey patch that builds up round a switch or a door edge."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(40):
        x, y = rng.gauss(size[0] / 2, size[0] * 0.13), rng.gauss(size[1] / 2, size[1] * 0.15)
        r = rng.uniform(14, 46)
        draw.ellipse([x - r, y - r * 1.3, x + r, y + r * 1.3], fill=rng.randint(20, 70))
    return _solid(size, (44, 38, 32), alpha.filter(ImageFilter.GaussianBlur(16)))


def moss(seed=8, size=(1024, 512)):
    """Green-brown growth where a wall stays wet: dense at the bottom, breaking up as it climbs."""
    rng = random.Random(seed)
    base = ImageChops.add(_noise(size, rng, 40), _noise(size, rng, 10), scale=2.0)
    rise = Image.linear_gradient("L").resize(size)                       # 0 at top, 255 at bottom
    alpha = ImageChops.multiply(base.point(lambda v: 255 if v > 118 else int(v * 0.5)), rise.point(
        lambda v: min(255, int(v * 1.4))))
    alpha = alpha.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.85))
    tone = _noise(size, rng, 16)
    image = Image.merge("RGB", [tone.point(lambda v, b=b, k=k: int(b + (v - 128) * k))
                                for b, k in ((52, 0.12), (62, 0.16), (38, 0.08))])
    image.putalpha(alpha)
    return image


def mould(seed=11, size=(1024, 1024)):
    """Black mould: dense speckle spreading out of one corner (top left)."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(2600):
        t = rng.random() ** 1.9                                   # most of it close to the corner
        angle = rng.uniform(0.0, math.pi / 2)
        r = t * size[0] * 1.05
        x, y = math.cos(angle) * r + rng.gauss(0, 12), math.sin(angle) * r + rng.gauss(0, 12)
        dot = rng.uniform(1.5, 9.0) * (1.25 - t)
        draw.ellipse([x - dot, y - dot, x + dot, y + dot], fill=rng.randint(70, 230))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.6))
    haze = _noise(size, rng, 10).point(lambda v: max(0, v - 120))
    fall = Image.radial_gradient("L").resize((size[0] * 2, size[1] * 2)).crop((size[0], size[1], size[0] * 2, size[1] * 2))
    haze = ImageChops.multiply(haze, ImageChops.invert(fall))
    alpha = ImageChops.lighter(alpha, haze.point(lambda v: min(255, int(v * 1.6))))
    tone = _noise(size, rng, 24)
    image = Image.merge("RGB", [tone.point(lambda v, b=b: int(b + (v - 128) * 0.10)) for b in (26, 30, 24)])
    image.putalpha(alpha)
    return image


def rust_stain(seed=13, size=(512, 1024)):
    """Rust run down from a fitting: an orange-brown bloom at the top with drips."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(22):
        x = size[0] * (0.5 + rng.gauss(0, 0.13))
        length = rng.uniform(0.25, 0.98) * size[1]
        width = rng.uniform(4, 22)
        for k in range(30):
            y0, y1 = length * k / 30, length * (k + 1) / 30
            draw.line([(x + math.sin(k * 0.4) * 2, y0), (x + math.sin(k * 0.4) * 2, y1)],
                      fill=int(rng.randint(90, 200) * (1 - k / 30) ** 1.3), width=int(width * (1 - 0.6 * k / 30)) + 1)
    draw.ellipse([size[0] * 0.2, -size[1] * 0.06, size[0] * 0.8, size[1] * 0.10], fill=200)
    alpha = alpha.filter(ImageFilter.GaussianBlur(5))
    tone = _noise(size, rng, 14)
    image = Image.merge("RGB", [tone.point(lambda v, b=b, k=k: int(b + (v - 128) * k))
                                for b, k in ((126, 0.25), (66, 0.18), (30, 0.10))])
    image.putalpha(alpha)
    return image


def grease(seed=14, size=(1024, 1024)):
    """Cooking grease: a yellow-brown film, heaviest in the middle, with spatter."""
    rng = random.Random(seed)
    film = _noise(size, rng, 6).point(lambda v: max(0, int((v - 90) * 1.5)))
    centre = ImageChops.invert(Image.radial_gradient("L").resize(size))
    alpha = ImageChops.multiply(film, centre.point(lambda v: min(255, int(v * 1.5))))
    draw = ImageDraw.Draw(alpha)
    for _ in range(420):
        x, y = rng.gauss(size[0] / 2, size[0] * 0.22), rng.gauss(size[1] / 2, size[1] * 0.22)
        r = rng.uniform(1.0, 6.5)
        draw.ellipse([x - r, y - r * rng.uniform(0.8, 1.6), x + r, y + r * rng.uniform(0.8, 1.6)],
                     fill=rng.randint(120, 235))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: int(v * 0.8))
    tone = _noise(size, rng, 18)
    image = Image.merge("RGB", [tone.point(lambda v, b=b, k=k: int(b + (v - 128) * k))
                                for b, k in ((96, 0.2), (72, 0.16), (34, 0.1))])
    image.putalpha(alpha)
    return image


def burnt(seed=15, size=(512, 512)):
    """Spills burnt black onto a hob, round the burners."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for cx, cy in ((0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)):
        for _ in range(26):
            a, r = rng.uniform(0, 6.28), size[0] * rng.uniform(0.10, 0.21)
            x, y = cx * size[0] + math.cos(a) * r, cy * size[1] + math.sin(a) * r
            blob = rng.uniform(6, 30)
            draw.ellipse([x - blob, y - blob * 0.7, x + blob, y + blob * 0.7], fill=rng.randint(80, 230))
    alpha = alpha.filter(ImageFilter.GaussianBlur(4))
    tone = _noise(size, rng, 12)
    image = Image.merge("RGB", [tone.point(lambda v, b=b, k=k: int(b + (v - 128) * k))
                                for b, k in ((58, 0.3), (40, 0.22), (26, 0.12))])
    image.putalpha(alpha)
    return image


def limescale(seed=16, size=(512, 1024)):
    """Chalky run-off below a tap: pale, streaked, crusted at the top."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(30):
        x = size[0] * (0.5 + rng.gauss(0, 0.16))
        length = rng.uniform(0.3, 0.95) * size[1]
        draw.line([(x, 0), (x + rng.uniform(-8, 8), length)], fill=rng.randint(60, 170), width=rng.randint(3, 16))
    alpha = alpha.filter(ImageFilter.GaussianBlur(6))
    fall = ImageChops.invert(Image.linear_gradient("L").resize(size))
    alpha = ImageChops.multiply(alpha, fall.point(lambda v: min(255, int(60 + v * 0.9))))
    tone = _noise(size, rng, 10)
    image = Image.merge("RGB", [tone.point(lambda v, b=b: int(b + (v - 128) * 0.12)) for b in (176, 172, 150)])
    image.putalpha(alpha)
    return image


def stain_rings(seed=17, size=(512, 512)):
    """Mug rings and a spill on a table or counter."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(5):
        x, y, r = rng.uniform(0.2, 0.8) * size[0], rng.uniform(0.2, 0.8) * size[1], rng.uniform(34, 44)
        draw.ellipse([x - r, y - r, x + r, y + r], outline=rng.randint(110, 200), width=rng.randint(3, 6))
    spill = _blob(size, rng, points=18, jitter=0.5, radius=0.17).point(lambda v: int(v * 0.42))
    alpha = ImageChops.lighter(alpha, ImageChops.offset(spill, 60, -40)).filter(ImageFilter.GaussianBlur(1.5))
    image = Image.new("RGB", size, (58, 40, 26))
    image.putalpha(alpha)
    return image


def scuffs(seed=18, size=(1024, 128)):
    """Knocks along a skirting board: dark rubber scuffs, and chips where the
    paint has gone and the wood shows."""
    rng = random.Random(seed)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for _ in range(46):
        x, y = rng.uniform(0, size[0]), rng.uniform(size[1] * 0.25, size[1] * 0.95)
        length, tilt = rng.uniform(18, 110), rng.uniform(-0.12, 0.12)
        shade = rng.randint(24, 60)
        draw.line([(x, y), (x + length, y + length * tilt)], fill=(shade, shade, shade - 4, rng.randint(70, 190)),
                  width=rng.randint(2, 6))
    for _ in range(16):
        x, y = rng.uniform(0, size[0]), rng.uniform(size[1] * 0.1, size[1] * 0.9)
        w, h = rng.uniform(6, 26), rng.uniform(4, 14)
        draw.polygon([(x, y), (x + w, y + rng.uniform(-3, 3)), (x + w * 0.8, y + h), (x + w * 0.1, y + h * 0.8)],
                     fill=(126, 100, 72, 235), outline=(60, 50, 40, 255))
    return image.filter(ImageFilter.GaussianBlur(0.8))


def dust(seed=19, size=(512, 512)):
    """Dust lying on a flat top: a pale film, thicker towards the back, with
    clean marks where things stood and a finger dragged through it."""
    rng = random.Random(seed)
    film = _noise(size, rng, 14).point(lambda v: int(70 + v * 0.45))
    back = ImageChops.invert(Image.linear_gradient("L").resize(size)).point(lambda v: int(120 + v * 0.53))
    alpha = ImageChops.multiply(film, back)
    draw = ImageDraw.Draw(alpha)
    for _ in range(3):
        x, y, r = rng.uniform(80, 430), rng.uniform(80, 430), rng.uniform(26, 48)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=18)
    x, y = rng.uniform(60, 300), rng.uniform(250, 400)
    draw.rectangle([x, y, x + rng.uniform(70, 130), y + rng.uniform(40, 80)], fill=20)
    draw.line([(60, 440), (190, 400), (330, 452), (450, 410)], fill=30, width=11, joint="curve")
    alpha = alpha.filter(ImageFilter.GaussianBlur(2.2))
    edge = Image.new("L", size, 0)
    ImageDraw.Draw(edge).rectangle([14, 14, size[0] - 14, size[1] - 14], fill=255)
    alpha = ImageChops.multiply(alpha, edge.filter(ImageFilter.GaussianBlur(10)))
    image = Image.new("RGB", size, (150, 146, 136))
    image.putalpha(alpha.point(lambda v: int(v * 0.62)))
    return image


DECALS = {
    "scuffs": scuffs,
    "dust": dust,
    "mould": mould,
    "rust_stain": rust_stain,
    "grease": grease,
    "burnt": burnt,
    "limescale": limescale,
    "stain_rings": stain_rings,
    "moss": moss,
    "grime_streaks": grime_streaks,
    "floor_grime": floor_grime,
    "water_stain": water_stain,
    "crack": crack,
    "plaster_damage": plaster_damage,
    "smudge": smudge,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in DECALS.items():
        path = OUT / f"{name}.png"
        make().save(path)
        print(f"  ~ {path.relative_to(HERE)}")


if __name__ == "__main__":
    main()
