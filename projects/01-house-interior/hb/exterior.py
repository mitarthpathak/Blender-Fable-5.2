"""The outside of the house (docs/ART_BIBLE.md): porch, screen door, trim,
gutters, yard, fence and a streetlight, and the clapboard itself: one lapped
board per course over the flat wall the shell builder makes."""

from __future__ import annotations

import math
import random

from mathutils import Vector

import plan
from . import dressing as dr
from .core import MeshBuilder
from .dressing import Decals, Face

GROUND = -0.45                 # the yard is three steps below the ground floor
E = plan.EXT_T
OUT_S = Face("x", -E, -1)      # outside faces of the four walls
OUT_N = Face("x", plan.DEPTH + E, 1)
OUT_W = Face("y", -E, -1)
OUT_E = Face("y", plan.WIDTH + E, 1)

PORCH = (0.30, 3.70, -2.30)    # x0, x1, front edge y
DOOR = next(o for w in plan.WALLS for o in w.openings if o.name == "door_front")


def porch(coll="exterior"):
    x0, x1, yf = PORCH
    yb = -E
    made = []
    mb = MeshBuilder()
    # deck, its skirt, and the steps down to the path
    mb.box((x0, yf, -0.07), (x1, yb, -0.005), "porch_boards")
    mb.box((x0 + 0.03, yf + 0.03, GROUND), (x1 - 0.03, yb, -0.07), "ext_trim", skip="+z-z")
    sx0, sx1 = DOOR.start - 0.25, DOOR.end + 0.25
    for k in range(1, 3):
        z = -0.005 - 0.15 * k
        mb.box((sx0, yf - 0.28 * k, GROUND), (sx1, yf - 0.28 * (k - 1), z), "porch_boards", skip="-z")
    made.append(mb.build("porch_deck", coll, recalc=True))

    # posts, roof and railings
    mb = MeshBuilder()
    posts = [x0 + 0.06, sx0 - 0.02, sx1 + 0.02, x1 - 0.06]
    top = 2.58
    for x in posts:
        mb.box((x - 0.055, yf + 0.03, -0.005), (x + 0.055, yf + 0.14, top), "ext_trim", skip="-z")
    mb.box((x0, yf + 0.02, top), (x1, yf + 0.15, top + 0.16), "ext_trim")              # beam
    for (xa, xb) in ((posts[0], posts[1]), (posts[2], posts[3])):
        _rail(mb, (xa + 0.055, yf + 0.085), (xb - 0.055, yf + 0.085))
    for x in (x0 + 0.06, x1 - 0.06):
        _rail(mb, (x, yf + 0.14), (x, yb))
    made.append(mb.build("porch_frame", coll, recalc=True))

    mb = MeshBuilder()
    lo, hi = top + 0.16, top + 0.62
    a, b = Vector((x0 - 0.2, yf - 0.25, lo)), Vector((x1 + 0.2, yf - 0.25, lo))
    c, d = Vector((x1 + 0.2, yb, hi)), Vector((x0 - 0.2, yb, hi))
    up = Vector((0, 0, 0.05))
    mb.face([a + up, b + up, c + up, d + up], "roof")
    mb.face([d, c, b, a], "ext_trim")
    for p, q in ((a, b), (b, c), (d, a)):
        mb.face([p, q, q + up, p + up], "ext_trim")
    made.append(mb.build("porch_roof", coll))
    return made


def _rail(mb, a, b, z0=-0.005, height=0.92):
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    if length < 0.2:
        return
    along_x = abs(bx - ax) > abs(by - ay)
    w = 0.03

    def bar(z_lo, z_hi, t):
        if along_x:
            mb.box((min(ax, bx), ay - t, z0 + z_lo), (max(ax, bx), ay + t, z0 + z_hi), "ext_trim")
        else:
            mb.box((ax - t, min(ay, by), z0 + z_lo), (ax + t, max(ay, by), z0 + z_hi), "ext_trim")
    bar(height - 0.05, height, w)
    bar(0.10, 0.14, w * 0.8)
    n = int(length / 0.13)
    for i in range(1, n):
        t = i / n
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        mb.box((x - 0.014, y - 0.014, z0 + 0.14), (x + 0.014, y + 0.014, z0 + height - 0.05), "ext_trim",
               skip="-z+z")


