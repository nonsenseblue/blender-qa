import bpy
bpy.ops.wm.open_mainfile(filepath="island.blend")
s = bpy.context.scene

# shared autumn look: golden meadow, autumn trees, fallen + drifting leaves, pumpkins and hay by the cottage
import autumn
autumn.apply(s, radius=3.8, lake=((1.2, -0.3), 1.2),
             pumpkins=[(1.45, 0.75, 0.13), (1.25, 0.82, 0.09), (2.55, 0.8, 0.11)], hay=(2.75, 1.7, 20))

s.render.filepath = __import__("os").path.abspath("island_autumn.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("island_autumn.blend"))
