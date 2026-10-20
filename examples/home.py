# Cutaway interior of the island villa, one floor per render.
# usage: python home.py -- ground|upper
# Footprint (metres): main block x 0..8, y 0..5.6 (front at y=0, facing -y); wing / balcony x 4.8..8, y -2.2..0.
# Camera looks from the front-right, so the front and right walls are cut low and the back/left walls stay tall.
import bpy, sys, math, random
from mathutils import Vector
FLOOR = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
R = math.radians
random.seed(8)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

_m = {}
def mat(h, rough=0.6, emit=0):
    if (h, rough, emit) in _m: return _m[(h, rough, emit)]
    m = bpy.data.materials.new(h); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = emit
    _m[(h, rough, emit)] = m; return m

# ---------- grouping: every piece of furniture is one group, so overlaps can be checked per item ----------
_cur = []
def item(name):
    g = bpy.data.objects.new(name, None); s.collection.objects.link(g); _cur.append(g); return g
def done():
    _cur.pop()
def _adopt(o):
    if _cur: o.parent = _cur[-1]
    return o

def bevel(o, w):
    if w <= 0: return
    m = o.modifiers.new("bevel", 'BEVEL'); m.width = w; m.segments = 3; m.limit_method = 'ANGLE'
    o.modifiers.new("wn", 'WEIGHTED_NORMAL')

def box(c, size, m, bw=0.02, rz=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=(0, 0, rz))
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(o, bw); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return _adopt(o)

def cyl(c, r, d, m, verts=32, bw=0.01, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=c, rotation=rot)
    o = bpy.context.object; bevel(o, bw); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return _adopt(o)

def ball(c, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=c, segments=24, ring_count=12)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return _adopt(o)

# axis-aligned box from min/max corners: handy for furniture laid out in room coordinates
def slab(x0, y0, z0, x1, y1, z1, m, bw=0.015):
    return box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), m, bw)

# ---------- palette ----------
WALL = mat("#f6efe6", 0.8); WALL_OUT = mat("#fff3dc", 0.8); SAGE = mat("#cfe3d0", 0.8); BLUSH = mat("#f6d9c8", 0.8)
OAK = mat("#d9b48a", 0.6); OAK2 = mat("#cfa77c", 0.6); TILE = mat("#ebe6de", 0.4); BTILE = mat("#d7ecf2", 0.3)
WOOD = mat("#b07a52", 0.6); DARKWOOD = mat("#7a5238", 0.6); WHITE = mat("#fffaf2", 0.5); CHROME = mat("#c9ccd3", 0.2)
DARK = mat("#3d3a4b", 0.5); SOFA = mat("#8fbce6", 0.9); CUSH1 = mat("#ffd36b", 0.9); CUSH2 = mat("#f7a8b8", 0.9)
RUG = mat("#f2c6b4", 0.95); RUG2 = mat("#cfe3d0", 0.95); LEAF = mat("#6cbf6a", 0.7); POT = mat("#e7896b", 0.7)
GLOWW = mat("#ffe2a8", 0.3, emit=6); SCREEN = mat("#7fd1ff", 0.3, emit=2.5); SKY = mat("#cfeaff", 0.3, emit=1.6)
BED = mat("#ffffff", 0.9); DUVET = mat("#a7c7e7", 0.9); BOOKS = [mat(h) for h in ("#e56b6f", "#6d9dc5", "#f2c14e", "#7cc69b", "#b48ead")]
RAIL = mat("#ffffff", 0.5); WATER = mat("#9fd8f5", 0.05)

T = 0.15            # wall thickness
H_FULL, H_CUT, H_OUT = 2.7, 0.95, 0.6   # tall walls, cut partitions, cut exterior walls

def wall_x(y, x0, x1, h, m, gaps=()):     # wall running along x at y
    xs = [x0] + [v for g in gaps for v in g] + [x1]
    for a, b in zip(xs[::2], xs[1::2]):
        if b - a > 0.01: slab(a, y - T / 2, 0, b, y + T / 2, h, m, 0.01)
def wall_y(x, y0, y1, h, m, gaps=()):     # wall running along y at x
    ys = [y0] + [v for g in gaps for v in g] + [y1]
    for a, b in zip(ys[::2], ys[1::2]):
        if b - a > 0.01: slab(x - T / 2, a, 0, x + T / 2, b, h - 0.003, m, 0.01)  # offset tops so corners don't z-fight
# Things hung on the two tall walls are described in wall coordinates (u along the wall, v = height, d = distance out).
WALLS = {"back": 5.6 - T / 2, "left": T / 2}
def slab_w(wall, u0, v0, u1, v1, d0, d1, m, bw=0.004):
    if wall == "back":
        p = WALLS["back"]; return slab(u0, p - d1, v0, u1, p - d0, v1, m, bw)
    p = WALLS["left"]; return slab(p + d0, u0, v0, p + d1, u1, v1, m, bw)
def disc_w(wall, u, v, r, d, m):
    if wall == "back":
        return cyl((u, WALLS["back"] - d, v), r, 0.004, m, 32, 0, rot=(R(90), 0, 0))
    return cyl((WALLS["left"] + d, u, v), r, 0.004, m, 32, 0, rot=(0, R(90), 0))
def poly_w(wall, pts, d, m):
    vs = [((u, WALLS["back"] - d, v) if wall == "back" else (WALLS["left"] + d, u, v)) for u, v in pts]
    me = bpy.data.meshes.new("poly"); me.from_pydata(vs, [], [list(range(len(vs)))])
    o = bpy.data.objects.new("poly", me); s.collection.objects.link(o); me.materials.append(m); return _adopt(o)

