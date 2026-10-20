import bpy, math, random
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
R = math.radians
random.seed(3)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def mat(name, h, rough=0.7, emit=0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = emit
    return m

def bevel(o, w):
    m = o.modifiers.new("bevel", 'BEVEL'); m.width = w; m.segments = 3; m.limit_method = 'ANGLE'
    o.modifiers.new("wn", 'WEIGHTED_NORMAL')

def box(loc, size, m, bw=0.03, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(o, bw); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def ball(loc, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=32, ring_count=16)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def cyl(loc, r, d, m, verts=32, rot=(0, 0, 0), bw=0.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object; bevel(o, bw); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

WALL = mat("wall", "#f6d9c8"); WALL2 = mat("wall2", "#efcab6"); FLOOR = mat("floor", "#d8a77c")
FLOOR2 = mat("floor2", "#cc9a70"); WOOD = mat("wood", "#b07a52"); WHITE = mat("white", "#fffaf2")
BLANKET = mat("blanket", "#8fbce6"); PILLOW = mat("pillow", "#ffffff"); RUG = mat("rug", "#f2a7a0", 0.95)
GLOW = mat("glow", "#ffe2a8", 0.3, emit=8); SKY = mat("sky", "#9fd8ff", 0.3, emit=1.5)
LEAF = mat("leaf", "#6cbf6a"); POT = mat("pot", "#e7896b"); BOOK = [mat(f"b{i}", h) for i, h in
    enumerate(["#e56b6f", "#6d9dc5", "#f2c14e", "#7cc69b", "#b48ead"])]
DESK = mat("desk", "#f3e3cf"); SCREEN = mat("screen", "#2b3a55", 0.2); SCREEN_ON = mat("screen_on", "#7fd1ff", 0.3, emit=3)
YELLOW = mat("yellow", "#ffd36b"); CAT = mat("cat", "#f4a259")

S = 4.0  # room size
# floor planks + two walls (open toward camera)
box((0, 0, -0.1), (S, S, 0.2), FLOOR, 0.02)
for i in range(8):
    box((-S / 2 + S / 16 + i * S / 8, 0, 0.002), (S / 8 - 0.02, S - 0.02, 0.01), FLOOR if i % 2 else FLOOR2, 0.004)
box((0, S / 2 + 0.1, 1.5), (S + 0.0, 0.2, 3.2), WALL, 0.02)
box((-S / 2 - 0.1, 0.1, 1.5), (0.2, S + 0.2, 3.2), WALL2, 0.02)
# skirting
box((0, S / 2 - 0.02, 0.07), (S, 0.04, 0.14), WHITE, 0.01)
box((-S / 2 + 0.02, 0, 0.07), (0.04, S, 0.14), WHITE, 0.01)

# window on back wall with sky + curtains
box((0.7, S / 2 - 0.01, 1.85), (1.3, 0.06, 1.1), WHITE, 0.02)
box((0.7, S / 2 - 0.03, 1.85), (1.1, 0.04, 0.9), SKY, 0.0)
box((0.7, S / 2 - 0.06, 1.85), (1.1, 0.03, 0.05), WHITE, 0.01); box((0.7, S / 2 - 0.06, 1.85), (0.05, 0.03, 0.9), WHITE, 0.01)
box((0.7, S / 2 - 0.12, 1.28), (1.45, 0.25, 0.06), WHITE, 0.015)  # sill
CURT = mat("curtain", "#ffd1dc", 0.9)
for sx in (-1, 1):
    for k in range(4):
        cyl((0.7 + sx * (0.72 + k * 0.07), S / 2 - 0.15, 1.75), 0.05, 1.3, CURT, 12)
cyl((0.7, S / 2 - 0.15, 2.45), 0.025, 1.9, WOOD, 12, rot=(0, R(90), 0))

# bed in the left-back corner
bx, by = -1.15, 0.85
box((bx, by, 0.2), (1.4, 2.1, 0.3), WOOD, 0.04)
box((bx, by + 1.0, 0.65), (1.4, 0.12, 1.0), WOOD, 0.05)  # headboard
box((bx, by, 0.45), (1.3, 2.0, 0.25), WHITE, 0.08)  # mattress
box((bx + 0.02, by - 0.25, 0.6), (1.36, 1.45, 0.1), BLANKET, 0.05)
box((bx, by + 0.65, 0.66), (0.9, 0.4, 0.18), PILLOW, 0.08)
# folded throw across the foot of the bed
box((bx, by - 0.7, 0.68), (1.38, 0.35, 0.06), mat("throw", "#f2c14e", 0.9), 0.025)
# nightstand + lamp
nx, ny = -0.12, 1.62
box((nx, ny, 0.3), (0.5, 0.5, 0.6), DESK, 0.03)
box((nx, ny - 0.26, 0.42), (0.35, 0.02, 0.15), WOOD, 0.005)
cyl((nx, ny, 0.65), 0.08, 0.1, WOOD, 16)
cyl((nx, ny, 0.8), 0.015, 0.25, WHITE, 8)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.2, radius2=0.12, depth=0.22, location=(nx, ny, 0.98))
o = bpy.context.object; o.data.materials.append(GLOW); bpy.ops.object.shade_smooth()
bpy.ops.object.light_add(type='POINT', location=(nx, ny, 0.95)); l = bpy.context.object
l.data.energy = 30; l.data.color = hexc("#ffcf88"); l.data.shadow_soft_size = 0.15

# desk on the right side of the back wall with laptop, mug, plant
dx, dy = 1.15, 1.45
box((dx, dy, 0.75), (1.4, 0.7, 0.06), DESK, 0.02)
for sx in (-1, 1):
    for sy in (-1, 1):
        box((dx + sx * 0.62, dy + sy * 0.28, 0.37), (0.06, 0.06, 0.72), WOOD, 0.01)
box((dx - 0.1, dy + 0.05, 0.795), (0.5, 0.35, 0.025), SCREEN, 0.01)  # laptop base
box((dx - 0.1, dy + 0.23, 0.96), (0.5, 0.025, 0.33), SCREEN, 0.01, rot=(R(-12), 0, 0))
box((dx - 0.1, dy + 0.21, 0.96), (0.44, 0.01, 0.27), SCREEN_ON, 0.0, rot=(R(-12), 0, 0))
cyl((dx + 0.35, dy - 0.05, 0.84), 0.06, 0.13, YELLOW, 20)
bpy.ops.mesh.primitive_torus_add(major_radius=0.04, minor_radius=0.012, location=(dx + 0.42, dy - 0.05, 0.85), rotation=(R(90), 0, 0))
bpy.context.object.data.materials.append(YELLOW)
cyl((dx + 0.5, dy + 0.18, 0.86), 0.07, 0.15, POT, 16)
for k in range(6):
    a = k / 6 * math.tau
    ball((dx + 0.5 + math.cos(a) * 0.06, dy + 0.18 + math.sin(a) * 0.06, 1.0), 0.07, LEAF, (0.6, 0.6, 1.4))
# chair
box((dx - 0.1, dy - 0.55, 0.45), (0.5, 0.5, 0.06), mat("chair", "#8fbce6"), 0.03)
box((dx - 0.1, dy - 0.78, 0.75), (0.5, 0.06, 0.55), mat("chair2", "#8fbce6"), 0.03)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl((dx - 0.1 + sx * 0.2, dy - 0.55 + sy * 0.2, 0.21), 0.025, 0.42, WOOD, 8)

# wall shelf with books on the left wall
box((-S / 2 + 0.15, -0.9, 1.75), (0.3, 1.1, 0.05), WOOD, 0.01)
z0 = 1.775
y = -1.38
for i in range(9):
    h = random.uniform(0.2, 0.3); t = random.uniform(0.05, 0.08)
    box((-S / 2 + 0.15, y + t / 2, z0 + h / 2), (0.22, t, h), BOOK[i % 5], 0.008)
    y += t + 0.01
# framed pictures
for (py, pz, w, h, c) in [(0.05, 2.0, 0.6, 0.45, "#7cc69b"), (0.75, 2.15, 0.4, 0.4, "#f2c14e")]:  # clear of the book shelf
    box((-S / 2 + 0.02, py, pz), (0.04, w, h), WOOD, 0.01)
    box((-S / 2 + 0.045, py, pz), (0.02, w - 0.08, h - 0.08), mat("pic" + c, c), 0.0)

# round rug, floor cushion, potted plant in corner
cyl((0.3, -0.5, 0.02), 1.0, 0.03, RUG, 64, bw=0.01)
cyl((0.5, -0.9, 0.1), 0.28, 0.14, mat("cushion", "#ffd36b", 0.9), 32, bw=0.06)
cyl((1.6, -1.55, 0.25), 0.2, 0.5, POT, 20)
for k in range(9):
    a = k / 9 * math.tau
    ball((1.6 + math.cos(a) * 0.12, -1.55 + math.sin(a) * 0.12, 0.65 + (k % 3) * 0.1), 0.13, LEAF, (0.5, 0.5, 1.6))
# string lights along the top of the back wall
import props
props.string_lights([(-S / 2 + 0.2 + i * (S - 0.4) / 14, S / 2 - 0.05, 2.89 - 0.12 * math.sin(i / 14 * math.pi * 2 % math.pi))
                     for i in range(15)],
                    [mat(f"bulb{k}", c, 0.3, emit=10) for k, c in enumerate(("#ffd36b", "#ff9ec4", "#9fd8ff"))],
                    mat("wire", "#3a3530", 0.5), (0, -1, 0), 0.05)

# lighting + camera
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#fde8d7"), 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
bpy.ops.object.light_add(type='AREA', location=(0.7, S / 2 + 1.5, 2.2), rotation=(R(-75), 0, 0))
l = bpy.context.object; l.data.energy = 250; l.data.size = 1.2; l.data.color = hexc("#fff1d6")  # sunlight through window
bpy.ops.object.light_add(type='AREA', location=(4, -4, 5))
l = bpy.context.object; l.data.energy = 600; l.data.size = 5
l.rotation_euler = (Vector((0, 0, 0)) - l.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(12, -12, 10))
cam = bpy.context.object; s.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 7.2
cam.rotation_euler = (Vector((0, 0, 1.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

s.render.engine = 'CYCLES'; s.cycles.samples = 128; s.cycles.use_denoising = True
s.render.resolution_x = s.render.resolution_y = 1000
s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast'
s.render.filepath = __import__("os").path.abspath("room.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("room.blend"))
