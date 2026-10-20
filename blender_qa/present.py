"""Make a set of renders look like one set: same canvas size, subject centred at the same scale.

Needs Pillow (`pip install pillow`); it does not need bpy.

    python -m blender_qa frame out_dir a.png b.png c.png --size 1600x1200 --fill 0.88
    python -m blender_qa frame out_dir day.png night.png snow.png --box-from day.png   # variants of one camera
"""
from PIL import Image, ImageChops, ImageFilter


def subject_box(img, threshold=6, despeckle=7, main_only=False):
    """Bounding box of everything that differs from the corner (background) colour.
    `despeckle` removes isolated dots (stars, snowflakes) before measuring.
    `main_only` keeps just the largest connected blob — the island with its waterfall — and leaves out
    separate things floating around it (clouds, a balloon, the moon)."""
    bg = img.getpixel((3, 3))
    diff = ImageChops.difference(img, Image.new("RGB", img.size, bg)).convert("L")
    mask = diff.point(lambda v: 255 if v > threshold else 0)
    if despeckle:
        mask = mask.filter(ImageFilter.MinFilter(despeckle))
    if main_only:
        return _largest_blob_box(mask) or mask.getbbox() or (0, 0, img.width, img.height)
    return mask.getbbox() or (0, 0, img.width, img.height)


def _largest_blob_box(mask, step=4):
    """Bounding box (full-resolution coords) of the largest 4-connected blob, found on a downsampled grid."""
    from collections import deque
    import numpy as np
    small = np.asarray(mask.resize((max(1, mask.width // step), max(1, mask.height // step)), Image.NEAREST)) > 0
    h, w = small.shape
    seen = np.zeros_like(small)
    best, best_box = 0, None
    for y0 in range(h):
        for x0 in range(w):
            if not small[y0, x0] or seen[y0, x0]:
                continue
            q = deque([(y0, x0)]); seen[y0, x0] = True
            n, ys, xs = 0, [y0, y0], [x0, x0]
            while q:
                y, x = q.popleft(); n += 1
                ys[0] = min(ys[0], y); ys[1] = max(ys[1], y); xs[0] = min(xs[0], x); xs[1] = max(xs[1], x)
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < h and 0 <= xx < w and small[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True; q.append((yy, xx))
            if n > best:
                best, best_box = n, (xs[0] * step, ys[0] * step, (xs[1] + 1) * step, (ys[1] + 1) * step)
    return best_box


def _place(img, ox, oy, W, H):
    """Put `img` at (ox, oy) on a WxH canvas. The background around it is estimated per row (median of
    the image's leftmost and rightmost strips), so flat and vertical-gradient skies continue seamlessly
    and nothing touching the border gets smeared outward."""
    import numpy as np
    a = np.asarray(img)
    h, w = a.shape[:2]
    k = max(2, w // 25)
    rows = np.median(np.concatenate([a[:, :k], a[:, -k:]], axis=1), axis=1)       # (h, 3) background per row
    # smooth over neighbouring rows: a cloud or star touching the border only spans a few rows,
    # while real background gradients change slowly
    win = max(3, h // 6)
    padded = np.pad(rows, ((win // 2, win - 1 - win // 2), (0, 0)), mode="edge")
    rows = np.stack([np.median(padded[i:i + win], axis=0) for i in range(h)])
    src = np.clip(np.arange(H) - oy, 0, h - 1)
    canvas = np.repeat(rows[src][:, None, :], W, axis=1).astype(np.uint8)
    cx0, cy0 = max(0, -ox), max(0, -oy)
    cx1, cy1 = min(w, W - ox), min(h, H - oy)
    canvas[max(0, oy):max(0, oy) + (cy1 - cy0), max(0, ox):max(0, ox) + (cx1 - cx0)] = a[cy0:cy1, cx0:cx1]
    return Image.fromarray(canvas)


def frame(src, dst, size=(1600, 1200), fill=0.88, box=None, margin=0.02, quality=88):
    """Scale `src` so its subject fills `fill` of the canvas and centre it; the margin continues the image's
    own background. Pass `box` to reuse one subject box for several renders of the same shot."""
    img = Image.open(src).convert("RGB")
    W, H = size
    x0, y0, x1, y1 = box or subject_box(img)
    pad = round(margin * max(x1 - x0, y1 - y0))
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    s = min(W * fill / (x1 - x0), H * fill / (y1 - y0))
    big = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    ox, oy = round(W / 2 - (x0 + x1) / 2 * s), round(H / 2 - (y0 + y1) / 2 * s)
    out = _place(big, ox, oy, W, H)
    if dst.lower().endswith((".jpg", ".jpeg")):
        out.save(dst, quality=quality)
    else:
        out.save(dst)
    return dst
