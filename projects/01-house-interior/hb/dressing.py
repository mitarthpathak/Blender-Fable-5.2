"""Procedural dressing: curtains, radiators, switches, cables, lamps, rugs,
books, loose paper and the grime and damage decals.

Most of it hangs on a wall, so pieces are described on a `Face`: a along the
wall, d out from it into the room, z up.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

import assets
import labels
import plan
from . import core, shapes
from .core import MeshBuilder


class Face:
    """One side of a wall. `axis` is the direction the wall runs, `c` the
    position of the surface, `sign` which way it looks."""

    def __init__(self, axis: str, c: float, sign: int):
        self.axis, self.c, self.sign = axis, c, sign

    def P(self, a, d, z):
        return Vector((a, self.c + self.sign * d, z)) if self.axis == "x" \
            else Vector((self.c + self.sign * d, a, z))

    @property
    def normal(self):
        return Vector((0, self.sign, 0)) if self.axis == "x" else Vector((self.sign, 0, 0))

    @property
    def along(self):
        return Vector((1, 0, 0)) if self.axis == "x" else Vector((0, 1, 0))

    def box(self, mb, a0, a1, d0, d1, z0, z1, key, skip=""):
        p, q = self.P(a0, d0, z0), self.P(a1, d1, z1)
        lo = (min(p.x, q.x), min(p.y, q.y), min(p.z, q.z))
        hi = (max(p.x, q.x), max(p.y, q.y), max(p.z, q.z))
        mb.box(lo, hi, key, skip=skip)

    @property
    def facing(self) -> float:
        """Compass angle of the direction this face looks, for placing models."""
        n = self.normal
        return math.degrees(math.atan2(n.y, n.x))


F1 = plan.FFL[1]
SOUTH = Face("x", 0.0, 1)
NORTH = Face("x", plan.DEPTH, -1)
WEST = Face("y", 0.0, 1)
EAST = Face("y", plan.WIDTH, -1)
HALL_EAST = Face("y", plan.PART_X0, -1)            # the partition, seen from the hall and landing
ROOM_WEST = Face("y", plan.PART_X1, 1)             # the partition, seen from the rooms
DIVIDER_S = Face("x", plan.DIVIDER_Y0, -1)         # the front rooms' side: living room, bedroom
DIVIDER_N = Face("x", plan.DIVIDER_Y1, 1)          # the back rooms' side: kitchen, bathroom
CHIMNEY = Face("y", 6.95, -1)
UTIL_EAST_IN = Face("y", plan.UTIL_X1, -1)                       # utility cupboard, its east wall
UTIL_EAST_OUT = Face("y", plan.UTIL_X1 + plan.INT_T, 1)          # the same wall from the bathroom
UTIL_NORTH_IN = Face("x", plan.UTIL_Y1, -1)
UTIL_NORTH_OUT = Face("x", plan.UTIL_Y1 + plan.INT_T, 1)


# --- Light points -----------------------------------------------------------

def lightpoint(name, location, kind, watts=40.0, colour=None, haze=True):
    """Mark where a lamp's bulb is. The lighting phase turns these into lights.
    `colour` (r, g, b) replaces the warm tungsten default: a fluorescent tube.
    `haze=False` stops the lamp lighting the render-only haze: a lamp that
    lights a whole room through it leaves the render blotchy."""
    obj = core.empty("lightpoint_" + name, "lightpoints", location)
    obj["kind"] = kind
    obj["watts"] = watts
    if colour:
        obj["colour"] = list(colour)
    obj["haze"] = bool(haze)
    return obj


def _bulb(mb, centre, radius, key):
    c = Vector(centre)
    rings = [(-1.0, 0.0), (-0.7, 0.71), (0.0, 1.0), (0.7, 0.71), (1.0, 0.0)]
    for (z0, r0), (z1, r1) in zip(rings, rings[1:]):
        mb.cylinder(c + Vector((0, 0, z0 * radius)), (0, 0, (z1 - z0) * radius), max(r0 * radius, 1e-4), key,
                    segments=10, caps="none", radius_top=max(r1 * radius, 1e-4))


def table_lamp(name, base, kind="warm", watts=40.0, coll="lamps", shade="lampshade_lit"):
    x, y, z = base
    mb = MeshBuilder()
    mb.cylinder((x, y, z), (0, 0, 0.018), 0.07, "ceramic", segments=16)
    mb.cylinder((x, y, z + 0.018), (0, 0, 0.07), 0.05, "ceramic", segments=16, caps="none", radius_top=0.065)
    mb.cylinder((x, y, z + 0.088), (0, 0, 0.08), 0.065, "ceramic", segments=16, caps="top", radius_top=0.025)
    mb.cylinder((x, y, z + 0.168), (0, 0, 0.09), 0.008, "metal_brass", segments=8)
    lit = kind != "off"
    _bulb(mb, (x, y, z + 0.30), 0.028, "bulb_on" if lit else "bulb_off")
    obj = mb.build("lamp_" + name, coll, smooth=True)
    # The shade is its own object: it is translucent, so it must not shadow the bulb.
    sh = MeshBuilder()
    sh.cylinder((x, y, z + 0.235), (0, 0, 0.19), 0.165, shade if lit else "lampshade", segments=20, caps="none",
                radius_top=0.105)
    shade_obj = sh.build("shade_" + name, coll, smooth=True)
    shade_obj.visible_shadow = False
    if lit:
        lightpoint(name, (x, y, z + 0.31), kind, watts)
    return obj


# Pendant shades, as (radius, height below the lampholder) profiles from the
# top of the shade down. No two rooms were fitted out in the same year.
SHADES = {
    "cone": [(0.035, 0.035), (0.17, -0.085)],                                                   # a plain coolie shade
    "drum": [(0.045, 0.045), (0.135, 0.030), (0.150, -0.150)],                                  # a fabric drum
    "bell": [(0.030, 0.050), (0.050, 0.020), (0.075, -0.045), (0.125, -0.100), (0.150, -0.112)],   # pressed glass
    "globe": [(0.030, 0.045), (0.085, 0.010), (0.118, -0.055), (0.100, -0.125), (0.050, -0.165), (0.0, -0.172)],
    "pleated": [(0.040, 0.040), (0.095, 0.000), (0.185, -0.110)],                               # with a scalloped rim
}


def pendant(name, x, y, ceiling, drop=0.55, kind="off", watts=40.0, coll="lamps", style="cone", tilt=0.0):
    """A ceiling pendant. `style` picks the shade from SHADES, or "bare" for
    a bulb on its flex and nothing else. `tilt` (degrees) hangs a shade
    crooked on its holder."""
    mb = MeshBuilder()
    mb.cylinder((x, y, ceiling - 0.022), (0, 0, 0.022), 0.055, "plastic_white", segments=14)
    mb.cylinder((x, y, ceiling - drop + 0.05), (0, 0, drop - 0.07), 0.0035, "plastic_black", segments=6,
                caps="none")
    mb.cylinder((x, y, ceiling - drop), (0, 0, 0.055), 0.019, "plastic_white", segments=10)
    lit = kind != "off"
    _bulb(mb, (x, y, ceiling - drop - 0.03), 0.03, "bulb_on" if lit else "bulb_off")
    obj = mb.build("pendant_" + name, coll, smooth=True)
    if style != "bare":
        profile = SHADES[style]
        glass = style in ("bell", "globe")
        key = ("glass_frosted" if glass else "lampshade_lit" if lit else "lampshade")
        n = 24
        tz = math.tan(math.radians(tilt))
        sh = MeshBuilder()
        rings = []
        for r, h in profile:
            if r <= 1e-5:
                rings.append([Vector((x, y, ceiling - drop + h))])
                continue
            loop = []
            for k in range(n):
                t = 2.0 * math.pi * k / n
                rr = r
                if style == "pleated":
                    rr = r * (1.0 + 0.045 * math.cos(t * 12))
                px, py = math.cos(t) * rr, math.sin(t) * rr
                loop.append(Vector((x + px, y + py, ceiling - drop + h + px * tz)))
            rings.append(loop)
        shapes.loft(sh, rings, key)                    # one skin: the materials are two-sided
        shade_obj = sh.build("shade_pendant_" + name, coll, smooth=True)
        shade_obj.visible_shadow = False
    if lit:
        lightpoint(name, (x, y, ceiling - drop - 0.04), kind, watts)
    return obj


def broken_floor_lamp(name, foot, direction_deg, coll="lamps"):
    """A floor lamp knocked over: the pole along the floor, shade crushed, bulb smashed."""
    x, y, z = foot
    u = Vector((math.cos(math.radians(direction_deg)), math.sin(math.radians(direction_deg)), 0))
    side = Vector((-u.y, u.x, 0))
    mb = MeshBuilder()
    r = 0.15
    base = Vector((x, y, z + r))
    mb.cylinder(base - u * 0.015, u * 0.03, r, "metal_dark", segments=18)
    pole_a, pole_b = base, Vector((x, y, z + 0.02)) + u * 1.45
    mb.cylinder(pole_a, pole_b - pole_a, 0.013, "metal_brass", segments=8)
    tip = pole_b
    shade_axis = (u + side * 0.35 + Vector((0, 0, 0.25))).normalized() * 0.24
    mb.cylinder(tip - shade_axis * 0.2, shade_axis, 0.11, "lampshade", segments=14, caps="none", radius_top=0.19)
    mb.cylinder(tip, u * 0.05, 0.018, "plastic_white", segments=8)
    rng = random.Random(7)
    for _ in range(14):                                  # shards of the bulb
        c = tip + u * rng.uniform(0.1, 0.45) + side * rng.uniform(-0.25, 0.25)
        c.z = z + 0.002
        a, b = rng.uniform(0.008, 0.02), rng.uniform(0, math.pi)
        pts = [c + Vector((math.cos(b + k * 2.1) * a, math.sin(b + k * 2.1) * a, 0)) for k in range(3)]
        mb.face(pts, "glass")
    return mb.build("lamp_" + name, coll, smooth=False)


# --- Curtains, rugs, radiators ----------------------------------------------

def curtain(name, face, a0, a1, z_top, z_bot, seed=0, off=0.105, key="fabric_curtain", coll="soft"):
    """One hanging panel between a0 and a1. The cloth is gathered tight at
    the heading and opens out as it falls: the pleats are uneven in width and
    depth, wander a little on the way down, and the hem neither hangs level
    nor in a straight line."""
    rng = random.Random(seed)
    width = a1 - a0
    cols = max(18, int(width / 0.016))
    rows = 14
    folds = max(2.0, width / 0.115)
    phase, p1, p2, p3, p4 = (rng.uniform(0, 6.28) for _ in range(5))
    tile = core.spec(key).tile
    mb = MeshBuilder()
    grid = []
    for i in range(cols + 1):
        s_ = i / cols
        # uneven pleats: some wide, some narrow
        warped = s_ + 0.045 * math.sin(2 * math.pi * 1.3 * s_ + p1) + 0.022 * math.sin(2 * math.pi * 3.4 * s_ + p2)
        angle = 2 * math.pi * folds * warped + phase
        depth = 0.75 + 0.5 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.8 * s_ + p3))       # and some deeper than others
        column = []
        for j in range(rows + 1):
            t = j / rows                                   # 0 at the heading
            amp = (0.010 + 0.046 * t ** 0.75) * depth
            twist = 0.9 * t * math.sin(2.2 * t + p4)       # each fold drifts sideways as it falls
            d = off + amp * math.sin(angle + twist) + 0.014 * t * math.sin(2 * math.pi * 0.6 * s_ + p2)
            a = a0 + width * s_ + 0.014 * t * math.cos(angle + twist)
            z = z_top + (z_bot - z_top) * t
            if j == rows:                                  # the hem
                z += 0.018 * math.sin(angle * 0.5 + p1) + 0.010 * math.sin(2 * math.pi * 0.5 * s_ + p3)
            column.append((face.P(a, d, z), (s_ * width * 1.7 / tile, z / tile)))
        grid.append(column)
    for i in range(cols):
        for j in range(rows):
            quad = [grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]]
            mb.face([q[0] for q in quad], key, uvs=[q[1] for q in quad])
    return mb.build(name, coll, smooth=True)


def curtain_pole(name, face, a0, a1, z, off=0.105, coll="soft"):
    mb = MeshBuilder()
    mb.cylinder(face.P(a0, off, z), face.along * (a1 - a0), 0.013, "metal_dark", segments=8)
    for a in (a0, a1):
        mb.cylinder(face.P(a, off, z) - face.along * 0.02 * (1 if a == a0 else -1), face.along * 0.02 * (1 if a == a0 else -1),
                    0.024, "metal_dark", segments=8)
    for a in (a0 + 0.12, (a0 + a1) / 2, a1 - 0.12):
        face.box(mb, a - 0.008, a + 0.008, 0.0, off, z - 0.008, z + 0.008, "metal_dark")
    return mb.build(name, coll)


def rug(name, x0, y0, x1, y1, z, key="carpet", coll="soft", thick=0.016, seed=0, fringe=True, lift=0.0):
    """A rug with a body: a pile of real thickness that rolls over at the
    edge, sides that are not quite straight, a ruck or two where it has been
    walked into, a fringe on the two short ends. `lift` turns one corner up."""
    rng = random.Random(sum(ord(ch) for ch in name) + seed)
    tile = core.spec(key).tile
    long_x = (x1 - x0) >= (y1 - y0)
    nx = max(6, int((x1 - x0) / 0.12))
    ny = max(6, int((y1 - y0) / 0.12))
    p1, p2, p3 = (rng.uniform(0, 6.28) for _ in range(3))
    ruck_at, ruck_dir = rng.uniform(0.25, 0.75), rng.uniform(-0.5, 0.5)
    corner = rng.choice(((0, 0), (1, 0), (0, 1), (1, 1)))
    mb = MeshBuilder()
    edge = 0.022                                             # the pile rolls down to the floor over this distance

    def point(i, j):
        s, t = i / nx, j / ny
        x, y = x0 + (x1 - x0) * s, y0 + (y1 - y0) * t
        # sides that wander a few millimetres
        x += 0.006 * math.sin(7.0 * t + p1) * (1 if s > 0.5 else -1) * abs(2 * s - 1) ** 6
        y += 0.006 * math.sin(6.0 * s + p2) * (1 if t > 0.5 else -1) * abs(2 * t - 1) ** 6
        rim = min(s * (x1 - x0), (1 - s) * (x1 - x0), t * (y1 - y0), (1 - t) * (y1 - y0))
        h = thick * min(1.0, rim / edge) ** 0.5
        along, across = (s, t) if long_x else (t, s)
        ruck = math.exp(-((along - ruck_at - ruck_dir * (across - 0.5)) / 0.035) ** 2)
        h += 0.011 * ruck * min(1.0, rim / 0.10) + 0.0025 * math.sin(9 * s + p3) * math.sin(8 * t + p1) * min(1.0, rim / 0.1)
        if lift:
            cs, ct = (s if corner[0] == 0 else 1 - s), (t if corner[1] == 0 else 1 - t)
            h += lift * max(0.0, 1.0 - (cs * (x1 - x0) + ct * (y1 - y0)) / 0.30) ** 2
        return Vector((x, y, z + 0.0015 + h)), (x / tile, y / tile)

    grid = [[point(i, j) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            quad = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
            mb.face([q[0] for q in quad], key, uvs=[q[1] for q in quad])
    if fringe:                                               # a fringe of knotted warp threads on the short ends
        ends = ((0, -1.0), (nx, 1.0)) if long_x else ((0, -1.0), (ny, 1.0))
        for index, sign in ends:
            count = int(((y1 - y0) if long_x else (x1 - x0)) / 0.022)
            for k in range(count):
                f = (k + 0.5) / count
                reach = rng.uniform(0.035, 0.055)
                skew = rng.uniform(-0.008, 0.008)
                if long_x:
                    bx, by = (x0 if index == 0 else x1), y0 + (y1 - y0) * f
                    a, b = Vector((bx, by - 0.007, z + 0.004)), Vector((bx, by + 0.007, z + 0.004))
                    tip = Vector((bx + sign * reach, by + skew, z + 0.002))
                else:
                    bx, by = x0 + (x1 - x0) * f, (y0 if index == 0 else y1)
                    a, b = Vector((bx + 0.007, by, z + 0.004)), Vector((bx - 0.007, by, z + 0.004))
                    tip = Vector((bx + skew, by + sign * reach, z + 0.002))
                tri = [a, b, tip]
                if (tri[1] - tri[0]).cross(tri[2] - tri[0]).z < 0:
                    tri = tri[::-1]
                mb.face(tri, "fabric_pillow")
    return mb.build(name, coll, smooth=True)


def roller_blind(name, face, a0, a1, z_top, z_bot, off=-0.05, key="fabric_curtain", coll="soft", seed=0):
    """A roller blind inside a window reveal: a roller on two brackets, a
    thin sheet of cloth hanging from the back of it with a slight curl, a
    wooden lath in its hem and a cord with an acorn. `off` is measured out
    from the wall face; negative is inside the reveal."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    r = 0.019
    axis = face.P(a0 + 0.012, off, z_top - r - 0.004)
    mb.cylinder(axis, face.along * (a1 - a0 - 0.024), r, key, segments=10)                       # cloth wound on the roller
    for a in (a0, a1 - 0.012):
        face.box(mb, a, a + 0.012, off - 0.028, off + 0.028, z_top - 0.05, z_top, "metal_white")
    cols, rows = 10, 8
    tile = core.spec(key).tile
    skew = rng.uniform(-0.012, 0.012)                          # it never hangs quite level
    grid = []
    for i in range(cols + 1):
        s = i / cols
        column = []
        for j in range(rows + 1):
            t = j / rows
            z = z_top - r - 0.004 + (z_bot - (z_top - r - 0.004)) * t + skew * (s - 0.5) * t
            d = off - r + 0.004 * math.sin(s * math.pi) * t + 0.003 * math.sin(3.0 * t + s * 2.0)
            column.append((face.P(a0 + 0.014 + (a1 - a0 - 0.028) * s, d, z), (s * (a1 - a0) / tile, z / tile)))
        grid.append(column)
    for i in range(cols):
        for j in range(rows):
            quad = [grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]]
            mb.face([q[0] for q in quad], key, uvs=[q[1] for q in quad])
    lath_l, lath_r = grid[0][rows][0], grid[cols][rows][0]
    mb.cylinder(lath_l - face.along * 0.004, (lath_r - lath_l) + face.along * 0.008, 0.008, "wood_mid", segments=6)
    mid = (lath_l + lath_r) / 2
    mb.cylinder(mid, (0, 0, -0.16), 0.0012, "plastic_white", segments=4, caps="none")
    mb.cylinder(mid + Vector((0, 0, -0.19)), (0, 0, 0.035), 0.007, "wood_mid", segments=6, radius_top=0.003)
    return shapes.soften(mb.build(name, coll), 50.0)


