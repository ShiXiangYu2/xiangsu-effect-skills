<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# §3.5 — PhysicsMesh template guide

> **Optional `material` resource** — same as StandardMesh §3.2 "Optional: bind a real editor material": bind any editor OMTL material and the particles render with its shading (PBR needs a scene light). No material ⇒ the unlit template output below.

## §3.5 — PhysicsMesh template guide

### When to pick PhysicsMesh

Pick `PhysicsMesh` when the *motion mechanic* is physical simulation under gravity + collisions — particles must **fall, bounce, and rest** rather than fly along a pre-baked velocity. Choose it by the mechanic, not the subject:

- **Things that fall and bounce on a ground plane** → PhysicsMesh. Bouncing balls, falling rocks, debris that piles up, dropped objects, simple ragdoll-ish chunks.
- **Per-particle 3D geometry following ballistic curves you script directly** (no plane interactions, no bounces) → StandardMesh (§3.2). Cheaper, less state.
- **Sparks / smoke / generic 2D billboards** → StandardQuad (§3.1).

If the visual reads as "they hit something and rebound", it's PhysicsMesh. If it reads as "they just keep falling forever in a curve", StandardMesh is plenty.

- **Particles that react to TOUCHING each other** (change colour/state/score on contact) → PhysicsMesh with `COLLISION_EVENT` (see "Collision events" below).
- **A fixed swarm that roams forever and never settles** → PhysicsMesh with `WALK_SPEED` + `isLoop:0` (see "Living self-propelled swarm" below).

### Mental model

- The engine runs **GPU Position-Based Dynamics** (PBD) on a SoA `physicsAttributeBuffer` distinct from the AoS attribute buffer the mesh-output reads. Each frame, an `UpdateAttributeBuffer` stage syncs position/velocity from SoA back to AoS so rendering stays consistent.
- The simulation loop, per substep:
  1. **Predict** — `velocity += gravity * subTimestep`, `position += velocity * subTimestep` (also saves `prevPosition`).
  2. **Collision detect** — push position out of every collider (default: a single ground plane at `GROUND_Y`; override/extend with `runtime.colliders`).
  3. **Inter-particle collision** (ON by default) — a GPU spatial hash buckets particles, and overlapping pairs get pushed apart (half each). Toggle off via `uniforms.update.enableInterParticleCollision`.
  4. **Update velocity** — recover velocity from `(position - prevPosition) / subTimestep` (PBD: any position correction becomes velocity automatically), then an energy-conserving cap ensures a collision never speeds a body up beyond its incoming speed (anti-launch).
  5. **Shape-matching** (only when `cluster_shape` binds a body) — pull member particles toward the body's rest shape; `SHAPE_STIFFNESS` sets how hard.
