"""Town plan for Halden Ridge: every dimension of the town in one place.

Pure data, no bpy. The layout drawing (layout.py), the Blender build
(build.py) and the Godot town script all read this file, so a change here
moves everything.

Axes and units are the house's (projects/01-house-interior/plan.py): metres,
+X east, +Y north, +Z up, origin at the inside south-west corner of the
player's house at ground-floor level. The street in front of the house runs
east-west to the south of it.

The house is never edited. Its own exterior pieces listed in HOUSE_HIDE are
removed by name in the town scene and rebuilt here at the same heights, so
the porch steps still land on the yard and the sidewalk and road line up:

    yard (lawns)   z = -0.45     GROUND
    sidewalks      z = -0.40     GROUND + 0.05
    road surface   z = -0.53     GROUND - 0.08   (13 cm curb face)
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Levels ------------------------------------------------------------------
GROUND = -0.45
SIDEWALK_Z = GROUND + 0.05
ROAD_Z = GROUND - 0.08
CURB_W = 0.15                   # top width of the curb stone
SIDEWALK_W = 1.6

# The player's house: outside faces of its walls and its porch (from the house plan).
HOUSE_BOX = (-0.30, -0.30, 7.60, 8.30)          # x0, y0, x1, y1
HOUSE_PORCH = (0.10, -2.86, 3.90, -0.30)          # porch, steps and roof overhang
HOUSE_DOOR_X = 1.775                              # centre of the front door
HOUSE_FRONT_PATH = (HOUSE_DOOR_X - 0.7, -8.6, HOUSE_DOOR_X + 0.7, -2.86)

# The house's own exterior objects that the town replaces. Removed by name in
# Godot (scripts/town.gd) and never touched in the house files.
HOUSE_HIDE = (
    "yard_ground", "yard_paths", "street_road", "fence_picket",
    "mailbox", "telephone_pole", "street_sodium",
)

# --- Extent ------------------------------------------------------------------
# Everything the player can reach lies inside WALK; the invisible collision
# walls stand on its edge. BUILD is a little bigger so the edges are dressed.
WALK = (-31.0, -57.0, 39.0, 18.5)               # x0, y0, x1, y1
BUILD = (-36.0, -62.0, 44.0, 22.0)


# --- Streets -----------------------------------------------------------------
@dataclass(frozen=True)
class Street:
    key: str
    name: str
    axis: str                  # "x": runs east-west; "y": runs north-south
    centre: float              # y of the centre line for "x", x for "y"
    start: float               # along the axis
    end: float
    road_w: float              # kerb to kerb
    sidewalks: tuple[str, ...]  # which sides have a sidewalk: "n", "s", "e", "w"
    limit_mph: int = 25

    @property
    def road(self) -> tuple[float, float, float, float]:
        h = self.road_w / 2
        if self.axis == "x":
            return (self.start, self.centre - h, self.end, self.centre + h)
        return (self.centre - h, self.start, self.centre + h, self.end)


# Ashgrove Street: the existing street in front of the house. Its road and its
# north sidewalk keep the house's exact positions (road y -18.1..-10.2,
# sidewalk y -10.2..-8.6).
ASHGROVE = Street("ashgrove", "Ashgrove Street", "x", -14.15, BUILD[0], BUILD[2], 7.9, ("n", "s"))
# Mill Road: the side street, running south from Ashgrove opposite the
# player's front door, towards the closed mill. The T-junction is in view as
# soon as the front door opens.
MILL = Street("mill", "Mill Road", "y", 3.5, BUILD[1], ASHGROVE.road[1], 7.0, ("w", "e"))
STREETS = (ASHGROVE, MILL)

JUNCTION = (MILL.road[0], ASHGROVE.road[1], MILL.road[2], ASHGROVE.road[3])
CORNER_RADIUS = 3.0             # kerb radius where Mill Road meets Ashgrove

# Sidewalk strips, x0, y0, x1, y1 (built at SIDEWALK_Z, with a curb on the road side).
SIDEWALKS = (
    ("ashgrove_n", (BUILD[0], ASHGROVE.road[3], BUILD[2], ASHGROVE.road[3] + SIDEWALK_W)),
    ("ashgrove_sw", (BUILD[0], ASHGROVE.road[1] - SIDEWALK_W, MILL.road[0], ASHGROVE.road[1])),
    ("ashgrove_se", (MILL.road[2], ASHGROVE.road[1] - SIDEWALK_W, BUILD[2], ASHGROVE.road[1])),
    ("mill_w", (MILL.road[0] - SIDEWALK_W, BUILD[1], MILL.road[0], ASHGROVE.road[1] - SIDEWALK_W)),
    ("mill_e", (MILL.road[2], BUILD[1], MILL.road[2] + SIDEWALK_W, ASHGROVE.road[1] - SIDEWALK_W)),
)


# --- Lots and houses ---------------------------------------------------------
@dataclass(frozen=True)
class KitHouse:
    """A closed house assembled from the modular kit (kit.py).

    The footprint is the outside of the walls. `facing` is the side the front
    door is on. Window and door positions are offsets along the front, from
    the left end as seen from the street."""

    width: float               # along the front
    depth: float
    facing: str                # "s", "n", "e"
    origin: tuple[float, float]  # world x, y of the front-left outside corner, seen from the street
    roof: str                  # "gable_side", "gable_front", "hip"
    porch: str                 # "full", "entry", "wrap"
    paint: str                 # key into PAINTS
    trim: str = "trim_cream"
    wear: float = 0.5          # 0 kept up .. 1 derelict
    storeys: int = 2
    door_at: float = 1.4       # front door: left edge, from the front-left corner
    windows_gf: tuple[tuple[float, float], ...] = ((3.2, 1.0),)    # (left edge, width)
    windows_ff: tuple[tuple[float, float], ...] = ((1.0, 1.0), (3.2, 1.0))
    boarded: tuple[str, ...] = ()  # e.g. "gf0", "ff1": storey and index of a boarded window
    broken: tuple[str, ...] = ()   # glass broken, no boards
    lit: str = ""                 # the one dimly lit window, e.g. "ff1"
    chimney: float = -1.0         # position along the ridge, 0..1; below 0 for none
    screen_door: bool = True


@dataclass(frozen=True)
class Lot:
    key: str
    address: str
    rect: tuple[float, float, float, float]   # x0, y0, x1, y1
    what: str
    house: KitHouse | None = None
    lawn: str = "overgrown"                   # "kept", "overgrown", "dead"
    fence: str = "picket"                     # front fence: "picket", "chainlink", "none"
    gate_at: float | None = None              # world x (or y) of the gap in the front fence


PAINTS = {
    # Faded, muted exterior paints. Linear albedo, inside the art bible's 4..80 % range.
    "sage": (0.30, 0.34, 0.27),
    "dusty_blue": (0.27, 0.31, 0.35),
    "oxblood": (0.27, 0.13, 0.11),
    "mustard": (0.42, 0.33, 0.16),
    "putty": (0.40, 0.38, 0.33),
    "trim_cream": (0.62, 0.58, 0.48),
    "trim_grey": (0.42, 0.42, 0.40),
}

LOTS = (
    Lot("L1", "14 Ashgrove Street", (-4.5, -8.6, 11.5, 18.0),
        "The player's house. The only building with an inside.",
        lawn="overgrown", fence="picket", gate_at=HOUSE_DOOR_X),
    Lot("L2", "12 Ashgrove Street", (-21.0, -8.6, -4.5, 18.0),
        "Abandoned since the mill closed. Ground floor boarded up, porch sagging.",
        KitHouse(7.6, 9.0, "s", (-16.6, -0.6), "gable_front", "entry", "dusty_blue",
                 wear=0.9, door_at=1.2, windows_gf=((3.6, 1.0), (5.4, 1.0)),
                 windows_ff=((1.0, 1.0), (4.4, 1.2)), boarded=("gf0", "gf1", "ff0"), broken=("ff1",),
                 chimney=0.75),
        lawn="dead", fence="picket", gate_at=-14.9),
    Lot("L3", "16 Ashgrove Street", (11.5, -8.6, 28.0, 18.0),
        "Someone may still live here: one upstairs window glows behind a blind.",
        KitHouse(9.2, 7.8, "s", (15.0, 0.2), "gable_side", "full", "sage",
                 wear=0.45, door_at=3.9, windows_gf=((1.0, 1.4), (6.4, 1.4)),
                 windows_ff=((1.0, 1.0), (4.1, 1.0), (7.0, 1.0)), lit="ff2", chimney=0.18),
        lawn="overgrown", fence="picket", gate_at=19.4),
    Lot("L4", "15 Ashgrove Street", (-20.0, -40.0, -1.6, -19.7),
        "Corner house, hip roof. Closed up; a window broken on the side street.",
        KitHouse(8.4, 7.6, "n", (-6.4, -27.0), "hip", "wrap", "putty",
                 wear=0.7, door_at=3.6, windows_gf=((1.0, 1.2), (6.2, 1.2)),
                 windows_ff=((1.1, 1.0), (6.3, 1.0)), boarded=("gf1",), broken=("ff0",), chimney=0.5),
        lawn="overgrown", fence="none"),
    Lot("L5", "17 Ashgrove Street", (8.6, -40.0, 27.0, -19.7),
        "Corner house, front gable, a faded sale sign. Empty.",
        KitHouse(7.4, 9.4, "n", (20.4, -26.2), "gable_front", "full", "mustard",
                 trim="trim_grey", wear=0.6, door_at=4.8, windows_gf=((1.0, 1.0), (2.6, 1.0)),
                 windows_ff=((1.4, 1.0), (4.8, 1.0)), boarded=("ff0",), chimney=-1.0),
        lawn="dead", fence="chainlink", gate_at=15.1),
    Lot("L6", "3 Mill Road", (-20.0, -58.0, -1.6, -40.0),
        "Faces Mill Road. Oxblood paint, side-gable roof, boarded throughout.",
        KitHouse(8.8, 7.6, "e", (-6.2, -53.4), "gable_side", "entry", "oxblood",
                 wear=0.8, door_at=3.7, windows_gf=((1.0, 1.2), (6.4, 1.2)),
                 windows_ff=((1.0, 1.0), (3.9, 1.0), (6.8, 1.0)), boarded=("gf0", "gf1", "ff1"),
                 chimney=0.82),
        lawn="overgrown", fence="picket", gate_at=-49.2),
    Lot("L7", "4 Mill Road", (8.6, -58.0, 27.0, -40.0),
        "Vacant lot behind a chain-link fence: a dead car on blocks, weeds, leaves.",
        lawn="overgrown", fence="chainlink"),
)

HOUSES = tuple(lot for lot in LOTS if lot.house)


def house_frame(h: KitHouse) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """World origin, 'along the front' unit vector and 'into the house' unit
    vector for a kit house. Local x runs along the front, local y goes back."""
    along = {"s": (1.0, 0.0), "n": (-1.0, 0.0), "e": (0.0, 1.0), "w": (0.0, -1.0)}[h.facing]
    back = {"s": (0.0, 1.0), "n": (0.0, -1.0), "e": (-1.0, 0.0), "w": (1.0, 0.0)}[h.facing]
    return h.origin, along, back


def house_rect(h: KitHouse) -> tuple[float, float, float, float]:
    (ox, oy), (ax, ay), (bx, by) = house_frame(h)
    xs = [ox, ox + ax * h.width, ox + bx * h.depth, ox + ax * h.width + bx * h.depth]
    ys = [oy, oy + ay * h.width, oy + by * h.depth, oy + ay * h.width + by * h.depth]
    return (min(xs), min(ys), max(xs), max(ys))


# --- Street furniture --------------------------------------------------------
@dataclass(frozen=True)
class Pole:
    key: str
    x: float
    y: float
    lamp: str = ""             # "", "on", "broken", "flicker"
    arm: tuple[float, float] = (0.0, -1.0)  # direction the lamp arm reaches, plan
    height: float = 8.4


# Ashgrove poles stand on the north sidewalk on the house pole's line (y -9.5);
# P2 is exactly where the house's own pole was.
POLES = (
    Pole("P1", -24.0, -9.5, "on", (0.0, -1.0)),
    Pole("P2", -4.2, -9.5, "on", (0.0, -1.0)),
    Pole("P3", 15.0, -9.5, "on", (0.0, -1.0)),
    Pole("P4", 33.0, -9.5, "broken", (0.0, -1.0)),
    Pole("P5", -0.8, -20.6, "on", (1.0, 0.0)),        # junction, south-west corner
    Pole("P6", -0.8, -36.0, "flicker", (1.0, 0.0)),
    Pole("P7", -0.8, -51.5, "on", (1.0, 0.0)),
)
# Wires hang between these poles (two or three conductors each, real catenaries).
WIRES = (("P1", "P2"), ("P2", "P3"), ("P3", "P4"), ("P2", "P5"), ("P5", "P6"), ("P6", "P7"))
WIRE_SAG = 0.045               # sag as a fraction of the span (mid-span drop / span)
# Service drops from a pole to a house: pole key, world x, y, z of the house end.
SERVICE_DROPS = (
    ("P2", 0.2, -0.3, 5.4),
    ("P1", -15.0, -0.6, 5.2),
    ("P3", 16.0, 0.2, 5.2),
)

LAMP_HEIGHT = 6.40 - 0.45      # lamp height above the sidewalk, as on the house pole

# Abandoned cars: key, x, y, heading in degrees (0 = east, 90 = north), state.
CARS = (
    ("car_sedan", 18.5, -16.9, 182.0, "abandoned"),   # parked, flat tyres, by L5
    ("car_wagon", 17.0, -49.0, 63.0, "on_blocks"),    # in the vacant lot
    ("car_crashed", 2.4, -54.6, 97.0, "crashed"),     # nose into the Mill Road barriers
)

# Edge blockers. kind, x, y, heading (deg), length.
BLOCKERS = (
    ("barrier", -29.0, -15.3, 90.0, 2.2),
    ("barrier", -29.3, -13.0, 85.0, 2.2),
    ("car_west", -28.0, -10.9, 128.0, 0.0),           # crashed into the corner pole
    ("fence_tall", -30.5, -11.0, 90.0, 59.0),         # across the west end, back lots to Mill Road lots
    ("fallen_tree", 36.0, -13.0, 104.0, 15.0),        # across Ashgrove at the east end
    ("fence_tall", 38.5, -11.0, 90.0, 59.0),
    ("jersey", 0.7, -55.8, 0.0, 2.0),
    ("jersey", 2.9, -55.7, 4.0, 2.0),
    ("jersey", 5.2, -56.0, -3.0, 2.0),
    ("sign_closed", 3.5, -55.0, 0.0, 0.0),
    ("fence_tall", 0.0, -57.4, 0.0, 61.0),           # across the south end of Mill Road
    ("fence_tall", 4.0, 18.4, 0.0, 70.0),             # along the backs of the north lots
    ("fence_tall", -20.4, -38.5, 90.0, 37.0),         # west side of the south lots
    ("fence_tall", 27.4, -38.5, 90.0, 37.0),          # east side of the south lots
)

# Bare trees: x, y, height, seed.
TREES = (
    (-9.0, -5.5, 9.0, 1), (9.5, -5.0, 8.0, 2), (23.0, -4.2, 10.0, 3), (-18.5, 12.0, 11.0, 4),
    (-11.0, -23.0, 9.5, 5), (24.0, -23.5, 8.5, 6), (-16.0, -47.0, 10.0, 7), (20.5, -44.0, 9.0, 8),
    (12.0, -53.0, 7.5, 9), (5.0, 12.0, 9.5, 10),
)

MAILBOXES = ((HOUSE_DOOR_X + 1.25, -8.55, 0), (-12.0, -8.55, 180), (20.6, -8.55, 0),
             (-3.3, -20.2, 0), (14.6, -20.2, 0), (-2.2, -48.0, 90))
TRASH_CANS = ((6.6, -9.1, 0.0, "up"), (7.3, -9.15, 20.0, "up"), (-3.0, -19.3, 75.0, "fallen"),
              (21.8, -9.0, 0.0, "up"), (-1.3, -43.5, 0.0, "up"))
MANHOLES = ((3.5, -14.2), (21.0, -14.0), (-17.0, -14.3), (3.6, -38.0))
HYDRANTS = ((10.0, -19.2),)

# Road damage. Patches: x0, y0, x1, y1. Potholes and puddles: x, y, radius.
PATCHES = ((-7.0, -13.5, -3.0, -11.4), (8.0, -16.9, 12.6, -15.2), (2.0, -27.0, 5.0, -23.5),
           (24.0, -12.8, 27.5, -10.9), (4.2, -46.0, 6.6, -41.0))
POTHOLES = ((-1.6, -12.4, 0.35), (10.8, -11.4, 0.45), (5.6, -21.8, 0.4), (1.6, -31.0, 0.5),
            (-14.0, -16.8, 0.3), (28.5, -15.0, 0.4))
PUDDLES = ((1.2, -11.0, 1.1), (5.9, -17.3, 1.4), (11.0, -11.3, 0.9), (2.2, -24.0, 1.6),
           (-10.5, -17.2, 1.2), (4.9, -33.5, 1.3), (17.8, -13.0, 1.0), (-0.8, -9.8, 0.5),
           (1.9, -7.4, 0.6), (-21.0, -11.0, 1.1))
LEAF_PILES = ((-6.5, -8.0), (0.3, -9.0), (8.8, -10.5), (-2.2, -18.6), (8.0, -19.0), (14.0, -9.0),
              (-12.0, -20.4), (-0.9, -26.0), (7.8, -29.5), (19.0, -43.0), (-8.0, -3.0), (10.0, -7.0))
# Faded road markings: centre lines of each street, and a stop line on Mill Road.
STOP_LINE = (MILL.centre, MILL.road[2] - 0.2, ASHGROVE.road[1] - 1.2)    # x0, x1, y


def check() -> list[str]:
    """Sanity checks on the numbers. Returns a list of problems, empty if fine."""
    problems = []
    if abs(ASHGROVE.road[1] - (-18.1)) > 1e-6 or abs(ASHGROVE.road[3] - (-10.2)) > 1e-6:
        problems.append("Ashgrove no longer lines up with the house's road (y -18.1..-10.2)")
    for lot in LOTS:
        x0, y0, x1, y1 = lot.rect
        if not (x0 < x1 and y0 < y1):
            problems.append(f"{lot.key} has an empty rectangle")
        if lot.house:
            hx0, hy0, hx1, hy1 = house_rect(lot.house)
            if hx0 < x0 + 1.0 or hx1 > x1 - 1.0 or hy0 < y0 + 1.0 or hy1 > y1 - 1.0:
                problems.append(f"{lot.key}: house is closer than 1 m to the lot edge")
    for a in LOTS:
        for b in LOTS:
            if a.key < b.key:
                ax0, ay0, ax1, ay1 = a.rect
                bx0, by0, bx1, by1 = b.rect
                if ax0 < bx1 - 1e-6 and bx0 < ax1 - 1e-6 and ay0 < by1 - 1e-6 and by0 < ay1 - 1e-6:
                    problems.append(f"{a.key} overlaps {b.key}")
    if not (6 <= len(LOTS) <= 8):
        problems.append("the brief asks for 6 to 8 lots")
    keys = {p.key for p in POLES}
    for a, b in WIRES:
        if a not in keys or b not in keys:
            problems.append(f"wire {a}-{b} names a missing pole")
    return problems


if __name__ == "__main__":
    issues = check()
    print("\n".join(issues) if issues else "plan OK")
    for lot in LOTS:
        print(f"{lot.key}  {lot.address:22s}  {lot.what}")
