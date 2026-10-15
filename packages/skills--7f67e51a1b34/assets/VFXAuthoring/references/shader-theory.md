<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->
<!-- NOTE: the shader techniques below are template-agnostic. Apply them to V4 via edit_vfx_source(scope="system:<name>:shader:<file>") for shader text and scope="system:<name>:defines" for tunables; start new effects with add_vfx_source. Never hand-build a bundle. -->

# Shader-level authoring — universal framework, cross-particle reads, AUSL

### Universal authoring workflow (the framework — read this first if you want to author anything beyond tunables)

This is the **primary mental model** for shader-level changes. The curated recipes below (Texture swap, Flipbook A/B, etc.) are **shortcuts that follow this same workflow** for high-frequency cases — they are NOT a separate system. Anything the engine can do with particles can be authored from this framework: sprite-sheet flipbooks, swarms / boids / attractors, custom force fields, multi-stage lifecycles, anything else.

**Order of operations for ANY shader-level prompt:**
1. Skim the curated recipes' "Pick this when" headers → if the prompt matches one, use that recipe as an accelerator (it's a pre-derived application of this framework).
2. If no recipe matches → apply this framework directly. **DO NOT refuse the prompt** — the framework covers every particle behaviour the engine supports.

#### Step 1: Map the user's behaviour to the 4 stages

The canonical has 4 GPU stages. Every particle effect is built by editing 1-4 of them:

| Stage | File | What you change here |
|---|---|---|
| **Spawn** | `systems/<name>/system.json → uniforms.spawn` (edit scope `system:<name>:uniforms`) | How often / how many new particles appear per second — see "Editing spawn / capacity on an existing effect" below |
| **Init** | `shaders/init.comp` | What each new particle looks like when born: position, velocity, age=0, per-particle palette / texIndex / stage byte / custom slots |
| **Update** | `shaders/update.comp` | Per-frame simulation: physics integration, age++, optional **cross-particle interaction** (boids / attractor / repulsor), force fields, drag, stage transitions |
| **Output** | `shaders/output.gles.vert` + `.frag` (+ metal pair) | How each live particle is rendered: billboard size curve, shape mask, texture sampling, colour, blend |

Read the user's prompt → identify which stages need to change → patch only those files. The other shader files stay at canonical content.

#### Step 2: Particle data model (slot layout)

Each particle is `PARTICLE_SIZE = 12u` uints in a global SSBO (`attributeBuffer`). The canonical layout:

| Slot | Field | Type | Used by |
|---|---|---|---|
| 0 | alive | uint (0/1) | All stages |
| 1-3 | position | vec3 as float bits | Init writes, update integrates, vert reads |
| 4-6 | velocity | vec3 as float bits | Init writes, update integrates |
| 7 | age | float bits | Update increments by `dt`, vert reads for size/alpha curve |
| 8 | lifetime | float bits | Init writes, update kills when `age > lifetime` |
| 9 | sampCol.r by default (= INIT-sample colour, §3.0c; zeros when `INIT_SAMPLE_TEX` is off) | float bits | REPURPOSABLE: flipbook texIndex (conventional), palette, stage byte — replace the `sampCol.r` write in init.comp. Mutually exclusive with the INIT_SAMPLE_TEX colour-bake on the same system. |
| 10-11 | sampCol.g / sampCol.b by default (inert zeros without INIT_SAMPLE_TEX) | float bits | REPURPOSABLE the same way: stage byte, palette index, custom per-particle data |

`PARTICLE_SIZE = 12u` is hardcoded in canonical shaders — DON'T change it. If you need more per-particle data, repurpose slots 9–11 (replace their `sampCol` writes in init.comp's WRITE BACK and read them wherever you need).

#### Step 3: Three compute-shader access patterns

Inside `init.comp` and `update.comp`, you have three ways to interact with the particle buffer:

**Pattern A — Read self** (every recipe uses this):
```glsl
uint base = particleOffset * PARTICLE_SIZE;
vec3 pos = vec3(
  uintBitsToFloat(attributeBuffer_buf[base + 1u]),
  uintBitsToFloat(attributeBuffer_buf[base + 2u]),
  uintBitsToFloat(attributeBuffer_buf[base + 3u])
);
```

**Pattern B — Write self** (every recipe uses this):
```glsl
attributeBuffer_buf[base + 1u] = floatBitsToUint(newPosX);
```

**Pattern C — Read OTHER particles** (★ key for boids / attractors / swarms / chains):
```glsl
// Loop over all particle slots and read each neighbour.
// CAPACITY is a vert-only macro — in update.comp declare the bound yourself:
// a local const matching uniforms.init.capacity, or a custom define (POOL_COUNT).
const uint POOL_COUNT = 200u;   // = uniforms.init.capacity
for (uint j = 0u; j < POOL_COUNT; j++) {
  if (j == particleOffset) continue;                           // skip self
  uint other_base = j * PARTICLE_SIZE;
  if (attributeBuffer_buf[other_base + 0u] == 0u) continue;    // skip dead
  vec3 other_pos = vec3(
    uintBitsToFloat(attributeBuffer_buf[other_base + 1u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 2u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 3u])
  );
  vec3 other_vel = vec3(
    uintBitsToFloat(attributeBuffer_buf[other_base + 4u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 5u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 6u])
  );
  // ... use other_pos / other_vel to influence this particle's velocity
}
```

The `attributeBuffer_buf` SSBO is **globally readable** — any compute thread can read any particle's slot. Cost: O(N²) per frame. Acceptable for `CAPACITY ≤ 500`. For larger N, use a spatial hash (advanced, not covered here).

