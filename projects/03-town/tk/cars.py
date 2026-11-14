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

from mathutils import Matrix, Vector

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
    return p, g, arch, hw


def _quad(mb, a, b, c, d, mat, colour):
    if (b - a).cross(d - a).length < 1e-6 and (c - b).cross(d - c).length < 1e-6:
        return
    mb.face([a, b, c, d], mat, color=colour)


def _wheel(flat=False):
    """Tyre and hubcap, axle along Y, centred on the origin."""
    mb = MeshBuilder()
    r, w = WHEEL_R, 0.10
    rings = [(-w, r - 0.05), (-w * 0.8, r - 0.008), (-w * 0.3, r), (w * 0.3, r), (w * 0.8, r - 0.008), (w, r - 0.05)]
    seg = 18
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
    for (x0, (a, g0, arch0, _)), (x1, (b, g1, arch1, _)) in zip(zip(xs, secs), zip(xs[1:], secs[1:])):
        xm = (x0 + x1) / 2
        gm = (g0 + g1) / 2
        in_pillar = any(abs(xm - p) < 0.05 for p in spec["pillars"])
        in_bed = bed is not None and bed[0] < xm < bed[1]
        sloped = abs(g1 - g0) > 0.02                             # windshield or rear glass
        for side in (1, -1):
            def P(pts, i):
                v = pts[i]
                return Vector((v.x, v.y * side, v.z))
            for i in range(6):
                q = [P(a, i), P(b, i), P(b, i + 1), P(a, i + 1)]
                if side < 0:
                    q.reverse()
                centre = (q[0] + q[1] + q[2] + q[3]) / 4
                if i < 3:
                    near_arch = arch0 > 0 or arch1 > 0
                    rusty = rng.random() < rust_level * (0.75 if (i == 0 or near_arch) else 0.12)
                    if rusty:
                        _quad(mb, *q, "metal_rust", jitter_color(rng, (0.75, 0.68, 0.6), 0.12))
                    else:
                        _quad(mb, *q, "car_paint", tone(centre))
                elif i == 3:                                     # belt to glass top
                    glass = gm > 0.6 and not in_pillar and not sloped
                    _quad(mb, *q, "car_glass" if glass else "car_paint", None if glass else tone(centre))
                    if glass:
                        continue
                elif i == 4:                                     # roof rail, or the rail of the bed
                    _quad(mb, *q, "car_paint", tone(centre, top=gm < 0.1))
                elif in_bed:
                    continue                                     # open bed
                elif sloped and gm > 0.08:
                    _quad(mb, *q, "car_glass", None)
                    continue
                else:
                    _quad(mb, *q, "car_paint", tone(centre, top=True))
                # the inside of the same panel: headlining and door cards, a little inboard
                if gm > 0.02:
                    inner = [Vector((v.x, v.y * 0.985, v.z - (0.014 if i >= 4 else 0.0))) for v in reversed(q)]
                    _quad(mb, *inner, "car_interior", (0.9, 0.88, 0.84) if i >= 4 else (1.0, 1.0, 1.0))
            # wheel-arch liner behind the cut
            if arch0 > 0 or arch1 > 0:
                za, zb_ = max(arch0, a[0].z), max(arch1, b[0].z)
                ya = (hw0 - 0.004) * side
                yi = (hw0 - 0.34) * side
                q = [Vector((x0, ya, za)), Vector((x1, ya, zb_)), Vector((x1, yi, zb_)), Vector((x0, yi, za))]
                mb.face(q if side < 0 else list(reversed(q)), "interior_dark")
                q = [Vector((x0, yi, 0.12)), Vector((x1, yi, 0.12)), Vector((x1, yi, zb_)), Vector((x0, yi, za))]
                mb.face(q if side > 0 else list(reversed(q)), "interior_dark")
        # floor pan (it faces up: this is the carpet seen through the glass)
        mb.face([Vector((x0, a[0].y, a[0].z)), Vector((x0, -a[0].y, a[0].z)), Vector((x1, -b[0].y, b[0].z)),
                 Vector((x1, b[0].y, b[0].z))], "car_interior", color=(0.7, 0.68, 0.64))
    # nose and tail panels
    for pts, front in ((secs[-1][0], True), (secs[0][0], False)):
        loop = [Vector((v.x, v.y, v.z)) for v in pts] + [Vector((v.x, -v.y, v.z)) for v in reversed(pts[:-1])]
        mb.face(loop if front else list(reversed(loop)), "car_paint", color=tone(pts[3]))

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
    mb.box((-half - 0.012, -0.16, zt - 0.02), (-half, 0.16, zt + 0.10), "trim", color=(0.75, 0.74, 0.68))
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
        x, (pts, g, _, _) = tops[rng.randrange(len(tops))]
        if bed and bed[0] < x < bed[1]:
            continue
        if 0.05 < g < 0.95:
            continue                                             # not on the glass slopes
        y = rng.uniform(-0.45, 0.45)
        mb.card((x, y, pts[6].z + 0.012), rng.uniform(0.5, 0.9), rng.uniform(0.4, 0.8), rng.uniform(0, 3.1),
                "decal_leaves", flat=True)
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
