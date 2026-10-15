<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# §3.0–§3.1 — StandardQuad template guide

> **📖 READ ORDER — core first.** To author a normal StandardQuad effect, go straight to
> **§3.1** below and read it in order: *When to pick* → *File layout* → *SSBO slot layout* →
> *Defines* → *Editable section contracts*. That is the complete authoring surface for
> fire / sparks / smoke / snow / glow / bursts — you rarely need anything above it.
> **§3.0–§3.0e are OPTIONAL ADD-ON FEATURES; read ONE only if the brief calls for it**, then
> return to §3.1:
> - §3.0 — spawn particles ON a mesh's surface (logo/model-shaped cloud)
> - §3.0b — per-particle texture sampling + flat tint + colour-over-life ramp
> - §3.0c — sample a texture AT INIT to bake colour / gate which particles live
> - §3.0d — analytic kill volumes + bounce (cheap boundaries, no physics)
> - §3.0e — box-volume spawn + built-in turbulence/sway
>
> Skip the add-ons otherwise — none are needed for a basic effect.

## §3.0 — Mesh-surface emission (`runtime.emit_source`) — Standard templates

To spawn particles ON a mesh's SURFACE (a particle cloud in the shape of a model —
logo, character, object outline), **just declare `runtime.emit_source`** pointing at a
mesh resource. The server samples that mesh's surface at compile time and injects the
sampled points into `init.comp`'s POSITION INIT, so each particle spawns on one of them.
Works for StandardQuad and StandardMesh. Absent → origin spawn (unchanged).

> **You do NOT sample the mesh yourself.** Do not read FBX files, do not look for any
> mesh-sampling helper, do not run shell commands. Declare `emit_source` and the
> server bakes the points during add_vfx_source / edit_vfx_source.

```json
{ "name": "surf", "template": "StandardQuad",
  "defines": {"SIZE_START": 0.1, "SIZE_END": 0.1, "SPEED_MIN": 0.0, "SPEED_MAX": 0.0,
              "LIFETIME_MIN": 10.0, "LIFETIME_MAX": 10.0, "GRAVITY": 0.0},
  "resources": {"Map0": {"ref": "tex"}, "emesh": {"ref": "srcmesh"}},
  "uniforms": {"init": [{"name": "capacity", "type": "Int", "value": 800}], "spawn": [...]},
  "runtime": {"emit_jitter": 0.0,
              "emit_source": {"resource": "emesh", "count": 800, "mode": "surface", "scale": 2.0}} }
```
- `srcmesh` in `shared_resources` = the GUID of a **Mesh** to sample (a mesh sub-asset —
  get it via `list_resources` / `inspect`, same kind of GUID you'd use as a StandardMesh
  render `mesh`). `emit_source.resource` is the resource KEY (`emesh`).
- `count` = how many surface points (≲ a few hundred is plenty; GLSL const-array
  ceiling). `mode` = `"surface"` (default). `scale` (optional, default 1) = a uniform
  multiplier on the mesh's native coordinates (points are sampled in the mesh's own
  local space, so the emission shape matches the mesh's native size).
- The server samples the mesh's **live geometry** and writes the baked `emit_points`
  into the bundle for you — you never pass `emit_points` directly, and it works for
  builtin AND imported meshes. (If `emit_points` are already present, the server leaves
  them.)
- Declaring `emit_source` also gives the asset panel an **Emission Mesh** picker — the
  user can swap the emission shape and the editor re-samples automatically. See
  `references/asset-inspector.md` §5b.
- Speed 0 + long lifetime → the cloud HOLDS the silhouette; give speed/forces to make
  it dissolve/flow off the surface. `emit_jitter` adds a small random offset per particle.
- Static point set (good for static meshes). Live/skinned surface emission (animated
  mesh) is not yet supported.

## §3.0b — Per-particle texture sampling + flat tint (StandardQuad)

- **Flat colour**: set defines `TINT_R/G/B` (default 1,1,1 = white) for a per-system
  particle colour (e.g. a yellow glow `TINT_R:1.0, TINT_G:0.78, TINT_B:0.12`). Override
  `v0.rgb` in output.gles.vert for per-particle / age-based colour instead.
- **Sample a source texture per particle** (`SAMPLE_TEXTURE: 1.0`): each particle takes
  the colour of `Map0` sampled at its OWN UV (derived from spawn position:
  `uv = pos.xy * SAMPLE_UV_SCALE + 0.5`, set `SAMPLE_UV_SCALE = 0.5 / grid_half_extent`).
  Pair with a GRID of `emit_points` to reconstruct an image as a field of coloured
  particles (pixel effect). Bind the source image as `Map0` (import via `edit_by_dsl.import_resource(...)`).
  The same mechanism can sample camera-capture or segmentation-style render textures that
  already exist in the current project resource set (discover them via `list_resources` /
  `inspect`) for a live pixelated-face look — that additionally needs the corresponding
  camera→RT wiring already present in the project.
