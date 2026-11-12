"""The utility cupboard: a walk-in store off the landing, carved out of the
back room upstairs. The hot-water tank lives here, with the household linen
on slatted shelves over it, and everything that cleans the house: mop and
bucket, broom, vacuum cleaner, ironing board, washing powder.

It is x 2.54 to 4.20, y 4.54 to 6.10, floor at 3.06. The door is in the west
wall and opens outwards onto the landing.
"""

from __future__ import annotations

import math
import random

from mathutils import Vector

import plan
from . import clutter as cl
from . import dressing as dr
from . import shapes
from .core import MeshBuilder
from .dressing import DIVIDER_N, F1, ROOM_WEST, UTIL_EAST_IN, UTIL_NORTH_IN, Decals

X0, Y0, X1, Y1 = plan.PART_X1, plan.DIVIDER_Y1, plan.UTIL_X1, plan.UTIL_Y1


def shelves(small):
    """Slatted linen shelves the full height of the east wall."""
    mb = MeshBuilder()
    face = UTIL_EAST_IN
    a0, a1, depth = Y0 + 0.04, Y1 - 0.04, 0.42
    levels = (0.42, 0.86, 1.30, 1.74)
    for a in (a0, (a0 + a1) / 2 - 0.02, a1 - 0.04):                 # uprights at the front
        face.box(mb, a, a + 0.04, depth - 0.04, depth, F1, F1 + 1.80, "wood_mid")
    for z in levels:
        face.box(mb, a0, a1, 0.0, 0.03, F1 + z - 0.05, F1 + z, "wood_mid")           # bearer on the wall
        for k in range(6):                                                           # slats
            d = 0.035 + k * 0.066
            face.box(mb, a0, a1, d, d + 0.046, F1 + z, F1 + z + 0.018, "wood_mid")
    mb.build("utility_shelves", "furniture")

    rng = random.Random(17)
    stock = (("fabric_pillow", 4), ("towel", 3), ("fabric_bed", 5), ("fabric_curtain", 3), ("towel", 4),
             ("fabric_pillow", 3), ("fabric_plaid", 2))
    k = 0
    for z in levels[:3]:
        a = a0 + 0.10
        while a < a1 - 0.22:
            key, layers = stock[k % len(stock)]
            k += 1
            width = rng.uniform(0.26, 0.34)
            p = face.P(a + width / 2, 0.21, F1 + z + 0.018)
            cl.folded(small, p.x, p.y, p.z, 0.30, width, key, layers=layers, yaw=rng.uniform(-4, 4), thick=0.028,
                      seed=k)
            a += width + rng.uniform(0.03, 0.09)
    # the top shelf: a box of decorations, spare bulbs, washing powder
    p = face.P(a0 + 0.30, 0.21, F1 + levels[3] + 0.018)
    cl.open_box(small, p.x, p.y, p.z, size=(0.32, 0.40, 0.24), yaw=90, flaps=(170.0, 30.0, 165.0, 40.0), seed=9)
    p = face.P(a0 + 0.78, 0.20, F1 + levels[3] + 0.018)
    shapes.obox(small, tuple(p), (0.19, 0.075, 0.26), 180 + 8, "c_orange", prints={"front": "detergent", "back": "detergent"})
    p = face.P(a0 + 1.08, 0.18, F1 + levels[3] + 0.018)
    cl.plastic_bottle(small, p.x, p.y, p.z, "bleach", yaw=170, size=(0.085, 0.05, 0.22))
    p = face.P(a0 + 1.24, 0.22, F1 + levels[3] + 0.018)
    cl.plastic_bottle(small, p.x, p.y, p.z, "conditioner", yaw=200, size=(0.07, 0.045, 0.20))


def tank():
    """A copper hot-water cylinder in its lagging jacket, with pipework."""
    mb = MeshBuilder()
    cx, cy, r = X0 + 0.30, Y1 - 0.30, 0.225
    shapes.lathe(mb, cx, cy, [(r * 0.9, F1 + 0.06), (r, F1 + 0.12), (r, F1 + 1.02), (r * 0.72, F1 + 1.14),
                              (r * 0.2, F1 + 1.18)], "fabric_curtain", 16)                # the jacket
    for z in (0.34, 0.80):                                                                # its straps
        shapes.annulus(mb, cx, cy, F1 + z, r + 0.004, r - 0.002, 0.03, "plastic_black", n=16)
    shapes.lathe(mb, cx, cy, [(r * 0.7, F1), (r * 0.9, F1 + 0.06)], "metal_dark", 12)
    top = Vector((cx, cy, F1 + 1.18))
    shapes.tube(mb, [top, top + Vector((0, 0, 0.30)), top + Vector((0.0, 0.20, 0.38)), top + Vector((0.0, 0.26, 0.38))],
                0.011, "metal_brass", segments=8)
    shapes.tube(mb, [top + Vector((0.0, 0.0, 0.30)), top + Vector((0.0, 0.0, 1.45))], 0.011, "metal_brass", segments=8)
    shapes.tube(mb, [(cx + 0.17, cy - 0.16, F1 + 0.20), (cx + 0.17, cy - 0.16, F1 + 0.04), (cx + 0.40, cy - 0.16, F1 + 0.04),
                     (cx + 0.40, cy - 0.16, F1)], 0.011, "metal_brass", segments=8)
    mb.box((cx + 0.10, cy - 0.21, F1 + 0.50), (cx + 0.20, cy - 0.15, F1 + 0.62), "plastic_cream")   # the thermostat
    return shapes.soften(mb.build("utility_tank", "furniture"))


