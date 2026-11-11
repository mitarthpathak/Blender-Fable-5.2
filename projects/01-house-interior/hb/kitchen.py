"""The kitchen: a fitted kitchen of about 1990 that nobody has cleaned in a
while. Everything here is built, not imported: oak-effect cabinets, speckled
laminate counters, an almond fridge left open, an electric cooker with a
stained hob, a steel sink full of dishes, a laminate table and vinyl chairs.

The room is x 2.54 to 7.30, y 4.54 to 8.00. The counter runs along the north
wall under the window and down the east wall; the fridge stands in the
south-east corner; the table is in the middle.
"""

from __future__ import annotations

import math
import random

from mathutils import Vector

import labels
import plan
from . import clutter as cl
from . import dressing as dr
from . import joinery, shapes
from .core import MeshBuilder
from .dressing import DIVIDER_N, EAST, NORTH, ROOM_WEST, Decals, Face

GF = 0.0
TOP = 0.90            # counter height
CARCASS = 0.58        # cabinet depth without doors
DOOR_T = 0.018
WALL_Z0, WALL_Z1, WALL_D = 1.42, 2.12, 0.32
TUBE = (0.74, 0.90, 0.86)      # an old cool-white fluorescent tube: pale, slightly green


# --- Cabinets -----------------------------------------------------------------

def _door(mb, face, a0, a1, z0, z1, depth, ajar=0.0, hinge_low=True, key="cabinet"):
    """A framed cabinet door closing against the carcass at `depth`."""
    w, h = a1 - a0 - 0.006, z1 - z0
    theta = math.radians(ajar)
    hinge = a0 + 0.003 if hinge_low else a1 - 0.003
    s = 1.0 if hinge_low else -1.0

    def to_world(u, d, v):
        out = DOOR_T - d
        return face.P(hinge + s * u * math.cos(theta), depth + u * math.sin(theta) + out, z0 + v)

    joinery.build_leaf(mb, to_world, w, h, DOOR_T, [(0.055, 0.055, w - 0.055, h - 0.055, False)], key)
    pull = to_world(w - 0.035, 0.0, h - 0.08 if z0 < 1.0 else 0.08)         # a knob at the free corner
    mb.cylinder(pull, face.normal * 0.022, 0.007, "metal_brass", segments=6)


def base_units(mb, face, a0, a1, sink=None, open_door=None, missing=None):
    """Floor cabinets from a0 to a1: plinth, carcass, a drawer over a door
    per unit, and the counter with its upstand. `sink` (a0, a1) leaves the
    carcass open under a cut-out in the counter."""
    count = max(1, round((a1 - a0) / 0.47))
    width = (a1 - a0) / count
    face.box(mb, a0, a1, 0.03, CARCASS - 0.06, GF, GF + 0.10, "plastic_black")                    # plinth
    for k in range(count):
        ua, ub = a0 + k * width, a0 + (k + 1) * width
        over_sink = sink and ua < sink[1] and ub > sink[0]
        if over_sink:                    # the carcass stops below the bowls; a rail carries the false drawer front
            face.box(mb, ua, ub, 0.0, CARCASS, GF + 0.10, GF + 0.69, "cabinet")
            face.box(mb, ua, ub, CARCASS - 0.018, CARCASS, GF + 0.69, GF + 0.86, "cabinet")
        else:
            face.box(mb, ua, ub, 0.0, CARCASS, GF + 0.10, GF + 0.86, "cabinet")
        face.box(mb, ua + 0.003, ub - 0.003, CARCASS, CARCASS + DOOR_T, GF + 0.725, GF + 0.855, "cabinet")
        if not over_sink:                                              # under the sink the drawer front is false
            p = face.P((ua + ub) / 2, CARCASS + DOOR_T, GF + 0.79)
            mb.cylinder(p - face.along * 0.045, face.along * 0.09, 0.006, "metal_brass", segments=6)
        if k == missing:
            continue
        _door(mb, face, ua, ub, GF + 0.115, GF + 0.715, CARCASS, ajar=38.0 if k == open_door else 0.0,
              hinge_low=k % 2 == 0)


def counter(mb, face, a0, a1, sink=None):
    """Laminate worktop with a rounded-over front and an upstand at the wall."""
    z0, z1, depth = GF + 0.86, GF + TOP, 0.625
    if sink:
        s0, s1 = sink
        face.box(mb, a0, s0, 0.0, depth, z0, z1, "counter")
        face.box(mb, s1, a1, 0.0, depth, z0, z1, "counter")
        face.box(mb, s0, s1, 0.0, 0.10, z0, z1, "counter")
        face.box(mb, s0, s1, 0.52, depth, z0, z1, "counter")
    else:
        face.box(mb, a0, a1, 0.0, depth, z0, z1, "counter")
    face.box(mb, a0, a1, 0.0, 0.018, z1, z1 + 0.09, "counter")


