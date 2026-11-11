"""Second half of derive.py: the decals of the detail pass, small tiling
texture sets for the surfaces that used to be flat colours (glass, chrome,
wire, plastic), and a normal map and an ORM map (occlusion, roughness,
metalness in R, G, B) for every generated decal.

Run through derive.py:

    python projects/03-town/derive.py

Output:
    textures/decals/<name>.png        albedo + alpha
    textures/decals/<name>_nor.png    normal map (OpenGL convention)
    textures/decals/<name>_orm.png    occlusion / roughness / metalness
    textures/flat/<name>_{diff,nor,orm}.png
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
DECALS = HERE / "textures" / "decals"
FLAT = HERE / "textures" / "flat"
RNG = np.random.default_rng(41)


# --- helpers ------------------------------------------------------------------

def noise(size: int, scale: int, octaves: int = 4, rng=RNG) -> np.ndarray:
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = max(2, scale * 2 ** o)
        grid = rng.random((n, n)).astype(np.float32)
        layer = np.asarray(Image.fromarray((grid * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC),
                           np.float32) / 255.0
        out += amp * layer
        total += amp
        amp *= 0.5
    out /= total
    return (out - out.min()) / max(out.max() - out.min(), 1e-6)


def blur(a: np.ndarray, radius: float) -> np.ndarray:
    img = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255.0


def normal_from_height(h: np.ndarray, strength: float) -> np.ndarray:
    """Tangent-space normal map (OpenGL: green up) from a height field in 0..1."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5      # image rows run down
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / length, ny / length, nz / length]) * 0.5 + 0.5


def save(arr: np.ndarray, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "RGBA" if arr.shape[2] == 4 else "RGB"
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), mode).save(path)


def orm(rough: np.ndarray, metal: float | np.ndarray = 0.0, ao: float | np.ndarray = 1.0) -> np.ndarray:
    r = np.clip(rough, 0.02, 1.0)
    return np.dstack([np.broadcast_to(ao, r.shape), r, np.broadcast_to(metal, r.shape)]).astype(np.float32)


def font(size, bold=True):
    names = ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf") if bold else ("arial.ttf", "DejaVuSans.ttf")
    for name in names + ("arial.ttf",):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def centred(d, y, text, f, fill, width):
    d.text(((width - d.textlength(text, font=f)) / 2, y), text, fill=fill, font=f)


# --- new decals ------------------------------------------------------------------

def weed_tuft():
    """A weed coming out of a crack: a rosette of broad leaves and a few seed stems."""
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(5)
    for _ in range(16):
        a = rng.uniform(np.pi * 0.08, np.pi * 0.92)
        length = rng.uniform(0.25, 0.6) * s
        w = rng.uniform(8, 16)
        x0, y0 = s / 2 + rng.uniform(-10, 10), s - 4
        x1, y1 = x0 + np.cos(a) * length, y0 - np.sin(a) * length
        nx, ny = -np.sin(a) * w, -np.cos(a) * w
        tone = rng.uniform(0, 1)
        col = (int(48 + 40 * tone), int(66 + 36 * tone), int(30 + 14 * tone), 255)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        d.polygon([(x0, y0), (mx + nx, my + ny), (x1, y1), (mx - nx, my - ny)], fill=col)
        d.line([(x0, y0), (x1, y1)], fill=(int(col[0] * 0.7), int(col[1] * 0.7), int(col[2] * 0.7), 255), width=1)
    for _ in range(5):
        x0 = s / 2 + rng.uniform(-14, 14)
        h = rng.uniform(0.6, 0.97) * s
        lean = rng.uniform(-0.2, 0.2) * h
        pts = [(x0 + lean * (t / 6) ** 1.4, s - h * t / 6) for t in range(7)]
        d.line(pts, fill=(96, 92, 54, 255), width=2)
        d.ellipse([pts[-1][0] - 4, pts[-1][1] - 7, pts[-1][0] + 4, pts[-1][1] + 5], fill=(120, 108, 66, 255))
    save(np.asarray(img.filter(ImageFilter.SMOOTH), np.float32) / 255.0, DECALS / "weed_tuft.png")


