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


def set_samples(scene, samples):
    """Lower the render samples on whichever engine is active; returns a function restoring them.
    Works for Cycles and Eevee; other engines are left alone."""
    eng = scene.render.engine
    if eng == "CYCLES":
        old = scene.cycles.samples
        scene.cycles.samples = samples
        return lambda: setattr(scene.cycles, "samples", old)
    if "EEVEE" in eng and hasattr(scene.eevee, "taa_render_samples"):
        old = scene.eevee.taa_render_samples
        scene.eevee.taa_render_samples = samples
        return lambda: setattr(scene.eevee, "taa_render_samples", old)
    return lambda: None


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
    old_cam, old_res = scene.camera, (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    restore = set_samples(scene, samples)
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
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = old_res
        restore()
        bpy.data.objects.remove(cam)
    return index


def camera_shots(scene, out_dir, size=960, samples=16):
    """Render the scene through every camera it has (perspective or ortho, any engine) — the hero views
    the scene will be judged from. Without cameras, one perspective three-quarter view of the whole scene
    is rendered. Returns [{"camera", "path"}]."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    os.makedirs(out_dir, exist_ok=True)
    cams = [o for o in scene.objects if o.type == "CAMERA" and o.name != "qa_cam"]
    temp = None
    if not cams:
        lo, hi = scene_bounds(scene, depsgraph)
        c = (lo + hi) / 2
        r = max((hi - lo).length / 2, 0.5)
        data = bpy.data.cameras.new("qa_hero"); data.lens = 50; data.clip_end = r * 20
        temp = bpy.data.objects.new("qa_hero", data); scene.collection.objects.link(temp)
        d = Vector((1, -1, 0.8)).normalized()
        temp.location = c + d * r / math.tan(data.angle / 2) * 1.1
        temp.rotation_euler = (c - temp.location).to_track_quat("-Z", "Y").to_euler()
        cams = [temp]
    rx, ry, pct = scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage
    old_cam = scene.camera
    k = size / max(rx, ry)
    scene.render.resolution_x, scene.render.resolution_y = max(1, round(rx * k)), max(1, round(ry * k))
    scene.render.resolution_percentage = 100
    restore = set_samples(scene, samples)
    shots = []
    try:
        for cam in cams:
            scene.camera = cam
            p = os.path.join(out_dir, f"camera_{cam.name.replace(' ', '_')}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            shots.append({"camera": cam.name, "path": p})
    finally:
        scene.camera = old_cam
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = rx, ry, pct
        restore()
        if temp is not None:
            bpy.data.objects.remove(temp)
    return shots
