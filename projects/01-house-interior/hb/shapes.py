"""Shapes the box-and-cylinder MeshBuilder does not have: rounded rings to loft
through (baths, basins, seats), turned profiles, boxes at an angle, and
quads that carry a picture from the print sheet."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

import labels
from . import core


def ring(cx, cy, z, rx, ry, n=20, power=2.0, yaw=0.0):
    """A closed loop of points round (cx, cy) at height z, counter-clockwise
    from above. power 2 is an ellipse; higher squares it off."""
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    points = []
    for k in range(n):
        t = 2.0 * math.pi * k / n
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** (2.0 / power), c)
        y = ry * math.copysign(abs(s) ** (2.0 / power), s)
        points.append(Vector((cx + x * ca - y * sa, cy + x * sa + y * ca, z)))
    return points


def loft(mb, rings, key, cap_first=False, cap_last=False):
    """Skin a run of rings. Going up, the faces look outwards; a run that
    climbs the outside of a bath, crosses the rim and goes down the inside
    comes out the right way round all the way. A one-point ring is an apex."""
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(len(b)):
                mb.face([a[0], b[(i + 1) % len(b)], b[i]][::-1], key)
        elif len(b) == 1:
            for i in range(len(a)):
                mb.face([a[i], a[(i + 1) % len(a)], b[0]], key)
        else:
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                mb.face([a[i], a[j], b[j], b[i]], key)
    if cap_first and len(rings[0]) > 2:
        mb.face(rings[0][::-1], key)
    if cap_last and len(rings[-1]) > 2:
        mb.face(rings[-1], key)


def lathe(mb, cx, cy, profile, key, n=16, cap_first=True, cap_last=True):
    """A turned shape: `profile` is (radius, z) pairs from bottom to top."""
    rings = [[Vector((cx, cy, z))] if r <= 1e-5 else ring(cx, cy, z, r, r, n) for r, z in profile]
    loft(mb, rings, key, cap_first, cap_last)


def tube(mb, points, radius, key, segments=8):
    """A bent pipe through the given points."""
    points = [Vector(p) for p in points]
    for a, b in zip(points, points[1:]):
        if (b - a).length > 1e-5:
            mb.cylinder(a, b - a, radius, key, segments=segments)


def soften(obj, angle=42.0):
    """Smooth shading that keeps real corners crisp: for anything turned,
    lofted or padded."""
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(angle))
    return obj


def obox(mb, centre, size, yaw, key, prints=None, lean=0.0, sides=None):
    """A box standing on `centre` (the middle of its base), turned `yaw`
    degrees about Z and optionally leant back `lean` degrees about its base
    edge. `size` is (width, depth, height); the front is the -Y face before
    turning. `prints` maps "front", "back", "left", "right", "top" to a
    region of the print sheet; `sides` maps them to another material. Other
    faces take `key`, which may itself be a region name starting "c_" for a
    flat colour from the sheet."""
    w, d, h = size
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cl, sl = math.cos(math.radians(lean)), math.sin(math.radians(lean))
    c = Vector(centre)

    def P(x, y, z):
        y, z = y * cl - z * sl + 0.0, y * sl + z * cl          # lean about the X axis through the base
        return c + Vector((x * ca - y * sa, x * sa + y * ca, z))

    x0, x1, y0, y1 = -w / 2, w / 2, -d / 2, d / 2
    faces = {      # corners as seen from outside: bottom-left, bottom-right, top-right, top-left
        "front": [P(x0, y0, 0), P(x1, y0, 0), P(x1, y0, h), P(x0, y0, h)],
        "back": [P(x1, y1, 0), P(x0, y1, 0), P(x0, y1, h), P(x1, y1, h)],
        "left": [P(x0, y1, 0), P(x0, y0, 0), P(x0, y0, h), P(x0, y1, h)],
        "right": [P(x1, y0, 0), P(x1, y1, 0), P(x1, y1, h), P(x1, y0, h)],
        "top": [P(x0, y0, h), P(x1, y0, h), P(x1, y1, h), P(x0, y1, h)],
        "bottom": [P(x0, y1, 0), P(x1, y1, 0), P(x1, y0, 0), P(x0, y0, 0)],
    }
    prints, sides = prints or {}, sides or {}
    for side, corners in faces.items():
        region = prints.get(side) or (key if key.startswith("c_") and side not in sides else None)
        if side in sides and side not in prints:
            mb.face(corners, sides[side])
        elif region:
            printed(mb, corners, region)
        else:
            mb.face(corners, key)


def printed(mb, corners, region):
    """A quad showing one region of the print sheet. Corners run bottom-left,
    bottom-right, top-right, top-left as the picture should be seen."""
    mb.face([Vector(p) for p in corners], print_material(), uvs=labels.uv(region))


def sheet(mb, centre, width, region, yaw=0.0, height=None, lift=0.0):
    """A printed sheet lying flat (a newspaper, a letter, a photograph)."""
    height = height or width / labels.aspect(region)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    c = Vector(centre) + Vector((0, 0, lift))
    u, v = Vector((ca, sa, 0)) * width / 2, Vector((-sa, ca, 0)) * height / 2
    printed(mb, [c - u - v, c + u - v, c + u + v, c - u + v], region)


def poster(mb, face, a, z, width, region, off=0.004, tilt=0.0):
    """A printed sheet pinned to a wall, centred at (a, z)."""
    height = width / labels.aspect(region)
    t = math.tan(math.radians(tilt)) * width / 2
    along = face.along
    # Which way is "right" when you stand facing the wall.
    right = (-face.normal).cross(Vector((0, 0, 1)))
    s = 1.0 if right.dot(along) > 0 else -1.0
    left_a, right_a = a - s * width / 2, a + s * width / 2
    corners = [face.P(left_a, off, z - height / 2 + t), face.P(right_a, off, z - height / 2 - t),
               face.P(right_a, off, z + height / 2 - t), face.P(left_a, off, z + height / 2 + t)]
    printed(mb, corners, region)


def print_material() -> str:
    """The key of the one material every printed thing uses."""
    key = "print"
    mat = core.material(key)
    if mat.get("print_ready") or not labels.SHEET.exists():
        return key
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(labels.SHEET), check_existing=True)
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = 0.72
    mat["print_ready"] = True
    return key


def cavity(mb, lo, hi, key, open_side="+z"):
    """The inside of a box with one side missing: a sink bowl or a drawer
    (open "+z"), the inside of a fridge or a cupboard (open towards the room)."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    hx, hy, hz = (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2
    sides = {
        "-x": ((x0, cy, cz), (0, hy, 0), (0, 0, hz), (1, 0, 0)),
        "+x": ((x1, cy, cz), (0, hy, 0), (0, 0, hz), (-1, 0, 0)),
        "-y": ((cx, y0, cz), (hx, 0, 0), (0, 0, hz), (0, 1, 0)),
        "+y": ((cx, y1, cz), (hx, 0, 0), (0, 0, hz), (0, -1, 0)),
        "-z": ((cx, cy, z0), (hx, 0, 0), (0, hy, 0), (0, 0, 1)),
        "+z": ((cx, cy, z1), (hx, 0, 0), (0, hy, 0), (0, 0, -1)),
    }
    for side, (centre, hu, hv, normal) in sides.items():
        if side != open_side:
            mb.rect(centre, hu, hv, normal, key)


def annulus(mb, cx, cy, z, r_out, r_in, height, key, n=14):
    """A flat ring: a hob element, the rim of a plate, a washer."""
    loft(mb, [ring(cx, cy, z, r_out, r_out, n), ring(cx, cy, z + height, r_out, r_out, n),
              ring(cx, cy, z + height, r_in, r_in, n), ring(cx, cy, z, r_in, r_in, n)], key)


def disc(mb, centre, normal, radius, region, n=20):
    """A round print, such as a clock face, on a plane facing `normal`."""
    c, w = Vector(centre), Vector(normal).normalized()
    up = Vector((0, 0, 1)) if abs(w.z) < 0.9 else Vector((0, 1, 0))
    right = up.cross(w).normalized()
    up = w.cross(right)
    (u0, v0), (u1, _), (_, v1), _ = labels.uv(region)
    points, uvs = [], []
    for k in range(n):
        t = 2.0 * math.pi * k / n
        points.append(c + (right * math.cos(t) + up * math.sin(t)) * radius)
        uvs.append((u0 + (u1 - u0) * (0.5 + 0.5 * math.cos(t)), v0 + (v1 - v0) * (0.5 + 0.5 * math.sin(t))))
    mb.face(points, print_material(), uvs=uvs)
