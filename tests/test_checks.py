"""Small procedural scenes, each with known defects (or deliberately none), checked against every detector.
Covers shapes bounding boxes get wrong (torus around a pole, rotated boxes, spheres), zero-config
ground detection, flying things, rule packs and the fast (box-only) mode.
Run:  python tests/test_checks.py   (needs the `bpy` module: pip install bpy)"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy
from blender_qa import checks
from blender_qa.kit import item, slab, cyl, ball, chair, mat

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from blender_qa import kit
    kit._mats.clear()
    return mat("#cccccc")


def run(**cfg):
    dg = bpy.context.evaluated_depsgraph_get()
    return checks.run_all(bpy.context.scene, dg, **cfg)


def pairs(issues, check):
    return {frozenset((i["a"], i.get("b"))) for i in issues if i["check"] == check}


def keys(issues, check):
    return {i["a"] for i in issues if i["check"] == check}


@case
def classic_defects():
    M = fresh()
    with item("base"):                       # not named "floor": recognised as ground by its shape
        slab(-5, -5, -0.2, 5, 5, 0, M)
    with item("table"):
        slab(0, 0, 0.7, 1, 1, 0.75, M)
        slab(0, 0, 0, 0.05, 0.05, 0.7, M)
    with item("crate"):                      # DEFECT overlap: pushed into the table top
        slab(0.8, 0.8, 0.6, 1.3, 1.3, 1.1, M)
    with item("shelf_solid"):                # DEFECT hidden_inside: book inside a solid shelf
        slab(3, 0, 0, 3.4, 1, 1.8, M)
        slab(3.1, 0.2, 0.3, 3.3, 0.3, 0.6, M)
    with item("lamp"):                       # DEFECT floating: shade hovers above its stand
        slab(-2, -2, 0, -1.9, -1.9, 1.0, M)
        slab(-2.2, -2.2, 1.2, -1.7, -1.7, 1.4, M)
    with item("panel_a"):                    # DEFECT zfight: two boxes sharing a coplanar top face
        slab(-3, 2, 0, -2, 3, 0.5, M, 0)
    with item("panel_b"):                    # (a different material: same-material seams are invisible)
        slab(-2.6, 2.2, 0.3, -1.8, 2.8, 0.5, mat("#cc6666"), 0)
    with item("stairs", role="stairs"):      # a tagged stair keeps the space above it clear
        slab(1.8, -3.2, 0, 2.6, -2.4, 0.2, M)
    with item("plant"):                      # DEFECT keep_clear: blocks the stairs
        slab(2, -3, 0.2, 2.3, -2.7, 0.8, M)
    with item("cloud"):                      # flies by name: never "floating"
        ball((0, 0, 4), 0.5, M)
    with item("balloon"):                    # a basket (its own feature) hanging under a flying envelope
        ball((3, 3, 4), 0.5, M)              # is held up by it
    with item("basket"):
        slab(2.9, 2.9, 3.4, 3.1, 3.1, 3.5, mat("#8a5a3c"), 0)
    with item("kite_tail"):                  # but a part hanging next to it in mid-air is not
        slab(4, 4, 3, 4.1, 4.1, 3.1, M, 0)
    iss = run()
    assert frozenset(("crate", "table")) in pairs(iss, "overlap"), iss
    assert "shelf_solid" in keys(iss, "hidden_inside"), iss
    assert keys(iss, "floating") == {"lamp", "kite_tail"}, iss
    assert keys(iss, "keep_clear") == {"plant"}, iss
    zf = [i for i in iss if i["check"] == "zfight"]
    names_b = {o.name for o in bpy.data.objects if o.parent and o.parent.name == "panel_b"}
    assert any(set(z["objects"]) & names_b for z in zf), zf
    assert pairs(iss, "overlap") == {frozenset(("crate", "table")), frozenset(("panel_a", "panel_b"))}, iss
    # without automatic ground every feature would float
    iss2 = run(ground_auto=False, zfight=False)
    assert "table" in keys(iss2, "floating"), iss2
    # telling it the floor name brings it back
    iss3 = run(ground_auto=False, ground=("base",), zfight=False)
    assert keys(iss3, "floating") == {"lamp", "kite_tail"}, iss3


@case
def curved_and_rotated_no_false_alarms():
    """Box-overlapping but not touching: ring around a pole, two rotated boards, two spheres touching."""
    M = fresh()
    with item("ground"):
        slab(-6, -6, -0.1, 6, 6, 0, M, 0)
    with item("pole"):
        cyl((0, 0, 1), 0.08, 2, M, 24, 0)
    with item("ring"):                       # lies on the floor around the pole, never touches it
        bpy.ops.mesh.primitive_torus_add(major_radius=0.5, minor_radius=0.1, location=(0, 0, 0.1))
        bpy.context.object.data.materials.append(M)
    for n, x in (("board_a", 2.0), ("board_b", 2.5)):   # 45° boards: boxes overlap, solids don't
        with item(n):
            o = slab(x - 0.4, -0.05, 0, x + 0.4, 0.05, 1.0, M, 0)
            o.rotation_euler.z = math.radians(45)
    with item("ball_a"):                     # resting on the floor, touching each other at one point
        ball((-2, 0, 0.3), 0.3, M)
    with item("ball_b"):
        ball((-1.4, 0, 0.3), 0.3, M)
    iss = run(zfight=False)
    assert not pairs(iss, "overlap"), iss
    assert not keys(iss, "floating"), iss
    # bounding boxes alone get this wrong
    fast = run(zfight=False, accurate=False)
    assert frozenset(("pole", "ring")) in pairs(fast, "overlap"), fast
    assert frozenset(("board_a", "board_b")) in pairs(fast, "overlap"), fast


@case
def real_penetrations():
    M = fresh()
    with item("ground"):
        slab(-6, -6, -0.1, 6, 6, 0, M, 0)
    with item("pole"):                       # DEFECT: pole straight through a shelf board
        cyl((0, 0, 1), 0.05, 2, M, 16, 0)
    with item("board"):
        slab(-0.5, -0.3, 0.9, 0.5, 0.3, 0.95, M, 0)
    with item("cabinet"):                    # DEFECT: a whole box sealed inside another feature
        slab(2, 0, 0, 3, 1, 1, M, 0)
    with item("parcel"):
        slab(2.3, 0.3, 0.3, 2.6, 0.6, 0.6, M, 0)
    with item("tilted"):                     # DEFECT: rotated plank poking into a wall
        o = slab(-3.5, -0.05, 0, -2.5, 0.05, 1.5, M, 0)
        o.rotation_euler.z = math.radians(30)
    with item("wall"):
        slab(-2.9, -1, 0, -2.8, 1, 2, M, 0)
    iss = run(zfight=False)
    ov = {i["a"] + "+" + i["b"]: i["how"] for i in iss if i["check"] == "overlap"}
    assert ov.get("board+pole") == "cross", ov
    assert ov.get("cabinet+parcel") == "enclosed", ov
    assert ov.get("tilted+wall") == "cross", ov
    assert len(ov) == 3, ov


@case
def seats_face_their_table():
    M = fresh()
    with item("ground"):
        slab(-6, -6, -0.1, 6, 6, 0, M, 0)
    with item("desk", role="table"):
        slab(0, 1, 0.72, 1.2, 1.7, 0.76, M, 0)
        for x in (0.02, 1.13):
            slab(x, 1.02, 0, x + 0.05, 1.68, 0.72, M, 0)
    with item("good_chair", role="seat", front="+y"):     # sitter looks at the desk
        chair(0.4, 0.6, "+y", M)
    with item("bad_chair", role="seat", front="-y"):      # DEFECT: backrest toward the desk
        chair(0.9, 0.6, "-y", M)
    iss = run(zfight=False)
    assert keys(iss, "seat_facing") == {"bad_chair"}, iss
    assert not keys(run(zfight=False, packs=()), "seat_facing"), "packs=() runs no rules"


@case
def flat_rug_and_decor():
    """A rug lying on the floor and decor in a shrub ring: neither is ground, the shrub yields."""
    M = fresh()
    with item("terrain"):
        slab(-6, -6, -0.1, 6, 6, 0, M, 0)
    with item("rug"):                        # small and flat: must stay a normal object
        slab(-0.6, -0.4, 0, 0.6, 0.4, 0.01, M, 0)
    with item("bench"):
        slab(1, 1, 0, 2, 1.4, 0.45, M, 0)
    with item("decor_shrub"):                # decor overlapping a solid
        ball((1.9, 1.2, 0.3), 0.3, M)
    S = checks.Scene(bpy.context.scene, bpy.context.evaluated_depsgraph_get(), checks.config())
    kinds = {it["key"]: it["kind"] for it in S.items}
    assert kinds["terrain"] == "ground" and kinds["rug"] == "solid" and kinds["decor_shrub"] == "decor", kinds
    iss = checks.declutter(S, remove=False)
    assert [i["a"] for i in iss] == ["decor_shrub"], iss
    assert not pairs(run(zfight=False), "overlap"), "decor is not reported as overlap"


@case
def text_and_seams():
    """Text touching its board is not floating (bound_box misses extrusion); same-material and buried
    coplanar seams are not z-fighting, a visible two-material seam is."""
    M, R_ = fresh(), mat("#cc4444")
    with item("ground"):
        slab(-6, -6, -0.1, 6, 6, 0, M, 0)
    with item("board"):
        slab(-1, -0.05, 0, 1, 0.05, 1.0, M, 0)
    with item("label"):                      # back face exactly on the board's front face (y = -0.05)
        bpy.ops.object.text_add(location=(0, -0.07, 0.6), rotation=(math.radians(90), 0, 0))
        t = bpy.context.object; t.data.body = "OPEN"; t.data.size = 0.3; t.data.extrude = 0.02
    with item("tiles"):                      # same material, flush tops: invisible, not reported
        slab(2, 0, 0, 3, 1, 0.2, M, 0)
        slab(2.5, 0.2, 0.1, 3.5, 0.8, 0.2, M, 0)
    with item("capped"):                     # flush tops buried inside a cap: invisible, not reported
        slab(-3, 0, 0, -2, 1, 0.5, M, 0)
        slab(-2.6, 0.2, 0.3, -1.8, 0.8, 0.5, R_, 0)
        slab(-3.1, -0.1, 0.45, -1.7, 1.1, 0.6, M, 0)
    with item("seam"):                       # two materials, flush, visible: reported
        slab(0, 2, 0, 1, 3, 0.5, M, 0)
        slab(0.4, 2.2, 0.3, 1.2, 2.8, 0.5, R_, 0)
    iss = run(packs=())
    assert not keys(iss, "floating"), iss
    zf = {o for i in iss if i["check"] == "zfight" for o in i["objects"]}
    owner = lambda key: {o.name for o in bpy.data.objects if o.parent and o.parent.name == key}
    assert zf and zf <= owner("seam"), (zf, iss)


for fn in CASES:
    fn()
    print("ok ", fn.__name__)
print("ALL CHECKS OK")
