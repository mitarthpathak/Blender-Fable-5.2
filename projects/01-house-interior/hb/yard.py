"""What stands against the back and sides of the house, and in its back yard.

The front was built first and the rest of the outside was a blank box. This
module gives the other three sides the same care: steps at the back door, a
light, the electricity meter, vents, a hose tap, trash cans, a window air
conditioner, foundation vents; a shed, a woodpile and a clothesline in the
yard; dirt, weeds and fallen leaves where the walls meet the ground.

Everything stays inside the house's own lot (in the town, lot L1: x -4.5 to
11.5, y up to 18.0), and nothing here is one of the seven yard and street
objects the town replaces (docs/TOWN.md), nor named like one.

`build()` runs with the structure, `dress()` with the props (it places Poly
Haven models, which the props phase owns).
"""

from __future__ import annotations

import math
import random

from mathutils import Vector

import plan
from . import clutter as cl
from . import dressing as dr
from . import models, shapes
from .core import MeshBuilder
from .dressing import Decals, Face
from .exterior import (AGAINST, CHIMNEY_OUT, CHIMNEY_Y, E, GROUND, LAP_OUT, OUT_E, OUT_N, OUT_S, OUT_W, PORCH,
                       _quad, _rail, blocked, clear)

YN = plan.DEPTH + E                    # outside face of the back wall
XE = plan.WIDTH + E                    # and of the east wall
BACK = next(o for w in plan.WALLS for o in w.openings if o.name == "door_back")
AC_WINDOW = next(o for w in plan.WALLS for o in w.openings if o.name == "win_bedroom_side")
PLINTH = 0.03                          # the block plinth stands this far off the wall face

STOOP = (BACK.start - 0.22, BACK.end + 0.22, 0.92)      # x0, x1, depth of the landing
SHED = (8.9, 15.4, 11.1, 17.2)                          # x0, y0, x1, y1
WOODPILE = (5.2, 16.58, 7.4, 17.0)
LINE_X, LINE_Y = -2.7, (11.2, 16.4)                     # the clothesline, down the west side of the yard


# --- Against the back wall ----------------------------------------------------

def back_steps(coll="exterior"):
    """A timber stoop at the back door: a landing level with the floor and
    two steps down to the yard, three 15 cm risers like the front, with a
    rail either side."""
    x0, x1, depth = STOOP
    yl = YN + depth
    mb = MeshBuilder()
    mb.box((x0, YN + 0.018, -0.065), (x1, yl, -0.005), "porch_boards")
    mb.box((x0 + 0.03, YN + 0.018, GROUND), (x1 - 0.03, yl - 0.03, -0.065), "ext_trim", skip="+z-z")
    for k in range(1, 3):
        z = -0.005 - 0.15 * k
        mb.box((x0, yl + 0.28 * (k - 1), GROUND), (x1, yl + 0.28 * k, z), "porch_boards", skip="-z")
    steps = mb.build("back_steps", coll, recalc=True)

    mb = MeshBuilder()
    for x in (x0 + 0.04, x1 - 0.04):
        mb.box((x - 0.04, yl - 0.08, -0.005), (x + 0.04, yl, 0.98), "ext_trim", skip="-z")
        _rail(mb, (x, YN + 0.03), (x, yl - 0.08))
        # a handrail down the steps to a short post in the yard
        foot = Vector((x, yl + 0.60, GROUND))
        mb.box((foot.x - 0.035, foot.y - 0.035, GROUND), (foot.x + 0.035, foot.y + 0.035, GROUND + 0.86), "ext_trim",
               skip="-z")
        a, b = Vector((x, yl - 0.04, 0.90)), Vector((x, foot.y, GROUND + 0.84))
        w = b - a
        mb.prism([(-0.03, -0.045), (0.03, -0.045), (0.03, 0.0), (-0.03, 0.0)], a, (1, 0, 0), (0, 0, 1), w.normalized(),
                 w.length, "ext_trim")
    rails = mb.build("back_steps_rails", coll, recalc=True)
    return [steps, rails]


def back_light(coll="exterior"):
    """A bulkhead lamp by the back door, on the latch side. Its bulb has
    gone: no light comes with it."""
    mb = MeshBuilder()
    x, z = BACK.start - 0.34, 1.95
    mb.box((x - 0.05, YN, z - 0.06), (x + 0.05, YN + 0.022, z + 0.06), "metal_dark")
    mb.box((x - 0.045, YN + 0.022, z - 0.10), (x + 0.045, YN + 0.13, z + 0.08), "glass_frosted")
    mb.box((x - 0.06, YN, z + 0.08), (x + 0.06, YN + 0.15, z + 0.10), "metal_dark")
    mb.cylinder((x, YN + 0.075, z - 0.06), (0, 0, 0.09), 0.02, "bulb_off", segments=8)
    obj = mb.build("back_light", coll)
    obj.visible_shadow = False
    return [obj]


def meter(coll="exterior"):
    """The electricity meter: a painted steel box with its glass dome, the
    service conduit up the wall to a weatherhead under the eave, and the
    earth wire down into the ground."""
    f, a = OUT_N, 0.42
    mb = MeshBuilder()
    f.box(mb, a - 0.16, a + 0.16, 0.0, 0.10, 1.16, 1.60, "metal_painted")
    f.box(mb, a - 0.17, a + 0.17, 0.0, 0.115, 1.60, 1.615, "metal_painted")                     # its drip cap
    mb.cylinder(f.P(a, 0.10, 1.40), f.normal * 0.012, 0.092, "metal_galv", segments=16)        # the meter's ring
    mb.cylinder(f.P(a, 0.112, 1.40), f.normal * 0.004, 0.078, "paper", segments=16)            # its dial plate
    shapes.loft(mb, [[f.P(a + math.cos(t) * r, d, 1.40 + math.sin(t) * r) for t in
                      (2.0 * math.pi * k / 14 for k in range(14))]
                     for r, d in ((0.086, 0.112), (0.080, 0.165), (0.050, 0.185))], "glass", cap_last=True)
    mb.cylinder(f.P(a, 0.05, 1.615), (0, 0, plan.ROOF_Z - 0.42 - 1.615), 0.024, "metal_galv", segments=8)
    top = f.P(a, 0.05, plan.ROOF_Z - 0.42)
    shapes.tube(mb, [top, top + Vector((0, 0.06, 0.10)), top + Vector((0, 0.17, 0.08))], 0.03, "metal_galv", segments=8)
    for z in (2.5, 3.8, 5.0):                                                                   # straps
        f.box(mb, a - 0.05, a + 0.05, 0.0, 0.078, z, z + 0.03, "metal_galv")
    mb.cylinder(f.P(a + 0.10, 0.03, GROUND), (0, 0, 1.16 - GROUND), 0.008, "metal_dark", segments=6, caps="none")
    return [shapes.soften(mb.build("meter_box", coll), 50.0)]


