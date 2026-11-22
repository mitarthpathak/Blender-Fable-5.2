"""Ridge Stationery & Books, 18 Ashgrove Street (lot L9): a two-storey
wood-frame shop with a flat above it, the kind every New England mill town
had on its main street, built in the house kit's style and returned in
house_kit.build_house's contract (see build_shop).

- A square false front: clapboard up past the roof, a frieze with raised
  panels, six sawn brackets and a moulded cornice. Behind it a low
  front-gable roof of rusted tin, so from the street the building reads as a
  flat-topped block.
- The shop front between two panelled pilasters: two big display windows on
  low panelled bulkheads either side of a recessed entrance with glazed
  returns, a glazed door under its own transom, and a band of milky transom
  lights over everything. Behind the glass a dim shop: display beds with a
  tiered stand of notebooks, a wire rack of exercise books, cartons and
  reams, shelving and a counter further back. The left pane is cracked and
  taped; a CLOSED card hangs in the door and a FOR SALE card leans in the
  right window.
- The fascia sign: RIDGE STATIONERY & BOOKS in raised wooden block letters on
  a faded green board between two consoles. The O has fallen off (its ghost
  is the darker paint it kept the sun off) and the Y hangs from one screw.
  A board saying BOOKS hangs square to the street from an iron bracket at
  the west corner, askew on its one good hook, so the shop reads from down
  Ashgrove.
- A striped canvas awning on a pipe frame, faded, sagging between the
  rafters and torn at the east end, where the canvas hangs off the wall rail.
- Upstairs, the flat: three sash windows to the street (curtains, a blind,
  one boarded), more on the sides and back, and its own door at the top of a
  wooden stair along the back wall, under a little shed roof.
- On the west wall, the street's approach, a painted advert for the shop,
  faded and flaking, painted board by board onto the clapboard; below it a
  gas meter and a hose bib.
- In the apron: the concrete forecourt, the step at the door, a bench under
  the left window and a newspaper box. Downpipes, grime, water streaks, a
  poster on the pilaster.

Local frame as house_kit.build_house: x along the front (0..width), y back
into the building (0 at the front wall), z up, the yard at GROUND. The street
is on -y. The main block is width x (depth - 1.4); the flat's stair stands in
the last 1.4 m of the footprint.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

from . import facade
from .core import MeshBuilder, ground_grime, jitter_color, lerp, mul
from .house_kit import (BOARD, BOARD_T, DOOR_H, DOOR_W, GROUND, NEUTRAL, WallFace, board_on_wall, chimney, clapboard,
                        front_door, paint, sash_window, wall_faces)

import plan

# --- Heights (local z; the yard is at GROUND) ------------------------------------------
APRON_Z = GROUND + 0.03            # top of the concrete apron in front
FLOOR = GROUND + 0.17              # shop floor: the step and the lobby
FF_Z = FLOOR + 3.20                # floor of the flat
EAVE_S = FF_Z + 3.03               # top of the side walls
BULK = 0.20                        # top of the bulkheads and the display beds
GLASS_HEAD = 2.30                  # head of the display windows, the lobby ceiling
TRANSOM_TOP = 2.85
HEAD_TOP = 2.98                    # top of the shop-front head beam
SIGN_TOP = 3.68
SIGN_CORN = 3.86                   # top of the small cornice over the sign
FF_SILL, FF_HEAD = 4.10, 5.50      # the flat's windows
GF_SILL_S, GF_HEAD_S = 0.85, 2.20  # back-shop windows in the side walls
FRIEZE = 7.06
CORNICE = 7.50
TOP = 7.98                         # top of the false front
# --- Plan --------------------------------------------------------------------------------
PIL = 0.32                         # corner pilasters
REC_D = 1.10                       # depth of the recessed entrance
BACK_GAP = 1.40                    # the flat's stair stands in the last 1.4 m of the footprint
ROOM_D = 3.30                      # depth of the shop seen through the glass
SLAB = 0.25                        # thickness of the false front above the side walls
PITCH = math.radians(20)
ROOF_OV = 0.30
APRON_D = 2.20                     # the apron in front of the shop (local y -2.2..0)

# Albedo divisors of the textured materials (their maps' linear means), so a vertex colour
# gives the albedo we want: trim, siding and door maps are ~0.75, fabric ~0.49, metal ~0.73.
FABRIC = 0.49
METAL = 0.73
SIGN_GREEN = (0.075, 0.11, 0.085)          # the board, sun-faded
SIGN_GREEN_KEPT = (0.035, 0.065, 0.045)    # where a letter kept the sun off it
GILT = (0.52, 0.40, 0.19)                  # the letters, faded gilt
DOOR_GREEN = (0.05, 0.10, 0.07)


def V(x, y, z):
    return Vector((x, y, z))


def _c(rgb, base=NEUTRAL):
    """Vertex colour giving a textured surface (map mean `base`) this albedo."""
    return mul(rgb, 1.0 / base)


# --- small geometry helpers ---------------------------------------------------------------

def _face_toward(mb, pts, normal, mat, colour=None, uvs=None):
    """A face with its winding chosen so that it faces `normal`."""
    pts = [Vector(p) for p in pts]
    n = Vector((0.0, 0.0, 0.0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    if n.dot(Vector(normal)) < 0:
        pts.reverse()
        if uvs:
            uvs = list(reversed(uvs))
    mb.face(pts, mat, color=colour, uvs=uvs)


def _inner_box(mb, lo, hi, mat, colour=None, skip=""):
    """A box seen from inside (a room): every face points inwards."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    P = [V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0),
         V(x0, y0, z1), V(x1, y0, z1), V(x1, y1, z1), V(x0, y1, z1)]
    faces = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
             "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
    for key, idx in faces.items():
        if key not in skip:
            mb.face([P[i] for i in reversed(idx)], mat, color=colour)


def _wall_at(p0, a, n, length, z0=0.0):
    """A WallFace whose z = 0 is at local z0 (for a door on the flat's landing)."""
    wf = WallFace(p0, a, n, length, "x")
    wf.p0 = Vector((p0[0], p0[1], z0))
    return wf


def _tube_box(mb, a, b, w, h, mat, colour=None):
    """A square timber from a to b (w wide across, h deep), its sides vertical."""
    a, b = Vector(a), Vector(b)
    d = b - a
    horiz = Vector((d.x, d.y)).length
    mb.obox((a + b) / 2, (d.length, w, h), math.atan2(d.y, d.x), mat, color=colour,
            tilt=(0.0, -math.atan2(d.z, horiz)))


def _profile(mb, wf, prof, u0, u1, mat, colour, wall=(None, None)):
    """A moulding: the (off, z) profile `prof` (from the wall, out and up, back to the
    wall) run along the wall from u0 to u1, its ends closed, and its back closed where
    it runs past the ends of the wall (wall = (u where the wall starts, where it ends))."""
    for (oa, za), (ob, zb) in zip(prof, prof[1:]):
        mb.face([wf.at(u0, za, oa), wf.at(u1, za, oa), wf.at(u1, zb, ob), wf.at(u0, zb, ob)], mat, color=colour)
    _face_toward(mb, [wf.at(u0, z, o) for o, z in prof], -wf.a, mat, mul(colour, 0.9))
    _face_toward(mb, [wf.at(u1, z, o) for o, z in prof], wf.a, mat, mul(colour, 0.9))
    zlo, zhi = prof[0][1], prof[-1][1]
    for a, b in ((u0, wall[0]), (wall[1], u1)):
        if a is not None and b is not None and b - a > 1e-3:
            _face_toward(mb, [wf.at(a, zlo, 0.0), wf.at(b, zlo, 0.0), wf.at(b, zhi, 0.0), wf.at(a, zhi, 0.0)], -wf.n,
                         mat, mul(colour, 0.7))


def _wall_card(mb, wf, u0, u1, z0, z1, off, mat, colour=None, uv=(0.0, 0.0, 1.0, 1.0)):
    """A flat card on a wall face with (part of) its texture's 0..1 square on it."""
    a, b, c, d = uv
    mb.face([wf.at(u0, z0, off), wf.at(u1, z0, off), wf.at(u1, z1, off), wf.at(u0, z1, off)], mat,
            uvs=[(a, b), (c, b), (c, d), (a, d)], color=colour)


# --- a block-letter font -----------------------------------------------------------------------
#
# Each glyph is a width (in cap heights) and centre lines of strokes in a 1-high box. A
# stroke becomes a rectangle T thick, run on by T/2 so the joints close, then clipped to
# the glyph's box so the run-on never pokes out. The same convex pieces become raised
# wooden letters (extruded) or paint (flat, laid on the clapboard rows).

T = 0.15
_C = T / 2


def _arc(cx, cy, rx, ry, a0, a1, n):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _bowl(x0, top, bottom, right, n=7):
    """A D-shaped bowl off a stem at x0, between centre lines top and bottom."""
    ry = (top - bottom) / 2
    rx = min(ry, right - x0 - 0.04)
    xs = right - rx
    return [(x0, top), (xs, top)] + _arc(xs, (top + bottom) / 2, rx, ry, 90, -90, n)[1:] + [(x0, bottom)]


def _glyph_table():
    c = _C
    g = {" ": (0.30, [])}
    g["I"] = (0.15, [[(0.075, c), (0.075, 1 - c)]])
    g["T"] = (0.60, [[(c, 1 - c), (0.60 - c, 1 - c)], [(0.30, c), (0.30, 1 - c)]])
    g["E"] = (0.52, [[(0.52 - c, 1 - c), (c, 1 - c), (c, c), (0.52 - c, c)], [(c, 0.5), (0.46 - c, 0.5)]])
    g["N"] = (0.62, [[(c, c), (c, 1 - c)], [(c + 0.02, 1 - c), (0.62 - c - 0.02, c)], [(0.62 - c, c), (0.62 - c, 1 - c)]])
    g["A"] = (0.66, [[(c, c), (0.33, 1 - c)], [(0.33, 1 - c), (0.66 - c, c)], [(0.17, 0.32), (0.49, 0.32)]])
    g["Y"] = (0.64, [[(c, 1 - c), (0.32, 0.47)], [(0.64 - c, 1 - c), (0.32, 0.47)], [(0.32, 0.50), (0.32, c)]])
    g["K"] = (0.60, [[(c, c), (c, 1 - c)], [(0.60 - c, 1 - c), (c + 0.03, 0.40)], [(0.24, 0.56), (0.60 - c, c)]])
    g["O"] = (0.66, [_arc(0.33, 0.5, 0.33 - c, 0.5 - c, 0, 360, 14)])
    g["G"] = (0.64, [_arc(0.32, 0.5, 0.32 - c, 0.5 - c, 42, 360, 12), [(0.64 - c - 0.0, 0.44), (0.36, 0.44)]])
    g["D"] = (0.62, [[(c, c), (c, 1 - c)], _bowl(c, 1 - c, c, 0.62 - c)])
    g["P"] = (0.58, [[(c, c), (c, 1 - c)], _bowl(c, 1 - c, 0.45, 0.58 - c, 6)])
    g["R"] = (0.60, [[(c, c), (c, 1 - c)], _bowl(c, 1 - c, 0.45, 0.58 - c, 6), [(0.30, 0.45), (0.60 - c, c)]])
    g["B"] = (0.60, [[(c, c), (c, 1 - c)], _bowl(c, 1 - c, 0.51, 0.56 - c, 6), _bowl(c, 0.51, c, 0.60 - c, 6)])
    g["S"] = (0.58, [_arc(0.29, 0.7125, 0.29 - c, 0.2125, 25, 270, 9) + _arc(0.29, 0.2875, 0.29 - c, 0.2125, 90, -155, 9)[1:]])
    amp = ([(0.61, 0.075)] + _arc(0.31, 0.765, 0.125, 0.16, 225, -45, 8) + _arc(0.27, 0.255, 0.195, 0.18, 140, 395, 9)
           + [(0.58, 0.47)])
    g["&"] = (0.66, [amp])
    g["."] = (0.22, [[(0.11, 0.49), (0.11, 0.51)]])        # the dot between words
    return g


