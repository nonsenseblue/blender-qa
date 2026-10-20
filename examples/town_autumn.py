import bpy
bpy.ops.wm.open_mainfile(filepath="town.blend")
s = bpy.context.scene

# the big island in autumn, with the same shared look as the small island
import autumn
autumn.apply(s, radius=6.1, lake=((1.2, -0.3), 1.2), fallen=220, drifting=45,
             pumpkins=[(1.3, 0.8, 0.13), (1.12, 1.0, 0.09), (4.05, 0.8, 0.11)], hay=(4.0, -0.75, 70))

s.render.filepath = __import__("os").path.abspath("town_autumn.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=__import__("os").path.abspath("town_autumn.blend"))
