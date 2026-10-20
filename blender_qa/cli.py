"""Command line entry point.

    python -m blender_qa check scene.blend [options]      # with the `bpy` module (pip install bpy)
    blender -b scene.blend --python-expr "import sys; sys.path.insert(0, '/path/to/blender-qa'); \\
        from blender_qa import cli; cli.main(['check', '--current'])"

Exit code is 1 when issues are found, so it can gate a pipeline.
"""
import argparse
import json
import sys


def _patterns(s):
    return tuple(p for p in (s or "").split(",") if p)


def _box(s):
    # "x0,y0,z0,x1,y1,z1[:label]"
    nums, _, label = s.partition(":")
    v = [float(t) for t in nums.split(",")]
    return (tuple(v[:3]), tuple(v[3:]), label or s)


def build_parser():
    p = argparse.ArgumentParser(prog="blender_qa", description="Automatic QA for Blender scenes.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "sweep"):
        s = sub.add_parser(name)
        s.add_argument("blend", nargs="?", help=".blend file (omit with --current inside Blender)")
        s.add_argument("--current", action="store_true", help="use the scene already open in Blender")
        s.add_argument("--group-by", default="parent", choices=("parent", "collection", "object"))
    c = sub.choices["check"]
    c.add_argument("--ground", default="", help="name patterns that count as ground (floor,terrain,water)")
    c.add_argument("--ground-size", type=float, default=3.0, help="objects wider than this count as ground")
    c.add_argument("--ignore", default="", help="patterns skipped entirely (rug,mat)")
    c.add_argument("--anchors", default="", help="patterns things may rest on/hang from (floor,walls)")
    c.add_argument("--ground-z", type=float, default=None, help="height of the floor/terrain surface")
    c.add_argument("--allow-float", default="", help="patterns meant to fly (cloud,balloon,star)")
    c.add_argument("--keep-clear", action="append", default=[], help="x0,y0,z0,x1,y1,z1:label (repeatable)")
    c.add_argument("--no-intra", action="store_true", help="skip the hidden-inside check")
    c.add_argument("--no-zfight", action="store_true")
    c.add_argument("--views", default="", help="only z-fight-check faces visible from these views (front,left,...)")
    c.add_argument("--json", help="write the report here")
    s = sub.choices["sweep"]
    s.add_argument("--out", default="qa_sweep")
    s.add_argument("--views", default="front,left")
    s.add_argument("--tile", type=float, default=2.6, help="tile size in metres")
    s.add_argument("--size", type=int, default=480)
    s.add_argument("--samples", type=int, default=16)
    s.add_argument("--exclude", default="", help="patterns ignored when computing the scene bounds")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    import bpy
    if args.blend and not args.current:
        bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    if args.cmd == "sweep":
        from .sweep import sweep
        index = sweep(scene, args.out, views=_patterns(args.views), tile=args.tile, size=args.size,
                      samples=args.samples, exclude=_patterns(args.exclude))
        print(json.dumps(index))
        return 0
    from . import checks
    issues = checks.run_all(scene, dg, group_by=args.group_by, ground=_patterns(args.ground),
                            ground_size=args.ground_size, ignore=_patterns(args.ignore),
                            anchors=_patterns(args.anchors), ground_z=args.ground_z,
                            allow_float=_patterns(args.allow_float), intra=not args.no_intra,
                            keep_clear=[_box(b) for b in args.keep_clear], zfight=not args.no_zfight,
                            views=_patterns(args.views) or None)
    for it in issues:
        print("QA", it["check"].upper(), json.dumps({k: v for k, v in it.items() if k != "check"}))
    counts = {}
    for it in issues:
        counts[it["check"]] = counts.get(it["check"], 0) + 1
    print("QA SUMMARY", json.dumps(counts) if counts else "clean")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(issues, f, indent=1)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
