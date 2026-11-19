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
from mathutils import Matrix, Vector, noise as _noise

import plan
from .core import MeshBuilder, collection, ground_grime, instance, jitter_color, lerp, light, mul

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

# --- uneven yards ---------------------------------------------------------------------------

LAWN_BUMP = 0.075        # metres: how far the yards rise and fall
LAWN_CELL = 0.75
# The player's lot comes from the house file: what must stay at lawn level there.
L1_FLAT = ((-0.3, -0.3, 7.6, 8.3), (0.08, -2.86, 3.92, -0.3), (0.9, -8.6, 2.7, -2.8), (1.0, 8.3, 2.6, 10.0),
           (3.3, 8.3, 7.6, 9.5), (8.2, 14.6, 11.3, 17.6), (3.7, 15.3, 7.5, 17.1), (-3.3, 11.1, -2.1, 16.5))
_FLAT: list | None = None
_HOUSES: list | None = None


def _zones():
    """Rectangles that stay flat: each house and its porch, the front path, and
    the house file's own yard pieces on L1."""
    global _FLAT, _HOUSES
    if _FLAT is None:
        _FLAT, _HOUSES = list(L1_FLAT), []          # (L1's lawn runs on under the house file's floor)
        for lot in plan.LOTS:
            h = lot.house
            if not h:
                continue
            (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)

            def rect(l0, m0, l1, m1):
                xs = [ox + ax * l + bx * m for l in (l0, l1) for m in (m0, m1)]
                ys = [oy + ay * l + by * m for l in (l0, l1) for m in (m0, m1)]
                return (min(xs), min(ys), max(xs), max(ys))
            house = rect(-0.3, -0.3, h.width + 0.3, h.depth + 0.3)
            _HOUSES.append(house)
            _FLAT.append(house)
            _FLAT.append(rect(h.door_at - 1.1, -3.3, h.door_at + 2.0, 0.0) if h.porch == "entry"
                         else rect(-0.4, -3.5, h.width + 0.4, 0.0))
            if h.porch == "wrap":
                _FLAT.append(rect(-0.4, 0.0, h.width + 0.4, h.depth * 0.6))
            door = rect(h.door_at + 0.45, -3.0, h.door_at + 0.45, -3.0)
            x0, y0, x1, y1 = lot.rect
            front = lot_front(lot)
            if front == "s":
                _FLAT.append((door[0] - 1.0, y0, door[0] + 1.0, door[1]))
            elif front == "n":
                _FLAT.append((door[0] - 1.0, door[1], door[0] + 1.0, y1))
            else:
                _FLAT.append((door[0], door[1] - 1.0, x1, door[1] + 1.0))
    return _FLAT


def lawn_offset(x: float, y: float) -> float:
    """How far the yard's surface is above lawn level (G) at x, y: soft rises and
    hollows a few centimetres deep, back to level at the lot edges, round the
    houses, porches and paths. Zero outside the lots."""
    lot = next((l for l in plan.LOTS if l.rect[0] <= x <= l.rect[2] and l.rect[1] <= y <= l.rect[3]), None)
    if lot is None:
        return 0.0
    x0, y0, x1, y1 = lot.rect
    d = min(x - x0, x1 - x, y - y0, y1 - y)
    for r in _zones():
        dx, dy = max(r[0] - x, 0.0, x - r[2]), max(r[1] - y, 0.0, y - r[3])
        d = min(d, math.hypot(dx, dy))
        if d <= 0.0:
            return 0.0
    t = min(1.0, d / 1.4)
    t = t * t * (3 - 2 * t)
    h = 0.62 * _noise.noise(Vector((x * 0.2, y * 0.2, 1.7))) + 0.38 * _noise.noise(Vector((x * 0.8, y * 0.8, 5.3)))
    return LAWN_BUMP * t * max(h, -0.2)


def lawn_grid(mb: MeshBuilder, lot, mat, tint, n):
    """A lot's lawn on a fine grid, following lawn_offset, with patches of bare
    earth and damp in the vertex colour. Cells under a house are left out."""
    _zones()
    x0, y0, x1, y1 = lot.rect
    nx, ny = max(1, round((x1 - x0) / LAWN_CELL)), max(1, round((y1 - y0) / LAWN_CELL))
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    pt = {(i, j): Vector((xs[i], ys[j], G + lawn_offset(xs[i], ys[j]))) for i in range(nx + 1) for j in range(ny + 1)}

    trails = _trails(lot)

    def colour(p):
        patch = _noise.noise(Vector((p.x * 0.16, p.y * 0.16, 9.1)))         # bare, trodden earth
        damp = _noise.noise(Vector((p.x * 0.5, p.y * 0.5, 3.3)))
        k = 1.0 - 0.42 * max(0.0, patch - 0.1) / 0.9 - 0.14 * max(0.0, damp)
        k *= 1.0 + 1.6 * (p.z - G)                                            # the rises a shade lighter, drier
        return mul(mul(tint, n(p)), k)

    def dirt(p):
        """How much bare earth shows (vertex alpha, read by the Godot lawn shader):
        bare patches, the drip line along every house, worn path edges, trails."""
        m = max(0.0, _noise.noise(Vector((p.x * 0.16, p.y * 0.16, 9.1))) - 0.2) * 1.1
        for r in _HOUSES + [z for z in _zones() if z not in _HOUSES]:
            dx, dy = max(r[0] - p.x, 0.0, p.x - r[2]), max(r[1] - p.y, 0.0, p.y - r[3])
            d = math.hypot(dx, dy)
            m = max(m, (0.85 if r in _HOUSES else 0.55) * max(0.0, 1.0 - d / (0.9 if r in _HOUSES else 0.6)))
        for a, b in trails:
            ab = b - a
            t = max(0.0, min(1.0, (Vector((p.x, p.y, 0)) - a).dot(ab) / max(ab.length_squared, 1e-6)))
            d = (Vector((p.x, p.y, 0)) - (a + ab * t)).length
            m = max(m, 0.9 * max(0.0, 1.0 - d / 0.45))
        return min(1.0, m)
    for i in range(nx):
        for j in range(ny):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(h[0] + 0.45 < cx < h[2] - 0.45 and h[1] + 0.45 < cy < h[3] - 0.45 for h in _HOUSES):
                continue
            q = [pt[i, j], pt[i + 1, j], pt[i + 1, j + 1], pt[i, j + 1]]
            mb.face(q, mat)
            mb.cols[-1] = [(*colour(p), dirt(p)) for p in q]