GLYPHS = _glyph_table()


def _clip(poly, axis, lo, hi):
    """Sutherland-Hodgman: the part of a convex polygon with lo <= coordinate <= hi."""
    def half(pts, inside, edge):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            pin, qin = inside(p), inside(q)
            if pin:
                out.append(p)
            if pin != qin:
                t = (edge - p[axis]) / (q[axis] - p[axis])
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out
    pts = half(poly, lambda p: p[axis] >= lo - 1e-9, lo)
    if pts:
        pts = half(pts, lambda p: p[axis] <= hi + 1e-9, hi)
    clean = []
    for p in pts:                                    # drop near-duplicates (they would weld into slivers)
        if not clean or (abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1])) > 2e-3:
            clean.append(p)
    if len(clean) > 1 and (abs(clean[0][0] - clean[-1][0]) + abs(clean[0][1] - clean[-1][1])) <= 2e-3:
        clean.pop()
    return clean


def _area(poly):
    return 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))


def _stroke(p, q, t):
    d = Vector((q[0] - p[0], q[1] - p[1]))
    d.normalize()
    n = Vector((-d.y, d.x))
    a, b = Vector(p) - d * t / 2, Vector(q) + d * t / 2
    return [tuple(a - n * t / 2), tuple(b - n * t / 2), tuple(b + n * t / 2), tuple(a + n * t / 2)]


def text_layout(text, u_centre, z_base, height, gap=0.13):
    """The strokes of `text` as convex polygons in wall coordinates (u, z), centred on
    u_centre. Returns [(char, u_left, width, [polygon, ...]), ...] per character."""
    total = sum(GLYPHS[ch][0] for ch in text) + gap * (len(text) - 1)
    x = u_centre - total * height / 2
    out = []
    for ch in text:
        w, lines = GLYPHS[ch]
        polys = []
        for line in lines:
            for p, q in zip(line, line[1:]):
                if abs(p[0] - q[0]) + abs(p[1] - q[1]) < 1e-6:
                    continue
                r = _clip(_clip(_stroke(p, q, T), 0, 0.0, w), 1, 0.0, 1.0)
                if len(r) >= 3 and _area(r) > 1e-5:
                    polys.append([(x + px * height, z_base + py * height) for px, py in r])
        out.append((ch, x, w * height, polys))
        x += (w + gap) * height
    return out


def text_width(text, height, gap=0.13):
    return (sum(GLYPHS[ch][0] for ch in text) + gap * (len(text) - 1)) * height


def _overlap(p, q):
    """Do two convex polygons overlap (separating-axis test)?"""
    for poly in (p, q):
        for i in range(len(poly)):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = by - ay, ax - bx
            pa = [nx * x + ny * y for x, y in p]
            qa = [nx * x + ny * y for x, y in q]
            if max(pa) <= min(qa) + 1e-9 or max(qa) <= min(pa) + 1e-9:
                return False
    return True


def depth_levels(polys):
    """A small integer per polygon such that overlapping polygons never share one.
    Coplanar overlapping faces shadow each other in Cycles (each one's shadow rays
    start on the other's plane) and fight in a depth buffer; stepping them a
    millimetre apart by level cures both."""
    boxes = [(min(u for u, _ in p), min(z for _, z in p), max(u for u, _ in p), max(z for _, z in p)) for p in polys]
    levels = []
    for i, p in enumerate(polys):
        used = set()
        bi = boxes[i]
        for j in range(i):
            bj = boxes[j]
            if bi[0] < bj[2] and bj[0] < bi[2] and bi[1] < bj[3] and bj[1] < bi[3] and _overlap(p, polys[j]):
                used.add(levels[j])
        k = 0
        while k in used:
            k += 1
        levels.append(k)
    return levels


def _rotate(poly, pivot, angle):
    c, s = math.cos(angle), math.sin(angle)
    return [(pivot[0] + (u - pivot[0]) * c - (z - pivot[1]) * s, pivot[1] + (u - pivot[0]) * s + (z - pivot[1]) * c)
            for u, z in poly]


def _raised(mb, wf, poly, off0, off1, mat, colour):
    """A convex polygon (u, z) extruded out of a wall face from off0 to off1."""
    mb.face([wf.at(u, z, off1) for u, z in poly], mat, color=colour)
    side = mul(colour, 0.85)
    for (ua, za), (ub, zb) in zip(poly, poly[1:] + poly[:1]):
        mb.face([wf.at(ua, za, off0), wf.at(ub, zb, off0), wf.at(ub, zb, off1), wf.at(ua, za, off1)], mat, color=side)


def _paint_on_boards(mb, wf, poly, z0, colour, eps):
    """A flat convex polygon (u, z) painted onto clapboard rows that start at z0: cut
    row by row and laid on each board's slope, with the board's own UVs, so the paint
    follows the boards and the grain runs through it."""
    zs = [z for _, z in poly]
    k0, k1 = int(math.floor((min(zs) - z0) / BOARD)), int(math.floor((max(zs) - z0) / BOARD))
    for k in range(k0, k1 + 1):
        r0 = z0 + k * BOARD
        r1 = r0 + BOARD
        piece = _clip(poly, 1, r0, r1)
        if len(piece) < 3 or abs(_area(piece)) < 2e-5:
            continue
        pts = [wf.at(u, z, BOARD_T * (r1 - z) / BOARD + eps) for u, z in piece]
        uvs = [(u / 2.4, k * 0.1 + (z - r0) / BOARD * 0.1) for u, z in piece]
        mb.face(pts, "siding", uvs=uvs, color=colour)


# --- windows --------------------------------------------------------------------------------------

_STYLES = ("curtains", "curtains", "blind", "blind", "bare", "sheet")


def _rng_for(style, seed):
    """A random stream whose first draws make facade.window_inside dress a window in
    `style` (it draws a fabric, then a style), so the street side can be chosen."""
    for s in range(seed, seed + 400):
        r = random.Random(s)
        r.randrange(len(facade.FABRICS))
        if r.choice(_STYLES) == style:
            return random.Random(s)
    return random.Random(seed)


def _window(mb, wf, o, trim, wear, rng, lit):
    u0, u1, sill, head, kind, state = o[:6]
    if state in ("curtains", "blind", "sheet", "bare"):
        sash_window(mb, wf, u0, u1 - u0, sill, head, trim, "ok", _rng_for(state, rng.randrange(10000)), lit, wear=wear)
    else:
        sash_window(mb, wf, u0, u1 - u0, sill, head, trim, state, rng, lit, wear=wear)


def _openings(W, D, door_at):
    """Openings per wall: (u0, u1, zb, zt, kind, state). u runs as in house_kit.wall_faces:
    front from the west corner, right (east) from the front, back from the east corner,
    left (west) from the back."""
    ops = {"front": [], "right": [], "back": [], "left": []}
    for u, st in ((1.0, "curtains"), (3.7, "blind"), (6.4, "boarded")):
        ops["front"].append((u, u + 1.0, FF_SILL, FF_HEAD, "win", st))
    ops["left"] += [(0.7, 1.6, FF_SILL, FF_HEAD, "win", "sheet"), (2.3, 3.2, FF_SILL, FF_HEAD, "win", "broken"),
                    (1.2, 2.1, GF_SILL_S, GF_HEAD_S, "win", "boarded")]
    ops["right"] += [(2.0, 2.9, FF_SILL, FF_HEAD, "win", "blind"), (5.6, 6.5, FF_SILL, FF_HEAD, "win", "curtains"),
                     (5.9, 6.8, GF_SILL_S, GF_HEAD_S, "win", "boarded")]
    ops["back"] += [(3.8, 4.8, FF_SILL, FF_HEAD, "win", "bare"), (6.4, 7.4, FF_SILL, FF_HEAD, "win", "curtains"),
                    (0.38, 0.38 + DOOR_W, FF_Z, FF_Z + DOOR_H, "door", "flat"),
                    (6.70, 6.70 + DOOR_W, FLOOR, FLOOR + DOOR_H, "door", "shop")]
    return ops


def _cuts(o):
    """The clapboard cut-out round an opening, as house_kit does it."""
    if o[4] == "win":
        return (o[0] - 0.10, o[1] + 0.10, o[2] - 0.20, o[3] + 0.13)
    return (o[0] - 0.11, o[1] + 0.11, o[2] - 0.02, o[3] + 0.14)


# --- the builder ------------------------------------------------------------------------------------

