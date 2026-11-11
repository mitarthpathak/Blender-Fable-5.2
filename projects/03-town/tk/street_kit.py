"""Street kit: ground, roads, curbs and sidewalks, road damage and markings,
telephone poles with catenary wires, sodium streetlights, fences, small
props, bare trees, abandoned cars, edge blockers, and the collision-only
helpers the game needs (curb and step ramps, edge walls).

Repeated props (poles, lamp heads, mailboxes, cans, manholes, trees, leaf
piles, barriers) are one mesh each, placed as linked duplicates, so the
.glb stores each mesh once and Godot can draw them as instances.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, collection, instance, jitter_color, lerp, light, mul

G = plan.GROUND
SW = plan.SIDEWALK_Z
RD = plan.ROAD_Z
_meshes: dict[str, bpy.types.Mesh] = {}


def shared(key: str, make) -> bpy.types.Mesh:
    """Build a kit mesh once and reuse it."""
    if key not in _meshes:
        mb = make()
        _meshes[key] = mb.build_mesh("kit_" + key)
    return _meshes[key]


def grid_quads(mb: MeshBuilder, rect, z, mat, cell, colour_fn):
    x0, y0, x1, y1 = rect
    nx, ny = max(1, round((x1 - x0) / cell)), max(1, round((y1 - y0) / cell))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    for i in range(nx):
        for j in range(ny):
            pts = [Vector((xs[i], ys[j], z)), Vector((xs[i + 1], ys[j], z)), Vector((xs[i + 1], ys[j + 1], z)),
                   Vector((xs[i], ys[j + 1], z))]
            mb.face(pts, mat)
            mb.cols[-1] = [(*colour_fn(p), 1.0) for p in pts]


# --- Ground, roads, sidewalks ----------------------------------------------------

POTHOLE_DEPTH = 0.075


class Sectors:
    """Flat detail split into 24 m squares, one object each, so Godot can cull
    and fade it by distance instead of drawing the whole town's decals at once."""

    SIZE = 24.0

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.cells: dict[tuple[int, int], MeshBuilder] = {}

    def at(self, x: float, y: float) -> MeshBuilder:
        key = (math.floor(x / self.SIZE), math.floor(y / self.SIZE))
        if key not in self.cells:
            self.cells[key] = MeshBuilder()
        return self.cells[key]

    def build(self, coll: str):
        for (i, j), mb in sorted(self.cells.items()):
            if not mb.empty():
                mb.build(f"{self.prefix}_{i + 8}_{j + 8}", coll)


def road_with_potholes(mb: MeshBuilder, rect, cell, colour_fn):
    """The road as a grid, with each pothole from the plan cut in as a real dip:
    the cells under it are replaced by a ring of asphalt, a broken rim and a
    bowl POTHOLE_DEPTH deep."""
    rng = random.Random(int(rect[0] * 7 + rect[1] * 13) & 0xFFFF)
    x0, y0, x1, y1 = rect
    nx, ny = max(1, round((x1 - x0) / cell)), max(1, round((y1 - y0) / cell))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    taken = set()
    holes = []
    for px, py, r in plan.POTHOLES:
        if not (x0 + 0.3 < px < x1 - 0.3 and y0 + 0.3 < py < y1 - 0.3):
            continue
        i0 = max(0, min(nx - 1, int((px - r - 0.25 - x0) / (x1 - x0) * nx)))
        i1 = max(0, min(nx - 1, int((px + r + 0.25 - x0) / (x1 - x0) * nx)))
        j0 = max(0, min(ny - 1, int((py - r - 0.25 - y0) / (y1 - y0) * ny)))
        j1 = max(0, min(ny - 1, int((py + r + 0.25 - y0) / (y1 - y0) * ny)))
        cells = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)}
        if cells & taken:
            continue
        taken |= cells
        holes.append((px, py, r, i0, i1, j0, j1))

    def face(pts, mat, tint=1.0):
        mb.face(pts, mat)
        mb.cols[-1] = [(*mul(colour_fn(p), tint), 1.0) for p in pts]

    for i in range(nx):
        for j in range(ny):
            if (i, j) not in taken:
                face([Vector((xs[i], ys[j], RD)), Vector((xs[i + 1], ys[j], RD)), Vector((xs[i + 1], ys[j + 1], RD)),
                      Vector((xs[i], ys[j + 1], RD))], "road")
    for px, py, r, i0, i1, j0, j1 in holes:
        # the rectangle of grid points round the removed cells
        loop = [Vector((xs[i], ys[j0], RD)) for i in range(i0, i1 + 1)]
        loop += [Vector((xs[i1 + 1], ys[j], RD)) for j in range(j0, j1 + 1)]
        loop += [Vector((xs[i], ys[j1 + 1], RD)) for i in range(i1 + 1, i0, -1)]
        loop += [Vector((xs[i0], ys[j], RD)) for j in range(j1 + 1, j0, -1)]
        n = 14
        rim, bowl = [], []
        for k in range(n):
            a = 2 * math.pi * k / n
            rr = r * rng.uniform(0.82, 1.18)
            rim.append(Vector((px + math.cos(a) * rr, py + math.sin(a) * rr, RD)))
            bowl.append(Vector((px + math.cos(a) * rr * 0.62, py + math.sin(a) * rr * 0.62,
                                RD - POTHOLE_DEPTH * rng.uniform(0.7, 0.95))))

        def ang(v):
            return math.atan2(v.y - py, v.x - px)
        A = sorted(loop, key=ang)
        B = sorted(rim, key=ang)
        aa = [ang(v) for v in A] + [ang(A[0]) + 2 * math.pi]
        bb = [ang(v) for v in B] + [ang(B[0]) + 2 * math.pi]
        i = j = 0
        while i < len(A) or j < len(B):                 # zip the two loops together by angle
            if i < len(A) and (j >= len(B) or aa[i + 1] <= bb[j + 1]):
                face([A[i], A[(i + 1) % len(A)], B[j % len(B)]], "road")
                i += 1
            else:
                face([A[i % len(A)], B[(j + 1) % len(B)], B[j]], "road")
                j += 1
        bowl_s = sorted(bowl, key=ang)
        for k in range(n):
            k2 = (k + 1) % n
            face([B[k], B[k2], bowl_s[k2], bowl_s[k]], "road_patch", 0.55)          # broken edge
            face([bowl_s[k], bowl_s[k2], Vector((px, py, RD - POTHOLE_DEPTH))], "road_patch", 0.4)

