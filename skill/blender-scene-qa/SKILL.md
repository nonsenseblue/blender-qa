---
name: blender-scene-qa
description: Build and self-review Blender scenes (dioramas, rooms, props) so the person never has to hunt for defects. Use whenever you model, edit or render anything in Blender/bpy — before showing any render, run the automatic checks (overlap, floating, z-fighting, hidden-inside, keep-clear) and a zoomed multi-angle visual sweep, fix everything, and only then share.
---

# Blender scene QA

The person reviewing your renders should never be the one who finds that a chair faces the
wall, a plant floats above its pot, or the "sink" is a flat grey plate. Every one of those
happened before this skill existed — see `PITFALLS.md` in the repo for the full list.

The tools live in the `blender_qa` package of this repo (locate it with
`git rev-parse --show-toplevel` or the path where the repo was cloned). They run with the `bpy`
module (`pip install bpy`, matching Python version) or inside Blender (`blender -b`).

## 1. Build so the checks can work

- Wrap every piece of furniture / prop / feature in its own parent empty:
  `with item("sofa"): ...` (`blender_qa.kit.item`). Checks compare *features*, not loose parts.
- Use semantic helpers instead of raw boxes where a mistake is easy:
  `kit.chair(x, y, face=...)` (backrest always opposite the facing side),
  `kit.basin(...)` (anything that holds water is hollow), `kit.potted_plant(...)` (leaves grow from the soil),
  `kit.slab(...)` (applies scale without moving the origin).
- Name floors/terrain/walls/water consistently (`floor`, `walls`, `terrain`, `lake`...) so they can be
  passed as `--ground` / `--anchors`.
- Things meant to fly (clouds, balloons, stars, fireflies) get recognisable names for `--allow-float`.

## 2. Automatic checks — must be clean before anyone sees a render

```bash
python -m blender_qa check scene.blend \
  --ground floor,terrain,lake --anchors floor,walls,terrain --ignore rug,mat \
  --allow-float cloud,balloon,star --views front,left \
  --keep-clear "0.1,3.3,0,1.3,5.5,2.4:stairs" --json qa.json
```

| check | finds |
|---|---|
| `overlap` | two features interpenetrating (sheep in a tree, toilet in a wall, chair in a table) |
| `hidden_inside` | a part completely inside a solid box of the same feature (books in a solid shelf, water in a solid tub) |
| `keep_clear` | anything in a zone that must stay walkable (stairs, doorways, paths, plaza exits) |
| `floating` | parts not touching anything that is (transitively) supported: leaves over a pot, handles off a door, steps in mid-air |
| `zfight` | coplanar overlapping same-facing faces → black seams/dots/flicker |

Exit code 1 means issues. Read every line: fix real ones in the *build script*, not by hand in the
.blend; treat false positives by tightening names/patterns, never by ignoring the report.
For scattered decor (shrubs, flowers, pebbles) call `checks.declutter(...)` in the build so decor
yields to solids automatically.

## 3. Visual sweep — look at every tile

```bash
python -m blender_qa sweep scene.blend --out qa_sweep --views front,left --tile 2.5
```

This renders the whole scene as zoomed tiles from two angles (`qa_sweep/sweep_front.png`,
`sweep_left.png`; rows = back→front, columns = left→right). Open both sheets and go through every
tile with this checklist. Write down every problem before fixing anything.

**Recognisability** — would a stranger name every object? Anything that is "just a box", a flat
plate, or a blob is a defect: sinks are concave with a tap, windows have frames/mullions/sill, art
has a frame and an image, appliances have doors/handles/controls, toilets have bowl/seat/lid.

**Orientation & logic** — seats face what they are for (desk, table, TV); beds have nightstands at the
head; bridges cross rivers; awnings slope down and out; the TV/screen/front of things faces the camera
when possible; content matches the place (a greenhouse holds plants, not a table).

**Circulation** — trace a path from every door, up every stair and out of every plaza. Nothing may
block a doorway, stair foot, stair top or walkway. Stair tops must open onto the floor above.

**Contact** — everything rests on, hangs from or leans against something: no hovering leaves,
cushions, handles, taps, rails; no wall-mounted item above a cut-away wall's height.

**Solids** — nothing that should show its inside (shelves, tubs, boats, planters, greenhouses) is a
closed block; water never shows *inside* a hull or room it should not reach.

**Render** — no black seams or dots, no washed-out blacks, subject not clipped by the frame,
no key feature hidden behind another object from the hero camera.

## 4. Fix, re-run, then share

1. Fix everything found in 2 and 3 in the build script.
2. Re-run the automatic checks and re-sweep the changed areas from both angles.
3. Only when both are clean, render the final images and share them — together, once.
   Do not ship one fix at a time and let the reviewer find the next problem.
4. When feedback is ambiguous ("that tree"), ask which object before changing anything, and undo
   any change made on a wrong guess.
5. After any scene change, stop/restart long renders (turntables, night versions) so nothing stale
   is delivered.

## 5. Blender gotchas that bit us

- `bpy.ops.object.transform_apply(scale=True)` also applies location and rotation unless told not to.
- Never name a helper script after a stdlib module (`inspect.py` broke bpy).
- Names get `.001` suffixes; compare base names.
- Blender 5 has layered actions (`action.fcurves` is gone): animate turntables by setting transforms per frame.
- Ortho cameras ignore world gradients; use a backdrop plane.
- glTF does not carry procedural textures; bake first.
- Boolean of a sphere from a sphere leaves a glowing inner bowl; cut flat shapes for crescents and similar.
