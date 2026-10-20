# ---------- extra life on the big island (runs inside island.py's namespace) ----------
random.seed(33)
WHITE_W = mat("#fbf7ef"); RED_R = mat("#e5534b"); SOIL = mat("#8a5a3c", 0.95); DARKW = mat("#7a5238")
CABBAGE = mat("#7cc69b"); CARROT = mat("#ff8a3d"); FLEECE = mat("#ffffff", 0.95); FACE = mat("#2e2b33", 0.6)

_snap = set(bpy.data.objects)
# windmill right of the river, sails facing the camera side (-y)
WX, WY = 5.45, 2.0
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.5, radius2=0.33, depth=1.7, location=(WX, WY, 0.85))
tower = bpy.context.object; tower.data.materials.append(WHITE_W); bevel(tower, 0.02)
cone((WX, WY, 1.95), 0.45, 0.55, RED_R, 8)
box((WX, WY - 0.49, 0.32), (0.24, 0.05, 0.44), DARKW, 0.01)                       # door
# little window seated on the tower's slanted facet (an axis-aligned box hovered 10 cm off it)
from mathutils.bvhtree import BVHTree
bpy.context.view_layer.update()
_bvh = BVHTree.FromObject(tower, bpy.context.evaluated_depsgraph_get())   # tree is in the tower's local space
_mw = tower.matrix_world
_p, _n, _i, _d = _bvh.ray_cast(_mw.inverted() @ Vector((WX - 0.12, WY - 2, 1.15)), Vector((0, 1, 0)))
_p, _n = _mw @ _p, (_mw.to_3x3() @ _n).normalized()
box(_p + _n * 0.02, (0.14, 0.05, 0.16), GLOW, 0.01, rot=_n.to_track_quat('-Y', 'Z').to_euler())
hub = Vector((WX, WY - 0.62, 1.7))
cyl(hub + Vector((0, 0.1, 0)), 0.05, 0.3, DARKW, 12, 0.005, rot=(R(90), 0, 0))     # axle into the cap
cyl(hub, 0.08, 0.08, DARKW, 16, 0.01, rot=(R(90), 0, 0))
for k in range(4):
    a = R(30 + k * 90)
    d = Vector((math.cos(a), 0, math.sin(a)))
    box(hub + d * 0.42, (0.78, 0.02, 0.04), DARKW, 0.005, rot=(0, -a, 0))           # spar
    box(hub + d * 0.5 + Vector((0, -0.015, 0)), (0.6, 0.012, 0.2), WHITE_W, 0.005, rot=(0, -a, 0))  # sail on the spar

group_new(_snap, "grp_windmill")
_snap = set(bpy.data.objects)
# fenced vegetable garden beside the cottage
GX, GY, GW, GD = 4.65, 0.5, 1.6, 1.3
box((GX, GY, 0.01), (GW, GD, 0.04), SOIL, 0.01)
for row in range(4):
    y = GY - GD / 2 + 0.22 + row * 0.29
    for i in range(6):
        x = GX - GW / 2 + 0.2 + i * 0.26
        if row % 2 == 0:
            ball((x, y, 0.09), 0.09, CABBAGE, (1, 1, 0.8), sub=2)
        else:
            cone((x, y, 0.06), 0.035, 0.08, CARROT, 8)
            ball((x, y, 0.13), 0.04, LEAF2, (0.6, 0.6, 1.3), sub=1)
def picket_line(p0, p1, skip_end=False):
    v = Vector(p1) - Vector(p0); n = max(2, int(v.length / 0.18))
    for i in range(n if skip_end else n + 1):
        p = Vector(p0) + v * (i / n)
        box((p.x, p.y, 0.15), (0.04, 0.04, 0.3), WHITE_W, 0.008)
    mid = (Vector(p0) + Vector(p1)) / 2; ang = math.atan2(v.y, v.x)
    box((mid.x, mid.y, 0.2), (v.length, 0.025, 0.04), WHITE_W, 0.005, rot=(0, 0, ang))
