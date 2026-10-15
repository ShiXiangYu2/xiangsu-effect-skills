<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# §2 — Multi-system event chains

## §2 — Multi-system event chains

A V4 bundle can declare **multiple systems** in one `.vfxsrc`, and any system can spawn into another via an `event`. Use this when one particle's *death* (or *each frame*, or *every N seconds*) should create new particles in a different system — fireworks, explosions with debris, rain → splashes, trails behind projectiles.

### Mental model

```
┌─ system A: rocket ─────────┐    on_die emits N particle offsets    ┌─ system B: shell ──────────┐
│  spawn → init → update ────┼───►  eventListOut0_buf (atomic queue) │  AMGSpawnerGPU → init → ...│
│  events: [{on_die→shell}]  │                                        │  source_position read in   │
└────────────────────────────┘                                        │  init.comp inherit prelude │
                                                                       └────────────────────────────┘
```

The engine wires the cross-system SSBO automatically based on three ContextBlock fields (`type=AMGSpawnerGPU` on target.spawn, `inCtxID` pointing at source.update, `siblingCtxID` picking the event slot). You do not manage GPU buffers — just declare `events` in the manifest and the importer wires it.

### Event schema

```json
{
  "id": "burst",
  "spawn_into": "shell",
  "trigger": {"kind": "on_die" | "always" | "rate" | "custom", ...},
  "inherit": ["position", "velocity"],
  "max_per_particle_per_frame": 32
}
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | GLSL-safe identifier, unique within the source system. Cannot be a GLSL keyword (`vec3`, `if`, etc.) or reserved name (`eventCount`, `source`, `particleOffset`). |
| `spawn_into` | yes | Name of the target system. Must exist; cannot self-loop; cannot create a cycle. |
| `trigger.kind` | yes | One of `on_die / always / rate / custom`. |
| `inherit` | no | Array of source-template attribute names (e.g. `["position"]`). Target's init.comp gets `source_<attr>` variables auto-declared at the `__EVENT_INHERIT_PRELUDE__` marker. Names must exist on the SOURCE template's `attribute_layout`. **Listing an attribute also auto-wires the matching INIT default**: `inherit:["position"]` rewrites POSITION INIT's `float px = 0.0; ...` to `float px = source_position.x; ...`; `inherit:["velocity"]` rewrites VELOCITY INIT similarly. You can still override the block (e.g., `source_position.x + (Rand-0.5)*0.3` for jitter) — the rewrite only fires on the unmodified canonical default. Other inherited attributes (age, lifetime, custom slots) provide `source_<attr>` but you write the assignment yourself. |
| `max_per_particle_per_frame` | depends | See default table below. |

### ⚠️ Event-target systems STILL SELF-SPAWN unless you suppress it (live-verified gotcha)

A system that should ONLY receive event spawns (a burst/trail/splash target) must
have its own spawner silenced — and **you cannot silence it with `spawnRate: 0`**:
the importer treats `spawnRateMin == 0 && spawnRateMax == 0` as "author didn't
supply spawn uniforms" and installs the DEFAULT spawner (~2/s). Those parasitic
particles are born at the target's POSITION INIT default — the **origin, i.e. the
centre of the screen** — producing a mystery emitter that constantly leaks
particles mid-frame (with a `shared_pool_with` glow layer they show up as big
blurry blobs). Verified live on a rocket→burst chain.

**The fix — epsilon spawn uniforms** (bypasses the 0/0 fallback, emits ~never):

```json
"uniforms": {"spawn": [
  {"name": "spawnRateMin", "type": "Float", "value": 0.0},
  {"name": "spawnRateMax", "type": "Float", "value": 0.000001},
  {"name": "delayMin", "type": "Float", "value": 9999.0},
  {"name": "delayMax", "type": "Float", "value": 9999.0},
  {"name": "originalSpawnRate", "type": "Float", "value": 0.0}
]}
```

Put this on EVERY system that must not self-spawn — that means BOTH:
1. **pure event-target systems** (burst/trail/splash receivers), AND
2. **every `shared_pool_with` render-layer system** (glow/halo passes). The
   importer builds a spawner for shared systems too, and a shared system almost
   never carries spawn uniforms — so it ALWAYS gets the parasitic default. This
   was isolated live with a red-core + blue-halo repro: core(epsilon) stayed
   silent, the halo leaked a blue blob at the origin until it got the same
   epsilon uniforms.

Mechanism note: the bundle controller drives the engine spawner from
`originalSpawnRate` each frame and SKIPS the write when it is 0 — the engine
then keeps whatever the import installed, which for missing/0-0 spawn uniforms
is the ~2/s default. The epsilon values above survive import (max ≠ 0 bypasses
the fallback) and emit effectively never.

Symptom checklist: "extra particles always appearing at screen centre" / "a
blurry second emitter I never authored" / "a soft blob parked at the origin
behind my effect" ⇒ this gotcha. Verify the fix with a control run: silence the
real emitters too — the screen must go COMPLETELY empty (make sure the preview
is actually alive: consecutive frames must differ).

### Trigger kinds

| Kind | Shape | When it fires |
|---|---|---|
| `on_die` | `{kind:"on_die", count:N}` or `{count:{min,max}}` | Once when source particle's lifetime expires. Emits `count` target particles. |
| `always` | `{kind:"always", count:N}` | Every frame for every alive source particle. Emits `count` target particles per source per frame. |
| `rate` (OverTime) | `{kind:"rate", mode:"OverTime", rate:R}` | Accumulates `R * dt` per frame; emits when accumulator crosses an integer. Continuous emission. |
| `rate` (OverDistance) | `{kind:"rate", mode:"OverDistance", rate:R}` | Same but accumulator = `R * speed * dt`. Distance-bound. |
| `custom` | `{kind:"custom"}` | Agent writes their own trigger condition into update.comp via `edit_vfx_source` (assign `eventCount = ...` inside the `__EVENT_TRIGGER_INJECT__` block). |

### `max_per_particle_per_frame` — when required, when defaulted

This caps the event buffer size; overflow particles are **silently dropped** by the atomic-counter (same as V3).

| Trigger | Required? | Default if omitted |
|---|---|---|
| `on_die` | no | `count` value |
| `always` | no | `count` value |
| `rate / OverTime` | no | `ceil(rate * 0.1)` (worst-case 100ms frame) |
| `rate / OverDistance` | **yes** | — (distance per frame is unbounded; specify) |
| `custom` | **yes** | — (cannot infer from trigger metadata) |

### Trail / tail / residue visibility ladder — sub-particle dimensioning

A continuous-emission event chain (`rate OverTime` or `always` from a source system into a sub-particle target) is the universal way to express "this particle leaves something behind it" — a trail, tail, contrail, motion path, decay residue, after-image. The chain wires the *topology* correctly; whether it reads as a **visible** trail at preview time depends on four independent dimensions, each tunable on the target system.

Wire the topology first (events + inherit position). Then iterate these four knobs to match the visual idea in the prompt. A wired-but-invisible trail is the most common event-chain authoring failure — the agent declares the event chain and stops, but the target system's defaults make the residue too small / too sparse / too fast-fading to register as a "trail" to a viewer.

| Visual dimension | Knob | Calibration rule |
|---|---|---|
| **Continuity** — does the trail read as a connected line, or scattered dots? | trigger rate × sub-particle lifetime → number of trail particles alive per parent at any moment | For a continuous-line read: aim for `rate × lifetime ≥ 40` alive per parent. Below `~15` it reads as dotted/discrete. |
| **Prominence** — can you see the trail at all next to the parent particle? | sub-particle's `SIZE_END` (= newborn size; see naming note in §3.1) relative to the parent's average rendered size | At least `0.4 × parent_size`. If parent shrinks (`SIZE_END > SIZE_START`), compare to parent's *average* over its lifetime, not start. |
| **Decay shape** — does the trail look like motion ("freshly laid then fading") or like noise ("uniformly dim")? | sub-particle's `SIZE_START` (= dying size) and the `ALPHA` block in its `output.gles.vert` | Two contrasts work: (a) `SIZE_END / SIZE_START ≥ 3` so trail tapers; (b) ALPHA has a bright plateau for the first 20-40% of life, then fades. Linear `1.0 - t` looks washed; `clamp(1.6 * (1.0 - smoothstep(0.20, 1.0, t)), 0.0, 1.0)` reads as "fresh sparks fade". |
| **Anchoring** — does the trail mark the parent's *past* path or move *with* the parent? | sub-particle's VELOCITY INIT — zero / micro-random for a true residue trail, or scaled copy of `source_velocity` for a drag-tail | True residue ("frozen smoke trail behind a rocket"): `vx = (Rand-0.5)*0.05` micro-jitter only. Drag-tail ("comet tail dragging behind"): `inherit:["velocity"]` (auto-wires) then scale, e.g. `vx = source_velocity.x * 0.3`. Mixing both — small inherited velocity + slow gravity — gives "ember sparks settling". |

Worked example (`shell → spark` in a fireworks-style chain, sub-particle of an exploded shell):
```json
// shell.events
{"id": "tail", "spawn_into": "spark",
 "trigger": {"kind": "rate", "mode": "OverTime", "rate": 120},
 "inherit": ["position"]}
