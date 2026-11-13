"""Close-up dressing for the kit houses (detail pass 2): the things a film
camera sees that a game camera in fog does not.

- Behind every pane there is now something: curtains with real folds, a
  venetian blind half down with a few slats askew, a sheet pinned up, or a
  bare dark room. The glass itself is see-through and dirty.
- A few windows are lit and show a real room: wallpaper, a floor, a lamp
  with a glowing shade, a bed or an armchair, a picture on the wall.
- On the houses that face the hero areas: louvred shutters (one hanging),
  brackets under the eaves and at the porch posts, a gable vent, a number
  plaque, a lantern by the door, a kick plate and a letter slot.
- Real porch furniture: a rocking chair, a side table with a mug, a doormat,
  a hanging basket of something long dead.

Everything is built in a wall's own frame through WallFace.at(u, z, off):
u along the wall, z up, off outwards (negative is inside the house).
"""

from __future__ import annotations

import math

from mathutils import Matrix, Vector

from .core import MeshBuilder, jitter_color, mul

HERO = {"L2", "L3", "L4", "L5"}                      # houses beside the player's and on the junction
SHUTTERS = {"L2": (0.16, 0.20, 0.24), "L5": (0.20, 0.17, 0.12)}
EAVE_BRACKETS = {"L3", "L4"}
NUMBER_CELL = {"L2": 0, "L3": 1, "L4": 2, "L5": 3, "L6": 4}
FABRICS = [(0.78, 0.74, 0.64), (0.62, 0.50, 0.48), (0.50, 0.56, 0.48), (0.60, 0.60, 0.62), (0.80, 0.78, 0.72)]
WALLPAPERS = [(0.62, 0.56, 0.44), (0.50, 0.56, 0.52), (0.66, 0.60, 0.58)]


# --- geometry in a wall's frame ---------------------------------------------------

def wquad(mb, wf, ua, ub, za, zb, off, mat, colour=None, uvs=None):
    """A flat panel on the wall plane, facing outwards."""
    mb.face([wf.at(ua, za, off), wf.at(ub, za, off), wf.at(ub, zb, off), wf.at(ua, zb, off)], mat, color=colour, uvs=uvs)


def wbox(mb, wf, ua, ub, za, zb, off_a, off_b, mat, colour=None, inward=False, skip=()):
    """A box in wall coordinates. Faces point out of the box, or into it for a room."""
    lo_o, hi_o = min(off_a, off_b), max(off_a, off_b)
    c = [wf.at(u, z, o) for o in (lo_o, hi_o) for z in (za, zb) for u in (ua, ub)]
    centre = sum(c, Vector()) / 8.0
    faces = {"back": (0, 1, 3, 2), "front": (4, 5, 7, 6), "floor": (0, 1, 5, 4), "ceiling": (2, 3, 7, 6),
             "left": (0, 2, 6, 4), "right": (1, 3, 7, 5)}
    for name, idx in faces.items():
        if name in skip:
            continue
        q = [c[i] for i in idx]
        n = (q[1] - q[0]).cross(q[2] - q[0])
        outward = n.dot((q[0] + q[2]) / 2 - centre) > 0
        if outward == inward:
            q.reverse()
        mb.face(q, mat, color=colour)


# --- behind the glass ------------------------------------------------------------------