- **Substeps decouple stability from frame rate**: more substeps = the solver integrates more times per frame, so fast bodies don't tunnel through surfaces at high impact speed. More substeps = more stable + more GPU cost (and stiffer shape-matching — see soft bodies).
- **Inter-particle collision can be disabled** by adding `{name: 'enableInterParticleCollision', type: 'Int', value: 0}` to `uniforms.update`. Use where overlap is intentional (dense cascades), or to let a soft body compress more freely.
- **Bodies**: `runtime.cluster_shape` binds particles into rigid/soft bodies (sphere=independent grains, cube/cube_dense=multi-particle bodies); `SHAPE_STIFFNESS` makes them rigid↔jelly; `FRACTURE_Y` shatters a body into free particles. See the dedicated sections below.
- **Colliders**: `runtime.colliders` declares plane (infinite or finite via `bounds`), sphere (outer/containment), box, and analytic `sdf` shapes (torus/roundBox/capsule — curved/concave surfaces a primitive can't express). See "Colliders" below.
- **Continuous emission + lifecycle**: the spawner (`uniforms.spawn` rate/delay) emits continuously; each particle lives `LIFETIME_MIN..MAX` seconds then dies and its slot is recycled, so a steady population is maintained indefinitely. Give particles an initial motion with `INITIAL_SPEED` (radial burst from the spawn centre) and/or let `GRAVITY_Y` drive them; combine with a collider so they collide with a surface, and keep inter-particle collision ON so they then pile / stack on each other without overlapping (set `particleMaxRadius` = `PARTICLE_RADIUS` for tight, non-overlapping stacking). A fast `INITIAL_SPEED` into a containment sphere makes the collision with the wall visible (the cloud is bounded to the sphere); low gravity keeps the motion dominated by the burst + bounces rather than settling.

### How it differs from StandardMesh (essential reading)

| | StandardMesh | PhysicsMesh |
|---|---|---|
| Velocity comes from… | Author-defined `VELOCITY INIT` + `GRAVITY` per-frame | `INITIAL_SPEED` (radial burst at spawn) + the solver integrating under `GRAVITY_Y`/forces/contacts |
| Collisions | None — particles fly through everything | Ground plane at `GROUND_Y` + inter-particle (spatial-hashed, default ON since F-A-1; toggle via uniforms.update.enableInterParticleCollision) |
| Update shader | Agent-edited `update.comp` | **Engine-generated 24-stage pipeline — NOT user-editable** |
| `init.comp` | Single shader with full `POSITION/VELOCITY/...` init contract | Two shaders: `init_1_attr.comp` (AoS slots, mirrors StandardMesh's init) + `init_2_physics.comp` (SoA physics state). Plus a `init_0_sync.comp` snapshot pass. |
| Particle reuse | Dead-list pop + push on death | Dead-list pop only (C MVP doesn't track death; particles get round-robin-overwritten when capacity exceeded) |
| Render output | Same | Same — uses the verbatim StandardMesh `output.gles.{vert,frag}` against the AoS slots |
| Events | Can be event source/target | **Cannot be a CROSS-SYSTEM event target** (`EVENT_TARGET_TEMPLATE_FORBIDDEN`); can still spawn on its own. (Separately, it HAS its own intra-system **collision events** — per-contact rules — see "Collision events" below; unrelated to the Phase-D chain system.) |

The mesh-rendering side is **identical** to StandardMesh (32-uint AoS layout, BaseTexture sampler, depth-write solid mesh). What changes is *how the position/velocity slots get filled each frame* — the engine PBD pipeline owns it, not your update shader.

### Mandatory pre-step: get the mesh GUID

Apply `skills_root/assets/VFXAuthoring/references/design-process.md` → “Mesh 来源检查” during planning,
then resolve the actual Mesh GUID before `add_vfx_source`. PhysicsMesh provides
simulation and rendering, not the requested rock, shard or prop model. Without
a confirmed source, request the needed file or keep the mesh-dependent proposal
blocked; do not rely on a placeholder. A missing binding causes
`MISSING_REQUIRED_RESOURCE` at `add_vfx_source`.

### File layout (after `add_vfx_source` expands the template)

```
systems/main/
├─ system.json
└─ shaders/
   ├─ update_ssbo2image.comp     # mesh-output AoS → image (GLES compat). Verbatim from StandardMesh.
   ├─ output.gles.{vert,frag}    # mesh-instanced render. Verbatim from StandardMesh.
   ├─ output.metal.{vert,frag}   # same, Metal target.
   └─ physics/
      ├─ init_0_sync.comp        # snapshot dead-list counters (1-thread).
      ├─ init_1_attr.comp        # AoS init: POSITION/VELOCITY/.../LIFETIME — EDITABLE.
      ├─ init_2_physics.comp     # SoA init: physics state (mass/radius/restitution/friction). Position MUST mirror init_1's formula.
      ├─ stage_01_predict.comp   # PBD predict step.
      ├─ stage_02_collision.comp # ground-plane projection.
      ├─ stage_18_update_velocity.comp
      ├─ stage_21_contact_velocity.comp # restitution + friction at contacts.
      ├─ stage_22_update_attr.comp      # SoA → AoS sync (the bridge to mesh output).
      ├─ stage_23_ssbo2image.comp       # COMPAT-mode no-op.
      └─ noop.comp                       # placeholder for skipped Stage enum slots.
```

You will only edit `init_1_attr.comp`'s POSITION/COLOR/LIFETIME blocks for most effects, and tweak template-level defines.

### Editable sections — what you change vs what's fixed

- **`init_1_attr.comp`** (AoS rendering attributes — same shape as StandardMesh init):
  - `POSITION INIT`, `VELOCITY INIT`, `ROTATION INIT`, `SCALE INIT`, `COLOR INIT`, `ALPHA INIT`, `ANGULAR VELOCITY INIT`, `LIFETIME INIT` — **same contracts as StandardMesh §3.2**.
  - **NOT editable**: the dead-list pop block, the WRITE BACK slot indices, the seed derivation. The slot layout must match the StandardMesh 32-uint AoS so the output shader can read it.
- **`init_2_physics.comp`** (SoA physics state):
  - If you change POSITION in init_1, mirror the same formula here (same `seed` → same `Rand` sequence ⇒ same position). Otherwise the rendered first-frame position drifts from the physics-tracked position until stage_22 syncs.
  - Otherwise this shader stays as-is; the SoA writes (`PHYS_MASS=1`, `PHYS_INV_MASS=1`, `PHYS_RESTITUTION=RESTITUTION`, etc.) cover the C MVP attribute set.
- **`init_0_sync.comp`** — never edit. Engine plumbing.
- **`stage_*.comp`** — never edit. These ARE the simulator. Environmental forces (wind/drag) are configured via `runtime.forces`, NOT by editing these.
- **`output.gles.{vert,frag}`** — same as StandardMesh; tweak materials by changing `Map0` resource or via the `output` uniforms, not by hand-editing the vert.

### Runtime exposed parameters (live-tunable in the asset inspector)

`LIFETIME_MIN/MAX`, `SPAWN_RADIUS`, `INITIAL_SPEED`, `BASE_COLOR_R/G/B`,
`COLOR_VARIETY`, `SCALE_VARIETY`, `SPIN_VARIETY`, `ORIENT_RANDOM` are runtime
uniforms, not compile-time constants. **Keep authoring them in `defines` as usual**
— the value you pass becomes the parameter's runtime DEFAULT (the inspector's
starting value), and the user can still tune it live in the panel afterwards.
Their meanings are documented in the table below alongside the remaining
compile-time defines. The solver knobs `substeps` / `positionIterations` /
`enableInterParticleCollision` / `particleMaxRadius` (uniforms) are also editable
in the panel (Physics group).

### Defines — what to tune

| Define | Meaning | Typical range |
|---|---|---|
| `GRAVITY_Y` | Gravity acceleration in y (negative = down) | `-9.8` (real-world), `-20.0` (snappy), `-2.0` (slow-mo) |
| `RESTITUTION` | Bounciness at contact (0 = stick, 1 = elastic, >1 = super-ball). Written per particle at init + read by stage_21 + engine inter-particle collision → a per-system **physics material** knob (see Materials below). | `0.0..1.0` typical, up to `1.3` for stylized over-bounce |
| `FRICTION` | Tangential damping at contact (0 = ice, 1 = rubber on rubber). Also per-particle / per-system (see Materials). **For SLIDING on an incline, friction is not a free "feel" knob — it's governed by the slope angle (see "Sliding on a slope" below).** | `0.0..1.0`, `0.1` for slippy, `0.5` for sticky |
| `BASE_COLOR_R/G/B` | Per-system fixed particle tint (default white `1,1,1`), used when `COLOR_VARIETY` is off. Lets different systems be visually distinct — e.g. one colour per material. | `0..1` each |
| `PARTICLE_RADIUS` | Collision radius (so the mesh sits ON the plane, not half-buried) | Match the mesh's visual radius — `0.5` for a unit ball |
| `GROUND_Y` | World-space y of the ground plane | `-5.0` typical; below the camera frustum is fine |
| `SPAWN_RADIUS` | Radius of the sphere around the host origin that particles spawn within (`0` ⇒ all from the exact centre) | `0..5` typical |
| `INITIAL_SPEED` | Speed of the initial velocity given at spawn, directed radially OUTWARD from the spawn centre (isotropic burst). `0` (default) = spawn at rest and let gravity/forces take over | `0` (rest); `4..20` for a burst/fountain |
| `LIFETIME_MIN/MAX` | Particle lifespan in seconds (set MIN=MAX for a fixed lifetime). When a particle's age exceeds its lifetime it DIES and its slot is RECYCLED, so continuous spawning sustains a steady population indefinitely (no exhaustion). Also drives age-based scale/alpha in the output. | `2..8` typical |
| `SCALE_START`/`SCALE_END` | Mesh-output scale-over-life multipliers (StandardMesh-style). Leave at `1.0/1.0` for constant scale; set `SCALE_END < SCALE_START` for shrinking on impact | `1.0/1.0` default |
| `FRACTURE_Y` | Height at which a clustered body breaks apart into free, independent particles (see "Fracture" below). Only meaningful with a cluster shape. | `-1000.0` (default = never fracture); set near a floor height to shatter on landing |
| `SHAPE_STIFFNESS` | How hard a clustered body holds its rest shape per solve iteration. `1.0` = perfectly rigid; lower = progressively softer / jelly (see "Soft bodies" below). | `1.0` (default rigid); `< 0.2` for visibly soft |
| `COLOR_VARIETY` | `> 0` tints each body (per-cluster) a random vibrant hue; `0` (default) = white / texture colour. Makes a group of bodies multi-coloured. | `0` (off) or `1` (on) |
| `SCALE_VARIETY` | Per-body random SIZE spread: each body's overall scale is `1 ± SCALE_VARIETY` (applied consistently to lattice spacing, collision radius, and visual mesh). `0` (default) = uniform size. | `0` (off); `0.3..0.5` for noticeable size variety |
| `SPIN_VARIETY` | Per-body random initial angular velocity (`ω × r` kick, random axis, rate up to this). NOTE: shape-matching DAMPS rigid angular velocity, so a high-stiffness body only gets a brief tumble before settling; pair with a lower `SHAPE_STIFFNESS` for the spin to survive (the body then wobbles softly rather than spinning rigidly). Persistent rigid spin needs true angular dynamics (not yet implemented). `0` = none. | `0` (off); `3..6` with `SHAPE_STIFFNESS < 0.6` |
| `ORIENT_RANDOM` | Whether each body spawns at a RANDOM orientation. `1` (default) tumbles bodies for natural variety; set `0` to spawn every body at its authored upright orientation — wanted for shaped clusters (`mesh`/`rod`/`sheet`/`points`) you want standing the right way up rather than tumbling. | `1` (default, random) or `0` (upright) |
| `INITIAL_VX` | Coherent horizontal velocity (m/s) added to every particle at spawn, on top of the radial `INITIAL_SPEED` burst. Use for a directional sideways throw / current. `0` (default) = none. | `0` (default); `±2..10` |
| `WALK_SPEED` | **Self-propelled / anti-decay.** When `> 0`, every frame the particle's velocity is RE-NORMALIZED to this fixed magnitude — the particle becomes "active matter" that NEVER slows or stops, while its DIRECTION still comes from collisions/walls → a perpetual lively random walk. This is the ONLY reliable way to keep a swarm moving forever: PBD always bleeds kinetic energy (`RESTITUTION<1` + position-solver damping), so a nominally "elastic" swarm WILL decay to rest without it. A dead-stopped particle is kicked in a per-particle hashed direction so it never sticks. `0` (default) = off (normal energy-losing physics). | `0` (off); `4..12` for a fast roaming swarm |
| `COLLISION_EVENT` | Master switch for the **particle-collision event system** (see "Collision events" below). `1` enables it: each particle is assigned a "team" tag at spawn, and a rule is run at every particle-particle contact. `0` (default) = off (inert; no per-contact logic). | `0` (off) or `1` (on) |
| `COLLISION_TEAMS` | Number of teams/states for the collision-event rule (the built-in example is cyclic dominance, see below). | `3` (default) |

### Sliding on a slope — derive `FRICTION` from the angle, don't guess by "feel"

Whether a body SLIDES down an incline (and how fast) is fixed by the slope angle θ
vs `FRICTION` (μ) — it is NOT a free "slippy/sticky" choice:

- A plane collider's tilt θ is the angle of its `normal` off vertical: `θ = acos(normal.y)`
  (a normal in the XY plane is `[sinθ, cosθ, 0]`).
- **Stick vs slide:** `μ ≥ tanθ` ⇒ the body STICKS (no slide). `μ < tanθ` ⇒ it slides.
- **Speed:** along-slope acceleration is `g·(sinθ − μ·cosθ)`. The closer μ is to `tanθ`,
  the slower the crawl; the smaller μ, the brisker the slide.
- **Rule of thumb for a lively slide:** `μ ≈ 0.1–0.3 × tanθ`. E.g. a 25° slope has
  `tanθ ≈ 0.47`, so `FRICTION ≈ 0.05–0.15`. The common mistake is leaving μ at a generic
  `0.25–0.5`: on a gentle slope that leaves almost no driving force, so the body barely
  creeps (it technically slides, but very slowly).
- **PBD skews sticky:** the position-based solver damps tangential motion MORE than the
  analytic formula, so pick μ at the LOW end and prefer a STEEPER slope over a higher μ.
- Two levers to speed a slide up: lower `FRICTION`, or steepen the slope (rotate the
  `normal` further from vertical). Raising `GRAVITY_Y` scales overall speed but does NOT
  change the stick-vs-slide threshold.

### Uniforms — engine-read physics knobs

`uniforms.init` (plain `exposeProperties` — only `capacity` goes in orderedUniform per `project_vfxsrc_init_props_persistence`):

| Name | Type | Engine effect |
|---|---|---|
| `capacity` | Int | **Total particle-buffer size = the maximum number of PARTICLES alive at once — NOT a count of bodies.** A rigid/soft body made of `numParticlesPerShape` particles consumes that many slots, so a single N-particle body needs `capacity ≥ N`, and K simultaneous bodies need `capacity ≥ K·N`. (Setting `capacity` to a small number while `numParticlesPerShape` is large yields only a handful of particles — too few to form even one body.) |
| `numParticlesPerShape` | Int | Particles per body. The importer DERIVES this from `cluster_shape` (sphere⇒1, cube⇒8, cube_dense⇒64, ball⇒50; parametric ⇒ N³/count/length/W·H), so set it to match the chosen `cluster_shape`. |
| `particleMaxRadius` | Float | Inter-particle collision radius (and spatial-hash cell hint). Set ≈ `PARTICLE_RADIUS`. |
| `substeps` | Int | Simulation substeps per frame. More = more stable at high impact speed (less tunneling), more GPU cost. ALSO interacts with shape stiffness — see soft-body note below. |
| `positionIterations` | Int | Constraint-solve iterations per substep. More = stiffer constraints (harder rigid bodies); fewer = softer. See soft-body note. |

Spawn uniforms behave the same as the other templates (`spawnRateMin/Max`, `delayMin/Max`, `originalSpawnRate`), **plus** one physics-relevant control:

| Name | Type | Engine effect |
|---|---|---|
| `isLoop` | Int | Whether the spawner repeats. **Defaults to `1` (loop) in the engine** (`AEVFXSpawnContext`), so a PhysicsMesh effect keeps emitting fresh particles every cycle — which looks like the simulation "restarting / repeating the same motion over and over". Set `{name:'isLoop', type:'Int', value:0}` to spawn the population **ONCE** and then never again. **This is the fix for "why does my physics effect keep repeating?"** — almost always you want `isLoop:0` for a one-shot drop / shatter / fixed swarm. Pair with a long `LIFETIME_MIN/MAX` so the one-shot population persists. |

### Starter recipe — minimal bouncing balls (copy-paste, then adjust)

```typescript
await edit_by_dsl({commands: [{command_type: 'add_vfx_source', params: {
  name: 'BouncyBalls',
  manifest: {effect: 'BouncyBalls'},
  systems: [{
    name: 'main',
    template: 'PhysicsMesh',
    defines: {
      GRAVITY_Y: -15.0,         // brisk fall
      RESTITUTION: 0.7,         // lively bounces
      FRICTION: 0.15,
      PARTICLE_RADIUS: 0.5,
      GROUND_Y: -5.0,
      SPAWN_RADIUS: 3.0,        // spread across a 3-unit sphere on spawn
      LIFETIME_MIN: 4.0,
      LIFETIME_MAX: 6.0,
      SCALE_START: 1.0,
      SCALE_END: 1.0,
    },
    resources: {
      mesh: {ref: 'ball_mesh'}, // a unit-radius sphere mesh
      Map0: {ref: 'ball_tex'},  // diffuse map for the mesh
    },
    uniforms: {
      init: [
        {name: 'capacity', type: 'Int', value: 128},
        {name: 'numParticlesPerShape', type: 'Int', value: 1},
        {name: 'particleMaxRadius', type: 'Float', value: 0.5},
        {name: 'substeps', type: 'Int', value: 3},
        {name: 'positionIterations', type: 'Int', value: 1},
      ],
      spawn: [
        // emit_rate = spawnRate / delay = 10 / 1.0 = 10/s. Supply =
        // capacity / lifetime_min = 128 / 4 = 32/s — comfortably above
        // demand, so SPAWN_DEMAND_EXCEEDS_SUPPLY won't fire.
        {name: 'spawnRateMin', type: 'Float', value: 10.0},
        {name: 'spawnRateMax', type: 'Float', value: 10.0},
        {name: 'delayMin', type: 'Float', value: 1.0},
        {name: 'delayMax', type: 'Float', value: 1.0},
      ],
    },
  }],
  shared_resources: {
    ball_mesh: {type: 'Mesh', guid: '<sphere_mesh_guid>'},
    ball_tex:  {type: 'Texture', guid: '<diffuse_guid>'},
  },
}}]});
// Returns the imported resource guid. Bind it to a SceneObject's VFXEffectBlock
// component the same way as §3.2 step 3. Import/compile failures are command errors.
```

### Gotchas

- **Particles look stuck above the ground** → `PARTICLE_RADIUS` too large for the mesh (collision pushes the position up by radius). Halve `PARTICLE_RADIUS` until the meshes visually touch the ground.
- **Particles vibrate at rest / never settle** → `RESTITUTION` too high (energy never dissipates). Drop to `0.4..0.6`. `FRICTION` helps too.
- **Particles tunnel through the ground at high speeds** → `substeps` too low. Raise to `5` or `8`. Or lower `GRAVITY_Y` magnitude.
- **All particles spawn at the same point** → `SPAWN_RADIUS = 0`. Set to a few units (`1..5`).
- **Import succeeds but nothing renders** → bind the `.vfxsrc` GUID to a `VFXEffectBlock` component on a SceneObject with a Transform, same as the other templates. Also verify the mesh GUID points at a real Mesh resource (Model GUIDs work — importer extracts the first Mesh).
- **`MISSING_REQUIRED_RESOURCE: 'mesh'`** → forgot `resources.mesh` on the system. Both `mesh` AND `Map0` are required (same as StandardMesh).
- **PhysicsMesh cannot receive events** (`EVENT_TARGET_TEMPLATE_FORBIDDEN`). A PhysicsMesh system can spawn on its own; it just can't be the *target* of another system's event in this phase.
- **Don't author scale-over-life with engine PBD**. Animate position via the physics; if you want shrinking, use the regular `SCALE_END < SCALE_START` curve on the AoS — that's a render-time multiplier, doesn't affect collision radius.

### Colliders — `runtime.colliders`

The default ground plane lives at `y = GROUND_Y` (a tunable `#define`). For anything more complex — a tilted plane, a bouncer sphere mid-scene, a marble-in-bowl containment — declare colliders in `system.runtime.colliders`:

```json
{
  "name": "main",
  "template": "PhysicsMesh",
  ...
  "runtime": {
    "colliders": [
      { "type": "plane",  "point": [0, -6, 0],  "normal": [0, 1, 0] },
      { "type": "sphere", "center": [0,  0, 0], "radius": 2 },
      { "type": "sphere", "center": [0,  0, 0], "radius": 10, "inside": true }
    ]
  }
}
```

The bundle-rebake injector swaps the marker block in `stage_02_collision.comp` for one GLSL block per entry, so every collider edit is picked up automatically on `add_vfx_source` / `edit_vfx_source` without a recompile step.

| Collider | Fields | Meaning |
|---|---|---|
| `plane` (infinite) | `point: [x,y,z]`, `normal: [x,y,z]` | Half-space test. Particle pushed along `+normal` to stay on the side `normal` points into. **`normal` must be unit-length** (validator rejects otherwise). A tilted `normal` makes a slope. |
| `plane` (finite) | …`point`, `normal`, `bounds: [xMin,xMax,zMin,zMax]` | Same half-space, but the push only applies while the particle is over the rectangular XZ patch. Past the patch edge there is NO support → the particle leaves the surface and falls. This is how a surface gets a finite extent / an edge to slide off. |
| `sphere` (outer) | `center`, `radius` | Particle centre stays beyond `radius + particleRadius` from `center` — particles bounce OFF the sphere. |
| `sphere` (containment) | `center`, `radius`, `"inside": true` | Particle centre stays within `radius − particleRadius` of `center` — particles are trapped INSIDE (a smooth concave container). |
| `box` | `center`, `halfExtents: [x,y,z]`, optional `rotation: [x,y,z]` (Euler radians) | Solid oriented box; particles are pushed out of it. **Caveat:** a ROTATED box is unstable with shape-matched rigid bodies (can fling them) — for a tilted finite surface prefer a `plane` with `bounds`. A flat (unrotated) box is fine. |
| `sdf` | `shape: 'torus'\|'roundBox'\|'capsule'`, `center`, optional `rotation: [x,y,z]` (Euler radians), optional `inside`. Shape params: torus/capsule `radii: [a,b]` (torus = [ringRadius, tubeRadius]; capsule = [halfHeight, radius]); roundBox `halfExtents: [x,y,z]` + optional `round`. | Analytic signed-distance collider — a curved/concave shape a primitive can't express (a `torus` has a hole; particles over the centre pass straight through while the ring catches the rest). Evaluated directly in the shader (no baked 3D-texture asset), so it's exact and moves/rotates with the host. `inside:true` flips to containment (trap particles inside the shape). |
| `sdfTexture` | `sampler` (name of a `Texture` uniform in `uniforms.update` bound to a `Texture3D` resource), `center`, `scale: [x,y,z]` (world size of the volume box), optional `rotation`, optional `gain`. | Collide with an ARBITRARY baked shape stored in a 3D volume texture (a `.vf` whose `.x` channel is the signed distance, negative inside) — logos, letterforms, scanned meshes, anything no analytic primitive covers. The volume's `[0,1]³` maps onto the box; particles inside (`.x<0`) are pushed out along the sampled gradient. Match `scale`'s aspect to the volume's voxel dims to avoid distortion. See "Texture-baked SDF" below. |

⚠️ **Local space**: collider geometry is in the *system's local space* (same space as particle positions). If you re-host the effect on a moving SceneObject, the colliders move with it. For a world-fixed ground, leave the host's Transform at origin.

⚠️ **Default is preserved**: if `runtime.colliders` is omitted (or `[]`), stage_02 keeps its built-in single-plane-at-`GROUND_Y` block. F-C MVP effects render identically without any JSON change.

⚠️ **Substep cost**: each collider adds a per-particle test inside stage_02. For 100+ colliders this becomes expensive at high `substeps`. Keep the list lean (<10 colliders typical).

**Texture-baked SDF** (`sdfTexture`): to collide with an arbitrary baked shape, wire three things so the volume reaches the physics solver as a `sampler3D`:
1. Declare the volume in `manifest.shared_resources` with `type: 'Texture3D'` (a `.vf` whose `.x` channel is the signed distance), e.g. `vol: { type: 'Texture3D', guid: '<.vf guid>' }`.
2. Map it through `system.resources` (`sdfvol: { ref: 'vol' }`) and bind it as a **`Texture` uniform in `uniforms.update`**: `{ name: 'u_sdf0', type: 'Texture', resource: 'sdfvol' }`. (A `Texture3D` is a `Texture`, so this is the normal texture-uniform path; the engine binds it to the physics-update compute stage by name.)
3. Reference that uniform name from the collider: `{ type: 'sdfTexture', sampler: 'u_sdf0', center, scale, ... }`.

The collider's `scale` is the world size of the volume's `[0,1]³` box — set its aspect to the voxel dimensions (e.g. a `128×127×41` volume → `scale` like `[13,13,4]`) so the shape isn't stretched. A particle whose sampled `.x < 0` is inside the baked solid and gets ejected along the field gradient; `gain` tunes the push strength. This is how an effect collides against a logo / character / scanned-mesh field that no analytic shape can represent.

### Rigid / soft bodies — `runtime.cluster_shape`

By default each particle is its OWN body (`cluster_shape: 'sphere'`, 1 particle per body — independent grains). To bind a GROUP of particles into a single body that holds a shape and tumbles/deforms together, choose a multi-sample shape:

```json
{ "name": "main", "template": "PhysicsMesh", "runtime": { "cluster_shape": "cube_dense" } }
```

`cluster_shape` is either a **string shorthand** or a **parametric object** for freely-generated analytic shapes:

| string shorthand | particles per body | reads as |
|---|---|---|
| `sphere` | 1 | independent grains/balls (no body) |
| `cube` | 8 | a coarse cube (corners only) = `{kind:'cube',resolution:2}` |
| `cube_dense` | 64 | a solid 4×4×4 block = `{kind:'cube',resolution:4}` |
| `ball` | 50 | a round body = `{kind:'ball',count:50}` |

| parametric object | particles per body | shape |
|---|---|---|
| `{"kind":"cube","resolution":N}` | N³ | solid block, N particles per edge |
| `{"kind":"ball","count":C}` | C | C points on a Fibonacci sphere |
| `{"kind":"rod","length":L}` | L | a line of L particles (local Z axis) |
| `{"kind":"sheet","size":[W,H]}` | W·H | a flat W×H plate (local XZ plane) |
| `{"kind":"points","offsets":[[x,y,z],…]}` | offsets.length | ANY shape — you give the explicit per-sample offset list |

The `points` form lets you build any rigid body from an arbitrary list of sample offsets (ring, letter, asymmetric cluster, …). Offsets are authored in neighbour-spacing-1 units (same as the analytic shapes — init_2 scales them by `PARTICLE_RADIUS·CLUSTER_SPACING`), and are **centroid-centred at bake time** so the body spawns on the spawn point regardless of where you placed the points. Keep the list within the per-body particle budget (~150–200, see capacity note); it bakes into the shader as a constant array, so tens–low-hundreds of points is the practical range.

```json
{ "name": "main", "template": "PhysicsMesh", "runtime": { "cluster_shape": {"kind":"cube","resolution":5} } }
```

The injector and the importer both derive `numParticlesPerShape` from the spec, so you only set `cluster_shape` (and a matching `capacity`/`numParticlesPerShape` — see below). Sample offsets are generated in closed form (centred at the body origin, neighbour spacing 1, scaled by `PARTICLE_RADIUS·CLUSTER_SPACING`), so any of these shapes composes with all the per-body variety knobs.

Mechanism: the engine runs **shape-matching** — each solve iteration it computes the body's current centre-of-mass + best-fit rotation and pulls every member particle toward its rest position in that frame. So the body keeps its shape while translating and rotating freely; impacts deform it and the shape-matching restores it.

**Per-body variety** (so a group of bodies isn't identical): each body spawns at a **random orientation** by default (seeded per body — shape-matching tracks it from there; set `ORIENT_RANDOM: 0` to keep bodies upright at their authored orientation). Opt in to more variety with `COLOR_VARIETY` (per-body random hue) and `SCALE_VARIETY` (per-body random size, applied consistently to spacing + collision + visual). All are seeded per body, so each body is internally uniform (one orientation/colour/size) while bodies differ from each other.

**Custom-shape bodies (`points`):** to make a cluster take a specific shape, pass an explicit list of local-space offsets as `cluster_shape: {kind:'points', offsets}` (centroid-centred, in neighbour-spacing-1 units; keep ≲ a few hundred points). Pair with `ORIENT_RANDOM: 0` to keep the figure standing upright, `SPAWN_RADIUS≈0` to centre it, and a render scale with sphere Ø < the centre spacing (`PARTICLE_RADIUS·CLUSTER_SPACING`) so the points stay distinct.

**Particle count / detail:** how high you can push `N` depends on whether the body MOVES — see "Particle-count limits" below. Short version: a STATIC/floating high-detail figure can be thousands (split `points` across ≤2500-per-system chunks); a body that FALLS/tumbles must stay a few hundred (COM overflow freezes bigger ones).

**Capacity (the #1 mistake):** `capacity` counts PARTICLES, not bodies. With `cube_dense` (64 particles/body), one body needs `capacity ≥ 64`; K bodies at once need `capacity ≥ 64·K`. A small capacity with a multi-sample shape yields only a few particles — not even one full body. Set `numParticlesPerShape` to the body's particle count (sphere 1, cube 8, cube_dense 64, ball 50; for a parametric spec it is N³ / count / length / W·H respectively).

Notes:
- A body's own particles don't collide with each other (the shape constraint holds them); they DO collide with other bodies' particles when inter-particle collision is on.
- The body's rotation is synced to the per-instance mesh each frame, so the rendered meshes tumble with the body.

### Fracture — `FRACTURE_Y` (a body breaks into free particles)

A clustered body can shatter into independent particles. Set the `FRACTURE_Y` define; when the body's centre-of-mass drops below that height, EVERY member particle is released from the body on the SAME frame and becomes a free particle (its own body), after which inter-particle collision lets the pieces scatter and pile.

- Default `-1000.0` = never fracture (stays a solid body forever).
- Set it slightly above a floor/surface height to make a body shatter on landing.
- Fracture is driven by the body's SHARED centre-of-mass (not each particle's own height), so the whole body breaks at once — a per-particle height test would release lower layers first and visibly tear the body apart.

**Free-fall + shatter recipe** (a shaped body drops onto the floor and breaks apart, the pieces piling): host the emitter high (`Transform.localPosition.y` well above the floor), `GROUND_Y` at the floor, `FRACTURE_Y` just above where the body's COM rests on the floor (so it detonates on impact), `SHAPE_STIFFNESS 1` (rigid until it shatters). IMPORTANT — **a shape-matched body falls ~10× SLOWER than free-fall** (the shape-match solve + the anti-launch cap bleed downward speed), so use a LARGE `GRAVITY_Y` (≈ `-40…-80`) to get a visibly-paced drop. After fracture the freed particles are independent and fall/pile normally. Live-verified end-to-end with a mesh-voxelized body (see below). Keep the body's particle count modest — high counts freeze (next section).

### Soft bodies — `SHAPE_STIFFNESS` (rigid ↔ jelly)

`SHAPE_STIFFNESS` (default `1.0`) controls how strongly shape-matching pulls particles back to the rest shape each iteration. `1.0` = rigid; lower = softer, so impacts deform the body and it springs back (jelly).

Key principle — **stiffness compounds over the solve loop**: shape-matching runs `substeps × positionIterations` times per frame, so a per-iteration stiffness `s` gives an effective per-frame stiffness ≈ `1 − (1 − s)^(substeps·positionIterations)`. With the usual 5–6 substeps × several iterations, even a small `s` compounds to nearly rigid. To get a VISIBLY soft / bouncy body you must lower BOTH:
- `SHAPE_STIFFNESS` to a small value, AND
- `substeps` and `positionIterations` to a few (so the spring doesn't fully converge each frame).

Then bigger deformation = lower stiffness / fewer iterations; more sustained wobble = lower `FRICTION` (less damping). Turning inter-particle collision off lets a soft body compress more freely.

(Stability: a built-in energy-conserving step prevents collisions from ever speeding a body up beyond its incoming speed, so rigid bodies never "launch" off a surface no matter the impact speed; for soft bodies this cap is relaxed in proportion to `1/SHAPE_STIFFNESS` so the spring can still rebound.)

### Physics materials — `RESTITUTION` + `FRICTION` (+ `SHAPE_STIFFNESS`)

A material is just a bundle of contact properties. The engine stores `restitution`
and `friction` PER PARTICLE (init writes the system's defines into each particle's
SoA slot; `stage_21` ground-contact and the engine's inter-particle collision read
them back), so each SYSTEM can be a different material. Give each a distinct
`BASE_COLOR_*` to tell them apart. Useful presets:

| material | RESTITUTION | FRICTION | SHAPE_STIFFNESS | reads as |
|---|---|---|---|---|
| rubber | 0.9 | 0.35 | 1 | very bouncy |
| steel / metal | 0.25 | 0.3 | 1 | low bounce, hard |
| ice | 0.08 | 0.02 | 1 | no bounce, slides far |
| wood | 0.45 | 0.65 | 1 | medium bounce, grips |
| clay / putty | 0.0 | 0.95 | 1 | dead thud, sticks |
| jelly | 0.1 | 0.5 | <0.3 (cluster) | squishes + wobbles |
| water | 0.0 | ~0.08 | 0.02 (cluster) + `FRACTURE_Y` near floor | a soft droplet blob that splats + spreads into a puddle on impact |

**Water** isn't a rigid body — approximate it as a multi-particle soft cluster
(`cluster_shape:'ball'`, ~50 small droplets, `SHAPE_STIFFNESS≈0.02`, restitution 0,
low friction, inter-particle collision ON) with `FRACTURE_Y` just above the floor so
it breaks into free droplets on landing and they spread out flat — a splash/puddle.

For SEVERAL materials in one scene, author one single-material system per material
(each its own `BASE_COLOR_*`) and host them at different X. Live-verified
(`_materials.test.ts`): rubber bounces highest, steel/wood medium, ice/clay barely,
water splashes into a flat spread. **Capture note:** single-particle balls fall at
FULL gravity speed (land in <1.5 s at high G — easy to mistake the rested frames for
"hovering"); CLUSTERS fall ~10× slower (shape-matching damping). For a visible
drop+bounce use MODERATE `GRAVITY_Y` (≈ −18…−25) + tight frame capture; for a
cluster (water/jelly) use a much bigger `GRAVITY_Y` (≈ −120…−180) to land it in the
same window.

### Particle-count limits (READ before scaling a body up)

There are THREE distinct ceilings; which one bites depends on what the body does:

1. **Continuous-spawn steady-state ≈ 150–200 alive.** This is only the emission-rate balance of a fountain of *independent* particles (spawnRate / delay / lifetime); it is NOT a hard cap. A body spawned all-at-once is unaffected — set `capacity = numParticlesPerShape = N`.

2. **`points` const-array ceiling ≈ 2500 per system.** A `cluster_shape:{kind:'points'}` bakes its offsets into the shader as a `const` array; above ~2500 the GLSL compiler runs out of memory (`bad_alloc`) and the editor crashes. To go higher, SPLIT the cloud across multiple systems in one `.vfxsrc` (each ≤2500), interleaved (`i % numSystems`) so chunks stay centred/aligned, all under one host — they combine into one figure. (Analytic shapes — cube/ball/rod/sheet — have no such limit; only explicit `points` do.)

3. **A FALLING / moving shape-matched body freezes above ≈ a few hundred particles.** The engine's shape-matching accumulates the body's centre-of-mass and covariance by summing every particle position as a scaled fixed-point int; past ~1000 particles the sum overflows and the COM goes to garbage, so the body **stops translating and hovers dead-still** (it will not fall). cube_dense (64) and a ~300-point body fall fine; a 1500-point body hovers. **So a body that must MOVE/FALL/tumble is capped at a few hundred particles**, while a STATIC or floating (no-gravity) high-detail body of thousands is fine. (A count-aware COM fixed-point scale in the importer would lift this — not yet implemented; tracked as a known limit.)

Net guidance: high-detail still figure → thousands OK (split `points` across systems, gravity 0). Body that falls and shatters → keep it to a few hundred particles, big `GRAVITY_Y`. Don't promise a 1000+-particle body that also moves under physics until the COM-scale fix lands.

### Collision events — `COLLISION_EVENT` (per-contact GPU rule)

A general hook that runs a rule at **every particle-particle contact**. The engine's
contact-solve stage has both colliding particle indices (`pa`,`pb`); when
`COLLISION_EVENT:1` the importer injects a rule there that reads/writes a per-particle
"team/state" tag (stored in a spare SoA slot, slot 38). Colour-change is just ONE
example handler — the same hook can drive scoring, kill/merge, state machines, etc.

**Built-in example rule — cyclic dominance (rock-paper-scissors).** With
`COLLISION_TEAMS:3`, each particle is one of 3 teams rendered red / yellow / blue. On
contact the "beaten" team adopts the winner (`1>0`, `2>1`, `0>2`): red→yellow→blue→red.
`stage_22` maps the team tag to the particle colour each frame.

Two hard-won rules for making this actually work:

- **Tags MUST be seeded from `particleIdx`, not the cluster seed.** A cluster spawns as
  ONE object sharing one `rigidbodyIdx` → one RNG seed, so seeding the team from the
  seed gives every particle in the cluster the SAME team (one colour, collisions never
  differ, zero dynamics). The init seeds from `particleIdx` so a single spawned cluster
  is a proper MIX of teams. (This is handled in the template; noted here because it's the
  #1 reason a collision-event swarm shows only one colour.)
- **Cyclic dominance in a FULLY-MIXED swarm collapses to one survivor fast** (it's
  well-mixed rock-paper-scissors → competitive exclusion). To keep all 3 colours
  visibly coexisting you need either a self-propelled swarm that keeps re-mixing (below)
  or limited mobility (local spiral-wave domains). High density + tight initial pack
  converges in ~1 s; spread the cloud out to start.

### Living self-propelled swarm (fixed count, never stops, never repeats)

The canonical "a fixed set of particles that stay alive and random-walk forever" recipe
— combines three mechanisms:

1. **Spawn ONCE** — `isLoop:0` (else the spawner loops and the motion visibly repeats).
2. **Never decay** — `WALK_SPEED>0` renormalizes speed every frame so PBD's inevitable
   energy bleed can't stop them; direction still comes from collisions → perpetual walk.
3. **Make them collide with each other** — particles in one cluster share a
   `rigidbodyId` and the engine SKIPS same-body contact pairs, so a cluster can't
   self-collide. Spawn them as one cluster (one object = N particles, which bypasses the
   per-particle spawn-rate validator), then `FRACTURE_Y` ABOVE the spawn height so it
   fractures IMMEDIATELY — fracture gives each particle a UNIQUE `rigidbodyId`, so now
   they collide with each other. Contain them in an `sdf roundBox` with `inside:true`.

Live-verified (`_collision_event.test.ts`): 256 particles spawn as one `points` cluster,
fracture instantly into independent grains, roam the whole box at constant speed for the
full clip without slowing, three colours coexist and cyclically take each other over.

```typescript
defines: {
  GRAVITY_Y: 0.0,          // no fall → pure roaming
  RESTITUTION: 0.98, FRICTION: 0.0,   // (energy still bleeds — WALK_SPEED is what keeps them going)
  PARTICLE_RADIUS: 0.42, GROUND_Y: -1000.0, SPAWN_RADIUS: 0.1,
  INITIAL_SPEED: 9.0,
  WALK_SPEED: 9.0,         // ← self-propelled: never stops
  LIFETIME_MIN: 60.0, LIFETIME_MAX: 60.0,   // long-lived
  SCALE_START: 0.08, SCALE_END: 0.08,
  FRACTURE_Y: 100.0,       // COM below this at spawn ⇒ fracture immediately → independent particles
  COLOR_VARIETY: 0.0, ORIENT_RANDOM: 0.0, SHAPE_STIFFNESS: 0.0,
  COLLISION_EVENT: 1.0, COLLISION_TEAMS: 3.0,
},
uniforms: {
  init:   [{name:'capacity',type:'Int',value:256}, {name:'numParticlesPerShape',type:'Int',value:256}, {name:'particleMaxRadius',type:'Float',value:0.42}],
  update: [{name:'substeps',type:'Int',value:6}, {name:'positionIterations',type:'Int',value:4}, {name:'enableInterParticleCollision',type:'Int',value:1}],
  spawn:  [{name:'spawnRateMin',type:'Float',value:1.0},{name:'spawnRateMax',type:'Float',value:1.0},{name:'delayMin',type:'Float',value:1.0},{name:'delayMax',type:'Float',value:1.0},
           {name:'isLoop',type:'Int',value:0}],   // ← spawn once, never repeat
},
runtime: {
  cluster_shape: {kind:'points', offsets: /* a scattered cloud of 256 [x,y,z] that FILLS the box */},
  colliders: [{type:'sdf', shape:'roundBox', halfExtents:[11,11,2.5], round:0.3, center:[0,0,0], inside:true}],
},
```

### Force externs — `runtime.forces`

Add per-substep environmental forces (wind, drag) to the predict integrator. Each entry generates one GLSL statement that mutates `velocity` BEFORE gravity adds its kick, stacking additively.

```json
"runtime": {
  "forces": [
    { "type": "drag", "coefficient": 0.5 },
    { "type": "wind", "direction": [1.0, 0.0, 0.0], "strength": 4.0 }
  ]
}
```

| Force | Fields | Effect | Use case |
|---|---|---|---|
| `wind` | `direction: [x,y,z]`, `strength` | `velocity += direction * strength * dt` | Constant directional acceleration. Combine multiple entries for cross-winds. |
| `drag` | `coefficient` | `velocity *= max(0, 1 - coefficient * dt)` | Velocity damping (1/seconds). Small (0.1–0.5) = floaty / leafy; large (2+) = molasses. |

⚠️ **Order matters**: forces apply in array order, BEFORE gravity. Drag-first damps already-built velocity (heavier feel); wind-first lets the wind land at full strength before damping. Mix and match.

⚠️ **`direction` is NOT auto-normalised**: pass a unit vector if you want `strength` to be the actual acceleration magnitude. The validator allows non-unit directions intentionally so you can pre-bake magnitude into `direction` and leave `strength: 1.0` for parameter-driven setups.

⚠️ **`drag.coefficient` units**: 1/seconds. Velocity halves every `ln(2)/coefficient` seconds. So `0.5` → halve every 1.39s; `2.0` → halve every 0.35s.

⚠️ **Works for all PhysicsMesh systems** — sphere mode (1 particle per body) AND cube mode (cluster). Forces apply per-particle, so a cube cluster's 8 samples each get the same wind + drag → cluster drifts as a whole.
