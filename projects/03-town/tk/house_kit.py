"""Modular house kit (docs/ART_BIBLE.md): clapboard walls, corner boards,
sash windows, doors and screen doors, three porch styles, three roof shapes,
gutters and downpipes, chimneys.

Every piece is a function that adds geometry to a MeshBuilder in the house's
local frame: x along the front (left to right as seen from the street), y
into the house, z up, with the ground floor at z = 0 (as in the player's
house) and the yard at z = -0.45. kit_houses() turns each plan.KitHouse into
one merged object with shared materials, so a house costs one draw call per
material, and stores the kit pieces themselves in a hidden "kit" collection.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from .core import MeshBuilder, collection, ground_grime, jitter_color, lerp, light, mul

GROUND = plan.GROUND
STOREY = 2.9
EAVE = 2 * STOREY - 0.05             # top of the walls
WALL_T = 0.25
BOARD = 0.20                         # clapboard exposure
BOARD_T = 0.022                      # how far the bottom of a board stands out
NEUTRAL = 0.75                       # mean of the neutral albedo maps (derive.py)

GF_SILL, GF_HEAD = 0.85, 2.25
FF_SILL, FF_HEAD = STOREY + 0.80, STOREY + 2.15
DOOR_W, DOOR_H = 0.95, 2.10

DOOR_COLOURS = [(0.10, 0.17, 0.13), (0.30, 0.09, 0.07), (0.12, 0.14, 0.20), (0.24, 0.18, 0.12), (0.30, 0.29, 0.26)]


def paint(key):
    """Vertex colour that gives a painted surface the plan's albedo."""
    return mul(plan.PAINTS[key], 1.0 / NEUTRAL)


# --- Walls --------------------------------------------------------------------

class WallFace:
    """One outside wall face: origin, along and outward directions, length."""

    def __init__(self, p0, a, n, length, name):
        self.p0, self.a, self.n = Vector((*p0, 0)), Vector((*a, 0)), Vector((*n, 0))
        self.length, self.name = length, name

    def at(self, u, z, off=0.0):
        return self.p0 + self.a * u + self.n * off + Vector((0, 0, z))


def wall_faces(w, d):
    return {
        "front": WallFace((0, 0), (1, 0), (0, -1), w, "front"),
        "right": WallFace((w, 0), (0, 1), (1, 0), d, "right"),
        "back": WallFace((w, d), (-1, 0), (0, 1), w, "back"),
        "left": WallFace((0, d), (0, -1), (-1, 0), d, "left"),
    }


def clapboard(mb: MeshBuilder, wf: WallFace, openings, z0, z1, colour, rng, wear, gable=None):
    """Real stepped clapboard rows from z0 to z1, cut round the openings.

    openings: (u0, u1, zb, zt). gable: (eave_z, slope) to clip the rows to a
    triangle that peaks at the middle of the wall."""
    raw_wood = (0.62, 0.58, 0.52)
    k = 0
    z = z0
    while z < z1 - 1e-4:
        r0, r1 = z, min(z + BOARD, z1)
        row_col = jitter_color(rng, colour, 0.05)
        cuts = sorted({r0, r1, *[c for o in openings for c in (o[2], o[3]) if r0 < c < r1]})
        for a, b in zip(cuts, cuts[1:]):
            mid = (a + b) / 2
            blocked = sorted((o[0], o[1]) for o in openings if o[2] < mid < o[3])
            spans, cur = [], 0.0
            for u0, u1 in blocked:
                if u0 > cur:
                    spans.append((cur, u0))
                cur = max(cur, u1)
            if cur < wf.length:
                spans.append((cur, wf.length))
            for s0, s1 in spans:
                if s1 - s0 < 0.02:
                    continue
                col = row_col
                if wear > 0.3 and rng.random() < (wear - 0.3) * 0.22:
                    col = lerp(row_col, raw_wood, rng.uniform(0.5, 0.9))       # paint gone
                off_a = BOARD_T * (r1 - a) / (r1 - r0)
                off_b = BOARD_T * (r1 - b) / (r1 - r0)
                if gable:
                    ez, slope = gable
                    half = wf.length / 2

                    def lim(zz):
                        return min(half, (zz - ez) / slope) if zz > ez else 0.0
                    la, lb = lim(a), lim(b)
                    if la >= half - 0.01:
                        continue
                    pa0, pa1 = max(s0, la), min(s1, wf.length - la)
                    pb0, pb1 = max(s0, lb), min(s1, wf.length - lb)
                    if pa1 - pa0 < 0.02:
                        continue
                    pts = [wf.at(pa0, a, off_a), wf.at(pa1, a, off_a), wf.at(max(pb1, pb0), b, off_b), wf.at(pb0, b, off_b)]
                else:
                    pts = [wf.at(s0, a, off_a), wf.at(s1, a, off_a), wf.at(s1, b, off_b), wf.at(s0, b, off_b)]
                # one texture plank per geometric board
                v0 = k * 0.1 + (a - r0) / BOARD * 0.1
                v1 = k * 0.1 + (b - r0) / BOARD * 0.1
                u0, u1 = (wf.at(s0, 0) - wf.p0).length / 2.4, (wf.at(s1, 0) - wf.p0).length / 2.4
                uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
                mb.face(pts, "siding", uvs=uvs, color=col)
                if abs(a - r0) < 1e-6 and not gable:                       # the lip under the board
                    mb.face([wf.at(s0, a, 0.0), wf.at(s1, a, 0.0), wf.at(s1, a, BOARD_T), wf.at(s0, a, BOARD_T)],
                            "siding", color=mul(col, 0.7))
        z += BOARD
        k += 1


