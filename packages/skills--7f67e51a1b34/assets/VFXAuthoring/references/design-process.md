<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first; read references/dimension-basis.md before this file. -->

# Design Process — how to CREATE an effect from a brief (not just compile one)

A technically-correct effect is not a good effect. This file is the working
method that turns "gorgeous fireworks / dreamy magic vortex / …" into something that
LOOKS right. It assumes the dimension axes + calibration anchors from
`references/dimension-basis.md`.

## The loop: Spec → Axes → Passes → Critique

### Step 1 — Write the VISUAL SPEC first (words, no API calls)

Before touching any tool, write 5–8 lines describing what a viewer would see:
phases and their durations, layers, palette script, and where things sit in the
frame. Example ("gorgeous fireworks"):

> Rockets launch from below the frame every ~0.8s (1.4s ascent, bright warm-white
> head + golden bead trail). At the apex (upper third) each bursts into ~140
> sparks that fly out to ~half the screen width, colour-evolving white-hot → gold
> → deep red while gravity pulls them down over ~1.3s. Sparks carry a soft glow
> halo. Continuous show, 1–2 bursts visible at any time.

Every phrase in the spec becomes a number later; if you can't write the spec,
you don't understand the brief yet — ask or decide, then write it.

### Step 2 — Map the spec onto the dimension axes

Go phrase by phrase through the spec and assign axes (`dimension-basis.md` §1),
using the calibration anchors for every number ("upper third" → y≈+8 of the
±23 frame; "half the screen width" → spread radius ≈ 7–9 units → spark speed ≈
radius / lifetime). Ballistics are just arithmetic: launch y=-22 to apex y=+8 in
the 1.45s lifetime ⇒ `vy0 = 1.45·g` and `vy0²/2g = 30` ⇒ `g≈28, vy0≈40`.

**Part of this step is deciding what ONE particle IS and sourcing its asset**
(`dimension-basis.md` §5): a brief that names a THING (snow, petals, coins,
bubbles) needs a sprite (existing project texture or `edit_by_dsl.import_resource(...)`) or a mesh — not a
white dot; pure light phenomena (glow, sparks, magic) want the builtin
`Default-Particle.png` or procedural circles + additive. Route every texture/mesh
through `shared_resources` so it becomes a user-swappable panel picker.

### Step 3 — Build in PASSES, verify each with a timeline capture

| Pass | What you set | What you verify (timeline capture, 3–4 frames) |
|---|---|---|
| **P1 Structure** | systems, events, spawn budget, trajectories (init/update edits). Default look — don't touch colour/blend yet. | Topology: does each stage happen, in order, at the right place/time? Are counts plausible? |
| **P2 Look** | colour ramps, tints, blend (additive?), texture/shape, alpha envelopes. | Palette reads as specced; luminosity right (additive overlaps brighten); nothing washed out or invisible. |
| **P3 Polish** | densities, sizes, halo layers, variation, rhythm. | The adjective: does it actually read as ornate / dreamy / cool? Composition fills the intended frame region. |

One pass = one `edit` batch + one timeline capture (`reset_preview` + several
`wait`+`screenshot` in ONE `interact_by_dsl` — see SKILL.md §Verification). Never
stack two passes without looking; a wrong P1 invalidates every P2 number.

### Step 4 — Critique rubric (apply to every timeline capture)

Read the frames as a SEQUENCE and check:

1. **Stages & timing** — every phase of the spec occurs, at its specced time/place.
2. **Motion** — things move between frames; spacing of emitted children < their size (a trail with `spacing = parent_speed / event_rate` wider than the child quad reads as dots, not a line).
3. **Scale vs frame** — compare against the anchors (a "burst" spanning 3 units of a 26-unit-wide screen is a puff, not a burst).
4. **Value structure** — is there a brightness hierarchy (hot core / mid tone / dim edge)? Flat single-tone = not yet "ornate".
5. **Colour evolution** — does colour change over a particle's life (ramp) or is it a dead flat tint?
6. **Parasites** — anything rendering that you did NOT spec? (See the self-spawn gotcha in `events-multisystem.md` — a mystery emitter at screen centre is the classic one.)
7. **Rhythm** — steady-state density matches the spec; no dead gaps unless specced.
8. **Particle identity** — does a single particle look like what the brief NAMES
   (snowflake/petal/coin = sprite or mesh), or did a generic white dot sneak in?
   Wrong identity is a sourcing task (`dimension-basis.md` §5), not a tuning task.

Fix the worst item, re-capture, repeat. 2–3 iterations is normal; the examples
below each took 3.

---

## ⚠️ The derivations below are PROCESS TRACES — floors, not targets

Read them to imitate the LOOP (spec → axes → passes → critique), never the look:

