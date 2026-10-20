import bpy, math, random
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="island.blend")
s = bpy.context.scene
R = math.radians
random.seed(9)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def recolor(name, h):
    bpy.data.materials[name].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hexc(h), 1)

def mat(h, rough=0.7):
    m = bpy.data.materials.new(h); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*hexc(h), 1)
    b.inputs["Roughness"].default_value = rough; return m

def ball(loc, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

# meadow turns golden, round trees go orange/red, pines stay evergreen
recolor("#9fd67c", "#d8c86a")   # grass
recolor("#6cbf6a", "#f08a3c")   # leaf
recolor("#8fd47a", "#e5534b")   # leaf2
recolor("#6fc3ee", "#5fb0d8")   # water a touch deeper
for m in bpy.data.materials:     # mountain foothills from green to autumn ochre
    if m.name in ("big", "small", "tiny"):
        cr = next(n for n in m.node_tree.nodes if n.type == 'VALTORGB')
        cr.color_ramp.elements[0].color = (*hexc("#c9b45e"), 1)
s.world.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#f7e3cf"), 1)
sun = next(o for o in s.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
sun.data.color = hexc("#ffd9a8"); sun.data.energy = 3.8

# fallen leaves on the ground and a few drifting in the air
LEAVES = [mat(h) for h in ("#f08a3c", "#e5534b", "#f2c14e", "#c9612c")]
def leaf(x, y, z, tilt):
    bpy.ops.mesh.primitive_circle_add(vertices=6, radius=0.06, fill_type='NGON', location=(x, y, z),
                                      rotation=(tilt, random.uniform(-tilt, tilt), random.uniform(0, 6.3)))
    o = bpy.context.object; o.scale = (1, 0.55, 1); o.data.materials.append(random.choice(LEAVES))
for _ in range(90):
    a = random.uniform(0, math.tau); r = random.uniform(0.6, 3.8)
    x, y = math.cos(a) * r, math.sin(a) * r
    if (Vector((x, y)) - Vector((1.2, -0.3))).length < 1.2: continue  # not on the lake
    leaf(x, y, 0.012, 0)
for _ in range(25):
    leaf(random.uniform(-4, 4), random.uniform(-4, 4), random.uniform(0.6, 3.0), random.uniform(0.3, 1.2))

# pumpkins and a hay bale by the cottage
PUMP = mat("#f08a3c", 0.6); STEMM = mat("#5a7a3a")
for (x, y, r) in [(1.45, 0.75, 0.13), (1.25, 0.82, 0.09), (2.55, 0.8, 0.11)]:
    ball((x, y, r * 0.8), r, PUMP, (1, 1, 0.8))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.015, depth=0.06, location=(x, y, r * 1.6))
    bpy.context.object.data.materials.append(STEMM)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.2, depth=0.3, location=(2.75, 1.7, 0.2), rotation=(R(90), 0, R(20)))
bpy.context.object.data.materials.append(mat("#e9c46a", 0.9))

s.render.filepath = __import__("os").path.abspath("island_autumn.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("island_autumn.blend"))
