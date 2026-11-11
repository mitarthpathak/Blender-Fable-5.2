"""Mesh, material and scene helpers shared by every part of the house builder."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import bmesh
import bpy
from mathutils import Vector

import assets
import plan

UP = Vector((0.0, 0.0, 1.0))


# --- Materials --------------------------------------------------------------

@dataclass(frozen=True)
class Spec:
    """A material before it has textures: a flat colour, and how big one
    repeat of its texture is in the world. UVs are written in metres divided
    by `tile`, so textures land at real scale with no mapping node, which is
    what a game engine wants."""

    color: str
    roughness: float = 0.7
    metallic: float = 0.0
    tile: float = 1.0
    rot: bool = False          # turn the texture a quarter turn
    alpha: float = 1.0
    emission: float = 0.0      # strength of a glow in the material's own colour


SPECS: dict[str, Spec] = {
    # walls, one per room so each can be painted separately
    "wall_hall": Spec("#b3ad9c", 0.85, tile=2.4),
    "wall_living": Spec("#8f9a8a", 0.85, tile=2.4),
    "wall_landing": Spec("#b3ad9c", 0.85, tile=2.4),
    "wall_bedroom": Spec("#8892a0", 0.85, tile=2.4),
    "wall_kitchen": Spec("#9c9577", 0.85, tile=2.4),
    "wall_bathroom": Spec("#869089", 0.85, tile=2.4),
    "tile_bathroom": Spec("#a7b0a3", 0.3),
    "tile_bathroom_wet": Spec("#a0a99c", 0.3),
    "mirror": Spec("#b8bcbc", 0.04, metallic=1.0),
    "wicker": Spec("#7a6444", 0.85),
    "plastic_cream": Spec("#b3ab92", 0.5),
    "plastic_red": Spec("#7e2a24", 0.45),
    "plastic_blue": Spec("#2f4a6e", 0.45),
    "plastic_green": Spec("#3f5e44", 0.45),
    "glass_bottle": Spec("#39502f", 0.08, alpha=0.55),
    "food_brown": Spec("#5a3d22", 0.7),
    "ash": Spec("#6f6c66", 0.95),
    "print": Spec("#b0a890", 0.72),
    "dishwater": Spec("#34352a", 0.06),
    "oven_glass": Spec("#0e0f10", 0.08),
    "vinyl": Spec("#5a2b22", 0.42),
    "tile_kitchen": Spec("#a89f88", 0.35),
    "panel_wood": Spec("#3b2b21", 0.55),
    "ceiling": Spec("#c9c6bd", 0.9, tile=2.4),
    "ext_siding": Spec("#8d9186", 0.8, rot=True),      # boards run along the wall
    "ext_clapboard": Spec("#8d9186", 0.8),             # the modelled boards over it
    "ext_trim": Spec("#a9a79b", 0.7),
    "ground_grass": Spec("#3a4030", 0.95),
    "ground_path": Spec("#6f6d66", 0.9),
    "ground_road": Spec("#2b2c2e", 0.85),
    "porch_boards": Spec("#6b665b", 0.8, rot=True),
    "screen_mesh": Spec("#1a1c1b", 0.6, alpha=0.45),
    "sodium_on": Spec("#ffa040", 0.3, emission=30.0),
    # floors
    "floor_hall": Spec("#7a6a5a", 0.5, tile=1.2),
    "floor_living": Spec("#6b4a2f", 0.45, tile=2.0),
    "floor_landing": Spec("#5e4630", 0.55, tile=2.0),
    "floor_bedroom": Spec("#5e4630", 0.55, tile=2.0),
    "floor_kitchen": Spec("#7d6f52", 0.5, tile=2.0),
    "floor_bathroom": Spec("#55524a", 0.45, tile=1.5),
    # kitchen and bathroom fittings
    "cabinet": Spec("#7c6444", 0.5),
    "counter": Spec("#8b8474", 0.45),
    "enamel": Spec("#b4b1a4", 0.35),
    "enamel_almond": Spec("#b0a688", 0.38),
    "porcelain": Spec("#b9b7ac", 0.25),
    "hob": Spec("#2b2a28", 0.45),
    "towel": Spec("#77695a", 0.95),
    "gingham": Spec("#6e7d62", 0.9),
    "shower_curtain": Spec("#8f9a97", 0.6),
    "metal_chrome": Spec("#9a9c9e", 0.22, metallic=1.0),
    "metal_steel": Spec("#77797a", 0.38, metallic=1.0),
    "hearth_tile": Spec("#3a3f3a", 0.35, tile=0.6),
    # joinery
    "trim_paint": Spec("#d8d4c8", 0.45, tile=1.2),
    "door_paint": Spec("#cfcabb", 0.45, tile=1.2),
    "front_door_paint": Spec("#27323a", 0.4, tile=1.2),
    "wood_stair": Spec("#4a3423", 0.5, tile=1.5),
    "wood_dark": Spec("#33231a", 0.4, tile=1.5),
    "wood_mid": Spec("#6a4a30", 0.5, tile=1.5),
    "glass": Spec("#9db4c0", 0.03, alpha=0.14),
    "glass_frosted": Spec("#aab4b8", 0.45, alpha=0.32),
    "stone_sill": Spec("#8d8a82", 0.8, tile=1.0),
    "metal_brass": Spec("#a8843c", 0.35, metallic=1.0),
    "metal_dark": Spec("#2a2b2d", 0.5, metallic=1.0),
    "metal_white": Spec("#a9a79d", 0.5, metallic=0.0),
    "plastic_white": Spec("#bdb9ac", 0.45),
    "plastic_black": Spec("#1e1e1e", 0.45),
    "soot": Spec("#1b1a18", 0.95),
    "roof": Spec("#2b2d31", 0.75, tile=1.0),
    "foundation": Spec("#5a5852", 0.9, tile=1.0),
    "door_worn": Spec("#3d3a33", 0.7),
    "fabric_curtain": Spec("#6d685b", 0.95),
    "fabric_plaid": Spec("#6b6a4a", 0.95),
    "fabric_bed": Spec("#8f8a7c", 0.95),
    "fabric_pillow": Spec("#c9c5b8", 0.95),
    "leather": Spec("#5a3a25", 0.5),
    "carpet": Spec("#6a6248", 1.0),
    "carpet_runner": Spec("#5a2f2a", 1.0),
    # lamps and small things
    "ceramic": Spec("#b1aa9a", 0.35),
    "lampshade": Spec("#b9ad94", 0.9, alpha=0.82),
    "lampshade_lit": Spec("#ffc98a", 0.9, alpha=0.78, emission=1.6),
    "bulb_on": Spec("#ffd9a0", 0.3, emission=14.0),
    "bulb_off": Spec("#d8d4c8", 0.2),
    "screen_on": Spec("#9fb6d8", 0.3, emission=3.0),
    "paper": Spec("#cfcabb", 0.85),
    "paper_brown": Spec("#9a8463", 0.85),
    "coffee": Spec("#1d130c", 0.3),
    "book_red": Spec("#5e211c", 0.6),
    "book_green": Spec("#26392c", 0.6),
    "book_blue": Spec("#232f47", 0.6),
    "book_cream": Spec("#b3a98d", 0.7),
    "book_brown": Spec("#4a3423", 0.6),
    "book_black": Spec("#222120", 0.5),
    "rubber": Spec("#232220", 0.95),
    # helpers
    "blockout": Spec("#9a9a9a", 0.9),
    "blockout_prop": Spec("#c98a4b", 0.9),
    "collider": Spec("#ff5d47", 0.9, alpha=0.5),
    "section_cap": Spec("#2a2d33", 0.9),
}


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(value: str) -> tuple[float, float, float]:
    h = value.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def spec(key: str) -> Spec:
    """The spec for a material. Where the material has a texture set, the
    tile size is that set's real-world size, so the texture lands at scale."""
    base = SPECS.get(key) or SPECS["blockout"]
    tile = assets.tile_of(key)
    return replace(base, tile=tile) if tile else base


