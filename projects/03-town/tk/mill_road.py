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


def valley_tree(seed):
    """Thin dead alders, with forked tips and roots visible on the ditch bank."""
    rng=random.Random(798+seed)
    mb=MeshBuilder()
    lean=rng.uniform(-0.7,0.7)
    trunk=[Vector((lean*(i/5)**2,0.13*math.sin(i),i*1.44)) for i in range(6)]
    mb.tube(trunk,0.23,"bark",segments=7,radii=(0.29,0.21,0.16,0.12,0.072,0.025))
    for i in range(5):
        a=i*math.tau/5
        mb.tube([(0,0,0.4),(0.31*math.cos(a),0.31*math.sin(a),0.06),
                 (0.67*math.cos(a),0.67*math.sin(a),-0.09)],0.07,"bark",segments=4,radii=(0.13,0.08,0.016))
    for k in range(12):
        base=trunk[2+k%3]+Vector((0,0,rng.uniform(-0.4,0.55)))
        a=k*2.4+rng.uniform(-0.42,0.42)
        d=Vector((math.cos(a),math.sin(a),rng.uniform(0.48,1.7)))
        elbow=base+d*rng.uniform(0.54,1.35)
        tip=elbow+d*0.56+Vector((0,0,rng.uniform(0.6,1.5)))
        mb.tube([base,elbow,tip],0.07,"bark",segments=5,radii=(0.10,0.06,0.015))
        for j in (-1,1):
            v=Vector((math.cos(a+j*0.65),math.sin(a+j*0.65),rng.uniform(0.7,1.5)))
            mb.tube([elbow,elbow+v*0.6,elbow+v+Vector((0,0,0.3))],0.04,"bark",segments=3,radii=(0.045,0.022,0.005))
    return mb


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
    # Splintered rails still attached to the post and two fallen boards point
    # through the opening. Keep the narrow passage clear of collision.
    for h in (0.61,1.43):
        rail.tube([(6.06,-57.42,plan.GROUND+h),(6.24,-57.62,plan.GROUND+h-0.13),
                   (6.41,-57.83,plan.GROUND+h-0.27)],0.052,"wood_weathered",segments=4,radii=(0.061,0.052,0.009))
    for k in range(2):
        rail.obox((6.02-0.21*k,-58.2,plan.ROAD_Z+0.023),(0.14,1.62,0.038),0.18+0.16*k,"wood_weathered")

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
    forest=[sk.shared(f"valley_tree_{i}",lambda i=i: valley_tree(i)) for i in range(3)]
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
        # The treeline's solid band is the bottom quarter of the card, so each card
        # stands on the ground it is seen against: one along the corridor's banks,
        # one beside the yard (5 m lower than the west bank; standing at the bank's
        # height there it hung in the air with sky under it).
        horizon.card((x,-87.75,surface(x,-99)-1),66.5,17,angle,"backdrop",uvs=((0,0),(1.5,0),(1.5,1),(0,1)))
        horizon.card((x,-142.5,GROUND(-121)-1),43,17,angle,"backdrop",uvs=((0,0),(1,0),(1,1),(0,1)))
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

def iron_letters(mb, caption, x, y, z, size):
    # Convert Blender's built-in lettering once, into the same batched iron mesh.
    font=bpy.data.curves.new("foundry lettering","FONT")
    font.body=caption
    font.size=size
    font.align_x="CENTER"
    font.extrude=0.015
    obj=bpy.data.objects.new("letter pattern",font)
    bpy.context.scene.collection.objects.link(obj)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        pts=[mesh.vertices[i].co for i in tri.vertices]
        mb.face([(x-v.x,y+v.z,z+v.y) for v in pts],"metal_painted",color=(0.65,0.63,0.51))
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.curves.remove(font)