def board_on_wall(mb, wf, u0, u1, z0, z1, depth, mat, colour, off0=0.0):
    """A flat trim board standing `depth` proud of the wall face (front, sides and top)."""
    p = [wf.at(u0, z0, off0 + depth), wf.at(u1, z0, off0 + depth), wf.at(u1, z1, off0 + depth), wf.at(u0, z1, off0 + depth)]
    mb.face(p, mat, color=colour)
    q = [wf.at(u0, z0, off0), wf.at(u1, z0, off0), wf.at(u1, z1, off0), wf.at(u0, z1, off0)]
    mb.face([q[1], q[2], p[2], p[1]], mat, color=colour)
    mb.face([q[3], q[0], p[0], p[3]], mat, color=colour)
    mb.face([q[2], q[3], p[3], p[2]], mat, color=colour)
    mb.face([q[0], q[1], p[1], p[0]], mat, color=mul(colour, 0.8))


# --- Windows and doors ------------------------------------------------------------

def sash_window(mb: MeshBuilder, wf: WallFace, u0, width, sill, head, trim, state, rng, lit_light=None):
    """A double-hung sash window in a board casing, recessed into the wall.
    state: "ok", "boarded", "broken", "lit"."""
    u1 = u0 + width
    c = 0.10
    dirt = mul(trim, 0.92)
    # casing, head with drip cap, sill and apron
    board_on_wall(mb, wf, u0 - c, u0, sill, head + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u1, u1 + c, sill, head + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c, u1 + c, head, head + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.02, u1 + c + 0.02, head + c, head + c + 0.03, 0.045, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.03, u1 + c + 0.03, sill - 0.045, sill, 0.07, "trim", dirt, BOARD_T)
    board_on_wall(mb, wf, u0 - c, u1 + c, sill - 0.20, sill - 0.045, 0.02, "trim", dirt, BOARD_T)
    # reveal: the jambs going into the wall
    depth = 0.12
    for uu, sgn in ((u0, 1), (u1, -1)):
        mb.face([wf.at(uu, sill, BOARD_T), wf.at(uu, head, BOARD_T), wf.at(uu, head, -depth), wf.at(uu, sill, -depth)]
                if sgn > 0 else
                [wf.at(uu, sill, -depth), wf.at(uu, head, -depth), wf.at(uu, head, BOARD_T), wf.at(uu, sill, BOARD_T)],
                "trim", color=mul(trim, 0.85))
    mb.face([wf.at(u0, head, -depth), wf.at(u1, head, -depth), wf.at(u1, head, BOARD_T), wf.at(u0, head, BOARD_T)],
            "trim", color=mul(trim, 0.7))
    mb.face([wf.at(u0, sill, BOARD_T), wf.at(u1, sill, BOARD_T), wf.at(u1, sill, -depth), wf.at(u0, sill, -depth)],
            "trim", color=dirt)
    # what is behind the glass
    back = -depth - 0.35
    behind = "window_lit" if state == "lit" else "interior_dark"
    mb.face([wf.at(u0, sill, back), wf.at(u1, sill, back), wf.at(u1, head, back), wf.at(u0, head, back)], behind,
            color=(1, 1, 1))
    for uu in (u0, u1):
        mb.face([wf.at(uu, sill, -depth), wf.at(uu, head, -depth), wf.at(uu, head, back), wf.at(uu, sill, back)]
                if uu == u1 else
                [wf.at(uu, sill, back), wf.at(uu, head, back), wf.at(uu, head, -depth), wf.at(uu, sill, -depth)],
                "interior_dark", color=(1, 1, 1))
    if state == "lit":
        # a pulled blind, lit from behind
        bl = head - (head - sill) * 0.62
        mb.face([wf.at(u0 + 0.03, bl, back + 0.05), wf.at(u1 - 0.03, bl, back + 0.05),
                 wf.at(u1 - 0.03, head - 0.02, back + 0.05), wf.at(u0 + 0.03, head - 0.02, back + 0.05)],
                "window_lit", color=(0.8, 0.75, 0.62))
        if lit_light is not None:
            lit_light.append(wf.at((u0 + u1) / 2, (sill + head) / 2, -0.9))
    # two sashes: the upper one outside the lower one
    mid = (sill + head) / 2
    f = 0.055
    for (zb, zt, off) in ((sill, mid + 0.02, -0.075), (mid - 0.02, head, -0.045)):
        for uu0, uu1, zz0, zz1 in ((u0, u0 + f, zb, zt), (u1 - f, u1, zb, zt), (u0, u1, zb, zb + f), (u0, u1, zt - f, zt)):
            board_on_wall(mb, wf, uu0, uu1, zz0, zz1, 0.035, "trim", trim, off)
        mun = (u0 + u1) / 2
        board_on_wall(mb, wf, mun - 0.012, mun + 0.012, zb + f, zt - f, 0.02, "trim", trim, off)    # 2 over 2
        if state == "broken":
            # jagged shards left in the frame
            for _ in range(3):
                su = rng.uniform(u0 + f, u1 - f - 0.15)
                sz = zb + f
                mb.face([wf.at(su, sz, off + 0.01), wf.at(su + rng.uniform(0.1, 0.25), sz, off + 0.01),
                         wf.at(su + rng.uniform(0.0, 0.1), sz + rng.uniform(0.1, 0.35), off + 0.01)], "glass_dirty")
        elif state != "boarded":
            mat = "glass_dirty" if rng.random() < 0.5 else "glass"
            mb.face([wf.at(u0 + f, zb + f, off + 0.012), wf.at(u1 - f, zb + f, off + 0.012),
                     wf.at(u1 - f, zt - f, off + 0.012), wf.at(u0 + f, zt - f, off + 0.012)], mat)
    if state == "boarded":
        n = max(2, int((head - sill) / 0.32))
        for i in range(n):
            zc = sill + (i + 0.5) * (head - sill) / n
            tilt = rng.uniform(-0.12, 0.12)
            h2 = rng.uniform(0.11, 0.15)
            ext = 0.12
            p = [wf.at(u0 - ext, zc - h2 + tilt, 0.06), wf.at(u1 + ext, zc - h2 - tilt, 0.06),
                 wf.at(u1 + ext, zc + h2 - tilt, 0.06), wf.at(u0 - ext, zc + h2 + tilt, 0.06)]
            mb.face(p, "plywood", color=jitter_color(rng, (0.85, 0.8, 0.72), 0.12))
            mb.face([wf.at(u0 - ext, zc - h2 + tilt, 0.04), wf.at(u1 + ext, zc - h2 - tilt, 0.04), p[1], p[0]],
                    "plywood", color=(0.6, 0.56, 0.5))


