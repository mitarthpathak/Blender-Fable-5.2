"""Phase 5: furnish and dress the house.

Placement is written out room by room; the kitchen and the bathroom have
modules of their own (kitchen.py, bathroom.py). Furniture comes from Poly Haven
models where a good one exists and is built here where it has to fit the
room (bed, wardrobe, chest, bookcases, curtains, radiators).
"""

from __future__ import annotations

import math
import random

from mathutils import Vector

import plan
from . import dressing as dr
from . import bathroom, joinery, kitchen, models, shapes, shell, utility, yard
from . import clutter as cl
from .core import MeshBuilder
from .dressing import (CHIMNEY, DIVIDER_N, DIVIDER_S, EAST, F1, HALL_EAST, NORTH, ROOM_WEST, SOUTH, WEST,
                       Decals)

GF = 0.0


def put(model_id, name, x, y, z=0.0, facing=-90.0, **kw):
    return models.place(model_id, name, (x, y, z), facing=facing, **kw)


# --- Furniture built to fit ---------------------------------------------------

def bed(name, x0, y0, x1, y1, floor, seed=5, coll="furniture"):
    """A double bed with its head against the wall at y1, left unmade."""
    rng = random.Random(seed)
    made = []
    frame = MeshBuilder()
    wood = "wood_dark"
    frame.box((x0, y1 - 0.05, floor), (x1, y1, floor + 1.05), wood)                     # headboard
    frame.box((x0, y0, floor), (x1, y0 + 0.04, floor + 0.50), wood)                      # footboard
    for x in (x0, x1 - 0.03):
        frame.box((x, y0 + 0.04, floor + 0.20), (x + 0.03, y1 - 0.05, floor + 0.36), wood)
    for x, y in ((x0, y0), (x1 - 0.06, y0), (x0, y1 - 0.06), (x1 - 0.06, y1 - 0.06)):
        frame.box((x, y, floor), (x + 0.06, y + 0.06, floor + 0.22), wood)
    made.append(frame.build(name + "_frame", coll, recalc=True))

    soft = MeshBuilder()
    mz = floor + 0.36
    soft.box((x0 + 0.04, y0 + 0.05, mz - 0.04), (x1 - 0.04, y1 - 0.06, mz + 0.18), "fabric_pillow", skip="-z")
    made.append(soft.build(name + "_mattress", coll))

    # Duvet: a draped sheet, thrown back at one corner.
    duvet = MeshBuilder()
    nx, ny = 26, 30
    top = mz + 0.215
    xa, xb, ya, yb = x0 - 0.10, x1 + 0.10, y0 - 0.06, y1 - 0.62
    tile = 0.9
    grid = []
    for i in range(nx + 1):
        row = []
        for j in range(ny + 1):
            s, t = i / nx, j / ny
            x, y = xa + (xb - xa) * s, ya + (yb - ya) * t
            z = top + 0.035 * math.sin(7.0 * s + 2.2 * t) * math.sin(5.0 * t + 1.3) + 0.02 * math.sin(13 * s * t + 1)
            z += rng.uniform(-0.006, 0.006)
            over = max(x0 + 0.04 - x, x - (x1 - 0.04), y0 + 0.05 - y, 0.0)             # past the mattress edge
            z -= min(0.42, over * 3.2)
            fold = max(0.0, (s - 0.55)) * max(0.0, (t - 0.6)) * 4.0                      # thrown-back corner
            y -= fold * 0.30
            z += fold * 0.10
            row.append((Vector((x, y, z)), (x / tile, y / tile)))
        grid.append(row)
    for i in range(nx):
        for j in range(ny):
            quad = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
            duvet.face([q[0] for q in quad], "fabric_bed", uvs=[q[1] for q in quad])
    made.append(duvet.build(name + "_duvet", coll, smooth=True))

    # Pillows: one slept on, one shoved against the headboard, one on the floor beside the bed.
    pillows = MeshBuilder()
    mid = (x0 + x1) / 2
    cl.pillow(pillows, mid - 0.40, y1 - 0.36, top + 0.085, 0.34, 0.23, 0.17, yaw=6.0, dent=0.45, seed=1)
    cl.pillow(pillows, mid + 0.38, y1 - 0.25, top + 0.17, 0.34, 0.23, 0.18, yaw=-9.0, lean=38.0, dent=0.15, seed=2)
    cl.pillow(pillows, x1 + 0.42, y0 + 0.75, floor + 0.07, 0.33, 0.22, 0.16, yaw=64.0, dent=0.2, seed=3)
    made.append(shapes.soften(pillows.build(name + "_pillows", coll), 60.0))
    return made


def wardrobe(name, face, a0, a1, floor, depth=0.58, height=2.02, ajar=24.0, coll="furniture"):
    """A two-door wardrobe. The right-hand door is a separate object, hinged, left ajar."""
    wood = "wood_dark"
    made = []
    mb = MeshBuilder()
    t = 0.022
    face.box(mb, a0, a0 + t, 0.0, depth, floor, floor + height, wood)
    face.box(mb, a1 - t, a1, 0.0, depth, floor, floor + height, wood)
    face.box(mb, a0, a1, 0.0, 0.01, floor, floor + height, wood)
    face.box(mb, a0 + t, a1 - t, 0.0, depth, floor + 0.09, floor + 0.11, wood)
    face.box(mb, a0 + t, a1 - t, 0.0, depth, floor + height - t, floor + height, wood)
    face.box(mb, a0 + t, a1 - t, 0.02, depth - 0.02, floor, floor + 0.09, wood)
    face.box(mb, a0 - 0.02, a1 + 0.02, 0.0, depth + 0.03, floor + height, floor + height + 0.05, wood)
    face.box(mb, a0 + t, a1 - t, 0.05, 0.07, floor + height - 0.2, floor + height - 0.18, "metal_brass")  # rail
    mid = (a0 + a1) / 2
    W, H, dt = mid - a0 - t - 0.003, height - 0.11 - t - 0.006, 0.02
    z0 = floor + 0.113

    def panels(w):
        return [(0.07, 0.10, w - 0.07, H * 0.42, False), (0.07, H * 0.42 + 0.08, w - 0.07, H - 0.08, False)]

    # left door, shut: part of the carcass
    def left(u, d, v):
        return face.P(a0 + t + 0.0015 + u, depth - d, z0 + v)
    joinery.build_leaf(mb, left, W, H, dt, panels(W), wood)
    lp = left(W - 0.03, -0.012, H * 0.5)
    mb.cylinder(lp, face.normal * 0.02, 0.011, "metal_brass", segments=8)
    made.append(mb.build(name, coll, recalc=True))

    door = MeshBuilder()

    def right(u, d, v):
        return face.P(a1 - t - 0.0015 - u, depth - d, z0 + v)
    joinery.build_leaf(door, right, W, H, dt, panels(W), wood)
    rp = right(W - 0.03, -0.012, H * 0.5)
    door.cylinder(rp, face.normal * 0.02, 0.011, "metal_brass", segments=8)
    hinge = face.P(a1 - t - 0.0015, depth, floor)
    leaf = door.build(name + "_door", coll, origin=hinge, recalc=True)
    # A leaf running towards -a opens outwards with a turn of this sign.
    sign = 1.0 if face.axis == "y" else -1.0
    leaf.rotation_euler = (0, 0, math.radians(ajar) * sign * face.sign)
    made.append(leaf)
    return made


