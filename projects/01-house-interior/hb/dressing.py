"""Procedural dressing: curtains, radiators, switches, cables, lamps, rugs,
books, loose paper and the grime and damage decals.

Most of it hangs on a wall, so pieces are described on a `Face`: a along the
wall, d out from it into the room, z up.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

import assets
import plan
from . import core
from .core import MeshBuilder


class Face:
    """One side of a wall. `axis` is the direction the wall runs, `c` the
    position of the surface, `sign` which way it looks."""

    def __init__(self, axis: str, c: float, sign: int):
        self.axis, self.c, self.sign = axis, c, sign

    def P(self, a, d, z):
        return Vector((a, self.c + self.sign * d, z)) if self.axis == "x" \
            else Vector((self.c + self.sign * d, a, z))

    @property
    def normal(self):
        return Vector((0, self.sign, 0)) if self.axis == "x" else Vector((self.sign, 0, 0))

    @property
    def along(self):
        return Vector((1, 0, 0)) if self.axis == "x" else Vector((0, 1, 0))

    def box(self, mb, a0, a1, d0, d1, z0, z1, key, skip=""):
        p, q = self.P(a0, d0, z0), self.P(a1, d1, z1)
        lo = (min(p.x, q.x), min(p.y, q.y), min(p.z, q.z))
        hi = (max(p.x, q.x), max(p.y, q.y), max(p.z, q.z))
        mb.box(lo, hi, key, skip=skip)

    @property
    def facing(self) -> float:
        """Compass angle of the direction this face looks, for placing models."""
        n = self.normal
        return math.degrees(math.atan2(n.y, n.x))


F1 = plan.FFL[1]
SOUTH = Face("x", 0.0, 1)
NORTH = Face("x", plan.DEPTH, -1)
WEST = Face("y", 0.0, 1)
EAST = Face("y", plan.WIDTH, -1)
HALL_EAST = Face("y", plan.PART_X0, -1)            # the partition, seen from the hall and landing
ROOM_WEST = Face("y", plan.PART_X1, 1)             # the partition, seen from the rooms
DIVIDER_S = Face("x", plan.DIVIDER_Y0, -1)         # bedroom side
DIVIDER_N = Face("x", plan.DIVIDER_Y1, 1)          # box room side
CHIMNEY = Face("y", 6.95, -1)


# --- Light points -----------------------------------------------------------

def lightpoint(name, location, kind, watts=40.0):
    """Mark where a lamp's bulb is. The lighting phase turns these into lights."""
    obj = core.empty("lightpoint_" + name, "lightpoints", location)
    obj["kind"] = kind
    obj["watts"] = watts
    return obj


def _bulb(mb, centre, radius, key):
    c = Vector(centre)
    rings = [(-1.0, 0.0), (-0.7, 0.71), (0.0, 1.0), (0.7, 0.71), (1.0, 0.0)]
    for (z0, r0), (z1, r1) in zip(rings, rings[1:]):
        mb.cylinder(c + Vector((0, 0, z0 * radius)), (0, 0, (z1 - z0) * radius), max(r0 * radius, 1e-4), key,
                    segments=10, caps="none", radius_top=max(r1 * radius, 1e-4))


def table_lamp(name, base, kind="warm", watts=40.0, coll="lamps", shade="lampshade_lit"):
    x, y, z = base
    mb = MeshBuilder()
    mb.cylinder((x, y, z), (0, 0, 0.018), 0.07, "ceramic", segments=16)
    mb.cylinder((x, y, z + 0.018), (0, 0, 0.07), 0.05, "ceramic", segments=16, caps="none", radius_top=0.065)
    mb.cylinder((x, y, z + 0.088), (0, 0, 0.08), 0.065, "ceramic", segments=16, caps="top", radius_top=0.025)
    mb.cylinder((x, y, z + 0.168), (0, 0, 0.09), 0.008, "metal_brass", segments=8)
    lit = kind != "off"
    _bulb(mb, (x, y, z + 0.30), 0.028, "bulb_on" if lit else "bulb_off")
    obj = mb.build("lamp_" + name, coll, smooth=True)
    # The shade is its own object: it is translucent, so it must not shadow the bulb.
    sh = MeshBuilder()
    sh.cylinder((x, y, z + 0.235), (0, 0, 0.19), 0.165, shade if lit else "lampshade", segments=20, caps="none",
                radius_top=0.105)
    shade_obj = sh.build("shade_" + name, coll, smooth=True)
    shade_obj.visible_shadow = False
    if lit:
        lightpoint(name, (x, y, z + 0.31), kind, watts)
    return obj