def tyre_marks():
    """Two curved rubber streaks, fading in and out."""
    w, h = 256, 1024
    a = np.zeros((h, w), np.float32)
    yy = np.arange(h)[:, None] / h
    xx = np.arange(w)[None, :] / w
    for centre in (0.30, 0.70):
        curve = centre + 0.10 * np.sin(yy * np.pi * 0.9) - 0.05 * yy
        band = np.exp(-((xx - curve) / 0.045) ** 2)
        a += band
    grain = noise(1024, 60, 3)[:, :w]
    fade = np.clip(np.sin(yy * np.pi) * 1.6, 0, 1)
    alpha = np.clip(a * fade * (0.45 + 0.75 * grain) * 0.8, 0, 0.85)
    col = np.ones((h, w, 3), np.float32) * np.array([0.03, 0.03, 0.032])
    save(np.dstack([col, alpha]), DECALS / "tyre_marks.png")


def poster(name, bg, ink, lines, tear=True, photo=False, size=(384, 512)):
    """A flyer taped to a pole. All names, numbers and businesses are made up."""
    w, h = size
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    y = 26
    for text, px, bold in lines:
        if text == "<photo>":
            d.rectangle([w * 0.2, y, w * 0.8, y + 170], fill=(96, 94, 88))
            d.ellipse([w * 0.37, y + 34, w * 0.63, y + 122], fill=(60, 58, 54))          # a grey blur of a cat
            d.polygon([(w * 0.39, y + 50), (w * 0.42, y + 22), (w * 0.47, y + 44)], fill=(60, 58, 54))
            d.polygon([(w * 0.61, y + 50), (w * 0.58, y + 22), (w * 0.53, y + 44)], fill=(60, 58, 54))
            y += 186
            continue
        f = font(px, bold)
        centred(d, y, text, f, ink, w)
        y += int(px * 1.25)
    a = np.asarray(img, np.float32) / 255.0
    damp = noise(512, 5)[:h, :w]
    a *= (0.62 + 0.38 * damp)[..., None]                    # rain-stained
    a[..., 2] *= 0.92
    alpha = np.ones((h, w), np.float32)
    if tear:
        edge = noise(512, 9, 3, np.random.default_rng(len(name)))[:h, :w]
        yy, xx = np.mgrid[0:h, 0:w]
        alpha[(yy > h * 0.82 + edge * h * 0.22)] = 0.0       # torn bottom
        alpha[(xx + yy * 0.5 < 34 * edge * 2)] = 0.0         # a missing corner
    save(np.dstack([a, alpha]), DECALS / f"{name}.png")


def metal_sign(name, bg, ink, lines, size=(256, 384), border=True):
    w, h = size
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    if border:
        d.rounded_rectangle([8, 8, w - 9, h - 9], radius=14, outline=ink, width=6)
    y = 34
    for text, px in lines:
        f = font(px)
        centred(d, y, text, f, ink, w)
        y += int(px * 1.2)
    a = np.asarray(img, np.float32) / 255.0
    fade = noise(512, 4)[:h, :w]
    rust = noise(512, 14, 3)[:h, :w]
    a = a * (0.55 + 0.35 * fade)[..., None] + 0.12                # sun-faded
    rmask = np.clip((rust - 0.62) * 6, 0, 1)[..., None]
    a = a * (1 - rmask) + np.array([0.26, 0.13, 0.07]) * rmask     # rust blooming through
    save(np.dstack([a, np.ones((h, w), np.float32)]), DECALS / f"{name}.png")


