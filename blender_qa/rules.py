"""Domain rule packs. Each takes a checks.Scene and returns issues. Rules only look at tags
(`qa_role`, `qa_front`, `qa_target`), so they apply to any scene that tags its objects — no names.

    interior   seats face what they are for (table / desk / screen / tv / counter)

Add a pack by writing a function and registering it in PACKS.
"""
from mathutils import Vector

FRONT = {"+x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "+y": Vector((0, 1, 0)), "-y": Vector((0, -1, 0))}
SEAT_TARGETS = ("table", "desk", "screen", "tv", "counter")


def _centre(it):
    lo, hi = it["box"]
    return (lo + hi) / 2


def _features(S, roles):
    """One representative item per tagged feature (the tag usually sits on the feature's parent empty)."""
    seen, out = set(), []
    for it in S.items:
        if it["role"] in roles and it["key"] not in seen and it["kind"] != "ignore":
            seen.add(it["key"])
            parts = [p for p in S.items if p["key"] == it["key"]]
            lo = Vector((min(p["box"][0].x for p in parts), min(p["box"][0].y for p in parts), min(p["box"][0].z for p in parts)))
            hi = Vector((max(p["box"][1].x for p in parts), max(p["box"][1].y for p in parts), max(p["box"][1].z for p in parts)))
            out.append({**it, "box": (lo, hi)})
    return out


def interior(S, reach=2.5, min_cos=0.3):
    """Every seat with a qa_front must face its target: qa_target if given, otherwise the nearest
    table/desk/screen/tv/counter within `reach` metres. A chair whose backrest sits between the sitter
    and the desk faces away from it and is reported."""
    from .checks import tag
    issues = []
    targets = _features(S, SEAT_TARGETS)
    for seat in _features(S, ("seat",)):
        front = tag(seat["obj"], "qa_front")
        if front not in FRONT:
            continue
        c = _centre(seat)
        named = tag(seat["obj"], "qa_target")
        cands = [t for t in targets if (named and t["key"] == named) or (not named and t["key"] != seat["key"])]
        if not cands:
            continue
        flat = lambda v: Vector((v.x, v.y, 0))
        best = min(cands, key=lambda t: (flat(_centre(t)) - flat(c)).length)
        d = flat(_centre(best)) - flat(c)
        if d.length > reach and not named:
            continue
        if d.length > 1e-6 and d.normalized().dot(FRONT[front]) < min_cos:
            issues.append({"check": "seat_facing", "a": seat["key"], "target": best["key"],
                           "note": f"{seat['key']} faces {front} but {best['key']} is the other way"})
    return issues


PACKS = {"interior": interior}
