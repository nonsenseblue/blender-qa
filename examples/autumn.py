"""Shared autumn look for the island scenes: golden meadow, orange/red round trees, fallen and drifting
leaves, pumpkins and a hay bale. One implementation, so a fix here reaches every autumn scene.

    import autumn; autumn.apply(scene, radius=3.8, lake=((1.2, -0.3), 1.2), pumpkins=[...], hay=(x, y, ang))
"""
import math
import random
import bpy
from mathutils import Vector

WATER = "#6fc3ee"


def hexc(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def _recolor(name, h):
    m = bpy.data.materials.get(name)
    if m is not None:
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*hexc(h), 1)


def _mat(h, rough=0.7):
    m = bpy.data.materials.new(h); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*hexc(h), 1)
    b.inputs["Roughness"].default_value = rough
    return m


def _ground(s, dg, x, y, r=0.0):
    """Height of open ground under a footprint of radius r at (x, y), or None if any of it is over water,
    rocks, paths or a slope (a leaf whose edge is tucked into a mountain foot is not lying on the grass)."""
    zs = []
    ring = [(r * math.cos(k * math.pi / 4), r * math.sin(k * math.pi / 4)) for k in range(8)] if r else []
    for dx, dy in [(0, 0)] + ring:
        hit, loc, nrm, _i, obj, _m = s.ray_cast(dg, Vector((x + dx, y + dy, 0.3)), Vector((0, 0, -1)))  # from just above the grass, so leaves can lie under trees
        if not hit or loc.z > 0.02 or nrm.z < 0.98:   # the flared foot of a mountain is low but not flat
            return None
        if obj.active_material and obj.active_material.name.startswith(WATER):
            return None
        zs.append(loc.z)
    return max(zs)


def apply(s, radius, lake, pumpkins=(), hay=None, seed=9, fallen=90, drifting=25):
    random.seed(seed)
    # meadow turns golden, round trees go orange/red, pines stay evergreen
    _recolor("#9fd67c", "#d8c86a")   # grass
    _recolor("#6cbf6a", "#f08a3c")   # leaf
    _recolor("#8fd47a", "#e5534b")   # leaf2
    _recolor(WATER, "#5fb0d8")       # water a touch deeper
    for m in bpy.data.materials:     # mountain foothills from green to autumn ochre
        if m.name in ("big", "small", "tiny"):
            cr = next(n for n in m.node_tree.nodes if n.type == 'VALTORGB')
            cr.color_ramp.elements[0].color = (*hexc("#c9b45e"), 1)
    s.world.node_tree.nodes["Background"].inputs[0].default_value = (*hexc("#f7e3cf"), 1)
    sun = next(o for o in s.objects if o.type == 'LIGHT' and o.data.type == 'SUN')
    sun.data.color = hexc("#ffd9a8"); sun.data.energy = 3.8

    leaves = [_mat(h) for h in ("#f08a3c", "#e5534b", "#f2c14e", "#c9612c")]

    def leaf(x, y, z, tilt):
        bpy.ops.mesh.primitive_circle_add(vertices=6, radius=0.06, fill_type='NGON', location=(x, y, z),
                                          rotation=(tilt, random.uniform(-tilt, tilt), random.uniform(0, 6.3)))
        o = bpy.context.object; o.scale = (1, 0.55, 1); o.data.materials.append(random.choice(leaves))
        return o

    dg = bpy.context.evaluated_depsgraph_get()
    (lx, ly), lr = lake
    for i in range(fallen):
        a = random.uniform(0, math.tau); r = random.uniform(0.6, radius)
        x, y = math.cos(a) * r, math.sin(a) * r
        if (Vector((x, y)) - Vector((lx, ly))).length < lr:
            continue  # not on the lake
        z = _ground(s, dg, x, y, 0.09)
        if z is None:
            continue
        # lie on the grass; each leaf at its own height so overlapping leaves never share a plane (z-fighting)
        leaf(x, y, z + 0.001 + (i % 20) * 0.0004, 0)
    placed = 0
    while placed < drifting:  # drifting in open air (never inside a mountain or a windmill): tagged as flying
        x, y, z = random.uniform(-radius, radius), random.uniform(-radius, radius), random.uniform(0.6, 3.0)
        hit, loc, *_ = s.ray_cast(dg, Vector((x, y, 20)), Vector((0, 0, -1)))
        if hit and loc.z > z - 0.15:
            continue
        leaf(x, y, z, random.uniform(0.3, 1.2))["qa_role"] = "fly"
        placed += 1

    # pumpkins (and a hay bale) standing on the ground
    pump, stem = _mat("#f08a3c", 0.6), _mat("#5a7a3a")
    for x, y, r in pumpkins:
        z = _ground(s, dg, x, y, r * 0.5)  # its squashed bottom rests on a smaller patch
        assert z is not None, f"pumpkin at {(x, y)} is not on open ground"
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, z + r * 0.8))
        o = bpy.context.object; o.scale = (1, 1, 0.8); o.data.materials.append(pump); bpy.ops.object.shade_smooth()
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.015, depth=0.06, location=(x, y, z + r * 1.6))
        bpy.context.object.data.materials.append(stem)
    if hay is not None:
        x, y, ang = hay
        z = _ground(s, dg, x, y, 0.2)
        assert z is not None, f"hay bale at {(x, y)} is not on open ground"
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.2, depth=0.3, location=(x, y, z + 0.2),
                                            rotation=(math.radians(90), 0, math.radians(ang)))
        bpy.context.object.data.materials.append(_mat("#e9c46a", 0.9))
