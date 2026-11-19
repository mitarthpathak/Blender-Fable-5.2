"""Abandoned cars: an original late-1980s / 1990s sedan, station wagon and
pickup. No real make, no badges, blank plates.

Each body is a loft: a seven-point half cross-section (rocker, door bulge,
belt line, glass, roof rail, roof centre) swept along the car's length, with
the hood, windshield, roof, rear glass and trunk all coming from how high the
"greenhouse" stands at each station. Wheel arches are cut by lifting the
lower edge of the side along a circle round each wheel, with a dark liner
behind. Then come bumpers, lamps, grille, mirrors, door shuts and handles,
wipers, wheels (sound, flat or missing), rust on the sills and arches, grime
in the vertex colours, and dirt and wet leaves on the flat tops. The glass is
see-through (dirty, streaked), over an interior: seats with a split seam, a
dashboard, a steering wheel, and what the last driver left behind.

Local axes: +X forward, +Z up, origin on the ground under the middle.
"""

from __future__ import annotations

import math
import random

from mathutils import Matrix, Vector, noise

from .core import MeshBuilder, jitter_color, mul

NEUTRAL = 0.75
WHEEL_R = 0.31
ARCH_R = 0.37

# kind: length, width, front axle x, rear axle x, belt height, roof height,
# and the greenhouse as (x, g) knots from tail to nose: g = 0 body top, 1 full roof.
SPECS = {
    "sedan": dict(L=4.72, W=1.76, fa=1.40, ra=-1.30, belt=0.93, roof=1.39,
                  g=((-2.36, 0), (-1.46, 0), (-0.92, 1), (0.42, 1), (1.04, 0), (2.36, 0)),
                  pillars=(-0.90, -0.20, 0.40), doors=(-0.94, -0.18, 0.86)),
    "wagon": dict(L=4.86, W=1.78, fa=1.45, ra=-1.33, belt=0.94, roof=1.44,
                  g=((-2.43, 0), (-2.38, 0), (-2.12, 1), (0.44, 1), (1.08, 0), (2.43, 0)),
                  pillars=(-2.08, -1.22, -0.22, 0.42), doors=(-1.20, -0.20, 0.88)),
    "pickup": dict(L=5.06, W=1.84, fa=1.58, ra=-1.42, belt=1.00, roof=1.56,
                   g=((-2.53, 0), (-0.52, 0), (-0.44, 1), (0.46, 1), (1.06, 0), (2.53, 0)),
                   pillars=(-0.42, 0.44), doors=(-0.40, 0.90), bed=(-2.46, -0.54)),
}


def _lerp(a, b, t):
    return a + (b - a) * t


def _g_at(spec, x):
    knots = spec["g"]
    for (x0, g0), (x1, g1) in zip(knots, knots[1:]):
        if x0 <= x <= x1:
            return _lerp(g0, g1, (x - x0) / max(x1 - x0, 1e-6))
    return 0.0


def _stations(spec):
    half = spec["L"] / 2
    xs = {round(-half + i * 0.13, 4) for i in range(int(spec["L"] / 0.13) + 1)}
    xs |= {round(k[0], 4) for k in spec["g"]} | {round(half, 4), round(-half, 4)}
    for axle in (spec["fa"], spec["ra"]):                       # dense round the arches
        for i in range(-8, 9):
            xs.add(round(axle + ARCH_R * math.sin(i / 8 * math.pi / 2), 4))
    for p in spec["pillars"]:
        xs |= {round(p - 0.045, 4), round(p + 0.045, 4)}
    if "bed" in spec:
        xs |= {round(spec["bed"][0], 4), round(spec["bed"][1], 4)}
    return sorted(x for x in xs if -half - 1e-6 <= x <= half + 1e-6)


def _section(spec, x, ride):
    """The half cross-section (y >= 0) at station x: seven points, sill to roof centre."""
    half = spec["L"] / 2
    hw = spec["W"] / 2
    end = min(half - abs(x), 0.5) / 0.5                          # 0 at the bumper faces
    hw -= 0.085 * (1 - end) ** 2                                 # corners drawn in
    nose = max(0.0, (x - 1.0) / (half - 1.0)) if x > 1.0 else 0.0
    belt = spec["belt"] - 0.085 * nose ** 1.5 + ride             # the hood falls to the nose
    zb = 0.21 + 0.10 * (1 - end) ** 2 + ride
    g = _g_at(spec, x)
    roof = spec["roof"] + ride
    arch = 0.0
    for axle in (spec["fa"], spec["ra"]):
        dx = abs(x - axle)
        if dx < ARCH_R:
            arch = max(arch, WHEEL_R + 0.015 + ride + math.sqrt(ARCH_R ** 2 - dx ** 2))
    mid = _lerp(zb, belt, 0.52)
    p = [
        Vector((x, hw - 0.10, zb)),
        Vector((x, hw - 0.005, zb + 0.10)),
        Vector((x, hw + 0.012, mid)),
        Vector((x, hw - 0.018, belt)),
        Vector((x, hw - 0.10 - 0.07 * g, belt + 0.02 + g * ((roof - belt) * 0.90 - 0.02))),
        Vector((x, hw - 0.22 - 0.06 * g, belt + 0.035 + g * (roof - belt - 0.035))),
        Vector((x, 0.0, belt + 0.055 + g * (roof - belt - 0.035))),
    ]
    if arch > 0:
        for i in (0, 1, 2):                                      # the arch lifts the lower edge
            if p[i].z < arch:
                p[i].z = arch
                p[i].y = hw - 0.004
    fine, bands = _refine(p)
    return p, g, arch, hw, fine, bands


