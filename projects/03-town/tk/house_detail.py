"""The small things that make a kit house read as lived in and weathered.

Called by house_kit.build_house with the house's own wall faces, in the
house's local frame (x along the front, y back, z up; walls from 0 to
width and 0 to depth):

- a foundation that stands proud of the siding: painted block, its paint
  flaking, with crawl-space vents along the sides and back, an access hatch,
  and a crack or two;
- water stains running down from every window sill and from the gutter
  outlets at the corners;
- the services on one side wall: an electric meter on its base, the
  conduit up to the weatherhead under the eave where the line from the
  pole comes in, a hose bib with the hose still on it, a dryer vent at the
  back;
- an air conditioner condenser on a pad beside the house, rusted;
- on the roof: a plumbing vent stack and one or two box vents on the back
  slope, and a patch of missing shingles on the worst houses.
"""

from __future__ import annotations

import math
import random

from mathutils import Vector

from .core import MeshBuilder, jitter_color, mul

FOUND_OUT = 0.05          # how far the foundation stands out from the wall line


def _wall_box(mb, wf, u0, u1, z0, z1, off0, off1, mat, colour=None):
    """A box on a wall face: u along it, z up, off outward from the wall line."""
    p = [wf.at(u, z, o) for (u, z, o) in ((u0, z0, off0), (u1, z0, off0), (u1, z1, off0), (u0, z1, off0),
                                          (u0, z0, off1), (u1, z0, off1), (u1, z1, off1), (u0, z1, off1))]
    for idx in ((4, 5, 6, 7), (0, 4, 7, 3), (5, 1, 2, 6), (7, 6, 2, 3), (0, 1, 5, 4)):
        mb.face([p[i] for i in idx], mat, color=colour)


def _wall_card(mb, wf, u0, u1, z0, z1, off, mat, colour=None):
    """A flat card on a wall face, facing out, with the texture's 0..1 square on it."""
    mb.face([wf.at(u0, z0, off), wf.at(u1, z0, off), wf.at(u1, z1, off), wf.at(u0, z1, off)], mat,
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], color=colour)


def foundation(mb, faces, ground, rng, wear):
    """Painted concrete block, proud of the siding, from below grade to the sill."""
    paint = (0.62, 0.6, 0.56)
    for key, wf in faces.items():
        _wall_box(mb, wf, -FOUND_OUT, wf.length + FOUND_OUT, ground - 0.08, 0.02, 0.0, FOUND_OUT, "concrete", paint)
        # crawl-space vents: a louvred grille set in the block, two per side, one or two at the back
        if key in ("left", "right", "back"):
            n = 2 if key != "back" else rng.randint(1, 2)
            for k in range(n):
                u = wf.length * (k + 1) / (n + 1) + rng.uniform(-0.3, 0.3)
                _wall_box(mb, wf, u - 0.2, u + 0.2, ground + 0.1, ground + 0.3, FOUND_OUT, FOUND_OUT + 0.004,
                          "metal_rust", (0.7, 0.66, 0.6))
                for j in range(4):
                    z = ground + 0.13 + j * 0.045
                    _wall_box(mb, wf, u - 0.18, u + 0.18, z, z + 0.012, FOUND_OUT + 0.004, FOUND_OUT + 0.02,
                              "metal_rust", (0.62, 0.58, 0.52))
        # paint flaking off the block, and a crack
        for _ in range(rng.randint(1, 3) if wear > 0.5 else rng.randint(0, 1)):
            u = rng.uniform(0.3, wf.length - 0.9)
            _wall_card(mb, wf, u, u + rng.uniform(0.4, 0.8), ground + 0.05, ground + rng.uniform(0.25, 0.4),
                       FOUND_OUT + 0.003, "decal_crack", (0.85, 0.85, 0.85))
    # the access hatch at the back
    wf = faces["back"]
    u = wf.length * 0.25
    _wall_box(mb, wf, u - 0.3, u + 0.3, ground + 0.02, -0.02, FOUND_OUT, FOUND_OUT + 0.025, "wood_weathered",
              (0.55, 0.5, 0.44))


