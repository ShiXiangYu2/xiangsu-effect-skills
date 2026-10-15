<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# Dimension Basis — compose ANY effect from a finite set of axes

Read this right after picking a template, BEFORE choosing any numbers. Effects are
infinite; the **axes are finite (~10)**. Every particle effect — listed in a recipe
or not — is a setting of these dimensions. Your job on a creative brief is:
decompose the prompt's nouns/adjectives onto the axes, write each axis's setting,
then iterate by screenshot. Recipes are pre-derived points in this space —
accelerators, never the boundary of what you can make.

## 1. The axes

| # | Dimension | Where it lives | Typical settings |
|---|---|---|---|
| 1 | **Emission shape** — where particles are born | origin (default) · box volume (`BOX_SIZE_X/Y/Z` defines, §3.0e) · any parametric shape — ring/spiral/line/heart-curve (override `POSITION INIT` in init.comp) · mesh-silhouette point cloud (`runtime.emit_points`, §3.0) | a ring: `px=cos(a)*R, py=sin(a)*R` with `a = Rand(seed)*6.2832` |
| 2 | **Emission rhythm** — continuous, burst, pulsed | `uniforms.spawn` — **`originalSpawnRate` is the operative knob** (particles/sec); while nonzero the controller OVERWRITES `spawnRateMin/Max`+`delayMin/Max` from it each frame, so set `originalSpawnRate`, OR set it `0` to let static `spawnRateMin/Max` apply. One-shot population: PhysicsMesh `isLoop:0`; pre-filled scene: `runtime.prewarmFrameCount` | continuous rain: `originalSpawnRate` 40; single burst: `0` + high static rate, long delay |
| 3 | **Population / density** | `alive ≈ (spawnRate/delay) × lifetime`, capped by `capacity` (supply law — `references/supply-budget.md`) | see density anchors below; ALWAYS size `capacity ≥ demand × lifetime_max` |
| 4 | **Initial velocity field** | `VELOCITY INIT` in init.comp; magnitude via `SPEED_MIN/MAX` | radial burst (template default) · directional (`vy = SPEED…`) · tangential swirl (`v = cross(axis, pos)`) · zero (hold position) |
| 5 | **Forces over life** | `GRAVITY` (exposed) · built-in wander `TURB_AMP/TURB_FREQ` (§3.0e) · anything else in update.comp `FORCE COMPUTATION` (attractor, drag, noise field, vortex) | smoke rise: GRAVITY −0.5 + TURB_AMP 0.6 |
| 6 | **Lifetime curves** — how a particle evolves as it ages | size taper `SIZE_END(birth)→SIZE_START(death)` · alpha envelope (vert `ALPHA` section) · colour over life (`runtime.color_ramp`, §3.0b) | fade-in/out envelope: `smoothstep(0,.15,t)*smoothstep(1,.85,t)` |
| 7 | **Particle look** — what one particle is | flat `TINT_R/G/B` · sprite texture (`Map0` + `USE_TEX_ALPHA:1`) · procedural soft circle (`USE_TEX_ALPHA:0`) · procedural masks in frag `SHAPE` (star/cross/sdf) · real mesh (StandardMesh) | **Choose the ASSET deliberately, not by default** — see §5 "Particle identity & asset sourcing" below and the USE_TEX_ALPHA anchor |
| 8 | **Blend / luminosity** — does light accumulate? | frag `FINAL OUTPUT`: normal `vec4(tint*alpha, alpha)` vs **additive `vec4(tint*alpha, 0.0)`** | additive = glow/fire/magic/energy; normal = smoke/solids. See §3 below |
| 9 | **Layering / structure** | multiple systems in ONE bundle: core + halo via `shared_pool_with` (re-render same pool, different size/shader — events-multisystem.md) · chains/trails/bursts via `events` (§2) | classic glow = small bright core + 3–4× dim halo on the same pool |
| 10 | **Variation** — why it doesn't look mechanical | `*_MIN/MAX` ranges · per-particle palette/shape/phase in free SSBO slots (init.comp) · mesh/physics `COLOR/SCALE/SPIN_VARIETY` | 6-colour palette in slot 9, shape enum in slot 11 |