def ground(coll="ground"):
    rng = random.Random(5)
    noise = {}

    def n(p, scale=1.0):
        key = (round(p.x, 2), round(p.y, 2))
        if key not in noise:
            noise[key] = rng.uniform(0.82, 1.08)
        return noise[key]

    lawn = MeshBuilder()
    # lawns lot by lot, then everything else in the build area as overgrown verge
    covered = []
    for lot in plan.LOTS:
        mat = "lawn_leafy" if lot.key == "L7" else {"kept": "lawn_kept", "overgrown": "lawn_overgrown", "dead": "lawn_dead"}[lot.lawn]
        tint = (0.50, 0.48, 0.38) if mat == "lawn_dead" else (0.85, 0.85, 0.80)   # damp, not bleached
        grid_quads(lawn, lot.rect, G, mat, 2.0, lambda p, t=tint: mul(t, n(p)))
        covered.append(lot.rect)
    bx0, by0, bx1, by1 = plan.BUILD
    # verge strips: north of the north lots, the corners outside the lots, south of Mill lots
    verge = [
        (bx0, plan.ASHGROVE.road[3] + plan.SIDEWALK_W, -21.0, by1),
        (28.0, plan.ASHGROVE.road[3] + plan.SIDEWALK_W, bx1, by1),
        (-21.0, 18.0, 28.0, by1),
        (bx0, by0, -20.0, plan.ASHGROVE.road[1] - plan.SIDEWALK_W),
        (27.0, by0, bx1, plan.ASHGROVE.road[1] - plan.SIDEWALK_W),
        (-20.0, by0, plan.MILL.road[0] - plan.SIDEWALK_W, -58.0),
        (plan.MILL.road[2] + plan.SIDEWALK_W, by0, 27.0, -58.0),
        (-20.0, -40.0, plan.MILL.road[0] - plan.SIDEWALK_W, -40.0),
    ]
    for r in verge:
        if r[2] - r[0] > 0.1 and r[3] - r[1] > 0.1:
            grid_quads(lawn, r, G, "lawn_overgrown", 3.0, lambda p: (n(p) * 0.9,) * 3)
    # gaps between the lots and the sidewalks on Mill Road
    lawn.build("ground_lawns", coll)

    road = MeshBuilder()

    def road_col(p):
        # darker, damper towards the curbs; lighter wheel tracks
        c = 0.85 * n(p)
        return (c, c * 1.0, c * 1.03)
    road_with_potholes(road, plan.ASHGROVE.road, 3.0, road_col)
    mill = plan.MILL.road
    road_with_potholes(road, (mill[0], mill[1], mill[2], plan.ASHGROVE.road[1]), 3.0, road_col)
    road.build("ground_road", coll)

    side = MeshBuilder()
    for key, r in plan.SIDEWALKS:
        grid_quads(side, r, SW, "sidewalk", 2.0, lambda p: (0.92 * n(p),) * 3)
        x0, y0, x1, y1 = r
        # the 5 cm step down to the lawn on the far side from the road
        if key == "ashgrove_n":
            side.quad((x1, y1, G), (x0, y1, G), (x0, y1, SW), (x1, y1, SW), "concrete")
        elif key.startswith("ashgrove_s"):
            side.quad((x0, y0, G), (x1, y0, G), (x1, y0, SW), (x0, y0, SW), "concrete")
        elif key == "mill_w":
            side.quad((x0, y1, G), (x0, y0, G), (x0, y0, SW), (x0, y1, SW), "concrete")
        else:
            side.quad((x1, y0, G), (x1, y1, G), (x1, y1, SW), (x1, y0, SW), "concrete")
    # curbs: a granite-grey concrete kerb along every road edge
    ag, mr = plan.ASHGROVE.road, plan.MILL.road
    curbs = [((ag[0], ag[3]), (ag[2], ag[3]), -1), ((ag[0], ag[1]), (mr[0], ag[1]), 1),
             ((mr[2], ag[1]), (ag[2], ag[1]), 1), ((mr[0], mr[1]), (mr[0], ag[1]), 1),
             ((mr[2], mr[1]), (mr[2], ag[1]), -1)]
    for (ax, ay), (bx, by), s in curbs:
        if ay == by:          # runs along x; s = -1: road is below (south), +1: road is above (north)
            yf = ay
            yb = ay + (plan.CURB_W if s < 0 else -plan.CURB_W)
            side.quad((ax, yf, RD), (bx, yf, RD), (bx, yf, SW), (ax, yf, SW), "concrete",
                      color=(0.8, 0.8, 0.78)) if s > 0 else \
                side.quad((bx, yf, RD), (ax, yf, RD), (ax, yf, SW), (bx, yf, SW), "concrete", color=(0.8, 0.8, 0.78))
            side.quad((ax, min(yf, yb), SW + 0.003), (bx, min(yf, yb), SW + 0.003), (bx, max(yf, yb), SW + 0.003),
                      (ax, max(yf, yb), SW + 0.003), "concrete", color=(0.85, 0.85, 0.83))
        else:                 # runs along y; s = +1: road to the east, -1: road to the west
            xf = ax
            xb = ax - plan.CURB_W * s * -1 if False else ax + (-plan.CURB_W if s > 0 else plan.CURB_W)
            if s > 0:
                side.quad((xf, by, RD), (xf, ay, RD), (xf, ay, SW), (xf, by, SW), "concrete", color=(0.8, 0.8, 0.78))
            else:
                side.quad((xf, ay, RD), (xf, by, RD), (xf, by, SW), (xf, ay, SW), "concrete", color=(0.8, 0.8, 0.78))
            side.quad((min(xf, xb), ay, SW + 0.003), (max(xf, xb), ay, SW + 0.003), (max(xf, xb), by, SW + 0.003),
                      (min(xf, xb), by, SW + 0.003), "concrete", color=(0.85, 0.85, 0.83))
    # front paths: the player's house, and each kit house from its steps to the sidewalk
    x0, y0, x1, y1 = plan.HOUSE_FRONT_PATH
    side.box((x0, y0, G), (x1, y1, G + 0.025), "concrete", skip="-z", color=(0.82, 0.8, 0.76))
    side.build("ground_sidewalks", coll)
    return curbs


def house_paths(houses, coll="ground"):
    """Concrete walks from each kit house's steps to the sidewalk."""
    mb = MeshBuilder()
    for key, (obj, m, ramps, steps) in houses.items():
        sx0, sx1, sy = steps
        lot = next(l for l in plan.LOTS if l.key == key)
        lx0, ly0, lx1, ly1 = lot.rect
        # local path from the steps forward to the lot front, in the house frame
        a = m @ Vector(((sx0 + sx1) / 2, sy, 0))
        h = lot.house
        if h.facing == "s":
            b = Vector((a.x, ly0, 0))
        elif h.facing == "n":
            b = Vector((a.x, ly1, 0))
        else:
            b = Vector((lx1, a.y, 0))
        w = 0.6
        if abs(a.x - b.x) < 1e-3:
            mb.box((a.x - w, min(a.y, b.y), G), (a.x + w, max(a.y, b.y), G + 0.025), "concrete", skip="-z",
                   color=(0.78, 0.76, 0.72))
        else:
            mb.box((min(a.x, b.x), a.y - w, G), (max(a.x, b.x), a.y + w, G + 0.025), "concrete", skip="-z",
                   color=(0.78, 0.76, 0.72))
    mb.build("ground_paths", coll)


def _surface_z(x, y):
    if _on_road(x, y):
        return RD
    if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for _, r in plan.SIDEWALKS):
        return SW
    return G


def curb_lines():
    """Every kerb as (start, end, side): the joint where weeds, moss and wet leaves collect."""
    ag, mr = plan.ASHGROVE.road, plan.MILL.road
    return [((ag[0], ag[3]), (ag[2], ag[3]), "n"), ((ag[0], ag[1]), (mr[0], ag[1]), "s"),
            ((mr[2], ag[1]), (ag[2], ag[1]), "s"), ((mr[0], mr[1]), (mr[0], ag[1]), "w"),
            ((mr[2], mr[1]), (mr[2], ag[1]), "e")]


