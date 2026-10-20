import bpy, sys, math, random
from mathutils import Vector
mode = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath="house.blend")
s = bpy.context.scene
R = math.radians
random.seed(7)

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

def ball(loc, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc)
    o = bpy.context.object; o.scale = scale; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def set_color(name, h):
    bpy.data.materials[name].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hexc(h), 1)

bg = s.world.node_tree.nodes["Background"]
sun = next(o for o in s.objects if o.type == 'LIGHT' and o.data.type == 'SUN')

def stars():
    # a dome of tiny emissive dots behind the island, only seen by the camera
    STAR = mat("star", (1, 1, 0.9), emit=12)
    cam = s.camera
    fwd = (Vector((0, 0, 0.3)) - cam.location).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    for _ in range(140):
        u, v = random.uniform(-6, 6), random.uniform(-6, 6)
        if abs(u) < 3.6 and -4.5 < v < 2.2: continue  # keep clear of the island
        p = Vector((0, 0, 0.3)) + fwd * 8 + right * u + up * v
        o = ball(p, random.uniform(0.015, 0.04), STAR)
        o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = False
    moon = ball(Vector((0, 0, 0.3)) + fwd * 8 + right * 3.3 + up * 4.2, 0.45, mat("moon", hexc("#fff4c8"), emit=4))
    moon.visible_shadow = False

if mode == "night":
    bg.inputs[0].default_value = (*hexc("#1c2348"), 1); bg.inputs[1].default_value = 0.35
    sun.data.energy = 0.35; sun.data.color = hexc("#9fb4ff")
    g = bpy.data.materials["glow"].node_tree.nodes["Principled BSDF"]; g.inputs["Emission Strength"].default_value = 18
    # warm light spilling out of the windows
    for loc in [(0.1, -0.9, 1.05), (0.95, 0.1, 1.0), (0.95, 0.9, 1.0), (-1.35, -1.0, 1.25)]:
        bpy.ops.object.light_add(type='POINT', location=loc)
        l = bpy.context.object; l.data.energy = 40; l.data.color = hexc("#ffbf66"); l.data.shadow_soft_size = 0.2
    # fireflies
    FF = mat("firefly", hexc("#d8ff7a"), emit=25)
    for _ in range(22):
        ball((random.uniform(-2.5, 2.5), random.uniform(-2.5, 2.5), random.uniform(0.3, 1.6)), 0.025, FF)
    stars()
    out = "house_night"

elif mode == "winter":
    SNOW = mat("snow", hexc("#f7fbff"), 0.6)
    set_color("grass", "#eef5fb"); set_color("leaf", "#4f9a72"); set_color("leaf2", "#6aad83")
    set_color("water", "#cfe9f7"); bpy.data.materials["water"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.25
    bg.inputs[0].default_value = (*hexc("#c9dcef"), 1)
    sun.data.color = hexc("#eaf2ff")
    # snow caps on every tree crown, bush and roof slab
    for o in list(s.objects):
        mats = [m.name for m in o.data.materials] if o.type == 'MESH' else []
        if not mats: continue
        top = max((o.matrix_world @ Vector(c)).z for c in o.bound_box)
        cx = sum((o.matrix_world @ Vector(c)).x for c in o.bound_box) / 8
        cy = sum((o.matrix_world @ Vector(c)).y for c in o.bound_box) / 8
        dims = o.dimensions
        if mats[0] in ("leaf", "leaf2") and dims.z > 0.25:
            ball((cx, cy, top - dims.z * 0.18), max(dims.x, dims.y) * 0.42, SNOW, (1, 1, 0.45))
        elif mats[0] == "roof":
            sn = o.copy(); sn.data = o.data.copy(); sn.data.materials[0] = SNOW
            s.collection.objects.link(sn)
            # transforms are baked into the mesh, so push the copy out along the slab's top face normal
            n = max(sn.data.polygons, key=lambda p: p.area * p.normal.z).normal
            bpy.ops.object.select_all(action='DESELECT'); sn.select_set(True); bpy.context.view_layer.objects.active = sn
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
            sn.location += n * 0.1
            sn.scale = (0.96, 0.96, 0.75)
        elif mats[0] == "fence" and dims.z > 0.3:
            ball((cx, cy, top), 0.06, SNOW, (1.2, 1.2, 0.6))
    # chimney smoke + falling snowflakes + snowman
    SMOKE = mat("smoke", hexc("#ffffff"), 0.9)
    for i in range(4):
        ball((0.3 + i * 0.12, 0.85 + i * 0.05, 3.25 + i * 0.32), 0.14 + i * 0.05, SMOKE)
    FLAKE = mat("flake", hexc("#ffffff"), emit=1.5)
    for _ in range(120):
        ball((random.uniform(-3.5, 3.5), random.uniform(-3.5, 3.5), random.uniform(0.2, 4.5)), 0.03, FLAKE)
    for z, r in [(0.22, 0.24), (0.55, 0.17), (0.8, 0.12)]:
        ball((0.6, -1.8, z), r, SNOW)
    ball((0.6, -1.93, 0.8), 0.025, mat("carrot", hexc("#ff8a3d")), (0.7, 3, 0.7))
    for sx in (-1, 1): ball((0.6 + sx * 0.05, -1.91, 0.84), 0.015, mat("coal", (0.02, 0.02, 0.02)))
    out = "house_winter"

elif mode == "spin":
    # orbit the camera around the island, low-res frames for a gif
    piv = bpy.data.objects.new("pivot", None); s.collection.objects.link(piv)
    s.camera.parent = piv
    s.render.resolution_x = s.render.resolution_y = 480; s.cycles.samples = 24
    N = 48
    for i in range(N):
        piv.rotation_euler = (0, 0, math.tau * i / N)
        s.render.filepath = __import__("os").path.abspath(f"spin/f_{i:03d}.png")
        bpy.ops.render.render(write_still=True)
    sys.exit()

s.render.filepath = __import__("os").path.abspath(f"{out}.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath(f"{out}.blend"))
