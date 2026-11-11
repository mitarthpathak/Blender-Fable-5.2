"""Printed things: one 2K sheet of packaging, paper and photographs.

    python3 projects/01-house-interior/labels.py

Everything on the sheet is an original design for the fictional town of
Halden Ridge in 1997: no real brand, publication or person. The props use it
through one material (`print`), so all the boxes, papers and pictures in the
house cost a game engine a single texture.

`REGIONS` maps a name to its rectangle on the sheet in pixels (x, y, w, h);
`uv(name)` gives the same rectangle as UV corners. No bpy.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHEET = HERE / "textures" / "prints" / "prints.png"
SIZE = 2048

REGIONS: dict[str, tuple[int, int, int, int]] = {
    # row 0
    "cereal_a": (0, 0, 352, 512), "cereal_b": (352, 0, 352, 512), "cereal_c": (704, 0, 352, 512),
    "calendar": (1056, 0, 400, 512), "clock": (1536, 0, 512, 512),
    "matchbook": (1456, 0, 80, 120), "cigarettes": (1456, 120, 80, 136), "sticky": (1456, 256, 80, 80),
    "stamp_note": (1456, 336, 80, 176),
    # row 1
    "newspaper": (0, 512, 400, 512), "magazine_a": (400, 512, 300, 400), "magazine_b": (700, 512, 300, 400),
    "envelope_a": (400, 912, 300, 112), "envelope_b": (700, 912, 300, 112),
    "pizza": (1000, 512, 512, 512), "takeout": (1512, 512, 256, 256), "menu": (1768, 512, 280, 400),
    "postcard": (1512, 768, 256, 160), "receipt": (1768, 912, 280, 112), "ticket": (1512, 928, 256, 96),
    # row 2
    "photo_a": (0, 1024, 384, 288), "photo_b": (384, 1024, 384, 288), "photo_c": (768, 1024, 384, 288),
    "photo_d": (1152, 1024, 384, 288), "drawing": (1536, 1024, 256, 320), "note": (1792, 1024, 256, 256),
    "soup": (0, 1312, 384, 160), "beans": (384, 1312, 384, 160), "soda": (768, 1312, 256, 160),
    "beer": (1024, 1312, 256, 160), "milk": (1280, 1312, 200, 224), "detergent": (1536, 1344, 256, 192),
    "coupon": (1792, 1280, 256, 128), "polaroid": (1792, 1408, 128, 128), "polaroid_b": (1920, 1408, 128, 128),
    # row 3
    "stove_panel": (0, 1536, 768, 128), "microwave": (0, 1664, 512, 300), "fridge_badge": (768, 1536, 256, 64),
    "shampoo": (512, 1664, 128, 256), "conditioner": (640, 1664, 128, 256), "toothpaste": (768, 1600, 320, 96),
    "soap": (768, 1696, 192, 128), "pills": (960, 1696, 128, 128), "bleach": (768, 1824, 160, 224),
    "tissues": (928, 1824, 160, 128), "letter": (1152, 1536, 360, 512), "missing": (1512, 1536, 360, 512),
    "phonebook": (1872, 1536, 176, 256), "paperback": (1872, 1792, 176, 256),
    "cardboard": (512, 1920, 256, 128), "vhs": (928, 1952, 224, 96),
    # flat colours for the sides of boxes
    "c_white": (4, 1972, 24, 24), "c_card": (36, 1972, 24, 24), "c_red": (68, 1972, 24, 24),
    "c_blue": (100, 1972, 24, 24), "c_yellow": (132, 1972, 24, 24), "c_green": (164, 1972, 24, 24),
    "c_black": (196, 1972, 24, 24), "c_cream": (228, 1972, 24, 24), "c_orange": (260, 1972, 24, 24),
    "c_brown": (292, 1972, 24, 24), "c_grey": (324, 1972, 24, 24), "c_teal": (356, 1972, 24, 24),
}

FLAT = {"c_white": (214, 210, 198), "c_card": (150, 122, 84), "c_red": (146, 44, 36), "c_blue": (44, 66, 110),
        "c_yellow": (196, 160, 60), "c_green": (58, 96, 62), "c_black": (30, 30, 30), "c_cream": (200, 188, 156),
        "c_orange": (184, 104, 44), "c_brown": (88, 60, 40), "c_grey": (120, 120, 116), "c_teal": (52, 104, 104)}


def uv(name: str, inset: float = 1.5):
    """UVs of a region's corners: bottom-left, bottom-right, top-right, top-left."""
    x, y, w, h = REGIONS[name]
    u0, u1 = (x + inset) / SIZE, (x + w - inset) / SIZE
    v0, v1 = 1.0 - (y + h - inset) / SIZE, 1.0 - (y + inset) / SIZE
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def aspect(name: str) -> float:
    """Width over height."""
    _, _, w, h = REGIONS[name]
    return w / h