GLASS = mat("#bfe3f7", 0.1, emit=1.3); FRAMEW = mat("#ffffff", 0.4); CURTAIN = mat("#f7d6c9", 0.95)
def window(wall, c, w, z, h, curtains=False):
    u0, u1, v0, v1 = c - w / 2, c + w / 2, z - h / 2, z + h / 2
    f = 0.05
    slab_w(wall, u0, v0, u1, v1, 0.0, 0.01, GLASS, 0)                       # glass, set into the wall
    for a_ in ((u0 - f, v0 - f, u0, v1 + f), (u1, v0 - f, u1 + f, v1 + f), (u0, v0 - f, u1, v0), (u0, v1, u1, v1 + f)):
        slab_w(wall, *a_, 0.0, 0.05, FRAMEW)                                 # frame
    slab_w(wall, c - 0.015, v0, c + 0.015, v1, 0.0, 0.035, FRAMEW, 0)       # mullions (different depths: no z-fight)
    slab_w(wall, u0, (v0 + v1) / 2 - 0.015, c - 0.015, (v0 + v1) / 2 + 0.015, 0.0, 0.03, FRAMEW, 0)
    slab_w(wall, c + 0.015, (v0 + v1) / 2 - 0.015, u1, (v0 + v1) / 2 + 0.015, 0.0, 0.03, FRAMEW, 0)
    slab_w(wall, u0 - 0.1, v0 - f - 0.04, u1 + 0.1, v0 - f, 0.0, 0.11, FRAMEW)   # sill
    if curtains:
        slab_w(wall, u0 - 0.35, v1 + 0.12, u1 + 0.35, v1 + 0.15, 0.0, 0.12, DARKWOOD)   # rod on its bracket
        for side in (-1, 1):
            uc = (u0 - 0.2) if side < 0 else (u1 + 0.2)
            for k in range(3):                                              # soft gathered panel
                slab_w(wall, uc - 0.13 + k * 0.09, v0 - 0.15, uc - 0.05 + k * 0.09, v1 + 0.12, 0.04 + (k % 2) * 0.02, 0.1 + (k % 2) * 0.02, CURTAIN, 0.02)

ART = {"sky": mat("#cfe8f5", 0.8), "sun": mat("#ffd36b", 0.8), "mtn": mat("#7cc69b", 0.8), "mtn2": mat("#4f9a72", 0.8),
       "snow": mat("#ffffff", 0.8), "cream": mat("#f7efe2", 0.8), "leaf": mat("#6cbf6a", 0.8), "leaf2": mat("#9fd67c", 0.8),
       "pink": mat("#f7a8b8", 0.8), "stem": mat("#4f9a72", 0.8)}
def framed_art(wall, c, z, w, h, kind):
    u0, u1, v0, v1 = c - w / 2, c + w / 2, z - h / 2, z + h / 2
    slab_w(wall, u0, v0, u1, v1, 0.0, 0.03, mat("#b9825a", 0.5), 0.006)    # wooden frame
    m = 0.03
    slab_w(wall, u0 + m, v0 + m, u1 - m, v1 - m, 0.03, 0.033, mat("#fffaf2", 0.7), 0)   # white mount
    a0, a1, b0, b1 = u0 + m + 0.05, u1 - m - 0.05, v0 + m + 0.05, v1 - m - 0.05
    if kind == "mountains":
        slab_w(wall, a0, b0, a1, b1, 0.033, 0.036, ART["sky"], 0)
        disc_w(wall, a1 - (a1 - a0) * 0.22, b1 - (b1 - b0) * 0.25, min(a1 - a0, b1 - b0) * 0.12, 0.038, ART["sun"])
        W, H = a1 - a0, b1 - b0
        poly_w(wall, [(a0, b0), (a0 + W * 0.62, b0), (a0 + W * 0.32, b0 + H * 0.72)], 0.039, ART["mtn"])
        poly_w(wall, [(a0 + W * 0.25, b0), (a1, b0), (a0 + W * 0.68, b0 + H * 0.58)], 0.040, ART["mtn2"])
        poly_w(wall, [(a0 + W * 0.25, b0 + H * 0.55), (a0 + W * 0.39, b0 + H * 0.55), (a0 + W * 0.32, b0 + H * 0.72)], 0.041, ART["snow"])
    elif kind == "leaf":
        slab_w(wall, a0, b0, a1, b1, 0.033, 0.036, ART["cream"], 0)
        cu, W, H = (a0 + a1) / 2, a1 - a0, b1 - b0
        slab_w(wall, cu - 0.006, b0 + H * 0.08, cu + 0.006, b0 + H * 0.85, 0.036, 0.039, ART["stem"], 0)
        for k in range(3):                                                  # pairs of leaves along the stem
            vv = b0 + H * (0.3 + k * 0.2); sz = W * (0.32 - k * 0.06)
            poly_w(wall, [(cu, vv), (cu - sz, vv + sz * 0.35), (cu - sz * 0.5, vv + sz * 0.75)], 0.04 + k * 0.003, ART["leaf"])
            poly_w(wall, [(cu, vv), (cu + sz, vv + sz * 0.35), (cu + sz * 0.5, vv + sz * 0.75)], 0.0415 + k * 0.003, ART["leaf2"])  # one layer per leaf
    else:  # "dots": soft abstract circles
        slab_w(wall, a0, b0, a1, b1, 0.033, 0.036, ART["cream"], 0)
        W, H = a1 - a0, b1 - b0
        for i, (fu, fv, fr, col) in enumerate([(0.3, 0.6, 0.22, "pink"), (0.62, 0.42, 0.28, "sky"), (0.72, 0.75, 0.12, "sun"), (0.25, 0.25, 0.12, "leaf2")]):
            disc_w(wall, a0 + W * fu, b0 + H * fv, min(W, H) * fr, 0.038 + i * 0.002, ART[col])   # each disc on its own layer

