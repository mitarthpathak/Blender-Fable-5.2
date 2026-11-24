"""Paint the ghost sign on the mill's spinning block: the name the mill once
showed the valley, in cream on a dark ground, faded, flaked and run.

    python projects/03-town/mill_sign.py

Writes textures/decals/mill_ghost_sign.png (1024 x 256, with alpha: where
the paint has gone, the brick shows through). Names are our own.
"""
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent / "textures" / "decals" / "mill_ghost_sign.png"
FONTS = ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def _font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def paint():
    rng = random.Random(1887)
    w, h = 1024, 256
    # the dark ground the letters were painted on, and the letters on it
    ground = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(ground)
    gd.rectangle((6, 6, w - 7, h - 7), fill=255)
    letters = Image.new("L", (w, h), 0)
    ld = ImageDraw.Draw(letters)
    for text, size, y in (("HALDEN  MILLS", 128, 22), ("WOOLENS  ·  WORSTEDS  ·  EST. 1887", 44, 180)):
        f = _font(size)
        while ld.textlength(text, font=f) > w - 110:          # fit inside the border with a margin
            size -= 4
            f = _font(size)
        tw = ld.textlength(text, font=f)
        ld.text(((w - tw) / 2, y), text, font=f, fill=255)
    ld.line((60, 160, w - 60, 160), fill=255, width=5)
    ld.rectangle((16, 16, w - 17, h - 17), outline=255, width=4)

    # weather: the paint has flaked in cloudy patches (coarse noise blown up and
    # thresholded softly), more towards the top where rain comes over the cornice,
    # with fine speckle; and it has run down in streaks
    coarse = Image.effect_noise((w // 16, h // 16), 90).resize((w, h), Image.BICUBIC)
    fine = Image.effect_noise((w // 3, h // 3), 70).resize((w, h), Image.BILINEAR)
    wear = Image.new("L", (w, h))
    cp, fp, ww = coarse.load(), fine.load(), wear.load()
    for y in range(h):
        top = 0.14 * (1 - y / h)
        for x in range(w):
            v = cp[x, y] / 255.0 - top
            ww[x, y] = int(255 * min(1.0, max(0.0, (v - 0.12) * 3.0)) * (0.75 + 0.25 * fp[x, y] / 255.0))
    wd = ImageDraw.Draw(wear)
    for _ in range(45):
        x = rng.randrange(w)
        y0 = rng.randrange(0, h // 3)
        wd.line((x, y0, x + rng.randrange(-2, 3), y0 + rng.randrange(40, 180)), fill=rng.randrange(40, 120),
                width=rng.choice((2, 3)))
    wear = wear.filter(ImageFilter.GaussianBlur(1.2))

    out = Image.new("RGBA", (w, h))
    px = out.load()
    gp, lp, wp = ground.load(), letters.load(), wear.load()
    for y in range(h):
        for x in range(w):
            keep = wp[x, y] / 255.0
            n = rng.random()
            if lp[x, y] > 128:
                # cream letters, faded; the brick shows where they have flaked
                a = int(230 * keep * (0.75 + 0.25 * n))
                px[x, y] = (205, 193, 160, a)
            elif gp[x, y] > 128:
                # the dark green-black ground, mostly gone
                a = int(120 * keep * keep * (0.6 + 0.4 * n))
                px[x, y] = (30, 38, 32, a)
            else:
                px[x, y] = (0, 0, 0, 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print("painted", OUT.name, out.size)


if __name__ == "__main__":
    paint()
