"""Bare late-autumn trees, built to stand up to a close look in the game.

What makes a bare tree read as real, and what the old one lacked:

- A trunk that flares into roots at the ground (five buttress roots going
  down into the soil) and tapers continuously up into the crown.
- Branch thickness that follows the "da Vinci" rule: the children of a
  branch together carry about its cross-section, so nothing is a pipe, and
  every tip tapers to a point.
- A crown of fine twigs. Geometry stops at the third level of branching;
  past that, alpha-tested cards of twig sprays (`twig_atlas`, a 2 x 2 atlas
  from detail_maps.py) sit along and at the end of every small branch,
  which gives the dense, hazy outline a winter tree has against the sky.
  Two of the four sprays still hold a few dry leaves.
- Bark mapped round each branch the right way: frames are carried along the
  branch (parallel transport) so the texture does not twist, and it wraps a
  whole number of times so there is no seam.
- Colour in the vertex colours: damp and dark at the foot, moss and lichen
  on one side of the trunk and the big limbs, greyer and lighter out at the
  thin wood.

Three forms (a spreading maple, a vase-shaped elm, a tree with a central
leader), two seeds each. About 4,500 triangles a tree; Godot makes the LODs.
Local axes: +Z up, origin on the ground at the trunk.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Quaternion, Vector, noise

from .core import MeshBuilder, mul

BARK = (0.56, 0.54, 0.5)              # grey-brown, times the bark texture
MOSS = (0.42, 0.48, 0.3)
MOSS_SIDE = Vector((0.3, 1.0, 0.0)).normalized()     # the damp side, roughly north
FORMS = ("spread", "vase", "leader")
VARIANTS = 6

# per form: trunk height (of the tree's height), number of scaffold limbs,
# their angle from vertical (degrees), their length (of the height), a leader?
FORM = {
    "spread": dict(trunk=0.30, limbs=(3, 4), angle=(38, 58), length=0.46, leader=False),
    "vase": dict(trunk=0.24, limbs=(3, 4), angle=(18, 32), length=0.62, leader=False),
    "leader": dict(trunk=0.36, limbs=(3, 5), angle=(42, 65), length=0.38, leader=True),
}


def _perp(d: Vector) -> Vector:
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    return d.cross(ref).normalized()


def _colour(p: Vector, r: float, n: Vector, seed: float):
    """Vertex colour of the bark at point p on a branch of radius r, facing n."""
    c = BARK
    thin = max(0.0, min(1.0, (0.06 - r) / 0.05))
    c = mul(c, 1.0 + 0.18 * thin)                                    # the thin wood greyer, lighter
    damp = max(0.0, 1.0 - p.z / 1.2)
    c = mul(c, 1.0 - 0.35 * damp)                                    # dark and wet at the foot
    side = max(0.0, n.dot(MOSS_SIDE))
    patch = noise.noise(Vector((p.x * 2.1, p.y * 2.1, p.z * 1.3 + seed)))
    moss = max(0.0, min(1.0, (side * 1.3 + patch * 0.8 - 0.55) * 2.0)) * max(0.0, 1.0 - thin * 1.5)
    moss *= 1.0 if p.z < 4.0 else 0.4
    return tuple(c[i] * (1 - moss) + MOSS[i] * moss for i in range(3))


def _tube(mb: MeshBuilder, pts, radii, sides, seed, tile=0.9):
    """A branch along pts with its own radius at each point; frames carried
    along (no twist); bark wrapped a whole number of times; pointed tip if
    the last radius is tiny."""
    pts = [Vector(p) for p in pts]
    dirs = []
    for k in range(len(pts)):
        d = pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]
        dirs.append(d.normalized())
    u = _perp(dirs[0])
    frames = []
    for k, d in enumerate(dirs):
        if k:
            q = dirs[k - 1].rotation_difference(d)
            u = (q @ u)
            u = (u - d * u.dot(d)).normalized()
        frames.append((u, d.cross(u)))
    wraps = max(1, round(2 * math.pi * radii[0] / tile))
    rings = []
    for k, p in enumerate(pts):
        u, v = frames[k]
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            n = u * math.cos(a) + v * math.sin(a)
            ring.append((p + n * radii[k], n))
        rings.append(ring)
    dist = 0.0
    for k in range(len(pts) - 1):
        seg = (pts[k + 1] - pts[k]).length
        for i in range(sides):
            j = (i + 1) % sides
            u0, u1 = i / sides * wraps, (i + 1) / sides * wraps
            quad = [rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]]
            mb.face([q[0] for q in quad], "bark",
                    uvs=[(u0, dist / tile), (u1, dist / tile), (u1, (dist + seg) / tile), (u0, (dist + seg) / tile)])
            rr = (radii[k], radii[k], radii[k + 1], radii[k + 1])
            mb.cols[-1] = [(*_colour(q[0], rr[m], q[1], seed), 1.0) for m, q in enumerate(quad)]
        dist += seg


class _Tree:
    def __init__(self, seed: int, form: str, height: float):
        self.rng = random.Random(seed)
        self.seed = seed * 0.37
        self.form = FORM[form]
        self.h = height
        self.mb = MeshBuilder()
        self.cards = 0
        self._taken = {}                 # card bases per 35 cm cell: overlapping bases read as a dark knot

    def card(self, base: Vector, d: Vector, length: float):
        """A twig spray card from `base` along `d`, rolled at random about it."""
        rng = self.rng
        cell_key = (round(base.x / 0.35), round(base.y / 0.35), round(base.z / 0.35))
        if self._taken.get(cell_key, 0) >= 2:
            return
        self._taken[cell_key] = self._taken.get(cell_key, 0) + 1
        side = _perp(d)
        side = Quaternion(d, rng.uniform(0, math.pi)) @ side
        # never small: a whole spray squeezed onto a little card reads as a dark knot
        length = max(0.45, min(1.3, length))
        w = length * rng.uniform(0.75, 1.0)
        top = d * length
        cell = rng.randrange(4)
        u0, v0 = (cell % 2) * 0.5, 0.5 - (cell // 2) * 0.5
        pts = [base - side * w / 2, base + side * w / 2, base + side * w / 2 + top, base - side * w / 2 + top]
        self.mb.face(pts, "twig_card", uvs=[(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5)])
        tone = rng.uniform(0.85, 1.05)
        self.mb.cols[-1] = [(tone, tone, tone, 1.0)] * 4
        self.cards += 1

    def branch(self, p: Vector, d: Vector, length: float, r0: float, depth: int):
        rng = self.rng
        n = (6, 5, 4, 3)[min(depth, 3)]
        sides = (12, 8, 6, 4)[min(depth, 3)]
        up = (0.0, 0.06, 0.03, -0.04)[min(depth, 3)]                 # limbs reach up, the thin wood sags
        wander = (0.05, 0.12, 0.18, 0.22)[min(depth, 3)]
        last = depth >= 3
        pts, radii, dirs = [p.copy()], [r0], [d.copy()]
        q, dd = p.copy(), d.copy()
        for i in range(n):
            dd = (dd + Vector((rng.uniform(-wander, wander), rng.uniform(-wander, wander), up))).normalized()
            q = q + dd * (length / n)
            t = (i + 1) / n
            pts.append(q.copy())
            radii.append(r0 * ((1 - t) ** 1.1 * 0.92 + 0.08) if not last else r0 * (1 - t * 0.97))
            dirs.append(dd.copy())
        _tube(self.mb, pts, radii, sides, self.seed)
        if last:
            # the finest wood: twig sprays along the end of it and out past the tip
            for k in range(rng.randint(2, 4)):
                i = rng.randint(max(1, n - 2), n)
                spray_d = (dirs[i] + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(-0.1, 0.4)))).normalized()
                self.card(pts[i] - spray_d * 0.05, spray_d, length * rng.uniform(0.55, 0.9))
            self.card(pts[-1] - dirs[-1] * 0.1, dirs[-1], length * rng.uniform(0.7, 1.1))
            return
        if depth == 2:
            # sprays straight off the outer half of the small limbs too, so the crown fills in
            for k in range(rng.randint(1, 2)):
                i = rng.randint(n // 2, n)
                spray_d = (dirs[i] + Vector((rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(0.0, 0.6)))).normalized()
                self.card(pts[i] - spray_d * 0.05, spray_d, length * rng.uniform(0.35, 0.55))
        # side branches: spread along the branch in a spiral, shorter towards the tip;
        # each takes a share of the branch's cross-section (da Vinci)
        kids = (0, 4, 4)[depth] if depth < 3 else 0
        golden = math.radians(137.5)
        phase = rng.uniform(0, 6.28)
        for k in range(kids):
            t = 0.25 + 0.7 * (k + rng.uniform(0.0, 0.8)) / kids
            i = min(n - 1, max(1, int(t * n)))
            base_d = dirs[i]
            ang = math.radians(rng.uniform(32, 58))
            axis = Quaternion(base_d, phase + golden * k) @ _perp(base_d)
            nd = (Quaternion(axis, ang) @ base_d).normalized()
            child_len = length * rng.uniform(0.5, 0.72) * (1.0 - 0.45 * t)
            self.branch(pts[i], nd, child_len, radii[i] * rng.uniform(0.5, 0.68), depth + 1)
        # the leader carries on from the tip
        nd = (dirs[-1] + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0.08))).normalized()
        self.branch(pts[-1], nd, length * rng.uniform(0.55, 0.7), radii[-1] * 1.05, depth + 1)

    def build(self) -> MeshBuilder:
        rng, f, h = self.rng, self.form, self.h
        r = h * 0.022
        trunk_h = h * f["trunk"] * rng.uniform(0.9, 1.1)
        lean = Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0))
        pts = [Vector((0, 0, -0.25))]
        radii = [r * 1.35]
        for k in range(1, 7):
            t = k / 6
            pts.append(lean * t ** 1.5 + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), trunk_h * t)))
            radii.append(r * (1.0 + 0.45 * math.exp(-t * 9.0)) * (1.0 - 0.18 * t))     # the flare, then a taper
        _tube(self.mb, pts, radii, 14, self.seed)
        # roots: five buttresses running out and down into the soil
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
            out = Vector((math.cos(a), math.sin(a), 0))
            rp = [Vector((0, 0, 0.35)) + out * r * 0.5, out * r * 1.4 + Vector((0, 0, 0.08)),
                  out * r * 2.6 + Vector((0, 0, -0.04)), out * r * 3.6 + Vector((0, 0, -0.16))]
            _tube(self.mb, rp, [r * 0.55, r * 0.42, r * 0.26, r * 0.08], 6, self.seed)
        top = pts[-1]
        n = rng.randint(*f["limbs"])
        phase = rng.uniform(0, 6.28)
        for k in range(n):
            a = phase + 2 * math.pi * k / n + rng.uniform(-0.35, 0.35)
            tilt = math.radians(rng.uniform(*f["angle"]))
            d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
            start = top - Vector((0, 0, rng.uniform(0.0, trunk_h * 0.18)))
            self.branch(start, d, h * f["length"] * rng.uniform(0.85, 1.1), r * 0.85 * rng.uniform(0.75, 0.95), 1)
        if f["leader"]:
            self.branch(top, (lean * 0.3 + Vector((0, 0, 1))).normalized(), h * 0.5, r * 0.8, 1)
        return self.mb


def tree(seed: int, height: float = 9.0) -> MeshBuilder:
    """One tree; the form comes from the seed (seed % 3)."""
    return _Tree(seed, FORMS[seed % 3], height).build()