def vents(coll="exterior"):
    """The tumble dryer's hooded outlet low on the back wall, the cooker
    hood's louvre on the east wall, and two air bricks in the plinth of
    every side."""
    mb = MeshBuilder()
    # dryer vent: a plate, a sloping hood, a dark mouth under it
    f, a, z = OUT_N, 2.98, 0.50
    f.box(mb, a - 0.09, a + 0.09, 0.0, 0.02, z - 0.09, z + 0.09, "metal_painted")
    mb.prism([(0.02, z + 0.085), (0.13, z - 0.02), (0.13, z - 0.075), (0.02, z - 0.075)], f.P(a - 0.075, 0, 0),
             f.normal, (0, 0, 1), f.along, 0.15, "metal_painted")
    _quad(mb, [f.P(a - 0.07, 0.022, z - 0.0752), f.P(a + 0.07, 0.022, z - 0.0752), f.P(a + 0.07, 0.128, z - 0.0752),
               f.P(a - 0.07, 0.128, z - 0.0752)], "soot", (0, 0, -1))
    # cooker hood outlet: a louvred square high on the east wall
    f, a, z = OUT_E, 6.33, 2.06
    f.box(mb, a - 0.13, a + 0.13, 0.0, 0.022, z - 0.13, z + 0.13, "metal_painted")
    for k in range(5):
        zz = z - 0.10 + k * 0.045
        mb.prism([(0.022, zz + 0.035), (0.05, zz), (0.05, zz - 0.006), (0.022, zz + 0.02)], f.P(a - 0.11, 0, 0),
                 f.normal, (0, 0, 1), f.along, 0.22, "metal_painted")
    # air bricks in the plinth
    for f, spots in ((OUT_S, (5.0, 6.8)), (OUT_N, (3.9, 5.6)), (OUT_W, (2.0, 6.2)), (OUT_E, (0.8, 5.2))):
        for a in spots:
            f.box(mb, a - 0.19, a + 0.19, PLINTH, PLINTH + 0.012, -0.35, -0.15, "metal_galv")
            for k in range(4):
                zz = -0.325 + k * 0.042
                f.box(mb, a - 0.17, a + 0.17, PLINTH + 0.012, PLINTH + 0.015, zz, zz + 0.022, "soot")
    return [mb.build("wall_vents", coll, recalc=True)]


def hose_tap(coll="exterior"):
    """A bib tap on the back wall and the garden hose left where it was last
    used: off the tap, across the ground and into a loose coil."""
    f, a, z = OUT_N, 3.42, 0.34
    mb = MeshBuilder()
    mb.cylinder(f.P(a, 0.0, z), f.normal * 0.085, 0.012, "metal_brass", segments=8)
    mb.cylinder(f.P(a, 0.012, z), f.normal * 0.006, 0.03, "metal_brass", segments=10)           # wall plate
    mb.cylinder(f.P(a, 0.075, z - 0.012), (0, 0, 0.055), 0.015, "metal_brass", segments=8)      # body
    mb.cylinder(f.P(a, 0.075, z + 0.05), (0, 0, 0.006), 0.032, "plastic_red", segments=10)      # hand wheel
    spout = f.P(a, 0.10, z - 0.045)
    shapes.tube(mb, [f.P(a, 0.085, z), f.P(a, 0.10, z - 0.01), spout], 0.011, "metal_brass", segments=8)
    tap = shapes.soften(mb.build("hose_tap", coll))

    hose = MeshBuilder()
    rng = random.Random(5)
    cx, cy, zg = 4.02, YN + 0.78, GROUND + 0.016
    path = [spout, spout + Vector((0.0, 0.03, -0.20)), Vector((a + 0.05, YN + 0.22, zg + 0.06)),
            Vector((a + 0.16, YN + 0.42, zg)), Vector((cx - 0.34, cy - 0.16, zg))]
    turns, per = 4, 18
    for k in range(turns * per + 1):
        t = 2.0 * math.pi * k / per
        r = 0.29 - 0.012 * (k / per) + rng.uniform(-0.012, 0.012)
        path.append(Vector((cx - math.cos(t) * r, cy - math.sin(t) * r * 0.9, zg + 0.021 * (k / per) + rng.uniform(0, 0.004))))
    end = path[-1]
    path += [end + Vector((0.10, 0.12, 0.0)), Vector((cx + 0.46, cy + 0.30, zg))]
    dr.cable(hose, path[:5], radius=0.012, key="plastic_hose", steps=5)
    shapes.tube(hose, path[4:], 0.012, "plastic_hose", segments=6)
    hose.cylinder(path[-1], (0.07, 0.03, 0.0), 0.014, "metal_brass", segments=8, radius_top=0.008)
    coil = shapes.soften(hose.build("hose_coil", coll), 70.0)
    return [tap, coil]


