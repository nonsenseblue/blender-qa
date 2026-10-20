import bpy, math, random
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
R = math.radians
random.seed(5)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

_mats = {}
def mat(h, rough=0.7, emit=0):
    key = (h, rough, emit)
    if key in _mats: return _mats[key]
    m = bpy.data.materials.new(h); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = emit
    _mats[key] = m; return m

def bevel(o, w):
    if w <= 0: return
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

def cone(loc, r1, r2, d, m, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=d, location=loc, rotation=rot)
    o = bpy.context.object; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def text(body, loc, size, m, rot=(R(90), 0, 0), depth=0.02):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.object; o.data.body = body; o.data.size = size; o.data.extrude = depth
    o.data.align_x = 'CENTER'; o.data.align_y = 'CENTER'; o.data.materials.append(m); return o

SIDEWALK = mat("#e4ddd3"); CURB = mat("#c9c1b6"); ROAD = mat("#8d8f99")
WALL = mat("#9ccfc0"); TRIM = mat("#fffaf2"); BRICK = mat("#d98e73"); WOOD = mat("#a8724c")
GLASS = mat("#ffe6b8", 0.2, emit=2.2); DARK = mat("#3d3a4b"); CREAM = mat("#fff3dc")
PINK = mat("#f7a8b8"); YELLOW = mat("#ffd36b"); CHOC = mat("#6b4430"); RED = mat("#e5534b")
LEAF = mat("#6cbf6a"); LEAF2 = mat("#8fd47a"); POT = mat("#e7896b"); METAL = mat("#5a5d6b", 0.4)

# --- ground: sidewalk island with curb and a slice of road ---
box((3.0, 0, -0.2), (12, 6, 0.4), CURB, 0.08)
box((3.3, 0.3, 0.02), (11.4, 5.4, 0.06), SIDEWALK, 0.02)
for i in range(19):  # paving lines
    box((-2.4 + i * 0.6, 0.3, 0.052), (0.015, 5.3, 0.005), CURB, 0)
for i in range(9):
    box((3.3, -2.4 + i * 0.6, 0.052), (11.3, 0.015, 0.005), CURB, 0)

# --- building: L-shaped corner shop, open toward camera (-x, -y faces visible) ---
BX, BY = 0.8, 0.8; W, D, H = 3.2, 3.2, 2.6
box((BX, BY, 0.05 + H / 2), (W, D, H), WALL, 0.04)
box((BX, BY, H + 0.12), (W + 0.12, D + 0.12, 0.14), TRIM, 0.03)  # cornice
box((BX, BY, 0.15), (W + 0.06, D + 0.06, 0.2), BRICK, 0.03)  # base course
fy = BY - D / 2; fx = BX - W / 2  # front (-y) and side (-x) faces

# front: big shop window + door
box((BX + 0.55, fy - 0.03, 1.05), (1.7, 0.08, 1.3), TRIM, 0.03)
box((BX + 0.55, fy - 0.06, 1.05), (1.55, 0.06, 1.15), GLASS, 0.0)
box((BX + 0.55, fy - 0.1, 1.05), (0.04, 0.03, 1.15), TRIM, 0.005)
box((BX + 0.55, fy - 0.25, 0.42), (1.7, 0.4, 0.06), TRIM, 0.02)  # display ledge outside? -> window sill
# cakes on display inside the window (sit just behind the glass, visible through emissive pane edge)
for i, (c, top) in enumerate([(PINK, CREAM), (CHOC, CREAM), (YELLOW, RED)]):
    x = BX - 0.05 + i * 0.6
    cyl((x, fy - 0.3, 0.55), 0.17, 0.2, c, 32, bw=0.03)
    cyl((x, fy - 0.3, 0.67), 0.18, 0.05, top, 32, bw=0.02)
    ball((x, fy - 0.3, 0.73), 0.04, RED)
    cyl((x, fy - 0.3, 0.46), 0.22, 0.02, TRIM, 32, bw=0.005)  # plate
# door
box((BX - 0.95, fy - 0.03, 0.95), (0.8, 0.08, 1.6), TRIM, 0.03)
box((BX - 0.95, fy - 0.07, 0.93), (0.66, 0.06, 1.5), WOOD, 0.02)
box((BX - 0.95, fy - 0.1, 1.15), (0.46, 0.03, 0.75), GLASS, 0.01)
ball((BX - 0.72, fy - 0.12, 0.85), 0.035, YELLOW)
text("OPEN", (BX - 0.95, fy - 0.13, 1.68), 0.13, RED)
box((BX - 0.95, fy - 0.3, 0.09), (0.9, 0.4, 0.08), CURB, 0.02)  # step