def _trails(lot):
    """Worn trails across a lot (from the porch steps round to the side yard, as
    people cut the corner), as (start, end) pairs. L1: back steps to the shed and
    the washing line."""
    if lot.key == "L1":
        return [(Vector((1.8, 10.0, 0)), Vector((8.6, 14.8, 0))), (Vector((1.8, 10.0, 0)), Vector((-2.4, 12.5, 0)))]
    h = lot.house
    if not h:
        return []
    rng = random.Random(hash(lot.key) % 1000)
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    W = lambda lx, ly: Vector((ox + ax * lx + bx * ly, oy + ay * lx + by * ly, 0))
    side = rng.choice((-1.2, h.width + 1.2))
    start = W(h.door_at + 0.45, -3.2)
    corner = W(side, -0.8)
    yard = W(side, h.depth * 0.6)
    return [(start, corner), (corner, yard)]


def settle_on_lawn(prefixes):
    """Lift every placed object whose name starts with one of `prefixes` by the
    yard's height under it, so nothing sinks into a rise."""
    import bpy
    for o in bpy.data.objects:
        if o.name.startswith(prefixes) and "colonly" not in o.name:
            o.location.z += lawn_offset(o.location.x, o.location.y)


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
        lawn_grid(lawn, lot, mat, tint, n)
        covered.append(lot.rect)
    bx0, by0, bx1, by1 = plan.BUILD
    # verge strips: north of the north lots, the corners outside the lots, south of Mill lots
    north, south = plan.ASHGROVE.road[3] + plan.SIDEWALK_W, plan.ASHGROVE.road[1] - plan.SIDEWALK_W
    verge = [
        (bx0, north, -30.5, by1),
        (38.5, north, bx1, by1),
        (-30.5, 18.0, 38.5, by1),
        (bx0, by0, -30.5, south),
        (-30.5, by0, -20.0, -40.0),
        (38.5, by0, bx1, south),
        (27.0, by0, 38.5, -40.0),
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
    """A pole-mounted transformer: tank, lid, cooling fins, two bushings, leads up to the lines."""
    mb = MeshBuilder()
    grey = (0.55, 0.57, 0.55)
    mb.cylinder((0, -0.35, 6.2), (0, 0, 0.85), 0.24, "metal_painted", segments=12, color=grey)
    mb.cylinder((0, -0.35, 7.05), (0, 0, 0.05), 0.26, "metal_painted", segments=12, color=mul(grey, 0.85))
    for k in range(6):
        a = math.pi * (0.25 + 0.5 * k / 5) + math.pi
        mb.obox((math.cos(a) * 0.27, -0.35 + math.sin(a) * 0.27, 6.6), (0.02, 0.10, 0.6), a + math.pi / 2, "metal_painted",
                color=mul(grey, 0.9))
    for x in (-0.12, 0.12):
        mb.cylinder((x, -0.35, 7.10), (0, 0, 0.16), 0.03, "glass_dirty", segments=6)
        mb.tube([(x, -0.35, 7.26), (x * 2.5, -0.12, 7.55), (x * 6.5, 0.0, 7.88)], 0.008, "wire", segments=4)
    mb.box((-0.06, -0.16, 6.5), (0.06, -0.1, 6.8), "metal_rust")
    mb.box((-0.14, -0.13, 6.25), (0.14, -0.10, 6.33), "metal_rust")
    mb.box((-0.14, -0.13, 6.9), (0.14, -0.10, 6.98), "metal_rust")
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
        if True:                                     # every pole carries a transformer
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
    nrm = Vector((-u.y, u.x, 0))
    grey = (0.62, 0.6, 0.55)                                     # bare wood where the paint has gone
    for s0, s1 in pieces:
        if s1 - s0 < 0.3:
            continue
        # posts every 2.4 m, rails between them that sag a little; a whole bay may lean
        n_bays = max(1, round((s1 - s0) / 2.4))
        bay = (s1 - s0) / n_bays
        bay_lean = [rng.uniform(-0.05, 0.05) if rng.random() < wear * 0.5 else 0.0 for _ in range(n_bays)]
        for k in range(n_bays):
            for zr in (0.25, 0.72):
                sag = rng.uniform(0.0, 0.025) * wear
                for half_ in (0, 1):
                    ca = a + u * (s0 + k * bay + half_ * bay / 2)
                    c = ca + u * (bay / 4)
                    mb.obox((c.x, c.y, G + zr + 0.03 - sag * (0.5 if half_ == 0 else 0.5)), (bay / 2, 0.04, 0.06),
                            rot, "trim", color=mul(colour, 0.9), tilt=(0.0, (sag if half_ == 0 else -sag) / max(bay, 0.1)))
        for k in range(1, n_bays):
            p = a + u * (s0 + k * bay) + nrm * 0.045
            mb.obox((p.x, p.y, G + 0.5), (0.085, 0.085, 1.0), rot, "trim", color=mul(colour, 0.82))
        s = s0
        while s < s1:
            bay_i = min(n_bays - 1, int((s - s0) / bay))
            r = rng.random()
            if r < 0.04 + 0.08 * wear:                            # gone: lying in the grass in front
                if rng.random() < 0.5:
                    p = a + u * s - nrm * rng.uniform(0.2, 0.7)
                    mb.obox((p.x, p.y, G + 0.015), (0.075, 0.9, 0.025), rot + rng.uniform(-0.6, 0.6), "trim",
                            color=mul(grey, 0.85))
            else:
                p = a + u * s
                h = 0.95 + rng.uniform(-0.03, 0.03)
                if rng.random() < 0.05 * wear:                    # snapped off
                    h = rng.uniform(0.35, 0.7)
                lean = rng.uniform(-0.06, 0.06) if rng.random() < wear * 0.3 else 0.0
                lean += bay_lean[bay_i]
                peel = min(1.0, max(0.0, rng.gauss(wear * 0.6, 0.25)))
                c = jitter_color(rng, tuple(colour[i] * (1 - peel) + grey[i] * peel for i in range(3)), 0.06)
                picket = MeshBuilder()
                picket.grime = ground_grime(-0.04, 0.35, 0.42)          # splash-back and moss at the foot
                picket.box((-0.0375, -0.0125, 0.0), (0.0375, 0.0125, h - 0.06), "trim", color=c, skip="+z-z")
                tip = [Vector((-0.0375, -0.0125, h - 0.06)), Vector((0.0375, -0.0125, h - 0.06)), Vector((0.0, -0.0125, h))]
                back = [Vector((v.x, 0.0125, v.z)) for v in tip]
                picket.face(tip, "trim", color=c)
                picket.face(list(reversed(back)), "trim", color=c)
                picket.face([tip[1], back[1], back[2], tip[2]], "trim", color=mul(c, 0.9))
                picket.face([tip[2], back[2], back[0], tip[0]], "trim", color=mul(c, 0.9))
                mb.extend(picket, Matrix.Translation((p.x, p.y, G + 0.04)) @ Matrix.Rotation(rot, 4, "Z")
                          @ Matrix.Rotation(lean, 4, "X"))
            s += 0.135
        for s in (s0, s1):
            p = a + u * s
            mb.obox((p.x, p.y, G + 0.54), (0.1, 0.1, 1.08), rot, "trim", color=mul(colour, 0.85))
            mb.obox((p.x, p.y, G + 1.095), (0.13, 0.13, 0.03), rot, "trim", color=mul(colour, 0.9))          # cap
            mb.obox((p.x, p.y, G + 1.13), (0.07, 0.07, 0.05), rot, "trim", color=mul(colour, 0.9))


def chainlink_run(mb, a, b, height=1.2):
    a, b = Vector((*a, G)), Vector((*b, G))
    d = b - a
    length = d.length
    n = max(1, int(length / 2.5))
    for i in range(n + 1):
        p = a.lerp(b, i / n)
        mb.cylinder(p, (0, 0, height + 0.05), 0.03, "metal_rust", segments=6, caps="top")
        mb.cylinder(p + Vector((0, 0, height + 0.05)), (0, 0, 0.03), 0.038, "metal_rust", segments=6, radius_top=0.012)   # cap
        mb.box((p.x - 0.036, p.y - 0.036, G + height - 0.06), (p.x + 0.036, p.y + 0.036, G + height - 0.02), "metal_rust")  # rail clamp
    mb.tube([a + Vector((0, 0, height)), b + Vector((0, 0, height))], 0.02, "metal_rust", segments=5)
    mb.tube([a + Vector((0, 0, 0.06)), b + Vector((0, 0, 0.06))], 0.005, "wire", segments=3)                 # tension wire
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
    last_missing = False
    while s < length:
        w = min(0.15, length - s)
        p = a + u * (s + w / 2)
        h = height + rng.uniform(-0.04, 0.04)
        lean = rng.uniform(-0.015, 0.015)
        r = rng.random()
        if r < 0.012 and not last_missing and 0.3 < s < length - 0.3:    # one board gone (15 cm: no way through)
            last_missing = True
            s += 0.15
            continue
        last_missing = False
        if r > 0.985:                                                # broken off at the top
            h = rng.uniform(1.2, 1.8)
        tone = (0.8, 0.76, 0.7)
        if 0.05 < r < 0.08:                                          # a replacement board, not yet greyed
            tone = (1.05, 0.92, 0.75)
        # no bottom face: it is in the ground. (The edges stay: without them the
        # 6 mm gaps between boards show the sky at a slant.)
        mb.obox((p.x, p.y, G + h / 2), (w - 0.006, 0.022, h), rot, "wood_weathered",
                color=jitter_color(rng, tone, 0.1), tilt=(lean, 0.0), skip="-z")
        s += 0.15
    n = max(1, int(length / 2.4))
    for i in range(n + 1):
        p = a.lerp(b, i / n) + nrm * 0.06
        mb.obox((p.x, p.y, G + height / 2), (0.09, 0.09, height + 0.05), rot, "wood_weathered", color=(0.6, 0.57, 0.52))
    for z in (0.35, height - 0.35):
        c = (a + b) / 2 + nrm * 0.05
        mb.obox((c.x, c.y, G + z), (length, 0.04, 0.09), rot, "wood_weathered", color=(0.62, 0.59, 0.54))


def lot_front(lot) -> str:
    """Which way a lot faces its street: "s" for the north side of Ashgrove,
    "n" for the south side, "e" for the lots on Mill Road."""
    x0, y0, x1, y1 = lot.rect
    if abs(y0 - (plan.ASHGROVE.road[3] + plan.SIDEWALK_W)) < 0.01:
        return "s"
    if abs(y1 - (plan.ASHGROVE.road[1] - plan.SIDEWALK_W)) < 0.01:
        return "n"
    return "e"


# --- where the fences go ---------------------------------------------------------------------

FENCE_CLEAR = 0.3          # metres kept between a fence and any building, porch or steps
FENCE_SEGMENTS: list = []  # every fence piece built: ((x, y), (x, y), kind), for the build's check


def _rect_of(h, l0, m0, l1, m1):
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    xs = [ox + ax * l + bx * m for l in (l0, l1) for m in (m0, m1)]
    ys = [oy + ay * l + by * m for l in (l0, l1) for m in (m0, m1)]
    return (min(xs), min(ys), max(xs), max(ys))


def building_rects():
    """Every footprint a fence must keep clear of, in world x0, y0, x1, y1, with a
    name: each kit house's walls, its porch with the steps (as house_kit.porch
    builds them), the side arm of a wrap porch, and the house file's house,
    porch, back steps and shed on L1."""
    from .house_kit import DOOR_W
    out = [((-0.3, -0.3, 7.6, 8.3), "house_L1"), ((0.08, -2.86, 3.92, -0.3), "porch_L1"),
           ((1.13, 8.3, 2.47, 9.85), "back_steps_L1"), ((8.19, 14.61, 11.25, 17.56), "shed_L1")]
    for lot in plan.LOTS:
        h = lot.house
        if not h:
            continue
        out.append((plan.house_rect(h), f"house_{lot.key}"))
        if h.porch == "entry":
            x0, x1, depth = h.door_at - 0.9, h.door_at + DOOR_W + 0.9, 1.7
        else:
            x0, x1, depth = -0.15, h.width + 0.15, 2.3
        out.append((_rect_of(h, min(x0, h.door_at - 0.35), -depth - 0.56, max(x1, h.door_at + DOOR_W + 0.35), 0.0),
                    f"porch_{lot.key}"))
        if h.porch == "wrap":
            sx0 = h.width + 0.15 - 2.2 if h.facing == "n" else -0.15
            out.append((_rect_of(h, sx0, 0.0, sx0 + 2.2, h.depth * 0.55), f"wrap_{lot.key}"))
    return out


# House-file pieces a fence may not be cut round (it would leave a hole next to
# them): the line is moved off them instead.
_FIXED = ("shed_L1",)


def _clip_run(a, b, margin=FENCE_CLEAR):
    """An axis-aligned run a-b with every building (plus margin) cut out of it."""
    (ax, ay), (bx, by) = a, b
    horizontal = abs(ay - by) < 1e-6
    c = ay if horizontal else ax
    lo, hi = sorted((ax, bx) if horizontal else (ay, by))
    pieces = [(lo, hi)]
    for (x0, y0, x1, y1), name in building_rects():
        p0, p1, q0, q1 = (x0, x1, y0, y1) if horizontal else (y0, y1, x0, x1)
        if not (q0 - margin < c < q1 + margin):
            continue
        cut0, cut1 = p0 - margin, p1 + margin
        nxt = []
        for s0, s1 in pieces:
            if cut1 <= s0 or cut0 >= s1:
                nxt.append((s0, s1))
                continue
            if cut0 - s0 > 0.3:
                nxt.append((s0, cut0))
            if s1 - cut1 > 0.3:
                nxt.append((cut1, s1))
        pieces = nxt
    return [((s0, c), (s1, c)) if horizontal else ((c, s0), (c, s1)) for s0, s1 in pieces]


def fence_layout():
    """The tall board fences, from the lots: down each lot line that is shared
    with a neighbour or the edge of town, from the back of the lot to 1.5 m
    behind the house front, then across to the house; on a corner lot's side
    street only from the back to the house's rear corner; along the back of
    the south lots; plus the edge-of-town fences in plan.BLOCKERS. Collinear
    lines within 0.6 m are one fence (the edge fence's line wins), each line
    keeps FENCE_CLEAR from the house file's fixed pieces by moving, and then
    every run is clipped round every building."""
    lines = {"x": [], "y": []}        # axis the line runs along: (perpendicular coordinate, lo, hi, fixed)
    def add(a, b, fixed=False):
        (ax, ay), (bx, by) = a, b
        if abs(ay - by) < 1e-6:
            lines["x"].append([ay, min(ax, bx), max(ax, bx), fixed])
        elif abs(ax - bx) < 1e-6:
            lines["y"].append([ax, min(ay, by), max(ay, by), fixed])
    for kind, x, y, heading, length in plan.BLOCKERS:
        if kind == "fence_tall":
            h = math.radians(heading)
            d = Vector((math.cos(h), math.sin(h))) * length / 2
            add((round(x - d.x, 3), round(y - d.y, 3)), (round(x + d.x, 3), round(y + d.y, 3)), fixed=True)

    def by_street(a, b):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        return any(r[0] - 0.6 <= mx <= r[2] + 0.6 and r[1] - 0.6 <= my <= r[3] + 0.6 for _, r in plan.SIDEWALKS)

    house_of = {name[6:]: r for r, name in building_rects() if name.startswith("house_")}
    for lot in plan.LOTS:
        if lot.key not in house_of:
            continue
        x0, y0, x1, y1 = lot.rect
        hx0, hy0, hx1, hy1 = house_of[lot.key]
        front = lot_front(lot)
        if front in ("s", "n"):
            fl = hy0 + 1.5 if front == "s" else hy1 - 1.5           # 1.5 m behind the house front
            rear_y, back_wall = (y1, hy1) if front == "s" else (y0, hy0)
            for lx, house_x in ((x0, hx0), (x1, hx1)):
                if by_street((lx, y0), (lx, y1)):                   # a corner lot's side street
                    add((lx, rear_y), (lx, back_wall))
                    add((lx, back_wall), (house_x, back_wall))
                else:
                    add((lx, rear_y), (lx, fl))
                    add((lx, fl), (house_x, fl))
            add((x0, rear_y), (x1, rear_y))
        else:                                                       # facing Mill Road, front at x1
            fl = hx1 - 1.5
            for ly, house_y in ((y0, hy0), (y1, hy1)):
                add((x0, ly), (fl, ly))
                add((fl, ly), (fl, house_y))
            add((x0, y0), (x0, y1))
    rects = building_rects()
    runs = []
    # 1. collinear lines within 0.75 m are one fence: work out each cluster's line
    clusters = {}
    for axis in ("x", "y"):
        out = []
        for l in sorted(lines[axis], key=lambda l: l[0]):
            # same fence: nearly the same line, and the spans meet (within 1 m)
            home = next((cl for cl in out if abs(l[0] - cl[0][0]) < 0.75 and
                         any(l[1] < m[2] + 1.0 and l[2] > m[1] - 1.0 for m in cl)), None)
            if home is not None:
                home.append(l)
            else:
                out.append([l])
        clusters[axis] = out
    coord = {}
    for axis in ("x", "y"):
        for cl in clusters[axis]:
            fixed = [l for l in cl if l[3]]
            c = fixed[0][0] if fixed else sum(l[0] for l in cl) / len(cl)
            # keep clear of the pieces that cannot be cut round: move the line off them
            for (rx0, ry0, rx1, ry1), name in rects:
                if name not in _FIXED:
                    continue
                q0, q1, p0, p1 = (ry0, ry1, rx0, rx1) if axis == "x" else (rx0, rx1, ry0, ry1)
                if any(l[1] < p1 and l[2] > p0 for l in cl) and q0 - FENCE_CLEAR - 0.05 < c < q1 + FENCE_CLEAR + 0.05:
                    c = q1 + FENCE_CLEAR + 0.05 if c > (q0 + q1) / 2 else q0 - FENCE_CLEAR - 0.05
            coord[axis, cl[0][0]] = c
    # 2. the ends of each run meet the line they run into, wherever that moved to
    span = {}
    for axis in ("x", "y"):
        for cl in clusters[axis]:
            span[axis, cl[0][0]] = (min(m[1] for m in cl), max(m[2] for m in cl), coord[axis, cl[0][0]])

    def snap(v, at, other):
        best = (0.75, v)
        for (ax, _), (lo, hi, c) in span.items():
            if ax == other and lo - 0.8 <= at <= hi + 0.8 and abs(c - v) < best[0]:
                best = (abs(c - v), c)
        return best[1]
    for axis, other in (("x", "y"), ("y", "x")):
        for cl in clusters[axis]:
            c = coord[axis, cl[0][0]]
            for l in cl:
                l[1], l[2] = snap(l[1], c, other), snap(l[2], c, other)
    # 3. merge each cluster's spans and clip them round the buildings
    for axis in ("x", "y"):
        for cl in clusters[axis]:
            c = coord[axis, cl[0][0]]
            spans = sorted((l[1], l[2]) for l in cl)
            merged = [list(spans[0])]
            for s0, s1 in spans[1:]:
                if s0 <= merged[-1][1] + 0.05:
                    merged[-1][1] = max(merged[-1][1], s1)
                else:
                    merged.append([s0, s1])
            for s0, s1 in merged:
                a, b = ((s0, c), (s1, c)) if axis == "x" else ((c, s0), (c, s1))
                for p0, p1 in _clip_run(a, b):
                    runs.append((p0, p1))
                    FENCE_SEGMENTS.append((p0, p1, "tall"))
    return runs


def fence_check(radius_trunk=0.3):
    """FENCE_HIT lines for every fence piece that touches a building footprint,
    porch or steps, or passes within a tree trunk. Returns the number of hits."""
    import bpy
    hits = 0
    for (a, b, kind) in FENCE_SEGMENTS:
        ax, ay = a
        bx, by = b
        for (x0, y0, x1, y1), name in building_rects():
            # the segment's box against the footprint (both axis-aligned)
            t = 0.1                                   # the fence's own half-thickness and its posts
            if min(ax, bx) - t < x1 and max(ax, bx) + t > x0 and min(ay, by) - t < y1 and max(ay, by) + t > y0:
                print(f"FENCE_HIT {kind} ({ax:.2f}, {ay:.2f})-({bx:.2f}, {by:.2f}) runs through {name}")
                hits += 1
        for o in bpy.data.objects:
            if not (o.name.startswith(("tree_", "edgetree_")) and o.type == "MESH"):
                continue
            px, py = o.location.x, o.location.y
            d = Vector((bx - ax, by - ay))
            t = max(0.0, min(1.0, ((px - ax) * d.x + (py - ay) * d.y) / max(d.length_squared, 1e-9)))
            if math.hypot(ax + d.x * t - px, ay + d.y * t - py) < radius_trunk * max(o.scale.x, 0.6):
                print(f"FENCE_HIT {kind} ({ax:.2f}, {ay:.2f})-({bx:.2f}, {by:.2f}) through the trunk of {o.name} at ({px:.2f}, {py:.2f})")
                hits += 1
    return hits


def fences(coll="fences"):
    FENCE_SEGMENTS.clear()
    rng = random.Random(21)
    pk, cl, tall = MeshBuilder(), MeshBuilder(), MeshBuilder()
    tall.grime = ground_grime(G, 0.55, 0.5)                       # damp and moss along the foot
    for lot in plan.LOTS:
        x0, y0, x1, y1 = lot.rect
        if lot_front(lot) == "s":
            a, b, gap = (x0 + 0.1, y0 + 0.25), (x1 - 0.1, y0 + 0.25), (lot.gate_at, y0 + 0.25) if lot.gate_at else None
        elif lot_front(lot) == "n":
            a, b, gap = (x0 + 0.1, y1 - 0.25), (x1 - 0.1, y1 - 0.25), (lot.gate_at, y1 - 0.25) if lot.gate_at else None
        else:
            a, b, gap = (x1 - 0.25, y0 + 0.1), (x1 - 0.25, y1 - 0.1), (x1 - 0.25, lot.gate_at) if lot.gate_at else None
        FENCE_SEGMENTS.extend((p0, p1, lot.fence) for p0, p1 in _clip_run(a, b) if lot.fence in ("picket", "chainlink"))
        if lot.fence == "picket":
            wear = lot.house.wear if lot.house else 0.5
            for p0, p1 in _clip_run(a, b):
                g = gap if gap and min(p0[0], p1[0]) - 0.01 <= gap[0] <= max(p0[0], p1[0]) + 0.01 and \
                    min(p0[1], p1[1]) - 0.01 <= gap[1] <= max(p0[1], p1[1]) + 0.01 else None
                picket_run(pk, p0, p1, rng, g, wear)
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
    chainlink_run(cl, (x0 + 0.2, -47.2), (x0 + 0.2, y1 - 0.2))          # Mill Road side: the vacant half only
    chainlink_run(cl, (x0 + 0.2, -47.2), (x1 - 0.6, -47.2))             # between the lot and Ridge Gas
    # Side and back fences: worked out from each lot and its house, then clipped
    # round every building (fence_layout); nothing hand-placed.
    for (ax, ay), (bx, by) in fence_layout():
        tall_fence_run(tall, (ax, ay), (bx, by), rng, 2.3)
    pk.build("fence_pickets", coll)      # not "fence_picket": that is the house's own, removed in the town
    cl.build("fence_chainlink", coll)
    tall.build("fence_tall", coll)


# --- Small props -----------------------------------------------------------------------

def _mailbox():
    """A rural mailbox on a braced post: rounded lid, door with a latch, a flag, a tube for the paper."""
    mb = MeshBuilder()
    wood = (0.6, 0.56, 0.5)
    tin = (0.75, 0.73, 0.7)
    mb.box((-0.045, -0.045, G - 0.1), (0.045, 0.045, G + 1.05), "wood_weathered", skip="-z", color=wood)
    mb.obox((0.0, -0.17, G + 0.86), (0.05, 0.42, 0.05), 0.0, "wood_weathered", color=wood, tilt=(0.75, 0.0))     # brace
    mb.box((-0.11, -0.30, G + 1.05), (0.11, 0.24, G + 1.08), "wood_weathered", color=wood)
    mb.box((-0.09, -0.27, G + 1.08), (0.09, 0.22, G + 1.20), "metal_rust", color=tin, skip="+z")
    # the rounded top, as half a cylinder
    seg = 8
    for i in range(seg):
        a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
        p0 = Vector((math.cos(a0) * 0.09, -0.27, G + 1.20 + math.sin(a0) * 0.09))
        p1 = Vector((math.cos(a1) * 0.09, -0.27, G + 1.20 + math.sin(a1) * 0.09))
        d = Vector((0, 0.49, 0))
        mb.face([p0, p0 + d, p1 + d, p1], "metal_rust", color=tin)
    for y, flip in ((-0.27, False), (0.22, True)):                 # door and back, as fans
        pts = [Vector((math.cos(math.pi * i / seg) * 0.09, y, G + 1.20 + math.sin(math.pi * i / seg) * 0.09)) for i in range(seg + 1)]
        pts += [Vector((-0.09, y, G + 1.08)), Vector((0.09, y, G + 1.08))]
        mb.face(pts if not flip else list(reversed(pts)), "metal_rust", color=mul(tin, 0.9))
    mb.box((-0.012, -0.285, G + 1.24), (0.012, -0.27, G + 1.27), "chrome_dull")                                    # latch
    mb.box((-0.08, -0.275, G + 1.08), (0.08, -0.268, G + 1.095), "chrome_dull")                                    # hinge
    mb.box((0.09, 0.02, G + 1.12), (0.10, 0.04, G + 1.34), "metal_painted", color=(0.6, 0.12, 0.08))               # flag
    mb.box((0.09, 0.02, G + 1.27), (0.10, 0.12, G + 1.34), "metal_painted", color=(0.6, 0.12, 0.08))
    mb.cylinder((0.0, -0.22, G + 0.99), (0, 0.40, 0), 0.055, "metal_painted", segments=8, caps="none", color=(0.3, 0.34, 0.4))  # paper tube
    return mb


def _trash_can():
    mb = MeshBuilder()
    zinc = (0.52, 0.54, 0.53)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.85), 0.27, "metal_painted", segments=14, radius_top=0.30, caps="bottom", color=zinc)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.16), 0.272, "metal_rust", segments=14, radius_top=0.276, caps="none",
                color=(0.6, 0.55, 0.5))                                            # the rusted-through foot
    mb.cylinder((0, 0, 0.85), (0, 0, 0.06), 0.32, "metal_painted", segments=14, color=mul(zinc, 0.9))
    mb.box((-0.06, -0.02, 0.91), (0.06, 0.02, 0.96), "metal_painted", color=mul(zinc, 0.8))
    for z in (0.3, 0.55):                                                          # pressed ribs
        mb.cylinder((0, 0, z), (0, 0, 0.03), 0.292, "metal_painted", segments=14, caps="none", color=mul(zinc, 0.85))
    for s in (-1, 1):                                                              # side handles
        mb.tube([(s * 0.29, -0.07, 0.62), (s * 0.34, 0.0, 0.60), (s * 0.29, 0.07, 0.62)], 0.01, "chrome_dull", segments=4)
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
    """Leaves banked where the wind left them: a low, lumpy, ragged mound,
    damp and dark, with single leaves lying on it and blown out round its edge
    so it has no clean outline."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    rings, segs = 6, 16
    r0 = rng.uniform(0.6, 0.95)
    hgt = rng.uniform(0.09, 0.15)
    lobes = [(rng.uniform(0.08, 0.2), rng.randint(2, 5), rng.uniform(0, 6.28)) for _ in range(3)]
    pts = [[None] * segs for _ in range(rings + 1)]
    for i in range(rings + 1):
        t = i / rings
        for j in range(segs):
            a = 2 * math.pi * j / segs
            edge = 1.0 + sum(amp * math.sin(k * a + ph) for amp, k, ph in lobes)
            rr = r0 * edge * (1 - t ** 1.4)
            z = hgt * math.sin(t * math.pi / 2) * (1.0 if i in (0, rings) else rng.uniform(0.7, 1.25))
            pts[i][j] = Vector((math.cos(a) * rr * 1.2, math.sin(a) * rr, z))
    for i in range(rings):
        for j in range(segs):
            k = (j + 1) % segs
            tone = mul((0.46, 0.38, 0.3), rng.uniform(0.8, 1.1))
            mb.face([pts[i][j], pts[i][k], pts[i + 1][k], pts[i + 1][j]], "leaves", color=tone)
    tones = [(0.95, 0.8, 0.55), (0.8, 0.62, 0.4), (0.6, 0.48, 0.34), (0.45, 0.38, 0.3)]
    for _ in range(30):
        a, t = rng.uniform(0, 6.28), rng.random() ** 0.6 * 1.35
        x, y = math.cos(a) * r0 * t * 1.2, math.sin(a) * r0 * t
        z = (hgt * math.cos(min(t, 1.0) * math.pi / 2) if t < 1 else 0.0) + 0.012
        size = rng.uniform(0.07, 0.13)
        m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rng.uniform(-0.4, 0.4), 4, "X")
        q = [m @ Vector(v) for v in ((-size / 2, -size * 0.6, 0), (size / 2, -size * 0.6, 0), (size / 2, size * 0.6, 0), (-size / 2, size * 0.6, 0))]
        cell = rng.randrange(4)
        cu, cv = (cell % 2) * 0.5, (cell // 2) * 0.5
        mb.face(q, "leaf_card", uvs=[(cu, cv), (cu + 0.5, cv), (cu + 0.5, cv + 0.5), (cu, cv + 0.5)],
                color=mul(tones[rng.randrange(4)], rng.uniform(0.55, 0.95)))
    return mb


TUFT_VARIANTS = 6
TUFT_TINTS = ((1.0, 0.9, 0.66), (0.72, 0.72, 0.46), (0.74, 0.58, 0.42))     # straw, olive, brown


def _tuft(seed):
    """A small grass tuft: three crossed alpha-tested cards of thin blades from
    the grass_blades atlas, 15 to 35 cm tall, leaning, darker at the root."""
    rng = random.Random(1000 + seed)
    mb = MeshBuilder()
    tint = TUFT_TINTS[seed % 3]
    cell = seed % 4
    u0, v0 = (cell % 2) * 0.5, 0.5 - (cell // 2) * 0.5
    h = rng.uniform(0.15, 0.35)
    for k in range(3):
        a = math.pi * k / 3 + rng.uniform(-0.3, 0.3)
        w = rng.uniform(0.2, 0.34) * (h / 0.25) ** 0.5
        d = Vector((math.cos(a), math.sin(a), 0)) * w / 2
        lean = Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0))
        top = Vector((0, 0, h * rng.uniform(0.85, 1.1)))
        c = mul(tint, rng.uniform(0.85, 1.05))
        pts = [-d, d, d + top + lean, -d + top + lean]
        mb.face(pts, "grass_blade_card", uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5)])
        mb.cols[-1] = [(*mul(c, 0.62), 1.0), (*mul(c, 0.62), 1.0), (*c, 1.0), (*c, 1.0)]
    return mb


_TUFTS: list = []


def tuft_cluster(x, y, z, rng, n=3, spread=0.25, coll="grass"):
    """A few tufts together round x, y (named grass_t*: instanced and faded in Godot)."""
    global _TUFTS
    if not _TUFTS:
        _TUFTS = [shared(f"grass_tuft_{k}", lambda k=k: _tuft(k)) for k in range(TUFT_VARIANTS)]
    for _ in range(n):
        tuft_cluster.count = getattr(tuft_cluster, "count", 0) + 1
        instance(_TUFTS[rng.randrange(TUFT_VARIANTS)], f"grass_t{tuft_cluster.count}", coll,
                 (x + rng.uniform(-spread, spread), y + rng.uniform(-spread, spread), z), rng.uniform(0, 6.28),
                 scale=rng.uniform(0.8, 1.45), tilt=(rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)))


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
            if lot_front(lot) == "s":
                spots.append((rng.uniform(x0, x1), y0 + rng.uniform(0.3, 1.2)))
            elif lot_front(lot) == "n":
                spots.append((rng.uniform(x0, x1), y1 - rng.uniform(0.3, 1.2)))
            else:
                gx, gy = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if lot.key == "L7" and gy < -47.0:
                    continue                             # that half is the station's concrete
                spots.append((gx, gy))
    # (the old big grass clumps along the fences are gone: small tufts now grow
    # in the kerb joints and along the sidewalk edges; yards.py does the lots)
    for start, end, side in curb_lines():
        a, b = Vector((*start, 0)), Vector((*end, 0))
        length = (b - a).length
        u = (b - a).normalized()
        for k in range(int(length / 2.6)):
            if rng.random() < 0.45:
                continue
            p = a + u * rng.uniform(k * 2.6, (k + 1) * 2.6)
            out = {"n": Vector((0, 1, 0)), "s": Vector((0, -1, 0)), "w": Vector((-1, 0, 0)), "e": Vector((1, 0, 0))}[side]
            q = p + out * rng.uniform(0.05, 0.15)                          # in the joint at the back of the kerb
            tuft_cluster(q.x, q.y, SW, rng, n=rng.randint(1, 3), spread=0.12)
    for _, (sx0, sy0, sx1, sy1) in plan.SIDEWALKS:                         # cracks across the slabs
        along_x = (sx1 - sx0) > (sy1 - sy0)
        n = int(max(sx1 - sx0, sy1 - sy0) / 6)
        for _ in range(n):
            x = rng.uniform(sx0 + 0.2, sx1 - 0.2)
            y = rng.uniform(sy0 + 0.2, sy1 - 0.2)
            tuft_cluster(x, y, SW, rng, n=rng.randint(1, 2), spread=0.1)
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
    """A bare deciduous tree that stands up to a close look: a flared, slightly
    leaning trunk, limbs that each keep a leader and throw side branches, and
    twigs that thin out and droop. About 4,000 triangles."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    bark = (0.62, 0.6, 0.56)
    kids_at = (4, 3, 2, 2)
    rings_at = (9, 7, 5, 4, 3)

    def branch(p, d, length, radius, depth):
        n = 5 if depth < 2 else 4
        pts, radii = [p], [radius]
        q, dd = p.copy(), d.copy()
        wander = 0.16 + 0.05 * depth
        for i in range(n):
            lift = 0.06 if depth < 2 else -0.05                    # limbs reach up, twigs sag
            dd = (dd + Vector((rng.uniform(-wander, wander), rng.uniform(-wander, wander), lift))).normalized()
            q = q + dd * (length / n)
            pts.append(q.copy())
            radii.append(radius * (1.0 - (i + 1) / n * 0.5))
        mb.tube(pts, radius, "bark", segments=rings_at[min(depth, 4)], radii=radii,
                color=mul(bark, 1.0 - 0.06 * depth))
        if depth >= 4 or radii[-1] < 0.006:
            return
        # the leader carries on from the tip; side branches leave lower down
        branch(pts[-1], (dd + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.1))).normalized(),
               length * rng.uniform(0.6, 0.75), radii[-1] * 0.95, depth + 1)
        for k in range(kids_at[depth] - 1):
            idx = rng.randint(1, n - 1)
            ang = rng.uniform(0, 2 * math.pi)
            side = Vector((math.cos(ang), math.sin(ang), rng.uniform(0.15, 0.6)))
            nd = (dd * 0.45 + side * 0.8).normalized()
            branch(pts[idx], nd, length * rng.uniform(0.45, 0.68), radii[idx] * rng.uniform(0.5, 0.68), depth + 1)

    trunk_h = height * 0.36
    r = height * 0.021
    lean = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
    trunk = [Vector((0, 0, -0.3)), Vector((0, 0, 0.12)), lean * 0.2 + Vector((0, 0, trunk_h * 0.35)),
             lean * 0.6 + Vector((0, 0, trunk_h * 0.7)), lean + Vector((0, 0, trunk_h))]
    mb.tube(trunk, r, "bark", segments=10, radii=[r * 1.7, r * 1.25, r * 1.05, r * 0.95, r * 0.85], color=bark)
    top = trunk[-1]
    n_limbs = rng.randint(3, 4)
    for k in range(n_limbs):
        ang = 2 * math.pi * k / n_limbs + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(ang) * 0.62, math.sin(ang) * 0.62, 0.78)).normalized()
        branch(top - Vector((0, 0, rng.uniform(0.0, trunk_h * 0.25))), d, height * 0.30, r * 0.62, 1)
    branch(top, (lean * 0.3 + Vector((0, 0, 1))).normalized(), height * 0.34, r * 0.8, 1)          # the leader
    return mb


def trees(coll="trees"):
    rng = random.Random(44)
    variants = [shared(f"tree_{k}", lambda k=k: _tree(200 + k)) for k in range(3)]
    for i, (x, y, h, seed) in enumerate(plan.TREES):
        instance(variants[seed % 3], f"tree_{i}", coll, (x, y, G), rng.uniform(0, 6.28), scale=h / 9.0)


# --- Cars --------------------------------------------------------------------------------

CAR_PAINTS = {"car_sedan": (0.14, 0.19, 0.17), "car_wagon": (0.30, 0.21, 0.13), "car_crashed": (0.13, 0.17, 0.24),
              "car_west": (0.26, 0.10, 0.09)}
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
    # (The house's water-table board used to cross its front doorway, and two wedges
    # here carried the player over it. The house now stops the board at the doorway,
    # so the wedges are gone; town.gd drops them from town models exported before that.)
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
