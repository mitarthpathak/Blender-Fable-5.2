"""Street detail and the small stories on each lot (detail pass, part 2).

Most care goes where the player looks first: the view out of the front door
and the junction. Everything here is small, so it is merged into 24 m
sectors ("detail_i_j" for solid props, "decals_b_i_j" for flat ones) that
Godot culls and fades with distance, and it reuses the kit's materials, so
the detail costs a handful of draw calls and nothing once it is out of range.

All text on signs and posters is our own (textures from detail_maps.py).
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, instance, jitter_color, mul
from . import street_kit as sk
from .street_kit import G, RD, SW, Sectors

# Sun-faded plastics and paint: nothing here is as bright as the day it was bought.
RED = (0.40, 0.15, 0.12)
GREEN = (0.16, 0.26, 0.17)
BLUE = (0.19, 0.25, 0.36)
YELLOW = (0.50, 0.42, 0.17)


# --- small shapes ----------------------------------------------------------------

def blob(mb, centre, rx, ry, rz, mat, rng, colour=(1, 1, 1), rings=4, segs=8, flat_bottom=True):
    """A lumpy rounded shape: a trash bag, a pumpkin, a ball."""
    c = Vector(centre)
    pts = []
    for i in range(rings + 1):
        t = i / rings
        phi = (t * 0.5 if flat_bottom else t - 0.5) * math.pi if flat_bottom else (t - 0.5) * math.pi
        row = []
        for j in range(segs):
            a = 2 * math.pi * j / segs
            k = 1.0 + rng.uniform(-0.12, 0.12)
            if flat_bottom:
                r, z = math.cos(phi) * k, math.sin(phi)
            else:
                r, z = math.cos(phi) * k, math.sin(phi) + 1.0
            row.append(c + Vector((math.cos(a) * r * rx, math.sin(a) * r * ry, z * rz * (1.0 if flat_bottom else 0.5))))
        pts.append(row)
    for i in range(rings):
        for j in range(segs):
            k = (j + 1) % segs
            mb.face([pts[i][j], pts[i][k], pts[i + 1][k], pts[i + 1][j]], mat, color=colour)


def loop(mb, centre, radius, axis_matrix, tube_r, mat, segs=12, colour=None):
    """A closed ring of tube (a bicycle wheel, a tyre, a hose coil)."""
    pts = [axis_matrix @ Vector((math.cos(2 * math.pi * i / segs) * radius, math.sin(2 * math.pi * i / segs) * radius, 0))
           + Vector(centre) for i in range(segs + 1)]
    mb.tube(pts, tube_r, mat, segments=5, color=colour)


def pole_card(mb, pole_xy, z, height, width, facing, mat, radius=0.15):
    """A flyer wrapped round a pole: three strips following its curve."""
    px, py = pole_xy
    half = width / 2 / radius                               # half the angle the paper covers
    for k in range(3):
        a0 = facing - half + 2 * half * k / 3
        a1 = facing - half + 2 * half * (k + 1) / 3
        p0 = Vector((px + math.cos(a0) * radius, py + math.sin(a0) * radius, z))
        p1 = Vector((px + math.cos(a1) * radius, py + math.sin(a1) * radius, z))
        up = Vector((0, 0, height))
        mb.face([p0, p1, p1 + up, p0 + up], mat, uvs=[(k / 3, 0), ((k + 1) / 3, 0), ((k + 1) / 3, 1), (k / 3, 1)])


def sign_post(mb, x, y, z, rot, mat, w=0.32, h=0.48, height=2.3, lean=0.0):
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Rotation(lean, 4, "X")
    part = MeshBuilder()
    part.cylinder((0, 0, -0.1), (0, 0, height + 0.1), 0.025, "metal_rust", segments=6, color=(0.7, 0.7, 0.68))
    part.card((0, -0.03, height - h), w, h, 0.0, mat)
    part.card((0, 0.03, height - h), w, h, math.pi, "metal_painted", color=(0.6, 0.6, 0.58))
    mb.extend(part, m)


# --- the street --------------------------------------------------------------------

def gutters_and_drains(det: Sectors, dec: Sectors, rng):
    """Wet leaves banked against the curbs, densest by the house and the junction, and storm drains."""
    focus = [(plan.HOUSE_DOOR_X, -10.2, 16.0), (3.5, -18.1, 13.0), (3.5, -26.0, 9.0)]
    for (ax, ay), (bx, by), side in sk.curb_lines():
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        inward = {"n": (0, 1), "s": (0, -1), "w": (-1, 0), "e": (1, 0)}[side]
        t = 0.0
        while t < length:
            x, y = ax + ux * t, ay + uy * t
            near = min(math.hypot(x - fx, y - fy) / fr for fx, fy, fr in focus)
            chance = 0.85 if near < 1.0 else 0.25
            seg = rng.uniform(1.2, 3.0)
            if abs(x) < 36 and y > -57 and rng.random() < chance:
                cx, cy = x + ux * seg / 2 - inward[0] * rng.uniform(0.22, 0.34), y + uy * seg / 2 - inward[1] * rng.uniform(0.22, 0.34)
                wet = rng.uniform(0.45, 0.7)
                dec.at(cx, cy).card((cx, cy, RD + 0.010), rng.uniform(0.5, 0.75), seg, math.atan2(uy, ux) - math.pi / 2,
                                    "decal_leaves", flat=True, color=(wet, wet * 0.95, wet * 0.9))
            t += seg
    drains = [(-2.6, -10.2, "n"), (9.4, -10.2, "n"), (-1.2, -18.1, "s"), (8.4, -18.1, "s"), (0.0, -30.5, "w"),
              (7.0, -43.0, "e"), (22.0, -10.2, "n")]
    for x, y, side in drains:
        inward = {"n": (0, 1), "s": (0, -1), "w": (-1, 0), "e": (1, 0)}[side]
        rot = {"n": 0.0, "s": math.pi, "w": math.pi / 2, "e": -math.pi / 2}[side]
        part = MeshBuilder()
        # iron frame and bars in the road at the foot of the curb, and the slot under the curb stone
        part.box((-0.42, -0.36, -0.012), (0.42, -0.02, 0.006), "metal_rust", color=(0.45, 0.42, 0.4))
        part.box((-0.37, -0.32, 0.006), (0.37, -0.06, 0.008), "interior_dark")
        for k in range(7):
            bx_ = -0.33 + k * 0.11
            part.box((bx_ - 0.02, -0.33, 0.006), (bx_ + 0.02, -0.05, 0.016), "metal_rust", color=(0.5, 0.47, 0.44))
        part.face([Vector((-0.45, -0.004, 0.0)), Vector((0.45, -0.004, 0.0)), Vector((0.45, -0.004, 0.10)),
                   Vector((-0.45, -0.004, 0.10))], "interior_dark")
        det.at(x, y).extend(part, Matrix.Translation((x, y, RD)) @ Matrix.Rotation(rot, 4, "Z"))
        # leaves and silt washed up to the grate
        dec.at(x, y).card((x - inward[0] * 0.4, y - inward[1] * 0.4, RD + 0.012), 1.5, 1.1, rot, "decal_leaves", flat=True,
                          color=(0.5, 0.48, 0.45))


def signs_and_bus_stop(det: Sectors, rng):
    sign_post(det.at(14.2, -9.0), 14.2, -9.0, SW, math.radians(8), "sign_parking", lean=0.05)
    sign_post(det.at(-13.5, -19.3), -13.5, -19.3, SW, math.radians(185), "sign_parking", lean=-0.09)
    sign_post(det.at(8.3, -27.5), 8.3, -27.5, SW, math.radians(95), "sign_parking", lean=0.03)
    # bus stop on the north sidewalk, east of the house path
    sign_post(det.at(11.6, -9.9), 11.6, -9.9, SW, math.radians(0), "sign_bus", w=0.36, h=0.54, height=2.6, lean=0.02)
    bench = MeshBuilder()
    wood = (0.62, 0.58, 0.52)
    for k in range(4):                                         # seat slats
        bench.box((-0.9, -0.25 + k * 0.12, 0.42), (0.9, -0.16 + k * 0.12, 0.45), "wood_weathered",
                  color=jitter_color(rng, wood, 0.1))
    for k in range(3):                                         # back slats, one missing
        if k == 1:
            continue
        bench.obox((0.0, 0.25, 0.60 + k * 0.13), (1.8, 0.03, 0.10), 0.0, "wood_weathered", color=jitter_color(rng, wood, 0.1),
                   tilt=(-0.2, 0.0))
    for sx in (-0.8, 0.8):
        bench.box((sx - 0.03, -0.27, 0.0), (sx + 0.03, -0.21, 0.42), "metal_rust")
        bench.box((sx - 0.03, 0.21, 0.0), (sx + 0.03, 0.27, 0.92), "metal_rust")
        bench.box((sx - 0.03, -0.27, 0.38), (sx + 0.03, 0.27, 0.42), "metal_rust")
    o = bench.build("bench_bus_stop", "props")
    o.location = (12.9, -9.05, SW)
    o.rotation_euler.z = math.radians(3)


def trash(det: Sectors, dec: Sectors, rng):
    """Bags piled round the cans nobody collected, a split bag, litter blown along the curb."""
    piles = [(6.95, -9.0, SW, 5), (-2.6, -19.2, SW, 3), (21.5, -9.1, SW, 2), (-1.0, -43.9, SW, 2)]
    for x, y, z, n in piles:
        for k in range(n):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(0.35, 0.75)
            bx_, by_ = x + math.cos(a) * r, y + math.sin(a) * r * 0.5 + 0.25
            blob(det.at(bx_, by_), (bx_, by_, z), rng.uniform(0.22, 0.3), rng.uniform(0.2, 0.28), rng.uniform(0.3, 0.42),
                 "bag_plastic", rng)
            det.at(bx_, by_).cylinder((bx_, by_, z + 0.3), (rng.uniform(-0.05, 0.05), 0, 0.12), 0.03, "bag_plastic", segments=5)
        dec.at(x, y).card((x + 0.3, y - 0.6, z + 0.008), 2.2, 2.2, rng.uniform(0, 3), "decal_litter", flat=True)
        det.at(x, y).obox((x - 0.5, y + 0.45, z + 0.03), (0.42, 0.42, 0.05), rng.uniform(0, 3), "plywood", color=(0.75, 0.62, 0.45))
    for x, y in ((1.0, -10.6), (4.2, -17.6), (-6.0, -10.5), (6.6, -21.5), (11.0, -17.7)):
        dec.at(x, y).card((x, y, RD + 0.011), 1.8, 1.4, rng.uniform(0, 3), "decal_litter", flat=True)


def _solid_prop(mb: MeshBuilder, name: str, matrix: Matrix, lo, hi):
    """A prop the player can bump into: its own object (so it casts a shadow)
    and a convex collision box round it ("-convcolonly": Godot draws none of it)."""
    obj = mb.build(name, "props")
    obj.matrix_world = matrix
    box = MeshBuilder()
    box.box(lo, hi, "concrete")
    col = box.build(name + "_col-convcolonly", "collision")
    col.matrix_world = matrix
    return obj


def cart_and_bike(det: Sectors, rng):
    # a shopping cart on its side at the south-east corner of the junction
    cart = MeshBuilder()
    w, d, h = 0.50, 0.85, 0.50
    for ya in (-w / 2, w / 2):
        cart.card((0, ya, 0.42), d, h, 0.0, "chainlink", uvs=((0, 0), (d, 0), (d, h), (0, h)))
        cart.card((0, ya, 0.42), d, h, math.pi, "chainlink", uvs=((0, 0), (d, 0), (d, h), (0, h)))
    for xa in (-d / 2, d / 2):
        cart.card((xa, 0, 0.42), w, h, math.pi / 2, "chainlink", uvs=((0, 0), (w, 0), (w, h), (0, h)))
        cart.card((xa, 0, 0.42), w, h, -math.pi / 2, "chainlink", uvs=((0, 0), (w, 0), (w, h), (0, h)))
    cart.card((0, 0, 0.42), d, w, 0.0, "chainlink", flat=True, uvs=((0, 0), (d, 0), (d, w), (0, w)))
    rim = [(-d / 2, -w / 2, 0.92), (d / 2, -w / 2, 0.92), (d / 2, w / 2, 0.92), (-d / 2, w / 2, 0.92), (-d / 2, -w / 2, 0.92)]
    cart.tube(rim, 0.012, "chrome_dull", segments=4)
    cart.tube([(-d / 2, -w / 2, 0.92), (-d / 2 - 0.16, -w / 2, 1.02), (-d / 2 - 0.16, w / 2, 1.02), (-d / 2, w / 2, 0.92)], 0.014,
              "plastic_dark", segments=4)
    for sx in (-0.34, 0.36):
        for sy in (-0.2, 0.2):
            cart.tube([(sx, sy, 0.42), (sx, sy, 0.10)], 0.012, "chrome_dull", segments=4)
            cart.cylinder((sx, sy - 0.02, 0.06), (0, 0.04, 0), 0.06, "plastic_dark", segments=8)
    cart.tube([(-0.34, -0.2, 0.14), (0.36, -0.2, 0.14), (0.36, 0.2, 0.14), (-0.34, 0.2, 0.14), (-0.34, -0.2, 0.14)], 0.012,
              "chrome_dull", segments=4)
    x, y = 9.6, -18.95
    _solid_prop(cart, "prop_cart", Matrix.Translation((x, y, SW + 0.27)) @ Matrix.Rotation(0.6, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X"),
                (-0.62, -0.27, 0.0), (0.46, 0.27, 1.04))

    # a bicycle left lying by the house's fence, its front wheel buckled
    bike = MeshBuilder()
    rust = (0.55, 0.3, 0.25)
    upright = Matrix.Rotation(math.pi / 2, 4, "X")
    for cx in (-0.52, 0.52):
        loop(bike, (cx, 0, 0.33), 0.32, upright, 0.016, "tyre", colour=(0.3, 0.3, 0.3))
        for k in range(6):
            a = k * math.pi / 3
            bike.tube([(cx, 0, 0.33), (cx + math.cos(a) * 0.31, 0, 0.33 + math.sin(a) * 0.31)], 0.004, "chrome_dull", segments=3)
    frame = [(-0.52, 0, 0.33), (-0.12, 0, 0.33), (0.30, 0, 0.78), (-0.22, 0, 0.74), (-0.12, 0, 0.33)]
    bike.tube(frame, 0.016, "metal_painted", segments=5, color=rust)
    bike.tube([(-0.52, 0, 0.33), (-0.22, 0, 0.74), (-0.26, 0, 0.90)], 0.014, "metal_painted", segments=5, color=rust)
    bike.tube([(0.52, 0, 0.33), (0.30, 0, 0.78), (0.26, 0, 0.98)], 0.014, "metal_painted", segments=5, color=rust)
    bike.tube([(0.26, -0.24, 0.98), (0.26, 0.24, 0.98)], 0.012, "chrome_dull", segments=4)
    bike.box((-0.36, -0.05, 0.90), (-0.14, 0.05, 0.94), "plastic_dark")
    bike.cylinder((-0.12, -0.05, 0.33), (0, 0.1, 0), 0.07, "chrome_dull", segments=8)
    x, y = -1.6, -8.05
    _solid_prop(bike, "prop_bike", Matrix.Translation((x, y, G + 0.06)) @ Matrix.Rotation(0.35, 4, "Z") @ Matrix.Rotation(1.42, 4, "X"),
                (-0.86, -0.26, 0.0), (0.86, 0.26, 1.0))


def posters(det: Sectors):
    poles = {p.key: p for p in plan.POLES}
    for key, mat, facing, z in (("P2", "poster_missing", -0.4, 1.25), ("P2", "poster_yardsale", 2.4, 1.45),
                                ("P5", "poster_meeting", 0.9, 1.3), ("P5", "poster_missing", 2.9, 1.2),
                                ("P3", "poster_missing", -2.6, 1.3), ("P1", "poster_yardsale", -0.3, 1.35),
                                ("P6", "poster_meeting", 0.6, 1.25), ("P7", "poster_missing", 0.9, 1.3)):
        p = poles[key]
        pole_card(det.at(p.x, p.y), (p.x, p.y), SW + z, 0.40, 0.30, facing, mat)
    # under the dead lamp on P4: its glass on the ground, and the lead hanging loose
    p = poles["P4"]
    hx, hy = p.x + p.arm[0] * 1.8, p.y + p.arm[1] * 1.8
    det.at(hx, hy).card((hx, hy, RD + 0.012), 1.3, 1.3, 0.4, "decal_shards", flat=True)
    det.at(hx, hy).tube([(hx, hy, SW + 6.55), (hx + 0.05, hy + 0.1, SW + 6.0), (hx - 0.08, hy + 0.05, SW + 5.5)], 0.012,
                        "wire", segments=4)


def road_marks(dec: Sectors, rng):
    """Tyre marks towards each wreck and round the junction, oil under every car."""
    for x, y, heading, length in ((2.9, -47.5, 97.0, 11.0), (7.6, -15.6, 205.0, 9.0), (-24.5, -12.6, 150.0, 8.0),
                                  (14.0, -15.0, 178.0, 7.0)):
        dec.at(x, y).card((x, y, RD + 0.006), 1.7, length, math.radians(heading) - math.pi / 2, "decal_tyre", flat=True)
    for key, x, y, heading, state in plan.CARS:
        zz = sk._surface_z(x, y)
        dec.at(x, y).card((x, y, zz + 0.009), 1.6, 1.3, rng.uniform(0, 3), "decal_oil", flat=True)
        if state == "crashed":
            dec.at(x, y).card((x + 0.4, y - 1.6, zz + 0.012), 1.6, 1.6, 0.0, "decal_shards", flat=True)


# --- the lots ---------------------------------------------------------------------------

def hose(mb, x, y, z, rng, colour=GREEN):
    for k in range(3):
        loop(mb, (x + rng.uniform(-0.02, 0.02), y + rng.uniform(-0.02, 0.02), z + 0.02 + 0.03 * k), 0.26 - 0.02 * k,
             Matrix.Identity(4), 0.014, "toy_plastic", segs=14, colour=colour)
    mb.tube([(x + 0.26, y, z + 0.03), (x + 0.6, y + 0.3, z + 0.02), (x + 1.2, y + 0.2, z + 0.02)], 0.014, "toy_plastic",
            segments=5, color=colour)


def pumpkin(mb, x, y, z, rng, r=0.16, rotten=False):
    col = (0.55, 0.5, 0.42) if rotten else (1.0, 1.0, 1.0)
    blob(mb, (x, y, z), r, r, r * (0.45 if rotten else 0.85), "pumpkin", rng, colour=col, rings=3, segs=10)
    if not rotten:
        mb.cylinder((x, y, z + r * 0.8), (0.01, 0, 0.06), 0.015, "bark", segments=5)


def lot_stories(det: Sectors, dec: Sectors, houses, rng):
    # L1, the player's own yard: a hose by the porch, the paper still on the path
    m = det.at(4.7, -1.0)
    hose(m, 4.7, -1.0, G, rng)
    m.cylinder((4.35, -0.34, G + 0.35), (0, -0.08, 0), 0.02, "chrome_dull", segments=6)
    det.at(1.9, -5.6).obox((1.95, -5.6, G + 0.05), (0.32, 0.13, 0.06), 0.5, "trim", color=(0.6, 0.58, 0.52))

    # L2, 12 Ashgrove: what was left of the yard sale on the poster
    x, y = -12.6, -5.2
    m = det.at(x, y)
    m.obox((x, y, G + 0.36), (1.6, 0.7, 0.03), 0.25, "plywood", color=(0.7, 0.62, 0.5), tilt=(0.0, 0.42))      # table, legs gone one side
    for lx, ly in ((0.55, 0.25), (0.6, -0.3)):
        m.cylinder((x + lx, y + ly, G), (0, 0, 0.62), 0.015, "metal_rust", segments=5)
    for k in range(4):
        m.obox((x - 0.9 + 0.5 * k, y - 0.9 + 0.1 * (k % 2), G + 0.16), (0.42, 0.36, 0.32), rng.uniform(0, 1.5), "plywood",
               color=jitter_color(rng, (0.72, 0.6, 0.45), 0.12))
    m.cylinder((x + 1.2, y - 0.6, G), (0, 0, 0.9), 0.02, "metal_rust", segments=5)                             # a floor lamp, fallen shade
    blob(m, (x + 1.5, y - 0.9, G), 0.18, 0.18, 0.2, "trim", rng, colour=(0.6, 0.57, 0.5), rings=2, segs=8)
    dec.at(x, y).card((x, y - 0.5, G + 0.014), 2.6, 2.6, 0.3, "decal_litter", flat=True)
    sign_post(m, x - 2.2, y - 2.3, G, math.radians(12), "poster_yardsale", w=0.5, h=0.62, height=0.95, lean=0.5)

    # L3, 16 Ashgrove (someone lives here): porch swing, pumpkins on the steps, a sheet ghost in the tree
    obj, hm, ramps, steps = houses["L3"]
    lot = next(l for l in plan.LOTS if l.key == "L3")
    h = lot.house
    sw_local = Vector((h.width - 1.9, -1.1, 0.0))
    world = hm @ sw_local
    m = det.at(world.x, world.y)
    swing = MeshBuilder()
    wood = (0.66, 0.62, 0.55)
    for k in range(4):
        swing.box((-0.65, -0.22 + k * 0.11, 0.44), (0.65, -0.14 + k * 0.11, 0.47), "wood_weathered", color=jitter_color(rng, wood, 0.08))
    for k in range(3):
        swing.obox((0, 0.25, 0.58 + 0.12 * k), (1.3, 0.025, 0.09), 0.0, "wood_weathered", color=jitter_color(rng, wood, 0.08),
                   tilt=(-0.18, 0.0))
    for sx in (-0.63, 0.63):
        swing.box((sx - 0.02, -0.22, 0.44), (sx + 0.02, 0.26, 0.62), "wood_weathered", color=wood)
        swing.tube([(sx, -0.2, 0.47), (sx, 0.0, 2.55)], 0.008, "chrome_dull", segments=3)
        swing.tube([(sx, 0.26, 0.9), (sx, 0.0, 2.55)], 0.008, "chrome_dull", segments=3)
    m.extend(swing, hm @ Matrix.Translation(sw_local) @ Matrix.Rotation(0.06, 4, "Z"))
    sx0, sx1, sy = steps
    for k, (lx, ly, r, rot) in enumerate(((sx0 - 0.25, -2.5, 0.17, False), (sx1 + 0.2, -2.45, 0.13, False),
                                          (sx1 + 0.45, -2.9, 0.15, True))):
        p = hm @ Vector((lx, ly, 0))
        pumpkin(det.at(p.x, p.y), p.x, p.y, G if ly < -2.4 else -0.02, rng, r, rot)
    tx, ty, th, _ = plan.TREES[2]
    gx, gy, gz = tx + 1.3, ty - 0.6, G + 2.1
    m = det.at(gx, gy)
    blob(m, (gx, gy, gz + 0.55), 0.14, 0.14, 0.16, "trim", rng, colour=(0.75, 0.74, 0.7), rings=3, segs=8)
    ring = [Vector((gx + math.cos(a) * 0.3, gy + math.sin(a) * 0.3, gz - 0.35 + 0.18 * math.sin(a * 3))) for a in
            [2 * math.pi * i / 8 for i in range(8)]]
    neck = [Vector((gx + math.cos(2 * math.pi * i / 8) * 0.12, gy + math.sin(2 * math.pi * i / 8) * 0.12, gz + 0.5)) for i in range(8)]
    for i in range(8):
        j = (i + 1) % 8
        m.face([ring[i], ring[j], neck[j], neck[i]], "trim", color=(0.7, 0.69, 0.66))
        m.face([ring[j], ring[i], neck[i], neck[j]], "trim", color=(0.55, 0.54, 0.52))
    m.tube([(gx, gy, gz + 0.7), (gx - 0.1, gy + 0.05, gz + 1.5)], 0.005, "wire", segments=3)
    hp = hm @ Vector((0.6, -2.9, 0))
    hose(det.at(hp.x, hp.y), hp.x, hp.y, G, rng)

    # L4, the corner house: a child's things left out in the long grass
    x, y = -9.4, -22.8
    m = det.at(x, y)
    blob(m, (x + 1.6, y + 0.4, G), 0.14, 0.14, 0.26, "toy_plastic", rng, colour=mul(RED, 1.2), rings=3, segs=10)      # ball
    m.box((x - 0.35, y - 0.2, G + 0.14), (x + 0.35, y + 0.2, G + 0.30), "toy_plastic", color=mul(RED, 1.2), skip="+z")   # wagon
    for wx in (-0.25, 0.25):
        for wy in (-0.22, 0.22):
            m.cylinder((x + wx, y + wy - 0.02, G + 0.09), (0, 0.04, 0), 0.09, "plastic_dark", segments=8)
    m.tube([(x + 0.35, y, G + 0.2), (x + 0.75, y, G + 0.05)], 0.012, "plastic_dark", segments=4)
    frame = [(x - 1.6, y + 1.2), (x - 0.3, y + 1.2), (x - 0.3, y + 2.5), (x - 1.6, y + 2.5), (x - 1.6, y + 1.2)]        # sandbox
    for (ax, ay), (bx_, by_) in zip(frame, frame[1:]):
        m.box((min(ax, bx_) - 0.04, min(ay, by_) - 0.04, G), (max(ax, bx_) + 0.04, max(ay, by_) + 0.04, G + 0.18), "wood_weathered",
              color=(0.66, 0.62, 0.56))
    m.face([Vector((x - 1.56, y + 1.24, G + 0.10)), Vector((x - 0.34, y + 1.24, G + 0.10)), Vector((x - 0.34, y + 2.46, G + 0.10)),
            Vector((x - 1.56, y + 2.46, G + 0.10))], "lawn_dead", color=(0.7, 0.66, 0.55))
    m.cylinder((x - 0.8, y + 1.7, G + 0.10), (0.03, 0, 0.16), 0.08, "toy_plastic", segments=8, radius_top=0.10, color=mul(BLUE, 1.2))
    m.box((x - 1.3, y + 2.0, G + 0.10), (x - 1.1, y + 2.06, G + 0.13), "toy_plastic", color=mul(YELLOW, 1.2))
    tri = MeshBuilder()                                                                                              # tricycle on its side
    loop(tri, (0.35, 0, 0.16), 0.15, Matrix.Rotation(math.pi / 2, 4, "X"), 0.02, "plastic_dark", segs=10)
    for wy in (-0.2, 0.2):
        loop(tri, (-0.3, wy, 0.11), 0.10, Matrix.Rotation(math.pi / 2, 4, "X"), 0.018, "plastic_dark", segs=10)
    tri.tube([(0.35, 0, 0.16), (0.28, 0, 0.5), (-0.3, 0, 0.14)], 0.014, "toy_plastic", segments=4, color=mul(RED, 1.2))
    tri.tube([(0.28, -0.18, 0.5), (0.28, 0.18, 0.5)], 0.012, "chrome_dull", segments=4)
    tri.box((-0.2, -0.08, 0.28), (0.0, 0.08, 0.31), "toy_plastic", color=mul(BLUE, 1.2))
    m.extend(tri, Matrix.Translation((x + 2.4, y + 1.9, G + 0.1)) @ Matrix.Rotation(1.1, 4, "Z") @ Matrix.Rotation(1.35, 4, "X"))

    # L6, 3 Mill Road: an empty dog house, its chain and bowl
    x, y = -3.9, -45.6
    m = det.at(x, y)
    wood = (0.6, 0.56, 0.5)
    m.box((x - 0.5, y - 0.6, G), (x + 0.5, y + 0.6, G + 0.6), "wood_weathered", color=wood, skip="-z+z")
    m.face([Vector((x + 0.502, y - 0.2, G)), Vector((x + 0.502, y + 0.2, G)), Vector((x + 0.502, y + 0.2, G + 0.42)),
            Vector((x + 0.502, y - 0.2, G + 0.42))], "interior_dark")
    for sgn in (-1, 1):
        a, b = Vector((x + 0.6, y + sgn * 0.7, G + 0.55)), Vector((x - 0.6, y + sgn * 0.7, G + 0.55))
        c, d = Vector((x - 0.6, y, G + 0.95)), Vector((x + 0.6, y, G + 0.95))
        m.face([a, b, c, d] if sgn < 0 else [b, a, d, c], "roof_shingle", color=(0.8, 0.8, 0.8))
    for xs_ in (x - 0.5, x + 0.5):
        m.face([Vector((xs_, y - 0.6, G + 0.6)), Vector((xs_, y + 0.6, G + 0.6)), Vector((xs_, y, G + 0.93))], "wood_weathered", color=wood)
    chain = [(x + 0.5, y + 0.5, G + 0.25), (x + 0.9, y + 0.7, G + 0.03), (x + 1.6, y + 0.3, G + 0.02), (x + 2.0, y + 0.9, G + 0.02)]
    m.tube(chain, 0.012, "chrome_dull", segments=4)
    m.cylinder((x + 1.3, y - 0.5, G), (0, 0, 0.07), 0.13, "chrome_dull", segments=10, radius_top=0.16)
    fx, fy = -1.85, -46.5
    det.at(fx, fy).card((fx + 0.035, fy, G + 0.55), 0.30, 0.30, math.pi / 2, "sign_beware")

    # L7, the vacant lot: tyres, pallets, a mattress
    x, y = 11.2, -42.2
    m = det.at(x, y)
    for k, (tx_, ty_, tz, tilt) in enumerate(((0, 0, 0.11, 0), (0.05, 0.03, 0.33, 0), (0.75, 0.2, 0.11, 0), (0.5, -0.8, 0.30, 1.2))):
        mat = Matrix.Rotation(tilt, 4, "Y") if tilt else Matrix.Identity(4)
        loop(m, (x + tx_, y + ty_, G + tz), 0.26, mat, 0.11, "tyre", segs=12, colour=(0.4, 0.4, 0.4))
    px, py = 23.6, -45.6
    m = det.at(px, py)
    for layer in range(3):
        z = G + layer * 0.15
        for k in range(5):
            m.box((px - 0.6, py - 0.5 + k * 0.24, z + 0.10), (px + 0.6, py - 0.4 + k * 0.24, z + 0.125), "wood_weathered",
                  color=jitter_color(rng, (0.66, 0.62, 0.55), 0.1))
        for k in range(3):
            m.box((px - 0.6 + k * 0.55, py - 0.5, z), (px - 0.5 + k * 0.55, py + 0.56, z + 0.10), "wood_weathered", color=(0.55, 0.52, 0.47))
    m = det.at(20.6, -41.8)
    m.obox((20.6, -41.8, G + 0.10), (1.9, 0.95, 0.2), 0.5, "trim", color=(0.5, 0.48, 0.42))
    dec.at(20.6, -41.8).card((20.7, -41.9, G + 0.205), 1.2, 0.8, 0.5, "decal_oil", flat=True)

    corner_stories(det, dec, rng)


def _house_local(key):
    """For lot `key`'s kit house: a function from house-local (x along the
    front, y back from it, world z) to world, and the same as a matrix. Local
    y below 0 is in front of the house, towards the street."""
    h = next(l for l in plan.LOTS if l.key == key).house
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    mat = Matrix(((ax, bx, 0, ox), (ay, by, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))
    return h, (lambda lx, ly, z=0.0: mat @ Vector((lx, ly, z))), mat


def _ladder(mb, length=3.0, width=0.42, rungs=9):
    """An aluminium ladder lying flat, along local x from 0."""
    for y in (-width / 2, width / 2):
        mb.box((0, y - 0.025, 0), (length, y + 0.025, 0.07), "chrome_dull", color=(0.62, 0.62, 0.6))
    for k in range(rungs):
        x = 0.2 + k * (length - 0.4) / (rungs - 1)
        mb.cylinder((x, -width / 2, 0.035), (0, width, 0), 0.016, "chrome_dull", segments=5, caps="", color=(0.55, 0.55, 0.53))


def _sawhorse(mb, colour):
    """A sawhorse: a beam on two splayed A-frames, at the local origin, along x."""
    mb.box((-0.55, -0.045, 0.66), (0.55, 0.045, 0.75), "wood_weathered", color=colour)
    for x in (-0.42, 0.42):
        for s in (-1, 1):
            mb.tube([(x, 0.0, 0.7), (x + 0.06 * (1 if x > 0 else -1), s * 0.3, 0.0)], 0.022, "wood_weathered", segments=4,
                    color=mul(colour, 0.9))


def _armchair(mb, colour):
    """An overstuffed armchair at the local origin, facing -y."""
    mb.box((-0.42, -0.4, 0.0), (0.42, 0.42, 0.42), "fabric", color=colour)                 # base and seat
    mb.box((-0.42, 0.22, 0.42), (0.42, 0.42, 0.95), "fabric", color=mul(colour, 0.95))     # back
    for x0 in (-0.42, 0.28):                                                                # arms
        mb.box((x0, -0.4, 0.42), (x0 + 0.14, 0.24, 0.62), "fabric", color=mul(colour, 0.9))
    mb.box((-0.3, -0.36, 0.42), (0.3, 0.2, 0.5), "fabric", color=mul(colour, 1.05))         # cushion


def corner_stories(det: Sectors, dec: Sectors, rng):
    """L8 to L11, the four houses at the ends of Ashgrove: a small story each,
    like the other lots'."""
    # L8, 10 Ashgrove: the boarding-up was never finished. Spare sheets lean on
    # the front wall, the sawhorse is still out, the ladder lies in the grass.
    h, W, M = _house_local("L8")
    story = MeshBuilder()
    for k in range(3):                                   # 4 x 8 ft plywood, leaning on the wall
        story.obox((5.75 + 0.14 * k, -0.33 - 0.03 * k, G + 1.17), (1.22, 0.014, 2.42), 0.0, "plywood",
                   color=jitter_color(rng, (0.72, 0.64, 0.5), 0.08), tilt=(-0.2, 0.0))
    _sawhorse(sh := MeshBuilder(), (0.62, 0.58, 0.5))
    story.extend(sh, Matrix.Translation((5.3, -3.4, G)) @ Matrix.Rotation(0.25, 4, "Z"))
    story.obox((5.3, -3.42, G + 0.77), (1.22, 0.6, 0.014), 0.25, "plywood", color=(0.68, 0.6, 0.47), tilt=(0.0, 0.05))
    _ladder(ld := MeshBuilder())
    story.extend(ld, Matrix.Translation((3.6, -5.6, G + 0.02)) @ Matrix.Rotation(-0.35, 4, "Z"))
    story.cylinder((6.6, -2.4, G + 0.09), (0.17, 0.05, 0.0), 0.09, "metal_painted", segments=10, color=(0.55, 0.55, 0.52))  # paint can, on its side
    story.cylinder((6.95, -2.85, G), (0, 0, 0.012), 0.11, "metal_painted", segments=10, color=(0.6, 0.58, 0.55))        # and its lid
    c = W(5.3, -3.0)
    det.at(c.x, c.y).extend(story, M)
    p = W(6.95, -2.3, G + 0.004)
    dec.at(p.x, p.y).card((p.x, p.y, p.z), 0.7, 0.45, rng.uniform(0, 3), "decal_oil", flat=True)                   # the spill

    # L9, 18 Ashgrove: someone kept a garden. A raised bed gone to weed, its
    # tomato stakes leaning, a watering can, the bird bath's bowl in the grass.
    h, W, M = _house_local("L9")
    story = MeshBuilder()
    bx0, by0, bx1, by1 = 5.3, -7.2, 7.9, -5.9
    wood = (0.6, 0.55, 0.47)
    story.box((bx0, by0, G), (bx1, by0 + 0.05, G + 0.28), "wood_weathered", color=wood)
    story.box((bx0, by1 - 0.05, G), (bx1, by1, G + 0.28), "wood_weathered", color=wood)
    story.box((bx0, by0, G), (bx0 + 0.05, by1, G + 0.28), "wood_weathered", color=wood)
    story.box((bx1 - 0.05, by0, G), (bx1, by1, G + 0.28), "wood_weathered", color=wood)
    story.face([Vector((bx0 + 0.05, by0 + 0.05, G + 0.22)), Vector((bx1 - 0.05, by0 + 0.05, G + 0.22)),
                Vector((bx1 - 0.05, by1 - 0.05, G + 0.22)), Vector((bx0 + 0.05, by1 - 0.05, G + 0.22))],
               "lawn_dead", color=(0.42, 0.36, 0.3))
    tops = []
    for k in range(5):                                   # stakes, some leaning, one fallen
        sx = bx0 + 0.35 + k * 0.48
        sy = (by0 + by1) / 2 + rng.uniform(-0.15, 0.15)
        if k == 3:
            story.obox((sx, sy - 0.2, G + 0.24), (0.025, 1.2, 0.025), 0.3, "wood_weathered", color=(0.66, 0.6, 0.5))
            continue
        lean = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.2, 0.2), 1.15))
        top = Vector((sx, sy, G + 0.2)) + lean
        story.tube([(sx, sy, G + 0.2), tuple(top)], 0.013, "wood_weathered", segments=4, color=(0.66, 0.6, 0.5))
        tops.append(top - Vector((0, 0, 0.25)))
    story.tube(tops, 0.003, "wire", segments=3)          # the twine between them, slack
    for k in range(6):                                   # dead vines round the stakes
        t = tops[k % len(tops)]
        story.tube([(t.x, t.y, G + 0.22), (t.x + rng.uniform(-0.2, 0.2), t.y + rng.uniform(-0.15, 0.15), G + 0.6),
                    (t.x + rng.uniform(-0.1, 0.1), t.y, t.z)], 0.007, "bark", segments=3, color=(0.5, 0.45, 0.36))
    can_x, can_y = 4.9, -5.0                             # the watering can, on its side
    story.cylinder((can_x, can_y, G + 0.13), (0.3, 0.0, 0.0), 0.13, "metal_painted", segments=10, color=(0.36, 0.42, 0.36))
    story.tube([(can_x + 0.28, can_y, G + 0.12), (can_x + 0.55, can_y - 0.08, G + 0.16)], 0.02, "metal_painted", segments=5,
               color=(0.36, 0.42, 0.36))
    story.tube([(can_x + 0.02, can_y, G + 0.24), (can_x + 0.15, can_y, G + 0.3), (can_x + 0.27, can_y, G + 0.24)], 0.012,
               "metal_painted", segments=4, color=(0.33, 0.38, 0.33))
    bb_x, bb_y = 1.2, -6.4                               # bird bath: the pedestal up, the bowl knocked off
    story.cylinder((bb_x, bb_y, G), (0, 0, 0.7), 0.11, "concrete", segments=10, radius_top=0.08, color=(0.62, 0.6, 0.56))
    story.cylinder((bb_x, bb_y, G), (0, 0, 0.06), 0.2, "concrete", segments=10, color=(0.6, 0.58, 0.54))
    story.cylinder((bb_x + 0.65, bb_y - 0.2, G + 0.02), (0.03, 0.0, 0.12), 0.32, "concrete", segments=12, radius_top=0.36,
                   color=(0.6, 0.58, 0.55))
    c = W(5.0, -6.0)
    det.at(c.x, c.y).extend(story, M)

    # L10, 13 Ashgrove: nobody took the papers in. They lie on the steps and
    # the porch in their bags; round the back, two sheets are still on the line.
    h, W, M = _house_local("L10")
    story = MeshBuilder()
    for k in range(9):                                   # rolled newspapers in faded bags
        on_porch = k < 4
        lx = h.door_at + 0.45 + rng.uniform(-0.9, 0.9)
        ly = rng.uniform(-1.6, -0.5) if on_porch else rng.uniform(-3.8, -2.9)
        z = -0.02 if on_porch else G
        a = rng.uniform(0, math.pi)
        d = Vector((math.cos(a), math.sin(a), 0.0)) * 0.3
        story.cylinder((lx - d.x / 2, ly - d.y / 2, z + 0.035), tuple(d), 0.035, "bag_plastic", segments=6,
                       color=jitter_color(rng, (0.75, 0.72, 0.62), 0.15))
    for lx in (0.6, 6.9):                                # the washing line, two T-posts
        story.cylinder((lx, 13.2, G), (0, 0, 2.0), 0.03, "metal_rust", segments=6)
        story.box((lx - 0.03, 12.75, G + 1.96), (lx + 0.03, 13.65, G + 2.02), "metal_rust")
    for y in (12.85, 13.55):
        story.tube([(0.6, y, G + 1.98), (3.75, y, G + 1.86), (6.9, y, G + 1.98)], 0.003, "wire", segments=3)
    for x0, x1, y, hang, col in ((1.2, 2.9, 12.85, 1.15, (0.78, 0.76, 0.7)), (4.0, 5.6, 13.55, 0.95, (0.55, 0.62, 0.66))):
        # a sheet pegged along the sagging line: 4 x 2 quads, bellied by the wind and hanging lower in the middle
        cols, rows = 4, 2
        grid = []
        for r in range(rows + 1):
            v = r / rows
            line = []
            for c in range(cols + 1):
                u = c / cols
                x = x0 + (x1 - x0) * u
                top = G + 1.98 - 0.12 * (x - 0.6) / 3.15 - 0.04 * math.sin(math.pi * u)
                line.append(Vector((x, y + 0.12 * v * math.sin(math.pi * u) + 0.03 * math.sin(3.0 * u + y),
                                    top - hang * v - 0.06 * v * math.sin(math.pi * u))))
            grid.append(line)
        for r in range(rows):
            for c in range(cols):
                quad = [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
                story.face(quad, "fabric", color=mul(col, 1.0 - 0.06 * r))
                story.face(list(reversed(quad)), "fabric", color=mul(col, 0.8))           # the back of the sheet
    story.obox((2.2, 14.3, G + 0.13), (0.6, 0.42, 0.26), 0.4, "toy_plastic", color=(0.62, 0.6, 0.55), skip="+z",
               tilt=(1.2, 0.0))                          # the laundry basket, tipped over
    c = W(3.7, 4.0)
    det.at(c.x, c.y).extend(story, M)

    # L11, 19 Ashgrove: cleared out in a hurry. The upstairs window was broken
    # from outside (the brick is on the porch, in the glass); an armchair and a
    # rolled rug were dumped in the side yard for a pickup that never came.
    h, W, M = _house_local("L11")
    story = MeshBuilder()
    win_x = h.windows_ff[0][0] + h.windows_ff[0][1] / 2
    story.obox((win_x + 0.3, -1.3, -0.02 + 0.035), (0.2, 0.09, 0.065), 0.7, "brick", color=(0.55, 0.32, 0.25))
    _armchair(ac := MeshBuilder(), (0.36, 0.4, 0.3))
    story.extend(ac, Matrix.Translation((h.width + 1.2, 1.4, G)) @ Matrix.Rotation(2.2, 4, "Z") @ Matrix.Rotation(0.08, 4, "X"))
    story.cylinder((h.width + 0.8, 3.2, G + 0.17), (0.25, 1.9, 0.0), 0.17, "fabric", segments=10, color=(0.42, 0.22, 0.18))
    c = W(h.width + 1.0, 2.0)
    det.at(c.x, c.y).extend(story, M)
    p = W(win_x + 0.1, -1.1, -0.02 + 0.006)
    dec.at(p.x, p.y).card((p.x, p.y, p.z), 1.1, 0.8, rng.uniform(0, 3), "decal_shards", flat=True)


# --- layered leaf litter -------------------------------------------------------------------

LEAF_TONES = [(0.95, 0.80, 0.55), (0.80, 0.62, 0.40), (0.60, 0.48, 0.34), (1.0, 0.9, 0.6), (0.45, 0.38, 0.30)]


def _leaf(mb, x, y, z, rng):
    """One fallen leaf: a small card, curled a little off the ground, from the 2 x 2 leaf sheet."""
    size = rng.uniform(0.07, 0.13)
    m = Matrix.Translation((x, y, z + rng.uniform(0.006, 0.025))) @ Matrix.Rotation(rng.uniform(0, 6.283), 4, "Z") \
        @ Matrix.Rotation(rng.uniform(-0.45, 0.45), 4, "X") @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, "Y")
    pts = [m @ Vector(v) for v in ((-size / 2, -size * 0.6, 0), (size / 2, -size * 0.6, 0), (size / 2, size * 0.6, 0),
                                   (-size / 2, size * 0.6, 0))]
    cell = rng.randrange(4)
    cu, cv = (cell % 2) * 0.5, (cell // 2) * 0.5
    tone = LEAF_TONES[rng.randrange(len(LEAF_TONES))]
    wet = rng.uniform(0.55, 1.0)
    mb.face(pts, "leaf_card", uvs=[(cu, cv), (cu + 0.5, cv), (cu + 0.5, cv + 0.5), (cu, cv + 0.5)], color=mul(tone, wet))


def leaf_layers(lv: Sectors, houses, rng):
    """The top layer of the leaf litter in the hero areas: single leaves over the
    flat leaf decals, thick where the wind leaves them (gutters, fence lines,
    steps, porch corners) and thin in the open."""
    def scatter(n, x0, y0, x1, y1, z=None, bias=None):
        for _ in range(n):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if bias == "y0":
                y = y0 + (y1 - y0) * rng.random() ** 2.2
            elif bias == "y1":
                y = y1 - (y1 - y0) * rng.random() ** 2.2
            elif bias == "x0":
                x = x0 + (x1 - x0) * rng.random() ** 2.2
            elif bias == "x1":
                x = x1 - (x1 - x0) * rng.random() ** 2.2
            _leaf(lv.at(x, y), x, y, sk._surface_z(x, y) if z is None else z, rng)

    dx = plan.HOUSE_DOOR_X
    # the house lot: the path, the foot of the steps, along the fence, the porch itself
    scatter(160, dx - 0.9, -8.5, dx + 0.9, -2.9, z=G + 0.025)
    scatter(120, dx - 1.6, -3.6, dx + 1.6, -2.6, z=G)
    scatter(220, -4.3, -8.3, 11.3, -7.3, z=G, bias="y0")
    scatter(70, 0.4, -2.2, 3.6, -0.4, z=-0.005, bias="y1")
    scatter(150, -4.0, -7.0, 11.0, -3.0, z=G)
    # the sidewalk and both gutters in front of the house
    scatter(260, -8.0, -10.2, 14.0, -8.6, bias="y1")
    scatter(300, -8.0, -11.0, 14.0, -10.2, bias="y1")
    scatter(260, -8.0, -18.1, 14.0, -17.3, bias="y0")
    # the junction: corners and the mouth of Mill Road
    scatter(200, -1.6, -19.7, 0.0, -18.1)
    scatter(200, 7.0, -19.7, 8.6, -18.1)
    scatter(220, 0.0, -19.5, 7.0, -10.4)
    # the first thirty metres of Mill Road: both gutters, both sidewalks, a thin scatter on the road
    scatter(320, 0.0, -48.0, 0.8, -18.1, bias="x0")
    scatter(320, 6.2, -48.0, 7.0, -18.1, bias="x1")
    scatter(200, -1.6, -48.0, 0.0, -19.7, bias="x1")
    scatter(200, 7.0, -48.0, 8.6, -19.7, bias="x0")
    scatter(160, 0.8, -48.0, 6.2, -19.5)
    # neighbours' porches and steps
    for key, (obj, m, ramps, steps) in houses.items():
        sx0, sx1, sy = steps
        for _ in range(60):
            p = m @ Vector((rng.uniform(sx0 - 1.2, sx1 + 1.2), rng.uniform(-2.2, -0.2), 0))
            _leaf(lv.at(p.x, p.y), p.x, p.y, -0.02, rng)
        for _ in range(50):
            p = m @ Vector((rng.uniform(sx0 - 0.6, sx1 + 0.6), rng.uniform(sy - 1.2, sy + 0.1), 0))
            _leaf(lv.at(p.x, p.y), p.x, p.y, G, rng)


def gate(med: Sectors, rng):
    """The player's front gate, left open: pickets on two rails, sagging on its hinges."""
    hx, hy = plan.HOUSE_DOOR_X + 0.85, -8.35
    leaf = MeshBuilder()
    col = (0.95, 0.93, 0.88)
    for zr in (0.25, 0.72):
        leaf.box((0.0, -0.02, G + zr), (1.55, 0.02, G + zr + 0.06), "trim", color=mul(col, 0.9))
    leaf.obox((0.78, 0.0, G + 0.5), (1.65, 0.03, 0.05), 0.0, "trim", color=mul(col, 0.85), tilt=(0.0, -0.28))   # diagonal brace
    x = 0.03
    while x < 1.5:
        h = 0.95 + rng.uniform(-0.02, 0.02)
        leaf.box((x, -0.045, G + 0.06), (x + 0.075, -0.02, G + h), "trim", color=jitter_color(rng, col, 0.08))
        tip = [Vector((x, -0.045, G + h)), Vector((x + 0.075, -0.045, G + h)), Vector((x + 0.0375, -0.045, G + h + 0.06))]
        leaf.face(tip, "trim", color=col)
        leaf.face([Vector((v.x, -0.02, v.z)) for v in reversed(tip)], "trim", color=col)
        x += 0.135
    for zr in (0.3, 0.75):                                          # strap hinges
        leaf.box((-0.03, -0.05, G + zr), (0.22, -0.045, G + zr + 0.04), "metal_rust")
    leaf.box((1.42, -0.055, G + 0.62), (1.54, -0.045, G + 0.66), "metal_rust")       # latch
    m = Matrix.Translation((hx, hy, 0)) @ Matrix.Rotation(math.radians(118), 4, "Z") @ Matrix.Rotation(-0.03, 4, "Y")
    med.at(hx, hy).extend(leaf, m)


# --- where the town ends ---------------------------------------------------------------------

EDGE_TREES = (
    (-33.5, -6.0, 11.0), (-34.5, -17.0, 9.5), (-33.0, -23.5, 12.0), (-35.5, -11.5, 13.0), (-34.0, 3.0, 10.0),
    (41.5, -8.0, 12.0), (42.5, -16.5, 10.0), (41.0, -22.0, 11.5), (43.0, -2.0, 9.0), (40.8, -12.5, 13.5),
    (-2.5, -59.5, 11.0), (4.0, -60.5, 12.5), (9.5, -59.5, 10.0), (-9.0, -60.0, 9.5), (16.0, -60.5, 11.0),
)


def fog_ends(rng):
    """Past each closed end of a street: dead trees, then a dark line of trees and roofs,
    so the view dissolves into the fog instead of stopping at a fence."""
    variants = [sk.shared(f"tree_{k}", lambda k=k: sk._tree(200 + k)) for k in range(3)]
    for i, (x, y, h) in enumerate(EDGE_TREES):
        instance(variants[i % 3], f"edgetree_{i}", "trees", (x, y, G), rng.uniform(0, 6.28), scale=h / 9.0)
    mb = MeshBuilder()
    # (south of Mill Road there is no card: the mill itself stands there, tk/store.py)
    for cx, cy, rot, width in ((-44.0, -14.0, -math.pi / 2, 56.0), (52.0, -14.0, math.pi / 2, 56.0),
                               # the diagonals stop short of the corner lots L10 and L11 (their
                               # inner ends were in those back yards, seen from behind: black)
                               (-45.3, -55.3, -math.pi / 4 - math.pi / 2, 40.0),
                               (53.3, -55.3, math.pi / 4 + math.pi / 2, 40.0)):
        mb.card((cx, cy, G - 0.5), width, 15.0, rot, "backdrop", uvs=((0, 0), (width / 60.0, 0), (width / 60.0, 1), (0, 1)))
    mb.build("backdrop_ends", "ground")
    # the ground beyond the fences is bare and dark
    gm = MeshBuilder()
    for rect in ((-46.0, -30.0, plan.BUILD[0], 4.0), (plan.BUILD[2], -30.0, 54.0, 4.0)):
        x0, y0, x1, y1 = rect
        gm.face([Vector((x0, y0, G)), Vector((x1, y0, G)), Vector((x1, y1, G)), Vector((x0, y1, G))], "lawn_dead",
                color=(0.3, 0.3, 0.27))
    gm.build("ground_beyond", "ground")


def build(houses):
    rng = random.Random(77)
    # det: small things, no shadows. med: things big enough to throw one (benches,
    # bags, signs, yard furniture). dec: flat decals. lv: single leaves.
    det, med, dec, lv = Sectors("detail"), Sectors("mprop"), Sectors("decals_b"), Sectors("leaves")
    gutters_and_drains(det, dec, rng)
    signs_and_bus_stop(med, rng)
    trash(med, dec, rng)
    cart_and_bike(det, rng)
    posters(det)
    road_marks(dec, rng)
    lot_stories(med, dec, houses, rng)
    street_extras(det, med, dec, random.Random(79))
    house_extras(med, houses, random.Random(80))
    gate(med, rng)
    leaf_layers(lv, houses, random.Random(78))
    from . import store
    store.station("houses")
    store.station_decals(dec, rng)
    store.mill("ground")
    det.build("props")
    med.build("props")
    dec.build("ground_detail")
    lv.build("ground_detail")
    # the knocked-over trash can is solid too
    for i, (x, y, rot, state) in enumerate(plan.TRASH_CANS):
        if state == "fallen":
            box = MeshBuilder()
            box.obox((x, y + 0.42, sk._surface_z(x, y) + 0.29), (0.62, 0.95, 0.58), math.radians(rot), "concrete")
            box.build(f"trash_can_fallen_{i}_col-convcolonly", "collision")
    fog_ends(rng)


# --- more street detail ---------------------------------------------------------------------

def _clear_of_damage(x, y, pad=0.4):
    """Not on a pothole, a patch, a puddle or a manhole: a decal there would float or sink."""
    for px, py, r in plan.POTHOLES + plan.PUDDLES:
        if math.hypot(x - px, y - py) < r + pad:
            return False
    for mx, my in plan.MANHOLES:
        if math.hypot(x - mx, y - my) < 0.6 + pad:
            return False
    for x0, y0, x1, y1 in plan.PATCHES:
        if x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad:
            return False
    return True


def _ribbon(mb, pts, width, z, mat, colour):
    """A flat strip along a polyline on the road."""
    for a, b in zip(pts, pts[1:]):
        d = (b - a).normalized()
        n = Vector((-d.y, d.x, 0)) * width / 2
        mb.face([Vector((a.x, a.y, z)) - n, Vector((b.x, b.y, z)) - n, Vector((b.x, b.y, z)) + n, Vector((a.x, a.y, z)) + n],
                mat, color=colour)


def _cone(mb, x, y, z, rng, fallen=False):
    """A traffic cone: square base, orange body, one white band. Fallen: on its side."""
    part = MeshBuilder()
    part.box((-0.19, -0.19, 0.0), (0.19, 0.19, 0.03), "plastic_dark")
    part.cylinder((0, 0, 0.03), (0, 0, 0.66), 0.15, "toy_plastic", segments=10, radius_top=0.025, color=(1.25, 0.42, 0.08))
    part.cylinder((0, 0, 0.36), (0, 0, 0.11), 0.095, "paint_white", segments=10, radius_top=0.077, caps="none",
                  color=(0.85, 0.85, 0.82))
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z")
    if fallen:
        m = m @ Matrix.Translation((0, 0, 0.16)) @ Matrix.Rotation(1.38, 4, "X")
    mb.extend(part, m)


def _litter(mb, x, y, z, kind, rng):
    a = rng.uniform(0, math.pi)
    d = Vector((math.cos(a), math.sin(a), 0.0))
    if kind == "can":
        col = [(0.7, 0.12, 0.1), (0.75, 0.75, 0.72), (0.15, 0.3, 0.6), (0.2, 0.45, 0.2)][rng.randrange(4)]
        mb.cylinder(tuple(Vector((x, y, z + 0.033)) - d * 0.06), tuple(d * 0.12), 0.033, "metal_painted", segments=8, color=col)
    elif kind == "crushed":
        mb.obox((x, y, z + 0.012), (0.08, 0.07, 0.024), a, "metal_painted", color=(0.7, 0.68, 0.64))
    elif kind == "bottle":
        col = [(0.25, 0.45, 0.2), (0.45, 0.3, 0.12), (0.7, 0.75, 0.72)][rng.randrange(3)]
        mb.cylinder(tuple(Vector((x, y, z + 0.035)) - d * 0.11), tuple(d * 0.17), 0.035, "glass_dirty", segments=8, color=col)
        mb.cylinder(tuple(Vector((x, y, z + 0.035)) + d * 0.06), tuple(d * 0.07), 0.035, "glass_dirty", segments=8, radius_top=0.013, color=col)
    elif kind == "cup":
        mb.cylinder(tuple(Vector((x, y, z + 0.04)) - d * 0.05), tuple(d * 0.1), 0.03, "trim", segments=8, radius_top=0.042,
                    color=(0.9, 0.88, 0.82))
    elif kind == "card":
        mb.obox((x, y, z + 0.008), (rng.uniform(0.25, 0.45), rng.uniform(0.2, 0.35), 0.012), a, "plywood",
                color=jitter_color(rng, (0.62, 0.48, 0.32), 0.1), tilt=(rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1)))
    else:  # bag
        blob(mb, (x, y, z), rng.uniform(0.12, 0.2), rng.uniform(0.1, 0.16), rng.uniform(0.06, 0.12), "bag_plastic", rng,
             colour=[(0.85, 0.85, 0.82), (0.25, 0.25, 0.27), (0.6, 0.55, 0.4)][rng.randrange(3)], rings=2, segs=8)