def chest(name, face, a0, a1, floor, depth=0.46, height=0.92, open_drawer=1, coll="furniture"):
    wood = "wood_dark"
    mb = MeshBuilder()
    t = 0.02
    face.box(mb, a0, a1, 0.0, depth - 0.02, floor + 0.08, floor + height - t, wood)
    face.box(mb, a0 - 0.012, a1 + 0.012, 0.0, depth + 0.012, floor + height - t, floor + height, wood)
    for a in (a0, a1 - 0.05):
        face.box(mb, a, a + 0.05, 0.02, depth - 0.02, floor, floor + 0.08, wood)
    n = 4
    dh = (height - t - 0.08 - 0.02) / n
    for k in range(n):
        z0 = floor + 0.09 + k * dh
        out = 0.17 if k == open_drawer else 0.0
        face.box(mb, a0 + 0.02, a1 - 0.02, depth - 0.02 + out, depth + out, z0, z0 + dh - 0.012, wood)
        if out:                                              # the drawer box, and something left hanging out
            face.box(mb, a0 + 0.03, a1 - 0.03, depth - 0.36 + out, depth - 0.02 + out, z0, z0 + dh - 0.05, wood,
                     skip="+z")
            face.box(mb, a0 + 0.10, a0 + 0.42, depth - 0.2 + out, depth + 0.035 + out, z0 + dh - 0.06, z0 + dh - 0.035,
                     "fabric_pillow")
        for a in (a0 + (a1 - a0) * 0.27, a0 + (a1 - a0) * 0.73):
            p = face.P(a, depth + out, z0 + dh / 2 - 0.006)
            mb.cylinder(p, face.normal * 0.022, 0.012, "metal_brass", segments=8)
    return [mb.build(name, coll, recalc=True)]


# --- Rooms ------------------------------------------------------------------

def hall():
    put("side_table_tall_01", "hall_side_table", 2.18, 2.95, GF, facing=180)
    dr.table_lamp("hall_table", (2.18, 2.95, 0.762), kind="warm", watts=12)
    dr.pendant("hall", 1.78, 5.30, plan.CEILING, drop=0.50, kind="flicker", watts=18, style="bell")
    dr.radiator("radiator_hall", HALL_EAST, 3.95, 4.95, GF)
    rail, hooks = dr.coat_rail("coat_rail_hall", WEST, 0.35, 1.55, 1.68)
    dr.curtain("coat_hall_dark", WEST, hooks[1] - 0.20, hooks[1] + 0.22, 1.66, 0.62, seed=11, off=0.085,
               key="fabric_bed")
    dr.curtain("coat_hall_long", WEST, hooks[3] - 0.19, hooks[3] + 0.21, 1.66, 0.48, seed=12, off=0.09,
               key="fabric_curtain")
    dr.rug("doormat_hall", 1.42, 0.12, 2.12, 0.62, GF, key="rubber", fringe=False, thick=0.012)
    dr.mail("mail_hall", (1.74, 0.82, GF + 0.012), count=11, seed=4, spread=0.42)
    put("hanging_picture_frame_03", "picture_stair_1", 0.0, 3.05, 2.40, facing=0)
    put("hanging_picture_frame_03", "picture_stair_2", 0.0, 3.92, 2.93, facing=0, tilt=(0, 7.0))
    put("fancy_picture_frame_01", "picture_hall", plan.PART_X0, 4.45, 1.62, facing=180)
    put("cardboard_box_01", "box_hall_1", 0.42, 7.55, GF, facing=20)
    put("cardboard_box_01", "box_hall_2", 0.44, 7.50, 0.34, facing=-15, scale=0.85)
    put("plastic_crate_03", "crate_hall", 0.55, 7.02, GF, facing=95)
    # a framed picture taken down and left leaning at the foot of the stair wall
    put("hanging_picture_frame_02", "picture_leaning", 0.10, 1.82, 0.27, facing=0, tilt=(0, 0))

    # Lived in: shoes under the coats, an umbrella, the post, a telephone, family photographs.
    small, soft = MeshBuilder(), MeshBuilder()
    dr.curtain("coat_hall_short", WEST, hooks[0] - 0.17, hooks[0] + 0.17, 1.66, 0.92, seed=13, off=0.08,
               key="fabric_plaid")
    for y, yaw, kind, boot in ((0.50, 4, "wood_dark", True), (0.63, -6, "wood_dark", True), (0.92, 10, "rubber", False),
                               (1.04, -3, "rubber", False), (1.34, 14, "vinyl", False)):
        cl.shoe(small, 0.20, y, GF, yaw=yaw, key=kind, boot=boot)
    cl.shoe(small, 0.46, 1.50, GF, yaw=-40, key="vinyl", tipped=True)
    cl.umbrella(small, (0.07, 0.10, GF), (0.05, 0.05, GF + 0.86))
    cl.post(small, 1.72, 0.80, GF + 0.013, seed=5, spread=0.36, count=9)
    cl.paper_stack(small, 2.12, 0.42, GF, count=14, yaw=8, seed=2)
    shapes.sheet(small, (2.10, 0.44, GF + 0.128), 0.21, "magazine_a", yaw=30, lift=0.001)
    cl.phone(small, 2.17, 3.06, GF + 0.762, yaw=-82)
    cl.book(small, 2.19, 2.83, GF + 0.762, "phonebook", yaw=-96, size=(0.15, 0.21, 0.035))
    cl.keys_dish(small, 2.16, 2.80, GF + 0.797, seed=3)
    cl.framed(small, HALL_EAST, 2.55, 1.66, 0.25, "photo_a", tilt=-1.5)
    cl.framed(small, HALL_EAST, 2.93, 1.58, 0.19, "photo_d", tilt=5.0, key="wood_mid")
    cl.framed(small, HALL_EAST, 2.60, 1.34, 0.16, "photo_b", tilt=1.0, key="metal_brass")
    shapes.poster(small, HALL_EAST, 0.50, 1.52, 0.21, "missing", tilt=2.0)                     # taped up by the front door
    shapes.poster(small, HALL_EAST, 0.74, 1.40, 0.15, "letter", tilt=-3.0)
    cl.open_box(small, 1.80, 7.46, GF, yaw=14, seed=1)
    cl.heap(soft, 1.80, 7.46, GF + 0.14, 0.19, 0.14, 0.14, "fabric_curtain", seed=4, yaw=14, spread=0.0)
    cl.open_box(small, 1.28, 7.60, GF, size=(0.40, 0.40, 0.34), yaw=-8, flaps=(170.0, 100.0, 160.0, 120.0), seed=2)
    for k in range(5):
        cl.book(small, 1.28 + 0.01 * k, 7.60, GF + 0.03 + k * 0.03, yaw=-8 + 9 * k, key=dr.BOOK_COLORS[k])
    shapes.soften(small.build("clutter_hall", "clutter"))
    shapes.soften(soft.build("clutter_hall_cloth", "clutter"), 80.0)

    fx = MeshBuilder()
    dr.cable(fx, [(2.10, 3.12, 0.77), (2.02, 3.22, 0.60), (2.30, 3.45, 0.04), (2.385, 3.56, 0.30)], radius=0.0028,
             key="plastic_cream")
    dr.switch(fx, HALL_EAST, 0.95, 1.22, double=True)             # by the front door
    dr.switch(fx, WEST, 7.25, 1.22)
    dr.socket(fx, HALL_EAST, 3.62, 0.32)
    dr.cable(fx, [(2.20, 2.96, 0.78), (2.33, 3.05, 0.60), (2.37, 3.30, 0.05), (2.385, 3.62, 0.30)], radius=0.003)
    fx.build("electrics_hall", "fixtures")

    d = Decals("decals_hall", seed=21)
    d.wall("floor_grime", HALL_EAST, 3.2, 0.34, 2.6, 0.36)
    d.wall("floor_grime", HALL_EAST, 6.2, 0.33, 2.2, 0.34)
    d.wall("floor_grime", WEST, 1.0, 0.34, 1.9, 0.36)
    d.wall("grime_streaks", WEST, 3.4, 2.05, 0.8, 1.5)
    d.wall("crack", WEST, 2.7, 2.2, 1.25, 1.25)
    d.wall("plaster_damage", HALL_EAST, 5.15, 1.34, 0.62, 0.62)
    d.wall("smudge", HALL_EAST, 0.95, 1.2, 0.36, 0.42)
    d.wall("smudge", HALL_EAST, 2.18, 1.05, 0.30, 0.5)
    d.wall("grime_streaks", NORTH, 0.7, 2.0, 0.9, 1.4)
    d.flat("water_stain", 1.75, 6.4, plan.CEILING, 1.5, 1.3, up=False, angle_deg=25)
    d.flat("smudge", 1.76, 1.1, GF, 1.3, 1.0, angle_deg=10)
    d.flat("nicotine", 1.5, 2.2, plan.CEILING, 1.8, 2.2, up=False, angle_deg=80)
    d.build()