def front_door(mb: MeshBuilder, wf: WallFace, u0, trim, door_col, screen=True, ajar=0.0):
    u1 = u0 + DOOR_W
    c = 0.11
    board_on_wall(mb, wf, u0 - c, u0, 0.0, DOOR_H + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u1, u1 + c, 0.0, DOOR_H + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c, u1 + c, DOOR_H, DOOR_H + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.02, u1 + c + 0.02, DOOR_H + c, DOOR_H + c + 0.03, 0.045, "trim", trim, BOARD_T)
    inset = -0.10
    for uu, flip in ((u0, False), (u1, True)):
        q = [wf.at(uu, 0, BOARD_T), wf.at(uu, DOOR_H, BOARD_T), wf.at(uu, DOOR_H, inset), wf.at(uu, 0, inset)]
        mb.face(list(reversed(q)) if flip else q, "trim", color=mul(trim, 0.8))
    mb.face([wf.at(u0, DOOR_H, inset), wf.at(u1, DOOR_H, inset), wf.at(u1, DOOR_H, BOARD_T), wf.at(u0, DOOR_H, BOARD_T)],
            "trim", color=mul(trim, 0.7))
    # the leaf: four raised panels
    mb.face([wf.at(u0, 0.0, inset), wf.at(u1, 0.0, inset), wf.at(u1, DOOR_H, inset), wf.at(u0, DOOR_H, inset)], "door",
            color=door_col)
    for zb, zt in ((0.15, 0.95), (1.10, 1.95)):
        for pu0, pu1 in ((u0 + 0.12, u0 + 0.43), (u1 - 0.43, u1 - 0.12)):
            board_on_wall(mb, wf, pu0, pu1, zb, zt, 0.012, "door", mul(door_col, 1.08), inset)
    mb.cylinder(wf.at(u1 - 0.09, 1.0, inset), wf.n * 0.07, 0.025, "chrome_dull", segments=8)
    mb.face([wf.at(u0 - 0.05, 0.0, 0.10), wf.at(u1 + 0.05, 0.0, 0.10), wf.at(u1 + 0.05, 0.0, inset),
             wf.at(u0 - 0.05, 0.0, inset)], "concrete", color=(0.7, 0.68, 0.64))
    if screen:
        sc = mul(trim, 0.95)
        off = 0.05
        for a0, a1, z0, z1 in ((u0, u0 + 0.07, 0.01, DOOR_H - 0.02), (u1 - 0.07, u1, 0.01, DOOR_H - 0.02),
                               (u0, u1, 0.01, 0.17), (u0, u1, 0.95, 1.04), (u0, u1, DOOR_H - 0.1, DOOR_H - 0.02)):
            board_on_wall(mb, wf, a0, a1, z0, z1, 0.028, "trim", sc, off)
        for z0, z1 in ((0.17, 0.95), (1.04, DOOR_H - 0.1)):
            mb.face([wf.at(u0 + 0.07, z0, off + 0.014), wf.at(u1 - 0.07, z0, off + 0.014),
                     wf.at(u1 - 0.07, z1, off + 0.014), wf.at(u0 + 0.07, z1, off + 0.014)], "screen_mesh")


# --- Porches -----------------------------------------------------------------------