def radiator(name, face, a0, a1, floor, height=0.58, coll="fixtures"):
    mb = MeshBuilder()
    z0, z1 = floor + 0.14, floor + 0.14 + height
    face.box(mb, a0, a1, 0.035, 0.085, z0, z1, "metal_white")
    n = int((a1 - a0) / 0.05)
    for k in range(n):
        a = a0 + (a1 - a0) * (k + 0.5) / n
        face.box(mb, a - 0.011, a + 0.011, 0.085, 0.097, z0 + 0.03, z1 - 0.03, "metal_white", skip="")
    face.box(mb, a0 - 0.004, a1 + 0.004, 0.03, 0.10, z1, z1 + 0.012, "metal_white")
    for a in (a0 + 0.12, a1 - 0.12):
        face.box(mb, a - 0.015, a + 0.015, 0.0, 0.035, z1 - 0.12, z1 - 0.06, "metal_white")
    for a, s in ((a0, -1), (a1, 1)):                      # valve and pipe into the floor
        p = face.P(a + s * 0.035, 0.06, z0 + 0.03)
        mb.cylinder((p.x, p.y, floor), (0, 0, z0 + 0.03 - floor), 0.009, "metal_brass", segments=8, caps="none")
        mb.cylinder((p.x, p.y, z0 + 0.01), (0, 0, 0.06), 0.02, "plastic_white", segments=8)
        face.box(mb, min(a, a + s * 0.035), max(a, a + s * 0.035), 0.05, 0.07, z0 + 0.02, z0 + 0.04, "metal_brass")
    return mb.build(name, coll, recalc=True)