def living():
    put("sofa_02", "sofa", 4.28, 2.30, GF, facing=0)
    dr.rug("rug_living", 4.05, 1.05, 6.55, 3.55, GF, seed=1, lift=0.025)
    put("small_wooden_table_01", "coffee_table", 5.42, 2.30, 0.012, facing=0)
    put("ArmChair_01", "armchair", 6.02, 3.42, GF, facing=-82)
    put("side_table_01", "tv_table", 6.98, 0.82, GF, facing=180)
    put("television_02", "television", 6.98, 0.82, 0.551, facing=158)
    dr.lightpoint("tv", (6.75, 0.92, 0.78), "tv", 6.0)
    put("potted_plant_02", "plant_living", 3.08, 0.62, GF, facing=40, scale=0.85)
    dr.bookcase("bookcase_living", EAST, 3.14, 4.36, GF, seed=2)
    put("vintage_grandfather_clock_01", "clock_living", 4.42, 4.16, GF, facing=-90)
    put("WoodenTable_03", "sideboard", 5.42, 4.12, GF, facing=-90)
    dr.table_lamp("sideboard", (5.86, 4.14, 0.832), kind="warm", watts=20)
    dr.broken_floor_lamp("broken", (2.86, 2.55, GF), direction_deg=76)
    dr.pendant("living", 4.9, 2.3, plan.CEILING, drop=0.6, kind="off", style="drum")
    put("mantel_clock_01", "mantel_clock", 6.84, 2.30, 1.146, facing=180)
    put("standing_picture_frame_02", "mantel_photo", 6.85, 1.74, 1.146, facing=165)
    put("brass_vase_01", "mantel_vase", 6.84, 2.90, 1.146, facing=0, scale=0.55)
    put("fancy_picture_frame_02", "picture_fireplace", 6.95, 2.30, 1.86, facing=180)
    put("wine_bottles_01", "bottles", 5.36, 2.02, 0.545, facing=20, scale=0.9)
    put("ceramic_vase_01", "vase_sideboard", 5.02, 4.14, 0.832, facing=0, scale=0.8)
    put("Ottoman_01", "ottoman", 5.18, 3.30, 0.012, facing=-75, scale=0.7)
    dr.radiator("radiator_living", SOUTH, 4.22, 5.62, GF)

    dr.curtain_pole("pole_living_front", SOUTH, 3.50, 6.34, 2.40)
    dr.curtain("curtain_living_front_l", SOUTH, 3.52, 4.18, 2.39, 0.04, seed=1)
    # (drawn back clear of the radiator: it used to hang through it)
    dr.curtain("curtain_living_front_r", SOUTH, 5.70, 6.33, 2.39, 0.04, seed=2)
    # the side window by the chimney: one thin curtain pushed to the side, stopping at the sill
    dr.curtain_pole("pole_living_side", EAST, 0.28, 1.32, 2.37, off=0.06)
    dr.curtain("curtain_living_side", EAST, 0.34, 0.84, 2.36, 0.965, seed=8, off=0.06, key="fabric_pillow")

    small, soft = MeshBuilder(), MeshBuilder()
    table = 0.548
    dr.mug(small, 5.50, 2.52, table)
    dr.mug(small, 5.33, 2.44, table)
    shapes.sheet(small, (5.43, 2.20, table), 0.30, "newspaper", yaw=118, lift=0.002)
    shapes.sheet(small, (5.48, 2.02, table), 0.20, "magazine_a", yaw=70, lift=0.004)
    cl.ashtray(small, 5.36, 2.62, table, butts=7, seed=6)
    cl.cigarettes(small, 5.50, 2.66, table, yaw=25)
    shapes.obox(small, (5.42, 2.70, table), (0.045, 0.055, 0.006), -30, "c_red", prints={"top": "matchbook"})
    cl.remote(small, 5.30, 2.28, table, yaw=-20)
    cl.tin(small, 5.52, 2.36, table, "beer", radius=0.032, height=0.12, turn=40)
    cl.tin(small, 5.05, 2.95, 0.045, "beer", radius=0.032, height=0.12, turn=120)         # one on the rug, on its side
    shapes.sheet(small, (4.9, 3.05, 0.013), 0.30, "newspaper", yaw=64, lift=0.002)
    shapes.sheet(small, (5.0, 1.5, 0.013), 0.21, "magazine_b", yaw=-20, lift=0.002)
    # on the sofa: two cushions and a blanket someone slept under
    cl.pillow(soft, 4.02, 1.68, 0.60, 0.22, 0.22, 0.15, yaw=90, lean=-62, seed=11, key="fabric_plaid")
    cl.pillow(soft, 4.20, 3.02, 0.50, 0.22, 0.22, 0.15, yaw=70, lean=-18, dent=0.4, seed=12, key="fabric_plaid")
    cl.heap(soft, 4.30, 2.35, 0.40, 0.26, 0.55, 0.12, "fabric_plaid", seed=13, spread=0.25)
    cl.pillow(soft, 5.9, 3.42, 0.52, 0.20, 0.20, 0.13, yaw=10, lean=-30, seed=14, key="fabric_curtain")
    # by the television: a video recorder, tapes, and slippers kicked off by the armchair
    shapes.obox(small, (6.98, 0.82, 0.30), (0.26, 0.38, 0.085), 68, "c_black")
    cl.vhs_stack(small, 6.60, 1.36, 0.012, count=5, yaw=20, seed=3)
    cl.vhs_stack(small, 6.86, 1.32, 0.012, count=2, yaw=-35, seed=4)
    cl.shoe(small, 5.62, 2.96, 0.012, yaw=-70, key="fabric_plaid", length=0.27)
    cl.shoe(small, 5.80, 2.86, 0.012, yaw=-95, key="fabric_plaid", length=0.27)
    # photographs: on the sideboard and the mantelpiece, and hung over the sideboard
    cl.standing_photo(small, 5.30, 4.20, 0.832, "photo_c", yaw=6)
    cl.standing_photo(small, 4.92, 4.26, 0.832, "polaroid", yaw=-14, width=0.09, key="wood_dark")
    cl.standing_photo(small, 6.86, 2.62, 1.146, "photo_b", yaw=-96, width=0.11)
    cl.framed(small, DIVIDER_S, 5.55, 1.62, 0.34, "photo_a", tilt=-2.0)
    # over the sofa (the model that hung here has a black canvas)
    cl.framed(small, ROOM_WEST, 3.55, 1.64, 0.62, "photo_c", tilt=-3.0, border=0.045)
    cl.framed(small, DIVIDER_S, 5.08, 1.52, 0.20, "photo_d", tilt=4.0, key="metal_brass")
    cl.framed(small, DIVIDER_S, 6.02, 1.50, 0.18, "photo_c", tilt=-1.0, key="wood_mid")
    # a packing box by the bookcase, half filled with what came off its shelves
    cl.open_box(small, 6.58, 3.72, 0.0, yaw=80, seed=3)
    for k in range(6):
        cl.book(small, 6.58, 3.72 + 0.004 * k, 0.03 + k * 0.032, yaw=80 + 11 * k, key=dr.BOOK_COLORS[(k * 2) % 6])
    cl.book(small, 6.36, 4.10, 0.0, "paperback", yaw=30)
    cl.book(small, 6.42, 4.14, 0.028, yaw=75, key="book_green")
    shapes.soften(small.build("clutter_living", "clutter"))
    shapes.soften(soft.build("clutter_living_cloth", "clutter"), 80.0)

    fx = MeshBuilder()
    dr.switch(fx, ROOM_WEST, 2.22, 1.22, double=True)
    dr.socket(fx, SOUTH, 6.72, 0.32)
    dr.socket(fx, DIVIDER_S, 6.25, 0.32)
    dr.cable(fx, [(6.96, 0.66, 0.60), (6.99, 0.42, 0.30), (6.90, 0.10, 0.02), (6.74, 0.012, 0.30)], radius=0.0035)
    dr.cable(fx, [(5.87, 4.15, 0.84), (6.02, 4.28, 0.6), (6.15, 4.36, 0.05), (6.25, 4.388, 0.30)], radius=0.003)
    dr.cable(fx, [(2.86, 2.55, 0.02), (2.66, 2.9, 0.01), (2.60, 3.3, 0.01), (2.552, 3.6, 0.30)], radius=0.003)
    dr.cable(fx, [(7.05, 0.80, 0.32), (7.16, 0.50, 0.12), (7.05, 0.20, 0.02), (6.80, 0.012, 0.30)], radius=0.003)
    dr.cable(fx, [(7.10, 0.86, 0.58), (7.24, 0.9, 0.40), (7.27, 1.2, 0.04), (7.20, 1.45, 0.02)], radius=0.0025)
    dr.socket(fx, ROOM_WEST, 3.6, 0.32)
    fx.build("electrics_living", "fixtures")

    d = Decals("decals_living", seed=22)
    d.wall("floor_grime", ROOM_WEST, 3.2, 0.34, 2.0, 0.36)
    d.wall("floor_grime", DIVIDER_S, 5.6, 0.33, 2.0, 0.34)
    d.wall("grime_streaks", SOUTH, 3.2, 1.9, 0.7, 1.5)
    d.wall("grime_streaks", SOUTH, 4.9, 0.44, 1.9, 0.62)
    d.wall("grime_streaks", DIVIDER_S, 6.7, 1.95, 0.8, 1.4)
    d.wall("crack", CHIMNEY, 2.75, 2.05, 0.9, 0.9)
    d.wall("water_stain", EAST, 3.8, 2.25, 1.0, 0.8)
    d.wall("smudge", ROOM_WEST, 2.22, 1.2, 0.36, 0.42)
    d.wall("plaster_damage", DIVIDER_S, 4.55, 2.2, 0.5, 0.5)
    d.flat("water_stain", 6.2, 3.6, plan.CEILING, 1.5, 1.3, up=False, angle_deg=70)
    d.flat("nicotine", 4.7, 2.4, plan.CEILING, 2.6, 2.2, up=False, angle_deg=20)       # over the sofa
    d.flat("water_stain", 3.4, 0.9, plan.CEILING, 1.0, 0.9, up=False, angle_deg=200)
    d.build()