def plant(x, y, h=0.9, r=0.18):
    # pot with soil; leaves grow out of the soil on short stems, so nothing hovers above the rim
    cyl((x, y, 0.15), r * 0.8, 0.3, POT, 20)
    cyl((x, y, 0.28), r * 0.72, 0.02, mat("#7a5238", 0.95), 20, 0)   # soil top just below the rim
    hz = r * 0.55 * 1.6                       # half height of a leaf
    for k in range(5):
        a = k / 5 * math.tau
        lx, ly = x + math.cos(a) * r * 0.35, y + math.sin(a) * r * 0.35
        cz = 0.3 + hz * 0.75 + h * 0.12 * (k % 3)
        cyl((lx, ly, (0.29 + cz) / 2), 0.012, cz - 0.29, mat("#4f9a72", 0.7), 6, 0)
        ball((lx, ly, cz), r * 0.55, LEAF, (0.7, 0.7, 1.6))
    cz = 0.3 + hz * 0.9 + h * 0.22
    cyl((x, y, (0.29 + cz) / 2), 0.014, cz - 0.29, mat("#4f9a72", 0.7), 6, 0)
    ball((x, y, cz), r * 0.5, LEAF, (0.7, 0.7, 1.7))

def faucet(x, y, z, dx, dy):
    # upright stem standing on the surface at z, with a spout reaching over the basin in direction (dx, dy)
    cyl((x, y, z + 0.085), 0.016, 0.17, CHROME, 12, 0.003)                  # stem top tucked under the spout
    if dx: slab(min(x, x + dx * 0.14), y - 0.012, z + 0.155, max(x, x + dx * 0.14), y + 0.012, z + 0.18, CHROME, 0.004)
    else:  slab(x - 0.012, min(y, y + dy * 0.14), z + 0.155, x + 0.012, max(y, y + dy * 0.14), z + 0.18, CHROME, 0.004)
    cyl((x + dx * 0.13, y + dy * 0.13, z + 0.145), 0.014, 0.03, CHROME, 12, 0.002)

def basin(x0, y0, x1, y1, z0, z1, m, wall=0.02):
    # an open, hollow basin: floor, four walls and a drain, so it reads as a bowl you can pour water into
    # pieces butt together without sharing faces, so no z-fighting seams
    slab(x0 + wall, y0 + wall, z0, x1 - wall, y1 - wall, z0 + wall, m, 0)          # floor
    slab(x0, y0, z0, x1, y0 + wall, z1, m, 0); slab(x0, y1 - wall, z0, x1, y1, z1, m, 0)   # front / back
    slab(x0, y0 + wall, z0, x0 + wall, y1 - wall, z1, m, 0); slab(x1 - wall, y0 + wall, z0, x1, y1 - wall, z1, m, 0)
    cyl(((x0 + x1) / 2, (y0 + y1) / 2, z0 + wall + 0.002), 0.025, 0.004, DARK, 16, 0)

def toilet(cx, cy, face):
    # cistern on the wall behind, pedestal + oval bowl, seat ring, lid raised against the cistern
    along_x = face in ('+x', '-x'); sgn = 1 if face in ('+x', '+y') else -1
    stretch = (1.35, 1, 1) if along_x else (1, 1.35, 1)
    ped = cyl((cx, cy, 0.11), 0.12, 0.22, WHITE, 32, 0.02); ped.scale = stretch
    bowl = cyl((cx, cy, 0.31), 0.18, 0.18, WHITE, 32, 0.03); bowl.scale = stretch
    bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.022, location=(cx, cy, 0.415))
    seat = _adopt(bpy.context.object); seat.scale = stretch; seat.data.materials.append(WHITE)
    back = 0.24 - 0.02            # bowl edge on the cistern side
    if along_x:
        wx = cx - sgn * back
        slab(min(wx, wx - sgn * 0.26), cy - 0.2, 0, max(wx, wx - sgn * 0.26), cy + 0.2, 0.75, WHITE, 0.03)   # cistern
        slab(min(wx, wx + sgn * 0.03), cy - 0.16, 0.42, max(wx, wx + sgn * 0.03), cy + 0.16, 0.8, WHITE, 0.02)  # lid up
        cyl((wx - sgn * 0.13, cy, 0.76), 0.03, 0.02, CHROME, 16, 0)
    else:
        wy = cy - sgn * back
        slab(cx - 0.2, min(wy, wy - sgn * 0.26), 0, cx + 0.2, max(wy, wy - sgn * 0.26), 0.75, WHITE, 0.03)
        slab(cx - 0.16, min(wy, wy + sgn * 0.03), 0.42, cx + 0.16, max(wy, wy + sgn * 0.03), 0.8, WHITE, 0.02)
        cyl((cx, wy - sgn * 0.13, 0.76), 0.03, 0.02, CHROME, 16, 0)