# striped awning over the front
def awning(center, length, axis):
    n = 9
    for i in range(n):
        m = RED if i % 2 == 0 else TRIM
        off = -length / 2 + (i + 0.5) * length / n
        if axis == 'x':
            box((center[0] + off, center[1] - 0.35, center[2]), (length / n + 0.002, 0.8, 0.05), m, 0.01, rot=(R(25), 0, 0))
            cyl((center[0] + off, center[1] - 0.7, center[2] - 0.2), 0.06, length / n, m, 16, rot=(0, R(90), 0), bw=0)
        else:
            box((center[0] - 0.35, center[1] + off, center[2]), (0.8, length / n + 0.002, 0.05), m, 0.01, rot=(0, R(-25), 0))
            cyl((center[0] - 0.7, center[1] + off, center[2] - 0.2), 0.06, length / n, m, 16, rot=(R(90), 0, 0), bw=0)
awning((BX, fy, 1.95), W - 0.2, 'x')

# shop sign above the awning
box((BX, fy - 0.04, 2.35), (2.0, 0.08, 0.38), CREAM, 0.04)
text("Café Mochi", (BX, fy - 0.09, 2.35), 0.26, CHOC)

# side face: two arched windows + hanging sign
for wy in (BY - 0.6, BY + 0.6):
    box((fx - 0.03, wy, 1.25), (0.08, 0.75, 1.0), TRIM, 0.03)
    box((fx - 0.06, wy, 1.25), (0.06, 0.62, 0.86), GLASS, 0.0)
    box((fx - 0.1, wy, 1.25), (0.03, 0.04, 0.86), TRIM, 0.005)
    box((fx - 0.15, wy, 0.75), (0.24, 0.8, 0.14), WOOD, 0.02)  # flower box
    for k in range(5):
        ball((fx - 0.15, wy - 0.3 + k * 0.15, 0.86), 0.07, PINK if k % 2 else YELLOW)
box((fx - 0.3, BY - 1.35, 2.2), (0.5, 0.04, 0.04), METAL, 0.01)
cyl((fx - 0.45, BY - 1.35, 1.98), 0.2, 0.05, CREAM, 32, rot=(R(90), 0, 0), bw=0.02)  # round hanging sign, faces -y
text("☕", (fx - 0.45, BY - 1.385, 1.98), 0.2, CHOC) if False else None
cyl((fx - 0.45, BY - 1.38, 1.98), 0.08, 0.02, CHOC, 20, rot=(R(90), 0, 0), bw=0)  # cup icon body
# roof details: AC unit + potted plants + string of lights along cornice
box((BX + 0.8, BY + 0.6, H + 0.4), (0.6, 0.45, 0.4), TRIM, 0.04)
for i in range(12):
    t = i / 11
    ball((fx + 0.05 + t * W, fy - 0.08, H - 0.05 - 0.08 * math.sin(t * math.pi * 3) ** 2), 0.035,
         mat(["#ffd36b", "#ff9ec4", "#9fd8ff"][i % 3], 0.3, emit=8))