def porch(mb: MeshBuilder, h, trim, deck_col, rng, ramps: list):
    """Porch on the front (local y < 0). Returns the steps' footprint for the path."""
    deck_z = -0.02
    if h.porch == "entry":
        x0, x1, depth = h.door_at - 0.9, h.door_at + DOOR_W + 0.9, 1.7
    else:
        x0, x1, depth = -0.15, h.width + 0.15, 2.3
    yf = -depth
    sag = 0.05 * h.wear if h.wear > 0.6 else 0.0          # a tired porch dips at the front corner
    mb.box((x0, yf, GROUND), (x1, -0.0, deck_z), "porch_deck", color=deck_col, rot=True,
           mats={"-y": "trim", "+x": "trim", "-x": "trim"}, skip="-z+y")
    if h.porch == "wrap":
        side_x0 = h.width + 0.15 - 2.2 if h.facing == "n" else -0.15
        side_x1 = side_x0 + 2.2
        mb.box((side_x0, 0.0, GROUND), (side_x1, h.depth * 0.55, deck_z), "porch_deck", color=deck_col, rot=True,
               mats={"+y": "trim", "+x": "trim", "-x": "trim"}, skip="-z-y")
    # lattice skirt: diagonal slats over a dark gap
    mb.face([Vector((x0, yf + 0.02, GROUND)), Vector((x1, yf + 0.02, GROUND)),
             Vector((x1, yf + 0.02, deck_z - 0.08)), Vector((x0, yf + 0.02, deck_z - 0.08))], "interior_dark")
    sk_h = deck_z - 0.08 - GROUND
    xx = x0 - sk_h
    while xx < x1:
        for sgn in (1, -1):
            a0 = max(x0, xx) if sgn > 0 else min(x1, xx + sk_h)
            za = GROUND + (a0 - xx) if sgn > 0 else GROUND + (xx + sk_h - a0)
            a1 = min(x1, xx + sk_h) if sgn > 0 else max(x0, xx)
            zb = GROUND + (a1 - xx) if sgn > 0 else GROUND + (xx + sk_h - a1)
            if abs(a1 - a0) > 0.03:
                d = Vector((0.025, 0, -0.025 * sgn))
                mb.face([Vector((a0, yf - 0.002, za)) - d, Vector((a1, yf - 0.002, zb)) - d,
                         Vector((a1, yf - 0.002, zb)) + d, Vector((a0, yf - 0.002, za)) + d], "trim",
                        color=mul(trim, 0.75))
        xx += 0.22
    # steps down to the path: three risers
    sx0, sx1 = h.door_at - 0.35, h.door_at + DOOR_W + 0.35
    rise = (deck_z - GROUND) / 3
    for k in range(1, 3):
        z = deck_z - rise * k
        mb.box((sx0, yf - 0.28 * k, GROUND), (sx1, yf - 0.28 * (k - 1), z), "porch_deck", color=deck_col, rot=True,
               skip="-z", mats={"-y": "trim"})
    # the collision ramp runs through the step noses, so it starts one tread out from the bottom step
    ramps.append(((sx0, yf - 0.86, GROUND), (sx1, yf, deck_z)))
    # posts, beam, railings
    top = 2.62
    if h.porch == "entry":
        posts = [x0 + 0.08, x1 - 0.08]
    else:
        n = 4 if h.width < 8.5 else 5
        posts = [x0 + 0.08 + (x1 - x0 - 0.16) * i / (n - 1) for i in range(n)]
    for i, px in enumerate(posts):
        dz = sag if i == len(posts) - 1 else 0.0
        mb.box((px - 0.06, yf + 0.04, deck_z - dz), (px + 0.06, yf + 0.16, top - dz), "trim", color=trim, skip="-z")
        mb.box((px - 0.08, yf + 0.02, deck_z - dz), (px + 0.08, yf + 0.18, deck_z + 0.18 - dz), "trim",
               color=mul(trim, 0.85), skip="-z")
    mb.box((x0, yf + 0.03, top - sag), (x1, yf + 0.17, top + 0.18), "trim", color=trim)
    for pa, pb in zip(posts, posts[1:]):
        if pa < sx1 and pb > sx0:                 # the gap over the steps
            continue
        rail(mb, (pa + 0.06, yf + 0.10), (pb - 0.06, yf + 0.10), deck_z, trim, rng, h.wear)
    for px in (x0 + 0.08, x1 - 0.08):
        if h.porch != "wrap" or abs(px - (x0 + 0.08 if h.facing != "n" else x1 - 0.08)) > 0.1:
            rail(mb, (px, yf + 0.16), (px, -0.05), deck_z, trim, rng, h.wear)
    # shed roof from the wall down to the beam
    lo, hi = top + 0.18, STOREY + 0.10
    ov = 0.25
    a, b = Vector((x0 - ov, yf - ov, lo - 0.05)), Vector((x1 + ov, yf - ov, lo - 0.05))
    c, d = Vector((x1 + ov, 0.0, hi)), Vector((x0 - ov, 0.0, hi))
    t = Vector((0, 0, 0.06))
    roof_mat = "roof_tin" if h.wear > 0.75 else "roof_shingle"
    mb.face([a + t, b + t, c + t, d + t], roof_mat, color=(0.9, 0.9, 0.9))
    mb.face([d, c, b, a], "trim", color=mul(trim, 0.75))
    for p, q in ((a, b), (b, c), (d, a)):
        mb.face([p, q, q + t, p + t], "trim", color=trim)
    if h.porch == "wrap":
        sx0w, sx1w = (h.width + 0.15 - 2.2, h.width + 0.15) if h.facing == "n" else (-0.15, 2.05)
        y1 = h.depth * 0.55
        outer = sx1w if h.facing == "n" else sx0w
        for py in (0.3, y1 - 0.1):
            mb.box((outer - 0.06 if h.facing == "n" else outer, py - 0.06, deck_z),
                   (outer if h.facing == "n" else outer + 0.06 * 2, py + 0.06, top), "trim", color=trim, skip="-z")
        rail(mb, (outer - 0.06 if h.facing == "n" else outer + 0.06, 0.4), (outer - 0.06 if h.facing == "n" else outer + 0.06, y1 - 0.2),
             deck_z, trim, rng, h.wear)
        a2 = Vector((sx0w - ov, -ov, lo)); b2 = Vector((sx1w + ov, -ov, lo))
        wall_x = h.width if h.facing == "n" else 0.0
        if h.facing == "n":
            a2, b2, c2, d2 = (Vector((sx1w + ov, 0, lo)), Vector((sx1w + ov, y1 + ov, lo)),
                              Vector((wall_x, y1 + ov, hi)), Vector((wall_x, 0, hi)))
        else:
            a2, b2, c2, d2 = (Vector((sx0w - ov, y1 + ov, lo)), Vector((sx0w - ov, 0, lo)),
                              Vector((wall_x, 0, hi)), Vector((wall_x, y1 + ov, hi)))
        mb.face([a2 + t, b2 + t, c2 + t, d2 + t], roof_mat, color=(0.9, 0.9, 0.9))
        mb.face([d2, c2, b2, a2], "trim", color=mul(trim, 0.75))
    porch_clutter(mb, x0, x1, yf, deck_z, sx0, sx1, rng, h.wear)
    return (sx0, sx1, yf - 0.56)


