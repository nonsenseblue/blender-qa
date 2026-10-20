import bpy, math, random
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
R = math.radians
random.seed(21)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

_m = {}
def mat(h, rough=0.7, emit=0):
    if (h, rough, emit) in _m: return _m[(h, rough, emit)]
    m = bpy.data.materials.new(h); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = emit
    _m[(h, rough, emit)] = m; return m

def bevel(o, w):
    m = o.modifiers.new("bevel", 'BEVEL'); m.width = w; m.segments = 3; m.limit_method = 'ANGLE'
    o.modifiers.new("wn", 'WEIGHTED_NORMAL')

def box(loc, size, m, bw=0.03, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel(o, bw); o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def ball(loc, r, m, scale=(1, 1, 1), sub=3, smooth=True):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m)
    if smooth: bpy.ops.object.shade_smooth()
    return o

def cyl(loc, r, d, m, verts=48, bw=0.03, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object
    if bw: bevel(o, bw)
    o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def cone(loc, r1, d, m, verts=8, r2=0):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=d, location=loc)
    o = bpy.context.object; o.data.materials.append(m); return o

def displace(o, strength, scale, seed_name):
    tex = bpy.data.textures.new(seed_name, 'CLOUDS'); tex.noise_scale = scale
    o.modifiers.new("sub", 'SUBSURF').subdivision_type = 'SIMPLE'
    o.modifiers["sub"].levels = 3; o.modifiers["sub"].render_levels = 3
    d = o.modifiers.new("disp", 'DISPLACE'); d.texture = tex; d.strength = strength; d.mid_level = 0.5

GRASS = mat("#9fd67c"); GRASS2 = mat("#8cc96b"); DIRT = mat("#a8744f"); ROCK = mat("#8a7a70")
WATER = mat("#6fc3ee", 0.05); FOAM = mat("#ffffff", 0.4); WOOD = mat("#b9825a"); WALL = mat("#fff3dc")
ROOF = mat("#5b8fd1"); GLOW = mat("#ffd27a", 0.3, emit=5); LEAF = mat("#6cbf6a"); LEAF2 = mat("#8fd47a")
PINE = mat("#4f9a72"); PINE2 = mat("#5fae80"); TRUNK = mat("#8a5a3c"); STONE = mat("#d9d4cc")
CLOUD = mat("#ffffff", 0.9); FLOW = [mat(h) for h in ("#ff9ec4", "#fff07a", "#ffffff", "#c9a7ff")]

# ---------- floating island ----------
RAD = 4.0
cyl((0, 0, -0.15), RAD, 0.3, GRASS, 64, 0.12)
cyl((0, 0, -0.55), RAD - 0.05, 0.55, DIRT, 64, 0.08)
bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=RAD - 0.15, radius2=0.2, depth=3.4, location=(0, 0, -2.5),
                                rotation=(R(180), 0, 0))
under = bpy.context.object; under.data.materials.append(ROCK); displace(under, 0.7, 0.5, "under")
bpy.ops.object.shade_smooth()
# little rocks hanging below
for k in range(6):
    a = k / 6 * math.tau + 0.4
    ball((math.cos(a) * 1.3, math.sin(a) * 1.3, -2.4 - random.random() * 0.4), 0.25 + random.random() * 0.2, ROCK,
         (1, 1, 1.4), sub=1, smooth=False)

# ---------- mountains: low-poly, colour by height (grass -> rock -> snow) ----------
def mountain_mat(name, z_rock, z_snow):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = 'CONSTANT'
    e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (*hexc("#7fbf68"), 1)
    e[1].position = z_rock; e[1].color = (*hexc("#9a8b80"), 1)
    e3 = e.new(z_snow); e3.color = (*hexc("#fbfdff"), 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.5; mr.inputs["From Max"].default_value = 1.5
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m

def mountain(loc, r, h, name, z_rock=0.35, z_snow=0.7):
    bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=r, depth=3, location=(loc[0], loc[1], 1.5 * h / 1.0 * 0 + h / 2))
    o = bpy.context.object; o.scale = (1, 1, h / 3)
    o.rotation_euler.z = random.random() * 6
    o.data.materials.append(mountain_mat(name, z_rock, z_snow))
    tex = bpy.data.textures.new(name, 'VORONOI'); tex.noise_scale = 0.9
    sub = o.modifiers.new("sub", 'SUBSURF'); sub.subdivision_type = 'SIMPLE'; sub.levels = sub.render_levels = 2
    d = o.modifiers.new("disp", 'DISPLACE'); d.texture = tex; d.strength = 0.35; d.mid_level = 0.6
    o.modifiers.new("dec", 'DECIMATE').ratio = 0.35  # chunky facets
    return o