- **Their numbers, palettes, layouts and system structures belong to THEIR briefs
  only.** A different brief must produce a different spec and therefore different
  settings — if your result visually resembles these examples despite a different
  brief, that is an anchoring failure: throw the numbers away and re-derive from
  YOUR spec.
- **The quality bar is YOUR step-1 spec, judged by the rubric — not these
  screenshots.** Each example passed its rubric after 3 iterations; richer briefs
  deserve more iterations, more layers, textures/sprites instead of bare soft
  circles, per-particle variation, multi-palette ramps — whatever the spec
  demands. Stopping at "looks about as good as the fireworks example" is
  under-delivering on any brief that asked for more.
- **They do not bound the technique space.** Neither example uses sprite sheets,
  meshes, physics, masks, emit_points, or cross-particle forces — all of
  those remain fully available (templates + dimension axes). Pick whatever the
  brief needs.

## Worked derivation 1 — "gorgeous fireworks" (multi-system event chain)

**Spec → axes:** 4 systems in one bundle — `rocket` (StandardQuad, launch-pad
POSITION INIT at y=-22 / vy≈40 VELOCITY INIT, GRAVITY 28, lifetime 1.35–1.55)
→ events `rate OverTime 200 → trail` + `on_die count 140 → sparks`; `trail`
(tiny fading beads, lifetime ~0.45); `sparks` (SPEED 8–14, GRAVITY 3,
`color_ramp` [[0,1,.97,.85],[0.3,1,.7,.2],[1,.55,.1,.05]]); `glow`
(`shared_pool_with: sparks`, ~3× size, TINT_A 0.45). All four frags switched to
the additive output. Both event targets carry the **epsilon spawn uniforms**
(`spawnRateMax 1e-6` — see events-multisystem.md).

**What the critique loop actually caught (real run):**
- P1: trail read as separated dots — spacing = 40 u/s ÷ 80/s = 0.5 u > bead width
  0.32 u → raised event rate to 200 (rubric #2's spacing rule).
- P2: burst too small/dim — sparks sped 5–9 → 8–14 (radius ≈ speed×lifetime vs
  the "half screen ≈ 9 u" anchor), count 70 → 140, additive + ramp turned the
  flat orange blob into a white-hot-core burst.
- P3: **a mystery blurry emitter at screen centre** — the importer's default-
  spawner fallback (rubric #6), with TWO sources: the spawnRate-0 event-target
  systems AND the `shared_pool_with` glow layer (which carried no spawn uniforms
  at all). Isolated with a red-core/blue-halo minimal repro; fixed by putting the
  epsilon spawn uniforms on all three non-emitter systems; verified by a control
  run (real emitters silenced → completely empty, with a LIVE preview —
  consecutive frames differed).

## Worked derivation 2 — "dreamy magic vortex" (parametric emission + custom force field)

**Spec:** a radius-6 ring of violet wisps swirling around the subject's face,
slowly spiralling inward to a bright core; dreamy violet→blue evolution; soft
glow throughout.

**Axes:** ONE pool + halo — `wisps` (StandardQuad): POSITION INIT = ring
(`px=cos(a)·R, py=sin(a)·R`, R=6±0.4); VELOCITY INIT = tangential
(`vx=-py/R·s, vy=px/R·s`, s≈3.5–5); update FORCE = inward pull 1.4 u/s² +
tangential maintenance 0.8 u/s² (so the swirl never decays); lifetime 2.8–4;
`color_ramp` violet→indigo→blue; spawn 70/s, capacity 380; `halo`
(`shared_pool_with`, 3× size, TINT_A 0.35). Both frags additive,
`USE_TEX_ALPHA 0`.

**Result:** ring of sparkling wisps around the face, spiral-fed bright core orb
(halo accumulation), aged particles drifting in blue below — "dreamy" carried by
slow speeds + soft circles + additive + the colour ramp, exactly the adjective
mapping in dimension-basis.md §5.

---

## Lessons that generalise (from these runs)

- **Trail continuity rule**: child spacing = parent_speed / event_rate; keep it
  below the child's rendered width or the trail reads as beads.
- **Every non-emitter system needs the epsilon spawn uniforms** — event targets
  AND `shared_pool_with` layers; `spawnRate: 0` / missing spawn uniforms do NOT
  mean silent (importer fallback). Mystery centre-screen particles = this.
- **A control experiment is only valid if the preview is alive** — identical
  bytes across consecutive screenshots = a frozen/dead preview; its "empty
  screen" proves nothing. Check frames differ before trusting any negative
  result.
- **Additive is the single biggest "ornate" lever** but flattens to white when
  everything is big and overlapping — keep the hot core SMALL and let the halo
  layer carry the bloom.
- **Derive ballistics, don't guess**: with the screen anchors every "where/when"
  phrase in the spec is one line of arithmetic.
- **One pass at a time.** Each of these effects took 3 captures; every iteration
  fixed the single worst rubric item.
