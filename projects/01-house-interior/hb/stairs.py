"""The stair: steps, strings, the panelled side with its cupboard, balustrades
and the collider ramp.

One straight flight along the west wall, climbing north. All positions come
from plan.py.
"""

from __future__ import annotations

import math

from mathutils import Vector

import plan
from .core import MeshBuilder, empty

X0, X1 = plan.STAIR_X0, plan.STAIR_X1        # treads span the west wall to here
Y0, Y1 = plan.STAIR_Y0, plan.STAIR_Y1
N, RISE, TREAD = plan.RISERS, plan.RISE, plan.TREAD
TOP = plan.FFL[1]

EDGE = plan.VOID_X1                          # outer face of the string, 1.15
BAL_X = (X1 + EDGE) / 2                      # balusters stand on the string
NOSE = 0.025
TREAD_T = 0.035
SLOPE = RISE / TREAD

CUPBOARD_DOOR = (4.75, 5.45, 1.25)           # y0, y1, height
LANDING_RAIL = 0.95                          # handrail height above the landing
LANDING_BAL_X = EDGE + 0.04                  # landing balustrade, on the floor edge
LANDING_BAL_Y = plan.VOID_Y0 - 0.04


def inner_line(y):
    """Height of the line through the back of each tread."""
    return SLOPE * (y - Y0)


def string_top(y):
    """Top edge of the strings: just above the nosings, level with the landing at the head."""
    return min(inner_line(y) + RISE + 0.05, TOP)


def rail_top(y):
    """Top of the raking handrail, 0.90 m above the nosings."""
    return inner_line(y) + RISE + 0.90


def soffit(y):
    """Underside of the flight."""
    return inner_line(y) - 0.12


def build_steps(coll, detail=True, override=None):
    tread_key = override or "wood_stair"
    riser_key = override or "trim_paint"
    mb = MeshBuilder()
    cx, hx = (X0 + X1) / 2, (X1 - X0) / 2
    for i in range(N):
        y = Y0 + i * TREAD
        z_lo, z_hi = i * RISE, (i + 1) * RISE
        last = i == N - 1
        nose = NOSE if detail else 0.0
        t = TREAD_T if detail else 0.0
        # riser
        mb.rect((cx, y, (z_lo + z_hi - t) / 2), (hx, 0, 0), (0, 0, (z_hi - t - z_lo) / 2), (0, -1, 0), riser_key)
        # tread (the top step is the edge of the landing floor)
        depth_end = y if last else y + TREAD
        if not last or detail:
            mb.rect((cx, (y - nose + depth_end) / 2, z_hi), (hx, 0, 0), (0, (depth_end - (y - nose)) / 2, 0),
                    (0, 0, 1), tread_key, rot=True)
        if detail:
            mb.rect((cx, y - nose, z_hi - t / 2), (hx, 0, 0), (0, 0, t / 2), (0, -1, 0), tread_key, rot=True)
            mb.rect((cx, y - nose / 2, z_hi - t), (hx, 0, 0), (0, nose / 2, 0), (0, 0, -1), tread_key, rot=True)
    return mb.build("stairs", coll)


def _sloped_face(mb, x, ya, yb, lo, hi, normal_x, key):
    """A face in the plane x between two height functions, from ya to yb."""
    pts = [(x, ya, lo(ya)), (x, yb, lo(yb)), (x, yb, hi(yb)), (x, ya, hi(ya))]
    if hi(ya) - lo(ya) < 1e-5:
        pts = [pts[0], pts[1], pts[2]]
    elif hi(yb) - lo(yb) < 1e-5:
        pts = [pts[0], pts[1], pts[3]]
    if normal_x > 0:
        pts = pts[::-1]
    # Seen from +x, counter-clockwise runs y increasing along the bottom.
    mb.face(pts[::-1], key)