def _can(mb, x, y, z, lid=True, turn=0.0):
    """A galvanised trash can: ribbed sides, a rolled rim, two drop handles."""
    r0, r1, h = 0.235, 0.265, 0.66
    profile = [(r0 * 0.96, z), (r0, z + 0.03)]
    for k in range(1, 4):                                   # three pressed ribs
        zz = z + h * k / 4.0
        r = r0 + (r1 - r0) * k / 4.0
        profile += [(r, zz - 0.022), (r + 0.01, zz - 0.008), (r + 0.01, zz + 0.008), (r, zz + 0.022)]
    profile += [(r1, z + h - 0.02), (r1 + 0.012, z + h - 0.008), (r1 + 0.012, z + h), (r1 - 0.006, z + h)]
    shapes.lathe(mb, x, y, profile, "metal_galv", 20, cap_first=True, cap_last=False)
    shapes.lathe(mb, x, y, [(r1 - 0.006, z + h), (r1 - 0.012, z + 0.05), (0.0, z + 0.05)], "metal_galv", 20,
                 cap_first=False, cap_last=False)            # the inside
    for s in (-1, 1):
        c = Vector((x + math.cos(turn) * s * (r1 + 0.004), y + math.sin(turn) * s * (r1 + 0.004), z + h * 0.72))
        side = Vector((-math.sin(turn), math.cos(turn), 0)) * 0.06
        out = Vector((math.cos(turn), math.sin(turn), 0)) * s * 0.02
        shapes.tube(mb, [c - side, c - side + out - Vector((0, 0, 0.07)), c + side + out - Vector((0, 0, 0.07)), c + side],
                    0.005, "metal_dark", segments=5)
    if lid:
        _lid(mb, x, y, z + h, 0.0, 0.0)


def _lid(mb, x, y, z, tilt_deg, yaw_deg):
    """A can's lid: a shallow dome with a rolled edge and a strap handle.
    Tilted, it stands on its edge."""
    r = 0.285
    ca, sa = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    ct, st = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))

    def P(px, py, pz):
        px, pz = px * ct - pz * st, px * st + pz * ct          # tip about the lid's own Y
        return Vector((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))

    rings = []
    for rr, hh in ((r, -0.03), (r + 0.006, -0.01), (r, 0.004), (r * 0.8, 0.03), (r * 0.4, 0.05), (0.0, 0.055)):
        if rr <= 1e-5:
            rings.append([P(0, 0, hh)])
        else:
            rings.append([P(math.cos(t) * rr, math.sin(t) * rr, hh) for t in (2.0 * math.pi * k / 20 for k in range(20))])
    shapes.loft(mb, rings, "metal_galv")
    shapes.tube(mb, [P(-0.07, 0, 0.05), P(-0.05, 0, 0.085), P(0.05, 0, 0.085), P(0.07, 0, 0.05)], 0.006, "metal_dark",
                segments=5)


def trash_cans(coll="yard"):
    """Two cans at the back of the house, by the kitchen. One has lost its
    lid to the wind: it lies against the wall, and a bag sits proud of the
    rim."""
    mb, soft = MeshBuilder(), MeshBuilder()
    _can(mb, 6.28, YN + 0.36, GROUND, lid=True, turn=0.3)
    _can(mb, 6.93, YN + 0.42, GROUND, lid=False, turn=1.9)
    _lid(mb, 7.26, YN + 0.105, GROUND + 0.275, 80.0, 90.0)
    cl.heap(soft, 6.93, YN + 0.42, GROUND + 0.52, 0.22, 0.22, 0.26, "plastic_black", seed=61)
    cl.heap(soft, 6.62, YN + 0.80, GROUND, 0.24, 0.20, 0.26, "plastic_black", seed=62, yaw=30)      # one that never went in
    cans = shapes.soften(mb.build("trash_cans", coll), 50.0)
    bags = shapes.soften(soft.build("trash_bags", coll), 80.0)
    return [cans, bags]


def ac_unit(coll="exterior"):
    """A window air conditioner in the bedroom's side window: the sash is
    pushed up over it (joinery.RAISED), accordion panels fill the gaps at
    its sides, and outside it hangs on two brackets with a louvred back."""
    f, o = OUT_E, AC_WINDOW
    a0, a1 = o.start + 0.10, o.end - 0.10
    z0, z1 = o.sill + 0.052, o.sill + 0.052 + 0.385
    back, front = 0.34, -0.262                              # outside the wall face, and indoors of it
    mb = MeshBuilder()
    f.box(mb, a0, a1, front, back, z0, z1, "metal_painted")
    f.box(mb, a0 - 0.008, a1 + 0.008, front - 0.022, front, z0 - 0.006, z1 + 0.006, "plastic_cream")     # the room side
    for k in range(9):
        zz = z0 + 0.03 + k * 0.036
        f.box(mb, a0 + 0.02, a1 - 0.17, front - 0.026, front - 0.022, zz, zz + 0.014, "plastic_black")
    for k in range(2):                                      # the controls
        mb.cylinder(f.P(a1 - 0.085, front - 0.022, z0 + 0.10 + k * 0.14), -f.normal * 0.018, 0.024, "plastic_black",
                    segments=10)
    for aa, ab in ((o.start + 0.05, a0), (a1, o.end - 0.05)):                                       # accordion panels
        f.box(mb, aa, ab, -0.150, -0.138, z0, z1 + 0.012, "plastic_cream")
    for k in range(10):                                     # the louvred back
        zz = z0 + 0.03 + k * 0.033
        f.box(mb, a0 + 0.03, a1 - 0.03, back, back + 0.005, zz, zz + 0.016, "metal_dark")
    for a in (a0, a1):                                      # side grilles, one each
        s = -1 if a == a0 else 1
        for k in range(6):
            zz = z0 + 0.06 + k * 0.045
            f.box(mb, min(a, a + s * 0.004), max(a, a + s * 0.004), 0.08, 0.30, zz, zz + 0.02, "metal_dark")
    for a in (a0 + 0.07, a1 - 0.07):                        # brackets off the wall under it
        f.box(mb, a - 0.015, a + 0.015, 0.0, 0.31, z0 - 0.03, z0, "metal_galv")
        p, q = f.P(a, 0.29, z0 - 0.03), f.P(a, LAP_OUT, z0 - 0.33)
        mb.cylinder(p, q - p, 0.009, "metal_galv", segments=6)
    return [mb.build("ac_unit", coll, recalc=True)]


# --- The back yard ------------------------------------------------------------