```
Spark system: `LIFETIME 0.4–0.6`, `SIZE_END = 0.55 × shell_SIZE_END`, `SIZE_START = 0`, velocity micro-jitter only. With shell capacity = 40 and these knobs: `120 × 0.5 × 40 = 2400` spark particles alive at burst peak, each tapering from ~half shell size to nothing over 0.5s — reads as a visible spoke radiating from each shell particle. (Verify spark capacity ≥ this.)

This ladder applies to any sub-particle chain whose role is "visual record of the parent's motion": rocket trails behind a launching shell, contrails behind a missile, glow residues from a moving sword, smoke from a thrown grenade. Don't memorize the specific shell-firework numbers — derive your own from the four dimensions.

### 5 worked recipes

#### 1. Fireworks: rocket → shell → spark + independent dust

```json
{
  "systems": [
    {
      "name": "rocket", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.4, "SIZE_END": 0.2, "LIFETIME_MIN": 1.5, "LIFETIME_MAX": 2.5, "SPEED_MIN": 3, "SPEED_MAX": 6, "GRAVITY": 5},
      "resources": {"Map0": {"ref": "tex"}},
      "events": [{"id": "burst", "spawn_into": "shell", "trigger": {"kind": "on_die", "count": 12}, "inherit": ["position"]}]
    },
    {
      "name": "shell", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.3, "SIZE_END": 0.1, "LIFETIME_MIN": 0.8, "LIFETIME_MAX": 1.4, "SPEED_MIN": 4, "SPEED_MAX": 8, "GRAVITY": 3},
      "resources": {"Map0": {"ref": "tex"}},
      "uniforms": {"spawn": [
        {"name": "spawnRateMin", "type": "Float", "value": 0.0},
        {"name": "spawnRateMax", "type": "Float", "value": 0.000001},
        {"name": "delayMin", "type": "Float", "value": 9999.0},
        {"name": "delayMax", "type": "Float", "value": 9999.0},
        {"name": "originalSpawnRate", "type": "Float", "value": 0.0}
      ]},
      "events": [{"id": "sparks", "spawn_into": "spark", "trigger": {"kind": "on_die", "count": 6}, "inherit": ["position", "velocity"]}]
    },
    {
      "name": "spark", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.1, "SIZE_END": 0.0, "LIFETIME_MIN": 0.3, "LIFETIME_MAX": 0.6, "SPEED_MIN": 1, "SPEED_MAX": 3, "GRAVITY": 1.5},
      "resources": {"Map0": {"ref": "tex"}},
      "uniforms": {"spawn": [
        {"name": "spawnRateMin", "type": "Float", "value": 0.0},
        {"name": "spawnRateMax", "type": "Float", "value": 0.000001},
        {"name": "delayMin", "type": "Float", "value": 9999.0},
        {"name": "delayMax", "type": "Float", "value": 9999.0},
        {"name": "originalSpawnRate", "type": "Float", "value": 0.0}
      ]}
    },
    {
      "name": "dust", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.5, "SIZE_END": 0.0, "LIFETIME_MIN": 3, "LIFETIME_MAX": 5, "SPEED_MIN": 0.5, "SPEED_MAX": 1.5, "GRAVITY": 0},
      "resources": {"Map0": {"ref": "tex"}}
    }
  ]
}
```

Notes:
- `shell` and `spark` are pure event targets → they carry the **epsilon spawn uniforms** (see the self-spawn gotcha above); without them each would leak ~2 parasitic particles/sec at the screen centre.
- `dust` has no `events` and no system targets it → independent system, zero event-chain overhead. It deliberately has NO spawn uniforms, so it gets the importer's default ~2/s ambient spawner — that's its intended emission.
- `shell` is both source AND target — chain middle nodes get both trigger code (in update.comp) and inherit prelude (in init.comp).
- `inherit: ["position"]` on rocket → shell **auto-wires** shell's POSITION INIT default to `float px = source_position.x; ...` (and analogously for `velocity`). You don't need a separate `edit_vfx_source` to wire inheritance for these two attributes — declaring `inherit` is enough. Override POSITION INIT if you want an offset (e.g., `source_position + jitter`). Other inherited attrs (age / lifetime / custom slots) only get the `source_<attr>` variable; you assign it manually.

#### 2. Continuous emission via `rate / OverTime`

A trail that emits N particles per second along a moving emitter:

```json
{
  "name": "emitter", "template": "StandardQuad",
  "events": [{"id": "trail", "spawn_into": "smoke",
    "trigger": {"kind": "rate", "mode": "OverTime", "rate": 60}, "inherit": ["position"]}]
}
```

`rate: 60` = 60 particles/second. Default `max_per_particle_per_frame` = `ceil(60 * 0.1) = 6` (worst 100ms frame). Override if your emitter has bursts.

#### 3. Distance-based emission

Tire/skid marks emit per unit traveled, not per second:

```json
{
  "name": "wheel", "template": "StandardQuad",
  "events": [{"id": "skid", "spawn_into": "smoke",
    "trigger": {"kind": "rate", "mode": "OverDistance", "rate": 4},
    "max_per_particle_per_frame": 8,
    "inherit": ["position"]}]
}
```

`rate: 4` = 4 particles per world-space unit traveled. **`max_per_particle_per_frame` is required** because the engine can't bound how far a particle moves per frame.

#### 4. Custom trigger (agent-written condition)

When `on_die / rate / always` don't fit — e.g., "emit a spark every time velocity y crosses zero". Declare the event with `kind: "custom"` + required budget, then `edit_vfx_source` to fill the trigger zone:

```json
{
  "events": [{"id": "bounce", "spawn_into": "spark",
    "trigger": {"kind": "custom"},
    "max_per_particle_per_frame": 4,
    "inherit": ["position"]}]
}
```

Then `edit_vfx_source(scope="system:src:shader:update.comp", content=...)` and inside the `__EVENT_TRIGGER_INJECT__` block, the auto-generated `__CUSTOM_TRIGGER_BODY__` line is your slot — replace it with your condition that assigns `eventCount`:

```glsl
// Inside __EVENT_TRIGGER_INJECT_START__ ... block
{
    // event[0] custom — emit on velocity-y zero crossing
    float prevVy = uintBitsToFloat(attributeBuffer_buf[base + 25u]);
    eventCount = (sign(prevVy) != sign(vy)) ? 1u : 0u;
    attributeBuffer_buf[base + 25u] = floatBitsToUint(vy);

    // (atomic append loop — generated, do not edit)
    ...
}
```

#### 5. Rain → splash with inherit position

```json
{
  "systems": [
    {
      "name": "drops", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.05, "SIZE_END": 0.02, "LIFETIME_MIN": 1, "LIFETIME_MAX": 2, "SPEED_MIN": 8, "SPEED_MAX": 12, "GRAVITY": 25},
      "resources": {"Map0": {"ref": "tex"}},
      "events": [{"id": "splash", "spawn_into": "ripple",
        "trigger": {"kind": "on_die", "count": 1}, "inherit": ["position"]}]
    },
    {
      "name": "ripple", "template": "StandardQuad",
      "defines": {"SIZE_START": 0.1, "SIZE_END": 0.6, "LIFETIME_MIN": 0.4, "LIFETIME_MAX": 0.6, "SPEED_MIN": 0, "SPEED_MAX": 0, "GRAVITY": 0},
      "resources": {"Map0": {"ref": "tex"}}
    }
  ]
}
```

The ripple system inherits the drop's death position so the ring appears exactly where the drop hit. Drop lifetime = travel time; on_die = impact.

### Validator errors

| Error code | Meaning | Recovery |
|---|---|---|
| `EVENT_CYCLE_DETECTED` | a → b → ... → a | Remove the back-edge. Cycles would spawn forever. |
| `UNKNOWN_TARGET_SYSTEM` | `spawn_into` names a system not in `systems[]` | Typo in `spawn_into` — match it to an existing system name. |
| `UNKNOWN_INHERIT_ATTR` | `inherit` attribute not in source template's `attribute_layout` | Valid attribute names (StandardQuad: `alive/position/velocity/age/lifetime`; StandardMesh: `alive/age/lifetime/position/velocity/rotation/scale/color/alpha/angular_velocity/seed`). |
| `MULTIPLE_SOURCES_NOT_SUPPORTED_IN_PHASE_D_MVP` | Two source systems' events both target the same destination | N-to-1 merging is not supported. Workaround: declare N separate target systems, one per source. |
| `EVENT_TARGET_TEMPLATE_FORBIDDEN` | Target uses `PhysicsMesh` / `StandardAnimatedMesh` | Those templates can't receive events. Use StandardQuad or StandardMesh as the target. |
| `DUPLICATE_EVENT_ID` | Two events with same `id` in the same source | Pick distinct ids — event ids become part of shader variable names. |
| `RESERVED_EVENT_ID` | `id` is a GLSL keyword or reserved name | Rename. Avoid: `vec3`, `if`, `eventCount`, `source`, `particleOffset`, etc. |
| `MISSING_MAX_PER_PARTICLE_PER_FRAME` | `rate/OverDistance` or `custom` trigger without `max_per_particle_per_frame` | Add the field — pick the largest plausible per-frame emission count. |

### Multi-output: render one pool with two skins (`shared_pool_with`)

To render the SAME particle pool with two different materials/sizes (e.g. a bright
sprite + a big soft glow halo behind it, or two blend passes), add a second system
with `shared_pool_with: "<source system name>"`. That system owns NO pool — it
contributes only an output that re-renders the source's particles with its own
shader/defines. Constraints: it must use the **same template** as the source
(identical particle layout), declare **no events**, and the source must be a real
pool (no chaining). V1 supports **StandardQuad** only. Example:

```json
"systems": [
  {"name": "core", "template": "StandardQuad", "defines": {"SIZE_START": 0.3, "SIZE_END": 0.3, ...},
   "resources": {"Map0": {"ref": "tex"}}, "uniforms": {"init": [{"name": "capacity", "type": "Int", "value": 64}], "spawn": [...]}},
  {"name": "glow", "template": "StandardQuad", "shared_pool_with": "core",
   "defines": {"SIZE_START": 1.4, "SIZE_END": 1.4, ...}, "resources": {"Map0": {"ref": "tex"}}}
]
```

The shared system inherits the source's `capacity` automatically; it needs no
init uniforms. **But it DOES need the epsilon spawn uniforms** (see the
self-spawn gotcha above) — without them the importer's default spawner leaks
~2 parasitic particles/sec at the origin through the shared layer (the classic
"blurry blob parked at screen centre"). Render order = the shared output draws
after the source's own.

### Things events do NOT do (current scope)

- **Multi-output for Mesh/Physics** — `shared_pool_with` currently supports StandardQuad only; cross-template pools (e.g. trail+sprite) are not supported.
- **N-to-1 source merging** — see error D5-4 above.
- **PhysicsMesh / AnimatedMesh as event targets** — not currently supported (use StandardQuad/StandardMesh).
- **Cross-bundle events** — events are within ONE `.vfxsrc`. Multi-bundle composition is not supported.
