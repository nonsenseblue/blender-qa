"""Scene checks. Each returns a list of plain-dict issues (printable, JSON-serialisable).

Layers
  core      overlap, hidden_inside, floating, zfight, keep_clear, declutter — pure geometry, any scene
  packs     domain rules driven by tags (see rules.py), e.g. "interior": seats face their table/screen

Zero configuration by default:
  * features are grouped automatically (parent hierarchy, else collections, else single objects)
  * ground is recognised from geometry (large and flat), so nothing has to be named "floor"
  * things meant to fly are recognised by common names (cloud, balloon, bird, star, moon...) or a tag

Tags (custom properties on an object or any of its parents) override the guesses:
  qa_role  = ground | anchor | fly | decor | ignore | walkway | door | stairs | seat | table | screen | ...
  qa_front = +x | -x | +y | -y        (which way a seat / screen / door faces)
"""
from collections import defaultdict
from mathutils import Vector
from . import geom
from .core import matches, world_bbox, boxes_hit, renderable

DEFAULTS = {
    "group_by": "auto",          # auto | parent | collection | object
    "ground": ("floor", "ground", "terrain", "water", "river", "lake", "pond", "sea", "ocean"),
    "ground_auto": True,         # recognise large flat objects as ground
    "anchors": (),               # extra things everything may rest on (walls are found through contact)
    "ground_z": None,            # anything whose bottom is at this height counts as resting on the floor
    "ignore": (),                # skipped entirely
    "allow_float": ("cloud", "balloon", "bird", "star", "moon", "sun", "firefl", "snowflake", "flake",
                    "particle", "sky", "halo", "glow", "smoke", "mist", "camera"),
    "decor": ("decor",),         # scattered decor that yields to solids
    "accurate": True,            # mesh-accurate (BVH); False = bounding boxes only (fast, coarse)
    "tol": 0.004,                # penetration tolerance (m)
    "contact_tol": 0.012,        # how close counts as touching (m)
    "intra": True,               # report parts hidden inside a closed part of the same feature
    "keep_clear": (),            # ((x0,y0,z0),(x1,y1,z1),label) zones that must stay empty
    "zfight": True,
    "zfight_min_area": 1e-4,     # seams smaller than this (m², 1 cm²) are below a pixel in normal renders
    "views": None,               # only z-fight-test faces visible from these view names
    "packs": ("interior",),      # tag-driven rule packs to run
}

FLAT_RATIO = 0.3                 # ground: thickness <= 0.3 * its larger horizontal size
GROUND_SHARE = 0.25              # ground: horizontal size >= 25% of the scene's
COLLECTION_SHARE = 0.2           # a collection holding more than this share of the scene is a "layer", not a feature


def tag(obj, key):
    o = obj
    while o is not None:
        if key in o.keys():
            return str(o[key])
        o = o.parent
    return None


def _top(obj):
    while obj.parent is not None:
        obj = obj.parent
    return obj


def feature_key(obj, group_by="auto", total=None):
    """Which feature an object belongs to. auto: its top parent if it has one, else a small collection
    it lives in, else itself (a "loose" object, see Scene)."""
    if group_by in ("auto", "parent"):
        top = _top(obj)
        if top is not obj or group_by == "parent":
            return top.name
    cols = [c for c in obj.users_collection if c.name != "Scene Collection"]
    if group_by == "collection" and cols:
        return cols[0].name
    if group_by == "auto" and cols and total and len(cols[0].all_objects) <= COLLECTION_SHARE * total:
        return cols[0].name
    return obj.name


def _names(obj, key):
    """Everything a name pattern is matched against: the object, its parents, its feature, its materials."""
    out, o = [key], obj
    while o is not None:
        out.append(o.name)
        o = o.parent
    out += [m.name for m in getattr(obj.data, "materials", ()) if m is not None]
    return out


