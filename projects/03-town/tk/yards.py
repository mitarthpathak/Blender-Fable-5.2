"""Yards (finishing pass): what fills the ground between the houses, their
fences and the street, which until now was flat lawn and nothing else.

For every kit house:

- dead foundation shrubs at the corners of the house and either side of the
  porch steps: a tangle of bare twigs with a few leaves still caught in it;
- long grass across the whole lot, front and back, not only along the front
  fence, thinning towards the house;
- in the back yard, what a house collects: a pair of trash cans by the back
  corner, a rusted drum, a stack of tyres or a woodpile, a folded lawn chair;
- a young tree or two where the yard is wide enough;
- leaves banked against the foot of every tall fence.

Everything repeated is a shared mesh placed as linked duplicates (Godot draws
them as MultiMeshes); the one-off yard props go into the 24 m prop sectors
with a collision box each.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, instance, jitter_color, mul
from . import street_kit as sk
from .street_kit import G, Sectors

SHRUB_VARIANTS = 4


# --- shared meshes -------------------------------------------------------------

def _shrub(seed: int) -> MeshBuilder:
    """A dead shrub about a metre tall: a dozen stems from one root, each
    forking twice and bending out, with a few cards of brown leaves caught in
    the twigs and lying round the foot."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    bark = (0.55, 0.5, 0.44)
    height = rng.uniform(0.75, 1.15)
    tips = []

    def stem(p, d, length, radius, depth):
        pts, radii = [p], [radius]
        q, dd = p.copy(), d.copy()
        for i in range(3):
            dd = (dd + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.05 if depth == 0 else -0.04))).normalized()
            q = q + dd * (length / 3)
            pts.append(q.copy())
            radii.append(radius * (1 - (i + 1) / 4))
        mb.tube(pts, radius, "bark", segments=4, radii=radii, color=mul(bark, rng.uniform(0.85, 1.05)))
        if depth < 2:
            for _ in range(2):
                k = rng.randint(1, 3)
                side = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 0.9))).normalized()
                stem(pts[k], (dd * 0.5 + side).normalized(), length * 0.55, radii[k] * 0.7, depth + 1)
        else:
            tips.append(pts[-1])

    stems = rng.randint(6, 8)
    for k in range(stems):
        a = 2 * math.pi * k / stems + rng.uniform(-0.3, 0.3)
        spread = rng.uniform(0.25, 0.55)
        d = Vector((math.cos(a) * spread, math.sin(a) * spread, 1.0)).normalized()
        stem(Vector((math.cos(a) * 0.04, math.sin(a) * 0.04, 0.0)), d, height * rng.uniform(0.45, 0.6), 0.014, 0)
    for p in rng.sample(tips, min(len(tips), 10)):                 # leaves still caught in the twigs
        mb.card((p.x, p.y, p.z - 0.12), rng.uniform(0.18, 0.3), rng.uniform(0.16, 0.26), rng.uniform(0, math.pi),
                "leaf_card", color=jitter_color(rng, (0.82, 0.74, 0.62), 0.1))
    for _ in range(3):                                             # and dropped round its foot
        mb.card((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.012), 0.55, 0.55, rng.uniform(0, 3.1),
                "decal_leaves", flat=True)
    return mb


def _drum() -> MeshBuilder:
    """A 55-gallon drum, rusted, with two rolling hoops and a dented lid."""
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), (0, 0, 0.88), 0.29, "metal_rust", segments=14, color=(0.78, 0.66, 0.56))
    for z in (0.29, 0.59):
        mb.cylinder((0, 0, z), (0, 0, 0.03), 0.30, "metal_rust", segments=14, caps="none", color=(0.66, 0.56, 0.48))
    mb.cylinder((0.12, 0.05, 0.88), (0, 0, 0.012), 0.03, "metal_rust", segments=8, color=(0.5, 0.44, 0.38))
    return mb