def _weed(seed):
    rng = random.Random(seed)
    mb = MeshBuilder()
    for k in range(2):
        a = rng.uniform(0, math.pi) + k * math.pi / 2
        mb.card((0, 0, 0), rng.uniform(0.28, 0.42), rng.uniform(0.26, 0.44), a, "weed_card",
                color=jitter_color(rng, (0.9, 0.9, 0.85), 0.12))
    return mb


def road_damage(coll="ground_detail"):
    rng = random.Random(9)
    mb = MeshBuilder()
    for x0, y0, x1, y1 in plan.PATCHES:
        z = RD + 0.004
        mb.quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), "road_patch", color=(0.7, 0.7, 0.72))
    mb.build("road_patches", coll)

    # markings: faded double yellow on Ashgrove, dashed centre on Mill Road, a stop line
    mk = MeshBuilder()
    ag = plan.ASHGROVE
    z = RD + 0.006

    def strip(x0, y0, x1, y1, mat, along_x=True):
        length = (x1 - x0) if along_x else (y1 - y0)
        mk.face([Vector((x0, y0, z)), Vector((x1, y0, z)), Vector((x1, y1, z)), Vector((x0, y1, z))], mat,
                uvs=[(0, 0), (0, length), (1, length), (1, 0)] if along_x else [(0, 0), (1, 0), (1, length), (0, length)])
    for xa, xb in ((plan.BUILD[0], plan.MILL.road[0] - 1.0), (plan.MILL.road[2] + 1.0, plan.BUILD[2])):
        for off in (0.07, -0.17):
            strip(xa, ag.centre + off, xb, ag.centre + off + 0.10, "paint_marking")
    y = plan.ASHGROVE.road[1] - 3.0
    while y > plan.BUILD[1]:
        strip(plan.MILL.centre - 0.05, y - 3.0, plan.MILL.centre + 0.05, y, "paint_marking", along_x=False)
        y -= 9.0
    x0, x1, ys = plan.STOP_LINE
    strip(x0, ys - 0.2, x1, ys + 0.2, "paint_white")
    mk.build("road_markings", coll)

    dc = Sectors("decals")
    for x, y, r in plan.PUDDLES:
        zz = _surface_z(x, y)
        dc.at(x, y).card((x, y, zz + (0.03 if zz == G else 0.008)), r * 2, r * 2 * rng.uniform(0.6, 0.9),
                         rng.uniform(0, math.pi), "puddle", flat=True)
    for x, y, r in plan.POTHOLES:                        # standing water in the bottom of each dip
        dc.at(x, y).card((x, y, RD - POTHOLE_DEPTH * 0.42), r * 1.9, r * 1.9, rng.uniform(0, math.pi), "puddle",
                         flat=True)
    cracks = []
    for _ in range(34):
        _, r = plan.SIDEWALKS[rng.randrange(len(plan.SIDEWALKS))]
        x, y = rng.uniform(r[0], r[2]), rng.uniform(r[1], r[3])
        if abs(x) > 34 or y < -56:
            continue
        cracks.append((x, y))
        dc.at(x, y).card((x, y, SW + 0.005), rng.uniform(0.8, 1.6), rng.uniform(0.6, 1.4), rng.uniform(0, math.pi),
                         "decal_crack", flat=True)
    for _ in range(14):
        x, y = rng.uniform(-25, 33), rng.uniform(-17.5, -10.8)
        dc.at(x, y).card((x, y, RD + 0.007), rng.uniform(0.8, 1.8), rng.uniform(0.6, 1.2), rng.uniform(0, math.pi),
                         "decal_oil", flat=True)
    hot = [(plan.HOUSE_DOOR_X, -9.5, 7.0), (3.5, -16.0, 9.0), (3.5, -24.0, 6.0)]
    for i in range(110):
        if i < 80:
            hx, hy, hr = hot[i % len(hot)]
            x, y = hx + rng.uniform(-hr, hr), hy + rng.uniform(-hr * 0.6, hr * 0.6)
        else:
            x, y = rng.uniform(-28, 36), rng.uniform(-17.8, -8.7)
        zz = _surface_z(x, y)
        dc.at(x, y).card((x, y, zz + (0.012 if zz == G else 0.007)), rng.uniform(0.9, 2.2), rng.uniform(0.9, 2.2),
                         rng.uniform(0, math.pi), "decal_leaves", flat=True)

    # moss and dirt packed into the joints: along each kerb, and across the sidewalk slabs
    weeds = [shared(f"weed_{k}", lambda k=k: _weed(k)) for k in range(3)]
    spots = []
    for (ax, ay), (bx, by), side in curb_lines():
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        inward = {"n": (0, 1), "s": (0, -1), "w": (-1, 0), "e": (1, 0)}[side]     # from the road towards the sidewalk
        rot = math.atan2(uy, ux) - math.pi / 2
        t = rng.uniform(0, 2)
        while t < length:
            seg = rng.uniform(0.8, 2.4)
            x, y = ax + ux * (t + seg / 2), ay + uy * (t + seg / 2)
            if abs(x) < 36 and y > -57 and rng.random() < 0.6:
                # in the gutter, at the foot of the kerb
                gx, gy = x - inward[0] * 0.06, y - inward[1] * 0.06
                dc.at(gx, gy).card((gx, gy, RD + 0.006), 0.16, seg, rot, "decal_moss_strip", flat=True,
                                   uvs=((0, 0), (1, 0), (1, seg), (0, seg)))
                if rng.random() < 0.45:                  # and in the joint behind the kerb stone
                    jx, jy = x + inward[0] * plan.CURB_W, y + inward[1] * plan.CURB_W
                    dc.at(jx, jy).card((jx, jy, SW + 0.006), 0.10, seg, rot, "decal_moss_strip", flat=True,
                                       uvs=((0, 0), (1, 0), (1, seg), (0, seg)))
                for _ in range(rng.randint(0, 2)):       # weeds rooted in the same joints
                    w = rng.uniform(-seg / 2, seg / 2)
                    back = rng.choice((-0.04, plan.CURB_W + 0.01))
                    spots.append((x + ux * w + inward[0] * back, y + uy * w + inward[1] * back,
                                  RD if back < 0 else SW))
            t += seg + rng.uniform(0.3, 3.0)
        # joints across the slabs, every two metres (the pavement texture's slab length)
        t = 1.0
        while t < length:
            x, y = ax + ux * t, ay + uy * t
            if abs(x) < 36 and y > -57 and rng.random() < 0.3:
                cx, cy = x + inward[0] * (plan.SIDEWALK_W / 2 + 0.05), y + inward[1] * (plan.SIDEWALK_W / 2 + 0.05)
                dc.at(cx, cy).card((cx, cy, SW + 0.006), 0.09, plan.SIDEWALK_W - 0.3, math.atan2(uy, ux),
                                   "decal_moss_strip", flat=True, uvs=((0, 0), (1, 0), (1, 1.3), (0, 1.3)))
                if rng.random() < 0.5:
                    spots.append((cx + inward[0] * rng.uniform(-0.6, 0.6), cy + inward[1] * rng.uniform(-0.6, 0.6), SW))
            t += 2.0
    for x, y in cracks:                                  # weeds coming up through the cracks
        for _ in range(rng.randint(1, 3)):
            spots.append((x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.3, 0.3), SW))
    for i, (x, y, zz) in enumerate(spots):
        instance(weeds[i % 3], f"weed_{i}", "grass", (x, y, zz), rng.uniform(0, 6.28), scale=rng.uniform(0.6, 1.25))
    dc.build(coll)

    mh = shared("manhole", _manhole)
    for i, (x, y) in enumerate(plan.MANHOLES):
        instance(mh, f"manhole_{i}", coll, (x, y, RD), rng.uniform(0, math.pi))
    return dc