x0, x1, y0, y1 = GX - GW / 2 - 0.05, GX + GW / 2 + 0.05, GY - GD / 2 - 0.05, GY + GD / 2 + 0.05
picket_line((x0, y1), (x1, y1)); picket_line((x1, y0), (x1, y1), True); picket_line((x0, y0), (x0, y1), True)
picket_line((x0 + 0.5, y0), (x1, y0), True)  # corners get a single post                       # gap on the front-left for a gate

group_new(_snap, "grp_garden").location.x = 0.4
_snap = set(bpy.data.objects)
# stepping-stone path: town -> bridge, bridge -> cottage door
def path(points, step=0.32):
    for a, b in zip(points, points[1:]):
        a, b = Vector(a), Vector(b); n = max(1, int((b - a).length / step))
        for i in range(n):
            p = a + (b - a) * (i / n)
            cyl((p.x + random.uniform(-0.03, 0.03), p.y + random.uniform(-0.03, 0.03), 0.015),
                0.11 + random.uniform(-0.02, 0.02), 0.03, STONE, 9, 0.008)
path([(1.15, -2.35), (1.5, -2.05), (1.88, -1.75)])
path([(2.8, -1.15), (3.0, -0.55), (2.75, 0.0), (2.33, 0.42)])

group_new(_snap, "grp_path")
_snap = set(bpy.data.objects)
# wooden jetty into the lake, with the boat moored beside it
for i in range(6):  # planks run from the shore (y -1.1) out over the water
    box((0.55, -1.1 + i * 0.13, 0.07), (0.32, 0.11, 0.03), WOOD, 0.005)
for py in (-1.1, -0.45):
    for px in (0.4, 0.7):
        cyl((px, py, 0.02), 0.025, 0.2, DARKW, 8, 0)
for px in (0.43, 0.67):  # joists under the planks (planks with gaps between them need something to lie on)
    box((px, -0.775, 0.04), (0.04, 0.76, 0.03), DARKW, 0.004)

group_new(_snap, "grp_jetty"); _snap = set(bpy.data.objects)
# three sheep grazing in the front meadow
def sheep(x, y, ang):
    f = Vector((math.cos(ang), math.sin(ang), 0)); sd = Vector((-f.y, f.x, 0))
    c = Vector((x, y, 0.2))
    for off, r in [(Vector((0, 0, 0)), 0.15), (f * 0.1, 0.12), (-f * 0.1, 0.12), (sd * 0.07, 0.11), (-sd * 0.07, 0.11),
                   (Vector((0, 0, 0.07)), 0.11)]:
        ball(c + off, r, FLEECE, sub=2)
    head = c + f * 0.22 + Vector((0, 0, -0.02))
    ball(head, 0.07, FACE, (1, 1, 1.15), sub=2)
    ball(head + Vector((0, 0, 0.06)) - f * 0.02, 0.05, FLEECE, sub=2)                 # woolly top
    for e in (-1, 1):
        ball(head + sd * e * 0.07 + Vector((0, 0, 0.02)), 0.03, FACE, (1, 1, 0.5), sub=1)  # ears
    for lf in (-1, 1):
        for ls in (-1, 1):
            p = c + f * lf * 0.09 + sd * ls * 0.06
            cyl((p.x, p.y, 0.06), 0.022, 0.12, FACE, 8, 0)
for _x, _y, _a in [(1.75, -3.0, 200), (2.25, -3.45, 150), (1.55, -3.8, 30)]:
    _s2 = set(bpy.data.objects); sheep(_x, _y, R(_a)); group_new(_s2, "grp_sheep")
_snap = set(bpy.data.objects)