def _tyres(n: int, seed: int) -> MeshBuilder:
    """A stack of old car tyres, none quite square on the one below."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    for k in range(n):
        ox, oy = rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04)
        z = k * 0.19
        for r_out, r_in in ((0.33, 0.20),):
            mb.cylinder((ox, oy, z), (0, 0, 0.19), r_out, "tyre", segments=16, caps="none", color=(0.36, 0.36, 0.36))
            mb.cylinder((ox, oy, z), (0, 0, 0.19), r_in, "tyre", segments=16, caps="none", color=(0.2, 0.2, 0.2))
            ring_top = [Vector((ox + math.cos(2 * math.pi * i / 16) * r, oy + math.sin(2 * math.pi * i / 16) * r, z + 0.19))
                        for r in (r_out, r_in) for i in range(16)]
            for i in range(16):
                j = (i + 1) % 16
                mb.face([ring_top[i], ring_top[j], ring_top[16 + j], ring_top[16 + i]], "tyre", color=(0.3, 0.3, 0.3))
    return mb


def _woodpile(seed: int) -> MeshBuilder:
    """Split logs stacked against a wall, under a sheet of tin."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    length, rows = 1.6, 5
    for row in range(rows):
        y = 0.0
        while y < length:
            r = rng.uniform(0.06, 0.09)
            z = row * 0.15 + r
            mb.cylinder((-0.2, y - length / 2 + r, z), (0.42, 0, 0), r, "bark", segments=6, color=jitter_color(rng, (0.7, 0.62, 0.52), 0.1))
            y += r * 2.05
    top = rows * 0.15 + 0.12
    mb.obox((0.0, 0.0, top), (0.6, length + 0.2, 0.012), rng.uniform(-0.05, 0.05), "roof_tin", tilt=(0.0, 0.12))
    return mb


