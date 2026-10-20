import bpy, math, random
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="island.blend")
s = bpy.context.scene
random.seed(17)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def emissive(name, h, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1)
    b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = strength
    return m

def ball(loc, r, m, seg=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=seg // 2)
    o = bpy.context.object; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def point(loc, energy, h, radius=0.1):
    bpy.ops.object.light_add(type='POINT', location=loc)
    l = bpy.context.object; l.data.energy = energy; l.data.color = hexc(h); l.data.shadow_soft_size = radius

# night sky and moonlight
bg = s.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*hexc("#1b2244"), 1); bg.inputs[1].default_value = 0.35
sun = next(o for o in s.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
sun.data.energy = 0.35; sun.data.color = hexc("#a8bcff")

# windows, string lights and lamp heads glow harder
for m in bpy.data.materials:
    if not m.use_nodes: continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if b and b.inputs["Emission Strength"].default_value > 0:
        b.inputs["Emission Strength"].default_value *= 3

# any lamp lights a bit brighter
for o in s.objects:
    if o.type == 'LIGHT' and o.data.type == 'POINT':
        o.data.energy *= 3
# warm spill from the cottage windows
for loc, e in [((1.9, 0.75, 0.45), 14), ((2.45, 1.3, 0.45), 12)]:
    point(loc, e, "#ffbf70", 0.15)

# fireflies around the lake and meadow
FF = emissive("firefly", "#d8ff7a", 30)
for _ in range(30):
    a = random.uniform(0, math.tau); r = random.uniform(0.5, 3.6)
    ball((math.cos(a) * r, math.sin(a) * r, random.uniform(0.2, 1.2)), 0.02, FF, 8)

# shared night sky: gradient backdrop, sparse stars, crescent moon with halo
import nightsky
nightsky.add(s, Vector((0, 0, 0)), moon=(-0.62, 0.66))

s.render.filepath = __import__("os").path.abspath("island_night.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("island_night.blend"))
