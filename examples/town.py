# Big island with the café street moved onto it.
# Reuses island.py (patched for a larger radius) and appends everything from street.blend.
import bpy, math, random
from mathutils import Vector

src = open("island.py").read()
patches = [
    ("RAD = 4.0", "RAD = 6.5"),
    ("         (1, 1, 0.6), sub=1, smooth=False)\nfor k in range(16)" if False else "(1, 1, 0.6), sub=1, smooth=False)\n\ndef river", "(1, 1, 0.6), sub=1, smooth=False).name = 'decor_stone'\n\ndef river"),
    ("for x, y, h in [(-0.3, 2.0, 0.9)", 'def group_new(snap, name):\n    g = bpy.data.objects.new(name, None); s.collection.objects.link(g)\n    for o in set(bpy.data.objects) - snap:\n        if o is not g and o.parent is None:\n            o.parent = g\n    return g\n_pine, _round_tree = pine, round_tree\ndef pine(x, y, h):\n    snap = set(bpy.data.objects); _pine(x, y, h); group_new(snap, "grp_tree")\ndef round_tree(x, y, h):\n    snap = set(bpy.data.objects); _round_tree(x, y, h); group_new(snap, "grp_tree")\nfor x, y, h in [(-0.3, 2.0, 0.9)'),
    ("ball((x, y, 0.04), 0.045, random.choice(FLOW), sub=2)", "ball((x, y, 0.04), 0.045, random.choice(FLOW), sub=2).name = 'decor_flower'"),
    ("BOAT_C, BOAT_A = Vector((0.75, -0.45, 0.13)), R(25)", "BOAT_C, BOAT_A = Vector((0.97, -0.55, 0.13)), R(90)"),
    ("radius1=RAD - 0.15, radius2=0.2, depth=3.4, location=(0, 0, -2.5)",
     "radius1=RAD - 0.15, radius2=0.3, depth=4.6, location=(0, 0, -3.1)"),
    ("FALL_Z = -2.5", "FALL_Z = -3.6"),
    # trees: drop the ones where the town goes, add a ring on the new outer meadow
    ("(-1.8, -1.2, 1.1), (-2.2, -1.9, 0.8), (1.5, 3.0, 0.7), (2.6, 2.2, 0.9)]:",
     "(-1.8, -1.2, 1.1), (1.5, 3.0, 0.7), (-4.6, 1.6, 1.2), (-3.6, 3.6, 1.0), (-1.6, 4.6, 1.1),"
     " (2.6, 4.2, 0.9), (4.6, 2.6, 1.1), (-5.2, -0.6, 1.0), (-4.2, 2.6, 0.8), (0.4, 5.2, 0.9)]:"),
    ("[(3.0, 0.4, 1.0), (0.2, -2.0, 0.9), (-0.8, -2.8, 1.1), (1.0, -3.2, 0.8), (3.2, 1.4, 0.8)]",
     "[(0.9, -4.6, 0.9), (5.8, -0.9, 1.1), (3.4, 3.4, 1.0), (0.6, -5.2, 0.9), (5.9, -0.2, 0.8)]"),
    ("for _ in range(40):", "for _ in range(110):"),
    ("r = random.uniform(1.0, 3.6)", "r = random.uniform(1.0, 6.1)"),
    ("or (x > 0.4 and y > 1.6): continue", "or (x > 0.4 and y > 1.6) or (-4.7 < x < 1.1 and y < -1.5) or (1.3 < x < 5.6 and -0.3 < y < 2.5) or (4.2 < x < 5.9 and -2.6 < y < -1.0) or (1.2 < x < 2.8 and -4.0 < y < -2.6) or ((x + 1.65) / 3.1) ** 2 + ((y + 2.85) / 1.8) ** 2 < 1: continue"),
    ("cloud(-3.6, 2.2, 3.6, 1.0); cloud(3.4, 2.8, 2.6, 0.8); cloud(-4.2, -2.6, 0.6, 0.7)",
     "cloud(-5.6, 3.2, 4.6, 1.3); cloud(5.0, 3.8, 3.4, 1.0); cloud(-6.6, -3.4, 1.0, 0.9); cloud(6.2, -3.0, -1.5, 0.8)"),
    ("cam.data.ortho_scale = 11.5", "cam.data.ortho_scale = 15.5"),
    # mountains scaled up to suit the bigger island
    ('mountain((-1.6, 1.5), 2.0, 3.2, "big")', 'mountain((-1.8, 2.1), 2.6, 4.3, "big")'),
    ('mountain((0.6, 2.4), 1.3, 2.0, "small", 0.45, 0.85)', 'mountain((0.3, 3.3), 1.6, 2.7, "small", 0.45, 0.85)'),
    ('mountain((-2.7, -0.3), 1.0, 1.3, "tiny", 0.6, 2.0)', 'mountain((-3.2, 0.3), 1.3, 1.8, "tiny", 0.6, 2.0)'),
    ("(Vector((0, 0, 0.0)) - cam.location)", "(Vector((0, 0, -0.6)) - cam.location)"),
    ("s.render.resolution_x = 1000; s.render.resolution_y = 1100", "s.render.resolution_x = 1300; s.render.resolution_y = 1300"),
    ("bpy.ops.render.render(write_still=True)", open("extras.py").read() + "\nadd_town()\n" + open("declutter.py").read() + "\nbpy.ops.render.render(write_still=True)"),
    ('"island.png" if not __import__("os").environ.get("BOATTEST") else "boat_test.png"',
     '"town.png"'),
    ('"island.blend"', '"town.blend"'),
]
for a, b in patches:
    assert a in src, a
    src = src.replace(a, b)
