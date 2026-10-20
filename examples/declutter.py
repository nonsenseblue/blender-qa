# ---------- overlap check (runs in the island namespace right before rendering) ----------
# Decor (trees, shrubs, meadow flowers) that collides with anything solid is removed;
# collisions between two solid features are printed so they can be fixed by hand.
from mathutils import Vector as _V

_dg = bpy.context.evaluated_depsgraph_get()
GROUND_MATS = {"#9fd67c", "#a8744f", "#8a7a70", "#6fc3ee", "big", "small", "tiny", "#ece3d3"}

def _top(o):
    while o.parent is not None:
        o = o.parent
    return o

def _key(o):
    t = _top(o)
    if t is o:
        return None
    return t.name

def _bbox(o):
    e = o.evaluated_get(_dg)
    pts = [e.matrix_world @ _V(c) for c in e.bound_box]
    return (_V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            _V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))

def _hit(a, b, pad=0.012):
    return all(a[0][i] + pad < b[1][i] and b[0][i] + pad < a[1][i] for i in range(3))

def _is_ground(o):
    if o.type == 'CURVE':
        return True
    lo, hi = _bbox(o)
    if hi.x - lo.x > 3 or hi.y - lo.y > 3:
        return True
    m = o.data.materials[0].name.split(".")[0] if getattr(o.data, "materials", None) and o.data.materials and o.data.materials[0] else ""
    return m in GROUND_MATS and not (_key(o) or "").startswith("grp_path")

items = [o for o in s.objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.hide_render]
decor, solids = {}, []
for o in items:
    k = _key(o)
    if o.name.startswith("decor_"):
        decor[o.name] = [o]
    elif k and k.startswith("grp_tree"):
        decor.setdefault(k, []).append(o)
    elif not _is_ground(o):
        solids.append(o)
sbox = [(o, _key(o), _bbox(o)) for o in solids]

removed = 0
for k, objs in decor.items():
    boxes = [_bbox(o) for o in objs]
    if any(_hit(b, sb) for b in boxes for (_, _, sb) in sbox):
        for o in objs:
            bpy.data.objects.remove(o)
        removed += 1
print(f"DECLUTTER removed {removed} decor items")

pairs = {}
# every grouped feature against everything solid (loose objects count as their own feature)
for i in range(len(sbox)):
    o1, _, b1 = sbox[i]
    for j in range(i + 1, len(sbox)):
        o2, g2, b2 = sbox[j]
        g1 = sbox[i][1]
        if not (g1 or g2):
            continue
        k1 = g1 or o1.name; k2 = g2 or o2.name
        if k1 != k2 and _hit(b1, b2):
            pairs.setdefault(tuple(sorted((k1, k2))), (o1.name, o2.name))
for (k1, k2), (n1, n2) in sorted(pairs.items()):
    print(f"OVERLAP {k1} <-> {k2}   ({n1} / {n2})")
print(f"OVERLAP total {len(pairs)}")