# --- Drawing ----------------------------------------------------------------

def _fonts():
    from PIL import ImageFont
    base = Path("/usr/share/fonts/truetype")
    files = {"sans": "dejavu/DejaVuSans-Bold.ttf", "serif": "dejavu/DejaVuSerif-Bold.ttf",
             "plain": "dejavu/DejaVuSans.ttf", "mono": "dejavu/DejaVuSansMono.ttf",
             "narrow": "liberation/LiberationSansNarrow-Bold.ttf", "italic": "dejavu/DejaVuSerif-BoldItalic.ttf"}
    cache: dict = {}

    def font(kind, size):
        key = (kind, size)
        if key not in cache:
            path = base / files[kind]
            try:
                cache[key] = ImageFont.truetype(str(path), size)
            except OSError:                       # the font is not installed: Pillow's own
                cache[key] = ImageFont.load_default(size)
        return cache[key]
    return font


class Sheet:
    def __init__(self):
        from PIL import Image, ImageDraw
        self.image = Image.new("RGB", (SIZE, SIZE), (120, 116, 108))
        self.draw = ImageDraw.Draw(self.image)
        self.font = _fonts()
        self.rng = random.Random(1997)

    def box(self, name):
        x, y, w, h = REGIONS[name]
        return x, y, w, h

    def fill(self, name, colour):
        x, y, w, h = self.box(name)
        self.draw.rectangle([x, y, x + w - 1, y + h - 1], fill=colour)

    def rect(self, name, fx0, fy0, fx1, fy1, colour, outline=None, width=1):
        x, y, w, h = self.box(name)
        self.draw.rectangle([x + fx0 * w, y + fy0 * h, x + fx1 * w, y + fy1 * h], fill=colour, outline=outline,
                            width=width)

    def ellipse(self, name, fx, fy, frx, fry, colour, outline=None, width=1):
        x, y, w, h = self.box(name)
        self.draw.ellipse([x + (fx - frx) * w, y + (fy - fry) * h, x + (fx + frx) * w, y + (fy + fry) * h],
                          fill=colour, outline=outline, width=width)

    def text(self, name, fx, fy, body, kind="sans", size=28, colour=(20, 20, 20), anchor="mm"):
        x, y, w, h = self.box(name)
        self.draw.text((x + fx * w, y + fy * h), body, font=self.font(kind, size), fill=colour, anchor=anchor)

    def lines(self, name, fx0, fy0, fx1, fy1, count, colour=(60, 60, 60), ragged=0.25, weight=2):
        """Rows of grey bars standing in for body text."""
        x, y, w, h = self.box(name)
        for k in range(count):
            yy = y + (fy0 + (fy1 - fy0) * k / max(count - 1, 1)) * h
            end = fx1 - self.rng.random() * ragged * (fx1 - fx0)
            self.draw.line([x + fx0 * w, yy, x + end * w, yy], fill=colour, width=weight)

    def poly(self, name, points, colour):
        x, y, w, h = self.box(name)
        self.draw.polygon([(x + px * w, y + py * h) for px, py in points], fill=colour)

    def soften(self, name, radius=1.2, grain=6, fade=0.0, tint=None):
        """Print is never perfectly sharp or clean: blur a touch, add grain, age the paper."""
        from PIL import Image, ImageFilter
        x, y, w, h = self.box(name)
        tile = self.image.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(radius))
        noise = Image.effect_noise((w, h), grain).convert("RGB")
        tile = Image.blend(tile, noise, 0.06)
        if tint:
            tile = Image.blend(tile, Image.new("RGB", (w, h), tint), fade)
        self.image.paste(tile, (x, y))