def _on_road(x, y):
    return any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in (s.road for s in plan.STREETS))


def _manhole():
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0.0), (0, 0, 0.012), 0.36, "manhole", segments=20, caps="top", uv_wrap=False)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.008), 0.42, "road_patch", segments=20, caps="none", uv_wrap=False)
    return mb


# --- Poles, wires, streetlights ------------------------------------------------------

def _pole_mesh():
    mb = MeshBuilder()
    mb.cylinder((0, 0, -0.2), (0, 0, 8.6), 0.15, "bark", segments=10, radius_top=0.10, color=(0.55, 0.5, 0.45))
    mb.box((-1.1, -0.05, 7.62), (1.1, 0.05, 7.76), "wood_weathered", color=(0.7, 0.66, 0.6))
    for x in (-0.9, 0.0, 0.9):
        mb.cylinder((x, 0, 7.76), (0, 0, 0.14), 0.04, "glass_dirty", segments=6)
    for x, z in ((-0.6, 7.3), (0.6, 7.3)):                       # cross-arm braces
        mb.tube([(0, 0.06, 6.9), (x, 0.06, 7.62)], 0.018, "metal_rust", segments=4)
    mb.box((-0.09, -0.08, 2.4), (0.09, -0.075, 2.7), "metal_rust")   # pole tag
    return mb


def _transformer():
    mb = MeshBuilder()
    mb.cylinder((0, -0.35, 6.2), (0, 0, 0.85), 0.24, "metal_painted", segments=10, color=(0.55, 0.57, 0.55))
    mb.box((-0.06, -0.16, 6.5), (0.06, -0.1, 6.8), "metal_rust")
    return mb


def _lamp_mesh(state):
    """Cobra-head sodium lamp on a curved arm reaching +X from the pole."""
    mb = MeshBuilder()
    mb.tube([(0.12, 0, 6.1), (0.8, 0, 6.55), (1.6, 0, 6.68)], 0.035, "metal_painted", segments=6,
            color=(0.5, 0.5, 0.48))
    mb.box((0.06, -0.06, 6.0), (0.14, 0.06, 6.25), "metal_painted", color=(0.5, 0.5, 0.48))
    mb.obox((1.85, 0, 6.68), (0.62, 0.28, 0.13), 0.0, "metal_painted", color=(0.5, 0.5, 0.48), tilt=(0.0, -0.08))
    if state != "broken":
        mb.obox((1.87, 0, 6.605), (0.48, 0.22, 0.03), 0.0, "sodium_on" if state != "off" else "sodium_off",
                tilt=(0.0, -0.08))
    else:
        mb.obox((1.87, 0, 6.61), (0.48, 0.22, 0.02), 0.0, "interior_dark", tilt=(0.0, -0.08))
        mb.face([Vector((1.65, -0.11, 6.6)), Vector((1.8, -0.11, 6.6)), Vector((1.7, -0.11, 6.5))], "glass_dirty")
    return mb


def poles(coll="poles"):
    pm = shared("pole", _pole_mesh)
    tm = shared("transformer", _transformer)
    by_key = {p.key: p for p in plan.POLES}
    lamps = {}
    tops = {}
    for p in plan.POLES:
        # cross-arm across the wires: face the average wire direction
        dirs = []
        for a, b in plan.WIRES:
            if p.key in (a, b):
                o = by_key[b if a == p.key else a]
                dirs.append(Vector((o.x - p.x, o.y - p.y)).normalized())
        d = dirs[0] if dirs else Vector((1, 0))
        if len(dirs) > 1 and dirs[0].dot(dirs[1]) < 0:
            d = (dirs[0] - dirs[1]).normalized()
        rot = math.atan2(d.y, d.x) + math.pi / 2          # arm along local X, wires along local Y
        base = Vector((p.x, p.y, SW))
        instance(pm, f"pole_{p.key}", coll, base, rot)
        if p.key in ("P2", "P5"):
            instance(tm, f"pole_{p.key}_transformer", coll, base, rot)
        tops[p.key] = (base, rot)
        if p.lamp:
            state = {"on": "on", "flicker": "on", "broken": "broken"}[p.lamp]
            lm = shared("lamp_" + state, lambda s=state: _lamp_mesh(s))
            arm_rot = math.atan2(p.arm[1], p.arm[0])
            instance(lm, f"streetlamp_{p.key}", coll, base, arm_rot)
            head = base + Vector((math.cos(arm_rot) * 1.87, math.sin(arm_rot) * 1.87, 6.58))
            name = f"street_sodium_{p.key}" + ("_flicker" if p.lamp == "flicker" else "")
            if p.lamp != "broken":
                lamps[p.key] = light(name, head, "point", 250.0, (1.0, 0.55, 0.2), radius=0.15)
            else:
                e = bpy.data.objects.new(f"street_sodium_{p.key}_broken", None)   # marks the dead lamp
                e.location = head
                collection("lights").objects.link(e)
    return tops, lamps


def _catenary(a: Vector, b: Vector, sag: float, n=18):
    """Points of a hanging cable from a to b with mid-span sag (true catenary)."""
    span = Vector((b.x - a.x, b.y - a.y)).length
    if span < 0.01:
        return [a, b]
    # solve a*(cosh(L/2a)-1) = sag for the catenary parameter
    lo, hi = 0.01, 1e5
    for _ in range(80):
        c = (lo + hi) / 2
        if c * (math.cosh(span / (2 * c)) - 1) > sag:
            lo = c
        else:
            hi = c
    c = (lo + hi) / 2
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (t - 0.5) * span
        drop = sag - c * (math.cosh(x / c) - 1)
        p = a.lerp(b, t)
        pts.append(Vector((p.x, p.y, p.z - drop)))
    return pts