- These are value-literal defines (no shader-marker injection); default off/white →
  backward compatible.
- **Colour over lifetime** (`runtime.color_ramp`): a gradient = a list of `[t,r,g,b]`
  stops (t in [0,1], linear RGB). The bundle rebake bakes a piecewise-linear lerp into
  the output vert's COLOR OVER LIFETIME block, evaluated at `t = age/lifetime`, so each
  particle's colour follows the gradient as it ages (birth colour → … → death colour).
  Marker-block injection (not defines); absent → flat tint. Pairs with any motion.

## §3.0c — Sample a texture AT INIT: bake colour + gate Set-Alive (StandardQuad)

A complement to §3.0b's per-pixel frag sampling: `init.comp` can sample a bound
`MaskTex` once at spawn and use the value to (a) bake a per-particle colour and/or
(b) decide whether the particle lives. This is the general "read a texture, drive
particle birth from it" mechanism — the texture can be an authored image, or a render
texture fed by the scene (camera capture, a segmentation mask, etc.).

- **Sample space** — the sample UV is the particle's spawn position in one of two spaces:
  `1` = the emitter's LOCAL space (`pos.xy * SAMPLE_UV_SCALE + 0.5`; no matrices), `2` =
  the projected SCREEN position (uses the engine view/projection the controller pushes to
  the Init context, so it reads whatever is on screen behind the particle).
- **Colour bake** (`INIT_SAMPLE_TEX: 1|2`): the sampled `MaskTex.rgb` becomes the
  particle's colour (carried in a custom slot, read by output.vert).
- **Set-Alive gate** (`SET_ALIVE_MASK: 1|2`): the particle survives only when
  `MaskTex.r ∈ [MASK_BAND_LO, MASK_BAND_HI]` (`MASK_INVERT` flips the test). A *band*
  (not just a threshold) is what lets one mask express three intents from the same data:
  keep the interior, keep the outside, or keep only the soft edge between them — by
  choosing the range. Killed particles are recycled (born off-screen, ~0 lifetime).
- The mask is read from a single channel (`.r`) — prepare the bound texture so its red
  channel is the 0→1 mask; don't add per-format channel switches. Gating by a *live*
  segmentation requires a populated mask render texture bound as `MaskTex` (a rendered
  segmentation pass produces it; a bare segmentation-texture resource may read empty).
- Value-literal defines, all default 0 → backward compatible.
- **Panel**: `MaskTex` (any `uniforms.init[]` Texture entry) appears as a swappable
  picker in the inspector's **Sampling** group — the user can replace the sampled
  texture later without you. Keep the binding routed through
  `resources`/`shared_resources` (asset-inspector.md §5a).

## §3.0d — Non-physics kill volumes + bounce (StandardQuad)

Cheap analytic boundaries for the simple Euler particles — the lightweight counterpart
to PhysicsMesh colliders (§3.5). No PBD, no inter-particle stacking; just a per-particle
test each frame against analytic shapes in the emitter's LOCAL space. Pick these when you
need a boundary or a single bounce, not a full rigid-body sim.

- **`runtime.kill_volume`**: a list of shapes (`plane` half-space / `sphere` / `box`).
  After integration, a particle inside (`mode:'inside'`, default) or outside
  (`mode:'outside'`) ANY shape is killed (slot recycled). Use for: rain dying on the
  ground, particles confined to a region (`mode:'outside'`), dissolve-on-enter.
  ```json
  "runtime": { "kill_volume": [{"shape":"sphere","center":[0,1,0],"radius":3.5}] }
  ```
- **`runtime.bounce`**: a list of `plane`/`sphere` surfaces. A particle that penetrates is
  pushed back to the surface and its velocity reflected. `restitution` (0 stick … 1 elastic,
  default 0.5), `friction` (tangential damping [0..1], default 0). Use for: sparks
  ricocheting off a floor, confetti settling, snow bouncing in a bowl.
  ```json
  "runtime": { "bounce": [{"shape":"plane","point":[0,-6,0],"normal":[0,1,0],"restitution":0.6}] }
  ```
- Both are marker-block injection (not defines); LOCAL-space coords (like emit/box spawn);
  absent → no-op. For real falling-bouncing-resting piles with stacking → PhysicsMesh (§3.5).