def build_strings(coll, detail=True, override=None):
    """The boards either side of the flight, the panelled side facing the
    hall, the underside, and the inside of the cupboard."""
    paint = override or "trim_paint"
    plaster = override or "wall_hall"
    mb = MeshBuilder()
    zero = lambda y: 0.0                                   # noqa: E731
    y_level = Y0 + (TOP - RISE - 0.05) / SLOPE             # where the string reaches landing level
    d0, d1, dh = CUPBOARD_DOOR

    # Hall side: clipped under the first floor, which carries on above it.
    def hall_top(y):
        return min(string_top(y), plan.CEILING) if y >= plan.VOID_Y0 - 1e-6 else string_top(y)

    y_clip = Y0 + (plan.CEILING - RISE - 0.05) / SLOPE     # string top reaches the ceiling
    cuts = sorted({Y0, d0, d1, y_clip, Y1})
    for ya, yb in zip(cuts, cuts[1:]):
        if detail and abs(ya - d0) < 1e-6 and abs(yb - d1) < 1e-6:
            _sloped_face(mb, EDGE, ya, yb, lambda y: dh, hall_top, 1, paint)       # over the door
            continue
        _sloped_face(mb, EDGE, ya, yb, zero, hall_top, 1, paint)

    # Stair side of the outer string, and its top edge.
    for ya, yb in ((Y0, y_level), (y_level, Y1)):
        _sloped_face(mb, X1, ya, yb, inner_line, string_top, -1, paint)
        mb.face([(X1, ya, string_top(ya)), (EDGE, ya, string_top(ya)),
                 (EDGE, yb, string_top(yb)), (X1, yb, string_top(yb))], paint)
    mb.rect(((X1 + EDGE) / 2, Y0, string_top(Y0) / 2), ((EDGE - X1) / 2, 0, 0), (0, 0, string_top(Y0) / 2),
            (0, -1, 0), paint)

    if detail:
        # Wall string: the skirting that follows the flight up the wall.
        w = 0.022
        for ya, yb in ((Y0, y_level), (y_level, Y1)):
            _sloped_face(mb, X0 + w, ya, yb, inner_line, string_top, 1, paint)
            mb.face([(X0, ya, string_top(ya)), (X0 + w, ya, string_top(ya)),
                     (X0 + w, yb, string_top(yb)), (X0, yb, string_top(yb))], paint)

        # Cupboard door reveals.
        for y, n in ((d0, 1), (d1, -1)):
            mb.rect(((X1 + EDGE) / 2, y, dh / 2), ((EDGE - X1) / 2, 0, 0), (0, 0, dh / 2), (0, n, 0), paint)
        mb.rect(((X1 + EDGE) / 2, (d0 + d1) / 2, dh), ((EDGE - X1) / 2, 0, 0), (0, (d1 - d0) / 2, 0),
                (0, 0, -1), paint)

    # Underside of the flight and the inside of the cupboard.
    ys = Y0 + 0.12 / SLOPE                                 # where the underside meets the floor
    mb.face([(X0, ys, 0.0), (X0, Y1, soffit(Y1)), (X1, Y1, soffit(Y1)), (X1, ys, 0.0)], plaster)
    inner_cuts = sorted({ys, d0, d1, Y1})
    for ya, yb in zip(inner_cuts, inner_cuts[1:]):
        lo = (lambda y: dh) if (detail and abs(ya - d0) < 1e-6 and abs(yb - d1) < 1e-6) else zero
        _sloped_face(mb, X1, ya, yb, lo, soffit, -1, plaster)
    # North end, under the head of the stair.
    mb.rect(((X0 + EDGE) / 2, Y1, plan.CEILING / 2), ((EDGE - X0) / 2, 0, 0), (0, 0, plan.CEILING / 2),
            (0, 1, 0), plaster)
    return mb.build("stairs_strings", coll)


def _post(mb, x, y, z0, z1, size, key, cap_key=None):
    h = size / 2
    mb.box((x - h, y - h, z0), (x + h, y + h, z1), key, skip="-z")
    if cap_key:
        mb.box((x - h - 0.012, y - h - 0.012, z1), (x + h + 0.012, y + h + 0.012, z1 + 0.025), cap_key)
        top = (x, y, z1 + 0.075)
        c = h - 0.005
        base = [(x - c, y - c, z1 + 0.025), (x + c, y - c, z1 + 0.025),
                (x + c, y + c, z1 + 0.025), (x - c, y + c, z1 + 0.025)]
        for a, b in zip(base, base[1:] + base[:1]):
            mb.face([a, b, top], cap_key)


