"""Automatic scene checks. Each returns a list of plain-dict issues so they can be printed or saved as JSON.

All checks work on world-space axis-aligned bounding boxes of evaluated objects, grouped into
"features" (by default: everything under the same top-level parent). That is coarse on purpose:
it is fast, needs no setup beyond grouping, and catches the mistakes that actually happen
(things inside each other, things in mid-air, decor in the way). Diagonal or curved shapes can
give false positives — review the report, do not blindly trust or ignore it.
"""
from collections import defaultdict
from mathutils import Vector
from .core import (matches, world_bbox, boxes_hit, boxes_touch, box_inside, group_key, renderable)


def _classify(scene, depsgraph, group_by, ground, ground_size, ignore):
    """Split renderable objects into ground (floors, terrain, water...) and solids, with their boxes."""
    ground_objs, solids = [], []
    for o in renderable(scene):
        if matches(o.name, ignore) or matches(group_key(o, group_by), ignore):
            continue
        bb = world_bbox(o, depsgraph)
        size = bb[1] - bb[0]
        is_ground = (matches(o.name, ground) or matches(group_key(o, group_by), ground)
                     or (ground_size and (size.x > ground_size or size.y > ground_size)))
        (ground_objs if is_ground else solids).append((o, group_key(o, group_by), bb))
    return ground_objs, solids


def overlap(scene, depsgraph, group_by="parent", ground=(), ground_size=3.0, ignore=(), pad=0.006,
            intra=False, keep_clear=()):
    """Interpenetration between different features.

    ground:      name patterns of floors/terrain/water that things are allowed to sit in
    ground_size: anything wider than this (metres) also counts as ground
    ignore:      patterns skipped entirely (rugs, mats, lights' geometry...)
    intra:       also report parts of one feature that are completely hidden inside another part
                 of the same feature (books inside a solid bookshelf, water inside a solid tub)
    keep_clear:  boxes ((x0,y0,z0),(x1,y1,z1), label) that must stay empty: stair landings, doorways
    """
    _, solids = _classify(scene, depsgraph, group_by, ground, ground_size, ignore)
    issues, seen = [], set()
    for i in range(len(solids)):
        o1, k1, b1 = solids[i]
        for j in range(i + 1, len(solids)):
            o2, k2, b2 = solids[j]
            if k1 == k2:
                continue
            key = tuple(sorted((k1, k2)))
            if key in seen or not boxes_hit(b1, b2, pad):
                continue
            seen.add(key)
            issues.append({"check": "overlap", "a": key[0], "b": key[1], "objects": [o1.name, o2.name],
                           "where": [round(v, 3) for v in (b1[0] + b1[1]) / 2]})
    if intra:
        by_group = defaultdict(list)
        for o, k, b in solids:
            by_group[k].append((o, b))
        for k, parts in by_group.items():
            for o1, b1 in parts:
                for o2, b2 in parts:
                    if (o1 is not o2 and box_inside(b1, b2) and (b1[1] - b1[0]).length < (b2[1] - b2[0]).length
                            and _boxiness(o2, depsgraph, b2) > 0.85):
                        issues.append({"check": "hidden_inside", "a": k, "objects": [o1.name, o2.name],
                                       "note": f"{o1.name} sits entirely inside {o2.name} — is {o2.name} solid?"})
    for (lo, hi, label) in keep_clear:
        zone = (Vector(lo), Vector(hi))
        hits = sorted({k for o, k, b in solids if boxes_hit(b, zone, pad)})
        for k in hits:
            issues.append({"check": "keep_clear", "zone": label, "a": k})
    return issues


def _boxiness(obj, depsgraph, bb):
    """Mesh volume / bounding-box volume: ~1 for a solid box (hides whatever is inside it),
    ~0.79 for a cylinder, ~0.52 for a sphere, 0 for open or flat geometry."""
    import bmesh
    if obj.type != "MESH":
        return 0.0
    size = bb[1] - bb[0]
    box_vol = size.x * size.y * size.z
    if box_vol <= 1e-9:
        return 0.0
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    bm.transform(ev.matrix_world)
    vol = abs(bm.calc_volume()) if all(e.is_manifold for e in bm.edges) else 0.0
    bm.free(); ev.to_mesh_clear()
    return vol / box_vol


def floating(scene, depsgraph, anchors=(), ground_z=None, tol=0.012, allow=(), group_by="parent"):
    """Objects not connected (by touching, within `tol`) to anything anchored.

    Anchors are objects matching `anchors` patterns (floor, walls, terrain) and, when `ground_z` is
    given, anything whose bottom is within `tol` of that height. Everything touching an anchor is
    supported, and so on transitively. What is left is floating: leaves above a pot, a handle a
    centimetre off a door, a step hanging in space. `allow` lists things meant to fly (clouds,
    balloons, stars, fireflies).
    """
    objs = [o for o in renderable(scene) if not matches(o.name, allow) and not matches(group_key(o, group_by), allow)]
    bb = {o.name: world_bbox(o, depsgraph) for o in objs}
    supported = {o.name for o in objs
                 if matches(o.name, anchors) or matches(group_key(o, group_by), anchors)
                 or (ground_z is not None and bb[o.name][0].z <= ground_z + tol)}
    stack = list(supported)
    while stack:
        n = stack.pop()
        for o in objs:
            if o.name not in supported and boxes_touch(bb[n], bb[o.name], tol):
                supported.add(o.name)
                stack.append(o.name)
    return [{"check": "floating", "a": group_key(o, group_by), "objects": [o.name],
             "bottom": [round(v, 3) for v in bb[o.name][0]]}
            for o in objs if o.name not in supported]


VIEW_DIRS = {"front": (1, -1, 1), "back": (-1, 1, 1), "left": (-1, -1, 1), "right": (1, 1, 1), "top": (0, 0, 1)}


