"""Check how the house sits on its lot in film.blend. Read-only.

    blender -b film.blend --python check_seams.py

Prints SEAM lines: ground heights round the house against the heights
docs/TOWN.md promises, where the town's path meets the porch steps, and
every town object whose bounding box runs into something that belongs to the
house (walls, porch, chimney, back steps, shed, woodpile, clothesline).
"""

import bpy
from mathutils import Vector

scene = bpy.context.scene
deps = bpy.context.evaluated_depsgraph_get()


def lib_of(obj):
    return (obj.library.filepath if obj.library else "").replace("\\", "/")


def box(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def ground(x, y, top=-0.20):
    hit, loc, _, _, obj, _ = scene.ray_cast(deps, Vector((x, y, top)), Vector((0, 0, -1)), distance=3.0)
    return (loc.z, obj.name) if hit else (None, None)


print("SEAM == ground heights (expected: lawn -0.45, sidewalk -0.40, road -0.53)")
for label, x, y, want in (("front lawn", 5.5, -5.0, -0.45), ("foot of porch steps", 1.78, -3.05, -0.45),
                          ("path to the street", 1.78, -6.0, -0.45), ("sidewalk", 1.78, -9.4, -0.40),
                          ("road", 1.78, -14.0, -0.53), ("west side yard", -2.2, 4.0, -0.45),
                          ("east side yard", 9.6, 4.0, -0.45), ("back yard", 4.0, 12.0, -0.45),
                          ("foot of back steps", 1.8, 10.0, -0.45), ("by the shed", 8.4, 16.3, -0.45),
                          ("north-west corner of lot", -4.0, 17.5, -0.45)):
    z, name = ground(x, y)
    if z is None:
        print(f"SEAM   GAP   {label}: no ground under ({x}, {y})")
    else:
        flag = "ok " if abs(z - want) < 0.035 else "OFF"
        print(f"SEAM   {flag}   {label}: {z:+.3f} on {name} (want {want:+.2f})")

mine = [o for o in scene.objects if "01-house-interior" in lib_of(o) and o.type == "MESH"]
theirs = [o for o in scene.objects if "03-town" in lib_of(o) and o.type == "MESH"]
print(f"SEAM == {len(mine)} house meshes, {len(theirs)} town meshes")

solid = [o for o in mine if not o.name.startswith(("decals", "ground_dirt", "glass_", "fog"))]
flat = ("ground", "road", "decals", "weed", "leaf", "puddle", "wire", "grass")
print("SEAM == town objects that run into the house or what stands in its yard")
found = 0
for t in theirs:
    if t.name.startswith(flat):
        continue
    tlo, thi = box(t)
    if (thi - tlo).length > 40:                              # whole-town meshes (fences, wires): checked by raycast below
        continue
    for h in solid:
        hlo, hhi = box(h)
        if all(tlo[i] < hhi[i] - 0.02 and thi[i] > hlo[i] + 0.02 for i in range(3)):
            found += 1
            print(f"SEAM   HIT   {t.name} overlaps {h.name}  town box ({tlo.x:.2f},{tlo.y:.2f},{tlo.z:.2f})-({thi.x:.2f},{thi.y:.2f},{thi.z:.2f})")
            break
if not found:
    print("SEAM   ok    none")

print("SEAM == what the town puts inside lot L1 (x -4.5..11.5, y -8.6..18.0), for reference")
for t in theirs:
    tlo, thi = box(t)
    c = (tlo + thi) / 2
    if -4.5 < c.x < 11.5 and -8.6 < c.y < 18.0 and (thi - tlo).length < 12 and not t.name.startswith(("weed", "decals")):
        print(f"SEAM   L1    {t.name} at ({c.x:.1f}, {c.y:.1f}), size {(thi - tlo).x:.1f} x {(thi - tlo).y:.1f} x {(thi - tlo).z:.1f}")

print("SEAM == fences: a ray north, east and west from the yard at 1 m")
for label, origin, direction in (("north", (4.0, 12.0, 0.5), (0, 1, 0)), ("east", (9.5, 12.0, 0.5), (1, 0, 0)),
                                 ("west", (-1.5, 12.0, 0.5), (-1, 0, 0)), ("shed to east fence", (11.2, 16.3, 0.5), (1, 0, 0)),
                                 ("shed to north fence", (10.0, 17.3, 0.5), (0, 1, 0))):
    hit, loc, _, _, obj, _ = scene.ray_cast(deps, Vector(origin), Vector(direction), distance=30.0)
    print(f"SEAM   {label}: " + (f"{obj.name} at {(loc - Vector(origin)).length:.2f} m ({loc.x:.2f}, {loc.y:.2f})" if hit else "nothing within 30 m"))