def street_extras(det: Sectors, med: Sectors, dec: Sectors, rng):
    """Tar snakes, a worn crosswalk, painted kerbs by the hydrants, litter in the
    gutters, a newspaper box, cable boxes, cones by the closures, a lost hubcap."""
    ag, mr = plan.ASHGROVE.road, plan.MILL.road
    # tar snakes: old cracks sealed with black tar, wandering across both roads
    for k in range(34):
        on_ash = k < 22
        for _ in range(20):
            x = rng.uniform(ag[0] + 3, ag[2] - 3) if on_ash else rng.uniform(mr[0] + 0.4, mr[2] - 0.4)
            y = rng.uniform(ag[1] + 0.4, ag[3] - 0.4) if on_ash else rng.uniform(mr[1] + 4, ag[1] - 1)
            if _clear_of_damage(x, y, 0.8):
                break
        else:
            continue
        heading = rng.uniform(0, math.pi) if rng.random() < 0.5 else (0.0 if on_ash else math.pi / 2)
        pts = [Vector((x, y, 0))]
        for _ in range(rng.randint(8, 26)):
            heading += rng.uniform(-0.45, 0.45)
            q = pts[-1] + Vector((math.cos(heading), math.sin(heading), 0)) * 0.22
            if not sk._on_road(q.x, q.y) or not _clear_of_damage(q.x, q.y, 0.3):
                break
            pts.append(q)
        if len(pts) > 3:
            _ribbon(dec.at(x, y), pts, rng.uniform(0.035, 0.06), RD + 0.005, "road_patch", (0.42, 0.42, 0.42))
    # a crosswalk over Ashgrove just west of the junction, worn to stubs where the wheels run
    cx = -4.4
    y = ag[1] + 0.35
    while y < ag[3] - 0.3:
        x0 = cx - 1.2
        while x0 < cx + 1.2:
            seg = rng.uniform(0.25, 0.9)
            x1 = min(x0 + seg, cx + 1.2)
            if rng.random() < 0.72:
                dec.at(cx, y).face([Vector((x0, y, RD + 0.007)), Vector((x1, y, RD + 0.007)), Vector((x1, y + 0.45, RD + 0.007)),
                                    Vector((x0, y + 0.45, RD + 0.007))], "paint_white", color=mul((0.82, 0.82, 0.78), rng.uniform(0.6, 0.9)))
            x0 = x1 + rng.uniform(0.03, 0.2)
        y += 0.95
    # yellow paint on the kerbs either side of each hydrant, mostly worn off
    for x, y in plan.HYDRANTS:
        m = det.at(x, y)
        col = (0.85, 0.66, 0.16)
        if abs(y - (ag[3] + 0.4)) < 0.9:                                  # north side of Ashgrove
            e = ag[3]
            m.box((x - 1.6, e - 0.012, RD), (x + 1.6, e + 0.11, SW + 0.004), "paint_marking", color=col)
        elif abs(y - (ag[1] - 0.9)) < 0.9:                                # south side
            e = ag[1]
            m.box((x - 1.6, e - 0.11, RD), (x + 1.6, e + 0.012, SW + 0.004), "paint_marking", color=col)
        else:                                                              # the east side of Mill Road
            e = mr[2]
            m.box((e - 0.012, y - 1.6, RD), (e + 0.11, y + 1.6, SW + 0.004), "paint_marking", color=col)
    # litter blown into the gutters
    kinds = ["can", "can", "crushed", "bottle", "cup", "card", "bag", "bag"]
    gutters = [("x", ag[3] - 0.2, ag[0] + 2, ag[2] - 2), ("x", ag[1] + 0.2, ag[0] + 2, ag[2] - 2),
               ("y", mr[0] + 0.2, mr[1] + 3, ag[1] - 2), ("y", mr[2] - 0.2, mr[1] + 3, ag[1] - 2)]
    for _ in range(64):
        axis, c, a0, a1 = gutters[rng.randrange(4)]
        t = rng.uniform(a0, a1)
        x, y = (t, c + rng.uniform(-0.12, 0.12)) if axis == "x" else (c + rng.uniform(-0.12, 0.12), t)
        if not _clear_of_damage(x, y, 0.2):
            continue
        _litter(det.at(x, y), x, y, RD, kinds[rng.randrange(len(kinds))], rng)
    # a newspaper box at the corner, its window fogged, chained to nothing
    nb = MeshBuilder()
    nb.box((-0.23, -0.2, 0.32), (0.23, 0.2, 0.92), "metal_painted", color=(0.2, 0.32, 0.55))
    nb.box((-0.2, -0.205, 0.55), (0.2, -0.2, 0.86), "glass_dirty", color=(0.6, 0.62, 0.6))
    nb.box((-0.08, -0.215, 0.36), (0.08, -0.2, 0.46), "chrome_dull")                       # coin slot box
    nb.box((-0.24, -0.21, 0.92), (0.24, 0.21, 0.96), "metal_painted", color=(0.18, 0.28, 0.48))
    for lx in (-0.18, 0.18):
        for ly in (-0.15, 0.15):
            nb.box((lx - 0.02, ly - 0.02, 0.0), (lx + 0.02, ly + 0.02, 0.32), "metal_rust")
    _solid_prop(nb, "prop_newsbox", Matrix.Translation((7.9, -19.1, SW)) @ Matrix.Rotation(math.radians(-8), 4, "Z"),
                (-0.25, -0.22, 0.0), (0.25, 0.22, 0.96))
    # cable-TV pedestals at the back of the sidewalk
    for i, (x, y, rot) in enumerate(((12.8, -8.82, 0.0), (-18.0, -19.48, math.pi), (-0.4, -27.5, math.pi / 2))):
        pb = MeshBuilder()
        pb.box((-0.16, -0.14, 0.0), (0.16, 0.14, 0.72), "metal_painted", color=(0.24, 0.32, 0.24))
        pb.cylinder((0, 0, 0.72), (0, 0, 0.06), 0.15, "metal_painted", segments=10, radius_top=0.1, color=(0.22, 0.3, 0.22))
        pb.box((-0.06, -0.145, 0.5), (0.06, -0.14, 0.58), "trim", color=(0.8, 0.78, 0.7))          # the warning label
        _solid_prop(pb, f"prop_pedestal_{i}", Matrix.Translation((x, y, SW)) @ Matrix.Rotation(rot, 4, "Z"),
                    (-0.17, -0.15, 0.0), (0.17, 0.15, 0.8))
    # cones left by whoever closed the roads, two knocked over
    for x, y, fallen in ((-27.5, -16.2, False), (-27.0, -14.3, True), (-27.8, -11.6, False),
                         (5.6, -52.6, False), (6.2, -54.0, True), (4.6, -51.0, False)):
        _cone(med.at(x, y), x, y, RD, rng, fallen)
    # the sidewalks: slabs heaved by roots and frost, one edge standing proud, and cracks
    for _ in range(14):
        name, (sx0, sy0, sx1, sy1) = plan.SIDEWALKS[rng.randrange(len(plan.SIDEWALKS))]
        along_x = (sx1 - sx0) > (sy1 - sy0)
        for _try in range(10):
            x = rng.uniform(sx0 + 1.0, sx1 - 1.0) if along_x else (sx0 + sx1) / 2
            y = (sy0 + sy1) / 2 if along_x else rng.uniform(sy0 + 1.0, sy1 - 1.0)
            if all(math.hypot(x - hx, y - hy) > 2.0 for hx, hy in plan.HYDRANTS) and \
                    all(math.hypot(x - p_.x, y - p_.y) > 1.5 for p_ in plan.POLES):
                break
        size = (1.5, (sy1 - sy0) - 0.06) if along_x else ((sx1 - sx0) - 0.06, 1.5)
        lift = rng.uniform(0.025, 0.045)
        tilt = (rng.choice((-1, 1)) * lift / size[1], 0.0) if along_x else (0.0, rng.choice((-1, 1)) * lift / size[0])
        det.at(x, y).obox((x, y, SW - 0.03 + lift / 2), (size[0], size[1], 0.06), 0.0, "sidewalk",
                          color=jitter_color(rng, (0.9, 0.9, 0.88), 0.05), tilt=tilt)
        dec.at(x, y).card((x + rng.uniform(-0.4, 0.4), y, SW + lift + 0.004), 0.9, 0.5, rng.uniform(0, 3.1), "decal_crack",
                          flat=True)
    for _ in range(26):
        name, (sx0, sy0, sx1, sy1) = plan.SIDEWALKS[rng.randrange(len(plan.SIDEWALKS))]
        x, y = rng.uniform(sx0 + 0.3, sx1 - 0.3), rng.uniform(sy0 + 0.2, sy1 - 0.2)
        dec.at(x, y).card((x, y, SW + 0.005), rng.uniform(0.6, 1.4), rng.uniform(0.3, 0.7), rng.uniform(0, 3.1), "decal_crack",
                          flat=True)
    # a hubcap off the west car, lying in the road
    hx, hy = -25.6, -12.0
    det.at(hx, hy).cylinder((hx, hy, RD + 0.002), (0.02, 0.0, 0.035), 0.19, "chrome_dull", segments=14, radius_top=0.12,
                            color=(0.6, 0.58, 0.55))


