"""Floor plan of the house: every dimension in one place.

Pure data, no bpy. The layout drawing, the blockout and the final structure
are all generated from this file, so a change here moves everything.

Units are metres. Axes: +X east, +Y north, +Z up. The origin is the inside
south-west corner of the ground floor at finished floor level. The street is
to the south (-Y); the front door is in the south wall.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Vertical dimensions ----------------------------------------------------
CEILING = 2.70                  # finished floor to ceiling, both storeys
RISERS = 18
RISE = 0.17
TREAD = 0.28
FLOOR_TO_FLOOR = RISERS * RISE  # 3.06
SLAB = FLOOR_TO_FLOOR - CEILING  # 0.36 of joists and boards between storeys
FFL = (0.0, FLOOR_TO_FLOOR)     # finished floor level of each storey
ROOF_Z = FLOOR_TO_FLOOR + CEILING  # 5.76, underside of the top ceiling

DOOR_H = 2.10
DOOR_W = 0.90
FRONT_DOOR_W = 0.95

# --- Horizontal dimensions --------------------------------------------------
EXT_T = 0.30                    # exterior wall thickness
INT_T = 0.14                    # partition thickness
WIDTH = 7.30                    # interior, east-west
DEPTH = 8.00                    # interior, north-south

HALL_W = 2.40                   # hallway, including the stair
PART_X0 = HALL_W                # hall / rooms partition
PART_X1 = PART_X0 + INT_T       # 2.54
DIVIDER_Y0 = 4.40               # wall between the front and back rooms, on both floors:
DIVIDER_Y1 = DIVIDER_Y0 + INT_T  # 4.54   living | kitchen below, bedroom | bathroom above

# --- Stair: one straight flight along the west wall, climbing north ----------
STAIR_W = 1.05
STAIR_X0, STAIR_X1 = 0.0, STAIR_W
STAIR_Y0 = 2.00                             # face of the first riser
STAIR_Y1 = STAIR_Y0 + (RISERS - 1) * TREAD   # 6.76, face of the top riser
VOID_X1 = 1.15                              # stair + balustrade zone
# The first-floor opening starts where headroom under the floor above would
# otherwise drop below 2.0 m.
VOID_Y0 = 3.00
VOID_Y1 = STAIR_Y1


@dataclass(frozen=True)
class Opening:
    """A hole in a wall. `start` runs along the wall's long axis in world
    coordinates; `sill` and `head` are absolute heights."""

    name: str
    kind: str                 # "door", "window", "opening" (cased, no leaf) or "fireplace"
    start: float
    width: float
    sill: float
    head: float
    hinge: str = ""           # doors: "start" or "end" of the opening
    swing: str = ""           # doors: "+" or "-" side of the wall the leaf opens to
    on_plan: bool = True      # False for high-level glazing a plan would not show
    note: str = ""

    @property
    def end(self) -> float:
        return self.start + self.width


@dataclass(frozen=True)
class Wall:
    name: str
    x0: float
    y0: float
    x1: float
    y1: float
    z0: float
    z1: float
    openings: tuple[Opening, ...] = ()

    @property
    def axis(self) -> str:
        """Direction the wall runs in."""
        return "x" if (self.x1 - self.x0) >= (self.y1 - self.y0) else "y"

    def on_storey(self, storey: int) -> bool:
        lo, hi = FFL[storey] + 0.3, FFL[storey] + CEILING - 0.3
        return self.z0 < hi and self.z1 > lo


@dataclass(frozen=True)
class Room:
    key: str
    label: str
    storey: int
    rects: tuple[tuple[float, float, float, float], ...]   # x0, y0, x1, y1
    label_at: tuple[float, float]

    @property
    def area(self) -> float:
        return sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in self.rects)


def _z(storey: int, height: float) -> float:
    return FFL[storey] + height


# --- Walls ------------------------------------------------------------------
# Exterior walls run the full height of the house and carry the openings of
# both storeys. The south and north walls own the corners.
WALLS: tuple[Wall, ...] = (
    Wall("wall_ext_south", -EXT_T, -EXT_T, WIDTH + EXT_T, 0.0, 0.0, ROOF_Z, (
        Opening("door_front", "door", 1.30, FRONT_DOOR_W, 0.0, DOOR_H,
                hinge="end", swing="+", note="hinged, separate object"),
        Opening("fanlight_front", "window", 1.30, FRONT_DOOR_W, 2.20, 2.50, on_plan=False),
        Opening("win_living_front", "window", 3.72, 2.40, 0.75, 2.25),
        Opening("win_landing_front", "window", 1.275, 1.00, _z(1, 0.90), _z(1, 2.25)),
        Opening("win_bedroom_front", "window", 3.72, 2.40, _z(1, 0.85), _z(1, 2.25)),
    )),
    Wall("wall_ext_north", -EXT_T, DEPTH, WIDTH + EXT_T, DEPTH + EXT_T, 0.0, ROOF_Z, (
        Opening("door_back", "door", 1.35, DOOR_W, 0.0, DOOR_H,
                hinge="end", swing="-", note="static, half glazed"),
        Opening("win_dining_rear", "window", 3.92, 2.00, 0.90, 2.25),
        Opening("win_boxroom_rear", "window", 4.12, 1.60, _z(1, 0.90), _z(1, 2.25)),
    )),
    Wall("wall_ext_west", -EXT_T, 0.0, 0.0, DEPTH, 0.0, ROOF_Z, (
        # Tall stair window: its sill sits 0.9 m above the tread below it.
        Opening("win_stair", "window", 4.30, 0.90, 2.90, 4.50),
    )),
    Wall("wall_ext_east", WIDTH, 0.0, WIDTH + EXT_T, DEPTH, 0.0, ROOF_Z),

    Wall("wall_gf_partition", PART_X0, 0.0, PART_X1, DEPTH, 0.0, CEILING, (
        Opening("door_living", "door", 1.15, DOOR_W, 0.0, DOOR_H, hinge="start", swing="+"),
        Opening("opening_hall_kitchen", "opening", 5.50, 1.50, 0.0, 2.20),
    )),
    Wall("wall_gf_divider", PART_X1, DIVIDER_Y0, WIDTH, DIVIDER_Y1, 0.0, CEILING, (
        # Living room to kitchen: a cased opening, no door.
        Opening("opening_living_kitchen", "opening", 3.00, 1.10, 0.0, DOOR_H),
    )),
    Wall("chimney_breast_gf", 6.95, 1.50, WIDTH, 3.10, 0.0, CEILING, (
        Opening("fireplace", "fireplace", 2.02, 0.56, 0.0, 0.72, on_plan=False),
    )),

    Wall("wall_ff_partition", PART_X0, 0.0, PART_X1, DEPTH, _z(1, 0.0), ROOF_Z, (
        Opening("door_bedroom", "door", 3.25, DOOR_W, _z(1, 0.0), _z(1, DOOR_H),
                hinge="end", swing="+"),
        Opening("door_bathroom", "door", 4.80, DOOR_W, _z(1, 0.0), _z(1, DOOR_H),
                hinge="start", swing="+"),
    )),
    Wall("wall_ff_divider", PART_X1, DIVIDER_Y0, WIDTH, DIVIDER_Y1, _z(1, 0.0), ROOF_Z),
    Wall("chimney_breast_ff", 6.95, 1.50, WIDTH, 3.10, _z(1, 0.0), ROOF_Z),
)

# --- Rooms ------------------------------------------------------------------
ROOMS: tuple[Room, ...] = (
    Room("hall", "HALLWAY", 0, ((0.0, 0.0, HALL_W, DEPTH),), (1.22, 1.52)),
    Room("living", "LIVING ROOM", 0, ((PART_X1, 0.0, WIDTH, DIVIDER_Y0),), (4.92, 3.95)),
    Room("kitchen", "KITCHEN", 0, ((PART_X1, DIVIDER_Y1, WIDTH, DEPTH),), (4.60, 5.25)),
    Room("landing", "LANDING", 1, (
        (0.0, 0.0, HALL_W, VOID_Y0),              # front landing
        (VOID_X1, VOID_Y0, HALL_W, DEPTH),        # corridor past the stairwell
        (0.0, VOID_Y1, VOID_X1, DEPTH),           # head of the stair
    ), (1.20, 1.90)),
    Room("bedroom", "BEDROOM", 1, ((PART_X1, 0.0, WIDTH, DIVIDER_Y0),), (4.92, 1.55)),
    Room("bathroom", "BATHROOM", 1, ((PART_X1, DIVIDER_Y1, WIDTH, DEPTH),), (4.75, 5.95)),
)

# The hole in the first floor over the stair.
STAIR_VOID = (0.0, VOID_Y0, VOID_X1, VOID_Y1)

# Balustrades as plan polylines per storey.
BALUSTRADES: tuple[tuple[int, tuple[tuple[float, float], ...]], ...] = (
    (0, ((1.10, STAIR_Y0), (1.10, 3.60))),                       # open foot of the stair
    (1, ((0.0, VOID_Y0), (1.10, VOID_Y0), (1.10, VOID_Y1))),      # around the stairwell
)

# Cupboard under the stair: enclosed from where there is 0.95 m of height.
UNDERSTAIR = (0.0, 3.60, VOID_X1, STAIR_Y1)

# --- Dressing intent (placement guides, not final sizes) ---------------------
# storey, label, x0, y0, x1, y1
FURNITURE: tuple[tuple[int, str, float, float, float, float], ...] = (
    (0, "coats / shoes", 0.00, 0.25, 0.35, 1.70),
    (0, "console", 2.08, 2.45, 2.40, 3.45),
    (0, "sofa", 3.90, 1.25, 4.80, 3.35),
    (0, "table", 5.35, 1.85, 5.95, 2.75),
    (0, "fire / TV", 6.72, 1.75, 6.95, 2.85),
    (0, "armchair", 5.30, 0.25, 6.10, 1.05),
    (0, "books", 6.95, 3.14, 7.30, 4.36),
    (0, "sideboard", 4.75, 3.95, 6.35, 4.40),
    (0, "counter / sink", 3.30, 7.40, 7.30, 8.00),
    (0, "stove", 6.66, 5.95, 7.30, 6.71),
    (0, "fridge", 6.58, 4.60, 7.30, 5.32),
    (0, "table", 3.85, 5.55, 5.05, 6.45),
    (1, "chair", 0.15, 0.25, 0.80, 0.90),
    (1, "wardrobe", 2.54, 0.25, 3.14, 2.15),
    (1, "bed", 4.25, 2.35, 5.85, 4.40),
    (1, "drawers", 6.85, 0.20, 7.30, 1.40),
    (1, "bath", 5.55, 7.22, 7.25, 8.00),
    (1, "wc", 3.05, 7.28, 3.47, 8.00),
    (1, "basin", 5.55, 4.54, 6.15, 5.00),
    (1, "shelves", 2.54, 6.60, 2.84, 7.60),
)

# storey, kind, x, y, label. Kinds: "warm" practical, "flicker", "broken".
LIGHTS: tuple[tuple[int, str, float, float, str], ...] = (
    (0, "warm", 2.24, 2.70, "table lamp"),
    (0, "flicker", 1.78, 5.30, "pendant (flicker-ready)"),
    (0, "broken", 2.85, 2.55, "broken floor lamp"),
    (0, "warm", 5.90, 4.20, "lamp"),
    (0, "warm", 6.80, 4.96, "fridge, left open"),
    (1, "warm", 6.05, 4.05, "bedside lamp"),
    (1, "warm", 5.85, 4.70, "mirror light"),
)

# Windows the moon shines through: storey, x, y of the window centre, and the
# direction the light travels in plan.
MOONLIGHT: tuple[tuple[int, float, float, float, float], ...] = (
    (0, 4.92, 0.0, 0.16, 1.0),
    (1, 4.92, 0.0, 0.16, 1.0),
    (1, 1.775, 0.0, 0.16, 1.0),
    (1, 0.0, 4.75, 1.0, 0.35),
)


def has_floor(x: float, y: float, storey: int) -> bool:
    """True where someone could stand: in a room, not on the stair, not in the stairwell."""
    if storey == 0 and STAIR_X0 <= x <= VOID_X1 and STAIR_Y0 <= y <= STAIR_Y1:
        return False
    return any(r.storey == storey and any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in r.rects)
               for r in ROOMS)


def has_ceiling(x: float, y: float, storey: int) -> bool:
    if not (0.0 <= x <= WIDTH and 0.0 <= y <= DEPTH):
        return False
    vx0, vy0, vx1, vy1 = STAIR_VOID
    return storey == 1 or not (vx0 <= x <= vx1 and vy0 <= y <= vy1)


def solid_spans(wall: Wall, storey: int | None = None) -> list[tuple[float, float]]:
    """Stretches of a wall with no opening, along its long axis. With a
    storey, only the openings a plan of that storey shows are cut out."""
    lo, hi = (wall.x0, wall.x1) if wall.axis == "x" else (wall.y0, wall.y1)
    cuts = sorted((o.start, o.end) for o in openings_on(wall, storey))
    spans, cursor = [], lo
    for start, end in cuts:
        if start > cursor:
            spans.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < hi:
        spans.append((cursor, hi))
    return spans


def openings_on(wall: Wall, storey: int | None = None) -> list[Opening]:
    if storey is None:
        return list(wall.openings)
    lo, hi = FFL[storey] + 0.3, FFL[storey] + CEILING - 0.3
    return [o for o in wall.openings if o.on_plan and o.sill < hi and o.head > lo]


def check() -> list[str]:
    """Sanity checks on the numbers. Returns a list of problems, empty if fine."""
    problems = []
    if abs(RISERS * RISE - FLOOR_TO_FLOOR) > 1e-6:
        problems.append("risers do not add up to the floor-to-floor height")
    for wall in WALLS:
        lo, hi = (wall.x0, wall.x1) if wall.axis == "x" else (wall.y0, wall.y1)
        for opening in wall.openings:
            if opening.start < lo + 0.05 or opening.end > hi - 0.05:
                problems.append(f"{opening.name} runs off the end of {wall.name}")
            if opening.sill < wall.z0 - 1e-6 or opening.head > wall.z1 - 0.05:
                problems.append(f"{opening.name} is outside the height of {wall.name}")
        for a in wall.openings:
            for b in wall.openings:
                if a.name < b.name and a.start < b.end and b.start < a.end \
                        and a.sill < b.head and b.sill < a.head:
                    problems.append(f"{a.name} overlaps {b.name}")
    # Headroom along the stair: clear height from each tread to the floor above.
    for i in range(1, RISERS):
        y = STAIR_Y0 + (i - 1) * TREAD            # front edge of tread i
        tread_z = i * RISE
        under_floor = not (VOID_Y0 <= y + TREAD / 2 <= VOID_Y1)
        if under_floor and (CEILING - tread_z) < 2.0:
            problems.append(f"headroom over tread {i} is {CEILING - tread_z:.2f} m")
    return problems