def switch(mb, face, a, z, double=False):
    w = 0.086
    face.box(mb, a - w / 2, a + w / 2, 0.0, 0.009, z - w / 2, z + w / 2, "plastic_white", skip="")
    for da in ((-0.018, 0.018) if double else (0.0,)):
        face.box(mb, a + da - 0.012, a + da + 0.012, 0.009, 0.0135, z - 0.022, z + 0.022, "plastic_white")


def socket(mb, face, a, z):
    face.box(mb, a - 0.073, a + 0.073, 0.0, 0.009, z - 0.043, z + 0.043, "plastic_white")
    for da in (-0.036, 0.036):
        face.box(mb, a + da - 0.019, a + da + 0.019, 0.009, 0.0095, z - 0.02, z + 0.018, "plastic_black", skip="")


def socket_broken(mb, face, a, z):
    """A socket with its cover hanging off by the wires."""
    face.box(mb, a - 0.06, a + 0.06, 0.0, 0.004, z - 0.036, z + 0.036, "plastic_black")          # the back box
    for da, key in ((-0.02, "plastic_red"), (0.015, "plastic_blue")):
        cable(mb, [face.P(a + da, 0.004, z + 0.01), face.P(a + da * 1.6, 0.04, z - 0.03),
                   face.P(a + 0.04 + da, 0.03, z - 0.085)], radius=0.002, key=key, steps=5)
    p, q = face.P(a - 0.02, 0.022, z - 0.16), face.P(a + 0.12, 0.034, z - 0.075)
    mb.box((min(p.x, q.x), min(p.y, q.y), min(p.z, q.z)), (max(p.x, q.x), max(p.y, q.y), max(p.z, q.z)), "plastic_white")


