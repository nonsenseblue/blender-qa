"""Small shared props for the example scenes."""
import bpy
from mathutils import Vector


def _link(name, data=None):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    return o


def _rod(a, b, r, m, parent, verts=8):
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)
    o.parent = parent
    return o


def string_lights(points, bulb_mats, wire_mat, wall_normal, wall_gap, r=0.035, wire_r=0.006, name="string_lights"):
    """A string of bulbs that actually hangs from something: a wire through `points` (its sag is up to
    the caller), a bulb hanging under every point, and a hook at each end running back to the wall
    (`wall_normal` points out of the wall toward the wire, `wall_gap` is the wire's distance from the
    wall face: the hooks end exactly on the face, touching it without sinking in). Everything is parented to one empty so checks treat it as one feature."""
    root = _link(name)
    pts = [Vector(p) for p in points]
    for a, b in zip(pts, pts[1:]):
        _rod(a, b, wire_r, wire_mat, root, 6)
    n = Vector(wall_normal).normalized()
    for p in (pts[0], pts[-1]):
        _rod(p, p - n * wall_gap, wire_r * 1.6, wire_mat, root, 6)
    for i, p in enumerate(pts):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=p - Vector((0, 0, wire_r + r - 0.004)),
                                             segments=16, ring_count=8)
        o = bpy.context.object
        o.data.materials.append(bulb_mats[i % len(bulb_mats)])
        bpy.ops.object.shade_smooth()
        o.parent = root
    return root