def chair(x, y, face, m=WOOD, seat=None):
    # face: direction the sitter looks ('+x','-x','+y','-y'); the backrest goes on the opposite side
    seat = seat or m
    slab(x - 0.22, y - 0.22, 0.42, x + 0.22, y + 0.22, 0.47, seat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            slab(x + sx * 0.18 - 0.02, y + sy * 0.18 - 0.02, 0, x + sx * 0.18 + 0.02, y + sy * 0.18 + 0.02, 0.42, m, 0.004)
    d = {'+x': (-1, 0), '-x': (1, 0), '+y': (0, -1), '-y': (0, 1)}[face]
    bx, by = x + d[0] * 0.2, y + d[1] * 0.2
    if d[0]: slab(bx - 0.02, y - 0.22, 0.47, bx + 0.02, y + 0.22, 0.9, m)
    else:    slab(x - 0.22, by - 0.02, 0.47, x + 0.22, by + 0.02, 0.9, m)

# ======================================================================================
def ground_floor():
    item("floor")
    slab(0, 0, -0.2, 8, 5.6, 0, OAK, 0.01)
    slab(4.8, -2.2, -0.2, 8, 0, 0, OAK, 0.01)
    slab(3.4, 2.75, 0.0, 7.93, 5.53, 0.006, TILE, 0)          # kitchen tiles
    slab(1.48, 3.93, 0.0, 3.22, 5.53, 0.006, BTILE, 0)        # WC tiles
    done()

    item("walls")
    wall_x(5.6, 0, 8, H_FULL, WALL)                            # back (tall)
    wall_y(0, 0, 5.6, H_FULL, WALL)                            # left (tall)
    wall_x(0, 0, 4.8, H_OUT, WALL, gaps=[(1.8, 2.6)])          # front of main block, front door gap
    wall_y(8, -2.2, 5.6, H_OUT, WALL)                          # right side incl. wing
    wall_x(-2.2, 4.8, 8, H_OUT, WALL)                          # wing front
    wall_y(4.8, -2.2, 0, H_OUT, WALL)                          # wing left
    wall_y(1.4, 3.3, 5.6, H_CUT, WALL)                         # stairs | WC
    wall_x(3.85, 1.4, 3.3, H_CUT, WALL, gaps=[(1.95, 2.75)])   # WC front with door
    wall_y(3.3, 3.85, 5.6, H_CUT, WALL)                        # WC | kitchen
    window("back", 6.0, 0.8, 1.6, 0.8); window("back", 2.3, 0.6, 1.75, 0.5)
    window("left", 2.75, 0.6, 1.5, 1.0)
    done()

    # ---- living room (front left): TV on the tall left wall, sofa facing it with its back to the room ----
    item("rug"); slab(0.75, 0.6, 0, 3.2, 2.6, 0.012, RUG, 0.005); done()
    item("tv_unit")
    slab(0.12, 1.0, 0, 0.55, 2.2, 0.45, WHITE)                               # console against the wall
    for i in range(2):
        slab(0.55, 1.05 + i * 0.58, 0.06, 0.565, 1.57 + i * 0.58, 0.4, mat("#9ccfc0", 0.5), 0.004)
    slab(0.2, 1.5, 0.45, 0.4, 1.7, 0.48, DARK, 0.005)                        # TV foot
    slab(0.27, 1.57, 0.48, 0.31, 1.63, 0.56, DARK, 0.004)
    slab(0.25, 1.0, 0.56, 0.31, 2.2, 1.22, DARK, 0.01)                       # TV, screen faces +x toward the sofa
    slab(0.31, 1.04, 0.6, 0.315, 2.16, 1.18, SCREEN, 0)
    done()
    item("sofa")
    slab(2.65, 0.6, 0.0, 3.55, 2.6, 0.42, SOFA, 0.06)                        # base + seat
    slab(3.33, 0.6, 0.42, 3.55, 2.6, 0.85, SOFA, 0.06)                       # backrest toward the room
    slab(2.65, 0.6, 0.42, 3.33, 0.78, 0.62, SOFA, 0.05)                      # arms
    slab(2.65, 2.42, 0.42, 3.33, 2.6, 0.62, SOFA, 0.05)
    box((3.25, 1.15, 0.58), (0.15, 0.38, 0.32), CUSH1, 0.06)                 # cushions on the seat against the back
    box((3.25, 2.05, 0.58), (0.15, 0.38, 0.32), CUSH2, 0.06)
    done()
    item("coffee_table")
    slab(1.3, 1.25, 0.36, 2.2, 1.95, 0.41, WOOD)
    for sx in (1.37, 2.13):
        for sy in (1.32, 1.88):
            slab(sx - 0.025, sy - 0.025, 0, sx + 0.025, sy + 0.025, 0.36, DARKWOOD, 0.004)
    cyl((1.55, 1.6, 0.46), 0.05, 0.1, CUSH2, 16)                              # mug
    slab(1.8, 1.45, 0.41, 2.1, 1.75, 0.44, BOOKS[1], 0.005)                   # magazines
    done()
    item("art_living"); framed_art("left", 1.6, 1.75, 1.0, 0.6, "dots"); done()
    item("floor_lamp")
    cyl((3.3, 0.33, 0.02), 0.14, 0.04, DARK, 24); cyl((3.3, 0.33, 0.77), 0.015, 1.46, DARK, 8)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.2, radius2=0.12, depth=0.25, location=(3.3, 0.33, 1.6))
    o = bpy.context.object; o.data.materials.append(GLOWW); _adopt(o)
    done()
    item("plant_living"); plant(3.55, 2.95); done()               # clear of the foot of the stairs
    item("shoe_bench"); slab(1.0, 0.12, 0, 1.72, 0.47, 0.45, OAK2); done()
    item("door_mat"); slab(1.9, 0.12, 0, 2.5, 0.55, 0.012, mat("#c96a5a", 0.95), 0.005); done()

    # ---- stairs (back left), rising toward the back wall ----
    item("stairs")
    n = 12
    for i in range(n):
        y0 = 3.35 + i * 0.18
        slab(0.12, y0, 0, 1.3, min(y0 + 0.18, 5.52), (i + 1) * 0.215, OAK2, 0.005)
    done()

    # ---- WC ----
    item("toilet_wc")
    toilet(2.3, 5.04, '-y')                                                   # cistern back flush with the wall
    done()
    item("wc_sink")
    basin(2.94, 4.35, 3.15, 4.85, 0.72, 0.85, WHITE, 0.025)                 # wall-hung basin
    slab(3.15, 4.35, 0.72, 3.222, 4.85, 0.85, WHITE, 0.01)                  # back deck fixed to the wall
    faucet(3.19, 4.6, 0.85, -1, 0)
    done()

    # ---- kitchen (back right): fridge, back counter with hob, side counter with sink, island ----
    item("fridge"); slab(3.45, 4.88, 0, 4.12, 5.52, 1.9, WHITE, 0.03)
    slab(3.47, 4.875, 0.68, 4.1, 4.88, 0.7, mat("#c9ccd3", 0.4), 0)          # seam between fridge door and freezer drawer
    slab(3.52, 4.855, 0.95, 3.55, 4.875, 1.45, CHROME, 0.004)                # door handle
    slab(3.6, 4.855, 0.55, 3.97, 4.875, 0.58, CHROME, 0.004)                 # drawer handle
    done()
    item("counter_back")
    slab(4.2, 4.9, 0, 7.92, 5.52, 0.88, WHITE, 0.01)
    slab(4.18, 4.88, 0.88, 7.92, 5.52, 0.92, OAK2, 0.005)                     # worktop
    for i in range(6):
        slab(4.25 + i * 0.6, 4.885, 0.1, 4.8 + i * 0.6, 4.9, 0.8, mat("#9ccfc0", 0.5), 0.004)  # door fronts
    done()
    item("hob")                                                              # black glass hob, four burner rings, knobs, a pot
    slab(6.58, 4.95, 0.92, 7.32, 5.45, 0.935, mat("#1d1c22", 0.15), 0.004)
    for bx_ in (6.77, 7.13):
        for by_ in (5.07, 5.33):
            bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.008, location=(bx_, by_, 0.938))
            o = bpy.context.object; o.data.materials.append(CHROME); _adopt(o)
    for i in range(4):
        cyl((6.68 + i * 0.18, 4.87, 0.82), 0.022, 0.025, DARK, 16, 0.002, rot=(R(90), 0, 0))
    cyl((6.77, 5.07, 1.0), 0.09, 0.12, mat("#e5534b", 0.4), 24, 0.01)        # little red pot
    slab(6.64, 5.06, 1.03, 6.69, 5.08, 1.045, DARK, 0.003)
    item("counter_back_rest")
    slab(6.6, 5.3, 1.6, 7.3, 5.52, 1.85, CHROME, 0.01)                        # hood canopy
    slab(6.85, 5.36, 1.85, 7.05, 5.52, 2.6, CHROME, 0.006)                    # its chimney up the wall
    slab(4.2, 5.17, 1.55, 5.4, 5.52, 2.25, mat("#9ccfc0", 0.5), 0.01)        # wall cabinets (window to their right)
    slab(4.79, 5.165, 1.57, 4.81, 5.17, 2.23, mat("#7fb3a3", 0.5), 0)         # door seam
    for hx in (4.72, 4.88):
        slab(hx - 0.01, 5.15, 1.6, hx + 0.01, 5.165, 1.75, CHROME, 0.003)    # handles
    cyl((5.0, 5.2, 1.0), 0.1, 0.16, CUSH1, 20); cyl((5.3, 5.2, 0.98), 0.07, 0.12, CUSH2, 20)  # canisters
    done()
    item("counter_side")
    SX0, SY0, SX1, SY1 = 7.42, 3.75, 7.78, 4.3                               # sink opening
    for a in ((7.3, 3.2, 7.92, SY0), (7.3, SY1, 7.92, 4.86), (7.3, SY0, SX0, SY1), (SX1, SY0, 7.92, SY1)):
        slab(a[0], a[1], 0, a[2], a[3], 0.88, WHITE, 0.01)                   # cabinet around the sink
        slab(a[0] - (0.02 if a[0] == 7.3 else 0), a[1], 0.88, a[2], a[3], 0.92, OAK2, 0.005)   # worktop with a hole
    slab(SX0, SY0, 0, SX1, SY1, 0.68, WHITE, 0.01)                           # cupboard under the sink
    basin(SX0, SY0, SX1, SY1, 0.7, 0.92, CHROME, 0.015)                      # recessed steel sink
    faucet(7.85, 4.02, 0.92, -1, 0)
    for i in range(2):
        slab(7.285, 3.25 + i * 0.8, 0.1, 7.3, 3.95 + i * 0.8, 0.8, mat("#9ccfc0", 0.5), 0.004)
    done()
    item("island")
    slab(4.7, 3.2, 0, 6.3, 3.95, 0.88, mat("#9ccfc0", 0.5), 0.01)
    slab(4.65, 3.15, 0.88, 6.35, 4.0, 0.93, OAK2, 0.005)
    ball((5.5, 3.6, 1.0), 0.09, mat("#ff8a3d"), (1, 1, 0.8)); ball((5.65, 3.5, 0.99), 0.07, mat("#e5534b"))  # fruit bowl
    cyl((5.55, 3.55, 0.945), 0.17, 0.03, WHITE, 24)
    done()
    for i, sx in enumerate((4.95, 5.5, 6.05)):          # stools on the dining side of the island
        item(f"stool_{i}")
        cyl((sx, 2.85, 0.65), 0.17, 0.06, WOOD, 24)
        cyl((sx, 2.85, 0.31), 0.025, 0.62, DARK, 8)
        cyl((sx, 2.85, 0.01), 0.15, 0.02, DARK, 24)
        done()

    # ---- dining (front right + wing): table with two chairs per long side, facing it ----
    item("dining_table")
    slab(5.6, -1.05, 0.72, 7.2, -0.15, 0.77, WOOD)
    for lx in (5.7, 7.1):
        for ly in (-0.95, -0.25):
            slab(lx - 0.03, ly - 0.03, 0, lx + 0.03, ly + 0.03, 0.72, DARKWOOD, 0.004)
    cyl((6.4, -0.6, 0.85), 0.07, 0.16, mat("#ffffff", 0.2), 20)               # vase
    ball((6.4, -0.6, 0.97), 0.09, CUSH2)
    done()
    for i, x in enumerate((6.0, 6.8)):
        item(f"dchair_front_{i}"); chair(x, -1.35, '+y', WOOD, SOFA); done()
        item(f"dchair_back_{i}"); chair(x, 0.15, '-y', WOOD, SOFA); done()
    item("sideboard")
    slab(7.45, -1.9, 0.05, 7.9, -0.6, 0.8, OAK2)
    for lyy in (-1.85, -0.65):
        slab(7.5, lyy - 0.03, 0, 7.56, lyy + 0.03, 0.05, DARKWOOD, 0.004)
        slab(7.82, lyy - 0.03, 0, 7.88, lyy + 0.03, 0.05, DARKWOOD, 0.004)
    for i in range(2):                                                       # two doors facing the room (-x)
        y0 = -1.86 + i * 0.63
        slab(7.435, y0, 0.12, 7.45, y0 + 0.6, 0.74, mat("#9ccfc0", 0.5), 0.004)
        cyl((7.43, y0 + (0.52 if i == 0 else 0.08), 0.45), 0.018, 0.012, DARK, 12, 0, rot=(0, R(90), 0))
    cyl((7.68, -1.6, 0.82), 0.06, 0.04, DARK, 16); cyl((7.68, -1.6, 0.95), 0.01, 0.22, DARK, 8)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.13, radius2=0.08, depth=0.16, location=(7.68, -1.6, 1.12))
    o = bpy.context.object; o.data.materials.append(GLOWW); _adopt(o)
    for k in range(3):
        slab(7.55, -1.05 + k * 0.0, 0.8 + k * 0.04, 7.82, -0.8, 0.84 + k * 0.04, BOOKS[k], 0.004)
    done()
    item("plant_dining"); plant(5.15, -1.85, 1.0, 0.2); done()

    # warm interior lights
    for c in [(2.2, 1.6, 2.2), (5.8, 4.2, 2.2), (6.4, -0.6, 2.0), (2.3, 4.7, 2.0)]:
        bpy.ops.object.light_add(type='POINT', location=c)
        l = bpy.context.object; l.data.energy = 120; l.data.color = hexc("#ffd6a0"); l.data.shadow_soft_size = 0.4