def cable(mb, points, radius=0.004, key="plastic_black", steps=10):
    """A cable through the given points, smoothed, as a thin square tube."""
    pts = [Vector(p) for p in points]
    path = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(steps):
            t = k / steps
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                               + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    path.append(pts[-1])
    for a, b in zip(path, path[1:]):
        if (b - a).length > 1e-5:
            mb.cylinder(a, b - a, radius, key, segments=4, caps="none")


# --- Small things -----------------------------------------------------------

BOOK_COLORS = ("book_red", "book_green", "book_blue", "book_cream", "book_brown", "book_black")


def book_row(mb, face, a0, a1, d_back, z, rng, fill=0.85, max_h=0.27):
    """Books standing on a shelf from a0 towards a1, spines facing the room.
    Every book has a spine from the sheet labels.py draws: a title, bands or a
    label, its own colour. Heights and depths vary, a few lean, and the row
    ends with some lying flat."""
    key = shapes.spines_material()
    viewer_right = (-face.normal).cross(Vector((0, 0, 1)))
    forward = face.along.dot(viewer_right) > 0

    def book(b0, b1, d0, d1, z0, z1, lean=0.0):
        index = rng.randrange(labels.SPINE_COUNT)
        cover = labels.spine_cover_uv(index)

        def P(a, d, zz):
            return face.P(a + (zz - z0) * lean, d, zz)
        left, right = (b0, b1) if forward else (b1, b0)
        mb.face([P(left, d1, z0), P(right, d1, z0), P(right, d1, z1), P(left, d1, z1)], key, uvs=labels.spine_uv(index))
        for a in (b0, b1):                                                   # the two covers
            pts = [P(a, d0, z0), P(a, d1, z0), P(a, d1, z1), P(a, d0, z1)]
            outward = face.along * (1 if a == b1 else -1)
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(outward) < 0:
                pts = pts[::-1]
            mb.face(pts, key, uvs=cover)
        top = [P(b0, d0, z1), P(b1, d0, z1), P(b1, d1 - 0.004, z1), P(b0, d1 - 0.004, z1)]     # the page block
        if (top[1] - top[0]).cross(top[2] - top[0]).z < 0:
            top = top[::-1]
        mb.face(top, "paper")

    a = a0
    stop = a0 + (a1 - a0) * fill
    while a < stop:
        w = rng.uniform(0.018, 0.048)
        h = rng.uniform(0.17, max_h)
        depth = rng.uniform(0.13, 0.19)
        if a + w > a1:
            break
        lean = rng.choice((0.0, 0.0, 0.0, 0.0, 0.05, 0.11)) if a + w + 0.05 < stop else 0.16
        book(a, a + w - 0.001, d_back, d_back + depth, z, z + h, lean)
        a += w + (h * lean if lean else 0.0)
    if rng.random() < 0.6 and a + 0.3 < a1:               # a few lying flat at the end
        zz = z
        for _ in range(rng.randint(2, 4)):
            t = rng.uniform(0.02, 0.04)
            face.box(mb, a + 0.03, a + 0.26, d_back, d_back + 0.18, zz, zz + t, rng.choice(BOOK_COLORS), skip="-z")
            zz += t