def zfight(scene, depsgraph, tol=1e-4, min_area=1e-5, ignore=(), group_by="object", skip_down=True, views=None):
    """Coplanar, overlapping, same-facing faces of different objects — they flicker and render as
    black seams/dots. Only axis-aligned faces are tested (boxes, slabs, walls), which is where it
    happens in practice.

    skip_down: ignore downward faces (bottoms resting on a floor are never seen)
    views:     only test faces visible from these camera directions (see VIEW_DIRS), e.g. ("front", "left")
    """
    from mathutils import Vector as V
    cams = [V(VIEW_DIRS[v]).normalized() for v in views] if views else None
    faces = defaultdict(list)       # faces to test: (axis, sign, plane) -> [(owner, name, (u0, v0, u1, v1))]
    allfaces = defaultdict(list)    # every axis-aligned face, used to decide what is pressed flat against something
    for o in renderable(scene, types=("MESH",)):
        if matches(o.name, ignore):
            continue
        ev = o.evaluated_get(depsgraph)
        me = ev.to_mesh()
        mw = ev.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        for p in me.polygons:
            n = (nm @ p.normal).normalized()
            axis = max(range(3), key=lambda i: abs(n[i]))
            if abs(n[axis]) < 0.999:
                continue
            pts = [mw @ me.vertices[i].co for i in p.vertices]
            plane = round(sum(q[axis] for q in pts) / len(pts) / tol) * tol
            u, v = [i for i in range(3) if i != axis]
            rect = (min(q[u] for q in pts), min(q[v] for q in pts), max(q[u] for q in pts), max(q[v] for q in pts))
            key = (axis, 1 if n[axis] > 0 else -1, round(plane, 5))
            entry = (group_key(o, group_by), o.name, rect)
            allfaces[key].append(entry)
            if skip_down and axis == 2 and n[2] < 0:
                continue
            if cams and not any(n.dot(c) > 0.05 for c in cams):
                continue
            faces[key].append(entry)
        ev.to_mesh_clear()
    def pressed(key, rect, owners):
        """The overlap region lies flat against an opposite-facing face of some other object
        (e.g. two boards both pressed against a wall): hidden, so it cannot flicker."""
        area = (rect[2] - rect[0]) * (rect[3] - rect[1])
        for k, n, r in allfaces.get((key[0], -key[1], key[2]), ()):
            if n in owners:
                continue
            du = min(rect[2], r[2]) - max(rect[0], r[0]); dv = min(rect[3], r[3]) - max(rect[1], r[1])
            if du > 0 and dv > 0 and du * dv >= 0.5 * area:   # 0.5: bevels shrink the flat part of faces
                return True
        return False

    issues, seen = [], set()
    for key, lst in faces.items():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda r: r[2][0])
        for i in range(len(lst)):
            k1, n1, r1 = lst[i]
            for j in range(i + 1, len(lst)):
                k2, n2, r2 = lst[j]
                if r2[0] >= r1[2]:
                    break
                if k1 == k2:
                    continue
                du = min(r1[2], r2[2]) - max(r1[0], r2[0]); dv = min(r1[3], r2[3]) - max(r1[1], r2[1])
                if du > tol and dv > tol and du * dv > min_area:
                    inter = (max(r1[0], r2[0]), max(r1[1], r2[1]), min(r1[2], r2[2]), min(r1[3], r2[3]))
                    if pressed(key, inter, (n1, n2)):
                        continue
                    pair = tuple(sorted((n1, n2)))
                    if pair not in seen:
                        seen.add(pair)
                        issues.append({"check": "zfight", "objects": list(pair), "axis": "xyz"[key[0]],
                                       "plane": key[2], "area": round(du * dv, 5)})
    issues.sort(key=lambda i: -i["area"])
    return issues


def declutter(scene, depsgraph, decor=(), ground=(), ground_size=3.0, ignore=(), group_by="parent", pad=0.006,
              remove=True):
    """Decor (shrubs, flowers, pebbles, scattered trees) that collides with anything solid yields:
    the whole decor feature is removed (or just reported with remove=False)."""
    _, solids = _classify(scene, depsgraph, group_by, ground, ground_size, ignore)
    decor_groups = defaultdict(list)
    rest = []
    for o, k, b in solids:
        if matches(o.name, decor) or matches(k, decor):
            decor_groups[k].append((o, b))
        else:
            rest.append((o, k, b))
    issues = []
    for k, parts in decor_groups.items():
        hit = next(((o2.name) for o, b in parts for (o2, k2, b2) in rest if boxes_hit(b, b2, pad)), None)
        if hit:
            issues.append({"check": "declutter", "a": k, "blocked_by": hit, "removed": remove})
            if remove:
                import bpy
                for o, _ in parts:
                    bpy.data.objects.remove(o)
    return issues


def run_all(scene, depsgraph, **cfg):
    """Run overlap + floating + zfight with one config dict (see cli.py for the keys)."""
    issues = []
    issues += overlap(scene, depsgraph, group_by=cfg.get("group_by", "parent"), ground=cfg.get("ground", ()),
                      ground_size=cfg.get("ground_size", 3.0), ignore=cfg.get("ignore", ()),
                      intra=cfg.get("intra", True), keep_clear=cfg.get("keep_clear", ()))
    issues += floating(scene, depsgraph, anchors=cfg.get("anchors", ()), ground_z=cfg.get("ground_z"),
                       allow=cfg.get("allow_float", ()), group_by=cfg.get("group_by", "parent"))
    if cfg.get("zfight", True):
        issues += zfight(scene, depsgraph, ignore=cfg.get("ignore", ()), views=cfg.get("views"))
    return issues