def wall_units(mb, face, a0, a1, z0=WALL_Z0, z1=WALL_Z1, open_door=None, missing=None, shelf_stuff=None):
    count = max(1, round((a1 - a0) / 0.47))
    width = (a1 - a0) / count
    for k in range(count):
        ua, ub = a0 + k * width, a0 + (k + 1) * width
        if k == missing or k == open_door:
            # an open carcass: sides, top, bottom, back and a shelf
            t = 0.018
            face.box(mb, ua, ua + t, 0.0, WALL_D, z0, z1, "cabinet")
            face.box(mb, ub - t, ub, 0.0, WALL_D, z0, z1, "cabinet")
            face.box(mb, ua + t, ub - t, 0.0, WALL_D, z0, z0 + t, "cabinet")
            face.box(mb, ua + t, ub - t, 0.0, WALL_D, z1 - t, z1, "cabinet")
            face.box(mb, ua + t, ub - t, 0.0, 0.006, z0 + t, z1 - t, "cabinet")
            face.box(mb, ua + t, ub - t, 0.006, WALL_D - 0.02, (z0 + z1) / 2, (z0 + z1) / 2 + t, "cabinet")
            if shelf_stuff:
                shelf_stuff(face, ua + t, ub - t, z0 + t, (z0 + z1) / 2 + t)
        else:
            face.box(mb, ua, ub, 0.0, WALL_D, z0, z1, "cabinet")
        if k != missing:
            _door(mb, face, ua, ub, z0 + 0.004, z1 - 0.004, WALL_D, ajar=62.0 if k == open_door else 0.0,
                  hinge_low=k % 2 == 0)


def cabinets():
    mb = MeshBuilder()
    sink = (4.42, 5.42)
    base_units(mb, NORTH, 3.30, 7.30 - CARCASS - 0.02, sink=sink, open_door=1)
    face_n = NORTH
    face_n.box(mb, 7.30 - CARCASS - 0.02, 7.30, 0.0, CARCASS, GF, GF + 0.86, "cabinet")       # the blind corner
    counter(mb, NORTH, 3.30, 7.30, sink=sink)
    base_units(mb, EAST, 5.34, 5.95, missing=None)
    counter(mb, EAST, 5.34, 5.95)
    base_units(mb, EAST, 6.71, 8.0 - 0.625, open_door=None)
    counter(mb, EAST, 6.71, 8.0 - 0.625)
    face_n.box(mb, 3.30 - 0.02, 3.30, 0.0, CARCASS + 0.02, GF, GF + 0.86, "cabinet")           # end panel
    obj = mb.build("kitchen_cabinets", "furniture", recalc=True)

    small = MeshBuilder()

    def tins(face, a0, a1, z_low, z_high):
        rng = random.Random(4)
        a = a0 + 0.06
        for region in ("soup", "beans", "soup"):
            p = face.P(a, 0.16 + rng.uniform(-0.03, 0.03), z_low)
            cl.tin(small, p.x, p.y, p.z, region, turn=rng.uniform(0, 360))
            a += 0.095
        p = face.P(a0 + 0.12, 0.15, z_high)
        cl.cereal(small, p.x, p.y, p.z, "cereal_c", yaw=face.facing + 90 + 12)
        p = face.P(a0 + 0.30, 0.17, z_high)
        cl.tin(small, p.x, p.y, p.z, "beans", turn=40)

    wall = MeshBuilder()
    wall_units(wall, NORTH, 3.30, 3.84, missing=None)
    wall_units(wall, NORTH, 6.02, 7.30, open_door=1, shelf_stuff=tins)
    wall_units(wall, EAST, 5.34, 5.95)
    wall_units(wall, EAST, 6.71, 8.0 - WALL_D)
    wall_units(wall, EAST, 4.60, 5.32, z0=1.80, z1=2.12)                                        # over the fridge
    wall.build("kitchen_wall_cabinets", "furniture", recalc=True)

    tiles = MeshBuilder()
    for face, a0, a1, z1 in ((NORTH, 3.30, 3.85, WALL_Z0), (NORTH, 5.99, 7.30, WALL_Z0),
                             (EAST, 5.34, 5.95, WALL_Z0), (EAST, 5.95, 6.71, 1.56), (EAST, 6.71, 7.40, WALL_Z0)):
        face.box(tiles, a0, a1, 0.0, 0.007, GF + TOP + 0.09, z1, "tile_kitchen")
    tiles.build("kitchen_splashback", "fixtures")
    return obj, small


