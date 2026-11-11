"""The bathroom: upstairs at the back, where the box room was. Damp has had
years to work on it: mould in the grout, cracked tiles, a ceiling stained by
a leak, rust under every fitting.

The room is x 2.54 to 7.30, y 4.54 to 8.00, floor at 3.06. The bath is in the
north-east corner under the shower, the toilet against the north wall, the
basin and mirror cabinet on the south wall.
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
from .dressing import DIVIDER_N, EAST, F1, NORTH, ROOM_WEST, Decals, Face
from .shapes import loft, ring

TUB = (5.60, 7.24, 7.30, 8.00)      # x0, y0, x1, y1
TUB_H = 0.55


def bath():
    x0, y0, x1, y1 = TUB
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    mb = MeshBuilder()
    n = 28
    loft(mb, [ring(cx, cy, F1, hx, hy, n, 12), ring(cx, cy, F1 + TUB_H - 0.02, hx, hy, n, 12),
              ring(cx, cy, F1 + TUB_H, hx - 0.012, hy - 0.012, n, 10),
              ring(cx, cy, F1 + TUB_H, hx - 0.075, hy - 0.075, n, 5),
              ring(cx - 0.02, cy, F1 + TUB_H - 0.06, hx - 0.10, hy - 0.095, n, 4.5),
              ring(cx - 0.03, cy, F1 + 0.22, hx - 0.16, hy - 0.13, n, 4),
              ring(cx - 0.04, cy, F1 + 0.14, hx - 0.26, hy - 0.20, n, 3.5)], "porcelain", cap_last=True)
    mb.cylinder((x1 - 0.42, cy, F1 + 0.141), (0, 0, 0.003), 0.03, "metal_chrome", segments=10)      # the waste
    tub = shapes.soften(mb.build("bathroom_bath", "furniture"))

    # tiles carried up the two walls round the bath, wetter and mouldier than the rest
    panel = MeshBuilder()
    NORTH.box(panel, x0 - 0.06, x1, 0.0, 0.007, F1 + TUB_H, F1 + 2.06, "tile_bathroom_wet")
    EAST.box(panel, y0 - 0.06, y1, 0.0, 0.007, F1 + TUB_H, F1 + 2.06, "tile_bathroom_wet")
    panel.build("bathroom_bath_tiles", "fixtures")

    # taps, spout and a shower riser on the east wall
    fx = MeshBuilder()
    wall_x = plan.WIDTH - 0.007
    for dy in (-0.11, 0.11):
        fx.cylinder((wall_x, cy + dy, F1 + 0.82), (-0.06, 0, 0), 0.016, "metal_chrome", segments=8)
        for ang in (0.0, 90.0):
            d = Vector((0, math.cos(math.radians(ang)), math.sin(math.radians(ang)))) * 0.035
            fx.cylinder(Vector((wall_x - 0.055, cy + dy, F1 + 0.82)) - d, d * 2, 0.007, "metal_chrome", segments=6)
    shapes.tube(fx, [(wall_x, cy, F1 + 0.72), (wall_x - 0.13, cy, F1 + 0.72), (wall_x - 0.15, cy, F1 + 0.68)], 0.014,
                "metal_chrome")
    shapes.tube(fx, [(wall_x - 0.02, cy, F1 + 0.86), (wall_x - 0.02, cy, F1 + 2.02), (wall_x - 0.20, cy, F1 + 2.06),
                     (wall_x - 0.24, cy, F1 + 2.02)], 0.009, "metal_chrome")
    shapes.lathe(fx, wall_x - 0.25, cy, [(0.012, F1 + 2.03), (0.055, F1 + 1.985), (0.055, F1 + 1.975)], "metal_chrome", 12)
    for z in (F1 + 1.2, F1 + 1.8):
        fx.cylinder((wall_x, cy, z), (-0.02, 0, 0), 0.012, "metal_chrome", segments=8)
    # the curtain rail and its rings
    fx.cylinder((x0 - 0.04, y0 - 0.02, F1 + 2.0), (x1 - x0 + 0.04, 0, 0), 0.011, "metal_chrome", segments=8)
    for k in range(9):
        x = x0 + 0.02 + k * 0.095
        shapes.annulus(fx, x, y0 - 0.02, F1 + 1.985, 0.019, 0.015, 0.004, "plastic_white", n=8)
    fx.build("bathroom_bath_fittings", "fixtures")

    rail = Face("x", y0 - 0.02, -1)
    curtain = dr.curtain("curtain_shower", rail, x0 + 0.0, x0 + 0.84, F1 + 1.975, F1 + 0.20, seed=14, off=0.0,
                         key="shower_curtain")
    curtain.visible_shadow = True
    return tub


def toilet():
    cx, back = 3.26, plan.DEPTH
    mb = MeshBuilder()
    by = back - 0.50                                        # centre of the bowl
    n = 20
    loft(mb, [ring(cx, by + 0.08, F1, 0.11, 0.20, n, 3), ring(cx, by + 0.08, F1 + 0.16, 0.095, 0.17, n, 3),
              ring(cx, by + 0.03, F1 + 0.30, 0.16, 0.22, n, 2.6), ring(cx, by, F1 + 0.385, 0.185, 0.25, n, 2.4),
              ring(cx, by, F1 + 0.395, 0.180, 0.245, n, 2.4), ring(cx, by, F1 + 0.392, 0.135, 0.195, n, 2.4),
              ring(cx, by + 0.02, F1 + 0.27, 0.085, 0.12, n, 2.2)], "porcelain", cap_first=True)
    mb.face(ring(cx, by + 0.02, F1 + 0.285, 0.092, 0.13, n, 2.2), "dishwater")
    # the cistern and its lid
    ty = back - 0.105
    loft(mb, [ring(cx, ty, F1 + 0.40, 0.235, 0.09, 24, 7), ring(cx, ty, F1 + 0.42, 0.245, 0.10, 24, 7),
              ring(cx, ty, F1 + 0.77, 0.250, 0.10, 24, 7)], "porcelain", cap_first=True, cap_last=True)
    loft(mb, [ring(cx, ty, F1 + 0.77, 0.262, 0.112, 24, 7), ring(cx, ty, F1 + 0.80, 0.262, 0.112, 24, 7),
              ring(cx, ty, F1 + 0.81, 0.25, 0.10, 24, 7)], "porcelain", cap_first=True, cap_last=True)
    mb.box((cx - 0.08, back - 0.20, F1 + 0.30), (cx + 0.08, back - 0.02, F1 + 0.41), "porcelain")     # the neck
    mb.cylinder((cx - 0.19, ty - 0.10, F1 + 0.70), (0, -0.018, 0), 0.012, "metal_chrome", segments=8)
    mb.box((cx - 0.20, ty - 0.125, F1 + 0.692), (cx - 0.11, ty - 0.115, F1 + 0.708), "metal_chrome")
    obj = shapes.soften(mb.build("bathroom_toilet", "furniture"))

    # the seat, down, and the lid, up against the cistern
    seat = MeshBuilder()
    loft(seat, [ring(cx, by, F1 + 0.397, 0.19, 0.255, n, 2.4), ring(cx, by, F1 + 0.418, 0.19, 0.255, n, 2.4),
                ring(cx, by, F1 + 0.418, 0.13, 0.19, n, 2.4), ring(cx, by, F1 + 0.397, 0.13, 0.19, n, 2.4)],
         "plastic_white")
    lid = []
    for d, shrink in ((0.0, 0.97), (0.006, 1.0), (0.018, 1.0), (0.022, 0.95)):
        lid.append([Vector((p.x, back - 0.215 - d - (p.y - by + 0.255) * 0.07, F1 + 0.42 + (p.y - by + 0.255)))
                    for p in ring(cx, by, 0.0, 0.19 * shrink, 0.255 * shrink, n, 2.4)])
    loft(seat, lid, "plastic_white", cap_first=True, cap_last=True)
    shapes.soften(seat.build("bathroom_toilet_seat", "furniture", recalc=True))
    return obj


def basin(small):
    """A pedestal basin on the south wall with a mirror cabinet over it."""
    a, wall_y = 5.85, plan.DIVIDER_Y1
    cy = wall_y + 0.235
    mb = MeshBuilder()
    n = 22
    loft(mb, [ring(a, cy - 0.03, F1 + 0.66, 0.13, 0.11, n, 2.5), ring(a, cy, F1 + 0.80, 0.27, 0.21, n, 3),
              ring(a, cy, F1 + 0.855, 0.29, 0.228, n, 3.4), ring(a, cy, F1 + 0.865, 0.285, 0.224, n, 3.4),
              ring(a, cy + 0.015, F1 + 0.86, 0.235, 0.165, n, 3), ring(a, cy + 0.02, F1 + 0.74, 0.12, 0.09, n, 2.4)],
         "porcelain", cap_first=True, cap_last=True)
    loft(mb, [ring(a, cy - 0.05, F1, 0.095, 0.085, 14, 3), ring(a, cy - 0.05, F1 + 0.30, 0.07, 0.065, 14, 3),
              ring(a, cy - 0.05, F1 + 0.68, 0.11, 0.09, 14, 3)], "porcelain", cap_first=True)
    mb.cylinder((a, cy + 0.02, F1 + 0.741), (0, 0, 0.003), 0.022, "metal_chrome", segments=10)
    for dx in (-0.10, 0.10):                                 # pillar taps
        base = Vector((a + dx, wall_y + 0.065, F1 + 0.862))
        shapes.tube(mb, [base, base + Vector((0, 0, 0.07)), base + Vector((0, 0.06, 0.085)),
                         base + Vector((0, 0.08, 0.06))], 0.010, "metal_chrome", segments=8)
        mb.box((base.x - 0.025, base.y - 0.005, base.z + 0.085), (base.x + 0.025, base.y + 0.005, base.z + 0.095),
               "metal_chrome")
    obj = shapes.soften(mb.build("bathroom_basin", "furniture"))

    # mirror cabinet: left door shut, right door ajar on a shelf of pills
    cab = MeshBuilder()
    a0, a1, z0, z1, depth, t = a - 0.29, a + 0.29, F1 + 1.28, F1 + 1.90, 0.13, 0.014
    DIVIDER_N.box(cab, a0, a0 + t, 0.0, depth, z0, z1, "enamel")
    DIVIDER_N.box(cab, a1 - t, a1, 0.0, depth, z0, z1, "enamel")
    DIVIDER_N.box(cab, a0 + t, a1 - t, 0.0, depth, z0, z0 + t, "enamel")
    DIVIDER_N.box(cab, a0 + t, a1 - t, 0.0, depth, z1 - t, z1, "enamel")
    DIVIDER_N.box(cab, a0 + t, a1 - t, 0.0, 0.006, z0 + t, z1 - t, "enamel")
    DIVIDER_N.box(cab, a0 + t, a1 - t, 0.006, depth - 0.02, (z0 + z1) / 2, (z0 + z1) / 2 + 0.008, "enamel")
    # doors: seen from the room (looking south) the left door is at the higher x
    shapes.obox(cab, (a + 0.145, wall_y + depth + 0.006, z0), (0.29, 0.012, z1 - z0), 180.0, "enamel",
                sides={"front": "mirror"})
    hinge = Vector((a0, wall_y + depth, z0))
    swing = math.radians(48.0)
    centre = hinge + Vector((math.cos(swing), math.sin(swing), 0)) * 0.145
    shapes.obox(cab, tuple(centre), (0.29, 0.012, z1 - z0), 180.0 - 48.0, "enamel", sides={"back": "mirror"})
    cab.build("bathroom_cabinet", "fixtures")
    # a strip light over the mirror: the one lamp in the room that still works
    light = MeshBuilder()
    DIVIDER_N.box(light, a - 0.24, a + 0.24, 0.0, 0.07, F1 + 1.96, F1 + 2.02, "plastic_white")
    DIVIDER_N.box(light, a - 0.22, a + 0.22, 0.07, 0.085, F1 + 1.965, F1 + 2.015, "bulb_on")
    lamp = light.build("lamp_mirror", "lamps")
    lamp.visible_shadow = False
    dr.lightpoint("mirror", (a, wall_y + 0.16, F1 + 1.98), "warm", 10.0)

    shelf_z = (z0 + z1) / 2 + 0.008
    for k, (dx, region) in enumerate(((-0.20, "pills"), (-0.13, "pills"), (-0.05, "soap"))):
        if region == "pills":
            cl.tin(small, a + dx, wall_y + 0.07, shelf_z, "pills", radius=0.021, height=0.06, turn=40 * k)
        else:
            shapes.obox(small, (a + dx, wall_y + 0.07, shelf_z), (0.09, 0.035, 0.06), 180, "c_green",
                        prints={"front": "soap"})
    cl.tin(small, a - 0.18, wall_y + 0.06, z0 + t, "pills", radius=0.024, height=0.075, turn=10)
    cl.plastic_bottle(small, a - 0.08, wall_y + 0.06, z0 + t, "conditioner", yaw=180, size=(0.05, 0.03, 0.13))
    # on the basin: a mug of toothbrushes, a squeezed tube, a bar of soap
    dr.mug(small, a + 0.20, wall_y + 0.085, F1 + 0.866)
    for k in range(2):
        small.cylinder((a + 0.20 + 0.01 * k, wall_y + 0.085, F1 + 0.87), (0.02 - 0.04 * k, 0.01, 0.15), 0.004,
                       ("plastic_blue", "plastic_red")[k], segments=5)
    shapes.obox(small, (a - 0.20, wall_y + 0.10, F1 + 0.866), (0.13, 0.035, 0.022), 200, "c_white",
                prints={"top": "toothpaste"})
    shapes.obox(small, (a + 0.02, wall_y + 0.07, F1 + 0.866), (0.075, 0.05, 0.022), 12, "c_cream")
    return obj


def furnishings(small, soft):
    fx = MeshBuilder()
    # towel rail on the south wall, one towel hung and one on the floor
    DIVIDER_N.box(fx, 3.98, 4.00, 0.0, 0.075, F1 + 1.12, F1 + 1.14, "metal_chrome")
    DIVIDER_N.box(fx, 4.66, 4.68, 0.0, 0.075, F1 + 1.12, F1 + 1.14, "metal_chrome")
    fx.cylinder(DIVIDER_N.P(3.98, 0.065, F1 + 1.13), DIVIDER_N.along * 0.70, 0.009, "metal_chrome", segments=8)
    # roll holder by the toilet
    NORTH.box(fx, 3.66, 3.68, 0.0, 0.06, F1 + 0.66, F1 + 0.72, "metal_chrome")
    fx.cylinder(NORTH.P(3.68, 0.05, F1 + 0.69), NORTH.along * 0.13, 0.008, "metal_chrome", segments=6)
    fx.cylinder(NORTH.P(3.695, 0.05, F1 + 0.69), NORTH.along * 0.10, 0.045, "paper", segments=12)
    # roller blind, half down, with its cord
    NORTH.box(fx, 4.08, 5.76, 0.012, 0.02, F1 + 1.58, F1 + 2.30, "fabric_curtain")
    NORTH.box(fx, 4.07, 5.77, 0.008, 0.026, F1 + 1.56, F1 + 1.585, "wood_mid")
    fx.cylinder(NORTH.P(4.07, 0.03, F1 + 2.29), NORTH.along * 1.70, 0.018, "plastic_white", segments=8)
    fx.cylinder(NORTH.P(5.72, 0.035, F1 + 1.30), (0, 0, 0.98), 0.0015, "plastic_white", segments=4, caps="none")
    # the light pull by the door
    fx.cylinder((2.92, 5.95, F1 + 1.35), (0, 0, plan.CEILING - 1.35), 0.0012, "plastic_white", segments=4, caps="none")
    fx.cylinder((2.92, 5.95, F1 + 1.31), (0, 0, 0.045), 0.008, "plastic_white", segments=6)
    fx.build("bathroom_fittings", "fixtures")

    dr.curtain("towel_bathroom", DIVIDER_N, 4.10, 4.50, F1 + 1.142, F1 + 0.60, seed=21, off=0.078, key="towel")
    dr.rug("bathmat", 6.02, 6.50, 6.86, 7.06, F1, key="towel")
    dr.radiator("radiator_bathroom", NORTH, 4.35, 5.45, F1)
    dr.pendant("bathroom", 4.6, 6.0, plan.ROOF_Z, drop=0.40, kind="off")

    # open shelves on the west wall
    unit = MeshBuilder()
    a0, a1, depth, height = 6.50, 7.10, 0.26, 1.10
    ROOM_WEST.box(unit, a0, a0 + 0.018, 0.0, depth, F1, F1 + height, "enamel")
    ROOM_WEST.box(unit, a1 - 0.018, a1, 0.0, depth, F1, F1 + height, "enamel")
    levels = (0.06, 0.40, 0.74, height - 0.018)
    for z in levels:
        ROOM_WEST.box(unit, a0 + 0.018, a1 - 0.018, 0.0, depth, F1 + z, F1 + z + 0.018, "enamel")
    unit.build("bathroom_shelves", "furniture")
    sx = plan.PART_X1 + 0.13
    cl.folded(small, sx, 6.68, F1 + 0.418, 0.20, 0.30, "towel", layers=4, yaw=3, seed=2)
    cl.folded(small, sx, 6.94, F1 + 0.418, 0.20, 0.22, "fabric_pillow", layers=2, yaw=-4, seed=3)
    for k, (y, lean) in enumerate(((6.62, 0), (6.74, 0), (6.86, 0))):
        small.cylinder((sx, y, F1 + 0.758), (0, 0, 0.10), 0.052, "paper", segments=12)
    small.cylinder((sx + 0.01, 6.74, F1 + 0.858), (0, 0, 0.10), 0.052, "paper", segments=12)
    cl.plastic_bottle(small, sx, 7.00, F1 + 0.758, "bleach", yaw=92, size=(0.085, 0.05, 0.22))
    shapes.obox(small, (sx, 6.80, F1 + 1.10), (0.24, 0.12, 0.085), 88, "c_teal", prints={"front": "tissues"})
    cl.plastic_bottle(small, sx, 6.62, F1 + 1.10, "shampoo", yaw=80)
    cl.folded(small, sx, 6.80, F1 + 0.078, 0.20, 0.34, "towel", layers=3, yaw=-2, seed=5)

    # bottles round the bath, and what has been left on the floor
    cl.plastic_bottle(small, 5.72, 7.93, F1 + TUB_H, "shampoo", yaw=10)
    cl.plastic_bottle(small, 5.82, 7.94, F1 + TUB_H, "conditioner", yaw=-14)
    shapes.obox(small, (6.05, 7.95, F1 + TUB_H), (0.075, 0.05, 0.022), 30, "c_cream")
    cl.plastic_bottle(small, 6.9, 7.28, F1 + TUB_H, "shampoo", yaw=75, size=(0.07, 0.04, 0.04))        # one on its side
    # laundry basket with the washing spilling out of it
    shapes.lathe(small, 3.12, 6.10, [(0.17, F1), (0.21, F1 + 0.52), (0.20, F1 + 0.52), (0.16, F1 + 0.03)], "wicker", 16,
                 cap_last=True)
    cl.heap(soft, 3.12, 6.10, F1 + 0.42, 0.19, 0.19, 0.20, "fabric_plaid", seed=7)
    cl.heap(soft, 3.46, 6.30, F1, 0.26, 0.20, 0.10, "fabric_curtain", seed=8, yaw=-25)
    cl.heap(soft, 3.36, 5.86, F1, 0.18, 0.14, 0.06, "towel", seed=10, yaw=40)
    cl.heap(soft, 5.30, 6.86, F1, 0.30, 0.22, 0.07, "towel", seed=9, yaw=18)                           # a dropped towel
    # a chair by the bath with clothes left on it, and a stool
    models.place("painted_wooden_chair_01", "bathroom_chair", (5.22, 7.56, F1), facing=-25)
    cl.heap(soft, 5.22, 7.54, F1 + 0.46, 0.17, 0.15, 0.09, "fabric_plaid", seed=12)
    models.place("wooden_stool_01", "bathroom_stool", (4.62, 5.02, F1), facing=30)
    # scales, a bin, the toilet brush and a plunger
    shapes.obox(small, (4.95, 5.20, F1), (0.30, 0.30, 0.045), 12, "c_grey")
    shapes.lathe(small, 5.38, 4.74, [(0.10, F1), (0.12, F1 + 0.26), (0.11, F1 + 0.26), (0.09, F1 + 0.02)],
                 "plastic_cream", 12, cap_last=True)
    shapes.lathe(small, 3.62, 7.86, [(0.055, F1), (0.06, F1 + 0.14)], "plastic_white", 10)
    small.cylinder((3.62, 7.86, F1 + 0.10), (0.01, 0, 0.32), 0.008, "plastic_white", segments=6)
    shapes.lathe(small, 2.86, 7.84, [(0.07, F1), (0.06, F1 + 0.06), (0.015, F1 + 0.09)], "rubber", 12)
    small.cylinder((2.86, 7.84, F1 + 0.08), (0.0, 0.03, 0.46), 0.011, "wood_mid", segments=6)
    cl.tin(small, 3.02, 7.50, F1, "beer", radius=0.032, height=0.12, turn=70)
    shapes.sheet(small, (3.55, 7.30, F1), 0.22, "magazine_b", yaw=20, lift=0.004)
    shapes.sheet(small, (3.60, 7.34, F1), 0.30, "newspaper", yaw=-30, lift=0.002)


def decals():
    d = Decals("decals_bathroom", seed=28)
    tile = 0.0095                                             # clear of the tile panels round the bath
    # cracked tiles
    d.wall("crack", NORTH, 6.55, F1 + 1.35, 1.0, 1.0, offset=tile)
    d.wall("crack", EAST, 7.55, F1 + 1.05, 0.8, 0.8, offset=tile)
    d.wall("crack", ROOM_WEST, 7.45, F1 + 0.95, 0.9, 0.9)
    d.wall("crack", DIVIDER_N, 6.75, F1 + 0.85, 0.9, 0.9)
    d.wall("plaster_damage", NORTH, 3.75, F1 + 1.18, 0.42, 0.42)                      # tiles gone, wall showing
    # mould: in the wet corner, along the ceiling line, behind the toilet
    d.wall("mould", NORTH, 6.80, F1 + 2.24, 1.0, 0.92, flip=True)
    d.wall("mould", EAST, 7.50, F1 + 2.24, 1.0, 0.92, flip=False)
    d.wall("mould", NORTH, 3.05, F1 + 2.20, 1.0, 1.0, flip=False)
    d.wall("mould", ROOM_WEST, 7.50, F1 + 2.20, 1.0, 1.0, flip=True)
    d.wall("mould", DIVIDER_N, 6.85, F1 + 2.25, 0.9, 0.9, flip=False)
    d.wall("grime_streaks", NORTH, 4.9, F1 + 0.46, 1.5, 0.78)                          # under the window
    d.wall("grime_streaks", EAST, 5.6, F1 + 2.0, 0.9, 1.3)
    d.wall("water_stain", ROOM_WEST, 6.0, F1 + 2.25, 1.1, 0.8)
    # rust and scale below the fittings
    d.wall("limescale", EAST, 7.62, F1 + 1.30, 0.34, 1.30, offset=tile)
    d.wall("rust_stain", EAST, 7.62, F1 + 0.66, 0.22, 0.20, offset=tile)
    d.wall("rust_stain", NORTH, 3.26, F1 + 0.30, 0.30, 0.50)
    d.wall("rust_stain", DIVIDER_N, 5.85, F1 + 0.50, 0.26, 0.56)
    d.wall("rust_stain", NORTH, 4.38, F1 + 0.14, 0.14, 0.26)
    d.wall("floor_grime", NORTH, 4.4, F1 + 0.30, 1.9, 0.34)
    d.wall("floor_grime", DIVIDER_N, 4.4, F1 + 0.30, 1.8, 0.34)
    d.wall("floor_grime", ROOM_WEST, 7.0, F1 + 0.30, 1.9, 0.34)
    d.wall("floor_grime", Face("x", TUB[1], -1), 6.45, F1 + 0.22, 1.6, 0.38, offset=0.004)       # the bath panel
    d.wall("smudge", ROOM_WEST, 5.9, F1 + 1.2, 0.36, 0.42)
    # the floor
    d.flat("water_stain", 6.3, 6.75, F1, 1.6, 1.1, angle_deg=8)
    d.flat("water_stain", 3.35, 7.35, F1, 1.0, 1.0, angle_deg=60)
    d.flat("smudge", 3.5, 5.4, F1, 1.6, 1.3, angle_deg=30)
    d.flat("mould", 7.0, 7.1, F1, 0.6, 0.5, angle_deg=270)
    d.flat("stain_rings", 5.0, 6.3, F1, 0.7, 0.7, angle_deg=40)
    # the ceiling: one bad leak over the bath, a second over the door, mould spreading from the corners
    d.flat("water_stain", 6.2, 7.0, plan.ROOF_Z, 2.3, 1.9, up=False, angle_deg=20)
    d.flat("water_stain", 3.6, 5.4, plan.ROOF_Z, 1.7, 1.5, up=False, angle_deg=110)
    d.flat("water_stain", 5.0, 6.2, plan.ROOF_Z, 1.2, 1.0, up=False, angle_deg=200)
    d.flat("mould", 6.75, 7.45, plan.ROOF_Z, 1.1, 1.1, up=False, angle_deg=90)
    d.flat("mould", 3.09, 7.45, plan.ROOF_Z, 1.1, 1.1, up=False, angle_deg=180)
    d.flat("mould", 6.75, 5.09, plan.ROOF_Z, 1.0, 1.0, up=False, angle_deg=0)
    d.flat("plaster_damage", 6.35, 7.15, plan.ROOF_Z, 0.7, 0.7, up=False, angle_deg=35)
    d.build()


def build():
    small, soft = MeshBuilder(), MeshBuilder()
    bath()
    toilet()
    basin(small)
    furnishings(small, soft)
    shapes.soften(soft.build("clutter_bathroom_cloth", "clutter"), 80.0)
    obj = shapes.soften(small.build("clutter_bathroom", "clutter"))
    obj.visible_shadow = True
    fx = MeshBuilder()
    dr.socket(fx, DIVIDER_N, 6.45, F1 + 1.25)
    fx.build("electrics_bathroom", "fixtures")
    decals()