def window_inside(mb, wf, u0, u1, sill, head, depth, state, rng, lights, room_kind=None):
    """What shows through a pane: dressing, then a dark recess or a lit room."""
    d0 = -depth - 0.07
    w = u1 - u0
    col = FABRICS[rng.randrange(len(FABRICS))]
    if room_kind:
        style = "curtains"
    elif state == "broken":
        style = rng.choice(("curtains", "bare"))
    else:
        style = rng.choice(("curtains", "curtains", "blind", "blind", "bare", "sheet"))
    if style == "curtains":
        gap = rng.uniform(0.34, 0.48) if room_kind else rng.uniform(0.0, 0.5)
        for side in (0, 1):
            cw = w * (1 - gap) / 2 * rng.uniform(0.85, 1.1)
            a0 = u0 - 0.04 if side == 0 else u1 + 0.04 - cw
            folds = 8
            zb = sill - 0.06 + (rng.uniform(0.1, 0.4) if state == "broken" else 0.0)       # torn short
            pts = [(a0 + cw * k / folds, d0 + (0.028 if k % 2 else -0.028)) for k in range(folds + 1)]
            for (ua, da), (ub, db) in zip(pts, pts[1:]):
                shade = 1.0 if da < db else 0.78                                            # one side of each fold in shadow
                mb.face([wf.at(ua, zb, da), wf.at(ub, zb, db), wf.at(ub, head + 0.04, db), wf.at(ua, head + 0.04, da)],
                        "fabric", color=mul(col, shade))
        mb.face([wf.at(u0 - 0.06, head + 0.01, d0 + 0.04), wf.at(u1 + 0.06, head + 0.01, d0 + 0.04),
                 wf.at(u1 + 0.06, head + 0.04, d0 + 0.04), wf.at(u0 - 0.06, head + 0.04, d0 + 0.04)], "chrome_dull")   # rail
    elif style == "blind":
        drop = rng.uniform(0.35, 1.0)
        n = int((head - sill) * drop / 0.05)
        slat = mul((0.80, 0.78, 0.70), rng.uniform(0.8, 1.0))
        for k in range(n):
            z = head - 0.02 - k * 0.05
            skew = rng.uniform(-0.05, 0.05) if rng.random() < 0.12 else 0.0
            mb.face([wf.at(u0 + 0.02, z - 0.042 + skew, d0 + 0.014), wf.at(u1 - 0.02, z - 0.042 - skew, d0 + 0.014),
                     wf.at(u1 - 0.02, z - skew, d0 - 0.014), wf.at(u0 + 0.02, z + skew, d0 - 0.014)], "fabric",
                    color=mul(slat, 0.9 + 0.1 * (k % 2)))
        mb.tube([wf.at(u1 - 0.08, head - 0.02, d0 + 0.02), wf.at(u1 - 0.08, head - 0.02 - n * 0.05 - 0.2, d0 + 0.02)], 0.003,
                "wire", segments=3)
    elif style == "sheet":
        top = sill + (head - sill) * rng.uniform(0.5, 0.85)
        mb.face([wf.at(u0, sill, d0), wf.at(u1, sill, d0 + 0.02), wf.at(u1, top - 0.08, d0 + 0.01), wf.at(u0, top, d0)],
                "fabric", color=mul(col, 0.85))
    if room_kind:
        _room(mb, wf, u0, u1, sill, head, depth, rng, lights, room_kind)
    else:
        back = -depth - 0.55
        wquad(mb, wf, u0 - 0.3, u1 + 0.3, sill - 0.3, head + 0.3, back, "interior_dark")
        wbox(mb, wf, u0 - 0.3, u1 + 0.3, sill - 0.3, head + 0.3, back, -depth - 0.02, "interior_dark", inward=True,
             skip=("front", "back"))