def sink(small):
    mb = MeshBuilder()
    y0, y1, z0, z1 = 8.0 - 0.52, 8.0 - 0.10, GF + 0.70, GF + TOP
    for x0, x1 in ((4.42, 4.90), (4.94, 5.42)):
        shapes.cavity(mb, (x0, y0, z0), (x1, y1, z1), "metal_steel")
        mb.cylinder((x0 + (x1 - x0) / 2, (y0 + y1) / 2, z0), (0, 0, 0.002), 0.03, "metal_dark", segments=10)
    mb.box((4.90, y0, z1 - 0.02), (4.94, y1, z1 + 0.003), "metal_steel")                         # between the bowls
    for lo, hi in (((4.40, y0 - 0.02, z1), (5.44, y0, z1 + 0.003)), ((4.40, y1, z1), (5.44, y1 + 0.04, z1 + 0.003)),
                   ((4.40, y0, z1), (4.42, y1, z1 + 0.003)), ((5.42, y0, z1), (5.44, y1, z1 + 0.003))):
        mb.box(lo, hi, "metal_steel")                                                           # the rim
    # mixer tap: two cross-head valves and a swan neck
    base = Vector((4.92, y1 + 0.02, z1 + 0.003))
    shapes.tube(mb, [base, base + Vector((0, 0, 0.20)), base + Vector((0, -0.05, 0.25)), base + Vector((0, -0.13, 0.25)),
                     base + Vector((0, -0.16, 0.21))], 0.011, "metal_chrome", segments=8)
    for dx in (-0.09, 0.09):
        mb.cylinder(base + Vector((dx, 0, 0)), (0, 0, 0.05), 0.014, "metal_chrome", segments=8)
        mb.box((base.x + dx - 0.03, base.y - 0.006, base.z + 0.05), (base.x + dx + 0.03, base.y + 0.006, base.z + 0.062),
               "metal_chrome")
    shapes.soften(mb.build("kitchen_sink", "fixtures"))

    # the washing-up nobody did
    rng = random.Random(8)
    small.rect((5.18, (y0 + y1) / 2, z0 + 0.075), (0.24, 0, 0), (0, 0.21, 0), (0, 0, 1), "dishwater")
    cl.plates(small, 4.66, 7.70, z0 + 0.002, 6, rng=rng)
    cl.bowl(small, 4.56, 7.60, z0 + 0.09)
    cl.pan(small, 5.20, 7.70, z0 + 0.05, handle_deg=205, food="food_brown")
    dr.mug(small, 5.30, 7.56, z0 + 0.03)
    cl.glass(small, 4.80, 7.56, z0 + 0.002)
    # draining rack on the counter with plates stood in it
    rack_x0, rack_x1 = 5.58, 5.94
    small.box((rack_x0, 7.52, GF + TOP), (rack_x1, 7.88, GF + TOP + 0.012), "plastic_cream")
    for k in range(5):
        x = rack_x0 + 0.05 + k * 0.058
        small.cylinder((x, 7.70, GF + TOP + 0.125), (0.010, 0, 0.004), 0.115, "ceramic", segments=14)
        small.box((x - 0.022, 7.56, GF + TOP + 0.012), (x - 0.018, 7.84, GF + TOP + 0.06), "plastic_cream")
    cl.plastic_bottle(small, 4.30, 7.86, GF + TOP, "bleach", yaw=8, size=(0.085, 0.05, 0.22))
    shapes.obox(small, (4.14, 7.62, GF + TOP), (0.11, 0.07, 0.03), 24, "c_yellow")                # a sponge


# --- Appliances ---------------------------------------------------------------