def landing():
    put("painted_wooden_chair_01", "landing_chair", 0.42, 0.48, F1, facing=40)
    put("potted_plant_04", "plant_landing", 1.78, -0.02, F1 + 0.90, facing=0, scale=1.2)
    put("hanging_picture_frame_02", "picture_landing", plan.PART_X0, 1.55, F1 + 1.62, facing=180)
    put("hanging_picture_frame_03", "picture_landing_2", plan.PART_X0, 7.70, F1 + 1.65, facing=180, tilt=(0, -5.0))
    dr.pendant("landing", 1.78, 1.6, plan.ROOF_Z, drop=0.42, kind="off", style="bare")
    dr.rug("runner_landing", 1.36, 3.25, 2.22, 7.55, F1, key="carpet_runner", seed=2, lift=0.03)
    dr.rug("rug_landing", 0.62, 1.20, 1.72, 2.72, F1, key="carpet_runner", seed=4)
    # the side window over the radiator: a short curtain, to the sill
    dr.curtain_pole("pole_landing_side", WEST, 0.55, 1.55, F1 + 2.37, off=0.06)
    dr.curtain("curtain_landing_side", WEST, 0.60, 1.14, F1 + 2.36, F1 + 0.965, seed=9, off=0.06, key="fabric_pillow")
    # a low bookcase on the front landing, with a lamp that no longer works
    dr.bookcase("bookcase_landing", HALL_EAST, 0.30, 1.30, F1, height=1.02, depth=0.26, shelves=3, seed=5, key="wood_mid")
    dr.table_lamp("landing", (2.25, 0.52, F1 + 1.05), kind="off")
    dr.radiator("radiator_landing", WEST, 0.6, 1.5, F1)
    put("cardboard_box_01", "box_landing", 0.5, 7.5, F1, facing=70, scale=0.9)

    small, soft = MeshBuilder(), MeshBuilder()
    cl.heap(soft, 0.44, 0.50, F1 + 0.46, 0.20, 0.18, 0.10, "fabric_curtain", seed=31, spread=0.15)   # clothes on the chair
    cl.heap(soft, 0.95, 0.62, F1, 0.26, 0.20, 0.09, "fabric_plaid", seed=32, yaw=30)
    cl.shoe(small, 1.30, 0.34, F1, yaw=100, key="wood_dark")
    cl.shoe(small, 1.46, 0.42, F1, yaw=80, key="wood_dark", tipped=True)
    cl.paper_stack(small, 1.98, 1.72, F1 + 0.016, count=9, yaw=-12, seed=5)
    cl.book(small, 2.26, 0.95, F1 + 1.05, "phonebook", yaw=-80, size=(0.15, 0.21, 0.035))
    cl.standing_photo(small, 2.30, 1.15, F1 + 1.05, "photo_d", yaw=-100)
    cl.framed(small, HALL_EAST, 4.05, F1 + 1.62, 0.26, "photo_b", tilt=1.5)
    cl.framed(small, HALL_EAST, 4.45, F1 + 1.56, 0.18, "photo_c", tilt=-4.0, key="wood_mid")
    cl.framed(small, HALL_EAST, 6.08, F1 + 1.60, 0.20, "photo_d", tilt=0.0, key="metal_brass")
    cl.open_box(small, 1.72, 7.50, F1, size=(0.44, 0.36, 0.28), yaw=-20, flaps=(100.0, 165.0, 130.0, 95.0), seed=6)
    cl.heap(soft, 1.72, 7.50, F1 + 0.10, 0.18, 0.14, 0.17, "fabric_curtain", seed=33, yaw=-20, spread=0.0)
    shapes.sheet(small, (1.9, 2.4, F1), 0.21, "magazine_b", yaw=50, lift=0.014)
    shapes.soften(small.build("clutter_landing", "clutter"))
    shapes.soften(soft.build("clutter_landing_cloth", "clutter"), 80.0)

    fx = MeshBuilder()
    dr.switch(fx, HALL_EAST, 2.85, F1 + 1.22, double=True)
    dr.socket(fx, HALL_EAST, 2.3, F1 + 0.32)
    fx.build("electrics_landing", "fixtures")

    d = Decals("decals_landing", seed=23)
    d.wall("floor_grime", HALL_EAST, 1.5, F1 + 0.34, 2.2, 0.36)
    d.wall("grime_streaks", WEST, 4.75, F1 - 0.55, 1.3, 1.3)        # under the stair window
    d.wall("crack", HALL_EAST, 7.72, F1 + 2.2, 0.5, 0.5)
    d.wall("plaster_damage", WEST, 7.35, F1 + 1.5, 0.55, 0.55)
    d.wall("smudge", HALL_EAST, 2.85, F1 + 1.2, 0.36, 0.42)
    d.flat("water_stain", 0.75, 5.0, plan.ROOF_Z, 1.4, 1.5, up=False, angle_deg=40)
    d.flat("water_stain", 1.6, 1.3, plan.ROOF_Z, 1.1, 1.0, up=False, angle_deg=150)
    d.flat("mould", 0.55, 0.55, plan.ROOF_Z, 1.0, 1.0, up=False, angle_deg=0)
    d.build()