def _room(mb, wf, u0, u1, sill, head, depth, rng, lights, kind):
    """A room seen through a lit window: just enough of it to be a room."""
    ru0, ru1 = u0 - 1.0, u1 + 1.0
    z0, z1 = sill - 0.85, head + 0.45
    front, back = -depth - 0.02, -depth - 3.3
    paper = WALLPAPERS[rng.randrange(len(WALLPAPERS))]
    wbox(mb, wf, ru0, ru1, z0, z1, back, front, "room_wall", colour=paper, inward=True, skip=("front", "floor", "ceiling"))
    wbox(mb, wf, ru0, ru1, z0, z1, back, front, "wood_weathered", colour=(0.55, 0.42, 0.3), inward=True,
         skip=("front", "back", "left", "right", "ceiling"))
    wbox(mb, wf, ru0, ru1, z0, z1, back, front, "room_wall", colour=(0.8, 0.79, 0.74), inward=True,
         skip=("front", "back", "left", "right", "floor"))
    wbox(mb, wf, ru0, ru1, z0, z0 + 0.12, back + 0.02, back, "trim", colour=(0.7, 0.68, 0.6))                    # skirting
    # a picture on the back wall
    pu = u0 + (u1 - u0) * 0.3
    wbox(mb, wf, pu, pu + 0.55, z0 + 1.35, z0 + 1.8, back + 0.03, back, "wood_weathered", colour=(0.35, 0.28, 0.2))
    wquad(mb, wf, pu + 0.05, pu + 0.5, z0 + 1.40, z0 + 1.75, back + 0.035, "room_wall", (0.42, 0.46, 0.40))
    # a lamp on a small table, its shade glowing
    lu = u1 + 0.35
    lo = back + 0.75
    wbox(mb, wf, lu - 0.25, lu + 0.25, z0, z0 + 0.6, lo - 0.22, lo + 0.22, "wood_weathered", colour=(0.4, 0.3, 0.22))
    mb.tube([wf.at(lu, z0 + 0.6, lo), wf.at(lu, z0 + 0.95, lo)], 0.02, "chrome_dull", segments=5)
    base = wf.at(lu, z0 + 0.95, lo)
    mb.cylinder(base, (0, 0, 0.28), 0.19, "window_lit_lamp", segments=10, radius_top=0.12, caps="none")
    lights.append(wf.at(lu, z0 + 1.15, lo))
    if kind == "bedroom":
        bu = u0 - 0.6
        wbox(mb, wf, bu, bu + 1.5, z0 + 0.25, z0 + 0.55, back + 0.1, back + 2.1, "fabric", colour=(0.55, 0.5, 0.52))    # bed
        wbox(mb, wf, bu, bu + 1.5, z0, z0 + 0.25, back + 0.1, back + 2.1, "wood_weathered", colour=(0.38, 0.3, 0.24))
        wbox(mb, wf, bu, bu + 1.5, z0, z0 + 1.1, back + 0.02, back + 0.1, "wood_weathered", colour=(0.35, 0.27, 0.2))   # headboard
        wbox(mb, wf, bu + 0.15, bu + 0.7, z0 + 0.55, z0 + 0.68, back + 0.15, back + 0.55, "fabric", colour=(0.82, 0.8, 0.76))
    else:
        au = u0 - 0.5                                                                                                    # armchair
        wbox(mb, wf, au, au + 0.8, z0, z0 + 0.42, back + 0.5, back + 1.3, "fabric", colour=(0.42, 0.34, 0.28))
        wbox(mb, wf, au, au + 0.8, z0 + 0.42, z0 + 1.0, back + 0.5, back + 0.7, "fabric", colour=(0.42, 0.34, 0.28))
        for su in (au, au + 0.66):
            wbox(mb, wf, su, su + 0.14, z0 + 0.42, z0 + 0.62, back + 0.7, back + 1.3, "fabric", colour=(0.38, 0.31, 0.26))
        su = u1 - 0.1                                                                                                    # bookcase
        wbox(mb, wf, su - 0.5, su + 0.4, z0, z0 + 1.9, back + 0.02, back + 0.3, "wood_weathered", colour=(0.36, 0.28, 0.2))
        for k in range(4):
            for b in range(7):
                bw = 0.11
                wquad(mb, wf, su - 0.46 + b * bw, su - 0.46 + (b + 0.85) * bw, z0 + 0.12 + k * 0.45, z0 + 0.12 + k * 0.45 + rng.uniform(0.26, 0.38),
                      back + 0.31, "room_wall", jitter_color(rng, [(0.4, 0.2, 0.16), (0.2, 0.28, 0.24), (0.5, 0.44, 0.3)][b % 3], 0.2))


# --- outside dressing ------------------------------------------------------------------------