group_new(_snap, "grp_jetty")
_snap = set(bpy.data.objects)
# hot-air balloon drifting over the back of the island
BX_, BY_, BZ_ = 3.6, 3.0, 5.0
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.75, segments=48, ring_count=24, location=(BX_, BY_, BZ_))
env = bpy.context.object; env.scale = (1, 1, 1.15); bpy.ops.object.shade_smooth()
em = bpy.data.materials.new("balloon"); em.use_nodes = True; nt = em.node_tree
tc = nt.nodes.new("ShaderNodeTexCoord"); gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'RADIAL'
nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
m8 = nt.nodes.new("ShaderNodeMath"); m8.operation = 'MULTIPLY'; m8.inputs[1].default_value = 10
fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'PINGPONG'; fr.inputs[1].default_value = 1
st = nt.nodes.new("ShaderNodeMath"); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = 0.5
nt.links.new(gr.outputs["Fac"], m8.inputs[0]); nt.links.new(m8.outputs[0], fr.inputs[0]); nt.links.new(fr.outputs[0], st.inputs[0])
mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = 'RGBA'
mx.inputs["A"].default_value = (*hexc("#e5534b"), 1); mx.inputs["B"].default_value = (*hexc("#ffd36b"), 1)
nt.links.new(st.outputs[0], mx.inputs["Factor"]); nt.links.new(mx.outputs["Result"], nt.nodes["Principled BSDF"].inputs["Base Color"])
env.data.materials.append(em)
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.42, radius2=0.12, depth=0.4, location=(BX_, BY_, BZ_ - 0.95))
bpy.context.object.data.materials.append(RED_R); bpy.ops.object.shade_smooth()
box((BX_, BY_, BZ_ - 1.55), (0.3, 0.3, 0.22), WOOD, 0.03)
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl((BX_ + sx * 0.13, BY_ + sy * 0.13, BZ_ - 1.27), 0.008, 0.38, DARKW, 6, 0)


group_new(_snap, "grp_balloon")
_snap = set(bpy.data.objects)
# ---------- two-storey villa where the cottage used to be ----------
VX0, VX1, VY0, VY1 = 1.4, 3.4, 0.85, 2.25          # main block footprint (front face at VY0, facing -y)
F1, F2 = 0.75, 1.4                                 # top of ground floor / top of walls
TRIMW = mat("#ffffff"); STONEB = mat("#d9d4cc"); DOORM = mat("#7a5238")
vx, vy = (VX0 + VX1) / 2, (VY0 + VY1) / 2
box((vx, vy, 0.04), (VX1 - VX0 + 0.12, VY1 - VY0 + 0.12, 0.08), STONEB, 0.02)        # plinth
box((vx, vy, 0.05 + (F2 - 0.05) / 2), (VX1 - VX0, VY1 - VY0, F2 - 0.05), WALL, 0.03)
box((vx, vy, F1), (VX1 - VX0 + 0.05, VY1 - VY0 + 0.05, 0.05), TRIMW, 0.01)             # band between floors
box((vx, vy, F2 - 0.02), (VX1 - VX0 + 0.07, VY1 - VY0 + 0.07, 0.06), TRIMW, 0.01)      # cornice

# hip roof with overhang
ov, rh = 0.14, 0.6
x0, x1, y0, y1 = VX0 - ov, VX1 + ov, VY0 - ov, VY1 + ov
d = (y1 - y0) / 2; yc = (y0 + y1) / 2; zt = F2 + 0.01
rverts = [(x0, y0, zt), (x1, y0, zt), (x1, y1, zt), (x0, y1, zt), (x0 + d, yc, zt + rh), (x1 - d, yc, zt + rh)]
rm = bpy.data.meshes.new("villa_roof")
rm.from_pydata(rverts, [], [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (3, 2, 1, 0)])
ro = bpy.data.objects.new("villa_roof", rm); s.collection.objects.link(ro); rm.materials.append(ROOF)
ro.modifiers.new("solid", 'SOLIDIFY').thickness = 0.06
box((1.75, 1.95, F2 + 0.42), (0.2, 0.2, 0.5), mat("#c96a5a"), 0.02)                    # chimney, just clears the ridge
box((1.75, 1.95, F2 + 0.68), (0.26, 0.26, 0.05), mat("#c96a5a"), 0.01)

def window_y(x, z, w, h, y=VY0, glow=GLOW):   # on the front face, looking -y
    box((x, y - 0.015, z), (w + 0.06, 0.04, h + 0.06), TRIMW, 0.008)
    box((x, y - 0.03, z), (w, 0.03, h), glow, 0.0)
    box((x, y - 0.05, z), (0.02, 0.015, h), TRIMW, 0.0); box((x, y - 0.05, z), (w, 0.015, 0.02), TRIMW, 0.0)