def stove(small):
    """A free-standing electric cooker, 76 cm wide, on the east wall."""
    mb = MeshBuilder()
    a0, a1 = 5.955, 6.705
    front = 0.655
    EAST.box(mb, a0, a1, 0.02, front, GF + 0.02, GF + 0.895, "enamel")
    EAST.box(mb, a0 + 0.03, a1 - 0.03, 0.05, front - 0.04, GF, GF + 0.02, "plastic_black")
    EAST.box(mb, a0 - 0.002, a1 + 0.002, 0.02, front + 0.012, GF + 0.895, GF + 0.912, "hob")       # the hob
    EAST.box(mb, a0, a1, 0.02, 0.085, GF + 0.912, GF + 1.13, "enamel")                            # backguard
    shapes.printed(mb, [EAST.P(a1 - 0.02, 0.0865, GF + 1.00), EAST.P(a0 + 0.02, 0.0865, GF + 1.00),
                        EAST.P(a0 + 0.02, 0.0865, GF + 1.115), EAST.P(a1 - 0.02, 0.0865, GF + 1.115)], "stove_panel")
    # oven door with a dark window, a towel-rail handle, and the drawer under it
    EAST.box(mb, a0 + 0.012, a1 - 0.012, front, front + 0.035, GF + 0.20, GF + 0.87, "enamel")
    EAST.box(mb, a0 + 0.10, a1 - 0.10, front + 0.035, front + 0.038, GF + 0.36, GF + 0.70, "oven_glass")
    EAST.box(mb, a0 + 0.012, a1 - 0.012, front, front + 0.03, GF + 0.03, GF + 0.185, "enamel")
    for z in (GF + 0.80, GF + 0.14):
        p = EAST.P(a0 + 0.08, front + 0.075, z)
        mb.cylinder(p, EAST.along * (a1 - a0 - 0.16), 0.011, "metal_chrome", segments=8)
        for a in (a0 + 0.10, a1 - 0.10):
            EAST.box(mb, a - 0.008, a + 0.008, front + 0.03, front + 0.075, z - 0.008, z + 0.008, "metal_chrome")
    # four coil elements over steel drip pans: two large, two small
    burners = []
    for da, dd, r in ((0.19, 0.20, 0.085), (0.56, 0.20, 0.105), (0.19, 0.47, 0.105), (0.56, 0.47, 0.085)):
        c = EAST.P(a0 + da, dd + 0.02, GF + 0.912)
        burners.append((c, r))
        shapes.lathe(mb, c.x, c.y, [(r + 0.022, c.z), (r + 0.026, c.z + 0.003), (r + 0.012, c.z + 0.002),
                                    (r * 0.3, c.z - 0.0005)], "metal_steel", 14, cap_first=False, cap_last=True)
        for k in range(3):
            ro = r * (1.0 - 0.3 * k)
            shapes.annulus(mb, c.x, c.y, c.z + 0.003, ro, ro - r * 0.17, 0.007, "metal_dark", n=14)
    obj = shapes.soften(mb.build("kitchen_stove", "furniture"))

    cl.pot(small, burners[1][0].x, burners[1][0].y, GF + 0.922, radius=0.095, height=0.12)
    cl.pan(small, burners[2][0].x, burners[2][0].y, GF + 0.922, radius=0.115, handle_deg=160, food="food_brown")

    hood = MeshBuilder()
    EAST.box(hood, a0, a1, 0.0, 0.50, GF + 1.56, GF + 1.60, "enamel_almond")
    hood.prism([(0.0, 0.0), (0.50, 0.0), (0.50, 0.035), (0.30, 0.13), (0.0, 0.13)],
               EAST.P(a0, 0.0, GF + 1.60), EAST.normal, (0, 0, 1), EAST.along, a1 - a0, "enamel_almond")
    EAST.box(hood, a0 + 0.06, a1 - 0.06, 0.06, 0.44, GF + 1.556, GF + 1.56, "metal_dark")          # the grease filter
    EAST.box(hood, a0 + 0.30, a0 + 0.44, 0.40, 0.47, GF + 1.552, GF + 1.556, "bulb_on")
    hood.build("kitchen_hood", "fixtures", recalc=True)
    lamp = EAST.P(a0 + 0.37, 0.43, GF + 1.52)
    dr.lightpoint("hood", tuple(lamp), "warm", 12.0, haze=False)
    return obj