# ======================================================================================
def upper_floor():
    item("floor")
    slab(1.3, 0, -1.4, 8, 5.6, 0, OAK, 0.01)          # thick cut floor; stairwell left open at x<1.3, y>3.35
    slab(0, 0, -1.4, 1.3, 3.35, 0, OAK, 0.01)
    slab(-0.075, 3.35, -1.4, 0.12, 5.675, 0, OAK, 0.005)    # close the stairwell's outer sides below floor level
    slab(0.12, 5.52, -1.4, 1.3, 5.675, 0, OAK, 0.005)
    slab(5.48, 2.98, 0.0, 7.93, 5.53, 0.006, BTILE, 0)
    slab(4.8, -2.2, -1.4, 8, 0, 0, mat("#e3d6c4", 0.8), 0.01)              # balcony deck
    done()
    item("stair_top")
    for i in range(3):     # last steps arriving from below
        y0 = 3.35 + (9 + i) * 0.18
        slab(0.12, y0, -1.4, 1.3, min(y0 + 0.18, 5.52), -2.7 + (9 + i + 1) * 0.215, OAK2, 0.005)   # solid flight below
    done()

    item("walls")
    wall_x(5.6, 0, 8, H_FULL, BLUSH)
    wall_y(0, 0, 5.6, H_FULL, SAGE)
    wall_x(0, 0, 4.8, H_OUT, WALL)
    wall_x(0, 4.8, 8, H_OUT, WALL, gaps=[(6.0, 6.8)])        # balcony door from the study
    wall_y(8, 0, 5.6, H_OUT, WALL)
    wall_x(3.3, 0, 4.4, H_CUT, WALL, gaps=[(3.3, 4.2)])   # bedroom | landing, bedroom door
    wall_y(4.4, 0, 3.3, H_CUT, WALL)                         # bedroom | study
    wall_x(2.9, 4.4, 8, H_CUT, WALL, gaps=[(4.5, 5.3)])      # study | landing+bath, study door
    wall_y(5.4, 2.9, 5.6, H_CUT, WALL, gaps=[(3.5, 4.3)])    # landing | bathroom, bathroom door
    window("back", 2.0, 1.0, 1.55, 1.0); window("back", 6.9, 0.9, 1.75, 0.6)
    window("left", 1.6, 1.3, 1.65, 0.8, curtains=True)
    done()
    item("stair_rail")
    for i in range(6):            # rail along the stairwell, open at the top end so you can step off toward the landing
        slab(1.33, 3.45 + i * 0.29, 0, 1.37, 3.49 + i * 0.29, 0.9, RAIL, 0.003)
    slab(1.32, 3.4, 0.9, 1.38, 4.92, 0.94, RAIL, 0.005)
    done()

    # ---- bedroom (front left): headboard on the left wall ----
    item("bed_rug"); slab(1.0, 0.45, 0, 3.0, 2.6, 0.012, RUG2, 0.005); done()
    item("bed")
    slab(0.14, 0.8, 0, 2.2, 2.4, 0.3, WOOD, 0.02)                            # frame (starts inside the headboard)
    slab(0.12, 0.75, 0, 0.2, 2.45, 1.05, WOOD, 0.02)                         # headboard on the wall
    slab(0.2, 0.83, 0.3, 2.17, 2.37, 0.52, BED, 0.06)                        # mattress
    slab(0.85, 0.8, 0.5, 2.22, 2.4, 0.58, DUVET, 0.04)                       # duvet
    box((0.42, 1.2, 0.6), (0.28, 0.6, 0.14), BED, 0.06); box((0.42, 2.0, 0.6), (0.28, 0.6, 0.14), BED, 0.06)
    done()
    for i, ny in enumerate((0.5, 2.7)):
        item(f"nightstand_{i}")
        slab(0.12, ny - 0.22, 0, 0.57, ny + 0.22, 0.5, OAK2)
        slab(0.57, ny - 0.19, 0.27, 0.575, ny + 0.19, 0.285, DARKWOOD, 0)     # drawer line
        cyl((0.585, ny, 0.38), 0.018, 0.02, DARKWOOD, 12, 0, rot=(0, R(90), 0))  # knob
        cyl((0.34, ny, 0.53), 0.05, 0.06, DARK, 16); cyl((0.34, ny, 0.65), 0.008, 0.2, DARK, 6)
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.12, radius2=0.07, depth=0.15, location=(0.34, ny, 0.8))
        o = bpy.context.object; o.data.materials.append(GLOWW); _adopt(o)
        done()
    item("wardrobe")
    slab(0.85, 2.68, 0, 2.15, 3.21, 2.0, WHITE, 0.02)                        # doors face -y into the room
    slab(1.49, 2.665, 0.2, 1.51, 2.68, 1.85, DARKWOOD, 0)
    for hx in (1.42, 1.58):
        slab(hx - 0.01, 2.665, 0.95, hx + 0.01, 2.68, 1.2, CHROME, 0)        # handles on the door face
    done()
    item("armchair")
    slab(3.25, 0.4, 0, 3.95, 1.05, 0.42, CUSH2, 0.06)                        # faces -x toward the bed side
    slab(3.75, 0.4, 0.42, 3.95, 1.05, 0.85, CUSH2, 0.06)
    slab(3.25, 0.4, 0.42, 3.75, 0.5, 0.62, CUSH2, 0.04)                      # arms
    slab(3.25, 0.95, 0.42, 3.75, 1.05, 0.62, CUSH2, 0.04)
    done()
    item("plant_bed"); plant(3.95, 2.85, 0.8, 0.17); done()

    # ---- study (front right): desk on the back partition, monitor facing the room ----
    item("study_rug"); slab(5.2, 0.5, 0, 7.6, 2.2, 0.012, RUG, 0.005); done()
    item("bookshelf")
    slab(4.48, 0.4, 0, 4.52, 2.2, 1.9, OAK2, 0.005)                          # open shelf: back panel,
    slab(4.52, 0.4, 0, 4.85, 0.44, 1.9, OAK2, 0.005)                         # two sides,
    slab(4.52, 2.16, 0, 4.85, 2.2, 1.9, OAK2, 0.005)
    slab(4.52, 0.44, 1.86, 4.85, 2.16, 1.9, OAK2, 0.005)                     # top
    for k in range(4):
        z = 0.1 + k * 0.45
        slab(4.52, 0.44, z, 4.85, 2.16, z + 0.03, WOOD, 0.004)
        y = 0.47
        while y < 2.05:
            w = random.uniform(0.04, 0.08); hgt = random.uniform(0.25, 0.36)
            slab(4.55, y, z + 0.03, 4.8, y + w, z + 0.03 + hgt, random.choice(BOOKS), 0.004)
            y += w + 0.012
    done()
    item("desk")
    slab(5.8, 2.15, 0.72, 7.2, 2.8, 0.76, WHITE, 0.01)
    for lx in (5.85, 7.15):
        slab(lx - 0.03, 2.2, 0, lx + 0.03, 2.75, 0.72, WHITE, 0.004)
    slab(6.3, 2.62, 0.76, 6.7, 2.7, 0.79, DARK, 0.005)                       # monitor foot
    slab(6.48, 2.64, 0.79, 6.52, 2.68, 0.95, DARK, 0.004)                    # stand
    slab(6.05, 2.6, 0.92, 6.95, 2.65, 1.42, DARK, 0.01)                      # monitor, screen faces -y
    slab(6.09, 2.595, 0.96, 6.91, 2.6, 1.38, SCREEN, 0)
    slab(6.2, 2.3, 0.76, 6.75, 2.45, 0.78, mat("#e9e4dc", 0.5), 0.004)       # keyboard
    box((6.9, 2.37, 0.775), (0.06, 0.1, 0.025), mat("#e9e4dc", 0.5), 0.01)   # mouse
    cyl((5.95, 2.6, 0.83), 0.045, 0.12, CUSH1, 16)                            # pencil cup
    done()
    item("pc_tower")                                                         # standing on the floor beside the desk
    slab(7.26, 2.36, 0.0, 7.46, 2.8, 0.46, mat("#d4d6dc", 0.4), 0.015)
    slab(7.28, 2.35, 0.03, 7.44, 2.36, 0.43, DARK, 0.004)                     # front panel facing the room
    for k in range(5):
        slab(7.3, 2.345, 0.08 + k * 0.05, 7.42, 2.35, 0.095 + k * 0.05, mat("#5a5d6b", 0.4), 0)   # vents
    cyl((7.36, 2.344, 0.39), 0.012, 0.004, mat("#7fd1ff", 0.3, emit=8), 16, 0, rot=(R(90), 0, 0))   # power light
    done()
    item("desk_chair"); chair(6.5, 1.75, '+y', DARK, SOFA); done()
    item("plant_study"); plant(7.65, 0.35, 0.9, 0.16); done()

    # ---- bathroom (back right) ----
    item("bathtub")
    slab(6.0, 4.75, 0, 7.92, 5.52, 0.12, WHITE, 0.02)                        # tub floor
    slab(6.0, 4.75, 0.12, 7.92, 4.85, 0.55, WHITE, 0.03)                     # four sides
    slab(6.0, 5.42, 0.12, 7.92, 5.52, 0.55, WHITE, 0.03)
    slab(6.0, 4.85, 0.12, 6.1, 5.42, 0.55, WHITE, 0.03)
    slab(7.82, 4.85, 0.12, 7.92, 5.42, 0.55, WHITE, 0.03)
    slab(6.1, 4.85, 0.12, 7.82, 5.42, 0.42, WATER, 0.0)                      # water inside
    ball((6.6, 5.1, 0.45), 0.05, CUSH1, (1, 1, 0.7)); ball((6.62, 5.07, 0.5), 0.025, CUSH1)  # rubber duck
    faucet(7.87, 5.15, 0.55, -1, 0)                                          # tap on the rim
    done()
    item("toilet_bath")
    toilet(7.44, 3.9, '-x')
    done()
    item("vanity")
    slab(6.3, 2.98, 0, 7.2, 3.45, 0.82, mat("#9ccfc0", 0.5), 0.01)          # against the study wall, faces +y
    slab(6.28, 2.98, 0.82, 7.22, 3.47, 0.86, WHITE, 0.01)
    basin(6.5, 3.1, 7.0, 3.42, 0.86, 0.99, WHITE, 0.022)                    # vessel basin on the counter
    faucet(6.75, 3.02, 0.86, 0, 1)
    done()
    item("bath_mat"); slab(6.3, 4.25, 0, 7.1, 4.65, 0.012, CUSH2, 0.005); done()
    item("towel_rail"); slab(5.475, 4.6, 0.85, 5.53, 5.4, 0.9, CHROME, 0.004)   # fixed to the partition
    slab(5.48, 4.7, 0.5, 5.56, 5.3, 0.88, CUSH1, 0.01); done()

    # ---- landing ----
    item("landing_bench")
    slab(2.2, 5.1, 0.38, 3.6, 5.52, 0.45, OAK2)
    for lx in (2.25, 3.55):
        slab(lx - 0.03, 5.13, 0, lx + 0.03, 5.49, 0.38, DARKWOOD, 0.004)
    slab(2.28, 5.14, 0.45, 3.52, 5.48, 0.5, CUSH2, 0.02)                    # seat pad
    box((2.65, 5.4, 0.62), (0.35, 0.12, 0.24), CUSH1, 0.05)                 # cushion leaning on the wall
    done()
    item("plant_landing"); plant(4.95, 5.15, 1.0, 0.2); done()
    item("frames")
    framed_art("back", 3.28, 1.45, 0.5, 0.62, "mountains")
    framed_art("back", 3.95, 1.5, 0.46, 0.5, "leaf")
    done()

    # ---- balcony: rail, round table with two chairs facing it, plants ----
    item("balcony_rail")
    for i in range(16):          # stops short of the corner post of the side rail
        x = 4.85 + i * 0.19
        slab(x - 0.02, -2.18, 0, x + 0.02, -2.14, 0.95, RAIL, 0.003)
    for i in range(11):
        y = -2.15 + i * 0.2
        slab(7.94, y - 0.02, 0, 7.98, y + 0.02, 0.95, RAIL, 0.003)
    slab(4.8, -2.2, 0.95, 7.92, -2.12, 1.0, RAIL, 0.005); slab(7.92, -2.2, 0.95, 8.0, -0.08, 1.002, RAIL, 0.005)
    done()
    item("balcony_table")
    cyl((6.4, -1.1, 0.7), 0.35, 0.04, WHITE, 32); cyl((6.4, -1.1, 0.35), 0.03, 0.68, DARK, 8); cyl((6.4, -1.1, 0.01), 0.18, 0.02, DARK, 24)
    cyl((6.3, -1.05, 0.76), 0.04, 0.08, CUSH2, 16)
    done()
    item("bchair_l"); chair(5.75, -1.1, '+x', WOOD, CUSH1); done()
    item("bchair_r"); chair(7.05, -1.1, '-x', WOOD, CUSH1); done()
    item("plant_balcony"); plant(5.1, -1.85, 0.8, 0.18); done()

    for c in [(1.6, 1.6, 2.2), (6.5, 1.4, 2.2), (6.7, 4.2, 2.2), (3.0, 4.4, 2.2)]:
        bpy.ops.object.light_add(type='POINT', location=c)
        l = bpy.context.object; l.data.energy = 120; l.data.color = hexc("#ffd6a0"); l.data.shadow_soft_size = 0.4

