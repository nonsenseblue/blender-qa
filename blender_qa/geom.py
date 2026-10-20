"""Mesh-accurate geometry: world-space BVH trees per object, penetration, containment and distance.

Bounding boxes are only the broad phase. Everything reported comes from the actual triangles, so
rotated, curved and organic shapes (characters, trees, vehicles, a torus around a pole) are judged
by their real surfaces, not by the box around them.
"""
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

_RAY = Vector((0.0123, 0.0217, 1.0)).normalized()   # slightly skewed so rays don't run along edges


class MeshInfo:
    __slots__ = ("name", "tree", "verts", "tris", "closed", "lo", "hi")

    def __init__(self, name, tree, verts, tris, closed):
        self.name, self.tree, self.verts, self.tris, self.closed = name, tree, verts, tris, closed
        self.lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts))) if verts else Vector()
        self.hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts))) if verts else Vector()

    @property
    def box(self):
        return (self.lo, self.hi)


class MeshCache:
    """Builds (once) a world-space BVH for every object that has geometry: meshes, curves, text."""

    def __init__(self, depsgraph, max_sample=1500):
        self.dg = depsgraph
        self.max_sample = max_sample
        self._cache = {}

    def get(self, obj):
        if obj.name in self._cache:
            return self._cache[obj.name]
        info = None
        ev = obj.evaluated_get(self.dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            me = None
        if me is not None and len(me.polygons):
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.transform(ev.matrix_world)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            closed = all(e.is_manifold for e in bm.edges)
            verts = [v.co.copy() for v in bm.verts]
            tris = [tuple(v.co.copy() for v in f.verts) for f in bm.faces]
            tree = BVHTree.FromBMesh(bm)
            bm.free()
            info = MeshInfo(obj.name, tree, verts, tris, closed)
        if me is not None:
            ev.to_mesh_clear()
        self._cache[obj.name] = info
        return info

    def sample(self, info):
        """Vertices to probe with, thinned out on dense meshes."""
        v = info.verts
        if len(v) <= self.max_sample:
            return v
        step = len(v) / self.max_sample
        return [v[int(i * step)] for i in range(self.max_sample)]


def boxes_near(a, b, tol):
    return all(a.lo[i] - tol <= b.hi[i] and b.lo[i] - tol <= a.hi[i] for i in range(3))


def _plane(tri):
    n = (tri[1] - tri[0]).cross(tri[2] - tri[0])
    if n.length < 1e-12:
        return None, None
    n.normalize()
    return n, n.dot(tri[0])


def _straddles(tri, plane, tol):
    n, d = plane
    if n is None:
        return False
    s = [n.dot(p) - d for p in tri]
    return min(s) < -tol and max(s) > tol


def inside(point, info):
    """Ray-parity test: is `point` inside the closed mesh `info`?"""
    if not info.closed:
        return False
    count, start = 0, point.copy()
    for _ in range(256):
        hit, _n, _i, _d = info.tree.ray_cast(start, _RAY)
        if hit is None:
            break
        count += 1
        start = hit + _RAY * 1e-5
    return count % 2 == 1


def penetration(a, b, tol=0.004):
    """How a and b interpenetrate, or None.

    'cross':    surfaces genuinely pass through each other — a triangle of each straddles the other's
                plane by more than `tol` on both sides (resting/touching faces never do)
    'enclosed': one is completely inside the other (closed) mesh with no surface contact
    """
    if not boxes_near(a, b, -tol):
        return None
    pairs = a.tree.overlap(b.tree)
    for i, j in pairs:
        ta, tb = a.tris[i], b.tris[j]
        if _straddles(ta, _plane(tb), tol) and _straddles(tb, _plane(ta), tol):
            return "cross"
    if not pairs:
        if b.closed and a.verts and inside(a.verts[0], b):
            return "enclosed"
        if a.closed and b.verts and inside(b.verts[0], a):
            return "enclosed"
    return None


def fully_inside(a, b, cache):
    """Every probed vertex of a lies inside closed b (a is hidden by b)."""
    if not b.closed or not boxes_near(a, b, 0):
        return False
    pts = cache.sample(a)
    return bool(pts) and all(inside(p, b) for p in pts)


def distance(a, b, cache, cutoff):
    """Smallest surface-to-surface distance (vertex-to-surface both ways), stopping early once below cutoff."""
    if a.tree.overlap(b.tree):
        return 0.0
    if (b.closed and a.verts and inside(a.verts[0], b)) or (a.closed and b.verts and inside(b.verts[0], a)):
        return 0.0                       # one is inside the other: held, not floating
    best = float("inf")
    for src, dst in ((a, b), (b, a)):
        for p in cache.sample(src):
            hit = dst.tree.find_nearest(p)
            if hit[0] is not None and hit[3] < best:
                best = hit[3]
                if best <= cutoff:
                    return best
    return best
