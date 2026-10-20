import bpy, math, random
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
R = math.radians
random.seed(4)

def mat(name, color, rough=0.7, emit=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1); b.inputs["Emission Strength"].default_value = emit
    return m

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

GRASS = mat("grass", hexc("#9fd67c")); DIRT = mat("dirt", hexc("#a8744f")); DIRT2 = mat("dirt2", hexc("#8a5a3c"))
WALL = mat("wall", hexc("#fff3dc")); ROOF = mat("roof", hexc("#ef7f6f")); TRIM = mat("trim", hexc("#ffffff"))
WOOD = mat("wood", hexc("#b9825a")); DOOR = mat("door", hexc("#7fb4e0")); STONE = mat("stone", hexc("#d9d4cc"))
GLOW = mat("glow", hexc("#ffd27a"), 0.3, emit=6); LEAF = mat("leaf", hexc("#6cbf6a")); LEAF2 = mat("leaf2", hexc("#8fd47a"))
TRUNK = mat("trunk", hexc("#8a5a3c")); BRICK = mat("brick", hexc("#c96a5a")); FLOW1 = mat("f1", hexc("#ff9ec4"))
FLOW2 = mat("f2", hexc("#fff07a")); WATER = mat("water", hexc("#8fd0f0"), 0.1); FENCE = mat("fence", hexc("#fffaf0"))