#### Step 4: Pick the authoring path

| User prompt mentions… | Path |
|---|---|
| "fire / smoke / explosion / lightning / magic rune" + sprite sheet | **Recipe A** (Flipbook, whole-effect) |
| "sparks / embers / dust / snow / rain / firefly" + sprite sheet | **Recipe B** (Flipbook, fragment) |
| "just replace the texture / change the colour map" | **Texture swap recipe** (above) |
| **"boids / swarm / flock / school / herd / group motion"** | **First-principles** + cross-particle loop (Pattern C). See "Worked example: Cross-particle interaction" below. |
| **"attractor / magnet / orbit around X / repulsor / electric charge"** | **First-principles** + uniform-driven force in `update.comp` |
| **"follow my hand / face / a SceneObject"** | **First-principles** + bind a uniform from controller for target position; force in `update.comp` |
| **"twisted / curl / turbulence / noise field"** | **First-principles** + procedural noise (`sin / cos / fbm`) in `update.comp` velocity term |
| **"chain / link / connect particles"** | **First-principles** + slot 10-11 stores neighbour indices; render with line topology (advanced; no template support — first-principles only) |
| **"streak / blade / shaft / motion trail of one particle / rain-like lines"** | **Capability A** — non-uniform / velocity-aligned billboard (reshape the quad) |
| **"spinning / tumbling / pointing along its path / oriented sprite"** | **Capability A** — rotate the quad axes (full-quadrant `atan` for heading) |
| **"on the ground / floor seal / shadow / flat pattern lying in 3D"** | **Capability A** — custom (non-camera) billboard basis with a depth component |
| **"first X then Y / it builds up / a storm that grows / timed phases / synced flash"** | **Capability B** — `totaltime` staging + deterministic schedule (slot publish to reach the vert) |
| **"form a shape / gather into / assemble / build an X out of particles / converge"** | **Capability C** — drive particles toward `f(particleOffset)` targets, ordered reveal, freeze |
| Anything else not on this table | **First-principles**: identify which stage to edit, write the patch from scratch, test. Do NOT refuse. |

The right-column "first-principles" path is the **universal fallback**. As long as the user wants particles, you can build it — the canonical's 4 stages cover every imaginable behaviour.

#### Step 5: Submit, compile, verify

1. **Read** the canonical base (11 files listed in "Canonical base contents" table below).
2. **Modify** the files identified in Step 1.
3. **Apply each change** via `edit_vfx_source(scope="system:<name>:shader:<file>")` for shader text and `edit_vfx_source(scope="system:<name>:defines")` for tunables. For a brand-new effect, start from `add_vfx_source` (template-driven) — you never hand-submit a whole bundle.
4. **Check** that the command and `_compile_check` succeeded. VFX import or shader compile failures are returned as command errors — fix and resubmit.
5. **Re-bind** the VFX component (see `edit_vfx_source` warning section below).
6. **Screenshot** to verify visual matches user intent.

#### Editing spawn / capacity / exposed defaults on an EXISTING effect (V4 worked example)

All JSON edits go through `edit_vfx_source` scopes; **arrays replace wholesale**, so
always read-modify-write the whole array:

```jsonc
// 1. Spawn rate: read scope "system:main:uniforms", then patch the WHOLE spawn array.
{"command_type": "edit_vfx_source", "params": {
  "vfx_name": "<Effect>.vfxsrc", "scope": "system:main:uniforms",
  "patch": {"spawn": [
    {"name": "spawnRateMin", "type": "Float", "value": 12},
    {"name": "spawnRateMax", "type": "Float", "value": 12},
    {"name": "delayMin", "type": "Float", "value": 1.0},
    {"name": "delayMax", "type": "Float", "value": 1.0},
    {"name": "originalSpawnRate", "type": "Float", "value": 12}
  ]}}}
```

Field semantics (keep all five CONSISTENT — `originalSpawnRate = spawnRate / delay`):
- **`originalSpawnRate` is the live driver**: the bundle controller re-derives the
  engine's per-dispatch rate/delay from it every frame (when ≠ 0).
- `spawnRateMin/Max` + `delayMin/Max` are the engine-level values (used at import
  and whenever `originalSpawnRate` is 0) — `spawnRate` particles per batch, one
  batch every `delay` SECONDS.
- To SILENCE a system that must not self-spawn (event targets, shared-pool layers)
  use the epsilon pattern from `references/events-multisystem.md` — plain zeros
  trigger the importer's ~2/s default-spawner fallback.

`capacity` lives in `uniforms.init` (same wholesale-array rule). Changing an
**exposed parameter's default** on an existing system is NOT a defines patch
(that throws `INVALID_UNIFORMS`) — patch the whole `exposed_parameters` array at
scope `system:<name>` instead (see SKILL.md "Patch semantics").

### The capabilities the model actually gives you (read before reaching for a recipe)

The 4-stage framework above tells you WHERE to edit. This section is WHAT the
quad-billboard + compute model can do beyond "set a velocity and a force" — the
moves that make ambitious briefs reachable. **Every item here is a GENERAL
capability with a minimal GLSL shape; none is tied to a specific effect.** Map
the brief onto these, then fill in your own numbers.

#### A. The billboard is yours to reshape and reorient

The output vert expands each particle into a quad as
`offset = (axisX * vOffsets.x + axisY * vOffsets.y) * size`, where `axisX/axisY`
are camera-facing basis vectors and `vOffsets ∈ [-1,1]²` is the corner. All three
inputs are yours to change:

