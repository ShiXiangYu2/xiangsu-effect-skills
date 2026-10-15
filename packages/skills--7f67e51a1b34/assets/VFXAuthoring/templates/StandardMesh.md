<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# §3.2 — StandardMesh template guide

## §3.2 — StandardMesh template guide

### When to pick StandardMesh

- Effects whose particles are **per-particle instances of a real 3D mesh**, transformed by a per-particle TRS (translate / rotate / scale) plus tint.
- Use cases: confetti, debris, falling coins/leaves, fluttering objects, projectile swarms, candy/popcorn, any effect where the particle has a recognizable 3D silhouette and tumbles in 3D.
- DO NOT use for: camera-facing 2D quads (`StandardQuad`), skinned/animated meshes that play a clip (`StandardAnimatedMesh` — see §3.3), physics-driven instances (`PhysicsMesh` — §3.5). (Trails / ribbons / streaks: use velocity-aligned or elongated StandardQuad billboards — see `references/shader-theory.md`.)

### How it differs from StandardQuad (essential reading)

StandardMesh shares the same authoring framework as StandardQuad — same contract-style shader sections, same `init.comp` / `update.comp` / `output.*` layout, same `add_vfx_source` / `edit_vfx_source` workflow. **Read §3.1 first.** This section covers ONLY the differences.

| Aspect | StandardQuad | **StandardMesh** |
|---|---|---|
| Particle geometry | 4-vertex billboard quad emitted by engine | **Full user-supplied mesh** (engine draws it once per particle via instancing) |
| Per-particle SSBO stride | 12 uints | **32 uints** (TRS + color/alpha + spin) |
| Output ContextBlock type | `AMGQuadOutput` | **`AMGMeshOutput`** — requires a `mesh` resource bound |
| `gl_VertexID` in vert | indexes the 4 quad corners | **walks the user mesh's vertex buffer** |
| `gl_InstanceID` in vert | unused for particle slot decoding | **IS the particle slot** (`uint particleOffset = uint(gl_InstanceID)`) |
| Required resources | `Map0` | **`mesh` + `Map0`** — agent MUST import the mesh first. Optionally also `material` (an editor OMTL material — see "Optional: bind a real editor material" below) |

### Mandatory pre-step: get the mesh GUID

Before you call `add_vfx_source(template="StandardMesh")`, you need a mesh resource GUID in the project.

**FIRST, check what already exists.** If the user refers to a mesh/model they already imported or one in the scene, call **`list_resources`** to find it by name, then `inspect` it to get the GUID (for a `.fbx`/`.obj` Model, inspect to read its `Mesh` sub-asset GUID). **Do NOT re-import an asset the user already has** — re-importing duplicates it and the user's intended GUID won't match.

**Only if it's not in the project**, import one:
1. **Built-in mesh** — query an exact resource such as
   `query_knowledge(category="resource", resource_type="Sphere.mesh")` and use the
   returned GUID directly.
2. **Local source mesh** — `edit_by_dsl.import_resource({path:"..."})`.
3. **Generated mesh** — only if the current branch explicitly exposes a supported mesh-generation path and the user is asking for that flow.

If the current toolset does not expose generated-mesh sourcing, ask the user for a local mesh file or reuse an existing project asset.

### Optional: bind a real editor material (PBR / any .omtl)

By default the particles render with the template's generated **unlit** output (texture × tint).
If the user wants real shading (PBR lighting, emission, matcap, a material they authored), bind
an **editor material** to the system — ANY material the editor's material picker offers works
unchanged (hand-written `.omtl` or material-graph; same universality as VFX Graph's Set Mesh):

```jsonc
// in add_vfx_source:
"systems": [{ ...,
  "resources": { "mesh": {"ref": "mesh"}, "Map0": {"ref": "Map0"}, "material": {"ref": "mymat"} } }],
"shared_resources": { ...,
  "mymat": { "type": "Material", "guid": "<MATERIAL_GUID>" } }
// builtin material GUIDs: Unlit 00000000-0000-0000-0000-00000000000a,
//                         Standard PBR ...000b, Default ...000c
```

How it works: the importer keeps the material's WHOLE shader (its vertex + varyings + fragment)
and injects the per-particle attribute load + TRS re-transform into its `vertex()` — so all the
material's own varyings (e.g. PBR's IBL terms) are produced per particle. Notes:

