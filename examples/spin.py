import bpy, sys, math
from mathutils import Vector
# usage: python spin.py -- <file.blend> <out_dir> [frames] [size] [samples]
args = sys.argv[sys.argv.index("--") + 1:]
blend, out = args[0], args[1]
N = int(args[2]) if len(args) > 2 else 48
size = int(args[3]) if len(args) > 3 else 480
samples = int(args[4]) if len(args) > 4 else 24
bpy.ops.wm.open_mainfile(filepath=blend)
s = bpy.context.scene
piv = bpy.data.objects.new("pivot", None); s.collection.objects.link(piv)
s.camera.parent = piv
ratio = s.render.resolution_y / s.render.resolution_x
s.render.resolution_x = size; s.render.resolution_y = int(size * ratio)
s.cycles.samples = samples
for i in range(N):
    piv.rotation_euler = (0, 0, math.tau * i / N)
    s.render.filepath = __import__("os").path.abspath(f"{out}/f_{i:03d}.png")
    bpy.ops.render.render(write_still=True)