def wires(tops, coll="poles"):
    mb = MeshBuilder()
    for ka, kb in plan.WIRES:
        (ba, ra), (bb, rb) = tops[ka], tops[kb]
        span = (Vector((bb.x - ba.x, bb.y - ba.y))).length
        for x in (-0.9, 0.0, 0.9):
            pa = ba + Matrix.Rotation(ra, 3, "Z") @ Vector((x, 0, 7.9))
            pb = bb + Matrix.Rotation(rb, 3, "Z") @ Vector((x, 0, 7.9))
            # keep conductors parallel: pair the arm ends that face the same side
            if (Matrix.Rotation(ra, 3, "Z") @ Vector((1, 0, 0))).dot(Matrix.Rotation(rb, 3, "Z") @ Vector((1, 0, 0))) < 0:
                pb = bb + Matrix.Rotation(rb, 3, "Z") @ Vector((-x, 0, 7.9))
            mb.tube(_catenary(pa, pb, span * plan.WIRE_SAG * (1.0 + 0.15 * x)), 0.011, "wire", segments=4)
        # a lower telephone cable
        pa = ba + Vector((0, 0, 6.0))
        pb = bb + Vector((0, 0, 6.0))
        mb.tube(_catenary(pa, pb, span * plan.WIRE_SAG * 1.6), 0.02, "wire", segments=4)
    for key, x, y, z in plan.SERVICE_DROPS:
        b, r = tops[key]
        pa = b + Matrix.Rotation(r, 3, "Z") @ Vector((0.9, 0, 7.9))
        pb = Vector((x, y, z))
        mb.tube(_catenary(pa, pb, (pb - pa).length * 0.07), 0.009, "wire", segments=4)
    mb.build("wires", coll)


# --- Fences ----------------------------------------------------------------------------

def picket_run(mb, a, b, rng, gap=None, wear=0.4, colour=(0.95, 0.93, 0.88)):
    """Picket fence from a to b (plan points), with an optional gate gap centred at `gap`."""
    a, b = Vector((*a, 0)), Vector((*b, 0))
    d = b - a
    length = d.length
    u = d.normalized()
    rot = math.atan2(u.y, u.x)
    pieces = [(0.0, length)]
    if gap is not None:
        g = (Vector((*gap, 0)) - a).dot(u)
        pieces = [(0.0, g - 0.85), (g + 0.85, length)]
    for s0, s1 in pieces:
        if s1 - s0 < 0.3:
            continue
        for zr in (0.25, 0.72):
            c = a + u * ((s0 + s1) / 2)
            mb.obox((c.x, c.y, G + zr + 0.03), (s1 - s0, 0.04, 0.06), rot, "trim", color=mul(colour, 0.9))
        s = s0
        while s < s1:
            if rng.random() > 0.06 + 0.1 * wear:
                p = a + u * s
                h = 0.95 + rng.uniform(-0.03, 0.03)
                lean = rng.uniform(-0.06, 0.06) if rng.random() < wear * 0.3 else 0.0
                mb.obox((p.x, p.y, G + 0.04 + h / 2), (0.075, 0.025, h), rot, "trim",
                        color=jitter_color(rng, colour, 0.08), tilt=(lean, 0.0))
            s += 0.135
        for s in (s0, s1):
            p = a + u * s
            mb.obox((p.x, p.y, G + 0.54), (0.1, 0.1, 1.08), rot, "trim", color=mul(colour, 0.85))


def chainlink_run(mb, a, b, height=1.2):
    a, b = Vector((*a, G)), Vector((*b, G))
    d = b - a
    length = d.length
    n = max(1, int(length / 2.5))
    for i in range(n + 1):
        p = a.lerp(b, i / n)
        mb.cylinder(p, (0, 0, height + 0.05), 0.03, "metal_rust", segments=6, caps="top")
    mb.tube([a + Vector((0, 0, height)), b + Vector((0, 0, height))], 0.02, "metal_rust", segments=5)
    up = Vector((0, 0, height))
    mb.face([a + Vector((0, 0, 0.03)), b + Vector((0, 0, 0.03)), b + up, a + up], "chainlink",
            uvs=[(0, 0), (length, 0), (length, height), (0, height)])


def tall_fence_run(mb, a, b, rng, height=2.2):
    a, b = Vector((*a, G)), Vector((*b, G))
    d = b - a
    length = d.length
    u = d.normalized()
    nrm = Vector((-u.y, u.x, 0))
    rot = math.atan2(u.y, u.x)
    s = 0.0
    while s < length:
        w = min(0.15, length - s)
        p = a + u * (s + w / 2)
        h = height + rng.uniform(-0.04, 0.04)
        lean = rng.uniform(-0.015, 0.015)
        mb.obox((p.x, p.y, G + h / 2), (w - 0.006, 0.022, h), rot, "wood_weathered",
                color=jitter_color(rng, (0.8, 0.76, 0.7), 0.1), tilt=(lean, 0.0))
        s += 0.15
    n = max(1, int(length / 2.4))
    for i in range(n + 1):
        p = a.lerp(b, i / n) + nrm * 0.06
        mb.obox((p.x, p.y, G + height / 2), (0.09, 0.09, height + 0.05), rot, "wood_weathered", color=(0.6, 0.57, 0.52))
    for z in (0.35, height - 0.35):
        c = (a + b) / 2 + nrm * 0.05
        mb.obox((c.x, c.y, G + z), (length, 0.04, 0.09), rot, "wood_weathered", color=(0.62, 0.59, 0.54))


def fences(coll="fences"):
    rng = random.Random(21)
    pk, cl, tall = MeshBuilder(), MeshBuilder(), MeshBuilder()
    for lot in plan.LOTS:
        x0, y0, x1, y1 = lot.rect
        if lot.key in ("L1", "L2", "L3"):
            a, b, gap = (x0 + 0.1, y0 + 0.25), (x1 - 0.1, y0 + 0.25), (lot.gate_at, y0 + 0.25) if lot.gate_at else None
        elif lot.key in ("L4", "L5"):
            a, b, gap = (x0 + 0.1, y1 - 0.25), (x1 - 0.1, y1 - 0.25), (lot.gate_at, y1 - 0.25) if lot.gate_at else None
        else:
            a, b, gap = (x1 - 0.25, y0 + 0.1), (x1 - 0.25, y1 - 0.1), (x1 - 0.25, lot.gate_at) if lot.gate_at else None
        if lot.fence == "picket":
            wear = lot.house.wear if lot.house else 0.5
            picket_run(pk, a, b, rng, gap, wear)
        elif lot.fence == "chainlink":
            if gap is None:
                chainlink_run(cl, a, b)
            else:
                horizontal = abs(a[1] - b[1]) < 1e-6
                if horizontal:
                    chainlink_run(cl, a, (gap[0] - 0.9, a[1]))
                    chainlink_run(cl, (gap[0] + 0.9, a[1]), b)
                else:
                    chainlink_run(cl, a, (a[0], gap[1] - 0.9))
                    chainlink_run(cl, (a[0], gap[1] + 0.9), b)
    # the vacant lot: chain-link on its other sides too
    x0, y0, x1, y1 = next(l for l in plan.LOTS if l.key == "L7").rect
    chainlink_run(cl, (x0 + 0.2, y1 - 0.2), (x1 - 0.6, y1 - 0.2))
    chainlink_run(cl, (x0 + 0.2, y0 + 0.4), (x0 + 0.2, y1 - 0.2))
    # side yards: tall fences from each house's sides to its lot edges, and down the lot lines
    side_runs = [
        # north lots: the house front line + 1.5 m across to the lot boundary, then back to the rear fence
        ((-4.5, 1.2), (-0.3, 1.2)), ((7.6, 1.2), (11.5, 1.2)),
        ((-21.0, 1.0), (-16.6, 1.0)), ((-9.0, 1.0), (-4.5, 1.0)),
        ((11.5, 1.8), (15.0, 1.8)), ((24.2, 1.8), (28.0, 1.8)),
        ((-4.5, 1.2), (-4.5, 18.4)), ((11.5, 1.2), (11.5, 18.4)),
        ((-21.0, 1.0), (-21.0, 18.4)), ((28.0, 1.8), (28.0, 18.4)),
        # south corner lots
        ((-20.4, -28.5), (-14.8, -28.5)), ((-6.4, -28.5), (-1.6, -28.5)),
        ((8.6, -27.7), (13.0, -27.7)), ((20.4, -27.7), (27.4, -27.7)),
        ((-20.4, -40.0), (-1.6, -40.0)),
        # Mill Road west lot
        ((-7.7, -58.0), (-7.7, -53.4)), ((-7.7, -44.6), (-7.7, -40.0)),
        # behind the south corner lots
        ((8.6, -40.0), (27.4, -40.0)),
    ]
    for a, b in side_runs:
        tall_fence_run(tall, a, b, rng)
    for kind, x, y, heading, length in plan.BLOCKERS:
        if kind == "fence_tall":
            h = math.radians(heading)
            d = Vector((math.cos(h), math.sin(h))) * length / 2
            tall_fence_run(tall, (x - d.x, y - d.y), (x + d.x, y + d.y), rng, 2.4)
    pk.build("fence_pickets", coll)      # not "fence_picket": that is the house's own, removed in the town
    cl.build("fence_chainlink", coll)
    tall.build("fence_tall", coll)