def porch_clutter(mb, x0, x1, yf, z, sx0, sx1, rng, wear):
    """A chair or a bench, a dead plant in a pot, boxes or a newspaper bundle."""
    spots = [x for x in (x0 + 0.7, x1 - 0.8) if not (sx0 - 0.4 < x < sx1 + 0.4)]
    for i, x in enumerate(spots):
        y = -0.55
        kind = rng.choice(("chair", "bench", "boxes")) if i == 0 else rng.choice(("pot", "boxes", "chair"))
        wood = jitter_color(rng, (0.62, 0.58, 0.52), 0.1)
        if kind == "chair":
            a = rng.uniform(-0.4, 0.4)
            m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(a, 4, "Z")
            c = MeshBuilder()
            c.box((-0.25, -0.25, 0.42), (0.25, 0.22, 0.46), "wood_weathered", color=wood)
            for lx, ly in ((-0.22, -0.22), (0.22, -0.22), (-0.22, 0.19), (0.22, 0.19)):
                c.box((lx - 0.025, ly - 0.025, 0.0), (lx + 0.025, ly + 0.025, 0.42), "wood_weathered", color=wood)
            c.box((-0.25, 0.18, 0.46), (0.25, 0.22, 0.95), "wood_weathered", color=wood)
            mb.extend(c, m)
        elif kind == "bench":
            mb.box((x - 0.6, y - 0.18, z + 0.40), (x + 0.6, y + 0.18, z + 0.44), "wood_weathered", color=wood)
            for lx in (x - 0.55, x + 0.5):
                mb.box((lx, y - 0.16, z), (lx + 0.05, y + 0.16, z + 0.40), "wood_weathered", color=wood)
        elif kind == "pot":
            mb.cylinder((x, y, z), (0, 0, 0.32), 0.17, "brick", segments=10, radius_top=0.21,
                        color=(0.75, 0.5, 0.4))
            mb.disc((x, y, z + 0.29), 0.19, "lawn_leafy", segments=10)
            for k in range(5):
                a = k * 1.25
                mb.tube([(x, y, z + 0.29), (x + math.cos(a) * 0.15, y + math.sin(a) * 0.15, z + 0.55 + 0.1 * (k % 2))],
                        0.008, "bark", segments=3)
        else:
            for k in range(rng.randint(1, 3)):
                bw = rng.uniform(0.3, 0.5)
                bz = z + 0.0 if k < 2 else z + 0.35
                bx = x + (k % 2) * 0.42 - 0.2
                mb.obox((bx, y, bz + 0.17), (bw, bw * 0.8, 0.34), rng.uniform(-0.3, 0.3), "plywood",
                        color=(0.72, 0.6, 0.45))
    if rng.random() < 0.6:                                         # newspapers nobody picked up
        nx = sx1 + 0.25
        for k in range(rng.randint(2, 4)):
            mb.obox((nx + rng.uniform(-0.1, 0.1), yf + 0.4 + rng.uniform(-0.1, 0.1), z + 0.03 + 0.035 * k),
                    (0.3, 0.12, 0.06), rng.uniform(0, 3), "trim", color=(0.62, 0.6, 0.55))


