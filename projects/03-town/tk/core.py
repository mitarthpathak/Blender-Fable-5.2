"""Mesh and material helpers for the town kit.

Every surface uses one of a small set of shared PBR materials (Poly Haven
albedo + normal + ARM). Paint colour, grime and wear ride in the vertex
colours, which multiply the albedo, so five houses in five colours still
share one siding material and one draw state. UVs are world metres divided
by the texture's real-world repeat size, so textures land at true scale.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

import assets

HERE = Path(__file__).resolve().parent.parent
DERIVED = HERE / "textures" / "derived"
DECALS = HERE / "textures" / "decals"


# --- Materials ---------------------------------------------------------------

# key: (texture set or None, derived diffuse name or None, extra settings)
MATS: dict[str, dict] = {
    # houses
    "siding": dict(set="weathered_plank_siding", diff="siding_neutral", tile=2.4),
    "trim": dict(set="white_planks_clean", diff="trim_neutral", tile=1.8),
    "porch_deck": dict(set="distressed_painted_planks", tile=1.6),
    "door": dict(set="distressed_painted_planks", diff="door_neutral", tile=1.2),
    "roof_shingle": dict(set="grey_roof_01", tile=3.0),
    "roof_slate": dict(set="roof_slates_02", tile=3.0),
    "roof_tin": dict(set="rusty_corrugated_iron", tile=1.5),
    "plywood": dict(set="plywood", tile=1.2),
    "brick": dict(set="red_brick", tile=1.4),
    "concrete": dict(set="concrete_floor_worn_02", tile=2.0),
    "metal_painted": dict(set="rusty_painted_metal", diff="metal_neutral", tile=1.5),
    "glass": dict(color=(0.06, 0.07, 0.075), rough=0.06, metal=0.0, spec=0.6),
    "glass_dirty": dict(color=(0.09, 0.09, 0.085), rough=0.35),
    "interior_dark": dict(color=(0.025, 0.024, 0.022), rough=0.9),
    "window_lit": dict(color=(0.55, 0.42, 0.26), rough=0.8, emit=(1.0, 0.62, 0.32), emit_strength=1.2),
    "screen_mesh": dict(color=(0.05, 0.05, 0.05), rough=0.6, alpha=0.5),
    # street
    "road": dict(set="asphalt_02", tile=3.0),
    "road_patch": dict(set="worn_asphalt", tile=2.5),
    "sidewalk": dict(set="concrete_pavement", tile=2.0),
    "lawn_kept": dict(set="leafy_grass", tile=2.0),
    "lawn_dead": dict(set="withered_grass", tile=2.5),
    "lawn_overgrown": dict(set="leafy_grass", diff="lawn_rough", tile=1.8),
    "lawn_leafy": dict(set="brown_mud_leaves_01", tile=1.2),
    "leaves": dict(set="forest_leaves_02", tile=1.5),
    "bark": dict(set="bark_brown_02", tile=1.2),
    "wood_weathered": dict(set="weathered_planks", tile=1.5),
    "metal_rust": dict(set="rusty_metal_02", tile=1.2),
    "car_paint": dict(set="rusty_metal_02", diff="carpaint_neutral", tile=1.2),
    "manhole": dict(set="metal_plate", tile=0.8),
    "barrier_concrete": dict(set="dirty_concrete", tile=2.0),
    "tyre": dict(set="rubber_tiles", tile=0.6),
    "chrome_dull": dict(color=(0.45, 0.45, 0.44), rough=0.45, metal=1.0),
    "plastic_dark": dict(color=(0.05, 0.05, 0.05), rough=0.55),
    "lamp_red": dict(color=(0.25, 0.03, 0.02), rough=0.3),
    "lamp_clear": dict(color=(0.5, 0.48, 0.42), rough=0.15),
    "sodium_on": dict(color=(1.0, 0.62, 0.30), rough=0.3, emit=(1.0, 0.55, 0.22), emit_strength=12.0),
    "sodium_off": dict(color=(0.30, 0.26, 0.20), rough=0.25),
    "wire": dict(color=(0.03, 0.03, 0.03), rough=0.6),
    "paint_marking": dict(diff_png="marking_yellow", tile=1.0, clip=True, rough=0.7),
    "paint_white": dict(diff_png="marking_white", tile=1.0, clip=True, rough=0.7),
    "chainlink": dict(diff_png="chainlink", tile=1.0, clip=True, rough=0.5, metal=0.6),
    "grass_card": dict(diff_png="grass_tuft", tile=1.0, clip=True, rough=0.9, two_sided=True),
    "puddle": dict(diff_png="puddle", tile=1.0, blend=True, rough=0.02, spec=0.9),
    "decal_grime": dict(diff_png="grime_streaks", tile=1.0, blend=True, rough=0.9),
    "decal_moss": dict(diff_png="moss", tile=1.0, blend=True, rough=0.95),
    "decal_crack": dict(diff_png="crack", tile=1.0, blend=True, rough=0.9),
    "decal_leaves": dict(diff_png="leaf_litter", tile=1.0, blend=True, rough=0.8),
    "decal_oil": dict(diff_png="oil_stain", tile=1.0, blend=True, rough=0.25),
    "sign_closed": dict(diff_png="sign_road_closed", tile=1.0, rough=0.6),
    "sign_sale": dict(diff_png="sign_for_sale", tile=1.0, rough=0.6),
}

_cache: dict[str, bpy.types.Material] = {}


def tile_of(key: str) -> float:
    return MATS[key].get("tile", 1.0)


def _image(path: Path, non_color: bool = False) -> bpy.types.Image:
    name = path.name
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(str(path), check_existing=True)
        img.name = name
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def material(key: str) -> bpy.types.Material:
    """The shared material for `key`, built on first use."""
    if key in _cache and _cache[key].name in bpy.data.materials:
        return _cache[key]
    spec = MATS[key]
    mat = bpy.data.materials.get(key) or bpy.data.materials.new(key)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    vc.location = (-500, 300)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.location = (0, 250)
    nt.links.new(vc.outputs["Color"], mix.inputs[7])     # B
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])

    if "set" in spec:
        set_id = spec["set"]
        diff_path = DERIVED / f"{spec['diff']}_diff.jpg" if "diff" in spec else assets.tex(set_id, "diff")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = _image(diff_path)
        tex.location = (-500, 100)
        nt.links.new(tex.outputs["Color"], mix.inputs[6])   # A
        arm = nt.nodes.new("ShaderNodeTexImage")
        arm.image = _image(assets.tex(set_id, "arm"), True)
        arm.location = (-500, -200)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.location = (-200, -200)
        nt.links.new(arm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        nor = nt.nodes.new("ShaderNodeTexImage")
        nor.image = _image(assets.tex(set_id, "nor_gl"), True)
        nor.location = (-500, -500)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.location = (-200, -500)
        nmap.inputs["Strength"].default_value = spec.get("normal", 1.0)
        nt.links.new(nor.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    elif "diff_png" in spec:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = _image(DECALS / f"{spec['diff_png']}.png")
        tex.location = (-500, 100)
        nt.links.new(tex.outputs["Color"], mix.inputs[6])
        bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.7)
        bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
        if spec.get("clip"):
            gt = nt.nodes.new("ShaderNodeMath")
            gt.operation = "GREATER_THAN"
            gt.inputs[1].default_value = 0.5
            gt.location = (0, -50)
            nt.links.new(tex.outputs["Alpha"], gt.inputs[0])
            nt.links.new(gt.outputs[0], bsdf.inputs["Alpha"])
            mat.surface_render_method = "DITHERED"
        elif spec.get("blend"):
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.surface_render_method = "BLENDED"
        # normal maps for the generated decals come from a small flat normal
    else:
        mix.inputs[6].default_value = (*spec["color"], 1.0)
        bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.7)
        bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
        if "alpha" in spec:
            bsdf.inputs["Alpha"].default_value = spec["alpha"]
            mat.surface_render_method = "BLENDED"
    if "spec" in spec:
        bsdf.inputs["Specular IOR Level"].default_value = spec["spec"]
    if "emit" in spec:
        bsdf.inputs["Emission Color"].default_value = (*spec["emit"], 1.0)
        bsdf.inputs["Emission Strength"].default_value = spec["emit_strength"]
    mat.use_backface_culling = not spec.get("two_sided", False)
    _cache[key] = mat
    return mat


# --- Mesh builder ----------------------------------------------------------------

def _uv_for(p: Vector, n: Vector, tile: float, rot: bool) -> tuple[float, float]:
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        u, v = p.x, p.y
    elif ax >= ay:
        u, v = p.y * (1 if n.x > 0 else -1), p.z
    else:
        u, v = p.x * (-1 if n.y > 0 else 1), p.z
    if rot:
        u, v = v, u
    return u / tile, v / tile


class MeshBuilder:
    """Collects faces with a material key, UVs and a vertex colour per corner."""

    def __init__(self, color=(1.0, 1.0, 1.0)):
        self.verts: list[Vector] = []
        self.faces: list[tuple[int, ...]] = []
        self.mats: list[str] = []
        self.uvs: list[list[tuple[float, float]]] = []
        self.cols: list[list[tuple[float, float, float, float]]] = []
        self.color = color
        self.grime = None            # callable(world point) -> multiplier, or None
        self.rot_keys: set[str] = set()

    # low level
    def face(self, pts, mat: str, uvs=None, color=None, rot=False):
        pts = [Vector(p) for p in pts]
        base = len(self.verts)
        self.verts.extend(pts)
        self.faces.append(tuple(range(base, base + len(pts))))
        self.mats.append(mat)
        if uvs is None:
            n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
            if n.length < 1e-12 and len(pts) > 3:
                n = (pts[2] - pts[0]).cross(pts[3] - pts[0])
            n = n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))
            t = tile_of(mat) if mat in MATS else 1.0
            uvs = [_uv_for(p, n, t, rot or mat in self.rot_keys) for p in pts]
        self.uvs.append(list(uvs))
        c = color or self.color
        cols = []
        for p in pts:
            k = self.grime(p) if self.grime else 1.0
            cols.append((c[0] * k, c[1] * k, c[2] * k, 1.0))
        self.cols.append(cols)
        return self

    def quad(self, a, b, c, d, mat, **kw):
        return self.face([a, b, c, d], mat, **kw)

    def box(self, lo, hi, mat, skip="", color=None, rot=False, mats=None):
        """Axis-aligned box. `skip` lists faces to leave out: '+x-x+y-y+z-z'.
        `mats` overrides the material per face, e.g. {'+z': 'roof'}."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        P = [Vector(v) for v in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        faces = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
                 "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
        for key, idx in faces.items():
            if key in skip:
                continue
            m = (mats or {}).get(key, mat)
            self.face([P[i] for i in idx], m, color=color, rot=rot)
        return self

    def obox(self, centre, size, rot_z, mat, color=None, skip="", tilt=(0.0, 0.0)):
        """Box of `size` (x, y, z) centred at `centre`, turned rot_z radians about Z
        (and optionally tilted about X then Y)."""
        sx, sy, sz = (s / 2 for s in size)
        m = Matrix.Translation(Vector(centre)) @ Matrix.Rotation(rot_z, 4, "Z") \
            @ Matrix.Rotation(tilt[1], 4, "Y") @ Matrix.Rotation(tilt[0], 4, "X")
        P = [m @ Vector(v) for v in ((-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
                                     (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz))]
        faces = {"-z": (0, 3, 2, 1), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4),
                 "+y": (2, 3, 7, 6), "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
        for key, idx in faces.items():
            if key not in skip:
                self.face([P[i] for i in idx], mat, color=color)
        return self

    def cylinder(self, base, axis, radius, mat, segments=10, radius_top=None, caps="both", color=None,
                 uv_wrap=True):
        base, axis = Vector(base), Vector(axis)
        length = axis.length
        d = axis.normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        v = d.cross(u)
        rt = radius if radius_top is None else radius_top
        ring0, ring1 = [], []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            o = u * math.cos(a) + v * math.sin(a)
            ring0.append(base + o * radius)
            ring1.append(base + axis + o * rt)
        t = tile_of(mat) if mat in MATS else 1.0
        circ = 2 * math.pi * max(radius, rt)
        for i in range(segments):
            j = (i + 1) % segments
            uvs = None
            if uv_wrap:
                u0, u1 = i / segments * circ / t, (i + 1) / segments * circ / t
                uvs = [(u0, 0), (u1, 0), (u1, length / t), (u0, length / t)]
            self.face([ring0[i], ring0[j], ring1[j], ring1[i]], mat, uvs=uvs, color=color)
        if caps in ("both", "bottom"):
            self.face(list(reversed(ring0)), mat, color=color)
        if caps in ("both", "top"):
            self.face(ring1, mat, color=color)
        return self

    def tube(self, pts, radius, mat, segments=6, color=None, radii=None):
        """A tube along a polyline (wires, branches, pipes)."""
        pts = [Vector(p) for p in pts]
        rings = []
        for k, p in enumerate(pts):
            if k == 0:
                d = pts[1] - pts[0]
            elif k == len(pts) - 1:
                d = pts[-1] - pts[-2]
            else:
                d = (pts[k + 1] - pts[k - 1])
            d.normalize()
            ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            u = d.cross(ref).normalized()
            v = d.cross(u)
            r = radii[k] if radii else radius
            rings.append([p + (u * math.cos(2 * math.pi * i / segments) + v * math.sin(2 * math.pi * i / segments)) * r
                          for i in range(segments)])
        t = tile_of(mat) if mat in MATS else 1.0
        dist = 0.0
        for k in range(len(rings) - 1):
            seg = (pts[k + 1] - pts[k]).length
            for i in range(segments):
                j = (i + 1) % segments
                uvs = [(i / segments * 0.5, dist / t), ((i + 1) / segments * 0.5, dist / t),
                       ((i + 1) / segments * 0.5, (dist + seg) / t), (i / segments * 0.5, (dist + seg) / t)]
                self.face([rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]], mat, uvs=uvs, color=color)
            dist += seg
        return self

    def disc(self, centre, radius, mat, segments=16, z_up=True, color=None, uv_square=False):
        c = Vector(centre)
        pts = [c + Vector((math.cos(2 * math.pi * i / segments) * radius,
                           math.sin(2 * math.pi * i / segments) * radius, 0)) for i in range(segments)]
        uvs = None
        if uv_square:
            uvs = [(0.5 + 0.5 * math.cos(2 * math.pi * i / segments), 0.5 + 0.5 * math.sin(2 * math.pi * i / segments))
                   for i in range(segments)]
        self.face(pts if z_up else list(reversed(pts)), mat, uvs=uvs, color=color)
        return self

    def card(self, centre, w, h, rot_z, mat, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), color=None, flat=False,
             lift=0.0):
        """A rectangle with 0..1 UVs: upright facing the rotation's -Y, or flat on the ground."""
        c = Vector(centre)
        a = Vector((math.cos(rot_z), math.sin(rot_z), 0))
        if flat:
            b = Vector((-math.sin(rot_z), math.cos(rot_z), 0))
            pts = [c - a * w / 2 - b * h / 2, c + a * w / 2 - b * h / 2, c + a * w / 2 + b * h / 2,
                   c - a * w / 2 + b * h / 2]
            pts = [p + Vector((0, 0, lift)) for p in pts]
        else:
            up = Vector((0, 0, 1))
            pts = [c - a * w / 2, c + a * w / 2, c + a * w / 2 + up * h, c - a * w / 2 + up * h]
        self.face(pts, mat, uvs=list(uvs), color=color)
        return self

    def extend(self, other: "MeshBuilder", matrix: Matrix | None = None):
        base = len(self.verts)
        m = matrix or Matrix.Identity(4)
        self.verts.extend(m @ v for v in other.verts)
        self.faces.extend(tuple(i + base for i in f) for f in other.faces)
        self.mats.extend(other.mats)
        self.uvs.extend(other.uvs)
        self.cols.extend(other.cols)
        return self

    def empty(self) -> bool:
        return not self.faces

    def build_mesh(self, name: str, merge: float = 0.0005, smooth=False) -> bpy.types.Mesh:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        keys = []
        for m in self.mats:
            if m not in keys:
                keys.append(m)
        for k in keys:
            mesh.materials.append(material(k))
        idx = {k: i for i, k in enumerate(keys)}
        mesh.polygons.foreach_set("material_index", [idx[m] for m in self.mats])
        uv = mesh.uv_layers.new(name="UVMap")
        col = mesh.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        li = 0
        flat_uv, flat_col = [], []
        for f, fu, fc in zip(self.faces, self.uvs, self.cols):
            for k in range(len(f)):
                flat_uv.extend(fu[k])
                flat_col.extend(fc[k])
                li += 1
        uv.data.foreach_set("uv", flat_uv)
        col.data.foreach_set("color", flat_col)
        mesh.color_attributes.active_color_index = 0
        mesh.update()
        if merge > 0:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
            bm.to_mesh(mesh)
            bm.free()
        for p in mesh.polygons:
            p.use_smooth = smooth
        return mesh

    def build(self, name: str, coll: str, origin=(0, 0, 0), smooth=False, merge=0.0005) -> bpy.types.Object:
        o = Vector(origin)
        if o.length > 0:
            self.verts = [v - o for v in self.verts]
        mesh = self.build_mesh(name, merge=merge, smooth=smooth)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = o
        collection(coll).objects.link(obj)
        return obj


