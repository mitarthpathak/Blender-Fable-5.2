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
    """A crack across plaster. Plaster breaks in straight runs that jog
    sideways where they meet a lath or a joint, so the line is made of short
    straight pieces with sudden turns, never a curve; it opens widest in
    the middle, has a pale broken edge and sheds a few flakes along the way."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    lip = Image.new("L", size, 0)
    draw, lip_draw = ImageDraw.Draw(alpha), ImageDraw.Draw(lip)

    def walk(x, y, angle, length, width, depth=0):
        done = 0.0
        heading = angle
        while done < length:
            run = rng.uniform(22, 70)
            turn = rng.uniform(-0.16, 0.16) if rng.random() < 0.7 else rng.choice((-1, 1)) * rng.uniform(0.5, 1.0)
            a = heading + turn
            nx, ny = x + math.cos(a) * run, y + math.sin(a) * run
            t = done / length
            w = max(1, int(round(width * (0.35 + 1.3 * math.sin(math.pi * min(1.0, t + 0.08))))))
            draw.line([(x, y), (nx, ny)], fill=235, width=w)
            lip_draw.line([(x - 1.5, y - 1.5), (nx - 1.5, ny - 1.5)], fill=150, width=w + 2)
            if rng.random() < 0.3:                          # a flake gone from the edge
                fx, fy = x + (nx - x) * rng.random(), y + (ny - y) * rng.random()
                r = rng.uniform(2, 6)
                draw.polygon([(fx + math.cos(k * 1.26 + a) * r * rng.uniform(0.5, 1.2),
                               fy + math.sin(k * 1.26 + a) * r * rng.uniform(0.5, 1.2)) for k in range(5)], fill=200)
            if depth < 1 and rng.random() < 0.12:
                walk(nx, ny, heading + rng.choice((-1, 1)) * rng.uniform(0.6, 1.0), length * 0.3, max(1.0, width * 0.5),
                     depth + 1)
            heading += (angle - heading) * 0.5 + turn * 0.25  # it keeps to its general direction
            x, y = nx, ny
            done += run

    walk(size[0] * 0.14, size[1] * 0.08, math.radians(58), size[0] * 1.0, 2.6)
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    pale = ImageChops.subtract(lip.filter(ImageFilter.GaussianBlur(1.0)), alpha)
    image = Image.composite(Image.new("RGB", size, (150, 144, 130)), Image.new("RGB", size, (26, 22, 19)), pale)
    image.putalpha(ImageChops.lighter(alpha, pale.point(lambda v: int(v * 0.5))))
    return image


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


def runoff(seed=21, size=(512, 1024)):
    """Dirt carried down a wall by rain, for the outside: streaks that begin
    at different heights and fade in as well as out, so the patch has no top
    edge and no outline."""
    rng = random.Random(seed)
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(64):
        x = rng.uniform(0.10, 0.90) * size[0]
        start = rng.uniform(0.0, 0.35) * size[1] * rng.random()
        length = rng.uniform(0.25, 0.9) * (size[1] - start)
        width = rng.uniform(2, 12)
        strength = rng.randint(30, 120)
        steps = 30
        for k in range(steps):
            t = k / steps
            y0, y1 = start + length * t, start + length * (k + 1) / steps
            fade = int(strength * min(1.0, t * 5.0) * (1 - t) ** 1.5)
            wobble = math.sin(k * 0.5 + x) * 2.5
            draw.line([(x + wobble, y0), (x + wobble, y1)], fill=fade, width=int(width * (1 - 0.5 * t)) + 1)
    alpha = alpha.filter(ImageFilter.GaussianBlur(6))
    cloud = _noise(size, rng, 70).point(lambda v: int(90 + v * 0.65))
    alpha = ImageChops.multiply(alpha, cloud)
    edge = Image.new("L", size, 0)
    ImageDraw.Draw(edge).rectangle([size[0] * 0.14, size[1] * 0.07, size[0] * 0.86, size[1] * 0.90], fill=255)
    alpha = ImageChops.multiply(alpha, edge.filter(ImageFilter.GaussianBlur(34)))
    return _solid(size, (34, 32, 26), alpha.point(lambda v: min(255, int(v * 1.5))))


def splash(seed=22, size=(1024, 384)):
    """Mud thrown up the foot of an outside wall by rain: solid at the ground,
    breaking into spatter as it climbs, green where it never dries. Tiles
    sideways."""
    rng = random.Random(seed)
    w, h = size
    alpha = Image.new("L", size, 0)
    draw = ImageDraw.Draw(alpha)
    for _ in range(1500):
        t = rng.random() ** 2.4                                 # most of it low
        x, y = rng.uniform(0, w), h * (1.0 - t * 0.95)
        r = rng.uniform(1.0, 7.0) * (1.2 - t)
        tone = rng.randint(60, 200)
        for dx in (-w, 0, w):
            draw.ellipse([x + dx - r, y - r * rng.uniform(0.8, 1.8), x + dx + r, y + r], fill=tone)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.6))
    rise = Image.linear_gradient("L").resize(size)              # 0 at the top, 255 at the bottom
    wave = _noise((w, 8), rng, 2).resize(size, Image.BICUBIC)
    band = ImageChops.add(rise.point(lambda v: int(max(0, v - 120) * 1.9)), wave.point(lambda v: int(v * 0.35)),
                          scale=1.4)
    band = ImageChops.multiply(band, rise.point(lambda v: min(255, int(v * 1.6))))
    alpha = ImageChops.lighter(alpha, band.filter(ImageFilter.GaussianBlur(5)))
    alpha = ImageChops.multiply(alpha, rise.point(lambda v: min(255, int(v * 2.6))))
    tone = _noise(size, rng, 30)
    green = _noise(size, rng, 90).point(lambda v: max(0, int((v - 135) * 2.2)))
    earth = Image.merge("RGB", [tone.point(lambda v, b=b: int(b + (v - 128) * 0.10)) for b in (44, 38, 29)])
    algae = Image.merge("RGB", [tone.point(lambda v, b=b: int(b + (v - 128) * 0.10)) for b in (42, 50, 30)])
    image = Image.composite(algae, earth, green)
    image.putalpha(alpha.point(lambda v: int(v * 0.88)))
    return image


def _leaf(draw, x, y, length, angle, colour, alpha):
    """One fallen leaf: a pointed oval with a midrib."""
    ca, sa = math.cos(angle), math.sin(angle)
    pts = []
    for k in range(12):
        t = 2 * math.pi * k / 12
        u = math.cos(t) * length / 2
        v = math.sin(t) * length * 0.26 * (1.0 - 0.45 * abs(math.cos(t)) ** 2)
        pts.append((x + u * ca - v * sa, y + u * sa + v * ca))
    draw.polygon(pts, fill=colour + (alpha,))
    dark = tuple(int(c * 0.7) for c in colour)
    draw.line([(x - ca * length / 2, y - sa * length / 2), (x + ca * length * 0.62, y + sa * length * 0.62)],
              fill=dark + (alpha,), width=1)


LEAF_COLOURS = ((92, 66, 34), (110, 78, 36), (74, 54, 30), (120, 94, 44), (86, 50, 28), (64, 58, 36), (98, 84, 52))


def leaf_litter(seed=23, size=(1024, 1024)):
    """Fallen leaves, wet and brown, lying where the wind left them: thick in
    the middle of the patch, single leaves at its edge."""
    rng = random.Random(seed)
    under = Image.new("L", size, 0)
    ImageDraw.Draw(under).ellipse([size[0] * 0.22, size[1] * 0.22, size[0] * 0.78, size[1] * 0.78], fill=90)
    under = ImageChops.multiply(under.filter(ImageFilter.GaussianBlur(70)), _noise(size, rng, 40))
    image = Image.merge("RGBA", (*Image.new("RGB", size, (36, 30, 22)).split(), under))
    draw = ImageDraw.Draw(image)
    for _ in range(520):
        r = abs(rng.gauss(0.0, 0.19))
        a = rng.uniform(0, 2 * math.pi)
        x, y = size[0] * (0.5 + math.cos(a) * r), size[1] * (0.5 + math.sin(a) * r)
        if not (30 < x < size[0] - 30 and 30 < y < size[1] - 30):
            continue
        shade = rng.uniform(0.7, 1.15)
        colour = tuple(min(255, int(c * shade)) for c in rng.choice(LEAF_COLOURS))
        _leaf(draw, x, y, rng.uniform(26, 58), rng.uniform(0, 2 * math.pi), colour, rng.randint(215, 255))
    return image.filter(ImageFilter.GaussianBlur(0.6))


def leaf_scatter(seed=24, size=(1024, 1024)):
    """A few loose leaves and nothing else: on a path, a step, a porch."""
    rng = random.Random(seed)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for _ in range(46):
        x, y = rng.uniform(60, size[0] - 60), rng.uniform(60, size[1] - 60)
        shade = rng.uniform(0.7, 1.15)
        colour = tuple(min(255, int(c * shade)) for c in rng.choice(LEAF_COLOURS))
        _leaf(draw, x, y, rng.uniform(44, 84), rng.uniform(0, 2 * math.pi), colour, rng.randint(225, 255))
    return image.filter(ImageFilter.GaussianBlur(0.6))


def weed_tuft(seed=25, size=(512, 512)):
    """A clump of dead grass and weed stems on a card: rooted at the bottom
    middle, blades leaning every way, a few seed heads."""
    rng = random.Random(seed)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    w, h = size
    for k in range(150):
        x0 = w * (0.5 + rng.gauss(0, 0.085))
        lean = rng.gauss(0, 0.33)
        length = h * rng.uniform(0.30, 0.94) * (1.0 - 0.45 * min(1.0, abs(lean)))
        shade = rng.uniform(0.6, 1.2)
        base = rng.choice(((74, 78, 44), (96, 90, 52), (60, 68, 38), (112, 100, 62), (84, 72, 44)))
        colour = tuple(min(255, int(c * shade)) for c in base)
        steps = 12
        pts = []
        for s in range(steps + 1):
            t = s / steps
            pts.append((x0 + lean * length * t * t * 1.25 + math.sin(t * 5 + k) * 3.0, h - 2.0 - length * t))
        for s in range(steps):
            width = max(1, int(round(5.0 * (1.0 - s / steps) ** 0.8)))
            draw.line([pts[s], pts[s + 1]], fill=colour + (255,), width=width)
        if rng.random() < 0.14:                                # a seed head
            tx, ty = pts[-1]
            for j in range(6):
                sx = tx + rng.uniform(-4, 4)
                draw.ellipse([sx - 3, ty + j * 5 - 3, sx + 3, ty + j * 5 + 3], fill=(120, 104, 70, 255))
    return image


def contact_dirt(seed=26, size=(1024, 128)):
    """What gathers where a floor meets a wall: a dark line tight against the
    skirting, fluff and grit thinning out into the room. The bottom of the
    image lies against the wall. Tiles sideways."""
    rng = random.Random(seed)
    w, h = size
    fall = Image.linear_gradient("L").resize(size)              # 0 at the top, 255 at the bottom
    tight = fall.point(lambda v: int(max(0, v - 196) * 4.3))
    loose = fall.point(lambda v: int(max(0, v - 60) * 0.55))
    wide = _noise((w, 4), rng, 1).resize(size, Image.BICUBIC)   # how far the dirt reaches, varying along the wall
    patch = ImageChops.multiply(loose, wide.point(lambda v: min(255, int(max(0, v - 50) * 1.5))))
    alpha = ImageChops.lighter(tight, patch)
    draw = ImageDraw.Draw(alpha)
    for _ in range(420):
        t = rng.random() ** 2.0
        x, y = rng.uniform(0, w), h * (1.0 - t * 0.8) - 2
        r = rng.uniform(0.6, 2.4)
        tone = rng.randint(90, 210)
        for dx in (-w, 0, w):
            draw.ellipse([x + dx - r * 2, y - r, x + dx + r * 2, y + r], fill=tone)
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.3))
    alpha = ImageChops.multiply(alpha, fall.point(lambda v: min(255, int(v * 4.0))))
    tone = _noise(size, rng, 20)
    image = Image.merge("RGB", [tone.point(lambda v, b=b: int(b + (v - 128) * 0.10)) for b in (30, 27, 23)])
    image.putalpha(alpha.point(lambda v: int(v * 0.86)))
    return image


def corner_dirt(seed=27, size=(256, 256)):
    """The corner of a room nobody sweeps: darkest in the corner itself (the
    bottom left of the image), fanning out along both walls."""
    rng = random.Random(seed)
    w, h = size
    alpha = Image.new("L", size, 0)
    px = alpha.load()
    noise = _noise(size, rng, 14).load()
    for y in range(h):
        for x in range(w):
            u, v = x / w, (h - 1 - y) / h
            reach = math.hypot(u, v)
            hug = min(u, v)
            value = max(0.0, 1.0 - reach * 1.25) ** 1.6 * 0.8 \
                + max(0.0, 1.0 - hug * 9.0) * max(0.0, 1.0 - reach * 1.05) * 0.6
            px[x, y] = int(min(1.0, value * (0.55 + noise[x, y] / 255.0 * 0.8)) * 255)
    draw = ImageDraw.Draw(alpha)
    for _ in range(90):
        t = rng.random() ** 1.6
        a = rng.uniform(0, math.pi / 2)
        x, y = math.cos(a) * t * w * 0.7, h - math.sin(a) * t * h * 0.7
        r = rng.uniform(0.5, 1.8)
        draw.ellipse([x - r * 2, y - r, x + r * 2, y + r], fill=rng.randint(120, 220))
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))
    image = Image.new("RGB", size, (30, 27, 23))
    image.putalpha(alpha.point(lambda v: int(v * 0.85)))
    return image


def nicotine(seed=28, size=(512, 512)):
    """A ceiling yellowed over the place someone always sat and smoked, or
    browned over a cooker: a broad soft cloud, darker at its heart."""
    rng = random.Random(seed)
    blob = _blob(size, rng, points=22, jitter=0.16, radius=0.33).filter(ImageFilter.GaussianBlur(45))
    cloud = ImageChops.multiply(blob, _noise(size, rng, 55).point(lambda v: int(120 + v * 0.53)))
    heart = _blob(size, rng, points=16, jitter=0.25, radius=0.15).filter(ImageFilter.GaussianBlur(30))
    alpha = ImageChops.lighter(cloud.point(lambda v: int(v * 0.42)), heart.point(lambda v: int(v * 0.5)))
    image = Image.new("RGB", size, (104, 84, 46))
    image.putalpha(alpha)
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
    # quality pass: the outside, the yard, ceilings, and where floors meet walls
    "runoff": runoff,
    "splash": splash,
    "leaf_litter": leaf_litter,
    "leaf_scatter": leaf_scatter,
    "weed_tuft": weed_tuft,
    "contact_dirt": contact_dirt,
    "corner_dirt": corner_dirt,
    "nicotine": nicotine,
}


def main():
    """Draw the decals that are not on disk yet; `--force` redraws them all."""
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in DECALS.items():
        path = OUT / f"{name}.png"
        if path.exists() and "--force" not in sys.argv:
            continue
        make().save(path)
        print(f"  ~ {path.relative_to(HERE)}")


if __name__ == "__main__":
    main()