class Scene:
    """Classified view of a scene: ground / fly / decor / ignore / solid, with feature keys and meshes.

    Objects that belong to no feature ("loose": no parent, no small collection) are clustered: loose
    objects of the same material that interpenetrate are taken to be one thing built from several
    primitives (a tree crown from three spheres). Clashes involving loose objects are reported as
    warnings, because without grouping a deliberate join cannot be told from a collision."""

    def __init__(self, scene, depsgraph, cfg):
        self.cfg = cfg
        self.dg = depsgraph
        self.meshes = geom.MeshCache(depsgraph)
        objs = renderable(scene)
        self.items = []
        boxes = {o.name: world_bbox(o, depsgraph) for o in objs}
        if cfg["accurate"]:   # the evaluated mesh's own extent (bound_box of text/curves misses extrusion)
            for o in objs:
                m = self.meshes.get(o)
                if m is not None:
                    boxes[o.name] = (m.lo.copy(), m.hi.copy())
        span = 1.0
        if boxes:
            span = max(max(b[1].x for b in boxes.values()) - min(b[0].x for b in boxes.values()),
                       max(b[1].y for b in boxes.values()) - min(b[0].y for b in boxes.values()), 1e-6)
        for o in objs:
            key = feature_key(o, cfg["group_by"], len(objs))
            role = tag(o, "qa_role")
            lo, hi = boxes[o.name]
            size = hi - lo
            horiz = max(size.x, size.y)
            names = _names(o, key)
            hit = lambda pats: any(matches(n, pats) for n in names)
            if role == "ignore" or hit(cfg["ignore"]):
                kind = "ignore"
            elif role in ("ground", "anchor") or (role is None and hit(cfg["ground"])):
                kind = "ground"
            elif role == "fly" or (role is None and hit(cfg["allow_float"])):
                kind = "fly"
            elif role == "decor" or (role is None and hit(cfg["decor"])):
                kind = "decor"
            elif cfg["ground_auto"] and role is None and horiz >= GROUND_SHARE * span and size.z <= FLAT_RATIO * horiz:
                kind = "ground"
            else:
                kind = "solid"
            loose = key == o.name and o.parent is None and not o.children
            self.items.append({"obj": o, "key": key, "role": role, "kind": kind, "box": (lo, hi), "loose": loose})
        self._cluster_loose()

    def _cluster_loose(self):
        loose = [it for it in self.items if it["loose"] and it["kind"] in ("solid", "fly", "decor")]
        mat = lambda it: it["obj"].active_material.name if it["obj"].active_material else None
        root = {it["obj"].name: it["obj"].name for it in loose}

        def find(n):
            while root[n] != n:
                root[n] = root[root[n]]
                n = root[n]
            return n
        for i, a in enumerate(loose):
            for b in loose[i + 1:]:
                if mat(a) is not None and mat(a) == mat(b) and a["kind"] == b["kind"] and _penetrates(self, a, b):
                    root[find(b["obj"].name)] = find(a["obj"].name)
        for it in loose:
            it["key"] = find(it["obj"].name)

    def mesh(self, item):
        return self.meshes.get(item["obj"])

    def of(self, *kinds):
        return [it for it in self.items if it["kind"] in kinds]


def _penetrates(S, a, b):
    cfg = S.cfg
    if not boxes_hit(a["box"], b["box"], cfg["tol"]):
        return None
    if not cfg["accurate"]:
        return "box"
    ma, mb = S.mesh(a), S.mesh(b)
    if ma is None or mb is None:
        return "box"
    return geom.penetration(ma, mb, cfg["tol"])


def overlap(S):
    """Different features interpenetrating."""
    issues, seen = [], set()
    solids = S.of("solid", "fly")
    for i in range(len(solids)):
        a = solids[i]
        for j in range(i + 1, len(solids)):
            b = solids[j]
            if a["key"] == b["key"]:
                continue
            pair = tuple(sorted((a["key"], b["key"])))
            if pair in seen:
                continue
            how = _penetrates(S, a, b)
            if how:
                seen.add(pair)
                issues.append({"check": "overlap", "level": "warn" if a["loose"] or b["loose"] else "error",
                               "a": pair[0], "b": pair[1], "how": how,
                               "objects": [a["obj"].name, b["obj"].name],
                               "where": [round(v, 3) for v in (a["box"][0] + a["box"][1]) / 2]})
    return issues


def hidden_inside(S):
    """A part entirely inside a closed part of the same feature (books in a solid shelf, water in a solid tub)."""
    issues = []
    by_key = defaultdict(list)
    for it in S.of("solid"):
        by_key[it["key"]].append(it)
    for key, parts in by_key.items():
        for a in parts:
            for b in parts:
                if a is b or not boxes_hit(a["box"], b["box"], 0):
                    continue
                ma, mb = S.mesh(a), S.mesh(b)
                if ma is None or mb is None:
                    continue
                if (ma.hi - ma.lo).length < (mb.hi - mb.lo).length and geom.fully_inside(ma, mb, S.meshes):
                    issues.append({"check": "hidden_inside", "level": "warn" if a["loose"] else "error", "a": key, "objects": [a["obj"].name, b["obj"].name],
                                   "note": f"{a['obj'].name} is completely inside the closed {b['obj'].name}"})
    return issues