def bookcase(name, face, a0, a1, floor, height=1.95, depth=0.30, shelves=5, seed=1, key="wood_dark",
             coll="furniture"):
    rng = random.Random(seed)
    mb = MeshBuilder()
    t = 0.022
    face.box(mb, a0, a0 + t, 0.0, depth, floor, floor + height, key)
    face.box(mb, a1 - t, a1, 0.0, depth, floor, floor + height, key)
    face.box(mb, a0, a1, 0.0, 0.008, floor, floor + height, key)                       # back
    face.box(mb, a0 - 0.01, a1 + 0.01, 0.0, depth + 0.012, floor + height, floor + height + 0.03, key)
    face.box(mb, a0 + t, a1 - t, 0.0, depth - 0.01, floor, floor + 0.08, key)          # plinth
    levels = [floor + 0.08 + (height - 0.08) * k / shelves for k in range(shelves)]
    for z in levels:
        face.box(mb, a0 + t, a1 - t, 0.008, depth - 0.006, z, z + t, key)
    books = MeshBuilder()
    for z in levels:
        gap = (height - 0.08) / shelves - t - 0.02
        if rng.random() < 0.85:
            book_row(books, face, a0 + t + 0.004, a1 - t - 0.004, 0.02, z + t, rng,
                     fill=rng.uniform(0.45, 0.95), max_h=min(0.27, gap))
    made = [mb.build(name, coll, recalc=True)]
    if not books.empty:
        made.append(books.build(name + "_books", coll))
    return made