def fridge(small):
    """A top-freezer refrigerator in almond enamel, its lower door left open
    with the light still on. The door is its own hinged object."""
    y0, y1 = 4.60, 5.32
    xb, xf = 7.30 - 0.03, 7.30 - 0.66                 # back and front of the cabinet
    top, split = GF + 1.70, GF + 1.20
    wall = 0.045
    mb = MeshBuilder()
    mb.box((xf, y0, GF + 0.02), (xb, y1, top), "enamel_almond", skip="-x")
    mb.box((xf + 0.04, y0 + 0.03, GF), (xb, y1 - 0.03, GF + 0.02), "plastic_black")
    # the front edge round the food compartment, and the divider under the freezer
    for lo, hi in (((xf, y0, GF + 0.02), (xf, y0 + wall, split)), ((xf, y1 - wall, GF + 0.02), (xf, y1, split)),
                   ((xf, y0 + wall, GF + 0.02), (xf, y1 - wall, GF + 0.10)),
                   ((xf, y0, split), (xf, y1, split + 0.03))):
        cy, cz = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
        mb.rect((xf, cy, cz), (0, (hi[1] - lo[1]) / 2, 0), (0, 0, (hi[2] - lo[2]) / 2), (-1, 0, 0), "enamel_almond")
    shapes.cavity(mb, (xf, y0 + wall, GF + 0.10), (xb - 0.04, y1 - wall, split), "plastic_white", open_side="-x")
    for z in (GF + 0.42, GF + 0.70, GF + 0.95):                                                   # shelves
        mb.box((xf + 0.11, y0 + wall, z), (xb - 0.05, y1 - wall, z + 0.008), "metal_white")
    mb.box((xf + 0.11, y0 + wall + 0.01, GF + 0.11), (xb - 0.06, y1 - wall - 0.01, GF + 0.30), "plastic_cream",
           skip="+z")                                                                           # the crisper drawer
    mb.box((xb - 0.10, (y0 + y1) / 2 - 0.04, split - 0.07), (xb - 0.05, (y0 + y1) / 2 + 0.04, split - 0.02), "bulb_on")
    # freezer door, shut
    mb.box((xf - 0.06, y0, split + 0.035), (xf, y1, top), "enamel_almond")
    mb.box((xf - 0.085, y1 - 0.07, split + 0.08), (xf - 0.06, y1 - 0.045, split + 0.30), "plastic_cream")
    shapes.printed(mb, [(xf - 0.0605, y0 + 0.31, top - 0.11), (xf - 0.0605, y0 + 0.07, top - 0.11),
                        (xf - 0.0605, y0 + 0.07, top - 0.05), (xf - 0.0605, y0 + 0.31, top - 0.05)], "fridge_badge")
    obj = mb.build("kitchen_fridge", "furniture")
    dr.lightpoint("fridge", (xb - 0.14, (y0 + y1) / 2, split - 0.10), "warm", 12.0, haze=False)

    # the lower door: hinged on the south side, so it opens towards the room
    door = MeshBuilder()
    hinge = Vector((xf, y0, GF))
    width, thick, z0, z1 = y1 - y0, 0.06, GF + 0.06, split + 0.02
    door.box((xf - thick, y0, z0), (xf, y1, z1), "enamel_almond")
    door.box((xf - thick - 0.025, y1 - 0.07, z1 - 0.34), (xf - thick, y1 - 0.045, z1 - 0.06), "plastic_cream")
    # inside: a liner and two door racks with bottles in them
    door.box((xf, y0 + 0.03, z0 + 0.03), (xf + 0.012, y1 - 0.03, z1 - 0.03), "plastic_white")
    for z in (z0 + 0.16, z0 + 0.62):
        door.box((xf + 0.012, y0 + 0.05, z), (xf + 0.085, y1 - 0.05, z + 0.012), "plastic_white")
        door.box((xf + 0.078, y0 + 0.05, z), (xf + 0.085, y1 - 0.05, z + 0.075), "plastic_white")
    cl.bottle(door, xf + 0.045, y0 + 0.16, z0 + 0.172, "glass_bottle", height=0.22)
    cl.bottle(door, xf + 0.045, y0 + 0.50, z0 + 0.172, "glass_bottle", height=0.26, radius=0.034)
    cl.tin(door, xf + 0.045, y0 + 0.30, z0 + 0.632, "soda", radius=0.032, height=0.12)
    # outside: what a family sticks to a fridge
    out = xf - thick - 0.0015
    for region, cy, cz, w, tilt in (("drawing", y0 + 0.24, GF + 0.92, 0.19, 4.0), ("note", y0 + 0.50, GF + 1.00, 0.11, -6.0),
                                    ("coupon", y0 + 0.47, GF + 0.80, 0.12, 3.0), ("polaroid", y0 + 0.20, GF + 0.62, 0.085, -8.0),
                                    ("menu", y0 + 0.50, GF + 0.50, 0.13, 2.0)):
        h = w / labels.aspect(region)
        t = math.tan(math.radians(tilt)) * w / 2
        # seen from the west, the picture's left is to the north
        shapes.printed(door, [(out, cy + w / 2, cz - h / 2 + t), (out, cy - w / 2, cz - h / 2 - t),
                              (out, cy - w / 2, cz + h / 2 - t), (out, cy + w / 2, cz + h / 2 + t)], region)
        door.cylinder((out, cy, cz + h / 2 - 0.012), (-0.004, 0, 0), 0.011,
                      random.Random(int(cy * 100)).choice(("plastic_red", "plastic_blue", "plastic_green")), segments=8)
    leaf = door.build("fridge_door", "doors", origin=hinge)
    leaf.rotation_euler = (0, 0, math.radians(58.0))
    leaf["opens_degrees"] = 115.0

    # what is left inside
    cl.carton(small, xf + 0.20, y0 + 0.20, GF + 0.958, yaw=20)
    cl.tin(small, xf + 0.30, y0 + 0.44, GF + 0.958, "beer", radius=0.032, height=0.12)
    cl.tin(small, xf + 0.18, y0 + 0.52, GF + 0.958, "beer", radius=0.032, height=0.12, turn=80)
    cl.plate(small, xf + 0.26, y0 + 0.36, GF + 0.708)
    small.face(shapes.ring(xf + 0.26, y0 + 0.36, GF + 0.722, 0.07, 0.06, 9), "food_brown")
    cl.takeout(small, xf + 0.22, y0 + 0.20, GF + 0.428, yaw=70, open_top=False)
    cl.bottle(small, xf + 0.30, y0 + 0.50, GF + 0.428, "glass_bottle", height=0.20)
    return obj


def microwave(small):
    c = EAST.P(5.645, 0.30, GF + TOP)
    shapes.obox(small, tuple(c), (0.50, 0.36, 0.29), EAST.facing + 90, "c_grey", prints={"front": "microwave"})


# --- Table and chairs ---------------------------------------------------------

def table(name, cx, cy, yaw=0.0, length=1.22, width=0.80, height=0.75):
    """A laminate-topped table with a steel edge band and chrome legs."""
    mb = MeshBuilder()
    shapes.obox(mb, (cx, cy, GF + height - 0.032), (length, width, 0.032), yaw, "metal_steel")
    shapes.obox(mb, (cx, cy, GF + height - 0.004), (length - 0.012, width - 0.012, 0.005), yaw, "counter")
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = sx * (length / 2 - 0.10), sy * (width / 2 - 0.09)
            head = Vector((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, GF + height - 0.032))
            foot = Vector((cx + (lx + sx * 0.05) * ca - (ly + sy * 0.04) * sa,
                           cy + (lx + sx * 0.05) * sa + (ly + sy * 0.04) * ca, GF))
            mb.cylinder(foot, head - foot, 0.016, "metal_chrome", segments=8)
            mb.cylinder(foot, (0, 0, 0.012), 0.019, "plastic_black", segments=8)
    return mb.build(name, "furniture")