# --- Scene helpers -----------------------------------------------------------------

def collection(name: str, parent: str | None = None) -> bpy.types.Collection:
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (bpy.data.collections[parent] if parent else bpy.context.scene.collection).children.link(c)
    return c


def instance(mesh: bpy.types.Mesh, name: str, coll: str, loc, rot_z=0.0, scale=1.0, tilt=(0.0, 0.0)):
    """A linked duplicate: a new object sharing `mesh`."""
    obj = bpy.data.objects.new(name, mesh)
    obj.location = Vector(loc)
    obj.rotation_euler = (tilt[0], tilt[1], rot_z)
    obj.scale = (scale, scale, scale)
    collection(coll).objects.link(obj)
    return obj


def light(name: str, loc, kind: str, energy: float, color, coll="lights", radius=0.1, **props):
    data = bpy.data.lights.new(name, "POINT" if kind == "point" else kind.upper())
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    for k, v in props.items():
        setattr(data, k, v)
    obj = bpy.data.objects.new(name, data)
    obj.location = Vector(loc)
    collection(coll).objects.link(obj)
    return obj


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ground_grime(z_ground: float, height=0.9, strength=0.45, top_z=None, top_strength=0.0):
    """Vertex-colour grime: darker near the ground (splash-back, moss, damp)."""
    def f(p):
        k = 1.0
        if p.z < z_ground + height:
            t = max(0.0, (p.z - z_ground) / height)
            k *= 1.0 - strength * (1.0 - t) ** 1.6
        if top_z is not None and p.z > top_z - 0.6:
            t = min(1.0, (p.z - (top_z - 0.6)) / 0.6)
            k *= 1.0 - top_strength * t
        return k
    return f


def jitter_color(rng: random.Random, c, amount=0.06):
    k = 1.0 + rng.uniform(-amount, amount)
    return (c[0] * k, c[1] * k * (1 + rng.uniform(-0.02, 0.02)), c[2] * k)
