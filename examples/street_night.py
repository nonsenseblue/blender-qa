import bpy, math, random
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="street.blend")
s = bpy.context.scene
random.seed(11)

def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

def emissive(name, h, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*hexc(h), 1)
    b.inputs["Emission Color"].default_value = (*hexc(h), 1); b.inputs["Emission Strength"].default_value = strength
    return m

def ball(loc, r, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = bpy.context.object; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o

def point(loc, energy, h, radius=0.1):
    bpy.ops.object.light_add(type='POINT', location=loc)
    l = bpy.context.object; l.data.energy = energy; l.data.color = hexc(h); l.data.shadow_soft_size = radius

# night sky + dim moonlight
bg = s.world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*hexc("#1b2244"), 1); bg.inputs[1].default_value = 0.3
sun = next(o for o in s.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
sun.data.energy = 0.3; sun.data.color = hexc("#9fb4ff")

# every emissive material (windows, string lights, lamp heads) glows harder
for m in bpy.data.materials:
    if not m.use_nodes: continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if b and b.inputs["Emission Strength"].default_value > 0:
        b.inputs["Emission Strength"].default_value *= 4

# existing café lamp light brighter, and light the far lamp too
for o in s.objects:
    if o.type == 'LIGHT' and o.data.type == 'POINT':
        o.data.energy = 120
point((8.4, 0.9, 2.4), 120, "#ffcf88")
# warm light spilling from shop windows and doors
for loc in [(1.35, -1.25, 1.0), (-0.15, -1.25, 1.0), (-1.05, 0.2, 1.3), (-1.05, 1.4, 1.3),
            (3.45, -1.25, 0.9), (4.75, -1.25, 0.9)]:
    point(loc, 45, "#ffbf70", 0.3)
# greenhouse glows from inside
point((4.2, 1.3, 2.9), 30, "#ffe0a0", 0.2)

# shared night sky: gradient backdrop, sparse stars, crescent moon with halo
import nightsky
nightsky.add(s, Vector((3.3, 0.3, 0.6)), moon=(-0.75, 0.74))

s.render.filepath = __import__("os").path.abspath("street_night.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("street_night.blend"))