def build_balustrades(coll):
    paint, wood = "trim_paint", "wood_dark"
    made = []

    # --- Raking balustrade on the outer string -----------------------------
    mb = MeshBuilder()
    newel = 0.10
    _post(mb, BAL_X, Y0 - newel / 2, 0.0, 1.22, newel, paint, wood)
    limit = plan.CEILING                                   # the first floor's edge above
    y_end = Y0 + (limit - RISE - 0.90) / SLOPE             # the rail runs into the floor edge here
    rw, rh = 0.06, 0.05
    for a, b in ((Y0, y_end),):
        pa = Vector((BAL_X, a, rail_top(a)))
        pb = Vector((BAL_X, b, rail_top(b)))
        w = (pb - pa)
        mb.prism([(-rw / 2, -rh), (rw / 2, -rh), (rw / 2, 0), (-rw / 2, 0)], pa,
                 (1, 0, 0), (0, 0, 1), w.normalized(), w.length, wood)
    b_size = 0.032
    for i in range(N - 1):
        for f in (0.07, 0.21):
            y = Y0 + i * TREAD + f
            z0 = string_top(y)
            z1 = rail_top(y) - rh
            if y >= plan.VOID_Y0:
                z1 = min(z1, limit)
            if z1 - z0 > 0.06:
                h = b_size / 2
                mb.box((BAL_X - h, y - h, z0), (BAL_X + h, y + h, z1), paint, skip="-z+z")
    made.append(mb.build("stairs_balustrade", coll))

    # --- Landing balustrade around the stairwell ---------------------------
    mb = MeshBuilder()
    zf = TOP
    zr = zf + LANDING_RAIL
    x, y_s, y_n = LANDING_BAL_X, LANDING_BAL_Y, Y1 - 0.05
    _post(mb, x, y_s, zf, zr + 0.12, 0.09, paint, wood)       # corner
    _post(mb, x, y_n, zf, zr + 0.12, 0.09, paint, wood)       # head of the stair
    mb.box((x - rw / 2, y_s + 0.045, zr - rh), (x + rw / 2, y_n - 0.045, zr), wood)
    mb.box((0.0, y_s - rw / 2, zr - rh), (x - 0.045, y_s + rw / 2, zr), wood)
    h = b_size / 2
    count = int((y_n - y_s - 0.09) / 0.12)
    for i in range(1, count + 1):
        y = y_s + 0.045 + (y_n - y_s - 0.09) * i / (count + 1)
        mb.box((x - h, y - h, zf), (x + h, y + h, zr - rh), paint, skip="-z+z")
    count = int((x - 0.045) / 0.12)
    for i in range(1, count + 1):
        bx = (x - 0.045) * i / (count + 1)
        mb.box((bx - h, y_s - h, zf), (bx + h, y_s + h, zr - rh), paint, skip="-z+z")
    made.append(mb.build("landing_balustrade", coll))

    # --- Handrail on the wall, with brackets --------------------------------
    mb = MeshBuilder()
    ya, yb = Y0 - 0.15, Y1 + 0.10
    rx = 0.075
    pa, pb = Vector((rx, ya, rail_top(ya))), Vector((rx, yb, rail_top(yb)))
    mb.cylinder(pa, pb - pa, 0.022, wood, segments=8)
    for k in range(6):
        y = ya + 0.25 + (yb - ya - 0.5) * k / 5
        z = rail_top(y) - 0.022
        mb.box((0.0, y - 0.012, z - 0.06), (0.012, y + 0.012, z + 0.01), "metal_brass")
        mb.box((0.012, y - 0.008, z - 0.035), (rx, y + 0.008, z - 0.02), "metal_brass")
    obj = mb.build("handrail_wall", coll)
    made.append(obj)
    return made


def build_cupboard_door(coll, angle_deg=22.0):
    """The cupboard door under the stair, hinged on its north edge and left ajar."""
    d0, d1, dh = CUPBOARD_DOOR
    width, t = d1 - d0 - 0.006, 0.028
    hinge = (EDGE, d1 - 0.003, 0.0)
    mb = MeshBuilder()
    # Built closed, in world position; the origin is moved to the hinge.
    mb.box((EDGE - t, d1 - 0.003 - width, 0.004), (EDGE, d1 - 0.003, dh - 0.004), "trim_paint")
    # Three ledges on the back, and a turn button on the front.
    for z in (0.18, dh / 2, dh - 0.18):
        mb.box((EDGE - t - 0.018, d1 - width + 0.03, z - 0.045), (EDGE - t, d1 - 0.03, z + 0.045), "trim_paint",
               skip="+x")
    mb.cylinder((EDGE, d0 + 0.06, dh * 0.55), (0.022, 0, 0), 0.016, "metal_brass", segments=10)
    obj = mb.build("door_understair", coll, origin=hinge)
    obj.rotation_euler = (0, 0, math.radians(angle_deg))
    return obj


def build_collider(coll):
    """A wedge the player walks on instead of the steps. Convex, so Godot can
    turn it into a convex collision shape: the '-convcolonly' suffix tells
    Godot's importer to do that and to drop the visible mesh."""
    mb = MeshBuilder()
    ya = Y0 - TREAD
    profile = [(ya, 0.0), (Y1, 0.0), (Y1, TOP)]
    near = [Vector((X0, y, z)) for y, z in profile]
    far = [Vector((X1, y, z)) for y, z in profile]
    mb.face(near, "collider")
    mb.face(far[::-1], "collider")
    for i in range(3):
        j = (i + 1) % 3
        mb.face([near[j], near[i], far[i], far[j]], "collider")
    obj = mb.build("stairs_ramp-convcolonly", coll, recalc=True)
    obj.display_type = "WIRE"
    obj.hide_render = True
    obj.visible_camera = False
    obj["collider"] = "stairs"
    return obj


def build(detail=True, override=None, coll="stairs"):
    made = [build_steps(coll, detail, override), build_strings(coll, detail, override)]
    if detail:
        made += build_balustrades(coll)
        made.append(build_cupboard_door(coll))
    made.append(build_collider("colliders"))
    return made