def shed(coll="yard"):
    """A board-and-batten tool shed in the north-east corner of the lot,
    under a lean-to roof of corrugated iron, standing on concrete blocks.
    The door, in the side that faces the house, hangs a little open."""
    x0, y0, x1, y1 = SHED
    hf, hb, t = 2.05, 1.80, 0.022                           # wall height front and back, board thickness
    base = GROUND + 0.13
    door = (9.55, 10.33, 1.84)                              # x0, x1, height
    boards, trim = "shed_boards", "ext_trim"
    made = []

    def top(y):
        return base + hf + (hb - hf) * (y - y0) / (y1 - y0)

    mb = MeshBuilder()
    for bx in (x0 + 0.22, (x0 + x1) / 2, x1 - 0.22):
        for by in (y0 + 0.12, y1 - 0.12):
            mb.box((bx - 0.2, by - 0.1, GROUND - 0.06), (bx + 0.2, by + 0.1, base - 0.045), "ext_foundation")
    mb.box((x0, y0, base - 0.045), (x1, y1, base), "porch_boards")                                  # the floor
    for xa, xb, za, zb in ((x0, door[0], base, base + hf), (door[1], x1, base, base + hf),
                           (door[0], door[1], base + door[2], base + hf)):
        mb.box((xa, y0, za), (xb, y0 + t, zb), boards)
    mb.box((x0, y1 - t, base), (x1, y1, base + hb), boards)
    for xa in (x0, x1 - t):
        mb.prism([(y0 + t, base), (y1 - t, base), (y1 - t, base + hb), (y0 + t, base + hf)], (xa, 0, 0),
                 (0, 1, 0), (0, 0, 1), (1, 0, 0), t, boards)
    # battens over the joints, corner boards, and a frame round the door
    bw, bt = 0.042, 0.012
    south, north = Face("x", y0, -1), Face("x", y1, 1)
    west, east = Face("y", x0, -1), Face("y", x1, 1)
    a = x0 + 0.29
    while a < x1 - 0.2:
        if not (door[0] - 0.10 < a < door[1] + 0.10):
            south.box(mb, a - bw / 2, a + bw / 2, 0.0, bt, base, base + hf, boards)
        north.box(mb, a - bw / 2, a + bw / 2, 0.0, bt, base, base + hb, boards)
        a += 0.275
    a = y0 + 0.28
    while a < y1 - 0.2:
        for f in (west, east):
            f.box(mb, a - bw / 2, a + bw / 2, 0.0, bt, base, top(a) - 0.01, boards)
        a += 0.27
    for f, lo, hi, h in ((south, x0, x1, hf), (north, x0, x1, hb)):
        for aa, ab in ((lo - 0.016, lo + 0.07), (hi - 0.07, hi + 0.016)):
            f.box(mb, aa, ab, 0.0, 0.016, base - 0.03, base + h, trim)
    for f, yc, h in ((west, y0, hf), (west, y1, hb), (east, y0, hf), (east, y1, hb)):
        aa, ab = (yc, yc + 0.07) if yc == y0 else (yc - 0.07, yc)
        f.box(mb, aa, ab, 0.0, 0.016, base - 0.03, base + h - 0.01, trim)
    for aa, ab, za, zb in ((door[0] - 0.08, door[0], base, base + door[2] + 0.08),
                           (door[1], door[1] + 0.08, base, base + door[2] + 0.08),
                           (door[0], door[1], base + door[2], base + door[2] + 0.08)):
        south.box(mb, aa, ab, 0.0, 0.018, za, zb, trim)
    # a ramp board up to the sill
    _quad(mb, [(door[0] + 0.05, y0 - 0.42, GROUND + 0.01), (door[1] - 0.05, y0 - 0.42, GROUND + 0.01),
               (door[1] - 0.05, y0, base - 0.01), (door[0] + 0.05, y0, base - 0.01)], "porch_boards", (0, -1, 3))
    made.append(mb.build("shed", coll, recalc=True))

    # the roof: corrugated sheets falling to the back, on a fascia
    mb = MeshBuilder()
    slope = (hf - hb) / (y1 - y0)
    ya, yb = y0 - 0.20, y1 + 0.14

    def rz(y):
        return base + hf + 0.035 - slope * (y - y0)

    xa, xb = x0 - 0.15, x1 + 0.15
    mb.prism([(ya, rz(ya)), (yb, rz(yb)), (yb, rz(yb) + 0.006), (ya, rz(ya) + 0.006)], (xa, 0, 0),
             (0, 1, 0), (0, 0, 1), (1, 0, 0), xb - xa, "roof_tin")
    x = xa + 0.02
    while x < xb - 0.03:                                     # the corrugations
        mb.prism([(ya, rz(ya) + 0.006), (yb, rz(yb) + 0.006), (yb, rz(yb) + 0.02), (ya, rz(ya) + 0.02)], (x, 0, 0),
                 (0, 1, 0), (0, 0, 1), (1, 0, 0), 0.034, "roof_tin", caps=True)
        x += 0.085
    for y in (y0 - 0.02, (y0 + y1) / 2, y1 - 0.05):          # purlins
        mb.box((xa + 0.03, y, rz(y + 0.035) - 0.07), (xb - 0.03, y + 0.07, rz(y + 0.035) - 0.002), trim)
    made.append(mb.build("shed_roof", coll, recalc=True))

    # the door: ledged and braced, on strap hinges, its hasp hanging open
    mb = MeshBuilder()
    W, H = door[1] - door[0] - 0.012, door[2] - 0.012
    dx0, dx1, dz = door[0] + 0.006, door[1] - 0.006, base + 0.006
    mb.box((dx0, y0, dz), (dx1, y0 + t, dz + H), boards)
    for z in (0.22, H / 2, H - 0.22):
        mb.box((dx0 + 0.03, y0 - 0.02, dz + z - 0.055), (dx1 - 0.03, y0, dz + z + 0.055), boards)
    for za, zb in ((0.275, H / 2 - 0.055), (H / 2 + 0.055, H - 0.275)):
        mb.prism([(dx0 + 0.05, dz + za), (dx0 + 0.16, dz + za), (dx1 - 0.05, dz + zb), (dx1 - 0.16, dz + zb)],
                 (0, y0 - 0.02, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0), 0.02, boards)
    for z in (0.22, H - 0.22):                               # strap hinges
        mb.box((dx1 - 0.30, y0 - 0.026, dz + z - 0.018), (dx1 + 0.03, y0 - 0.02, dz + z + 0.018), "metal_dark")
    mb.box((dx0 + 0.02, y0 - 0.027, dz + 0.98), (dx0 + 0.13, y0 - 0.02, dz + 1.02), "metal_dark")          # hasp
    shapes.tube(mb, [(dx0 + 0.035, y0 - 0.03, dz + 0.99), (dx0 + 0.035, y0 - 0.036, dz + 0.94),
                     (dx0 + 0.06, y0 - 0.036, dz + 0.94)], 0.004, "metal_steel", segments=5)
    mb.box((dx0 + 0.02, y0 - 0.05, dz + 0.885), (dx0 + 0.075, y0 - 0.026, dz + 0.94), "metal_brass")       # padlock
    leaf = mb.build("shed_leaf", coll, origin=(dx1, y0, base), recalc=True)
    leaf.rotation_euler = (0, 0, math.radians(11.0))
    made.append(leaf)

    # round it: a ladder on its side wall, an oil drum, a tyre, a stack of planks
    mb = MeshBuilder()
    for dy in (0.0, 0.36):
        foot, head = Vector((x0 - 0.62, y0 + 0.55 + dy, GROUND)), Vector((x0 - 0.03, y0 + 0.50 + dy, base + 1.86))
        w = head - foot
        mb.prism([(-0.014, -0.035), (0.014, -0.035), (0.014, 0.035), (-0.014, 0.035)], foot, (0, 1, 0),
                 w.cross(Vector((0, 1, 0))).normalized(), w.normalized(), w.length, "wood_mid")
    for k in range(7):
        s = 0.10 + 0.125 * k
        p = Vector((x0 - 0.62, y0 + 0.55, GROUND)).lerp(Vector((x0 - 0.03, y0 + 0.50, base + 1.86)), s)
        mb.cylinder(p, (0.0, 0.36, 0.0), 0.012, "wood_mid", segments=6)
    shapes.lathe(mb, x0 - 0.42, y0 - 0.30, [(0.27, GROUND), (0.285, GROUND + 0.02), (0.285, GROUND + 0.28),
                                           (0.295, GROUND + 0.30), (0.285, GROUND + 0.32), (0.285, GROUND + 0.58),
                                           (0.295, GROUND + 0.60), (0.285, GROUND + 0.62), (0.285, GROUND + 0.87),
                                           (0.275, GROUND + 0.88), (0.265, GROUND + 0.86), (0.0, GROUND + 0.86)],
                 "roof_tin", 18)
    shapes.annulus(mb, x1 - 0.45, y0 - 0.48, GROUND + 0.004, 0.31, 0.185, 0.19, "rubber", n=18)
    rng = random.Random(8)
    for k in range(5):                                       # planks left along the back of the shed
        z = GROUND + 0.02 + k * 0.034
        ox, yaw = rng.uniform(-0.1, 0.1), rng.uniform(-3, 3)
        shapes.obox(mb, (x0 + 1.05 + ox, y1 + 0.24, z), (rng.uniform(1.6, 2.1), 0.15, 0.03), yaw, boards)
    made.append(shapes.soften(mb.build("shed_things", coll), 50.0))
    return made