- **Non-uniform axis scale → elongated quads.** Scale the two axes differently —
  `(axisX * vOffsets.x * 0.12 + axisY * vOffsets.y * 1.0) * size` makes a thin
  tall sliver instead of a square. Anything line-like (streak, blade, shaft,
  single-particle ribbon) is a stretched quad.
- **Align the long axis to motion → speed streaks.** Swap the up-axis for the
  velocity direction so the quad points where the particle moves:
  ```glsl
  float spd = length(velocity);
  vec3 dir  = spd > 0.001 ? velocity / spd : axisY;
  vec3 side = normalize(cross(dir, axisZ));
  float stretch = clamp(spd * 0.1, 1.0, 2.6);   // optional: faster = longer
  vec3 offset = (side * vOffsets.x * 0.10 + dir * vOffsets.y * stretch) * size;
  ```
  Letting `stretch` grow with speed makes fast particles draw lines and slow ones
  stay compact — a natural shape mix from one system.
- **Rotate the quad in the view plane → spin / heading.** Rotate the expansion
  axes by an angle `a`:
  ```glsl
  vec3 ax = axisX * cos(a) - axisY * sin(a);
  vec3 ay = axisX * sin(a) + axisY * cos(a);
  vec3 offset = (ax * vOffsets.x + ay * vOffsets.y) * size;
  ```
  `a` can be a per-particle spin (store a rate in a free slot, `a = rate * age`)
  or the heading of motion. **For heading from velocity use the FULL-QUADRANT
  `atan(vx, vy)` — never clamp a component.** `atan(vx, max(vy, ε))` locks the
  orientation to two quadrants, so particles fly sideways when moving down or
  left. Guard the zero-speed case with a speed threshold (`spd > thresh ? atan(vx,vy) : 0.0`), not a clamp.
- **Drop the camera basis entirely → non-billboard placement.** Replace
  `axisX/axisY` with your own constant world basis to lay the quad on a plane
  instead of facing the camera. A ground-plane basis:
  ```glsl
  vec3 gU = vec3(1.0, 0.0, 0.0);
  vec3 gV = normalize(vec3(0.0, 0.36, -0.55)); // screen-rise + real DEPTH (-z)
  vec3 offset = (gU * vOffsets.x + gV * vOffsets.y) * size;
  ```
  Because `gV` carries a real depth component, the quad reads as lying on the
  floor and perspective shrinks its far edge — the way to render a flat pattern
  (seal, shadow, ripple, grid) that sits in 3D rather than mugging the camera.