def mail(name, centre, count=9, seed=3, spread=0.35, coll="clutter"):
    """Post lying where it fell through the letterbox."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    cx, cy, z = centre
    for k in range(count):
        w, h = rng.choice(((0.22, 0.11), (0.23, 0.16), (0.30, 0.21)))
        x, y = cx + rng.uniform(-spread, spread), cy + rng.uniform(-spread * 0.7, spread * 0.7)
        ang = rng.uniform(0, math.pi)
        u, v = Vector((math.cos(ang), math.sin(ang), 0)) * w / 2, Vector((-math.sin(ang), math.cos(ang), 0)) * h / 2
        c = Vector((x, y, z + 0.002 + k * 0.0012))
        mb.face([c - u - v, c + u - v, c + u + v, c - u + v], rng.choice(("paper", "paper", "paper_brown")),
                uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return mb.build(name, coll)


def mug(mb, x, y, z, key="ceramic"):
    mb.cylinder((x, y, z), (0, 0, 0.09), 0.036, key, segments=12, caps="base", radius_top=0.04)
    mb.cylinder((x, y, z + 0.078), (0, 0, 0.001), 0.036, "coffee", segments=12, caps="top")
    mb.box((x + 0.038, y - 0.006, z + 0.025), (x + 0.062, y + 0.006, z + 0.07), key)


def newspaper(mb, x, y, z, angle_deg, key="paper"):
    ang = math.radians(angle_deg)
    u, v = Vector((math.cos(ang), math.sin(ang), 0)) * 0.19, Vector((-math.sin(ang), math.cos(ang), 0)) * 0.14
    for k in range(3):
        c = Vector((x, y, z + 0.002 + 0.003 * k))
        mb.face([c - u - v, c + u - v, c + u + v, c - u + v], key, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def coat_rail(name, face, a0, a1, z, coll="fixtures"):
    mb = MeshBuilder()
    face.box(mb, a0, a1, 0.0, 0.018, z - 0.05, z + 0.05, "wood_dark")
    hooks = []
    n = max(2, int((a1 - a0) / 0.22))
    for k in range(n):
        a = a0 + (a1 - a0) * (k + 0.5) / n
        face.box(mb, a - 0.006, a + 0.006, 0.018, 0.075, z - 0.006, z + 0.006, "metal_brass")
        face.box(mb, a - 0.006, a + 0.006, 0.063, 0.075, z - 0.006, z + 0.04, "metal_brass")
        hooks.append(a)
    return mb.build(name, coll), hooks


# --- Decals -----------------------------------------------------------------

def decal_material(texture: str):
    key = "decal_" + texture
    mat = core.material(key)
    path = assets.TEXTURES / "decals" / f"{texture}.png"
    if mat.get("decal_ready") or not path.exists():
        return key
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.92
    mat.surface_render_method = "BLENDED"
    mat["decal_ready"] = True
    return key


class Decals:
    """Collects decal quads for one room into one object."""

    def __init__(self, name, seed=0):
        self.name, self.mb, self.rng = name, MeshBuilder(), random.Random(seed)

    def wall(self, texture, face, a, z, w, h, flip=None, offset=0.0022, uv=None):
        """A decal on a wall face, centred at (a, z). `uv` (u0, v0, u1, v1)
        shows only that part of the image, for a texture that repeats along
        the wall or is carried over a step in it."""
        key = decal_material(texture)
        flip = self.rng.random() < 0.5 if flip is None else flip
        d = offset + self.rng.random() * 0.0006
        corners = [face.P(a - w / 2, d, z - h / 2), face.P(a + w / 2, d, z - h / 2),
                   face.P(a + w / 2, d, z + h / 2), face.P(a - w / 2, d, z + h / 2)]
        u0, v0, u1, v1 = uv or (0.0, 0.0, 1.0, 1.0)
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        if flip:
            uvs = [(u1, v0), (u0, v0), (u0, v1), (u1, v1)]
        n = (corners[1] - corners[0]).cross(corners[2] - corners[0])
        if n.dot(face.normal) < 0:
            corners, uvs = corners[::-1], uvs[::-1]
        self.mb.face(corners, key, uvs=uvs)

    def flat(self, texture, x, y, z, w, h, up=True, angle_deg=0.0):
        key = decal_material(texture)
        ang = math.radians(angle_deg)
        u = Vector((math.cos(ang), math.sin(ang), 0)) * w / 2
        v = Vector((-math.sin(ang), math.cos(ang), 0)) * h / 2
        c = Vector((x, y, z + (0.002 if up else -0.002)))
        pts = [c - u - v, c + u - v, c + u + v, c - u + v]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if not up:
            pts, uvs = pts[::-1], uvs[::-1]
        self.mb.face(pts, key, uvs=uvs)

    def quad(self, texture, points, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
        """A decal on any four points, wound to face the viewer."""
        self.mb.face([Vector(p) for p in points], decal_material(texture), uvs=list(uvs))

    def card(self, texture, x, y, z, width, height, angle_deg=0.0, lean=0.0):
        """A picture standing upright on the ground (a tuft of weeds). Decal
        materials are two-sided, so one quad is seen from both sides. `lean`
        tips its top over, in metres."""
        key = decal_material(texture)
        ang = math.radians(angle_deg)
        u = Vector((math.cos(ang), math.sin(ang), 0)) * width / 2
        tip = Vector((-math.sin(ang), math.cos(ang), 0)) * lean + Vector((0, 0, height))
        c = Vector((x, y, z))
        self.mb.face([c - u, c + u, c + u + tip, c - u + tip], key, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])

    def build(self, coll="decals"):
        if self.mb.empty:
            return None
        obj = self.mb.build(self.name, coll)
        obj.visible_shadow = False
        return obj