# --- more on the houses -------------------------------------------------------------------

def _ridge(h, t):
    """A point on the roof ridge, house-local, t from 0 to 1 along it, and the ridge's direction."""
    from .house_kit import EAVE
    w, d = h.width, h.depth
    if h.roof == "gable_side":
        return Vector((w * (0.1 + 0.8 * t), d / 2, EAVE + d / 2 * math.tan(math.radians(34)))), Vector((1, 0, 0))
    if h.roof == "gable_front":
        return Vector((w / 2, d * (0.1 + 0.8 * t), EAVE + w / 2 * math.tan(math.radians(40)))), Vector((0, 1, 0))
    ov, pitch = 0.35, math.radians(30)
    ez = EAVE - ov * math.tan(pitch)
    half = min(w, d) / 2 + ov
    rz = ez + half * math.tan(pitch)
    if w >= d:
        x0, x1 = -ov + half, w + ov - half
        return Vector((x0 + (x1 - x0) * t, d / 2, rz)), Vector((1, 0, 0))
    y0, y1 = -ov + half, d + ov - half
    return Vector((w / 2, y0 + (y1 - y0) * t, rz)), Vector((0, 1, 0))


def _antenna(mb, base, along, rng):
    """A 1980s TV aerial on a mast strapped to the ridge, leaning a little."""
    lean = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 1.0)).normalized()
    top = base + lean * rng.uniform(1.8, 2.4)
    alu = (0.62, 0.62, 0.6)
    mb.tube([base, top], 0.022, "chrome_dull", segments=5, color=alu)
    across = Vector((-along.y, along.x, 0))
    for level, length in ((0.0, 1.5), (-0.55, 1.0)):
        c = top + Vector((0, 0, level))
        a, b = c - along * length * 0.4, c + along * length * 0.6
        mb.tube([a, b], 0.009, "chrome_dull", segments=3, color=alu)
        n = 7 if length > 1.2 else 4
        for k in range(n):
            p = a.lerp(b, (k + 0.5) / n)
            half = 0.5 - 0.045 * k
            if rng.random() < 0.12:                      # an element snapped off, hanging
                mb.tube([p, p + across * 0.1 + Vector((0, 0, -0.35))], 0.005, "chrome_dull", segments=3, color=alu)
                continue
            mb.tube([p - across * half, p + across * half], 0.005, "chrome_dull", segments=3, color=alu)
    mb.tube([top - Vector((0, 0, 0.4)), base + across * 0.06 + Vector((0, 0, -0.4))], 0.004, "wire", segments=3)  # the lead-in


