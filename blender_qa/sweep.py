"""Visual sweep: render the whole scene as a grid of zoomed tiles from several angles and stitch
them into contact sheets, so every corner gets looked at before anyone else sees the render.

Needs only bpy + numpy (both ship with Blender), no PIL.
"""
import math
import os
import numpy as np
import bpy
from mathutils import Vector
from .core import renderable, world_bbox, matches

VIEWS = {  # camera offset direction for each named view
    "front": (1, -1), "back": (-1, 1), "left": (-1, -1), "right": (1, 1),
}


def scene_bounds(scene, depsgraph, exclude=()):
    boxes = [world_bbox(o, depsgraph) for o in renderable(scene) if not matches(o.name, exclude)]
    lo = Vector((min(b[0].x for b in boxes), min(b[0].y for b in boxes), min(b[0].z for b in boxes)))
    hi = Vector((max(b[1].x for b in boxes), max(b[1].y for b in boxes), max(b[1].z for b in boxes)))
    return lo, hi


def _stitch(paths, cols, out_path):
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, im in enumerate(imgs):
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        r, c = divmod(i, cols)
        # Blender image rows start at the bottom; tile 0 goes top-left
        sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = px
        bpy.data.images.remove(im)
    out = bpy.data.images.new("sweep", width=cols * w, height=rows * h, alpha=True)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)


def sweep(scene, out_dir, views=("front", "left"), tile=2.6, grid=None, z=None, size=480, samples=16,
          elevation=0.55, exclude=(), cols=4, spots=None):
    """Render tiles and write one contact sheet per view: <out_dir>/sweep_<view>.png.

    grid:  (nx, ny) tiles over the scene's XY bounds (default: enough tiles of `tile` metres)
    spots: explicit list of (x, y, z, ortho_scale) instead of a grid
    Returns {view: [(index, x, y)]} so a tile number on a sheet can be traced back to a spot.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    os.makedirs(out_dir, exist_ok=True)
    lo, hi = scene_bounds(scene, depsgraph, exclude)
    zc = z if z is not None else lo.z + min(1.0, (hi.z - lo.z) / 3)
    if spots is None:
        nx = grid[0] if grid else max(1, math.ceil((hi.x - lo.x) / tile))
        ny = grid[1] if grid else max(1, math.ceil((hi.y - lo.y) / tile))
        # one sheet row per y band (back of the scene first), one column per x band
        spots = [(lo.x + (i + 0.5) * (hi.x - lo.x) / nx, lo.y + (j + 0.5) * (hi.y - lo.y) / ny, zc, tile)
                 for j in reversed(range(ny)) for i in range(nx)]
        cols = nx
    cam_data = bpy.data.cameras.new("qa_cam"); cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("qa_cam", cam_data); scene.collection.objects.link(cam)
    old_cam, old_res, old_samples = scene.camera, (scene.render.resolution_x, scene.render.resolution_y), None
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = size
    if scene.render.engine == "CYCLES":
        old_samples = scene.cycles.samples; scene.cycles.samples = samples
    index = {}
    try:
        for view in views:
            dx, dy = VIEWS[view]
            paths = []
            for n, (x, y, zz, sc) in enumerate(spots):
                tgt = Vector((x, y, zz))
                cam.location = tgt + Vector((dx, dy, elevation * math.sqrt(2))).normalized() * 30
                cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
                cam_data.ortho_scale = sc
                cam_data.clip_end = 200
                p = os.path.join(out_dir, f"tile_{view}_{n:03d}.png")
                scene.render.filepath = p
                bpy.ops.render.render(write_still=True)
                paths.append(p)
            _stitch(paths, cols, os.path.join(out_dir, f"sweep_{view}.png"))
            index[view] = [(n, round(s[0], 2), round(s[1], 2)) for n, s in enumerate(spots)]
    finally:
        scene.camera = old_cam
        scene.render.resolution_x, scene.render.resolution_y = old_res
        if old_samples is not None:
            scene.cycles.samples = old_samples
        bpy.data.objects.remove(cam)
    return index
