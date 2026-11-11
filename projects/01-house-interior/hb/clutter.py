"""Small loose things, built to be scattered: tins, bottles, cartons, plates,
ashtrays, shoes. Each function adds to a MeshBuilder the caller owns, so a
room's clutter ends up as one or two objects."""

from __future__ import annotations

import math
import random

from mathutils import Vector

import labels
from . import core, shapes
from .shapes import lathe, obox, printed, ring, loft


def tin(mb, x, y, z, region, radius=0.037, height=0.105, turn=0.0, n=10):
    """A food tin with a paper label wrapped round it."""
    (u0, v0), (u1, _), (_, v1), _ = labels.uv(region)
    lo, hi = ring(x, y, z + 0.006, radius, radius, n, yaw=turn), ring(x, y, z + height - 0.006, radius, radius, n,
                                                                      yaw=turn)
    for i in range(n):
        j = (i + 1) % n
        ua, ub = u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n
        mb.face([lo[i], lo[j], hi[j], hi[i]], shapes.print_material(), uvs=[(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    lathe(mb, x, y, [(radius, z), (radius + 0.001, z + 0.006)], "metal_steel", n, cap_last=False)
    lathe(mb, x, y, [(radius + 0.001, z + height - 0.006), (radius, z + height)], "metal_steel", n, cap_first=False)


def bottle(mb, x, y, z, key="glass_bottle", height=0.24, radius=0.032, cap="metal_brass"):
    lathe(mb, x, y, [(radius * 0.9, z), (radius, z + 0.01), (radius, z + height * 0.58),
                     (radius * 0.42, z + height * 0.78), (radius * 0.40, z + height * 0.97)], key, 10)
    lathe(mb, x, y, [(radius * 0.46, z + height * 0.95), (radius * 0.46, z + height)], cap, 8)


def plastic_bottle(mb, x, y, z, region, yaw=0.0, size=(0.07, 0.04, 0.19), cap="plastic_white"):
    """A shampoo or cleaner bottle: a flat-sided body with a label, and a cap."""
    obox(mb, (x, y, z), size, yaw, "c_cream", prints={"front": region})
    lathe(mb, x, y, [(0.014, z + size[2]), (0.014, z + size[2] + 0.028)], cap, 8)


def plate(mb, x, y, z, radius=0.125, key="ceramic"):
    lathe(mb, x, y, [(radius * 0.55, z), (radius * 0.62, z + 0.004), (radius, z + 0.018), (radius, z + 0.022),
                     (radius * 0.6, z + 0.009)], key, 14, cap_last=True)


def plates(mb, x, y, z, count, radius=0.125, rng=None):
    rng = rng or random.Random(1)
    for k in range(count):
        plate(mb, x + rng.uniform(-0.008, 0.008), y + rng.uniform(-0.008, 0.008), z + k * 0.014, radius)


def bowl(mb, x, y, z, radius=0.075, key="ceramic", fill=None):
    lathe(mb, x, y, [(radius * 0.45, z), (radius * 0.55, z + 0.006), (radius, z + 0.055), (radius * 0.96, z + 0.058),
                     (radius * 0.5, z + 0.012)], key, 12)
    if fill:
        mb.face(ring(x, y, z + 0.034, radius * 0.72, radius * 0.72, 10), fill)


def glass(mb, x, y, z, key="glass", height=0.11, radius=0.033):
    lathe(mb, x, y, [(radius * 0.85, z), (radius, z + height), (radius * 0.93, z + height),
                     (radius * 0.80, z + 0.008)], key, 10, cap_last=True)


def pan(mb, x, y, z, radius=0.12, depth=0.045, handle_deg=30.0, key="metal_dark", food=None):
    lathe(mb, x, y, [(radius * 0.9, z), (radius, z + depth), (radius * 0.96, z + depth),
                     (radius * 0.86, z + 0.006)], key, 14, cap_last=True)
    a = math.radians(handle_deg)
    d = Vector((math.cos(a), math.sin(a), 0))
    mb.cylinder(Vector((x, y, z + depth - 0.01)) + d * radius, d * 0.17 + Vector((0, 0, 0.015)), 0.011, "plastic_black",
                segments=6)
    if food:
        mb.face(ring(x, y, z + 0.012, radius * 0.8, radius * 0.8, 12), food)


def pot(mb, x, y, z, radius=0.10, height=0.11, lid=True, key="metal_steel"):
    lathe(mb, x, y, [(radius * 0.95, z), (radius, z + 0.008), (radius, z + height)], key, 14, cap_last=not lid)
    for s in (-1, 1):
        mb.box((x + s * radius - 0.008, y - 0.03, z + height - 0.03), (x + s * radius + 0.03 * s + 0.008, y + 0.03,
                                                                      z + height - 0.018), "plastic_black")
    if lid:
        lathe(mb, x, y, [(radius + 0.004, z + height), (radius * 0.6, z + height + 0.02), (0.0, z + height + 0.026)],
              key, 14, cap_first=False)
        lathe(mb, x, y, [(0.014, z + height + 0.024), (0.018, z + height + 0.05)], "plastic_black", 8)


def takeout(mb, x, y, z, yaw=0.0, open_top=True, tipped=False):
    """A paper take-away carton with a wire handle."""
    obox(mb, (x, y, z), (0.095, 0.075, 0.10), yaw, "c_white", prints={"front": "takeout", "back": "takeout"},
         lean=82.0 if tipped else 0.0)
    if tipped or not open_top:
        return
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for side in (-1, 1):                                     # the two long flaps, standing open
        base = Vector((x, y, z + 0.10)) + Vector((-sa, ca, 0)) * 0.0375 * side
        u = Vector((ca, sa, 0)) * 0.0475
        out = Vector((-sa, ca, 0)) * 0.028 * side + Vector((0, 0, 0.045))
        printed(mb, [base - u, base + u, base + u + out, base - u + out], "c_white")
    arc = [Vector((x, y, z + 0.09)) + Vector((ca, sa, 0)) * 0.05 * math.cos(t) + Vector((0, 0, 0.075)) * math.sin(t)
           for t in (math.pi * k / 8 for k in range(9))]
    shapes.tube(mb, arc, 0.0012, "metal_steel", segments=4)


def cereal(mb, x, y, z, region, yaw=0.0, fallen=False):
    side = {"cereal_a": "c_yellow", "cereal_b": "c_blue", "cereal_c": "c_brown"}[region]
    if fallen:
        obox(mb, (x, y, z), (0.19, 0.28, 0.062), yaw, side, prints={"top": region})
    else:
        obox(mb, (x, y, z), (0.19, 0.062, 0.28), yaw, side, prints={"front": region, "back": region})


def pizza_box(mb, x, y, z, yaw=0.0, lean=0.0):
    obox(mb, (x, y, z), (0.33, 0.33, 0.042), yaw, "c_card", prints={"top": "pizza"}, lean=lean)


def carton(mb, x, y, z, yaw=0.0):
    """A milk carton with its gabled top."""
    obox(mb, (x, y, z), (0.07, 0.07, 0.195), yaw, "c_white", prints={"front": "milk", "back": "milk"})
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    top = Vector((x, y, z + 0.195))
    u, v = Vector((ca, sa, 0)) * 0.035, Vector((-sa, ca, 0)) * 0.035
    ridge_a, ridge_b = top - u + Vector((0, 0, 0.035)), top + u + Vector((0, 0, 0.035))
    printed(mb, [top - u - v, top + u - v, ridge_b, ridge_a], "c_blue")
    printed(mb, [top + u + v, top - u + v, ridge_a, ridge_b], "c_blue")
    printed(mb, [top - u + v, top - u - v, ridge_a], "c_white")
    printed(mb, [top + u - v, top + u + v, ridge_b], "c_white")


def ashtray(mb, x, y, z, butts=5, seed=1, key="glass_bottle"):
    """A heavy glass ashtray, full."""
    rng = random.Random(seed)
    lathe(mb, x, y, [(0.055, z), (0.07, z + 0.006), (0.075, z + 0.03), (0.062, z + 0.03), (0.052, z + 0.01)], key, 12,
          cap_last=True)
    mb.face(ring(x, y, z + 0.014, 0.05, 0.05, 10), "ash")
    for _ in range(butts):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.0, 0.03)
        base = Vector((x + math.cos(a) * r, y + math.sin(a) * r, z + 0.016 + rng.uniform(0, 0.006)))
        d = Vector((math.cos(a + 1.3), math.sin(a + 1.3), rng.uniform(0.0, 0.5))).normalized()
        mb.cylinder(base, d * 0.026, 0.004, "paper_brown", segments=5)
        mb.cylinder(base + d * 0.026, d * 0.012, 0.004, "paper", segments=5)


def cigarettes(mb, x, y, z, yaw=0.0):
    obox(mb, (x, y, z), (0.056, 0.088, 0.022), yaw, "c_white", prints={"top": "cigarettes"})


def shoe(mb, x, y, z, yaw=0.0, key="leather", length=0.29, tipped=False, boot=False):
    """One shoe, heel at the back: a sole and an upper lofted through rings."""
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    roll = math.radians(78.0) if tipped else 0.0

    def P(along, across, up):
        across, up = across * math.cos(roll) - up * math.sin(roll), across * math.sin(roll) + up * math.cos(roll)
        if tipped:
            up += 0.045
        return Vector((x + along * ca - across * sa, y + along * sa + across * ca, z + up))

    def loop(centre, half_len, half_wid, up, n=12, toe=1.0):
        points = []
        for k in range(n):
            t = 2.0 * math.pi * k / n
            c, s = math.cos(t), math.sin(t)
            reach = half_len * (toe if c > 0 else 1.0)
            narrow = 1.0 - 0.18 * max(c, 0.0)             # the toe is narrower than the ball
            points.append(P(centre + c * reach, s * half_wid * narrow, up))
        return points

    half = length / 2.0
    sole = [loop(0.0, half, 0.048, 0.0), loop(0.0, half, 0.050, 0.014)]
    loft(mb, sole, "rubber", cap_first=True, cap_last=True)
    top = 0.16 if boot else 0.075
    rings = [loop(0.0, half * 0.98, 0.047, 0.014), loop(-0.004, half * 0.95, 0.046, 0.045, toe=0.96),
             loop(-half * 0.42, half * 0.52, 0.040, top * 0.82), loop(-half * 0.46, half * 0.44, 0.036, top)]
    loft(mb, rings, key)
    # the opening, and the dark inside
    loft(mb, [rings[-1], loop(-half * 0.46, half * 0.36, 0.028, top - 0.012)], "rubber", cap_last=True)


def folded(mb, x, y, z, width, depth, key, layers=3, yaw=0.0, thick=0.022, seed=0):
    """A folded towel, shirt or blanket: a soft stack."""
    rng = random.Random(seed)
    for k in range(layers):
        shrink = 1.0 - 0.03 * k
        obox(mb, (x + rng.uniform(-0.006, 0.006), y + rng.uniform(-0.006, 0.006), z + k * thick),
             (width * shrink, depth * shrink, thick * 0.95), yaw + rng.uniform(-2.5, 2.5), key)


def book(mb, x, y, z, region=None, yaw=0.0, size=(0.13, 0.19, 0.028), key="book_red"):
    if region:
        obox(mb, (x, y, z), size, yaw, "c_cream", prints={"top": region})
    else:
        obox(mb, (x, y, z), size, yaw, key)


def heap(mb, x, y, z, rx, ry, height, key, seed=0, yaw=0.0, n=14):
    """A pile of cloth: dropped clothes, a towel on the floor, washing in a
    basket. A lumpy mound, never the same twice."""
    rng = random.Random(seed)
    rings = []
    for t in (0.0, 0.25, 0.55, 0.8):
        loop = ring(x, y, z + height * (t ** 0.8), rx * (1.0 - 0.75 * t ** 1.4), ry * (1.0 - 0.75 * t ** 1.4), n, 2.4, yaw)
        for p in loop:
            p.x += rng.uniform(-0.12, 0.12) * rx * (0.3 + t)
            p.y += rng.uniform(-0.12, 0.12) * ry * (0.3 + t)
            p.z += rng.uniform(-0.10, 0.16) * height * (0.2 + t)
        rings.append(loop)
    rings.append([Vector((x + rng.uniform(-0.2, 0.2) * rx, y + rng.uniform(-0.2, 0.2) * ry, z + height))])
    loft(mb, rings, key)


def pillow(mb, cx, cy, cz, rx, ry, thick, yaw=0.0, lean=0.0, dent=0.3, seed=0, key="fabric_pillow", grid=(14, 10)):
    """A stuffed pillow or cushion: fat in the middle, pinched to a seam at
    the edge, slept on or sat against. `cz` is the height of its middle;
    `lean` props it up about its long axis."""
    rng = random.Random(seed)
    nu, nv = grid
    tile = core.spec(key).tile
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cl_, sl = math.cos(math.radians(lean)), math.sin(math.radians(lean))
    p1, p2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    du, dv = rng.uniform(-0.25, 0.25), rng.uniform(-0.2, 0.2)

    def place(x, y, z):
        y, z = y * cl_ - z * sl, y * sl + z * cl_
        return Vector((cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z))

    top, bottom, uvs = {}, {}, {}
    for i in range(nu + 1):
        u = -1.0 + 2.0 * i / nu
        for j in range(nv + 1):
            v = -1.0 + 2.0 * j / nv
            puff = max(0.0, (1.0 - abs(u) ** 4) * (1.0 - abs(v) ** 4)) ** 0.45
            x = u * rx * (1.0 - 0.07 * (1.0 - v * v))          # the sides draw in, the corners stay out
            y = v * ry * (1.0 - 0.07 * (1.0 - u * u))
            hollow = dent * math.exp(-((u - du) ** 2 + (v - dv) ** 2) / 0.22)
            crease = 0.07 * math.sin(4.5 * u + p1) * math.sin(3.5 * v + p2)
            top[i, j] = place(x, y, thick * 0.55 * puff * (1.0 - hollow + crease))
            bottom[i, j] = place(x, y, -thick * 0.40 * puff)
            uvs[i, j] = ((x + rx) / tile, (y + ry) / tile)
    for i in range(nu):
        for j in range(nv):
            quad = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            mb.face([top[q] for q in quad], key, uvs=[uvs[q] for q in quad])
            mb.face([bottom[q] for q in quad][::-1], key, uvs=[uvs[q] for q in quad][::-1])


def open_box(mb, x, y, z, size=(0.46, 0.36, 0.30), yaw=0.0, flaps=(118.0, 150.0, 95.0, 140.0), seed=0):
    """A packing box with its flaps open: cardboard inside and out, taped,
    stencilled. Fill it with a heap() or books afterwards."""
    w, d, h = size
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def P(px, py, pz):
        return Vector((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))

    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    for k in range(4):
        (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
        outer = [P(ax, ay, 0), P(bx, by, 0), P(bx, by, h), P(ax, ay, h)]
        printed(mb, outer, "cardboard" if k % 2 == 0 else "c_card")
        printed(mb, [P(bx * 0.985, by * 0.985, 0.004), P(ax * 0.985, ay * 0.985, 0.004), P(ax * 0.985, ay * 0.985, h),
                     P(bx * 0.985, by * 0.985, h)], "c_card")
        # the flap on this side, folded outwards by its own angle
        nx, ny = (ay - by), (bx - ax)
        length = math.hypot(nx, ny)
        nx, ny = nx / length, ny / length                      # outward normal of this wall
        reach = (d if k % 2 == 0 else w) * 0.5
        a = math.radians(flaps[k])
        ox, oy, oz = nx * reach * math.sin(a), ny * reach * math.sin(a), -reach * math.cos(a)
        flap = [P(ax, ay, h), P(bx, by, h), P(bx + ox, by + oy, h + oz), P(ax + ox, ay + oy, h + oz)]
        printed(mb, flap, "c_card")
        printed(mb, flap[::-1], "c_card")
    printed(mb, [P(-w / 2, -d / 2, 0.004), P(w / 2, -d / 2, 0.004), P(w / 2, d / 2, 0.004), P(-w / 2, d / 2, 0.004)],
            "c_card")


def framed(mb, face, a, z, width, region, tilt=0.0, key="wood_dark", border=0.022):
    """A photograph in a plain frame, hung on a wall. `tilt` knocks it crooked."""
    height = width / labels.aspect(region)
    right = (-face.normal).cross(Vector((0, 0, 1)))
    up = Vector((0, 0, 1))
    t = math.radians(tilt)
    right, up = right * math.cos(t) + up * math.sin(t), up * math.cos(t) - right * math.sin(t)
    c = face.P(a, 0.0, z)
    n = face.normal

    def Q(u, v, out):
        return c + right * u + up * v + n * out

    hw, hh = width / 2, height / 2
    printed(mb, [Q(-hw, -hh, 0.008), Q(hw, -hh, 0.008), Q(hw, hh, 0.008), Q(-hw, hh, 0.008)], region)
    bars = ((-hw - border, -hh - border, hw + border, -hh), (-hw - border, hh, hw + border, hh + border),
            (-hw - border, -hh, -hw, hh), (hw, -hh, hw + border, hh))
    for u0, v0, u1, v1 in bars:
        front = [Q(u0, v0, 0.018), Q(u1, v0, 0.018), Q(u1, v1, 0.018), Q(u0, v1, 0.018)]
        back = [Q(u0, v0, 0.0), Q(u1, v0, 0.0), Q(u1, v1, 0.0), Q(u0, v1, 0.0)]
        mb.face(front, key)
        for i in range(4):
            j = (i + 1) % 4
            mb.face([back[i], back[j], front[j], front[i]], key)


def standing_photo(mb, x, y, z, region, yaw=0.0, width=0.13, key="metal_brass"):
    """A photograph in a small frame, propped on a shelf or a table."""
    height = width / labels.aspect(region)
    obox(mb, (x, y, z), (width + 0.024, 0.012, height + 0.024), yaw, key, lean=-12.0)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    lean = math.radians(-12.0)

    def P(px, pz):
        py = -0.0065
        py, pz = py * math.cos(lean) - pz * math.sin(lean), py * math.sin(lean) + pz * math.cos(lean)
        return Vector((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))

    printed(mb, [P(-width / 2, 0.012), P(width / 2, 0.012), P(width / 2, 0.012 + height), P(-width / 2, 0.012 + height)],
            region)


def post(mb, x, y, z, seed=0, spread=0.3, count=8):
    """Letters, bills and flyers where they fell."""
    rng = random.Random(seed)
    regions = ("envelope_a", "envelope_b", "envelope_a", "letter", "menu", "coupon", "magazine_a", "postcard",
               "envelope_b", "receipt")
    for k in range(count):
        region = regions[k % len(regions)]
        width = {"letter": 0.21, "menu": 0.20, "magazine_a": 0.21}.get(region, 0.22 if "envelope" in region else 0.14)
        shapes.sheet(mb, (x + rng.uniform(-spread, spread), y + rng.uniform(-spread * 0.7, spread * 0.7), z), width,
                     region, yaw=rng.uniform(0, 360), lift=0.003 + k * 0.0014)


def paper_stack(mb, x, y, z, count=10, yaw=0.0, seed=0, region="newspaper", width=0.30):
    """A pile of newspapers or magazines, not squared up."""
    rng = random.Random(seed)
    depth = width / labels.aspect(region)
    for k in range(count):
        obox(mb, (x + rng.uniform(-0.012, 0.012), y + rng.uniform(-0.012, 0.012), z + k * 0.009),
             (width, depth, 0.0086), yaw + rng.uniform(-7, 7), "c_cream", prints={"top": region})


def phone(mb, x, y, z, yaw=0.0, key="plastic_cream"):
    """A push-button desk telephone with its handset on the cradle and a coiled cord."""
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def P(px, py, pz):
        return Vector((x + px * ca - py * sa, y + px * sa + py * ca, z + pz))

    obox(mb, (x, y, z), (0.17, 0.21, 0.045), yaw, key)
    obox(mb, tuple(P(0, 0.055, 0.045)), (0.17, 0.09, 0.025), yaw, key)
    for row in range(4):                                       # the keypad
        for col in range(3):
            obox(mb, tuple(P(-0.03 + col * 0.03, -0.075 + row * 0.026, 0.045)), (0.02, 0.017, 0.006), yaw, "plastic_white")
    shapes.tube(mb, [P(-0.07, 0.055, 0.085), P(0.07, 0.055, 0.085)], 0.017, key, segments=8)       # handset bar
    for side in (-1, 1):
        mb.cylinder(P(side * 0.075, 0.055, 0.062), (0, 0, 0.03), 0.026, key, segments=10)
    cord = [P(-0.085, 0.055, 0.07)]
    for k in range(1, 26):
        t = k / 25
        cord.append(P(-0.10 - 0.07 * math.sin(t * math.pi) + 0.008 * math.sin(k * 2.2), 0.05 - 0.12 * t,
                      0.07 - 0.062 * min(1.0, t * 2.2) + 0.008 * math.cos(k * 2.2)))
    shapes.tube(mb, cord, 0.0028, key, segments=4)


def remote(mb, x, y, z, yaw=0.0):
    obox(mb, (x, y, z), (0.05, 0.17, 0.02), yaw, "plastic_black")
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for row in range(4):
        px, py = 0.0, -0.05 + row * 0.03
        obox(mb, (x + px * ca - py * sa, y + px * sa + py * ca, z + 0.02), (0.03, 0.012, 0.003), yaw, "plastic_red"
             if row == 3 else "plastic_cream")


def keys_dish(mb, x, y, z, seed=0):
    rng = random.Random(seed)
    bowl(mb, x, y, z, radius=0.07)
    for _ in range(4):
        a = rng.uniform(0, 6.28)
        mb.box((x + math.cos(a) * 0.02 - 0.02, y + math.sin(a) * 0.02 - 0.005, z + 0.02),
               (x + math.cos(a) * 0.02 + 0.02, y + math.sin(a) * 0.02 + 0.005, z + 0.023), "metal_brass")
    shapes.annulus(mb, x, y, z + 0.022, 0.016, 0.013, 0.002, "metal_steel", n=8)


def umbrella(mb, foot, top):
    """A furled umbrella leaning in a corner."""
    foot, top = Vector(foot), Vector(top)
    axis = top - foot
    mb.cylinder(foot, axis * 0.08, 0.006, "metal_steel", segments=6)
    mb.cylinder(foot + axis * 0.08, axis * 0.72, 0.012, "plastic_black", segments=8, radius_top=0.034)
    mb.cylinder(foot + axis * 0.80, axis * 0.06, 0.034, "plastic_black", segments=8, radius_top=0.010)
    shapes.tube(mb, [foot + axis * 0.86, top, top + Vector((0.035, 0.0, 0.03)), top + Vector((0.06, 0.0, -0.01))], 0.009,
                "wood_dark", segments=6)


def vhs_stack(mb, x, y, z, count=4, yaw=0.0, seed=0):
    rng = random.Random(seed)
    for k in range(count):
        obox(mb, (x + rng.uniform(-0.01, 0.01), y + rng.uniform(-0.01, 0.01), z + k * 0.026), (0.19, 0.105, 0.025),
             yaw + rng.uniform(-6, 6), "c_black", prints={"front": "vhs"})


def suitcase(mb, x, y, z, yaw=0.0, key="leather", seed=0):
    """A suitcase open on the floor, half packed."""
    obox(mb, (x, y, z), (0.62, 0.42, 0.11), yaw, key)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    obox(mb, (x - 0.24 * sa, y + 0.24 * ca, z + 0.11), (0.62, 0.09, 0.42), yaw, key, lean=-14.0)     # the lid, up
    heap(mb, x, y, z + 0.10, 0.27, 0.17, 0.10, "fabric_bed", seed=seed)
    heap(mb, x + 0.12 * ca, y + 0.12 * sa, z + 0.12, 0.12, 0.10, 0.07, "fabric_plaid", seed=seed + 1)


def clock_radio(mb, x, y, z, yaw=0.0):
    obox(mb, (x, y, z), (0.20, 0.10, 0.065), yaw, "plastic_black", sides={"front": "oven_glass"})