def pendant(name, x, y, ceiling, drop=0.55, kind="off", watts=40.0, coll="lamps"):
    mb = MeshBuilder()
    mb.cylinder((x, y, ceiling - 0.022), (0, 0, 0.022), 0.055, "plastic_white", segments=14)
    mb.cylinder((x, y, ceiling - drop + 0.05), (0, 0, drop - 0.07), 0.0035, "plastic_black", segments=6,
                caps="none")
    mb.cylinder((x, y, ceiling - drop), (0, 0, 0.055), 0.019, "plastic_white", segments=10)
    lit = kind != "off"
    _bulb(mb, (x, y, ceiling - drop - 0.03), 0.03, "bulb_on" if lit else "bulb_off")
    obj = mb.build("pendant_" + name, coll, smooth=True)
    sh = MeshBuilder()
    sh.cylinder((x, y, ceiling - drop - 0.085), (0, 0, 0.12), 0.17, "lampshade_lit" if lit else "lampshade",
                segments=18, caps="none", radius_top=0.035)
    shade_obj = sh.build("shade_pendant_" + name, coll, smooth=True)
    shade_obj.visible_shadow = False
    if lit:
        lightpoint(name, (x, y, ceiling - drop - 0.04), kind, watts)
    return obj


def broken_floor_lamp(name, foot, direction_deg, coll="lamps"):
    """A floor lamp knocked over: the pole along the floor, shade crushed, bulb smashed."""
    x, y, z = foot
    u = Vector((math.cos(math.radians(direction_deg)), math.sin(math.radians(direction_deg)), 0))
    side = Vector((-u.y, u.x, 0))
    mb = MeshBuilder()
    r = 0.15
    base = Vector((x, y, z + r))
    mb.cylinder(base - u * 0.015, u * 0.03, r, "metal_dark", segments=18)
    pole_a, pole_b = base, Vector((x, y, z + 0.02)) + u * 1.45
    mb.cylinder(pole_a, pole_b - pole_a, 0.013, "metal_brass", segments=8)
    tip = pole_b
    shade_axis = (u + side * 0.35 + Vector((0, 0, 0.25))).normalized() * 0.24
    mb.cylinder(tip - shade_axis * 0.2, shade_axis, 0.11, "lampshade", segments=14, caps="none", radius_top=0.19)
    mb.cylinder(tip, u * 0.05, 0.018, "plastic_white", segments=8)
    rng = random.Random(7)
    for _ in range(14):                                  # shards of the bulb
        c = tip + u * rng.uniform(0.1, 0.45) + side * rng.uniform(-0.25, 0.25)
        c.z = z + 0.002
        a, b = rng.uniform(0.008, 0.02), rng.uniform(0, math.pi)
        pts = [c + Vector((math.cos(b + k * 2.1) * a, math.sin(b + k * 2.1) * a, 0)) for k in range(3)]
        mb.face(pts, "glass")
    return mb.build("lamp_" + name, coll, smooth=False)


# --- Curtains, rugs, radiators ----------------------------------------------