def bevel(o, w=0.04, seg=3):
    m = o.modifiers.new("bevel", 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'
    o.modifiers.new("wn", 'WEIGHTED_NORMAL')

def box(loc, size, m, bw=0.04, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(scale=True); bevel(o, bw); o.data.materials.append(m)
    bpy.ops.object.shade_smooth(); return o

def ball(loc, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def cyl(loc, r, d, m, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object; bevel(o, 0.02); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

# --- island base: grass slab on layered dirt ---
box((0, 0, -0.15), (6, 6, 0.3), GRASS, 0.12)
box((0, 0, -0.55), (5.9, 5.9, 0.5), DIRT, 0.1)
box((0, 0, -0.95), (5.6, 5.6, 0.4), DIRT2, 0.1)

# --- house ---
HX, HY = -0.4, 0.4; W, D, H = 2.4, 2.0, 1.5
box((HX, HY, 0.1), (W + 0.2, D + 0.2, 0.2), STONE, 0.05)  # foundation
box((HX, HY, 0.2 + H / 2), (W, D, H), WALL, 0.05)
# gable roof: two slanted slabs + triangular gable walls
pitch = R(38); half = D / 2 + 0.3; slope = half / math.cos(pitch)
top = 0.2 + H
ridge = top + math.tan(pitch) * D / 2
for sy in (-1, 1):
    box((HX, HY + sy * half / 2, ridge - math.tan(pitch) * half / 2 + 0.1),
        (W + 0.5, slope + 0.1, 0.16), ROOF, 0.06, rot=(-sy * pitch, 0, 0))
# gable walls: triangular prism filling the space between wall top and roof
verts = []
for x in (HX - W / 2, HX + W / 2):
    verts += [(x, HY - D / 2, top), (x, HY + D / 2, top), (x, HY, ridge)]
gm = bpy.data.meshes.new("gable")
gm.from_pydata(verts, [], [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])
g = bpy.data.objects.new("gable", gm); s.collection.objects.link(g); gm.materials.append(WALL)
# round attic window on the visible gable
cyl((HX + W / 2 + 0.03, HY, top + 0.3), 0.17, 0.08, TRIM, 24, rot=(0, R(90), 0))
cyl((HX + W / 2 + 0.06, HY, top + 0.3), 0.12, 0.06, GLOW, 24, rot=(0, R(90), 0))
# chimney
box((HX + 0.7, HY + 0.45, top + 0.8), (0.32, 0.32, 0.9), BRICK, 0.04)
box((HX + 0.7, HY + 0.45, top + 1.27), (0.42, 0.42, 0.1), BRICK, 0.03)
# door (front face = -Y) with frame, knob, step
fy = HY - D / 2
box((HX - 0.45, fy - 0.03, 0.2 + 0.5), (0.62, 0.12, 1.08), TRIM, 0.03)
box((HX - 0.45, fy - 0.07, 0.2 + 0.48), (0.5, 0.1, 0.96), DOOR, 0.03)
ball((HX - 0.27, fy - 0.14, 0.68), 0.04, mat("knob", hexc("#ffd27a"), 0.2))
box((HX - 0.45, fy - 0.3, 0.12), (0.8, 0.4, 0.12), STONE, 0.03)
# glowing windows: front + side, with frames, crossbars and flower boxes
def window(loc, normal_axis):
    x, y, z = loc
    if normal_axis == 'y':
        box((x, y - 0.03, z), (0.62, 0.1, 0.62), TRIM, 0.03)
        box((x, y - 0.06, z), (0.48, 0.08, 0.48), GLOW, 0.01)
        box((x, y - 0.11, z), (0.48, 0.04, 0.05), TRIM, 0.01); box((x, y - 0.11, z), (0.05, 0.04, 0.48), TRIM, 0.01)
        box((x, y - 0.17, z - 0.38), (0.66, 0.2, 0.16), WOOD, 0.03)
        for i in range(5): ball((x - 0.24 + i * 0.12, y - 0.17, z - 0.28), 0.06, FLOW1 if i % 2 else FLOW2)
    else:
        box((x + 0.03, y, z), (0.1, 0.62, 0.62), TRIM, 0.03)
        box((x + 0.06, y, z), (0.08, 0.48, 0.48), GLOW, 0.01)
        box((x + 0.11, y, z), (0.04, 0.48, 0.05), TRIM, 0.01); box((x + 0.11, y, z), (0.04, 0.05, 0.48), TRIM, 0.01)
window((HX + 0.5, fy, 1.05), 'y')
window((HX + W / 2, HY - 0.3, 1.0), 'x')
window((HX + W / 2, HY + 0.5, 1.0), 'x')
# porch lamp
box((HX - 0.95, fy - 0.08, 1.25), (0.14, 0.14, 0.2), GLOW, 0.03)

# --- stepping-stone path to the front edge ---
for i, (px, py) in enumerate([(-0.85, -1.05), (-0.7, -1.55), (-0.85, -2.05), (-0.7, -2.55)]):
    cyl((px, py, 0.02), 0.22 + random.uniform(-0.03, 0.03), 0.06, STONE, 10)

# --- trees ---
def tree(x, y, h=1.0, round_=True):
    cyl((x, y, 0.3 * h), 0.09 * h, 0.6 * h, TRUNK, 10)
    if round_:
        ball((x, y, 0.85 * h), 0.45 * h, LEAF)
        ball((x + 0.18 * h, y - 0.1 * h, 1.15 * h), 0.3 * h, LEAF2)
    else:
        for k, r in enumerate((0.5, 0.38, 0.25)):
            bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=r * h, depth=0.55 * h, location=(x, y, (0.75 + k * 0.32) * h))
            o = bpy.context.object; bevel(o, 0.03); o.data.materials.append(LEAF if k % 2 == 0 else LEAF2)
tree(2.0, 1.7, 1.2); tree(2.3, 0.6, 0.8, False); tree(-2.3, 2.1, 1.0, False); tree(1.6, -2.1, 0.7)

# --- bushes with flowers along the house ---
for bx, by, r in [(-1.85, -0.7, 0.28), (0.85, -0.75, 0.24), (-2.1, 0.3, 0.22)]:
    ball((bx, by, r * 0.6), r, LEAF2, (1, 1, 0.8))
    for k in range(4):
        a = k * 1.6 + random.random()
        ball((bx + math.cos(a) * r * 0.7, by + math.sin(a) * r * 0.7, r * 0.95), 0.05, FLOW1 if k % 2 else FLOW2)

# --- little pond ---
cyl((1.7, -0.6, 0.0), 0.6, 0.04, WATER, 32).scale = (1, 0.7, 1)
for k in range(9):
    a = k / 9 * math.tau
    ball((1.7 + math.cos(a) * 0.66, -0.6 + math.sin(a) * 0.48, 0.03), 0.08 + random.uniform(0, 0.04), STONE, (1, 1, 0.6))

# --- picket fence along the back and left edge ---
def picket(x, y):
    box((x, y, 0.25), (0.08, 0.05, 0.5), FENCE, 0.02)
for i in range(13):
    picket(-2.7 + i * 0.45, 2.75)
for i in range(1, 12):
    picket(-2.75, 2.75 - i * 0.45)
box((0, 2.75, 0.18), (5.5, 0.04, 0.06), FENCE, 0.015); box((0, 2.75, 0.36), (5.5, 0.04, 0.06), FENCE, 0.015)
box((-2.75, 0.3, 0.18), (0.04, 4.9, 0.06), FENCE, 0.015); box((-2.75, 0.3, 0.36), (0.04, 4.9, 0.06), FENCE, 0.015)

# --- mailbox ---
cyl((0.25, -2.4, 0.3), 0.04, 0.6, WOOD, 8)
box((0.25, -2.4, 0.66), (0.2, 0.32, 0.18), mat("mail", hexc("#7fb4e0")), 0.06)

# --- lighting, world, camera ---
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (*hexc("#d6eefa"), 1); bg.inputs[1].default_value = 1.0
bpy.ops.object.light_add(type='SUN', rotation=(R(50), R(10), R(-35)))
sun = bpy.context.object; sun.data.energy = 3.5; sun.data.angle = R(8); sun.data.color = hexc("#fff1dc")
bpy.ops.object.light_add(type='POINT', location=(HX - 0.45, fy - 0.6, 1.2))
bpy.context.object.data.energy = 25; bpy.context.object.data.color = hexc("#ffcf7a")

bpy.ops.object.camera_add(location=(14, -14, 11.5))
cam = bpy.context.object; s.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 10.5
cam.rotation_euler = (Vector((0, 0, 0.3)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

s.render.engine = 'CYCLES'; s.cycles.samples = 96; s.cycles.use_denoising = True
s.render.resolution_x = 1000; s.render.resolution_y = 1000
s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast'
s.render.film_transparent = False
s.render.filepath = __import__("os").path.abspath("house.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("house.blend"))
