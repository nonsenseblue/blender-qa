# Pitfalls

Every problem below actually happened while building the example scenes in this repo
(a cosy island diorama, a café street and a two-storey house interior),
and almost all of them were spotted by the person reviewing the renders, not by the author.
Each entry says what went wrong, why, how it was fixed, and how to catch it next time
(**Catch** names the `blender_qa` check or the manual review step that finds it).

## 1. Recognisability: "what is that?"

Low-poly stylisation is fine; an object that does not read as itself is not.
If a viewer has to ask what something is, it is a defect.

| # | What happened | Fix | Catch |
|---|---|---|---|
| 1.1 | Hob = four grey discs glued on the worktop ("buttons"). | Black glass panel, chrome burner rings, knobs on the front edge, a pot on one burner. | Manual: zoomed sweep, ask "would a stranger name this?" |
| 1.2 | Kitchen sink = flat grey rectangle flush with the worktop ("a mat"). | Cut a hole in worktop and cabinet, add a recessed hollow basin with a drain. | `zfight`/manual: anything meant to hold water must be concave. |
| 1.3 | Wash basins = a solid block / a flat disc. | Hollow basin (floor + four walls + drain); wall-hung or vessel style. | Manual. |
| 1.4 | Windows = a pale blue plane on the wall. | Frame, cross mullions, sill, recessed glass; curtains where it fits. | Manual. |
| 1.5 | Wall art = two coloured squares. | Wooden frame, white mount, simple imagery (mountains + sun, leaf study). | Manual. |
| 1.6 | PC tower placed inside a desk leg; black front looked like a hole. | Stand it beside the desk, light case, front panel, vents, power LED. | `overlap`, manual. |
| 1.7 | Toilets = two boxes. | Pedestal + oval bowl + seat ring + raised lid against the cistern + flush button. | Manual. |
| 1.8 | Taps = a single vertical rod. | Stem + spout reaching over the basin + outlet. | Manual. |
| 1.9 | Sideboard and hall bench = plain solid boxes. | Doors/handles/feet, items on top; bench with legs and a seat pad. | Manual: "is this just a box?" |
| 1.10 | Boat = squashed red ellipsoid with a plank ("a hot dog"). | Lower half-sphere with pinched bow/stern, solidify shell, thwarts, oars. | Manual. |
| 1.11 | Moon = flat white disc; then a full moon with a dark centre; then a crescent inside a round halo. | Flat crescent from two discs (boolean of *flat* shapes — a sphere minus a sphere leaves a glowing inner bowl), faint craters, and a glow only off the lit limb (grow the outer disc, keep the same bite) — a crescent has no round halo. | Manual: is the lighting physically consistent? |
| 1.12 | Stars "look like snow": too many, all the same size, also below the horizon. | ~90 stars, varied size/brightness/tint, only in the upper sky, gradient sky backdrop. | Manual. |
| 1.13 | Waterfall ends in mid-air with a blob — "a giant water drop". | Widen the stream as it falls, add streaks, dissolve the end into a mist cloud. | Manual. |
| 1.14 | Windmill sails a jumble of planks. | Symmetric spars with sails on them, hub clear of the cap. | Manual, check from 2+ angles. |
| 1.15 | Greenhouse: flowers embedded in a solid refracting glass block; then "a big table" inside. | Thin panes with IOR 1.0; fill it with what a greenhouse holds (raised beds, a small tree, hanging pots). | Manual: does the content match the place? |
| 1.16 | Cartoon animals built from primitives looked creepy. | Avoid primitive-blob animals unless asked; use a reference; keep proportions cute; delete when in doubt. | Manual. |
| 1.17 | "OPEN" sign placed at the top edge of the door, hidden under the awning. | Put it on the door glass. | Manual: is every label actually visible from the camera? |

## 2. Solids hiding their insides

A closed box hides everything placed inside it.

| # | What happened | Fix | Catch |
|---|---|---|---|
| 2.1 | Bookshelf was a solid block: books inside were invisible ("a chest of drawers"). | Back panel + sides + shelves. | `hidden_inside`. |
| 2.2 | Bathtub was solid: the water inside never rendered. | Floor + four sides, water slab inside, a rubber duck. | Same. |
| 2.3 | Hollow boat showed lake water inside the hull. | Raise the boat; add floorboards above the waterline. | Manual from the camera angle. |
| 2.4 | Soil disc placed 1 cm *below* the top of a solid pot cylinder: never rendered (in every potted plant, including the kit helper). | Soil sits on the pot top, inside the rim. | `hidden_inside`. |
| 2.5 | Lemons placed inside the tree crown sphere: invisible. | Put fruit on the surface so it pokes out. | `hidden_inside`. |

## 3. Orientation and logic