def _lawn_chair(seed: int) -> MeshBuilder:
    """A folding aluminium lawn chair with its webbing gone slack, knocked over."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    for s in (-1, 1):
        mb.tube([(s * 0.26, -0.25, 0.0), (s * 0.26, 0.15, 0.42), (s * 0.26, 0.32, 0.88)], 0.012, "chrome_dull", segments=4)
        mb.tube([(s * 0.26, 0.25, 0.0), (s * 0.26, -0.12, 0.40)], 0.012, "chrome_dull", segments=4)
    for k in range(5):
        z = 0.42 + k * 0.09
        mb.obox((0.0, 0.15 + k * 0.034, z), (0.52, 0.05, 0.006), 0.0, "fabric", color=jitter_color(rng, (0.55, 0.62, 0.5), 0.08),
                tilt=(-0.5, 0.0))
    return mb


# --- placing ---------------------------------------------------------------------

def _frame(h):
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)

    def W(lx, ly):
        return Vector((ox + ax * lx + bx * ly, oy + ay * lx + by * ly, 0.0))
    return W


def _inside(x, y, rect, pad=0.0):
    return rect[0] - pad <= x <= rect[2] + pad and rect[1] - pad <= y <= rect[3] + pad


def _clear(x, y, blocked):
    return not any(_inside(x, y, r) for r in blocked)


def _porch_box(h):
    """The porch, its steps and the path, in house-local coordinates (x0, y0, x1, y1)."""
    if h.porch == "entry":
        return (h.door_at - 1.1, -2.9, h.door_at + 0.9 + 1.1, 0.0)
    return (-0.4, -3.2, h.width + 0.4, 0.0)


def build(houses, coll="props"):
    rng = random.Random(91)
    shrubs = [sk.shared(f"shrub_{k}", lambda k=k: _shrub(300 + k)) for k in range(SHRUB_VARIANTS)]
    clumps = [sk.shared(f"grass_clump_{k}", lambda k=k: sk._grass_clump(k)) for k in range(3)]
    can = sk.shared("trash_can", sk._trash_can)
    drum = sk.shared("yard_drum", _drum)
    trees = [sk.shared(f"tree_{k}", lambda k=k: sk._tree(200 + k)) for k in range(3)]
    med = Sectors("mprop_yard")
    counts = {"shrubs": 0, "grass": 0, "cans": 0, "props": 0, "trees": 0}

    houses_by_key = dict(houses)
    for lot in plan.LOTS:
        if lot.key not in houses_by_key:
            continue
        h = lot.house
        W = _frame(h)
        hx0, hy0, hx1, hy1 = plan.house_rect(h)
        px0, py0, px1, py1 = _porch_box(h)
        porch = [W(px0, py0), W(px1, py1)]
        porch_rect = (min(p.x for p in porch), min(p.y for p in porch), max(p.x for p in porch), max(p.y for p in porch))
        if h.porch == "wrap":                                   # its side arm
            side = [W(h.width + 0.15 - 2.4, 0.0), W(h.width + 0.4, h.depth * 0.6)] if h.facing == "n" else \
                [W(-0.4, 0.0), W(2.3, h.depth * 0.6)]
            wrap_rect = (min(p.x for p in side), min(p.y for p in side), max(p.x for p in side), max(p.y for p in side))
        else:
            wrap_rect = (0, 0, 0, 0)
        door = W(h.door_at + 0.45, -3.0)
        x0, y0, x1, y1 = lot.rect
        # the front path, from the steps to the street
        front = sk.lot_front(lot)
        path_rect = (door.x - 0.9, min(door.y, y0 if front == "s" else y1), door.x + 0.9, max(door.y, y0 if front == "s" else y1)) \
            if front in ("s", "n") else (min(door.x, x1), door.y - 0.9, max(door.x, x1), door.y + 0.9)
        blocked = [(hx0 - 0.15, hy0 - 0.15, hx1 + 0.15, hy1 + 0.15), porch_rect, wrap_rect, path_rect]

        # 1. shrubs: the four corners of the house, and either side of the steps
        spots = [(-0.75, 0.35), (h.width + 0.75, 0.35), (-0.75, h.depth - 0.4), (h.width + 0.75, h.depth - 0.4)]
        if h.porch == "entry":
            spots += [(px0 - 0.6, -0.5), (px1 + 0.6, -0.5), (px0 - 1.7, -0.5), (px1 + 1.7, -0.5)]
        else:
            spots += [(h.door_at - 0.9, py0 - 0.6), (h.door_at + 0.9 + 0.9, py0 - 0.6)]
        for lx, ly in spots:
            p = W(lx, ly)
            if not _inside(p.x, p.y, lot.rect, -0.6) or not _clear(p.x, p.y, blocked[1:]):
                continue
            instance(shrubs[rng.randrange(SHRUB_VARIANTS)], f"shrub_{counts['shrubs']}", coll, (p.x, p.y, G),
                     rng.uniform(0, 6.28), scale=rng.uniform(0.8, 1.25))
            counts["shrubs"] += 1

        # 2. long grass across the whole lot, sparser near the house
        area = (x1 - x0) * (y1 - y0)
        tries = int(area / 5.5)
        for _ in range(tries):
            gx, gy = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(y0 + 0.4, y1 - 0.4)
            if not _clear(gx, gy, blocked):
                continue
            near = min(abs(gx - hx0), abs(gx - hx1), abs(gy - hy0), abs(gy - hy1))
            if near < 2.0 and rng.random() < 0.5:
                continue
            instance(clumps[rng.randrange(3)], f"grass_y{counts['grass']}", "grass", (gx, gy, G), rng.uniform(0, 6.28),
                     scale=rng.uniform(0.6, 1.25))
            counts["grass"] += 1

        # 3. the back yard: cans by the back corner, then two or three of the rest
        back = h.depth + 0.8
        corner = W(h.width - 0.6 if rng.random() < 0.5 else 0.6, back)
        if _inside(corner.x, corner.y, lot.rect, -0.8):
            for k in range(2):
                p = corner + Vector((0.65 * k * (1 if h.facing in "sn" else 0), 0.65 * k * (1 if h.facing == "e" else 0), 0))
                instance(can, f"trash_can_y{counts['cans']}", "props", (p.x, p.y, G), rng.uniform(0, 6.28))
                counts["cans"] += 1
        choices = ["drum", "tyres", "woodpile", "chair", "drum"]
        rng.shuffle(choices)
        for kind in choices[: rng.randint(2, 3)]:
            for _ in range(12):
                lx, ly = rng.uniform(0.3, h.width - 0.3), rng.uniform(h.depth + 1.2, h.depth + 4.5)
                p = W(lx, ly)
                if _inside(p.x, p.y, lot.rect, -1.0) and _clear(p.x, p.y, blocked):
                    break
            else:
                continue
            rot = rng.uniform(0, 6.28)
            if kind == "drum":
                instance(drum, f"yard_drum_{counts['props']}", "props", (p.x, p.y, G), rot)
                box = MeshBuilder()
                box.cylinder((p.x, p.y, G), (0, 0, 0.9), 0.3, "concrete", segments=8)
                box.build(f"yard_drum_{counts['props']}_col-convcolonly", "collision")
            else:
                part = {"tyres": lambda: _tyres(rng.randint(2, 4), rng.randint(0, 99)),
                        "woodpile": lambda: _woodpile(rng.randint(0, 99)),
                        "chair": lambda: _lawn_chair(rng.randint(0, 99))}[kind]()
                m = Matrix.Translation((p.x, p.y, G)) @ Matrix.Rotation(rot, 4, "Z")
                if kind == "chair":
                    m = m @ Matrix.Rotation(1.35, 4, "X")         # lying on its back
                med.at(p.x, p.y).extend(part, m)
                if kind != "chair":
                    size = (0.75, 0.75, 0.8) if kind == "tyres" else (0.5, 1.8, 0.95)
                    box = MeshBuilder()
                    box.obox((p.x, p.y, G + size[2] / 2), size, rot, "concrete")
                    box.build(f"yard_{kind}_{counts['props']}_col-convcolonly", "collision")
            counts["props"] += 1

        # 4. a young tree in the back yard, if there is room for one
        for _ in range(10):
            lx, ly = rng.uniform(-1.0, h.width + 1.0), rng.uniform(h.depth + 3.0, h.depth + 7.5)
            p = W(lx, ly)
            if _inside(p.x, p.y, lot.rect, -1.5) and _clear(p.x, p.y, blocked) and \
                    all((Vector((tx, ty, 0)) - p).length > 4.0 for tx, ty, _, _ in plan.TREES):
                instance(trees[rng.randrange(3)], f"tree_y{counts['trees']}", "trees", (p.x, p.y, G), rng.uniform(0, 6.28),
                         scale=rng.uniform(0.55, 0.8))
                counts["trees"] += 1
                break

    # 5. leaves and weeds banked along the foot of the tall board fences
    piles = [sk.shared(f"leaf_pile_{k}", lambda k=k: sk._leaf_pile(k)) for k in range(3)]
    n = 0
    for lot in plan.LOTS:
        if not lot.house:
            continue
        x0, y0, x1, y1 = lot.rect
        for x, y in ((x0 + 0.7, y1 - 0.7), (x1 - 0.7, y1 - 0.7), (x0 + 0.7, y0 + 0.7), (x1 - 0.7, y0 + 0.7)):
            if sk.lot_front(lot) == "s" and y < y0 + 1.0 or sk.lot_front(lot) == "n" and y > y1 - 1.0:
                continue                                         # not in the front yard by the street
            instance(piles[n % 3], f"leaf_pile_y{n}", "props", (x, y, G), rng.uniform(0, 6.28), scale=rng.uniform(0.6, 1.0))
            n += 1
    med.build("props")
    print("YARDS", counts, "leaf piles", n)
    return counts