def cleaning(small, soft):
    # mop standing in its bucket
    bx, by = X0 + 0.70, Y0 + 0.30
    shapes.lathe(small, bx, by, [(0.13, F1), (0.165, F1 + 0.27), (0.155, F1 + 0.27), (0.12, F1 + 0.02)], "plastic_blue", 14,
                 cap_last=True)
    small.face(shapes.ring(bx, by, F1 + 0.10, 0.13, 0.13, 12), "dishwater")
    arc = [Vector((bx, by, F1 + 0.26)) + Vector((0.165 * math.cos(t), 0.0, 0.17 * math.sin(t)))
           for t in (math.pi * k / 10 for k in range(11))]
    shapes.tube(small, arc, 0.004, "metal_steel", segments=4)
    small.cylinder((bx + 0.03, by + 0.02, F1 + 0.10), (-0.10, -0.20, 1.25), 0.013, "wood_mid", segments=6)
    cl.heap(soft, bx + 0.03, by + 0.02, F1 + 0.08, 0.09, 0.09, 0.12, "fabric_pillow", seed=51)
    # a broom and a dustpan against the south wall
    small.cylinder((X0 + 1.10, Y0 + 0.16, F1 + 0.06), (0.06, -0.13, 1.32), 0.012, "wood_mid", segments=6)
    shapes.obox(small, (X0 + 1.10, Y0 + 0.16, F1), (0.30, 0.05, 0.07), 6, "c_brown")
    shapes.obox(small, (X0 + 1.34, Y0 + 0.10, F1), (0.24, 0.02, 0.24), -4, "c_red", lean=-12)
    # an ironing board folded and leant in the corner
    shapes.obox(small, (X0 + 0.16, Y0 + 0.50, F1), (0.035, 0.36, 1.36), 4, "c_grey", lean=0)
    shapes.obox(small, (X0 + 0.135, Y0 + 0.50, F1 + 0.02), (0.012, 0.34, 1.32), 4, "c_teal")
    # an upright vacuum cleaner
    vx, vy = X0 + 1.00, Y1 - 0.34
    shapes.obox(small, (vx, vy, F1), (0.30, 0.34, 0.11), 20, "c_red")
    shapes.lathe(small, vx, vy + 0.02, [(0.10, F1 + 0.11), (0.11, F1 + 0.16), (0.11, F1 + 0.62), (0.08, F1 + 0.70)],
                 "plastic_red", 12)
    small.cylinder((vx, vy + 0.08, F1 + 0.68), (0.0, 0.05, 0.46), 0.014, "metal_steel", segments=6)
    small.cylinder((vx - 0.06, vy + 0.13, F1 + 1.14), (0.12, 0, 0), 0.016, "plastic_black", segments=6)
    dr.cable(small, [(vx + 0.08, vy + 0.10, F1 + 0.5), (vx + 0.2, vy + 0.05, F1 + 0.2), (vx + 0.1, vy - 0.25, F1 + 0.02),
                     (vx - 0.2, vy - 0.4, F1 + 0.015)], radius=0.004)
    # the laundry basket, full
    shapes.lathe(small, X0 + 0.42, Y0 + 0.95, [(0.17, F1), (0.21, F1 + 0.52), (0.20, F1 + 0.52), (0.16, F1 + 0.03)],
                 "wicker", 16, cap_last=True)
    cl.heap(soft, X0 + 0.42, Y0 + 0.95, F1 + 0.42, 0.19, 0.19, 0.20, "fabric_plaid", seed=7)
    cl.heap(soft, X0 + 0.80, Y0 + 1.05, F1, 0.22, 0.17, 0.07, "towel", seed=10, yaw=40)
    shapes.sheet(small, (X0 + 0.95, Y0 + 0.62, F1), 0.21, "magazine_a", yaw=70, lift=0.003)


def build():
    small, soft = MeshBuilder(), MeshBuilder()
    shelves(small)
    tank()
    cleaning(small, soft)
    shapes.soften(small.build("clutter_utility", "clutter"))
    shapes.soften(soft.build("clutter_utility_cloth", "clutter"), 80.0)
    dr.pendant("utility", (X0 + X1) / 2 - 0.2, (Y0 + Y1) / 2, plan.ROOF_Z, drop=0.30, kind="off")
    fx = MeshBuilder()
    dr.switch(fx, ROOM_WEST, 5.82, F1 + 1.22)
    dr.socket(fx, DIVIDER_N, 3.30, F1 + 0.32)
    fx.build("electrics_utility", "fixtures")

    d = Decals("decals_utility", seed=29)
    d.wall("floor_grime", DIVIDER_N, 3.3, F1 + 0.30, 1.4, 0.34)
    d.wall("grime_streaks", UTIL_NORTH_IN, 2.9, F1 + 1.5, 0.6, 1.6)
    d.wall("water_stain", UTIL_NORTH_IN, 3.0, F1 + 2.2, 0.9, 0.7)
    d.wall("rust_stain", UTIL_NORTH_IN, 2.84, F1 + 0.5, 0.22, 0.5)
    d.wall("smudge", ROOM_WEST, 5.82, F1 + 1.2, 0.3, 0.4)
    d.wall("crack", DIVIDER_N, 3.6, F1 + 1.9, 0.8, 0.8)
    d.flat("water_stain", X0 + 0.45, Y1 - 0.45, F1, 0.9, 0.9, angle_deg=30)
    d.flat("smudge", 3.3, 5.3, F1, 1.2, 1.2, angle_deg=10)
    d.flat("water_stain", 3.4, 5.4, plan.ROOF_Z, 1.3, 1.2, up=False, angle_deg=110)
    d.flat("mould", X0 + 0.5, Y1 - 0.5, plan.ROOF_Z, 0.9, 0.9, up=False, angle_deg=90)
    d.build()
