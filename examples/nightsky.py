"""Shared night sky for every night render: gradient backdrop, sparse varied stars, crescent moon with
craters and a soft halo. One implementation, so a fix here reaches every night scene.

    import nightsky; nightsky.add(scene, target=Vector((0, 0, 0)), moon=(-0.62, 0.66))
"""
import math
import random
import bpy
from mathutils import Vector


def _lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def _emissive(name, h, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*_lin(h), 1)
    b.inputs["Emission Color"].default_value = (*_lin(h), 1); b.inputs["Emission Strength"].default_value = strength
    return m


def _camera_only(o):
    o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = False; o.visible_transmission = False
    return o


def _bare(m):
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    return nt


def add(scene, target, moon=(-0.62, 0.66), stars=90, star_floor=-0.05, seed=17):
    """target: point the ortho camera looks at. moon: (u, v) as fractions of half the frame
    (u right, v up). stars only appear above v = star_floor (the upper sky)."""
    rnd = random.Random(seed)
    cam = scene.camera
    fwd = (target - cam.location).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    aspect = scene.render.resolution_x / scene.render.resolution_y
    half = cam.data.ortho_scale / 2                  # half of the longer side
    hu, hv = (half, half / aspect) if aspect >= 1 else (half * aspect, half)
    k = half / 7.75                                  # sizes were tuned at ortho_scale 15.5
    face_rot = fwd.to_track_quat("-Z", "Y").to_euler()

    # gradient backdrop (ortho cameras ignore world gradients)
    bpy.ops.mesh.primitive_plane_add(size=half * 2.6, location=target + fwd * 26)
    sky = _camera_only(bpy.context.object); sky.rotation_euler = face_rot
    sm = bpy.data.materials.new("night_sky"); sm.use_nodes = True; nt = _bare(sm)
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); em = nt.nodes.new("ShaderNodeEmission")
    ramp.color_ramp.elements[0].color = (*_lin("#3a2f63"), 1); ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[1].color = (*_lin("#0d1230"), 1); ramp.color_ramp.elements[1].position = 0.85
    nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    sky.data.materials.append(sm)

    # sparse stars: mostly dim, a few bright, slight warm/cool tints, upper sky only
    mats = [_emissive("star_dim", "#cfd6ff", 2.5), _emissive("star_mid", "#fff8e0", 5),
            _emissive("star_warm", "#ffe6b0", 6), _emissive("star_bright", "#ffffff", 12)]
    for _ in range(stars):
        u = rnd.uniform(-hu, hu); v = rnd.uniform(hv * star_floor, hv)
        m = rnd.choices(mats, weights=(5, 3, 1, 1))[0]
        r = (0.012 + (0.02 if m.name.startswith("star_bright") else 0) + rnd.uniform(0, 0.012)) * k
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=target + fwd * 24 + right * u + up * v, segments=8, ring_count=4)
        o = _camera_only(bpy.context.object); o.data.materials.append(m)

    # crescent: a flat disc minus an offset disc (a sphere minus a sphere leaves a glowing bowl)
    mc = target + fwd * 23 + right * (moon[0] * hu) + up * (moon[1] * hv)
    R = 0.42 * k
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R, depth=0.02, location=mc, rotation=face_rot)
    disc = _camera_only(bpy.context.object); disc.data.materials.append(_emissive("moon", "#fff1c2", 3))
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R * 0.9, depth=0.3, location=mc + right * R * 0.48 + up * R * 0.31,
                                        rotation=face_rot)
    cut = bpy.context.object; cut.hide_render = True
    bo = disc.modifiers.new("crescent", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = cut
    crater = _emissive("crater", "#e6d49e", 2.2)
    for du, dv, r in [(-0.64, -0.19, 0.12), (-0.43, -0.57, 0.083), (-0.76, 0.29, 0.071)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * R, depth=0.01,
                                            location=mc + right * du * R + up * dv * R - fwd * 0.015, rotation=face_rot)  # on the disc face
        o = _camera_only(bpy.context.object); o.data.materials.append(crater)
    # soft glow only off the lit limb: grow the outer disc, keep the same bite, so nothing spills into the dark side
    cut_c = mc + right * R * 0.48 + up * R * 0.31
    for g, alpha in ((0.07, 0.32), (0.16, 0.16), (0.28, 0.07)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R * (1 + g), depth=0.01, location=mc + fwd * (0.05 + g),
                                            rotation=face_rot)
        glow = _camera_only(bpy.context.object)
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R * 0.9, depth=0.1, location=cut_c + fwd * (0.05 + g),
                                            rotation=face_rot)   # same depth as this glow layer, or the cut misses it
        gcut = bpy.context.object; gcut.hide_render = True
        gb = glow.modifiers.new("crescent", "BOOLEAN"); gb.operation = "DIFFERENCE"; gb.object = gcut
        gm = bpy.data.materials.new(f"moon_glow_{g}"); gm.use_nodes = True; nt = _bare(gm)
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*_lin("#fff1c2"), 1)
        em.inputs["Strength"].default_value = 1.2
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        glow.data.materials.append(gm)