(ground_floor if FLOOR == "ground" else upper_floor)()

# ---------- overlap check between furniture items and walls ----------
dg = bpy.context.evaluated_depsgraph_get()
def bbox(o):
    e = o.evaluated_get(dg); pts = [e.matrix_world @ Vector(c) for c in e.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
def hit(a, b, pad=0.006):
    return all(a[0][i] + pad < b[1][i] and b[0][i] + pad < a[1][i] for i in range(3))
groups = {}
for o in s.objects:
    if o.type == 'MESH' and o.parent is not None and o.parent.name != "floor" and not any(k in o.parent.name for k in ("rug", "mat")):
        groups.setdefault(o.parent.name, []).append(bbox(o))
names = sorted(groups); bad = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        if any(hit(a, b) for a in groups[names[i]] for b in groups[names[j]]):
            bad.append((names[i], names[j]))
for a, b in bad: print("OVERLAP", a, "<->", b)
print("OVERLAP total", len(bad))

# ---------- floating check: anything not connected (by touching) to the floor or a wall is reported ----------
objs = [o for o in s.objects if o.type == 'MESH']
bb = {o.name: bbox(o) for o in objs}
def touch(a, b, tol=0.012):
    return all(a[0][i] - tol <= b[1][i] and b[0][i] - tol <= a[1][i] for i in range(3))
anchor = {o.name for o in objs if o.parent and o.parent.name in ("floor", "walls")}
seen, stack = set(anchor), list(anchor)
while stack:
    n = stack.pop()
    for o in objs:
        if o.name not in seen and touch(bb[n], bb[o.name]):
            seen.add(o.name); stack.append(o.name)
floating = [o for o in objs if o.name not in seen]
for o in floating:
    print("FLOAT", o.parent.name if o.parent else "-", o.name, [round(v, 2) for v in bb[o.name][0]])
print("FLOAT total", len(floating))

# ---------- light, camera, render ----------
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#fbefe2"), 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
bpy.ops.object.light_add(type='SUN', rotation=(R(50), R(10), R(-40)))
sun = bpy.context.object; sun.data.energy = 2.5; sun.data.angle = R(10); sun.data.color = hexc("#fff1dc")
tgt = Vector((4.0, 1.6, 0.6))
bpy.ops.object.camera_add(location=tgt + Vector((12, -12, 11)))
cam = bpy.context.object; s.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 12.5
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
s.render.engine = 'CYCLES'; s.cycles.samples = 96; s.cycles.use_denoising = True
s.render.resolution_x = 1300; s.render.resolution_y = 1100
s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast'
s.render.filepath = __import__("os").path.abspath(f"home_{FLOOR}.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath(f"home_{FLOOR}.blend"))