A brief like "magic vortex" decomposes as: shape=ring(1) + tangential swirl(4) +
inward attractor(5) + violet→cyan ramp(6) + soft circles(7) + additive(8) +
core/halo layers(9). Write those settings; that IS the effect.

## 2. Calibration anchors (measured live; default portrait camera, host at origin)

The #1 reason a technically-correct effect looks wrong is mis-scaled numbers.
These anchors were measured by rendering reference particles and reading the
screenshots — trust them over intuition:

- **Screen width ≈ 26 world units; height ≈ 46** (9:16 preview, default camera).
- **A quad of SIZE `s` renders ≈ `2s` world units wide** → `SIZE 1.0` ≈ **7.8 % of
  screen width**; `SIZE 6+` is screen-filling.
- Size feel: `0.05–0.15` fine dust/sparkle · `0.2–0.5` sparks/snow/rain ·
  `0.8–1.5` distinct orbs · `2–4` large glow blobs.
- Speed feel (units/sec): `0.5–1` ambient drift · `2–5` lively motion · `8+`
  fast streaks; a particle travels `speed × lifetime` units — keep it within ~26
  if it must stay on screen.
- Density feel (alive count): `<10` sparse accents · `30–80` readable cloud ·
  `150–400` dense field. `alive = rate × lifetime`; check `capacity` covers it.
- **⚠️ `USE_TEX_ALPHA` defaults to 1.0** (silhouette = texture alpha). With an
  OPAQUE texture (e.g. builtin white `…1543`) particles render as **hard
  squares**. Two correct paths for soft dots (both live-verified): bind the
  builtin **`Default-Particle.png`** (`00000000-0000-0000-0000-00000000004g`,
  soft circular alpha — works at the DEFAULT 1.0; the stock choice), or white
  `…1543` + `USE_TEX_ALPHA: 0.0` (procedural circle — pairs with the additive
  glow recipe below).
- Mesh templates: apparent size = mesh native bounds × `SCALE` (builtin Heart at
  `SCALE 0.8` ≈ 13 % screen width). Mesh bounds vary wildly — screenshot once to
  calibrate any unfamiliar mesh before tuning.

## 3. Additive glow (live-verified)

In the quad frag's `FINAL OUTPUT`, replace `color0 = vec4(tint * alpha, alpha);`
with:

```glsl
// ADDITIVE: premultiplied blend (src=One) with alpha=0 keeps dst -> pure add
color0 = vec4(tint * alpha, 0.0);
```

The output blend is premultiplied (`srcColor=One`), so zero destination-fade makes
the particle **add light**: overlaps brighten through the tint toward white-hot —
verified live (flat opaque blob → luminous core with hot centre). This is the
single biggest lever for "glow / ornate / energy".

- Combine with: `USE_TEX_ALPHA: 0` (soft circle), a warm/saturated `TINT`, larger
  `SIZE`, and a `shared_pool_with` halo layer.
- Additive can only BRIGHTEN — for dark smoke/solid objects keep the normal
  premultiplied output (they need occlusion).
- Per-particle mixing is fine: you can output additive in one system and normal
  in another layer of the same bundle.

### Opaque black-background sprite (no usable alpha) — SAME `alpha=0` trick

The trick above also fixes a very common drop-in case: a texture whose background
is **solid BLACK with no useful alpha channel** — most lightning / fire / spark /
electric flipbook sheets, and many imported PNGs. Under the default premultiplied
output it renders as a **black square** (the opaque black background is drawn).

The fix is the SAME one-line frag edit — change the FINAL OUTPUT to:

