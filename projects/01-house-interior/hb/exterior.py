"""The outside of the house (docs/ART_BIBLE.md): porch, screen door, trim,
gutters, the chimney stack, rake boards and ridge, yard, fence and a
streetlight, and the clapboard itself: one lapped board per course over the
flat wall the shell builder makes. What stands in the yard and against the
back wall is in yard.py."""

from __future__ import annotations

import math
import random

from mathutils import Vector

import plan
from . import dressing as dr
from . import shapes
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

# The roof, as shell.build_envelope makes it: eaves front and back, the ridge
# running east-west over the middle of the house.
OVER, RISE = 0.35, 2.3
EAVE_Z = plan.ROOF_Z + 0.16
RIDGE_Y = plan.DEPTH / 2
RIDGE_Z = EAVE_Z + RISE
ROOF_SLOPE = RISE / (RIDGE_Y + E + OVER)
VERGE = 0.14                   # how far the roof sails past each gable

# The chimney stack on the east wall, outside the chimney breast.
CHIMNEY_Y = (1.50, 3.10)       # the breast, to above the ground-floor ceiling
SHAFT_Y = (1.86, 2.74)         # the stack above its shoulders
CHIMNEY_OUT = 0.45             # how far it stands off the wall
SHOULDER_Z = (3.25, 4.00)
CHIMNEY_TOP = RIDGE_Z + 0.70


def roof_z(y):
    """Height of the roof surface over a point."""
    return EAVE_Z + min(y + E + OVER, plan.DEPTH + E + OVER - y) * ROOF_SLOPE


def _quad(mb, points, key, normal):
    """A face wound to look along `normal`, whatever order its points came in."""
    pts = [Vector(p) for p in points]
    if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(Vector(normal)) < 0:
        pts = pts[::-1]
    return mb.face(pts, key)


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
    # a knee brace from each post up to the beam, towards every bay it carries
    for k, x in enumerate(posts):
        for side in ((1,), (-1, 1), (-1, 1), (-1,))[k]:
            mb.prism([(0.055, -0.30), (0.055, -0.235), (0.29, 0.0), (0.225, 0.0)], (x, yf + 0.065, top),
                     (side, 0, 0), (0, 0, 1), (0, 1, 0), 0.04, "ext_trim")
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

    # What holds the roof up: rafters from a ledger on the wall out over the
    # beam, a fascia across their tails and a barge board down each side.
    mb = MeshBuilder()
    ya, za, zb = yf - 0.25, lo, hi
    slope = (zb - za) / (yb - ya)
    depth, n = 0.075, 9
    for k in range(n):
        x = x0 - 0.14 + (x1 - x0 + 0.28 - 0.045) * k / (n - 1)
        mb.prism([(ya + 0.02, za + slope * 0.02 - depth), (yb, zb - depth), (yb, zb), (ya + 0.02, za + slope * 0.02)],
                 (x, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0), 0.045, "ext_trim")
    mb.box((x0 - 0.2, yb - 0.035, zb - 0.14), (x1 + 0.2, yb, zb), "ext_trim")                 # ledger
    mb.box((x0 - 0.222, ya - 0.022, za - 0.10), (x1 + 0.222, ya, za + 0.05), "ext_trim")      # fascia
    for x in (x0 - 0.222, x1 + 0.2):
        mb.prism([(ya, za - 0.10), (yb, zb - 0.10), (yb, zb + 0.05), (ya, za + 0.05)],
                 (x, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0), 0.022, "ext_trim")
    made.append(mb.build("porch_rafters", coll, recalc=True))
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
    faces = {"wall_ext_south": OUT_S, "wall_ext_north": OUT_N, "wall_ext_west": OUT_W, "wall_ext_east": OUT_E}
    doorways = {face: sorted((o.start, o.end) for o in next(w for w in plan.WALLS if w.name == wall).openings
                             if o.kind == "door") for wall, face in faces.items()}
    for face, a0, a1 in ((OUT_S, x0, x1), (OUT_N, x0, x1), (OUT_W, y0, y1), (OUT_E, y0, y1)):
        # The water table runs round the house but stops at each doorway: across
        # one it would be a 14 cm board to step over.
        cursor = a0
        for start, end in doorways.get(face, []) + [(a1, a1)]:
            if start > cursor:
                face.box(mb, cursor, start, 0.0, 0.03, -0.01, 0.14, "ext_trim")
            cursor = max(cursor, end)
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
        if name == "east":                               # no boards behind the chimney stack
            mid_z = sum(SHOULDER_Z) / 2
            holes += [(CHIMNEY_Y[0], CHIMNEY_Y[1], -1.0, mid_z), (SHAFT_Y[0], SHAFT_Y[1], mid_z, 99.0)]
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


