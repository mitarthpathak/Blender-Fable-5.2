"""The county road and receiving yard south of Halden Ridge. Plan coordinates in metres."""
import math
import random

import bpy
from mathutils import Vector
import plan
from . import street_kit as sk
from .core import MeshBuilder, instance, light

GROUND = plan.mill_grade
RUST = (0.51, 0.37, 0.27)
GREY = (0.68, 0.66, 0.59)


def surface(x, y):
    z = GROUND(y)
    if y <= -121:
        return z
    if x < -2:
        return z + min(5, (-2-x)*0.46) - 0.42
    if x > 9:
        return z - min(9, (x-9)*0.64) - 0.36
    ditch = max(0, 1-abs(x+1.6)/0.9) + max(0, 1-abs(x-8.9)/1.0)
    dip = max(0, 1-abs(x-2.0)/1.6) * max(0, 1-abs(y+88)/3)
    return z - 0.34*ditch - 0.09*dip


def road():
    rng = random.Random(3248)
    mesh, marks = MeshBuilder(), MeshBuilder()
    xs = [-80,-22,-10,-5,-2.5,-1.6,-0.7,0,1,2,3.5,5.4,7,8,9,11,19,38,80]
    for north in range(-62,-121,-1):
        for a,b in zip(xs,xs[1:]):
            mat = "road" if 0 <= a < 7 else "road_patch" if -2 <= a < 9 else "lawn_dead"
            if 1 <= a < 3.5 and -90 <= north <= -86:
                mat = "road_patch"
            pts = [(x,y,surface(x,y)) for x,y in ((a,north-1),(b,north-1),(b,north),(a,north))]
            c = rng.uniform(0.72,0.83)
            mesh.face(pts,mat,color=(c,c*0.94,c*0.86))
        if north % 8 < 4 and rng.random() < 0.88:
            for x in (3.4,3.6):
                marks.face([(a,b,surface(a,b)+0.008) for a,b in
                            ((x,north-0.94),(x+0.075,north-0.94),(x+0.075,north),(x,north))],
                           "paint_marking",color=(0.68,0.63,0.52))
    mesh.build("ground_mill_road","ground",origin=(3,-91,-2))
    x=4.1
    for step in range(91):
        y=-68-step*0.49
        nx=x+rng.uniform(-0.2,0.2)
        marks.face([(a,b,surface(a,b)+0.009) for a,b in
                    ((nx,y-0.49),(nx+0.047,y-0.49),(x+0.047,y),(x,y))],"road_patch",color=(0.23,0.21,0.19))
        if step%6==0:
            marks.card((x,y,surface(x,y)),0.25,0.17,rng.random()*3,"weed_card")
        x=nx
    marks.build("detail_mill_asphalt","ground_detail",origin=(3,-88,-2))
    rail=MeshBuilder()
    for y in range(-63,-120,-2):
        if -89 <= y <= -85:
            continue
        def beam_x(t):
            return 7.55 + max(0,1-abs(t+87)/5)*1.6
        z=GROUND(y)
        rail.box((7.51,y-0.06,z-0.16),(7.61,y+0.06,z+0.82),"metal_rust",color=RUST)
        for height in (0.55,0.71):
            rail.tube([(beam_x(y),y,z+height),(beam_x(y-2),y-2,GROUND(y-2)+height)],
                      0.084,"metal_painted",segments=5,color=GREY)
    rail.build("barrier_mill_guardrail","props",origin=(7,-90,-2))
    forest=sk.tree_variants()
    ribbons=MeshBuilder()
    for i in range(64):
        y=-63-i//2*1.83+rng.uniform(-0.55,0.55)
        x=rng.uniform(-15,-3) if i%2 else rng.uniform(10.7,24)
        z=surface(x,y)
        instance(forest[i%3],f"milltree_{i}","trees",(x,y,z),rng.uniform(0,6.28),scale=rng.uniform(0.68,1.02))
        if i%3==0:
            ribbons.cylinder((x,y,z+1.25),(0,0,0.13),0.28,"fabric",segments=8,color=(0.82,0.045,0.019))
            ribbons.tube([(x+0.24,y,z+1.35),(x+0.49,y+0.10,z+1.11),(x+0.54,y+0.25,z+1.02)],
                         0.037,"fabric",segments=3,color=(0.82,0.045,0.019))
    ribbons.build("detail_mill_ribbons","props",origin=(2,-91,-2))
    wires=MeshBuilder()
    last=None
    for i,y in enumerate((-64,-79,-94,-109,-121)):
        x=-0.67
        z=surface(x,y)
        broken=i==3
        if broken:
            wires.cylinder((x,y,z),(0.32,0,3.35),0.16,"bark",segments=8,radius_top=0.095)
        else:
            instance(sk.shared("mill_pole",sk._pole_mesh),f"millpole_{i}","poles",(x,y,z),tilt=(0,0.036))
        top=Vector((x+0.28,y,z+(3.27 if broken else 7.85)))
        if last:
            for off in (-0.8,0.8):
                points=[last.lerp(top,k/10)+Vector((off,0,-1.25*math.sin(math.pi*k/10))) for k in range(11)]
                wires.tube(points,0.016,"wire",segments=3)
        last=top
        if i==2:
            instance(sk.shared("mill_lamp",lambda: sk._lamp_mesh("on")),"streetlamp_M8","poles",(x+0.23,y,z+6.6))
            light("street_sodium_M8_flicker",(x+2,y,z+6.6),"point",200,(1,0.56,0.23))
    wires.build("wires_mill","poles",origin=(0,-92,4))
    horizon=MeshBuilder()
    for x,angle in ((-29,-math.pi/2),(31,math.pi/2)):
        horizon.card((x,-99,surface(x,-99)-1),89,17,angle,"backdrop",uvs=((0,0),(2,0),(2,1),(0,1)))
    horizon.build("backdrop_valley","ground",origin=(3,-98,-2))
    # Move the old road-end tree from the carriageway onto the bank.
    tree=bpy.data.objects.get("edgetree_11")
    if tree:
        tree.location.x=-5.4
