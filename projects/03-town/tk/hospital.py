"""Halden Ridge Community Hospital, on the south side of Ashgrove Street.

A small county hospital of 1964, closed in 1995: two storeys of faded buff
brick on a concrete plinth, pale concrete bands at the first floor and the
roof, a brick parapet under a concrete coping, and long ribbons of
aluminium-framed windows, some boarded with plywood, some broken, blinds
half down in a few, hopper vents left open.

- **Main entrance** (round door_at): a recessed aluminium storefront, its
  pair of glass doors chained and padlocked, the CLOSED notice taped inside;
  a flat concrete canopy on two steel posts; two steps up to the landing and
  a 1:16 ramp along the front with pipe rails. Between two concrete fins the
  name in bronze block letters, built from boxes: HALDEN RIDGE / COMMUNITY
  HOSPITAL. The P of HOSPITAL has come off (its pins and a clean ghost are
  left on the brick) and leans against the wall by the door; the N of HALDEN
  hangs from one pin.
- **Emergency** (local x 0..6.6): a higher drive-through canopy over the
  ambulance bay, a red-on-white EMERGENCY panel on its fascia, steel double
  doors at grade, yellow bollards, oil on the paving.
- **Roof**: a stair bulkhead and the lift overrun, two air handlers, a
  boiler flue, mushroom vents and standing water. Scuppers through the
  parapet drop into conductor heads and downpipes.
- One upstairs room on the front still has a lamp on behind a half-down
  blind (`lit_points`).

Built like house_kit.build_house: one MeshBuilder in the house's local frame
(x along the front, left to right seen from the street; y back into the
building; z up, the yard at GROUND), shared core materials with the colour
in the vertices. Returns (mb, matrix, ramps, lit_points, steps).
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, ground_grime, jitter_color, mul
from .house_kit import GROUND, WallFace, wall_faces


def _metal(c):
    """Vertex colour that gives metal_painted (mean albedo 0.83, 0.70, 0.67) the albedo c."""
    return (c[0] / 0.83, c[1] / 0.70, c[2] / 0.67)


# --- levels (local z) ----------------------------------------------------------------
SLAB = GROUND + 0.04             # top of the paving across the front apron
FLOOR = GROUND + 0.30            # ground-floor level: the entrance landing and the storefront
STOREY = 3.8
F2 = FLOOR + STOREY              # first floor
ROOF = FLOOR + 2 * STOREY        # top of the roof slab
PARAPET = ROOF + 0.85
COPING = PARAPET + 0.08
PLINTH_TOP = GROUND + 0.40
BAND1 = (F2 - 0.25, F2 + 0.20)   # pale concrete floor band
BAND2 = (ROOF - 0.25, ROOF + 0.20)
GF_SILL, GF_HEAD = FLOOR + 0.95, FLOOR + 2.75
FF_SILL, FF_HEAD = F2 + 0.95, F2 + 2.75
REVEAL = 0.18                    # wall face to the window frame
PARA_T = 0.30                    # parapet thickness
APRON = 3.6                      # depth of the paved front apron (local y -3.6..0)

# --- colours (vertex colours multiplying the shared maps) ------------------------------
BRICK = (1.24, 1.85, 1.71)       # red_brick faded towards buff (a stronger shift turns the mortar blue)
CONC = (2.0, 2.45, 3.2)          # concrete_floor_worn_02 made pale: bands, coping, sills
PLINTH = (1.7, 2.05, 2.7)
PAVING = (1.5, 1.85, 2.45)
FRAME = "chrome_dull"                # anodised aluminium sections
ALU = (1.45, 1.45, 1.4)
BRONZE = _metal((0.13, 0.10, 0.07))
RED = _metal((0.36, 0.05, 0.04))
WHITE = _metal((0.60, 0.59, 0.55))
STEEL = _metal((0.11, 0.13, 0.12))
RAIL = _metal((0.30, 0.31, 0.29))
ER_DOOR = _metal((0.16, 0.19, 0.16))
BEIGE = _metal((0.21, 0.22, 0.19))
SAFETY = (0.70, 0.55, 0.12)
PLY = (0.85, 0.80, 0.72)
PLY_OLD = (0.62, 0.60, 0.55)
CURTAINS = [(0.62, 0.70, 0.66), (0.60, 0.66, 0.74), (0.78, 0.76, 0.68)]
SLATS = (0.80, 0.78, 0.70)

# --- block letters ----------------------------------------------------------------------
# A condensed, square-cornered face like the aluminium letters of the 1960s, on a grid
# 7 units high: advance width, rectangles (x0, z0, x1, z1) and diagonal strokes
# ((xa, za), (xb, zb)), each stroke one unit wide.
GLYPHS = {
    "A": (4, [(0, 0, 1, 6), (3, 0, 4, 6), (1, 6, 3, 7), (1, 3, 3, 4)], []),
    "C": (4, [(0, 1, 1, 6), (1, 6, 4, 7), (1, 0, 4, 1)], []),
    "D": (4, [(0, 0, 1, 7), (1, 6, 3, 7), (1, 0, 3, 1), (3, 1, 4, 6)], []),
    "E": (4, [(0, 0, 1, 7), (1, 6, 4, 7), (1, 3, 3.4, 4), (1, 0, 4, 1)], []),
    "G": (4, [(0, 1, 1, 6), (1, 6, 4, 7), (1, 0, 4, 1), (3, 1, 4, 3), (2, 3, 4, 4)], []),
    "H": (4, [(0, 0, 1, 7), (3, 0, 4, 7), (1, 3, 3, 4)], []),
    "I": (1, [(0, 0, 1, 7)], []),
    "L": (4, [(0, 0, 1, 7), (1, 0, 4, 1)], []),
    "M": (6, [(0, 0, 1, 7), (5, 0, 6, 7)], [((0.6, 6.4), (3.0, 2.6)), ((5.4, 6.4), (3.0, 2.6))]),
    "N": (4, [(0, 0, 1, 7), (3, 0, 4, 7)], [((0.6, 6.5), (3.4, 0.5))]),
    "O": (4, [(0, 1, 1, 6), (3, 1, 4, 6), (1, 6, 3, 7), (1, 0, 3, 1)], []),
    "P": (4, [(0, 0, 1, 7), (1, 6, 3, 7), (3, 4, 4, 6), (1, 3, 3, 4)], []),
    "R": (4, [(0, 0, 1, 7), (1, 6, 3, 7), (3, 4, 4, 6), (1, 3, 3, 4)], [((2.0, 3.2), (3.5, 0.5))]),
    "S": (4, [(1, 6, 4, 7), (0, 4, 1, 6), (1, 3, 3, 4), (3, 1, 4, 3), (0, 0, 3, 1)], []),
    "T": (4, [(1.5, 0, 2.5, 6), (0, 6, 4, 7)], []),
    "U": (4, [(0, 1, 1, 7), (3, 1, 4, 7), (1, 0, 3, 1)], []),
    "Y": (4, [(1.5, 0, 2.5, 3.4)], [((0.5, 6.6), (2.0, 3.0)), ((3.5, 6.6), (2.0, 3.0))]),
}


# --- geometry on a wall face (u along it, z up, off outwards) ----------------------------------

def _q(mb, wf, u0, u1, z0, z1, off, mat, col=None, uvs=None):
    """A flat panel on the wall plane, facing out."""
    mb.face([wf.at(u0, z0, off), wf.at(u1, z0, off), wf.at(u1, z1, off), wf.at(u0, z1, off)], mat, color=col, uvs=uvs)


def _card(mb, wf, u0, u1, z0, z1, off, mat, col=None):
    """A decal card: the texture's 0..1 square on a wall panel."""
    _q(mb, wf, u0, u1, z0, z1, off, mat, col, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def _wbox(mb, wf, u0, u1, z0, z1, o0, o1, mat, col=None, skip=""):
    """A box on a wall face. skip: f(ront) b(ack, the wall side) l r (ends) t(op) d(own)."""
    P = wf.at
    faces = {
        "f": (P(u0, z0, o1), P(u1, z0, o1), P(u1, z1, o1), P(u0, z1, o1)),
        "b": (P(u1, z0, o0), P(u0, z0, o0), P(u0, z1, o0), P(u1, z1, o0)),
        "l": (P(u0, z0, o0), P(u0, z0, o1), P(u0, z1, o1), P(u0, z1, o0)),
        "r": (P(u1, z0, o1), P(u1, z0, o0), P(u1, z1, o0), P(u1, z1, o1)),
        "t": (P(u0, z1, o1), P(u1, z1, o1), P(u1, z1, o0), P(u0, z1, o0)),
        "d": (P(u0, z0, o0), P(u1, z0, o0), P(u1, z0, o1), P(u0, z0, o1)),
    }
    for k, pts in faces.items():
        if k not in skip:
            mb.face(list(pts), mat, color=col)


def _prism(mb, wf, poly, off0, off1, mat, col, sides=True):
    """An extruded polygon (counter-clockwise in u, z) standing off a wall, front and sides."""
    mb.face([wf.at(u, z, off1) for u, z in poly], mat, color=col)
    if sides:
        n = len(poly)
        for i in range(n):
            (ua, za), (ub, zb) = poly[i], poly[(i + 1) % n]
            mb.face([wf.at(ua, za, off0), wf.at(ub, zb, off0), wf.at(ub, zb, off1), wf.at(ua, za, off1)], mat, color=col)


def _reveal(mb, wf, u0, u1, zb, zt, depth, mat, col, head_mat=None, head_col=None):
    """Jambs and head of an opening, going into the wall."""
    mb.face([wf.at(u0, zb, 0), wf.at(u0, zb, -depth), wf.at(u0, zt, -depth), wf.at(u0, zt, 0)], mat, color=col)
    mb.face([wf.at(u1, zb, -depth), wf.at(u1, zb, 0), wf.at(u1, zt, 0), wf.at(u1, zt, -depth)], mat, color=col)
    mb.face([wf.at(u0, zt, -depth), wf.at(u1, zt, -depth), wf.at(u1, zt, 0), wf.at(u0, zt, 0)], head_mat or mat,
            color=head_col or col)


def _wall(mb, wf, z0, z1, holes, mat, col, cuts=()):
    """The wall face from z0 to z1 as rectangles round the holes (u0, u1, zb, zt).
    `cuts` add rows so the vertex grime has vertices to vary on."""
    levels = sorted({z0, z1, *[c for c in cuts if z0 < c < z1],
                     *[c for h in holes for c in (h[2], h[3]) if z0 < c < z1]})
    for a, b in zip(levels, levels[1:]):
        mid = (a + b) / 2
        cur, spans = 0.0, []
        for u0, u1 in sorted((h[0], h[1]) for h in holes if h[2] < mid < h[3]):
            if u0 > cur:
                spans.append((cur, u0))
            cur = max(cur, u1)
        if cur < wf.length:
            spans.append((cur, wf.length))
        for s0, s1 in spans:
            if s1 - s0 > 1e-3:
                _q(mb, wf, s0, s1, a, b, 0.0, mat, col)


def _band(mb, wf, z0, z1, out, mat, col, extend, gaps=()):
    """A course standing `out` proud of the wall along the whole face, broken at `gaps`.
    Front and back courses run past the corners; the side ones butt into them."""
    a0, a1 = (-out, wf.length + out) if extend else (0.0, wf.length)
    edges = [a0] + [g for gap in sorted(gaps) for g in gap] + [a1]
    for s0, s1 in zip(edges[::2], edges[1::2]):
        if s1 - s0 > 1e-3:
            skip = "b"
            if not extend and s0 == a0:
                skip += "l"
            if not extend and s1 == a1:
                skip += "r"
            _wbox(mb, wf, s0, s1, z0, z1, 0.0, out, mat, col, skip=skip)


# --- lettering --------------------------------------------------------------------------------

def _advance(ch):
    return 2.0 if ch == " " else GLYPHS[ch][0]


def _text_width(text, s):
    return (sum(_advance(c) for c in text) + (len(text) - 1)) * s


def _glyph(mb, wf, ch, u, z, s, off0, off1, col, mat="metal_painted", sides=True):
    _w, rects, diags = GLYPHS[ch]
    for x0, z0, x1, z1 in rects:
        _prism(mb, wf, [(u + x0 * s, z + z0 * s), (u + x1 * s, z + z0 * s), (u + x1 * s, z + z1 * s),
                        (u + x0 * s, z + z1 * s)], off0, off1, mat, col, sides)
    for k, ((xa, za), (xb, zb)) in enumerate(diags):
        pa, pb = Vector((u + xa * s, z + za * s)), Vector((u + xb * s, z + zb * s))
        t = (pb - pa).normalized()
        p = Vector((-t.y, t.x)) * (s / 2)
        # a hair behind the upright strokes, so overlapping fronts never share a plane
        _prism(mb, wf, [tuple(pa - p), tuple(pb - p), tuple(pb + p), tuple(pa + p)], off0,
               off1 - 0.004 * (k + 1), mat, col, sides)


def _text(mb, wf, text, uc, z, height, off0, off1, col, rng, fallen=None, crooked=None, ghost=None):
    """Raised letters centred on uc, baseline z. Letter `fallen` is gone (pins and a clean
    ghost on the wall); letter `crooked` hangs from its top pin. Returns where the fallen
    one was: (char, u, z, unit)."""
    s = height / 7.0
    u = uc - _text_width(text, s) / 2
    out = None
    for i, ch in enumerate(text):
        if ch != " ":
            c = jitter_color(rng, col, 0.18)
            pins = ((u + 0.5 * s, z + 1.5 * s), (u + 0.5 * s, z + 5.5 * s))
            if i == fallen:
                out = (ch, u, z, s)
                if ghost is not None:
                    _glyph(mb, wf, ch, u, z, s, 0.0, 0.004, ghost, mat="brick", sides=False)
                for pu, pz in pins:
                    _wbox(mb, wf, pu - 0.007, pu + 0.007, pz - 0.007, pz + 0.007, 0.0, off1 - 0.004, "chrome_dull",
                          (0.45, 0.38, 0.30), skip="b")
            elif i == crooked:
                tmp = MeshBuilder()
                _glyph(tmp, wf, ch, u, z, s, off0, off1, c)
                pivot = wf.at(pins[1][0], pins[1][1], 0.0)
                m = Matrix.Translation(pivot) @ Matrix.Rotation(-0.40, 4, wf.n) @ Matrix.Translation(-pivot)
                mb.extend(tmp, m)
                pu, pz = pins[0]
                _wbox(mb, wf, pu - 0.007, pu + 0.007, pz - 0.007, pz + 0.007, 0.0, off1 - 0.004, "chrome_dull",
                      (0.45, 0.38, 0.30), skip="b")
            else:
                _glyph(mb, wf, ch, u, z, s, off0, off1, c)
        u += (_advance(ch) + 1.0) * s
    return out


# --- windows ------------------------------------------------------------------------------------

def _pick(rng, weights):
    r = rng.random() * sum(weights.values())
    for k, w in weights.items():
        r -= w
        if r <= 0:
            return k
    return k


def _blind(mb, wf, ga, gb, zt, zb, drop, off, rng, crook=0.0):
    """A venetian blind let down `drop` of the way, a slat or two askew, one side lower if `crook`."""
    n = max(3, int((zt - zb) * drop / 0.07))
    col = mul(SLATS, rng.uniform(0.75, 1.0))
    for j in range(n):
        z = zt - 0.03 - j * 0.07
        dz = crook * j / n
        skew = rng.uniform(-0.05, 0.05) if rng.random() < 0.12 else 0.0
        za, zb_ = z - dz + skew, z - skew
        mb.face([wf.at(ga + 0.01, za - 0.055, off + 0.015), wf.at(gb - 0.01, zb_ - 0.055, off + 0.015),
                 wf.at(gb - 0.01, zb_, off - 0.015), wf.at(ga + 0.01, za, off - 0.015)], "fabric",
                color=mul(col, 0.9 + 0.1 * (j % 2)))
    zl = zt - 0.03 - n * 0.07
    _wbox(mb, wf, ga + 0.01, gb - 0.01, zl - 0.03, zl, off - 0.012, off + 0.012, FRAME, ALU)
    mb.tube([wf.at(gb - 0.1, zt - 0.02, off + 0.02), wf.at(gb - 0.1, zl - 0.35, off + 0.02)], 0.003, "wire", segments=3)


def _curtain(mb, wf, ua, ub, zb, zt, off, col):
    """A cubicle curtain inside, hanging in folds."""
    folds = 6
    for k in range(folds):
        a = ua + (ub - ua) * k / folds
        b = ua + (ub - ua) * (k + 1) / folds
        da, db = (off + 0.05, off - 0.05) if k % 2 == 0 else (off - 0.05, off + 0.05)
        mb.face([wf.at(a, zb, da), wf.at(b, zb, db), wf.at(b, zt, db), wf.at(a, zt, da)], "fabric",
                color=mul(col, 1.0 if k % 2 == 0 else 0.8))


def _lit_room(mb, wf, ua, ub, zb, zt, rng, lit_points):
    """The one room with a lamp on: a throat the width of the pane, then a ward behind
    the dark backdrops of the panes either side."""
    front, mid, back = -REVEAL - 0.03, -0.95, -3.6
    z0, z1 = zb - 0.95, zt + 0.5
    green, ceil = (0.55, 0.62, 0.50), (0.78, 0.78, 0.74)
    ra, rb = ua - 1.3, ub + 1.3
    # throat
    mb.face([wf.at(ua, z0, front), wf.at(ua, z0, mid), wf.at(ua, z1, mid), wf.at(ua, z1, front)], "room_wall", color=green)
    mb.face([wf.at(ub, z0, mid), wf.at(ub, z0, front), wf.at(ub, z1, front), wf.at(ub, z1, mid)], "room_wall", color=green)
    mb.face([wf.at(ua, z0, front), wf.at(ub, z0, front), wf.at(ub, z0, mid), wf.at(ua, z0, mid)], "room_wall",
            color=(0.42, 0.42, 0.40))
    mb.face([wf.at(ua, z1, mid), wf.at(ub, z1, mid), wf.at(ub, z1, front), wf.at(ua, z1, front)], "room_wall", color=ceil)
    # its dark outsides, seen through the panes either side
    mb.face([wf.at(ua, z0, -0.9), wf.at(ua, z0, front), wf.at(ua, z1, front), wf.at(ua, z1, -0.9)], "interior_dark")
    mb.face([wf.at(ub, z0, front), wf.at(ub, z0, -0.9), wf.at(ub, z1, -0.9), wf.at(ub, z1, front)], "interior_dark")
    # the ward
    _q(mb, wf, ra, rb, z0, z1, back, "room_wall", green)
    mb.face([wf.at(ra, z0, mid), wf.at(ra, z0, back), wf.at(ra, z1, back), wf.at(ra, z1, mid)], "room_wall", color=green)
    mb.face([wf.at(rb, z0, back), wf.at(rb, z0, mid), wf.at(rb, z1, mid), wf.at(rb, z1, back)], "room_wall", color=green)
    for a, b in ((ra, ua), (ub, rb)):                                        # the window wall, from inside
        mb.face([wf.at(b, z0, mid), wf.at(a, z0, mid), wf.at(a, z1, mid), wf.at(b, z1, mid)], "room_wall", color=green)
    mb.face([wf.at(ra, z0, mid), wf.at(rb, z0, mid), wf.at(rb, z0, back), wf.at(ra, z0, back)], "room_wall",
            color=(0.42, 0.42, 0.40))
    mb.face([wf.at(ra, z1, back), wf.at(rb, z1, back), wf.at(rb, z1, mid), wf.at(ra, z1, mid)], "room_wall", color=ceil)
    # a hospital bed, its foot towards the window
    bc = (ua + ub) / 2 + 0.15
    bu0, bu1 = bc - 0.48, bc + 0.48
    _wbox(mb, wf, bu0, bu1, z0 + 0.25, z0 + 0.55, back + 0.15, back + 2.15, "metal_painted", (0.75, 0.78, 0.74))
    _wbox(mb, wf, bu0 + 0.03, bu1 - 0.03, z0 + 0.55, z0 + 0.68, back + 0.18, back + 2.1, "fabric", (0.82, 0.82, 0.78))
    _wbox(mb, wf, bu0 + 0.15, bu1 - 0.15, z0 + 0.68, z0 + 0.78, back + 0.25, back + 0.6, "fabric", (0.9, 0.9, 0.86))
    _wbox(mb, wf, bu0, bu1, z0, z0 + 1.05, back + 0.12, back + 0.16, "metal_painted", (0.7, 0.72, 0.7))
    for lu in (bu0 + 0.03, bu1 - 0.03):
        for lo in (back + 0.2, back + 2.1):
            mb.tube([wf.at(lu, z0, lo), wf.at(lu, z0 + 0.25, lo)], 0.02, "chrome_dull", segments=4)
    _wbox(mb, wf, ua - 0.6, ua - 0.1, z0, z0 + 0.75, back + 0.15, back + 0.6, "metal_painted", (0.72, 0.74, 0.68))
    _wbox(mb, wf, bc - 0.4, bc + 0.4, z0 + 1.55, z0 + 1.7, back, back + 0.13, "metal_painted", (0.8, 0.8, 0.76), skip="b")
    # someone's lamp on a table in the window, still on
    tu = ua + 0.35
    _wbox(mb, wf, tu - 0.3, tu + 0.3, z0 + 0.72, z0 + 0.76, front - 0.55, front - 0.15, "wood_weathered", (0.5, 0.4, 0.3))
    for lu in (tu - 0.27, tu + 0.27):
        mb.tube([wf.at(lu, z0, front - 0.35), wf.at(lu, z0 + 0.72, front - 0.35)], 0.015, "chrome_dull", segments=4)
    lamp = wf.at(tu, z0 + 0.76, front - 0.35)
    mb.tube([lamp, lamp + Vector((0, 0, 0.3))], 0.01, "chrome_dull", segments=4)
    mb.cylinder(lamp + Vector((0, 0, 0.28)), (0, 0, 0.2), 0.13, "window_lit_lamp", segments=10, radius_top=0.08, caps="none")
    lit_points.append(lamp + Vector((0, 0, 0.38)))
    # the cubicle curtain, half drawn, and a chair
    _curtain(mb, wf, ra + 0.1, ua + 0.2, z0 + 0.3, z1 - 0.15, back + 2.5, CURTAINS[0])
    mb.tube([wf.at(ra + 0.05, z1 - 0.1, back + 2.5), wf.at(rb - 0.05, z1 - 0.1, back + 2.5)], 0.012, "chrome_dull", segments=4)
    _wbox(mb, wf, ub + 0.9, ub + 1.3, z0 + 0.42, z0 + 0.47, back + 2.4, back + 2.85, "metal_painted", (0.35, 0.45, 0.5))
    _wbox(mb, wf, ub + 0.9, ub + 1.3, z0 + 0.47, z0 + 0.95, back + 2.4, back + 2.45, "metal_painted", (0.35, 0.45, 0.5))


def _ribbon(mb, wf, u0, u1, zb, zt, states, rng, brick, stain_floor, stain_p=0.6, lit_points=None):
    """A ribbon of aluminium windows: one opening, panes between mullions, a transom
    with hopper vents. states per pane: ok, blind, curtain, sheet, boarded, loose, broken, lit."""
    R = REVEAL
    n = len(states)
    pw = (u1 - u0) / n
    sc = MeshBuilder()                                                # soldier course over the head
    sc.rot_keys.add("brick")
    _wbox(sc, wf, u0 - 0.1, u1 + 0.1, zt, zt + 0.21, 0.0, 0.012, "brick", mul(brick, 0.88), skip="bt")
    mb.extend(sc)
    _reveal(mb, wf, u0, u1, zb, zt, R, "brick", mul(brick, 0.9), head_mat="concrete", head_col=mul(CONC, 0.8))
    _wbox(mb, wf, u0 - 0.07, u1 + 0.07, zb - 0.09, zb, -R, 0.06, "concrete", mul(CONC, 0.92), skip="b")
    fo0, fo1, go, fw = -R + 0.02, -R + 0.08, -R + 0.05, 0.055
    _wbox(mb, wf, u0, u1, zt - fw, zt, fo0, fo1, FRAME, ALU, skip="btlr")
    _wbox(mb, wf, u0, u1, zb, zb + fw, fo0, fo1, FRAME, ALU, skip="bdlr")
    _wbox(mb, wf, u0, u0 + fw, zb + fw, zt - fw, fo0, fo1, FRAME, ALU, skip="bltd")
    _wbox(mb, wf, u1 - fw, u1, zb + fw, zt - fw, fo0, fo1, FRAME, ALU, skip="brtd")
    tz = zt - 0.55
    _wbox(mb, wf, u0 + fw, u1 - fw, tz - 0.025, tz + 0.025, fo0, fo1 - 0.006, FRAME, ALU, skip="blr")
    for k in range(1, n):
        uk = u0 + k * pw
        _wbox(mb, wf, uk - 0.028, uk + 0.028, zb + fw, zt - fw, fo0, fo1, FRAME, ALU, skip="btd")
    back = -0.9
    bz0, bz1 = zb - 0.35, zt + 0.35
    for k, st in enumerate(states):
        pa, pb = u0 + k * pw, u0 + (k + 1) * pw
        ga, gb = pa + (fw if k == 0 else 0.028), pb - (fw if k == n - 1 else 0.028)
        za, zc = zb + fw, zt - fw
        # the dark behind each pane (a lit room instead for the one that is lit)
        if st == "lit":
            _lit_room(mb, wf, pa, pb, zb, zt, rng, lit_points if lit_points is not None else [])
        else:
            ba, bb = pa - (0.35 if k == 0 else 0.0), pb + (0.35 if k == n - 1 else 0.0)
            _q(mb, wf, ba, bb, bz0, bz1, back, "interior_dark")
            mb.face([wf.at(ba, bz1, back), wf.at(bb, bz1, back), wf.at(bb, bz1, -R), wf.at(ba, bz1, -R)], "interior_dark")
            mb.face([wf.at(ba, bz0, -R), wf.at(bb, bz0, -R), wf.at(bb, bz0, back), wf.at(ba, bz0, back)], "interior_dark")
            if k == 0:
                mb.face([wf.at(ba, bz0, -R), wf.at(ba, bz0, back), wf.at(ba, bz1, back), wf.at(ba, bz1, -R)], "interior_dark")
            if k == n - 1:
                mb.face([wf.at(bb, bz0, back), wf.at(bb, bz0, -R), wf.at(bb, bz1, -R), wf.at(bb, bz1, back)], "interior_dark")
        # glass, or what is left of it
        if st in ("ok", "blind", "curtain", "sheet", "lit"):
            if st == "ok" and rng.random() < 0.3:                 # the hopper vent left open
                _q(mb, wf, ga, gb, za, tz - 0.025, go, "window_glass")
                mb.face([wf.at(ga, tz + 0.025, go), wf.at(gb, tz + 0.025, go), wf.at(gb, zc, go - 0.16),
                         wf.at(ga, zc, go - 0.16)], "window_glass")
                _wbox(mb, wf, ga, gb, zc - 0.03, zc, go - 0.18, go - 0.14, FRAME, ALU)
            else:
                _q(mb, wf, ga, gb, za, zc, go, "window_glass")
        elif st == "ac":                                              # a sleeve unit in the bottom of the pane
            za2 = za + 0.48
            _q(mb, wf, ga, gb, za2, zc, go, "window_glass")
            _q(mb, wf, ga, gb, za, za2, go + 0.01, "plywood", PLY_OLD)
            cu = (ga + gb) / 2
            body = jitter_color(rng, BEIGE, 0.08)
            _wbox(mb, wf, cu - 0.33, cu + 0.33, za + 0.03, za + 0.43, go - 0.25, 0.3, "metal_painted", body, skip="b")
            for j in range(5):
                zz = za + 0.08 + j * 0.065
                _wbox(mb, wf, cu - 0.28, cu + 0.28, zz, zz + 0.03, 0.3, 0.312, "metal_painted", mul(body, 0.6), skip="b")
            _card(mb, wf, cu - 0.28, cu + 0.28, max(stain_floor, zb - 1.1), zb - 0.09, 0.004, "decal_streaks", (0.9, 0.75, 0.6))
        elif st == "broken":
            for _ in range(rng.randint(2, 4)):
                top = rng.random() < 0.4
                su = rng.uniform(ga, gb - 0.3)
                sw = rng.uniform(0.15, 0.35)
                tip = rng.uniform(0.15, 0.45)
                zz = zc if top else za
                sgn = -1 if top else 1
                mb.face([wf.at(su, zz, go), wf.at(su + sw, zz, go), wf.at(su + rng.uniform(0, sw), zz + sgn * tip, go)]
                        if not top else
                        [wf.at(su + sw, zz, go), wf.at(su, zz, go), wf.at(su + rng.uniform(0, sw), zz + sgn * tip, go)],
                        "glass_dirty")
        # dressing behind the glass
        if st in ("blind", "lit"):
            _blind(mb, wf, ga, gb, zc, za, rng.uniform(0.35, 0.7) if st == "blind" else 0.3, go - 0.06, rng,
                   crook=rng.choice((0.0, 0.0, 0.25)) if st == "blind" else 0.0)
        elif st == "curtain":
            c0 = rng.uniform(0.0, 0.4)
            _curtain(mb, wf, ga + (gb - ga) * c0, gb + 0.1, za - 0.1, zc + 0.05, -0.5, CURTAINS[rng.randrange(3)])
        elif st == "sheet":
            top = za + (zc - za) * rng.uniform(0.5, 0.8)
            mb.face([wf.at(ga, za, go - 0.03), wf.at(gb, za, go - 0.025), wf.at(gb, top - 0.06, go - 0.025),
                     wf.at(ga, top, go - 0.03)], "fabric", color=(0.72, 0.70, 0.62))
        elif st == "broken" and rng.random() < 0.5:                  # a blind hanging down through the hole
            _blind(mb, wf, ga, gb, zc, za, rng.uniform(0.6, 0.9), go - 0.06, rng, crook=0.35)
        # plywood nailed over the opening
        if st in ("boarded", "loose"):
            ea = pa - (0.03 if k == 0 else -0.002)
            eb = pb + (0.03 if k == n - 1 else -0.002)
            col = jitter_color(rng, PLY if rng.random() < 0.5 else PLY_OLD, 0.1)
            if st == "boarded":
                _wbox(mb, wf, ea, eb, zb, zt + 0.03, 0.0, 0.02, "plywood", col, skip="b")
            else:                                                     # pulled away at the top
                tmp = MeshBuilder()
                _wbox(tmp, wf, ea, eb, zb, zt + 0.03, 0.0, 0.02, "plywood", col)
                pivot = wf.at(ea, zb, 0.02)
                m = Matrix.Translation(pivot) @ Matrix.Rotation(0.12, 4, wf.a) @ Matrix.Rotation(-0.05, 4, wf.n) \
                    @ Matrix.Translation(-pivot)
                mb.extend(tmp, m)
        # dirty water down the wall from the sill
        if rng.random() < stain_p:
            w = pw * rng.uniform(0.6, 1.0)
            c = (pa + pb) / 2 + rng.uniform(-0.15, 0.15)
            top = zb - 0.09
            bot = max(stain_floor, top - rng.uniform(0.5, 1.3))
            if top - bot > 0.2:
                _card(mb, wf, c - w / 2, c + w / 2, bot, top, 0.004, "decal_streaks")


def _states(n, rng, weights, fixed=None):
    out = [_pick(rng, weights) for _ in range(n)]
    for k, v in (fixed or {}).items():
        out[k] = v
    return out


# --- pieces in the local frame -----------------------------------------------------------------

def _rail(mb, pts, posts, r=0.024):
    """Steel pipe rail along `pts`, with posts (x, y, z_foot, z_top)."""
    mb.tube(pts, r, "metal_painted", segments=6, color=RAIL)
    for x, y, zf, zt in posts:
        mb.tube([(x, y, zf), (x, y, zt)], r, "metal_painted", segments=6, color=RAIL)
        mb.cylinder((x, y, zf), (0, 0, 0.01), 0.06, "metal_painted", segments=6, color=RAIL, caps="top")


def _bollard(mb, x, y, h=1.0):
    mb.cylinder((x, y, SLAB - 0.02), (0, 0, h), 0.1, "metal_painted", segments=10, color=SAFETY, caps="none")
    mb.cylinder((x, y, SLAB - 0.02 + h), (0, 0, 0.06), 0.1, "metal_painted", segments=10, radius_top=0.05,
                color=SAFETY, caps="top")
    mb.cylinder((x, y, SLAB + h * 0.62), (0, 0, 0.09), 0.103, "metal_painted", segments=10, color=(0.2, 0.2, 0.2),
                caps="none")


def _post(mb, x, y, z_top, yellow=False):
    s = 0.075
    if yellow:
        mb.box((x - s, y - s, SLAB), (x + s, y + s, SLAB + 1.0), "metal_painted", color=SAFETY, skip="-z+z")
        mb.box((x - s, y - s, SLAB + 1.0), (x + s, y + s, z_top), "metal_painted", color=STEEL, skip="-z+z")
    else:
        mb.box((x - s, y - s, SLAB), (x + s, y + s, z_top), "metal_painted", color=STEEL, skip="-z+z")
    mb.box((x - 0.14, y - 0.14, SLAB), (x + 0.14, y + 0.14, SLAB + 0.02), "metal_painted", color=mul(STEEL, 1.4),
           skip="-z")
    for dx, dy in ((-0.1, -0.1), (0.1, -0.1), (0.1, 0.1), (-0.1, 0.1)):
        mb.cylinder((x + dx, y + dy, SLAB + 0.02), (0, 0, 0.03), 0.012, "metal_rust", segments=6, caps="top")


def _canopy(mb, x0, x1, y0, z_under, z_top, rng, lights=()):
    """A flat concrete canopy cantilevered off the wall: deep fascia, gravel stop, dead lights."""
    mb.box((x0, y0, z_under), (x1, 0.0, z_top), "concrete", color=CONC, skip="+y",
           mats={"+z": "road_patch"})
    m = 0.03
    mb.box((x0 - m, y0 - m, z_top - 0.05), (x1 + m, y0 + 0.12, z_top + 0.05), FRAME, color=mul(ALU, 0.8),
           skip="+y")
    for xe in (x0, x1):
        a, b = (xe - m, xe + 0.12) if xe == x0 else (xe - 0.12, xe + m)
        mb.box((a, y0 + 0.12, z_top - 0.05), (b, 0.0, z_top + 0.05), FRAME, color=mul(ALU, 0.8),
               skip="+y-y")
    for lx, ly in lights:                                            # recessed fixtures, long dead
        mb.box((lx - 0.22, ly - 0.22, z_under - 0.03), (lx + 0.22, ly + 0.22, z_under), "metal_painted",
               color=mul(ALU, 0.9), skip="+z")
        mb.face([Vector((lx - 0.17, ly - 0.17, z_under - 0.032)), Vector((lx - 0.17, ly + 0.17, z_under - 0.032)),
                 Vector((lx + 0.17, ly + 0.17, z_under - 0.032)), Vector((lx + 0.17, ly - 0.17, z_under - 0.032))],
                "sodium_off")
    # water run off the fascia
    wf = WallFace((x0, y0), (1, 0), (0, -1), x1 - x0, "fascia")
    u = rng.uniform(0.1, 0.6)
    while u < x1 - x0 - 0.5:
        w = rng.uniform(0.4, 0.9)
        _card(mb, wf, u, u + w, z_under + 0.02, z_top - 0.02, 0.004, "decal_grime", (0.9, 0.9, 0.9))
        u += w + rng.uniform(0.6, 1.8)


def _downpipe(mb, wf, u, rng, shoe_out=False):
    """Scupper through the parapet band, conductor head, pipe to the ground."""
    _q(mb, wf, u - 0.09, u + 0.09, ROOF + 0.03, ROOF + 0.16, 0.034, "interior_dark")
    _wbox(mb, wf, u - 0.07, u + 0.07, ROOF + 0.02, ROOF + 0.05, 0.03, 0.22, "metal_painted", (0.5, 0.5, 0.48), skip="b")
    hz0, hz1 = BAND2[0] - 0.5, BAND2[0] - 0.06
    _wbox(mb, wf, u - 0.17, u + 0.17, hz0 + 0.12, hz1, 0.0, 0.27, "metal_painted", (0.55, 0.53, 0.5), skip="b")
    _wbox(mb, wf, u - 0.09, u + 0.09, hz0, hz0 + 0.12, 0.06, 0.21, "metal_painted", (0.5, 0.48, 0.45), skip="bt")
    off = 0.135
    foot = (SLAB if shoe_out else GROUND) + 0.28
    pts = [wf.at(u, hz0 + 0.02, off), wf.at(u, foot, off)]
    if shoe_out:
        pts.append(wf.at(u, SLAB + 0.07, off + 0.24))
    mb.tube(pts, 0.05, "metal_painted", segments=8, color=(0.48, 0.46, 0.43))
    if not shoe_out:                                                    # cast-iron boot into the drain
        mb.cylinder(wf.at(u, GROUND - 0.02, off), (0, 0, 0.32), 0.07, "metal_rust", segments=8, color=(0.6, 0.55, 0.5),
                    caps="top")
    z = foot + 0.6
    while z < hz0 - 0.3:
        _wbox(mb, wf, u - 0.06, u + 0.06, z, z + 0.04, 0.0, off + 0.055, "metal_rust", (0.6, 0.55, 0.5), skip="b")
        z += 1.8
    _card(mb, wf, u - 0.2, u + 0.2, hz0 - rng.uniform(1.2, 2.0), hz0, 0.004, "decal_streaks")


# --- the building -------------------------------------------------------------------------------

def build_hospital(lot, rng: random.Random):
    """Returns (MeshBuilder in the local frame, local->world matrix, step ramps (local boxes),
    lit-window light points (local), path start (sx0, sx1, y)), as house_kit.build_house."""
    h = lot.house
    W, D = h.width, h.depth
    wear = h.wear
    mb = MeshBuilder()
    faces = wall_faces(W, D)
    lit_points: list = []
    ramps: list = []
    dc = h.door_at + 0.9                        # centre of the pair of doors
    SF = (dc - 1.8, dc + 1.8)                    # storefront: sidelight, two leaves, sidelight
    RECESS = 0.5
    BAY = (dc - 3.15, dc + 3.15)                 # entrance bay between the concrete fins
    FIN_W = 0.3
    ER = (1.5, 3.3)                              # emergency double doors
    ERC = (-0.25, 6.6)                           # emergency canopy, x
    ERC_Y = -(APRON + 0.4)                       # its front: 0.4 m past the apron, above 3.4 m
    MC = (BAY[0] - 0.25, BAY[1] + 0.25)          # main canopy, x
    MC_Y = -2.6
    LAND = (BAY[0] - 0.15, BAY[1] + 0.05, -1.8)  # landing x0, x1, front y
    STEP = (dc - 2.2, dc + 2.2)
    RAMP = (LAND[1], LAND[1] + 12 * 0.3 + 0.05 * 12)   # 1:16 down to the paving
    brick = BRICK
    stain_p = 0.35 + 0.45 * wear

    mb.grime = ground_grime(GROUND, 1.3, 0.25 + 0.3 * wear, top_z=PARAPET, top_strength=0.12 + 0.15 * wear)
    cuts = (GROUND + 0.9, GROUND + 1.3, PARAPET - 0.6)

    # --- the four walls, with their openings ---------------------------------------------
    front_holes = [
        (ER[0], ER[1], SLAB - 0.1, SLAB + 2.3, "er"),
        (4.0, 6.6, GF_SILL, GF_HEAD, "win"),
        (SF[0], SF[1], FLOOR - 0.1, GF_HEAD, "store"),
        (BAY[1] + 0.65, W - 0.6, GF_SILL, GF_HEAD, "win"),
        (0.6, 6.6, FF_SILL, FF_HEAD, "win"),
        (BAY[1] + 0.65, W - 0.6, FF_SILL, FF_HEAD, "win"),
    ]
    side_holes = [(1.5, 11.5, GF_SILL, GF_HEAD, "win"), (1.5, 11.5, FF_SILL, FF_HEAD, "win")]
    back_holes = [
        (1.0, 6.0, GF_SILL, GF_HEAD, "win"),
        (6.8, 9.6, GROUND - 0.1, GROUND + 3.1, "roller"),
        (10.0, 11.0, GROUND - 0.1, GROUND + 2.15, "door"),
        (12.4, W - 1.0, GF_SILL, GF_HEAD, "win"),
        (1.0, 11.0, FF_SILL, FF_HEAD, "win"),
        (12.4, W - 1.0, FF_SILL, FF_HEAD, "win"),
    ]
    holes = {"front": front_holes, "left": side_holes, "right": side_holes, "back": back_holes}
    for key, wf in faces.items():
        col = jitter_color(rng, brick, 0.03)
        _wall(mb, wf, PLINTH_TOP, PARAPET, holes[key], "brick", col, cuts)
        ext = key in ("front", "back")
        door_gaps = [(o[0], o[1]) for o in holes[key] if o[4] in ("er", "store", "roller", "door")]
        _band(mb, wf, GROUND - 0.05, PLINTH_TOP, 0.04, "concrete", PLINTH, ext, gaps=door_gaps)
        _band(mb, wf, BAND1[0], BAND1[1], 0.03, "concrete", CONC, ext)
        _band(mb, wf, BAND2[0], BAND2[1], 0.03, "concrete", CONC, ext)
        # rain run off the coping, down the parapet
        u = rng.uniform(0.2, 1.0)
        while u < wf.length - 0.6:
            w = rng.uniform(0.5, 1.2)
            _card(mb, wf, u, min(u + w, wf.length - 0.05), BAND2[1] + 0.01, PARAPET - 0.01, 0.004, "decal_grime",
                  (0.85, 0.85, 0.85))
            u += w + rng.uniform(0.4, 2.2)

    # moss and damp along the foot of the plinth, thickest on this north side
    for key, wf in faces.items():
        u = rng.uniform(0.0, 1.5)
        while u < wf.length - 0.8:
            w = rng.uniform(1.2, 3.0)
            w = min(w, wf.length - u)
            gap = any(o[0] - 0.1 < u + w and u < o[1] + 0.1 and o[4] in ("er", "store", "roller", "door") for o in holes[key])
            if not gap and (key == "front" or rng.random() < 0.6):
                mb.face([wf.at(u, GROUND - 0.02, 0.043), wf.at(u + w, GROUND - 0.02, 0.043),
                         wf.at(u + w, GROUND + rng.uniform(0.18, 0.3), 0.043), wf.at(u, GROUND + 0.22, 0.043)],
                        "decal_moss_strip", uvs=[(0, 0), (0, w / 1.5), (1, w / 1.5), (1, 0)], color=(0.8, 0.8, 0.8))
            u += w + rng.uniform(0.5, 2.5)

    # --- windows ----------------------------------------------------------------------------
    wf = faces["front"]
    gf = {"boarded": 0.55 * wear + 0.1, "loose": 0.05, "broken": 0.12, "blind": 0.2, "ok": 0.1, "sheet": 0.06}
    ff = {"boarded": 0.15, "broken": 0.2 * wear + 0.05, "blind": 0.3, "ok": 0.3, "curtain": 0.12, "sheet": 0.05, "ac": 0.05}
    for u0, u1, zb, zt, kind in front_holes:
        if kind != "win":
            continue
        n = max(1, round((u1 - u0) / 1.2))
        if zb == GF_SILL:
            fixed = {0: "blind", 1: "sheet"} if u0 < 7 else {0: "boarded", 2: "loose", 3: "broken"}
            st = _states(n, rng, gf, fixed)
            floor_z = PLINTH_TOP
        else:
            fixed = {0: "blind", 2: "broken", 3: "curtain", 4: "ac"} if u0 < 7 else {1: "blind", 3: "lit", 4: "broken"}
            st = _states(n, rng, ff, fixed)
            floor_z = BAND1[1] + 0.02
        _ribbon(mb, wf, u0, u1, zb, zt, st, rng, brick, floor_z, stain_p, lit_points)
    for key in ("left", "right", "back"):
        wf = faces[key]
        for u0, u1, zb, zt, kind in holes[key]:
            if kind != "win":
                continue
            n = max(1, round((u1 - u0) / 1.25))
            st = _states(n, rng, gf if zb == GF_SILL else ff)
            st = ["blind" if s == "lit" else s for s in st]
            _ribbon(mb, wf, u0, u1, zb, zt, st, rng, brick, PLINTH_TOP if zb == GF_SILL else BAND1[1] + 0.02,
                    stain_p * 0.8)

    # --- main entrance: the recessed storefront -----------------------------------------------
    wf = faces["front"]
    s0, s1 = SF
    zt = GF_HEAD
    _reveal(mb, wf, s0, s1, FLOOR, zt, RECESS, "brick", mul(brick, 0.85), head_mat="concrete", head_col=mul(CONC, 0.75))
    so0, so1 = -RECESS, -RECESS + 0.1            # storefront sections
    sg = -RECESS + 0.05                          # its glass
    dz = FLOOR + 2.1                             # door head
    leaves = ((s0 + 0.9, dc), (dc, s1 - 0.9))
    verts = [s0, s0 + 0.9, s1 - 0.9, s1]
    for k, uu in enumerate(verts):
        a, b = (uu, uu + 0.06) if k == 0 else ((uu - 0.06, uu) if k == 3 else (uu - 0.035, uu + 0.035))
        _wbox(mb, wf, a, b, FLOOR, zt, so0, so1, FRAME, ALU, skip="b")
    for za_, zb_ in ((zt - 0.06, zt), (dz, dz + 0.07)):
        _wbox(mb, wf, s0 + 0.06, s1 - 0.06, za_, zb_, so0, so1 - 0.004, FRAME, ALU, skip="blr")
    # transom glass, sidelights (one boarded, one with the crack) with kick panels
    _q(mb, wf, s0 + 0.06, s1 - 0.06, dz + 0.07, zt - 0.06, sg, "window_glass")
    for a, b, which in ((s0 + 0.06, s0 + 0.865, "crack"), (s1 - 0.865, s1 - 0.06, "board")):
        _wbox(mb, wf, a, b, FLOOR, FLOOR + 0.35, so0, so1 - 0.01, FRAME, mul(ALU, 0.85), skip="blr")
        _q(mb, wf, a, b, FLOOR + 0.35, dz, sg, "window_glass")
        if which == "crack":
            _card(mb, wf, a + 0.05, b - 0.05, FLOOR + 0.6, FLOOR + 1.5, sg + 0.004, "glass_crack")
            _card(mb, wf, a + 0.12, a + 0.62, FLOOR + 1.0, FLOOR + 1.65, sg - 0.01, "poster_meeting")
        else:
            _wbox(mb, wf, a - 0.02, b + 0.02, FLOOR + 0.05, dz + 0.05, so1, so1 + 0.02, "plywood", PLY_OLD, skip="b")
    # the two leaves: narrow stiles, deep bottom rail, glass, pull bars, chain and padlock
    lo0, lo1 = so1, so1 + 0.05
    for i, (a, b) in enumerate(leaves):
        for ua, ub, za_, zb_ in ((a, a + 0.1, FLOOR, dz), (b - 0.1, b, FLOOR, dz), (a + 0.1, b - 0.1, dz - 0.1, dz),
                                 (a + 0.1, b - 0.1, FLOOR, FLOOR + 0.25), (a + 0.1, b - 0.1, FLOOR + 0.98, FLOOR + 1.04)):
            _wbox(mb, wf, ua, ub, za_, zb_, so0 + 0.02, lo1, FRAME, mul(ALU, 0.95), skip="b")
        _q(mb, wf, a + 0.1, b - 0.1, FLOOR + 0.25, dz - 0.1, sg, "window_glass")
        hu = b - 0.16 if i == 0 else a + 0.16
        for hz in (FLOOR + 0.85, FLOOR + 1.35):
            mb.tube([wf.at(hu, hz, lo1), wf.at(hu, hz, lo1 + 0.06)], 0.012, "chrome_dull", segments=5)
        mb.tube([wf.at(hu, FLOOR + 0.8, lo1 + 0.06), wf.at(hu, FLOOR + 1.4, lo1 + 0.06)], 0.016, "chrome_dull", segments=6)
    _card(mb, wf, leaves[0][0] + 0.2, leaves[0][0] + 0.62, FLOOR + 1.2, FLOOR + 1.76, sg - 0.012, "sign_closed_store")
    ha, hb = dc - 0.16, dc + 0.16
    zc = FLOOR + 1.12
    co = lo1 + 0.06
    chain = [wf.at(ha + 0.02, zc + 0.12, co), wf.at(dc, zc + 0.08, co + 0.03), wf.at(hb - 0.02, zc + 0.12, co),
             wf.at(hb + 0.02, zc + 0.02, co - 0.02), wf.at(hb - 0.03, zc - 0.06, co + 0.02), wf.at(dc + 0.03, zc - 0.1, co + 0.04),
             wf.at(ha + 0.03, zc - 0.06, co + 0.02), wf.at(ha - 0.02, zc + 0.03, co - 0.02), wf.at(ha + 0.04, zc + 0.1, co + 0.01),
             wf.at(dc - 0.02, zc - 0.02, co + 0.05), wf.at(dc, zc - 0.2, co + 0.05)]
    for j in range(len(chain) - 1):                                     # links, alternating, as short tubes
        p, q = chain[j], chain[j + 1]
        steps = max(1, int((q - p).length / 0.05))
        for t in range(steps):
            a = p.lerp(q, t / steps)
            b = p.lerp(q, (t + 0.9) / steps)
            mb.tube([a, b], 0.007, "chrome_dull", segments=3, color=(0.55, 0.5, 0.45))
    lk = wf.at(dc, zc - 0.27, co + 0.05)
    mb.box((lk.x - 0.03, lk.y - 0.015, lk.z - 0.04), (lk.x + 0.03, lk.y + 0.015, lk.z + 0.03), "chrome_dull",
           color=(0.75, 0.6, 0.35))
    mb.tube([lk + Vector((-0.018, 0, 0.03)), lk + Vector((-0.018, 0, 0.07)), lk + Vector((0.018, 0, 0.07)),
             lk + Vector((0.018, 0, 0.03))], 0.005, "chrome_dull", segments=4)
    # the lobby behind the glass: walls, a counter, chairs, a fallen ceiling tile, papers
    lx0, lx1, ly0, ly1, lz1 = BAY[0] + 0.4, BAY[1] - 0.4, RECESS, RECESS + 4.5, FLOOR + 3.1
    lob = MeshBuilder()
    green = (0.38, 0.44, 0.38)
    lob.box((lx0, ly0, FLOOR), (lx1, ly1, lz1), "room_wall", color=green, skip="-y-z")
    for f in range(len(lob.faces)):                                    # turn it inside out
        lob.faces[f] = tuple(reversed(lob.faces[f]))
        lob.uvs[f].reverse()
        lob.cols[f].reverse()
    mb.extend(lob)
    for a, b, za_, zb_ in ((lx0, s0, FLOOR, lz1), (s1, lx1, FLOOR, lz1), (s0, s1, zt, lz1)):   # its front wall, inside
        mb.face([Vector((b, ly0, za_)), Vector((a, ly0, za_)), Vector((a, ly0, zb_)), Vector((b, ly0, zb_))], "room_wall",
                color=green)
    mb.face([Vector((lx0, ly0, FLOOR + 0.004)), Vector((lx1, ly0, FLOOR + 0.004)), Vector((lx1, ly1, FLOOR + 0.004)),
             Vector((lx0, ly1, FLOOR + 0.004))], "concrete", color=(1.1, 1.3, 1.6))
    mb.box((dc - 1.6, ly1 - 1.6, FLOOR), (dc + 1.2, ly1 - 1.0, FLOOR + 1.05), "wood_weathered", color=(0.5, 0.42, 0.34),
           skip="-z")
    for k in range(4):
        cx = lx0 + 0.4 + k * 0.6
        mb.box((cx - 0.24, ly0 + 1.4, FLOOR + 0.42), (cx + 0.24, ly0 + 1.9, FLOOR + 0.48), "plastic_dark",
               color=(0.5, 0.55, 0.6))
        mb.box((cx - 0.24, ly0 + 1.85, FLOOR + 0.48), (cx + 0.24, ly0 + 1.9, FLOOR + 0.9), "plastic_dark",
               color=(0.5, 0.55, 0.6))
    mb.obox((dc + 0.6, ly0 + 1.6, FLOOR + 0.9), (0.6, 0.6, 0.015), 0.4, "room_wall", color=(0.75, 0.74, 0.7),
            tilt=(0.9, 0.3))
    for _ in range(7):
        px, py = rng.uniform(lx0 + 0.3, lx1 - 0.3), rng.uniform(ly0 + 0.4, ly1 - 2.0)
        mb.card((px, py, FLOOR + 0.008), rng.uniform(0.2, 0.3), rng.uniform(0.25, 0.32), rng.uniform(0, 3), "fabric",
                color=(0.85, 0.83, 0.78), flat=True)
    # recess floor
    mb.grime = None
    mb.box((s0, 0.0, GROUND - 0.05), (s1, RECESS, FLOOR), "concrete", color=PAVING, skip="-z-y-x+x+y")

    # --- emergency doors -------------------------------------------------------------------------
    e0, e1 = ER
    ez = SLAB + 2.3
    _reveal(mb, wf, e0, e1, SLAB, ez, 0.14, "concrete", mul(CONC, 0.85))
    _q(mb, wf, e0, e1, SLAB + 2.2, ez, -0.14, "metal_painted", ER_DOOR)
    em = (e0 + e1) / 2
    for a, b in ((e0, em - 0.005), (em + 0.005, e1)):
        _q(mb, wf, a, b, SLAB, SLAB + 2.2, -0.13, "metal_painted", ER_DOOR)
        _wbox(mb, wf, a + 0.05, b - 0.05, SLAB, SLAB + 0.3, -0.13, -0.124, "chrome_dull", (0.6, 0.58, 0.55), skip="b")
        _wbox(mb, wf, a + 0.25, b - 0.25, SLAB + 1.3, SLAB + 1.9, -0.13, -0.122, "metal_painted", mul(ER_DOOR, 1.3),
              skip="b")
        _q(mb, wf, a + 0.28, b - 0.28, SLAB + 1.33, SLAB + 1.87, -0.121, "glass_dirty")
        mb.tube([wf.at(a + 0.08, SLAB + 1.0, -0.06), wf.at(b - 0.08, SLAB + 1.0, -0.06)], 0.018, "chrome_dull", segments=6)
        for pu in (a + 0.1, b - 0.1):
            mb.tube([wf.at(pu, SLAB + 1.0, -0.13), wf.at(pu, SLAB + 1.0, -0.06)], 0.015, "chrome_dull", segments=5)
    _wbox(mb, wf, em - 0.005, em + 0.005, SLAB, SLAB + 2.2, -0.135, -0.128, "interior_dark", skip="b")
    mb.face([wf.at(e0, SLAB + 0.002, 0.0), wf.at(e1, SLAB + 0.002, 0.0), wf.at(e1, SLAB + 0.002, -0.13),
             wf.at(e0, SLAB + 0.002, -0.13)], "metal_rust", color=(0.7, 0.68, 0.65))
    mb.grime = ground_grime(GROUND, 1.3, 0.25 + 0.3 * wear)
    # call box, a dead wall lamp over the doors, the fire department connection
    _wbox(mb, wf, e1 + 0.25, e1 + 0.45, SLAB + 1.15, SLAB + 1.45, 0.0, 0.06, "metal_painted", (0.62, 0.62, 0.58), skip="b")
    _wbox(mb, wf, e1 + 0.3, e1 + 0.4, SLAB + 1.33, SLAB + 1.4, 0.06, 0.07, "lamp_red", skip="b")
    _wbox(mb, wf, em - 0.2, em + 0.2, ez + 0.25, ez + 0.5, 0.0, 0.2, FRAME, mul(ALU, 0.8), skip="b")
    mb.face([wf.at(em - 0.16, ez + 0.248, 0.02), wf.at(em + 0.16, ez + 0.248, 0.02), wf.at(em + 0.16, ez + 0.248, 0.18),
             wf.at(em - 0.16, ez + 0.248, 0.18)], "sodium_off")
    fu = 6.78
    brass = (0.75, 0.55, 0.28)
    mb.cylinder(wf.at(fu, PLINTH_TOP + 0.45, 0.0), wf.n * 0.12, 0.06, "chrome_dull", segments=8, color=brass)
    for du in (-0.09, 0.09):
        mb.cylinder(wf.at(fu, PLINTH_TOP + 0.45, 0.1), wf.n * 0.1 + wf.a * du * 0.8 - Vector((0, 0, 0.05)), 0.045,
                    "chrome_dull", segments=8, color=brass)
    _card(mb, wf, fu - 0.3, fu + 0.3, PLINTH_TOP + 0.02, PLINTH_TOP + 0.4, 0.004, "decal_streaks")

    # --- entrance bay: fins and the name ------------------------------------------------------------
    for a, b in ((BAY[0] - FIN_W, BAY[0]), (BAY[1], BAY[1] + FIN_W)):          # (two boxes, for the grime)
        mb.box((a, -0.25, GROUND - 0.05), (b, 0.0, GROUND + 1.3), "concrete", color=CONC, skip="+y-z+z")
        mb.box((a, -0.25, GROUND + 1.3), (b, 0.0, COPING + 0.15), "concrete", color=CONC, skip="+y-z")
    mb.grime = None
    zl2, zl1, lh = F2 + 1.45, F2 + 2.15, 0.42
    _text(mb, wf, "HALDEN RIDGE", dc, zl1, lh, 0.035, 0.075, BRONZE, rng, crooked=5)
    fallen = _text(mb, wf, "COMMUNITY HOSPITAL", dc, zl2, lh, 0.035, 0.075, BRONZE, rng, fallen=13,
                   ghost=mul(brick, 1.18))
    for zl in (zl1, zl2):                                              # rust run from the letters' pins
        u = BAY[0] + 0.3
        while u < BAY[1] - 0.5:
            w = rng.uniform(0.3, 0.7)
            _card(mb, wf, u, u + w, zl - rng.uniform(0.3, 0.55), zl + 0.05, 0.004, "decal_streaks", (0.95, 0.8, 0.7))
            u += w + rng.uniform(0.3, 1.0)
    # the P that came down, leaning against the brick by the door
    ch, _u, _z, s = fallen
    tmp = MeshBuilder()
    lw = WallFace((0, 0), (1, 0), (0, -1), 1.0, "letter")
    _glyph(tmp, lw, ch, 0.0, 0.0, s, 0.0, 0.04, mul(BRONZE, 1.15))
    lean = 0.24
    m = Matrix.Translation((s1 + 0.25, -0.012 - lh * math.sin(lean), FLOOR + 0.002)) @ Matrix.Rotation(0.12, 4, "Z") \
        @ Matrix.Rotation(-lean, 4, "X")
    mb.extend(tmp, m)

    # a bronze dedication plaque by the door, an ash urn, wall lights, the meter bank
    _wbox(mb, wf, BAY[0] + 0.4, BAY[0] + 1.0, FLOOR + 1.3, FLOOR + 1.75, 0.0, 0.015, "metal_painted", mul(BRONZE, 1.6), skip="b")
    for k in range(5):
        zz = FLOOR + 1.62 - k * 0.06
        _wbox(mb, wf, BAY[0] + 0.48 + (0.08 if k else 0.0), BAY[0] + 0.92 - (0.08 if k else 0.0), zz, zz + 0.025, 0.015,
              0.02, "metal_painted", mul(BRONZE, 2.4), skip="b")
    _card(mb, wf, BAY[0] + 0.45, BAY[0] + 0.95, FLOOR + 0.7, FLOOR + 1.3, 0.004, "decal_streaks", (0.8, 0.9, 0.8))
    mb.cylinder((BAY[1] - 0.45, -0.55, FLOOR), (0, 0, 0.62), 0.2, "concrete", segments=10, radius_top=0.23, color=mul(CONC, 0.8),
                caps="none")
    mb.disc((BAY[1] - 0.45, -0.55, FLOOR + 0.6), 0.2, "lawn_leafy", segments=10, color=(0.5, 0.45, 0.4))
    for key, u in (("left", D - 1.2), ("right", 1.2)):
        sf = faces[key]
        _wbox(mb, sf, u - 0.15, u + 0.15, FLOOR + 2.9, FLOOR + 3.15, 0.0, 0.22, "metal_painted", mul(BRONZE, 1.5), skip="b")
        mb.face([sf.at(u - 0.12, FLOOR + 2.899, 0.03), sf.at(u + 0.12, FLOOR + 2.899, 0.03), sf.at(u + 0.12, FLOOR + 2.899, 0.2),
                 sf.at(u - 0.12, FLOOR + 2.899, 0.2)], "sodium_off")
    sf = faces["left"]
    _wbox(mb, sf, 0.45, 1.25, PLINTH_TOP + 0.3, PLINTH_TOP + 1.6, 0.0, 0.16, "metal_painted", (0.55, 0.56, 0.52), skip="b")
    for k, uu in enumerate((0.6, 0.85, 1.1)):
        mb.cylinder(sf.at(uu, PLINTH_TOP + 0.9, 0.16), sf.n * 0.05, 0.07, "glass_dirty", segments=8)
        mb.tube([sf.at(uu, PLINTH_TOP + 1.6, 0.1), sf.at(uu, FLOOR + 3.3, 0.1)], 0.025, "metal_painted", segments=5,
                color=(0.5, 0.5, 0.48))
    _card(mb, sf, 0.4, 1.3, PLINTH_TOP, PLINTH_TOP + 0.35, 0.004, "decal_streaks")

    # a wheelchair, tipped over at the foot of the ramp
    wc = MeshBuilder()
    for sx in (-0.3, 0.3):
        ring = [(sx, 0.05 + 0.3 * math.cos(2 * math.pi * k / 12), 0.3 + 0.3 * math.sin(2 * math.pi * k / 12)) for k in range(13)]
        wc.tube(ring, 0.014, "tyre", segments=4)
        wc.cylinder((sx - 0.02, 0.05, 0.3), (0.04, 0, 0), 0.05, "chrome_dull", segments=6)
        wc.tube([(sx * 0.85, -0.38, 0.12), (sx * 0.85, -0.3, 0.52), (sx * 0.85, 0.22, 0.52), (sx * 0.85, 0.22, 0.95),
                 (sx * 0.85, 0.32, 0.98)], 0.012, "chrome_dull", segments=4)
        wc.cylinder((sx * 0.85 - 0.015, -0.4, 0.07), (0.03, 0, 0), 0.07, "tyre", segments=8)
        wc.box((sx * 0.85 - 0.08, -0.5, 0.12), (sx * 0.85 + 0.08, -0.36, 0.14), "plastic_dark")
    wc.box((-0.25, -0.28, 0.5), (0.25, 0.2, 0.53), "fabric", color=(0.25, 0.27, 0.3))
    wc.box((-0.25, 0.19, 0.55), (0.25, 0.22, 0.92), "fabric", color=(0.25, 0.27, 0.3))
    mb.extend(wc, Matrix.Translation((RAMP[1] - 0.3, -2.7, SLAB + 0.315)) @ Matrix.Rotation(0.6, 4, "Z")
              @ Matrix.Rotation(math.pi / 2, 4, "Y"))

    # --- canopies ---------------------------------------------------------------------------------------
    mc_under, mc_top = FLOOR + 3.0, FLOOR + 3.45
    _canopy(mb, MC[0], MC[1], MC_Y, mc_under, mc_top, rng, lights=((dc - 2.0, -1.3), (dc, -1.3), (dc + 2.0, -1.3)))
    er_under, er_top = BAND1[0] + 0.02, BAND1[0] + 0.62
    _canopy(mb, ERC[0], ERC[1], ERC_Y, er_under, er_top, rng, lights=((1.4, -1.6), (3.4, -1.6), (5.4, -1.6)))
    # the EMERGENCY panel on its fascia: red letters on white
    ew = WallFace((ERC[0], ERC_Y), (1, 0), (0, -1), ERC[1] - ERC[0], "er_fascia")
    pc = (ER[0] + ER[1]) / 2 + 0.25 - ERC[0]
    _wbox(mb, ew, pc - 1.35, pc + 1.35, er_under + 0.06, er_top - 0.06, 0.0, 0.035, "metal_painted", WHITE, skip="b")
    _text(mb, ew, "EMERGENCY", pc, er_under + 0.13, 0.34, 0.035, 0.055, RED, rng)
    mw = WallFace((MC[0], MC_Y), (1, 0), (0, -1), MC[1] - MC[0], "main_fascia")
    _text(mb, mw, "ENTRANCE", dc - MC[0], mc_under + 0.1, 0.22, 0.012, 0.035, BRONZE, rng)
    _card(mb, ew, pc - 1.3, pc - 0.4, er_under + 0.07, er_top - 0.07, 0.056, "decal_grime", (0.95, 0.95, 0.95))
    _card(mb, ew, pc + 0.5, pc + 1.25, er_under + 0.07, er_top - 0.07, 0.056, "decal_grime", (0.95, 0.95, 0.95))
    # posts: two under each canopy, the ambulance bay's with yellow feet; bollards by the doors
    for x in (MC[0] + 0.55, MC[1] - 0.55):
        _post(mb, x, MC_Y + 0.25, mc_under)
    for x in (ERC[0] + 0.55, ERC[1] - 0.3):
        _post(mb, x, -APRON + 0.25, er_under, yellow=True)
    for x in (ER[0] - 0.45, ER[1] + 0.85):
        _bollard(mb, x, -0.55)

    # --- landing, steps, ramp, rails, planters ------------------------------------------------------------
    lx0, lx1, ly = LAND
    mb.box((lx0, ly, GROUND - 0.05), (lx1, 0.0, FLOOR), "concrete", color=PAVING, skip="-z+y")
    tread = (SLAB + FLOOR) / 2
    mb.box((STEP[0], ly - 0.36, GROUND - 0.05), (STEP[1], ly, tread), "concrete", color=mul(PAVING, 0.95), skip="-z+y")
    for yy in (ly - 0.36, ly):                                         # worn nosings
        mb.box((STEP[0] + 0.05, yy - 0.002, (tread if yy < ly else FLOOR) - 0.04), (STEP[1] - 0.05, yy + 0.04,
               (tread if yy < ly else FLOOR) + 0.002), "metal_rust", color=(0.55, 0.52, 0.48), skip="-z+y")
    # the collision wedge runs through the nose of the tread, as house_kit.porch's does
    ramps.append(((STEP[0], ly - 0.36 * (FLOOR - GROUND) / (FLOOR - tread), GROUND), (STEP[1], ly, FLOOR)))
    r0, r1 = RAMP
    top = [Vector((r0, ly, FLOOR)), Vector((r1, ly, SLAB)), Vector((r1, 0.0, SLAB)), Vector((r0, 0.0, FLOOR))]
    mb.face(top, "concrete", color=PAVING)
    mb.face([Vector((r0, ly, GROUND - 0.05)), Vector((r1, ly, GROUND - 0.05)), Vector((r1, ly, SLAB)),
             Vector((r0, ly, FLOOR))], "concrete", color=mul(PAVING, 0.9))
    ry = ly + 0.08
    rh = 0.88

    def ramp_z(x):
        return FLOOR + (SLAB - FLOOR) * (x - r0) / (r1 - r0)
    _rail(mb, [(STEP[1] + 0.1, ry, FLOOR + rh), (r0, ry, FLOOR + rh), (r1, ry, SLAB + rh), (r1 + 0.3, ry, SLAB + rh),
               (r1 + 0.3, ry, SLAB + 0.1)],
          [(STEP[1] + 0.1, ry, FLOOR, FLOOR + rh), (r0 + 0.05, ry, FLOOR, FLOOR + rh)]
          + [(x, ry, ramp_z(x), ramp_z(x) + rh) for x in (r0 + (r1 - r0) / 3, r0 + 2 * (r1 - r0) / 3, r1 - 0.05)])
    mb.tube([(r0 + 0.1, ry, FLOOR + 0.45), (r1 - 0.05, ry, SLAB + 0.45)], 0.02, "metal_painted", segments=6, color=RAIL)
    wy = -0.12
    mb.tube([(r0 + 0.35, wy, ramp_z(r0 + 0.35) + rh), (r1 + 0.2, wy, SLAB + rh)], 0.022, "metal_painted", segments=6, color=RAIL)
    for x in (r0 + 0.4, (r0 + r1) / 2, r1 - 0.2):
        mb.box((x - 0.02, wy, ramp_z(x) + rh - 0.02), (x + 0.02, 0.0, ramp_z(x) + rh + 0.0), "metal_painted", color=RAIL,
               skip="+y")
    _rail(mb, [(lx0 + 0.1, ry, FLOOR + rh), (STEP[0] - 0.1, ry, FLOOR + rh)],
          [(lx0 + 0.1, ry, FLOOR, FLOOR + rh), (STEP[0] - 0.1, ry, FLOOR, FLOOR + rh)])
    for x in (STEP[0] + 0.12, STEP[1] - 0.12):                         # handrails down the steps
        _rail(mb, [(x, ly + 0.25, FLOOR + rh), (x, ly - 0.05, FLOOR + rh), (x, ly - 0.6, SLAB + rh), (x, ly - 0.6, SLAB + 0.3)],
              [(x, ly + 0.25, FLOOR, FLOOR + rh), (x, ly - 0.6, SLAB, SLAB + rh)])
    for (px0, px1, py0, py1) in ((6.0, 6.9, -1.5, -0.45), (W - 2.1, W - 0.9, -1.25, -0.4)):
        mb.box((px0, py0, GROUND - 0.05), (px1, py1, SLAB + 0.55), "concrete", color=mul(CONC, 0.85), skip="-z")
        mb.face([Vector((px0 + 0.08, py0 + 0.08, SLAB + 0.47)), Vector((px1 - 0.08, py0 + 0.08, SLAB + 0.47)),
                 Vector((px1 - 0.08, py1 - 0.08, SLAB + 0.47)), Vector((px0 + 0.08, py1 - 0.08, SLAB + 0.47))],
                "lawn_leafy", color=(0.7, 0.66, 0.6))
        cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
        for k in range(7):                                             # a dead shrub
            a = k * 2.4 + rng.uniform(-0.3, 0.3)
            r = rng.uniform(0.15, 0.35)
            tip = (cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8, SLAB + 0.47 + rng.uniform(0.35, 0.7))
            mb.tube([(cx + rng.uniform(-0.05, 0.05), cy, SLAB + 0.47), ((cx + tip[0]) / 2, (cy + tip[1]) / 2, tip[2] - 0.2), tip],
                    0.012, "bark", segments=3)
        # mb.grime is off here

    # the flagpole, its halyard slapping in the wind and no flag
    fpx, fpy = W - 3.0, -3.0
    mb.cylinder((fpx, fpy, GROUND - 0.05), (0, 0, 0.2), 0.32, "concrete", segments=12, color=mul(CONC, 0.9), caps="top")
    ftop = SLAB + 8.7
    mb.cylinder((fpx, fpy, SLAB + 0.1), (0, 0, ftop - SLAB - 0.1), 0.065, "metal_painted", segments=10, radius_top=0.04,
                color=(0.62, 0.62, 0.6), caps="none")
    mb.cylinder((fpx, fpy, ftop), (0, 0, 0.07), 0.07, "metal_painted", segments=8, color=(0.5, 0.5, 0.48))
    mb.cylinder((fpx, fpy, ftop + 0.07), (0, 0, 0.09), 0.07, "chrome_dull", segments=8, radius_top=0.0, color=(0.8, 0.62, 0.35))
    mb.cylinder((fpx, fpy, ftop + 0.07), (0, 0, -0.0001), 0.07, "chrome_dull", segments=8, caps="none")
    mb.tube([(fpx + 0.09, fpy, ftop + 0.03), (fpx + 0.075, fpy - 0.02, SLAB + 4.5), (fpx + 0.07, fpy, SLAB + 1.32)], 0.006,
            "wire", segments=3, color=(0.7, 0.68, 0.62))
    mb.tube([(fpx + 0.04, fpy, ftop + 0.03), (fpx + 0.05, fpy + 0.01, SLAB + 1.25)], 0.006, "wire", segments=3,
            color=(0.7, 0.68, 0.62))
    mb.box((fpx + 0.035, fpy - 0.015, SLAB + 1.2), (fpx + 0.075, fpy + 0.015, SLAB + 1.36), "chrome_dull")

    # --- the paved apron ----------------------------------------------------------------------------------
    mb.box((0.0, -APRON, GROUND - 0.05), (W, 0.0, SLAB), "concrete", color=PAVING, skip="-z+y")
    for x in (rng.uniform(1.0, 2.5), rng.uniform(3.5, 5.5)):           # oil where the ambulances stood
        y = rng.uniform(-2.6, -1.8)
        mb.card((x, y, SLAB + 0.004), rng.uniform(0.6, 0.9), rng.uniform(0.5, 0.7), rng.uniform(0, 3), "decal_oil", flat=True,
                color=(1.5, 1.5, 1.5))
    for x, y, w in ((rng.uniform(1, 5), -2.0, 1.4), (rng.uniform(19.5, 21), -2.2, 1.2), (rng.uniform(14.0, 16), -2.3, 1.2)):
        mb.card((x, y, SLAB + 0.005), w, w * 0.6, rng.uniform(0, 3), "decal_crack", flat=True)
    for x, y, z, w in ((1.2, -0.75, SLAB, 1.0), (dc + 1.4, RECESS - 0.35, FLOOR, 1.0), (lx0 + 0.5, -0.5, FLOOR, 1.0),
                       (W - 0.8, -0.6, SLAB, 1.5), (r1 + 0.25, -0.5, SLAB, 1.0), (6.45, -1.0, SLAB + 0.47, 0.8)):
        mb.card((x, y, z + 0.006), w, w * 0.8, rng.uniform(0, 3), "decal_leaves", flat=True)
    mb.card((dc - 0.8, -0.9, FLOOR + 0.007), 0.9, 0.9, 0.5, "decal_litter", flat=True)
    mb.card((BAY[1] + 0.65 + 3.5 * 1.2, -0.45, SLAB + 0.006), 1.0, 0.7, 1.2, "decal_shards", flat=True)

    # --- roof -------------------------------------------------------------------------------------------
    t = PARA_T
    mb.face([Vector((t, t, ROOF)), Vector((W - t, t, ROOF)), Vector((W - t, D - t, ROOF)), Vector((t, D - t, ROOF))],
            "road", color=(0.62, 0.62, 0.6))
    for p, q in (((t, t), (t, D - t)), ((t, D - t), (W - t, D - t)), ((W - t, D - t), (W - t, t)), ((W - t, t), (t, t))):
        mb.face([Vector((*p, ROOF)), Vector((*q, ROOF)), Vector((*q, PARAPET)), Vector((*p, PARAPET))], "brick",
                color=mul(brick, 0.85))
    c = 0.05
    mb.box((-c, -c, PARAPET), (W + c, t + 0.04, COPING), "concrete", color=CONC)
    mb.box((-c, D - t - 0.04, PARAPET), (W + c, D + c, COPING), "concrete", color=CONC)
    mb.box((-c, t + 0.04, PARAPET), (t + 0.04, D - t - 0.04, COPING), "concrete", color=CONC, skip="+y-y")
    mb.box((W - t - 0.04, t + 0.04, PARAPET), (W + c, D - t - 0.04, COPING), "concrete", color=CONC, skip="+y-y")
    # stair bulkhead and lift overrun
    bx0, bx1, by0, by1, bh = dc + 1.4, dc + 4.4, 5.0, 8.4, 2.8
    mb.box((bx0, by0, ROOF), (bx1, by1, ROOF + bh), "brick", color=mul(brick, 0.95), skip="-z+z")
    mb.box((bx0 - 0.05, by0 - 0.05, ROOF + bh), (bx1 + 0.05, by1 + 0.05, ROOF + bh + 0.1), "concrete", color=CONC)
    mb.box((dc - 0.8, by0 + 0.8, ROOF), (bx0, by1, ROOF + 2.0), "brick", color=mul(brick, 0.9), skip="-z+x+z")
    mb.box((dc - 0.85, by0 + 0.75, ROOF + 2.0), (bx0, by1 + 0.05, ROOF + 2.08), "concrete", color=CONC, skip="+x")
    bw = WallFace((bx0, by0), (1, 0), (0, -1), bx1 - bx0, "bulkhead")
    du = 1.6
    _wbox(mb, bw, du - 0.5, du + 0.5, ROOF, ROOF + 2.15, 0.0, 0.04, FRAME, mul(ALU, 0.8), skip="b")
    _q(mb, bw, du - 0.45, du + 0.45, ROOF, ROOF + 2.1, 0.045, "metal_painted", ER_DOOR)
    mb.cylinder(bw.at(du + 0.35, ROOF + 1.0, 0.045), bw.n * 0.06, 0.025, "chrome_dull", segments=6)
    _wbox(mb, bw, du - 0.12, du + 0.12, ROOF + 2.3, ROOF + 2.5, 0.0, 0.15, FRAME, mul(ALU, 0.8), skip="b")
    # air handlers, a boiler flue, vents, standing water
    for ax, ay, rot in ((2.4, 4.0, 0), (W - 4.8, 7.0, 0)):
        mb.box((ax - 0.05, ay - 0.05, ROOF), (ax + 2.85, ay + 1.65, ROOF + 0.25), "metal_painted", color=(0.4, 0.4, 0.38),
               skip="-z")
        body = jitter_color(rng, BEIGE, 0.08)
        mb.box((ax, ay, ROOF + 0.25), (ax + 2.8, ay + 1.6, ROOF + 1.55), "metal_painted", color=body, skip="-z")
        for k in range(6):
            zz = ROOF + 0.45 + k * 0.15
            mb.box((ax + 0.3, ay - 0.03, zz), (ax + 1.6, ay, zz + 0.05), "metal_painted", color=mul(body, 0.7), skip="+y")
        for fx in (ax + 0.75, ax + 2.05):
            mb.cylinder((fx, ay + 0.8, ROOF + 1.55), (0, 0, 0.18), 0.5, "metal_painted", segments=12, color=mul(body, 0.9),
                        caps="none")
            mb.disc((fx, ay + 0.8, ROOF + 1.6), 0.48, "interior_dark", segments=12)
            for a in (0.3, 1.87):                                      # the fan guard
                mb.obox((fx, ay + 0.8, ROOF + 1.73), (0.96, 0.03, 0.02), a, "chrome_dull")
        mb.box((ax + 2.8, ay + 0.4, ROOF), (ax + 3.5, ay + 1.2, ROOF + 1.1), "metal_painted", color=mul(body, 0.85),
               skip="-z-x")
    fx, fy = 6.8, D - 2.2
    mb.cylinder((fx, fy, ROOF), (0, 0, 3.6), 0.22, "metal_rust", segments=10, color=(0.55, 0.5, 0.46), caps="none")
    mb.cylinder((fx, fy, ROOF + 3.75), (0, 0, 0.25), 0.4, "metal_rust", segments=10, radius_top=0.05, color=(0.5, 0.46, 0.42))
    mb.disc((fx, fy, ROOF + 3.6), 0.22, "interior_dark", segments=10)
    for k in range(3):
        a = k * 2.1
        mb.tube([(fx + math.cos(a) * 0.22, fy + math.sin(a) * 0.22, ROOF + 3.4), (fx + math.cos(a) * 0.4, fy + math.sin(a) * 0.4,
                 ROOF + 3.8)], 0.015, "metal_rust", segments=3)
    for vx, vy in ((8.0, 3.2), (W - 2.5, 3.4), (4.0, D - 3.5)):
        mb.cylinder((vx, vy, ROOF), (0, 0, 0.55), 0.16, "metal_painted", segments=10, color=(0.6, 0.6, 0.58), caps="none")
        mb.cylinder((vx, vy, ROOF + 0.55), (0, 0, 0.2), 0.34, "metal_painted", segments=10, radius_top=0.08,
                    color=(0.62, 0.62, 0.6))
        mb.disc((vx, vy, ROOF + 0.55), 0.34, "interior_dark", segments=10, z_up=False)
    for vx, vy in ((dc - 0.3, D - 2.5), (bx1 + 1.5, D - 1.8), (2.0, 7.5), (W - 1.4, D - 1.0)):
        mb.cylinder((vx, vy, ROOF), (0, 0, 0.45), 0.05, "metal_painted", segments=6, color=(0.5, 0.5, 0.48), caps="top")
    for px, py, r in ((6.0, 7.0, 1.6), (W - 6.0, 10.5, 1.2), (2.0, 2.0, 0.9)):
        mb.card((px, py, ROOF + 0.004), r * 2, r * 1.5, rng.uniform(0, 3), "puddle", flat=True)
    for px, py in ((t + 0.6, t + 0.6), (W - t - 0.8, D - t - 0.8), (dc, t + 0.5)):
        mb.card((px, py, ROOF + 0.006), 1.4, 1.1, rng.uniform(0, 3), "decal_leaves", flat=True)

    # --- scuppers and downpipes -----------------------------------------------------------------------
    mb.grime = None
    _downpipe(mb, faces["front"], W - 0.3, rng, shoe_out=True)
    _downpipe(mb, faces["left"], D - 0.45, rng)
    _downpipe(mb, faces["right"], D - 0.45, rng)
    _downpipe(mb, faces["back"], 11.7, rng)
    _downpipe(mb, faces["back"], W - 0.4, rng)

    # --- the back: a roller door forced up a little, a steel door ----------------------------------------
    wf = faces["back"]
    r0_, r1_ = 6.8, 9.6
    _reveal(mb, wf, r0_, r1_, GROUND, GROUND + 3.1, 0.2, "concrete", mul(CONC, 0.85))
    _q(mb, wf, r0_, r1_, GROUND, GROUND + 0.5, -0.6, "interior_dark")
    mb.face([wf.at(r0_, GROUND + 0.002, 0.0), wf.at(r1_, GROUND + 0.002, 0.0), wf.at(r1_, GROUND + 0.002, -0.6),
             wf.at(r0_, GROUND + 0.002, -0.6)], "concrete", color=PAVING)
    sh = MeshBuilder()
    sh.rot_keys.add("roof_tin")
    _q(sh, wf, r0_ + 0.06, r1_ - 0.06, GROUND + 0.42, GROUND + 3.1, -0.16, "roof_tin", (0.62, 0.62, 0.6))
    _wbox(sh, wf, r0_ + 0.06, r1_ - 0.06, GROUND + 0.38, GROUND + 0.45, -0.17, -0.12, "metal_painted", (0.4, 0.4, 0.38))
    mb.extend(sh)
    for uu in (r0_ + 0.03, r1_ - 0.03):
        _wbox(mb, wf, uu - 0.03, uu + 0.03, GROUND, GROUND + 3.1, -0.2, -0.13, "metal_painted", (0.45, 0.45, 0.42), skip="b")
    _wbox(mb, wf, r0_ - 0.1, r1_ + 0.1, GROUND + 3.1, GROUND + 3.55, 0.0, 0.35, "metal_painted", (0.5, 0.49, 0.46), skip="b")
    d0, d1 = 10.0, 11.0
    _reveal(mb, wf, d0, d1, GROUND, GROUND + 2.15, 0.12, "concrete", mul(CONC, 0.85))
    _q(mb, wf, d0, d1, GROUND, GROUND + 2.15, -0.12, "metal_painted", mul(ER_DOOR, 1.2))
    mb.cylinder(wf.at(d1 - 0.12, GROUND + 1.0, -0.12), wf.n * 0.06, 0.025, "chrome_dull", segments=6)
    _card(mb, wf, d0 - 0.2, d1 + 0.2, PLINTH_TOP, GROUND + 1.6, 0.004, "decal_grime")

    (ox, oy), (ax_, ay_), (bx_, by_) = plan.house_frame(h)
    m = Matrix(((ax_, bx_, 0, ox), (ay_, by_, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))
    steps = (STEP[0], STEP[1], ly - 0.36)
    return mb, m, ramps, lit_points, steps