def window_x(y, z, w, h, x=VX1):              # on the right face, looking +x
    box((x + 0.015, y, z), (0.04, w + 0.06, h + 0.06), TRIMW, 0.008)
    box((x + 0.03, y, z), (0.03, w, h), GLOW, 0.0)
    box((x + 0.05, y, z), (0.015, 0.02, h), TRIMW, 0.0); box((x + 0.05, y, z), (0.015, w, 0.02), TRIMW, 0.0)

# ground floor front: door with porch, one window
box((1.95, VY0 - 0.02, 0.32), (0.32, 0.05, 0.52), TRIMW, 0.01)
box((1.95, VY0 - 0.04, 0.31), (0.25, 0.04, 0.48), DOORM, 0.01)
ball((2.03, VY0 - 0.07, 0.3), 0.018, mat("#ffd27a", 0.2))
window_y(2.38, 0.42, 0.3, 0.3)
box((1.95, VY0 - 0.2, 0.04), (0.5, 0.3, 0.05), STONEB, 0.01)                           # step
box((1.95, VY0 - 0.17, 0.66), (0.62, 0.42, 0.05), ROOF, 0.015)                        # porch roof
for px in (1.71, 2.19):
    cyl((px, VY0 - 0.33, 0.35), 0.028, 0.6, TRIMW, 12, 0.005)
box((1.62, VY0 - 0.02, 0.5), (0.06, 0.04, 0.1), GLOW, 0.01)                            # porch lamp, on the wall

# one-storey wing at the front right; its flat roof is the upstairs balcony
WX0, WX1, WY0 = 2.6, 3.4, 0.3
box(((WX0 + WX1) / 2, (WY0 + VY0) / 2, 0.05 + (F1 - 0.05) / 2), (WX1 - WX0, VY0 - WY0, F1 - 0.05), WALL, 0.03)
box(((WX0 + WX1) / 2, (WY0 + VY0) / 2, F1), (WX1 - WX0 + 0.05, VY0 - WY0 + 0.05, 0.05), TRIMW, 0.01)
window_y(3.0, 0.42, 0.46, 0.32, y=WY0)
window_x((WY0 + VY0) / 2, 0.42, 0.3, 0.3)
for i in range(9):    # railing posts along the front and right edges
    box((WX0 + 0.03 + i * (WX1 - WX0 - 0.06) / 8, WY0 + 0.03, F1 + 0.13), (0.025, 0.025, 0.22), TRIMW, 0.004)
for i in range(1, 6):
    box((WX1 - 0.03, WY0 + 0.03 + i * (VY0 - WY0 - 0.06) / 5, F1 + 0.13), (0.025, 0.025, 0.22), TRIMW, 0.004)
box(((WX0 + WX1) / 2, WY0 + 0.03, F1 + 0.25), (WX1 - WX0, 0.04, 0.03), TRIMW, 0.006)
box((WX1 - 0.03, (WY0 + VY0) / 2, F1 + 0.25), (0.04, VY0 - WY0, 0.03), TRIMW, 0.006)
cyl((2.8, 0.55, F1 + 0.095), 0.07, 0.14, POT if "POT" in globals() else mat("#e7896b"), 16, 0.01)   # potted plant on the balcony
ball((2.8, 0.55, F1 + 0.235), 0.1, LEAF2, sub=2)

# upstairs front: two windows with flower boxes, french door onto the balcony
for x in (1.7, 2.2):
    window_y(x, 1.08, 0.28, 0.34)
    box((x, VY0 - 0.07, 0.86), (0.34, 0.1, 0.06), WOOD, 0.01)
    for k in range(4):
        ball((x - 0.12 + k * 0.08, VY0 - 0.07, 0.91), 0.035, FLOW[k % len(FLOW)], sub=1)
window_y(3.0, 1.0, 0.32, 0.48)
# right face windows on both floors
window_x(1.6, 0.42, 0.3, 0.3); window_x(1.25, 1.08, 0.28, 0.34); window_x(1.95, 1.08, 0.28, 0.34)
# little hedge either side of the porch
for hx in (1.5, 2.45):
    ball((hx, VY0 - 0.12, 0.1), 0.12, LEAF, (1.2, 1, 0.8), sub=2)

group_new(_snap, "grp_villa").location.x = 0.35  # clear of the lake-shore stones
