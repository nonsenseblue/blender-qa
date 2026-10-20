import bpy, math, random
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath="town.blend")
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

# street lamps (already point lights, scaled down with the town) a bit brighter
for o in s.objects:
    if o.type == 'LIGHT' and o.data.type == 'POINT':
        o.data.energy *= 3
# warm spill from windows: cottage, café, florist, windmill; second street lamp
for loc, e in [((2.35, 0.45, 0.5), 14), ((3.35, 0.05, 0.45), 14), ((2.35, 0.55, 1.1), 12), ((4.0, 1.6, 0.8), 14), ((-2.6, -3.6, 0.5), 15), ((-3.75, -2.5, 0.6), 10),
               ((-1.6, -3.6, 0.45), 15), ((5.33, 1.55, 1.15), 8), ((0.63, -2.6, 1.1), 10)]:
    point(loc, e, "#ffbf70", 0.15)

# fireflies around the lake and meadow
FF = emissive("firefly", "#d8ff7a", 30)
for _ in range(45):
    a = random.uniform(0, math.tau); r = random.uniform(0.5, 5.5)
    ball((math.cos(a) * r, math.sin(a) * r, random.uniform(0.2, 1.2)), 0.02, FF, 8)

# stars + moon on a plane behind the island, facing the camera
cam = s.camera
target = Vector((0, 0, -0.6))
fwd = (target - cam.location).normalized()
right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
half = cam.data.ortho_scale / 2
def camera_only(o):
    o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = False; o.visible_transmission = False

# gradient night sky on a backdrop behind everything: deep navy at the top, violet-blue toward the bottom
bpy.ops.mesh.primitive_plane_add(size=half * 2.4, location=target + fwd * 26)
sky = bpy.context.object; sky.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler(); camera_only(sky)
sm = bpy.data.materials.new("sky"); sm.use_nodes = True; nt = sm.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ramp = nt.nodes.new("ShaderNodeValToRGB"); em = nt.nodes.new("ShaderNodeEmission")
ramp.color_ramp.elements[0].color = (*hexc("#3a2f63"), 1); ramp.color_ramp.elements[0].position = 0.15
ramp.color_ramp.elements[1].color = (*hexc("#0d1230"), 1); ramp.color_ramp.elements[1].position = 0.85
nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
sky.data.materials.append(sm)

# sparse stars of varied size and brightness, kept to the upper sky
star_mats = [emissive("star_dim", "#cfd6ff", 2.5), emissive("star_mid", "#fff8e0", 5),
             emissive("star_warm", "#ffe6b0", 6), emissive("star_bright", "#ffffff", 12)]
for _ in range(90):
    u = random.uniform(-half, half); v = random.uniform(-half * 0.05, half)
    m = random.choices(star_mats, weights=(5, 3, 1, 1))[0]
    r = 0.012 + (0.02 if m.name == "star_bright" else 0.0) + random.uniform(0, 0.012)
    camera_only(ball(target + fwd * 24 + right * u + up * v, r, m, 8))

# crescent moon with faint craters and a soft halo
mc = target + fwd * 23 + right * (-half * 0.62) + up * (half * 0.66)
# flat crescent facing the camera: a thin disc minus an offset thicker disc
face_rot = fwd.to_track_quat('-Z', 'Y').to_euler()
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.42, depth=0.02, location=mc, rotation=face_rot)
moon = bpy.context.object; moon.data.materials.append(emissive("moon", "#fff1c2", 3)); camera_only(moon)
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.38, depth=0.3, location=mc + right * 0.2 + up * 0.13, rotation=face_rot)
cut = bpy.context.object; cut.hide_render = True
bo = moon.modifiers.new("crescent", 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cut
crater = emissive("crater", "#e6d49e", 2.2)
for du, dv, r in [(-0.27, -0.08, 0.05), (-0.18, -0.24, 0.035), (-0.32, 0.12, 0.03)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=0.01, location=mc + right * du + up * dv - fwd * 0.02,
                                        rotation=face_rot)
    o = bpy.context.object; o.data.materials.append(crater); camera_only(o)
# halo: emission that fades out toward the sphere's silhouette
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.95, segments=48, ring_count=24, location=mc + fwd * 0.5)
halo = bpy.context.object; bpy.ops.object.shade_smooth(); camera_only(halo)
hm = bpy.data.materials.new("halo"); hm.use_nodes = True; nt = hm.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
pw = nt.nodes.new("ShaderNodeMath"); pw.operation = 'POWER'; pw.inputs[1].default_value = 5
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*hexc("#fff1c2"), 1); em.inputs["Strength"].default_value = 0.22
tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lw.outputs["Facing"], inv.inputs[1]); nt.links.new(inv.outputs[0], pw.inputs[0])
nt.links.new(pw.outputs[0], mix.inputs["Fac"]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
halo.data.materials.append(hm)

s.render.filepath = __import__("os").path.abspath("town_night.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("town_night.blend"))