# --- Small props -----------------------------------------------------------------------

def _mailbox():
    mb = MeshBuilder()
    mb.box((-0.045, -0.045, G - 0.1), (0.045, 0.045, G + 1.05), "wood_weathered", skip="-z", color=(0.6, 0.56, 0.5))
    mb.box((-0.11, -0.26, G + 1.05), (0.11, 0.22, G + 1.08), "wood_weathered", color=(0.6, 0.56, 0.5))
    mb.box((-0.09, -0.25, G + 1.08), (0.09, 0.22, G + 1.20), "metal_rust", color=(0.75, 0.73, 0.7))
    mb.cylinder((0, -0.25, G + 1.20), (0, 0.47, 0), 0.09, "metal_rust", segments=12, color=(0.75, 0.73, 0.7))
    mb.box((0.09, 0.05, G + 1.12), (0.10, 0.07, G + 1.32), "metal_painted", color=(0.6, 0.12, 0.08))
    return mb


def _trash_can():
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0.0), (0, 0, 0.85), 0.27, "metal_rust", segments=14, radius_top=0.30, caps="bottom",
                color=(0.62, 0.64, 0.6))
    mb.cylinder((0, 0, 0.85), (0, 0, 0.06), 0.32, "metal_rust", segments=14, color=(0.58, 0.6, 0.56))
    mb.box((-0.06, -0.02, 0.91), (0.06, 0.02, 0.96), "metal_rust")
    for z in (0.2, 0.5):
        mb.cylinder((0, 0, z), (0, 0, 0.03), 0.285, "metal_rust", segments=14, caps="none", color=(0.5, 0.5, 0.48))
    return mb


def _hydrant():
    mb = MeshBuilder()
    c = (0.55, 0.14, 0.1)
    mb.cylinder((0, 0, 0), (0, 0, 0.62), 0.11, "metal_painted", segments=12, color=c)
    mb.cylinder((0, 0, 0.62), (0, 0, 0.12), 0.12, "metal_painted", segments=12, radius_top=0.05, color=c)
    for a in (0, math.pi):
        mb.cylinder((math.cos(a) * 0.1, math.sin(a) * 0.1, 0.42), (math.cos(a) * 0.08, math.sin(a) * 0.08, 0), 0.045,
                    "metal_painted", segments=8, color=c)
    return mb


def _leaf_pile(seed):
    rng = random.Random(seed)
    mb = MeshBuilder()
    rings, segs = 4, 12
    r0 = rng.uniform(0.6, 0.9)
    hgt = rng.uniform(0.18, 0.3)
    pts = [[None] * segs for _ in range(rings + 1)]
    for i in range(rings + 1):
        t = i / rings
        for j in range(segs):
            a = 2 * math.pi * j / segs
            rr = r0 * (1 - t ** 1.6) * rng.uniform(0.85, 1.15)
            pts[i][j] = Vector((math.cos(a) * rr * 1.2, math.sin(a) * rr, hgt * math.sin(t * math.pi / 2)))
    for i in range(rings):
        for j in range(segs):
            k = (j + 1) % segs
            mb.face([pts[i][j], pts[i][k], pts[i + 1][k], pts[i + 1][j]], "leaves")
    return mb


def _grass_clump(seed):
    rng = random.Random(seed)
    mb = MeshBuilder()
    for _ in range(3):
        a = rng.uniform(0, math.pi)
        w, h = rng.uniform(0.5, 0.8), rng.uniform(0.35, 0.6)
        ox, oy = rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)
        mb.card((ox, oy, 0), w, h, a, "grass_card", color=jitter_color(rng, (0.9, 0.9, 0.85), 0.1))
    return mb


def props(coll="props"):
    rng = random.Random(33)
    mbm = shared("mailbox", _mailbox)
    for i, (x, y, rot) in enumerate(plan.MAILBOXES):
        instance(mbm, f"mailbox_{i}", coll, (x, y, 0), math.radians(rot) + rng.uniform(-0.15, 0.15),
                 tilt=(rng.uniform(-0.05, 0.05), 0))
    can = shared("trash_can", _trash_can)
    for i, (x, y, rot, state) in enumerate(plan.TRASH_CANS):
        z = SW if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for _, r in plan.SIDEWALKS) else G
        if state == "fallen":
            instance(can, f"trash_can_{i}", coll, (x, y, z + 0.29), math.radians(rot), tilt=(math.pi / 2, 0))
        else:
            instance(can, f"trash_can_{i}", coll, (x, y, z), math.radians(rot))
    hyd = shared("hydrant", _hydrant)
    for i, (x, y) in enumerate(plan.HYDRANTS):
        instance(hyd, f"hydrant_{i}", coll, (x, y, SW), 0.3)
    piles = [shared(f"leaf_pile_{k}", lambda k=k: _leaf_pile(k)) for k in range(3)]
    for i, (x, y) in enumerate(plan.LEAF_PILES):
        z = SW if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for _, r in plan.SIDEWALKS) else \
            (RD if _on_road(x, y) else G)
        instance(piles[i % 3], f"leaf_pile_{i}", coll, (x, y, z), rng.uniform(0, 6.28), scale=rng.uniform(0.8, 1.4))
    # grass along fences, foundations and the vacant lot
    clumps = [shared(f"grass_clump_{k}", lambda k=k: _grass_clump(k)) for k in range(3)]
    spots = []
    for lot in plan.LOTS:
        if lot.lawn == "kept":
            continue
        x0, y0, x1, y1 = lot.rect
        n = 40 if lot.key == "L7" else 18
        for _ in range(n):
            if lot.key in ("L1", "L2", "L3"):
                spots.append((rng.uniform(x0, x1), y0 + rng.uniform(0.3, 1.2)))
            elif lot.key in ("L4", "L5"):
                spots.append((rng.uniform(x0, x1), y1 - rng.uniform(0.3, 1.2)))
            else:
                spots.append((rng.uniform(x0, x1), rng.uniform(y0, y1)))
    for i, (x, y) in enumerate(spots):
        instance(clumps[i % 3], f"grass_{i}", "grass", (x, y, G), rng.uniform(0, 6.28), scale=rng.uniform(0.7, 1.3))
    # sale sign in L5's yard
    mb = MeshBuilder()
    mb.box((-0.03, -0.03, G), (0.03, 0.03, G + 1.2), "wood_weathered", skip="-z")
    mb.box((-0.03, -0.03, G + 1.0), (0.7, 0.03, G + 1.05), "wood_weathered")
    mb.card((0.36, -0.035, G + 0.62), 0.62, 0.34, 0.0, "sign_sale")
    mb.card((0.36, 0.035, G + 0.62), 0.62, 0.34, math.pi, "sign_sale", uvs=((1, 0), (0, 0), (0, 1), (1, 1)))
    o = mb.build("sign_for_sale", coll)
    o.location = (17.8, -22.0, 0)
    o.rotation_euler.z = math.radians(170)


