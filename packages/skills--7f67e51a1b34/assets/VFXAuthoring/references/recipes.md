<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->
<!-- NOTE: recipes are template-agnostic. Apply tunables via edit_vfx_source(scope="system:<name>:defines") and shader text via scope="system:<name>:shader:<file>"; start new effects with add_vfx_source. Never hand-build a bundle. -->

# Recipes — sprite-sheet flipbook & worked examples

### Flipbook recipe (animated sprite sheets)

Use this when the user has a **sprite sheet** (one PNG with a `COLS × ROWS` grid of frames) and wants each particle to display content from that sheet — fire, smoke, explosions, sparkles, magic puffs, character poses, etc.

#### Mental model — choose the motion model FIRST

Before writing any patches, look at what a single frame of the sheet depicts. **This determines whether particles should move or stay put**, which fundamentally changes the recipe:

| What's in one frame? | Motion model | Examples |
|---|---|---|
| **A complete instance** of the effect — full fire flame, full explosion frame, full character pose | **A. Whole effect** — particles **stationary**, large. Default is **sequential** (1 particle at a time, handoff cadence, GIF-style loop). Stacking is an opt-in variant for "rich shimmer" prompts. | fire 🔥, smoke 💨, explosions 💥, lightning ⚡, magic runes 🪄 |
| **A fragment** — single spark, ember, dust mote, snowflake, raindrop | **B. Fragment** — particles **drift** with velocity, small, many (50-500), each shows one cell of variety. | sparks ✨, embers, snow ❄️, rain 🌧️, dust |

Quick check: **can you recognise the subject from a single frame alone?**
- **Yes** → "Whole effect" model. Particle stays put; sheet plays the animation as a sequential GIF-loop. (Opt-in: stack multiple particles for rich shimmer when explicitly asked.)
- **No, single frame is just a sub-element** → "Fragment" model. Particle drifts; each particle adds spatial richness.