def chair(name, cx, cy, yaw, fallen=False):
    """A chrome-tube kitchen chair with a padded vinyl seat and back."""
    mb = MeshBuilder()
    seat_z = 0.45

    def R(x, y, z):
        ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        if fallen:                                    # on its back
            y, z = -z + 0.02, y + 0.24
        return Vector((cx + x * ca - y * sa, cy + x * sa + y * ca, GF + z))

    def pad(x0, x1, y0, y1, z0, z1, n=10, power=4.0):
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        rings = []
        for z, shrink in ((z0, 0.94), (z0 + (z1 - z0) * 0.3, 1.0), (z0 + (z1 - z0) * 0.8, 1.0), (z1, 0.90)):
            loop = shapes.ring(mx, my, z, (x1 - x0) / 2 * shrink, (y1 - y0) / 2 * shrink, 16, power)
            rings.append([R(p.x, p.y, p.z) for p in loop])
        shapes.loft(mb, rings, "vinyl", cap_first=True, cap_last=True)

    pad(-0.21, 0.21, -0.20, 0.21, seat_z - 0.045, seat_z)
    # the back pad is a slab standing on edge: build it lying down, then stand it up
    back = []
    for d, shrink in ((0.0, 0.92), (0.012, 1.0), (0.04, 1.0), (0.05, 0.90)):
        loop = shapes.ring(0.0, 0.0, 0.0, 0.20 * shrink, 0.13 * shrink, 16, 4.0)
        back.append([R(p.x, 0.205 + d + (p.y + 0.13) * 0.10, seat_z + 0.30 + p.y + 0.13) for p in loop])
    shapes.loft(mb, back, "vinyl", cap_first=True, cap_last=True)
    for sx in (-1, 1):
        shapes.tube(mb, [R(sx * 0.19, -0.19, 0.0), R(sx * 0.18, -0.17, seat_z - 0.05), R(sx * 0.18, 0.17, seat_z - 0.05),
                         R(sx * 0.20, 0.21, 0.0)], 0.011, "metal_chrome", segments=6)
        shapes.tube(mb, [R(sx * 0.18, 0.17, seat_z - 0.05), R(sx * 0.18, 0.215, seat_z + 0.30),
                         R(sx * 0.18, 0.25, seat_z + 0.58)], 0.011, "metal_chrome", segments=6)
    return shapes.soften(mb.build(name, "furniture", recalc=True))


def dining(small):
    table("kitchen_table", 4.42, 6.02)
    chair("kitchen_chair_1", 4.40, 5.36, 184.0)
    chair("kitchen_chair_2", 4.52, 6.74, -8.0)
    chair("kitchen_chair_3", 3.50, 6.10, 98.0)
    chair("kitchen_chair_fallen", 5.42, 6.42, 100.0, fallen=True)
    z = GF + 0.752
    cl.cereal(small, 4.20, 6.16, z, "cereal_a", yaw=-18)
    cl.cereal(small, 4.74, 5.86, z, "cereal_b", yaw=62, fallen=True)
    cl.bowl(small, 4.30, 5.84, z, fill="paper")
    small.box((4.39, 5.80, z), (4.405, 5.93, z + 0.004), "metal_steel")                           # a spoon
    dr.mug(small, 4.56, 6.22, z)
    dr.mug(small, 3.98, 5.92, z)
    cl.takeout(small, 4.70, 6.20, z, yaw=25)
    cl.takeout(small, 4.84, 6.10, z, yaw=-50, tipped=True)
    cl.pizza_box(small, 4.02, 6.20, z, yaw=14)
    shapes.sheet(small, (4.46, 5.74, z), 0.30, "newspaper", yaw=-9, lift=0.002)
    shapes.sheet(small, (4.36, 5.76, z), 0.13, "envelope_b", yaw=30, lift=0.006)
    cl.ashtray(small, 4.86, 5.74, z, seed=3)
    cl.cigarettes(small, 4.98, 5.86, z, yaw=40)
    cl.tin(small, 4.62, 5.92, z, "soda", radius=0.032, height=0.12, turn=200)


# --- The rest of the room -------------------------------------------------------