def bedroom():
    bed("bed", 4.25, 2.35, 5.85, 4.40, F1)
    put("ClassicNightstand_01", "nightstand_left", 3.92, 4.16, F1, facing=-90)
    put("painted_wooden_nightstand", "nightstand_right", 6.18, 4.12, F1, facing=-90)
    dr.table_lamp("bedside", (6.18, 4.14, F1 + 0.617), kind="warm", watts=25)
    wardrobe("wardrobe", ROOM_WEST, 0.28, 2.02, F1)
    chest("chest_of_drawers", EAST, 0.24, 1.36, F1)
    put("ceramic_vase_01", "vase_bedroom", 7.05, 0.5, F1 + 0.92, facing=0, scale=0.75)
    put("standing_picture_frame_02", "photo_bedroom", 7.06, 1.05, F1 + 0.92, facing=170)
    put("painted_wooden_chair_01", "bedroom_chair", 6.55, 1.85, F1, facing=150)
    dr.rug("rug_bedroom", 3.30, 2.55, 4.20, 4.05, F1, seed=6)
    dr.pendant("bedroom", 4.9, 2.0, plan.ROOF_Z, drop=0.55, kind="off", style="pleated", tilt=7.0)
    dr.radiator("radiator_bedroom", SOUTH, 4.22, 5.62, F1)
    put("hanging_picture_frame_03", "picture_bedroom", 5.05, plan.DIVIDER_Y0, F1 + 1.78, facing=-90)

    dr.curtain_pole("pole_bedroom", SOUTH, 3.50, 6.34, F1 + 2.40)
    # sill length: full-length curtains hung through the radiator under the window
    dr.curtain("curtain_bedroom_l", SOUTH, 3.52, 4.95, F1 + 2.39, F1 + 0.79, seed=5)
    dr.curtain("curtain_bedroom_r", SOUTH, 5.72, 6.32, F1 + 2.39, F1 + 0.79, seed=6)
    # the side window: a roller blind pulled down to the air conditioner in it
    dr.roller_blind("blind_bedroom_side", EAST, 0.455, 1.145, F1 + 2.243, F1 + 1.46, off=-0.055, seed=5)
    # the north-east corner: a linen hamper and two boxes that were never unpacked
    put("cardboard_box_01", "box_bedroom_1", 6.90, 2.86, F1, facing=8)
    put("cardboard_box_01", "box_bedroom_2", 6.93, 2.84, F1 + 0.34, facing=-20, scale=0.8)
    # the west wall, between the wardrobe and the door: a dressing mirror leant against it
    glass = MeshBuilder()
    lean = 0.085
    for (a0, a1, z0, z1, key, out) in ((2.20, 2.72, 0.03, 1.60, "wood_dark", 0.0), (2.245, 2.675, 0.075, 1.555, "mirror", 0.004)):
        pts = [ROOM_WEST.P(a0, 0.03 + lean * (1 - z0 / 1.6) + out, F1 + z0), ROOM_WEST.P(a1, 0.03 + lean * (1 - z0 / 1.6) + out, F1 + z0),
               ROOM_WEST.P(a1, 0.03 + lean * (1 - z1 / 1.6) + out, F1 + z1), ROOM_WEST.P(a0, 0.03 + lean * (1 - z1 / 1.6) + out, F1 + z1)]
        if (pts[1] - pts[0]).cross(pts[2] - pts[0]).dot(ROOM_WEST.normal) < 0:
            pts = pts[::-1]
        glass.face(pts, key)
    for a in (2.20, 2.70):
        ROOM_WEST.box(glass, a, a + 0.02, 0.0, 0.03 + lean, F1, F1 + 0.03, "wood_dark")
    glass.build("bedroom_mirror", "furniture")

    small, soft = MeshBuilder(), MeshBuilder()
    dr.mug(small, 3.95, 4.14, F1 + 0.70)
    shapes.sheet(small, (6.05, 3.2, F1), 0.30, "newspaper", yaw=40, lift=0.003)
    # bedside: a glass, pills, an ashtray, a paperback, a clock radio
    cl.glass(small, 3.82, 4.20, F1 + 0.70)
    cl.tin(small, 4.04, 4.24, F1 + 0.70, "pills", radius=0.022, height=0.065, turn=30)
    cl.tin(small, 4.08, 4.08, F1 + 0.722, "pills", radius=0.022, height=0.065, turn=200)
    cl.book(small, 3.80, 4.04, F1 + 0.70, "paperback", yaw=-15)
    cl.clock_radio(small, 6.28, 4.24, F1 + 0.617, yaw=12)
    cl.ashtray(small, 6.06, 4.02, F1 + 0.617, butts=4, seed=9)
    # clothes: over the chair, on the floor, and a suitcase open and half packed
    cl.heap(soft, 6.56, 1.86, F1 + 0.46, 0.20, 0.18, 0.14, "fabric_plaid", seed=41, spread=0.15)
    shapes.lathe(small, 6.98, 3.62, [(0.17, F1), (0.21, F1 + 0.55), (0.20, F1 + 0.55), (0.16, F1 + 0.03)], "wicker", 16,
                 cap_last=True)
    cl.heap(soft, 6.98, 3.62, F1 + 0.46, 0.19, 0.19, 0.17, "fabric_bed", seed=45, spread=0.0)
    cl.paper_stack(small, 2.74, 2.48, F1 + 0.016, count=6, yaw=20, seed=8, region="magazine_b", width=0.21)
    cl.shoe(small, 2.70, 2.95, F1 + 0.016, yaw=10, key="vinyl")
    cl.shoe(small, 2.82, 3.05, F1 + 0.016, yaw=-25, key="vinyl", tipped=True)
    cl.heap(soft, 5.95, 1.55, F1, 0.30, 0.22, 0.07, "towel", seed=42, yaw=40)
    cl.heap(soft, 3.50, 2.45, F1, 0.22, 0.18, 0.08, "fabric_curtain", seed=43, yaw=-20)
    cl.suitcase(small, soft, 5.36, 2.98, F1 + 0.585, yaw=78, seed=44)       # on the foot of the bed
    cl.shoe(small, 4.02, 3.20, F1, yaw=95, key="wood_dark")
    cl.shoe(small, 3.90, 3.02, F1, yaw=70, key="wood_dark")
    cl.shoe(small, 6.20, 2.70, F1, yaw=-150, key="rubber", boot=True, tipped=True)
    # the top of the chest of drawers: photographs, a tin of coins, a hairbrush's worth of clutter
    cl.standing_photo(small, 7.04, 0.78, F1 + 0.92, "photo_a", yaw=-100)
    cl.standing_photo(small, 7.08, 1.24, F1 + 0.92, "polaroid_b", yaw=-80, width=0.09, key="wood_dark")
    shapes.sheet(small, (6.90, 0.98, F1 + 0.92), 0.10, "polaroid", yaw=30, lift=0.002)
    shapes.sheet(small, (6.86, 0.62, F1 + 0.92), 0.13, "postcard", yaw=-60, lift=0.002)
    cl.framed(small, DIVIDER_S, 5.95, F1 + 1.66, 0.24, "photo_b", tilt=3.0)
    rng = random.Random(9)
    for k in range(4):                                      # books stacked by the bed
        t = rng.uniform(0.022, 0.04)
        small.box((3.72, 3.52, F1 + 0.001 + k * 0.034), (3.92, 3.80, F1 + 0.001 + k * 0.034 + t),
                  rng.choice(dr.BOOK_COLORS), skip="-z")
    shapes.soften(small.build("clutter_bedroom", "clutter"))
    shapes.soften(soft.build("clutter_bedroom_cloth", "clutter"), 80.0)

    fx = MeshBuilder()
    dr.switch(fx, ROOM_WEST, 3.05, F1 + 1.22)
    dr.socket(fx, DIVIDER_S, 6.45, F1 + 0.32)
    dr.socket(fx, DIVIDER_S, 3.7, F1 + 0.32)
    dr.cable(fx, [(6.19, 4.15, F1 + 0.63), (6.33, 4.25, F1 + 0.5), (6.42, 4.36, F1 + 0.1), (6.45, 4.388, F1 + 0.30)],
             radius=0.003)
    dr.cable(fx, [(6.34, 4.28, F1 + 0.63), (6.40, 4.33, F1 + 0.45), (6.46, 4.37, F1 + 0.12), (6.49, 4.388, F1 + 0.30)],
             radius=0.0025)
    fx.build("electrics_bedroom", "fixtures")

    d = Decals("decals_bedroom", seed=24)
    d.wall("floor_grime", EAST, 2.4, F1 + 0.34, 1.8, 0.34)
    d.wall("grime_streaks", SOUTH, 6.6, F1 + 1.95, 0.7, 1.4)
    d.wall("grime_streaks", SOUTH, 4.9, F1 + 0.5, 1.9, 0.62)
    d.wall("crack", DIVIDER_S, 3.4, F1 + 2.0, 1.0, 1.0)
    d.wall("water_stain", EAST, 3.7, F1 + 2.2, 1.0, 0.8)
    d.wall("smudge", ROOM_WEST, 3.05, F1 + 1.2, 0.36, 0.42)
    d.flat("water_stain", 6.4, 3.4, plan.ROOF_Z, 1.7, 1.5, up=False, angle_deg=15)
    d.flat("nicotine", 4.9, 3.5, plan.ROOF_Z, 2.2, 1.8, up=False, angle_deg=100)        # over the bed
    d.flat("mould", 2.99, 0.45, plan.ROOF_Z, 0.9, 0.9, up=False, angle_deg=0)
    d.build()


