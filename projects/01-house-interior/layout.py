"""Phase 1, layout: draw the floor plan from plan.py and render it top-down.

This builds a flat drawing, not the house. It is saved as its own .blend so
the real scene never inherits drawing geometry.

    scripts/bmcp.py code projects/01-house-interior/layout.py
"""

import importlib
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import plan  # noqa: E402

importlib.reload(plan)  # Blender keeps modules between runs

BLEND = HERE / "layout.blend"
# 01_layout_plan.png is the plan as first signed off (through living/dining room, box room).
RENDER = HERE / "renders" / "08_layout_plan_kitchen_bathroom.png"

# Where each storey's plan sits on the sheet.
OFFSET = ((0.0, 0.0), (10.6, 0.0))
SHEET = (-2.3, -4.7, 19.4, 11.5)          # x0, y0, x1, y1
RESOLUTION_X = 2400

COLORS = {
    "sheet": "#171a1f",
    "wall": "#e9e6dd",
    "hall": "#33404d",
    "living": "#3d4a3a",
    "landing": "#33404d",
    "bedroom": "#493f55",
    "kitchen": "#4d4a35",
    "bathroom": "#34504f",
    "void": "#0d0f12",
    "threshold": "#2a333d",
    "window": "#63c2ff",
    "door": "#ffb454",
    "front_door": "#ff5d47",
    "stair": "#aeb6c0",
    "furniture": "#6f7a86",
    "text": "#f3f1ea",
    "dim": "#8c96a3",
    "warm": "#ffcf70",
    "flicker": "#ff8a3d",
    "broken": "#c9517a",
    "moon": "#9fc0ff",
    "baluster": "#d9a066",
}

# Drawing layers: a small z step keeps later layers on top.
Z = {name: i * 0.01 for i, name in enumerate(
    ("floor", "void", "grid", "furniture", "stair", "wall", "glass", "door", "light", "text"))}

_materials = {}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(key):
    if key not in _materials:
        h = COLORS[key].lstrip("#")
        rgb = [srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]
        mat = bpy.data.materials.new(f"plan_{key}")
        mat.diffuse_color = (*rgb, 1.0)
        _materials[key] = mat
    return _materials[key]


def add_mesh(name, verts, faces, color, layer):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, y, Z[layer]) for x, y in verts], [], faces)
    mesh.materials.append(material(color))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def rect(name, x0, y0, x1, y1, color, layer):
    return add_mesh(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [(0, 1, 2, 3)], color, layer)


def line(name, points, width, color, layer, dash=None):
    """A polyline as thin quads. `dash` is (on, off) lengths."""
    verts, faces = [], []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay)
        if length < 1e-6:
            continue
        ux, uy = (bx - ax) / length, (by - ay) / length
        nx, ny = -uy * width / 2, ux * width / 2
        pieces = [(0.0, length)]
        if dash:
            on, off = dash
            pieces, t = [], 0.0
            while t < length:
                pieces.append((t, min(t + on, length)))
                t += on + off
        for s, e in pieces:
            i = len(verts)
            verts += [(ax + ux * s + nx, ay + uy * s + ny), (ax + ux * e + nx, ay + uy * e + ny),
                      (ax + ux * e - nx, ay + uy * e - ny), (ax + ux * s - nx, ay + uy * s - ny)]
            faces.append((i, i + 1, i + 2, i + 3))
    return add_mesh(name, verts, faces, color, layer)