def yard(coll="lot"):
    """The lot and the street as the house first had them. The town replaces
    all seven of these objects (docs/TOWN.md), so they keep their names and
    places, and live in a collection of their own that a scene linking this
    file can leave out."""
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


def chimney(coll="exterior"):
    """The brick stack the fireplace needs: a breast the width of the one
    indoors, drawn in over two cement-washed shoulders to a stack that goes
    up past the ridge. From just under the roof the stack is its full depth,
    standing on the wall, so it comes up through the verge of the roof with
    lead round it. Two pots on a concrete crown."""
    mb = MeshBuilder()
    xw = plan.WIDTH + E
    xo = xw + CHIMNEY_OUT
    xi = plan.WIDTH - 0.02                               # the stack's inner face, over the wall
    (y0, y1), (s0, s1), (zs0, zs1) = CHIMNEY_Y, SHAFT_Y, SHOULDER_Z
    z_full = roof_z(s0) - 0.12
    top = CHIMNEY_TOP
    brick, wash = "ext_brick", "stone_sill"
    mb.box((xw, y0, GROUND - 0.10), (xo, y1, zs0), brick, skip="-x-z+z")
    _quad(mb, [(xo, y0, zs0), (xo, y1, zs0), (xo, s1, zs1), (xo, s0, zs1)], brick, (1, 0, 0))
    _quad(mb, [(xw, y0, zs0), (xo, y0, zs0), (xo, s0, zs1), (xw, s0, zs1)], wash, (0, -1, 1))
    _quad(mb, [(xw, y1, zs0), (xo, y1, zs0), (xo, s1, zs1), (xw, s1, zs1)], wash, (0, 1, 1))
    mb.box((xw, s0, zs1), (xo, s1, z_full), brick, skip="-x-z+z")
    mb.box((xi, s0, z_full), (xo, s1, top - 0.24), brick, skip="-z+z")
    mb.box((xi - 0.03, s0 - 0.03, top - 0.24), (xo + 0.03, s1 + 0.03, top - 0.15), brick)          # two oversailing courses
    mb.box((xi - 0.055, s0 - 0.055, top - 0.15), (xo + 0.055, s1 + 0.055, top - 0.06), brick)
    mb.box((xi - 0.075, s0 - 0.075, top - 0.06), (xo + 0.075, s1 + 0.075, top), "foundation")     # the crown
    cx = (xi + xo) / 2
    for py in (s0 + 0.24, s1 - 0.24):                    # the pots
        shapes.lathe(mb, cx, py, [(0.105, top), (0.092, top + 0.05), (0.082, top + 0.30), (0.10, top + 0.325),
                                  (0.10, top + 0.345), (0.07, top + 0.345)], brick, 12, cap_first=False, cap_last=False)
        mb.face(shapes.ring(cx, py, top + 0.31, 0.07, 0.07, 12), "soot")
    stack = mb.build("chimney", coll)

    # lead where the stack comes through the roof
    lead = MeshBuilder()
    t, up = 0.004, 0.15
    xe = xw + VERGE + 0.004
    _quad(lead, [(xi - t, s0, roof_z(s0) - 0.02), (xi - t, s1, roof_z(s1) - 0.02), (xi - t, s1, roof_z(s1) + up),
                 (xi - t, s0, roof_z(s0) + up)], "metal_galv", (-1, 0, 0))
    for y, n in ((s0 - t, -1), (s1 + t, 1)):
        _quad(lead, [(xi - t, y, roof_z(y) - 0.02), (xe, y, roof_z(y) - 0.02), (xe, y, roof_z(y) + up),
                     (xi - t, y, roof_z(y) + up)], "metal_galv", (0, n, 0))
    # an apron lying on the slates below the stack, and a soaker up the slope beside it
    ya, yb = s0 - 0.16, s0
    lift = Vector((0, 0, 0.006))
    _quad(lead, [Vector((xi - 0.12, ya, roof_z(ya))) + lift, Vector((xe, ya, roof_z(ya))) + lift,
                 Vector((xe, yb, roof_z(yb))) + lift, Vector((xi - 0.12, yb, roof_z(yb))) + lift], "metal_galv", (0, -1, 2))
    _quad(lead, [Vector((xi - 0.12, s0, roof_z(s0))) + lift, Vector((xi, s0, roof_z(s0))) + lift,
                 Vector((xi, s1 + 0.1, roof_z(s1 + 0.1))) + lift, Vector((xi - 0.12, s1 + 0.1, roof_z(s1 + 0.1))) + lift],
          "metal_galv", (0, -1, 2))
    flashing = lead.build("chimney_flashing", coll)
    return [stack, flashing]


