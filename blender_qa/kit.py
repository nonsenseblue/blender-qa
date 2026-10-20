"""Small building kit that bakes in the lessons from PITFALLS.md.

- `item("sofa")` groups everything created inside it under one parent empty, which is what the
  checks use to tell features apart.
- Helpers take *semantic* arguments (which way a chair faces, a basin's outline) so the easy
  mistakes — backrest on the wrong side, a "sink" that is a flat plate — cannot happen.
"""
import math
from contextlib import contextmanager
import bpy

_stack = []


@contextmanager
def item(name, role=None, front=None, target=None):
    """with item("desk", role="table"): ...  — every object created inside is parented to an empty
    called `name`. `role` / `front` / `target` become the qa_role / qa_front / qa_target tags the
    rule packs read (e.g. item("chair", role="seat", front="+y"))."""
    g = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(g)
    for k, v in (("qa_role", role), ("qa_front", front), ("qa_target", target)):
        if v is not None:
            g[k] = v
    before = set(bpy.data.objects)
    _stack.append(g)
    try:
        yield g
    finally:
        _stack.pop()
        for o in set(bpy.data.objects) - before:
            if o is not g and o.parent is None:
                o.parent = g


_mats = {}


def mat(hex_color, rough=0.6, emit=0.0):
    """Cached Principled material from a hex colour (sRGB)."""
    key = (hex_color, rough, emit)
    if key in _mats:
        return _mats[key]
    h = hex_color.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)
    m = bpy.data.materials.new(hex_color)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*lin, 1)
        b.inputs["Emission Strength"].default_value = emit
    _mats[key] = m
    return m


def _finish(o, m, bevel):
    if bevel > 0:
        md = o.modifiers.new("bevel", "BEVEL"); md.width = bevel; md.segments = 3; md.limit_method = "ANGLE"
        o.modifiers.new("wn", "WEIGHTED_NORMAL")
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def slab(x0, y0, z0, x1, y1, z1, m, bevel=0.015):
    """Box from its min/max corners. Scale is applied *without* touching location/rotation
    (transform_apply's defaults would move the origin to the world origin)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object
    o.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, m, bevel)


def cyl(c, r, depth, m, verts=32, bevel=0.01, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=c, rotation=rot)
    return _finish(bpy.context.object, m, bevel)


def ball(c, r, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=c, segments=24, ring_count=12)
    o = bpy.context.object; o.scale = scale
    return _finish(o, m, 0)


FACING = {"+x": (-1, 0), "-x": (1, 0), "+y": (0, -1), "-y": (0, 1)}


def chair(x, y, face, frame, seat=None, size=0.44, seat_h=0.45, back_h=0.9):
    """A chair whose sitter looks toward `face` ('+x', '-x', '+y', '-y'); the backrest is always
    on the opposite side, so it can never end up between the sitter and the table."""
    seat = seat or frame
    h = size / 2
    slab(x - h, y - h, seat_h - 0.05, x + h, y + h, seat_h, seat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = x + sx * (h - 0.04), y + sy * (h - 0.04)
            slab(lx - 0.02, ly - 0.02, 0, lx + 0.02, ly + 0.02, seat_h - 0.05, frame, 0.004)
    dx, dy = FACING[face]
    if dx:
        bx = x + dx * (h - 0.02)
        slab(bx - 0.02, y - h, seat_h, bx + 0.02, y + h, back_h, frame)
    else:
        by = y + dy * (h - 0.02)
        slab(x - h, by - 0.02, seat_h, x + h, by + 0.02, back_h, frame)


def basin(x0, y0, x1, y1, z0, z1, m, wall=0.02, drain=None):
    """An open, hollow basin (sink, tub, planter): floor + four walls that butt together without
    sharing faces (no z-fighting), plus a drain. Anything that holds water must be concave."""
    slab(x0 + wall, y0 + wall, z0, x1 - wall, y1 - wall, z0 + wall, m, 0)
    slab(x0, y0, z0, x1, y0 + wall, z1, m, 0); slab(x0, y1 - wall, z0, x1, y1, z1, m, 0)
    slab(x0, y0 + wall, z0, x0 + wall, y1 - wall, z1, m, 0); slab(x1 - wall, y0 + wall, z0, x1, y1 - wall, z1, m, 0)
    if drain is not None:
        cyl(((x0 + x1) / 2, (y0 + y1) / 2, z0 + wall + 0.002), 0.025, 0.004, drain, 16, 0)


def potted_plant(x, y, z, pot, soil, stem, leaf, h=0.9, r=0.18):
    """Pot + soil + leaves on stems that start at the soil — leaves never hover above the rim."""
    cyl((x, y, z + 0.15), r * 0.8, 0.3, pot, 20)
    cyl((x, y, z + 0.302), r * 0.72, 0.008, soil, 20, 0)        # soil on the solid pot inside its rim (below the top it is hidden)
    hz = r * 0.55 * 1.6
    for k in range(5):
        a = k / 5 * math.tau
        lx, ly = x + math.cos(a) * r * 0.35, y + math.sin(a) * r * 0.35
        cz = z + 0.3 + hz * 1.05 + h * 0.12 * (k % 3)           # leaf starts just above the soil
        cyl((lx, ly, (z + 0.3 + cz) / 2), 0.012, cz - z - 0.3, stem, 6, 0)
        ball((lx, ly, cz), r * 0.55, leaf, (0.7, 0.7, 1.6))
