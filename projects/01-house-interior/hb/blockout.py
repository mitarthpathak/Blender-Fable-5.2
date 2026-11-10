"""Blockout-only stand-ins: grey boxes where furniture will go, door leaves,
and a figure for scale. None of this survives into the structure phase."""

from __future__ import annotations

import math

import plan
from .core import MeshBuilder

# Rough heights for the placement guides in plan.FURNITURE.
HEIGHTS = {
    "coats / shoes": 1.7, "console": 0.8, "sofa": 0.8, "table": 0.42, "fire / TV": 1.1,
    "armchair": 0.85, "books": 1.9, "dining table": 0.75, "sideboard": 0.85, "chair": 0.9,
    "wardrobe": 2.0, "bed": 0.55, "drawers": 0.9, "desk": 0.75, "shelves": 1.8, "boxes": 0.6,
}


def build_furniture(coll="blockout"):
    made = []
    for storey, label, x0, y0, x1, y1 in plan.FURNITURE:
        z = plan.FFL[storey]
        mb = MeshBuilder()
        mb.box((x0, y0, z), (x1, y1, z + HEIGHTS.get(label, 0.8)), "blockout_prop", skip="-z")
        made.append(mb.build("proxy_" + label.replace(" / ", "_").replace(" ", "_"), coll))
    return made


def build_door_leaves(coll="blockout"):
    """Flat leaves, each hinged where the plan says and left half open, to
    check swings and clearances."""
    made = []
    for wall in plan.WALLS:
        for o in wall.openings:
            if o.kind != "door":
                continue
            along_x = wall.axis == "x"
            lo, hi = (wall.y0, wall.y1) if along_x else (wall.x0, wall.x1)
            face = hi if o.swing == "+" else lo
            hinge_a = o.start if o.hinge == "start" else o.end
            direction = 1.0 if o.hinge == "start" else -1.0       # closed leaf runs this way
            hinge = (hinge_a, face, o.sill) if along_x else (face, hinge_a, o.sill)
            mb = MeshBuilder()
            t = 0.04
            w = o.width * direction
            c0 = face - t if o.swing == "+" else face
            if along_x:
                mb.box((min(hinge_a, hinge_a + w), c0, o.sill), (max(hinge_a, hinge_a + w), c0 + t, o.head),
                       "blockout_prop")
            else:
                mb.box((c0, min(hinge_a, hinge_a + w), o.sill), (c0 + t, max(hinge_a, hinge_a + w), o.head),
                       "blockout_prop")
            obj = mb.build(o.name, coll, origin=hinge)
            # The front door stays shut: the player opens it later.
            angle = 0.0 if o.name == "door_front" else 55.0
            obj.rotation_euler = (0, 0, math.radians(angle) * open_sign(wall, o))
            made.append(obj)
    return made


def open_sign(wall, o) -> float:
    """Sign of the Z rotation that swings a leaf to its opening side."""
    along_x = wall.axis == "x"
    direction = 1.0 if o.hinge == "start" else -1.0
    side = 1.0 if o.swing == "+" else -1.0
    # A leaf along +x swings to +y with a positive turn; along +y it swings to +x with a negative one.
    return direction * side * (1.0 if along_x else -1.0)


def build_figure(x, y, z, coll="blockout", name="scale_figure_1m80"):
    """A 1.80 m figure: enough to judge door heights and corridor widths."""
    mb = MeshBuilder()
    mb.cylinder((x, y, z), (0, 0, 1.50), 0.21, "collider", segments=14)
    mb.cylinder((x, y, z + 1.55), (0, 0, 0.25), 0.11, "collider", segments=12)
    obj = mb.build(name, coll, smooth=True)
    return obj