def litter():
    """Scraps of paper, a flattened cup, wrappers: scattered on transparent ground."""
    s = 512
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(77)
    for _ in range(34):
        x, y = rng.uniform(40, s - 40, 2)
        w, h = rng.uniform(14, 46), rng.uniform(10, 34)
        a = rng.uniform(0, np.pi)
        tone = rng.uniform(0.45, 0.8)
        tint = rng.choice([(1.0, 0.98, 0.92), (0.95, 0.9, 0.8), (0.8, 0.82, 0.86), (0.85, 0.7, 0.55)])
        col = tuple(int(255 * tone * c) for c in tint) + (255,)
        ca, sa = np.cos(a), np.sin(a)
        pts = [(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in
               ((-w / 2, -h / 2), (w / 2, -h / 2 + rng.uniform(-4, 4)), (w / 2, h / 2), (-w / 2 + rng.uniform(-4, 4), h / 2))]
        d.polygon(pts, fill=col)
    save(np.asarray(img.filter(ImageFilter.SMOOTH), np.float32) / 255.0, DECALS / "litter.png")


def glass_shards():
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(13)
    for _ in range(70):
        r = rng.uniform(0, 1) ** 1.6 * s * 0.45
        a = rng.uniform(0, 2 * np.pi)
        x, y = s / 2 + np.cos(a) * r, s / 2 + np.sin(a) * r
        size = rng.uniform(3, 11)
        pts = [(x + np.cos(a2) * size * rng.uniform(0.4, 1), y + np.sin(a2) * size * rng.uniform(0.4, 1))
               for a2 in np.sort(rng.uniform(0, 2 * np.pi, 3))]
        v = int(rng.uniform(120, 200))
        d.polygon(pts, fill=(v, int(v * 1.02), int(v * 1.05), 235))
    save(np.asarray(img, np.float32) / 255.0, DECALS / "glass_shards.png")


def moss_strip():
    """Moss and dirt packed into a joint: a soft-edged band, 1 m long."""
    w, h = 64, 512
    n1 = noise(512, 8)[:, :w]
    n2 = noise(512, 40, 2)[:, :w]
    xx = np.abs(np.arange(w)[None, :] / (w - 1) * 2 - 1)
    alpha = np.clip((0.75 - xx - 0.5 * (1 - n1)) * 4, 0, 1) * (0.55 + 0.45 * n2)
    green = n2[..., None]
    col = np.array([0.10, 0.13, 0.06]) * (1 - green) + np.array([0.20, 0.24, 0.10]) * green
    col = col * (0.7 + 0.5 * n1[..., None])
    save(np.dstack([col.astype(np.float32), alpha.astype(np.float32)]), DECALS / "moss_strip.png")


def backdrop():
    """A dark tree line and rooftops for the street ends: a silhouette, lost in fog."""
    w, h = 1024, 256
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(99)
    d.rectangle([0, h * 0.72, w, h], fill=255)
    x = -20
    while x < w + 20:                                           # bare crowns
        r = rng.uniform(26, 70)
        top = h * 0.72 - rng.uniform(40, 150)
        d.line([(x, h * 0.75), (x + rng.uniform(-6, 6), top + r * 0.6)], fill=255, width=int(rng.uniform(4, 9)))
        for _ in range(22):
            a = rng.uniform(np.pi * 1.05, np.pi * 1.95)
            length = r * rng.uniform(0.5, 1.2)
            bx, by = x, top + r * 0.7
            d.line([(bx, by), (bx + np.cos(a) * length, by + np.sin(a) * length * 0.9)], fill=255,
                   width=int(rng.uniform(1, 3)))
        x += rng.uniform(34, 90)
    for _ in range(5):                                          # a few roofs
        rx = rng.uniform(40, w - 160)
        rw, rh = rng.uniform(80, 130), rng.uniform(50, 80)
        base = h * 0.74
        d.rectangle([rx, base - rh, rx + rw, base], fill=255)
        d.polygon([(rx - 8, base - rh), (rx + rw / 2, base - rh - rw * 0.32), (rx + rw + 8, base - rh)], fill=255)
    alpha = np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255.0
    col = np.ones((h, w, 3), np.float32) * np.array([0.035, 0.04, 0.045])
    save(np.dstack([col, alpha]), DECALS / "backdrop_trees.png")


def halo():
    """Soft round glow for the cheap fog halo round street lights (Low quality)."""
    s = 128
    y, x = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - r, 0, 1) ** 2.2
    col = np.ones((s, s, 3), np.float32)
    save(np.dstack([col, a.astype(np.float32)]), DECALS / "halo.png")