## §3.0e — Box spawn + built-in turbulence (StandardQuad)

Two value-literal defines for common spawn-shape / motion needs (both default 0 = off):

- **Box spawn** (`BOX_SIZE_X/Y/Z`): each particle's spawn position gets a uniform random
  offset within a box of these LOCAL half-extents×2, added on top of POSITION INIT (so it
  composes with emit_points / event-inherited positions). 0 on an axis = no spread on it.
  Use for a volumetric emitter (a slab/column/cube of particles) instead of a point source.
- **Built-in turbulence / sway** (`TURB_AMP`, `TURB_FREQ`): a cheap time-animated
  (`totaltime`) sin/cos wander added to velocity each frame in update.comp — `TURB_AMP` =
  strength, `TURB_FREQ` = churn speed. Gives smoke/embers an organic drift (sway) with no
  shader edit. For arbitrary noise fields / curl beyond this knob, fall back to
  first-principles (procedural noise in the update FORCE block).

## §3.1 — StandardQuad template guide

### When to pick StandardQuad

- Effects whose particles are **camera-facing 2D quads** (textured or pure soft-circle).
- Use cases: fire, smoke, sparks, snow, rain, magic glyphs, dust, glow particles, simple impact / explosion bursts.
- DO NOT use for: 3D mesh particles (use `StandardMesh` — see §3.2), bouncing/colliding physics (use `PhysicsMesh` — see §3.5). (Trails / ribbons / streaks ARE done with StandardQuad — velocity-aligned or elongated billboards; see `references/shader-theory.md`.)

### File layout (after `add_vfx_source` expands the template)

```
Assets/VFXSources/<YourEffect>.vfxsrc/
├── index.vfxsrc                       — manifest (single_system)
├── controller/VFXController.js        — shared controller
└── systems/main/
    ├── system.json                    — name / template / defines / uniforms / resources
    └── shaders/
        ├── init.comp                  — particle spawn (POSITION INIT / VELOCITY INIT / LIFETIME INIT)
        ├── update.comp                — per-frame physics (FORCE COMPUTATION / INTEGRATE / WRITE BACK)
        ├── update_ssbo2image.comp     — SSBO → image2D for compat-mode GLES VS read
        ├── output.gles.vert           — billboard expansion (AXES / ALPHA / SIZE / TINT / V-FLIP)
        ├── output.gles.frag           — color + alpha (SHAPE / TINT / FINAL OUTPUT)
        ├── output.metal.vert          — Metal mirror (importer doesn't compile; reference only)
        └── output.metal.frag          — same
```

### SSBO slot layout (PARTICLE_SIZE = 12 uints)

```
slot 0     : alive       (uint, 1=alive 0=dead)
slot 1-3   : position    (vec3 stored as floatBitsToUint)
slot 4-6   : velocity    (vec3 stored as floatBitsToUint)
slot 7     : age         (float bits)
slot 8     : lifetime    (float bits)
slot 9-11  : FREE        ← agent can use for custom state (flipbook texIndex, collision flag, etc.)
```

All shaders MUST agree on PARTICLE_SIZE = 12. If you write a new slot in init, also read it in update / vert at the same index.

### Defines (authoring tunables)

Every name in this table is a **runtime exposed parameter** (see `references/asset-inspector.md` §2–§3): you still author it in `defines`, but the value becomes the parameter's runtime DEFAULT — the asset panel's starting value, live-tunable by the user afterwards. None of them are compile-time constants. (`TINT_R/G/B/A` and `USE_TEX_ALPHA` — §3.0b — are exposed the same way. The §3.0b–§3.0e value-literal defines like `SHEET_*`, `BOX_SIZE_*`, `TURB_*` ARE compile-time: changing them is an `edit_vfx_source` + reimport.)

| Name | Used in | Effect |
|---|---|---|
| `SIZE_START` | output.gles.vert | ⚠️ Naming is inverted vs. intuition: the taper runs **`SIZE_END` at birth → `SIZE_START` at death**. So `SIZE_START` is the DYING size. |
| `SIZE_END` | output.gles.vert | The NEWBORN size. Default canonical: SIZE_END=0.75 > SIZE_START=0.35, so particles shrink over life. Flip the two values if you want growth. |
| `LIFETIME_MIN` / `LIFETIME_MAX` | init.comp | Random lifetime range (seconds). Set MIN=MAX for fixed lifetime. |
| `SPEED_MIN` / `SPEED_MAX` | init.comp | Random initial speed range (units/sec). |
| `GRAVITY` | update.comp | Per-second downward velocity change. Set to 0 for weightless effects, negative for buoyancy (smoke rising). |