def material(key: str) -> bpy.types.Material:
    """The material for a key. Created flat-coloured; the materials phase
    swaps textures into the same material so every mesh picks them up."""
    name = "m_" + key
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    s = spec(key)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgb = hex_rgb(s.color)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = s.roughness
    bsdf.inputs["Metallic"].default_value = s.metallic
    mat.diffuse_color = (*rgb, s.alpha)
    if s.emission:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = s.emission
    if s.alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = s.alpha
        mat.surface_render_method = "BLENDED"
    return mat


# --- Scene organisation -----------------------------------------------------

def collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def link(obj: bpy.types.Object, coll: str) -> bpy.types.Object:
    collection(coll).objects.link(obj)
    return obj


def empty(name: str, coll: str, location=(0, 0, 0)) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_size = 0.2
    return link(obj, coll)


# --- Mesh building ----------------------------------------------------------

class MeshBuilder:
    """Collects faces, then makes one mesh object. Faces get world-scale UVs
    and a material each; vertices are welded."""

    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.keys: list[str] = []
        self._verts: dict[tuple[int, int, int], bmesh.types.BMVert] = {}
        self.smooth = False

    def _slot(self, key: str) -> int:
        if key not in self.keys:
            self.keys.append(key)
        return self.keys.index(key)

    def _vert(self, p) -> bmesh.types.BMVert:
        k = (round(p[0] * 20000), round(p[1] * 20000), round(p[2] * 20000))
        v = self._verts.get(k)
        if v is None:
            v = self._verts[k] = self.bm.verts.new(p)
        return v

    def face(self, pts, key: str, uvs=None, rot: bool | None = None):
        """Add a polygon. `pts` wind counter-clockwise seen from outside."""
        pts = [Vector(p) for p in pts]
        verts = [self._vert(p) for p in pts]
        if len(set(verts)) < 3:
            return None
        try:
            f = self.bm.faces.new(verts)
        except ValueError:          # the same face twice
            return None
        f.material_index = self._slot(key)
        s = spec(key)
        if uvs is None:
            n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            if n.length < 1e-12 and len(pts) > 3:
                n = (pts[2] - pts[0]).cross(pts[3] - pts[0])
            n.normalize()
            turn = s.rot if rot is None else rot
            uvs = [world_uv(p, n, s.tile, turn) for p in pts]
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def rect(self, center, half_u, half_v, normal, key: str, rot: bool | None = None):
        """A rectangle from its centre and two half-edge vectors, wound to
        face along `normal`."""
        c, hu, hv = Vector(center), Vector(half_u), Vector(half_v)
        if hu.cross(hv).dot(Vector(normal)) < 0:
            hu = -hu
        return self.face([c - hu - hv, c + hu - hv, c + hu + hv, c - hu + hv], key, rot=rot)

    def box(self, lo, hi, key, skip: str = "", rot: bool | None = None):
        """An axis-aligned box. `key` is one material or a dict by side
        ("-x", "+x", "-y", "+y", "-z", "+z"). `skip` lists sides to leave open."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        hx, hy, hz = (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2
        sides = {
            "-x": ((x0, cy, cz), (0, hy, 0), (0, 0, hz), (-1, 0, 0)),
            "+x": ((x1, cy, cz), (0, hy, 0), (0, 0, hz), (1, 0, 0)),
            "-y": ((cx, y0, cz), (hx, 0, 0), (0, 0, hz), (0, -1, 0)),
            "+y": ((cx, y1, cz), (hx, 0, 0), (0, 0, hz), (0, 1, 0)),
            "-z": ((cx, cy, z0), (hx, 0, 0), (0, hy, 0), (0, 0, -1)),
            "+z": ((cx, cy, z1), (hx, 0, 0), (0, hy, 0), (0, 0, 1)),
        }
        for side, (c, hu, hv, n) in sides.items():
            if side in skip:
                continue
            k = key[side] if isinstance(key, dict) else key
            if k:
                self.rect(c, hu, hv, n, k, rot=rot)

    def prism(self, profile, axis_origin, u, v, w, length, key, caps=True, rot=None):
        """Extrude a 2D profile (list of (a, b), counter-clockwise) along w.
        A point is origin + a*u + b*v; the extrusion runs `length` along w."""
        o, u, v, w = Vector(axis_origin), Vector(u), Vector(v), Vector(w)
        near = [o + u * a + v * b for a, b in profile]
        far = [p + w * length for p in near]
        flip = u.cross(v).dot(w) < 0
        n = len(profile)
        for i in range(n):
            j = (i + 1) % n
            quad = [near[i], near[j], far[j], far[i]]
            self.face(quad[::-1] if flip else quad, key, rot=rot)
        if caps:
            self.face(near if flip else near[::-1], key, rot=rot)
            self.face(far[::-1] if flip else far, key, rot=rot)

    def cylinder(self, base, axis, radius, key, segments=12, caps="both", radius_top=None):
        """A cylinder or cone frustum from `base` along the vector `axis`."""
        base, axis = Vector(base), Vector(axis)
        w = axis.normalized()
        ref = Vector((1, 0, 0)) if abs(w.x) < 0.9 else Vector((0, 1, 0))
        u = w.cross(ref).normalized()
        v = w.cross(u)
        r1 = radius if radius_top is None else radius_top
        ring0 = [base + (u * math.cos(t) + v * math.sin(t)) * radius
                 for t in (2 * math.pi * i / segments for i in range(segments))]
        ring1 = [base + axis + (u * math.cos(t) + v * math.sin(t)) * r1
                 for t in (2 * math.pi * i / segments for i in range(segments))]
        for i in range(segments):
            j = (i + 1) % segments
            self.face([ring0[i], ring0[j], ring1[j], ring1[i]], key)
        if caps in ("both", "base"):
            self.face(ring0[::-1], key)
        if caps in ("both", "top"):
            self.face(ring1, key)

    def build(self, name: str, coll: str, origin=None, smooth: bool | None = None,
              recalc: bool = False):
        """Finish the mesh. With `origin`, vertices are stored relative to it
        and the object sits there, so it becomes the pivot. `recalc` makes
        the normals of a closed mesh point outwards."""
        bm = self.bm
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if origin is not None:
            bmesh.ops.translate(bm, verts=bm.verts, vec=-Vector(origin))
        bm.normal_update()
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for key in self.keys:
            mesh.materials.append(material(key))
        if smooth if smooth is not None else self.smooth:
            mesh.shade_smooth()
        obj = bpy.data.objects.new(name, mesh)
        if origin is not None:
            obj.location = origin
        return link(obj, coll)

    @property
    def empty(self) -> bool:
        return len(self.bm.faces) == 0


def world_uv(p: Vector, n: Vector, tile: float, turn: bool = False):
    """Project a point onto its face plane in metres, then scale by the tile
    size. On walls V is always up; on floors and ceilings U is east."""
    if abs(n.z) > 0.999:
        u, v = p.x, p.y
    else:
        t = UP.cross(n)
        t.normalize()
        b = n.cross(t)
        u, v = p.dot(t), p.dot(b)
    if turn:
        u, v = v, -u
    return (u / tile, v / tile)


# --- Plan queries -----------------------------------------------------------

EPS = 1e-4


def in_rect(x, y, rect, pad=EPS) -> bool:
    return rect[0] - pad <= x <= rect[2] + pad and rect[1] - pad <= y <= rect[3] + pad


def room_at(x: float, y: float, z: float) -> str | None:
    """Which room a point is in, or None for inside a wall, the floor
    structure, or outside the house."""
    if in_rect(x, y, plan.STAIR_VOID) and 0.0 <= z <= plan.ROOF_Z:
        return "hall" if z < plan.FFL[1] else "landing"
    for room in plan.ROOMS:
        z0 = plan.FFL[room.storey]
        if z0 - EPS <= z <= z0 + plan.CEILING + EPS and any(in_rect(x, y, r) for r in room.rects):
            return room.key
    return None


def inside_house(x: float, y: float, z: float) -> bool:
    return (-EPS <= x <= plan.WIDTH + EPS and -EPS <= y <= plan.DEPTH + EPS
            and -EPS <= z <= plan.ROOF_Z + EPS)


def wall_containing(x, y, z, ignore=None):
    for w in plan.WALLS:
        if w is ignore:
            continue
        if w.x0 + EPS < x < w.x1 - EPS and w.y0 + EPS < y < w.y1 - EPS and w.z0 - EPS < z < w.z1 + EPS:
            return w
    return None


def tri_count(objects=None) -> int:
    total = 0
    for obj in objects or bpy.data.objects:
        if obj.type == "MESH":
            total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return total