def new_decals():
    weed_tuft()
    tyre_marks()
    moss_strip()
    litter()
    glass_shards()
    backdrop()
    halo()
    paper, ink = (214, 208, 190), (34, 32, 30)
    poster("poster_missing", paper, ink, [
        ("MISSING", 64, True), ("<photo>", 0, False), ("TOBY", 44, True), ("grey tabby, white paws", 22, False),
        ("last seen on Mill Road", 22, False), ("call 555-0148", 30, True)])
    poster("poster_meeting", (206, 200, 170), ink, [
        ("TOWN MEETING", 40, True), ("", 12, False), ("What happens to", 26, False), ("the HALDEN MILL?", 30, True),
        ("", 12, False), ("Grange Hall", 28, False), ("Thursday 7 pm", 28, False), ("", 12, False),
        ("All residents welcome", 22, False)])
    poster("poster_yardsale", (222, 198, 120), ink, [
        ("YARD SALE", 52, True), ("", 10, False), ("everything must go", 26, False), ("", 10, False),
        ("12 Ashgrove St", 34, True), ("Sat + Sun", 30, False), ("", 10, False), ("tools - furniture", 22, False),
        ("records - toys", 22, False)])
    metal_sign("sign_parking", (198, 196, 186), (120, 28, 24), [("NO", 64), ("PARKING", 44), ("", 14), ("THIS SIDE", 34),
                                                               ("OF STREET", 34), ("", 10), ("NOV 1 - APR 1", 26)])
    metal_sign("sign_bus", (32, 62, 88), (214, 210, 196), [("BUS", 70), ("STOP", 62), ("", 14), ("RIDGE", 40),
                                                          ("LINE 4", 46), ("", 10), ("Mill - Depot", 24)])
    metal_sign("sign_beware", (204, 178, 60), (26, 24, 22), [("BEWARE", 50), ("OF", 40), ("DOG", 70)], size=(256, 256))


# --- flat sets ------------------------------------------------------------------------

def flat_set(name, colour, rough, rough_var, bump, metal=0.0, streaks=0.0, pits=0.0, twist=False, size=256,
             colour_var=0.08):
    """A small tiling albedo / normal / ORM set for a surface that has no photo texture."""
    rng = np.random.default_rng(abs(hash(name)) % (2 ** 32) if False else sum(map(ord, name)))
    n1 = noise(size, 4, 4, rng)
    n2 = noise(size, 24, 3, rng)
    height = 0.5 * n1 + 0.5 * n2
    r = rough + rough_var * (n1 - 0.5) * 2
    albedo = np.ones((size, size, 3), np.float32) * np.array(colour, np.float32)
    albedo *= (1 - colour_var + 2 * colour_var * n2)[..., None]
    if streaks > 0:                                   # rain streaks and wipe marks down the surface
        col_noise = noise(size, 32, 2, rng)[:1, :].repeat(size, axis=0)
        s = blur(col_noise * n1, 1.2)
        r = r + streaks * (s - s.mean()) * 3
        albedo *= (1 - 0.35 * streaks * (s - s.min()) / max(np.ptp(s), 1e-6))[..., None]
    if pits > 0:
        specks = (rng.random((size, size)) > 1 - 0.012 * pits).astype(np.float32)
        specks = blur(specks, 0.9) * 3
        height = height - specks
        r = r + specks * 0.3
        albedo *= (1 - 0.5 * np.clip(specks, 0, 1))[..., None]
    if twist:                                         # stranded cable: diagonal ridges
        yy, xx = np.mgrid[0:size, 0:size]
        height = 0.5 + 0.5 * np.sin((xx + yy) / size * 2 * np.pi * 16)
    save(albedo, FLAT / f"{name}_diff.png")
    save(normal_from_height(height.astype(np.float32), bump), FLAT / f"{name}_nor.png")
    save(orm(r.astype(np.float32), metal), FLAT / f"{name}_orm.png")
    print("flat", name)


def flat_sets():
    flat_set("glass", (0.060, 0.070, 0.075), 0.07, 0.03, 0.6, streaks=0.25)
    flat_set("glass_dirty", (0.105, 0.105, 0.098), 0.34, 0.12, 0.5, streaks=0.5, pits=0.4, colour_var=0.07)
    flat_set("chrome", (0.50, 0.50, 0.49), 0.42, 0.10, 2.5, metal=1.0, pits=1.6)
    flat_set("wire", (0.035, 0.035, 0.035), 0.58, 0.06, 6.0, twist=True, size=128)
    flat_set("plastic_dark", (0.055, 0.055, 0.057), 0.55, 0.08, 3.0, pits=0.5)
    flat_set("lamp_red", (0.28, 0.035, 0.025), 0.28, 0.08, 2.0, streaks=0.4)
    flat_set("lamp_clear", (0.52, 0.50, 0.44), 0.16, 0.06, 2.0, streaks=0.4)
    flat_set("bag_plastic", (0.045, 0.045, 0.05), 0.32, 0.12, 5.0, colour_var=0.2)
    flat_set("pumpkin", (0.52, 0.22, 0.05), 0.55, 0.10, 4.0, pits=0.8, colour_var=0.25)
    flat_set("toy_plastic", (0.80, 0.80, 0.78), 0.40, 0.10, 2.0, pits=0.6, colour_var=0.12)