def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def _refine(p, steps=3):
    """The section rounded: a Catmull-Rom spline through the seven points, each
    band cut in `steps`. The spline passes through the points, so the belt
    line and the glass edges stay where they were; the panels between them
    swell and the roof gets a crown. Returns the points and, for each segment,
    the band (0..5) it belongs to."""
    n = len(p)
    out, bands = [p[0].copy()], []
    for i in range(n - 1):
        a = p[i - 1] if i > 0 else p[0] * 2 - p[1]
        d = p[i + 2] if i + 2 < n else Vector((p[-2].x, -p[-2].y, p[-2].z))     # mirrored: flat across the centre
        if (p[i + 1] - p[i]).length < 1e-4:
            for _ in range(steps):
                out.append(p[i + 1].copy())
                bands.append(i)
            continue
        for k in range(1, steps + 1):
            q = _catmull(a, p[i], p[i + 1], d, k / steps)
            q.x = p[i].x
            out.append(q)
            bands.append(i)
    return out, bands


def _quad(mb, a, b, c, d, mat, colour, uv_axes=None):
    """uv_axes: two axis indices to map the texture continuously over many
    small quads (the glass); otherwise each face is projected on its own."""
    if (b - a).cross(d - a).length < 1e-6 and (c - b).cross(d - c).length < 1e-6:
        return
    uvs = None
    if uv_axes:
        i, j = uv_axes
        uvs = [(p[i] / 1.1, p[j] / 0.55) for p in (a, b, c, d)]
    mb.face([a, b, c, d], mat, color=colour, uvs=uvs)


def _wheel(flat=False):
    """Tyre and hubcap, axle along Y, centred on the origin."""
    mb = MeshBuilder()
    r, w = WHEEL_R, 0.10
    # sidewall, a rounded shoulder, and a tread with two grooves round it
    rings = [(-w, r - 0.05), (-w * 0.96, r - 0.026), (-w * 0.84, r - 0.009), (-w * 0.66, r - 0.001), (-w * 0.40, r),
             (-w * 0.36, r - 0.007), (-w * 0.30, r - 0.007), (-w * 0.26, r), (w * 0.26, r), (w * 0.30, r - 0.007),
             (w * 0.36, r - 0.007), (w * 0.40, r), (w * 0.66, r - 0.001), (w * 0.84, r - 0.009), (w * 0.96, r - 0.026),
             (w, r - 0.05)]
    seg = 26
    grey = (0.42, 0.42, 0.42)
    for (y0, r0), (y1, r1) in zip(rings, rings[1:]):
        for i in range(seg):
            a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            mb.face([Vector((math.cos(a0) * r0, y0, math.sin(a0) * r0)), Vector((math.cos(a0) * r1, y1, math.sin(a0) * r1)),
                     Vector((math.cos(a1) * r1, y1, math.sin(a1) * r1)), Vector((math.cos(a1) * r0, y0, math.sin(a1) * r0))],
                    "tyre", color=grey)
    for side in (-1, 1):
        ring_r = r - 0.05
        rim = [Vector((math.cos(2 * math.pi * i / seg) * ring_r, side * w, math.sin(2 * math.pi * i / seg) * ring_r))
               for i in range(seg)]
        hub = [Vector((v.x * 0.72, side * (w - 0.035), v.z * 0.72)) for v in rim]
        cap = [Vector((v.x * 0.30, side * (w - 0.01), v.z * 0.30)) for v in rim]
        for i in range(seg):
            j = (i + 1) % seg
            q1 = [rim[i], rim[j], hub[j], hub[i]]
            q2 = [hub[i], hub[j], cap[j], cap[i]]
            mb.face(q1 if side < 0 else list(reversed(q1)), "tyre", color=(0.3, 0.3, 0.3))
            mb.face(q2 if side < 0 else list(reversed(q2)), "chrome_dull", color=(0.8, 0.78, 0.74))
        mb.face(cap if side > 0 else list(reversed(cap)), "chrome_dull", color=(0.6, 0.58, 0.55))
        # a chrome beauty ring round the steel wheel, and five lug nuts round the cap
        outer = [Vector((v.x * 0.98, side * (w - 0.004), v.z * 0.98)) for v in rim]
        inner = [Vector((v.x * 0.86, side * (w - 0.012), v.z * 0.86)) for v in rim]
        for i in range(seg):
            j = (i + 1) % seg
            q = [outer[i], outer[j], inner[j], inner[i]]
            mb.face(q if side < 0 else list(reversed(q)), "chrome_dull", color=(0.72, 0.7, 0.66))
        for k in range(5):
            a = 2 * math.pi * k / 5 + 0.3
            mb.cylinder((math.cos(a) * 0.085, side * (w - 0.03), math.sin(a) * 0.085), (0, side * 0.025, 0), 0.012,
                        "chrome_dull", segments=6, color=(0.55, 0.53, 0.5))
    if flat:
        for v in mb.verts:                                       # the tyre slumps onto the road
            if v.z < 0:
                v.y *= 1.0 + 0.22 * min(1.0, -v.z / r)
                v.z = max(v.z * 0.62, -r * 0.60)
    return mb