def receiving_yard():
    from . import cars
    rng=random.Random(781)
    z=GROUND(-121)
    floor=MeshBuilder()
    for x in range(-69,69,3):
        for y in range(-139,-121,3):
            mat="concrete" if -9 <= x < 19 else "lawn_dead"
            c=rng.uniform(0.51,0.68)
            floor.quad((x,y,z),(x+3,y,z),(x+3,y+3,z),(x,y+3,z),mat,color=(c,c*0.94,c*0.87))
    floor.build("ground_mill_yard","ground",origin=(4,-130,z))
    gate=MeshBuilder()
    for x in (-9,-5,-1,1.1,6.7,10.8,15,19):
        gate.box((x-0.24,-121.43,z),(x+0.24,-120.95,z+3.25),"brick")
        gate.box((x-0.30,-121.49,z+3.25),(x+0.30,-120.89,z+3.40),"concrete")
    for a,b in ((-9,1.1),(6.7,19)):
        gate.box((a,-121.4,z),(b,-121.0,z+0.60),"brick")
        for h in (0.74,2.25):
            gate.box((a,-121.26,z+h),(b,-121.19,z+h+0.07),"metal_painted")
        for k in range(math.ceil((b-a)/0.22)):
            x=a+k*0.22
            gate.cylinder((x,-121.22,z+0.6),(0,0,1.86),0.023,"metal_rust",segments=4)
    for x,dx,dy in ((1.1,2.70,0.0),(6.7,-0.65,-2.76)):
        for h in (0.19,1.90):
            gate.tube([(x,-121.19,z+h),(x+dx,-121.19+dy,z+h-0.07)],0.045,"metal_painted",segments=4)
        for k in range(13):
            t=k/12
            gate.cylinder((x+t*dx,-121.19+t*dy,z+0.17-0.07*t),(0,0,1.98),0.025,"metal_rust",segments=4)
    for k in range(9):
        a=k*0.072
        gate.tube([(3.76,-121.17,z+1.38-a),(3.80+0.03*(k%2),-121.12,z+1.33-a),
                   (3.76,-121.17,z+1.28-a)],0.013,"metal_rust",segments=4)
    gate.box((0.78,-121.36,z+3.24),(7,-121.12,z+3.93),"metal_painted",color=(0.16,0.20,0.17))
    iron_letters(gate,"H LDEN  MIL S",3.9,-121.08,z+3.36,0.58)
    # Returning wing fences enclose the yard behind the gate.
    for x in (-8.97,18.97):
        gate.box((x-0.10,-137,z),(x+0.10,-121,z+2.24),"brick")
    gate.build("barrier_mill_gate","props",origin=(4,-122,z))
    shed=MeshBuilder()
    shed.box((-7.8,-127,z),(-3.6,-122.8,z+3.15),"brick")
    shed.box((-8,-127.2,z+3.15),(-3.4,-122.6,z+3.42),"roof_tin")
    shed.box((-6.88,-122.79,z+1.02),(-4.35,-122.75,z+2.44),"interior_dark")
    for x in (-6.82,-5.63,-4.4):
        shed.box((x,-122.74,z+1.02),(x+0.048,-122.70,z+2.44),"metal_painted")
    notice(shed,-5.61,-122.74,z+0.44,1.05,0.50,5)
    # Close facade in front of the cheap far mass. Blind openings are deep black.
    shed.box((-12,-138.3,z-0.2),(22,-136.95,z+7.9),"brick",color=(0.68,0.57,0.49))
    shed.box((-12,-137.12,z+7.75),(22,-136.74,z+8.04),"concrete")
    for x in (-5,3,11):
        shed.box((x-2,-136.95,z+0.68),(x+2,-136.88,z+4.2),"interior_dark")
        for k in range(17):
            shed.box((x-1.85,-136.85,z+0.77+k*0.19),(x+1.85,-136.80,z+0.93+k*0.19),"metal_painted",color=GREY)
        shed.box((x-2.5,-136.94,z),(x+2.5,-135.35,z+0.73),"barrier_concrete")
        for dx in (-1.9,1.9):
            shed.box((x+dx-0.12,-135.44,z+0.27),(x+dx+0.12,-135.28,z+0.68),"tyre")
    for i in range(15):
        x=-10+2.15*i
        shed.box((x,-136.94,z+5.0),(x+1.36,-136.84,z+6.78),"interior_dark")
        for dx in (0.03,0.66,1.29):
            shed.box((x+dx,-136.84,z+5.03),(x+dx+0.035,-136.80,z+6.75),"metal_rust")
        shed.box((x,-136.84,z+5.85),(x+1.35,-136.78,z+5.90),"metal_rust")
        shed.quad((x+0.04,-136.82,z+6.73),(x+0.47,-136.82,z+6.73),
                  (x+0.42,-136.82,z+6.34),(x+0.09,-136.82,z+6.12),"glass_dirty")
        if i==8:
            shed.box((x+0.70,-136.84,z+5.03),(x+1.28,-136.80,z+5.82),"window_lit")
    notice(shed,2.9,-136.78,z+4.27,1.57,0.61,7)
    for k in range(7):
        x=14.8+(k%3)*0.67
        y=-133.4+(k//3)*0.69
        shed.cylinder((x,y,z),(0,0,0.88),0.29,"metal_rust",segments=12)
        for h in (0.24,0.62):
            shed.cylinder((x,y,z+h),(0,0,0.03),0.304,"metal_painted",segments=12)
    for k in range(4):
        for dx in (-0.45,0,0.45):
            shed.box((-5+dx,-132,z+k*0.16),(-4.88+dx,-130.8,z+k*0.16+0.09),"wood_weathered")
        for j in range(5):
            shed.box((-5.5,-131.98+j*0.24,z+k*0.16+0.09),(-4.32,-131.78+j*0.24,z+k*0.16+0.15),"wood_weathered")
    shed.build("barrier_mill_receiving","props",origin=(4,-133,z))
    truck=cars.build("pickup",(0.27,0.24,0.17),613,"abandoned","car_mill_delivery","cars")
    truck.location=(10.9,-132.56,z)
    truck.rotation_euler.z=math.pi/2
    cargo=MeshBuilder()
    cargo.box((9.84,-135.17,z+0.7),(11.96,-133.08,z+2.69),"roof_tin",color=(0.62,0.59,0.52))
    notice(cargo,10.89,-133.07,z+1.71,1.25,0.55,6)
    cargo.build("barrier_mill_cargo","props",origin=(10.9,-134,z))