def details():
    """One more layer over every room: knocks along the skirting, dust on
    the tops of things, wallpaper lifting at its seams, a socket hanging off
    the wall, extension leads, damp below the windows."""
    d = Decals("decals_detail", seed=40)
    skirt = 0.0205                                         # clear of the skirting board's face
    for face, a, floor in (
            (HALL_EAST, 0.62, GF), (HALL_EAST, 3.05, GF), (HALL_EAST, 4.9, GF), (WEST, 0.95, GF), (WEST, 7.45, GF),
            (NORTH, 0.62, GF), (ROOM_WEST, 2.9, GF), (DIVIDER_S, 6.7, GF), (SOUTH, 3.05, GF), (SOUTH, 6.6, GF),
            (EAST, 0.75, GF), (ROOM_WEST, 5.0, GF), (ROOM_WEST, 7.62, GF), (DIVIDER_N, 4.9, GF),
            (HALL_EAST, 1.0, F1), (HALL_EAST, 3.9, F1), (HALL_EAST, 6.08, F1), (SOUTH, 0.55, F1), (WEST, 7.45, F1),
            (DIVIDER_S, 3.3, F1), (DIVIDER_S, 6.9, F1), (SOUTH, 3.05, F1), (EAST, 3.65, F1), (ROOM_WEST, 2.62, F1)):
        d.wall("scuffs", face, a, floor + 0.085, 1.15, 0.15, offset=skirt)
    for x, y, z, w, h, turn in (
            (5.42, 4.12, 0.834, 1.25, 0.50, 0), (6.85, 2.30, 1.1475, 0.22, 1.60, 0), (7.03, 0.80, 0.963, 0.42, 0.46, 20),
            (7.145, 3.75, 2.012, 0.30, 1.20, 0), (2.18, 2.95, 0.7625, 0.36, 0.36, 40),
            (6.97, 0.80, F1 + 0.9215, 0.62, 1.10, 0), (2.85, 1.15, F1 + 2.0725, 0.60, 1.74, 0),
            (3.92, 4.16, F1 + 0.7015, 0.50, 0.38, 0), (6.66, 7.84, 2.1215, 1.25, 0.30, 0), (6.97, 4.96, 1.7015, 0.62, 0.70, 0),
            (3.57, 7.84, 2.1215, 0.52, 0.30, 0)):
        d.flat("dust", x, y, z, w, h, angle_deg=turn)
    # damp below the windows that had none yet, and on the landing sill wall
    d.wall("grime_streaks", SOUTH, 1.775, F1 + 0.46, 1.0, 0.8)
    d.wall("water_stain", SOUTH, 1.775, F1 + 0.62, 0.9, 0.5)
    d.wall("water_stain", SOUTH, 4.9, 0.50, 1.6, 0.42)
    d.wall("water_stain", SOUTH, 4.9, F1 + 0.58, 1.6, 0.42)
    d.wall("grime_streaks", WEST, 4.75, 2.55, 0.9, 0.7)
    d.build()

    paper = MeshBuilder()
    for face, a, z, length, width, key, seed in (
            (HALL_EAST, 3.55, 2.02, 0.60, 0.52, "wall_hall", 1), (WEST, 1.55, 2.10, 0.52, 0.52, "wall_hall", 2),
            (HALL_EAST, 7.45, 2.20, 0.44, 0.40, "wall_hall", 3),
            (DIVIDER_S, 6.62, 1.95, 0.68, 0.52, "wall_living", 4), (SOUTH, 3.02, 2.00, 0.62, 0.48, "wall_living", 5),
            (HALL_EAST, 2.2, F1 + 2.02, 0.60, 0.52, "wall_landing", 6), (WEST, 2.2, F1 + 2.10, 0.52, 0.52, "wall_landing", 7),
            (NORTH, 0.6, F1 + 2.05, 0.56, 0.46, "wall_landing", 8)):
        cl.peel(paper, face, a, z, length, width, key, seed=seed)
    obj = paper.build("wallpaper_peels", "soft", smooth=True)
    obj.visible_shadow = True

    fx = MeshBuilder()
    dr.socket_broken(fx, EAST, 0.62, 0.32)                                # living room, by the television
    dr.socket_broken(fx, HALL_EAST, 6.45, F1 + 0.32)                       # landing
    dr.socket(fx, WEST, 6.9, F1 + 0.32)
    dr.socket(fx, SOUTH, 6.9, F1 + 0.32)
    cl.power_strip(fx, 6.62, 0.30, 0.0, yaw=12)
    dr.cable(fx, [(6.76, 0.30, 0.02), (6.95, 0.22, 0.02), (7.10, 0.40, 0.2), (7.02, 0.66, 0.32)], radius=0.003)
    dr.cable(fx, [(6.48, 0.29, 0.02), (6.2, 0.2, 0.012), (5.9, 0.10, 0.012), (5.72, 0.012, 0.30)], radius=0.003)
    # an extension lead across the bedroom floor to the clock radio
    dr.cable(fx, [(6.9, 0.012, F1 + 0.30), (6.6, 0.3, F1 + 0.012), (6.5, 1.6, F1 + 0.012), (6.75, 3.2, F1 + 0.012),
                  (6.5, 3.9, F1 + 0.012)], radius=0.0035, key="plastic_white")
    cl.power_strip(fx, 6.44, 3.98, F1, yaw=70)
    fx.build("electrics_detail", "fixtures")