```glsl
color0 = vec4(tint * alpha, 0.0);   // additive (alpha=0)
```

Why it keys the black out: `tint` is the per-pixel sprite colour
(`v0.rgb * texColor.rgb`, or `texColor.rgb` in the flipbook frag), so a **black
texel gives `tint = 0` → `color0.rgb = 0`**. With `alpha = 0` the premultiplied
blend keeps `dst` (the background shows through) and bright pixels ADD (glow). No
texture alpha needed. **Live-verified** on an opaque lightning sheet: black square
→ glowing bolts over the camera feed.

> ⚠️ There is **no `runtime.blendMode` / blend-mode system.json field**. The
> StandardQuad/Strip output blend is fixed (premultiplied); the additive look is
> produced in the FRAG (`alpha=0`), as above — NOT by a blend-mode switch. An
> opaque-black-bg sprite that renders as a black box is a FRAG fix, never a config
> field.

## 4. Colour — the one non-obvious rule

**`TINT` / `COLOR` are LINEAR RGB, not sRGB.** The mood palettes themselves (fire-warm,
ice-blue, gold, toxic-green, pastel…) you already know — just feed LINEAR values, not the
sRGB hexes you'd reach for by habit. For colour that EVOLVES over life (always richer than
a flat tint): `runtime.color_ramp` stops `[[t,r,g,b],…]`, e.g. fire
`[[0, 1,0.95,0.7],[0.4, 1,0.6,0.15],[1, 0.6,0.1,0.05]]`.

## 5. Particle identity & asset sourcing — decide what ONE particle IS

A bare white dot is a CHOICE, not a default. For every effect, ask: what should a
single particle look like for THIS brief — a glow dot? a snowflake sprite? a petal?
a 3D coin mesh? Then SOURCE that asset deliberately:

| Need | Source |
|---|---|
| Soft glow dot | builtin `Default-Particle.png` `00000000-0000-0000-0000-00000000004g` (soft circular alpha, works at default `USE_TEX_ALPHA`) |
| Flat colour / procedural shapes / additive glow base | builtin white `…000000001543` + `USE_TEX_ALPHA: 0` |
| Heart sprite | builtin `defaultHeart.png` `…000000001001` (texture) / Heart mesh `…000000001002` |
| Water droplet | builtin `water_particle.png` `…000002000210` |
| A sprite of anything else (snowflake, petal, star, leaf, rune…) | existing project texture or a local file imported through `edit_by_dsl.import_resource(...)` |
| A user-mentioned asset ("the one I imported…") | `list_resources` → `inspect` for the GUID — NEVER re-import a duplicate |
| 3D shapes (coins, debris, confetti pieces…) | mesh templates + existing project mesh / `edit_by_dsl.import_resource(...)` (see StandardMesh §3.2 pre-step) |

Two rules:
- **Route every asset through `shared_resources` + `{ref}`** — each becomes a
  swappable picker on the asset panel (`references/asset-inspector.md` §5), so the
  user can replace the texture/mesh later without you. A hardcoded or missing
  binding is a dead end for the user.
- **If the brief names a THING (snow, petals, coins, bubbles), the particle should
  LOOK like that thing** — source a sprite/mesh for it; don't ship a white dot and
  call it snow. Conversely pure light phenomena (glow, sparks, magic) are exactly
  where procedural dots + additive shine.

## 6. From adjectives to axes

Decompose the adjective onto the axes exactly like the magic-vortex example in §1: pick the 2–3
axes it most constrains, set them, screenshot, iterate. The mapping itself is ordinary
reasoning (rich → more layers/colour/variation; subtle → sparse + slow + no additive
saturation). The two **engine-specific, highest-leverage** levers worth reaching for first
on "ornate / dazzling / cool" are **additive (§3)** and **small-bright-core + large-dim-halo
layering (§1 axis 9)**. Never refuse because "no recipe matches": the axes cover everything
the engine can render.