def curtain(name, face, a0, a1, z_top, z_bot, seed=0, off=0.105, key="fabric_curtain", coll="soft"):
    """One hanging panel between a0 and a1, gathered into folds."""
    rng = random.Random(seed)
    width = a1 - a0
    cols = max(10, int(width / 0.03))
    rows = 7
    folds = max(1.5, width / 0.12)
    phase = rng.uniform(0, 6.28)
    tile = core.spec(key).tile
    mb = MeshBuilder()
    grid = []
    for i in range(cols + 1):
        s = i / cols
        column = []
        wobble = rng.uniform(-0.006, 0.006)
        for j in range(rows + 1):
            t = j / rows                                   # 0 at the top
            amp = 0.022 + 0.03 * t
            d = off + amp * math.sin(2 * math.pi * folds * s + phase + 0.6 * math.sin(3 * t + phase)) + wobble * t
            z = z_top + (z_bot - z_top) * t + (0.012 * math.sin(9 * s + phase) if j == rows else 0)
            column.append((face.P(a0 + width * s, d, z), (s * width * 1.7 / tile, z / tile)))
        grid.append(column)
    for i in range(cols):
        for j in range(rows):
            quad = [grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]]
            mb.face([q[0] for q in quad], key, uvs=[q[1] for q in quad])
    return mb.build(name, coll, smooth=True)


def curtain_pole(name, face, a0, a1, z, off=0.105, coll="soft"):
    mb = MeshBuilder()
    mb.cylinder(face.P(a0, off, z), face.along * (a1 - a0), 0.013, "metal_dark", segments=8)
    for a in (a0, a1):
        mb.cylinder(face.P(a, off, z) - face.along * 0.02 * (1 if a == a0 else -1), face.along * 0.02 * (1 if a == a0 else -1),
                    0.024, "metal_dark", segments=8)
    for a in (a0 + 0.12, (a0 + a1) / 2, a1 - 0.12):
        face.box(mb, a - 0.008, a + 0.008, 0.0, off, z - 0.008, z + 0.008, "metal_dark")
    return mb.build(name, coll)


def rug(name, x0, y0, x1, y1, z, key="carpet", coll="soft"):
    mb = MeshBuilder()
    mb.box((x0, y0, z), (x1, y1, z + 0.012), key, skip="-z")
    return mb.build(name, coll)


def radiator(name, face, a0, a1, floor, height=0.58, coll="fixtures"):
    mb = MeshBuilder()
    z0, z1 = floor + 0.14, floor + 0.14 + height
    face.box(mb, a0, a1, 0.035, 0.085, z0, z1, "metal_white")
    n = int((a1 - a0) / 0.05)
    for k in range(n):
        a = a0 + (a1 - a0) * (k + 0.5) / n
        face.box(mb, a - 0.011, a + 0.011, 0.085, 0.097, z0 + 0.03, z1 - 0.03, "metal_white", skip="")
    face.box(mb, a0 - 0.004, a1 + 0.004, 0.03, 0.10, z1, z1 + 0.012, "metal_white")
    for a in (a0 + 0.12, a1 - 0.12):
        face.box(mb, a - 0.015, a + 0.015, 0.0, 0.035, z1 - 0.12, z1 - 0.06, "metal_white")
    for a, s in ((a0, -1), (a1, 1)):                      # valve and pipe into the floor
        p = face.P(a + s * 0.035, 0.06, z0 + 0.03)
        mb.cylinder((p.x, p.y, floor), (0, 0, z0 + 0.03 - floor), 0.009, "metal_brass", segments=8, caps="none")
        mb.cylinder((p.x, p.y, z0 + 0.01), (0, 0, 0.06), 0.02, "plastic_white", segments=8)
        face.box(mb, min(a, a + s * 0.035), max(a, a + s * 0.035), 0.05, 0.07, z0 + 0.02, z0 + 0.04, "metal_brass")
    return mb.build(name, coll, recalc=True)


def switch(mb, face, a, z, double=False):
    w = 0.086
    face.box(mb, a - w / 2, a + w / 2, 0.0, 0.009, z - w / 2, z + w / 2, "plastic_white", skip="")
    for da in ((-0.018, 0.018) if double else (0.0,)):
        face.box(mb, a + da - 0.012, a + da + 0.012, 0.009, 0.0135, z - 0.022, z + 0.022, "plastic_white")


