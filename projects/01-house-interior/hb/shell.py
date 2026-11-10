"""The shell of the house: walls with their openings, floors and ceilings.

Each wall is built as a grid. The wall's two faces are cut wherever an
opening, a storey or a room boundary crosses them; each grid cell is then
either wall or hole. Only faces that can be seen are made: a face is skipped
when it would lie against another wall or inside the floor structure. That
keeps the mesh free of hidden and overlapping polygons.
"""

from __future__ import annotations

from mathutils import Vector

import plan
from . import core
from .core import MeshBuilder

SAMPLE = 0.03       # how far in front of a face its surroundings are sampled
WAINSCOT = 0.95     # height of the wood panelling
WAINSCOT_ROOMS = ("hall", "living", "landing")


def face_material(point, wall, override=None) -> str | None:
    """The material a wall face needs, judged from a point just in front of
    it. None means nobody can ever see the face."""
    x, y, z = point
    if z < 0.0:
        return None
    if core.wall_containing(x, y, z, ignore=wall) is not None:
        return None
    room = core.room_at(x, y, z)
    if room:
        if override:
            return override
        storey = 1 if z >= plan.FFL[1] else 0
        panelled = room in WAINSCOT_ROOMS and z - plan.FFL[storey] < WAINSCOT and z < plan.CEILING + plan.FFL[storey]
        return "panel_wood" if panelled else f"wall_{room}"
    if not core.inside_house(x, y, z):
        return override or "ext_siding"
    return None                       # inside the floor build-up


def _cuts(values, lo, hi):
    out = sorted({round(v, 4) for v in values if lo - 1e-6 <= v <= hi + 1e-6} | {round(lo, 4), round(hi, 4)})
    return [v for i, v in enumerate(out) if i == 0 or v - out[i - 1] > 1e-4]


def build_wall(wall: plan.Wall, coll="structure", name=None, zclip=None, override=None,
               cap_key="section_cap"):
    """One wall as one object. `zclip` (lo, hi) builds only that slice and
    caps a cut top, for cutaway previews. `override` forces one material."""
    along_x = wall.axis == "x"
    a0, a1 = (wall.x0, wall.x1) if along_x else (wall.y0, wall.y1)
    c0, c1 = (wall.y0, wall.y1) if along_x else (wall.x0, wall.x1)
    z0, z1 = wall.z0, wall.z1
    if zclip:
        z0, z1 = max(z0, zclip[0]), min(z1, zclip[1])
        if z1 - z0 < 1e-4:
            return None
    cut_top = z1 < wall.z1 - 1e-4

    ea = Vector((1, 0, 0)) if along_x else Vector((0, 1, 0))
    ec = Vector((0, 1, 0)) if along_x else Vector((1, 0, 0))
    ez = Vector((0, 0, 1))

    def P(a, c, z):
        return Vector((a, c, z)) if along_x else Vector((c, a, z))

    # Where the faces must be divided.
    a_values, z_values = [], [plan.CEILING, plan.FFL[1], WAINSCOT, plan.FFL[1] + WAINSCOT]
    for o in wall.openings:
        a_values += [o.start, o.end]
        z_values += [o.sill, o.head]
    for room in plan.ROOMS:
        for r in room.rects:
            a_values += [r[0], r[2]] if along_x else [r[1], r[3]]
    for other in plan.WALLS:
        if other is not wall:
            a_values += [other.x0, other.x1] if along_x else [other.y0, other.y1]
    v = plan.STAIR_VOID
    a_values += [v[0], v[2]] if along_x else [v[1], v[3]]
    A, Z = _cuts(a_values, a0, a1), _cuts(z_values, z0, z1)

    def is_open(i, j):
        a, z = (A[i] + A[i + 1]) / 2, (Z[j] + Z[j + 1]) / 2
        return any(o.start < a < o.end and o.sill < z < o.head for o in wall.openings)

    mb = MeshBuilder()
    thick, cm = c1 - c0, (c0 + c1) / 2
    na, nz = len(A) - 1, len(Z) - 1

    def reveal_key(a, z):
        """A reveal takes the paint of the room it opens into."""
        for c, n in ((c1, 1), (c0, -1)):
            p = P(a, c + n * SAMPLE, z)
            room = core.room_at(*p)
            if room:
                return override or f"wall_{room}"
        return override or "ext_siding"

    for i in range(na):
        for j in range(nz):
            if is_open(i, j):
                continue
            am, zm = (A[i] + A[i + 1]) / 2, (Z[j] + Z[j + 1]) / 2
            ha, hz = (A[i + 1] - A[i]) / 2, (Z[j + 1] - Z[j]) / 2

            # The two faces of the wall.
            for c, n in ((c0, -1), (c1, 1)):
                key = face_material(P(am, c + n * SAMPLE, zm), wall, override)
                if key:
                    mb.rect(P(am, c, zm), ea * ha, ez * hz, ec * n, key)

            # The four edges of the cell: a reveal into a hole, or the end of the wall.
            edges = (
                (i - 1, j, P(A[i], cm, zm), -ea, ec * thick / 2, ez * hz),
                (i + 1, j, P(A[i + 1], cm, zm), ea, ec * thick / 2, ez * hz),
                (i, j - 1, P(am, cm, Z[j]), -ez, ea * ha, ec * thick / 2),
                (i, j + 1, P(am, cm, Z[j + 1]), ez, ea * ha, ec * thick / 2),
            )
            for ni, nj, centre, normal, hu, hv in edges:
                inside = 0 <= ni < na and 0 <= nj < nz
                if inside:
                    if is_open(ni, nj):
                        mb.rect(centre, hu, hv, normal, reveal_key(am, zm))
                elif cut_top and nj == nz:
                    mb.rect(centre, hu, hv, normal, cap_key)
                else:
                    key = face_material(centre + normal * SAMPLE, wall, override)
                    if key:
                        mb.rect(centre, hu, hv, normal, key)

    if mb.empty:
        return None
    return mb.build(name or wall.name, coll)