def _log(mb, a, b, radius, rng, split=False):
    """A length of firewood from a to b: bark round it, pale wood at the cut
    ends. `split` makes it a half round with one flat face."""
    a, b = Vector(a), Vector(b)
    w = (b - a).normalized()
    u = w.cross(Vector((0, 0, 1))).normalized()
    v = u.cross(w)
    n = 8
    turn = rng.uniform(0, 6.28)
    if split:
        angles = [turn + math.pi * k / 5 for k in range(6)]
    else:
        angles = [turn + 2.0 * math.pi * k / n for k in range(n)]
    radii = [radius * rng.uniform(0.86, 1.1) for _ in angles]
    near = [a + (u * math.cos(t) + v * math.sin(t)) * r for t, r in zip(angles, radii)]
    far = [p + (b - a) for p in near]
    count = len(near)
    for i in range(count):
        j = (i + 1) % count
        flat = split and i == count - 1
        mb.face([near[i], near[j], far[j], far[i]], "log_end" if flat else "bark")
    mb.face(near[::-1], "log_end")
    mb.face(far, "log_end")


def woodpile(coll="yard"):
    """Firewood stacked between stakes along the back of the yard, a tarp
    over the top held down with bricks, a chopping block with the axe left
    in it and the last few logs nobody stacked."""
    x0, y0, x1, y1 = WOODPILE
    rng = random.Random(14)
    mb = MeshBuilder()
    z = GROUND + 0.07
    for y in (y0 + 0.07, y1 - 0.07):                         # two rails keep it off the ground
        _log(mb, (x0 - 0.05, y, GROUND + 0.035), (x1 + 0.05, y, GROUND + 0.035), 0.04, rng)
    for x in (x0 - 0.06, x1 + 0.06):                         # stakes at the ends
        for y in (y0 + 0.08, y1 - 0.08):
            _log(mb, (x, y, GROUND - 0.05), (x + rng.uniform(-0.03, 0.03), y, GROUND + 1.22), 0.032, rng)
    tops = []
    row = 0
    while z < GROUND + 0.98:
        x = x0 + rng.uniform(0.0, 0.07)
        height = 0.0
        while x < x1 - 0.06:
            r = rng.uniform(0.055, 0.10)
            if x + 2 * r > x1:
                break
            ya = y0 + rng.uniform(-0.035, 0.035)
            _log(mb, (x + r, ya, z + r), (x + r + rng.uniform(-0.012, 0.012), ya + (y1 - y0) + rng.uniform(-0.03, 0.03),
                                         z + r + rng.uniform(-0.008, 0.008)), r, rng, split=rng.random() < 0.45)
            height = max(height, 2 * r)
            x += 2 * r * rng.uniform(0.94, 1.02)
        z += height * 0.86
        row += 1
    top = z + 0.01
    made = [mb.build("woodpile", coll)]

    # the tarp: over the top and down both faces, sagging between the logs
    tarp = MeshBuilder()
    nx, ny = 22, 12
    xa, xb = x0 - 0.16, x1 + 0.10
    yc, half, reach = (y0 + y1) / 2, (y1 - y0) / 2 + 0.03, 0.46
    p1, p2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    grid = []
    for i in range(nx + 1):
        s = i / nx
        column = []
        for j in range(ny + 1):
            tt = -1.0 + 2.0 * j / ny                         # across the pile, -1 to 1
            across = tt * (half + reach)
            over = max(0.0, abs(across) - half)              # how far down the face this point has gone
            y = yc + math.copysign(min(abs(across), half) + over * 0.16, across)
            zz = top + 0.012 * math.sin(11.0 * s + p1) * (1.0 - min(1.0, over * 4)) - over * 0.94
            y += math.copysign(0.03 * math.sin(14.0 * s + p2 + tt), across) * min(1.0, over * 5)
            zz += 0.02 * math.sin(9.0 * s + 3.0 * tt + p1) * min(1.0, over * 5)
            if s > 0.86:                                     # one end blown back off the logs
                zz += (s - 0.86) * 1.1 * (1.0 - abs(tt)) * 0.5
            column.append(Vector((xa + (xb - xa) * s, y, zz)))
        grid.append(column)
    for i in range(nx):
        for j in range(ny):
            tarp.face([grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]], "tarp")
    made.append(tarp.build("woodpile_tarp", coll, smooth=True))

    loose = MeshBuilder()
    for bx, by, yaw in ((x0 + 0.5, yc - 0.05, 14.0), (x0 + 1.35, yc + 0.06, -8.0), (x1 - 0.5, yc - 0.02, 80.0)):
        shapes.obox(loose, (bx, by, top + 0.012), (0.215, 0.102, 0.065), yaw, "ext_brick")
    # the chopping block and the axe
    bx, by = 4.35, 16.15
    _log(loose, (bx, by, GROUND - 0.02), (bx + 0.01, by, GROUND + 0.44), 0.21, rng)
    head = Vector((bx + 0.02, by - 0.02, GROUND + 0.44))
    loose.box((head.x - 0.012, head.y - 0.085, head.z - 0.03), (head.x + 0.012, head.y + 0.045, head.z + 0.065),
              "metal_dark")
    shapes.tube(loose, [head + Vector((0, 0.03, 0.03)), head + Vector((0.04, 0.42, 0.34)),
                        head + Vector((0.05, 0.60, 0.44))], 0.017, "wood_mid", segments=6)
    for k in range(7):                                       # split logs lying round the block
        ang = rng.uniform(0, 6.28)
        d = rng.uniform(0.45, 1.0)
        c = Vector((bx + math.cos(ang) * d, by + math.sin(ang) * d, GROUND + 0.06))
        along = Vector((math.cos(ang * 3.1), math.sin(ang * 3.1), 0)) * 0.21
        _log(loose, c - along, c + along, rng.uniform(0.055, 0.085), rng, split=True)
    made.append(loose.build("woodpile_block", coll))
    return made


