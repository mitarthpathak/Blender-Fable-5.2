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

RED = (0.55, 0.10, 0.08)
GREEN = (0.12, 0.30, 0.14)
BLUE = (0.14, 0.24, 0.50)
YELLOW = (0.70, 0.55, 0.10)


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
                               (-40.0, -52.0, -math.pi / 4 - math.pi / 2, 40.0),
                               (46.0, -52.0, math.pi / 4 + math.pi / 2, 40.0)):
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