# --- outdoor seating: round table, umbrella, two chairs FACING the table ---
tx, ty = -1.3, -1.6
cyl((tx, ty, 0.42), 0.04, 0.75, METAL, 12)
cyl((tx, ty, 0.08), 0.2, 0.03, METAL, 24)
cyl((tx, ty, 0.8), 0.38, 0.04, TRIM, 32)
cyl((tx, ty, 1.35), 0.025, 1.3, TRIM, 8)
cone((tx, ty, 2.0), 0.95, 0.03, 0.4, mat("#9fd8ff"), 16)
cyl((tx + 0.08, ty - 0.05, 0.86), 0.05, 0.09, CREAM, 16)  # coffee cups
cyl((tx - 0.12, ty + 0.06, 0.86), 0.05, 0.09, CREAM, 16)
cyl((tx - 0.02, ty - 0.14, 0.83), 0.1, 0.015, TRIM, 24); cyl((tx - 0.02, ty - 0.14, 0.87), 0.06, 0.06, PINK, 24)
def chair(cx, cy, facing):
    # facing: unit vector from chair toward the table; backrest goes on the opposite side
    fx_, fy_ = facing
    box((cx, cy, 0.45), (0.42, 0.42, 0.05), WOOD, 0.02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl((cx + sx * 0.17, cy + sy * 0.17, 0.22), 0.02, 0.44, METAL, 8, bw=0)
    bx_, by_ = cx - fx_ * 0.2, cy - fy_ * 0.2
    size = (0.04, 0.42, 0.45) if abs(fx_) > abs(fy_) else (0.42, 0.04, 0.45)
    box((bx_, by_, 0.72), size, WOOD, 0.02)
chair(tx - 0.65, ty, (1, 0))
chair(tx + 0.65, ty, (-1, 0))

# --- street stuff: lamp post, planters, menu A-board, bench ---
lx, ly = -2.1, 0.9
cyl((lx, ly, 1.25), 0.05, 2.4, DARK, 12)
cyl((lx, ly, 0.11), 0.14, 0.12, DARK, 16)
cyl((lx, ly, 2.45), 0.14, 0.25, GLASS, 8)
cone((lx, ly, 2.62), 0.2, 0.02, 0.15, DARK, 8)
bpy.ops.object.light_add(type='POINT', location=(lx, ly, 2.4)); l = bpy.context.object
l.data.energy = 25; l.data.color = hexc("#ffcf88")
for px, py in [(fx - 0.35, BY + 1.35)]:
    box((px, py, 0.3), (0.45, 0.45, 0.5), BRICK, 0.04)
    for k in range(7):
        a = k / 7 * math.tau
        ball((px + math.cos(a) * 0.12, py + math.sin(a) * 0.12, 0.65 + (k % 2) * 0.1), 0.16, LEAF if k % 2 else LEAF2)
# A-frame menu board, chalk side facing the camera (-y)
ax_, ay_ = 0.0, -2.0
for sgn in (-1, 1):
    box((ax_, ay_ + sgn * 0.1, 0.42), (0.5, 0.04, 0.8), WOOD, 0.015, rot=(R(sgn * 12), 0, 0))
C = Vector((ax_, ay_ - 0.135, 0.44))
up = Vector((0, math.sin(R(12)), math.cos(R(12)))); nrm = Vector((0, -math.cos(R(12)), math.sin(R(12))))
box(C, (0.4, 0.02, 0.62), DARK, 0.005, rot=(R(-12), 0, 0))
# writing lies flat on the tilted chalkboard face
text("MENU", C + up * 0.18 + nrm * 0.012, 0.09, TRIM, rot=(R(78), 0, 0), depth=0.004)
for k in range(4):
    box(C + up * (0.06 - k * 0.09) + nrm * 0.012, (0.26, 0.004, 0.02), TRIM, 0, rot=(R(-12), 0, 0))
# bicycle-free zone: a little bench along the side wall
box((fx - 0.45, BY + 0.0, 0.42), (0.4, 0.9, 0.06), WOOD, 0.02)
box((fx - 0.27, BY + 0.0, 0.66), (0.05, 0.9, 0.3), WOOD, 0.02)  # backrest against wall side
for sy in (-1, 1):
    box((fx - 0.45, BY + sy * 0.38, 0.2), (0.35, 0.05, 0.4), METAL, 0.01)


# ===== flower shop next door (shares the café's +x wall) =====
PINKW = mat("#f6c1cc"); GREEN = mat("#4f9a72"); STEM = mat("#5aa864")
PETALS = [mat(h) for h in ("#ff7aa2", "#ffd36b", "#ffffff", "#b48ef0", "#ff9e6b", "#e5534b")]
GH = bpy.data.materials.new("greenhouse"); GH.use_nodes = True
_b = GH.node_tree.nodes["Principled BSDF"]; _b.inputs["Base Color"].default_value = (*hexc("#f4fbff"), 1)
_b.inputs["Roughness"].default_value = 0.05; _b.inputs["Transmission Weight"].default_value = 0.9
FX, FY, FW, FD, FH = 3.9, 0.8, 3.0, 3.2, 2.3
box((FX, FY, 0.05 + FH / 2), (FW, FD, FH), PINKW, 0.04)
box((FX, FY, FH + 0.12), (FW + 0.12, FD + 0.12, 0.14), TRIM, 0.03)
box((FX, FY, 0.15), (FW + 0.06, FD + 0.06, 0.2), mat("#e7e1d6"), 0.03)
ffy = FY - FD / 2

def bouquet(x, y, z, r=0.16, n=7):
    for k in range(n):
        a = k / n * math.tau + random.random()
        rr = r * (0.3 + 0.7 * random.random())
        ball((x + math.cos(a) * rr, y + math.sin(a) * rr, z + random.uniform(0, 0.1)), 0.055 + random.uniform(0, 0.02),
             random.choice(PETALS))
    ball((x, y, z - 0.05), r * 0.9, STEM, (1, 1, 0.6))

# shop window with flower display on the sill
box((FX - 0.45, ffy - 0.03, 1.0), (1.6, 0.08, 1.2), TRIM, 0.03)
box((FX - 0.45, ffy - 0.06, 1.0), (1.45, 0.06, 1.05), GLASS, 0.0)
box((FX - 0.45, ffy - 0.25, 0.37), (1.65, 0.4, 0.06), TRIM, 0.02)
for i in range(4):
    x = FX - 1.0 + i * 0.37
    cyl((x, ffy - 0.27, 0.48), 0.1, 0.16, POT, 20)
    bouquet(x, ffy - 0.27, 0.66, 0.11, 6)
# door on the right
box((FX + 0.85, ffy - 0.03, 0.95), (0.8, 0.08, 1.6), TRIM, 0.03)
box((FX + 0.85, ffy - 0.07, 0.93), (0.66, 0.06, 1.5), GREEN, 0.02)
box((FX + 0.85, ffy - 0.1, 1.15), (0.46, 0.03, 0.75), GLASS, 0.01)
ball((FX + 0.62, ffy - 0.12, 0.85), 0.035, YELLOW)
box((FX + 0.85, ffy - 0.3, 0.09), (0.9, 0.4, 0.08), CURB, 0.02)
# flat green awning with a scalloped edge
box((FX, ffy - 0.38, 1.82), (FW - 0.1, 0.8, 0.05), GREEN, 0.01, rot=(R(20), 0, 0))
for i in range(12):
    x = FX - (FW - 0.1) / 2 + (i + 0.5) * (FW - 0.1) / 12
    cyl((x, ffy - 0.76, 1.66), 0.12, 0.04, GREEN if i % 2 == 0 else TRIM, 24, rot=(R(90), 0, 0), bw=0.005)
# sign
box((FX, ffy - 0.04, 2.08), (1.6, 0.08, 0.32), GREEN, 0.04)
text("Flora", (FX, ffy - 0.09, 2.08), 0.24, TRIM)
# rooftop greenhouse: thin non-refracting glass panes around a potting table
_b.inputs["IOR"].default_value = 1.0
gx, gy = FX + 0.3, FY + 0.5
GW_, GD_, GZ0, GZ1 = 1.4, 1.1, FH + 0.2, FH + 1.0
gz = (GZ0 + GZ1) / 2; gh = GZ1 - GZ0
for sy in (-1, 1):
    box((gx, gy + sy * GD_ / 2, gz), (GW_, 0.02, gh), GH, 0.0)
for sx in (-1, 1):
    box((gx + sx * GW_ / 2, gy, gz), (0.02, GD_, gh), GH, 0.0)
box((gx, gy, GZ1 - 0.01), (GW_, GD_, 0.02), GH, 0.0)
for dx_ in (-0.7, 0, 0.7):
    box((gx + dx_, gy - 0.55, gz), (0.04, 0.04, gh), TRIM, 0.005)
    box((gx + dx_, gy + 0.55, gz), (0.04, 0.04, gh), TRIM, 0.005)
box((gx, gy, GZ1 + 0.02), (1.48, 1.18, 0.05), TRIM, 0.01)
# planted greenhouse: two raised beds along the long walls, a path between, a little lemon tree, hanging pots
SOILG = mat("#7a5238", 0.95)
for sy in (-1, 1):
    by_ = gy + sy * 0.38
    box((gx, by_, GZ0 + 0.08), (1.25, 0.26, 0.16), WOOD, 0.01)              # bed frame
    box((gx, by_, GZ0 + 0.165), (1.21, 0.22, 0.01), SOILG, 0.0)              # soil
    for i in range(9):
        x = gx - 0.54 + i * 0.135 + random.uniform(-0.02, 0.02)
        y = by_ + random.uniform(-0.05, 0.05)
        ball((x, y, GZ0 + 0.24), 0.07, LEAF if i % 2 else LEAF2, (1, 1, 1.4))  # leafy clump
        if i % 2 == 0:
            ball((x + 0.02, y, GZ0 + 0.36), 0.035, random.choice(PETALS))      # flower on top
    for i in range(3):  # a few taller stems
        x = gx - 0.4 + i * 0.4
        cyl((x, by_ + 0.04, GZ0 + 0.35), 0.008, 0.3, STEM, 6)
        ball((x, by_ + 0.04, GZ0 + 0.52), 0.05, random.choice(PETALS))
# potted lemon tree at the far end of the path
cyl((gx - 0.52, gy, GZ0 + 0.07), 0.08, 0.14, POT, 16)
cyl((gx - 0.52, gy, GZ0 + 0.3), 0.012, 0.35, WOOD, 6)
ball((gx - 0.52, gy, GZ0 + 0.55), 0.13, LEAF)
for k in range(4):
    a_ = k / 4 * math.tau
    ball((gx - 0.52 + math.cos(a_) * 0.1, gy + math.sin(a_) * 0.1, GZ0 + 0.52), 0.025, YELLOW)
# two pots hanging from the roof with trailing leaves
for hx in (gx + 0.05, gx + 0.4):
    cyl((hx, gy, GZ1 - 0.08), 0.004, 0.14, METAL, 6)
    cone((hx, gy, GZ1 - 0.19), 0.06, 0.04, 0.08, POT, 16)
    ball((hx, gy, GZ1 - 0.14), 0.06, LEAF2)
    for k in range(3):
        ball((hx - 0.04 + k * 0.04, gy, GZ1 - 0.25 - k % 2 * 0.04), 0.022, LEAF)

# tiered flower stand on the pavement, buckets of bouquets
sx0, sy0 = FX + 2.3, ffy - 0.75
for tier in range(3):
    box((sx0, sy0 + tier * 0.25, 0.12 + tier * 0.22), (1.5, 0.28, 0.05), WOOD, 0.01)
    for j in range(4):
        x = sx0 - 0.55 + j * 0.37
        y = sy0 + tier * 0.25
        cyl((x, y, 0.22 + tier * 0.22), 0.09, 0.16, METAL, 16, bw=0.005)
        bouquet(x, y, 0.38 + tier * 0.22, 0.1, 5)
for side in (-1, 1):
    box((sx0 + side * 0.73, sy0 + 0.25, 0.35), (0.05, 0.8, 0.7), WOOD, 0.01)
# watering can
cyl((sx0 - 0.4, sy0 - 0.4, 0.17), 0.1, 0.22, mat("#7fb4e0", 0.4), 20)
cone((sx0 - 0.26, sy0 - 0.4, 0.25), 0.03, 0.015, 0.25, mat("#7fb4e0", 0.4), 12, rot=(0, R(55), 0))
bpy.ops.mesh.primitive_torus_add(major_radius=0.08, minor_radius=0.015, location=(sx0 - 0.48, sy0 - 0.4, 0.3), rotation=(R(90), 0, 0))
bpy.context.object.data.materials.append(mat("#7fb4e0", 0.4))

# street tree in a square planter, and a bench facing the street (backrest on the shop side)
bx2, by2 = 7.1, 1.6
box((bx2, by2, 0.42), (1.2, 0.4, 0.06), WOOD, 0.02)
box((bx2, by2 + 0.18, 0.66), (1.2, 0.05, 0.3), WOOD, 0.02)
for sx in (-1, 1):
    box((bx2 + sx * 0.5, by2, 0.2), (0.05, 0.35, 0.4), METAL, 0.01)
# second street lamp at the far end
lx2, ly2 = 8.4, 0.9
cyl((lx2, ly2, 1.25), 0.05, 2.4, DARK, 12)
cyl((lx2, ly2, 0.11), 0.14, 0.12, DARK, 16)
cyl((lx2, ly2, 2.45), 0.14, 0.25, GLASS, 8)
cone((lx2, ly2, 2.62), 0.2, 0.02, 0.15, DARK, 8)

# --- lighting & camera ---
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#fde7d9"), 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
bpy.ops.object.light_add(type='SUN', rotation=(R(48), R(12), R(-50)))
sun = bpy.context.object; sun.data.energy = 3.2; sun.data.angle = R(6); sun.data.color = hexc("#fff0dc")

bpy.ops.object.camera_add(location=(3.3 - 13, 0.3 - 14, 0.6 + 10.5))
cam = bpy.context.object; s.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 12.2
cam.rotation_euler = (Vector((3.3, 0.3, 0.6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

s.render.engine = 'CYCLES'; s.cycles.samples = 128; s.cycles.use_denoising = True
s.render.resolution_x = 1400; s.render.resolution_y = 1000
s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast'
s.render.filepath = __import__("os").path.abspath("street.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("street.blend"))