def _zone_info(lo, hi):
    import bmesh
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector([lo[i] + (v.co[i] + 0.5) * (hi[i] - lo[i]) for i in range(3)])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    info = geom.MeshInfo("zone", BVHTree.FromBMesh(bm), [v.co.copy() for v in bm.verts],
                         [tuple(v.co.copy() for v in f.verts) for f in bm.faces], True)
    bm.free()
    return info


def keep_clear(S):
    """Zones that must stay walkable: from the config, and from objects tagged walkway / door / stairs
    (their footprint extruded 2 m up)."""
    zones = [(Vector(lo), Vector(hi), label) for lo, hi, label in S.cfg["keep_clear"]]
    zone_owner = {}
    for it in S.items:
        if it["role"] in ("walkway", "door", "stairs"):
            lo, hi = it["box"]
            label = f"{it['role']}:{it['key']}"
            zones.append((Vector((lo.x, lo.y, lo.z + S.cfg["contact_tol"])), Vector((hi.x, hi.y, hi.z + 2.0)), label))
            zone_owner[label] = it["key"]
    found = {}
    for lo, hi, label in zones:
        zinfo = _zone_info(lo, hi)
        for it in S.of("solid", "decor"):
            if it["role"] in ("walkway", "door", "stairs") or it["key"] == zone_owner.get(label):
                continue
            if not boxes_hit(it["box"], (lo, hi), S.cfg["tol"]):
                continue
            m = S.mesh(it)
            if m is not None and S.cfg["accurate"]:
                inside_pts = any(all(lo[i] + S.cfg["tol"] < p[i] < hi[i] - S.cfg["tol"] for i in range(3))
                                 for p in S.meshes.sample(m))
                if not (inside_pts or geom.penetration(m, zinfo, S.cfg["tol"])):
                    continue
            found[(label, it["key"])] = {"check": "keep_clear", "zone": label, "a": it["key"], "objects": [it["obj"].name]}
    return list(found.values())


def floating(S):
    """Objects not connected (by touching) to anything grounded. Fly objects are exempt and hold up
    what is attached to them (craters on a moon, a basket under a balloon)."""
    cfg = S.cfg
    tol = cfg["contact_tol"]
    nodes = S.of("ground", "solid", "decor", "fly")
    supported = set()
    for it in nodes:
        if (it["kind"] in ("ground", "fly") or matches(it["obj"].name, cfg["anchors"]) or matches(it["key"], cfg["anchors"])
                or (cfg["ground_z"] is not None and it["box"][0].z <= cfg["ground_z"] + tol)):
            supported.add(it["obj"].name)
    by_name = {it["obj"].name: it for it in nodes}
    stack = list(supported)
    while stack:
        a = by_name[stack.pop()]
        for b in nodes:
            n = b["obj"].name
            if n in supported:
                continue
            if not all(a["box"][0][i] - tol <= b["box"][1][i] and b["box"][0][i] - tol <= a["box"][1][i] for i in range(3)):
                continue
            if cfg["accurate"]:
                ma, mb = S.mesh(a), S.mesh(b)
                if ma is not None and mb is not None and geom.distance(ma, mb, S.meshes, tol) > tol:
                    continue
            supported.add(n)
            stack.append(n)
    return [{"check": "floating", "a": it["key"], "objects": [it["obj"].name],
             "bottom": [round(v, 3) for v in it["box"][0]]}
            for it in nodes if it["obj"].name not in supported]


def declutter(S, remove=True):
    """Decor that collides with a solid yields: the whole decor feature is removed (or only reported)."""
    import bpy
    groups = defaultdict(list)
    for it in S.of("decor"):
        groups[it["key"]].append(it)
    solids = S.of("solid")
    issues = []
    for key, parts in groups.items():
        blocker = next((s["obj"].name for p in parts for s in solids
                        if s["key"] != key and _penetrates(S, p, s)), None)
        if blocker:
            issues.append({"check": "declutter", "a": key, "blocked_by": blocker, "removed": remove})
            if remove:
                for p in parts:
                    bpy.data.objects.remove(p["obj"])
    return issues


VIEW_DIRS = {"front": (1, -1, 1), "back": (-1, 1, 1), "left": (-1, -1, 1), "right": (1, 1, 1), "top": (0, 0, 1)}