def shutters(mb, wf, u0, u1, sill, head, colour, rng, wear):
    """A pair of louvred shutters outside the casing. On a tired house one hangs by a hinge."""
    sw = min(0.34, (u1 - u0) * 0.5)
    col = mul(colour, 1.0 / 0.75)
    for side in (0, 1):
        if wear > 0.8 and side == 1 and rng.random() < 0.3:
            continue                                               # gone altogether
        a0 = u0 - 0.115 - sw if side == 0 else u1 + 0.115
        hang = (rng.uniform(0.06, 0.12) if (wear > 0.55 and rng.random() < 0.35) else 0.0) * (1 if side == 0 else -1)

        def zz(u, z):
            return z + hang * (u - (a0 + sw if side == 0 else a0)) / sw - abs(hang) * 0.5
        off = 0.03
        # stiles and rails
        for ua, ub, za, zb in ((a0, a0 + 0.05, sill, head), (a0 + sw - 0.05, a0 + sw, sill, head), (a0, a0 + sw, sill, sill + 0.07),
                               (a0, a0 + sw, head - 0.07, head), (a0, a0 + sw, (sill + head) / 2 - 0.035, (sill + head) / 2 + 0.035)):
            mb.face([wf.at(ua, zz(ua, za), off + 0.03), wf.at(ub, zz(ub, za), off + 0.03), wf.at(ub, zz(ub, zb), off + 0.03),
                     wf.at(ua, zz(ua, zb), off + 0.03)], "trim", color=jitter_color(rng, col, 0.05))
        # louvres
        n = int((head - sill - 0.2) / 0.07)
        for k in range(n):
            z = sill + 0.09 + k * 0.07
            if abs(z - (sill + head) / 2) < 0.06:
                continue
            ua, ub = a0 + 0.05, a0 + sw - 0.05
            mb.face([wf.at(ua, zz(ua, z), off + 0.03), wf.at(ub, zz(ub, z), off + 0.03), wf.at(ub, zz(ub, z + 0.06), off + 0.004),
                     wf.at(ua, zz(ua, z + 0.06), off + 0.004)], "trim", color=mul(col, 0.82))
        wquad(mb, wf, a0 + 0.04, a0 + sw - 0.04, sill + 0.05 - abs(hang), head - 0.05, off + 0.002, "interior_dark")


def eave_brackets(mb, wf, colour, z_top, spacing=0.92):
    """Sawn brackets under the eave, a metre apart."""
    n = max(2, int(wf.length / spacing))
    for i in range(n + 1):
        u = 0.15 + (wf.length - 0.3) * i / n
        wbox(mb, wf, u - 0.035, u + 0.035, z_top - 0.36, z_top - 0.02, 0.03, 0.08, "trim", colour)
        wbox(mb, wf, u - 0.035, u + 0.035, z_top - 0.09, z_top - 0.02, 0.08, 0.30, "trim", colour)
        mb.face([wf.at(u - 0.03, z_top - 0.34, 0.08), wf.at(u + 0.03, z_top - 0.34, 0.08), wf.at(u + 0.03, z_top - 0.09, 0.28),
                 wf.at(u - 0.03, z_top - 0.09, 0.28)], "trim", color=mul(colour, 0.85))
        for du in (-0.03, 0.03):
            tri = [wf.at(u + du, z_top - 0.34, 0.08), wf.at(u + du, z_top - 0.09, 0.28), wf.at(u + du, z_top - 0.09, 0.08)]
            mb.face(tri if du > 0 else list(reversed(tri)), "trim", color=mul(colour, 0.9))