# --- Trees ------------------------------------------------------------------------------

def _tree(seed, height=9.0):
    """A bare deciduous tree: tapered trunk and recursive, drooping branches."""
    rng = random.Random(seed)
    mb = MeshBuilder()

    def branch(p, d, length, radius, depth):
        pts, radii = [p], [radius]
        q = p.copy()
        dd = d.copy()
        n = 4
        for i in range(n):
            dd = (dd + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(-0.12, 0.08)))).normalized()
            q = q + dd * (length / n)
            pts.append(q.copy())
            radii.append(radius * (1 - (i + 1) / n * 0.65))
        mb.tube(pts, radius, "bark", segments=max(4, 8 - depth * 2), radii=radii, color=(0.62, 0.6, 0.56))
        if depth >= 4 or radius < 0.012:
            return
        kids = rng.randint(2, 3) if depth > 0 else rng.randint(3, 5)
        for k in range(kids):
            t = rng.uniform(0.45, 0.95)
            idx = min(len(pts) - 1, max(1, int(t * n)))
            base = pts[idx]
            ang = rng.uniform(0, 2 * math.pi)
            spread = rng.uniform(0.5, 0.95)
            nd = (dd * (1 - spread) + Vector((math.cos(ang), math.sin(ang), rng.uniform(0.2, 0.7))) * spread).normalized()
            branch(base, nd, length * rng.uniform(0.5, 0.72), radii[idx] * rng.uniform(0.5, 0.7), depth + 1)

    trunk_h = height * 0.38
    r = height * 0.026
    mb.tube([Vector((0, 0, -0.3)), Vector((0, 0, trunk_h * 0.5)), Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), trunk_h))],
            r, "bark", segments=9, radii=[r * 1.25, r, r * 0.85], color=(0.62, 0.6, 0.56))
    top = Vector((0, 0, trunk_h))
    for k in range(rng.randint(3, 4)):
        ang = 2 * math.pi * k / 4 + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(ang) * 0.6, math.sin(ang) * 0.6, 0.8)).normalized()
        branch(top, d, height * 0.42, r * 0.6, 1)
    return mb


def trees(coll="trees"):
    rng = random.Random(44)
    variants = [shared(f"tree_{k}", lambda k=k: _tree(200 + k)) for k in range(3)]
    for i, (x, y, h, seed) in enumerate(plan.TREES):
        instance(variants[seed % 3], f"tree_{i}", coll, (x, y, G), rng.uniform(0, 6.28), scale=h / 9.0)


# --- Cars --------------------------------------------------------------------------------

CAR_PAINTS = {"car_sedan": (0.30, 0.31, 0.33), "car_wagon": (0.33, 0.24, 0.16), "car_crashed": (0.18, 0.22, 0.27),
              "car_west": (0.40, 0.38, 0.33)}
# plan key: (body, state). Bodies are built in tk/cars.py.
CAR_KINDS = {"car_sedan": ("sedan", "abandoned"), "car_wagon": ("wagon", "on_blocks"),
             "car_crashed": ("pickup", "crashed"), "car_west": ("sedan", "crashed")}


def cars(coll="cars"):
    from . import cars as car_kit
    out = []
    for key, x, y, heading, _state in plan.CARS:
        kind, state = CAR_KINDS[key]
        o = car_kit.build(kind, CAR_PAINTS[key], sum(map(ord, key)), state, key, coll)
        o.location = (x, y, RD if _on_road(x, y) else G)
        o.rotation_euler.z = math.radians(heading)
        out.append(o)
    for kind, x, y, heading, _ in plan.BLOCKERS:
        if kind == "car_west":
            body, state = CAR_KINDS["car_west"]
            o = car_kit.build(body, CAR_PAINTS["car_west"], 77, state, "car_west", coll)
            o.location = (x, y, SW)
            o.rotation_euler = (0.04, -0.03, math.radians(heading))
            out.append(o)
    return out


# --- Edge blockers ------------------------------------------------------------------------

def _sawhorse():
    mb = MeshBuilder()
    for x in (-1.0, 1.0):
        for s in (-1, 1):
            mb.obox((x, s * 0.18, 0.5), (0.06, 0.05, 1.05), 0.0, "wood_weathered", tilt=(s * 0.33, 0.0),
                    color=(0.7, 0.66, 0.6))
    for z in (0.85, 0.55):
        n = 8
        for i in range(n):
            x0 = -1.1 + 2.2 * i / n
            col = (0.85, 0.83, 0.78) if i % 2 == 0 else (0.75, 0.32, 0.12)
            mb.box((x0, -0.03, z), (x0 + 2.2 / n, 0.03, z + 0.2), "trim", color=col)
    return mb


def _jersey():
    mb = MeshBuilder()
    prof = [(-0.30, 0.0), (0.30, 0.0), (0.27, 0.08), (0.12, 0.32), (0.08, 0.81), (-0.08, 0.81), (-0.12, 0.32),
            (-0.27, 0.08)]
    L = 2.0
    for i in range(len(prof)):
        a, b = prof[i], prof[(i + 1) % len(prof)]
        if i == 0:
            continue
        mb.face([Vector((-L / 2, a[0], a[1])), Vector((-L / 2, b[0], b[1])), Vector((L / 2, b[0], b[1])),
                 Vector((L / 2, a[0], a[1]))], "barrier_concrete", color=(0.85, 0.84, 0.8))
    for s in (-1, 1):
        pts = [Vector((s * L / 2, p[0], p[1])) for p in prof]
        mb.face(pts if s < 0 else list(reversed(pts)), "barrier_concrete", color=(0.8, 0.79, 0.75))
    return mb