def screen_door(coll="doors", ajar=-18.0):
    """A screen door on the outside of the front door, hinged on the side
    away from the front door's own hinge, opening outwards."""
    y = -E - 0.012
    x0, x1 = DOOR.start + 0.02, DOOR.end - 0.02
    z0, z1, t = 0.01, DOOR.head - 0.03, 0.028
    mb = MeshBuilder()
    for xa, xb in ((x0, x0 + 0.075), (x1 - 0.075, x1)):
        mb.box((xa, y - t, z0), (xb, y, z1), "ext_trim")
    for za, zb in ((z0, z0 + 0.16), (0.95, 1.04), (z1 - 0.09, z1)):
        mb.box((x0 + 0.075, y - t, za), (x1 - 0.075, y, zb), "ext_trim")
    for za, zb in ((z0 + 0.16, 0.95), (1.04, z1 - 0.09)):                  # the mesh panels
        mb.rect(((x0 + x1) / 2, y - t / 2, (za + zb) / 2), ((x1 - x0) / 2 - 0.075, 0, 0), (0, 0, (zb - za) / 2),
                (0, -1, 0), "screen_mesh")
    mb.box((x1 - 0.06, y - t - 0.03, 1.0), (x1 - 0.035, y - t, 1.12), "metal_dark")   # pull handle
    door = mb.build("door_screen", coll, origin=(x0, y, 0.0))
    door.rotation_euler = (0, 0, math.radians(ajar))
    door["opens_degrees"] = -105.0
    door.visible_shadow = True
    return door


def trim(coll="exterior"):
    """Corner boards, a water table, and plain board casings round the openings."""
    mb = MeshBuilder()
    w, d = 0.11, 0.022
    x0, x1, y0, y1 = -E, plan.WIDTH + E, -E, plan.DEPTH + E
    for x, sx in ((x0, -1), (x1, 1)):
        for y, sy in ((y0, -1), (y1, 1)):
            mb.box((min(x, x + sx * d), min(y, y - sy * w), 0.0), (max(x, x + sx * d), max(y, y - sy * w), plan.ROOF_Z),
                   "ext_trim")
            mb.box((min(x, x - sx * w), min(y, y + sy * d), 0.0), (max(x, x - sx * w), max(y, y + sy * d), plan.ROOF_Z),
                   "ext_trim")
    for face, a0, a1 in ((OUT_S, x0, x1), (OUT_N, x0, x1), (OUT_W, y0, y1), (OUT_E, y0, y1)):
        face.box(mb, a0, a1, 0.0, 0.03, -0.01, 0.14, "ext_trim")
    faces = {"wall_ext_south": OUT_S, "wall_ext_north": OUT_N, "wall_ext_west": OUT_W}
    for wall in plan.WALLS:
        face = faces.get(wall.name)
        if not face:
            continue
        for o in wall.openings:
            c = 0.10
            face.box(mb, o.start - c, o.start, 0.0, d, o.sill - (0.0 if o.kind == "door" else 0.06), o.head + c, "ext_trim")
            face.box(mb, o.end, o.end + c, 0.0, d, o.sill - (0.0 if o.kind == "door" else 0.06), o.head + c, "ext_trim")
            face.box(mb, o.start - c - 0.02, o.end + c + 0.02, 0.0, d + 0.012, o.head + c, o.head + c + 0.035, "ext_trim")
            face.box(mb, o.start, o.end, 0.0, d, o.head, o.head + c, "ext_trim")
    return [mb.build("exterior_trim", coll, recalc=True)]