def stains(mb, faces, openings, eave, rng, wear):
    """Dirty water marks down the siding: under every window sill, and down
    from the gutter outlets at the corners (the water_streaks decal: dark
    at the top, fading down)."""
    for key, wf in faces.items():
        for o in openings[key]:
            if o[4] != "win":
                continue
            u0, u1, sill = o[0], o[1], o[2]
            if rng.random() < 0.3 + 0.6 * wear:
                w = (u1 - u0) * rng.uniform(0.7, 1.1)
                c = (u0 + u1) / 2 + rng.uniform(-0.1, 0.1)
                _wall_card(mb, wf, c - w / 2, c + w / 2, sill - 0.2 - rng.uniform(0.5, 1.1), sill - 0.2, 0.035,
                           "decal_streaks")
        for u in (0.2, wf.length - 0.6):
            if rng.random() < 0.4 + 0.5 * wear:
                _wall_card(mb, wf, u, u + 0.4, eave - rng.uniform(1.4, 2.6), eave - 0.25, 0.035, "decal_streaks")


def services(mb, faces, ground, eave, rng, side):
    """Meter, conduit and weatherhead, hose bib and hose on `side`; a dryer vent at the back."""
    wf = faces[side]
    u = wf.length * 0.49 + rng.uniform(-0.1, 0.1)          # between the side windows (0.3 and 0.68 of the wall)
    grey = (0.62, 0.62, 0.6)
    # meter base and the glass dome of the meter
    _wall_box(mb, wf, u - 0.15, u + 0.15, 1.15, 1.6, 0.02, 0.12, "metal_painted", grey)
    dome = wf.at(u, 1.42, 0.12)
    mb.cylinder(tuple(dome), tuple(wf.n * 0.09), 0.085, "glass_dirty", segments=12, color=(0.8, 0.82, 0.8))
    # conduit to the weatherhead under the eave, where the service drop comes in
    mb.tube([wf.at(u, 1.6, 0.06), wf.at(u, eave - 0.5, 0.06)], 0.022, "metal_painted", segments=6, color=grey)
    head = wf.at(u, eave - 0.45, 0.06)
    mb.tube([head, head + Vector((0, 0, 0.08)) + wf.n * 0.06], 0.04, "metal_painted", segments=6, color=mul(grey, 0.8))
    for k in (-1, 1):
        mb.tube([head + wf.a * 0.03 * k + Vector((0, 0, 0.06)), head + wf.a * 0.12 * k + Vector((0, 0, -0.08)) + wf.n * 0.1],
                0.006, "wire", segments=3)
    # a ground rod clamp and its wire down the foundation
    mb.tube([wf.at(u + 0.05, 1.15, 0.05), wf.at(u + 0.08, 0.0, 0.06), wf.at(u + 0.1, ground + 0.05, 0.1)], 0.004,
            "chrome_dull", segments=3)
    # hose bib low on the wall, and the hose hanging from it in loops
    hu = wf.length * rng.uniform(0.15, 0.35)
    bib = wf.at(hu, 0.25, 0.05)
    mb.cylinder(tuple(bib), tuple(wf.n * 0.1), 0.014, "chrome_dull", segments=6)
    mb.cylinder(tuple(bib + wf.n * 0.06 + Vector((0, 0, 0.0))), (0, 0, 0.05), 0.022, "metal_rust", segments=6)
    green = (0.22, 0.4, 0.22)
    pts = [bib + wf.n * 0.1]
    for k in range(10):
        a = 2 * math.pi * k / 9
        pts.append(wf.at(hu + 0.25 * math.cos(a) * 0.6, 0.05 + 0.2 * (1 + math.sin(a)) * 0.5, 0.12 + 0.03 * k / 9))
    pts.append(wf.at(hu + 0.4, ground + 0.03, 0.4))
    mb.tube(pts, 0.012, "toy_plastic", segments=5, color=green)
    # dryer vent at the back, with its flap hanging open
    bw = faces["back"]
    vu = bw.length * rng.uniform(0.86, 0.9)                 # clear of the back door (0.62 to 0.62 + 0.9 m)
    mb.cylinder(tuple(bw.at(vu, 0.75, 0.0)), tuple(bw.n * 0.08), 0.06, "metal_painted", segments=10, color=(0.75, 0.74, 0.7))
    _wall_box(mb, bw, vu - 0.08, vu + 0.08, 0.66, 0.84, 0.08, 0.1, "metal_painted", (0.72, 0.71, 0.67))
    _wall_card(mb, bw, vu - 0.15, vu + 0.15, 0.3, 0.72, 0.012, "decal_streaks")   # lint and soot under it