def kitchen_wall():
    """The kitchen's long bare wall, by the table: a chest used as a
    sideboard with the bread bin and the radio on it, a shelf of tins over
    it, an apron on a hook by the way through to the living room."""
    chest("kitchen_sideboard", DIVIDER_N, 4.45, 5.45, GF, depth=0.42, height=0.86, open_drawer=2)
    mb = MeshBuilder()
    DIVIDER_N.box(mb, 4.28, 5.30, 0.0, 0.17, GF + 1.90, GF + 1.92, "wood_mid")
    for a in (4.38, 5.20):
        mb.prism([(0.0, GF + 1.90), (0.15, GF + 1.90), (0.0, GF + 1.76)], DIVIDER_N.P(a, 0, 0), DIVIDER_N.normal,
                 (0, 0, 1), DIVIDER_N.along, 0.018, "wood_mid")
    DIVIDER_N.box(mb, 4.22, 4.30, 0.0, 0.016, GF + 1.60, GF + 1.66, "wood_mid")
    mb.cylinder(DIVIDER_N.P(4.26, 0.016, GF + 1.63), DIVIDER_N.normal * 0.04, 0.006, "metal_brass", segments=6)
    mb.build("kitchen_shelf", "furniture", recalc=True)
    dr.curtain("apron_kitchen", DIVIDER_N, 4.14, 4.40, GF + 1.62, GF + 0.86, seed=15, off=0.045, key="gingham")
    small = MeshBuilder()
    y, top = plan.DIVIDER_Y1 + 0.20, GF + 0.86
    shapes.loft(small, [shapes.ring(4.72, y, top + zz, 0.17 * sc, 0.115 * sc, 18, 5.0) for zz, sc in
                        ((0.0, 0.97), (0.02, 1.0), (0.13, 1.0), (0.19, 0.86), (0.205, 0.5))], "enamel_almond",
                cap_first=True, cap_last=True)                                              # the bread bin
    cl.clock_radio(small, 5.20, y - 0.02, top, yaw=172)
    cl.plates(small, 5.02, y + 0.02, top, 4, radius=0.10)
    dr.mug(small, 4.98, y + 0.17, top)
    shapes.sheet(small, (5.22, y + 0.15, top), 0.20, "letter", yaw=160, lift=0.002)
    sz = GF + 1.92
    for k, (a, region) in enumerate(((4.36, "soup"), (4.46, "beans"), (4.58, "soup"), (4.98, "beans"))):
        cl.tin(small, a, plan.DIVIDER_Y1 + 0.085, sz, region, turn=40 * k)
    cl.cereal(small, 4.78, plan.DIVIDER_Y1 + 0.075, sz, "cereal_a", yaw=178)
    cl.bottle(small, 5.14, plan.DIVIDER_Y1 + 0.08, sz, height=0.25)
    cl.bottle(small, 5.22, plan.DIVIDER_Y1 + 0.09, sz, height=0.22, key="glass")
    shapes.soften(small.build("clutter_kitchen_wall", "clutter"))
    d = Decals("decals_kitchen_extra", seed=33)
    d.flat("nicotine", 6.75, 6.3, plan.CEILING, 1.7, 2.0, up=False, angle_deg=10)             # over the cooker
    d.flat("grease", 6.6, 6.3, plan.CEILING, 1.1, 1.2, up=False, angle_deg=50)
    d.flat("dust", 4.95, y, top + 0.0015, 1.0, 0.42)
    d.build()