def _seat(mb, x, y, z, width, rng, back_h=0.62):
    """A seat: cushion, raked backrest, headrest. Vinyl, split along one seam."""
    col = jitter_color(rng, (1.0, 1.0, 1.0), 0.08)
    mb.box((x - 0.26, y - width / 2, z), (x + 0.26, y + width / 2, z + 0.14), "car_seat", color=col)
    mb.obox((x - 0.31, y, z + 0.14 + back_h / 2), (0.12, width, back_h), 0.0, "car_seat", color=col, tilt=(0.0, -0.22))
    if width < 0.7:
        mb.obox((x - 0.40, y, z + 0.20 + back_h), (0.09, 0.26, 0.18), 0.0, "car_seat", color=mul(col, 0.9), tilt=(0.0, -0.22))
    # the torn seam, foam showing
    mb.obox((x + 0.02, y + width * 0.18, z + 0.142), (0.22, 0.03, 0.004), rng.uniform(-0.3, 0.3), "trim", color=(0.7, 0.62, 0.42))


def _interior(mb, spec, kind, ride, rng, state):
    """Seats, dashboard, steering wheel, parcel shelf, and what was left inside."""
    hw = spec["W"] / 2
    roof_knots = [k[0] for k in spec["g"] if k[1] == 1]
    cab0, cab1 = roof_knots[0], roof_knots[-1]              # the roof runs from cab0 to cab1
    zero = [k[0] for k in spec["g"] if k[1] == 0]
    ws_base = min(x for x in zero if x > cab1)              # foot of the windshield
    floor = 0.21 + ride + 0.02
    belt = spec["belt"] + ride
    sz = floor + 0.20
    # front seats (a bench in the pickup), rear bench in the sedan and the wagon
    fx = cab1 - 0.42
    if kind == "pickup":
        _seat(mb, fx, 0.0, sz, hw * 2 - 0.42, rng)
    else:
        for y in (-0.37, 0.37):
            _seat(mb, fx, y, sz, 0.52, rng)
        _seat(mb, cab0 + (0.62 if kind == "sedan" else 1.55), 0.0, sz, hw * 2 - 0.40, rng, back_h=0.5)
    # dashboard: a padded shelf with a cowl over the dials, a glovebox hanging open
    dx0, dx1 = ws_base - 0.52, ws_base - 0.05
    mb.box((dx0, -hw + 0.12, belt - 0.30), (dx1, hw - 0.12, belt - 0.02), "plastic_dark", color=(1.4, 1.35, 1.3))
    mb.box((dx0 - 0.05, 0.14, belt - 0.02), (dx0 + 0.20, 0.62, belt + 0.06), "plastic_dark", color=(1.2, 1.2, 1.2))
    mb.obox((dx0 - 0.07, -0.40, belt - 0.26), (0.03, 0.36, 0.16), 0.0, "plastic_dark", color=(1.6, 1.5, 1.4), tilt=(0.0, 0.9))
    # steering wheel on its column
    wx, wy, wz = dx0 - 0.16, 0.38, belt - 0.05
    tilt = Matrix.Rotation(math.radians(64), 4, "Y")
    ring = [tilt @ Vector((math.cos(2 * math.pi * i / 14) * 0.185, math.sin(2 * math.pi * i / 14) * 0.185, 0)) + Vector((wx, wy, wz))
            for i in range(15)]
    mb.tube(ring, 0.014, "plastic_dark", segments=5, color=(1.3, 1.3, 1.3))
    for a in (0.5, 2.6, 4.7):
        mb.tube([Vector((wx, wy, wz)), tilt @ Vector((math.cos(a) * 0.18, math.sin(a) * 0.18, 0)) + Vector((wx, wy, wz))], 0.011,
                "plastic_dark", segments=4)
    mb.tube([(wx, wy, wz), (dx0 + 0.12, wy, belt - 0.16)], 0.025, "plastic_dark", segments=6)
    # gear lever, handbrake
    if kind != "pickup":
        mb.box((fx - 0.15, -0.09, sz - 0.04), (fx + 0.45, 0.09, sz + 0.06), "plastic_dark", color=(1.3, 1.3, 1.3))
        mb.tube([(fx + 0.30, 0.0, sz + 0.06), (fx + 0.36, 0.0, sz + 0.24)], 0.012, "chrome_dull", segments=4)
    # parcel shelf under the sedan's rear glass
    if kind == "sedan":
        rear_base = max(x for x in zero if x < cab0)
        mb.face([Vector((rear_base, -hw + 0.14, belt - 0.03)), Vector((cab0 + 0.30, -hw + 0.14, belt - 0.03)),
                 Vector((cab0 + 0.30, hw - 0.14, belt - 0.03)), Vector((rear_base, hw - 0.14, belt - 0.03))], "car_interior",
                color=(0.8, 0.78, 0.72))
    # what was left behind: papers on the passenger seat, a coffee cup, a bag in the footwell, leaves blown in
    for k in range(3):
        mb.obox((fx + rng.uniform(-0.1, 0.1), -0.37 + rng.uniform(-0.1, 0.1), sz + 0.145 + 0.006 * k), (0.22, 0.30, 0.004),
                rng.uniform(0, 3), "trim", color=(0.72, 0.7, 0.64))
    mb.cylinder((dx0 + 0.10, -0.05, belt - 0.02), (0, 0, 0.10), 0.035, "trim", segments=8, color=(0.7, 0.66, 0.58))
    mb.obox((fx + 0.45, -0.40, floor + 0.12), (0.26, 0.22, 0.22), 0.4, "plywood", color=(0.66, 0.54, 0.4))
    if state != "on_blocks":
        mb.card((dx0 + 0.2, -0.3, belt - 0.012), 0.5, 0.4, 0.3, "decal_leaves", flat=True)
    else:                                                    # stripped: the radio is gone, wires hang out
        mb.box((dx0 - 0.01, -0.14, belt - 0.24), (dx0 + 0.02, 0.10, belt - 0.12), "interior_dark")
        for k in range(3):
            mb.tube([(dx0, -0.08 + 0.06 * k, belt - 0.2), (dx0 - 0.08, -0.1 + 0.07 * k, belt - 0.34),
                     (dx0 - 0.05, -0.12 + 0.08 * k, belt - 0.5)], 0.005, "wire", segments=3)