def _dish(mb, at, facing):
    """A small satellite dish on a wall bracket, pointing up and away."""
    out = facing.normalized()
    arm_end = at + out * 0.28
    mb.tube([at, arm_end], 0.02, "metal_painted", segments=5, color=(0.7, 0.7, 0.68))
    axis = (out * 0.6 + Vector((0, 0, 0.8))).normalized()
    rim = arm_end + axis * 0.12
    mb.cylinder(tuple(arm_end), tuple(axis * 0.12), 0.04, "metal_painted", segments=14, radius_top=0.3, color=(0.8, 0.8, 0.78))
    mb.tube([rim - axis * 0.06 + out * 0.0, rim + axis * 0.38], 0.008, "metal_painted", segments=3, color=(0.6, 0.6, 0.58))
    mb.box(tuple(rim + axis * 0.38 - Vector((0.03, 0.03, 0.03))), tuple(rim + axis * 0.38 + Vector((0.03, 0.03, 0.05))),
           "plastic_dark")


def _window_ac(mb, x, z, rng):
    """A window air conditioner hanging out of a front window: house-local, front wall at y 0."""
    beige = jitter_color(rng, (0.72, 0.68, 0.58), 0.05)
    mb.box((x - 0.31, -0.42, z), (x + 0.31, 0.06, z + 0.4), "metal_painted", color=beige)
    for k in range(7):
        zz = z + 0.05 + k * 0.045
        mb.box((x - 0.27, -0.425, zz), (x + 0.27, -0.42, zz + 0.022), "plastic_dark")
    mb.box((x - 0.3, -0.36, z - 0.04), (x + 0.3, -0.3, z), "metal_rust")                # the bracket under it
    mb.tube([(x - 0.25, -0.33, z - 0.02), (x - 0.25, -0.02, z - 0.3)], 0.012, "metal_rust", segments=4)
    mb.tube([(x + 0.25, -0.33, z - 0.02), (x + 0.25, -0.02, z - 0.3)], 0.012, "metal_rust", segments=4)