def contact_dirt():
    """Dirt where every floor meets its walls: a dark line against the
    skirting that reaches further into the room in some places than others,
    and a fan of it in every inside corner."""
    d = Decals("decals_contact", seed=52)
    rng = d.rng
    base = joinery.SKIRT_T + 0.001
    for run in shell.wall_runs("floor", joinery.SKIRT_T):
        p0, p1, n = run["p0"], run["p1"], run["normal"]
        length = (p1 - p0).length
        if length < 0.25:
            continue
        along = (p1 - p0).normalized()
        at = 0.0
        while at < length - 0.05:
            piece = min(rng.uniform(1.0, 2.2), length - at)
            reach = rng.uniform(0.10, 0.24)
            lift = Vector((0, 0, 0.0030 + rng.random() * 0.0006))
            a, b = p0 + along * at + n * base + lift, p0 + along * (at + piece) + n * base + lift
            u0 = rng.random()
            u1 = u0 + piece / 1.9
            pts, uvs = [a, b, b + n * reach, a + n * reach], [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).z < 0:
                pts, uvs = pts[::-1], uvs[::-1]
            d.quad("contact_dirt", pts, uvs)
            at += piece
        for end, corner, away in (("end0", p0, along), ("end1", p1, -along)):
            if run[end] != "inside" or run["axis"] != "x":       # each corner once
                continue
            size = rng.uniform(0.24, 0.42)
            c = corner + n * base + away * base + Vector((0, 0, 0.0038))
            pts, uvs = [c, c + away * size, c + away * size + n * size, c + n * size], [(0, 0), (1, 0), (1, 1), (0, 1)]
            if (pts[1] - pts[0]).cross(pts[2] - pts[0]).z < 0:
                pts, uvs = pts[::-1], uvs[::-1]
            d.quad("corner_dirt", pts, uvs)
    return d.build()


def build():
    models.reset()
    hall()
    living()
    kitchen.build()
    kitchen_wall()
    landing()
    bedroom()
    bathroom.build()
    utility.build()
    details()
    contact_dirt()
    yard.dress()