def roof_details(coll="exterior"):
    """What finishes a roof: the slates carried past each gable on a verge
    with a rake board under it, a ridge roll, and the soil stack's vent."""
    made = []
    x0, x1 = -E, plan.WIDTH + E
    ys, yn = -E - OVER, plan.DEPTH + E + OVER
    mb = MeshBuilder()
    for xg, s in ((x0, -1), (x1, 1)):
        xo = xg + s * VERGE
        lift = Vector((0, 0, 0.004))
        for ya, yb in ((ys, RIDGE_Y), (RIDGE_Y, yn)):                                    # the verge, slated
            za, zb = roof_z(ya), roof_z(yb)
            n = (0, -1, 2) if yb <= RIDGE_Y else (0, 1, 2)
            _quad(mb, [Vector((xg, ya, za)) + lift, Vector((xo, ya, za)) + lift, Vector((xo, yb, zb)) + lift,
                       Vector((xg, yb, zb)) + lift], "roof", n)
            _quad(mb, [(xg, ya, za - 0.012), (xo, ya, za - 0.012), (xo, yb, zb - 0.012), (xg, yb, zb - 0.012)],
                  "ext_trim", (0, -n[1], -2))                                           # its soffit
            # the rake board at its edge, and a narrower board against the wall under it
            for xa, drop, thick in ((xo - (0.028 if s > 0 else 0.0), 0.19, 0.028),
                                    (xg + (0.0 if s > 0 else -0.02), 0.11, 0.02)):
                mb.prism([(ya, za - drop), (yb, zb - drop), (yb, zb + 0.004), (ya, za + 0.004)], (xa, 0, 0),
                         (0, 1, 0), (0, 0, 1), (1, 0, 0), thick, "ext_trim")
        # the eaves fascias turn the corner under the verge
        for y, sy in ((ys, -1), (yn, 1)):
            mb.box((min(xg, xo), min(y, y + sy * 0.025), EAVE_Z - 0.17), (max(xg, xo), max(y, y + sy * 0.025), EAVE_Z + 0.035),
                   "ext_trim")
    made.append(mb.build("roof_verges", coll))

    mb = MeshBuilder()
    e, w, t = 0.012, 0.17, 0.014
    drop = w * ROOF_SLOPE
    mb.prism([(-w, -drop + e), (0.0, e), (w, -drop + e), (w, -drop + e + t), (0.0, e + t + 0.004), (-w, -drop + e + t)],
             (x0 - VERGE - 0.02, RIDGE_Y, RIDGE_Z), (0, 1, 0), (0, 0, 1), (1, 0, 0), x1 - x0 + 2 * VERGE + 0.04,
             "metal_galv")
    # the vent of the soil stack, through the back slope over the bathroom
    vx, vy = 3.95, 7.42
    vz = roof_z(vy)
    mb.cylinder((vx, vy, vz - 0.10), (0, 0, 0.62), 0.05, "metal_galv", segments=10)
    shapes.lathe(mb, vx, vy, [(0.17, vz - 0.07), (0.075, vz + 0.085), (0.055, vz + 0.11)], "metal_galv", 10,
                 cap_first=False, cap_last=False)
    made.append(shapes.soften(mb.build("roof_ridge", coll, recalc=True)))
    return made


def blocked(wall_name, extra=()):
    """Where nothing may be stuck on a wall: its openings with their casings,
    as (a0, a1, z0, z1), plus whatever stands against it."""
    wall = next(w for w in plan.WALLS if w.name == wall_name)
    return [(o.start - 0.14, o.end + 0.14, o.sill - 0.08, o.head + 0.16) for o in wall.openings] + list(extra)


def clear(zones, a0, a1, z0, z1):
    return not any(a0 < b[1] and a1 > b[0] and z0 < b[3] and z1 > b[2] for b in zones)


# What stands against each wall and hides its foot: the porch, the back
# steps, the chimney. (a0, a1, z0, z1)
AGAINST = {
    "wall_ext_south": [(PORCH[0] - 0.25, PORCH[1] + 0.25, -1.0, 3.30)],
    "wall_ext_north": [(0.95, 2.65, -1.0, 0.16)],
    "wall_ext_west": [],
    "wall_ext_east": [(CHIMNEY_Y[0] - 0.06, CHIMNEY_Y[1] + 0.06, -1.0, SHOULDER_Z[1]),
                      (SHAFT_Y[0] - 0.06, SHAFT_Y[1] + 0.06, SHOULDER_Z[1], 99.0)],
}
SPLASH_H = 0.95                # how far the mud reaches up from the ground