def car(kind: str, paint, seed: int, state: str = "abandoned") -> MeshBuilder:
    """state: "abandoned" (flat tyres), "on_blocks" (wheels gone), "crashed" (front stove in)."""
    spec = SPECS[kind]
    rng = random.Random(seed)
    mb = MeshBuilder()
    half, hw0 = spec["L"] / 2, spec["W"] / 2
    flat = state in ("abandoned", "crashed")
    ride = {"abandoned": -0.055, "crashed": -0.04, "on_blocks": 0.10}[state]
    rust_level = {"abandoned": 0.5, "crashed": 0.35, "on_blocks": 0.85}[state]
    col = mul(paint, 1.0 / NEUTRAL)

    def tone(p, top=False):
        """Paint colour with road grime low down and dirt settled on the flat tops."""
        k = 1.0
        if p.z < 0.75:
            k *= 0.62 + 0.38 * max(0.0, (p.z - 0.2) / 0.55)
        if top:
            k *= 0.70 + 0.12 * rng.random()
        return (col[0] * k, col[1] * k, col[2] * k)

    xs = _stations(spec)
    secs = [_section(spec, x, ride) for x in xs]
    bed = spec.get("bed")
    for (x0, (a7, g0, arch0, _, a, bands)), (x1, (b7, g1, arch1, _, b, _b)) in zip(zip(xs, secs), zip(xs[1:], secs[1:])):
        xm = (x0 + x1) / 2
        gm = (g0 + g1) / 2
        in_pillar = any(abs(xm - p) < 0.05 for p in spec["pillars"])
        in_bed = bed is not None and bed[0] < xm < bed[1]
        sloped = abs(g1 - g0) > 0.02                             # windshield or rear glass
        for side in (1, -1):
            def P(pts, i):
                v = pts[i]
                return Vector((v.x, v.y * side, v.z))
            for j, i in enumerate(bands):
                q = [P(a, j), P(b, j), P(b, j + 1), P(a, j + 1)]
                if side > 0:                                     # wound to face out: a game engine culls back faces
                    q.reverse()
                centre = (q[0] + q[1] + q[2] + q[3]) / 4
                if i < 3:
                    # rust comes through in patches (smooth noise), worst along the sills and round the arches
                    near_arch = arch0 > 0 or arch1 > 0
                    low = 1.0 - min(1.0, max(0.0, (centre.z - 0.25) / 0.45))
                    n = noise.noise(Vector((centre.x * 2.6, centre.z * 3.2 + side * 7.0, seed * 0.37)))
                    rusty = n + 0.55 * low + (0.25 if near_arch else 0.0) > 1.15 - 0.75 * rust_level
                    if rusty:
                        _quad(mb, *q, "metal_rust", jitter_color(rng, (0.75, 0.68, 0.6), 0.12))
                    else:
                        _quad(mb, *q, "car_paint", tone(centre))
                elif i == 3:                                     # belt to glass top
                    glass = gm > 0.6 and not in_pillar and not sloped
                    _quad(mb, *q, "car_glass" if glass else "car_paint", None if glass else tone(centre),
                          uv_axes=(0, 2) if glass else None)
                    if glass:
                        # the rubber seal along the bottom and the top of the side glass
                        first, last = j == 0 or bands[j - 1] != 3, j + 1 >= len(bands) or bands[j + 1] != 3
                        lo0, lo1, up0, up1 = P(a, j), P(b, j), P(a, j + 1), P(b, j + 1)
                        out = Vector((0, 0.004 * side, 0))
                        for pair in ([((lo0, lo1), (up0, up1))] if first else []) + ([((up0, up1), (lo0, lo1))] if last else []):
                            (e0, e1), (o0, o1) = pair
                            strip = [e0 + out, e1 + out, e1.lerp(o1, 0.22) + out, e0.lerp(o0, 0.22) + out]
                            if (strip[1] - strip[0]).cross(strip[3] - strip[0]).y * side < 0:
                                strip.reverse()                  # facing out of the car
                            _quad(mb, *strip, "plastic_dark", (0.5, 0.5, 0.5))
                        continue
                elif i == 4:                                     # roof rail, or the rail of the bed
                    _quad(mb, *q, "car_paint", tone(centre, top=gm < 0.1))
                elif in_bed:
                    continue                                     # open bed
                elif sloped and gm > 0.08:
                    _quad(mb, *q, "car_glass", None, uv_axes=(1, 2))
                    continue
                else:
                    _quad(mb, *q, "car_paint", tone(centre, top=True))
                # the inside of the same panel: headlining and door cards, a little inboard
                if gm > 0.02:
                    inner = [Vector((v.x, v.y * 0.985, v.z - (0.014 if i >= 4 else 0.0))) for v in reversed(q)]
                    _quad(mb, *inner, "car_interior", (0.9, 0.88, 0.84) if i >= 4 else (1.0, 1.0, 1.0))
            # wheel-arch liner behind the cut
            if arch0 > 0 or arch1 > 0:
                za, zb_ = max(arch0, a7[0].z), max(arch1, b7[0].z)
                ya = (hw0 - 0.004) * side
                yi = (hw0 - 0.34) * side
                q = [Vector((x0, ya, za)), Vector((x1, ya, zb_)), Vector((x1, yi, zb_)), Vector((x0, yi, za))]
                mb.face(q if side < 0 else list(reversed(q)), "interior_dark")
                q = [Vector((x0, yi, 0.12)), Vector((x1, yi, 0.12)), Vector((x1, yi, zb_)), Vector((x0, yi, za))]
                mb.face(q if side > 0 else list(reversed(q)), "interior_dark")
        # floor pan (it faces up: this is the carpet seen through the glass)
        mb.face([Vector((x0, a7[0].y, a7[0].z)), Vector((x0, -a7[0].y, a7[0].z)), Vector((x1, -b7[0].y, b7[0].z)),
                 Vector((x1, b7[0].y, b7[0].z))], "car_interior", color=(0.7, 0.68, 0.64))
    # nose and tail panels
    for sec, front in ((secs[-1], True), (secs[0], False)):
        pts = sec[4]
        loop = [Vector((v.x, v.y, v.z)) for v in pts] + [Vector((v.x, -v.y, v.z)) for v in reversed(pts[:-1])]
        mb.face(loop if front else list(reversed(loop)), "car_paint", color=tone(sec[0][3]))

    _interior(mb, spec, kind, ride, rng, state)

    belt_f = secs[-1][0][3].z
    belt_r = secs[0][0][3].z
    zb_f = secs[-1][0][0].z
    # bumpers: grey plastic wrapping the corners
    for x, sgn in ((half, 1), (-half, -1)):
        z0 = (zb_f if sgn > 0 else secs[0][0][0].z) - 0.02
        w = hw0 - 0.07
        mb.box((min(x, x + sgn * 0.09), -w, z0), (max(x, x + sgn * 0.09), w, z0 + 0.20), "plastic_dark")
        for s in (-1, 1):
            mb.obox((x - sgn * 0.10, s * (w + 0.015), z0 + 0.10), (0.34, 0.07, 0.20), s * sgn * -0.32, "plastic_dark")
    # grille, headlamps, indicators
    zg = zb_f + 0.22
    mb.box((half, -0.42, zg), (half + 0.012, 0.42, zg + 0.17), "plastic_dark")
    for k in range(5):
        mb.box((half + 0.012, -0.40, zg + 0.015 + k * 0.032), (half + 0.02, 0.40, zg + 0.028 + k * 0.032), "chrome_dull")
    for s in (-1, 1):
        lamp = "interior_dark" if state == "crashed" and s > 0 else "lamp_clear"
        y0, y1 = sorted((s * 0.44, s * 0.68))
        mb.box((half, y0, zg + 0.01), (half + 0.016, y1, zg + 0.16), lamp)
        y0, y1 = sorted((s * 0.69, s * 0.75))
        mb.box((half, y0, zg + 0.01), (half + 0.014, y1, zg + 0.16), "lamp_red", color=(1.6, 1.2, 0.5))   # amber
    # tail lamps and a blank plate
    zt = belt_r - 0.24
    for s in (-1, 1):
        y0, y1 = (0.36, hw0 - 0.12) if s > 0 else (-(hw0 - 0.12), -0.36)
        mb.box((-half - 0.014, y0, zt), (-half, y1, zt + 0.13), "lamp_red")
    # licence plates (a 2 x 2 atlas of four, tk/detail_maps.plates), on a dark backing
    cell = seed % 4
    u0, v0 = (cell % 2) * 0.5, 0.5 - (cell // 2) * 0.5
    plate_uv = [(u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5)]
    mb.box((-half - 0.010, -0.165, zt - 0.05), (-half, 0.165, zt + 0.12), "plastic_dark")
    mb.face([Vector((-half - 0.012, 0.15, zt - 0.04)), Vector((-half - 0.012, -0.15, zt - 0.04)),
             Vector((-half - 0.012, -0.15, zt + 0.11)), Vector((-half - 0.012, 0.15, zt + 0.11))], "plate", uvs=plate_uv)
    if state != "crashed":
        zf = (zb_f - 0.02) + 0.10
        mb.face([Vector((half + 0.094, -0.15, zf - 0.075)), Vector((half + 0.094, 0.15, zf - 0.075)),
                 Vector((half + 0.094, 0.15, zf + 0.075)), Vector((half + 0.094, -0.15, zf + 0.075))], "plate", uvs=plate_uv)
    if kind != "pickup":
        mb.box((-half - 0.012, -0.34, zt + 0.0), (-half - 0.004, -0.17, zt + 0.12), "lamp_red", color=(0.5, 0.5, 0.5))
        mb.box((-half - 0.012, 0.17, zt + 0.0), (-half - 0.004, 0.34, zt + 0.12), "lamp_red", color=(0.5, 0.5, 0.5))
    # mirrors
    cowl = next(k[0] for k in reversed(spec["g"]) if k[1] == 1)       # where the windshield starts
    for s in (-1, 1):
        mb.obox((cowl + 0.34, s * (hw0 + 0.09), spec["belt"] + ride + 0.09), (0.07, 0.16, 0.11), s * 0.25, "plastic_dark")
        mb.box((cowl + 0.32, min(s * (hw0 - 0.02), s * (hw0 + 0.03)), spec["belt"] + ride + 0.03),
               (cowl + 0.36, max(s * (hw0 - 0.02), s * (hw0 + 0.03)), spec["belt"] + ride + 0.07), "plastic_dark")
    # door shut lines and handles
    for dx in spec["doors"]:
        for s in (-1, 1):
            y = s * (hw0 + 0.014)
            q = [Vector((dx - 0.006, y, 0.36 + ride)), Vector((dx + 0.006, y, 0.36 + ride)),
                 Vector((dx + 0.006, y * 0.985, spec["belt"] + ride - 0.01)), Vector((dx - 0.006, y * 0.985, spec["belt"] + ride - 0.01))]
            mb.face(q if s < 0 else list(reversed(q)), "interior_dark")
    for dx in spec["doors"][:-1]:
        for s in (-1, 1):
            mb.box((dx + 0.08, min(s * hw0, s * (hw0 + 0.022)), spec["belt"] + ride - 0.13),
                   (dx + 0.22, max(s * hw0, s * (hw0 + 0.022)), spec["belt"] + ride - 0.10), "chrome_dull")
    # wipers on the windshield base
    wx = next(k[0] for k in reversed(spec["g"][:-1]) if k[1] == 0) - 0.03
    for y0 in (-0.55, 0.05):
        mb.obox((wx - 0.10, y0 + 0.25, spec["belt"] + ride + 0.10), (0.02, 0.5, 0.012), 0.12, "plastic_dark", tilt=(0.0, -0.5))
    # rubbing strips along the doors, between the arches
    xs0, xs1 = spec["ra"] + ARCH_R + 0.08, spec["fa"] - ARCH_R - 0.08
    for s in (-1, 1):
        mb.box((xs0, min(s * (hw0 - 0.01), s * (hw0 + 0.024)), 0.57 + ride),
               (xs1, max(s * (hw0 - 0.01), s * (hw0 + 0.024)), 0.63 + ride), "plastic_dark", color=(0.55, 0.55, 0.55))
    # the fuel filler door on the left rear quarter, a shade off the paint
    fx = spec["ra"] + (0.52 if kind != "pickup" else 0.62)
    mb.box((fx - 0.09, -(hw0 + 0.012), spec["belt"] + ride - 0.27), (fx + 0.09, -(hw0 + 0.004), spec["belt"] + ride - 0.11),
           "car_paint", color=mul(col, 0.8))
    # a radio antenna on the right front fender: bent back on the crashed pickup
    ax, ay, az = spec["fa"] + 0.05, hw0 - 0.12, spec["belt"] + ride - 0.03
    mb.cylinder((ax, ay, az - 0.02), (0, 0, 0.04), 0.014, "chrome_dull", segments=6)
    if state == "crashed":
        mb.tube([(ax, ay, az), (ax - 0.05, ay, az + 0.3), (ax - 0.45, ay + 0.05, az + 0.42)], 0.004, "chrome_dull", segments=3)
    else:
        mb.tube([(ax, ay, az), (ax - 0.18, ay, az + 0.78)], 0.004, "chrome_dull", segments=3)
    # the exhaust under the back, rusted through
    mb.cylinder((-half + 0.25, -0.45, 0.24 + ride), (-0.34, 0, 0), 0.026, "metal_rust", segments=8, caps="none")
    mb.cylinder((-half - 0.09, -0.45, 0.24 + ride), (0.002, 0, 0), 0.026, "interior_dark", segments=8)
    # a bright strip along the belt line under the side glass, from the rear glass to the windshield
    roof_knots = [k[0] for k in spec["g"] if k[1] == 1]
    zero_knots = [k[0] for k in spec["g"] if k[1] == 0]
    cab0, cab1 = roof_knots[0], roof_knots[-1]
    rear_foot = max(x for x in zero_knots if x < cab0)
    ws_foot = min(x for x in zero_knots if x > cab1)
    for s in (-1, 1):
        y_in, y_out = s * (hw0 - 0.032), s * (hw0 - 0.004)
        mb.box((rear_foot + 0.04, min(y_in, y_out), spec["belt"] + ride - 0.012), (ws_foot - 0.04, max(y_in, y_out),
               spec["belt"] + ride + 0.014), "chrome_dull", color=(0.75, 0.74, 0.7))
    # side marker lamps: amber at the front of the front wings, red at the back of the rear quarters
    for mx, lamp, colour in ((half - 0.22, "lamp_red", (1.6, 1.2, 0.5)), (-half + 0.22, "lamp_red", None)):
        pts, _g, _a, _hw, _f, _b = _section(spec, mx, ride)
        zz = spec["belt"] + ride - 0.20
        t = max(0.0, min(1.0, (zz - pts[2].z) / max(pts[3].z - pts[2].z, 1e-3)))
        yy = pts[2].y + (pts[3].y - pts[2].y) * t
        for s in (-1, 1):
            mb.box((mx - 0.05, min(s * (yy - 0.006), s * (yy + 0.006)), zz - 0.022),
                   (mx + 0.05, max(s * (yy - 0.006), s * (yy + 0.006)), zz + 0.022), lamp, color=colour)
    # the interior you see through the glass: a rear-view mirror and two sun visors, one flipped down
    rz_in = spec["roof"] + ride - 0.05
    mb.box((cab1 - 0.08, -0.12, rz_in - 0.13), (cab1 - 0.05, 0.12, rz_in - 0.07), "plastic_dark")
    mb.tube([(cab1 - 0.06, 0.0, rz_in - 0.07), (cab1 - 0.04, 0.0, rz_in)], 0.008, "plastic_dark", segments=4)
    for y0, y1, down in ((0.08, 0.62, True), (-0.62, -0.08, False)):
        if down:
            mb.obox((cab1 - 0.06, (y0 + y1) / 2, rz_in - 0.10), (0.02, y1 - y0, 0.17), 0.0, "car_interior",
                    color=(0.85, 0.82, 0.76), tilt=(0.0, 0.25))
        else:
            mb.box((cab1 - 0.22, y0, rz_in - 0.035), (cab1 - 0.04, y1, rz_in - 0.01), "car_interior", color=(0.85, 0.82, 0.76))
    # wet leaves caught at the foot of the windshield, round the wipers
    tones = [(0.95, 0.8, 0.55), (0.8, 0.62, 0.4), (0.6, 0.48, 0.34), (0.45, 0.38, 0.3)]
    for _ in range(rng.randint(6, 12)):
        lx = ws_foot + rng.uniform(0.0, 0.22)
        ly = rng.uniform(-hw0 + 0.25, hw0 - 0.25)
        lz = _section(spec, lx, ride)[0][6].z + 0.012
        size = rng.uniform(0.07, 0.12)
        m = Matrix.Translation((lx, ly, lz)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, "X")
        q = [m @ Vector(v) for v in ((-size / 2, -size * 0.6, 0), (size / 2, -size * 0.6, 0), (size / 2, size * 0.6, 0),
                                     (-size / 2, size * 0.6, 0))]
        c = rng.randrange(4)
        cu, cv = (c % 2) * 0.5, (c // 2) * 0.5
        mb.face(q, "leaf_card", uvs=[(cu, cv), (cu + 0.5, cv), (cu + 0.5, cv + 0.5), (cu, cv + 0.5)],
                color=mul(tones[rng.randrange(4)], rng.uniform(0.5, 0.85)))
    # a crashed car's windshield is cracked from where a head or the pole hit it
    if state == "crashed":
        xa, xb = cab1 + 0.12 * (ws_foot - cab1), cab1 + 0.88 * (ws_foot - cab1)
        za, zb = _section(spec, xa, ride)[0][6].z + 0.012, _section(spec, xb, ride)[0][6].z + 0.012
        # one web on the passenger side, square on the glass (the glass is about 1.3 m across)
        y0, y1 = -0.66, 0.02
        mb.face([Vector((xb, y0, zb)), Vector((xb, y1, zb)), Vector((xa, y1, za)), Vector((xa, y0, za))],
                "glass_crack", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # the wagon's roof rack: two rails on six feet
    if kind == "wagon":
        rz = spec["roof"] + ride
        for s in (-1, 1):
            y = s * (hw0 - 0.32)
            mb.box((-2.02, y - 0.018, rz + 0.06), (0.30, y + 0.018, rz + 0.09), "chrome_dull", color=(0.5, 0.5, 0.5))
            for fx_ in (-1.98, -0.86, 0.26):
                mb.box((fx_ - 0.03, y - 0.022, rz - 0.01), (fx_ + 0.03, y + 0.022, rz + 0.07), "plastic_dark")
    # what the town did about it: a ticket under the wiper, and an orange tow
    # notice stuck to the rear side glass
    if state == "abandoned":
        tx = next(k[0] for k in reversed(spec["g"][:-1]) if k[1] == 0) - 0.16
        mb.obox((tx, -0.38, spec["belt"] + ride + 0.16), (0.2, 0.09, 0.004), 0.25, "trim", color=(0.95, 0.94, 0.88),
                tilt=(0.0, -0.55))
        # on the right rear door glass, which leans in about 20 degrees
        nx = spec["pillars"][0] + 0.32
        mb.obox((nx, hw0 - 0.084, spec["belt"] + ride + 0.19), (0.26, 0.004, 0.17), 0.0, "toy_plastic",
                color=(1.3, 0.45, 0.08), tilt=(0.35, 0.0))
    # the pickup's bed: floor, inner walls and the cab's back wall
    if bed:
        x0, x1 = bed
        zf = 0.62 + ride
        yi = hw0 - 0.24
        zr = spec["belt"] + ride + 0.03
        inner = mul(col, 0.55)
        mb.face([Vector((x0, -yi, zf)), Vector((x1, -yi, zf)), Vector((x1, yi, zf)), Vector((x0, yi, zf))], "metal_rust",
                color=(0.7, 0.66, 0.6))
        for s in (-1, 1):
            q = [Vector((x0, s * yi, zf)), Vector((x1, s * yi, zf)), Vector((x1, s * yi, zr)), Vector((x0, s * yi, zr))]
            mb.face(q if s > 0 else list(reversed(q)), "car_paint", color=inner)
        mb.face([Vector((x1, -yi, zf)), Vector((x1, -yi, zr + 0.02)), Vector((x1, yi, zr + 0.02)), Vector((x1, yi, zf))], "car_paint",
                color=inner)
        mb.face([Vector((x0, yi, zf)), Vector((x0, yi, zr)), Vector((x0, -yi, zr)), Vector((x0, -yi, zf))], "car_paint", color=inner)
        # what was left in the back: a spare tyre and a few boards
        spare = _wheel()
        mb.extend(spare, Matrix.Translation((x0 + 0.55, 0.2, zf + 0.11)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        for k in range(3):
            mb.obox((x0 + 1.2, -0.35 + 0.16 * k, zf + 0.03 + 0.01 * k), (1.5, 0.14, 0.03), rng.uniform(-0.08, 0.08),
                    "wood_weathered", color=(0.7, 0.66, 0.6))
    # wheels, or the blocks a car sits on once they are gone
    for axle, front in ((spec["fa"], True), (spec["ra"], False)):
        for s in (-1, 1):
            y = s * (hw0 - 0.115)
            if state == "on_blocks" and rng.random() < 0.75:
                for k in range(2):
                    mb.box((axle - 0.20, y - 0.10 - 0.02 * k, 0.19 * k), (axle + 0.20, y + 0.10 + 0.02 * k, 0.19 * (k + 1)),
                           "barrier_concrete", color=(0.6, 0.58, 0.55))
                mb.cylinder((axle, y - s * 0.05, WHEEL_R + ride + 0.02), (0, s * 0.06, 0), 0.13, "metal_rust", segments=10)
                continue
            is_flat = flat and (rng.random() < 0.7 or state == "crashed" and front)
            w = _wheel(flat=is_flat)
            steer = (0.42 if front and state == "crashed" else 0.0)
            z = WHEEL_R * (0.62 if is_flat else 1.0) + (0.10 if state == "on_blocks" else 0.0)
            mb.extend(w, Matrix.Translation((axle, y, z)) @ Matrix.Rotation(steer, 4, "Z"))
    # dirt and wet leaves settled on the flat tops
    tops = [(x, s) for x, s in zip(xs, secs) if abs(x) < half - 0.4]
    for _ in range(5 if state != "crashed" else 3):
        x, (pts, g, _, _, _, _) = tops[rng.randrange(len(tops))]
        if bed and bed[0] < x < bed[1]:
            continue
        if 0.05 < g < 0.95:
            continue                                             # not on the glass slopes
        y = rng.uniform(-0.45, 0.45)
        mb.card((x, y, pts[6].z + 0.012), rng.uniform(0.5, 0.9), rng.uniform(0.4, 0.8), rng.uniform(0, 3.1),
                "decal_leaves", flat=True)
    # dents: a few soft pushes into the side panels (more on the wrecks)
    for _ in range({"abandoned": 2, "crashed": 5, "on_blocks": 4}[state]):
        side = rng.choice((-1, 1))
        c = Vector((rng.uniform(spec["ra"] + ARCH_R + 0.15, spec["fa"] - ARCH_R - 0.15), side * hw0,
                    rng.uniform(0.45, spec["belt"] + ride - 0.05)))
        radius, depth = rng.uniform(0.16, 0.32), rng.uniform(0.012, 0.03)
        for v in mb.verts:
            if v.y * side < hw0 - 0.08:
                continue
            d2 = ((v.x - c.x) ** 2 + (v.z - c.z) ** 2) / (radius * radius)
            if d2 < 4.0:
                v.y -= side * depth * math.exp(-d2 * 1.5)
    if state == "crashed":
        fa = spec["fa"]
        for v in mb.verts:                                       # the front end pushed back and up
            if v.x > fa + 0.25:
                t = (v.x - fa - 0.25) / (half - fa - 0.25)
                v.x = fa + 0.25 + (v.x - fa - 0.25) * 0.62
                if v.z > 0.7:
                    v.z += 0.13 * math.sin(min(1.0, t) * math.pi) * (1.0 + 0.5 * math.sin(v.y * 5.0))
                v.y += 0.05 * t * math.sin(v.z * 7.0)
    return mb


def build(kind, paint, seed, state, name, coll):
    """One car object, smooth-shaded with crisp creases."""
    return car(kind, paint, seed, state).build(name, coll, sharp_angle=38.0)