def clothesline(coll="yard"):
    """Two steel T-posts down the side of the yard with three lines between
    them, sagging, and a sheet nobody brought in."""
    mb = MeshBuilder()
    x, (ya, yb) = LINE_X, LINE_Y
    h = 1.92
    for y, lean in ((ya, 0.03), (yb, -0.05)):
        foot, head = Vector((x, y, GROUND - 0.05)), Vector((x + lean, y, GROUND + h))
        mb.cylinder(foot, head - foot, 0.028, "metal_painted", segments=8)
        mb.cylinder(head + Vector((-0.5, 0, -0.03)), (1.0, 0, 0), 0.02, "metal_painted", segments=8)
        for s in (-1, 1):                                    # braces under the arm
            mb.cylinder(head + Vector((0, 0, -0.34)), Vector((s * 0.32, 0, 0.30)), 0.009, "metal_painted", segments=6)
    for k, dx in enumerate((-0.44, 0.0, 0.44)):
        a = Vector((x + 0.03 + dx, ya, GROUND + h - 0.03))
        b = Vector((x - 0.05 + dx, yb, GROUND + h - 0.03))
        sag = 0.10 + 0.04 * k
        path = [a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t))) for t in (i / 12 for i in range(13))]
        shapes.tube(mb, path, 0.0025, "plastic_white", segments=4)
    line = shapes.soften(mb.build("clothesline", coll), 60.0)
    hang = Face("y", x + 0.42, -1)
    sheet = dr.curtain("clothesline_sheet", hang, 12.75, 14.05, GROUND + h - 0.13, GROUND + 0.72, seed=7, off=0.0,
                       key="fabric_bed", coll=coll)
    return [line, sheet]


# --- The ground ---------------------------------------------------------------

def _ribbon(mb, points, width, rng, z, inner=0.0):
    """A strip of bare earth along a polyline: one edge on the line (or
    `inner` behind it), the other wandering in and out."""
    pts = [Vector((p[0], p[1], z)) for p in points]
    rows = []
    for a, b in zip(pts, pts[1:]):
        along = (b - a)
        length = along.length
        out = Vector((-along.y, along.x, 0)).normalized()     # to the left of the way the line runs
        steps = max(2, int(length / 0.35))
        for k in range(steps + 1):                           # both ends: at a corner the two rows fan round it
            p = a + along * k / steps
            wide = width * rng.uniform(0.55, 1.35)
            rows.append((p - out * inner, p + out * wide))
    for (i0, o0), (i1, o1) in zip(rows, rows[1:]):
        poly = [i0, o0, o1] if (i0 - i1).length < 0.12 else [i0, o0, o1, i1]
        if (poly[1] - poly[0]).cross(poly[2] - poly[0]).z < 0:
            poly = poly[::-1]
        mb.face(poly, "ground_dirt")