mountain((-1.6, 1.5), 2.0, 3.2, "big")
mountain((0.6, 2.4), 1.3, 2.0, "small", 0.45, 0.85)
mountain((-2.7, -0.3), 1.0, 1.3, "tiny", 0.6, 2.0)

# ---------- river: from the mountain foot, through a lake, over the edge ----------
LAKE = (1.2, -0.3)
cyl((LAKE[0], LAKE[1], 0.0), 1.05, 0.06, WATER, 64, 0.02).scale = (1, 0.75, 1)
for k in range(16):
    a = k / 16 * math.tau
    ball((LAKE[0] + math.cos(a) * 1.12, LAKE[1] + math.sin(a) * 0.82, 0.02), 0.09 + random.random() * 0.05, STONE,
         (1, 1, 0.6), sub=1, smooth=False)

def river(points, width):
    cd = bpy.data.curves.new("river", 'CURVE'); cd.dimensions = '3D'
    cd.bevel_depth = width; cd.bevel_resolution = 4
    sp = cd.splines.new('BEZIER'); sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new("river", cd); s.collection.objects.link(o); cd.materials.append(WATER)
    o.scale = (1, 1, 0.12)  # flatten the tube into a stream
    return o
river([(-0.7, 0.5, 0.15), (-0.2, 0.0, 0.15), (0.0, -0.4, 0.15), (0.4, -0.4, 0.15)], 0.22)
edge = Vector((math.cos(R(-45)), math.sin(R(-45)), 0)) * RAD
river([(1.9, -0.75, 0.15), (2.3, -1.4, 0.15), (2.6, -2.4, 0.15), (edge.x + 0.05, edge.y - 0.05, 0.15)], 0.24)

# waterfall pouring off the rim toward the camera, with foam and mist
wf_dir = Vector((edge.x, edge.y, 0)).normalized()
FALL_Z = -2.5
centre = [(edge - wf_dir * 0.25) + Vector((0, 0, 0.02)), edge + wf_dir * 0.1 + Vector((0, 0, -0.05)),
          edge + wf_dir * 0.3 + Vector((0, 0, FALL_Z * 0.38)), edge + wf_dir * 0.45 + Vector((0, 0, FALL_Z))]
widen = (1.0, 1.0, 1.45, 2.3)  # the stream spreads as it falls
fall = river([tuple(c) for c in centre], 0.2)
fall.scale = (1, 1, 1)
for bp, w in zip(fall.data.splines[0].bezier_points, widen):
    bp.radius = w
# white streaks running down the face of the fall
perp = Vector((-wf_dir.y, wf_dir.x, 0))
for lat in (-0.55, 0.05, 0.5):
    sd = bpy.data.curves.new("streak", 'CURVE'); sd.dimensions = '3D'; sd.bevel_depth = 0.014
    sp = sd.splines.new('BEZIER'); sp.bezier_points.add(2)
    for bp, i, f in zip(sp.bezier_points, (1, 2, 3), (0.0, 0.25, 0.92)):
        r = 0.2 * widen[i]
        c = centre[i] + (centre[3] - centre[i]) * 0 if i < 3 else centre[3] + (centre[2] - centre[3]) * 0.08
        bp.co = c + wf_dir * r * 0.95 + perp * lat * r
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    so = bpy.data.objects.new("streak", sd); s.collection.objects.link(so); sd.materials.append(FOAM)
# the fall dissolves into a soft cloud of mist instead of ending in mid-air
base = centre[3]
for k in range(16):
    off = perp * random.uniform(-0.7, 0.7) + wf_dir * random.uniform(-0.35, 0.45) + Vector((0, 0, random.uniform(-0.25, 0.3)))
    ball(base + off, 0.22 + random.random() * 0.24, CLOUD)
for k in range(5):  # drifting wisps below
    off = perp * random.uniform(-1.1, 1.1) + Vector((0, 0, random.uniform(-0.7, -0.4)))
    ball(base + off, 0.12 + random.random() * 0.1, CLOUD, (1.4, 1.4, 0.8))