def blockers(coll="blockers"):
    rng = random.Random(55)
    saw = shared("sawhorse", _sawhorse)
    jer = shared("jersey", _jersey)
    for i, (kind, x, y, heading, length) in enumerate(plan.BLOCKERS):
        h = math.radians(heading)
        z = RD if _on_road(x, y) else (SW if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for _, r in plan.SIDEWALKS) else G)
        if kind == "barrier":
            instance(saw, f"barrier_{i}", coll, (x, y, z), h)
        elif kind == "jersey":
            instance(jer, f"jersey_{i}", coll, (x, y, z), h + rng.uniform(-0.05, 0.05))
        elif kind == "sign_closed":
            mb = MeshBuilder()
            for px in (-0.7, 0.7):
                mb.box((px - 0.03, -0.03, 0.0), (px + 0.03, 0.03, 1.6), "metal_rust")
            mb.card((0, -0.035, 0.95), 1.3, 0.62, 0.0, "sign_closed")
            mb.card((0, 0.035, 0.95), 1.3, 0.62, math.pi, "sign_closed", uvs=((1, 0), (0, 0), (0, 1), (1, 1)))
            o = mb.build("sign_road_closed", coll)
            o.location = (x, y, z + 0.81 - 0.81)
            o.rotation_euler.z = h + math.pi
        elif kind == "fallen_tree":
            t = _tree(909, 13.0)
            o = t.build("fallen_tree", coll)
            o.location = (x - math.cos(h) * length * 0.45, y - math.sin(h) * length * 0.45, RD + 0.25)
            o.rotation_euler = (0.0, math.radians(84), h)
            # the trunk hits the road and the crown rests on the far side
            stump = MeshBuilder()
            stump.cylinder((0, 0, G - 0.1), (0, 0, 0.9), 0.36, "bark", segments=10, radius_top=0.33,
                           color=(0.62, 0.6, 0.56))
            stump.disc((0, 0, G + 0.8), 0.33, "wood_weathered", segments=10, color=(0.9, 0.82, 0.7))
            so = stump.build("fallen_tree_stump", coll)
            so.location = (x - math.cos(h) * length * 0.52, y - math.sin(h) * length * 0.52 + 0.2, 0)


# --- Collision helpers ---------------------------------------------------------------------

def wedge(mb: MeshBuilder, lo, hi, rise_dir: str):
    """A wedge filling the box lo..hi, top sloping up towards `rise_dir` ('+x','-x','+y','-y')."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    if rise_dir == "+y":
        top = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)]
        sides = [((x0, y0, z0), (x0, y1, z0), (x0, y1, z1)), ((x1, y0, z0), (x1, y1, z1), (x1, y1, z0))]
        back = [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    elif rise_dir == "-y":
        top = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z0), (x0, y1, z0)]
        sides = [((x0, y1, z0), (x0, y0, z1), (x0, y0, z0)), ((x1, y1, z0), (x1, y0, z0), (x1, y0, z1))]
        back = [(x1, y0, z0), (x0, y0, z0), (x0, y0, z1), (x1, y0, z1)]
    elif rise_dir == "+x":
        top = [(x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0)]
        sides = [((x0, y0, z0), (x1, y0, z0), (x1, y0, z1)), ((x0, y1, z0), (x1, y1, z1), (x1, y1, z0))]
        back = [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]
    else:
        top = [(x0, y0, z1), (x1, y0, z0), (x1, y1, z0), (x0, y1, z1)]
        sides = [((x1, y0, z0), (x0, y0, z1), (x0, y0, z0)), ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1))]
        back = [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)]
    mb.face(top, "concrete")
    for s in sides:
        mb.face(list(s), "concrete")
    mb.face(back, "concrete")
    mb.face([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], "concrete")


def collision(curbs, houses, coll="collision"):
    """Collision-only objects. Godot builds a static body from each and draws none of them:
    '-convcolonly' gives a convex shape, '-colonly' a trimesh."""
    col = collection(coll)
    k = 0
    # curb ramps: the player capsule cannot step a 13 cm kerb, so each kerb gets a gentle wedge
    for (ax, ay), (bx, by), s in curbs:
        if ay == by:
            length = bx - ax
            n = max(1, int(length / 16))
            for i in range(n):
                xa, xb = ax + length * i / n, ax + length * (i + 1) / n
                mb = MeshBuilder()
                if s < 0:   # road to the south of this kerb
                    wedge(mb, (xa, ay - 0.45, RD - 0.02), (xb, ay + 0.02, SW), "+y")
                else:
                    wedge(mb, (xa, ay - 0.02, RD - 0.02), (xb, ay + 0.45, SW), "-y")
                mb.build(f"curb_ramp_{k}-convcolonly", coll)
                k += 1
        else:
            length = by - ay
            n = max(1, int(length / 16))
            for i in range(n):
                ya, yb = ay + length * i / n, ay + length * (i + 1) / n
                mb = MeshBuilder()
                if s > 0:   # road to the east
                    wedge(mb, (ax - 0.02, ya, RD - 0.02), (ax + 0.45, yb, SW), "-x")
                else:
                    wedge(mb, (ax - 0.45, ya, RD - 0.02), (ax + 0.02, yb, SW), "+x")
                mb.build(f"curb_ramp_{k}-convcolonly", coll)
                k += 1
    # step ramps: the player's porch steps and each kit house's
    x0, y0, x1, y1 = (1.05, -3.14, 2.50, -2.30)      # through the noses of the house's two steps
    mb = MeshBuilder()
    wedge(mb, (x0, y0, G - 0.02), (x1, y1, -0.005), "+y")
    mb.build("steps_ramp_L1-convcolonly", coll)
    # The house's water-table board crosses its front doorway 14 cm above the floor
    # (exterior_trim, z -0.01..0.14 at y -0.33..-0.30). The house is not ours to edit,
    # so two small wedges let the player walk over it instead of being stopped by it.
    dx0, dx1 = plan.HOUSE_DOOR_X - 0.475, plan.HOUSE_DOOR_X + 0.475
    mb = MeshBuilder()
    wedge(mb, (dx0, -0.30, -0.02), (dx1, 0.32, 0.145), "-y")
    mb.build("door_sill_ramp_in-convcolonly", coll)
    mb = MeshBuilder()
    wedge(mb, (dx0, -0.85, -0.02), (dx1, -0.33, 0.145), "+y")
    mb.build("door_sill_ramp_out-convcolonly", coll)
    for key, (obj, m, ramps, steps) in houses.items():
        for j, (lo, hi) in enumerate(ramps):
            mb = MeshBuilder()
            wedge(mb, lo, hi, "+y")          # local frame: the porch is at +y of its steps
            world = MeshBuilder()
            world.extend(mb, m)
            world.build(f"steps_ramp_{key}_{j}-convcolonly", coll)
    # invisible walls on the edge of the walkable area
    wx0, wy0, wx1, wy1 = plan.WALK
    for name, lo, hi in (("w", (wx0 - 0.5, wy0, -1.0), (wx0, wy1, 4.0)), ("e", (wx1, wy0, -1.0), (wx1 + 0.5, wy1, 4.0)),
                         ("s", (wx0, wy0 - 0.5, -1.0), (wx1, wy0, 4.0)), ("n", (wx0, wy1, -1.0), (wx1, wy1 + 0.5, 4.0))):
        mb = MeshBuilder()
        mb.box(lo, hi, "concrete")
        mb.build(f"edge_wall_{name}-convcolonly", coll)
    # the fallen tree's trunk as a simple box
    for kind, x, y, heading, length in plan.BLOCKERS:
        if kind == "fallen_tree":
            mb = MeshBuilder()
            mb.obox((x, y, RD + 0.45), (length, 0.8, 1.0), math.radians(heading), "concrete")
            mb.build("fallen_tree_trunk-convcolonly", coll)
    return col