> Common mistake: defaulting to "fragment" (the canonical's natural shape with radial velocity + gravity) when the sheet actually depicts complete effects. The visual symptom is "30 mini-fires scattered around" instead of "one fire that flickers". When unsure, **try A first** — it's correct for most user prompts ("add a fire", "smoke effect", "explosion").

Both recipes share infrastructure:

- The canonical's **slot 9** of the per-particle SSBO carries `sampCol.r` (the INIT-sample colour feature, §3.0c) by default. The flipbook repurposes it as the per-particle `texIndex` — flipbook and INIT_SAMPLE_TEX colour-bake are therefore mutually exclusive on one system. Slots 10/11 keep their sampCol writes (inert without INIT_SAMPLE_TEX).
- All UV math lives in `output.gles.vert` / `output.gles.frag`. The Metal frag is reference-only; AUSL cross-compiles GLES → both targets.
- The canonical's frag soft-circle mask is dropped in both recipes — sprite sheets carry their own alpha.

#### Recipe A — Animated complete effect (fire / smoke / explosion / lightning / magic rune)

> **Pick this when** the user prompt is one of:
> - "add a fire / flame effect with a flipbook"
> - "smoke effect" / "explosion" / "magic rune" / "lightning" with sprite sheet
> - **"each frame shows a complete X"** (the explicit Recipe-A signal)
> When you see any of these, the answer is Recipe A. Do NOT default to Texture swap or Recipe B.
>
> **Default behaviour: SEQUENTIAL playback.** One particle at a time, all spawning at frame 0, playing through every cell of the sheet, then a fresh particle takes over via crossfade — exactly like a GIF on loop. No stacking, no random per-particle phase, no flicker richness. Particles always land at the same screen position.
>
> **Switch to the LAYERED variant** (below) ONLY when the user EXPLICITLY asks for:
> - "stacked" / "layered" / "multi-layered" flicker
> - "rich shimmer" / "rich flicker" / "intense flicker"
> - "multiple flames overlapping"
> - "shimmering" or "fluctuating" intensity
>
> If the prompt doesn't mention any of these, do NOT add stacking. Sequential playback is the safer default — adding stacking when the user didn't ask makes the effect look noisy and intensifies the load on the GPU for no reason.

> 🟥 **STOP — Phase 0: MEASURE THE TEXTURE FIRST.** The shader is parameterised by 5 numbers that MUST match the actual sprite sheet you imported. Using example values produces black/garbled output regardless of how correct everything else is. Filenames lie. User-provided textures also frequently contain different grids than their names suggest. Always open the texture and count.
>
> | Token (goes into JSON `defines`) | How to obtain | Don't trust |
> |---|---|---|
> | `SHEET_COLS` | Open the imported PNG and **count columns of frames** | `flame_8x8.png` filename, user verbal claim, AIGC prompt |
> | `SHEET_ROWS` | Open the imported PNG and **count rows of frames** | Same as above |
> | `TOTAL_FRAMES` | `SHEET_COLS * SHEET_ROWS` (computed by you, written into JSON) | — |
> | `SHEET_W` | Run `inspect(<texture_guid>)` → read `width` in pixels | Filenames like `_1024.png` |
> | `SHEET_H` | Same — read `height` in pixels | Same |
> | `FPS` | Default `24` unless user specifies otherwise | — |
>
> Do not proceed to Phase 1 until you have these 6 numbers in hand. The JSON defines table in Phase 1 has a placeholder for each — write the actual measured value, not an example.
>
> ⚠️ **Recipe A is ATOMIC — all 6 patches below are REQUIRED.** The single most common failure mode of this recipe is cherry-picking "the flipbook-related patches" (init slot 9, vert/frag UV math) and skipping "the motion / spawn-rate / size patches" — the agent thinks those are unrelated tuning and leaves the canonical's defaults. The result is "particles oscillating on screen with the right cell selected" instead of "one localised flickering fire". **Every one of the 6 is necessary** — see the failure-mode table at the bottom of this recipe for which visual symptom maps to which missed patch.
>
> **The 6 REQUIRED edits (in the order they appear below):**
> 1. **JSON `defines`**: `SIZE_START/END` (large, 1.8–2.2), **`LIFETIME_MIN/MAX = TOTAL_FRAMES / FPS`** (exactly one animation cycle), **`SPEED_MIN/MAX=0`, `GRAVITY=0`**, **sheet tokens from Phase 0 (`SHEET_COLS`, `SHEET_ROWS`, `TOTAL_FRAMES`, `SHEET_W`, `SHEET_H`, `FPS`)** — skip → particles too small AND/OR drift radially AND/OR garbled cells AND/OR no clean loop
> 2. **JSON spawn uniforms — HANDOFF cadence**: `spawnRate=1`, `delay = LIFETIME − 0.4` (so a fresh particle takes over ~0.4s before the old one dies; the envelope crossfade hides the seam), `originalSpawnRate = 1 / delay` — skip → either multiple desynced particles stack (too much shimmer) or single particle dies between cycles (visible blink)
> 3. **`init.comp`**: slot 9 = `floatBitsToUint(0.0)` — every particle starts at frame 0. Skip → particles spawn at random frames and the loop never feels "in sync"
> 4. **`init.comp`**: velocity `vx=vy=vz=0` (replace the whole radial-sphere block) — **most-skipped patch** → particles drift radially from canonical's default, "oscillating on screen"
> 5. **`update.comp`**: Flipbook Player advance slot 9 by `FPS * dt` — skip → animation doesn't play, each particle freezes on its starting frame
> 6. **`output.gles.vert` + `output.gles.frag`**: curUV+nextUV in vTex.xyzw + `mix` in frag + **soft envelope** — the envelope (`smoothstep(0,0.15,t) * smoothstep(1,0.85,t)`) is LOAD-BEARING because it produces the crossfade that hides the old-dies / new-spawns handoff. Skip the mix → choppy FPS-stutter; skip the envelope → loop boundary shows a visible blink every cycle.
>
> Apply ALL 6. If any seems "optional" to you, it isn't.

The shaders below contain **no hardcoded grid or texture dimensions** — every such value is a token (UPPER_CASE identifier) that the canonical importer replaces with the value you put in JSON `defines`. **Do not edit the literal numbers in the shader snippets** — those numbers don't exist. Drive everything from the JSON defines table.

**JSON (`systems/<name>/system.json`):** bind the sprite sheet + tune defines + set the HANDOFF spawn cadence. Every number here is computed from Phase 0's 6 tokens — write the actual values, not these examples.
```js
// Phase 0 measured: SHEET_COLS=8, SHEET_ROWS=8, TOTAL_FRAMES=64, SHEET_W=512, SHEET_H=512, FPS=24.
// Derived: cycle = TOTAL_FRAMES / FPS = 64/24 ≈ 2.67  → LIFETIME = 2.7
//          overlap = 0.4 (matches the frag envelope width)
//          delay   = LIFETIME − overlap = 2.3
//          originalSpawnRate = 1 / delay ≈ 0.43

baseSource.resources.Map0 = { type: 'Texture', guid: spriteSheetGuid };
baseSource.defines = {
  ...baseSource.defines,
  // ── motion / size / lifetime (LIFETIME = exactly one cycle for sequential playback) ──
  SIZE_START: 1.8,
  SIZE_END:   2.2,
  LIFETIME_MIN: 2.7, // ← COMPUTE: TOTAL_FRAMES / FPS (one full playthrough)
  LIFETIME_MAX: 2.7, // same — fixed lifetime keeps every particle's cycle phase predictable
  SPEED_MIN: 0.0,
  SPEED_MAX: 0.0,
  GRAVITY:    0.0,
  // ── sprite-sheet layout (from Phase 0 inspection) ──
  SHEET_COLS:   8,   // ← MEASURE: column count visible in the PNG
  SHEET_ROWS:   8,   // ← MEASURE: row count visible in the PNG
  TOTAL_FRAMES: 64,  // ← COMPUTE: SHEET_COLS * SHEET_ROWS
  SHEET_W:    512,   // ← MEASURE: texture pixel width  (from inspect)
  SHEET_H:    512,   // ← MEASURE: texture pixel height (from inspect)
  FPS:         24,   // animation rate (default 24 unless user asks otherwise)
};
// Handoff cadence: a fresh particle spawns ~0.4s before the old one dies.
// During that 0.4s window both are partially visible (one fading out via envelope,
// one fading in) — the eye reads it as one continuous fire.
for (const u of baseSource.contexts.spawn.uniforms) {
  if (u.name === 'spawnRateMin' || u.name === 'spawnRateMax') u.value = 1.0;
  if (u.name === 'delayMin' || u.name === 'delayMax')         u.value = 2.3;  // = LIFETIME − 0.4
  if (u.name === 'originalSpawnRate')                          u.value = 0.43; // = 1 / delay
}
```
**The `8 / 8 / 64 / 512 / 512 / 24` above are example values for a fictional 8×8@512px@24fps sheet.** Replace them with what `inspect(<texture_guid>)` returns and what you visually counted. If the texture is 10 cols × 6 rows at 1024×1024, the table reads `SHEET_COLS: 10, SHEET_ROWS: 6, TOTAL_FRAMES: 60, SHEET_W: 1024, SHEET_H: 1024` — and `LIFETIME` becomes `60/24 = 2.5`, `delayMin/Max` becomes `2.1`, `originalSpawnRate` becomes `0.48`.

**Startup-gap caveat — known constraint of sequential playback.** `delayMin` is both the inter-spawn interval AND the time until the first spawn — so the scene is empty for ~`LIFETIME − 0.4` seconds after preview start. Three options, in order of preference:
- **Accept the wind-up** — "ignite-on-record" / "magic-cast" / spell-charging effects benefit from a brief blank ramp-up and this is usually fine
- **Pick a shorter cycle** — if the user has a choice of sheet, prefer one whose `TOTAL_FRAMES / FPS ≤ 1.0` so the gap is barely noticeable
- **Prewarm** — set `runtime.prewarmFrameCount` in the JSON to advance simulation before t=0 (rough formula: `ceil((LIFETIME + 0.4) / runtime.prewarmDeltaTime)` — for a 30 Hz prewarm and 2.7s cycle, ~95 frames). Costs a one-time simulation burst at scene load.

**`shaders/init.comp`** — write `0.0` into slot 9 as **float bits** (every particle starts at frame 0; update.comp advances it with fractional precision for blending) and zero velocity / position spread.

Replace:
```glsl
attributeBuffer_buf[base +  9u] = floatBitsToUint(sampCol.r); // slot 9  = sampled R
```
with:
```glsl
// Sequential playback: every particle starts at frame 0. No random per-particle
// phase — the handoff spawn cadence + envelope crossfade keep one continuous loop.
// Stored as float bits because update.comp advances texIndex with fractional precision
// (needed for Flipbook Blend in frag).
attributeBuffer_buf[base +  9u] = floatBitsToUint(0.0);
```

Replace the velocity block:
```glsl
    float theta = Rand(seed) * 6.2831853;
    float phi   = acos(1.0 - 2.0 * Rand(seed));
    float speed = SPEED_MIN + Rand(seed) * (SPEED_MAX - SPEED_MIN);
    float vx = speed * sin(phi) * cos(theta);
    float vy = speed * cos(phi);
    float vz = speed * sin(phi) * sin(theta);
```
with:
```glsl
    // Whole-effect model: particles stay put; the sheet animation is the motion.
    float vx = 0.0;
    float vy = 0.0;
    float vz = 0.0;
```

Position stays at origin (canonical default).

**`shaders/update.comp`** — Flipbook Player: advance slot 9 as a float so `fract(texIndex)` is meaningful for blending.

Replace:
```glsl
        } else {
            // Apply gravity (−Y world axis). GRAVITY is token-replaced by the importer
            // from system.json -> defines.
            vy -= GRAVITY * dt;
```
with:
```glsl
        } else {
            // Flipbook Player: advance slot-9 texIndex by FPS as a float, wrap at TOTAL_FRAMES.
            // FPS and TOTAL_FRAMES are token-replaced by the importer from JSON defines —
            // DO NOT write literal numbers (24.0 / 64.0). The whole point is that this
            // shader works for ANY sheet layout / FPS the user provides.
            float texIndex_f   = uintBitsToFloat(attributeBuffer_buf[base + 9u]);
            texIndex_f         = mod(texIndex_f + float(FPS) * dt, float(TOTAL_FRAMES));
            attributeBuffer_buf[base + 9u] = floatBitsToUint(texIndex_f);
            // Apply gravity (−Y world axis). GRAVITY is token-replaced by the importer
            // from system.json -> defines.
            vy -= GRAVITY * dt;
```

**`shaders/output.gles.vert`** — compute **both** current-frame and next-frame cell UVs into `vTex.xyzw`, pass `fract(texIndex)` via `v0.r` so frag can blend.

Replace (live-particle branch):
```glsl
        vTex = vec4(tex_cord.x, 1.0 - tex_cord.y, 0.0, 0.0);
        v0   = vec4(1.0, 1.0, 1.0, alpha);
```
with:
```glsl
        // Flipbook Blend: vert computes both current + next frame cell UVs.
        // SHEET_COLS / SHEET_ROWS / SHEET_W / SHEET_H are token-replaced from JSON defines —
        // DO NOT write literals (8.0 / 512.0). This shader is layout-agnostic.
        float texIndex = uintBitsToFloat(attributeBuffer_buf[base + 9u]);
#ifdef VFX_COMPAT_MODE
        texIndex = 0.0;
#endif
        float cols       = float(SHEET_COLS);
        float rows       = float(SHEET_ROWS);
        float total      = cols * rows;
        float curFrame   = mod(floor(texIndex), total);
        float nextFrame  = mod(ceil(texIndex),  total);
        vec2  cellSize   = vec2(1.0 / cols, 1.0 / rows);
        vec2  halfTexel  = 0.5 / vec2(float(SHEET_W), float(SHEET_H));
        vec2  uvSize     = cellSize - 2.0 * halfTexel;
        vec2  quadUV     = vec2(tex_cord.x, 1.0 - tex_cord.y);
        // Row inverted: frame 0 = top-left of sheet (typical authoring convention).
        vec2  cellCur    = vec2(mod(curFrame,  cols), (rows - 1.0) - floor(curFrame  / cols)) * cellSize;
        vec2  cellNext   = vec2(mod(nextFrame, cols), (rows - 1.0) - floor(nextFrame / cols)) * cellSize;
        vTex = vec4(cellCur + halfTexel + quadUV * uvSize,
                    cellNext + halfTexel + quadUV * uvSize);
        // Pack blend factor fract(texIndex) into v0.r; .gba unused, alpha kept.
        v0   = vec4(fract(texIndex), 1.0, 1.0, alpha);
```

**`shaders/output.gles.frag`** — sample both UVs and mix; apply soft alpha envelope (fade-in + fade-out via smoothstep on `t = age/lifetime`).

Replace this body:
```glsl
    vec2 uv = vTex.xy;

    // Soft circular falloff: compute radial distance from quad centre.
    // UV origin is at the corner (0,0); centre is at (0.5, 0.5).
    vec2  centeredUV = uv - 0.5;
    float distSq     = dot(centeredUV, centeredUV) * 4.0; // 0 at centre, 1 at rim
    float shape      = 1.0 - smoothstep(0.0, 1.0, distSq);

    // Combine age-based alpha (from v0.a) with the circular shape falloff.
    // Drop the Map0 texture alpha multiplier — if the texture binding fails the
    // sampler returns 0 and the particle becomes invisible. Use a fixed tint mixed
    // with the optional texture sample so particles always render.
    vec4 texColor = texture(Map0, uv);
    vec3 tint = mix(v0.rgb, v0.rgb * texColor.rgb, step(0.001, texColor.a));
    float alpha = v0.a * shape;
```
with:
```glsl
    // Flipbook Blend: sample current + next frame, mix by v0.r = fract(texIndex).
    // textureLod(.., 0.0) disables mip selection — sprite-sheet mips would
    // downsample across cell boundaries and muddy small particles.
    vec4 cur = textureLod(Map0, vTex.xy, 0.0);
    vec4 nxt = textureLod(Map0, vTex.zw, 0.0);
    vec4 texColor = mix(cur, nxt, v0.r);
    // Use the sprite's own colour + alpha. No tint, no procedural soft circle.
    vec3 tint = texColor.rgb;
    // Soft envelope: fade in over first 15% of life, fade out over last 15%.
    // v2.w = age, v1.w = lifetime (already exposed by canonical vert).
    float t       = clamp(v2.w / max(v1.w, 0.001), 0.0, 1.0);
    float envIn   = smoothstep(0.0, 0.15, t);
    float envOut  = smoothstep(1.0, 0.85, t);
    float alpha   = envIn * envOut * texColor.a;
```

The downstream `color0 = vec4(tint * alpha, alpha);` line is unchanged — output stays premultiplied.

> **If the sheet is OPAQUE** (`texColor.a == 1` everywhere — a dark/black background that is not transparent), the `* texColor.a` factor never drops it, so the particle renders as a glowing subject on a solid box. Drop that factor and emit additive instead — `float alpha = envIn * envOut;` then `color0 = vec4(tint * alpha, 0.0);` — so a dark texel (`tint → 0`) keys out and bright pixels glow (the §3 additive trick; see `references/dimension-basis.md` §3). Sheets that DO carry real alpha keep the default premultiplied output.

**Verify the result the same way regardless of harness:** take two screenshots ≥0.5s apart — the flame/sheet frame must obviously differ between them, proving the animation is playing (a single screenshot cannot distinguish "playing" from "frozen on frame 0").

**Asset panel (automatic):** because the JSON carries `SHEET_COLS`+`SHEET_ROWS`, the
generated asset gets a **Flipbook** inspector group with the three user-relevant
controls — `Sheet Columns` / `Sheet Rows` / `Playback FPS`. `TOTAL_FRAMES` is
re-derived (COLS×ROWS) on panel grid edits, and `SHEET_W`/`SHEET_H` auto-follow
when the user swaps the sheet texture via the Texture picker. Author all six
tokens as measured — the panel only takes over AFTER generation.

##### Recipe A — failure-mode debug table

After applying Recipe A, capture a screenshot and check it against this table. Each symptom maps back to a specific missed patch — the fastest way to localise "I followed the recipe but the result is wrong":

| If the screenshot shows… | The missed patch is | Why |
|---|---|---|
| Particles flying outward radially, like a fountain or explosion ("oscillating on screen") | **Patch #4** — velocity NOT zeroed in `init.comp` | Canonical's default is `speed * radial direction on unit sphere`. Without replacing it with `vx=vy=vz=0`, every particle drifts radially from origin. This is the single most common Recipe A failure. |
| Dozens of tiny fires scattered everywhere instead of one localised flame | **Patch #2** (spawn rate not adjusted, 240+ particles alive) OR **Patch #1** (SIZE_START/END too small) | Canonical spawns 240/sec; with the canonical's small size that's the right look for explosions but not fire. Default Recipe A needs ~1 large particle (handoff), not 240 small ones. |
| Scene shows multiple overlapping flames flickering chaotically, even though the user only asked for "a fire" | **Patch #2** + **Patch #3** wrong — got the Layered Flicker variant by accident | Default Recipe A is SEQUENTIAL (one particle, frame-0 start, handoff cadence). If you applied `Rand(seed) * TOTAL_FRAMES` to slot 9 + `originalSpawnRate ≈ 2.5`, you built the Layered variant. Revert slot 9 to `floatBitsToUint(0.0)` and adjust spawn to `delayMin/Max = LIFETIME − 0.4`, `originalSpawnRate = 1/delay`. |
| Scene is completely empty for ~2 seconds then a fire appears | **Sequential playback startup gap** — this is the known tradeoff of the default | Either accept the wind-up, pick a shorter sheet (`TOTAL_FRAMES / FPS ≤ 1.0`), or set `runtime.prewarmFrameCount`. See the startup-gap caveat after the JSON block. |
| One particle sitting still on the same frame, no animation | **Patch #5** — `update.comp` Flipbook Player missing | Without `texIndex += FPS*dt`, slot 9 stays at its initial value forever. Each particle freezes on whatever frame it spawned at. |
| Animation plays but with visible "stair-step" frame changes (24fps stutter) | The `mix(cur, nxt, v0.r)` half of **Patch #6** was dropped | Without temporal interpolation between adjacent cells, transitions happen discretely at 24fps and the eye perceives them as steps. The blend is what gives Recipe A its "burning" smoothness. |
| Fire appears to pop in/out abruptly at the start/end of each particle's life | The soft envelope half of **Patch #6** was dropped (`smoothstep(0, 0.15, t) * smoothstep(1, 0.85, t)`) | Canonical's `alpha = 1.0 - t*t` starts at full opacity → "pop" at birth. The envelope replaces this with a fade-in-fade-out. |
| Each particle is a SQUARE CROP of fire texture instead of a flame silhouette | The texture isn't actually a sprite sheet — agent got a single image | The imported texture is a single-frame image. Recipe A's cell math (`vTex.xy = cellOffset + ...`) only makes sense on a real grid sheet. Two recovery paths: (a) ask the user for an actual sprite sheet, OR (b) **switch to a non-flipbook path**: use the Texture swap recipe (single texture, particles fade with age) or the Universal authoring workflow (first-principles patches for whatever motion the user wanted). DO NOT refuse — pick a path. |
| Particle shows **garbled patchwork** of multiple flame fragments / mangled crops, or no recognisable frame at all | `SHEET_COLS` / `SHEET_ROWS` in JSON `defines` don't match the actual texture grid | Phase 0 was skipped. Re-OPEN the imported PNG and count visible columns × rows. AIGC almost never honours an "8×8 grid" prompt — a sheet asked for as 8×8 commonly returns 10×6, 6×8, etc. The filename means nothing. Update JSON defines and re-author the package. |
| Frame plays correctly but **edges show thin slivers of the adjacent cell** | `SHEET_W` / `SHEET_H` in JSON `defines` don't match the actual texture pixel dimensions | The half-texel inset is mis-sized. Run `inspect(<texture_guid>)` to get the actual `width` / `height` and update JSON defines. |
| Edits compile cleanly but the preview keeps showing the previous state | The post-edit re-bind step was missed | See `edit_vfx_source` warning in the DSL commands section above. After every `edit_vfx_source`, re-issue `set_component` with the same `vfxProfile` GUID. |
| Recipe-A-shaped flame, but oversaturated white blob in the centre | The soft-circle mask + white-tint fallback wasn't dropped (you're stacking Recipe A on top of the canonical's procedural circle) | The Recipe A frag patch REPLACES the whole alpha/tint section, including the `alpha = v0.a * shape` line. If you only added cell-UV math but kept the original alpha line, the canonical's white circle still bleeds through. |

If the screenshot looks correct (one localised fire that flickers, base wider than tip, no scatter), you're done — proceed to documenting or wrapping the asset.

##### Recipe A variant — LAYERED FLICKER (opt-in: rich shimmer / multi-overlap)

> ⚠️ **Opt-in only.** The default Recipe A above is sequential single-particle playback (GIF-style loop). This variant adds multiple overlapping particles with **random starting frames** to create a flicker-rich composite — useful for "shimmering" fire, intense magical effects, "many flames overlapping" looks. Pick this variant ONLY when the user explicitly asks for one of:
> - "stacked" / "layered" / "multi-layered" flicker
> - "rich shimmer" / "rich flicker" / "intense flicker"
> - "multiple flames overlapping"
> - "shimmering" or "fluctuating" intensity
>
> If the user didn't ask for it, DO NOT switch — sequential playback is the safer default.

**Three load-bearing differences from default Recipe A:**

1. **`shaders/init.comp`** — every particle starts at a RANDOM frame instead of frame 0. Replace:
   ```glsl
   attributeBuffer_buf[base +  9u] = floatBitsToUint(0.0);
   ```
   with:
   ```glsl
   // Layered flicker: per-particle random starting frame creates the
   // out-of-phase shimmer when multiple particles overlap.
   attributeBuffer_buf[base +  9u] = floatBitsToUint(Rand(seed) * float(TOTAL_FRAMES));
   ```

2. **JSON `defines`** — restore the longer / variable lifetime from the canonical (no need to lock to one cycle since particles aren't synchronised anyway):
   ```js
   baseSource.defines.LIFETIME_MIN = 2.0;
   baseSource.defines.LIFETIME_MAX = 3.0;   // some variance helps the layered look
   ```

3. **JSON spawn uniforms** — bump rate so ~5-8 particles co-exist at any moment. Each one is at a different cycle phase → composite flickers richly:
   ```js
   for (const u of baseSource.contexts.spawn.uniforms) {
     if (u.name === 'spawnRateMin' || u.name === 'spawnRateMax') u.value = 1.0;
     if (u.name === 'delayMin' || u.name === 'delayMax')         u.value = 0.4;   // continuous spawn
     if (u.name === 'originalSpawnRate')                          u.value = 2.5;  // ~2.5/sec
   }
   ```
   Keep size + texture binding + vert + frag the same as default Recipe A (envelope still helps — each individual particle's birth/death stays soft, the composite is rich because the phases differ, not because the births are loud).

**Why default Recipe A doesn't stack:** if the user asks for "a fire" and you add layering uninvited, three things go wrong: (1) the look is busier than they imagined, (2) GPU cost multiplies by ~5×, (3) the user perceives the result as "wrong" even though every patch is technically correct. Layering is a *flavour*, not a *correctness* property.

**Why this variant doesn't need a startup-gap warning:** with ~2.5/sec spawn and 0.4s delay, the first particle appears at t=0.4s and there are particles continuously visible from then on — no 2-second blank. (That's the user-facing tradeoff with the sequential default: instant-on costs random per-particle phase.)

#### Recipe B — Drifting fragments (sparks / embers / snow / rain / dust)

> **Pick this when** the user prompt is one of:
> - "sparks / embers / dust / fireflies" with sprite sheet variety
> - "snow / rain / falling X" — particles drift down
> - "rising X / particles spread out" — drift up / out
> - **Each individual frame is a tiny fragment, NOT a complete subject.**
> If you can recognise the subject from one frame (a whole flame, a whole rune), that's Recipe A, not this one.

When the sheet's individual frames are small fragments rather than complete effects, particles need motion (drift) and there are many of them (~50-500 alive). Recipe is shorter — most of Recipe A's machinery doesn't apply.

**JSON (`systems/<name>/system.json`):** bind the sprite sheet. Keep canonical's default spawn rate (240/sec). Tune size to fragment scale + motion via existing defines:
```js
baseSource.resources.Map0 = { type: 'Texture', guid: spriteSheetGuid };
baseSource.defines = {
  ...baseSource.defines,
  SIZE_START: 0.10,   // fragments are small
  SIZE_END:   0.25,
  // SPEED / GRAVITY / LIFETIME match the user's motion intent (rising sparks?
  // falling snow? swirling embers?) — see Common motion archetypes below.
};
```

**`shaders/init.comp`** — random fixed-frame cell per particle (no animation needed for fragments; variety is the point). Replace the slot-9 padding write:
```glsl
attributeBuffer_buf[base +  9u] = floatBitsToUint(sampCol.r); // slot 9  = sampled R
```
with:
```glsl
// Per-particle fixed cell index, drawn from [0, TOTAL_FRAMES).
// TOTAL_FRAMES is token-replaced from JSON defines — DO NOT write a literal.
attributeBuffer_buf[base +  9u] = uint(floor(Rand(seed) * float(TOTAL_FRAMES)));
```

Keep the canonical's radial velocity + position OR replace per motion archetype below.

**`shaders/output.gles.vert`** — read slot 9, expose via `vTex.z` (no second UV needed since no blending):

Replace:
```glsl
        vTex = vec4(tex_cord.x, 1.0 - tex_cord.y, 0.0, 0.0);
```
with:
```glsl
        float texIndex = float(attributeBuffer_buf[base + 9u]);
#ifdef VFX_COMPAT_MODE
        texIndex = 0.0;
#endif
        vTex = vec4(tex_cord.x, 1.0 - tex_cord.y, texIndex, 0.0);
```

**`shaders/output.gles.frag`** — single-cell UV math + drop the soft-circle mask:

Replace `vec2 uv = vTex.xy;` with (SHEET_COLS/SHEET_ROWS come from JSON defines — DO NOT write literals):
```glsl
    float cols       = float(SHEET_COLS);
    float rows       = float(SHEET_ROWS);
    float frame      = floor(vTex.z + 0.5);
    float col        = mod(frame, cols);
    float row        = (rows - 1.0) - floor(frame / cols);    // frame 0 = top-left
    vec2  cellSize   = vec2(1.0 / cols, 1.0 / rows);
    vec2  cellOffset = vec2(col, row) * cellSize;
    vec2  halfTexel  = 0.5 / vec2(textureSize(Map0, 0));
    vec2  uv         = cellOffset + halfTexel + vTex.xy * (cellSize - 2.0 * halfTexel);
```
Recipe B also needs `SHEET_COLS` and `SHEET_ROWS` in JSON `defines` (measured from the sheet, same as Recipe A's Phase 0). `init.comp`'s random cell-index write also references `TOTAL_FRAMES` — make sure to set all three in defines before submitting.

Replace `vec4 texColor = texture(Map0, uv);` with:
```glsl
    vec4 texColor = textureLod(Map0, uv, 0.0);
```

Replace the alpha line `float alpha = v0.a * shape;` with (drop the soft-circle):
```glsl
    vec3 tint  = v0.rgb * texColor.rgb;
    float alpha = v0.a * texColor.a;
```

#### Common motion archetypes (for Fragment recipe)

The canonical's default motion is radial-explosion + gravity-down — appropriate for explosions/fireworks, wrong for most other fragments. Patch `shaders/init.comp`'s velocity block to match the user's intent:

| Archetype | init.comp velocity patch | defines override |
|---|---|---|
| Sparks / embers rising | `vx = (Rand-0.5) * 0.6; vy = SPEED_MIN + Rand * (SPEED_MAX-SPEED_MIN); vz = (Rand-0.5) * 0.6;` | `GRAVITY: -2.0` (slight upward pull) |
| Snow falling | `vx = (Rand-0.5) * 0.3; vy = -SPEED_MIN - Rand * (SPEED_MAX-SPEED_MIN); vz = (Rand-0.5) * 0.3;` | `GRAVITY: 0.5` (gentle drift) |
| Rain falling | `vx = 0.0; vy = -SPEED_MIN - Rand * (SPEED_MAX-SPEED_MIN); vz = 0.0;` | `GRAVITY: 5.0` (heavy fall) |
| Dust / floating | `theta = Rand * 6.28; phi = acos(1-2*Rand); speed = SPEED_MIN + Rand * (...); vx/vy/vz = speed * trig;` (canonical default) | `GRAVITY: 0.0` (no fall) |
| Explosion (current canonical default) | (keep canonical's radial sphere) | (keep canonical defaults) |

#### Hard constraints (both recipes)

- **`COLS × ROWS` in vert/frag must match the actual sprite sheet layout.** A mismatch produces wrong cell sampling, possibly out of bounds → black.
- **Sheet layout tokens MUST come from JSON `defines`, not literal shader values.** The shader snippets above use `SHEET_COLS / SHEET_ROWS / SHEET_W / SHEET_H / TOTAL_FRAMES / FPS` as identifier tokens — the importer whole-word-substitutes them with the JSON `defines` values. **If you find yourself editing a literal number in the shader to "match the texture", you are doing it wrong** — adjust the JSON instead. The shader stays texture-agnostic; the JSON is where the per-effect parameters live.
- **Slot 9 collisions.** If you've already repurposed slot 9 for stage byte / colour palette / shape enum elsewhere, move texIndex to slot 10 or 11 and update vert + (Recipe B only) frag to match.
- **VFX_COMPAT_MODE only carries slots 0–8 to the GLES vert via texture sampling** — slot 9 reads fail there. Both recipes fall back to `texIndex = 0` under `#ifdef VFX_COMPAT_MODE`, degrading to "always show cell 0" instead of crashing on older GLES.
- **Only edit `output.gles.frag`** (not the Metal frag). AUSL cross-compiles GLES → both targets.

#### Source-texture quality is the limiting factor

Neither recipe can clean up artefacts baked into the source PNG:

- **Dithered / halftone alpha** in the sheet's frames (Floyd-Steinberg-style transparency dither) renders pixel-crisp at LOD 0 — that's the source asset's choice, not a sampler bug. Ask the user for a sheet with smooth alpha instead of trying to patch it away in the shader.
- **Pre-multiplied alpha mismatches** (sheet authored straight-alpha but canonical frag does premultiplied output) → colour fringing at edges. Either premultiply the sample with its alpha, or re-author the sheet.
- **Sheets with zero inter-cell gutter** are inherently fragile — half-texel inset only buys ½ pixel of safety margin. Sheets with 1–2 px transparent gutters between cells are much more robust.

When the output looks "noisy" or "halftone-y", inspect the source sheet first — the shader is doing what it should.