def socket(mb, face, a, z):
    face.box(mb, a - 0.073, a + 0.073, 0.0, 0.009, z - 0.043, z + 0.043, "plastic_white")
    for da in (-0.036, 0.036):
        face.box(mb, a + da - 0.019, a + da + 0.019, 0.009, 0.0095, z - 0.02, z + 0.018, "plastic_black", skip="")


def cable(mb, points, radius=0.004, key="plastic_black", steps=10):
    """A cable through the given points, smoothed, as a thin square tube."""
    pts = [Vector(p) for p in points]
    path = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(steps):
            t = k / steps
            path.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                               + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    path.append(pts[-1])
    for a, b in zip(path, path[1:]):
        if (b - a).length > 1e-5:
            mb.cylinder(a, b - a, radius, key, segments=4, caps="none")


# --- Small things -----------------------------------------------------------

BOOK_COLORS = ("book_red", "book_green", "book_blue", "book_cream", "book_brown", "book_black")


def book_row(mb, face, a0, a1, d_back, z, rng, fill=0.85, max_h=0.27):
    """Books standing on a shelf from a0 towards a1, spines facing the room."""
    a = a0
    stop = a0 + (a1 - a0) * fill
    while a < stop:
        w = rng.uniform(0.018, 0.048)
        h = rng.uniform(0.17, max_h)
        depth = rng.uniform(0.13, 0.19)
        if a + w > a1:
            break
        face.box(mb, a, a + w - 0.001, d_back, d_back + depth, z, z + h, rng.choice(BOOK_COLORS), skip="-z")
        a += w
    if rng.random() < 0.6 and a + 0.3 < a1:               # a few lying flat at the end
        zz = z
        for _ in range(rng.randint(2, 4)):
            t = rng.uniform(0.02, 0.04)
            face.box(mb, a + 0.03, a + 0.26, d_back, d_back + 0.18, zz, zz + t, rng.choice(BOOK_COLORS), skip="-z")
            zz += t


def bookcase(name, face, a0, a1, floor, height=1.95, depth=0.30, shelves=5, seed=1, key="wood_dark",
             coll="furniture"):
    rng = random.Random(seed)
    mb = MeshBuilder()
    t = 0.022
    face.box(mb, a0, a0 + t, 0.0, depth, floor, floor + height, key)
    face.box(mb, a1 - t, a1, 0.0, depth, floor, floor + height, key)
    face.box(mb, a0, a1, 0.0, 0.008, floor, floor + height, key)                       # back
    face.box(mb, a0 - 0.01, a1 + 0.01, 0.0, depth + 0.012, floor + height, floor + height + 0.03, key)
    face.box(mb, a0 + t, a1 - t, 0.0, depth - 0.01, floor, floor + 0.08, key)          # plinth
    levels = [floor + 0.08 + (height - 0.08) * k / shelves for k in range(shelves)]
    for z in levels:
        face.box(mb, a0 + t, a1 - t, 0.008, depth - 0.006, z, z + t, key)
    books = MeshBuilder()
    for z in levels:
        gap = (height - 0.08) / shelves - t - 0.02
        if rng.random() < 0.85:
            book_row(books, face, a0 + t + 0.004, a1 - t - 0.004, 0.02, z + t, rng,
                     fill=rng.uniform(0.45, 0.95), max_h=min(0.27, gap))
    made = [mb.build(name, coll, recalc=True)]
    if not books.empty:
        made.append(books.build(name + "_books", coll))
    return made


