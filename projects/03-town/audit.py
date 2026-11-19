"""Audit town.blend for placement bugs, and print one line per problem.

    blender -b projects/03-town/town.blend --python projects/03-town/audit.py

Every prop is checked as a separate piece: the town's merged sector meshes
(detail_*, mprop_*, leaves_*) are split into their connected parts first.

- FLOAT  a piece whose lowest point is more than 4 cm above the ground under it
- SUNK   a solid piece (can, drum, car, mailbox, prop) buried more than 15 cm
- INSIDE a piece standing inside a house footprint or on a porch where it
         does not belong (yard and street things only)
- FENCE  a piece that a fence line passes through
- ROAD   grass, shrubs or yard things on the road
- TREE   a tree trunk too close to a house wall (1.2 m) or a fence (0.4 m)

Ends with AUDIT <n> problems.
"""

from __future__ import annotations

import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan  # noqa: E402
from tk import street_kit as sk  # noqa: E402

GROUND_PREFIX = ("ground_lawns", "ground_sidewalks", "ground_road", "ground_curbs", "ground_paths", "ground_verge",
                 "ground_station", "ground_beyond", "road_patches", "ground_")
SPLIT_PREFIX = ("detail_", "mprop_", "props")
SOLID = ("trash_can", "yard_drum", "car_", "prop_", "hydrant", "barrier", "jersey")    # (mailbox posts are buried)
YARD_THINGS = ("grass_", "weed_", "shrub_", "leaf_pile", "yard_drum", "tree_", "trash_can_y")

problems = []


def say(kind, name, where, detail):
    problems.append(kind)
    print(f"{kind:6s} {name:28s} at ({where.x:7.2f}, {where.y:7.2f}, {where.z:6.2f})  {detail}")


def world_verts(o):
    m = o.matrix_world
    return [m @ v.co for v in o.data.vertices]


# the ground: one BVH over every ground mesh
ground_objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(GROUND_PREFIX)
               and "colonly" not in o.name and not o.name.startswith("ground_detail")]
verts, polys = [], []
for o in ground_objs:
    base = len(verts)
    verts.extend(world_verts(o))
    polys.extend([[base + i for i in p.vertices] for p in o.data.polygons])
ground = BVHTree.FromPolygons(verts, polys)


def ground_z(x, y):
    hit = ground.ray_cast(Vector((x, y, 20.0)), Vector((0, 0, -1)), 60.0)
    return hit[0].z if hit[0] is not None else None


houses = sk.building_rects()
house_only = [(r, n) for r, n in houses if n.startswith(("house_", "porch_", "wrap_", "shed_", "back_steps"))]
sk.FENCE_SEGMENTS.clear()
sk.fence_layout()
fences = list(sk.FENCE_SEGMENTS)
for lot in plan.LOTS:                     # front fences
    x0, y0, x1, y1 = lot.rect
    if lot.fence in ("picket", "chainlink"):
        front = sk.lot_front(lot)
        if front == "s":
            fences.append(((x0 + 0.1, y0 + 0.25), (x1 - 0.1, y0 + 0.25), lot.fence))
        elif front == "n":
            fences.append(((x0 + 0.1, y1 - 0.25), (x1 - 0.1, y1 - 0.25), lot.fence))


def pieces(o):
    """(name, world vertices) for each connected part of a merged mesh, or the whole object."""
    if not o.name.startswith(SPLIT_PREFIX):
        return [(o.name, world_verts(o))]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    m = o.matrix_world
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, part = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            part.append(m @ a.co)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen:
                    seen.add(b.index)
                    stack.append(b)
        out.append((f"{o.name}#{len(out)}", part))
    bm.free()
    return out


def bbox(vs):
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return lo, hi


scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
checked = 0
for o in bpy.data.objects:
    if o.type != "MESH" or "colonly" in o.name or o.name.startswith(GROUND_PREFIX):
        continue
    colls = {c.name for c in o.users_collection}
    if colls & {"kit", "collision", "houses", "lights", "poles", "fences", "ground", "ground_detail"}:
        continue
    if o.name.startswith(("backdrop", "wires", "edgetree_", "mill", "station", "fallen_tree", "decals", "leaves_",
                          "road_markings", "puddles")):
        continue
    for name, vs in pieces(o):
        if len(vs) < 3:
            continue
        lo, hi = bbox(vs)
        c = (lo + hi) / 2
        size = hi - lo
        checked += 1
        gz = ground_z(c.x, c.y)
        # ground contact: the lowest point against the ground under the piece (its lowest corner's spot)
        if gz is not None and size.z < 4.0:
            low = min(vs, key=lambda v: v.z)
            gz_low = ground_z(low.x, low.y)
            g = gz_low if gz_low is not None else gz
            if lo.z - g > 0.04 and lo.z - g < 0.8 and not name.startswith(("sign_", "pole", "streetlamp")):
                # floating only if nothing is under it: a log on a woodpile or a poster on a pole is fine
                # cast from just above the lowest point and skip the piece's own object, so a
                # thing resting exactly on a porch deck or a box finds what it rests on
                start, under = low + Vector((0, 0, 0.01)), None
                for _ in range(8):
                    hit = scene.ray_cast(dg, start, Vector((0, 0, -1)), distance=lo.z - g + 0.03)
                    if not hit[0]:
                        break
                    inside_self = all(lo[i] - 0.002 <= hit[1][i] <= hi[i] + 0.002 for i in range(3))
                    if hit[4].name != o.name or not inside_self:
                        under = hit[4]                 # another object, or another piece of the same sector
                        break
                    start = hit[1] - Vector((0, 0, 0.001))
                if under is None or under.name.startswith(GROUND_PREFIX):
                    say("FLOAT", name, c, f"lowest point {lo.z - g:.2f} m above the ground")
            elif g - lo.z > 0.15 and name.startswith(SOLID):
                say("SUNK", name, c, f"{g - lo.z:.2f} m into the ground")
        # inside a house, porch or shed (things that stand in yards or on the street)
        if (name.startswith(YARD_THINGS) or name.startswith(("detail_", "mprop_", "prop_", "props"))) and lo.z < 0.3:
            for (x0, y0, x1, y1), hname in house_only:
                if x0 + 0.1 < c.x < x1 - 0.1 and y0 + 0.1 < c.y < y1 - 0.1:
                    if hname.startswith("porch_") and name.startswith(("mprop_", "detail_", "props")):
                        continue                  # porch clutter and lot stories are meant to be on porches
                    say("INSIDE", name, c, f"in {hname}")
                    break
        # a fence line through it (only things bigger than a tuft)
        if max(size.x, size.y) > 0.25 and not name.startswith(("grass_", "weed_", "tree_", "edgetree_")) and lo.z < 0.5:
            for (ax, ay), (bx, by), kind in fences:
                if kind in ("picket", "chainlink") and name.startswith(("leaf_pile", "detail_")):
                    continue                  # leaves and twigs lie under a picket or chain-link fence
                if abs(ay - by) < 1e-6:                   # along x
                    if lo.y < ay < hi.y and lo.x < max(ax, bx) and hi.x > min(ax, bx) and size.y < 3.0:
                        if min(ay - lo.y, hi.y - ay) > 0.06:
                            say("FENCE", name, c, f"{kind} fence at y {ay:.2f} through it")
                            break
                elif lo.x < ax < hi.x and lo.y < max(ay, by) and hi.y > min(ay, by) and size.x < 3.0:
                    if min(ax - lo.x, hi.x - ax) > 0.06:
                        say("FENCE", name, c, f"{kind} fence at x {ax:.2f} through it")
                        break
        # yard things on the road
        if name.startswith(("grass_", "weed_", "shrub_", "leaf_pile", "yard_drum", "trash_can_y")) and sk._on_road(c.x, c.y):
            if not (name.startswith(("grass_", "weed_", "leaf_pile")) and sk._near_curb(c.x, c.y, 0.35)):
                say("ROAD", name, c, "on the road")             # (weeds and leaves in the gutter are meant)

# trees: trunk clearances
for o in bpy.data.objects:
    if not o.name.startswith(("tree_", "edgetree_")) or o.type != "MESH":
        continue
    p = o.location
    for (x0, y0, x1, y1), hname in house_only:
        dx, dy = max(x0 - p.x, 0, p.x - x1), max(y0 - p.y, 0, p.y - y1)
        if (dx * dx + dy * dy) ** 0.5 < 1.2 and hname.startswith(("house_", "shed_")):
            say("TREE", o.name, p, f"trunk {(dx * dx + dy * dy) ** 0.5:.2f} m from {hname}")
    for (ax, ay), (bx, by), kind in fences:
        d = Vector((bx - ax, by - ay))
        t = max(0.0, min(1.0, ((p.x - ax) * d.x + (p.y - ay) * d.y) / max(d.length_squared, 1e-9)))
        q = Vector((ax + d.x * t, ay + d.y * t))
        if (q - p.xy).length < 0.4:
            say("TREE", o.name, p, f"trunk {(q - p.xy).length:.2f} m from a {kind} fence")
            break

print(f"AUDIT {len(problems)} problems in {checked} pieces checked")
from collections import Counter
print("AUDIT by kind:", dict(Counter(problems)))
