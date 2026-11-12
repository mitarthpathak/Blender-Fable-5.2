"""Joinery: doors on their hinges, sash windows, architraves, skirting,
coving and the fireplace. Everything is placed from plan.py."""

from __future__ import annotations

import math

from mathutils import Vector

import plan
from . import core, shell
from .blockout import open_sign
from .core import MeshBuilder

# How far each door stands open, in degrees. The front door is shut: the
# player opens it.
DOOR_ANGLE = {"door_front": 0.0, "door_back": 0.0, "door_living": 64.0,
              "door_bedroom": 22.0, "door_bathroom": 38.0, "door_utility": 26.0}
DOOR_STYLE = {"door_front": "front", "door_back": "half_glazed"}
DOOR_PAINT = {"door_front": "front_door_paint", "door_back": "door_worn"}

LINING = 0.03           # door lining thickness
LEAF_T = 0.04
ARCH_W, ARCH_T = 0.07, 0.016
SKIRT_H, SKIRT_T = 0.16, 0.018
FRAME_SETBACK, FRAME_D, FRAME_W = 0.08, 0.10, 0.05


class WallFrame:
    """Coordinates measured on a wall: a along it, c across it, z up."""

    def __init__(self, wall):
        self.wall = wall
        self.along_x = wall.axis == "x"
        self.c0, self.c1 = (wall.y0, wall.y1) if self.along_x else (wall.x0, wall.x1)

    def P(self, a, c, z):
        return Vector((a, c, z)) if self.along_x else Vector((c, a, z))

    def box(self, mb, a0, a1, c0, c1, z0, z1, key, skip=""):
        p, q = self.P(a0, c0, z0), self.P(a1, c1, z1)
        lo = (min(p.x, q.x), min(p.y, q.y), min(p.z, q.z))
        hi = (max(p.x, q.x), max(p.y, q.y), max(p.z, q.z))
        if min(hi[i] - lo[i] for i in range(3)) > 1e-5:
            mb.box(lo, hi, key, skip=skip)

    def exterior_side(self):
        """+1 if the c1 face looks outdoors, -1 if c0 does, 0 for an interior wall."""
        w = self.wall
        mid_a = ((w.x0 + w.x1) / 2) if self.along_x else ((w.y0 + w.y1) / 2)
        for c, sign in ((self.c1, 1), (self.c0, -1)):
            p = self.P(mid_a, c + sign * 0.05, 1.0)
            if not core.inside_house(*p):
                return sign
        return 0


def architrave(mb, f, a0, a1, z0, z1, c_face, sign, key="trim_paint", bottom=False):
    """A flat architrave with a raised outer band, around an opening on one
    face of a wall. `sign` is the direction the face looks along c."""
    w, t, band_w, band_t = ARCH_W, ARCH_T, 0.022, 0.026

    def strip(aa, ab, za, zb, thick):
        f.box(mb, aa, ab, c_face, c_face + sign * thick, za, zb, key)

    strip(a0 - w, a0, z0, z1, t)
    strip(a1, a1 + w, z0, z1, t)
    strip(a0 - w, a1 + w, z1, z1 + w, t)
    strip(a0 - w, a0 - w + band_w, z0, z1 + w, band_t)
    strip(a1 + w - band_w, a1 + w, z0, z1 + w, band_t)
    strip(a0 - w, a1 + w, z1 + w - band_w, z1 + w, band_t)
    if bottom:
        strip(a0 - w, a1 + w, z0 - w, z0, t)


# --- Doors ------------------------------------------------------------------

def panel_layout(style, W, H):
    """Panels as (u0, v0, u1, v1, glazed)."""
    stile, top, bottom, mull = 0.10, 0.10, 0.21, 0.09
    lock0, lock1 = 0.82, 0.98
    left = (stile, W / 2 - mull / 2)
    right = (W / 2 + mull / 2, W - stile)
    lower = [(left[0], bottom, left[1], lock0, False), (right[0], bottom, right[1], lock0, False)]
    if style == "half_glazed":
        return lower + [(stile, lock1, W - stile, H - top, True)]
    glazed = style == "front"
    upper = [(left[0], lock1, left[1], H - top, glazed), (right[0], lock1, right[1], H - top, glazed)]
    return lower + upper