def condenser(mb, faces, ground, rng, side):
    """An air-conditioner condenser on a concrete pad beside the house (or, at
    the back, between the back window and the back door)."""
    wf = faces[side]
    u = wf.length * (rng.uniform(0.6, 0.75) if side == "left" else rng.uniform(0.25, 0.4))
    if side == "back":
        u = wf.length * 0.45
    c = wf.at(u, ground, 0.75)
    a, n = wf.a, wf.n
    def box(lo_a, hi_a, lo_n, hi_n, z0, z1, mat, col):
        p = [c + a * x + n * y + Vector((0, 0, z)) for x, y, z in ((lo_a, lo_n, z0), (hi_a, lo_n, z0), (hi_a, hi_n, z0), (lo_a, hi_n, z0),
                                                                   (lo_a, lo_n, z1), (hi_a, lo_n, z1), (hi_a, hi_n, z1), (lo_a, hi_n, z1))]
        # (a, n, up) is a left-handed frame, so each face's corners go the other way round
        for idx in ((4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            mb.face([p[i] for i in reversed(idx)], mat, color=col)
    box(-0.45, 0.45, -0.4, 0.4, 0.0, 0.08, "concrete", (0.6, 0.58, 0.55))          # the pad
    beige = jitter_color(rng, (0.7, 0.67, 0.58), 0.05)
    box(-0.36, 0.36, -0.33, 0.33, 0.08, 0.72, "metal_painted", beige)            # the cabinet
    # grille louvres on all four sides
    for k in range(9):
        z = 0.14 + k * 0.06
        box(-0.37, 0.37, -0.34, -0.33, z, z + 0.025, "metal_rust", (0.5, 0.48, 0.44))
        box(-0.37, 0.37, 0.33, 0.34, z, z + 0.025, "metal_rust", (0.5, 0.48, 0.44))
    # the fan guard on top: rings and the dark fan behind
    top = c + Vector((0, 0, 0.725))
    mb.cylinder(tuple(top), (0, 0, 0.003), 0.28, "interior_dark", segments=16)
    for r in (0.1, 0.18, 0.26):
        ring = [top + Vector((math.cos(2 * math.pi * i / 16) * r, math.sin(2 * math.pi * i / 16) * r, 0.01)) for i in range(17)]
        mb.tube(ring, 0.004, "chrome_dull", segments=3)
    # the copper lines and the cable into the wall
    mb.tube([c + a * -0.36 + n * -0.2 + Vector((0, 0, 0.3)), c + a * -0.5 + n * -0.6 + Vector((0, 0, 0.35)),
             wf.at(u - 0.5, 0.4, 0.02)], 0.012, "metal_rust", segments=5, color=(0.75, 0.5, 0.35))


def roof_z(h, x, y, eave, roof_kind):
    """Height of the outside of the roof at house-local x, y (inside the footprint)."""
    w, d = h.width, h.depth
    ov, t = 0.35, 0.12
    if roof_kind in ("gable_side", "gable_front"):
        side = roof_kind == "gable_side"
        pitch = math.radians(34 if side else 40)
        ez = eave - ov * math.tan(pitch)
        across, span = (y, d) if side else (x, w)
        return ez + (min(across + ov, span + ov - across)) * math.tan(pitch) + t
    pitch = math.radians(30)
    ez = eave - ov * math.tan(pitch)
    half = min(w, d) / 2 + ov
    return ez + min(x + ov, w + ov - x, y + ov, d + ov - y, half) * math.tan(pitch) + t


def roof_bits(mb, h, eave, rng, wear):
    """A plumbing vent stack and box vents on the back half of the roof; on a
    worn house a patch of missing shingles showing the dark felt."""
    w, d = h.width, h.depth
    def spot(fx, fy):
        x, y = w * fx, d * fy
        return Vector((x, y, roof_z(h, x, y, eave, h.roof)))
    # vent stack: a grey pipe with a lead flashing
    p = spot(rng.uniform(0.3, 0.7), 0.72 if h.roof != "gable_front" else 0.6)
    if h.roof == "gable_front":
        p = spot(0.72, rng.uniform(0.4, 0.7))
    mb.cylinder(tuple(p - Vector((0, 0, 0.1))), (0, 0, 0.42), 0.045, "metal_painted", segments=10, color=(0.55, 0.55, 0.53))
    mb.cylinder(tuple(p - Vector((0, 0, 0.04))), (0, 0, 0.06), 0.12, "metal_rust", segments=10, radius_top=0.06,
                color=(0.5, 0.5, 0.5))
    mb.cylinder(tuple(p + Vector((0, 0, 0.32))), (0, 0, 0.004), 0.04, "interior_dark", segments=10)
    # box vents
    for k in range(rng.randint(1, 2)):
        q = spot(0.2 + 0.25 * k + rng.uniform(0, 0.1), 0.8) if h.roof != "gable_front" else spot(0.78, 0.25 + 0.3 * k)
        mb.box((q.x - 0.22, q.y - 0.22, q.z - 0.08), (q.x + 0.22, q.y + 0.22, q.z + 0.1), "metal_painted",
               color=(0.4, 0.4, 0.4))
        mb.box((q.x - 0.24, q.y - 0.24, q.z + 0.1), (q.x + 0.24, q.y + 0.24, q.z + 0.14), "metal_painted",
               color=(0.45, 0.45, 0.45))
    # missing shingles: a ragged patch of black felt, on the front slope where it shows from the street
    if wear > 0.6:
        fy = 0.22 if h.roof != "gable_front" else 0.5
        fx = rng.uniform(0.25, 0.65) if h.roof != "gable_front" else 0.25
        c = spot(fx, fy)
        n = 9
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            r = rng.uniform(0.3, 0.55)
            x, y = c.x + math.cos(a) * r * 1.4, c.y + math.sin(a) * r
            ring.append(Vector((x, y, roof_z(h, x, y, eave, h.roof) + 0.004)))
        for i in range(n):
            mb.face([Vector((c.x, c.y, c.z + 0.004)), ring[i], ring[(i + 1) % n]], "interior_dark", color=(0.6, 0.6, 0.6))


def _clearance(h, lot, side):
    """Metres from the house's `side` wall to the edge of its lot."""
    import plan
    (ox, oy), (ax, ay), (bx, by) = plan.house_frame(h)
    dx, dy = (ax, ay) if side == "right" else (-ax, -ay)
    hx0, hy0, hx1, hy1 = plan.house_rect(h)
    x0, y0, x1, y1 = lot.rect
    if dx > 0.5:
        return x1 - hx1
    if dx < -0.5:
        return hx0 - x0
    if dy > 0.5:
        return y1 - hy1
    return hy0 - y0


def dress(mb, h, lot, faces, openings, ground, eave, rng: random.Random):
    wear = h.wear
    wrap_side = ("right" if h.facing == "n" else "left") if h.porch == "wrap" else None
    sides = [s_ for s_ in ("left", "right") if s_ != wrap_side]
    side = rng.choice(sides)                                  # services: never behind a wrap porch
    other = "right" if side == "left" else "left"
    foundation(mb, faces, ground, rng, wear)
    stains(mb, faces, openings, eave, rng, wear)
    services(mb, faces, ground, eave, rng, side)
    if rng.random() < 0.75:
        # beside the house if the side yard is wide enough (the unit reaches 1.2 m out), else at the back
        spot = other if other != wrap_side and _clearance(h, lot, other) > 1.7 else "back"
        condenser(mb, faces, ground, rng, spot)
    roof_bits(mb, h, eave, rng, wear)