def _patch(mb, x, y, rx, ry, rng, z, n=14):
    """A worn patch of bare earth with a ragged outline."""
    ring = [Vector((x + math.cos(t) * rx * rng.uniform(0.7, 1.15), y + math.sin(t) * ry * rng.uniform(0.7, 1.15), z))
            for t in (2.0 * math.pi * k / n for k in range(n))]
    centre = Vector((x, y, z))
    for i in range(n):
        mb.face([centre, ring[i], ring[(i + 1) % n]], "ground_dirt")


def ground(coll="yard"):
    """Bare earth where grass does not grow: under the drip of the walls,
    where feet go from the back steps to the shed, round the woodpile."""
    rng = random.Random(27)
    mb = MeshBuilder()
    x0, x1, y0, y1 = -E - PLINTH, XE + PLINTH, -E - PLINTH, YN + PLINTH
    px0, px1 = PORCH[0] + 0.03, PORCH[1] - 0.03
    sx0, sx1 = STOOP[0], STOOP[1]
    cy0, cy1 = CHIMNEY_Y
    # round the house, clockwise seen from above, so "out" is away from the walls
    runs = (
        [(px0, y0), (x0, y0), (x0, y1), (sx0, y1)],                                   # front-left, west side, back to the steps
        [(sx1, y1), (x1, y1), (x1, cy1)],                                             # back, round the corner to the chimney
        [(x1, cy1), (x1 + CHIMNEY_OUT, cy1), (x1 + CHIMNEY_OUT, cy0), (x1, cy0)],     # round the chimney
        [(x1, cy0), (x1, y0), (px1, y0)],                                             # east side to the porch
    )
    for k, run in enumerate(runs):
        _ribbon(mb, run, 0.42, rng, GROUND + 0.005 + 0.001 * k, inner=0.05)
    # the way from the steps to the shed door, and the places that get stood on
    foot = Vector(((sx0 + sx1) / 2, YN + STOOP[2] + 0.75, 0))
    shed_door = Vector((9.94, SHED[1] - 0.6, 0))
    _patch(mb, foot.x, foot.y - 0.2, 0.95, 0.6, rng, GROUND + 0.0165)
    _patch(mb, 4.35, 16.15, 1.0, 0.9, rng, GROUND + 0.0172)                                         # the chopping block
    _patch(mb, (WOODPILE[0] + WOODPILE[2]) / 2, WOODPILE[1] - 0.1, 1.5, 0.5, rng, GROUND + 0.0178)
    _patch(mb, 6.6, YN + 0.55, 0.85, 0.5, rng, GROUND + 0.0184)                                     # the trash cans
    _patch(mb, LINE_X, 13.6, 0.7, 2.2, rng, GROUND + 0.019)                                         # under the line
    made = [mb.build("ground_dirt_strip", coll)]

    # fallen leaves: wherever the wind is stopped by a corner
    d = Decals("decals_yard", seed=37)
    zl = GROUND + 0.021
    for x, y, w, turn in (
            (sx0 - 0.55, YN + 0.5, 1.5, 20), (sx1 + 0.6, YN + 0.45, 1.3, 130), ((sx0 + sx1) / 2, YN + 1.9, 1.2, 250),
            (XE + 0.5, cy1 + 0.45, 1.4, 60), (XE + 0.45, cy0 - 0.5, 1.5, 300), (XE + 0.5, 7.3, 1.2, 110),
            (-E - 0.5, 1.2, 1.3, 200), (-E - 0.55, 5.4, 1.5, 40), (-E - 0.4, 7.9, 1.1, 170),
            (PORCH[0] - 0.45, -0.75, 1.3, 280), (PORCH[1] + 0.5, -0.8, 1.4, 90), (6.2, -0.8, 1.3, 15),
            (4.6, YN + 0.5, 1.2, 220), (7.2, YN + 0.9, 1.3, 330),
            (SHED[0] + 0.3, SHED[1] - 0.45, 1.5, 70), (SHED[0] - 0.4, SHED[3] - 0.5, 1.4, 190),
            (WOODPILE[0] - 0.4, WOODPILE[1] - 0.2, 1.3, 310), (WOODPILE[2] + 0.2, WOODPILE[1] - 0.3, 1.2, 100)):
        d.flat("leaf_litter", x, y, zl + d.rng.random() * 0.002, w, w, angle_deg=turn)
    for x, y, w, turn in ((1.2, YN + 0.5, 1.0, 40), (2.1, YN + 1.25, 1.1, 200)):                     # on the back steps
        d.flat("leaf_scatter", x + 0.6, y, -0.005 if y < YN + STOOP[2] else -0.155, w * 0.9, w * 0.7, angle_deg=turn)
    d.flat("leaf_scatter", 2.75, -1.45, -0.005, 1.5, 1.4, angle_deg=30)                              # on the porch deck
    d.flat("leaf_litter", 0.78, -0.72, -0.005, 0.95, 0.95, angle_deg=120)
    d.flat("leaf_litter", 3.30, -2.0, -0.005, 0.8, 0.8, angle_deg=260)
    # marks on the walls behind what hangs on them
    off = LAP_OUT + 0.002
    d.wall("rust_stain", OUT_E, (AC_WINDOW.start + AC_WINDOW.end) / 2, AC_WINDOW.sill - 0.45, 0.42, 0.9, offset=off)
    d.wall("runoff", OUT_E, 6.33, 1.35, 0.5, 1.2, offset=off)                                        # grease below the hood outlet
    d.wall("runoff", OUT_N, 2.98, 0.26, 0.34, 0.36, offset=off)                                      # lint below the dryer vent
    d.wall("rust_stain", OUT_N, 0.42, 0.78, 0.3, 0.8, offset=off)                                    # under the meter
    d.wall("rust_stain", OUT_N, 3.42, 0.10, 0.2, 0.42, offset=off)                                   # under the tap
    made.append(d.build())

    # weeds: tufts of dead grass against the plinth and round everything that is never moved
    w = Decals("decals_yard_weeds", seed=43)
    rng = w.rng

    def tuft(x, y, size=1.0):
        width, height = rng.uniform(0.28, 0.6) * size, rng.uniform(0.22, 0.55) * size
        turn = rng.uniform(0, 180)
        for k in range(2):
            w.card("weed_tuft", x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), GROUND - 0.01, width, height,
                   angle_deg=turn + k * rng.uniform(70, 110), lean=rng.uniform(-0.06, 0.06))

    for name, face, lo, hi in (("wall_ext_south", OUT_S, -E, XE), ("wall_ext_north", OUT_N, -E, XE),
                               ("wall_ext_west", OUT_W, -E, YN), ("wall_ext_east", OUT_E, -E, YN)):
        zones = blocked(name, AGAINST[name])
        a = lo + rng.uniform(0.1, 0.5)
        while a < hi - 0.1:
            if clear(zones, a - 0.3, a + 0.3, GROUND, -0.02) and rng.random() < 0.8:
                p = face.P(a, PLINTH + rng.uniform(0.05, 0.3), 0)
                tuft(p.x, p.y)
            a += rng.uniform(0.25, 1.1)
    for x, y in ((XE + CHIMNEY_OUT + 0.1, cy0 + 0.3), (XE + CHIMNEY_OUT + 0.12, cy1 - 0.5), (XE + CHIMNEY_OUT + 0.08, 2.3)):
        tuft(x, y)
    sx0_, sy0_, sx1_, sy1_ = SHED
    for k in range(22):                                      # round the shed
        t = rng.random()
        side = k % 4
        x, y = ((sx0_ + (sx1_ - sx0_) * t, sy0_ - 0.1), (sx0_ + (sx1_ - sx0_) * t, sy1_ + 0.1),
                (sx0_ - 0.1, sy0_ + (sy1_ - sy0_) * t), (sx1_ + 0.1, sy0_ + (sy1_ - sy0_) * t))[side]
        if side == 0 and 9.4 < x < 10.5:
            continue                                         # not across the door
        tuft(x, y, 1.15)
    for k in range(12):                                      # along the woodpile and under the clothes posts
        tuft(WOODPILE[0] + (WOODPILE[2] - WOODPILE[0]) * rng.random(), WOODPILE[3] + rng.uniform(0.05, 0.3), 1.2)
    for y in LINE_Y:
        for k in range(3):
            tuft(LINE_X + rng.uniform(-0.25, 0.25), y + rng.uniform(-0.25, 0.25))
    for x, y in ((6.05, YN + 0.2), (7.3, YN + 0.75), (STOOP[0] - 0.15, YN + 0.7), (STOOP[1] + 0.2, YN + 1.0),
                 (4.1, 16.5), (4.75, 15.8), (8.45, 15.0), (11.0, 14.8)):
        tuft(x, y)
    made.append(w.build())
    return made