def build_shop(lot, rng: random.Random):
    """Ridge Stationery & Books with the flat above. Returns (MeshBuilder in the local
    frame, local->world matrix, step ramps, lit-window light points, path start),
    exactly as house_kit.build_house."""
    h = lot.house
    W, DEPTH = h.width, h.depth
    D = DEPTH - BACK_GAP
    wear = h.wear
    siding = paint(h.paint)
    trim = paint(h.trim)
    rx0, rx1 = h.door_at - 0.45, h.door_at + DOOR_W + 0.45          # the recessed entrance
    mb = MeshBuilder()
    faces = wall_faces(W, D)
    ops = _openings(W, D, h.door_at)
    lit_points: list = []
    ramps: list = []

    mb.grime = ground_grime(GROUND, 1.2, 0.30 + 0.35 * wear)
    _walls(mb, faces, ops, W, D, siding, trim, wear, rng, lit_points)
    _shopfront(mb, faces["front"], W, rx0, rx1, h.door_at, trim, siding, wear, rng)
    _false_front(mb, faces, W, D, trim, siding, rng)
    _advert(mb, faces["left"], D, siding, random.Random(rng.randrange(10000)))
    _gas_meter(mb, faces["left"], D)
    mb.grime = ground_grime(GROUND, 1.0, 0.2)
    _sign(mb, faces["front"], W, trim, random.Random(rng.randrange(10000)))
    _blade_sign(mb, trim, random.Random(rng.randrange(10000)))
    _roof(mb, W, D, trim, rng)
    _back_stair(mb, faces, W, D, trim, wear, rng)
    mb.grime = None
    _interior(mb, W, rx0, rx1, h.door_at, random.Random(rng.randrange(10000)))
    _awning(mb, W, random.Random(rng.randrange(10000)))
    mb.grime = ground_grime(GROUND, 0.5, 0.25)
    _apron(mb, W, rx0, rx1, trim, random.Random(rng.randrange(10000)))
    mb.grime = None
    _stains(mb, faces, ops, W, D, rng, wear)

    # the step into the lobby: a wedge from the apron up to the step's nose
    ramps.append(((rx0 - 0.12, -0.40 - 0.50, APRON_Z), (rx1 + 0.12, -0.40, FLOOR)))
    steps = (h.door_at - 0.35, h.door_at + DOOR_W + 0.35, -APRON_D)
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    m = Matrix(((ax, bx, 0, ox), (ay, by, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))
    return mb, m, ramps, lit_points, steps


# --- walls --------------------------------------------------------------------------------------------

def _walls(mb, faces, ops, W, D, siding, trim, wear, rng, lit):
    tp = math.tan(PITCH)
    for key, wf in faces.items():
        cuts = [_cuts(o) for o in ops[key]]
        if key == "front":
            clapboard(mb, wf, cuts, SIGN_CORN, FRIEZE, siding, rng, wear)
            for u0, u1 in ((0.0, 0.14), (W - 0.14, W)):
                board_on_wall(mb, wf, u0, u1, SIGN_CORN, FRIEZE, 0.035, "trim", trim, BOARD_T)
        else:
            clapboard(mb, wf, cuts, FLOOR + 0.18, EAVE_S, siding, rng, wear)
            if key == "back":
                clapboard(mb, wf, [], EAVE_S, EAVE_S + W / 2 * tp + 0.05, siding, rng, wear, gable=(EAVE_S, tp))
            # water table, frieze under the eaves, foundation proud of the siding
            board_on_wall(mb, wf, 0.0, wf.length, FLOOR, FLOOR + 0.18, 0.03, "trim", mul(trim, 0.85))
            board_on_wall(mb, wf, 0.0, wf.length, EAVE_S - 0.22, EAVE_S, 0.03, "trim", trim, BOARD_T)
            facade.wbox(mb, wf, -0.05 if key != "right" else 0.0, wf.length + (0.05 if key != "left" else 0.0),
                        GROUND - 0.08, FLOOR + 0.02, 0.0, 0.05, "concrete", (0.62, 0.6, 0.56), skip=("back", "floor"))
            # corner boards (at the front corners they run up the end of the false front)
            for u0, u1 in ((0.0, 0.12), (wf.length - 0.12, wf.length)):
                front_corner = (key == "left" and u0 > 0) or (key == "right" and u0 == 0.0)
                if front_corner:
                    a, b = (wf.length - SLAB - 0.02, wf.length) if key == "left" else (0.0, SLAB + 0.02)
                    board_on_wall(mb, wf, a, b, FLOOR, EAVE_S, 0.035, "trim", trim, BOARD_T)
                    board_on_wall(mb, wf, a, b, EAVE_S, TOP, 0.035 + BOARD_T, "trim", trim)   # closes the false front's end
                else:
                    board_on_wall(mb, wf, u0, u1, FLOOR, EAVE_S, 0.035, "trim", trim, BOARD_T)
        for o in ops[key]:
            if o[4] == "win":
                _window(mb, wf, o, trim, wear, rng, lit)
    # the doors at the back: the flat's at the top of the stair, the shop's at the ground, boarded
    door_col = _c(DOOR_GREEN)
    for o in ops["back"]:
        if o[4] != "door":
            continue
        z0 = FF_Z + 0.01 if o[5] == "flat" else FLOOR
        wf = _wall_at((W, D), (-1, 0), (0, 1), W, z0)
        front_door(mb, wf, o[0], trim, door_col if o[5] == "flat" else mul(door_col, 0.8), screen=o[5] == "flat")
        if o[5] == "shop":
            mb.box((W - o[1] - 0.15, D + 0.05, GROUND - 0.02), (W - o[0] + 0.15, D + 0.45, FLOOR - 0.012), "concrete",
                   skip="-z", color=(0.66, 0.64, 0.6))
            for k, (dz, tilt) in enumerate(((0.55, 0.03), (1.45, -0.04))):
                mb.obox((W - (o[0] + o[1]) / 2, D + 0.14, FLOOR + dz), (DOOR_W + 0.3, 0.02, 0.9), 0.0, "plywood",
                        color=jitter_color(rng, (0.82, 0.76, 0.66), 0.08), tilt=(0.0, tilt))


# --- the shop front --------------------------------------------------------------------------------

def _panel(mb, wf, u0, u1, z0, z1, off, colour, frame_col):
    """A raised panel in a moulded frame on a flat surface at `off`."""
    m = 0.045
    for a, b, c, d in ((u0, u1, z0, z0 + m), (u0, u1, z1 - m, z1), (u0, u0 + m, z0 + m, z1 - m), (u1 - m, u1, z0 + m, z1 - m)):
        board_on_wall(mb, wf, a, b, c, d, 0.018, "trim", frame_col, off)
    board_on_wall(mb, wf, u0 + m + 0.03, u1 - m - 0.03, z0 + m + 0.03, z1 - m - 0.03, 0.010, "trim", colour, off)


def _glazed_frame(mb, wf, a, b, trim, glass="window_glass"):
    """Stiles, rails and the plate glass of one display window between u a and b."""
    st = 0.09
    board_on_wall(mb, wf, a, a + st, BULK + 0.06, GLASS_HEAD, 0.08, "trim", trim, -0.05)
    board_on_wall(mb, wf, b - st, b, BULK + 0.06, GLASS_HEAD, 0.08, "trim", trim, -0.05)
    board_on_wall(mb, wf, a + st, b - st, GLASS_HEAD - 0.08, GLASS_HEAD, 0.08, "trim", trim, -0.05)
    board_on_wall(mb, wf, a + st, b - st, BULK + 0.06, BULK + 0.12, 0.06, "trim", mul(trim, 0.9), -0.05)
    facade.wquad(mb, wf, a + st, b - st, BULK + 0.12, GLASS_HEAD - 0.08, -0.02, glass)
    return a + st, b - st


def _shopfront(mb, wf, W, rx0, rx1, door_at, trim, siding, wear, rng):
    bulk_col = mul(siding, 0.85)
    # pilasters: shaft, a raised panel, plinth and capital
    for ua in (0.0, W - PIL):
        ub = ua + PIL
        facade.wbox(mb, wf, ua, ub, GROUND - 0.02, 2.66, 0.0, 0.06, "trim", trim, skip=("back", "floor"))
        board_on_wall(mb, wf, ua + 0.06, ub - 0.06, 0.40, 2.45, 0.012, "trim", mul(trim, 1.04), 0.06)
        board_on_wall(mb, wf, ua - (0.02 if ua > 0 else 0.0), ub + (0.02 if ua == 0 else 0.0), GROUND - 0.02, 0.24, 0.10,
                      "trim", mul(trim, 0.8))
        board_on_wall(mb, wf, ua, ub, 2.62, 2.86, 0.10, "trim", trim)
        board_on_wall(mb, wf, ua, ub, 2.58, 2.62, 0.08, "trim", mul(trim, 0.9))
    # head beam over the whole front, with a drip
    board_on_wall(mb, wf, -0.03, W + 0.03, 2.85, HEAD_TOP, 0.09, "trim", trim)
    board_on_wall(mb, wf, -0.04, W + 0.04, 2.83, 2.86, 0.11, "trim", mul(trim, 0.9))
    # the two display windows on their bulkheads
    spans = ((PIL, rx0), (rx1, W - PIL))
    panes = []
    for a, b in spans:
        facade.wbox(mb, wf, a, b, APRON_Z - 0.03, BULK, -0.12, 0.0, "trim", bulk_col, skip=("back", "floor"))
        board_on_wall(mb, wf, a, b, APRON_Z - 0.03, APRON_Z + 0.09, 0.015, "trim", mul(trim, 0.55))   # scuffed kick
        n = 2
        pw = (b - a - 0.16) / n
        for i in range(n):
            pu = a + 0.08 + i * pw
            _panel(mb, wf, pu + 0.03, pu + pw - 0.03, APRON_Z + 0.13, BULK - 0.05, 0.0, mul(bulk_col, 1.05), trim)
        board_on_wall(mb, wf, a - 0.01, b + 0.01, BULK, BULK + 0.06, 0.13, "trim", mul(trim, 0.9), -0.06)   # sill
        panes.append(_glazed_frame(mb, wf, a, b, trim))
    # transom: a bar over the windows and the entrance, milky lights above it
    board_on_wall(mb, wf, PIL, W - PIL, GLASS_HEAD, GLASS_HEAD + 0.08, 0.10, "trim", trim, -0.06)
    board_on_wall(mb, wf, PIL, W - PIL, TRANSOM_TOP - 0.05, TRANSOM_TOP, 0.07, "trim", trim, -0.05)
    n = 14
    for i in range(n + 1):
        u = PIL + (W - 2 * PIL) * i / n
        board_on_wall(mb, wf, max(PIL, u - 0.025), min(W - PIL, u + 0.025), GLASS_HEAD + 0.08, TRANSOM_TOP - 0.05, 0.06,
                      "trim", trim, -0.04)
    for i in range(n):
        ua = PIL + (W - 2 * PIL) * i / n + 0.025
        ub = PIL + (W - 2 * PIL) * (i + 1) / n - 0.025
        broken = i == 11
        if not broken:
            facade.wquad(mb, wf, ua, ub, GLASS_HEAD + 0.08, TRANSOM_TOP - 0.05, -0.02, "glass_dirty",
                         jitter_color(rng, (0.85, 0.85, 0.8), 0.06))
        else:                                                     # a light knocked out: the dark behind
            facade.wquad(mb, wf, ua, ub, GLASS_HEAD + 0.08, TRANSOM_TOP - 0.05, -0.20, "interior_dark")
    # the cracked pane (left window), taped across
    pa, pb = panes[0]
    cu, cz, s = pb - 0.7, 1.3, 0.9
    u0c, z0c = cu - 0.42 * s, cz - 0.54 * s
    u1c = min(pb - 0.01, u0c + s)
    _wall_card(mb, wf, u0c, u1c, z0c, z0c + s, -0.018, "glass_crack", (0.30, 0.32, 0.32),
               uv=(0.0, 0.0, (u1c - u0c) / s, 1.0))
    tape = _c((0.50, 0.44, 0.30))
    for k, (ang, ln) in enumerate(((0.72, 0.24), (-0.62, 0.21))):
        d = Vector((math.cos(ang), math.sin(ang)))
        nn = Vector((-d.y, d.x)) * 0.02
        a0, a1 = Vector((cu, cz)) - d * ln, Vector((cu, cz)) + d * ln
        o = -0.016 + 0.0015 * k
        mb.face([wf.at(*(a0 - nn), o), wf.at(*(a1 - nn), o), wf.at(*(a1 + nn), o), wf.at(*(a0 + nn), o)], "trim", color=tape)

    # --- the recessed entrance -------------------------------------------------------------------
    stone = (0.74, 0.72, 0.67)
    mb.box((rx0 - 0.12, -0.40, APRON_Z - 0.02), (rx1 + 0.12, 0.0, FLOOR), "concrete", skip="-z+y", color=stone)
    mb.face([V(rx0, 0.0, FLOOR), V(rx1, 0.0, FLOOR), V(rx1, REC_D, FLOOR), V(rx0, REC_D, FLOOR)], "concrete",
            color=mul(stone, 0.92))
    _face_toward(mb, [V(rx0, 0.0, GLASS_HEAD), V(rx1, 0.0, GLASS_HEAD), V(rx1, REC_D, GLASS_HEAD), V(rx0, REC_D, GLASS_HEAD)],
                 (0, 0, -1), "trim", mul(trim, 0.7))
    _face_toward(mb, [V(rx0, 0.0, GLASS_HEAD + 0.02), V(rx1, 0.0, GLASS_HEAD + 0.02), V(rx1, REC_D, GLASS_HEAD + 0.02),
                      V(rx0, REC_D, GLASS_HEAD + 0.02)], (0, 0, 1), "interior_dark")
    # glazed returns on low bulkheads, left and right of the lobby (u runs front to back on
    # the left one, back to front on the right one; their front ends die into the bulkheads)
    for wr, front_end, (sa, sb), (ga, gb) in (
            (WallFace((rx0, 0.0), (0, 1), (1, 0), REC_D, "lr"), "left", (REC_D - 0.09, REC_D), (0.0, REC_D - 0.09)),
            (WallFace((rx1, REC_D), (0, -1), (-1, 0), REC_D, "rr"), "right", (0.0, 0.09), (0.09, REC_D))):
        facade.wbox(mb, wr, 0.0, REC_D, FLOOR, BULK, -0.10, 0.0, "trim", bulk_col, skip=("back", "floor", front_end))
        board_on_wall(mb, wr, 0.0, REC_D, FLOOR, FLOOR + 0.09, 0.015, "trim", mul(trim, 0.55))
        _panel(mb, wr, 0.12, REC_D - 0.12, FLOOR + 0.12, BULK - 0.05, 0.0, mul(bulk_col, 1.05), trim)
        board_on_wall(mb, wr, 0.0, REC_D, BULK, BULK + 0.06, 0.12, "trim", mul(trim, 0.9), -0.06)
        board_on_wall(mb, wr, sa, sb, BULK + 0.06, GLASS_HEAD, 0.08, "trim", trim, -0.05)
        board_on_wall(mb, wr, ga, gb, GLASS_HEAD - 0.08, GLASS_HEAD, 0.08, "trim", trim, -0.05)
        board_on_wall(mb, wr, ga, gb, BULK + 0.06, BULK + 0.12, 0.06, "trim", mul(trim, 0.9), -0.05)
        facade.wquad(mb, wr, ga, gb, BULK + 0.12, GLASS_HEAD - 0.08, -0.02, "window_glass")
    # the door wall at the back of the lobby: panelled sides, the glazed door, its transom
    dw = WallFace((0.0, REC_D), (1, 0), (0, -1), W, "door")
    d0, d1 = door_at, door_at + DOOR_W
    door_col = _c(DOOR_GREEN)
    for a, b in ((rx0, d0 - 0.08), (d1 + 0.08, rx1)):
        facade.wbox(mb, dw, a, b, FLOOR, GLASS_HEAD, -0.10, 0.0, "trim", mul(trim, 0.95), skip=("back", "floor"))
        _panel(mb, dw, a + 0.06, b - 0.06, FLOOR + 0.15, 0.95, 0.0, mul(trim, 1.0), mul(trim, 0.9))
        _panel(mb, dw, a + 0.06, b - 0.06, 1.05, GLASS_HEAD - 0.12, 0.0, mul(trim, 1.0), mul(trim, 0.9))
    for a, b in ((d0 - 0.08, d0), (d1, d1 + 0.08)):
        board_on_wall(mb, dw, a, b, FLOOR, GLASS_HEAD, 0.06, "trim", trim, -0.02)
    top = FLOOR + DOOR_H
    board_on_wall(mb, dw, d0, d1, top, top + 0.08, 0.06, "trim", trim, -0.02)
    facade.wquad(mb, dw, d0, d1, top + 0.08, GLASS_HEAD, -0.03, "window_glass")
    facade.wquad(mb, dw, d0, d1, top + 0.08, GLASS_HEAD, -0.30, "interior_dark")
    # the leaf: stiles, rails, a lower panel, glass over the lock rail
    inset = -0.055
    for a, b, c, e in ((d0, d0 + 0.12, FLOOR, top), (d1 - 0.12, d1, FLOOR, top), (d0 + 0.12, d1 - 0.12, FLOOR, FLOOR + 0.24),
                       (d0 + 0.12, d1 - 0.12, FLOOR + 0.70, FLOOR + 0.86), (d0 + 0.12, d1 - 0.12, top - 0.12, top)):
        board_on_wall(mb, dw, a, b, c, e, 0.045, "door", door_col, inset)
    board_on_wall(mb, dw, d0 + 0.12, d1 - 0.12, FLOOR + 0.24, FLOOR + 0.70, 0.02, "door", mul(door_col, 0.95), inset)
    board_on_wall(mb, dw, d0 + 0.2, d1 - 0.2, FLOOR + 0.31, FLOOR + 0.63, 0.012, "door", mul(door_col, 1.1), inset + 0.02)
    facade.wquad(mb, dw, d0 + 0.12, d1 - 0.12, FLOOR + 0.86, top - 0.12, inset + 0.02, "window_glass")
    facade.wquad(mb, dw, d0 + 0.04, d1 - 0.04, FLOOR + 0.03, FLOOR + 0.22, inset + 0.0465, "chrome_dull")   # kick plate
    facade.wbox(mb, dw, d0 + 0.30, d1 - 0.30, FLOOR + 0.76, FLOOR + 0.80, inset + 0.045, inset + 0.052, "chrome_dull")
    hu = d1 - 0.07
    mb.cylinder(dw.at(hu, FLOOR + 0.90, inset + 0.045), (0, -0.05, 0), 0.01, "chrome_dull", segments=6)
    mb.cylinder(dw.at(hu, FLOOR + 1.18, inset + 0.045), (0, -0.05, 0), 0.01, "chrome_dull", segments=6)
    mb.cylinder(dw.at(hu, FLOOR + 0.88, inset + 0.095), (0, 0, 0.32), 0.014, "chrome_dull", segments=6)      # the pull
    # the CLOSED card hanging inside the glass on a string
    cz = FLOOR + 1.42
    cuc = (d0 + d1) / 2
    _wall_card(mb, dw, cuc - 0.2, cuc + 0.2, cz, cz + 0.09, inset - 0.03, "sign_closed_store",
               uv=(0.04, 0.80, 0.96, 0.955))
    hook = dw.at(cuc, cz + 0.30, inset - 0.025)
    for du in (-0.18, 0.18):
        mb.tube([dw.at(cuc + du, cz + 0.085, inset - 0.03), hook], 0.0025, "wire", segments=3)
    mb.cylinder(hook, (0, 0.012, 0), 0.012, "chrome_dull", segments=6)
    # behind the door glass the dark shop (the room box closes it)
    # a newspaper bundle nobody took in, on the lobby floor
    for k in range(3):
        mb.obox((rx1 - 0.35 + rng.uniform(-0.05, 0.05), 0.55 + rng.uniform(-0.1, 0.1), FLOOR + 0.03 + 0.04 * k),
                (0.32, 0.24, 0.04), rng.uniform(-0.4, 0.4), "trim", color=_c((0.55, 0.53, 0.48)))
    for u, z in ((rx0 + 0.25, 0.35), (rx1 - 0.6, 0.2)):
        mb.card((u, 0.6 + z, FLOOR + 0.003), 0.7, 0.6, rng.uniform(0, 3), "decal_leaves", flat=True)
    # posters: a missing cat on the west pilaster, the town meeting inside the right window
    pu = PIL / 2
    mb.face([wf.at(pu - 0.11, 1.30, 0.0735), wf.at(pu + 0.11, 1.31, 0.0735), wf.at(pu + 0.105, 1.60, 0.0735),
             wf.at(pu - 0.115, 1.59, 0.0735)], "poster_missing", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pa, pb = panes[1]
    _wall_card(mb, wf, pa + 0.15, pa + 0.45, 1.30, 1.70, -0.026, "poster_meeting")


# --- the false front, cornice and sign ----------------------------------------------------------------

def _false_front(mb, faces, W, D, trim, siding, rng):
    wf = faces["front"]
    # frieze with raised panels between six sawn brackets
    board_on_wall(mb, wf, -0.04, W + 0.04, FRIEZE, CORNICE, 0.04, "trim", trim)
    n = 6
    us = [0.16 + (W - 0.32) * i / (n - 1) for i in range(n)]
    for u0, u1 in zip(us, us[1:]):
        board_on_wall(mb, wf, u0 + 0.16, u1 - 0.16, FRIEZE + 0.08, CORNICE - 0.07, 0.015, "trim", mul(trim, 1.05), 0.04)
    br = [(0.0, FRIEZE + 0.06), (0.07, FRIEZE + 0.06), (0.30, CORNICE + 0.13), (0.0, CORNICE + 0.06)]
    for u in us:
        bmb = [(o + 0.04, z) for o, z in br]
        _raised_profile(mb, wf, bmb, u - 0.05, u + 0.05, "trim", trim)
        mb.obox(wf.at(u, FRIEZE + 0.02, 0.09), (0.07, 0.07, 0.08), 0.0, "trim", color=trim)         # drop
    # the cornice
    prof = [(0.0, CORNICE), (0.09, CORNICE), (0.09, CORNICE + 0.07), (0.34, CORNICE + 0.15), (0.34, CORNICE + 0.34),
            (0.39, CORNICE + 0.36), (0.39, TOP), (0.0, TOP)]
    _profile(mb, wf, prof, -0.12, W + 0.12, "trim", trim, wall=(0.0, W))
    _face_toward(mb, [V(0, 0, TOP), V(W, 0, TOP), V(W, SLAB, TOP), V(0, SLAB, TOP)], (0, 0, 1), "metal_painted",
                 _c((0.32, 0.31, 0.29), METAL))
    # the back of the false front, over the roof: bare boards, never painted
    _face_toward(mb, [V(0, SLAB, EAVE_S), V(W, SLAB, EAVE_S), V(W, SLAB, TOP), V(0, SLAB, TOP)], (0, 1, 0),
                 "siding", _c((0.30, 0.28, 0.25), 0.74))
    for x in range(1, 5):                                   # its braces down to the roof
        xx = W * x / 5
        _tube_box(mb, (xx, SLAB + 0.05, TOP - 0.3), (xx, SLAB + 1.4, EAVE_S + (min(xx, W - xx)) * math.tan(PITCH) + 0.12),
                  0.06, 0.09, "wood_weathered", (0.7, 0.66, 0.6))
    # small cornice over the sign
    sprof = [(0.0, SIGN_TOP), (0.06, SIGN_TOP), (0.06, SIGN_TOP + 0.04), (0.14, SIGN_TOP + 0.10), (0.14, SIGN_CORN - 0.03),
             (0.17, SIGN_CORN - 0.02), (0.17, SIGN_CORN), (0.0, SIGN_CORN)]
    _profile(mb, wf, sprof, -0.10, W + 0.10, "trim", trim, wall=(0.0, W))
    _face_toward(mb, [wf.at(-0.10, SIGN_CORN + 0.005, 0.17), wf.at(W + 0.10, SIGN_CORN + 0.005, 0.17),
                      wf.at(W + 0.10, SIGN_CORN + 0.005, 0.0), wf.at(-0.10, SIGN_CORN + 0.005, 0.0)], (0, 0, 1),
                 "metal_painted", _c((0.30, 0.29, 0.27), METAL))
    # the service drop comes in here: weatherhead, insulator, conduit down to the wall
    u = 2.85
    grey = _c((0.42, 0.42, 0.40), METAL)
    mb.tube([wf.at(u, SIGN_CORN + 0.06, 0.075), wf.at(u, 5.55, 0.075)], 0.022, "metal_painted", segments=6, color=grey)
    head = wf.at(u, 5.55, 0.075)
    mb.tube([head, head + Vector((0, 0, 0.08)) + wf.n * 0.06], 0.04, "metal_painted", segments=6, color=mul(grey, 0.8))
    for k in (-1, 1):
        mb.tube([head + wf.a * 0.03 * k + Vector((0, 0, 0.06)), head + wf.a * 0.14 * k + Vector((0, 0, -0.10)) + wf.n * 0.12],
                0.006, "wire", segments=3)
    mb.box((u + 0.15, -0.10, 5.62), (u + 0.21, 0.0, 5.66), "metal_painted", color=grey)
    mb.cylinder(V(u + 0.18, -0.08, 5.66), (0, 0, 0.07), 0.035, "glass_dirty", segments=8, color=(0.6, 0.7, 0.65))
    facade.wbox(mb, wf, u - 0.05, u + 0.05, SIGN_CORN + 0.02, SIGN_CORN + 0.12, BOARD_T, 0.11, "metal_painted", grey)


def _raised_profile(mb, wf, prof, u0, u1, mat, colour):
    """A convex (off, z) profile extruded along the wall from u0 to u1 (a bracket)."""
    for (oa, za), (ob, zb) in zip(prof, prof[1:] + prof[:1]):
        mb.face([wf.at(u0, za, oa), wf.at(u1, za, oa), wf.at(u1, zb, ob), wf.at(u0, zb, ob)], mat, color=colour)
    _face_toward(mb, [wf.at(u0, z, o) for o, z in prof], -wf.a, mat, mul(colour, 0.9))
    _face_toward(mb, [wf.at(u1, z, o) for o, z in prof], wf.a, mat, mul(colour, 0.9))


def _sign(mb, wf, W, trim, rng):
    """RIDGE STATIONERY & BOOKS in raised letters on the fascia board, between consoles."""
    board = _c(SIGN_GREEN)
    board_on_wall(mb, wf, 0.26, W - 0.26, HEAD_TOP, SIGN_TOP, 0.05, "door", board)
    for a, b, c, d in ((0.26, W - 0.26, HEAD_TOP, HEAD_TOP + 0.05), (0.26, W - 0.26, SIGN_TOP - 0.05, SIGN_TOP),
                       (0.26, 0.31, HEAD_TOP + 0.05, SIGN_TOP - 0.05), (W - 0.31, W - 0.26, HEAD_TOP + 0.05, SIGN_TOP - 0.05)):
        board_on_wall(mb, wf, a, b, c, d, 0.03, "trim", trim, 0.05)
    # consoles at the tops of the pilasters, flanking the board
    for ua in (0.0, W - 0.32):
        facade.wbox(mb, wf, ua, ua + 0.32, HEAD_TOP, SIGN_TOP, 0.0, 0.11, "trim", trim, skip=("back",))
        board_on_wall(mb, wf, ua + 0.06, ua + 0.26, HEAD_TOP + 0.10, SIGN_TOP - 0.10, 0.015, "trim", mul(trim, 1.05), 0.11)
        board_on_wall(mb, wf, ua - 0.01, ua + 0.33, SIGN_TOP - 0.06, SIGN_TOP, 0.13, "trim", mul(trim, 0.9))
    # streaks where the cornice drips on the board (the letters stand through them)
    for u in (0.9, 2.6, 5.3, 7.1):
        _wall_card(mb, wf, u, u + rng.uniform(0.5, 0.9), HEAD_TOP + 0.06, SIGN_TOP - 0.03, 0.052, "decal_grime",
                   uv=(rng.uniform(0, 0.4), 0.55, rng.uniform(0.6, 1.0), 1.0))
    text = "RIDGE STATIONERY & BOOKS"
    H = 0.40
    zb = HEAD_TOP + (SIGN_TOP - HEAD_TOP - H) / 2
    gilt = _c(GILT)
    for i, (ch, ul, w, polys) in enumerate(text_layout(text, W / 2, zb, H)):
        if not polys:
            continue
        if i == 11:                                            # the O of STATIONERY: gone, its ghost darker
            for p, lv in zip(polys, depth_levels(polys)):
                mb.face([wf.at(u, z, 0.052 + 0.0012 * lv) for u, z in p], "door", color=_c(SIGN_GREEN_KEPT))
            for du in (0.06, w - 0.06):
                mb.cylinder(wf.at(ul + du, zb + H / 2, 0.05), (0, -0.006, 0), 0.008, "metal_rust", segments=5)
            continue
        ang = rng.uniform(-0.02, 0.02)
        pivot = (ul + w * 0.15, zb + H * 0.85)
        if i == 15:                                            # the Y hangs from its left screw
            ang = -0.32
        elif i == 23:
            ang = 0.05
        col = lerp(gilt, board, rng.uniform(0.0, 0.25))
        if rng.random() < 0.3:
            col = mul(col, rng.uniform(0.75, 0.9))
        off0 = 0.05 if i != 15 else 0.055
        polys = [_rotate(p, pivot, ang) if ang else p for p in polys]
        for p, lv in zip(polys, depth_levels(polys)):
            _raised(mb, wf, p, off0, off0 + 0.033 + 0.0015 * lv, "trim", col)
        if i == 15:
            mb.cylinder(wf.at(*pivot, 0.05), (0, -0.045, 0), 0.007, "metal_rust", segments=5)


def _blade_sign(mb, trim, rng):
    """BOOKS on a board hung square to the street from an iron bracket at the west
    corner, so it reads down Ashgrove; one hook has rusted through and it hangs askew."""
    x = 0.27                                   # the board's mid plane
    y0, y1 = -1.12, -0.27                      # its outer and inner ends
    zb, zt = 4.12, 4.62
    iron = _c((0.05, 0.05, 0.05), METAL)
    s = MeshBuilder()
    board = _c(SIGN_GREEN)
    s.box((x - 0.02, y0, zb), (x + 0.02, y1, zt), "door", color=board)
    for lo, hi in (((x - 0.028, y0 - 0.02, zt - 0.035), (x + 0.028, y1 + 0.02, zt + 0.02)),
                   ((x - 0.028, y0 - 0.02, zb - 0.02), (x + 0.028, y1 + 0.02, zb + 0.035)),
                   ((x - 0.028, y0 - 0.02, zb + 0.035), (x + 0.028, y0 + 0.02, zt - 0.035)),
                   ((x - 0.028, y1 - 0.02, zb + 0.035), (x + 0.028, y1 + 0.02, zt - 0.035))):
        s.box(lo, hi, "trim", color=trim)
    gilt = _c(GILT)
    for wf in (WallFace((x - 0.02, y1), (0, -1), (-1, 0), y1 - y0, "w"), WallFace((x + 0.02, y0), (0, 1), (1, 0), y1 - y0, "e")):
        H = 0.20
        for ch, ul, w, polys in text_layout("BOOKS", (y1 - y0) / 2, (zb + zt) / 2 - H / 2, H):
            col = lerp(gilt, board, rng.uniform(0.0, 0.2))
            for p, lv in zip(polys, depth_levels(polys)):
                _raised(s, wf, p, 0.0, 0.014 + 0.0012 * lv, "trim", col)
    hook = Vector((x, y1 - 0.08, zt + 0.02))
    for yy in (y1 - 0.08, y0 + 0.08):          # the eyes on top of the board
        s.tube([V(x, yy, zt + 0.02), V(x, yy - 0.025, zt + 0.06), V(x, yy - 0.05, zt + 0.02)], 0.006, "metal_rust", segments=4)
    mb.extend(s, Matrix.Translation(hook) @ Matrix.Rotation(0.14, 4, "X") @ Matrix.Translation(-hook))
    # the bracket: wall plate, the arm, a brace with a scroll, the hooks (the outer one broken)
    za = 4.86
    mb.box((x - 0.04, -0.045, 4.28), (x + 0.04, 0.0, 4.92), "metal_painted", color=iron)
    mb.box((x - 0.015, y0 - 0.06, za - 0.015), (x + 0.015, -0.04, za + 0.015), "metal_painted", color=iron)
    mb.tube([V(x, -0.04, 4.36), V(x, -0.35, 4.55), V(x, -0.7, za - 0.015)], 0.012, "metal_painted", segments=5, color=iron)
    scroll = [V(x, -0.3 - 0.09 * math.cos(a), za - 0.12 + 0.09 * math.sin(a)) for a in [i * 0.6 for i in range(9)]]
    mb.tube(scroll, 0.008, "metal_painted", segments=4, color=iron)
    mb.tube([V(x, y1 - 0.08, za - 0.015), V(x, y1 - 0.07, zt + 0.10), V(x, y1 - 0.09, zt + 0.05)], 0.007, "metal_rust", segments=4)
    mb.tube([V(x, y0 + 0.08, za - 0.015), V(x, y0 + 0.09, za - 0.12), V(x, y0 + 0.07, za - 0.16)], 0.007, "metal_rust", segments=4)
    mb.tube([V(x, y1 - 0.08, za + 0.015), V(x, y0 - 0.04, za + 0.015)], 0.004, "metal_rust", segments=3)


# --- the painted advert on the west wall ----------------------------------------------------------------

def _advert(mb, wf, D, siding, rng):
    """RIDGE STATIONERY / PENS . PAPER . BOOKS painted on the upper west wall, faded
    and flaking. The paint is laid on the clapboard itself, row by row."""
    z0 = FLOOR + 0.18                                 # where the side walls' clapboard rows start
    ua, ub = 3.55, D - 0.65
    za, zb = 3.70, 5.02
    ground = (0.22, 0.10, 0.08)                      # oxblood, as painted
    cream = (0.62, 0.58, 0.47)
    wall = mul(siding, NEUTRAL)
    # the ground of the sign, in patches: some flaked to the boards, some faded
    k0 = int(math.ceil((za - z0) / BOARD))
    k1 = int(math.floor((zb - z0) / BOARD))
    for k in range(k0, k1):
        r0 = z0 + k * BOARD
        u = ua
        while u < ub - 1e-3:
            step = min(ub - u, rng.uniform(0.25, 0.9))
            if rng.random() > 0.1:
                col = lerp(ground, wall, rng.uniform(0.08, 0.38))
                _paint_on_boards(mb, wf, [(u, r0), (u + step, r0), (u + step, r0 + BOARD), (u, r0 + BOARD)], z0,
                                 _c(col, 0.74), 0.002)
            u += step
    za, zb = z0 + k0 * BOARD, z0 + k1 * BOARD
    # a thin border and the lettering
    lines = (("RIDGE STATIONERY", 0.38, za + 0.64), ("PENS . PAPER . BOOKS", 0.25, za + 0.20))
    polys = []
    for text, H, base in lines:
        H = min(H, (ub - ua - 0.3) / text_width(text, 1.0))
        for ch, ul, w, ps in text_layout(text, (ua + ub) / 2, base, H):
            polys += ps
    m = 0.07
    for a, b, c, d in ((ua + m, ub - m, za + m, za + m + 0.035), (ua + m, ub - m, zb - m - 0.035, zb - m),
                       (ua + m, ua + m + 0.035, za + m, zb - m), (ub - m - 0.035, ub - m, za + m, zb - m)):
        polys.append([(a, c), (b, c), (b, d), (a, d)])
    for p, lv in zip(polys, depth_levels(polys)):
        if rng.random() < 0.06:
            continue                                            # flaked away
        col = lerp(cream, wall, rng.uniform(0.1, 0.35))
        _paint_on_boards(mb, wf, p, z0, _c(col, 0.74), 0.004 + 0.0008 * lv)


def _gas_meter(mb, wf, D):
    """A gas meter on the west wall, its riser out of the ground, and a hose bib."""
    u = D - 5.6
    grey = _c((0.36, 0.37, 0.35), METAL)
    pipe = [wf.at(u, GROUND - 0.05, 0.10), wf.at(u, 0.15, 0.10), wf.at(u, 0.30, 0.10)]
    mb.tube(pipe, 0.022, "metal_rust", segments=6, color=(0.7, 0.66, 0.6))
    facade.wbox(mb, wf, u - 0.20, u + 0.20, 0.30, 0.78, 0.03, 0.20, "metal_painted", grey)
    facade.wbox(mb, wf, u - 0.12, u + 0.12, 0.46, 0.62, 0.20, 0.21, "glass_dirty", (0.7, 0.72, 0.7))     # the dials
    mb.tube([wf.at(u - 0.12, 0.78, 0.12), wf.at(u - 0.12, 0.92, 0.12), wf.at(u - 0.12, 0.98, 0.04)], 0.018, "metal_rust",
            segments=6, color=(0.7, 0.66, 0.6))
    mb.cylinder(wf.at(u + 0.32, 0.55, 0.10), (0, 0, 0.12), 0.07, "metal_painted", segments=8, color=grey)   # regulator
    mb.tube([wf.at(u + 0.20, 0.50, 0.10), wf.at(u + 0.32, 0.55, 0.10)], 0.014, "metal_rust", segments=5)
    bib = wf.at(u - 1.4, 0.25, 0.03)
    mb.cylinder(bib, tuple(wf.n * 0.09), 0.014, "chrome_dull", segments=6)
    mb.cylinder(bib + wf.n * 0.06, (0, 0, 0.05), 0.022, "metal_rust", segments=6)


# --- the roof, gutters, downpipes, chimney ---------------------------------------------------------------

def _roof(mb, W, D, trim, rng):
    ov = ROOF_OV
    tp = math.tan(PITCH)
    ez = EAVE_S - ov * tp
    rz = EAVE_S + W / 2 * tp
    t = Vector((0, 0, 0.12))
    y0, y1 = 0.10, D + 0.35
    mid = W / 2
    rc = (0.9, 0.88, 0.85)
    for xe in (-ov, W + ov):
        up = Vector((-1 if xe < 0 else 1, 0, 2))
        quad = [V(xe, y0, ez), V(xe, y1, ez), V(mid, y1, rz), V(mid, y0, rz)]
        _face_toward(mb, [p + t for p in quad], up, "roof_tin", rc)
        mb.uvs[-1] = [(p.y / 1.5, abs(p.x - mid) / math.cos(PITCH) / 1.5) for p in mb.verts[-4:]]   # ribs down the slope
        _face_toward(mb, quad, -up, "trim", mul(trim, 0.7))
        side = Vector((-1 if xe < 0 else 1, 0, 0))
        _face_toward(mb, [V(xe, y0, ez), V(xe, y1, ez), V(xe, y1, ez) + t, V(xe, y0, ez) + t], side, "trim", trim)  # fascia
        # rake at the back, and the end of the overhang beside the false front
        _face_toward(mb, [V(xe, y1, ez), V(mid, y1, rz), V(mid, y1, rz) + t, V(xe, y1, ez) + t], (0, 1, 0), "trim", trim)
        xw = 0.0 if xe < 0 else W
        _face_toward(mb, [V(xe, y0, ez), V(xw, y0, ez + ov * tp), V(xw, y0, ez + ov * tp) + t, V(xe, y0, ez) + t],
                     (0, -1, 0), "trim", trim)
    mb.tube([V(mid, y0, rz + 0.12), V(mid, y1, rz + 0.12)], 0.05, "roof_tin", segments=4, color=rc)
    # flashing where the roof meets the back of the false front
    flash = _c((0.30, 0.29, 0.27), METAL)
    for xe in (0.0, W):
        _face_toward(mb, [V(xe, SLAB, EAVE_S + 0.125), V(mid, SLAB, rz + 0.125), V(mid, SLAB + 0.18, rz + 0.125),
                          V(xe, SLAB + 0.18, EAVE_S + 0.125)], (0, 0, 1), "metal_painted", flash)
        _face_toward(mb, [V(xe, SLAB + 0.003, EAVE_S + 0.12), V(mid, SLAB + 0.003, rz + 0.12), V(mid, SLAB + 0.003, rz + 0.27),
                          V(xe, SLAB + 0.003, EAVE_S + 0.27)], (0, 1, 0), "metal_painted", flash)
    # lid over the walls (seen through the gable vent), gable vent, chimney
    mb.face([V(0, SLAB, EAVE_S), V(0, D, EAVE_S), V(W, D, EAVE_S), V(W, SLAB, EAVE_S)], "interior_dark")
    facade.gable_vent(mb, WallFace((W, D), (-1, 0), (0, 1), W, "back"), trim, EAVE_S + W / 2 * tp * 0.5)
    chimney(mb, V(mid + 0.9, D - 1.6, rz), EAVE_S + (W / 2 - 0.9) * tp + 0.12, rng)
    # gutters along both eaves and four downpipes
    gcol = mul(trim, 0.85)
    for xe, out in ((-ov, -1.0), (W + ov, 1.0)):
        o = Vector((out, 0, 0))
        p0, p1 = V(xe + out * 0.02, y0, ez), V(xe + out * 0.02, y1, ez)
        lo = Vector((0, 0, -0.10))
        _face_toward(mb, [p0 + lo, p1 + lo, p1 + lo + o * 0.12, p0 + lo + o * 0.12], (0, 0, -1), "metal_painted", gcol)
        _face_toward(mb, [p0 + lo + o * 0.12, p1 + lo + o * 0.12, p1 + o * 0.12, p0 + o * 0.12], o, "metal_painted", gcol)
        _face_toward(mb, [p0 + lo, p1 + lo, p1, p0], -o, "metal_painted", mul(gcol, 0.8))
        for p in (p0, p1):
            _face_toward(mb, [p + lo, p + lo + o * 0.12, p + o * 0.12, p], (0, -1 if p is p0 else 1, 0), "metal_painted", gcol)
        xw = -0.09 if out < 0 else W + 0.09
        for yp, back in ((0.55, 1), (D - 0.35, -1)):
            gx = xe + out * 0.08
            pts = [V(gx, yp, ez - 0.10), V(gx, yp, ez - 0.22), V(xw, yp, ez - 0.50), V(xw, yp, GROUND + 0.22),
                   V(xw, yp + 0.2 * back, GROUND + 0.07)]
            rusty = rng.random() < 0.5
            mb.tube(pts, 0.035, "metal_rust" if rusty else "metal_painted", segments=6,
                    color=(0.75, 0.72, 0.68) if rusty else gcol)
            x_wall = 0.0 if out < 0 else W
            for zz in (0.9, 2.6, 4.3):
                mb.box((min(xw, x_wall), yp - 0.02, zz), (max(xw, x_wall), yp + 0.02, zz + 0.03), "metal_painted", color=gcol)


# --- the flat's stair at the back -------------------------------------------------------------------------

def _back_stair(mb, faces, W, D, trim, wear, rng):
    wood = mul(trim, 0.92)                     # painted grey, like the porches
    deck = (0.72, 0.70, 0.66)
    n = 18
    sx0, sx1 = 2.70, 6.95                      # nose of the bottom step .. the landing
    rise = (FF_Z - GROUND) / n
    going = (sx1 - sx0) / (n - 1)
    yi, yo = D + 0.06, D + 1.0
    for k in range(1, n):
        z = GROUND + k * rise
        xa = sx0 + (k - 1) * going
        if wear > 0.5 and k == 7:                          # a tread split and dropped at one end
            mb.obox((xa + going / 2, (yi + yo) / 2, z - 0.06), (going + 0.03, yo - yi - 0.06, 0.04), 0.05, "porch_deck",
                    color=mul(deck, 0.8), tilt=(0.12, 0.0))
            continue
        mb.box((xa - 0.03, yi + 0.03, z - 0.04), (xa + going, yo - 0.03, z), "porch_deck",
               color=jitter_color(rng, deck, 0.08), rot=True)
    ang = math.atan2(FF_Z - GROUND, sx1 - sx0 + going)
    for y in (yi + 0.025, yo - 0.025):                    # stringers
        a = V(sx0 - 0.15, y, GROUND + 0.02)
        b = V(sx1, y, FF_Z - 0.06)
        _tube_box(mb, a + Vector((0, 0, -0.10)), b + Vector((0, 0, -0.10)), 0.05, 0.28, "trim", mul(wood, 0.85))
    # the landing on four posts, its deck and joists
    lx0, lx1, ly0, ly1 = sx1, W - 0.03, D, D + 1.25
    mb.box((lx0, ly0 + 0.03, FF_Z - 0.05), (lx1, ly1, FF_Z), "porch_deck", color=(0.72, 0.70, 0.66), rot=True)
    mb.box((lx0, ly0 + 0.03, FF_Z - 0.25), (lx1, ly1, FF_Z - 0.05), "trim", color=mul(wood, 0.8), skip="+z")
    roof_lo = FF_Z + 2.32
    posts = [(lx0 + 0.06, ly1 - 0.06), (lx1 - 0.06, ly1 - 0.06), (lx0 + 0.06, ly0 + 0.10), (lx1 - 0.06, ly0 + 0.10)]
    for i, (px, py) in enumerate(posts):
        ztop = roof_lo if i < 2 else FF_Z - 0.25
        mb.box((px - 0.06, py - 0.06, GROUND - 0.02), (px + 0.06, py + 0.06, ztop), "trim",
               color=jitter_color(rng, wood, 0.06), skip="-z")
    # diagonal brace under the landing
    _tube_box(mb, (lx1 - 0.06, ly1 - 0.06, 1.0), (lx0 + 0.3, ly1 - 0.06, FF_Z - 0.26), 0.05, 0.08, "trim", mul(wood, 0.85))
    # handrails: up the outer side of the stair, round the landing
    rail_h = 0.92
    bot = V(sx0 - 0.05, yo - 0.03, GROUND + rise + rail_h)
    topp = V(lx0 + 0.06, yo - 0.03, FF_Z + rail_h)
    mb.box((sx0 - 0.11, yo - 0.09, GROUND - 0.02), (sx0 + 0.01, yo + 0.03, GROUND + rise + rail_h + 0.1), "trim",
           color=wood, skip="-z")                                                   # newel
    _tube_box(mb, bot, topp, 0.06, 0.05, "trim", wood)
    for k in range(1, n, 2):
        x = sx0 + (k - 0.5) * going
        zb_ = GROUND + k * rise
        if wear > 0.5 and k in (9,):
            continue
        mb.box((x - 0.018, yo - 0.05, zb_), (x + 0.018, yo - 0.014, zb_ + rail_h - 0.03), "trim", color=wood,
               skip="-z")
    for (ax_, ay_), (bx_, by_) in (((lx0 + 0.06, ly1 - 0.06), (lx1 - 0.06, ly1 - 0.06)),
                                   ((lx1 - 0.06, ly1 - 0.06), (lx1 - 0.06, ly0 + 0.10))):
        mb.box((min(ax_, bx_) - 0.03, min(ay_, by_) - 0.03, FF_Z + rail_h - 0.05),
               (max(ax_, bx_) + 0.03, max(ay_, by_) + 0.03, FF_Z + rail_h), "trim", color=wood)
        length = math.hypot(bx_ - ax_, by_ - ay_)
        nb = int(length / 0.13)
        for j in range(1, nb):
            t = j / nb
            x, y = ax_ + (bx_ - ax_) * t, ay_ + (by_ - ay_) * t
            mb.box((x - 0.016, y - 0.016, FF_Z), (x + 0.016, y + 0.016, FF_Z + rail_h - 0.05), "trim",
                   color=wood, skip="-z+z")
    # a shed roof over the landing and the door
    a, b = V(lx0 - 0.15, ly1 + 0.13, roof_lo), V(W, ly1 + 0.13, roof_lo)
    c, d = V(W, D, roof_lo + 0.30), V(lx0 - 0.15, D, roof_lo + 0.30)
    tt = Vector((0, 0, 0.05))
    _face_toward(mb, [a + tt, b + tt, c + tt, d + tt], (0, 0.3, 1), "roof_tin", (0.85, 0.85, 0.85))
    _face_toward(mb, [a, b, c, d], (0, 0, -1), "trim", mul(trim, 0.7))
    for p, q, nrm in ((a, b, (0, 1, 0)), (d, a, (-1, 0, 0)), (b, c, (1, 0, 0))):
        _face_toward(mb, [p, q, q + tt, p + tt], nrm, "trim", trim)
    mb.box((lx0 - 0.1, ly1 - 0.10, roof_lo - 0.14), (W, ly1 + 0.02, roof_lo), "trim", color=wood)   # beam


# --- inside the shop ------------------------------------------------------------------------------------

def _interior(mb, W, rx0, rx1, door_at, rng):
    """What shows through the glass: display beds, stands, boxes, shelves, a counter,
    in a dark room that closes the shell behind the shop front."""
    _inner_box(mb, (PIL, 0.06, FLOOR - 0.005), (W - PIL, ROOM_D, FF_Z), "interior_dark", skip="-y-z")
    floor_col = (0.32, 0.28, 0.24)
    for x0, y0, x1, y1 in ((PIL, 0.06, rx0 - 0.10, ROOM_D), (rx1 + 0.10, 0.06, W - PIL, ROOM_D),
                           (rx0 - 0.10, REC_D + 0.10, rx1 + 0.10, ROOM_D)):
        mb.face([V(x0, y0, FLOOR - 0.005), V(x1, y0, FLOOR - 0.005), V(x1, y1, FLOOR - 0.005), V(x0, y1, FLOOR - 0.005)],
                "wood_weathered", color=floor_col)
    felt = _c((0.20, 0.11, 0.10), FABRIC)
    beds = ((PIL, rx0 - 0.10), (rx1 + 0.10, W - PIL))
    for x0, x1 in beds:
        mb.box((x0, 0.04, FLOOR), (x1, 0.95, BULK), "fabric", skip="-z-y-x+x", color=felt)
    covers = [(0.42, 0.14, 0.11), (0.14, 0.20, 0.32), (0.16, 0.28, 0.18), (0.08, 0.08, 0.08), (0.52, 0.43, 0.22),
              (0.45, 0.42, 0.38)]

    def notebook(c, rz, lean, col):
        mb.obox(c, (0.17, 0.012, 0.23), rz, "trim", color=_c(lerp(col, (0.55, 0.53, 0.48), 0.25)), tilt=(lean, 0.0))

    # left window: a tiered stand of notebooks, a pyramid of cartons, a fallen card
    sx0, sx1 = 0.85, 2.05
    for k, (yf, hz) in enumerate(((0.35, 0.10), (0.52, 0.20), (0.69, 0.30))):
        mb.box((sx0, yf, BULK), (sx1, 0.86, BULK + hz), "trim", color=_c((0.55, 0.53, 0.48)), skip="-z")
        for j in range(5):
            x = sx0 + 0.13 + j * 0.235
            if k == 1 and j == 3:
                continue                                         # one gone
            notebook((x, yf + 0.05, BULK + hz + 0.105), rng.uniform(-0.05, 0.05), -0.28, rng.choice(covers))
    notebook((1.6, 0.22, BULK + 0.008), 0.6, -math.pi / 2, covers[0])                       # one lying flat
    for c, size, rz in (((2.55, 0.55, BULK + 0.15), (0.48, 0.40, 0.30), 0.1), ((2.62, 0.58, BULK + 0.42), (0.38, 0.32, 0.24), -0.2),
                        ((2.9, 0.3, BULK + 0.10), (0.30, 0.26, 0.20), 0.5)):
        mb.obox(c, size, rz, "plywood", color=(0.72, 0.6, 0.45))
    mb.obox((0.62, 0.45, BULK + 0.004), (0.32, 0.22, 0.008), 0.3, "trim", color=_c((0.6, 0.58, 0.52)))
    # right window: a wire rack of exercise books, a carton, reams of paper, the FOR SALE card
    rx, ry = 6.55, 0.55
    mb.cylinder((rx, ry, BULK), (0, 0, 1.45), 0.012, "chrome_dull", segments=6)
    mb.cylinder((rx, ry, BULK), (0, 0, 0.02), 0.18, "chrome_dull", segments=10)
    for k, zz in enumerate((0.45, 0.85, 1.25)):
        mb.box((rx - 0.42, ry - 0.14, BULK + zz - 0.01), (rx + 0.42, ry + 0.14, BULK + zz), "chrome_dull")
        for j in range(4):
            if k == 2 and j == 0:
                continue
            notebook((rx - 0.31 + j * 0.205, ry - 0.06, BULK + zz + 0.11), rng.uniform(-0.04, 0.04), -0.22, rng.choice(covers))
    mb.obox((5.62, 0.55, BULK + 0.2), (0.5, 0.42, 0.40), 0.15, "plywood", color=(0.72, 0.6, 0.45), skip="+z")
    mb.obox((5.62, 0.55, BULK + 0.02), (0.46, 0.38, 0.02), 0.15, "interior_dark")
    for side in (-1, 1):                                                  # its flaps open
        mb.obox((5.62 + side * 0.33, 0.55, BULK + 0.42), (0.2, 0.40, 0.008), 0.15, "plywood", color=(0.7, 0.58, 0.44),
                tilt=(0.0, side * 0.9))
    for k in range(4):
        mb.obox((7.55 + rng.uniform(-0.02, 0.02), 0.5, BULK + 0.04 + 0.075 * k), (0.32, 0.23, 0.07), rng.uniform(-0.1, 0.1),
                "trim", color=_c((0.66, 0.65, 0.6) if k % 2 else (0.5, 0.52, 0.55)))
    xa, xb = 5.42, 6.02
    mb.face([V(xa, 0.13, BULK + 0.005), V(xb, 0.13, BULK + 0.005), V(xb, 0.21, BULK + 0.30), V(xa, 0.21, BULK + 0.30)],
            "sign_sale", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # the shop behind: shelving along the back wall, a counter, two pendant lamps
    shelf = (0.30, 0.24, 0.18)
    for x0, x1 in ((0.55, 2.55), (3.05, 5.35), (5.85, 7.85)):
        for x in (x0, x1 - 0.04):
            mb.box((x, ROOM_D - 0.36, FLOOR), (x + 0.04, ROOM_D - 0.01, 2.35), "wood_weathered", color=shelf, skip="-z")
        for k in range(5):
            z = FLOOR + 0.12 + k * 0.48
            mb.box((x0, ROOM_D - 0.36, z), (x1, ROOM_D - 0.01, z + 0.03), "wood_weathered", color=shelf)
            if k == 4:
                continue
            x = x0 + 0.06
            while x < x1 - 0.2:
                bw = rng.uniform(0.18, 0.45)
                bh = rng.uniform(0.16, 0.36)
                if rng.random() < 0.75:
                    col = rng.choice(((0.42, 0.36, 0.28), (0.30, 0.22, 0.18), (0.22, 0.26, 0.30), (0.5, 0.48, 0.42)))
                    mb.box((x, ROOM_D - 0.32, z + 0.03), (min(x + bw, x1 - 0.06), ROOM_D - 0.05, z + 0.03 + bh), "trim",
                           color=_c(col), skip="-z+y")
                x += bw + 0.03
    mb.box((5.7, 1.9, FLOOR), (7.7, 2.45, FLOOR + 0.95), "wood_weathered", color=(0.42, 0.34, 0.26), skip="-z")
    mb.box((5.65, 1.85, FLOOR + 0.95), (7.75, 2.5, FLOOR + 0.99), "wood_weathered", color=(0.5, 0.42, 0.32))
    mb.obox((6.9, 2.2, FLOOR + 1.12), (0.38, 0.34, 0.26), 0.2, "metal_painted", color=_c((0.12, 0.12, 0.11), METAL))  # till
    for lx in (1.9, 6.4):
        mb.tube([V(lx, 1.7, FF_Z), V(lx, 1.7, FF_Z - 0.55)], 0.006, "wire", segments=3)
        mb.cylinder(V(lx, 1.7, FF_Z - 0.75), (0, 0, 0.2), 0.20, "metal_painted", segments=10, radius_top=0.05,
                    color=_c((0.14, 0.22, 0.16), METAL), caps="top")


# --- the awning ---------------------------------------------------------------------------------------------

def _awning(mb, W, rng):
    """Striped canvas on a pipe frame over the shop front: faded, sagging between the
    rafters, torn at the east end where the canvas has come off the front rail."""
    x0, x1 = PIL - 0.02, W - PIL + 0.02
    yw, zw = -0.12, HEAD_TOP - 0.04
    yf, zf = -1.85, 2.38
    bay = (x1 - x0) / 4
    raf = [x0 + bay * i for i in range(5)]
    nst = 24
    sw = (x1 - x0) / nst
    green, cream = (0.17, 0.25, 0.20), (0.50, 0.47, 0.40)

    def sag(x, s):
        k = min(int((x - x0) / bay), 3)
        f = max(0.0, min(1.0, (x - raf[k]) / bay))
        depth = 0.06 + (0.05 if k == 2 else 0.0)
        return depth * math.sin(math.pi * f) * math.sin(math.pi * s) ** 0.8 + 0.012 * math.sin(math.pi * s)

    def P(x, s):
        return V(x, yw + (yf - yw) * s, zw + (zf - zw) * s - sag(x, s))

    ss = (0.0, 0.25, 0.5, 0.75, 1.0)
    up = (0, -0.35, 1)
    for i in range(nst):
        xa, xb = x0 + i * sw, x0 + (i + 1) * sw
        base = jitter_color(rng, green if i % 2 == 0 else cream, 0.05)
        if i >= 20:
            # hanging off the wall rail, the bottom ragged
            L = rng.uniform(0.7, 0.86)
            tw = 0.05 * (i - 21.5)

            def H(x, t, L=L, tw=tw):
                return V(x + tw * t, yw - 0.04 - 0.20 * t - 0.05 * math.sin(math.pi * t), zw - L * t)
            for t0, t1 in ((0.0, 0.34), (0.34, 0.67), (0.67, 1.0)):
                col = _c(mul(base, 1.0 - 0.15 * t1), FABRIC)
                if t1 < 1.0:
                    _face_toward(mb, [H(xa, t0), H(xb, t0), H(xb, t1), H(xa, t1)], (0, -1, 0), "fabric", col)
                else:
                    ja, jb = rng.uniform(0.85, 1.0), rng.uniform(0.85, 1.0)
                    jm = rng.uniform(1.0, 1.12)
                    _face_toward(mb, [H(xa, t0), H(xb, t0), H(xb, jb), H((xa + xb) / 2, jm), H(xa, ja)], (0, -1, 0), "fabric", col)
            continue
        s_end = {18: 0.70, 19: 0.52}.get(i, 1.0)
        prev = 0.0
        for s1 in ss[1:]:
            if prev >= s_end - 1e-6:
                break
            s1c = min(s1, s_end)
            col = _c(mul(base, 1.0 - 0.12 * s1c), FABRIC)
            pts = [P(xa, prev), P(xb, prev), P(xb, s1c), P(xa, s1c)]
            _face_toward(mb, pts, up, "fabric", col)
            prev = s1c
        if s_end < 1.0:                                       # the torn edge curls down
            a, b = P(xa, s_end), P(xb, s_end)
            dn = Vector((0, -0.10, -0.16))
            _face_toward(mb, [a, b, b + dn + Vector((0, 0, rng.uniform(-0.05, 0.05))), (a + b) / 2 + dn * 1.3,
                              a + dn + Vector((0, 0, rng.uniform(-0.05, 0.05)))], up, "fabric",
                         _c(mul(base, 0.85), FABRIC))
        # the scalloped valance; loose and low at the torn end, missing past it
        if i <= 20:
            ta, tb = P(xa, 1.0), P(xb, 1.0)
            drop = 0.24 if i < 18 else 0.28
            o = Vector((0, -0.03 if i < 18 else -0.07, -drop))
            mid = (ta + tb) / 2 + o + Vector((0, 0, -0.05))
            col = _c(mul(base, 0.8), FABRIC)
            _face_toward(mb, [ta, tb, tb + o, mid, ta + o], (0, -1, 0), "fabric", col)
    # the frame: wall rail, front rail, rafters, two arms, brackets on the head beam
    frame = _c((0.20, 0.21, 0.19), METAL)
    mb.tube([V(x0, yw, zw - 0.02), V(x1, yw, zw - 0.02)], 0.022, "metal_painted", segments=6, color=frame)
    mb.tube([V(x0, yf, zf - 0.03), V(x1, yf, zf - 0.03)], 0.026, "metal_painted", segments=6, color=frame)
    for x in raf:
        mb.tube([V(x, yw, zw - 0.04), V(x, yf, zf - 0.05)], 0.02, "metal_painted", segments=5, color=frame)
        mb.box((x - 0.04, -0.13, HEAD_TOP - 0.10), (x + 0.04, -0.085, HEAD_TOP - 0.01), "metal_rust", color=(0.7, 0.66, 0.6))
    for x in (x0 + 0.05, x1 - 0.05):
        mb.tube([V(x, -0.11, 2.44), V(x, yf + 0.05, zf - 0.07)], 0.018, "metal_painted", segments=5, color=frame)


# --- the apron ------------------------------------------------------------------------------------------------

def _apron(mb, W, rx0, rx1, trim, rng):
    """The concrete forecourt with a bench under the left window and a newspaper box."""
    y0 = -APRON_D
    slab = (0.80, 0.78, 0.74)
    mb.face([V(0, y0 + 0.05, APRON_Z), V(W, y0 + 0.05, APRON_Z), V(W, 0, APRON_Z), V(0, 0, APRON_Z)], "sidewalk", color=slab)
    _face_toward(mb, [V(0, y0, GROUND - 0.01), V(W, y0, GROUND - 0.01), V(W, y0 + 0.05, APRON_Z), V(0, y0 + 0.05, APRON_Z)],
                 (0, -1, 0.5), "sidewalk", mul(slab, 0.85))
    for x, nx in ((0.0, -1), (W, 1)):
        _face_toward(mb, [V(x, y0, GROUND - 0.01), V(x, y0 + 0.05, APRON_Z), V(x, 0, APRON_Z), V(x, 0, GROUND - 0.01)],
                     (nx, 0, 0), "sidewalk", mul(slab, 0.85))
    for c, w, hgt, mat in (((5.8, -1.15), 1.4, 1.2, "decal_crack"), ((1.4, -1.45), 1.2, 1.0, "decal_crack"),
                           ((7.6, -0.4), 1.1, 0.8, "decal_leaves"), ((0.5, -0.35), 0.9, 0.6, "decal_leaves"),
                           ((3.1, -0.6), 0.8, 0.6, "decal_leaves")):
        mb.card((c[0], c[1], APRON_Z + 0.003), w, hgt, rng.uniform(0, 3), mat, flat=True)
    # the bench, its iron ends, a slat gone from the back
    bx0, bx1, yb = 0.75, 2.35, -0.32
    z = APRON_Z
    wood = (0.78, 0.74, 0.68)
    iron = _c((0.05, 0.05, 0.05), METAL)
    for k in range(3):
        ya = yb - 0.42 + k * 0.135
        mb.box((bx0, ya, z + 0.42), (bx1, ya + 0.11, z + 0.45), "wood_weathered", color=jitter_color(rng, wood, 0.06))
    mb.obox(((bx0 + bx1) / 2, yb - 0.02, z + 0.62), (bx1 - bx0, 0.03, 0.10), 0.0, "wood_weathered",
            color=jitter_color(rng, wood, 0.06), tilt=(0.17, 0.0))
    mb.obox(((bx0 + bx1) / 2 + 0.05, yb + 0.02, z + 0.74), (bx1 - bx0 - 0.1, 0.03, 0.10), 0.0, "wood_weathered",
            color=mul(wood, 0.9), tilt=(0.17, -0.22))                       # hanging off one screw
    for x in (bx0 + 0.12, bx1 - 0.12):
        mb.box((x - 0.025, yb - 0.40, z), (x + 0.025, yb - 0.36, z + 0.42), "metal_painted", color=iron, skip="-z")
        _tube_box(mb, (x, yb - 0.02, z), (x, yb + 0.03, z + 0.86), 0.05, 0.04, "metal_painted", iron)
        mb.box((x - 0.025, yb - 0.44, z + 0.38), (x + 0.025, yb - 0.0, z + 0.42), "metal_painted", color=iron)
        mb.tube([V(x, yb - 0.02, z + 0.64), V(x, yb - 0.40, z + 0.62), V(x, yb - 0.40, z + 0.45)], 0.018, "metal_painted",
                segments=5, color=iron)
    # the newspaper box near the front, rusting at the foot
    nb = MeshBuilder()
    nb.grime = ground_grime(0.0, 0.5, 0.3)
    body = _c((0.26, 0.075, 0.06), METAL)
    for lx, ly in ((-0.17, -0.15), (0.17, -0.15), (-0.17, 0.15), (0.17, 0.15)):
        nb.box((lx - 0.02, ly - 0.02, 0.0), (lx + 0.02, ly + 0.02, 0.28), "metal_painted", color=mul(body, 0.7), skip="-z")
    nb.box((-0.22, -0.20, 0.28), (0.22, 0.20, 1.0), "metal_painted", color=body)
    nb.box((-0.23, -0.21, 0.98), (0.23, 0.21, 1.02), "metal_painted", color=mul(body, 0.85))
    nb.face([V(-0.17, -0.205, 0.62), V(0.12, -0.205, 0.62), V(0.12, -0.205, 0.93), V(-0.17, -0.205, 0.93)], "window_glass")
    nb.face([V(-0.15, -0.17, 0.64), V(0.10, -0.17, 0.64), V(0.10, -0.17, 0.90), V(-0.15, -0.17, 0.90)], "trim",
            color=_c((0.58, 0.56, 0.5)))
    nb.box((0.13, -0.225, 0.75), (0.21, -0.20, 0.93), "chrome_dull")
    nb.box((-0.08, -0.23, 0.56), (0.06, -0.20, 0.59), "chrome_dull")
    nb.face([V(-0.22, -0.2015, 0.28), V(0.22, -0.2015, 0.28), V(0.22, -0.2015, 0.42), V(-0.22, -0.2015, 0.42)],
            "metal_rust", color=(0.45, 0.42, 0.40))
    mb.extend(nb, Matrix.Translation((7.05, -1.62, APRON_Z)) @ Matrix.Rotation(0.06, 4, "Z"))


# --- stains -----------------------------------------------------------------------------------------------

def _stains(mb, faces, ops, W, D, rng, wear):
    """Water streaks under the sills and from the cornice, grime streaks down the false front."""
    for key, wf in faces.items():
        for o in ops[key]:
            if o[4] != "win" or key == "front":
                continue
            if rng.random() < 0.4 + 0.5 * wear:
                w = (o[1] - o[0]) * rng.uniform(0.7, 1.05)
                c = (o[0] + o[1]) / 2 + rng.uniform(-0.1, 0.1)
                _wall_card(mb, wf, c - w / 2, c + w / 2, o[2] - 0.2 - rng.uniform(0.5, 1.0), o[2] - 0.2, 0.028, "decal_streaks")
        if key != "front":
            for u in (0.25, wf.length - 0.7):
                if rng.random() < 0.6:
                    _wall_card(mb, wf, u, u + 0.45, EAVE_S - rng.uniform(1.5, 2.6), EAVE_S - 0.24, 0.028, "decal_streaks")
    wf = faces["front"]
    for u in (0.25, 2.25, 4.85, 7.55):
        _wall_card(mb, wf, u, u + rng.uniform(0.45, 0.7), FRIEZE - rng.uniform(1.1, 1.8), FRIEZE, 0.028, "decal_grime",
                   uv=(0.0, rng.uniform(0.3, 0.5), 1.0, 1.0))