def build_walls(coll="structure", **kwargs):
    return [o for o in (build_wall(w, coll, **kwargs) for w in plan.WALLS) if o]


def build_floors(coll="structure", override=None):
    """One floor object per room, and the strips under doorways."""
    made = []
    for room in plan.ROOMS:
        mb = MeshBuilder()
        z = plan.FFL[room.storey]
        for x0, y0, x1, y1 in room.rects:
            mb.rect(((x0 + x1) / 2, (y0 + y1) / 2, z), ((x1 - x0) / 2, 0, 0), (0, (y1 - y0) / 2, 0),
                    (0, 0, 1), override or f"floor_{room.key}")
        made.append(mb.build(f"floor_{room.key}", coll))

    # A doorway is a gap in a wall, so the floor has to carry through it.
    for storey, tag in enumerate(("gf", "ff")):
        mb = MeshBuilder()
        for wall in plan.WALLS:
            for o in wall.openings:
                if o.kind in ("window", "fireplace") or abs(o.sill - plan.FFL[storey]) > 1e-4:
                    continue
                if wall.axis == "x":
                    lo, hi = (o.start, wall.y0), (o.end, wall.y1)
                else:
                    lo, hi = (wall.x0, o.start), (wall.x1, o.end)
                cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
                mb.rect((cx, cy, o.sill), ((hi[0] - lo[0]) / 2, 0, 0), (0, (hi[1] - lo[1]) / 2, 0),
                        (0, 0, 1), override or "wood_mid")
        if not mb.empty:
            made.append(mb.build(f"floor_thresholds_{tag}", coll))
    return made


def build_ceilings(coll="structure", override=None):
    made = []
    key = override or "ceiling"
    w, d = plan.WIDTH, plan.DEPTH
    vx0, vy0, vx1, vy1 = plan.STAIR_VOID

    # Ground-floor ceiling: everything except the stairwell.
    mb = MeshBuilder()
    z = plan.CEILING
    for x0, y0, x1, y1 in ((0, 0, w, vy0), (vx1, vy0, w, vy1), (0, vy1, w, d)):
        mb.rect(((x0 + x1) / 2, (y0 + y1) / 2, z), ((x1 - x0) / 2, 0, 0), (0, (y1 - y0) / 2, 0),
                (0, 0, -1), key)
    made.append(mb.build("ceiling_gf", coll))

    # The edge of the first floor where it stops at the stairwell.
    mb = MeshBuilder()
    apron = override or "trim_paint"
    zm, hz = (plan.CEILING + plan.FFL[1]) / 2, plan.SLAB / 2
    mb.rect((vx1, (vy0 + vy1) / 2, zm), (0, (vy1 - vy0) / 2, 0), (0, 0, hz), (-1, 0, 0), apron)
    mb.rect(((vx0 + vx1) / 2, vy0, zm), ((vx1 - vx0) / 2, 0, 0), (0, 0, hz), (0, 1, 0), apron)
    made.append(mb.build("stairwell_apron", coll))

    mb = MeshBuilder()
    mb.rect((w / 2, d / 2, plan.ROOF_Z), (w / 2, 0, 0), (0, d / 2, 0), (0, 0, -1), key)
    made.append(mb.build("ceiling_ff", coll))
    return made


