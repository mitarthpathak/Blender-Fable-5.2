"""Part 2, layout: draw the town plan from plan.py, top-down, to scale.

Plain Python with matplotlib (no Blender needed):

    python projects/03-town/layout.py          # writes renders/01_town_plan.png
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan  # noqa: E402

OUT = HERE / "renders" / "01_town_plan.png"

C = {
    "sheet": "#15181c", "lawn_kept": "#2f3b2a", "lawn_overgrown": "#34402b", "lawn_dead": "#3d3a2b",
    "road": "#3a3d42", "sidewalk": "#6c6b66", "curb": "#9a978e", "house": "#e9e6dd",
    "player": "#ff5d47", "porch": "#b9a98a", "fence": "#c8c2b0", "chain": "#8aa0ad", "tall": "#d9a066",
    "pole": "#ffcf70", "broken": "#c9517a", "flicker": "#ff8a3d", "wire": "#6d655a",
    "car": "#a0522d", "tree": "#7c8c6c", "text": "#f3f1ea", "dim": "#8c96a3", "walk": "#63c2ff",
    "puddle": "#4d6f8a", "patch": "#2c2f33", "leaf": "#8a6a3a", "marking": "#b8a35a",
}


def rect(ax, r, color, z=1, **kw):
    x0, y0, x1, y1 = r
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=color, edgecolor="none", zorder=z, **kw))


def main() -> None:
    issues = plan.check()
    if issues:
        raise SystemExit("plan.py problems:\n" + "\n".join(issues))
    bx0, by0, bx1, by1 = plan.BUILD
    fig = plt.figure(figsize=(16, 16 * (by1 - by0) / (bx1 - bx0) + 1.2), dpi=150)
    ax = fig.add_axes([0.03, 0.03, 0.94, 0.90])
    ax.set_facecolor(C["sheet"])
    fig.patch.set_facecolor(C["sheet"])
    ax.set_xlim(bx0, bx1)
    ax.set_ylim(by0, by1)
    ax.set_aspect("equal")
    ax.tick_params(colors=C["dim"], labelsize=7)
    for s in ax.spines.values():
        s.set_color(C["dim"])

    # lawns
    rect(ax, plan.BUILD, C["lawn_overgrown"], 0)
    for lot in plan.LOTS:
        rect(ax, lot.rect, C["lawn_" + lot.lawn], 1)
        x0, y0, x1, y1 = lot.rect
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=C["dim"], lw=0.6,
                               ls=(0, (4, 4)), zorder=2))
    # roads and sidewalks
    for st in plan.STREETS:
        rect(ax, st.road, C["road"], 3)
    for _, r in plan.SIDEWALKS:
        rect(ax, r, C["sidewalk"], 3)
    for p in plan.PATCHES:
        rect(ax, p, C["patch"], 4)
    # road markings: faded double yellow on Ashgrove, single on Mill Road, stop line
    ax.plot([bx0, plan.MILL.road[0] - 1], [plan.ASHGROVE.centre + 0.1] * 2, color=C["marking"], lw=0.6, zorder=4)
    ax.plot([bx0, plan.MILL.road[0] - 1], [plan.ASHGROVE.centre - 0.1] * 2, color=C["marking"], lw=0.6, zorder=4)
    ax.plot([plan.MILL.road[2] + 1, bx1], [plan.ASHGROVE.centre + 0.1] * 2, color=C["marking"], lw=0.6, zorder=4)
    ax.plot([plan.MILL.road[2] + 1, bx1], [plan.ASHGROVE.centre - 0.1] * 2, color=C["marking"], lw=0.6, zorder=4)
    ax.plot([plan.MILL.centre] * 2, [by0, plan.ASHGROVE.road[1] - 2], color=C["marking"], lw=0.6,
            ls=(0, (6, 6)), zorder=4)
    x0, x1, y = plan.STOP_LINE
    ax.plot([x0, x1], [y, y], color=C["text"], lw=1.6, alpha=0.6, zorder=4)
    for x, y, r in plan.PUDDLES:
        ax.add_patch(Circle((x, y), r, facecolor=C["puddle"], alpha=0.7, zorder=5))
    for x, y, r in plan.POTHOLES:
        ax.add_patch(Circle((x, y), r, facecolor="#111", zorder=5))
    for x, y in plan.MANHOLES:
        ax.add_patch(Circle((x, y), 0.35, facecolor="#555", edgecolor="#888", lw=0.5, zorder=5))
    for x, y in plan.LEAF_PILES:
        ax.add_patch(Circle((x, y), 0.6, facecolor=C["leaf"], alpha=0.8, zorder=5))

    # the player's house, its porch and path
    rect(ax, plan.HOUSE_FRONT_PATH, C["sidewalk"], 4)
    rect(ax, plan.HOUSE_PORCH, C["porch"], 6)
    rect(ax, plan.HOUSE_BOX, C["player"], 7)
    ax.text((plan.HOUSE_BOX[0] + plan.HOUSE_BOX[2]) / 2, 4.0, "PLAYER'S\nHOUSE\n(enterable)", ha="center",
            va="center", color=C["sheet"], fontsize=8, weight="bold", zorder=8)
    ax.annotate("", xy=(plan.HOUSE_DOOR_X, -0.6), xytext=(plan.HOUSE_DOOR_X, 1.6),
                arrowprops=dict(arrowstyle="-|>", color=C["sheet"], lw=1.5), zorder=9)

    # kit houses
    for lot in plan.HOUSES:
        h = lot.house
        r = plan.house_rect(h)
        rect(ax, r, C["house"], 7)
        (ox, oy), (axx, ayy), (bxx, byy) = plan.house_frame(h)
        # porch on the front
        depth = 2.2 if h.porch != "entry" else 1.6
        p0 = (ox + axx * (0 if h.porch != "entry" else h.door_at - 0.9), oy + ayy * (0 if h.porch != "entry" else h.door_at - 0.9))
        plen = h.width if h.porch != "entry" else 2.8
        corners = [p0, (p0[0] + axx * plen, p0[1] + ayy * plen),
                   (p0[0] + axx * plen - bxx * depth, p0[1] + ayy * plen - byy * depth),
                   (p0[0] - bxx * depth, p0[1] - byy * depth)]
        ax.add_patch(Polygon(corners, facecolor=C["porch"], zorder=6))
        d = (ox + axx * (h.door_at + 0.475), oy + ayy * (h.door_at + 0.475))
        ax.plot(*d, marker="s", color=C["broken"], ms=4, zorder=9)
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        label = f"{lot.key}\n{h.roof.replace('_', ' ')}\n{h.paint}"
        if h.lit:
            label += "\n(lit window)"
        ax.text(cx, cy, label, ha="center", va="center", color=C["sheet"], fontsize=7, zorder=8)
    for lot in plan.LOTS:
        x0, y0, x1, y1 = lot.rect
        ax.text(x0 + 0.5, y1 - 0.6 if y1 < 0 else y1 - 0.8, f"{lot.key}  {lot.address}", color=C["text"],
                fontsize=7, va="top", zorder=10)
        if not lot.house and lot.key != "L1":
            ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 3, "VACANT LOT", color=C["dim"], fontsize=9, ha="center", zorder=10)

    # trees, cars, blockers
    for x, y, hgt, _ in plan.TREES:
        ax.add_patch(Circle((x, y), hgt * 0.28, facecolor="none", edgecolor=C["tree"], lw=0.8, zorder=11))
        ax.add_patch(Circle((x, y), 0.25, facecolor=C["tree"], zorder=11))
    for key, x, y, heading, state in plan.CARS:
        draw_car(ax, x, y, heading, C["car"])
        ax.text(x, y - 2.3, state.replace("_", " "), color=C["dim"], fontsize=6, ha="center", zorder=12)
    for kind, x, y, heading, length in plan.BLOCKERS:
        a = math.radians(heading)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        if kind == "fence_tall":
            ax.plot([x - dx, x + dx], [y - dy, y + dy], color=C["tall"], lw=2.0, zorder=12)
        elif kind in ("barrier", "jersey"):
            ax.plot([x - dx, x + dx], [y - dy, y + dy], color="#e8e2c8", lw=4.0, zorder=12)
        elif kind == "fallen_tree":
            ax.plot([x - dx, x + dx], [y - dy, y + dy], color="#6b5135", lw=5.0, zorder=12)
            ax.text(x + 1.5, y, "fallen tree", color=C["dim"], fontsize=6, zorder=12)
        elif kind == "car_west":
            draw_car(ax, x, y, heading, C["car"])
            ax.text(x, y + 2.3, "crashed", color=C["dim"], fontsize=6, ha="center", zorder=12)
        elif kind == "sign_closed":
            ax.text(x, y + 1.3, "ROAD CLOSED", color="#e8e2c8", fontsize=6, ha="center", zorder=12)

    # fences on the lot fronts
    for lot in plan.LOTS:
        if lot.fence == "none":
            continue
        color = C["chain"] if lot.fence == "chainlink" else C["fence"]
        x0, y0, x1, y1 = lot.rect
        if lot.key in ("L1", "L2", "L3"):
            seg = ((x0, y0 + 0.25), (x1, y0 + 0.25))
        elif lot.key in ("L4", "L5"):
            seg = ((x0, y1 - 0.25), (x1, y1 - 0.25))
        else:
            seg = ((x1 - 0.25, y0), (x1 - 0.25, y1))
        g = lot.gate_at
        horizontal = seg[0][1] == seg[1][1]
        if g is None:
            ax.plot(*zip(*seg), color=color, lw=1.2, zorder=12)
        elif horizontal:
            ax.plot([seg[0][0], g - 0.9], [seg[0][1]] * 2, color=color, lw=1.2, zorder=12)
            ax.plot([g + 0.9, seg[1][0]], [seg[0][1]] * 2, color=color, lw=1.2, zorder=12)
        else:
            ax.plot([seg[0][0]] * 2, [seg[0][1], g - 0.9], color=color, lw=1.2, zorder=12)
            ax.plot([seg[0][0]] * 2, [g + 0.9, seg[1][1]], color=color, lw=1.2, zorder=12)

    # poles, wires, lamps
    poles = {p.key: p for p in plan.POLES}
    for a, b in plan.WIRES:
        ax.plot([poles[a].x, poles[b].x], [poles[a].y, poles[b].y], color=C["wire"], lw=0.8, zorder=13)
    for key, x, y, _ in plan.SERVICE_DROPS:
        ax.plot([poles[key].x, x], [poles[key].y, y], color=C["wire"], lw=0.5, ls=":", zorder=13)
    for p in plan.POLES:
        col = {"on": C["pole"], "broken": C["broken"], "flicker": C["flicker"]}.get(p.lamp, C["dim"])
        if p.lamp in ("on", "flicker"):
            ax.add_patch(Circle((p.x + p.arm[0] * 1.6, p.y + p.arm[1] * 1.6), 6.0, facecolor=col, alpha=0.07, zorder=13))
        ax.plot(p.x, p.y, marker="o", color=col, ms=5, zorder=14)
        ax.text(p.x + 0.5, p.y + 0.4, f"{p.key} {p.lamp}", color=col, fontsize=6, zorder=14)

    for x, y, _ in plan.MAILBOXES:
        ax.plot(x, y, marker="s", color="#c0c8d0", ms=2.5, zorder=14)
    for x, y, _, state in plan.TRASH_CANS:
        ax.plot(x, y, marker="o", color="#7d8a78", ms=3, zorder=14)

    # walkable boundary
    wx0, wy0, wx1, wy1 = plan.WALK
    ax.add_patch(Rectangle((wx0, wy0), wx1 - wx0, wy1 - wy0, fill=False, edgecolor=C["walk"], lw=1.0,
                           ls=(0, (2, 3)), zorder=15))
    ax.text(wx0 + 0.4, wy0 + 0.5, "invisible collision walls", color=C["walk"], fontsize=7, zorder=15)

    # street names
    ax.text(-22, plan.ASHGROVE.centre - 0.25, plan.ASHGROVE.name.upper(), color=C["text"], fontsize=11,
            ha="center", va="center", weight="bold", alpha=0.85, zorder=16)
    ax.text(18, plan.ASHGROVE.centre - 0.25, plan.ASHGROVE.name.upper(), color=C["text"], fontsize=11,
            ha="center", va="center", weight="bold", alpha=0.85, zorder=16)
    ax.text(plan.MILL.centre, -45, plan.MILL.name.upper(), color=C["text"], fontsize=11, rotation=90,
            ha="center", va="center", weight="bold", alpha=0.85, zorder=16)
    # fog visibility ring from the front door
    ax.add_patch(Circle((plan.HOUSE_DOOR_X, -0.6), 25.0, fill=False, edgecolor=C["walk"], lw=0.6, alpha=0.5,
                        ls=(0, (1, 4)), zorder=15))
    ax.text(plan.HOUSE_DOOR_X + 18.5, -18.0, "25 m fog\nvisibility\nfrom the door", color=C["walk"], fontsize=6,
            alpha=0.8, zorder=15)

    # north arrow and scale bar
    ax.annotate("N", xy=(41.5, 20.5), xytext=(41.5, 16.5), color=C["text"], ha="center",
                arrowprops=dict(arrowstyle="-|>", color=C["text"]), fontsize=10, zorder=16)
    ax.plot([30, 40], [-60.5, -60.5], color=C["text"], lw=2, zorder=16)
    ax.text(35, -60.0, "10 m", color=C["text"], fontsize=8, ha="center", zorder=16)

    fig.text(0.03, 0.965, "HALDEN RIDGE  ·  Ashgrove Street and Mill Road", color=C["text"], fontsize=16,
             weight="bold")
    fig.text(0.03, 0.945, "Town plan from projects/03-town/plan.py. Metres; origin at the house's inside SW corner; "
             "+Y north. Red: the player's house (only enterable building).", color=C["dim"], fontsize=9)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=C["sheet"])
    print("wrote", OUT)


def draw_car(ax, x, y, heading, color):
    a = math.radians(heading)
    ca, sa = math.cos(a), math.sin(a)
    L, W = 4.7, 1.8
    pts = []
    for lx, ly in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)):
        pts.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca))
    ax.add_patch(Polygon(pts, facecolor=color, edgecolor="#222", lw=0.5, zorder=12))


if __name__ == "__main__":
    main()