# the little cottage makes way for the villa (built in extras.py)
src = src[:src.index("# ---------- cottage by the lake ----------")] + src[src.index("# little rowing boat on the lake"):]

def add_town():
    s = bpy.context.scene
    with bpy.data.libraries.load("street.blend") as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    town = bpy.data.objects.new("Town", None); s.collection.objects.link(town)
    for o in data_to.objects:
        if o is None or o.type == 'CAMERA' or (o.type == 'LIGHT' and o.data.type == 'SUN'):
            continue
        s.collection.objects.link(o)
        if o.parent is None:
            o.parent = town
    # street block is 12 x 6 centred on (3, 0); shrink it and set it down left of the lake, shop fronts facing -y
    town.scale = (0.45, 0.45, 0.45)
    town.location = (-1.8 - 3 * 0.45, -3.0, 0.02)
    for o in town.children:  # lamp lights scaled down with everything else
        if o.type == 'LIGHT':
            o.data.energy *= 0.45 ** 2
    # drop the street's square kerb, pavement and paving lines
    for o in list(town.children):
        if o.type == 'MESH' and o.data.materials and o.data.materials[0].name.split(".")[0] in ("#c9c1b6", "#e4ddd3"):
            bpy.data.objects.remove(o)
    g = PLAZA_NS
    # soft oval plaza of pale stone under the shops, ringed with shrubs and flowers
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1, depth=0.06, location=(-1.65, -2.85, 0.01))
    pl = bpy.context.object; pl.scale = (2.85, 1.6, 1); pl.data.materials.append(g["mat"]("#ece3d3", 0.85))
    g["bevel"](pl, 0.02); bpy.ops.object.shade_smooth()
    for k in range(70):
        a = k / 70 * math.tau
        x, y = -1.65 + math.cos(a) * 2.95, -2.85 + math.sin(a) * 1.7
        if -1.2 < math.degrees(a) - 360 * (a > math.pi) < 25 or 300 < math.degrees(a) < 335:
            continue  # openings toward the path and the front
        if k % 3 == 0:
            g["ball"]((x, y, 0.1), 0.13, g["LEAF2"] if k % 2 else g["LEAF"], (1, 1, 0.8), sub=2).name = "decor_bush"
        else:
            g["ball"]((x, y, 0.05), 0.045, random.choice(g["FLOW"]), sub=2).name = "decor_flower"
    # coloured roofs so the buildings read as part of the village
    for r in (g["box"]((-2.79, -2.64, 1.27), (1.4, 1.4, 0.03), g["mat"]("#d98e73"), 0.01),
              g["box"]((-1.395, -2.64, 1.13), (1.3, 1.4, 0.03), g["mat"]("#7cc69b"), 0.01)):
        r.parent = town; r.matrix_parent_inverse = town.matrix_world.inverted()  # roof caps belong to the street

PLAZA_NS = {"__name__": "__main__"}
PLAZA_NS["add_town"] = add_town
exec(compile(src, "island", "exec"), PLAZA_NS)
