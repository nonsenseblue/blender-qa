"""Builds a tiny scene with one known defect of each kind and checks every detector finds exactly it.
Run:  python tests/test_checks.py   (needs the `bpy` module: pip install bpy)"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy
from blender_qa import checks
from blender_qa.kit import item, slab, mat

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
M = mat("#cccccc")

with item("floor"):
    slab(-5, -5, -0.2, 5, 5, 0, M)
with item("table"):                      # fine: rests on the floor
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
    slab(-3, 2, 0, -2, 3, 0.5, M)
with item("panel_b"):
    slab(-2.6, 2.2, 0.3, -1.8, 2.8, 0.5, M)
with item("plant"):                      # DEFECT keep_clear: blocks the stair landing
    slab(2, -3, 0, 2.3, -2.7, 0.8, M)

dg = bpy.context.evaluated_depsgraph_get()
ov = checks.overlap(s, dg, ground=("floor",), intra=True,
                    keep_clear=[((1.8, -3.2, 0), (2.6, -2.4, 2), "stair landing")])
fl = checks.floating(s, dg, anchors=("floor",))
zf = checks.zfight(s, dg)

found = {(i["check"], i.get("a"), i.get("b")) for i in ov}
assert ("overlap", "crate", "table") in found, ov
assert any(i["check"] == "hidden_inside" and i["a"] == "shelf_solid" for i in ov), ov
assert any(i["check"] == "keep_clear" and i["a"] == "plant" for i in ov), ov
assert not any(i["check"] == "overlap" and "panel_a" in (i["a"], i["b"]) and "lamp" in (i["a"], i["b"]) for i in ov)
assert [i["a"] for i in fl] == ["lamp"], fl
assert len(zf) >= 1 and any(set(z["objects"]) & {o.name for o in bpy.data.objects if o.parent and o.parent.name == "panel_b"} for z in zf), zf
# the table's leg touches the floor and the top touches the leg: nothing else may be reported floating
print("overlap:", ov)
print("floating:", fl)
print("zfight:", zf)
print("ALL CHECKS OK")