def gable_vent(mb, wf, colour, z_mid):
    u = wf.length / 2
    w, h = 0.26, 0.38
    for ua, ub, za, zb in ((u - w - 0.05, u - w, z_mid - h, z_mid + h), (u + w, u + w + 0.05, z_mid - h, z_mid + h),
                           (u - w - 0.05, u + w + 0.05, z_mid - h - 0.05, z_mid - h), (u - w - 0.05, u + w + 0.05, z_mid + h, z_mid + h + 0.05)):
        wbox(mb, wf, ua, ub, za, zb, 0.022, 0.05, "trim", colour)
    wquad(mb, wf, u - w, u + w, z_mid - h, z_mid + h, 0.024, "interior_dark")
    for k in range(9):
        z = z_mid - h + 0.02 + k * (2 * h / 9)
        mb.face([wf.at(u - w, z, 0.05), wf.at(u + w, z, 0.05), wf.at(u + w, z + 0.07, 0.026), wf.at(u - w, z + 0.07, 0.026)], "trim",
                color=mul(colour, 0.85))


def door_dressing(mb, wf, door_u0, door_w, lot_key, colour, rng, lights, lit=False):
    """Number plaque, lantern, kick plate and letter slot at a front door."""
    u1 = door_u0 + door_w
    cell = NUMBER_CELL.get(lot_key)
    if cell is not None:
        cx, cy = cell % 3, cell // 3
        uvs = [(cx / 3, 1 - (cy + 1) / 2), ((cx + 1) / 3, 1 - (cy + 1) / 2), ((cx + 1) / 3, 1 - cy / 2), (cx / 3, 1 - cy / 2)]
        wquad(mb, wf, u1 + 0.20, u1 + 0.42, 1.52, 1.685, 0.03, "house_numbers", uvs=uvs)
    # lantern on the hinge side
    lu = door_u0 - 0.30
    wbox(mb, wf, lu - 0.06, lu + 0.06, 1.78, 2.02, 0.022, 0.035, "metal_painted", (0.2, 0.2, 0.2))
    wbox(mb, wf, lu - 0.07, lu + 0.07, 1.74, 1.78, 0.03, 0.17, "metal_painted", (0.2, 0.2, 0.2))
    wbox(mb, wf, lu - 0.055, lu + 0.055, 1.78, 1.98, 0.045, 0.155, "window_lit_lamp" if lit else "glass_dirty")
    wbox(mb, wf, lu - 0.08, lu + 0.08, 1.98, 2.02, 0.03, 0.18, "metal_painted", (0.2, 0.2, 0.2))
    if lit:
        lights.append(wf.at(lu, 1.88, 0.3))
    inset = -0.10
    wquad(mb, wf, door_u0 + 0.04, u1 - 0.04, 0.03, 0.22, inset + 0.004, "chrome_dull")                              # kick plate
    wbox(mb, wf, door_u0 + 0.30, u1 - 0.30, 0.99, 1.04, inset + 0.002, inset + 0.012, "chrome_dull")                # letter slot


# --- porch furniture ---------------------------------------------------------------------------

def rocking_chair(rng, wood=(0.50, 0.42, 0.33)):
    mb = MeshBuilder()
    col = jitter_color(rng, wood, 0.1)
    for sy in (-0.24, 0.24):                                       # curved runners
        pts = [Vector((-0.42 + 0.84 * t, sy, 0.02 + 0.10 * (2 * t - 1) ** 2)) for t in [i / 8 for i in range(9)]]
        mb.tube(pts, 0.017, "wood_weathered", segments=4, color=col)
        for x, top in ((-0.22, 1.08), (0.24, 0.62)):               # back post and front leg
            mb.tube([(x, sy, 0.04), (x - (0.08 if x < 0 else 0.0), sy, top)], 0.018, "wood_weathered", segments=4, color=col)
        mb.tube([(-0.28, sy, 0.62), (0.26, sy, 0.62)], 0.018, "wood_weathered", segments=4, color=col)      # arm
    for k in range(5):                                             # seat slats
        x = -0.20 + k * 0.10
        mb.box((x, -0.25, 0.40), (x + 0.08, 0.25, 0.42), "wood_weathered", color=jitter_color(rng, col, 0.06))
    for k in range(5):                                             # back slats
        y = -0.20 + k * 0.10
        mb.tube([(-0.24, y, 0.42), (-0.30, y, 1.05)], 0.012, "wood_weathered", segments=3, color=col)
    mb.tube([(-0.30, -0.25, 1.06), (-0.30, 0.25, 1.06)], 0.02, "wood_weathered", segments=4, color=col)
    return mb