def wall_things(small):
    fx = MeshBuilder()
    # a wall clock, stopped
    centre = DIVIDER_N.P(5.70, 0.0, GF + 2.02)
    fx.cylinder(centre, DIVIDER_N.normal * 0.035, 0.155, "plastic_black", segments=20, caps="none")
    shapes.disc(fx, centre + DIVIDER_N.normal * 0.026, DIVIDER_N.normal, 0.146, "clock")
    for length, angle, w in ((0.085, 62.0, 0.006), (0.12, -48.0, 0.004)):                           # the hands
        tip = centre + DIVIDER_N.normal * 0.03
        across = DIVIDER_N.normal.cross(Vector((0, 0, 1)))
        d = across * math.cos(math.radians(angle)) + Vector((0, 0, 1)) * math.sin(math.radians(angle))
        fx.cylinder(tip, d * length, w, "plastic_black", segments=4)
    shapes.poster(fx, DIVIDER_N, 4.72, GF + 1.52, 0.30, "calendar", tilt=-1.5)
    shapes.poster(fx, DIVIDER_N, 5.25, GF + 1.38, 0.20, "letter", tilt=3.0)

    # a wall telephone by the door to the hall, cord hanging
    ROOM_WEST.box(fx, 7.14, 7.30, 0.0, 0.045, GF + 1.30, GF + 1.54, "plastic_cream")
    ROOM_WEST.box(fx, 7.165, 7.275, 0.045, 0.085, GF + 1.33, GF + 1.52, "plastic_cream")           # the handset
    cord = [ROOM_WEST.P(7.22, 0.05, GF + 1.31)]
    for k in range(1, 30):
        t = k / 29
        cord.append(ROOM_WEST.P(7.22 + 0.012 * math.sin(k * 2.1), 0.06 + 0.02 * math.sin(t * math.pi)
                                + 0.012 * math.cos(k * 2.1), GF + 1.31 - 0.62 * math.sin(t * math.pi * 0.5)))
    shapes.tube(fx, cord, 0.003, "plastic_cream", segments=4)

    dr.switch(fx, ROOM_WEST, 7.08, GF + 1.22)
    dr.socket(fx, NORTH, 6.60, GF + 1.12)
    dr.socket(fx, EAST, 5.50, GF + 1.12)
    dr.socket(fx, EAST, 4.72, GF + 0.32)
    dr.cable(fx, [(7.02, 5.44, GF + 1.02), (7.20, 5.48, GF + 1.06), (7.288, 5.50, GF + 1.12)], radius=0.003)
    # a fluorescent strip light on the ceiling, on its way out: it flickers
    fx.box((3.86, 5.95, plan.CEILING - 0.055), (5.06, 6.09, plan.CEILING), "plastic_white")
    fx.build("electrics_kitchen", "fixtures")
    tube = MeshBuilder()
    tube.cylinder((3.90, 6.02, plan.CEILING - 0.07), (1.12, 0, 0), 0.014, "bulb_on", segments=8)
    lamp = tube.build("lamp_kitchen_tube", "lamps")
    lamp.visible_shadow = False
    dr.lightpoint("kitchen", (4.46, 6.02, plan.CEILING - 0.14), "flicker", 26.0, colour=TUBE, haze=False)

    dr.radiator("radiator_kitchen", ROOM_WEST, 7.38, 7.92, GF)
    dr.curtain_pole("pole_kitchen", NORTH, 3.87, 5.99, GF + 2.36)
    dr.curtain("curtain_kitchen_l", NORTH, 3.89, 4.52, GF + 2.35, GF + 1.02, seed=3, key="gingham")
    dr.curtain("curtain_kitchen_r", NORTH, 5.46, 5.97, GF + 2.35, GF + 1.02, seed=4, key="gingham")

    # the bin, overflowing, and what did not make it in
    shapes.lathe(small, 2.86, 7.66, [(0.13, GF), (0.16, GF + 0.46), (0.15, GF + 0.46), (0.12, GF + 0.02)],
                 "plastic_cream", 14, cap_last=True)
    cl.pizza_box(small, 2.96, 7.72, GF + 0.30, yaw=30, lean=62)
    cl.takeout(small, 2.82, 7.60, GF + 0.44, yaw=10, tipped=True)
    cl.tin(small, 3.10, 7.36, GF, "soup", turn=30)
    cl.tin(small, 3.02, 7.28, GF + 0.037, "beer", radius=0.032, height=0.12)
    cl.cereal(small, 6.90, 7.74, GF + TOP, "cereal_c", yaw=-20)
    cl.tin(small, 6.88, 7.30, GF + TOP, "beans")
    cl.tin(small, 6.98, 7.22, GF + TOP, "soup", turn=120)
    dr.mug(small, 6.20, 7.74, GF + TOP)
    dr.mug(small, 3.62, 7.72, GF + TOP)
    cl.plates(small, 3.90, 7.74, GF + TOP, 3)
    cl.takeout(small, 6.94, 6.94, GF + TOP, yaw=-70)
    cl.bottle(small, 3.44, 7.84, GF + TOP, height=0.27)
    cl.bottle(small, 3.54, 7.88, GF + TOP, height=0.24)
    shapes.sheet(small, (3.70, 7.56, GF + TOP), 0.21, "menu", yaw=-70, lift=0.002)
    # a tea towel over the oven rail
    for k, (drop, out) in enumerate(((0.26, 0.012), (0.20, -0.012))):
        a0, a1 = 6.16, 6.44
        d = 0.655 + 0.075 + out
        small.face([EAST.P(a0, d, GF + 0.80 - drop), EAST.P(a1, d, GF + 0.80 - drop), EAST.P(a1, d, GF + 0.812),
                    EAST.P(a0, d, GF + 0.812)][::(1 if k else -1)], "gingham")


