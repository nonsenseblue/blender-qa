"""Visual review packet: the sweep sheets, the camera shots, the automatic findings and the checklist,
in one markdown file to work through (or to hand to a vision model / a second reviewer).

Automatic checks find geometry problems. They cannot tell that a sink looks like a mat, a chair faces
the wall or a moon has the wrong halo — only looking does. The packet makes the looking systematic.
"""
import json
import os

CHECKLIST = {
    "Recognisability": "Would a stranger name every object? Anything that is just a box, a flat plate or a blob "
                       "is a defect: sinks are concave with a tap, windows have frames, art has a frame and an image, "
                       "appliances have doors/handles/controls.",
    "Orientation & logic": "Seats face what they are for; beds have nightstands at the head; bridges cross rivers; "
                           "awnings slope down and out; fronts face the camera when possible; content matches the place.",
    "Circulation": "Trace a path from every door, up every stair and out of every plaza. Nothing blocks a doorway, "
                   "stair foot, stair top or walkway.",
    "Contact": "Everything rests on, hangs from or leans against something: no hovering leaves, cushions, handles, "
               "bulbs without a wire, text off its board.",
    "Solids": "Nothing that should show its inside (shelves, tubs, boats, planters) is a closed block; water never "
              "shows inside a hull.",
    "Physical plausibility": "Lighting, shadows and sky agree (a crescent has no round halo, stars only in the sky); "
                             "water falls and spreads; scale is consistent between neighbouring objects.",
    "Render": "No black seams or dots, no washed-out blacks, subject not clipped, no key feature hidden behind another "
              "object from the camera.",
}


def write_packet(out_dir, index, shots, issues=None, title="Scene review"):
    """Write <out_dir>/review.md and return its path.

    index:  {view: [(tile, x, y)]} from sweep.sweep
    shots:  [{"camera", "path"}] from sweep.camera_shots
    issues: optional list from checks.run_all, listed so the visual pass can confirm or dismiss them
    """
    lines = [f"# {title}", "",
             "Go through every image below with the checklist. Write every problem down before fixing any.", ""]
    if issues is not None:
        errs = [i for i in issues if i.get("level", "error") == "error"]
        warns = [i for i in issues if i.get("level") == "warn"]
        lines += ["## Automatic findings", "",
                  f"{len(errs)} errors, {len(warns)} warnings." if issues else "Clean.", ""]
        for it in errs + warns:
            body = {k: v for k, v in it.items() if k not in ("check", "level")}
            lines.append(f"- **{it.get('level', 'error')} {it['check']}** `{json.dumps(body)}`")
        lines.append("")
    if shots:
        lines += ["## Camera views", ""]
        for s in shots:
            lines += [f"### {s['camera']}", "", f"![{s['camera']}]({os.path.relpath(s['path'], out_dir)})", ""]
    for view, tiles in index.items():
        lines += [f"## Sweep: {view}", "",
                  f"![sweep {view}](sweep_{view}.png)", "",
                  "Tiles run left→right, back→front; tile centres (x, y): "
                  + ", ".join(f"{n}=({x}, {y})" for n, x, y in tiles), ""]
    lines += ["## Checklist", ""]
    for head, text in CHECKLIST.items():
        lines += [f"- [ ] **{head}** — {text}"]
    path = os.path.join(out_dir, "review.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path