def _cereal(s: Sheet, name, title, sub, ground, band, bowl):
    s.fill(name, ground)
    s.rect(name, 0, 0, 1, 0.30, band)
    s.text(name, 0.5, 0.11, title, "sans", 46, (250, 244, 224))
    s.text(name, 0.5, 0.235, sub, "narrow", 22, (250, 244, 224))
    s.ellipse(name, 0.5, 0.66, 0.36, 0.17, (236, 232, 222), outline=(120, 110, 96), width=3)       # the bowl
    s.ellipse(name, 0.5, 0.63, 0.30, 0.12, (240, 238, 226))
    for _ in range(46):                                                                             # the cereal
        fx, fy = 0.5 + s.rng.uniform(-0.24, 0.24), 0.62 + s.rng.uniform(-0.075, 0.07)
        s.ellipse(name, fx, fy, 0.03, 0.02, tuple(max(0, c + s.rng.randint(-26, 12)) for c in bowl))
    s.rect(name, 0.06, 0.88, 0.94, 0.965, band)
    s.text(name, 0.5, 0.922, "NET WT 14 OZ (397g)", "narrow", 18, (250, 244, 224))
    s.soften(name, 0.8, 5, 0.12, (150, 130, 100))


def _photo(s: Sheet, name, sky, ground, people, house=False, polaroid=False):
    """A snapshot: sky, ground, maybe a house, and figures too soft to be anyone."""
    from PIL import Image, ImageDraw, ImageFilter
    x, y, w, h = s.box(name)
    tile = Image.new("RGB", (w, h), sky)
    d = ImageDraw.Draw(tile)
    for k in range(h // 2):
        t = k / (h / 2)
        d.line([0, k, w, k], fill=tuple(int(c * (0.78 + 0.22 * t)) for c in sky))
    d.rectangle([0, h * 0.62, w, h], fill=ground)
    if house:
        d.rectangle([w * 0.52, h * 0.30, w * 0.94, h * 0.66], fill=(126, 132, 122))
        d.polygon([(w * 0.48, h * 0.30), (w * 0.73, h * 0.10), (w * 0.98, h * 0.30)], fill=(70, 66, 64))
        d.rectangle([w * 0.60, h * 0.42, w * 0.68, h * 0.66], fill=(52, 60, 66))
        d.rectangle([w * 0.76, h * 0.38, w * 0.88, h * 0.50], fill=(170, 180, 176))
    for fx, scale, colour in people:
        head = h * 0.055 * scale
        top = h * (0.74 - 0.36 * scale)
        d.ellipse([w * fx - head, top, w * fx + head, top + head * 2.2], fill=(196, 156, 128))
        d.rounded_rectangle([w * fx - head * 1.7, top + head * 2.1, w * fx + head * 1.7, h * 0.80], radius=head,
                            fill=colour)
    tile = tile.filter(ImageFilter.GaussianBlur(2.6))
    tile = Image.blend(tile, Image.new("RGB", (w, h), (196, 160, 110)), 0.22)                   # faded dye
    tile = Image.blend(tile, Image.effect_noise((w, h), 14).convert("RGB"), 0.07)
    border = 16 if polaroid else 9
    frame = Image.new("RGB", (w, h), (226, 220, 204))
    inner = tile.resize((w - 2 * border, h - (4 if polaroid else 2) * border))
    frame.paste(inner, (border, border))
    s.image.paste(frame, (x, y))


def draw() -> "Image.Image":
    s = Sheet()
    ink, cream, red, navy = (28, 28, 30), (232, 224, 200), (168, 44, 36), (36, 52, 92)

    _cereal(s, "cereal_a", "OAT RINGS", "TOASTED WHOLE GRAIN CEREAL", (196, 154, 52), (150, 52, 36), (190, 150, 84))
    _cereal(s, "cereal_b", "CORN POPS", "CRISP GOLDEN CORN PUFFS", (44, 86, 132), (196, 150, 40), (214, 172, 70))
    _cereal(s, "cereal_c", "BRAN-O", "HIGH FIBER WHEAT FLAKES", (96, 62, 40), (212, 198, 160), (150, 108, 66))

    # Calendar: a landscape above, October 1997 below, days crossed off to the 14th.
    s.fill("calendar", (226, 220, 204))
    s.rect("calendar", 0.05, 0.04, 0.95, 0.43, (120, 150, 172))
    s.poly("calendar", [(0.05, 0.43), (0.05, 0.30), (0.30, 0.16), (0.50, 0.31), (0.70, 0.12), (0.95, 0.33),
                        (0.95, 0.43)], (74, 86, 70))
    s.rect("calendar", 0.05, 0.36, 0.95, 0.43, (58, 82, 96))
    s.text("calendar", 0.5, 0.49, "OCTOBER 1997", "serif", 26, ink)
    s.text("calendar", 0.5, 0.965, "HALDEN RIDGE SAVINGS & LOAN", "narrow", 15, (90, 30, 26))
    for col, letter in enumerate("SMTWTFS"):
        s.text("calendar", 0.11 + col * 0.13, 0.545, letter, "sans", 15, red if col == 0 else ink)
    day = 1
    for row in range(5):
        for col in range(7):
            if row == 0 and col < 3:
                continue
            if day > 31:
                break
            fx, fy = 0.11 + col * 0.13, 0.61 + row * 0.075
            s.text("calendar", fx, fy, str(day), "plain", 15, ink)
            if day <= 14:
                x, y, w, h = s.box("calendar")
                s.draw.line([x + (fx - 0.035) * w, y + (fy + 0.02) * h, x + (fx + 0.035) * w, y + (fy - 0.02) * h],
                            fill=red, width=2)
            day += 1
    s.soften("calendar", 0.7, 5, 0.10, (170, 150, 110))

    # Clock face.
    s.fill("clock", (40, 38, 36))
    s.ellipse("clock", 0.5, 0.5, 0.49, 0.49, (226, 220, 200))
    for hour in range(1, 13):
        a = math.radians(hour * 30 - 90)
        s.text("clock", 0.5 + 0.38 * math.cos(a), 0.5 + 0.38 * math.sin(a), str(hour), "serif", 44, ink)
    for tick in range(60):
        a = math.radians(tick * 6)
        x, y, w, h = s.box("clock")
        r0, r1 = (0.445, 0.475) if tick % 5 else (0.43, 0.475)
        s.draw.line([x + (0.5 + r0 * math.cos(a)) * w, y + (0.5 + r0 * math.sin(a)) * h,
                     x + (0.5 + r1 * math.cos(a)) * w, y + (0.5 + r1 * math.sin(a)) * h], fill=ink, width=3)
    s.text("clock", 0.5, 0.66, "QUARTZ", "narrow", 20, (90, 90, 90))
    s.soften("clock", 0.8, 5, 0.14, (170, 150, 100))

    s.fill("matchbook", (120, 30, 28))
    s.text("matchbook", 0.5, 0.35, "RIDGE", "narrow", 20, cream)
    s.text("matchbook", 0.5, 0.60, "DINER", "narrow", 20, cream)
    s.fill("cigarettes", (220, 214, 200))
    s.rect("cigarettes", 0, 0, 1, 0.34, (150, 40, 34))
    s.text("cigarettes", 0.5, 0.56, "CREST", "serif", 18, (150, 40, 34))
    s.text("cigarettes", 0.5, 0.80, "FILTERS", "narrow", 12, ink)
    s.fill("sticky", (214, 196, 96))
    s.lines("sticky", 0.12, 0.25, 0.9, 0.75, 4, (60, 60, 90), 0.4, 2)
    s.fill("stamp_note", (224, 218, 200))
    s.lines("stamp_note", 0.1, 0.12, 0.9, 0.9, 11, (70, 70, 96), 0.5, 2)

    # Newspaper front page.
    s.fill("newspaper", (204, 198, 180))
    s.text("newspaper", 0.5, 0.055, "Halden Ridge Courier", "italic", 30, ink)
    s.rect("newspaper", 0.04, 0.095, 0.96, 0.10, ink)
    s.text("newspaper", 0.5, 0.118, "TUESDAY, OCTOBER 14, 1997            35 CENTS", "narrow", 12, ink)
    s.rect("newspaper", 0.04, 0.135, 0.96, 0.138, ink)
    s.text("newspaper", 0.5, 0.185, "MILL CLOSURE CONFIRMED", "serif", 21, ink)
    s.text("newspaper", 0.5, 0.235, "Third family leaves Alder Street this month", "plain", 14, ink)
    s.rect("newspaper", 0.05, 0.27, 0.58, 0.55, (104, 104, 100))
    s.poly("newspaper", [(0.05, 0.55), (0.05, 0.44), (0.22, 0.36), (0.34, 0.45), (0.46, 0.33), (0.58, 0.42),
                         (0.58, 0.55)], (64, 64, 62))
    for column in range(3):
        fx0 = 0.05 + column * 0.31
        top = 0.59 if column < 2 else 0.27
        s.lines("newspaper", fx0, top, fx0 + 0.27, 0.965, int((0.965 - top) / 0.0155), (70, 68, 64), 0.12, 1)
    s.soften("newspaper", 0.6, 7, 0.16, (176, 160, 120))

    for name, title, ground, accent in (("magazine_a", "TV WEEK", (150, 44, 40), (232, 208, 90)),
                                        ("magazine_b", "HEARTH & HOME", (56, 96, 92), (232, 224, 200))):
        s.fill(name, ground)
        s.text(name, 0.5, 0.10, title, "sans", 30 if len(title) < 9 else 22, accent)
        s.ellipse(name, 0.5, 0.52, 0.30, 0.26, tuple(min(255, c + 40) for c in ground))
        s.ellipse(name, 0.5, 0.44, 0.10, 0.09, (198, 160, 132))
        s.rect(name, 0.34, 0.52, 0.66, 0.78, (60, 60, 70))
        s.text(name, 0.5, 0.88, "FALL PREVIEW  ·  OCT 11-17", "narrow", 16, accent)
        s.soften(name, 0.9, 6, 0.12, (150, 130, 100))

    for name, kind in (("envelope_a", 0), ("envelope_b", 1)):
        s.fill(name, (222, 216, 200) if not kind else (204, 180, 130))
        s.lines(name, 0.38, 0.42, 0.74, 0.72, 3, (60, 60, 80), 0.3, 2)
        s.rect(name, 0.86, 0.12, 0.96, 0.42, (120, 60, 56) if not kind else (60, 80, 110))
        s.lines(name, 0.05, 0.14, 0.26, 0.30, 2, (90, 90, 90), 0.3, 1)
        if kind:
            s.text(name, 0.22, 0.80, "FINAL NOTICE", "sans", 15, (150, 30, 26))

    s.fill("pizza", (184, 150, 104))
    s.ellipse("pizza", 0.5, 0.5, 0.36, 0.36, None, outline=(150, 44, 36), width=10)
    s.text("pizza", 0.5, 0.42, "SAL'S", "serif", 62, (150, 44, 36))
    s.text("pizza", 0.5, 0.55, "PIZZA & SUBS", "sans", 30, (40, 80, 50))
    s.text("pizza", 0.5, 0.64, "MAIN ST · HALDEN RIDGE", "narrow", 18, ink)
    s.text("pizza", 0.5, 0.92, "HOT  &  FRESH", "sans", 26, (150, 44, 36))
    s.soften("pizza", 1.0, 8, 0.10, (120, 96, 60))

    s.fill("takeout", (224, 218, 204))
    s.rect("takeout", 0.08, 0.10, 0.92, 0.90, None, outline=(160, 40, 34), width=5)
    s.text("takeout", 0.5, 0.36, "LUCKY", "serif", 44, (160, 40, 34))
    s.text("takeout", 0.5, 0.58, "GARDEN", "serif", 38, (160, 40, 34))
    s.text("takeout", 0.5, 0.78, "THANK YOU", "narrow", 20, (160, 40, 34))
    s.soften("takeout", 0.8, 5, 0.08, (160, 140, 100))

    s.fill("menu", (214, 196, 120))
    s.text("menu", 0.5, 0.07, "LUCKY GARDEN", "serif", 24, (150, 36, 30))
    s.text("menu", 0.5, 0.13, "TAKE-OUT MENU", "narrow", 16, ink)
    s.lines("menu", 0.08, 0.20, 0.92, 0.94, 26, (70, 50, 30), 0.35, 2)
    s.fill("postcard", (120, 150, 170))
    s.poly("postcard", [(0, 1), (0, 0.6), (0.3, 0.35), (0.55, 0.62), (0.8, 0.30), (1, 0.55), (1, 1)], (70, 90, 70))
    s.text("postcard", 0.5, 0.86, "Greetings from Lake Arden", "italic", 15, cream)
    s.soften("postcard", 1.0, 6, 0.15, (180, 150, 110))
    s.fill("receipt", (226, 222, 210))
    s.lines("receipt", 0.06, 0.15, 0.94, 0.85, 6, (90, 90, 90), 0.5, 1)
    s.fill("ticket", (196, 120, 60))
    s.text("ticket", 0.5, 0.5, "ADMIT ONE", "sans", 26, ink)

    _photo(s, "photo_a", (150, 176, 196), (96, 112, 78), [(0.28, 1.0, (60, 70, 110)), (0.44, 0.92, (150, 60, 56))],
           house=True)
    _photo(s, "photo_b", (182, 176, 150), (120, 104, 76), [(0.34, 1.0, (70, 70, 70)), (0.52, 0.62, (190, 170, 80)),
                                                           (0.68, 0.96, (120, 80, 110))])
    _photo(s, "photo_c", (120, 140, 150), (70, 84, 66), [(0.5, 0.7, (170, 60, 50))], house=True)
    _photo(s, "photo_d", (196, 170, 130), (110, 90, 70), [(0.3, 1.0, (40, 60, 80)), (0.6, 1.0, (200, 196, 180))])
    _photo(s, "polaroid", (150, 170, 180), (90, 100, 80), [(0.5, 1.0, (140, 50, 50))], polaroid=True)
    _photo(s, "polaroid_b", (176, 160, 130), (100, 86, 66), [(0.4, 0.7, (60, 80, 110)), (0.62, 1.0, (90, 90, 90))],
           polaroid=True)

    # A child's drawing for the fridge.
    s.fill("drawing", (226, 222, 208))
    s.rect("drawing", 0.25, 0.42, 0.72, 0.80, None, outline=(150, 60, 50), width=5)
    s.poly("drawing", [(0.20, 0.42), (0.485, 0.20), (0.77, 0.42), (0.74, 0.44), (0.485, 0.25), (0.23, 0.44)],
           (60, 70, 130))
    s.ellipse("drawing", 0.84, 0.14, 0.09, 0.07, (212, 176, 60))
    s.rect("drawing", 0.0, 0.80, 1.0, 0.86, (70, 120, 66))
    for fx in (0.10, 0.90):
        s.ellipse("drawing", fx, 0.66, 0.035, 0.028, None, outline=ink, width=3)
        s.rect("drawing", fx - 0.004, 0.69, fx + 0.004, 0.80, ink)
    s.text("drawing", 0.5, 0.93, "my hous", "plain", 22, (60, 70, 130))
    s.fill("note", (224, 216, 190))
    s.text("note", 0.5, 0.16, "MILK  EGGS", "mono", 22, (40, 50, 110))
    s.text("note", 0.5, 0.32, "CALL DR. WEISS", "mono", 20, (40, 50, 110))
    s.lines("note", 0.1, 0.48, 0.9, 0.86, 4, (40, 50, 110), 0.5, 2)

    for name, title, ground, band in (("soup", "TOMATO SOUP", (164, 44, 36), (226, 220, 200)),
                                      ("beans", "BAKED BEANS", (40, 74, 110), (214, 160, 60)),
                                      ("soda", "RIDGE COLA", (150, 36, 32), (226, 220, 200)),
                                      ("beer", "OLD MILL LAGER", (196, 168, 96), (60, 44, 30))):
        s.fill(name, ground)
        s.rect(name, 0, 0.30, 1, 0.70, band)
        s.text(name, 0.5, 0.5, title, "serif", 26 if len(title) < 12 else 20, ground)
        s.soften(name, 0.8, 5, 0.08, (140, 120, 90))
    s.fill("milk", (224, 222, 212))
    s.rect("milk", 0, 0, 1, 0.26, (44, 80, 130))
    s.text("milk", 0.5, 0.42, "MILK", "sans", 44, (44, 80, 130))
    s.text("milk", 0.5, 0.60, "VITAMIN D", "narrow", 18, ink)
    s.rect("milk", 0.2, 0.70, 0.8, 0.94, (150, 150, 146))
    s.text("milk", 0.5, 0.82, "HAVE YOU", "narrow", 13, ink)
    s.fill("detergent", (196, 110, 40))
    s.ellipse("detergent", 0.5, 0.5, 0.42, 0.36, (226, 220, 200))
    s.text("detergent", 0.5, 0.5, "SURGE", "sans", 44, (40, 70, 130))
    s.fill("coupon", (220, 212, 190))
    s.rect("coupon", 0.03, 0.06, 0.97, 0.94, None, outline=ink, width=2)
    s.text("coupon", 0.5, 0.36, "SAVE 40¢", "sans", 32, (150, 36, 30))
    s.lines("coupon", 0.1, 0.62, 0.9, 0.84, 3, (80, 80, 80), 0.3, 1)

    # Appliance fronts.
    s.fill("stove_panel", (190, 186, 172))
    for knob in range(4):
        fx = 0.10 + knob * 0.105 + (0.42 if knob > 1 else 0.0)
        s.ellipse("stove_panel", fx, 0.5, 0.036, 0.22, (60, 58, 54))
        s.text("stove_panel", fx, 0.86, ("LF", "LR", "RR", "RF")[knob], "narrow", 13, ink)
    s.rect("stove_panel", 0.36, 0.22, 0.60, 0.78, (26, 30, 26))
    s.text("stove_panel", 0.48, 0.5, "12:00", "mono", 34, (70, 150, 90))
    s.fill("microwave", (44, 42, 40))
    s.rect("microwave", 0.04, 0.10, 0.70, 0.90, (22, 24, 26), outline=(90, 88, 84), width=4)
    s.rect("microwave", 0.75, 0.10, 0.96, 0.90, (70, 68, 64))
    s.rect("microwave", 0.77, 0.14, 0.94, 0.26, (26, 34, 28))
    for row in range(4):
        for col in range(3):
            s.rect("microwave", 0.775 + col * 0.058, 0.34 + row * 0.13, 0.82 + col * 0.058, 0.43 + row * 0.13,
                   (110, 108, 100))
    s.fill("fridge_badge", (150, 150, 146))
    s.text("fridge_badge", 0.5, 0.5, "NORVALE", "serif", 30, (40, 40, 44))

    for name, title, ground, accent in (("shampoo", "SILK", (70, 120, 110), cream),
                                        ("conditioner", "SILK", (196, 170, 120), (70, 120, 110)),
                                        ("bleach", "BRITE", (226, 222, 206), navy)):
        s.fill(name, ground)
        s.ellipse(name, 0.5, 0.45, 0.38, 0.20, accent)
        s.text(name, 0.5, 0.45, title, "sans", 30, ground)
        s.lines(name, 0.15, 0.72, 0.85, 0.90, 4, accent, 0.3, 2)
    s.fill("toothpaste", (226, 224, 216))
    s.rect("toothpaste", 0, 0, 0.30, 1, (40, 110, 130))
    s.text("toothpaste", 0.62, 0.5, "DENTA-FRESH", "sans", 24, (40, 110, 130))
    s.fill("soap", (196, 208, 196))
    s.text("soap", 0.5, 0.5, "SPRING", "serif", 28, (50, 90, 70))
    s.fill("pills", (220, 216, 204))
    s.rect("pills", 0, 0, 1, 0.22, (70, 110, 150))
    s.lines("pills", 0.08, 0.36, 0.92, 0.88, 6, ink, 0.4, 2)
    s.fill("tissues", (150, 170, 190))
    s.ellipse("tissues", 0.5, 0.5, 0.30, 0.22, (226, 224, 216))

    # A typed letter, and a poster off a telephone pole.
    s.fill("letter", (224, 220, 206))
    s.text("letter", 0.5, 0.07, "HALDEN RIDGE POWER & LIGHT", "serif", 17, ink)
    s.rect("letter", 0.08, 0.10, 0.92, 0.104, ink)
    s.text("letter", 0.5, 0.18, "NOTICE OF DISCONNECTION", "sans", 20, (150, 30, 26))
    s.lines("letter", 0.10, 0.26, 0.90, 0.80, 24, (70, 70, 74), 0.2, 2)
    s.lines("letter", 0.10, 0.88, 0.45, 0.92, 2, (40, 50, 110), 0.3, 3)
    s.fill("missing", (220, 214, 196))
    s.text("missing", 0.5, 0.09, "MISSING", "sans", 58, ink)
    s.rect("missing", 0.22, 0.17, 0.78, 0.60, (150, 148, 140))
    s.ellipse("missing", 0.5, 0.33, 0.13, 0.11, (110, 108, 102))
    s.rect("missing", 0.33, 0.44, 0.67, 0.60, (96, 94, 90))
    s.text("missing", 0.5, 0.67, "LAST SEEN OCT. 9", "sans", 22, ink)
    s.text("missing", 0.5, 0.73, "ALDER STREET", "sans", 22, ink)
    s.lines("missing", 0.12, 0.80, 0.88, 0.90, 4, (60, 60, 60), 0.2, 2)
    s.text("missing", 0.5, 0.95, "CALL 555-0142", "sans", 24, (150, 30, 26))
    for name in ("letter", "missing"):
        s.soften(name, 0.7, 7, 0.10, (170, 150, 110))

    s.fill("phonebook", (196, 168, 60))
    s.text("phonebook", 0.5, 0.20, "AREA", "sans", 26, ink)
    s.text("phonebook", 0.5, 0.36, "PHONE", "sans", 26, ink)
    s.text("phonebook", 0.5, 0.52, "BOOK", "sans", 26, ink)
    s.text("phonebook", 0.5, 0.82, "1997-98", "narrow", 20, ink)
    s.fill("paperback", (40, 44, 60))
    s.ellipse("paperback", 0.5, 0.56, 0.30, 0.22, (150, 44, 40))
    s.text("paperback", 0.5, 0.16, "THE LONG", "serif", 20, cream)
    s.text("paperback", 0.5, 0.26, "WINTER", "serif", 20, cream)
    s.text("paperback", 0.5, 0.90, "A NOVEL", "narrow", 14, cream)

    # The side of a packing box: board, a strip of tape, a stencil.
    from PIL import Image
    x, y, w, h = REGIONS["cardboard"]
    board = Image.blend(Image.new("RGB", (w, h), (150, 122, 84)), Image.effect_noise((w, h), 26).convert("RGB"), 0.10)
    s.image.paste(board, (x, y))
    for row in range(0, h, 5):
        s.draw.line([x, y + row, x + w, y + row], fill=(140, 113, 77), width=1)
    s.rect("cardboard", 0.0, 0.40, 1.0, 0.60, (176, 150, 104))
    s.text("cardboard", 0.30, 0.20, "FRAGILE", "sans", 22, (40, 34, 28))
    s.text("cardboard", 0.78, 0.82, "KITCHEN", "mono", 15, (30, 30, 60))
    s.poly("cardboard", [(0.80, 0.30), (0.86, 0.12), (0.92, 0.30), (0.88, 0.30), (0.88, 0.36), (0.84, 0.36),
                         (0.84, 0.30)], (40, 34, 28))
    # Video tapes seen edge on: black shells with hand-written labels.
    s.fill("vhs", (24, 24, 26))
    for row, title in enumerate(("XMAS 94", "TAPE 3", "GAME 7")):
        s.rect("vhs", 0.10, 0.06 + row * 0.33, 0.90, 0.26 + row * 0.33, (214, 208, 190))
        s.text("vhs", 0.5, 0.16 + row * 0.33, title, "mono", 15, (40, 50, 110))

    for name, colour in FLAT.items():
        x, y, w, h = REGIONS[name]
        s.draw.rectangle([x - 4, y - 4, x + w + 3, y + h + 3], fill=colour)
    return s.image


def main():
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    draw().save(SHEET, optimize=True)
    print(f"  ~ {SHEET.relative_to(HERE)}")


if __name__ == "__main__":
    main()