| # | What happened | Fix | Catch |
|---|---|---|---|
| 3.1 | Desk chair with the backrest on the desk side. | `chair(x, y, face)` helper: backrest always opposite the facing direction. | Manual: every seat faces what it is for. |
| 3.2 | Nightstand at the foot of the bed. | Nightstands at the headboard, one per side. | Manual checklist. |
| 3.3 | Bridge laid *along* the river. | Rotate the deck perpendicular to the local river tangent. | Manual. |
| 3.4 | Awning sloping up and away from the wall. | Slope down and out; check sign of the rotation. | Manual. |
| 3.5 | TV seen from behind from the only camera. | Put the TV on a tall (uncut) wall, sofa faces it with its back to the camera. | Manual: things with a "front" face the camera when possible. |
| 3.6 | Cut-away walls hid the bathroom fittings. | Exterior cut walls lower (0.6 m) than interior partitions (0.95 m). | Manual sweep. |
| 3.7 | A hob, a window and wall cabinets competing for the same wall. | Plan wall elevations: cabinets, window and hood side by side. | `overlap`. |

## 4. Circulation: can you actually walk there?

| # | What happened | Fix | Catch |
|---|---|---|---|
| 4.1 | Flower stand + planter tree walled off the pavement behind the shop. | Stand against the shop wall; tree removed. | Manual: trace a path from every door. |
| 4.2 | Potted plant at the foot of the stairs. | Move it. | `--keep-clear` zones (stairs, doors) in `overlap`. |
| 4.3 | Upstairs the stairwell was fenced on every side — no way off the stairs. | Open the rail at the top end toward the landing. | Manual: walk the stairs in your head. |
| 4.4 | Trees blocking the exit of a plaza. | Keep exits clear. | `--keep-clear`. |
| 4.5 | Misread feedback: removed the wrong trees. | Ask which object when feedback is ambiguous; restore anything removed by mistake. | Process. |

## 5. Interpenetration (clipping)

| # | What happened | Fix | Catch |
|---|---|---|---|
| 5.1 | Sheep standing inside a tree trunk. | Move the tree. | `overlap`. |
| 5.2 | Lamp-post base sunk into the ground on a paving seam. | Base sits on the surface; avoid seams. | `overlap`, `floating`. |
| 5.3 | Boat overlapping the jetty; jetty mostly on land. | Jetty from shore into water, boat parallel with a gap. | `overlap`. |
| 5.4 | House porch on the lake-shore stones. | Move the house. Classify small rocks as *decor*, not ground, so they are checked. | `overlap` (ground classification!). |
| 5.5 | Shrubs ringing a plaza pushed into café chairs. | Decor auto-yields to solids. | `declutter`. |
| 5.6 | Roof caps swallowing an AC unit and greenhouse posts. | Caps sit *on* the roof; group caps with their building. | `overlap`. |
| 5.7 | Picture frames hung over a window; balcony rail ending inside a wall. | Plan wall elevations; trim rails at walls. | `overlap`. |
| 5.8 | Helper called with the cistern position instead of the bowl centre → toilet in the wall. | Document helper argument semantics; re-run checks after every helper change. | `overlap`. |
| 5.9 | Picture frame hung through the books on a wall shelf. The scene was ungrouped, so it showed up only as a *warning* among deliberate joins. | Move the frames to clear wall; group scenes so clashes are definite errors. | `overlap` warnings — read them. |

## 6. Floating objects

| # | What happened | Fix | Catch |
|---|---|---|---|
| 6.1 | Plant leaves hovering above the pot. | Soil disc, stems, leaves start at the soil. | `floating`. |
| 6.2 | Cushions hovering above the seat. | Rest on the seat against the back. | `floating`. |
| 6.3 | Handles 1.5 cm off a door; towel rail 2.5 cm off a wall; tap above the tub rim. | Snap to the surface. | `floating` (tolerance ~1 cm). |
| 6.4 | Wall-mounted items above a cut-away wall's height float in the air. | In cut-aways only mount things on full-height walls. | `floating`. |
| 6.5 | Visible stair flight hanging under the upper floor. | Thick cut floor slab hides it. | `floating`, sweep from below/side. |
| 6.6 | String lights = a row of bulbs in mid-air, no wire (café, bedroom, street). | `props.string_lights`: wire through the points, bulbs hang under it, hooks end exactly on the wall face. | `floating`. |
| 6.7 | Footbridge deck hovering above both banks; jetty planks with gaps and nothing under them. | Legs set into the banks; joists under the planks. | `floating`. |
| 6.8 | Window box placed axis-aligned next to an 8-sided tapered tower: 10 cm off the slanted wall. | Ray-cast the wall, place the box on the hit point, rotate it to the face normal. | `floating`. |
| 6.9 | Sign bracket 5 cm off the wall, porch lamp 2 cm off, balcony pot 2.5 cm above the slab, chair and bench backrests 2–6 cm above their seats. | Compute positions from the surfaces they attach to. | `floating`. |