def rail(mb, a, b, z0, trim, rng, wear, height=0.9):
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    if length < 0.25:
        return
    along_x = abs(bx - ax) > abs(by - ay)
    w = 0.035

    def bar(zl, zh):
        if along_x:
            mb.box((min(ax, bx), ay - w, z0 + zl), (max(ax, bx), ay + w, z0 + zh), "trim", color=trim)
        else:
            mb.box((ax - w, min(ay, by), z0 + zl), (ax + w, max(ay, by), z0 + zh), "trim", color=trim)
    bar(height - 0.06, height)
    bar(0.08, 0.13)
    n = int(length / 0.12)
    for i in range(1, n):
        if wear > 0.6 and rng.random() < 0.08:
            continue                                   # a missing baluster
        t = i / n
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        mb.box((x - 0.016, y - 0.016, z0 + 0.13), (x + 0.016, y + 0.016, z0 + height - 0.06), "trim",
               color=mul(trim, 0.95), skip="-z+z")


# --- Roofs ---------------------------------------------------------------------------

def roof(mb: MeshBuilder, h, trim, gutter_col, roof_mat, rng):
    """Returns (ridge_z, list of eave lines for gutters, chimney base point)."""
    w, d = h.width, h.depth
    ov = 0.35
    t = Vector((0, 0, 0.12))
    eaves = []
    rc = (0.85, 0.85, 0.85)
    if h.roof in ("gable_side", "gable_front"):
        side = h.roof == "gable_side"
        span = d if side else w
        pitch = math.radians(34 if side else 40)
        rise = span / 2 * math.tan(pitch)
        ez = EAVE - ov * math.tan(pitch)
        rz = EAVE + rise
        if side:
            L0, L1 = -0.25, w + 0.25
            def P(along, across, z):
                return Vector((along, across, z))
            mid = d / 2
            lo_a, hi_a = -ov, d + ov
        else:
            L0, L1 = -0.25, d + 0.25
            def P(along, across, z):
                return Vector((across, along, z))
            mid = w / 2
            lo_a, hi_a = -ov, w + ov
        # two slopes
        for e_across in (lo_a, hi_a):
            pa, pb = P(L0, e_across, ez), P(L1, e_across, ez)
            pc, pd = P(L1, mid, rz), P(L0, mid, rz)
            pts = [pa, pb, pc, pd] if (e_across == lo_a) == side else [pb, pa, pd, pc]
            mb.face([p + t for p in pts], roof_mat, color=rc)
            mb.face(list(reversed(pts)), "trim", color=mul(trim, 0.7))          # soffit / underside
            mb.face([pts[0], pts[1], pts[1] + t, pts[0] + t], "trim", color=trim)  # fascia
            eaves.append((pa, pb))
        # rake boards at the gable ends
        for L in (L0, L1):
            for e_across in (lo_a, hi_a):
                p, q = P(L, e_across, ez), P(L, mid, rz)
                mb.face([p, q, q + t, p + t] if (L == L0) != side else [q, p, p + t, q + t], "trim", color=trim)
        ridge = (P(L0, mid, rz + 0.12), P(L1, mid, rz + 0.12))
        mb.tube([ridge[0], ridge[1]], 0.06, roof_mat, segments=4, color=rc)
        chimney_at = P(L0 + (L1 - L0) * max(0.0, h.chimney), mid, rz)
        return rz, eaves, chimney_at, ("left", "right") if side else ("front", "back"), ez, pitch
    # hip roof
    pitch = math.radians(30)
    x0, y0, x1, y1 = -ov, -ov, w + ov, d + ov
    ez = EAVE - ov * math.tan(pitch)
    half = min(x1 - x0, y1 - y0) / 2
    rz = ez + half * math.tan(pitch)
    if (x1 - x0) >= (y1 - y0):
        r0, r1 = Vector((x0 + half, (y0 + y1) / 2, rz)), Vector((x1 - half, (y0 + y1) / 2, rz))
    else:
        r0, r1 = Vector(((x0 + x1) / 2, y0 + half, rz)), Vector(((x0 + x1) / 2, y1 - half, rz))
    A, B, C, D = Vector((x0, y0, ez)), Vector((x1, y0, ez)), Vector((x1, y1, ez)), Vector((x0, y1, ez))
    if (x1 - x0) >= (y1 - y0):
        planes = [[A, B, r1, r0], [C, D, r0, r1], [B, C, r1], [D, A, r0]]
    else:
        planes = [[A, B, r0], [B, C, r1, r0], [C, D, r1], [D, A, r0, r1]]
    for pl in planes:
        mb.face([p + t for p in pl], roof_mat, color=rc)
        mb.face(list(reversed(pl)), "trim", color=mul(trim, 0.7))
        mb.face([pl[0], pl[1], pl[1] + t, pl[0] + t], "trim", color=trim)
        eaves.append((pl[0], pl[1]))
    for p, q in ((A, r0), (B, r1 if (x1 - x0) >= (y1 - y0) else r0), (C, r1), (D, r0 if (x1 - x0) >= (y1 - y0) else r1)):
        mb.tube([p + t * 1.1, q + t * 1.1], 0.05, roof_mat, segments=4, color=rc)
    mb.tube([r0 + t * 1.1, r1 + t * 1.1], 0.06, roof_mat, segments=4, color=rc)
    chimney_at = r0.lerp(r1, max(0.0, h.chimney))
    return rz, eaves, chimney_at, (), ez, pitch