LAP = 0.115            # how much of each board shows
LAP_OUT = 0.016        # the bottom edge of a board stands this far off the wall
LAP_IN = 0.003         # and its top edge, tucked under the next board, this far
CASING = 0.10          # boards stop at the window and door casings


LAP_TILE = 16 * LAP      # the board texture repeats every 16 courses (assets.py, `laps`)


def _lap(mb, face, a0, a1, z0, z1, rng, base, a0_top=None, a1_top=None):
    """One clapboard: a face leaning out towards its bottom edge. The dark
    line under each board is in the texture as well as in the geometry, so
    it survives at a distance where a 13 mm ledge is smaller than a pixel.
    `base` is the height the courses are counted from."""
    a0_top = a0 if a0_top is None else a0_top
    a1_top = a1 if a1_top is None else a1_top
    if a1 - a0 < 0.02 or z1 - z0 < 0.008:
        return
    du, dv = rng.random(), rng.randrange(16) / 16.0      # every board is a different piece of wood
    pts = [face.P(a0, LAP_OUT, z0), face.P(a1, LAP_OUT, z0), face.P(a1_top, LAP_IN, z1), face.P(a0_top, LAP_IN, z1)]
    uvs = [(a / LAP_TILE + du, (z - base) / LAP_TILE + dv)
           for a, z in ((a0, z0), (a1, z0), (a1_top, z1), (a0_top, z1))]
    if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(face.normal) < 0:
        pts, uvs = pts[::-1], uvs[::-1]
    mb.face(pts, "ext_clapboard", uvs=uvs)


def clapboard(coll="exterior"):
    """Lapped boards on the four walls and the two gables. Each course is cut
    at the casings; a course that crosses the top or bottom of an opening
    keeps the part of the board above or below it."""
    rng = random.Random(11)
    made = []
    x0, x1, y0, y1 = -E, plan.WIDTH + E, -E, plan.DEPTH + E
    walls = (("south", OUT_S, x0, x1, "wall_ext_south"), ("north", OUT_N, x0, x1, "wall_ext_north"),
             ("west", OUT_W, y0, y1, "wall_ext_west"), ("east", OUT_E, y0, y1, "wall_ext_east"))
    bottom, top = 0.14, plan.ROOF_Z + 0.16
    courses = []
    z = bottom
    while z < top - 1e-6:
        courses.append((z, min(z + LAP, top)))
        z += LAP

    for name, face, lo, hi, wall_name in walls:
        wall = next(w for w in plan.WALLS if w.name == wall_name)
        holes = [(o.start - CASING, o.end + CASING, o.sill - (0.0 if o.kind == "door" else 0.06), o.head + CASING + 0.035)
                 for o in wall.openings]
        cuts = sorted({lo + 0.11, hi - 0.11} | {v for h in holes for v in h[:2]})
        mb = MeshBuilder()
        for z0, z1 in courses:
            spans = []                                   # (a0, a1, z0, z1) pieces of this course
            for a0, a1 in zip(cuts, cuts[1:]):
                am = (a0 + a1) / 2
                hole = next((h for h in holes if h[0] < am < h[1] and h[2] < z1 and h[3] > z0), None)
                if hole is None:
                    if spans and spans[-1][1] == a0 and spans[-1][2:] == (z0, z1):
                        spans[-1] = (spans[-1][0], a1, z0, z1)
                    else:
                        spans.append((a0, a1, z0, z1))
                else:
                    if hole[2] > z0 + 0.008:
                        spans.append((a0, a1, z0, hole[2]))
                    if hole[3] < z1 - 0.008:
                        spans.append((a0, a1, hole[3], z1))
            for a0, a1, za, zb in spans:
                _lap(mb, face, a0, a1, za, zb, rng, z0)
        made.append(mb.build(f"clapboard_{name}", coll))

    # The gables: the same courses, each one narrower than the last.
    over, rise = 0.35, 2.3
    mid, half = (y0 + y1) / 2, (y1 - y0) / 2 + over
    for name, face in (("gable_west", OUT_W), ("gable_east", OUT_E)):
        mb = MeshBuilder()
        z = top
        while z < top + rise - 0.02:
            z1 = min(z + LAP, top + rise - 0.01)
            w0, w1 = half * (1 - (z - top) / rise), half * (1 - (z1 - top) / rise)
            _lap(mb, face, mid - w0, mid + w0, z, z1, rng, z, mid - w1, mid + w1)
            z += LAP
        made.append(mb.build(f"clapboard_{name}", coll))
    return made