def mail(name, centre, count=9, seed=3, spread=0.35, coll="clutter"):
    """Post lying where it fell through the letterbox."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    cx, cy, z = centre
    for k in range(count):
        w, h = rng.choice(((0.22, 0.11), (0.23, 0.16), (0.30, 0.21)))
        x, y = cx + rng.uniform(-spread, spread), cy + rng.uniform(-spread * 0.7, spread * 0.7)
        ang = rng.uniform(0, math.pi)
        u, v = Vector((math.cos(ang), math.sin(ang), 0)) * w / 2, Vector((-math.sin(ang), math.cos(ang), 0)) * h / 2
        c = Vector((x, y, z + 0.002 + k * 0.0012))
        mb.face([c - u - v, c + u - v, c + u + v, c - u + v], rng.choice(("paper", "paper", "paper_brown")),
                uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return mb.build(name, coll)


def mug(mb, x, y, z, key="ceramic"):
    mb.cylinder((x, y, z), (0, 0, 0.09), 0.036, key, segments=12, caps="base", radius_top=0.04)
    mb.cylinder((x, y, z + 0.078), (0, 0, 0.001), 0.036, "coffee", segments=12, caps="top")
    mb.box((x + 0.038, y - 0.006, z + 0.025), (x + 0.062, y + 0.006, z + 0.07), key)


def newspaper(mb, x, y, z, angle_deg, key="paper"):
    ang = math.radians(angle_deg)
    u, v = Vector((math.cos(ang), math.sin(ang), 0)) * 0.19, Vector((-math.sin(ang), math.cos(ang), 0)) * 0.14
    for k in range(3):
        c = Vector((x, y, z + 0.002 + 0.003 * k))
        mb.face([c - u - v, c + u - v, c + u + v, c - u + v], key, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def coat_rail(name, face, a0, a1, z, coll="fixtures"):
    mb = MeshBuilder()
    face.box(mb, a0, a1, 0.0, 0.018, z - 0.05, z + 0.05, "wood_dark")
    hooks = []
    n = max(2, int((a1 - a0) / 0.22))
    for k in range(n):
        a = a0 + (a1 - a0) * (k + 0.5) / n
        face.box(mb, a - 0.006, a + 0.006, 0.018, 0.075, z - 0.006, z + 0.006, "metal_brass")
        face.box(mb, a - 0.006, a + 0.006, 0.063, 0.075, z - 0.006, z + 0.04, "metal_brass")
        hooks.append(a)
    return mb.build(name, coll), hooks


# --- Decals -----------------------------------------------------------------

def decal_material(texture: str):
    key = "decal_" + texture
    mat = core.material(key)
    path = assets.TEXTURES / "decals" / f"{texture}.png"
    if mat.get("decal_ready") or not path.exists():
        return key
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.92
    mat.surface_render_method = "BLENDED"
    mat["decal_ready"] = True
    return key


class Decals:
    """Collects decal quads for one room into one object."""

    def __init__(self, name, seed=0):
        self.name, self.mb, self.rng = name, MeshBuilder(), random.Random(seed)

    def wall(self, texture, face, a, z, w, h, flip=None):
        key = decal_material(texture)
        flip = self.rng.random() < 0.5 if flip is None else flip
        d = 0.0022 + self.rng.random() * 0.0006
        corners = [face.P(a - w / 2, d, z - h / 2), face.P(a + w / 2, d, z - h / 2),
                   face.P(a + w / 2, d, z + h / 2), face.P(a - w / 2, d, z + h / 2)]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if flip:
            uvs = [(1, 0), (0, 0), (0, 1), (1, 1)]
        n = (corners[1] - corners[0]).cross(corners[2] - corners[0])
        if n.dot(face.normal) < 0:
            corners, uvs = corners[::-1], uvs[::-1]
        self.mb.face(corners, key, uvs=uvs)

    def flat(self, texture, x, y, z, w, h, up=True, angle_deg=0.0):
        key = decal_material(texture)
        ang = math.radians(angle_deg)
        u = Vector((math.cos(ang), math.sin(ang), 0)) * w / 2
        v = Vector((-math.sin(ang), math.cos(ang), 0)) * h / 2
        c = Vector((x, y, z + (0.002 if up else -0.002)))
        pts = [c - u - v, c + u - v, c + u + v, c - u + v]
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if not up:
            pts, uvs = pts[::-1], uvs[::-1]
        self.mb.face(pts, key, uvs=uvs)

    def build(self, coll="decals"):
        if self.mb.empty:
            return None
        obj = self.mb.build(self.name, coll)
        obj.visible_shadow = False
        return obj
