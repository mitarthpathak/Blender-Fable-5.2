"""Surfaces that are drawn rather than photographed: a block foundation, square
bathroom tiles, vinyl floor tiles, a striped wallpaper. Plain numpy and Pillow,
seeded, so the same maps come out every time. assets.py calls these from
`derive()`; each takes the photographed base it is painted over and returns
the maps it makes.

Every generator returns a dict with "diff" and, when the surface owns its
maps, "nor" and "arm" (AO, roughness, metal in R, G, B) as PIL images. All
of them tile.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def _rgb(hex_colour):
    return np.array([int(hex_colour.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _base(image, size, tint=None, grey=0.0):
    """The photograph, resized, optionally pulled towards grey and tinted to a mean colour."""
    pixels = np.asarray(image.convert("RGB").resize((size, size), Image.LANCZOS), dtype=np.float32)
    if grey:
        pixels = pixels * (1.0 - grey) + pixels.mean(axis=2, keepdims=True) * grey
    if tint:
        pixels *= _rgb(tint) / np.maximum(pixels.reshape(-1, 3).mean(axis=0), 1.0)
    return pixels


def _noise(rng, size, cell):
    """Soft tiling noise, 0 to 1."""
    n = max(2, size // cell)
    small = rng.random((n, n)).astype(np.float32)
    small = np.pad(small, 2, mode="wrap")
    big = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize(
        (size * (n + 4) // n, size * (n + 4) // n), Image.BICUBIC), dtype=np.float32) / 255.0
    o = size * 2 // n
    return big[o:o + size, o:o + size]


def _blur(field, radius):
    """Gaussian blur that wraps, so the result still tiles."""
    size = field.shape[0]
    pad = int(radius * 3) + 1
    wide = np.pad(field, pad, mode="wrap")
    lo, hi = float(wide.min()), float(wide.max())
    span = max(hi - lo, 1e-6)
    image = Image.fromarray(((wide - lo) / span * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    return (np.asarray(image, dtype=np.float32) / 255.0 * span + lo)[pad:pad + size, pad:pad + size]


def _normal(height, strength):
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    n = np.dstack((-dx, dy, np.ones_like(height)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255.0).astype(np.uint8))


def _arm(ao, rough, metal=None):
    metal = np.zeros_like(rough) if metal is None else metal
    return Image.fromarray((np.dstack((ao, rough, metal)).clip(0, 1) * 255.0).astype(np.uint8))


def _image(pixels):
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


# --- Foundation: painted concrete block -------------------------------------------

def blocks(image, surface, size=1024, across=5, courses=10):
    """Concrete blocks in running bond, 40 x 20 cm on a 2 m repeat: each a
    slightly different grey, mortar joints raked back and dark with damp,
    lime bloom and green at the joints."""
    rng = np.random.default_rng(41)
    base = _base(image, size, surface.tint, grey=0.7)
    bw, bh = size / across, size / courses
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    row = np.floor(yy / bh)
    shift = (row % 2) * bw / 2
    col = np.floor(((xx + shift) % size) / bw)
    fx = ((xx + shift) % bw) / bw
    fy = (yy % bh) / bh
    joint_px = 5.0
    edge = np.minimum(np.minimum(fx, 1 - fx) * bw, np.minimum(fy, 1 - fy) * bh)
    joint = np.clip(1.0 - edge / joint_px, 0.0, 1.0)
    tone = rng.uniform(0.86, 1.10, (courses, across)).astype(np.float32)
    block_tone = tone[row.astype(int) % courses, col.astype(int) % across]
    pores = _noise(rng, size, 6) * 0.5 + _noise(rng, size, 3) * 0.5
    damp = np.clip(_noise(rng, size, 180) * 1.5 - 0.45, 0, 1)
    green = np.clip(_noise(rng, size, 90) * 1.7 - 0.9, 0, 1) * np.clip(joint * 2.0 + 0.25, 0, 1)
    colour = base * block_tone[..., None] * (0.90 + 0.2 * pores[..., None])
    colour *= (1.0 - 0.30 * damp[..., None])
    colour = colour * (1.0 - joint[..., None] * 0.55) + np.array([58.0, 55.0, 50.0]) * joint[..., None] * 0.55
    colour = colour * (1.0 - green[..., None] * 0.55) + np.array([52.0, 62.0, 40.0]) * green[..., None] * 0.55
    height = (1.0 - joint) * 0.8 + pores * 0.2
    rough = 0.86 + 0.1 * pores - 0.12 * damp
    ao = 1.0 - 0.45 * joint
    return {"diff": _image(colour), "nor": _normal(_blur(height, 1.0), 5.0), "arm": _arm(ao, rough)}


# --- Bathroom: square glazed tiles ---------------------------------------------------

def square_tiles(image, surface, size=2048, count=8):
    """Glazed wall tiles 108 mm square, eight to a repeat. Each tile a hair
    different in tone, edges pillowed, a few crazed or chipped; the grout
    grey with dirt and, by `surface.mould`, black with mould in patches."""
    rng = np.random.default_rng(int(17 + surface.mould * 100))
    cell = size // count
    glaze = _rgb(surface.tint or "#a7b0a3")
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    fx, fy = (xx % cell), (yy % cell)
    edge = np.minimum(np.minimum(fx, cell - 1 - fx), np.minimum(fy, cell - 1 - fy))
    grout_px = 4.0
    grout = np.clip(1.0 - (edge - 1.0) / grout_px, 0.0, 1.0) ** 1.5
    pillow = np.clip(edge / 16.0, 0.0, 1.0) ** 0.6                      # the glaze rounds over at the edge
    tone = rng.uniform(0.93, 1.05, (count, count)).astype(np.float32)
    warm = rng.uniform(-1.0, 1.0, (count, count)).astype(np.float32)
    ty, tx = (yy // cell).astype(int), (xx // cell).astype(int)
    colour = np.empty((size, size, 3), dtype=np.float32)
    colour[:] = glaze
    colour *= tone[ty, tx][..., None]
    colour[..., 0] += warm[ty, tx] * 3.0
    colour[..., 2] -= warm[ty, tx] * 3.0
    cloud = _noise(rng, size, 96)
    colour *= (0.982 + 0.036 * cloud[..., None])

    # crazing and chips on a few tiles
    marks = Image.new("L", (size, size), 0)
    chips = Image.new("L", (size, size), 0)
    md, cd = ImageDraw.Draw(marks), ImageDraw.Draw(chips)
    for _ in range(5):
        cx, cy = rng.integers(0, count, 2)
        x, y = cx * cell + rng.uniform(20, cell - 20), cy * cell + 6.0
        for _ in range(int(rng.integers(8, 16))):
            nx = float(np.clip(x + rng.uniform(-18, 18), cx * cell + 6, (cx + 1) * cell - 6))
            ny = float(min(y + rng.uniform(8, 26), (cy + 1) * cell - 6))
            md.line([x, y, nx, ny], fill=200, width=1)
            x, y = nx, ny
    for _ in range(7):
        cx, cy = rng.integers(0, count, 2)
        corner = (cx * cell + (cell if rng.random() < 0.5 else 0), cy * cell + (cell if rng.random() < 0.5 else 0))
        r = rng.uniform(7, 16)
        cd.ellipse([corner[0] - r, corner[1] - r, corner[0] + r, corner[1] + r], fill=255)
    craze = np.asarray(marks, dtype=np.float32) / 255.0
    chip = np.asarray(chips.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0 * (1.0 - grout)
    colour = colour * (1.0 - craze[..., None] * 0.45)
    colour = colour * (1.0 - chip[..., None]) + np.array([150.0, 128.0, 104.0]) * chip[..., None]   # the biscuit under the glaze

    # grout: grey, dirtier low in each joint, then mould in patches
    dirt = _noise(rng, size, 48)
    grout_colour = np.array([128.0, 124.0, 112.0]) * (0.62 + 0.5 * dirt[..., None])
    colour = colour * (1.0 - grout[..., None]) + grout_colour * grout[..., None]
    m = surface.mould
    patch = np.clip((_noise(rng, size, 300) * 0.6 + _noise(rng, size, 70) * 0.4 - (0.74 - 0.42 * m)) * 5.0, 0.0, 1.0)
    speck = (_noise(rng, size, 3) > 0.52).astype(np.float32)
    near = np.clip(1.0 - (edge - 1.0) / (grout_px + 10.0 * m), 0.0, 1.0)
    cover = np.clip(patch * (grout * 0.95 + near * speck * 0.55 * m), 0.0, 1.0)
    film = patch * 0.07 * m
    colour = colour * (1.0 - film[..., None])
    colour = colour * (1.0 - cover[..., None]) + np.array([30.0, 33.0, 26.0]) * cover[..., None]
    # soap and scale: a dull pale bloom
    scum = np.clip(_noise(rng, size, 220) * 1.6 - 0.75, 0, 1) * (1.0 - grout) * (0.4 + 0.6 * m)

    height = pillow * (1.0 - grout) - chip * 0.6 - craze * 0.15
    rough = 0.16 + 0.10 * cloud + 0.72 * grout + 0.5 * chip + 0.35 * scum + 0.25 * cover
    ao = 1.0 - 0.35 * grout
    colour = colour * (1.0 - scum[..., None] * 0.05) + 205.0 * scum[..., None] * 0.05
    return {"diff": _image(colour), "nor": _normal(_blur(height, 1.2), 9.0), "arm": _arm(ao, rough)}


# --- Kitchen: vinyl composition tiles -----------------------------------------------

def vinyl_tiles(image, surface, size=2048, count=8):
    """Nine-inch vinyl tiles in two colours, laid chequerwise with the streak
    of each tile turned a quarter from its neighbour. Worn pale and matt where
    people walk, dark in the seams, a few corners lifted and broken."""
    rng = np.random.default_rng(29)
    cell = size // count
    light, dark = _rgb("#8b836d"), _rgb("#716b58")
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    ty, tx = (yy // cell).astype(int), (xx // cell).astype(int)
    fx, fy = xx % cell, yy % cell
    edge = np.minimum(np.minimum(fx, cell - 1 - fx), np.minimum(fy, cell - 1 - fy))
    seam = np.clip(1.0 - edge / 2.5, 0.0, 1.0)
    check = ((tx + ty) % 2).astype(np.float32)

    # the marbling: noise drawn out along one axis, turned on alternate tiles
    def streaks(axis):
        n = rng.random((size // 4, size // 64) if axis == 0 else (size // 64, size // 4)).astype(np.float32)
        img = Image.fromarray((n * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        return np.asarray(img, dtype=np.float32) / 255.0
    sa, sb = streaks(0), streaks(1)
    turn = (((tx * 7 + ty * 3) % 2) == 0)
    marble = np.where(turn, sa, sb)
    marble = (marble - 0.5) * 2.0
    flecks = (_noise(rng, size, 2) > 0.80).astype(np.float32) * 0.5

    tone = rng.uniform(0.94, 1.06, (count, count)).astype(np.float32)[ty, tx]
    colour = light * (1.0 - check[..., None]) + dark * check[..., None]
    colour = colour * tone[..., None] * (1.0 + 0.055 * marble[..., None] + 0.09 * flecks[..., None])
    grain = np.asarray(image.convert("L").resize((size, size), Image.LANCZOS), dtype=np.float32)
    colour *= (grain / max(float(grain.mean()), 1.0))[..., None] ** 0.7

    # wear: a broad path worn dull and pale, ground-in dirt elsewhere
    path = np.clip(_noise(rng, size, 700) * 1.8 - 0.55, 0.0, 1.0)
    grime = np.clip(_noise(rng, size, 130) * 0.7 + _noise(rng, size, 30) * 0.5 - 0.55, 0.0, 1.0) * (1.0 - path * 0.7)
    colour = colour * (1.0 - path[..., None] * 0.10) + 150.0 * path[..., None] * 0.10
    colour = colour * (1.0 - grime[..., None] * 0.42)
    scratch = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(scratch)
    for _ in range(90):
        x, y = rng.uniform(0, size), rng.uniform(0, size)
        a = rng.uniform(0, np.pi)
        ln = rng.uniform(20, 160)
        sd.line([x, y, x + np.cos(a) * ln, y + np.sin(a) * ln], fill=int(rng.uniform(40, 130)), width=1)
    scratches = np.asarray(scratch, dtype=np.float32) / 255.0
    colour = colour * (1.0 + scratches[..., None] * 0.22)

    # seams, and a few broken corners with the black adhesive showing
    seam_dirt = seam * (0.55 + 0.45 * _noise(rng, size, 40))
    colour = colour * (1.0 - seam_dirt[..., None] * 0.72)
    broken = Image.new("L", (size, size), 0)
    bd = ImageDraw.Draw(broken)
    for _ in range(6):
        cx, cy = rng.integers(0, count, 2) * cell
        r = rng.uniform(14, 40)
        pts = [(cx + np.cos(t) * r * rng.uniform(0.5, 1.0), cy + np.sin(t) * r * rng.uniform(0.5, 1.0))
               for t in np.linspace(0, 2 * np.pi, 9)[:-1]]
        bd.polygon(pts, fill=255)
    gone = np.asarray(broken.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    colour = colour * (1.0 - gone[..., None]) + np.array([30.0, 27.0, 23.0]) * gone[..., None]

    height = 1.0 - seam * 0.5 - gone * 0.9 + marble * 0.02
    rough = 0.34 + 0.22 * path + 0.25 * grime + 0.4 * seam + 0.5 * gone + 0.15 * scratches
    ao = 1.0 - 0.3 * seam - 0.3 * gone
    return {"diff": _image(colour), "nor": _normal(_blur(height, 1.0), 4.0), "arm": _arm(ao, rough)}


# --- Bedroom: striped wallpaper over the plaster -----------------------------------

def stripes(image, surface, size=2048, periods=16, drops=4):
    """A 1970s striped paper gone dull: a broad stripe and a narrow one with
    pin lines between, a small sprig up the broad stripe, hung in drops whose
    seams have opened and browned. The plaster photograph underneath gives it
    its stains and unevenness."""
    rng = np.random.default_rng(53)
    base = _base(image, size, surface.tint, grey=0.85)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    period = size / periods
    f = (xx % period) / period
    broad = (f < 0.56).astype(np.float32)
    pin = (np.abs(f - 0.58) < 0.012) | (np.abs(f - 0.98) < 0.012) | (np.abs(f - 0.78) < 0.006)
    shade = 1.0 + 0.065 * broad - 0.05 * (1.0 - broad)
    colour = base * shade[..., None]
    colour = colour * (1.0 - pin[..., None] * 0.22)
    # the sprig: a small leaf pair, staggered on alternate stripes
    sprig = Image.new("L", (size, size), 0)
    sd = ImageDraw.Draw(sprig)
    step = size // 16
    for i in range(periods):
        cx = (i + 0.28) * period
        for j in range(16):
            cy = j * step + (step // 2 if i % 2 else 0)
            sd.ellipse([cx - 9, cy - 4, cx - 1, cy + 4], fill=200)
            sd.ellipse([cx + 1, cy - 14, cx + 9, cy - 6], fill=200)
            sd.line([cx, cy + 12, cx, cy - 14], fill=160, width=2)
    s = np.asarray(sprig.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0
    colour = colour * (1.0 - s[..., None] * 0.20) + _rgb("#5d6a5e") * s[..., None] * 0.20
    # fading: sun-bleached in broad patches, the pattern lost with it
    fade = np.clip(_noise(rng, size, 500) * 1.6 - 0.5, 0.0, 1.0)[..., None]
    colour = colour * (1.0 - fade * 0.5) + base * 1.03 * fade * 0.5
    # the seams between drops
    drop = size / drops
    d = np.abs(((xx + drop / 2) % drop) - drop / 2)
    seam = np.clip(1.0 - d / 2.0, 0.0, 1.0) * (0.45 + 0.55 * _noise(rng, size, 60))
    brown = np.clip(1.0 - d / 26.0, 0.0, 1.0) * np.clip(_noise(rng, size, 140) * 1.6 - 0.6, 0.0, 1.0)
    colour = colour * (1.0 - brown[..., None] * 0.22) + _rgb("#6e5f44") * brown[..., None] * 0.22
    colour = colour * (1.0 - seam[..., None] * 0.5)
    return {"diff": _image(colour)}


# --- Plain helpers --------------------------------------------------------------------

def dull(image, surface, size=None, grey=0.6):
    """The photograph pulled most of the way to grey before tinting: for
    textures whose own colours are too loud for this house."""
    size = size or image.size[0]
    return {"diff": _image(_base(image, size, surface.tint, grey=grey))}


def dull_hard(image, surface):
    return dull(image, surface, grey=0.88)


GENERATORS = {"blocks": blocks, "square_tiles": square_tiles, "vinyl_tiles": vinyl_tiles, "stripes": stripes,
              "dull": dull, "dull_hard": dull_hard}
