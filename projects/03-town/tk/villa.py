"""The villa on L10 (13 Ashgrove Street) and the cottage on L4 (15 Ashgrove Street).

Two houses with builders of their own (plan.KitHouse.kind "villa" and
"cottage"), made in the kit's local frame and returning what
house_kit.build_house returns: (mb, m, ramps, lit_points, steps).

    x along the front, 0 to width (facing "n": x 0 is the east end),
    y from the front wall (0) back to depth, front yard at y < 0,
    z up, ground floor at 0, the yard at house_kit.GROUND (-0.45).

- **The villa**: the house the mill owner's family would have built, two
  tall storeys under a low hip roof with a deep bracketed cornice. A
  symmetrical five-bay front of tall sash windows with louvred shutters, a
  stone portico of four columns in the middle carrying a balcony with a
  turned balustrade and a French door onto it, a double door under a
  fanlight, corner pilasters, a canted bay window on the east side, a brick
  chimney breast up the west side and a second stack through the roof, an
  iron cresting round the flat top of the roof. Closed for years: shutters
  hanging by one hinge or gone, a window boarded, slates missing, a
  downpipe broken off, moss on the north slope and on the steps.
  The main block stands 0.7 m in from both ends of the footprint so the bay
  (east) and the chimney breast (west) stay inside it at ground level.
- **The cottage**: one storey of clapboard under a steep front gable, a
  little gabled hood on brackets over a concrete stoop, two front windows,
  two on the Mill Road side, a brick chimney on the ridge. Closed up and
  going: a window broken, one boarded, shingles missing, a downpipe snapped
  off; yet a lamp burns in the front room (its light is the one lit point).

Materials are the town's (core.MATS); colour, paint loss and grime ride in
the vertex colours as on the kit houses.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector

import plan
from . import facade, house_detail
from .core import MeshBuilder, ground_grime, jitter_color, lerp, mul
from .house_kit import (BOARD_T, DOOR_COLOURS, DOOR_H, DOOR_W, GROUND, NEUTRAL, WallFace, board_on_wall,
                        clapboard, front_door, paint, sash_window)

UP = Vector((0.0, 0.0, 1.0))
STONE = (0.80, 0.78, 0.72)                 # limestone-look concrete
SHUTTER_GREEN = mul((0.11, 0.15, 0.12), 1.0 / NEUTRAL)
IRON = (0.16, 0.15, 0.14)


# --- small geometry helpers ----------------------------------------------------------

def _matrix(h):
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    return Matrix(((ax, bx, 0, ox), (ay, by, 0, oy), (0, 0, 1, 0), (0, 0, 0, 1)))


def _newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        n.x += (p.y - q.y) * (p.z + q.z)
        n.y += (p.z - q.z) * (p.x + q.x)
        n.z += (p.x - q.x) * (p.y + q.y)
    return n


def _face(mb, pts, mat, want, color=None, uvs=None):
    """A face whose normal points along `want`, whatever order its corners come in."""
    pts = [Vector(p) for p in pts]
    if _newell(pts).dot(Vector(want)) < 0:
        pts.reverse()
        if uvs is not None:
            uvs = list(reversed(uvs))
    mb.face(pts, mat, color=color, uvs=uvs)


def _plane(mb, pts, eave_a, eave_b, mat, color, tile, lift=0.0):
    """A roof plane facing up, its texture rows running along the eave a->b."""
    pts = [Vector(p) for p in pts]
    n = _newell(pts).normalized()
    if n.z < 0:
        n = -n
    a, b = Vector(eave_a), Vector(eave_b)
    e = (b - a).normalized()
    s = n.cross(e)
    if s.z < 0:
        s = -s
    uvs = [((p - a).dot(e) / tile, (p - a).dot(s) / tile) for p in pts]
    _face(mb, [p + n * lift for p in pts], mat, n, color=color, uvs=uvs)
    return n


def _wf(p, q, name):
    """A WallFace from 2D point p to q with the outside on the right hand (seen from above)."""
    p, q = Vector((*p, 0.0)), Vector((*q, 0.0))
    d = q - p
    a = d.normalized()
    return WallFace((p.x, p.y), (a.x, a.y), (a.y, -a.x), d.length, name)


def _faces(x0, y0, x1, y1):
    """The four outside faces of a box of walls, named and oriented as house_kit.wall_faces."""
    return {"front": _wf((x0, y0), (x1, y0), "front"), "right": _wf((x1, y0), (x1, y1), "right"),
            "back": _wf((x1, y1), (x0, y1), "back"), "left": _wf((x0, y1), (x0, y0), "left")}


def _band(mb, wf, wrap, ua, ub, z0, z1, depth, colour, off0=0.0):
    """A trim board from u=ua to ub; `wrap` at an end (u < 0 or u > length) carries it
    past the corner by its depth, so it closes the corner with the side wall's board."""
    e = depth + off0 if wrap else 0.0
    board_on_wall(mb, wf, ua - (e if ua <= 0.0 else 0.0), ub + (e if ub >= wf.length else 0.0), z0, z1, depth, "trim",
                  colour, off0)


def _wbox(mb, wf, ua, ub, za, zb, oa, ob, mat, colour=None, skip=()):
    facade.wbox(mb, wf, ua, ub, za, zb, oa, ob, mat, colour, skip=skip)


def _wquad(mb, wf, ua, ub, za, zb, off, mat, colour=None, uvs=None):
    _face(mb, [wf.at(ua, za, off), wf.at(ub, za, off), wf.at(ub, zb, off), wf.at(ua, zb, off)], mat, wf.n, colour, uvs)


