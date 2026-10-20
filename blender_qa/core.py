"""Shared geometry helpers: world-space bounding boxes, grouping and name matching."""
import fnmatch
from mathutils import Vector


def base_name(name):
    """'Cube.012' -> 'Cube' (Blender appends .NNN on name clashes)."""
    head, _, tail = name.rpartition(".")
    return head if head and tail.isdigit() else name


def matches(name, patterns):
    """True if the name (or its base name) matches any glob/substring pattern."""
    for p in patterns or ():
        if any(ch in p for ch in "*?["):
            if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(base_name(name), p):
                return True
        elif p in name:
            return True
    return False


def world_bbox(obj, depsgraph):
    """Axis-aligned bounding box of the evaluated object (modifiers applied) in world space."""
    ev = obj.evaluated_get(depsgraph)
    pts = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def boxes_hit(a, b, pad=0.006):
    """Boxes interpenetrate by more than `pad` on every axis (touching is not a hit)."""
    return all(a[0][i] + pad < b[1][i] and b[0][i] + pad < a[1][i] for i in range(3))


def boxes_touch(a, b, tol=0.012):
    """Boxes overlap or are within `tol` of each other on every axis."""
    return all(a[0][i] - tol <= b[1][i] and b[0][i] - tol <= a[1][i] for i in range(3))


def box_inside(inner, outer, margin=0.002):
    return all(outer[0][i] - margin <= inner[0][i] and inner[1][i] <= outer[1][i] + margin for i in range(3))


def top_ancestor(obj):
    while obj.parent is not None:
        obj = obj.parent
    return obj


def group_key(obj, group_by="parent"):
    """Which feature an object belongs to.

    parent:     the top-most ancestor (wrap each item in a parent empty — see kit.item)
    collection: the first collection the object is linked to
    object:     every object is its own feature
    """
    if group_by == "parent":
        return top_ancestor(obj).name
    if group_by == "collection":
        cols = obj.users_collection
        return cols[0].name if cols else obj.name
    return obj.name


def renderable(scene, types=("MESH", "CURVE", "FONT", "SURFACE", "META")):
    return [o for o in scene.objects if o.type in types and not o.hide_render and o.visible_get()]