### Editable section contracts

Each shader in the template is split into named sections. **Each section is a contract: it declares what you must produce, what you can read, and what you must not touch.** Write any GLSL that satisfies the contract; there is no canonical list of "supported effects". The agent's job is to read the user's prompt and write GLSL that accomplishes it. The defaults that ship in each section are the canonical starting point — replace them.

#### init.comp

| Section | PURPOSE | MUST PRODUCE | AVAILABLE INPUTS | CONSTRAINTS |
|---|---|---|---|---|
| `POSITION INIT` | Set the initial spawn position of each new particle in local space. | `px / py / pz` (3 finite floats) | `seed` (mutable uint, `Rand(seed)` for [0,1) draws); `particleId`; `builtiParametersValue.{spawnId, systemSeed}`; when this system is an event target with `inherit:["position"]`, also `source_position` (vec3) and `sourceBase` (uint flat index into source's attributeBuffer). | No SSBO reads — incoming particle's slot is empty. Local space; the Model matrix applies downstream. **Default value is conditional**: independent systems get `float px = 0.0; float py = 0.0; float pz = 0.0;` (origin); event targets with `inherit:["position"]` get `float px = source_position.x; ...` auto-wired by the inherit injector. Override the block if you want an offset / jitter; the rewrite only fires on the unmodified template default. |
| `VELOCITY INIT` | Set the initial velocity vector. | `vx / vy / vz` (3 finite floats, units/sec) | Same as POSITION INIT, plus `px/py/pz` from above (so velocity can be a function of position); when the event has `inherit:["velocity"]`, also `source_velocity` (vec3). | No SSBO reads of other particles. **Default value is conditional**: independent systems get the canonical isotropic radial burst (theta/phi/speed → vx/vy/vz); event targets with `inherit:["velocity"]` get `float vx = source_velocity.x; ...` auto-wired. Override to scale (`source_velocity * 0.5`), redirect, or compose. |
| `LIFETIME INIT` | Set per-particle lifetime in seconds. | `lifetime` (finite float, > 0) | Same as above. | Strictly positive — zero or negative crashes the update stage. |
| `WRITE BACK` | Persist results to the SSBO. | (writes to slots 0..11) | Computed values above. | **Don't edit.** Slot layout must stay in sync across all 7 shaders. If you add a custom attribute at slot 9/10/11, add a corresponding write here AND a matching read in update.comp + output.gles.vert. |

#### update.comp

| Section | PURPOSE | MUST PRODUCE | AVAILABLE INPUTS | CONSTRAINTS |
|---|---|---|---|---|
| `LOAD ATTRIBUTES` | Read this particle's current state from the SSBO. | local vars `px,py,pz,vx,vy,vz,age,lt` and `dt` | The SSBO at slot `base + 0..8`. | Don't read other particles unless implementing a Pattern C cross-particle effect (boids/attractor) — see §Cross-particle reads below. |
| `AGING` | Advance the particle's age by `dt`. | updated `age` | `age`, `dt` | One line. Don't skip. |
| `EXPIRE PATH` | Detect end-of-life and return slot to dead list. | (early return + writes `alive=0` and dead list) | `age`, `lt` | **Don't edit the dead-list pattern.** Engine depends on it for slot reuse. You may add side-effect code *before* the dead-list return (e.g., emit a death-time signal into a custom attribute). |
| `FORCE COMPUTATION` | Modify `vx/vy/vz` for this frame based on forces. | updated `vx, vy, vz` | All loaded attributes + `dt`. | No SSBO writes here. |
| `INTEGRATE` | Update position from velocity. | updated `px, py, pz` | Updated velocity + `dt`. | Default Euler is fine for almost everything. Switch to semi-implicit only for stiff attractors. |
| `WRITE BACK` | Persist updates to the SSBO. | (writes to slots 1..7) | Updated locals. | **Don't edit which slots are written.** Add a slot 9/10/11 write here if you added one in init.comp's WRITE BACK. |

#### output.gles.vert

| Section | PURPOSE | MUST PRODUCE | AVAILABLE INPUTS | CONSTRAINTS |
|---|---|---|---|---|
| `QUAD CORNER` | Decode `gl_VertexID` into per-corner UV and offset. | `tex_cord` (vec2 UV) and `vOffsets` (vec2 in [-1,1]) | `gl_VertexID`, `gl_InstanceID` | **Don't edit.** Engine emits exactly 4 verts per particle in this order. |
| `FETCH ATTRIBUTES` | Read this particle's state for rendering. | `alive, position, velocity, age, lifetime` | SSBO (or sampler in `VFX_COMPAT_MODE`) at slot `base + 0..8` | Maintain both #ifdef branches if shipping cross-platform; dev preview can use just the #else (non-compat) branch. |
| `BILLBOARD AXES` | Define the three world-space basis vectors used to expand the quad. | `axisX, axisY, axisZ` (3 vec3) | `View` matrix; `velocity` (if velocity-aligned); `position`. | All three must be world-space unit vectors. They define the plane the quad sits on. |
| `ALPHA` | Compute the per-particle alpha from age/lifetime. | `alpha` (float, typically [0,1]) | `age, lifetime, t = age/lifetime` | Any curve (linear / quadratic / smoothstep / step) is valid. |
| `SIZE` | Compute the per-particle quad size. | `size` (float, > 0) | `t`, `SIZE_START`, `SIZE_END`, anything in scope. | Must be > 0; size-0 collapses the quad to a point. |
| `EMIT VARYINGS` | Write final values to varyings the frag shader reads. | `gl_Position, vTex, v0, v1, v2, v_posWS` | All locals above. | `vTex.y` is **already V-flipped** (`1.0 - tex_cord.y`). Don't re-flip in frag. |
| `DEAD-PARTICLE FALLBACK` | Collapse dead/out-of-bounds particles. | `gl_Position = vec4(0,0,0,1)` and zero varyings | `inBound`, `alive` | **Don't add real geometry here.** A dead particle must not rasterize. |

#### output.gles.frag

| Section | PURPOSE | MUST PRODUCE | AVAILABLE INPUTS | CONSTRAINTS |
|---|---|---|---|---|
| `SHAPE` | Compute a per-pixel mask for the particle's silhouette. | `shape` (float, typically [0,1]) | `uv = vTex.xy` (V-flip already applied), centered offsets from quad center. | Any mask function (procedural / texture alpha / sdf) works. |
| `TINT / COLOR MIX` | Compute the per-pixel color. | `tint` (vec3) | `v0.rgb` (per-particle tint from vert), `texColor = texture(Map0, uv)`, `v1/v2` (per-particle attrs). | If you sample Map0 as a gradient (1D color ramp indexed by age), don't also rely on Map0.alpha for shape — they conflict. |
| `FINAL OUTPUT` | Write the framebuffer color. | `color0 = vec4(...)` | `tint, shape, v0.a, texColor.a`, all locals. | Output is premultiplied alpha: `color0 = vec4(tint*alpha, alpha)`. Don't switch to straight alpha unless you also adjust the engine output material's blend state. |

#### update_ssbo2image.comp / output.metal.{vert,frag}

These are **not part of the agent's editable surface** in the typical iteration loop:
- `update_ssbo2image.comp` blits the SSBO into a sampler2D for VFX_COMPAT_MODE (older GLES devices without SSBO-in-VS). Edit only if you added a custom attribute that vert/frag need to read in compat mode.
- `output.metal.{vert,frag}` are reference mirrors. The importer cross-compiles AUSL from `output.gles.{vert,frag}` to Metal automatically; the .metal files are kept in sync for readability and don't affect rendering.

### Cross-particle reads (Pattern C — boids / attractor / swarm)

If the user prompt asks for inter-particle interaction (every particle reacts to nearby particles — flocking, attraction, repulsion, swarm cohesion), `update.comp`'s `FORCE COMPUTATION` section can read other particles' state from the same `attributeBuffer_buf` SSBO. The pattern:

```glsl
// Inside FORCE COMPUTATION
const uint CAPACITY = 2000u;
for (uint j = 0u; j < CAPACITY; j++) {
  if (j == particleOffset) continue;          // skip self
  uint other_base = j * PARTICLE_SIZE;
  if (attributeBuffer_buf[other_base + 0u] == 0u) continue;  // skip dead
  vec3 other_pos = vec3(
    uintBitsToFloat(attributeBuffer_buf[other_base + 1u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 2u]),
    uintBitsToFloat(attributeBuffer_buf[other_base + 3u])
  );
  // ... compute interaction force using this particle's state and other_pos ...
}
```

Cost: O(N²) per frame. Viable for `CAPACITY ≤ 500`. Above that, you'd need a spatial hash (advanced; skip unless explicitly requested).

The loop bound must match the system's actual capacity (system.json → uniforms.init.capacity). Either inline it as a local const (as above), or add a CUSTOM define (e.g. `POOL_COUNT`) to `system.json.defines` and reference that — do NOT use the name `CAPACITY` in defines (it's reserved and the expander rejects it; the real `#define CAPACITY` exists only in the output vert).
