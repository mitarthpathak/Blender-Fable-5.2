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
            instance(sk.shared("mill_lamp",lambda: sk._lamp_mesh("on")),"streetlamp_M8","poles",(x+0.23,y,z))
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
def notice(mb,x,y,z,w,h,index):
    u=(index%2)*0.5
    v=0.75-(index//2)*0.25
    mb.quad((x+w/2,y,z),(x-w/2,y,z),(x-w/2,y,z+h),(x+w/2,y,z+h),
            "mill_notices",uvs=((u,v),(u+0.5,v),(u+0.5,v+0.25),(u,v+0.25)))


def sign(mb,x,y,width,index):
    z=surface(x,y)
    for dx in (-0.37*width,0.37*width):
        mb.box((x+dx-0.035,y-0.06,z-0.1),(x+dx+0.035,y+0.04,z+1.9),"metal_rust")
    mb.box((x-width/2,y,z+1.12),(x+width/2,y+0.07,z+1.12+width*0.5),"metal_painted")
    notice(mb,x,y+0.073,z+1.12,width,width*0.5,index)


def roadside_stories():
    from . import cars
    mb=MeshBuilder()
    y=-73
    z=GROUND(y)
    # A faded blue timekeeper's cabin, with a clock stopped at twelve past five.
    mb.box((-1.52,y-1,z-0.34),(0.33,y+1,z+2.49),"metal_painted",color=(0.23,0.34,0.35))
    mb.box((-1.65,y-1.17,z+2.49),(0.47,y+1.18,z+2.63),"roof_tin")
    mb.box((-1.38,y+1,z+1.09),(0.17,y+1.04,z+2.17),"interior_dark")
    for xx in (-1.28,-0.58,0.09):
        mb.box((xx,y+1.04,z+1.09),(xx+0.033,y+1.07,z+2.17),"metal_rust")
    notice(mb,-0.59,y+1.015,z+0.49,1.16,0.53,5)
    mb.cylinder((-0.57,y+1.05,z+1.77),(0,0.07,0),0.24,"trim",segments=20)
    for dx,dz in ((0.136,0.046),(-0.065,-0.10)):
        mb.tube([(-0.57,y+1.13,z+1.77),(-0.57+dx,y+1.13,z+1.77+dz)],0.009,"plastic_dark")
    for k in range(10):
        mb.tube([(0.66+0.13*k,y,z+0.68+0.34*k),(0.79+0.13*k,y,z+1.02+0.34*k)],
                0.058,"trim",segments=4,color=(0.68,0.16,0.08) if k%2 else GREY)
    mb.box((0.50,y-0.14,z),(0.80,y+0.14,z+0.84),"metal_painted")
    sign(mb,6.5,-67,2.05,0)
    sign(mb,6.1,-111,1.75,4)
    for i,py in enumerate((-79,-94)):
        notice(mb,-0.62,py+0.16,surface(-0.67,py)+1.36,0.40,0.43,1+i)
    # Roofed bus stop with the timetable still in its case.
    by=-87
    bz=surface(0,by)
    for x in (-1.48,0):
        for dy in (-1.65,1.65):
            mb.box((x-0.05,by+dy-0.05,bz-0.4),(x+0.05,by+dy+0.05,bz+2.29),"metal_rust")
    mb.box((-1.65,by-1.85,bz+2.27),(0.18,by+1.85,bz+2.38),"roof_tin")
    mb.box((-1.45,by-1.62,bz+0.68),(-1.39,by+1.62,bz+2.17),"glass_dirty")
    mb.box((-1.35,by-1.3,bz+0.40),(-0.83,by+1.3,bz+0.49),"wood_weathered")
    mb.box((-1.4,by+1.62,bz+0.91),(-0.09,by+1.68,bz+1.59),"metal_painted")
    notice(mb,-0.745,by+1.69,bz+0.93,1.25,0.63,3)
    for dy in (-1,1):
        mb.box((-1.2,by+dy-0.08,bz-0.2),(-0.99,by+dy+0.08,bz+0.41),"metal_rust")
    mb.build("barrier_mill_checkpoint","props",origin=(1,-81,-1))
    car=cars.build("wagon",(0.20,0.24,0.21),371,"on_blocks","car_mill_dispatch","cars")
    car.location=(2.3,-100,GROUND(-100))
    car.rotation_euler.z=1.34
    traces=MeshBuilder()
    for k in range(13):
        x=3.8+k*0.43
        yy=-98+k*0.19+0.08*((-1)**k)
        traces.card((x,yy,surface(x,yy)+0.014),0.13,0.26,-1.0,"decal_oil",flat=True)
    traces.obox((3.9,-98.5,GROUND(-98.5)+0.062),(0.19,0.09,0.09),0.7,"fabric",color=(0.47,0.17,0.12))
    for k in range(7):
        yy=-92+k*0.30
        traces.obox((7.43,yy,GROUND(yy)+0.14),(0.16,0.25,0.004),0.29*k,"trim",tilt=(0.25,0.46))
    # Rusted two-horn siren looking in opposite directions.
    x,y=7.6,-116
    z=GROUND(y)
    traces.cylinder((x,y,z),(0,0,4.1),0.085,"metal_rust")
    for side in (-1,1):
        traces.cylinder((x,y,z+3.95),(0,side*0.53,0.07),0.065,"metal_painted",radius_top=0.28,caps="none")
    traces.build("detail_mill_traces","props",origin=(3,-102,-2))