for k in range(5):  # foam where the river tips over
    p = edge - wf_dir * 0.05 + Vector((random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0))
    ball((p.x, p.y, 0.05), 0.08, FOAM, (1, 1, 0.5))

# little wooden bridge across the lower river
bx, by = 2.33, -1.45
box((bx, by, 0.2), (0.9, 0.42, 0.06), WOOD, 0.015, rot=(0, 0, R(32)))
for sx in (-1, 1):
    off = Vector((math.cos(R(32 + 90)), math.sin(R(32 + 90)), 0)) * 0.19 * sx
    box((bx + off.x, by + off.y, 0.38), (0.9, 0.04, 0.04), WOOD, 0.01, rot=(0, 0, R(32)))
    for px in (-0.4, 0, 0.4):
        along = Vector((math.cos(R(32)), math.sin(R(32)), 0)) * px
        box((bx + off.x + along.x, by + off.y + along.y, 0.3), (0.05, 0.05, 0.2), WOOD, 0.01)
    for px in (-0.38, 0.38):  # stout legs under the deck ends, set into the banks (the deck must not hover)
        along = Vector((math.cos(R(32)), math.sin(R(32)), 0)) * px
        box((bx + off.x * 0.85 + along.x, by + off.y * 0.85 + along.y, 0.03), (0.07, 0.07, 0.28), WOOD, 0.01)

# ---------- cottage by the lake ----------
HX, HY = 1.9, 1.3
box((HX, HY, 0.45), (1.0, 0.85, 0.8), WALL, 0.04)
top = 0.85; pitch = R(35); half = 0.85 / 2 + 0.15
ridge = top + math.tan(pitch) * 0.85 / 2
for sy in (-1, 1):
    box((HX, HY + sy * half / 2, ridge - math.tan(pitch) * half / 2 + 0.06),
        (1.2, half / math.cos(pitch) + 0.06, 0.09), ROOF, 0.03, rot=(-sy * pitch, 0, 0))
verts = []
for x in (HX - 0.5, HX + 0.5):
    verts += [(x, HY - 0.425, top), (x, HY + 0.425, top), (x, HY, ridge)]
gm = bpy.data.meshes.new("gable"); gm.from_pydata(verts, [], [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])
g = bpy.data.objects.new("gable", gm); s.collection.objects.link(g); gm.materials.append(WALL)
box((HX - 0.2, HY - 0.44, 0.35), (0.28, 0.05, 0.5), WOOD, 0.01)          # door faces the lake (-y)
box((HX + 0.25, HY - 0.44, 0.55), (0.26, 0.05, 0.24), GLOW, 0.01)        # front window
box((HX + 0.51, HY, 0.55), (0.05, 0.26, 0.24), GLOW, 0.01)               # side window
box((HX + 0.25, HY + 0.2, ridge + 0.05), (0.14, 0.14, 0.35), mat("#c96a5a"), 0.02)  # chimney
# path from the door to the lake shore
for i, (px, py) in enumerate([(HX - 0.2, HY - 0.75), (HX - 0.3, HY - 1.05), (HX - 0.45, HY - 1.3)]):
    cyl((px, py, 0.02), 0.12, 0.04, STONE, 10, 0.01)
# little rowing boat on the lake
# open hull: lower half of a sphere, ends pinched to a point, shelled with solidify (wood inside)
BOAT_C, BOAT_A = Vector((0.75, -0.45, 0.13)), R(25)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16)
boat = bpy.context.object
me = boat.data
import bmesh
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.001], context='VERTS')
for v in bm.verts:
    v.co.y *= max(0.0, 1 - v.co.x ** 2) ** 0.6  # pointy bow and stern
bm.to_mesh(me); bm.free()
boat.scale = (0.42, 0.17, 0.13); boat.location = BOAT_C; boat.rotation_euler.z = BOAT_A
me.materials.append(mat("#e5534b")); me.materials.append(WOOD)
sol = boat.modifiers.new("shell", 'SOLIDIFY'); sol.thickness = 0.12; sol.material_offset = 1; sol.offset = 1
boat.modifiers.new("smooth", 'SUBSURF').levels = 1
bpy.ops.object.shade_smooth()
fwd = Vector((math.cos(BOAT_A), math.sin(BOAT_A), 0)); side = Vector((-fwd.y, fwd.x, 0))
# floorboards inside the hull, above the waterline so the lake doesn't show through
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1, depth=0.02, location=BOAT_C + Vector((0, 0, -0.07)))
fl = bpy.context.object; fl.scale = (0.33, 0.12, 1); fl.rotation_euler.z = BOAT_A; fl.data.materials.append(WOOD)
for t in (-0.13, 0.12):  # two bench seats across the boat
    box(BOAT_C + fwd * t + Vector((0, 0, -0.03)), (0.07, 0.26, 0.02), WOOD, 0.005, rot=(0, 0, BOAT_A))