def wall_runs(level="floor", thickness=0.018):
    """Stretches of wall that meet a floor (or a ceiling), for skirting and
    coving. Yields dicts with the two ends of the run on the wall face, the
    normal pointing into the room, the room, the height, and what each end
    meets: "open" (a doorway), "inside" (an inside corner) or "outside"."""
    out = []
    for wall in plan.WALLS:
        along_x = wall.axis == "x"
        a0, a1 = (wall.x0, wall.x1) if along_x else (wall.y0, wall.y1)
        c0, c1 = (wall.y0, wall.y1) if along_x else (wall.x0, wall.x1)
        ea = Vector((1, 0, 0)) if along_x else Vector((0, 1, 0))
        ec = Vector((0, 1, 0)) if along_x else Vector((1, 0, 0))

        def P(a, c, z):
            return Vector((a, c, z)) if along_x else Vector((c, a, z))

        values = [plan.STAIR_Y0, plan.STAIR_Y1] if not along_x else [plan.VOID_X1]
        for o in wall.openings:
            values += [o.start, o.end]
        for room in plan.ROOMS:
            for r in room.rects:
                values += [r[0], r[2]] if along_x else [r[1], r[3]]
        for other in plan.WALLS:
            if other is not wall:
                values += [other.x0, other.x1] if along_x else [other.y0, other.y1]
        v = plan.STAIR_VOID
        values += [v[0], v[2]] if along_x else [v[1], v[3]]
        A = _cuts(values, a0, a1)

        for storey in (0, 1):
            z = plan.FFL[storey] if level == "floor" else plan.FFL[storey] + plan.CEILING
            zs = z + 0.05 if level == "floor" else z - 0.05
            if not (wall.z0 - 1e-6 <= zs <= wall.z1 + 1e-6):
                continue
            exists = plan.has_floor if level == "floor" else plan.has_ceiling

            def opening_at(a):
                return next((o for o in wall.openings if o.start < a < o.end and o.sill < zs < o.head), None)

            def room_of(point):
                key = face_material(point, wall)
                if not key or not key.startswith("wall_"):
                    return None
                return key[5:] if exists(point.x, point.y, storey) else None

            def end_kind(point, direction, n, beyond_open):
                if beyond_open:
                    return "open"
                q = point + direction * 0.02 + n * (thickness / 2)
                q.z = zs
                return "inside" if core.wall_containing(q.x, q.y, q.z) is not None else "outside"

            # the two long faces
            for c, sign in ((c0, -1), (c1, 1)):
                n = ec * sign
                segments = []
                for i in range(len(A) - 1):
                    am = (A[i] + A[i + 1]) / 2
                    if opening_at(am):
                        continue
                    room = room_of(P(am, c + sign * SAMPLE, zs))
                    if not room:
                        continue
                    if segments and segments[-1][2] == room and abs(segments[-1][1] - A[i]) < 1e-6:
                        segments[-1][1] = A[i + 1]
                    else:
                        segments.append([A[i], A[i + 1], room])
                for s0, s1, room in segments:
                    p0, p1 = P(s0, c, z), P(s1, c, z)
                    out.append(dict(
                        p0=p0, p1=p1, normal=n, room=room, z=z, axis=wall.axis, wall=wall.name,
                        end0=end_kind(p0, -ea, n, bool(opening_at(s0 - 0.01)) and s0 > a0 + 1e-6),
                        end1=end_kind(p1, ea, n, bool(opening_at(s1 + 0.01)) and s1 < a1 - 1e-6)))

            # the two ends
            cm = (c0 + c1) / 2
            for a, sign in ((a0, -1), (a1, 1)):
                n = ea * sign
                room = room_of(P(a + sign * SAMPLE, cm, zs))
                if not room:
                    continue
                p0, p1 = P(a, c0, z), P(a, c1, z)
                out.append(dict(
                    p0=p0, p1=p1, normal=n, room=room, z=z, axis="y" if along_x else "x", wall=wall.name,
                    end0=end_kind(p0, -ec, n, False), end1=end_kind(p1, ec, n, False)))
    return out


def build_envelope(coll="structure"):
    """Close the house: a slab under the ground floor, and a deck and pitched
    roof over the top ceiling. Without them the shell is open at both ends
    and light gets in along the wall heads."""
    e = plan.EXT_T
    x0, y0, x1, y1 = -e, -e, plan.WIDTH + e, plan.DEPTH + e
    made = []

    mb = MeshBuilder()
    mb.box((x0 - 0.03, y0 - 0.03, -0.55), (x1 + 0.03, y1 + 0.03, -0.002), "foundation")
    made.append(mb.build("ground_slab", coll, recalc=True))

    # Roof: a deck sealing the wall heads, then a gable roof with its ridge
    # running east-west and eaves overhanging the front and back.
    mb = MeshBuilder()
    top = plan.ROOF_Z
    mb.box((x0, y0, top + 0.002), (x1, y1, top + 0.16), "foundation")
    over, rise = 0.35, 2.3
    eave, ridge_y = top + 0.16, (y0 + y1) / 2
    a = Vector((x0, y0 - over, eave))
    b = Vector((x0, y1 + over, eave))
    c = Vector((x0, ridge_y, eave + rise))
    span = Vector((x1 - x0, 0, 0))
    mb.face([a, a + span, c + span, c], "roof")                 # south slope
    mb.face([b + span, b, c, c + span], "roof")                 # north slope
    mb.face([a, c, b], "ext_siding")                             # west gable
    mb.face([a + span, b + span, c + span], "ext_siding")        # east gable
    mb.face([a, b, b + span, a + span], "foundation")           # underside
    made.append(mb.build("roof", coll, recalc=True))
    return made
