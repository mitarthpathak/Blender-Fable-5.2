"""Two places that make Halden Ridge a town rather than a street.

- **Ridge Gas & Grocery**: a small closed filling station where Mill Road
  ends, on the south half of the vacant lot. A flat-roofed block store with
  its window boarded, a canopy over two dead pumps, a price sign with digits
  missing, an ice chest, a pay phone, oil drums. One fluorescent tube under
  the canopy still buzzes.
- **The Halden mill**: the reason the town exists and the reason it is
  emptying. A long brick weaving shed with a sawtooth roof, a stair tower,
  a water tank and a tall stack, a hundred metres past the end of Mill
  Road. In fog it is a shape; in clear weather it is a building.

Names, brands and prices are our own.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, collection, jitter_color, light, mul
from .street_kit import G, RD, SW, Sectors

# Station footprint, on the south half of lot L7 (east side of Mill Road).
PAD = (9.0, -57.0, 23.6, -47.4)                  # concrete forecourt
STORE = (16.4, -56.4, 23.2, -50.4)               # x0, y0, x1, y1: the building
STORE_H = 3.3
CANOPY = (10.2, -55.6, 14.6, -49.2)
CANOPY_Z = 4.1
PUMPS = ((12.4, -54.0), (12.4, -50.8))
CREAM = (0.62, 0.58, 0.48)
GREEN = (0.13, 0.24, 0.17)


def _grime(z0, height, strength):
    def f(p):
        if p.z < z0 + height:
            return 1.0 - strength * (1.0 - (p.z - z0) / height) ** 1.5
        return 1.0
    return f


def _pump(mb, x, y, z, rng):
    """A 1980s pump: steel cabinet, glass face with the dials behind it, hose and nozzle."""
    body = mul(CREAM, 1.1)
    mb.box((x - 0.30, y - 0.22, z), (x + 0.30, y + 0.22, z + 1.05), "metal_painted", color=body, skip="-z")
    mb.box((x - 0.32, y - 0.24, z + 1.05), (x + 0.32, y + 0.24, z + 1.62), "metal_painted", color=mul(GREEN, 1.6))
    for side in (-1, 1):
        fy = y + side * 0.245
        q = [Vector((x - 0.24, fy, z + 1.12)), Vector((x + 0.24, fy, z + 1.12)), Vector((x + 0.24, fy, z + 1.52)),
             Vector((x - 0.24, fy, z + 1.52))]
        mb.face(q if side < 0 else list(reversed(q)), "glass_dirty")
        q = [Vector((x - 0.26, fy * 1.0 + side * 0.002, z + 0.25)), Vector((x + 0.26, fy + side * 0.002, z + 0.25)),
             Vector((x + 0.26, fy + side * 0.002, z + 0.95)), Vector((x - 0.26, fy + side * 0.002, z + 0.95))]
        mb.face(q if side < 0 else list(reversed(q)), "metal_rust", color=(0.8, 0.76, 0.7))
    mb.box((x - 0.34, y - 0.26, z + 1.62), (x + 0.34, y + 0.26, z + 1.68), "chrome_dull")
    # hose looped from the top to the nozzle in its cradle
    hx = x + 0.31
    mb.tube([(hx, y, z + 1.55), (hx + 0.16, y + 0.05, z + 1.1), (hx + 0.22, y, z + 0.45), (hx + 0.10, y - 0.05, z + 0.25),
             (hx + 0.03, y - 0.08, z + 0.85)], 0.018, "plastic_dark", segments=5)
    mb.box((hx, y - 0.12, z + 0.82), (hx + 0.07, y - 0.04, z + 1.0), "chrome_dull")


def station(coll="houses"):
    rng = random.Random(64)
    mb = MeshBuilder()
    x0, y0, x1, y1 = PAD
    # forecourt slab, cracked and stained, with a low island under the pumps
    mb.box((x0, y0, G - 0.05), (x1, y1, G + 0.04), "concrete", skip="-z", color=(0.72, 0.70, 0.66))
    ix0, ix1 = PUMPS[0][0] - 0.55, PUMPS[0][0] + 0.55
    mb.box((ix0, PUMPS[0][1] - 0.9, G + 0.04), (ix1, PUMPS[1][1] + 0.9, G + 0.19), "concrete", skip="-z",
           color=(0.8, 0.78, 0.72))
    for px, py in PUMPS:
        _pump(mb, px, py, G + 0.19, rng)
    for py in (PUMPS[0][1] - 0.75, PUMPS[1][1] + 0.75):                      # bollards
        mb.cylinder((PUMPS[0][0], py, G + 0.19), (0, 0, 0.75), 0.06, "metal_painted", segments=8, color=(0.75, 0.6, 0.12))

    # canopy: two steel posts, a deep fascia in the station's green, a ribbed underside
    cx0, cy0, cx1, cy1 = CANOPY
    for py in (PUMPS[0][1] - 0.2, PUMPS[1][1] + 0.2):
        mb.box((PUMPS[0][0] - 0.09, py - 0.09, G + 0.19), (PUMPS[0][0] + 0.09, py + 0.09, CANOPY_Z), "metal_painted",
               color=(0.7, 0.7, 0.66), skip="-z")
    mb.grime = _grime(CANOPY_Z, 0.5, 0.25)
    mb.box((cx0, cy0, CANOPY_Z), (cx1, cy1, CANOPY_Z + 0.55), "metal_painted", color=mul(GREEN, 1.5),
           mats={"-z": "roof_tin", "+z": "roof_tin"})
    mb.grime = None
    mb.box((cx0 - 0.02, cy0 - 0.02, CANOPY_Z + 0.36), (cx1 + 0.02, cy1 + 0.02, CANOPY_Z + 0.44), "metal_painted",
           color=mul(CREAM, 1.2))
    # the tube that still works, and one that does not
    for k, py in enumerate((PUMPS[0][1], PUMPS[1][1])):
        mb.box((PUMPS[0][0] - 0.6, py - 0.06, CANOPY_Z - 0.06), (PUMPS[0][0] + 0.6, py + 0.06, CANOPY_Z), "metal_painted",
               color=(0.8, 0.8, 0.78))
        mb.box((PUMPS[0][0] - 0.55, py - 0.03, CANOPY_Z - 0.09), (PUMPS[0][0] + 0.55, py + 0.03, CANOPY_Z - 0.06),
               "tube_on" if k == 0 else "sodium_off")

    # the store: painted block walls, flat roof behind a parapet, a boarded window, a locked door
    sx0, sy0, sx1, sy1 = STORE
    z0, z1 = G + 0.04, G + 0.04 + STORE_H
    mb.grime = _grime(z0, 1.3, 0.4)
    wall = mul(CREAM, 1.15)
    door = (sy0 + 0.9, sy0 + 1.9)                 # along the west front
    win = (sy0 + 2.5, sy1 - 0.6)
    # west front, cut round the door and the window
    for ya, yb, za, zb in ((sy0, door[0], z0, z1), (door[0], door[1], z0 + 2.1, z1), (door[1], win[0], z0, z1),
                           (win[0], win[1], z0, z0 + 0.9), (win[0], win[1], z0 + 2.3, z1), (win[1], sy1, z0, z1)):
        mb.face([Vector((sx0, yb, za)), Vector((sx0, ya, za)), Vector((sx0, ya, zb)), Vector((sx0, yb, zb))],
                "barrier_concrete", color=wall)
    mb.box((sx0, sy0, z0), (sx1, sy1, z1), "barrier_concrete", color=wall, skip="-x-z+z")
    mb.box((sx0 - 0.03, sy0 - 0.03, z0), (sx1 + 0.03, sy1 + 0.03, z0 + 0.5), "barrier_concrete", color=mul(GREEN, 1.4),
           skip="-z+z")                                                       # painted base band
    mb.grime = None
    mb.face([Vector((sx0, sy0, z1 - 0.25)), Vector((sx1, sy0, z1 - 0.25)), Vector((sx1, sy1, z1 - 0.25)),
             Vector((sx0, sy1, z1 - 0.25))], "roof_tin", color=(0.6, 0.6, 0.6))
    mb.box((sx0 - 0.06, sy0 - 0.06, z1), (sx1 + 0.06, sy1 + 0.06, z1 + 0.10), "metal_painted", color=(0.6, 0.6, 0.57))
    # door: steel frame, a glazed leaf with a bar across it and a notice taped inside
    dz = z0 + 2.1
    mb.box((sx0 - 0.02, door[0] - 0.06, z0), (sx0 + 0.10, door[0], dz + 0.06), "metal_painted", color=(0.5, 0.5, 0.48))
    mb.box((sx0 - 0.02, door[1], z0), (sx0 + 0.10, door[1] + 0.06, dz + 0.06), "metal_painted", color=(0.5, 0.5, 0.48))
    mb.box((sx0 - 0.02, door[0], dz), (sx0 + 0.10, door[1], dz + 0.06), "metal_painted", color=(0.5, 0.5, 0.48))
    mb.face([Vector((sx0 + 0.05, door[1], z0)), Vector((sx0 + 0.05, door[0], z0)), Vector((sx0 + 0.05, door[0], dz)),
             Vector((sx0 + 0.05, door[1], dz))], "glass_dirty")
    mb.face([Vector((sx0 + 0.4, door[1], z0)), Vector((sx0 + 0.4, door[0], z0)), Vector((sx0 + 0.4, door[0], dz)),
             Vector((sx0 + 0.4, door[1], dz))], "interior_dark")
    mb.box((sx0 + 0.0, door[0] + 0.05, z0 + 1.0), (sx0 + 0.04, door[1] - 0.05, z0 + 1.06), "chrome_dull")
    mb.card((sx0 + 0.03, (door[0] + door[1]) / 2, z0 + 1.25), 0.42, 0.56, -math.pi / 2, "sign_closed_store")
    # the shop window: plywood sheets over it, one corner pulled away, the dark shop behind
    mb.face([Vector((sx0 + 0.25, win[1], z0 + 0.9)), Vector((sx0 + 0.25, win[0], z0 + 0.9)), Vector((sx0 + 0.25, win[0], z0 + 2.3)),
             Vector((sx0 + 0.25, win[1], z0 + 2.3))], "interior_dark")
    y = win[0] - 0.05
    k = 0
    while y < win[1]:
        w = min(1.22, win[1] + 0.05 - y)
        if k != 2:
            lean = rng.uniform(-0.02, 0.02)
            mb.obox((sx0 - 0.02, y + w / 2, z0 + 1.6), (0.02, w - 0.01, 1.55), 0.0, "plywood",
                    color=jitter_color(rng, (0.82, 0.76, 0.66), 0.1), tilt=(lean, 0.0))
        else:                                              # the loose sheet, hanging by one corner
            mb.obox((sx0 - 0.08, y + w / 2 + 0.1, z0 + 1.35), (0.02, w - 0.01, 1.55), 0.0, "plywood",
                    color=(0.7, 0.64, 0.55), tilt=(0.22, 0.0))
        y += w
        k += 1
    # fascia sign along the front, lamps over it long dead
    mb.box((sx0 - 0.10, sy0 + 0.3, z1 - 0.95), (sx0 - 0.02, sy1 - 0.3, z1 - 0.20), "metal_painted", color=mul(GREEN, 1.4))
    mb.card((sx0 - 0.105, (sy0 + sy1) / 2, z1 - 0.92), sy1 - sy0 - 0.8, 0.68, -math.pi / 2, "sign_station")
    # along the front: ice chest, pay phone, newspaper box, a bench of stacked crates
    ice_y = sy1 - 1.5
    mb.box((sx0 - 0.75, ice_y - 0.9, z0), (sx0 - 0.05, ice_y + 0.9, z0 + 1.25), "metal_painted", color=(0.82, 0.83, 0.82),
           skip="-z")
    mb.card((sx0 - 0.755, ice_y, z0 + 0.35), 1.5, 0.75, -math.pi / 2, "sign_ice")
    ph_y = door[0] - 0.5
    mb.box((sx0 - 0.20, ph_y - 0.22, z0 + 1.0), (sx0, ph_y + 0.22, z0 + 1.75), "metal_painted", color=(0.25, 0.3, 0.42))
    mb.box((sx0 - 0.22, ph_y - 0.12, z0 + 1.25), (sx0 - 0.20, ph_y + 0.12, z0 + 1.55), "chrome_dull")
    mb.tube([(sx0 - 0.21, ph_y + 0.15, z0 + 1.3), (sx0 - 0.26, ph_y + 0.18, z0 + 0.9), (sx0 - 0.22, ph_y + 0.05, z0 + 0.62)], 0.008,
            "chrome_dull", segments=4)                                         # the handset hangs off its cord
    mb.box((sx0 - 0.26, ph_y + 0.0, z0 + 0.45), (sx0 - 0.20, ph_y + 0.07, z0 + 0.62), "plastic_dark")
    nb_y = door[1] + 0.45
    mb.box((sx0 - 0.45, nb_y - 0.2, z0), (sx0 - 0.08, nb_y + 0.2, z0 + 1.0), "metal_painted", color=(0.55, 0.14, 0.1), skip="-z")
    mb.face([Vector((sx0 - 0.452, nb_y + 0.16, z0 + 0.45)), Vector((sx0 - 0.452, nb_y - 0.16, z0 + 0.45)),
             Vector((sx0 - 0.452, nb_y - 0.16, z0 + 0.92)), Vector((sx0 - 0.452, nb_y + 0.16, z0 + 0.92))], "glass_dirty")
    # round the side and back: drums, a dumpster, a propane cage
    for k, (dx, dy) in enumerate(((sx0 + 0.5, sy1 + 0.45), (sx0 + 1.15, sy1 + 0.5), (sx0 + 0.85, sy1 + 1.05))):
        mb.cylinder((dx, dy, z0), (0, 0, 0.88), 0.29, "metal_rust", segments=14, color=jitter_color(rng, (0.6, 0.62, 0.66), 0.15))
        for zr in (0.28, 0.6):
            mb.cylinder((dx, dy, z0 + zr), (0, 0, 0.03), 0.30, "metal_rust", segments=14, caps="none", color=(0.5, 0.5, 0.5))
    mb.box((sx1 - 2.4, sy1 + 0.3, z0), (sx1 - 0.4, sy1 + 1.5, z0 + 1.2), "metal_painted", color=mul(GREEN, 1.2), skip="-z")
    mb.box((sx1 - 2.45, sy1 + 0.25, z0 + 1.2), (sx1 - 0.35, sy1 + 1.55, z0 + 1.26), "plastic_dark")

    # the price sign by the road: a tall pole, the brand, three grades, digits fallen out
    px, py = 9.9, -48.3
    mb.cylinder((px, py, G), (0, 0, 5.6), 0.09, "metal_painted", segments=10, color=(0.7, 0.7, 0.66))
    mb.box((px - 0.08, py - 0.95, G + 3.0), (px + 0.08, py + 0.95, G + 5.5), "metal_painted", color=(0.78, 0.77, 0.72))
    mb.card((px - 0.085, py, G + 4.45), 1.8, 0.95, -math.pi / 2, "sign_station",
            uvs=((0.0, 0), (0.42, 0), (0.42, 1), (0.0, 1)))
    mb.card((px + 0.085, py, G + 4.45), 1.8, 0.95, math.pi / 2, "sign_station",
            uvs=((0.0, 0), (0.42, 0), (0.42, 1), (0.0, 1)))
    mb.card((px - 0.085, py, G + 3.1), 1.7, 1.3, -math.pi / 2, "sign_prices")
    mb.card((px + 0.085, py, G + 3.1), 1.7, 1.3, math.pi / 2, "sign_prices")
    obj = mb.build("house_station", coll)
    obj["address"] = "Ridge Gas & Grocery, Mill Road"

    # the one tube under the canopy that still lights
    light("street_tube_station_flicker", (PUMPS[0][0], PUMPS[0][1], CANOPY_Z - 0.2), "point", 60.0, (0.75, 0.95, 0.85),
          radius=0.3)
    return obj


def station_decals(dec: Sectors, rng):
    x0, y0, x1, y1 = PAD
    for _ in range(9):
        x, y = rng.uniform(x0 + 0.5, STORE[0] - 0.5), rng.uniform(y0 + 0.5, y1 - 0.5)
        dec.at(x, y).card((x, y, G + 0.048), rng.uniform(0.8, 1.8), rng.uniform(0.7, 1.5), rng.uniform(0, 3), "decal_oil", flat=True)
    for _ in range(7):
        x, y = rng.uniform(x0 + 0.5, x1 - 0.5), rng.uniform(y0 + 0.5, y1 - 0.5)
        dec.at(x, y).card((x, y, G + 0.046), rng.uniform(1.0, 2.0), rng.uniform(0.8, 1.6), rng.uniform(0, 3), "decal_crack", flat=True)
    for x, y in ((11.2, -52.4), (13.6, -50.0), (15.2, -55.0)):
        dec.at(x, y).card((x, y, G + 0.05), 2.2, 2.2, rng.uniform(0, 3), "decal_leaves", flat=True)
    dec.at(15.0, -53.5).card((15.0, -53.5, G + 0.05), 2.4, 2.4, 0.6, "decal_litter", flat=True)


# --- the mill ---------------------------------------------------------------------------------

MILL_Y = -128.0                                   # its north face, about 70 m past the end of Mill Road


def mill(coll="ground"):
    """The Halden mill as distant geometry: enough for a true silhouette and for clear weather."""
    rng = random.Random(1887)
    mb = MeshBuilder()
    brick = (0.55, 0.50, 0.47)
    z0 = G - 0.5

    def block(x0, y0, x1, y1, h, floors, bays, colour=brick):
        mb.grime = _grime(z0, 6.0, 0.25)
        mb.box((x0, y0, z0), (x1, y1, z0 + h), "brick", color=colour, skip="-z")
        mb.grime = None
        # tall arched-head mill windows on the faces we can see: dark, a few still glazed
        fh = (h - 1.5) / floors
        for face, a0, a1, fixed in (("n", x0, x1, y1), ("w", y0, y1, x0), ("e", y0, y1, x1)):
            n = max(1, int((a1 - a0) / bays))
            step = (a1 - a0) / n
            for i in range(n):
                for f in range(floors):
                    c = a0 + step * (i + 0.5)
                    zb = z0 + 1.6 + f * fh
                    zt = zb + fh * 0.62
                    w = step * 0.42
                    mat = "glass_dirty" if rng.random() < 0.25 else "interior_dark"
                    if face == "n":
                        q = [Vector((c + w, fixed + 0.05, zb)), Vector((c - w, fixed + 0.05, zb)), Vector((c - w, fixed + 0.05, zt)),
                             Vector((c + w, fixed + 0.05, zt))]
                    elif face == "w":
                        q = [Vector((fixed - 0.05, c + w, zb)), Vector((fixed - 0.05, c - w, zb)), Vector((fixed - 0.05, c - w, zt)),
                             Vector((fixed - 0.05, c + w, zt))]
                    else:
                        q = [Vector((fixed + 0.05, c - w, zb)), Vector((fixed + 0.05, c + w, zb)), Vector((fixed + 0.05, c + w, zt)),
                             Vector((fixed + 0.05, c - w, zt))]
                    mb.face(q, mat)

    # the weaving shed: long and low, under a sawtooth roof whose glass faces north
    sx0, sx1 = -44.0, 38.0
    sy0, sy1 = MILL_Y - 26.0, MILL_Y
    sh = 11.0
    block(sx0, sy0, sx1, sy1, sh, 2, 4.6)
    teeth = 7
    span = (sy1 - sy0) / teeth
    for t in range(teeth):
        ya, yb = sy0 + t * span, sy0 + (t + 1) * span
        top = z0 + sh + 3.4
        mb.face([Vector((sx0, ya, z0 + sh)), Vector((sx1, ya, z0 + sh)), Vector((sx1, yb, top)), Vector((sx0, yb, top))],
                "roof_slate", color=(0.7, 0.7, 0.7))
        mb.face([Vector((sx1, yb, z0 + sh)), Vector((sx0, yb, z0 + sh)), Vector((sx0, yb, top)), Vector((sx1, yb, top))],
                "glass_dirty")
        for x in (sx0, sx1):
            tri = [Vector((x, ya, z0 + sh)), Vector((x, yb, z0 + sh)), Vector((x, yb, top))]
            mb.face(tri if x == sx1 else list(reversed(tri)), "brick", color=brick)
    # the four-storey spinning block and its stair tower
    block(-12.0, MILL_Y - 2.0, 20.0, MILL_Y + 14.0, 19.0, 4, 4.0, mul(brick, 0.95))
    block(20.0, MILL_Y + 3.0, 27.0, MILL_Y + 10.0, 26.0, 5, 3.4, mul(brick, 0.9))
    mb.box((19.6, MILL_Y + 2.6, z0 + 26.0), (27.4, MILL_Y + 10.4, z0 + 27.0), "brick", color=mul(brick, 0.8))
    # water tank on the roof
    tx, ty, tz = 2.0, MILL_Y + 6.0, z0 + 19.0
    for dx, dy in ((-1.6, -1.6), (1.6, -1.6), (1.6, 1.6), (-1.6, 1.6)):
        mb.tube([(tx + dx, ty + dy, tz), (tx + dx * 0.8, ty + dy * 0.8, tz + 4.0)], 0.12, "metal_rust", segments=5)
    mb.cylinder((tx, ty, tz + 4.0), (0, 0, 4.2), 2.3, "wood_weathered", segments=14, color=(0.55, 0.5, 0.45))
    mb.cylinder((tx, ty, tz + 8.2), (0, 0, 1.6), 2.4, "metal_rust", segments=14, radius_top=0.2, color=(0.5, 0.48, 0.46))
    # the stack
    cx, cy = -30.0, MILL_Y + 8.0
    mb.box((cx - 3.0, cy - 3.0, z0), (cx + 3.0, cy + 3.0, z0 + 6.0), "brick", color=mul(brick, 0.9), skip="-z")
    mb.cylinder((cx, cy, z0 + 6.0), (0, 0, 40.0), 2.3, "brick", segments=16, radius_top=1.5, color=mul(brick, 0.85))
    mb.cylinder((cx, cy, z0 + 46.0), (0, 0, 1.2), 1.75, "brick", segments=16, color=mul(brick, 0.7))
    # a boiler house against it and a long loading shed towards the town
    block(-40.0, MILL_Y + 2.0, -34.0, MILL_Y + 14.0, 9.0, 1, 4.0, mul(brick, 0.9))
    mb.box((-10.0, MILL_Y + 14.0, z0), (16.0, MILL_Y + 20.0, z0 + 5.0), "roof_tin", color=(0.7, 0.68, 0.64), skip="-z",
           mats={"+z": "roof_tin"})
    obj = mb.build("backdrop_mill", coll)
    obj["what"] = "The Halden mill, closed"
    # bare ground and a broken fence line between the town and the mill
    gm = MeshBuilder()
    gm.face([Vector((-60.0, MILL_Y - 40.0, z0 + 0.45)), Vector((60.0, MILL_Y - 40.0, z0 + 0.45)), Vector((60.0, plan.BUILD[1], z0 + 0.45)),
             Vector((-60.0, plan.BUILD[1], z0 + 0.45))], "lawn_dead", color=(0.42, 0.40, 0.33))
    gm.build("backdrop_mill_ground", coll)
    return obj