def _pot(mb, x, y, z, rng):
    """A clay pot with a plant long dead in it."""
    clay = jitter_color(rng, (0.6, 0.33, 0.22), 0.08)
    mb.cylinder((x, y, z), (0, 0, 0.3), 0.13, "trim", segments=10, radius_top=0.17, color=clay)
    mb.cylinder((x, y, z + 0.27), (0, 0, 0.04), 0.18, "trim", segments=10, color=mul(clay, 0.9))
    mb.face([Vector((x + math.cos(a) * 0.16, y + math.sin(a) * 0.16, z + 0.28)) for a in
             [2 * math.pi * i / 10 for i in range(10)]], "lawn_dead", color=(0.35, 0.28, 0.22))
    for _ in range(rng.randint(4, 7)):
        tip = Vector((x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), z + rng.uniform(0.45, 0.8)))
        mb.tube([(x, y, z + 0.28), ((x + tip.x) / 2, (y + tip.y) / 2, tip.z - 0.12), tip], 0.006, "bark", segments=3,
                color=(0.5, 0.42, 0.32))


# which house gets what: an aerial, a dish, an air conditioner in a front window, pots on the porch
HOUSE_EXTRAS = {
    "L2": ("antenna",), "L3": ("dish", "ac:ff0", "pots"), "L4": ("antenna",), "L5": ("antenna",),
    "L6": ("antenna", "pots"), "L8": ("antenna",), "L9": ("antenna", "ac:gf1", "pots"), "L10": ("dish",),
    "L11": ("antenna", "ac:ff1"),
}