for sgn in (-1, 1):  # two oars stowed lengthwise on top of the seats
    p = BOAT_C + side * sgn * 0.06 + Vector((0, 0, -0.005))
    cyl(p, 0.012, 0.52, WOOD, 8, 0, rot=(0, R(90), BOAT_A))
    box(p + fwd * 0.22, (0.12, 0.045, 0.012), WOOD, 0.005, rot=(0, 0, BOAT_A))

# ---------- trees, flowers, clouds ----------
def pine(x, y, h):
    cyl((x, y, 0.12 * h), 0.05 * h, 0.25 * h, TRUNK, 8, 0.005)
    for k, r in enumerate((0.32, 0.25, 0.17)):
        c = cone((x, y, (0.35 + k * 0.22) * h), r * h, 0.38 * h, PINE if k % 2 == 0 else PINE2)
def round_tree(x, y, h):
    cyl((x, y, 0.25 * h), 0.06 * h, 0.5 * h, TRUNK, 8, 0.005)
    ball((x, y, 0.7 * h), 0.33 * h, LEAF); ball((x + 0.12 * h, y - 0.08 * h, 0.9 * h), 0.22 * h, LEAF2)

for x, y, h in [(-0.3, 2.0, 0.9), (0.2, 1.3, 1.0), (-2.7, 1.6, 1.1), (-3.0, 0.9, 0.8), (-0.9, -0.6, 0.9),
                (-1.8, -1.2, 1.1), (-2.2, -1.9, 0.8), (1.5, 3.0, 0.7), (2.6, 2.2, 0.9)]:
    pine(x, y, h)
for x, y, h in [(3.0, 0.4, 1.0), (0.2, -2.0, 0.9), (-0.8, -2.8, 1.1), (1.0, -3.2, 0.8), (3.2, 1.4, 0.8)]:
    round_tree(x, y, h)
for _ in range(40):  # flower dots on the meadow, kept off the water and mountains
    a = random.uniform(0, math.tau); r = random.uniform(1.0, 3.6)
    x, y = math.cos(a) * r, math.sin(a) * r
    if (Vector((x, y)) - Vector(LAKE)).length < 1.3 or (x < -0.3 and y > -0.2) or (x > 0.4 and y > 1.6): continue
    ball((x, y, 0.04), 0.045, random.choice(FLOW), sub=2)

def cloud(x, y, z, sc):
    for dx, dz, r in [(0, 0, 0.45), (0.45, -0.08, 0.35), (-0.45, -0.1, 0.32), (0.2, 0.2, 0.32)]:
        ball((x + dx * sc, y, z + dz * sc), r * sc, CLOUD, (1, 0.8, 0.8)).name = "cloud"
cloud(-3.6, 2.2, 3.6, 1.0); cloud(3.4, 2.8, 2.6, 0.8); cloud(-4.2, -2.6, 0.6, 0.7)

# ---------- light, sky, camera ----------
w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (*hexc("#cfeaf8"), 1); bg.inputs[1].default_value = 1.0
bpy.ops.object.light_add(type='SUN', rotation=(R(50), R(10), R(-35)))
sun = bpy.context.object; sun.data.energy = 3.5; sun.data.angle = R(6); sun.data.color = hexc("#fff1dc")

bpy.ops.object.camera_add(location=(14, -14, 11.5))
cam = bpy.context.object; s.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 11.5
cam.rotation_euler = (Vector((0, 0, 0.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()

s.render.engine = 'CYCLES'; s.cycles.samples = 128; s.cycles.use_denoising = True
s.render.resolution_x = 1000; s.render.resolution_y = 1100
s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Base Contrast'
s.render.filepath = __import__("os").path.abspath("island.png" if not __import__("os").environ.get("BOATTEST") else "boat_test.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("island.blend"))