def porch_furniture(mb, x0, x1, yf, deck_z, sx0, sx1, door_x, rng, wear, beam_z):
    """Rocking chair, side table with a mug, doormat, and a basket hanging from the beam."""
    side = x1 - 1.0 if (x1 - sx1) > (sx0 - x0) else x0 + 1.0
    if not (sx0 - 0.5 < side < sx1 + 0.5):
        chair = rocking_chair(rng)
        mb.extend(chair, Matrix.Translation((side, -0.75, deck_z)) @ Matrix.Rotation(-math.pi / 2 + rng.uniform(-0.4, 0.4), 4, "Z")
                  @ Matrix.Rotation(rng.uniform(-0.08, 0.05), 4, "Y"))
        tx = side + (0.75 if side < (x0 + x1) / 2 else -0.75)
        mb.cylinder((tx, -0.55, deck_z + 0.50), (0, 0, 0.03), 0.24, "wood_weathered", segments=12, color=(0.5, 0.44, 0.36))
        mb.cylinder((tx, -0.55, deck_z), (0, 0, 0.50), 0.03, "wood_weathered", segments=6, color=(0.45, 0.4, 0.33))
        mb.cylinder((tx, -0.55, deck_z), (0, 0, 0.03), 0.16, "wood_weathered", segments=10, color=(0.45, 0.4, 0.33))
        mb.cylinder((tx + 0.06, -0.5, deck_z + 0.53), (0, 0, 0.09), 0.04, "trim", segments=8, color=(0.7, 0.66, 0.6))     # mug
        mb.box((tx - 0.14, -0.68, deck_z + 0.53), (tx - 0.02, -0.52, deck_z + 0.545), "trim", color=(0.6, 0.58, 0.52))  # a paperback
    # doormat
    mb.box((door_x - 0.42, -0.62, deck_z), (door_x + 0.42, -0.08, deck_z + 0.012), "fabric", color=(0.24, 0.2, 0.16), skip="-z")
    # hanging basket on the beam, the plant long dead
    hx = (x0 + sx0) / 2 if (sx0 - x0) > 1.2 else (sx1 + x1) / 2
    hz = beam_z - 0.55
    for a in (0, 2.1, 4.2):
        mb.tube([(hx, yf + 0.10, beam_z), (hx + math.cos(a) * 0.15, yf + 0.10 + math.sin(a) * 0.15, hz + 0.02)], 0.004,
                "chrome_dull", segments=3)
    mb.cylinder((hx, yf + 0.10, hz - 0.16), (0, 0, 0.18), 0.10, "wood_weathered", segments=10, radius_top=0.17,
                color=(0.42, 0.34, 0.26))
    for k in range(9):
        a = k * 0.7
        r = rng.uniform(0.15, 0.32)
        mb.tube([(hx, yf + 0.10, hz), (hx + math.cos(a) * r * 0.5, yf + 0.10 + math.sin(a) * r * 0.5, hz + rng.uniform(0.05, 0.2)),
                 (hx + math.cos(a) * r, yf + 0.10 + math.sin(a) * r, hz - rng.uniform(0.1, 0.4))], 0.004, "bark", segments=3)


def post_brackets(mb, posts, yf, top, trim):
    """Diagonal braces from each porch post up to the beam."""
    for i, px in enumerate(posts):
        for sgn in (-1, 1):
            if (i == 0 and sgn < 0) or (i == len(posts) - 1 and sgn > 0):
                continue
            mb.obox((px + sgn * 0.19, yf + 0.10, top - 0.19), (0.44, 0.035, 0.045), 0.0, "trim", color=trim,
                    tilt=(0.0, -sgn * math.pi / 4))