def build():
    made = back_steps() + back_light() + meter() + vents() + hose_tap() + ac_unit()
    made += trash_cans() + shed() + woodpile() + clothesline() + ground()
    return [m for m in made if m is not None]


# --- Dressing that uses the furniture models (props phase) ---------------------

def dress():
    """The porch deck and the back landing: somewhere to sit, a mat, what
    was put down by the door and never taken in."""
    deck = -0.005
    models.place("painted_wooden_chair_01", "porch_chair", (3.12, -0.95, deck), facing=-118)
    models.place("plastic_crate_03", "porch_crate", (3.36, -1.86, deck), facing=12)
    models.place("potted_plant_01", "porch_plant", (0.66, -1.98, deck), facing=40, scale=0.9)
    dr.rug("doormat_porch", 1.38, -0.92, 2.17, -0.40, deck, key="rubber", fringe=False, thick=0.012)
    dr.rug("doormat_back", STOOP[0] + 0.28, YN + 0.10, STOOP[1] - 0.28, YN + 0.56, deck, key="rubber", fringe=False,
           thick=0.012)

    small, soft = MeshBuilder(), MeshBuilder()
    shapes.sheet(small, (1.62, -1.55, deck), 0.30, "newspaper", yaw=38, lift=0.004)                  # this week's, unread
    shapes.sheet(small, (1.95, -1.82, deck), 0.30, "newspaper", yaw=-25, lift=0.004)
    shapes.sheet(small, (1.30, -1.25, deck), 0.20, "menu", yaw=70, lift=0.003)
    cl.shoe(small, 2.48, -0.50, deck, yaw=95, key="rubber", boot=True)
    cl.shoe(small, 2.62, -0.56, deck, yaw=80, key="rubber", boot=True, tipped=True)
    cl.tin(small, 2.86, -0.70, deck, "beer", radius=0.032, height=0.12, turn=40)                     # by the chair
    cl.tin(small, 2.78, -0.86, deck + 0.032, "beer", radius=0.032, height=0.12, turn=100)
    cl.ashtray(small, 2.92, -0.52, deck, butts=6, seed=21, key="ceramic")
    for k, (dx, dy) in enumerate(((-0.10, -0.07), (0.02, 0.06), (0.11, -0.05), (-0.02, -0.10))):     # empties in the crate
        cl.bottle(small, 3.36 + dx, -1.86 + dy, deck + 0.02, height=0.25 - 0.01 * k)
    cl.pillow(soft, 3.12, -0.97, deck + 0.50, 0.19, 0.19, 0.09, yaw=-28, dent=0.5, seed=71, key="fabric_plaid")
    # the back landing: a broom against the wall, a crate of empties, a bag that never reached the cans
    small.cylinder((STOOP[1] - 0.10, YN + 0.07, deck + 0.05), (-0.03, -0.045, 1.30), 0.012, "wood_mid", segments=6)
    shapes.obox(small, (STOOP[1] - 0.10, YN + 0.085, deck), (0.30, 0.05, 0.07), 4, "c_brown")
    cl.heap(soft, STOOP[0] + 0.16, YN + 0.72, deck, 0.17, 0.16, 0.22, "plastic_black", seed=63)
    cl.tin(small, STOOP[0] + 0.42, YN + 0.80, deck, "soup", turn=70)
    shapes.soften(small.build("clutter_porch", "clutter"))
    shapes.soften(soft.build("clutter_porch_cloth", "clutter"), 80.0)
