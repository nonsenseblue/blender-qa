"""Command line entry point.

    python -m blender_qa check  scene.blend [--config qa.toml] [options]   # needs the `bpy` module
    python -m blender_qa sweep  scene.blend --out qa_sweep                 # zoomed contact sheets
    python -m blender_qa review scene.blend --out qa_review                # sweep + hero shots + checklist
    python -m blender_qa frame  out_dir a.png b.png ...                    # uniform presentation (Pillow)

Inside Blender:
    blender -b scene.blend --python-expr "import sys; sys.path.insert(0, '/path/to/blender-qa'); \\
        from blender_qa import cli; cli.main(['check', '--current'])"

`check` needs no configuration: features, ground and flying things are recognised automatically.
Settings can live in qa.toml (found next to the .blend or given with --config); flags override it.
Exit code is 1 when errors are found (warnings do not fail), so it can gate a pipeline.
"""
import argparse
import json
import os
import sys


def _patterns(s):
    return tuple(p for p in (s or "").split(",") if p) if s is not None else None


def _box(s):
    # "x0,y0,z0,x1,y1,z1[:label]"
    nums, _, label = s.partition(":")
    v = [float(t) for t in nums.split(",")]
    return (tuple(v[:3]), tuple(v[3:]), label or s)


def load_config(path):
    """qa.toml -> dict of check settings (see checks.DEFAULTS for the keys)."""
    import tomllib
    with open(path, "rb") as f:
        data = tomllib.load(f)
    data = data.get("check", data)
    if "keep_clear" in data:
        data["keep_clear"] = [(tuple(z["min"]), tuple(z["max"]), z.get("label", "zone")) for z in data["keep_clear"]]
    return data


def _load_for(args):
    path = getattr(args, "config", None)
    if path is None and args.blend:
        cand = os.path.join(os.path.dirname(os.path.abspath(args.blend)), "qa.toml")
        path = cand if os.path.exists(cand) else None
    return load_config(path) if path else {}