def gutters(mb: MeshBuilder, eaves, col, ground=GROUND):
    for pa, pb in eaves:
        d = (pb - pa)
        if d.length < 0.5:
            continue
        a = d.normalized()
        out = Vector((a.y, -a.x, 0))                    # eaves run with the house on the left of a
        z = pa.z + 0.02
        p0, p1 = pa + out * 0.02, pb + out * 0.02
        lo = Vector((0, 0, -0.10))
        o = out * 0.12
        mb.face([p0 + lo, p1 + lo, p1 + lo + o, p0 + lo + o], "metal_painted", color=col)
        mb.face([p0 + lo + o, p1 + lo + o, p1 + o, p0 + o], "metal_painted", color=col)
        mb.face([p1 + lo, p0 + lo, p0, p1], "metal_painted", color=mul(col, 0.8))
        for end, inward in ((p0, a), (p1, -a)):
            top = end + inward * 0.15 + out * 0.06 + lo
            wall_pt = top - out * 0.42
            mb.tube([top, top + Vector((0, 0, -0.15)), wall_pt + Vector((0, 0, -0.45))], 0.035, "metal_painted",
                    segments=6, color=col)
            mb.tube([wall_pt + Vector((0, 0, -0.45)), Vector((wall_pt.x, wall_pt.y, ground + 0.25)),
                     Vector((wall_pt.x, wall_pt.y, ground + 0.25)) + out * 0.25 + Vector((0, 0, -0.18))],
                    0.035, "metal_painted", segments=6, color=col)


def chimney(mb: MeshBuilder, at: Vector, rz, rng):
    x, y = at.x, at.y
    w, d = 0.62, 0.86
    top = rz + 0.95
    mb.box((x - w / 2, y - d / 2, EAVE - 0.3), (x + w / 2, y + d / 2, top), "brick", skip="-z",
           color=jitter_color(rng, (0.62, 0.58, 0.55), 0.08))
    mb.box((x - w / 2 - 0.05, y - d / 2 - 0.05, top), (x + w / 2 + 0.05, y + d / 2 + 0.05, top + 0.08), "concrete",
           color=(0.55, 0.53, 0.5))
    mb.box((x - 0.14, y - 0.14, top + 0.08), (x + 0.14, y + 0.14, top + 0.30), "interior_dark")


# --- One house ---------------------------------------------------------------------------