def weathering():
    """Moss, mud and rain marks. Nothing is at one height or one spacing, and
    nothing is laid across a door, a window, the porch or the chimney."""
    d = Decals("decals_exterior", seed=31)
    rng = d.rng
    OFF = LAP_OUT + 0.002                    # clear of the boards' bottom edges
    PLINTH = 0.0335                          # clear of the block plinth and the water table
    walls = (("wall_ext_south", OUT_S, -E, plan.WIDTH + E, True, 0.45),
             ("wall_ext_north", OUT_N, -E, plan.WIDTH + E, True, 0.95),     # the north side never dries
             ("wall_ext_west", OUT_W, -E, plan.DEPTH + E, False, 0.7),
             ("wall_ext_east", OUT_E, -E, plan.DEPTH + E, False, 0.6))
    split = (0.14 - GROUND) / SPLASH_H
    for name, face, lo, hi, eave, damp in walls:
        zones = blocked(name, AGAINST[name])
        # moss up from the water table, in clumps of every size
        a = lo + rng.uniform(0.3, 1.3)
        while a < hi - 0.5:
            w, h = rng.uniform(0.8, 2.3), rng.uniform(0.28, 0.95)
            if rng.random() < damp and a - w / 2 > lo + 0.1 and a + w / 2 < hi - 0.1 \
                    and clear(zones, a - w / 2, a + w / 2, 0.14, 0.14 + h):
                d.wall("moss", face, a, 0.14 + h / 2, w, h, offset=OFF)
            a += w * rng.uniform(0.55, 1.7)
        # mud splashed up the plinth and the bottom boards
        a = lo + 0.12
        while a < hi - 0.4:
            w = min(rng.uniform(1.7, 2.6), hi - 0.12 - a)
            if clear(zones, a, a + w, GROUND, -0.01):
                u0 = rng.random()
                u1 = u0 + w / 2.55
                d.wall("splash", face, a + w / 2, (GROUND + 0.14) / 2, w, 0.14 - GROUND, flip=False, offset=PLINTH,
                       uv=(u0, 0.0, u1, split))
                if clear(zones, a, a + w, 0.14, GROUND + SPLASH_H):
                    d.wall("splash", face, a + w / 2, (0.14 + GROUND + SPLASH_H) / 2, w, GROUND + SPLASH_H - 0.14,
                           flip=False, offset=OFF, uv=(u0, split, u1, 1.0))
            a += w
        # rain marks: down from the gutters on the eaves walls ...
        if eave:
            spots = [lo + 0.3, hi - 0.3] + [rng.uniform(lo + 1.0, hi - 1.0) for _ in range(4)]
            for a in spots:
                w, h = rng.uniform(0.7, 1.4), rng.uniform(1.3, 3.0)
                top = plan.ROOF_Z + 0.14
                if clear(zones, a - w / 2, a + w / 2, top - h, top):
                    d.wall("runoff", face, a, top - h / 2, w, h, offset=OFF)
        # ... and below every window sill
        wall = next(w_ for w_ in plan.WALLS if w_.name == name)
        for o in wall.openings:
            if o.kind != "window" or o.head - o.sill < 0.6:
                continue
            others = [z for z in zones if not (abs(z[0] - (o.start - 0.14)) < 1e-6 and abs(z[2] - (o.sill - 0.08)) < 1e-6)]
            w, top = o.width + rng.uniform(0.1, 0.35), o.sill - 0.075
            for h in (rng.uniform(0.9, 1.5), 0.55):
                if clear(others, o.start, o.end, top - h, top):
                    d.wall("runoff", face, (o.start + o.end) / 2, top - h / 2, w, h, offset=OFF)
                    break
    # the chimney: soot and rain down from its crown, damp at its foot
    out = Face("y", plan.WIDTH + E + CHIMNEY_OUT, 1)
    mid = sum(SHAFT_Y) / 2
    d.wall("runoff", out, mid, CHIMNEY_TOP - 1.1, 0.86, 1.9, offset=0.003)
    d.wall("runoff", out, mid, SHOULDER_Z[0] - 0.9, 1.5, 1.8, offset=0.003)
    d.wall("moss", out, sum(CHIMNEY_Y) / 2, 0.02, 1.5, 0.8, offset=0.003)
    d.wall("splash", out, sum(CHIMNEY_Y) / 2, GROUND + SPLASH_H / 2, 1.6, SPLASH_H, flip=False, offset=0.004)
    return d.build()


def build():
    from . import yard as back                      # yard.py: what stands behind and beside the house
    made = porch() + [screen_door()] + trim() + clapboard() + gutters() + yard() + porch_light()
    made += chimney() + roof_details()
    made += back.build()
    weathering()
    return made