def zfight(S, tol=1e-4, min_area=None, skip_down=True):
    """Coplanar, overlapping, same-facing faces of different objects and materials that are not pressed
    against something else — they flicker and render as black seams/dots. Axis-aligned faces only."""
    views = S.cfg["views"]
    min_area = S.cfg["zfight_min_area"] if min_area is None else min_area
    cams = [Vector(VIEW_DIRS[v]).normalized() for v in views] if views else None
    faces, allfaces = defaultdict(list), defaultdict(list)
    for it in S.items:
        if it["kind"] == "ignore" or it["obj"].type != "MESH":
            continue
        o = it["obj"]
        ev = o.evaluated_get(S.dg)
        me = ev.to_mesh()
        mw = ev.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        for p in me.polygons:
            if p.area < 1e-9:      # degenerate faces (bevels collapse some) have meaningless normals
                continue
            n = (nm @ p.normal).normalized()
            axis = max(range(3), key=lambda i: abs(n[i]))
            if abs(n[axis]) < 0.999:
                continue
            pts = [mw @ me.vertices[i].co for i in p.vertices]
            plane = round(sum(q[axis] for q in pts) / len(pts) / tol) * tol
            u, v = [i for i in range(3) if i != axis]
            rect = (min(q[u] for q in pts), min(q[v] for q in pts), max(q[u] for q in pts), max(q[v] for q in pts))
            key = (axis, 1 if n[axis] > 0 else -1, round(plane, 5))
            entry = (o.name, rect, p.material_index < len(o.material_slots) and o.material_slots[p.material_index].material)
            allfaces[key].append(entry)
            if skip_down and axis == 2 and n[2] < 0:
                continue
            if cams and not any(n.dot(c) > 0.05 for c in cams):
                continue
            faces[key].append(entry)
        ev.to_mesh_clear()

    def pressed(key, rect, owners):
        area = (rect[2] - rect[0]) * (rect[3] - rect[1])
        for n, r, _m in allfaces.get((key[0], -key[1], key[2]), ()):
            if n in owners:
                continue
            du = min(rect[2], r[2]) - max(rect[0], r[0]); dv = min(rect[3], r[3]) - max(rect[1], r[1])
            if du > 0 and dv > 0 and du * dv >= 0.5 * area:   # 0.5: bevels shrink the flat part of faces
                return True
        return False

    solids = [it for it in S.items if it["kind"] != "ignore"]

    def buried(key, rect, owners):
        """The seam lies inside some other closed solid (a frame or cap covering both tops): invisible."""
        u, v = [i for i in range(3) if i != key[0]]
        p = Vector((0, 0, 0))
        p[key[0]] = key[2] + key[1] * 0.001
        p[u], p[v] = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        for it in solids:
            lo, hi = it["box"]
            if it["obj"].name in owners or not all(lo[i] < p[i] < hi[i] for i in range(3)):
                continue
            m = S.mesh(it)
            if m is not None and geom.inside(p, m):
                return True
        return False

    issues, seen = [], set()
    for key, lst in faces.items():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda r: r[1][0])
        for i in range(len(lst)):
            n1, r1, m1 = lst[i]
            for j in range(i + 1, len(lst)):
                n2, r2, m2 = lst[j]
                if r2[0] >= r1[2]:
                    break
                if n1 == n2 or (m1 and m1 == m2):   # same material: the flicker is invisible
                    continue
                du = min(r1[2], r2[2]) - max(r1[0], r2[0]); dv = min(r1[3], r2[3]) - max(r1[1], r2[1])
                if du > tol and dv > tol and du * dv > min_area:
                    inter = (max(r1[0], r2[0]), max(r1[1], r2[1]), min(r1[2], r2[2]), min(r1[3], r2[3]))
                    if pressed(key, inter, (n1, n2)) or buried(key, inter, (n1, n2)):
                        continue
                    pair = tuple(sorted((n1, n2)))
                    if pair not in seen:
                        seen.add(pair)
                        issues.append({"check": "zfight", "objects": list(pair), "axis": "xyz"[key[0]],
                                       "plane": key[2], "area": round(du * dv, 5)})
    issues.sort(key=lambda i: -i["area"])
    return issues


def config(**overrides):
    cfg = dict(DEFAULTS)
    for k, v in overrides.items():
        if v is None:
            continue
        if k not in DEFAULTS:
            raise KeyError(f"unknown setting {k!r}")
        cfg[k] = tuple(v) if isinstance(v, list) and k != "keep_clear" else v
    return cfg


def run_all(scene, depsgraph, **overrides):
    """Every core check plus the configured rule packs. Returns a list of issues, each with a level:
    "error" (a definite defect) or "warn" (involves loose objects, so it may be deliberate)."""
    from . import rules
    cfg = config(**overrides)
    S = Scene(scene, depsgraph, cfg)
    issues = overlap(S) + keep_clear(S) + floating(S)
    if cfg["intra"]:
        issues += hidden_inside(S)
    if cfg["zfight"]:
        issues += zfight(S)
    for pack in cfg["packs"] or ():
        issues += rules.PACKS[pack](S)
    for it in issues:
        it.setdefault("level", "error")
    return issues