def gutters(coll="exterior"):
    mb = MeshBuilder()
    over = 0.35
    z = plan.ROOF_Z + 0.10
    x0, x1 = -E - 0.02, plan.WIDTH + E + 0.02
    for y, s in ((-E - over, -1), (plan.DEPTH + E + over, 1)):
        ya, yb = (y - 0.11, y) if s < 0 else (y, y + 0.11)
        mb.box((x0, ya, z - 0.09), (x1, yb, z), "metal_white", skip="+z")
        for x in (x0 + 0.08, x1 - 0.08):                                  # downpipe at each end
            ym = (ya + yb) / 2
            wall_y = (-E - 0.07) if s < 0 else (plan.DEPTH + E + 0.07)
            mb.cylinder((x, ym, z - 0.09), (0, wall_y - ym, -0.42), 0.035, "metal_white", segments=8, caps="none")
            mb.cylinder((x, wall_y, z - 0.51), (0, 0, GROUND + 0.25 - (z - 0.51)), 0.035, "metal_white", segments=8,
                        caps="none")
            mb.cylinder((x, wall_y, GROUND + 0.25), (0, s * 0.22, -0.2), 0.035, "metal_white", segments=8)
    return [mb.build("gutters", coll)]


def yard(coll="exterior"):
    made = []
    mb = MeshBuilder()
    cx = (DOOR.start + DOOR.end) / 2
    street_y = -8.6
    mb.box((-16, street_y, GROUND - 0.2), (24, 20, GROUND), "ground_grass", skip="-z")
    made.append(mb.build("yard_ground", coll))
    mb = MeshBuilder()
    mb.box((cx - 0.7, street_y, GROUND), (cx + 0.7, PORCH[2] - 0.56, GROUND + 0.025), "ground_path", skip="-z")
    mb.box((-16, street_y - 1.6, GROUND), (24, street_y, GROUND + 0.05), "ground_path", skip="-z")      # sidewalk
    made.append(mb.build("yard_paths", coll))
    mb = MeshBuilder()
    mb.box((-16, street_y - 9.5, GROUND - 0.2), (24, street_y - 1.6, GROUND - 0.08), "ground_road", skip="-z")
    made.append(mb.build("street_road", coll))

    # picket fence along the front, with a gap at the path; a few pickets missing or leaning
    rng = random.Random(3)
    mb = MeshBuilder()
    fy = street_y + 0.25
    for xa, xb in ((-9.0, cx - 0.85), (cx + 0.85, 13.0)):
        mb.box((xa, fy - 0.02, GROUND + 0.25), (xb, fy + 0.02, GROUND + 0.31), "ext_trim")
        mb.box((xa, fy - 0.02, GROUND + 0.72), (xb, fy + 0.02, GROUND + 0.78), "ext_trim")
        x = xa
        while x < xb:
            if rng.random() > 0.08:
                h = 0.95 + rng.uniform(-0.03, 0.03)
                mb.box((x, fy - 0.045, GROUND + 0.04), (x + 0.075, fy - 0.02, GROUND + h), "ext_trim")
            x += 0.135
        for px in (xa, xb):
            mb.box((px - 0.05, fy - 0.03, GROUND), (px + 0.05, fy + 0.07, GROUND + 1.08), "ext_trim", skip="-z")
    made.append(mb.build("fence_picket", coll, recalc=True))

    # mailbox by the path
    mb = MeshBuilder()
    mx, my = cx + 1.25, street_y + 0.05
    mb.box((mx - 0.045, my - 0.045, GROUND), (mx + 0.045, my + 0.045, GROUND + 1.05), "wood_dark", skip="-z")
    mb.box((mx - 0.09, my - 0.25, GROUND + 1.05), (mx + 0.09, my + 0.22, GROUND + 1.20), "metal_white")
    mb.cylinder((mx, my - 0.25, GROUND + 1.20), (0, 0.47, 0), 0.09, "metal_white", segments=12)
    mb.box((mx + 0.09, my + 0.05, GROUND + 1.12), (mx + 0.10, my + 0.07, GROUND + 1.30), "front_door_paint")
    made.append(mb.build("mailbox", coll))

    # telephone pole and a sodium streetlight on it
    mb = MeshBuilder()
    px, py = -4.2, street_y - 0.9
    mb.cylinder((px, py, GROUND), (0, 0, 8.4), 0.14, "wood_dark", segments=10, radius_top=0.10)
    mb.box((px - 1.1, py - 0.05, GROUND + 7.7), (px + 1.1, py + 0.05, GROUND + 7.82), "wood_dark")
    mb.cylinder((px, py, GROUND + 6.3), (1.5, 0.2, 0.35), 0.03, "metal_dark", segments=6)
    mb.box((px + 1.35, py + 0.08, GROUND + 6.52), (px + 1.95, py + 0.34, GROUND + 6.64), "metal_dark")
    mb.box((px + 1.42, py + 0.11, GROUND + 6.50), (px + 1.88, py + 0.31, GROUND + 6.52), "sodium_on")
    made.append(mb.build("telephone_pole", coll))
    dr.lightpoint("street_sodium", (px + 1.65, py + 0.21, GROUND + 6.40), "sodium", 250.0)
    return made