def decals():
    d = Decals("decals_kitchen", seed=27)
    d.wall("grease", EAST, 6.33, GF + 1.34, 0.86, 0.50, offset=0.0095)                # on the tiles behind the hob
    d.wall("grease", EAST, 6.33, GF + 2.05, 1.1, 0.9)                                 # and on the wall above the hood
    d.wall("grime_streaks", EAST, 6.33, GF + 2.25, 0.9, 0.8)
    d.wall("mould", NORTH, 3.15, GF + 2.25, 1.1, 0.9, flip=False)
    d.wall("water_stain", NORTH, 6.7, GF + 2.42, 1.0, 0.5)
    d.wall("grime_streaks", NORTH, 3.0, GF + 0.9, 0.6, 1.6)
    d.wall("floor_grime", ROOM_WEST, 7.4, GF + 0.34, 1.1, 0.36)
    d.wall("floor_grime", DIVIDER_N, 5.3, GF + 0.34, 2.2, 0.36)
    d.wall("crack", DIVIDER_N, 6.2, GF + 2.0, 1.0, 1.0)
    d.wall("smudge", ROOM_WEST, 7.08, GF + 1.2, 0.36, 0.42)
    d.wall("smudge", DIVIDER_N, 4.25, GF + 1.15, 0.30, 0.5)
    d.wall("plaster_damage", ROOM_WEST, 5.05, GF + 1.9, 0.5, 0.5)
    # the cabinet fronts: hand marks round the handles, drips, and dirt kicked up from the floor
    north_front = Face("x", plan.DEPTH - CARCASS - DOOR_T, -1)
    east_front = Face("y", plan.WIDTH - CARCASS - DOOR_T, -1)
    for a in (3.75, 4.70, 5.65, 6.35):
        d.wall("smudge", north_front, a, GF + 0.66, 0.34, 0.40)
    d.wall("grime_streaks", north_front, 4.92, GF + 0.50, 0.9, 0.72)                  # under the sink
    d.wall("grime_streaks", north_front, 6.30, GF + 0.50, 0.5, 0.72)
    d.wall("floor_grime", north_front, 4.6, GF + 0.26, 2.4, 0.34)
    d.wall("floor_grime", east_front, 7.05, GF + 0.26, 0.66, 0.34)
    d.wall("smudge", east_front, 5.64, GF + 0.66, 0.34, 0.40)
    d.wall("grime_streaks", Face("y", plan.WIDTH - 0.69, -1), 6.33, GF + 0.52, 0.6, 0.66)   # down the oven door
    d.wall("smudge", Face("y", plan.WIDTH - 0.72 - 0.001, -1), 5.20, GF + 1.42, 0.22, 0.5)  # the freezer handle
    d.wall("rust_stain", Face("y", plan.WIDTH - 0.72 - 0.001, -1), 4.72, GF + 1.50, 0.16, 0.36)
    d.flat("burnt", 7.30 - 0.36, 6.33, GF + 0.9125, 0.60, 0.72)
    d.flat("grease", 7.30 - 0.34, 6.33, GF + 0.9128, 0.66, 0.76)
    d.flat("stain_rings", 4.52, 6.06, GF + 0.7515, 0.9, 0.62, angle_deg=12)
    d.flat("stain_rings", 3.74, 7.70, GF + TOP + 0.0006, 0.6, 0.5, angle_deg=80)
    d.flat("stain_rings", 7.00, 7.10, GF + TOP + 0.0006, 0.5, 0.6, angle_deg=200)
    d.flat("water_stain", 4.95, 7.02, GF, 1.5, 0.9, angle_deg=4)                      # in front of the sink
    d.flat("water_stain", 6.25, 5.05, GF, 1.1, 1.2, angle_deg=40)                     # a leak from the fridge
    d.flat("smudge", 3.0, 6.2, GF, 1.4, 1.8, angle_deg=70)                            # the track in from the hall
    d.flat("grease", 6.05, 6.35, GF, 1.0, 1.1, angle_deg=20)
    d.flat("mould", 2.95, 7.6, plan.CEILING, 1.3, 1.3, up=False, angle_deg=180)
    d.flat("water_stain", 6.3, 7.1, plan.CEILING, 1.7, 1.4, up=False, angle_deg=30)
    d.build()


def build():
    _, small = cabinets()
    sink(small)
    stove(small)
    fridge(small)
    microwave(small)
    dining(small)
    wall_things(small)
    obj = shapes.soften(small.build("clutter_kitchen", "clutter"))
    obj.visible_shadow = True
    decals()