> **Rotating UVs needs a crop (general gotcha).** If you rotate the texture UVs
> (to spin a sprite's *artwork* rather than the quad), the rotated sample window's
> CORNERS fall outside `[0,1]` and pick up clamp/wrap garbage — ghost edges that
> appear around 45°. The artwork is normally an inscribed circle, so mask beyond
> UV radius 0.5: `alpha *= 1.0 - smoothstep(0.48, 0.5, length(uv - 0.5));`.
> Applies to ANY rotated-UV sprite.

#### B. `update.comp` has a clock (`totaltime`) — author behaviour over time

`update.comp` can read `totaltime` (seconds since the effect started; the
controller pushes it each frame). This is how an effect EVOLVES instead of looping
at a steady state:

- **Phased behaviour in ONE shader.** Weight each force/behaviour term by
  `smoothstep(t0, t1, totaltime)` to sequence acts — calm, then strengthening,
  then a different character — by summing weighted terms. No multiple emitters, no
  event chain needed for a timeline that lives inside one system.
- **Deterministic schedules without event chains.** Hash a time-slot index for
  reproducible "random" timing:
  ```glsl
  float slot = floor(totaltime / PERIOD);
  float r    = fract(sin(slot * 12.9898) * 43758.5453);
  float tIn  = totaltime - slot * PERIOD;
  bool fire  = (r > THRESH) && (tIn < WINDOW);   // this slot fires, briefly
  ```
  Because it is a pure function of time, **two systems that compute the SAME hash
  stay in sync with zero communication** — a lightweight alternative to event
  chains when several systems must react on the same beat (one acts, another
  reacts, both deriving the same schedule).
- **The output vert has NO `totaltime` → publish/subscribe through a slot.** When
  the render needs a time-driven value, compute it in `update.comp` and write it
  to a free slot (9–11); read that slot in the vert/frag. The general bridge for
  getting any per-frame global into the output stage.

#### C. Particles as a controllable formation (drive toward TARGETS, not just forces)

Forces give organic motion; for ORDERED results, drive each particle toward a
target position you compute. This turns the pool from a spray into a programmable
point-set that can FORM shapes.

- **Target = a pure function of `particleOffset`.** Hash the index to a point on
  any shape — a ring, a sphere surface, a lattice, a voxelised mesh point list:
  ```glsl
  float h1 = fract(sin(float(particleOffset) * 12.9898) * 43758.5453);
  float h2 = fract(sin(float(particleOffset) * 78.233) * 43758.5453);
  // e.g. a point on a sphere surface:
  float phi = acos(1.0 - 2.0 * h1); float th = h2 * 6.2831853;
  vec3 target = center + radius * vec3(sin(phi)*cos(th), cos(phi), sin(phi)*sin(th));
  ```
  Zero per-particle storage; the same function every frame is a stable formation.
- **Two ways to arrive.** (1) *Servo* — steer velocity toward the target so the
  approach still obeys the surrounding motion: `v += (target - pos) * k * dt;`
  (clamp the step). (2) *Materialise in place* — park hidden at the target and
  fade in. Choose by whether the arrival travel should be seen.
- **Ordered reveal.** Gate each particle's activation on an attribute of its
  target (height, radius, index) vs. `totaltime` → progressive build-up / sweep /
  bottom-up assembly. Before its time, park it (hidden, or off to one side).
- **Arrive and freeze.** Within ε of the target, snap position and zero velocity
  so the formation is crisp and holds: `if (dist < 0.12) { pos = target; vel = vec3(0.0); }`.
- **Hold a fixed placed set (persistent formation).** A formation must persist, so
  spawn-once-and-hold rather than continuously recycle: size `capacity` to the
  point count and drive a steady `originalSpawnRate` that fills and holds it (same
  spawn machinery as a flow — see the spawn-budget rules — used for a constant
  population instead of a stream).

#### D. One system can carry several looks (channel-encode a free slot)

A single free slot can pack a small category AND an intensity: store
`category + intensity` (integer part = which look, fraction = a value), then decode
in the vert/frag:
```glsl
float s = uintBitsToFloat(attributeBuffer_buf[base + 11u]);
float band = floor(s);    // 0,1,2… selects material / colour / role
float lvl  = fract(s);    // carried intensity (brightness, visibility…)
```
Branch on `band` for colour/size, use `lvl` as brightness or alpha. Lets ONE
system render several distinct materials/parts instead of one system per look.
Generalises the slot-packing in the recipes below.

### Worked example: Cross-particle interaction (boids / swarm pattern)

**Use this** when the user wants particles that **react to each other** — flocks, schools, herds, swarms, or any "group motion" prompt. Three canonical boids rules + slight random wander:
- **Cohesion** — steer toward the average position of neighbours
- **Alignment** — steer toward the average velocity of neighbours
- **Separation** — steer away from neighbours that get too close
- **Wander** — small random force so the group doesn't lock into a frozen formation

This pattern was historically not in SKILL.md — agents who hit "boids" or "swarm" prompts had no path forward. The full first-principles synthesis lives here as a reusable example. Adapt the constants for your specific prompt.

**V4 authoring** — pass everything at `add_vfx_source` time (custom boids tunables
are ordinary compile-time defines; the motion names are exposed params routed to
runtime defaults — same `defines` spelling either way):

```jsonc
// inside add_vfx_source params → systems[0]
"defines": {
  // ── motion / size / lifetime (small fast units in a contained volume) ──
  "SIZE_START": 0.25, "SIZE_END": 0.35,
  "LIFETIME_MIN": 30.0, "LIFETIME_MAX": 30.0,  // long-lived — boids don't "die"
  "SPEED_MIN": 1.5, "SPEED_MAX": 2.5,          // initial scatter speed
  "GRAVITY": 0.0,                               // no fall — boids navigate
  "USE_TEX_ALPHA": 0.0,                         // soft-circle dots (default 1.0 = texture alpha -> squares on the white tex)
  // ── boids tuning (custom defines, token-substituted into update.comp) ──
  "NEIGHBOR_RADIUS": 3.0,     // how far a boid "senses" others
  "SEPARATION_RADIUS": 0.8,   // closer than this → push away
  "COHESION_WEIGHT": 0.6, "ALIGNMENT_WEIGHT": 0.8,
  "SEPARATION_WEIGHT": 1.5,   // separation > cohesion to avoid collapse
  "WANDER_WEIGHT": 0.4,
  "MIN_SPEED": 1.0, "MAX_SPEED": 4.0,  // clamp so no boid stops or runs away
  "POOL_COUNT": 200                    // = uniforms.init.capacity (loop bound; CAPACITY is vert-only)
},
"uniforms": {
  // capacity 200-300 for a visible group, NOT 2000 (O(N²) cost).
  "init": [{"name": "capacity", "type": "Int", "value": 200}],
  // Continuous gentle replenishment: ~6/s × 30s lifetime ≈ 180 alive steady-state.
  "spawn": [
    {"name": "spawnRateMin", "type": "Float", "value": 6},
    {"name": "spawnRateMax", "type": "Float", "value": 6},
    {"name": "delayMin", "type": "Float", "value": 1.0},
    {"name": "delayMax", "type": "Float", "value": 1.0},
    {"name": "originalSpawnRate", "type": "Float", "value": 6}
  ]
}
```

**`shaders/init.comp` patch** — spread spawn positions across a volume (instead of all at origin):

Replace:
```glsl
    // Spawn position: at local origin — particles burst outward from the centre.
    float px = 0.0;
    float py = 0.0;
    float pz = 0.0;
```
with:
```glsl
    // Scatter initial positions across a [-5, 5]³ volume so boids start dispersed.
    float px = (Rand(seed) - 0.5) * 10.0;
    float py = (Rand(seed) - 0.5) * 10.0;
    float pz = (Rand(seed) - 0.5) * 10.0;
```
(velocity block stays at canonical's spherical random — that gives each boid a small initial heading.)

**`shaders/update.comp` patch** — the boids algorithm lives entirely in the
`FORCE COMPUTATION` contract section (the template's load / aging / expire /
integrate / write-back all stay untouched). Replace the section's default line:

```glsl
            vy -= GRAVITY * dt;
```

with:

```glsl
            // ── BOIDS (Pattern C): accumulate neighbour stats ──
            vec3 sumPos = vec3(0.0);     // for cohesion
            vec3 sumVel = vec3(0.0);     // for alignment
            vec3 sumSep = vec3(0.0);     // for separation
            int  neighborCount = 0;

            for (uint j = 0u; j < uint(POOL_COUNT); j++) {   // cast! defines substitute as FLOAT literals
                if (j == particleOffset) continue;
                uint ob = j * PARTICLE_SIZE;
                if (attributeBuffer_buf[ob + 0u] == 0u) continue;  // dead
                vec3 op = vec3(
                  uintBitsToFloat(attributeBuffer_buf[ob + 1u]),
                  uintBitsToFloat(attributeBuffer_buf[ob + 2u]),
                  uintBitsToFloat(attributeBuffer_buf[ob + 3u])
                );
                vec3 dp = op - vec3(px, py, pz);
                float d2 = dot(dp, dp);
                if (d2 > NEIGHBOR_RADIUS * NEIGHBOR_RADIUS) continue;

                sumPos += op;
                sumVel += vec3(
                  uintBitsToFloat(attributeBuffer_buf[ob + 4u]),
                  uintBitsToFloat(attributeBuffer_buf[ob + 5u]),
                  uintBitsToFloat(attributeBuffer_buf[ob + 6u])
                );
                if (d2 < SEPARATION_RADIUS * SEPARATION_RADIUS) {
                    sumSep -= dp / max(d2, 0.0001);
                }
                neighborCount++;
            }

            // Apply the 3 boids steering forces + wander
            if (neighborCount > 0) {
                float invN = 1.0 / float(neighborCount);
                vec3 cohesion   = (sumPos * invN - vec3(px, py, pz)) * COHESION_WEIGHT;
                vec3 alignment  = (sumVel * invN - vec3(vx, vy, vz)) * ALIGNMENT_WEIGHT;
                vec3 separation = sumSep * SEPARATION_WEIGHT;
                vx += (cohesion.x + alignment.x + separation.x) * dt;
                vy += (cohesion.y + alignment.y + separation.y) * dt;
                vz += (cohesion.z + alignment.z + separation.z) * dt;
            }
            // Wander: small random nudge each frame
            uint wseed = particleOffset ^ floatBitsToUint(age);
            wseed = (wseed ^ 61u) ^ (wseed >> 16u); wseed *= 9u; wseed = wseed ^ (wseed >> 4u);
            vx += (uintBitsToFloat((wseed >> 9u) | 0x3f800000u) - 1.5) * WANDER_WEIGHT * dt;
            wseed *= 0x27d4eb2du;
            vy += (uintBitsToFloat((wseed >> 9u) | 0x3f800000u) - 1.5) * WANDER_WEIGHT * dt;
            wseed = wseed ^ (wseed >> 15u);
            vz += (uintBitsToFloat((wseed >> 9u) | 0x3f800000u) - 1.5) * WANDER_WEIGHT * dt;

            // Clamp speed to [MIN_SPEED, MAX_SPEED] so no boid stops or escapes
            float spd = length(vec3(vx, vy, vz));
            if (spd > 0.001) {
                float clamped = clamp(spd, MIN_SPEED, MAX_SPEED);
                float scale   = clamped / spd;
                vx *= scale; vy *= scale; vz *= scale;
            }
```

Integration and write-back stay at template defaults — the section contract takes
care of them.

`CAPACITY` does NOT exist in update.comp (it's a vert-only reserved macro, and the expander rejects it in `defines`). The boids defines above therefore include a custom `POOL_COUNT` matching `uniforms.init.capacity` — the loop below uses `POOL_COUNT`. Keep the capacity at 200–300 for boids.

**`output.gles.vert` / `.frag`** — no patch needed. With `USE_TEX_ALPHA: 0` in the defines, each boid renders as a soft white circle out of the box. Want fish or bird sprites instead? Add a sprite-sheet texture and combine with Recipe B's UV math (single-cell sample), no further boids-specific change.

**How to adapt this pattern to other cross-particle effects:**

| Effect | Change |
|---|---|
| Attractor at a fixed point | Replace boids loop with `force = (TARGET - pos) * ATTRACTOR_STRENGTH`; no neighbour loop. Add `TARGET_X/Y/Z` to defines. |
| Attractor at a moving SceneObject (hand / face) | Same as above but `TARGET_X/Y/Z` come from a controller-bound uniform (advanced — extend `output.uniforms`) |
| Repulsor / electric charge | Boids loop, but only Separation force (keep cohesion/alignment weights at 0) |
| Mutual attraction (planet-style) | Boids loop, but force = `dp / d²` (gravity-like), no radius cutoff |
| Predator-prey | Either two systems in one bundle, or one pool with slot 10 = "type" tag and a conditional force on tag mismatch |

**Performance note**: O(N²) means CAPACITY=200 → 40000 distance tests per frame → fine on mobile GPU. CAPACITY=500 → 250000 tests → starts costing. Above 500, switch to spatial hash (build a uint grid in a separate compute pass before the main update). Outside scope of this skill.


### Canonical base contents

The canonical 12-uint Quad shaders live in the `StandardQuad` template. Init a StandardQuad effect (or read `skills_root/assets/VFXAuthoring/templates/StandardQuad.md`), then `Read` each shader's `read_path` (from the `add_vfx_source` return's `files[]`, or `inspect(vfx_guid).vfx_workspace.files`) to pull the files. The files and their roles (paths are relative to the system, e.g. `systems/<name>/shaders/init.comp`):

| File | Role | Typical change knob |
|------|------|---------------------|
| `index.vfxsrc` | Bundle manifest (version=4, points at controller + per-system folders) | Almost never change. Update `effect` name to match your `vfx_name`. |
| `systems/<name>/system.json` | Compile config: `defines` (compile-time constants substituted into every shader), spawn / init / update / output uniforms, resource bindings | **`defines` is the first place to look** — size, lifetime, speed, gravity all live there. Also spawn rate, capacity, texture guid. (Blend state is NOT configurable in system.json — the importer fixes premultiplied-alpha blending for the output.) |
| `controller/VFXController.js` | Per-frame spawn-rate manager (frame-rate-aware actualRate / delay) | Rarely change. Edits go in shaders, not here. |
| `shaders/init.comp` | AUSL compute that spawns each particle (position, velocity, lifetime, age=0) | **Most edits live here**: spawn shape, velocity distribution, per-particle palette, per-particle shape enum, stage byte |
| `shaders/update.comp` | AUSL compute that ages + integrates each particle per frame | Gravity, drag, stage transitions (e.g. launch → explode at apex), per-particle colour evolution |
| `shaders/update_ssbo2image.comp` | AUSL compute that copies SSBO → 2D texture for GLES `VFX_COMPAT_MODE` | Never change unless adding/removing attributes; mirror init.comp's layout |
| `shaders/output.gles.vert` | AUSL vertex (GLES) — expand particle into billboard quad, set varyings `v0/v1/v2` from attribute buffer | Quad size curve, colour ramp from attribute, per-particle attribute unpacking |
| `shaders/output.gles.frag` | AUSL fragment (GLES) — sample texture, soft-shape mask, premultiplied output | Shape mask (round / cross / star), blend behaviour, texture sampling |
| `shaders/output.metal.vert` | Hand-written Metal MSL parallel to `output.gles.vert` | Same edits as GLES version, kept in sync manually |
| `shaders/output.metal.frag` | Hand-written Metal MSL parallel to `output.gles.frag` | Same edits as GLES version, kept in sync manually |
| `NOTES.txt` | Engine-verified default values + hard-constraint reminders | **Read first** before changing any numbers |

> **Hard constraints from `NOTES.txt`** — don't violate or compile fails / renders nothing:
> - `PARTICLE_SIZE = 12` must match across all 7 shaders. To add an attribute, bump PARTICLE_SIZE in all 7 + update `update_ssbo2image.comp` texture layout.
> - `CAPACITY` is a RESERVED name: the rebake rewrites the `#define CAPACITY <N>u` line in the OUTPUT VERT shaders from `uniforms.init.capacity`, and the expander REJECTS `CAPACITY` in your `defines`. It exists ONLY in the vert — in `update.comp`/`init.comp` there is no such macro. For a cross-particle loop bound in update.comp, add a CUSTOM define (e.g. `"POOL_COUNT": 200`) matching `uniforms.init.capacity` and reference `POOL_COUNT` in the loop.
> - Texture uniform name in `systems/<name>/system.json → output.uniforms[].name` must equal the `uniform sampler2D <NAME>` declared in the output frag shader. Default is `Map0`.
> - `output.gles.vert/.frag` must be valid AUSL with shared `#pragma input/varying/output` blocks and split `#pragma vs/#pragma fs` blocks (importer composes them into single AUSL source — see `composeOutputAuslSource` in VFXGraphImporter.ts).
> - `defines` names are case-sensitive whole-identifier tokens (regex `\bNAME\b`). The importer rewrites them to literal numbers BEFORE AUSL sees the source, so they aren't real `#define` directives — they look like macros in the shader but compile as if you'd written the literal value. Don't pass `#define NAME ...` directives yourself; just put the value in `defines` and reference `NAME` in the shader.
> - **⚠️ Defines ALWAYS substitute as FLOAT literals** (`200` becomes `200.0`). In any INTEGER context — loop bounds, array indices, uint comparisons — wrap them: `uint(POOL_COUNT)`, `int(TOTAL_FRAMES)`. Forgetting the cast produces `CrossShader compiled error: no operation '<' between uint and const float` (and the cross-shader failure may surface only in the EDITOR error toast / engine log — see the verification note below).
> - Don't author `.vg` topology and don't edit generated `Library/Artifact/...` or sticker bundles directly.


## Shader authoring

### AUSL format overview

| File | Format | Entry point |
|------|--------|-------------|
| `shaders/init.comp` | AUSL compute | `void compute()` |
| `shaders/update.comp` | AUSL compute | `void compute()` |
| `shaders/update_ssbo2image.comp` | AUSL compute | `void compute()` |
| `shaders/output.gles.vert` | AUSL vertex (GLES) | `void vertex()` |
| `shaders/output.gles.frag` | AUSL fragment (GLES) | `void fragment()` |
| `shaders/output.metal.vert` | AUSL vertex (Metal) | `vertex void vertex0()` |
| `shaders/output.metal.frag` | AUSL fragment (Metal) | `fragment void fragment0()` |

All compute shaders start with the `#pragma cs` block and end with `void compute()`.
GLES vert/frag shaders use `#pragma vs` / `#pragma fs` sections to declare stage-specific uniforms and buffers.

Minimal valid compute shader (compiles, no-op):
```glsl
void compute() {}
```

Minimal valid vertex snippet (compiles, no geometry output):
```glsl
void vertex() {}
```

Minimal valid Metal vertex snippet:
```glsl
vertex void vertex0() {}
```

### Canonical buffer layout (PARTICLE_SIZE = 12)

The full canonical example uses this fixed per-particle layout (12 `uint` slots per particle):

| Slot | Content | Type in buffer |
|------|---------|----------------|
| 0 | `alive` | `uint` (0 = dead, 1 = alive) |
| 1 | `position.x` | `float` stored as `floatBitsToUint` |
| 2 | `position.y` | `float` stored as `floatBitsToUint` |
| 3 | `position.z` | `float` stored as `floatBitsToUint` |
| 4 | `velocity.x` | `float` stored as `floatBitsToUint` |
| 5 | `velocity.y` | `float` stored as `floatBitsToUint` |
| 6 | `velocity.z` | `float` stored as `floatBitsToUint` |
| 7 | `age` | `float` stored as `floatBitsToUint` |
| 8 | `lifetime` | `float` stored as `floatBitsToUint` |
| 9–11 | `sampCol.rgb` (INIT-sample colour, §3.0c; zeros when off) — repurposable | `float` stored as `floatBitsToUint` |

`PARTICLE_SIZE = 12` must be consistent across **all 7 shader files**.
If you add or remove attributes, update every shader that reads the buffer and the capacity define in `output.gles.vert`.

### Dead-list mechanics

The dead list is a stack managed atomically across init and update:

| Buffer | Binding | Content |
|--------|---------|---------|
| `attributeBuffer` | std430, 0 | Per-particle attribute data (PARTICLE_SIZE uints each) |
| `deadList_andCounter_Buf` | std430, 1 | `[0]` = current dead count; `[1+]` = dead particle indices |
| `deadListCountCopy_Buf` | std430, 2 | Copy of `deadList_andCounter_Buf[0]` read by next init frame |

- **init.comp** pops slots: `atomicAdd(deadList[0], -1u)` → use returned index
- **update.comp** pushes expired slots back: `atomicAdd(deadList[0], 1u) + 1u` → write index

### Compat-mode texture layout (VFX_COMPAT_MODE)

GLES 2/3 devices without SSBO support in the vertex shader require `update_ssbo2image.comp` to copy the particle buffer to a 2D texture.

Texture: `layout(rgba16f, binding=0) uniform highp writeonly image2D attributeBuffer_vs`
Width: `BUFFER_WIDTH = 2048`

For `PARTICLE_SIZE = 12` (12 slots ÷ 4 channels = **3 rgba16f texels per particle**):

| Texel offset | Channels | Content |
|-------------|----------|---------|
| `p*3 + 0` | `.rgba` | `float(alive), px, py, pz` |
| `p*3 + 1` | `.rgba` | `vx, vy, vz, age` |
| `p*3 + 2` | `.rgba` | `lt, 0, 0, 0` |

`alive` is encoded as `1.0 / 0.0` (not `uintBitsToFloat`) so it survives fp16 precision loss.

The vertex shader reads back: `alive = (t0.r > 0.5) ? 1u : 0u`.

### Full canonical example

Init a `StandardQuad` effect, then `Read` each shader's `read_path` (from the `add_vfx_source` return's `files[]`, or `inspect(vfx_guid).vfx_workspace.files`) to pull the complete, commented implementation of all seven shaders. Use those as your starting point and customise the simulation logic inside `void compute()` / `void vertex()` / `void fragment()`, applying each change via `edit_vfx_source({vfx_name, path: <read_path>, content: ...})`.

Key customisation points per shader:

**init.comp** — particle spawn shape, initial velocity, lifetime range:
```glsl
// Change spawn radius
float spawnRadius = Rand(seed) * 0.15;
// Change upward burst speed
float vy = 2.5 + Rand(seed) * 2.5;
// Change lifetime
float lifetime = 1.2 + Rand(seed) * 1.8;
```

**update.comp** — per-frame forces, collision response:
```glsl
// Change gravity strength
vy -= 3.5 * dt;
// Add drag: vx *= (1.0 - 0.5*dt); vy *= ...; vz *= ...;
```

**output.gles.vert** — billboard size and colour ramp:
```glsl
// Change size curve
float size = 0.05 + (1.0 - t) * 0.10;
// Add colour ramp — interpolate from v0 start to v0 end colours
```

**output.gles.frag** — particle texture, shape, blend:
```glsl
// Replace soft-circle falloff with sprite alpha
float alpha = v0.a * texColor.a;
// Change shape: use smoothstep(...) with different radii
```

### Multi-stage / per-particle recipes (single-system alternatives to event chains)

A single StandardQuad system can host most "compound" particle effects — encode stage transitions and per-particle variation **inside `init.comp` / `update.comp` / the attribute buffer**. Use this when one pool is enough; use multi-system `events` (see `references/events-multisystem.md`) when stages need different render looks/sizes per stage or independent capacities.

Slots 9–11 of the per-particle buffer are the carrier for per-particle data the engine doesn't know about (they hold inert `sampCol` writes by default — replace them). Repurpose as: **`colour` (slot 9, packed RGB)**, **`stage` (slot 10, 0=launch / 1=explosion)**, **`shape` (slot 11, enum)** — pick whatever fits the effect.

#### Recipe: per-particle colour

`init.comp` — pick a random palette index per particle, pack into one float, and
write it to slot 9 (REPLACING the default `floatBitsToUint(sampCol.r)` write there):
```glsl
// pick 1 of 6 firework palette entries
uint paletteIdx = uint(Rand(seed) * 6.0);
vec3 paletteCol = (paletteIdx == 0u) ? vec3(1.0, 0.2, 0.2)   // red
                : (paletteIdx == 1u) ? vec3(1.0, 0.6, 0.0)   // orange
                : (paletteIdx == 2u) ? vec3(1.0, 1.0, 0.2)   // yellow
                : (paletteIdx == 3u) ? vec3(0.2, 1.0, 0.4)   // green
                : (paletteIdx == 4u) ? vec3(0.3, 0.6, 1.0)   // blue
                                     : vec3(1.0, 0.4, 1.0);  // pink
uint packed = (uint(paletteCol.r * 255.0) << 16) |
              (uint(paletteCol.g * 255.0) << 8)  |
               uint(paletteCol.b * 255.0);
attributeBuffer_buf[base + 9u] = packed;
```

`output.gles.vert` — unpack, drive `v0.rgb`:
```glsl
uint packed = attributeBuffer_buf[base + 9u];
vec3 tint = vec3(float((packed >> 16) & 0xFFu) / 255.0,
                 float((packed >>  8) & 0xFFu) / 255.0,
                 float( packed        & 0xFFu) / 255.0);
v0 = vec4(tint, alpha);
```

#### Recipe: multi-stage lifecycle (e.g. launch → explode)

Store a `stage` byte in slot 10 (or use `age vs. threshold`). The same simulation loop in `update.comp` switches behaviour per stage:

`init.comp` — spawn ALL particles in *launch* stage at the bottom of frame, with strong upward velocity and weak lateral:
```glsl
// launch position: random x at bottom of frame, slightly random z
float px = (Rand(seed) - 0.5) * 8.0;
float py = -10.0;
float pz = (Rand(seed) - 0.5) * 2.0;

// launch velocity: strong up, small spread
float vx = (Rand(seed) - 0.5) * 0.3;
float vy = 8.0 + Rand(seed) * 4.0;       // strong upward burst
float vz = (Rand(seed) - 0.5) * 0.3;

float lifetime = 3.5 + Rand(seed) * 1.5;  // long: launch + explosion + fade
attributeBuffer_buf[base + 10u] = 0u;     // stage = launch
attributeBuffer_buf[base + 11u] = packed; // stash future explosion colour now
```

`update.comp` — when a launch particle reaches its apex or runs out of upward speed, *re-randomise* its velocity into an outward explosion burst and flip its stage:
```glsl
uint stage = attributeBuffer_buf[base + 10u];
vy -= 9.8 * dt;            // gravity for launch phase

if (stage == 0u && vy < 0.0) {           // apex reached → explode
    uint seed2 = wang_hash(uint(age * 1000.0) ^ particleOffset);
    // isotropic burst on the unit sphere × explosion speed
    float theta = Rand(seed2) * 6.2831853;
    float phi   = acos(1.0 - 2.0 * Rand(seed2));
    float burst = 4.0 + Rand(seed2) * 3.0;
    vx = burst * sin(phi) * cos(theta);
    vy = burst * cos(phi);
    vz = burst * sin(phi) * sin(theta);
    attributeBuffer_buf[base + 10u] = 1u;   // stage = explosion
}
```

`output.gles.vert` — colour the trail dim, the explosion bright:
```glsl
uint stage = attributeBuffer_buf[base + 10u];
float brightness = (stage == 0u) ? 0.4 : 1.0;
v0.rgb *= brightness;
```

#### Recipe: per-particle shape (round / cross / star)

Stash a shape enum in slot 11 at spawn; branch in `output.gles.frag`:
```glsl
uint shape = uint(v1.w);  // pack shape into an existing varying float — or add a varying

float mask;
if (shape == 0u) {
    // round: smoothstep falloff on radial distance (default)
    mask = 1.0 - smoothstep(0.4, 0.5, distSq);
} else if (shape == 1u) {
    // cross: horizontal + vertical bars
    vec2 c = abs(centeredUV);
    mask = step(min(c.x, c.y), 0.1) * (1.0 - smoothstep(0.45, 0.5, max(c.x, c.y)));
} else {
    // star: 5 radial petals
    float a = atan(centeredUV.y, centeredUV.x);
    float r = length(centeredUV) * 2.0;
    float petals = 0.5 + 0.5 * cos(a * 5.0);
    mask = (1.0 - smoothstep(petals * 0.5, petals * 0.5 + 0.05, r));
}
color0 = vec4(v0.rgb * v0.a * mask, v0.a * mask);
```

#### Combine all three for fireworks

The example prompt *"launch upward with trailing flames, explode in the sky into different colors and shapes"* maps to:
- **launch trail** → stage=0 branch + dim brightness in vert
- **explosion** → stage=0→1 transition at apex
- **different colours** → slot 9 packed palette
- **different shapes** → slot 11 shape enum branched in frag
- gravity in update applies the same way to launch and debris

Single `.vfxsrc`, ~50 extra lines across `init.comp` / `update.comp` / output shaders. No chaining of emitters needed.

### BuiltinParameters fields

| Context | Fields |
|---------|--------|
| init | `delta, dispatchWidth, nbSpawned, spawnId, systemSeed` |
| update | `delta, dispatchWidth, nbSpawned, spawnId, systemSeed, stripCapacity, particleNumPerStrip, nbMax` |
| ssbo2image | all update fields + `prewarming` |

`nbSpawned` in the **init** context = particles to spawn this frame.
`nbSpawned` in the **update / ssbo2image** contexts = total simulation capacity (use as the dispatch upper bound).