def porch_light(coll="exterior"):
    mb = MeshBuilder()
    x, y, z = DOOR.end + 0.32, -E, 1.95
    mb.box((x - 0.05, y - 0.02, z - 0.06), (x + 0.05, y, z + 0.06), "metal_dark")
    mb.box((x - 0.045, y - 0.13, z - 0.10), (x + 0.045, y - 0.02, z + 0.08), "glass_frosted")
    mb.box((x - 0.06, y - 0.15, z + 0.08), (x + 0.06, y, z + 0.10), "metal_dark")
    obj = mb.build("porch_light", coll)
    obj.visible_shadow = False
    dr.lightpoint("porch", (x, y - 0.08, z), "warm", 18.0)
    return [obj]


def weathering():
    d = Decals("decals_exterior", seed=31)
    OFF = LAP_OUT + 0.002                    # clear of the boards' bottom edges
    for face, lo, hi in ((OUT_S, -E, plan.WIDTH + E), (OUT_N, -E, plan.WIDTH + E),
                         (OUT_W, -E, plan.DEPTH + E), (OUT_E, -E, plan.DEPTH + E)):
        a = lo + 0.9
        while a < hi - 0.6:
            d.wall("moss", face, a, 0.62, 1.9, 0.9, offset=OFF)
            a += 1.7
        for a in (lo + 0.25, hi - 0.25):                                   # down from the gutter ends
            d.wall("grime_streaks", face, a, plan.ROOF_Z - 1.4, 0.9, 2.8, offset=OFF)
        d.wall("grime_streaks", face, (lo + hi) / 2 + 1.3, plan.ROOF_Z - 1.0, 1.1, 2.0, offset=OFF)
    for wall, face in (("wall_ext_south", OUT_S), ("wall_ext_north", OUT_N), ("wall_ext_west", OUT_W)):
        for o in next(w for w in plan.WALLS if w.name == wall).openings:
            if o.kind == "window":
                d.wall("grime_streaks", face, (o.start + o.end) / 2, o.sill - 0.75, o.width + 0.2, 1.3, offset=OFF)
    return d.build()


def build():
    made = porch() + [screen_door()] + trim() + clapboard() + gutters() + yard() + porch_light()
    weathering()
    return made