def arc(name, cx, cy, radius, a0, a1, width, color, layer, dash=None):
    steps = max(8, int(abs(a1 - a0) / math.radians(5)))
    points = [(cx + radius * math.cos(a0 + (a1 - a0) * i / steps),
               cy + radius * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
    return line(name, points, width, color, layer, dash)


def disc(name, cx, cy, radius, color, layer, segments=28):
    verts = [(cx + radius * math.cos(2 * math.pi * i / segments),
              cy + radius * math.sin(2 * math.pi * i / segments)) for i in range(segments)]
    return add_mesh(name, verts, [tuple(range(segments))], color, layer)


def arrow(name, x0, y0, x1, y1, width, color, layer, head=0.22):
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    bx, by = x1 - ux * head, y1 - uy * head
    line(name, [(x0, y0), (bx, by)], width, color, layer)
    nx, ny = -uy * head * 0.45, ux * head * 0.45
    add_mesh(name + "_head", [(x1, y1), (bx + nx, by + ny), (bx - nx, by - ny)], [(0, 1, 2)], color, layer)


def text(body, x, y, size, color="text", align="CENTER", rotation=0.0, valign="CENTER"):
    curve = bpy.data.curves.new("label", "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.align_y = valign
    curve.materials.append(material(color))
    obj = bpy.data.objects.new("label_" + body.split("\n")[0][:24], curve)
    obj.location = (x, y, Z["text"])
    obj.rotation_euler = (0, 0, rotation)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --- Plan elements ----------------------------------------------------------

def draw_room(room, ox, oy):
    for i, (x0, y0, x1, y1) in enumerate(room.rects):
        rect(f"room_{room.key}_{i}", ox + x0, oy + y0, ox + x1, oy + y1, room.key, "floor")
    x0, y0, x1, y1 = room.rects[0]
    cx, cy = room.label_at
    narrow = (x1 - x0) < 3.0
    text(room.label, ox + cx, oy + cy, 0.24 if narrow else 0.30)
    if len(room.rects) > 1:
        detail = f"{room.area:.0f} m2"
    elif narrow:
        detail = f"{x1 - x0:.2f} x {y1 - y0:.2f} m\n{room.area:.0f} m2"
    else:
        detail = f"{x1 - x0:.2f} x {y1 - y0:.2f} m   {room.area:.0f} m2"
    text(detail, ox + cx, oy + cy - 0.3, 0.17 if narrow else 0.19, "dim", valign="TOP")


def draw_wall(wall, storey, ox, oy):
    along_x = wall.axis == "x"
    for i, (s, e) in enumerate(plan.solid_spans(wall, storey)):
        if along_x:
            rect(f"{wall.name}_{i}", ox + s, oy + wall.y0, ox + e, oy + wall.y1, "wall", "wall")
        else:
            rect(f"{wall.name}_{i}", ox + wall.x0, oy + s, ox + wall.x1, oy + e, "wall", "wall")

    lo, hi = (wall.y0, wall.y1) if along_x else (wall.x0, wall.x1)
    mid, thick = (lo + hi) / 2, hi - lo

    def pt(a, across):
        """Map (along, across) on this wall to sheet coordinates."""
        return (ox + a, oy + across) if along_x else (ox + across, oy + a)

    for o in plan.openings_on(wall, storey):
        if o.kind != "window":
            # The floor runs through a doorway.
            a, b = pt(o.start, lo), pt(o.end, hi)
            rect(o.name + "_threshold", min(a[0], b[0]), min(a[1], b[1]),
                 max(a[0], b[0]), max(a[1], b[1]), "threshold", "floor")
        if o.kind == "window":
            a, b = pt(o.start, mid - thick * 0.16), pt(o.end, mid + thick * 0.16)
            rect(o.name, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]),
                 "window", "glass")
            for face in (lo, hi):
                line(o.name + "_edge", [pt(o.start, face), pt(o.end, face)], 0.025, "wall", "glass")
        elif o.kind == "opening":
            for face in (lo, hi):
                line(o.name + "_edge", [pt(o.start, face), pt(o.end, face)], 0.03, "wall", "glass",
                     dash=(0.12, 0.10))
        elif o.kind == "door":
            color = "front_door" if o.name == "door_front" else "door"
            face = hi if o.swing == "+" else lo
            sign = 1.0 if o.swing == "+" else -1.0
            hinge_a = o.start if o.hinge == "start" else o.end
            free_a = o.end if o.hinge == "start" else o.start
            hinge, closed_tip = pt(hinge_a, face), pt(free_a, face)
            open_tip = pt(hinge_a, face + sign * o.width)
            line(o.name + "_leaf", [hinge, open_tip], 0.06, color, "door")
            a0 = math.atan2(closed_tip[1] - hinge[1], closed_tip[0] - hinge[0])
            a1 = math.atan2(open_tip[1] - hinge[1], open_tip[0] - hinge[0])
            if a1 - a0 > math.pi:
                a1 -= 2 * math.pi
            if a0 - a1 > math.pi:
                a1 += 2 * math.pi
            arc(o.name + "_swing", hinge[0], hinge[1], o.width, a0, a1, 0.022, color, "door",
                dash=(0.09, 0.07))
            disc(o.name + "_hinge", hinge[0], hinge[1], 0.07, color, "door")
            # threshold
            for f in (lo, hi):
                line(o.name + "_edge", [pt(o.start, f), pt(o.end, f)], 0.02, color, "glass")


def draw_stair(storey, ox, oy):
    x0, x1 = plan.STAIR_X0, plan.STAIR_X1
    # On the first-floor plan only the part of the flight seen through the
    # stairwell is drawn; the lowest treads are under the floor.
    start_y = plan.STAIR_Y0 if storey == 0 else plan.VOID_Y0
    for i in range(plan.RISERS):
        y = plan.STAIR_Y0 + i * plan.TREAD
        if y < start_y - 1e-6:
            continue
        line(f"stair_riser_{i}", [(ox + x0, oy + y), (ox + x1, oy + y)], 0.022, "stair", "stair")
    cx = ox + (x0 + x1) / 2
    line("stair_side", [(ox + x1, oy + start_y), (ox + x1, oy + plan.STAIR_Y1)], 0.022, "stair", "stair")
    # The arrow points the way you walk from this storey: up from the ground
    # floor, down from the first.
    foot, head = oy + start_y + 0.14, oy + plan.STAIR_Y1 - 0.10
    if storey == 1:
        foot, head = head, foot
    disc("stair_start", cx, foot, 0.055, "stair", "stair")
    arrow("stair_arrow", cx, foot, cx, head, 0.03, "stair", "stair")


def draw_storey(storey):
    ox, oy = OFFSET[storey]

    for room in plan.ROOMS:
        if room.storey == storey:
            draw_room(room, ox, oy)

    if storey == 1:
        vx0, vy0, vx1, vy1 = plan.STAIR_VOID
        rect("stair_void", ox + vx0, oy + vy0, ox + vx1, oy + vy1, "void", "void")
    else:
        ux0, uy0, ux1, uy1 = plan.UNDERSTAIR
        line("understair", [(ox + ux1, oy + uy0), (ox + ux1, oy + uy1)], 0.03, "wall", "stair",
             dash=(0.14, 0.10))
        line("understair_front", [(ox + ux0, oy + uy0), (ox + ux1, oy + uy0)], 0.03, "wall", "stair",
             dash=(0.14, 0.10))
        text("cupboard under stair", ox + 1.33, oy + 5.2, 0.13, "dim", rotation=math.pi / 2)

    for s, label, x0, y0, x1, y1 in plan.FURNITURE:
        if s != storey:
            continue
        outline = [(ox + x0, oy + y0), (ox + x1, oy + y0), (ox + x1, oy + y1), (ox + x0, oy + y1),
                   (ox + x0, oy + y0)]
        line("furn_" + label, outline, 0.02, "furniture", "furniture")
        tall = (y1 - y0) > (x1 - x0) * 1.3
        text(label, ox + (x0 + x1) / 2, oy + (y0 + y1) / 2, 0.13, "furniture",
             rotation=math.pi / 2 if tall else 0.0)

    draw_stair(storey, ox, oy)

    for wall in plan.WALLS:
        if wall.on_storey(storey):
            draw_wall(wall, storey, ox, oy)

    for s, points in plan.BALUSTRADES:
        if s == storey:
            line("balustrade", [(ox + x, oy + y) for x, y in points], 0.05, "baluster", "wall")

    for s, kind, x, y, label in plan.LIGHTS:
        if s == storey:
            disc("light_" + label, ox + x, oy + y, 0.13, kind, "light")
            disc("light_core", ox + x, oy + y, 0.05, "sheet", "text", segments=16)

    for s, x, y, dx, dy in plan.MOONLIGHT:
        if s == storey:
            n = math.hypot(dx, dy)
            dx, dy = dx / n, dy / n
            for k in (-0.3, 0.0, 0.3):
                sx, sy = ox + x - dy * k * 1.0 - dx * 0.75, oy + y + dx * k * 1.0 - dy * 0.75
                arrow("moon", sx, sy, sx + dx * 1.7, sy + dy * 1.7, 0.02, "moon", "light", head=0.16)

    # Overall dimensions, outside the walls.
    e = plan.EXT_T
    x0, x1, y0, y1 = ox - e, ox + plan.WIDTH + e, oy - e, oy + plan.DEPTH + e
    line("dim_w", [(x0, y1 + 0.45), (x1, y1 + 0.45)], 0.018, "dim", "text")
    for x in (x0, x1):
        line("dim_tick", [(x, y1 + 0.33), (x, y1 + 0.57)], 0.018, "dim", "text")
    text(f"{x1 - x0:.2f} m", (x0 + x1) / 2, y1 + 0.66, 0.2, "dim")
    line("dim_d", [(x1 + 0.45, y0), (x1 + 0.45, y1)], 0.018, "dim", "text")
    for y in (y0, y1):
        line("dim_tick", [(x1 + 0.33, y), (x1 + 0.57, y)], 0.018, "dim", "text")
    text(f"{y1 - y0:.2f} m", x1 + 0.68, (y0 + y1) / 2, 0.2, "dim", rotation=math.pi / 2)

    title = "GROUND FLOOR" if storey == 0 else "FIRST FLOOR"
    text(title, ox - e, y1 + 1.28, 0.42, align="LEFT")
    text(f"floor level {plan.FFL[storey]:+.2f} m   ceiling {plan.CEILING:.2f} m",
         ox - e + 4.15, y1 + 1.24, 0.2, "dim", align="LEFT")


def draw_annotations():
    ox, oy = OFFSET[0]
    door = next(o for w in plan.WALLS for o in w.openings if o.name == "door_front")
    cx = ox + door.start + door.width / 2
    arrow("street_arrow", cx, oy - 0.55, cx, oy - 1.35, 0.03, "front_door", "text")
    text("FRONT DOOR", cx + 0.25, oy - 0.78, 0.2, "front_door", align="LEFT")
    text("hinged, own object, pivot on the hinge line", cx + 0.25, oy - 1.06, 0.15, "dim", align="LEFT")
    text("STREET", cx, oy - 1.62, 0.26, "front_door")
    text("back door (static)", ox + 1.8, oy + plan.DEPTH + plan.EXT_T + 0.14, 0.13, "door")

    labels = (
        (0, "stair window above", -0.42, 4.75, math.pi / 2, "window"),
        (0, "UP", 0.52, 1.80, 0.0, "stair"),
        (1, "DOWN", 0.55, 7.02, 0.0, "stair"),
        (1, "stair window", -0.42, 4.75, math.pi / 2, "window"),
        (1, "balustrade", 1.34, 5.9, math.pi / 2, "baluster"),
        (0, "fireplace", 7.45, 2.3, math.pi / 2, "sheet"),
    )
    for storey, body, x, y, rot, color in labels:
        sx, sy = OFFSET[storey]
        text(body, sx + x, sy + y, 0.14, color, rotation=rot)

    # North arrow and scale bar.
    nx, ny = SHEET[2] - 0.9, SHEET[3] - 1.35
    arrow("north", nx, ny - 0.45, nx, ny + 0.45, 0.04, "text", "text", head=0.26)
    text("N", nx, ny + 0.68, 0.26)
    bx, by = OFFSET[1][0] + 2.3, -2.05
    for i in range(5):
        rect(f"scale_{i}", bx + i, by, bx + i + 1, by + 0.1, "text" if i % 2 == 0 else "dim", "text")
        text(str(i), bx + i, by - 0.2, 0.15, "dim")
    text("5 m", bx + 5, by - 0.2, 0.15, "dim")

    # Legend.
    lx, ly = SHEET[0] + 0.5, -2.45
    text("KEY", lx, ly + 0.42, 0.2, align="LEFT")
    entries = (
        ("wall", "wall  (ext 0.30, partition 0.14)"), ("window", "window"),
        ("door", "door and swing"), ("front_door", "front door (player opens it)"),
        ("baluster", "balustrade"), ("furniture", "furniture placement guide"),
        ("warm", "warm practical lamp"), ("flicker", "flicker-ready light"),
        ("broken", "broken lamp"), ("moon", "moonlight direction"),
    )
    for i, (color, label) in enumerate(entries):
        col, row = divmod(i, 5)
        x, y = lx + col * 4.6, ly - row * 0.36
        rect("key_" + color, x, y - 0.09, x + 0.42, y + 0.09, color, "text")
        text(label, x + 0.58, y, 0.17, "dim", align="LEFT")

    # Title and build notes.
    text("01 HOUSE INTERIOR", SHEET[0] + 0.5, SHEET[3] - 0.62, 0.52, align="LEFT")
    text("floor plan, revised: kitchen and bathroom   real-world scale, metres",
         SHEET[0] + 7.0, SHEET[3] - 0.66, 0.22, "dim", align="LEFT")
    notes = (
        f"Floor to floor {plan.FLOOR_TO_FLOOR:.2f} m  =  {plan.RISERS} risers x {plan.RISE:.2f}.  "
        f"Doors {plan.DOOR_W:.2f} x {plan.DOOR_H:.2f} m, front door {plan.FRONT_DOOR_W:.2f}.",
        f"Hallway lane beside the stair {plan.HALL_W - plan.VOID_X1:.2f} m.  "
        f"Stair {plan.STAIR_W:.2f} m wide, {plan.STAIR_Y1 - plan.STAIR_Y0:.2f} m run, "
        "with an invisible ramp collider alongside.",
        "The stairwell is open from the hallway up to the first-floor ceiling.",
        "Moon just west of south: light comes through the front and stair windows.",
        "The wall between living room and kitchen stands under the one upstairs; the outer shell is unchanged.",
    )
    for i, body in enumerate(notes):
        text(body, OFFSET[1][0] - 0.3, -2.75 - i * 0.36, 0.17, "dim", align="LEFT")


def setup_render():
    scene = bpy.context.scene
    x0, y0, x1, y1 = SHEET
    width, height = x1 - x0, y1 - y0

    cam_data = bpy.data.cameras.new("plan_camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(width, height)
    cam = bpy.data.objects.new("plan_camera", cam_data)
    cam.location = ((x0 + x1) / 2, (y0 + y1) / 2, 10.0)
    scene.collection.objects.link(cam)
    scene.camera = cam

    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = int(round(RESOLUTION_X * height / width / 2) * 2)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(RENDER)

    # A drawing wants flat, exact colours: Workbench with no lighting, and no
    # filmic tone mapping.
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "MATERIAL"
    shading.show_object_outline = False
    scene.display.render_aa = "16"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    world = bpy.data.worlds.new("plan_world")
    h = COLORS["sheet"].lstrip("#")
    world.color = [srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]
    scene.world = world


def main():
    problems = plan.check()
    if problems:
        raise SystemExit("plan.py has problems:\n  " + "\n  ".join(problems))

    bpy.ops.wm.read_homefile(use_empty=True)
    window = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):
        _materials.clear()
        for storey in (0, 1):
            draw_storey(storey)
        draw_annotations()
        setup_render()

        RENDER.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True, relative_remap=True)
        bpy.ops.render.render(write_still=True)
        print(f"saved  {BLEND}")
        print(f"render {RENDER}")


main()