def build_house(lot, rng: random.Random):
    """Assemble one kit house. Returns (MeshBuilder in local frame, local->world matrix,
    step ramps (local boxes), lit-window light points (local), path start (local))."""
    h = lot.house
    w, d = h.width, h.depth
    mb = MeshBuilder()
    siding = paint(h.paint)
    trim = paint(h.trim)
    wear = h.wear
    grime = ground_grime(GROUND, 1.1, 0.30 + 0.35 * wear, top_z=EAVE, top_strength=0.15 + 0.2 * wear)
    mb.grime = grime
    door_col = mul(DOOR_COLOURS[rng.randrange(len(DOOR_COLOURS))], 1.0 / NEUTRAL)
    deck_col = (0.9, 0.88, 0.84) if wear < 0.6 else (0.72, 0.70, 0.66)
    faces = wall_faces(w, d)

    # openings per wall: (u0, u1, zb, zt, kind, state)
    def state(tag):
        if tag in h.boarded:
            return "boarded"
        if tag in h.broken:
            return "broken"
        if tag == h.lit:
            return "lit"
        return "ok"

    openings = {k: [] for k in faces}
    for i, (u, ww) in enumerate(h.windows_gf):
        openings["front"].append((u, u + ww, GF_SILL, GF_HEAD, "win", state(f"gf{i}")))
    for i, (u, ww) in enumerate(h.windows_ff):
        openings["front"].append((u, u + ww, FF_SILL, FF_HEAD, "win", state(f"ff{i}")))
    openings["front"].append((h.door_at, h.door_at + DOOR_W, 0.0, DOOR_H, "door", "ok"))
    for side in ("left", "right"):
        for frac, sill, head in ((0.3, GF_SILL, GF_HEAD), (0.68, GF_SILL, GF_HEAD), (0.3, FF_SILL, FF_HEAD),
                                 (0.68, FF_SILL, FF_HEAD)):
            if rng.random() < 0.25:
                continue
            u = d * frac - 0.45
            st = "boarded" if rng.random() < wear * 0.4 else ("broken" if rng.random() < wear * 0.15 else "ok")
            openings[side].append((u, u + 0.9, sill, head, "win", st))
    for frac, sill, head in ((0.25, GF_SILL, GF_HEAD), (0.25, FF_SILL, FF_HEAD), (0.7, FF_SILL, FF_HEAD)):
        openings["back"].append((w * frac - 0.5, w * frac + 0.5, sill, head, "win",
                                 "boarded" if rng.random() < wear * 0.4 else "ok"))
    openings["back"].append((w * 0.62, w * 0.62 + 0.9, 0.0, DOOR_H, "door", "ok"))

    # roof first: it says which walls carry a gable
    roof_mat = "roof_slate" if h.roof == "hip" else "roof_shingle"
    rz, eaves, chimney_at, gable_walls, ez, pitch = roof(mb, h, trim, trim, roof_mat, rng)

    lit_points: list = []
    for key, wf in faces.items():
        ops = [(o[0] - 0.10, o[1] + 0.10, o[2] - (0.20 if o[4] == "win" else 0.0), o[3] + 0.13) for o in openings[key]]
        clapboard(mb, wf, ops, 0.18, EAVE, siding, rng, wear)
        if key in gable_walls:
            span = wf.length
            clapboard(mb, wf, [], EAVE, EAVE + span / 2 * math.tan(pitch) + 0.05, siding, rng, wear,
                      gable=(EAVE, math.tan(pitch)))
        # water table at the bottom, frieze under the eaves
        board_on_wall(mb, wf, 0.0, wf.length, 0.0, 0.18, 0.03, "trim", mul(trim, 0.85))
        board_on_wall(mb, wf, 0.0, wf.length, EAVE - 0.22, EAVE, 0.03, "trim", trim, BOARD_T)
        # foundation below the siding
        mb.face([wf.at(0, GROUND - 0.05, 0.0), wf.at(wf.length, GROUND - 0.05, 0.0), wf.at(wf.length, 0.0, 0.0),
                 wf.at(0, 0.0, 0.0)], "concrete", color=(0.62, 0.6, 0.56))
        for o in openings[key]:
            if o[4] == "win":
                sash_window(mb, wf, o[0], o[1] - o[0], o[2], o[3], trim, o[5], rng, lit_points)
            elif key == "front":
                front_door(mb, wf, o[0], trim, door_col, screen=h.screen_door)
            else:
                front_door(mb, wf, o[0], trim, mul(door_col, 0.8), screen=False)
    # corner boards
    for key, wf in faces.items():
        for u0, u1 in ((0.0, 0.12), (wf.length - 0.12, wf.length)):
            board_on_wall(mb, wf, u0, u1, 0.0, EAVE, 0.035, "trim", trim, BOARD_T)
    # a lid over the top of the walls (seen through the gable vents only, but keeps the shell closed)
    mb.face([Vector((0, 0, EAVE)), Vector((0, d, EAVE)), Vector((w, d, EAVE)), Vector((w, 0, EAVE))], "interior_dark")
    gutters(mb, eaves, mul(trim, 0.9))
    if h.chimney >= 0:
        chimney(mb, chimney_at, rz, rng)
    ramps: list = []
    mb.grime = None
    steps = porch(mb, h, trim, deck_col, rng, ramps)
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    m = Matrix(((ax, bx, 0, ox), (ay, by, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))
    return mb, m, ramps, lit_points, steps


def kit_houses(coll="houses"):
    """Build every kit house in plan.HOUSES. Returns {lot key: (object, matrix, ramps, steps)}."""
    out = {}
    for i, lot in enumerate(plan.HOUSES):
        rng = random.Random(100 + i)
        mb, m, ramps, lit_points, steps = build_house(lot, rng)
        world = MeshBuilder()
        world.extend(mb, m)
        obj = world.build(f"house_{lot.key}", coll)
        obj["lot"] = lot.key
        obj["address"] = lot.address
        for k, p in enumerate(lit_points):
            light(f"lit_window_{lot.key}_{k}", m @ p, "point", 18.0, (1.0, 0.62, 0.32), coll="lights", radius=0.2)
        out[lot.key] = (obj, m, ramps, steps)
    return out


def kit_reference(coll="kit"):
    """The kit pieces on their own, in a hidden collection: one wall bay, each
    window state, the door, each porch style and each roof shape. Kept in the
    .blend as the catalogue the houses are assembled from."""
    from types import SimpleNamespace
    rng = random.Random(1)
    col = collection(coll)
    col.hide_render = True
    col.hide_viewport = True
    x = 0.0
    trim = paint("trim_cream")
    wf = WallFace((0, 0), (1, 0), (0, -1), 2.4, "front")
    for st in ("ok", "boarded", "broken", "lit"):
        mb = MeshBuilder()
        clapboard(mb, wf, [(0.6, 1.8, 0.65, 2.38)], 0.0, 3.0, paint("sage"), rng, 0.4)
        sash_window(mb, wf, 0.7, 1.0, GF_SILL, GF_HEAD, trim, st, rng)
        o = mb.build(f"kit_wall_window_{st}", coll)
        o.location.x = x
        x += 3.0
    mb = MeshBuilder()
    clapboard(mb, wf, [(0.6, 1.8, 0.0, 2.23)], 0.0, 3.0, paint("dusty_blue"), rng, 0.4)
    front_door(mb, wf, 0.73, trim, DOOR_COLOURS[0])
    o = mb.build("kit_wall_door", coll)
    o.location.x = x
    x += 3.0
    for style in ("full", "entry", "wrap"):
        for shape in ("gable_side", "gable_front", "hip"):
            h = SimpleNamespace(width=7.0, depth=7.0, porch=style, roof=shape, door_at=2.0, wear=0.4, facing="s",
                                chimney=0.5)
            mb = MeshBuilder()
            porch(mb, h, trim, (0.9, 0.88, 0.84), rng, [])
            roof(mb, h, trim, trim, "roof_shingle", rng)
            o = mb.build(f"kit_{style}_porch_{shape}_roof", coll)
            o.location.x = x
            x += 10.0