# --- normal and ORM maps for every decal --------------------------------------------------

# name: (height source, normal strength, roughness, metalness, roughness follows height by)
DECAL_RULES = {
    "marking_yellow": ("alpha", 2.0, 0.62, 0.0, 0.0),
    "marking_white": ("alpha", 2.0, 0.62, 0.0, 0.0),
    "chainlink": ("alpha_soft", 6.0, 0.45, 0.85, 0.0),
    "grass_tuft": ("luma", 3.0, 0.85, 0.0, 0.0),
    "weed_tuft": ("luma", 3.0, 0.8, 0.0, 0.0),
    "puddle": ("flat", 0.0, 0.04, 0.0, 0.0),
    "leaf_litter": ("alpha_soft", 5.0, 0.5, 0.0, 0.0),
    "oil_stain": ("flat", 0.0, 0.16, 0.0, 0.0),
    "crack": ("-alpha", 8.0, 0.92, 0.0, 0.0),
    "grime_streaks": ("flat", 0.0, 0.88, 0.0, 0.0),
    "moss": ("luma", 5.0, 0.95, 0.0, 0.0),
    "moss_strip": ("alpha_soft", 5.0, 0.95, 0.0, 0.0),
    "tyre_marks": ("flat", 0.0, 0.92, 0.0, 0.0),
    "litter": ("alpha_soft", 3.0, 0.7, 0.0, 0.0),
    "glass_shards": ("alpha", 6.0, 0.08, 0.0, 0.0),
    "sign_road_closed": ("luma", 1.5, 0.55, 0.0, 0.0),
    "sign_for_sale": ("luma", 1.5, 0.55, 0.0, 0.0),
    "sign_parking": ("luma", 1.5, 0.5, 0.6, 0.0),
    "sign_bus": ("luma", 1.5, 0.5, 0.6, 0.0),
    "sign_beware": ("luma", 1.5, 0.5, 0.6, 0.0),
    "poster_missing": ("paper", 2.5, 0.8, 0.0, 0.0),
    "poster_meeting": ("paper", 2.5, 0.8, 0.0, 0.0),
    "poster_yardsale": ("paper", 2.5, 0.8, 0.0, 0.0),
    "backdrop_trees": ("flat", 0.0, 1.0, 0.0, 0.0),
}


def decal_maps():
    for name, (source, strength, rough, metal, _) in DECAL_RULES.items():
        path = DECALS / f"{name}.png"
        if not path.exists():
            print("missing decal", name)
            continue
        a = np.asarray(Image.open(path).convert("RGBA"), np.float32) / 255.0
        luma = a[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        alpha = a[..., 3]
        h, w = alpha.shape
        grain = noise(max(h, w), 48, 2)[:h, :w]
        if source == "alpha":
            height = alpha
        elif source == "alpha_soft":
            height = blur(alpha, 2.0)
        elif source == "-alpha":
            height = 1.0 - blur(alpha, 1.0)
        elif source == "luma":
            height = blur(luma, 1.0) * alpha
        elif source == "paper":
            height = 0.5 * noise(max(h, w), 6)[:h, :w] + 0.2 * grain          # buckled by rain
        else:
            height = np.full_like(alpha, 0.5)
        r = np.full_like(alpha, rough)
        if name == "puddle":
            r = 0.04 + 0.5 * np.clip(1 - alpha / max(alpha.max(), 1e-6), 0, 1) ** 2     # still water, damp rim
        elif name == "chainlink":
            rust = noise(max(h, w), 5)[:h, :w]
            r = 0.4 + 0.35 * rust
            metal = (0.9 - 0.6 * np.clip((rust - 0.55) * 4, 0, 1)).astype(np.float32)
        else:
            r = r + 0.08 * (grain - 0.5)
        save(normal_from_height(height.astype(np.float32), strength), DECALS / f"{name}_nor.png")
        save(orm(r.astype(np.float32), metal), DECALS / f"{name}_orm.png")
    print("decal maps", len(DECAL_RULES))


def run():
    new_decals()
    flat_sets()
    decal_maps()


if __name__ == "__main__":
    run()