def _card(mb, wf, ua, ub, za, zb, off, mat, colour=None):
    """A decal card on a wall with the texture's whole square on it."""
    _wquad(mb, wf, ua, ub, za, zb, off, mat, colour, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def _moss_band(mb, a, b, a2, b2, normal, lift=0.012):
    """Moss (the decal is dense along v=0 and clears towards v=1) from the edge a-b up to
    a2-b2, its texture repeating along the edge so the band can be as long as the edge."""
    reps = max(1.0, round((Vector(b) - Vector(a)).length / 1.6))
    n = Vector(normal).normalized() * lift
    _face(mb, [Vector(a) + n, Vector(b) + n, Vector(b2) + n, Vector(a2) + n], "decal_moss", normal,
          uvs=[(0, 0), (reps, 0), (reps, 1), (0, 1)])


# Scroll console profile: (out from the wall, down from the top), a quarter ellipse.
_CONSOLE = [(0.0, 0.0), (0.46, 0.0), (0.46, -0.07), (0.31, -0.12), (0.19, -0.21), (0.11, -0.33), (0.06, -0.50),
            (0.0, -0.50)]


def _console(mb, wf, u, z_top, off0, scale, colour, width=0.09):
    """A scroll bracket under an eave or a hood: its top along the soffit, its back on the wall."""
    prof = [(off0 + o * scale, z_top + dz * scale) for o, dz in _CONSOLE]
    for side in (-1, 1):
        uu = u + side * width / 2
        _face(mb, [wf.at(uu, z, o) for o, z in prof], "trim", wf.a * side, colour)
    cz = sum(z for _, z in prof) / len(prof)
    co = sum(o for o, _ in prof) / len(prof)
    for (oa, za), (ob, zb) in zip(prof, prof[1:] + prof[:1]):
        mo, mz = (oa + ob) / 2 - co, (za + zb) / 2 - cz
        want = wf.n * mo + UP * mz
        _face(mb, [wf.at(u - width / 2, za, oa), wf.at(u + width / 2, za, oa), wf.at(u + width / 2, zb, ob),
                   wf.at(u - width / 2, zb, ob)], "trim", want, mul(colour, 0.9 if mz < 0 else 1.0))
    # a drop under the scroll
    _wbox(mb, wf, u - width / 2 - 0.01, u + width / 2 + 0.01, z_top - 0.56 * scale, z_top - 0.48 * scale, off0,
          off0 + 0.09 * scale, "trim", mul(colour, 0.95))


def _shutter(mb, wf, a0, sw, sill, head, col, rng, hang=0.0, pivot=(0.0, 0.0), off=0.03):
    """One louvred shutter from u=a0 to a0+sw. `hang`: radians it has swung round
    `pivot` (u, z), its lower hinge gone."""
    c, s = math.cos(hang), math.sin(hang)
    pu, pz = pivot

    def P(u, z, o):
        du, dz = u - pu, z - pz
        out = o + (abs(du) * 0.06 if hang else 0.0)          # a loose one leans off the wall
        return wf.at(pu + du * c - dz * s, pz + du * s + dz * c, out)

    fo = off + 0.03
    jc = jitter_color(rng, col, 0.06)
    mid = (sill + head) / 2
    # stiles the full height, rails between them (nothing overlaps in one plane)
    for ua, ub, za, zb in ((a0, a0 + 0.05, sill, head), (a0 + sw - 0.05, a0 + sw, sill, head),
                           (a0 + 0.05, a0 + sw - 0.05, sill, sill + 0.07), (a0 + 0.05, a0 + sw - 0.05, head - 0.07, head),
                           (a0 + 0.05, a0 + sw - 0.05, mid - 0.035, mid + 0.035)):
        mb.face([P(ua, za, fo), P(ub, za, fo), P(ub, zb, fo), P(ua, zb, fo)], "trim", color=jc)
    # edges, so it has a thickness from the side
    corners = [(a0, sill), (a0 + sw, sill), (a0 + sw, head), (a0, head)]
    centre = P(a0 + sw / 2, mid, off)
    for (ua, za), (ub, zb) in zip(corners, corners[1:] + corners[:1]):
        want = P((ua + ub) / 2, (za + zb) / 2, off) - centre
        _face(mb, [P(ua, za, off), P(ub, zb, off), P(ub, zb, fo), P(ua, za, fo)], "trim", want, mul(jc, 0.8))
    n = max(4, int((head - sill - 0.16) / 0.085))
    step = (head - sill - 0.16) / n
    for k in range(n):
        z = sill + 0.08 + k * step
        if z + step * 0.9 > mid - 0.04 and z < mid + 0.04:
            continue
        ua, ub = a0 + 0.05, a0 + sw - 0.05
        mb.face([P(ua, z, fo), P(ub, z, fo), P(ub, z + step * 0.9, off + 0.004), P(ua, z + step * 0.9, off + 0.004)],
                "trim", color=mul(jc, 0.82))
    mb.face([P(a0 + 0.04, sill + 0.05, off + 0.002), P(a0 + sw - 0.04, sill + 0.05, off + 0.002),
             P(a0 + sw - 0.04, head - 0.05, off + 0.002), P(a0 + 0.04, head - 0.05, off + 0.002)], "interior_dark")


def _shutters(mb, wf, u0, width, sill, head, col, rng, modes=("ok", "ok"), sw=0.36):
    """A pair of shutters outside the casing. modes per side: "ok", "hang" (swung down
    on its top hinge), "drop" (further), "gone"."""
    for side, mode in enumerate(modes):
        if mode == "gone":
            # the hinge pins are all that is left
            hu = u0 - 0.115 if side == 0 else u0 + width + 0.115
            for z in (sill + 0.15, head - 0.15):
                _wbox(mb, wf, hu - 0.02, hu + 0.02, z - 0.02, z + 0.02, BOARD_T, BOARD_T + 0.04, "metal_rust", (0.5, 0.45, 0.4))
            continue
        a0 = u0 - 0.115 - sw if side == 0 else u0 + width + 0.115
        hang = 0.0
        pivot = (0.0, 0.0)
        if mode in ("hang", "drop"):
            ang = math.radians(rng.uniform(9, 16) if mode == "hang" else rng.uniform(28, 38))
            if side == 0:                      # hinged on its right edge, the left edge drops
                hang, pivot = ang, (a0 + sw, head - 0.12)
            else:
                hang, pivot = -ang, (a0, head - 0.12)
        _shutter(mb, wf, a0, sw, sill, head, col, rng, hang, pivot)


def _turned(mb, x, y, z0, h, col):
    zs = [z0, z0 + 0.12, z0 + 0.30, z0 + 0.48, z0 + h]
    radii = [0.024, 0.042, 0.024, 0.032, 0.022]
    mb.tube([(x, y, z) for z in zs], 0.03, "trim", segments=5, color=col, radii=radii)


def _balustrade(mb, a, b, z0, h, col, rng, wear, spacing=0.17, broken=False):
    """Bottom rail, handrail and turned balusters from a to b (plan points), on z0."""
    a, b = Vector((a[0], a[1], z0)), Vector((b[0], b[1], z0))
    d = b - a
    L = d.length
    e = d / L
    ang = math.atan2(e.y, e.x)
    mid = (a + b) / 2
    mb.obox(mid + Vector((0, 0, 0.065)), (L, 0.10, 0.07), ang, "trim", color=mul(col, 0.9))
    mb.obox(mid + Vector((0, 0, h - 0.035)), (L, 0.13, 0.07), ang, "trim", color=col)
    n = max(1, int(L / spacing))
    gone = rng.randrange(1, n) if (broken and n > 2) else -1
    for i in range(1, n):
        p = a + e * (L * i / n)
        if i == gone:
            # snapped: the top half hangs from the rail, the rest lies on the floor
            mb.tube([(p.x, p.y, z0 + h - 0.07), (p.x + 0.03, p.y, z0 + h - 0.32)], 0.025, "trim", segments=5,
                    color=mul(col, 0.8))
            mb.obox((p.x + 0.12, p.y - 0.18, z0 + 0.03), (0.05, 0.42, 0.05), ang + 0.6, "trim", color=mul(col, 0.8))
            continue
        if wear > 0.4 and rng.random() < 0.04:
            continue
        _turned(mb, p.x, p.y, z0 + 0.10, h - 0.17, mul(col, rng.uniform(0.9, 1.0)))


def _post(mb, x, y, z0, h, col, w=0.17):
    mb.box((x - w / 2, y - w / 2, z0), (x + w / 2, y + w / 2, z0 + h), "trim", color=col, skip="-z")
    mb.box((x - w / 2 - 0.025, y - w / 2 - 0.025, z0 + h), (x + w / 2 + 0.025, y + w / 2 + 0.025, z0 + h + 0.05), "trim",
           color=col)
    mb.cylinder((x, y, z0 + h + 0.05), (0, 0, 0.09), 0.06, "trim", segments=8, radius_top=0.02, color=col, caps="none")


def _column(mb, x, y, z0, z1, col):
    """A Tuscan column: square plinth, torus, tapering shaft, echinus, abacus."""
    mb.box((x - 0.2, y - 0.2, z0), (x + 0.2, y + 0.2, z0 + 0.18), "trim", color=mul(col, 0.92), skip="-z")
    mb.cylinder((x, y, z0 + 0.18), (0, 0, 0.07), 0.18, "trim", segments=12, radius_top=0.165, caps="top", color=col)
    mb.cylinder((x, y, z0 + 0.25), (0, 0, z1 - 0.22 - (z0 + 0.25)), 0.15, "trim", segments=12, radius_top=0.128,
                caps="none", color=col)
    mb.cylinder((x, y, z1 - 0.22), (0, 0, 0.08), 0.135, "trim", segments=12, radius_top=0.18, caps="none", color=col)
    mb.box((x - 0.2, y - 0.2, z1 - 0.14), (x + 0.2, y + 0.2, z1), "trim", color=col, skip="+z")


def _chimney_stack(mb, x0, y0, x1, y1, z0, top, rng, pots=2):
    """Brick stack from z0 to top with a corbelled band, a stone cap and clay pots."""
    brick = jitter_color(rng, (0.62, 0.56, 0.52), 0.06)
    mb.box((x0, y0, z0), (x1, y1, top - 0.35), "brick", color=brick, skip="-z")
    mb.box((x0 - 0.06, y0 - 0.06, top - 0.35), (x1 + 0.06, y1 + 0.06, top - 0.12), "brick", color=mul(brick, 0.95))
    mb.box((x0 - 0.02, y0 - 0.02, top - 0.12), (x1 + 0.02, y1 + 0.02, top), "brick", color=brick)
    mb.box((x0 - 0.08, y0 - 0.08, top), (x1 + 0.08, y1 + 0.08, top + 0.08), "concrete", color=(0.55, 0.53, 0.5))
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    long_x = (x1 - x0) >= (y1 - y0)
    for k in range(pots):
        t = (k + 0.5) / pots - 0.5
        px = cx + t * (x1 - x0) * 0.6 if long_x else cx
        py = cy if long_x else cy + t * (y1 - y0) * 0.6
        mb.cylinder((px, py, top + 0.08), (0, 0, 0.38 + 0.06 * k), 0.12, "brick", segments=8, radius_top=0.1,
                    color=(0.72, 0.45, 0.33), caps="none")
        mb.disc((px, py, top + 0.40 + 0.06 * k), 0.095, "interior_dark", segments=8)


def _pipe_clamps(mb, pts, col):
    for p in pts:
        mb.cylinder(p - Vector((0, 0, 0.02)), (0, 0, 0.04), 0.045, "metal_painted", segments=6, color=col)


def _gutter(mb, p0, p1, out, col):
    """A half-round-ish box gutter hung on the fascia from p0 to p1 (the top of the fascia)."""
    out = Vector(out)
    lo = Vector((0, 0, -0.11))
    o = out * 0.13
    a, b = Vector(p0) + out * 0.015, Vector(p1) + out * 0.015
    _face(mb, [a + lo, b + lo, b + lo + o, a + lo + o], "metal_painted", -UP, mul(col, 0.8))
    _face(mb, [a + lo + o, b + lo + o, b + o + UP * 0.01, a + o + UP * 0.01], "metal_painted", out, col)
    _face(mb, [a + lo, b + lo, b, a], "metal_painted", out, mul(col, 0.7))
    _face(mb, [a + lo + o * 0.1, b + lo + o * 0.1, b + lo + o * 0.9, a + lo + o * 0.9], "interior_dark", UP)
    side = (b - a).normalized()
    for p, sgn in ((a, -1), (b, 1)):
        _face(mb, [p + lo, p + lo + o, p + o, p], "metal_painted", side * sgn, col)


# --- the villa ------------------------------------------------------------------------------

V_INSET = 0.7                    # the main block stands this far in from both ends of the footprint
V_STY = 3.15                     # storey height
V_EAVE = 2 * V_STY               # 6.30: top of the walls, underside of the cornice
V_FRIEZE = V_EAVE - 0.50         # frieze board from here to the eave
V_GF = (0.65, 2.75)              # sill, head
V_FF = (V_STY + 0.70, V_STY + 2.45)
V_WIN_W = 1.0
V_OV = 0.44                      # cornice overhang (its crown moulding reaches 0.5)
V_FASCIA = 0.28
V_PITCH = math.radians(27)
V_DECK = 2.2                     # the flat top of the hip roof (each way, at least)
V_STACK_TOP = 10.25
PORT_Z = 3.0                     # underside of the portico entablature
BALC_Z = 3.38                    # the balcony floor on top of it
DECK_Z = -0.02                   # portico floor (as the kit's porch decks)


def _villa_windows(cx, x0, x1, D):
    """Every window of the villa: (face, u0, width, sill, head, state, shutters or None, tag)."""
    gs, gh = V_GF
    fs, fh = V_FF
    w = V_WIN_W
    out = []
    bays = [cx - 4.2, cx - 2.1, cx + 2.1, cx + 4.2]
    gf_modes = [("ok", "hang"), None, None, ("gone", "ok")]
    ff_modes = [("drop", "ok"), ("ok", "ok"), ("hang", "ok"), ("ok", "gone")]
    for i, bx in enumerate(bays):
        u0 = bx - x0 - w / 2
        out.append(("front", u0, w, gs, gh, "boarded" if i == 3 else "ok", gf_modes[i], f"gf{i}"))
        out.append(("front", u0, w, fs, fh, "ok", ff_modes[i], f"ff{i}"))
    # east side (u runs from the back corner to the front): the bay below, one window over it, a pair further back
    out.append(("left", D - 3.6 - w / 2, w, fs, fh, "ok", ("ok", "ok"), "e_ff0"))
    out.append(("left", D - 8.6 - w / 2, w, gs, gh, "ok", ("hang", "ok"), "e_gf1"))
    out.append(("left", D - 8.6 - w / 2, w, fs, fh, "ok", ("ok", "ok"), "e_ff1"))
    # west side (u = y): either side of the chimney breast
    for k, y in enumerate((2.2, D - 2.6)):
        out.append(("right", y - w / 2, w, gs, gh, "ok", ("ok", "ok"), f"w_gf{k}"))
        out.append(("right", y - w / 2, w, fs, fh, "broken" if k == 1 else "ok", ("ok", "gone" if k == 1 else "ok"),
                    f"w_ff{k}"))
    # back (u from the west corner): no shutters
    bw = x1 - x0
    for u, st in ((1.3, "ok"), (bw - 2.0 - w, "ok")):
        out.append(("back", u, w, gs, gh, st, None, "b_gf"))
    for u in (1.3, bw / 2 - w / 2 - 0.3, bw - 2.0 - w):
        out.append(("back", u, w, fs, fh, "ok", None, "b_ff"))
    return out


def _double_door(mb, wf, uc, width, leaf_h, fan_h, trim, door_col, rng):
    """A pair of panelled doors under a fanlight, in a surround with a keystone."""
    u0, u1 = uc - width / 2, uc + width / 2
    cz = leaf_h + 0.06
    top = cz + fan_h
    c = 0.16
    inset = -0.12
    face = BOARD_T + 0.012
    # surround: pilaster casings on plinth blocks, a head and a cornice cap
    board_on_wall(mb, wf, u0 - c, u0, 0.0, top, 0.04, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u1, u1 + c, 0.0, top, 0.04, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.015, u0, 0.0, 0.32, 0.055, "trim", mul(trim, 0.88), BOARD_T)
    board_on_wall(mb, wf, u1, u1 + c + 0.015, 0.0, 0.32, 0.055, "trim", mul(trim, 0.88), BOARD_T)
    board_on_wall(mb, wf, u0 - c, u1 + c, top, top + 0.12, 0.04, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.05, u1 + c + 0.05, top + 0.12, top + 0.18, 0.085, "trim", trim, BOARD_T)
    # jambs
    for uu, sgn in ((u0, 1), (u1, -1)):
        _face(mb, [wf.at(uu, 0.0, face), wf.at(uu, cz, face), wf.at(uu, cz, inset), wf.at(uu, 0.0, inset)], "trim",
              wf.a * sgn, mul(trim, 0.8))
    # stone threshold
    _face(mb, [wf.at(u0, 0.0, BOARD_T + 0.08), wf.at(u1, 0.0, BOARD_T + 0.08), wf.at(u1, 0.0, inset),
               wf.at(u0, 0.0, inset)], "concrete", UP, (0.7, 0.68, 0.63))
    # the two leaves, four raised panels each, an astragal where they meet
    for a, b in ((u0, uc), (uc, u1)):
        _wquad(mb, wf, a, b, 0.0, leaf_h, inset, "door", door_col)
        for zb, zt in ((0.16, 0.92), (1.08, leaf_h - 0.14)):
            board_on_wall(mb, wf, a + 0.11, b - 0.11, zb, zt, 0.014, "door", mul(door_col, 1.08), inset)
    board_on_wall(mb, wf, uc - 0.018, uc + 0.018, 0.0, leaf_h, 0.02, "door", mul(door_col, 0.9), inset)
    for du in (-0.07, 0.07):
        mb.cylinder(wf.at(uc + du, 1.02, inset), wf.n * 0.065, 0.024, "chrome_dull", segments=8)
    # a notice taped to the right leaf, long since faded
    _wquad(mb, wf, uc + 0.18, uc + 0.48, 1.30, 1.70, inset + 0.016, "trim", (0.86, 0.84, 0.76))
    # transom bar
    board_on_wall(mb, wf, u0, u1, leaf_h, cz, 0.05, "trim", trim, inset)
    # the fanlight: a half ellipse of glass with radial bars, the dark hall behind
    n = 10
    rx, rz = width / 2, fan_h
    arc = [(uc - rx * math.cos(math.pi * i / n), cz + rz * math.sin(math.pi * i / n)) for i in range(n + 1)]
    for i in range(n):
        tri = [(uc, cz), arc[i], arc[i + 1]]
        _face(mb, [wf.at(u, z, inset + 0.02) for u, z in tri], "window_glass", wf.n)
        _face(mb, [wf.at(u, z, inset - 0.3) for u, z in tri], "interior_dark", wf.n)
    for i in range(2, n, 2):
        (pu, pz), (qu, qz) = (uc, cz), arc[i]
        L = math.hypot(qu - pu, qz - pz)
        nu, nz = -(qz - pz) / L * 0.014, (qu - pu) / L * 0.014
        _face(mb, [wf.at(pu + nu, pz + nz, inset + 0.04), wf.at(qu + nu, qz + nz, inset + 0.04),
                   wf.at(qu - nu, qz - nz, inset + 0.04), wf.at(pu - nu, pz - nz, inset + 0.04)], "trim", wf.n, trim)
    _wbox(mb, wf, uc - 0.07, uc + 0.07, cz, cz + 0.07, inset + 0.02, inset + 0.05, "trim", trim)   # the hub
    # the spandrels, flush with the surround, and the arch's soffit back to the glass
    for corner, rng_i in (((u0, top), range(0, n // 2)), ((u1, top), range(n // 2, n))):
        for i in rng_i:
            _face(mb, [wf.at(*corner, face), wf.at(*arc[i], face), wf.at(*arc[i + 1], face)], "trim", wf.n,
                  mul(trim, 0.95))
    for i in range(n):
        (au, az), (bu, bz) = arc[i], arc[i + 1]
        mu, mz = (au + bu) / 2, (az + bz) / 2
        want = wf.a * (uc - mu) + UP * (cz - mz)
        _face(mb, [wf.at(au, az, face), wf.at(bu, bz, face), wf.at(bu, bz, inset), wf.at(au, az, inset)], "trim", want,
              mul(trim, 0.78))
    # keystone
    _wbox(mb, wf, uc - 0.08, uc + 0.08, top - 0.17, top + 0.13, face, face + 0.06, "trim", mul(trim, 1.02))


def _french_door(mb, wf, u0, width, z0, z1, trim, rng):
    """A pair of glazed doors onto the balcony, in a cased opening like the windows'."""
    u1 = u0 + width
    c = 0.10
    board_on_wall(mb, wf, u0 - c, u0, z0, z1, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u1, u1 + c, z0, z1, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c, u1 + c, z1, z1 + c, 0.025, "trim", trim, BOARD_T)
    board_on_wall(mb, wf, u0 - c - 0.03, u1 + c + 0.03, z1 + c, z1 + c + 0.05, 0.06, "trim", trim, BOARD_T)
    depth = 0.14
    for uu, sgn in ((u0, 1), (u1, -1)):
        _face(mb, [wf.at(uu, z0, BOARD_T), wf.at(uu, z1, BOARD_T), wf.at(uu, z1, -depth), wf.at(uu, z0, -depth)], "trim",
              wf.a * sgn, mul(trim, 0.85))
    _face(mb, [wf.at(u0, z1, BOARD_T), wf.at(u1, z1, BOARD_T), wf.at(u1, z1, -depth), wf.at(u0, z1, -depth)], "trim",
          -UP, mul(trim, 0.7))
    _face(mb, [wf.at(u0, z0, BOARD_T + 0.05), wf.at(u1, z0, BOARD_T + 0.05), wf.at(u1, z0, -depth),
               wf.at(u0, z0, -depth)], "trim", UP, mul(trim, 0.8))
    facade.window_inside(mb, wf, u0, u1, z0 + 0.05, z1, depth, "ok", rng, [], None)
    off = -depth + 0.04
    um = (u0 + u1) / 2
    f = 0.06
    for a, b in ((u0, um), (um, u1)):
        board_on_wall(mb, wf, a, a + f, z0, z1, 0.04, "trim", trim, off)
        board_on_wall(mb, wf, b - f, b, z0, z1, 0.04, "trim", trim, off)
        board_on_wall(mb, wf, a + f, b - f, z0, z0 + 0.46, 0.04, "trim", trim, off)
        board_on_wall(mb, wf, a + f, b - f, z1 - f, z1, 0.04, "trim", trim, off)
        board_on_wall(mb, wf, a + f + 0.05, b - f - 0.05, z0 + 0.08, z0 + 0.38, 0.012, "trim", mul(trim, 0.95), off + 0.04)
        g0, g1 = z0 + 0.46, z1 - f
        for k in (1, 2, 3):
            zz = g0 + (g1 - g0) * k / 4
            board_on_wall(mb, wf, a + f, b - f, zz - 0.012, zz + 0.012, 0.025, "trim", trim, off)
        board_on_wall(mb, wf, (a + b) / 2 - 0.012, (a + b) / 2 + 0.012, g0, g1, 0.025, "trim", trim, off)
        _wquad(mb, wf, a + f, b - f, g0, g1, off + 0.012, "window_glass")


def _portico(mb, cx, half, yf, trim, rng, wear, ramps):
    """Stone platform and steps, four columns, the entablature and the balcony on top.
    Returns the inner columns' x (the steps run between them) and the steps' x."""
    x0p, x1p = cx - half, cx + half
    stone = STONE
    # the platform: a stone slab with a nosing on a stone base
    mb.box((x0p + 0.03, yf + 0.03, GROUND), (x1p - 0.03, 0.0, DECK_Z - 0.07), "concrete", color=mul(stone, 0.92),
           skip="-z")
    mb.box((x0p, yf, DECK_Z - 0.07), (x1p, 0.0, DECK_Z), "concrete", color=stone)
    # three stone steps up between two cheek blocks
    sx0, sx1 = cx - 1.25, cx + 1.25
    rise = (DECK_Z - GROUND) / 3
    for k, (ya, yb) in ((1, (yf - 0.3, yf + 0.03)), (2, (yf - 0.6, yf - 0.3))):
        mb.box((sx0, ya, GROUND), (sx1, yb, DECK_Z - rise * k), "concrete", color=jitter_color(rng, stone, 0.05),
               skip="-z+y")
    for xa, xb in ((sx0 - 0.26, sx0), (sx1, sx1 + 0.26)):
        mb.box((xa, yf - 0.62, GROUND), (xb, yf + 0.03, DECK_Z + 0.05), "concrete", color=mul(stone, 0.96), skip="-z")
    ramps.append(((sx0, yf - 0.9, GROUND), (sx1, yf, DECK_Z)))
    # columns: a pair either side of the steps, engaged pilasters on the wall behind the outer ones
    yc = yf + 0.28
    cols = [x0p + 0.3, sx0 - 0.3, sx1 + 0.3, x1p - 0.3]
    for i, x in enumerate(cols):
        col = jitter_color(rng, trim, 0.04)
        if i == 3 and wear > 0.3:
            col = lerp(col, (0.62, 0.58, 0.52), 0.35)          # paint gone off the weather side
        _column(mb, x, yc, DECK_Z, PORT_Z, col)
    # entablature, ceiling (old porch-ceiling blue), cornice, balcony floor
    e0, e1, ef = x0p - 0.05, x1p + 0.05, yf - 0.05
    mb.box((e0, ef, PORT_Z), (e1, 0.0, PORT_Z + 0.30), "trim", color=trim, skip="-z+y")
    _face(mb, [(e0, ef, PORT_Z), (e1, ef, PORT_Z), (e1, 0.0, PORT_Z), (e0, 0.0, PORT_Z)], "trim", -UP, (0.62, 0.74, 0.76))
    mb.box((e0 + 0.01, ef - 0.012, PORT_Z + 0.09), (e1 - 0.01, ef, PORT_Z + 0.11), "trim", color=mul(trim, 0.85))
    mb.box((e0 - 0.06, ef - 0.06, PORT_Z + 0.30), (e1 + 0.06, 0.0, BALC_Z), "trim", color=mul(trim, 0.95),
           skip="+y", mats={"+z": "roof_tin"})
    # the balcony: newel posts and a turned balustrade, one baluster snapped
    bz = BALC_Z
    hb = 0.92
    yb = ef + 0.07
    posts = [(e0 + 0.08, yb), (cols[1], yb), (cols[2], yb), (e1 - 0.08, yb)]
    pc = mul(trim, 0.97)
    for px, py in posts:
        _post(mb, px, py, bz, hb, pc)
    for (ax, ay), (bx, by) in zip(posts, posts[1:]):
        _balustrade(mb, (ax + 0.085, ay), (bx - 0.085, by), bz, hb, trim, rng, wear, broken=(ax == cols[1]))
    for sx in (e0 + 0.08, e1 - 0.08):
        _post(mb, sx, -0.12, bz, hb, pc)
        _balustrade(mb, (sx, yb + 0.085), (sx, -0.205), bz, hb, trim, rng, wear)
    # a lantern hangs from the ceiling over the doors, its glass broken
    lx, ly = cx, yf * 0.5
    mb.tube([(lx, ly, PORT_Z), (lx, ly, PORT_Z - 0.38)], 0.008, "metal_rust", segments=4)
    mb.cylinder((lx, ly, PORT_Z - 0.01), (0, 0, 0.01), 0.07, "metal_painted", segments=8, color=IRON)
    lz = PORT_Z - 0.38
    mb.box((lx - 0.12, ly - 0.12, lz - 0.05), (lx + 0.12, ly + 0.12, lz), "metal_painted", color=IRON)
    for dx, dy in ((-0.1, -0.1), (0.1, -0.1), (0.1, 0.1), (-0.1, 0.1)):
        mb.box((lx + dx - 0.012, ly + dy - 0.012, lz - 0.42), (lx + dx + 0.012, ly + dy + 0.012, lz - 0.05), "metal_painted",
               color=IRON)
    mb.box((lx - 0.1, ly - 0.1, lz - 0.42), (lx + 0.1, ly + 0.1, lz - 0.05), "glass_dirty", skip="-y")
    mb.box((lx - 0.1, ly - 0.1, lz - 0.30), (lx + 0.1, ly - 0.098, lz - 0.05), "glass_dirty")      # a shard left in front
    mb.box((lx - 0.11, ly - 0.11, lz - 0.47), (lx + 0.11, ly + 0.11, lz - 0.42), "metal_painted", color=IRON)
    return cols, (sx0, sx1)


def _villa_roof(mb, x0, y0, x1, y1, trim, rng, wear):
    """The cornice (soffit, fascia, crown), the hip roof with its flat top and iron
    cresting. Returns (eave z of the roof surface, function z(x, y) of the roof)."""
    ov = V_OV
    rx0, ry0, rx1, ry1 = x0 - ov, y0 - ov, x1 + ov, y1 + ov
    ez = V_EAVE + V_FASCIA
    tp = math.tan(V_PITCH)
    T = (min(rx1 - rx0, ry1 - ry0) - V_DECK) / 2
    zt = ez + T * tp
    A, B, C, D = (Vector((rx0, ry0, ez)), Vector((rx1, ry0, ez)), Vector((rx1, ry1, ez)), Vector((rx0, ry1, ez)))
    A2, B2, C2, D2 = (Vector((rx0 + T, ry0 + T, zt)), Vector((rx1 - T, ry0 + T, zt)), Vector((rx1 - T, ry1 - T, zt)),
                      Vector((rx0 + T, ry1 - T, zt)))
    slate = (0.46, 0.47, 0.51)
    for p, q, q2, p2 in ((A, B, B2, A2), (B, C, C2, B2), (C, D, D2, C2), (D, A, A2, D2)):
        _plane(mb, [p, q, q2, p2], p, q, "roof_slate", jitter_color(rng, slate, 0.03), 3.0)
    # hip and top rolls
    for p, q in ((A, A2), (B, B2), (C, C2), (D, D2)):
        mb.tube([p + UP * 0.03, q + UP * 0.03], 0.05, "roof_slate", segments=4, color=(0.7, 0.7, 0.72))
    # the flat top: tin, a curb, the cresting
    _face(mb, [A2 + UP * 0.02, B2 + UP * 0.02, C2 + UP * 0.02, D2 + UP * 0.02], "roof_tin", UP, (0.62, 0.6, 0.58))
    ring = [A2, B2, C2, D2]
    for p, q in zip(ring, ring[1:] + ring[:1]):
        mb.tube([p + UP * 0.05, q + UP * 0.05], 0.05, "metal_painted", segments=4, color=(0.35, 0.34, 0.32))
        mb.tube([p + UP * 0.40, q + UP * 0.40], 0.012, "metal_rust", segments=4, color=(0.6, 0.55, 0.5))
        L = (q - p).length
        n = max(2, int(L / 0.42))
        for i in range(n):
            if wear > 0.4 and rng.random() < 0.12:
                continue                                    # spikes snapped off
            s = p.lerp(q, (i + 0.5) / n)
            mb.tube([s + UP * 0.05, s + UP * 0.40, s + UP * 0.52], 0.012, "metal_rust", segments=3,
                    radii=[0.012, 0.014, 0.002], color=(0.6, 0.55, 0.5))
    # cornice: soffit from the frieze face out to the fascia, fascia, crown moulding
    fo = BOARD_T + 0.03
    inner = [Vector((x0 - fo, y0 - fo, V_EAVE)), Vector((x1 + fo, y0 - fo, V_EAVE)), Vector((x1 + fo, y1 + fo, V_EAVE)),
             Vector((x0 - fo, y1 + fo, V_EAVE))]
    outer = [Vector((rx0, ry0, V_EAVE)), Vector((rx1, ry0, V_EAVE)), Vector((rx1, ry1, V_EAVE)), Vector((rx0, ry1, V_EAVE))]
    for i in range(4):
        j = (i + 1) % 4
        _face(mb, [inner[i], inner[j], outer[j], outer[i]], "trim", -UP, mul(trim, 0.78))
        p, q = outer[i], outer[j]
        out = (q - p).normalized().cross(UP)
        _face(mb, [p, q, q + UP * V_FASCIA, p + UP * V_FASCIA], "trim", out, trim)
        # crown: a box along the fascia top; the front and back ones run past the corners
        e = (q - p).normalized()
        a0 = p - e * (0.06 if i in (0, 2) else 0.0)
        a1 = q + e * (0.06 if i in (0, 2) else 0.0)
        pts = [a0, a1, a1 + out * 0.06, a0 + out * 0.06]
        bot = [v + UP * (V_FASCIA - 0.10) for v in pts]
        topp = [v + UP * (V_FASCIA + 0.03) for v in pts]
        _face(mb, [bot[2], bot[3], topp[3], topp[2]], "trim", out, mul(trim, 1.02))
        _face(mb, bot, "trim", -UP, mul(trim, 0.75))
        _face(mb, topp, "trim", UP, mul(trim, 0.9))
        if i in (0, 2):
            for k0, k1 in ((0, 3), (1, 2)):
                _face(mb, [bot[k0], bot[k1], topp[k1], topp[k0]], "trim", e * (-1 if k0 == 0 else 1), trim)
    # a ragged patch of missing slates on the north (front) slope, and moss low on it
    n0 = Vector((0.0, -1.0, 1.0 / tp)).normalized()
    if wear > 0.3:
        cxp = rx0 + (rx1 - rx0) * rng.uniform(0.25, 0.35)
        cyp = ry0 + 1.6
        k = 15
        ring2 = []
        for i in range(k):
            ang = 2 * math.pi * i / k
            r = rng.uniform(0.25, 0.65) if i % 2 else rng.uniform(0.45, 0.65)
            x, y = cxp + math.cos(ang) * r * 1.5, cyp + math.sin(ang) * r
            ring2.append(Vector((x, y, ez + (y - ry0) * tp + 0.014)))
        c = Vector((cxp, cyp, ez + (cyp - ry0) * tp + 0.014))
        for i in range(k):
            _face(mb, [c, ring2[i], ring2[(i + 1) % k]], "interior_dark", n0, (0.7, 0.7, 0.7))
        for i in range(4):                         # loose slates slid down into the cornice
            sx = cxp + rng.uniform(-0.8, 0.8)
            mb.obox((sx, ry0 + 0.3, ez + 0.3 * tp + 0.05), (0.28, 0.42, 0.012), rng.uniform(-0.3, 0.3), "roof_slate",
                    color=(0.65, 0.65, 0.68), tilt=(V_PITCH + rng.uniform(-0.08, 0.08), 0.0))
    band = 0.9                                     # moss low on the north slope, hip to hip
    _moss_band(mb, A, B, Vector((rx0 + band, ry0 + band, ez + band * tp)), Vector((rx1 - band, ry0 + band, ez + band * tp)),
               n0)

    def roof_z(x, y):
        d = min(x - rx0, rx1 - x, y - ry0, ry1 - y, T)
        return ez + max(0.0, d) * tp
    return ez, roof_z


def _bay(mb, east_wf, x0, yc, face_w, trim, siding, rng, wear, openings):
    """A canted bay window on the east wall: three clapboard faces with a sash window
    each, a frieze and a low tin roof against the wall. It fills the footprint's
    east strip (from x 0 to the main wall at x0)."""
    out = x0
    wall_w = face_w + 2 * out
    W1, C1 = (x0, yc + wall_w / 2), (0.0, yc + face_w / 2)
    C0, W0 = (0.0, yc - face_w / 2), (x0, yc - wall_w / 2)
    segs = [_wf(W1, C1, "bay1"), _wf(C1, C0, "bay2"), _wf(C0, W0, "bay3")]
    top = 3.15
    gs, gh = V_GF
    states = ["ok", "ok", "ok"]
    for k, wf in enumerate(segs):
        L = wf.length
        ww = 1.0 if k == 1 else 0.55
        u0 = (L - ww) / 2
        clapboard(mb, wf, [(u0 - 0.10, u0 + ww + 0.10, gs - 0.20, gh + 0.13)], 0.18, top, siding, rng, wear)
        board_on_wall(mb, wf, -0.01, L + 0.01, 0.0, 0.18, 0.03, "trim", mul(trim, 0.85))
        board_on_wall(mb, wf, 0.0, L, top - 0.20, top, 0.03, "trim", trim, BOARD_T)
        board_on_wall(mb, wf, 0.0, L, top - 0.24, top - 0.20, 0.045, "trim", trim, BOARD_T)
        _wbox(mb, wf, -0.03, L + 0.03, GROUND - 0.08, 0.02, 0.0, 0.05, "concrete", (0.62, 0.6, 0.56))
        for ua, ub in ((0.0, 0.08), (L - 0.08, L)):
            board_on_wall(mb, wf, ua, ub, 0.18, top - 0.24, 0.03, "trim", trim, BOARD_T)
        sash_window(mb, wf, u0, ww, gs, gh, trim, states[k], rng, [], wear=wear)
        openings.setdefault(wf.name, []).append((u0, u0 + ww, gs, gh, "win", states[k]))
    # beads closing the outside corners between the faces
    for wa, wb in ((segs[0], segs[1]), (segs[1], segs[2])):
        p = wb.p0
        a = p + wa.n * (BOARD_T + 0.03)
        b = p + wb.n * (BOARD_T + 0.03)
        _face(mb, [a, b, b + UP * top, a + UP * top], "trim", (wa.n + wb.n), trim)
    # the roof: offset outline, a soffit lid, fascia, three tin facets up to the wall
    ov = 0.14

    def off_line(wf):
        p = Vector((wf.p0.x, wf.p0.y)) + Vector((wf.n.x, wf.n.y)) * ov
        return p, Vector((wf.a.x, wf.a.y))

    def meet(l1, l2):
        (p, d), (q, e) = l1, l2
        den = d.x * e.y - d.y * e.x
        t = ((q.x - p.x) * e.y - (q.y - p.y) * e.x) / den
        return p + d * t

    l1, l2, l3 = (off_line(s) for s in segs)
    c1e, c0e = meet(l1, l2), meet(l2, l3)
    w1e = l1[0] + l1[1] * ((x0 - l1[0].x) / l1[1].x)
    w0e = l3[0] + l3[1] * ((x0 - l3[0].x) / l3[1].x)
    outline = [w1e, c1e, c0e, w0e]
    zlo, zhi = top + 0.12, top + 0.43
    lid = [Vector((v.x, v.y, top)) for v in outline]
    _face(mb, lid, "trim", -UP, mul(trim, 0.78))
    for p, q in zip(lid, lid[1:]):
        e = (q - p).normalized()
        _face(mb, [p, q, q + UP * 0.12, p + UP * 0.12], "trim", e.cross(UP), trim)
    E = [Vector((v.x, v.y, zlo)) for v in outline]
    P1, P0 = Vector((x0, c1e.y, zhi)), Vector((x0, c0e.y, zhi))
    tin = (0.74, 0.70, 0.66)
    _plane(mb, [E[1], E[2], P0, P1], E[1], E[2], "roof_tin", tin, 1.5)
    _plane(mb, [E[0], E[1], P1], E[0], E[1], "roof_tin", tin, 1.5)
    _plane(mb, [E[2], E[3], P0], E[2], E[3], "roof_tin", tin, 1.5)
    for p, q in ((E[1], P1), (E[2], P0)):
        mb.tube([p + UP * 0.02, q + UP * 0.02], 0.03, "metal_painted", segments=4, color=(0.5, 0.48, 0.45))
    # flashing up the wall along the roof line
    line = [Vector((x0 - 0.035, w1e.y, zlo + 0.03)), Vector((x0 - 0.035, P1.y, zhi + 0.03)),
            Vector((x0 - 0.035, P0.y, zhi + 0.03)), Vector((x0 - 0.035, w0e.y, zlo + 0.03))]
    for p, q in zip(line, line[1:]):
        _face(mb, [p, q, q + UP * 0.06, p + UP * 0.06], "metal_rust", Vector((-1, 0, 0)), (0.6, 0.56, 0.5))


def build_villa(lot, rng: random.Random):
    """The villa: returns (mb in the local frame, local->world matrix, step ramps, lit points, path start)."""
    h = lot.house
    W, D = h.width, h.depth
    x0, x1 = V_INSET, W - V_INSET
    cx = W / 2
    mb = MeshBuilder()
    wear = h.wear
    siding = paint(h.paint)
    trim = paint(h.trim)
    door_col = mul(DOOR_COLOURS[0], 1.0 / NEUTRAL)
    mb.grime = ground_grime(GROUND, 1.3, 0.30 + 0.35 * wear, top_z=V_EAVE, top_strength=0.12 + 0.2 * wear)
    faces = _faces(x0, 0.0, x1, D)
    fwf = faces["front"]
    lit_points: list = []
    ramps: list = []

    # openings, per wall: (u0, u1, zb, zt, kind, state)
    wins = _villa_windows(cx, x0, x1, D)
    openings = {k: [] for k in faces}
    for face, u0, w, s, hd, st, sh, tag in wins:
        openings[face].append((u0, u0 + w, s, hd, "win", st, tag))
    door_w, leaf_h, fan_h = 1.4, 2.2, 0.42
    du = cx - x0
    openings["front"].append((du - door_w / 2, du + door_w / 2, 0.0, leaf_h + 0.06 + fan_h, "double", "ok"))
    fr_w = 1.2
    fr_z0 = BALC_Z + 0.02
    openings["front"].append((du - fr_w / 2, du + fr_w / 2, fr_z0, V_FF[1], "french", "ok"))
    openings["back"].append(((x1 - x0) / 2 + 0.3, (x1 - x0) / 2 + 0.3 + DOOR_W, 0.0, DOOR_H, "door", "ok"))

    # walls: clapboard cut round the openings, water table, frieze, foundation
    for key, wf in faces.items():
        ops = []
        for o in openings[key]:
            if o[4] == "win":
                ops.append((o[0] - 0.10, o[1] + 0.10, o[2] - 0.20, o[3] + 0.13))
            elif o[4] == "double":                      # the surround is 0.16 wide, its cap 0.18 over the top
                ops.append((o[0] - 0.16, o[1] + 0.16, 0.0, o[3] + 0.18))
            elif o[4] == "french":
                ops.append((o[0] - 0.10, o[1] + 0.10, o[2], o[3] + 0.15))
            else:
                ops.append((o[0] - 0.10, o[1] + 0.10, o[2], o[3] + 0.13))
        clapboard(mb, wf, ops, 0.18, V_EAVE, siding, rng, wear)
        wrap = key in ("front", "back")
        L = wf.length
        _band(mb, wf, wrap, 0.0, L, 0.0, 0.18, 0.04, mul(trim, 0.85))
        _band(mb, wf, wrap, 0.0, L, V_FRIEZE, V_EAVE, BOARD_T + 0.03, trim)
        _band(mb, wf, wrap, 0.0, L, V_FRIEZE - 0.05, V_FRIEZE, BOARD_T + 0.06, mul(trim, 0.95))
        # corner pilasters with a base and a capital; the front and back ones wrap the corner
        for ua, ub in ((0.0, 0.30), (L - 0.30, L)):
            _band(mb, wf, wrap, ua, ub, 0.18, V_FRIEZE - 0.25, BOARD_T + 0.04, trim)
            _band(mb, wf, wrap, ua, ub, 0.0, 0.55, BOARD_T + 0.065, mul(trim, 0.9))
            _band(mb, wf, wrap, ua, ub, V_FRIEZE - 0.25, V_FRIEZE - 0.05, BOARD_T + 0.075, trim)
    house_detail.foundation(mb, faces, GROUND, random.Random(sum(map(ord, lot.key)) + 7), wear)

    # windows and their shutters
    for face, u0, w, s, hd, st, sh, tag in wins:
        wf = faces[face]
        sash_window(mb, wf, u0, w, s, hd, trim, st, rng, lit_points, wear=wear)
        if sh is not None:
            _shutters(mb, wf, u0, w, s, hd, SHUTTER_GREEN, rng, sh)
    # doors: the double door under the fanlight, the French door onto the balcony, the back door
    _double_door(mb, fwf, du, door_w, leaf_h, fan_h, trim, door_col, rng)
    _french_door(mb, fwf, du - fr_w / 2, fr_w, fr_z0, V_FF[1], trim, rng)
    _shutters(mb, fwf, du - fr_w / 2, fr_w, fr_z0, V_FF[1], SHUTTER_GREEN, rng, ("ok", "hang"))
    bwf = faces["back"]
    front_door(mb, bwf, (x1 - x0) / 2 + 0.3, trim, mul(door_col, 0.8), screen=False)
    # the portico and the balcony, engaged pilasters on the wall behind the outer columns
    half = 3.2
    yf = -1.9
    cols, (sx0, sx1) = _portico(mb, cx, half, yf, trim, rng, wear, ramps)
    for x in (cols[0], cols[3]):
        board_on_wall(mb, fwf, x - x0 - 0.12, x - x0 + 0.12, 0.0, PORT_Z, 0.06, "trim", mul(trim, 0.95))
    # the bay window on the east side
    _bay(mb, faces["left"], x0, 3.6, 1.6, trim, siding, rng, wear, openings)

    # chimneys: a breast up the west wall, a stack through the roof at the east back
    cy0, cy1 = D / 2 - 1.2, D / 2 + 0.6
    brick = jitter_color(rng, (0.6, 0.54, 0.5), 0.05)
    mb.box((x1, cy0, GROUND - 0.05), (W - 0.03, cy1, V_FRIEZE - 0.25), "brick", color=brick, skip="-z-x+z")
    mb.box((x1, cy0 - 0.03, V_FRIEZE - 0.30), (W, cy1 + 0.03, V_FRIEZE - 0.22), "concrete", color=(0.62, 0.6, 0.56),
           skip="-x")
    sm = (cy0 + cy1) / 2
    _chimney_stack(mb, x1, sm - 0.5, W, sm + 0.5, V_FRIEZE - 0.22, V_STACK_TOP, rng)
    _chimney_stack(mb, x0 + 2.0, D - 3.8, x0 + 2.7, D - 2.9, V_EAVE, V_STACK_TOP - 0.15, rng)

    # cornice brackets in pairs, clear of the chimney and the downpipes
    pipes_u = {"left": (0.6, D - 0.6), "right": (0.6, D - 0.6)}
    for key, wf in faces.items():
        L = wf.length
        n = max(2, round((L - 0.6) / 2.1))
        for i in range(n + 1):
            u = 0.3 + (L - 0.6) * i / n
            for du2 in ((0.0,) if i in (0, n) else (-0.15, 0.15)):
                uu = u + du2
                if key == "right" and cy0 - 0.3 < uu < cy1 + 0.3:
                    continue
                if any(abs(uu - p if key == "right" else (L - uu) - p) < 0.25 for p in pipes_u.get(key, ())):
                    continue
                _console(mb, wf, uu, V_EAVE, BOARD_T + 0.03, 1.0, trim)
    ez, roof_z = _villa_roof(mb, x0, 0.0, x1, D, trim, rng, wear)
    # a vent stack on the back slope
    vx, vy = x1 - 2.6, D - 1.4
    vz = roof_z(vx, vy)
    mb.cylinder((vx, vy, vz - 0.2), (0, 0, 0.6), 0.05, "metal_painted", segments=8, color=(0.5, 0.5, 0.48))
    # downpipes from the box gutter in the cornice, down the side walls; the front east one broken off
    pc = mul(trim, 0.85)
    for key, xw, sgn in (("left", x0, -1), ("right", x1, 1)):
        for y in (0.6, D - 0.6):
            xo = xw + sgn * 0.11
            top = Vector((xw + sgn * (V_OV - 0.12), y, V_EAVE + 0.02))
            bottom = GROUND + 0.22
            if key == "left" and y < 1.0 and wear > 0.3:
                bottom = 1.5                                   # the lower length is gone
            pts = [top, Vector((xw + sgn * 0.3, y, V_EAVE - 0.35)), Vector((xo, y, V_EAVE - 0.6)), Vector((xo, y, bottom))]
            if bottom < 0:
                pts.append(Vector((xw + sgn * 0.3, y, GROUND + 0.06)))
            mb.tube(pts, 0.04, "metal_painted", segments=6, color=pc)
            _pipe_clamps(mb, [Vector((xo, y, z)) for z in (V_EAVE - 1.0, 3.4, 1.2) if z > bottom + 0.1], pc)
            if bottom > 0:
                _card(mb, _wf((xw, y + 0.25), (xw, y - 0.25), "streak") if key == "left" else
                      _wf((xw, y - 0.25), (xw, y + 0.25), "streak"), 0.0, 0.5, GROUND + 0.1, bottom - 0.1,
                      BOARD_T + 0.008, "decal_streaks")

    # stains under the sills and from the cornice; the meter and conduit on the east wall
    house_detail.stains(mb, faces, openings, V_EAVE, rng, wear)
    house_detail.services(mb, faces, GROUND, V_FRIEZE, random.Random(sum(map(ord, lot.key)) + 11), "left")
    # moss and a crack on the steps
    rise = (DECK_Z - GROUND) / 3
    for k, yb in ((1, yf), (2, yf - 0.3)):
        z = DECK_Z - rise * k + 0.004
        _moss_band(mb, (sx0, yb, z), (sx1, yb, z), (sx0, yb - 0.22, z), (sx1, yb - 0.22, z), UP, lift=0.0)
    mb.card((cx + 0.4, yf + 0.6, DECK_Z + 0.004), 1.2, 0.8, 0.3, "decal_crack", flat=True)
    # a lid over the walls (keeps the shell closed)
    _face(mb, [(x0, 0, V_EAVE), (x1, 0, V_EAVE), (x1, D, V_EAVE), (x0, D, V_EAVE)], "interior_dark", -UP)
    mb.grime = None
    steps = (sx0, sx1, yf - 0.6)
    return mb, _matrix(h), ramps, lit_points, steps


# --- the cottage ----------------------------------------------------------------------------

C_EAVE = 2.70                    # top of the walls
C_PITCH = math.radians(46)
C_OV_SIDE, C_OV_RAKE = 0.30, 0.25
C_T = 0.12                       # roof thickness


def _gable_roof(mb, x0, x1, y0, y1, eave, pitch, ov_s, ov_r, t, mat, trim, rng, colour=(0.85, 0.85, 0.85)):
    """A gable roof whose ridge runs along y over x0..x1 (gables at y0 and y1).
    Returns (eave z of the underside at the outer edge, ridge z of the underside)."""
    tp = math.tan(pitch)
    xm = (x0 + x1) / 2
    ez = eave - ov_s * tp
    rz = eave + (xm - x0) * tp
    ya, yb = y0 - ov_r, y1 + ov_r
    for xe in (x0 - ov_s, x1 + ov_s):
        under = [Vector((xe, ya, ez)), Vector((xe, yb, ez)), Vector((xm, yb, rz)), Vector((xm, ya, rz))]
        top = [p + UP * t for p in under]
        n = _plane(mb, top, top[0], top[1], mat, jitter_color(rng, colour, 0.03), 3.0)
        _face(mb, under, "trim", -n, mul(trim, 0.72))
        out = Vector((-1.0 if xe < xm else 1.0, 0.0, 0.0))
        _face(mb, [under[0], under[1], top[1], top[0]], "trim", out, trim)                   # fascia
        # rake boards at both gables, a little deeper than the roof
        for y, sgn in ((ya, -1), (yb, 1)):
            p, q = Vector((xe, y, ez)), Vector((xm, y, rz))
            drop = UP * 0.07
            _face(mb, [p - drop, q - drop, q + UP * t, p + UP * t], "trim", Vector((0, sgn, 0)), trim)
            back = Vector((0, sgn * 0.03, 0))
            _face(mb, [p - drop, q - drop, q - drop - back, p - drop - back], "trim", -UP, mul(trim, 0.8))
            _face(mb, [p - drop - back, q - drop - back, q - back, p - back], "trim", Vector((0, -sgn, 0)), mul(trim, 0.8))
    mb.tube([Vector((xm, ya, rz + t + 0.02)), Vector((xm, yb, rz + t + 0.02))], 0.06, mat, segments=4,
            color=mul(colour, 0.9))
    return ez, rz


def _hood(mb, x0, x1, depth, ze, trim, rng, wf):
    """A little gabled hood over the front door, on two scroll brackets."""
    pitch = math.radians(45)
    xm = (x0 + x1) / 2
    zr = ze + (xm - x0) * math.tan(pitch)
    t = 0.08
    yf = -depth
    for xe in (x0, x1):
        under = [Vector((xe, yf, ze)), Vector((xe, 0.0, ze)), Vector((xm, 0.0, zr)), Vector((xm, yf, zr))]
        top = [p + UP * t for p in under]
        n = _plane(mb, top, top[0], top[1], "roof_shingle", jitter_color(rng, (0.8, 0.8, 0.8), 0.03), 3.0)
        _face(mb, under, "trim", -n, mul(trim, 0.72))
        out = Vector((-1.0 if xe < xm else 1.0, 0, 0))
        _face(mb, [under[0], under[1], top[1], top[0]], "trim", out, trim)
        _face(mb, [Vector((xe, yf, ze - 0.05)), Vector((xm, yf, zr - 0.05)), Vector((xm, yf, zr + t)), Vector((xe, yf, ze + t))],
              "trim", Vector((0, -1, 0)), trim)
    # the pediment, set back under the rake, with a tie board along its foot
    inset = 0.05
    _face(mb, [Vector((x0 + 0.05, yf + inset, ze)), Vector((x1 - 0.05, yf + inset, ze)), Vector((xm, yf + inset, zr - 0.04))],
          "trim", Vector((0, -1, 0)), mul(trim, 0.95))
    mb.box((x0 + 0.03, yf + 0.02, ze - 0.10), (x1 - 0.03, yf + 0.12, ze), "trim", color=trim)
    _face(mb, [Vector((x0 + 0.05, yf + 0.12, ze)), Vector((x1 - 0.05, yf + 0.12, ze)), Vector((x1 - 0.05, 0.0, ze)),
               Vector((x0 + 0.05, 0.0, ze))], "trim", -UP, mul(trim, 0.8))
    for x in (x0 + 0.1, x1 - 0.1):
        _console(mb, wf, x, ze - 0.10, BOARD_T, 1.15, trim, width=0.08)
    # a bare bulb fixture under it, long dead
    mb.cylinder((xm, -depth * 0.5, ze), (0, 0, -0.04), 0.07, "metal_painted", segments=8, color=(0.5, 0.48, 0.44))
    mb.cylinder((xm, -depth * 0.5, ze - 0.04), (0, 0, -0.09), 0.045, "glass_dirty", segments=8, radius_top=0.02)


def _cottage_services(mb, wf, u, eave, ground, rng):
    """Meter, a service mast up through the eave to a weatherhead, the ground wire, a
    hose bib with the hose coiled on its hanger. Returns the weatherhead point."""
    grey = (0.62, 0.62, 0.6)
    _wbox(mb, wf, u - 0.15, u + 0.15, 1.15, 1.6, BOARD_T, 0.12, "metal_painted", grey)
    mb.cylinder(tuple(wf.at(u, 1.42, 0.12)), tuple(wf.n * 0.09), 0.085, "glass_dirty", segments=12, color=(0.8, 0.82, 0.8))
    mast_top = eave + 1.05
    mb.tube([wf.at(u, 1.6, 0.07), wf.at(u, mast_top, 0.07)], 0.028, "metal_painted", segments=6, color=grey)
    head = wf.at(u, mast_top, 0.07)
    mb.tube([head, head + UP * 0.07 + wf.n * 0.07], 0.045, "metal_painted", segments=6, color=mul(grey, 0.8))
    for k in (-1, 1):
        mb.tube([head + wf.a * 0.03 * k + UP * 0.05, head + wf.a * 0.12 * k + UP * -0.1 + wf.n * 0.12], 0.006, "wire",
                segments=3)
    _wbox(mb, wf, u - 0.05, u + 0.05, eave - 0.30, eave - 0.24, 0.04, 0.10, "metal_rust", (0.55, 0.5, 0.45))   # strap
    mb.tube([wf.at(u + 0.05, 1.15, 0.05), wf.at(u + 0.08, 0.0, 0.06), wf.at(u + 0.1, ground + 0.05, 0.09)], 0.004,
            "chrome_dull", segments=3)
    hu = u - 0.9
    bib = wf.at(hu, 0.3, 0.05)
    mb.cylinder(tuple(bib), tuple(wf.n * 0.08), 0.014, "chrome_dull", segments=6)
    hang = wf.at(hu + 0.45, 0.85, 0.04)
    _wbox(mb, wf, hu + 0.37, hu + 0.53, 0.78, 0.86, 0.02, 0.09, "metal_rust", (0.55, 0.5, 0.45))
    green = (0.22, 0.38, 0.2)
    pts = [bib + wf.n * 0.08, wf.at(hu + 0.2, 0.2, 0.09), wf.at(hu + 0.45, 0.86, 0.09)]
    for k in range(10):
        a = 2 * math.pi * k / 9
        pts.append(wf.at(hu + 0.45 + 0.16 * math.sin(a), 0.86 - 0.24 * (1 - math.cos(a)) * 0.5 - 0.02 * k, 0.07 + 0.004 * k))
    mb.tube(pts, 0.012, "toy_plastic", segments=5, color=green)
    del hang
    return head


def _roof_patch(mb, roof_z, cx, cy, rng, normal, r=(0.3, 0.5)):
    """A ragged patch of missing roofing showing the dark felt."""
    k = 15
    ring = []
    for i in range(k):
        ang = 2 * math.pi * i / k
        rr = rng.uniform(*r) * (rng.uniform(0.55, 1.0) if i % 2 else 1.0)
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 1.4
        ring.append(Vector((x, y, roof_z(x, y) + 0.006)))
    c = Vector((cx, cy, roof_z(cx, cy) + 0.006))
    for i in range(k):
        _face(mb, [c, ring[i], ring[(i + 1) % k]], "interior_dark", normal, (0.6, 0.6, 0.6))


def build_cottage(lot, rng: random.Random):
    """The cottage: returns (mb in the local frame, local->world matrix, step ramps, lit points, path start)."""
    h = lot.house
    w, d = h.width, h.depth
    mb = MeshBuilder()
    wear = h.wear
    siding = paint(h.paint)
    trim = paint(h.trim)
    door_col = mul(DOOR_COLOURS[2], 1.0 / NEUTRAL)
    mb.grime = ground_grime(GROUND, 1.1, 0.30 + 0.35 * wear, top_z=C_EAVE, top_strength=0.15 + 0.2 * wear)
    faces = _faces(0.0, 0.0, w, d)
    fwf = faces["front"]
    lit_points: list = []
    ramps: list = []
    tp = math.tan(C_PITCH)
    gs, gh = 0.85, 2.25
    door_at = h.door_at
    dc = door_at + DOOR_W / 2
    ww = 1.05
    # (face, u0, width, sill, head, state, room)
    wins = [("front", dc - 0.475 - 0.49 - ww - 0.04, ww, gs, gh, "lit", "living"),
            ("front", dc + 0.475 + 0.53, ww, gs, gh, "boarded", None),
            ("left", d - 4.6 - 0.45, 0.9, gs, gh, "ok", None),
            ("left", d - 1.75 - 0.45, 0.9, gs, gh, "broken", None),
            ("right", 1.55, 0.9, gs, gh, "ok", None),
            ("right", d - 1.5, 0.6, 1.45, 2.1, "ok", None),
            ("back", 1.0, 1.0, gs, gh, "boarded", None)]
    openings = {k: [] for k in faces}
    for face, u0, ww_, s, hd, st, room in wins:
        openings[face].append((u0, u0 + ww_, s, hd, "win", st))
    openings["front"].append((door_at, door_at + DOOR_W, 0.0, DOOR_H, "door", "ok"))
    openings["back"].append((w - 2.9 - DOOR_W, w - 2.9, 0.0, DOOR_H, "door", "ok"))

    # roof first (its numbers give the gables)
    ez, rz = _gable_roof(mb, 0.0, w, 0.0, d, C_EAVE, C_PITCH, C_OV_SIDE, C_OV_RAKE, C_T, "roof_shingle", trim, rng)

    def roof_z(x, y):
        return ez + C_T + min(x + C_OV_SIDE, w + C_OV_SIDE - x) * tp

    for key, wf in faces.items():
        ops = [(o[0] - 0.10, o[1] + 0.10, o[2] - (0.20 if o[4] == "win" else 0.0), o[3] + 0.13) for o in openings[key]]
        clapboard(mb, wf, ops, 0.18, C_EAVE, siding, rng, wear)
        if key in ("front", "back"):
            clapboard(mb, wf, [], C_EAVE, rz + 0.05, siding, rng, wear, gable=(C_EAVE, tp))
            facade.gable_vent(mb, wf, trim, C_EAVE + (rz - C_EAVE) * 0.5)
        wrap = key in ("front", "back")
        L = wf.length
        _band(mb, wf, wrap, 0.0, L, 0.0, 0.18, BOARD_T + 0.03, mul(trim, 0.85))
        _band(mb, wf, wrap, 0.0, L, C_EAVE - 0.20, C_EAVE, BOARD_T + 0.03, trim)
        for ua, ub in ((0.0, 0.12), (L - 0.12, L)):
            _band(mb, wf, wrap, ua, ub, 0.18, C_EAVE - 0.20, BOARD_T + 0.035, trim)
    house_detail.foundation(mb, faces, GROUND, random.Random(sum(map(ord, lot.key)) + 7), wear)
    for face, u0, ww_, s, hd, st, room in wins:
        sash_window(mb, faces[face], u0, ww_, s, hd, trim, st, rng, lit_points, room_kind=room, wear=wear)
    front_door(mb, fwf, door_at, trim, door_col, screen=True)
    front_door(mb, faces["back"], w - 2.9 - DOOR_W, trim, mul(door_col, 0.8), screen=False)
    # number plaque, kick plate and letter slot (the kit's door dressing, without its lantern: the hood has a light)
    cell = facade.NUMBER_CELL.get(lot.key)
    u1 = door_at + DOOR_W
    if cell is not None:
        cxn, cyn = cell % 3, cell // 3
        uvs = [(cxn / 3, 1 - (cyn + 1) / 2), ((cxn + 1) / 3, 1 - (cyn + 1) / 2), ((cxn + 1) / 3, 1 - cyn / 2),
               (cxn / 3, 1 - cyn / 2)]
        _wquad(mb, fwf, u1 + 0.17, u1 + 0.39, 1.45, 1.615, 0.03, "house_numbers", uvs=uvs)
    _wquad(mb, fwf, door_at + 0.04, u1 - 0.04, 0.03, 0.22, -0.10 + 0.004, "chrome_dull")
    _wbox(mb, fwf, door_at + 0.30, u1 - 0.30, 0.99, 1.04, -0.10 + 0.002, -0.10 + 0.012, "chrome_dull")
    # the hood over the door, the stoop and its steps, a pipe handrail
    _hood(mb, dc - 0.85, dc + 0.85, 0.78, 2.46, trim, rng, fwf)
    sx0, sx1 = dc - 0.82, dc + 0.82
    st0, st1 = dc - 1.12, dc + 1.12
    yf = -0.95
    conc = (0.74, 0.72, 0.68)
    mb.box((st0, yf, GROUND), (st1, 0.0, DECK_Z), "concrete", color=conc, skip="-z")
    rise = (DECK_Z - GROUND) / 3
    for k in (1, 2):
        mb.box((sx0, yf - 0.3 * k, GROUND), (sx1, yf - 0.3 * (k - 1), DECK_Z - rise * k), "concrete",
               color=jitter_color(rng, conc, 0.05), skip="-z+y")
    ramps.append(((sx0, -1.8, GROUND), (sx1, yf, DECK_Z)))
    rx = st1 - 0.1
    rail = mul(IRON, 1.6)
    mb.tube([(rx, yf - 0.5, GROUND), (rx, yf - 0.5, GROUND + 0.9)], 0.02, "metal_painted", segments=6, color=rail)
    mb.tube([(rx, -0.15, DECK_Z), (rx, -0.15, DECK_Z + 0.9)], 0.02, "metal_painted", segments=6, color=rail)
    mb.tube([(rx, yf - 0.62, GROUND + 0.85), (rx, yf - 0.5, GROUND + 0.9), (rx, yf, DECK_Z + 0.9), (rx, -0.15, DECK_Z + 0.9),
             (rx, -0.03, DECK_Z + 0.85)], 0.018, "metal_rust", segments=6, color=(0.75, 0.6, 0.5))
    z = DECK_Z - rise * 2 + 0.004
    _moss_band(mb, (sx0, yf - 0.3, z), (sx1, yf - 0.3, z), (sx0, yf - 0.48, z), (sx1, yf - 0.48, z), UP, lift=0.0)
    mb.card((dc + 0.3, yf * 0.5, DECK_Z + 0.004), 0.9, 0.7, 0.8, "decal_crack", flat=True)

    # chimney on the ridge towards the back, vent stack, missing shingles on the Mill Road slope
    xm = w / 2
    _chimney_stack(mb, xm - 0.30, d - 1.75, xm + 0.30, d - 1.05, C_EAVE, rz + C_T + 0.85, rng, pots=1)
    vx, vy = w - 1.4, d - 2.2
    mb.cylinder((vx, vy, roof_z(vx, vy) - 0.15), (0, 0, 0.5), 0.045, "metal_painted", segments=8, color=(0.55, 0.55, 0.53))
    n_east = Vector((-math.sin(C_PITCH), 0.0, math.cos(C_PITCH)))
    if wear > 0.5:
        _roof_patch(mb, roof_z, 1.3, 2.6, rng, n_east)
        _roof_patch(mb, roof_z, 1.9, 4.6, rng, n_east, r=(0.15, 0.3))
    # moss low on both slopes, along the gutters
    ya_, yb_ = -C_OV_RAKE, d + C_OV_RAKE
    for xe, xi, nrm in ((-C_OV_SIDE, 0.55, n_east), (w + C_OV_SIDE, w - 0.55, Vector((math.sin(C_PITCH), 0.0, math.cos(C_PITCH))))):
        _moss_band(mb, (xe, ya_, roof_z(xe, 0)), (xe, yb_, roof_z(xe, 0)), (xi, ya_, roof_z(xi, 0)), (xi, yb_, roof_z(xi, 0)),
                   nrm, lift=0.008)
    # gutters along both eaves; downpipes at the corners, the front one on Mill Road snapped off
    gc = mul(trim, 0.88)
    ya, yb = -C_OV_RAKE, d + C_OV_RAKE
    for xe, sgn in ((-C_OV_SIDE, -1), (w + C_OV_SIDE, 1)):
        top_e = ez + C_T
        _gutter(mb, (xe, ya + 0.05, top_e), (xe, yb - 0.05, top_e), (sgn, 0, 0), gc)
        xw = (0.0 if sgn < 0 else w) + sgn * 0.075
        for y_end, y_wall in ((ya + 0.2, 0.25), (yb - 0.2, d - 0.25)):
            g = Vector((xe + sgn * 0.08, y_end, top_e - 0.11))
            bottom = GROUND + 0.2
            if sgn < 0 and y_end < 0 and wear > 0.5:
                bottom = 1.1
            pts = [g, g + Vector((0, 0, -0.15)), Vector((xw, y_wall, top_e - 0.55)), Vector((xw, y_wall, bottom))]
            if bottom < 0:
                pts.append(Vector((xw + sgn * 0.04, y_wall + (0.18 if y_wall < d / 2 else -0.18), GROUND + 0.05)))
            mb.tube(pts, 0.035, "metal_painted", segments=6, color=gc)
            _pipe_clamps(mb, [Vector((xw, y_wall, z)) for z in (1.8, 0.6) if z > bottom + 0.1], gc)
    # the meter and a mast for the line from the pole, on the Mill Road side
    _cottage_services(mb, faces["left"], d / 2, C_EAVE, GROUND, rng)
    house_detail.stains(mb, faces, openings, C_EAVE, random.Random(sum(map(ord, lot.key)) + 9), wear)
    # lid over the walls
    _face(mb, [(0, 0, C_EAVE + 0.04), (w, 0, C_EAVE + 0.04), (w, d, C_EAVE + 0.04), (0, d, C_EAVE + 0.04)], "interior_dark",
          -UP)
    mb.grime = None
    steps = (sx0, sx1, yf - 0.6)
    return mb, _matrix(h), ramps, lit_points, steps