## 7. Rendering artefacts

| # | What happened | Fix | Catch |
|---|---|---|---|
| 7.1 | Black dots/edges where two boxes share a coplanar face (basin walls, window mullion cross, wall tops at corners, duplicated fence posts). | Butt pieces instead of overlapping; offset heights by a few mm; one post per corner. | `zfight`. |
| 7.2 | Black reads as grey (AgX + bright lights + glossy). | Darker albedo, lower specular, rim lights. | Manual. |
| 7.3 | Ortho camera ignores world gradients (all rays parallel). | Put a gradient backdrop plane behind the scene. | Manual. |
| 7.4 | Text floating in front of a tilted board looks off-centre. | Place text on the board plane using the board's own axes. | `floating`. |
| 7.5 | Subject clipped by the frame / lots of empty space. | Re-frame after every layout change. | Sweep includes a full-frame tile. |
| 7.6 | One object hides another *from the camera* (windmill in front of the front door) with no physical overlap. | Check occlusion of key features from the hero camera. | Manual: hero-camera review. |
| 7.7 | Deliverables at different sizes and aspect ratios, subjects at different scales — the README gallery looked messy. | Frame every render the same way: one canvas size, subject centred at the same fill; reuse one subject box for variants of the same shot. | `blender_qa frame`. |
| 7.8 | Padding a gradient sky with one flat colour drew a visible box; stretching edge pixels smeared clouds and stars into lines. | Estimate the background per row from the border strips, smoothed over neighbouring rows. | `blender_qa frame`. |
| 7.9 | Gallery ordered by file name split variants of one scene across rows. | Order by scene; keep variants (day / night / season) side by side. | Manual. |

## 8. Blender / Python gotchas

| # | What happened | Fix |
|---|---|---|
| 8.1 | `transform_apply(scale=True)` also applies location/rotation by default → origins at world 0, later scaling shrinks toward the origin. | Pass `location=False, rotation=False` explicitly. |
| 8.2 | A helper script named `inspect.py` shadowed the stdlib module and silently broke bpy. | Never name scripts after stdlib modules. |
| 8.3 | `pkill -f island` killed the shell running it. | Kill by PID / task id. |
| 8.4 | Name-based checks broke on `.001` material/object suffixes. | Compare `name.split(".")[0]` or use custom properties. |
| 8.5 | Blender 5 layered actions: `action.fcurves` no longer exists. | Render turntables by setting the transform per frame. |
| 8.6 | glTF cannot carry procedural textures. | Bake to images before exporting. |
| 8.7 | Long background renders kept rendering a stale scene after edits. | Stop and restart renders after every scene change. |
| 8.8 | A checker loop rebound its own loop variables and silently checked the wrong pairs. | Unit-test checkers on a tiny known scene. |
| 8.9 | `bound_box` of text objects ignores the extrusion, so text touching a board looked 2 cm away. | Use the evaluated mesh's own extent. |
| 8.10 | Bounding-box overlap called a ring around a pole and two rotated boards collisions; hand-tuned name lists hid the noise. | Judge on the triangles (BVH); boxes only as a broad phase. |
| 8.11 | Z-fight false alarms: identical materials (invisible), seams buried inside a cap, zero-area faces left by bevels (random normals). | Skip same-material pairs, seams inside another closed solid, degenerate faces and sub-1 cm² overlaps. |

## 9. Process

1. Build → **run the automatic checks** (`overlap`, `floating`, `zfight`) → fix until clean.
2. **Sweep** the whole scene in zoomed tiles from at least two angles and look at every tile
   with the checklist in `skill/blender-scene-qa/SKILL.md`.
3. Fix everything found, re-run 1 and 2.
4. Only then show the result. Do not ship one fix at a time and let the reviewer find the next one.
5. When feedback is ambiguous, ask which object is meant before changing things.
6. A fix is not done until the same defect is fixed **everywhere** it exists: the improved night sky
   went into one scene while two other night scenes kept the old moon and snow-like stars. Put
   shared looks (sky, materials, helpers) in one module that every scene imports.
7. A checker tuned until your own scenes pass is not a checker. The first version used bounding
   boxes and per-scene name lists and reported "clean"; made generic (real meshes, automatic ground,
   no per-scene settings) it found 20+ defects in renders that had already been published
   (entries 1.17, 2.4–2.5, 5.9, 6.6–6.9). Test checkers on scenes they were not tuned on.
8. Before publishing, re-render **every** deliverable from the current scripts. The gallery once mixed
   fresh renders with old ones (an island still had the old "dripping" waterfall, a street night had
   a tree that had been removed, day and night shots came from different camera versions).
