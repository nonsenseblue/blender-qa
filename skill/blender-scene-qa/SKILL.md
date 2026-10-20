---
name: blender-scene-qa
description: Build and self-review Blender scenes (dioramas, rooms, props, any bpy scene) so the person never has to hunt for defects. Use whenever you model, edit or render anything in Blender/bpy — before showing any render, run the mesh-accurate automatic checks (overlap, floating, z-fighting, hidden-inside, keep-clear, rule packs) and the visual review packet (camera views + zoomed multi-angle sweep + checklist), fix everything, and only then share.
---

# Blender scene QA

The person reviewing your renders should never be the one who finds that a chair faces the
wall, a plant floats above its pot, or the "sink" is a flat grey plate. Every one of those
happened before this skill existed — see `PITFALLS.md` in the repo for the full list.

The tools live in the `blender_qa` package of this repo (locate it with
`git rev-parse --show-toplevel` or the path where the repo was cloned). They run with the `bpy`
module (`pip install bpy`, matching Python version) or inside Blender (`blender -b`).

## 1. Build so the checks can work

The checks need no configuration, but they get sharper with structure:

- Wrap every piece of furniture / prop / feature in its own parent empty:
  `with item("sofa"): ...` (`blender_qa.kit.item`), or give it its own collection. Without grouping,
  clashes between loose objects can only be reported as *warnings*.
- Tag what matters (`item("chair", role="seat", front="+y")`, `role="table"`, `role="stairs"`,
  `role="fly"`...): tags drive the rule packs and the keep-clear zones, and override every guess.
- Use semantic helpers instead of raw boxes where a mistake is easy:
  `kit.chair(x, y, face=...)` (backrest always opposite the facing side),
  `kit.basin(...)` (anything that holds water is hollow), `kit.potted_plant(...)` (soil visible,
  leaves grow from it), `kit.slab(...)` (applies scale without moving the origin).
- Name things meant to fly (clouds, balloons, stars) recognisably, or tag them `qa_role=fly`.

## 2. Automatic checks — no errors before anyone sees a render

```bash
python -m blender_qa check scene.blend --warnings --json qa.json
```

| check | finds |
|---|---|
| `overlap` | two features whose surfaces pass through each other, or one sealed inside another |
| `hidden_inside` | a part completely inside a closed part of the same feature (books in a solid shelf, soil inside a solid pot) |
| `keep_clear` | anything in a zone that must stay walkable (tagged stairs/doors/walkways, or zones in qa.toml) |
| `floating` | parts not touching anything that is (transitively) grounded: leaves over a pot, bulbs without a wire, a window off a slanted wall |
| `zfight` | visible coplanar overlapping faces of different materials → black seams/dots/flicker |
| `seat_facing` | a tagged seat turning its back on its table/desk/screen (rule pack `interior`) |

Everything is judged on the real mesh (BVH), ground is recognised from geometry, settings live in
`qa.toml` next to the .blend. Exit code 1 means errors. Fix real ones in the *build script*,
not by hand in the .blend. **Read the warnings too**: they involve loose objects and are mostly
deliberate joins, but a book through a picture frame was hiding among them. Treat false positives
by grouping/tagging, never by ignoring the report. For scattered decor (shrubs, flowers, pebbles)
call `checks.declutter(...)` in the build so decor yields to solids automatically.

## 3. Visual review — look at every image

```bash
python -m blender_qa review scene.blend --out qa_review
```

This renders every scene camera, sweeps the whole scene as zoomed tiles from two angles, runs the
checks and writes `qa_review/review.md`. Open every image (camera views, `sweep_front.png`,
`sweep_left.png`; rows = back→front, columns = left→right) and go through it with this checklist.
For anything an automatic finding points at, render a close-up from two angles before deciding.
Write down every problem before fixing anything.

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

**Physical plausibility** — lighting, shadows and sky agree (a crescent has no round halo); water
falls and spreads; neighbouring objects are at a consistent scale.

**Render** — no black seams or dots, no washed-out blacks, subject not clipped by the frame,
no key feature hidden behind another object from the hero camera.

## 4. Fix, re-run, then share

1. Fix everything found in 2 and 3 in the build script.
2. Re-run the automatic checks and re-review the changed areas from both angles.
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