def build_leaf(mb, to_world, W, H, t, panels, key, glass_key="glass_frosted"):
    """A panelled door leaf. `to_world(u, d, v)` places a point: u from the
    hinge edge, d into the thickness from the hinge-side face, v up."""
    bevel, recess = 0.014, 0.011

    def quad(pts, k):
        mb.face([to_world(*p) for p in pts], k)

    us = sorted({0.0, W} | {p[0] for p in panels} | {p[2] for p in panels})
    vs = sorted({0.0, H} | {p[1] for p in panels} | {p[3] for p in panels})

    def in_panel(u, v):
        return any(p[0] < u < p[2] and p[1] < v < p[3] for p in panels)

    for d, s in ((0.0, 1.0), (t, -1.0)):
        for i in range(len(us) - 1):
            for j in range(len(vs) - 1):
                if in_panel((us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2):
                    continue
                quad([(us[i], d, vs[j]), (us[i + 1], d, vs[j]), (us[i + 1], d, vs[j + 1]), (us[i], d, vs[j + 1])], key)
        for u0, v0, u1, v1, glazed in panels:
            depth = (t / 2 - 0.003) if glazed else recess
            di = d + s * depth
            outer = [(u0, d, v0), (u1, d, v0), (u1, d, v1), (u0, d, v1)]
            inner = [(u0 + bevel, di, v0 + bevel), (u1 - bevel, di, v0 + bevel),
                     (u1 - bevel, di, v1 - bevel), (u0 + bevel, di, v1 - bevel)]
            for k in range(4):
                m = (k + 1) % 4
                quad([outer[k], outer[m], inner[m], inner[k]], key)
            quad(inner, glass_key if glazed else key)
    # the four edges
    quad([(0, 0, 0), (0, t, 0), (0, t, H), (0, 0, H)], key)
    quad([(W, 0, 0), (W, t, 0), (W, t, H), (W, 0, H)], key)
    quad([(0, 0, 0), (W, 0, 0), (W, t, 0), (0, t, 0)], key)
    quad([(0, 0, H), (W, 0, H), (W, t, H), (0, t, H)], key)


def leaf_box(mb, to_world, u0, u1, d0, d1, v0, v1, key):
    p, q = to_world(u0, d0, v0), to_world(u1, d1, v1)
    lo = (min(p.x, q.x), min(p.y, q.y), min(p.z, q.z))
    hi = (max(p.x, q.x), max(p.y, q.y), max(p.z, q.z))
    mb.box(lo, hi, key)


def build_door(wall, o, coll="doors"):
    f = WallFrame(wall)
    side = 1.0 if o.swing == "+" else -1.0
    face = f.c1 if side > 0 else f.c0
    other = f.c0 if side > 0 else f.c1
    made = []

    # Lining, stops and architraves: the fixed frame, one object.
    mb = MeshBuilder()
    lo_c, hi_c = min(f.c0, f.c1), max(f.c0, f.c1)
    f.box(mb, o.start, o.start + LINING, lo_c, hi_c, o.sill, o.head, "trim_paint")
    f.box(mb, o.end - LINING, o.end, lo_c, hi_c, o.sill, o.head, "trim_paint")
    f.box(mb, o.start + LINING, o.end - LINING, lo_c, hi_c, o.head - LINING, o.head, "trim_paint")
    if o.kind == "door":
        s0 = face - side * LEAF_T                      # the stop sits behind the closed leaf
        s1 = s0 - side * 0.035
        f.box(mb, o.start + LINING, o.start + LINING + 0.012, s0, s1, o.sill, o.head - LINING, "trim_paint")
        f.box(mb, o.end - LINING - 0.012, o.end - LINING, s0, s1, o.sill, o.head - LINING, "trim_paint")
        f.box(mb, o.start + LINING, o.end - LINING, s0, s1, o.head - LINING - 0.012, o.head - LINING, "trim_paint")
    ext = f.exterior_side()
    for c, sign in ((f.c1, 1), (f.c0, -1)):
        if sign != ext:                                # no architrave on the brick outside
            architrave(mb, f, o.start, o.end, o.sill, o.head, c, sign)
    made.append(mb.build("frame_" + o.name, coll, recalc=True))
    if o.kind != "door":
        return made

    # The leaf: built closed, with its origin on the hinge line.
    W = o.width - 2 * LINING - 0.006
    H = o.head - LINING - o.sill - 0.008
    hinge_a = (o.start + LINING + 0.003) if o.hinge == "start" else (o.end - LINING - 0.003)
    direction = 1.0 if o.hinge == "start" else -1.0
    z0 = o.sill + 0.005

    def to_world(u, d, v):
        return f.P(hinge_a + direction * u, face - side * d, z0 + v)

    key = DOOR_PAINT.get(o.name, "door_paint")
    mb = MeshBuilder()
    style = DOOR_STYLE.get(o.name, "four")
    build_leaf(mb, to_world, W, H, LEAF_T, panel_layout(style, W, H), key)

    # Lever handles on both faces, and three hinges.
    hu, hv = W - 0.06, 0.99
    for d_face, out in ((0.0, -1.0), (LEAF_T, 1.0)):
        def D(x, _f=d_face, _o=out):
            return _f + _o * x
        leaf_box(mb, to_world, hu - 0.022, hu + 0.022, D(0), D(0.006), hv - 0.09, hv + 0.09, "metal_brass")
        leaf_box(mb, to_world, hu - 0.009, hu + 0.009, D(0.006), D(0.05), hv - 0.009, hv + 0.009, "metal_brass")
        leaf_box(mb, to_world, hu - 0.115, hu + 0.011, D(0.04), D(0.056), hv - 0.009, hv + 0.009, "metal_brass")
    for hz in (0.22, H / 2, H - 0.22):
        leaf_box(mb, to_world, -0.006, 0.006, -0.008, 0.004, hz - 0.045, hz + 0.045, "metal_brass")

    if style == "front":
        # letterbox flap, night latch and a bolt on the inside face
        leaf_box(mb, to_world, W / 2 - 0.13, W / 2 + 0.13, -0.008, 0.0, 0.865, 0.935, "metal_brass")
        leaf_box(mb, to_world, W - 0.115, W - 0.012, -0.03, 0.0, 1.36, 1.45, "metal_brass")
        leaf_box(mb, to_world, W - 0.10, W - 0.012, -0.02, 0.0, 1.78, 1.82, "metal_dark")
        leaf_box(mb, to_world, W / 2 - 0.13, W / 2 + 0.13, LEAF_T, LEAF_T + 0.008, 0.865, 0.935, "metal_brass")

    hinge = f.P(hinge_a, face, o.sill)
    leaf = mb.build(o.name, coll, origin=hinge, recalc=True)
    leaf.rotation_euler = (0, 0, math.radians(DOOR_ANGLE.get(o.name, 0.0)) * open_sign(wall, o))
    leaf["hinge"] = o.hinge
    leaf["opens_degrees"] = 95.0 * open_sign(wall, o)
    made.append(leaf)
    return made


# --- Windows ----------------------------------------------------------------

def build_window(wall, o, coll="windows"):
    f = WallFrame(wall)
    ext = f.exterior_side() or 1
    c_ext = f.c1 if ext > 0 else f.c0
    c_int = f.c0 if ext > 0 else f.c1
    thick = abs(f.c1 - f.c0)

    def Q(q):
        """Depth into the wall from its outside face."""
        return c_ext - ext * q

    q0, q1 = FRAME_SETBACK, FRAME_SETBACK + FRAME_D
    fw = FRAME_W
    frame, glass = MeshBuilder(), MeshBuilder()
    paint = "trim_paint"

    def bar(a0, a1, qa, qb, z0, z1):
        f.box(frame, a0, a1, Q(qa), Q(qb), z0, z1, paint)

    bar(o.start, o.start + fw, q0, q1, o.sill, o.head)
    bar(o.end - fw, o.end, q0, q1, o.sill, o.head)
    bar(o.start + fw, o.end - fw, q0, q1, o.head - fw, o.head)
    bar(o.start + fw, o.end - fw, q0, q1, o.sill, o.sill + fw)

    inner0, inner1 = o.start + fw, o.end - fw
    zb, zt = o.sill + fw, o.head - fw
    fixed = (o.head - o.sill) < 0.6                     # a fanlight: one fixed pane
    bays = max(1, round(o.width / 0.85))
    mull = 0.05
    bay_w = (inner1 - inner0 - mull * (bays - 1)) / bays
    for b in range(bays):
        a0 = inner0 + b * (bay_w + mull)
        a1 = a0 + bay_w
        if b > 0:
            bar(a0 - mull, a0, q0, q1, zb, zt)
        if fixed:
            f.box(glass, a0 - 0.004, a1 + 0.004, Q((q0 + q1) / 2), Q((q0 + q1) / 2 + 0.004), zb - 0.004, zt + 0.004,
                  "glass")
            continue
        mid = (zb + zt) / 2
        sw = 0.045
        # (depth range, bottom, top, bottom rail height): the top sash is the outer one
        for (sa, sb), s_lo, s_hi, rail in (((q0 + 0.008, q0 + 0.048), mid - 0.02, zt, sw),
                                           ((q0 + 0.052, q0 + 0.092), zb, mid + 0.02, 0.065)):
            bar(a0, a0 + sw, sa, sb, s_lo, s_hi)
            bar(a1 - sw, a1, sa, sb, s_lo, s_hi)
            bar(a0 + sw, a1 - sw, sa, sb, s_hi - sw, s_hi)
            bar(a0 + sw, a1 - sw, sa, sb, s_lo, s_lo + rail)
            if bay_w > 0.7:
                am = (a0 + a1) / 2
                bar(am - 0.011, am + 0.011, sa + 0.008, sb - 0.008, s_lo + rail, s_hi - sw)
            qm = (sa + sb) / 2
            f.box(glass, a0 + sw - 0.004, a1 - sw + 0.004, Q(qm - 0.002), Q(qm + 0.002),
                  s_lo + rail - 0.004, s_hi - sw + 0.004, "glass")

    # Inside: a window board over the sill, and an architrave round the reveal.
    f.box(frame, o.start - 0.05, o.end + 0.05, Q(q1), Q(thick + 0.035), o.sill - 0.03, o.sill, paint)
    architrave(frame, f, o.start, o.end, o.sill, o.head, c_int, -ext)
    # Outside: a projecting sill.
    f.box(frame, o.start - 0.04, o.end + 0.04, Q(-0.045), Q(q0), o.sill - 0.07, o.sill, "stone_sill")

    made = [frame.build("window_" + o.name, coll, recalc=True)]
    pane = glass.build("glass_" + o.name, coll, recalc=True)
    pane.visible_shadow = False            # moonlight passes; the glazing bars still cast
    made.append(pane)
    return made


# --- Skirting and coving ----------------------------------------------------

def _run_ends(run, thickness):
    """Adjust the ends of a run so pieces meet cleanly at corners and stop
    at door architraves."""
    p0, p1 = run["p0"].copy(), run["p1"].copy()
    direction = (p1 - p0).normalized()
    for which, sign in (("end0", -1.0), ("end1", 1.0)):
        kind, shift = run[which], 0.0
        if kind == "open":
            shift = -(ARCH_W + 0.002)
        elif kind == "outside" and run["axis"] == "x":
            shift = thickness
        elif kind == "inside" and run["axis"] == "y":
            shift = -thickness
        if which == "end0":
            p0 -= direction * shift
        else:
            p1 += direction * shift
    return p0, p1


def build_skirting(coll="trim"):
    profile = [(0.0, 0.0), (SKIRT_T, 0.0), (SKIRT_T, SKIRT_H - 0.03), (SKIRT_T - 0.008, SKIRT_H - 0.012),
               (0.006, SKIRT_H), (0.0, SKIRT_H)]
    builders: dict[str, MeshBuilder] = {}
    for run in shell.wall_runs("floor", SKIRT_T):
        p0, p1 = _run_ends(run, SKIRT_T)
        length = (p1 - p0).length
        if length < 0.04 or (p1 - p0).dot(run["p1"] - run["p0"]) <= 0:
            continue
        mb = builders.setdefault(run["room"], MeshBuilder())
        mb.prism(profile, p0, run["normal"], (0, 0, 1), (p1 - p0).normalized(), length, "trim_paint")
    return [mb.build(f"skirting_{room}", coll, recalc=True) for room, mb in builders.items()]


def build_coving(coll="trim"):
    size = 0.085
    profile = [(0.0, 0.0), (size, 0.0), (size, -0.012), (size * 0.55, -size * 0.45),
               (0.012, -size), (0.0, -size)]
    builders: dict[str, MeshBuilder] = {}
    for run in shell.wall_runs("ceiling", size):
        p0, p1 = _run_ends(dict(run, end0="inside" if run["end0"] != "outside" else "outside",
                                end1="inside" if run["end1"] != "outside" else "outside"), size)
        length = (p1 - p0).length
        if length < 0.05 or (p1 - p0).dot(run["p1"] - run["p0"]) <= 0:
            continue
        mb = builders.setdefault(run["room"], MeshBuilder())
        mb.prism(profile, p0, run["normal"], (0, 0, 1), (p1 - p0).normalized(), length, "ceiling")
    return [mb.build(f"coving_{room}", coll, recalc=True) for room, mb in builders.items()]


# --- Fireplace --------------------------------------------------------------

def build_fireplace(coll="fireplace"):
    wall = next(w for w in plan.WALLS if w.name == "chimney_breast_gf")
    o = wall.openings[0]
    xf = wall.x0                              # front of the chimney breast
    yc = (o.start + o.end) / 2
    made = []

    # Firebox: a sooty lining just inside the recess, and a grate.
    mb = MeshBuilder()
    e, depth = 0.004, 0.30
    y0, y1, zt = o.start + e, o.end - e, o.head - e
    xb = xf + depth
    cx, hx = (xf + xb) / 2, depth / 2
    mb.rect((xb, yc, zt / 2), (0, (y1 - y0) / 2, 0), (0, 0, zt / 2), (-1, 0, 0), "soot")
    mb.rect((cx, y0, zt / 2), (hx, 0, 0), (0, 0, zt / 2), (0, 1, 0), "soot")
    mb.rect((cx, y1, zt / 2), (hx, 0, 0), (0, 0, zt / 2), (0, -1, 0), "soot")
    mb.rect((cx, yc, zt), (hx, 0, 0), (0, (y1 - y0) / 2, 0), (0, 0, -1), "soot")
    mb.rect((cx, yc, 0.026), (hx, 0, 0), (0, (y1 - y0) / 2, 0), (0, 0, 1), "hearth_tile")
    made.append(mb.build("fireplace_firebox", coll))

    mb = MeshBuilder()
    for k in range(6):                         # grate bars
        y = y0 + 0.05 + (y1 - y0 - 0.10) * k / 5
        mb.box((xf + 0.04, y - 0.007, 0.10), (xf + 0.24, y + 0.007, 0.114), "metal_dark")
    for x in (xf + 0.045, xf + 0.235):
        mb.box((x - 0.008, y0 + 0.04, 0.026), (x + 0.008, y0 + 0.055, 0.10), "metal_dark")
        mb.box((x - 0.008, y1 - 0.055, 0.026), (x + 0.008, y1 - 0.04, 0.10), "metal_dark")
    mb.box((xf + 0.03, y0 + 0.04, 0.114), (xf + 0.045, y1 - 0.04, 0.20), "metal_dark")
    # cast-iron insert framing the opening
    w_out, h_out, proud = 0.46, 0.92, 0.018
    mb.box((xf - proud, yc - w_out, 0.0), (xf, o.start, h_out), "metal_dark", skip="+x")
    mb.box((xf - proud, o.end, 0.0), (xf, yc + w_out, h_out), "metal_dark", skip="+x")
    mb.box((xf - proud, o.start, o.head), (xf, o.end, h_out), "metal_dark", skip="+x")
    made.append(mb.build("fireplace_insert", coll, recalc=True))

    # Painted surround and mantel shelf.
    mb = MeshBuilder()
    leg_w, leg_p, top_z = 0.16, 0.07, 1.10
    for s in (-1, 1):
        ya, yb = yc + s * w_out, yc + s * (w_out + leg_w)
        mb.box((xf - leg_p, min(ya, yb), 0.0), (xf, max(ya, yb), top_z), "trim_paint", skip="+x-z")
        mb.box((xf - leg_p - 0.012, min(ya, yb) - 0.012, 0.0), (xf, max(ya, yb) + 0.012, 0.12), "trim_paint",
               skip="+x-z")
    mb.box((xf - leg_p + 0.01, yc - w_out, h_out), (xf, yc + w_out, top_z), "trim_paint", skip="+x")
    mb.box((xf - 0.21, yc - w_out - leg_w - 0.07, top_z), (xf, yc + w_out + leg_w + 0.07, top_z + 0.045),
           "trim_paint", skip="+x")
    mb.box((xf - 0.17, yc - w_out - leg_w - 0.03, top_z - 0.035), (xf, yc + w_out + leg_w + 0.03, top_z),
           "trim_paint", skip="+x")
    made.append(mb.build("fireplace_surround", coll, recalc=True))

    mb = MeshBuilder()
    mb.box((xf - 0.46, yc - w_out - leg_w - 0.06, 0.0), (xf, yc + w_out + leg_w + 0.06, 0.025), "hearth_tile",
           skip="-z+x")
    made.append(mb.build("fireplace_hearth", coll))
    return made


def build():
    made = []
    for wall in plan.WALLS:
        for o in wall.openings:
            if o.kind in ("door", "opening"):
                made += build_door(wall, o)
            elif o.kind == "window":
                made += build_window(wall, o)
    made += build_skirting()
    made += build_coving()
    made += build_fireplace()
    return made