- **No `material` resource ⇒ unlit output exactly as before** (fully backward compatible).
- **Lit materials need a light in the scene** (Standard PBR renders BLACK without one — add a
  `Directional Light` object before judging a "black particles" screenshot).
- The material's authored uniform values (colors/textures/floats) are seeded onto the output
  context automatically. `Map0` is ignored by the material path (the material's own textures
  apply); keep `Map0` for the unlit fallback.
- Output blend is VFXAlpha; the material's own blend/render-queue is not yet derived.
- The output stage's generated frag sections (`TEXTURE SAMPLE` / `LIGHTING` / `TINT`) do NOT
  apply when a material is bound — the material's fragment replaces them entirely. Per-particle
  color/alpha still reach material-graph materials via `vfx_data_0..4` (`VFXGRAPH` define).
- Swapping the material later: rewrite `shared_resources` (for example through `edit_by_dsl.edit_vfx_source({scope:"manifest", patch:{...}})`,
  patch:{shared_resources:{<name>:{type:"Material", guid}}}})`, or the editor inspector's Material
  picker) — the re-import recompiles the output.

### File layout (after `add_vfx_source` expands the template)

```
Assets/VFXSources/<YourEffect>.vfxsrc/
├── index.vfxsrc                       — manifest (single_system, system.template="StandardMesh")
│                                        manifest.shared_resources MUST declare "mesh" → user mesh GUID
├── controller/VFXController.js        — same per-frame spawn-rate controller as Quad
└── systems/main/
    ├── system.json                    — name / template="StandardMesh" / defines / uniforms /
    │                                    resources.mesh = {ref: "mesh"}, resources.Map0 = {ref: "Map0"}
    │                                    (+ optional resources.material = {ref: "<shared Material>"})
    └── shaders/
        ├── init.comp                  — particle spawn (POSITION / VELOCITY / ROTATION / SCALE /
        │                                COLOR / ALPHA / ANGULAR VELOCITY / LIFETIME INIT)
        ├── update.comp                — per-frame physics (FORCE COMPUTATION / ROTATION INTEGRATION /
        │                                INTEGRATE / WRITE BACK)
        ├── update_ssbo2image.comp     — SSBO → image2D for compat-mode GLES VS read (8 texels/particle)
        ├── output.gles.vert           — mesh-instanced expansion (SCALE/ALPHA/COLOR OVER LIFETIME,
        │                                POSITION COMPOSE, EMIT VARYINGS)
        ├── output.gles.frag           — color + alpha (TEXTURE SAMPLE / LIGHTING / TINT / FINAL OUTPUT)
        ├── output.metal.vert          — Metal mirror (importer doesn't compile; reference only)
        └── output.metal.frag          — same
```

### SSBO slot layout (PARTICLE_SIZE = 32 uints)

```
slot 0       alive            (uint, 1=alive 0=dead)
slot 1       age              (float bits)
slot 2       lifetime         (float bits)
slot 3-5     position         (vec3 local-space)
slot 6-8     velocity         (vec3, m/s local)
slot 9-12    rotation         (vec4 quaternion, (x,y,z,w) with w=real; KEEP NORMALIZED)
slot 13-15   scale            (vec3, defaults to the exposed SCALE uniform on init)
slot 16-18   color            (vec3, linear RGB in [0,1])
slot 19      alpha            (float, [0,1])
slot 20-22   angular_velocity (vec3, rad/s)
slot 23      seed             (uint — frozen per-particle for stable noise)
slot 24-31   FREE             ← agent can use for custom state (e.g. mesh variant index, age-trigger flags)
```

All shaders MUST agree on PARTICLE_SIZE = 32. The free slots are 24..31 (8 uints) — note that's a **different** free range from StandardQuad's 9..11.

### Defines (authoring tunables)

Every name in this table is a **runtime exposed parameter** (see `references/asset-inspector.md` §2–§3): you still author it in `defines`, but the value becomes the parameter's runtime DEFAULT — the asset panel's starting value, live-tunable by the user afterwards. None of them are compile-time constants.

| Name | Used in | Effect |
|---|---|---|
| `LIFETIME_MIN` / `LIFETIME_MAX` | init.comp | Random lifetime range (seconds). |
| `SPEED_MIN` / `SPEED_MAX` | init.comp | Random initial speed range (units/sec). |
| `GRAVITY` | update.comp | Per-second downward velocity change. Set to 0 for weightless effects, negative for buoyancy. |
| `SCALE` | init.comp | Uniform per-axis birth scale of the mesh instance (single-source; the vert passes the per-particle scale through unchanged). **There is NO `SCALE_START`/`SCALE_END` on this template** — for a scale-over-life taper, edit the vert's `SCALE OVER LIFETIME` section instead. |
| `SPIN` | init.comp | Base angular-velocity magnitude (rad/s) used by ANGULAR VELOCITY INIT. |
| `COLOR_R/G/B/A` | init.comp | Per-particle base tint (linear RGB + alpha); the panel groups them into one RGBA swatch. |

### Editable section contracts — what's new vs §3.1

The init / update / output shaders use the same contract-style section comments as StandardQuad. The new sections specific to StandardMesh:

#### init.comp — additional sections beyond Quad's

| Section | PURPOSE | MUST PRODUCE | CONSTRAINTS |
|---|---|---|---|
| `ROTATION INIT` | Initial orientation as a unit quaternion. | `rx, ry, rz, rw` — 4 floats forming a unit quaternion. Identity is (0,0,0,1). | MUST be unit length. Use `QuatFromAxisAngle(axis, angle)` (provided) or write the math inline. |
| `SCALE INIT` | Per-axis birth scale of the mesh instance. | `sx, sy, sz` (positive floats). | > 0 per component. Default is the exposed `SCALE` uniform on all three axes; the output vert passes the per-particle scale through unchanged (no lifecycle curve by default). |
| `COLOR INIT` | Per-particle tint in linear RGB. | `cr, cg, cb` ([0,1]). | Linear RGB. Convert from sRGB / hex on the agent side, not here. |
| `ALPHA INIT` | Per-particle alpha at birth. | `alpha0` ([0,1]). | Output vert may multiply by an age curve in ALPHA OVER LIFETIME. |
| `ANGULAR VELOCITY INIT` | Spin rate around local X/Y/Z. | `wx, wy, wz` (rad/sec). | Typical confetti: ±10 rad/s. Update.comp integrates rotation from this every frame. |

#### update.comp — additional sections beyond Quad's

| Section | PURPOSE | MUST PRODUCE | CONSTRAINTS |
|---|---|---|---|
| `ROTATION INTEGRATION` | Advance the quaternion by angular velocity. | Updated, normalized quaternion `q`. | Always renormalize at the end. Default small-angle Euler integration (`q += 0.5 * ω⊗q * dt; q = normalize(q)`) is correct for typical spin rates. |
| `COLOR / ALPHA / SCALE EVOLUTION` (optional) | Per-frame change to slots 13..19. | (writes to slot 13..19) | By default these slots stay at their init values. Touch only when you need dynamic per-frame change (e.g., color shifts on impact, scale-pulse on death). |

#### output.gles.vert — sections distinct from Quad

| Section | PURPOSE | MUST PRODUCE | CONSTRAINTS |
|---|---|---|---|
| `PARTICLE OFFSET DECODE` | Resolve `particleOffset` from `gl_InstanceID`. | `particleOffset` (uint). | **Don't edit.** This is THE key mesh-vs-quad difference. `particleOffset = uint(gl_InstanceID)` (NOT `gl_VertexID / 4 + ...` like the Quad path). The engine emits one instance per particle and walks the mesh's vertex buffer per instance. |
| `FETCH ATTRIBUTES` | Read this particle's state. | `alive, age, lifetime, position, velocity, rotation, scale, color, alpha`. | Maintain both `#ifdef VFX_COMPAT_MODE` branches if shipping cross-platform. 8 texels per particle in compat mode. |
| `SCALE OVER LIFETIME` | Modulate per-particle scale by age curve. | `finalScale` (vec3, > 0). | Default passes the SSBO scale through (`finalScale = scale`) — single-source from the exposed `SCALE`. Write an age curve here (e.g. `scale * mix(1.0, 0.2, t)`) for grow/shrink-over-life. Components must stay > 0 — collapsing to zero is rarely intended. |
| `ALPHA OVER LIFETIME` | Modulate per-particle alpha by age curve. | `finalAlpha` (float, [0,1]). | Any falloff. Default fades the last 30% of life. |
| `COLOR OVER LIFETIME` | Modulate per-particle color by age. | `finalColor` (vec3, linear RGB). | Pass through if no per-life color change. |
| `POSITION COMPOSE` | Combine per-particle TRS with the mesh vertex. | `worldPos` (vec3), `worldNormal` (vec3, unit). | Default is T * R * S * v (standard TRS). `R = QuatToMat3(rotation)` is provided. Mesh attributes are `attPosition` / `texcoord` / `normal` — the UV/normal names MUST match the engine vertex semantics (`texcoord`/`normal`), or they silently bind to nothing → garbage UV. |
| `EMIT VARYINGS` | Write `gl_Position` + vTex/v0/v1/v2/v_posWS/v_normalWS. | Above + `vTex = vec4(texcoord.x, texcoord.y, 0, 0)` — **NO V-flip** (unlike Quad). The mesh's own UV atlas maps directly; flipping `texcoord.y` mis-samples (faces/colours land on the wrong rows). | One varying NEW vs Quad: `v_normalWS` for the frag lighting term. |

#### output.gles.frag — sections distinct from Quad

A mesh is a SOLID surface: the frag is opaque + lit (sRGB-correct), depth-writing is on, and alpha is driven by the per-particle age-alpha only — NOT gated by the texture's alpha (that's a cut-out-sprite pattern that washes solid meshes out).