def build_parser():
    p = argparse.ArgumentParser(prog="blender_qa", description="Automatic and visual QA for Blender scenes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("frame", help="same canvas size and subject scale for a set of renders (needs Pillow)")
    f.add_argument("out_dir")
    f.add_argument("images", nargs="+")
    f.add_argument("--size", default="1600x1200")
    f.add_argument("--fill", type=float, default=0.88)
    f.add_argument("--box-from", help="reuse this image's subject box for all (variants of one camera)")
    f.add_argument("--main-only", action="store_true", help="frame the largest connected subject only (ignore clouds, moon, balloon)")

    for name in ("check", "sweep", "review"):
        s = sub.add_parser(name)
        s.add_argument("blend", nargs="?", help=".blend file (omit with --current inside Blender)")
        s.add_argument("--current", action="store_true", help="use the scene already open in Blender")

    c = sub.choices["check"]
    c.add_argument("--config", help="qa.toml (default: qa.toml next to the .blend, if present)")
    c.add_argument("--group-by", choices=("auto", "parent", "collection", "object"))
    c.add_argument("--ground", help="extra name patterns that are ground (floor,terrain,water)")
    c.add_argument("--no-auto-ground", action="store_true", help="do not guess ground from geometry")
    c.add_argument("--anchors", help="extra patterns things may rest on")
    c.add_argument("--ground-z", type=float, help="height of the floor/terrain surface")
    c.add_argument("--ignore", help="patterns skipped entirely (rug,mat)")
    c.add_argument("--allow-float", help="patterns meant to fly (replaces the built-in list)")
    c.add_argument("--decor", help="patterns of decor that yields to solids")
    c.add_argument("--keep-clear", action="append", default=[], help="x0,y0,z0,x1,y1,z1:label (repeatable)")
    c.add_argument("--fast", action="store_true", help="bounding boxes only (coarse)")
    c.add_argument("--no-intra", action="store_true", help="skip the hidden-inside check")
    c.add_argument("--no-zfight", action="store_true")
    c.add_argument("--views", help="only z-fight-check faces visible from these views (front,left,...)")
    c.add_argument("--packs", help="rule packs to run (default: interior); '' for none")
    c.add_argument("--warnings", action="store_true", help="also list warnings, not only count them")
    c.add_argument("--json", help="write the report here (errors and warnings)")

    for name in ("sweep", "review"):
        s = sub.choices[name]
        s.add_argument("--out", default=f"qa_{name}")
        s.add_argument("--views", default="front,left")
        s.add_argument("--tile", type=float, default=2.6, help="tile size in metres")
        s.add_argument("--size", type=int, default=480)
        s.add_argument("--samples", type=int, default=16)
        s.add_argument("--exclude", default="", help="patterns ignored when computing the scene bounds")
        s.add_argument("--cameras", action="store_true", help="also render every camera in the scene (review always does)")
        s.add_argument("--config", help="qa.toml for the checks listed in the review")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "frame":
        from PIL import Image
        from .present import frame, subject_box
        os.makedirs(args.out_dir, exist_ok=True)
        size = tuple(int(v) for v in args.size.lower().split("x"))
        box = (subject_box(Image.open(args.box_from).convert("RGB"), main_only=args.main_only)
               if args.box_from else None)
        for src in args.images:
            dst = os.path.join(args.out_dir, os.path.splitext(os.path.basename(src))[0] + ".jpg")
            b = box or subject_box(Image.open(src).convert("RGB"), main_only=args.main_only)
            print(frame(src, dst, size=size, fill=args.fill, box=b))
        return 0

    import bpy
    if args.blend and not args.current:
        bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()

    if args.cmd in ("sweep", "review"):
        from .sweep import sweep, camera_shots
        index = sweep(scene, args.out, views=_patterns(args.views), tile=args.tile, size=args.size,
                      samples=args.samples, exclude=_patterns(args.exclude))
        shots = camera_shots(scene, args.out, size=max(args.size, 800), samples=args.samples) if (args.cameras or args.cmd == "review") else []
        if args.cmd == "review":
            from .review import write_packet
            from . import checks
            issues = checks.run_all(scene, bpy.context.evaluated_depsgraph_get(), **_load_for(args))
            print(write_packet(args.out, index, shots, issues,
                               title=f"Review: {os.path.basename(args.blend) if args.blend else scene.name}"))
        else:
            print(json.dumps({"tiles": index, "cameras": shots}))
        return 0

    from . import checks
    cfg = _load_for(args)
    flags = {
        "group_by": args.group_by, "ground": _patterns(args.ground), "anchors": _patterns(args.anchors),
        "ground_z": args.ground_z, "ignore": _patterns(args.ignore), "allow_float": _patterns(args.allow_float),
        "decor": _patterns(args.decor), "views": _patterns(args.views), "packs": _patterns(args.packs),
        "keep_clear": [_box(b) for b in args.keep_clear] or None,
        "accurate": False if args.fast else None, "intra": False if args.no_intra else None,
        "zfight": False if args.no_zfight else None, "ground_auto": False if args.no_auto_ground else None,
    }
    cfg.update({k: v for k, v in flags.items() if v is not None})
    issues = checks.run_all(scene, dg, **cfg)
    for it in sorted(issues, key=lambda i: i["level"] != "error"):
        if it["level"] == "warn" and not args.warnings:
            continue
        print("QA", it["level"].upper(), it["check"].upper(),
              json.dumps({k: v for k, v in it.items() if k not in ("check", "level")}))
    counts = {"error": {}, "warn": {}}
    for it in issues:
        c = counts[it["level"]]
        c[it["check"]] = c.get(it["check"], 0) + 1
    print("QA SUMMARY", json.dumps({k: v for k, v in counts.items() if v}) if issues else "clean")
    if counts["warn"]:
        print("QA NOTE warnings (listed with --warnings) involve loose objects (no parent / feature collection): group each feature "
              "under a parent empty or its own collection to turn them into definite results")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(issues, f, indent=1)
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