def house_extras(med: Sectors, houses, rng):
    from .house_kit import EAVE, FF_SILL, GF_SILL
    for key, extras in HOUSE_EXTRAS.items():
        if key not in houses:
            continue
        obj, hm, ramps, steps = houses[key]
        h = next(l for l in plan.LOTS if l.key == key).house
        local = MeshBuilder()
        for extra in extras:
            if extra == "antenna":
                base, along = _ridge(h, rng.uniform(0.15, 0.3))
                _antenna(local, base + Vector((0, 0, 0.1)), along, rng)
            elif extra == "dish":
                _dish(local, Vector((h.width + 0.03, h.depth * 0.3, EAVE - 0.7)), Vector((1, -0.4, 0)))
            elif extra.startswith("ac:"):
                tag = extra[3:]
                windows = h.windows_ff if tag.startswith("ff") else h.windows_gf
                i = int(tag[2:])
                if i >= len(windows) or tag in h.boarded or tag in h.broken:
                    continue
                u0, width = windows[i]
                _window_ac(local, u0 + width / 2, (FF_SILL if tag.startswith("ff") else GF_SILL) + 0.02, rng)
            elif extra == "pots":
                for dx in (-0.55, 1.45):
                    _pot(local, h.door_at + dx, -0.5, -0.02, rng)
        centre = hm @ Vector((h.width / 2, h.depth / 2, 0))
        med.at(centre.x, centre.y).extend(local, hm)