| Section | PURPOSE | MUST PRODUCE | CONSTRAINTS |
|---|---|---|---|
| `TEXTURE SAMPLE` | Sample `BaseTexture` (the mesh's diffuse; the `Map0` resource is bound to this sampler) at mesh UV. | `texColor` (vec4). | If your mesh has no UVs (default Cube etc.), `vTex.xy` may be constant — just set `texColor = vec4(1.0)`. |
| `LIGHTING` | Per-pixel diffuse term from `v_normalWS`. | `diffuse` (float). | Cheap fixed-direction half-lambert with a guard for zero normals. For real PBR, bind an optional `material` resource instead (see "Optional: bind a real editor material" — the material's fragment then replaces this whole frag). Skip (set `diffuse = 1.0`) for unlit FX (confetti glow, projectiles). |

The remaining sections (`TINT / COLOR MIX`, `ALPHA`, `FINAL OUTPUT`) follow the same contract as StandardQuad's frag.

### Authoring workflow — putting it together

```text
1. // Make sure the mesh resource exists in the project.
   // Use an existing project mesh when possible.
   // Otherwise import a local file through edit_by_dsl.import_resource(...) and capture the returned guid.

2. // Initialize the .vfxsrc with the StandardMesh template, wiring the mesh GUID into shared_resources.
   await edit_by_dsl({commands: [{
     command_type: "add_vfx_source",
     params: {
       name: "MyMeshEffect",
       manifest: {effect: "MyMeshEffect"},
       shared_resources: {
         mesh_res: {type: "Mesh", guid: "<MESH_GUID>"},
         tex_res: {type: "Texture", guid: "<WHITE_TEX_GUID_OR_USER_TEXTURE>"},
       },
       systems: [{
         name: "main",
         template: "StandardMesh",
         defines: { LIFETIME_MIN: 2.0, LIFETIME_MAX: 3.0, SPEED_MIN: 1.5, SPEED_MAX: 3.0,
                    GRAVITY: 5.0, SCALE: 1.0 },
         resources: { mesh: {ref: "mesh_res"}, Map0: {ref: "tex_res"} },
       }],
     },
   }]})

3. // Verify the default renders SOMETHING (cube tumbling under gravity etc.).
   interact_by_dsl.screenshot()

4. // Iterate per file: take read_path from files[] → Read → edit_vfx_source.
   //   init.comp        → POSITION/VELOCITY/ROTATION/SCALE/COLOR/ALPHA/...
   //   update.comp      → FORCE COMPUTATION / ROTATION INTEGRATION / ...
   //   output.gles.vert → SCALE/ALPHA/COLOR OVER LIFETIME, POSITION COMPOSE
   //   output.gles.frag → TEXTURE SAMPLE / LIGHTING / TINT / FINAL OUTPUT
   // read_path comes from the add_vfx_source return's files[], or
   // inspect(vfx_guid).vfx_workspace.files[] for an existing bundle.
   Read(read_path)                              // native tool
   ...write GLSL satisfying the section contract...
   // write back through edit_by_dsl
   await edit_by_dsl({commands: [
     {command_type: "edit_vfx_source", params: { vfx_name, path: read_path, content }},
   ]})

5. // After every edit_by_dsl.edit_vfx_source(...): re-bind the VisualEffect component (see §"edit_vfx_source — REQUIRED post-edit re-bind step")
6. verify with interact_by_dsl (typically wait + screenshot)
```

### Starter recipe — minimal StandardMesh effect (copy-paste, then adjust)

> **Built-in default available:** you can build a StandardMesh effect that renders in any
> project with **no external imports** by using the built-in VFX Heart mesh
> (`00000000-...-1002`) + Heart texture (`00000000-...-1001`): call `add_vfx_source`
> (template `StandardMesh`) with those built-in Heart GUIDs as `shared_resources`, then bind
> the returned guid to a VisualEffect component (host on an `"Empty Object"`, not `"Empty"`).
> The recipe below shows the more general path — `add_vfx_source` with arbitrary
> mesh + texture sources.

The right "default" for arbitrary user content is this recipe: it produces a complete working mesh particle effect in any project, against any user-supplied mesh.

This sequence is the canonical first-time mesh particle effect. Run it after the user names a mesh source (`.fbx` from disk or an existing project asset):

```typescript
// Step 1 — get a Mesh GUID. One of these sources, depending on the branch:
//   A) Local file:  use edit_by_dsl.import_resource({path: '/Users/.../cardboard_dino.fbx'})
//   B) Existing project asset: list_resources / inspect
// The result has `guid` — capture it (e.g. '4a3f...').

// Step 2 — call add_vfx_source. This produces a complete V4 .vfxsrc bundle and registers
// the corresponding VisualEffectAsset GUID for binding.
await edit_by_dsl({commands: [{
  command_type: 'add_vfx_source',
  params: {
    name: 'DinoBurst',
    manifest: {effect: 'DinoBurst'},
    shared_resources: {
      dino_mesh: {type: 'Mesh',    guid: '<MESH_GUID_FROM_STEP_1>'},
      white_tex: {type: 'Texture', guid: '00000000-0000-0000-0000-000000001543'}, // built-in white
    },
    systems: [{
      name: 'main',
      template: 'StandardMesh',
      defines: {
        LIFETIME_MIN: 2.5, LIFETIME_MAX: 3.5,
        SPEED_MIN:    2.0, SPEED_MAX:    4.0,
        GRAVITY:      5.0,
        SCALE:        0.8,                  // visible without filling the screen
      },
      uniforms: {
        init: [{name: 'capacity', type: 'Int', value: 200}],
      },
      resources: {
        mesh: {ref: 'dino_mesh'},
        Map0: {ref: 'white_tex'},
      },
    }],
  },
}]})
// Returns { guid: '<vfxprofile_guid>', source_asset_path: 'Assets/VFXSources/DinoBurst.vfxsrc' }.
// Import or shader compile failures are returned as command errors.

// Step 3 — bind to a SceneObject. Render-time:
await edit_by_dsl({commands: [
  {command_type: 'add_scene_object', params: {type: 'Transform', name: 'DinoBurst'}, alias: 'obj'},
  {command_type: 'add_component', params: {scene_object: {$ref: 'obj'}, type: 'VFXEffectBlock'}, alias: 'fx'},
  {command_type: 'set_component', params: {
    guid: {$ref: 'fx'},
    properties: {vfxProfile: {guid: '<vfxprofile_guid_from_step_2>'}},
  }},
]})

// Step 4 — screenshot to verify. Dinosaurs should spawn at origin, spread out, fall under gravity, fade in last 30% of life.
await interact_by_dsl({commands: [
  {command_type: 'wait', params: {ms: 500}},
  {command_type: 'screenshot'},
]})
```

If steps 1-3 succeed but step 4 shows nothing visible, check each of these in order:
- Step 2 completed without a command error or `_compile_check` error?
- The mesh has visible bounding box at origin? `inspect` the mesh resource to check
- Capacity > 0 and spawn rate > 0? Check `system.json.uniforms`
- Camera positioned to see the origin? Default Camera at `(0, 0, 40)` looking at `-Z` works

### Common StandardMesh pitfalls

- **Forgetting to import the mesh first.** Without a mesh GUID in `manifest.shared_resources.mesh`, the importer throws "StandardMesh system missing required resource 'mesh'". Always import or reuse an existing project mesh GUID, then wire it into `resources.mesh` at `add_vfx_source` time. (Exception: if you use a built-in VFX mesh GUID like `00000000-...-1002` for Heart, no import step needed — they ship as built-ins.)
- **Mesh GUID resolves to APJS.Model not Mesh.** `.fbx` / `.obj` imports return an `APJS.Model` container, not a raw `APJS.Mesh`. The importer handles this automatically — when the resource is a Model, it picks one of the model's sub-meshes (clone + register as an independent runtime artifact). **For multi-sub-mesh Models** (e.g. a character .fbx with `body` + `helmet`): pass `shared_resources.<key>.submesh: "<name>"` to pick a specific named sub-mesh. The name is the source node name from the .fbx (e.g. "alien" / "helmet"). Without `submesh`, the importer falls back to largest-by-vertex-count (works for "I want the body, not the prop"). Example:
  ```ts
  shared_resources: {
    body_mesh:   {type: 'Mesh', guid: '<model_guid>', submesh: 'alien'},
    helmet_mesh: {type: 'Mesh', guid: '<model_guid>', submesh: 'helmet'},
  }
  ```
  If your guessed name doesn't match a real sub-mesh, the engine logs a warning with the available names and falls back to largest-by-verts. So a wrong `submesh` value never crashes — at worst it picks the wrong piece.
- **Old `add_builtin_object` host examples are stale on this branch.** Prefer a plain `Transform` host created through `add_scene_object`, then add the engine component `VFXEffectBlock` with `add_component`. `VisualEffect` is the APJS class name, not the DSL component type.
- **Mesh has no normals or UVs.** Library meshes vary. If your mesh is stripped, the `LIGHTING` section's `diffuse` term degenerates (the template guards `length(v_normalWS) < 0.01` and skips lighting) and the `TEXTURE SAMPLE` may sample garbage UVs — set `texColor = vec4(1.0)` and rely on `v0.rgb` tint.
- **Particles invisible after edit.** Common causes: (a) `scale` slot read but never written in init.comp → init writes garbage → output.vert collapses to zero. Check the WRITE BACK block includes slot 13..15. (b) `alpha0 = 0` left over from a paste — set explicitly. (c) rotation quat denormalized — output's `QuatToMat3` produces a degenerate basis; ensure init's ROTATION INIT produces unit length.
- **Spin too fast / Strobe.** `angular_velocity` is in rad/sec. A value of 60 rad/s is ~10 rev/s — at 60fps each frame rotates ~1 rad which can alias visually. Stay under ±15 rad/s for readable motion.
- **Tried to read `gl_VertexID / 4 + gl_InstanceID * 2048` (Quad pattern).** Wrong for mesh — the mesh has a real vertex buffer indexed by `gl_VertexID`. Read your particle slot from `gl_InstanceID` only.
- **Used 12-uint Quad slot indices** (e.g., wrote position to slots 1..3). Wrong for mesh — position lives at slots 3..5 in the 32-uint layout. Use the table above.
- **Set `capacity` too high.** Mesh draw cost scales with mesh vertex count × particle count. A 1000-vertex mesh at capacity=2000 is ~2M vertex shader invocations per frame. Start at capacity=200..512 and ramp up only after verifying performance.

### Iteration loop pattern

For most effects you'll do:

```text
1. edit_by_dsl.add_vfx_source({...})                                        // initial bundle
2. interact_by_dsl.screenshot()                                             // verify it renders at all
3. Read(read_path from files[] / inspect.vfx_workspace)                     // read the section you'll modify
4. (write GLSL that fulfills the section contract AND the user's prompt)
5. edit_by_dsl.edit_vfx_source({...})                                       // submit
6. edit_by_dsl.set_component({...})                                         // re-bind
7. interact_by_dsl.screenshot()
8. ...repeat until the user's intent is satisfied.
```

Don't try to discover the right effect by trial and error on `defines`. Read the user's prompt, decide what each editable section needs to produce, write GLSL that produces it.

Always re-issue `set_component` through `edit_by_dsl` after every `edit_vfx_source` so `VisualEffect.vfxProfile` re-binds to the same GUID. See "edit_vfx_source — REQUIRED post-edit re-bind step" below.

### Pitfalls and gotchas

- **Forgetting Map0** → bundle fails validation with `MISSING_REQUIRED_RESOURCE`. Always include a Texture resource ref.
- **Mismatched PARTICLE_SIZE** → SSBO indexing collapses. Don't change the `#define PARTICLE_SIZE 32u` in any shader (StandardMesh's stride is 32 uints, not Quad's 12).
- **AUSL silently rejects `#define KEY VAL`** lines. To add new constants, put them in `system.json:defines` (importer does whole-identifier substitution pre-AUSL).
- **Editing custom logic into vert/frag means COMPAT_MODE branch needs the same change**. Most agents skip COMPAT and just edit the non-COMPAT (#else) branch — that's fine for dev preview; production export does need both.
- **Setting `LIFETIME_MIN == LIFETIME_MAX`** is the recommended way to get uniform lifetime (no `Set Lifetime (Constant)` needed).
- **The default texture GUID `00000000-0000-0000-0000-000000001543`** is the built-in white texture. Use it when you want the procedural soft-circle to be the visible shape (e.g. dots, glow particles). For sprite-driven shapes (fire flame, star), bind an actual texture and switch the frag shader's Shape variant.
