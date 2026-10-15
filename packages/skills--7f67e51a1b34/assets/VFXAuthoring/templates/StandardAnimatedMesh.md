<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow, DSL, scope grammar, and the §-anchor → file legend. -->

# §3.3 — StandardAnimatedMesh template guide

## §3.3 — StandardAnimatedMesh template guide

### When to pick StandardAnimatedMesh

- **The defining property: each particle is a SKINNED mesh that PLAYS A BAKED ANIMATION CLIP** (the mesh's own vertices deform over time), in addition to moving as a particle. Pick this whenever the per-particle mesh must animate its own geometry — for ANY rigged/skinned asset, not any specific subject. Walking/flying creatures, a waving flag, a beating heart, a deforming/morphing prop, a character doing an action — all the same mechanism. Don't restrict it to "flocks" or to any named creature; the subject is just whatever mesh the user supplies.
- If the mesh should NOT deform (rigid instances that only translate/rotate/scale), use `StandardMesh` (§3.2) — it's cheaper and needs no animation clip.
- DO NOT use for: static (non-animated) meshes (`StandardMesh` — §3.2), camera-facing quads (`StandardQuad` — §3.1), physics (`PhysicsMesh` — §3.5).

### The one mechanism that differs from StandardMesh — VAT

**Read §3.2 first.** StandardAnimatedMesh shares the ENTIRE StandardMesh framework — same 32-uint SSBO layout, same `init.comp` / `update.comp`, same `AMGMeshOutput` rendering, same TRS + tint. The movement / spawn placement / per-particle orientation you author in `init.comp` + `update.comp` is **identical to StandardMesh** — that is where the particles' trajectories live, authored from the user's prompt exactly as for any mesh particle.

The ONLY new thing is the **VAT (Vertex Animation Texture)**: at `add_vfx_source` time the importer bakes the `(mesh, animation)` pair into a texture storing every vertex's position at every frame, binds it to the `u_positionTexture` sampler, and rewrites the `VAT_VERTEX_COUNT / VAT_FRAME_COUNT / VAT_TEXTURE_SIZE` defines. At render time `output.gles.vert`'s **VAT SAMPLE** section maps each particle's `age` → a playback frame and samples the animated vertex. **You do not manage the texture, the bake, or those three defines** — declare the `animation` resource and they happen.

So the mental split: **particle system = where each instance GOES (init/update, like StandardMesh); VAT = what each instance's mesh DOES (its baked clip).** They are independent — a particle's `age` drives both its movement and its animation phase.

### Required resources (one more than StandardMesh)

| Resource | Notes |
|---|---|
| `mesh` | The **skinned** mesh GUID (must have a skin/skeleton). |
| `material` *(optional)* | An editor OMTL material GUID — same semantics as StandardMesh §3.2 "Optional: bind a real editor material": the material's whole shader drives the look (PBR/lit needs a scene light), the VAT displacement is injected into its vertex so the baked animation still plays. Playback uses the defaults (30fps loop). No material ⇒ unlit template output. |
| `animation` | The animation clip GUID to bake. The mesh must belong to this animation's model — the importer resolves model→mesh and errors clearly (`AnimatedMesh: mesh ... does not belong to ... animation`) if they don't match. |
| `Map0` | Fragment-shader texture (the mesh's albedo). White builtin texture if unused. |

**Finding the mesh + animation GUIDs — check what already exists FIRST:**
- **If the user refers to a mesh/model already in the project** (e.g. "use the dragon I imported", or one visible in the scene): call **`list_resources`** to list project resources and find it by name, then `inspect` that Model's GUID to read its sub-asset GUIDs (the `Mesh` sub-asset and the `Animation` sub-asset). **Do NOT re-import it** — the user already has it; re-importing creates a duplicate and the GUIDs the user means won't match.
- **Only if it's not in the project**, import it through `edit_by_dsl` with command_type `import_resource` using a local rigged `.fbx` (or another supported asset-source path on the current branch). A rigged model imports as a `Model` whose sub-assets include the skinned `Mesh` and the `Animation` clip — `inspect` the Model GUID to capture both.

### Runtime (agent-tunable playback)

`system.runtime`:
- `vat_fps` (default 30) — bake/playback frame rate. Lower = slower wingbeat / fewer baked frames.
- `play_mode` — `"loop"` (0) | `"pingpong"` (1) | `"once"` (2). Maps to the `playMode` branch in the VAT SAMPLE section.

### The VAT SAMPLE editable section (output.gles.vert)

This is the AnimatedMesh-specific knob. It produces `vatPosition` (the animated vertex) which then flows through the same POSITION COMPOSE as StandardMesh.

| What you can change | How |
|---|---|
| Playback speed | `VAT_FPS` local (default 30). |
| Loop behavior | `playMode` local: 0 loop / 1 pingpong / 2 once-and-hold. For a clip that plays once when the particle spawns and then freezes, set `playMode = 2u`. |
| Per-particle animation offset (so instances aren't all on the same frame) | Offset `age` by a per-particle seed before the frame mapping — e.g. read the `seed` slot and add a phase, so each instance's clip is out of sync. |

**Do not edit** the texel-index math (`pixelIndex = frame * VAT_VERTEX_COUNT + gl_VertexID` unpacked into the square VAT) — it mirrors the importer's bake layout.

### Worked example — call shape (NOT a recipe to copy, NOT subject-specific)

```typescript
// 1. Get the mesh + animation GUIDs. FIRST check if they already exist
//    (list_resources → inspect the Model for its Mesh + Animation sub-assets);
//    ONLY import if absent. Substitute the user's actual asset.
//    (If importing: run edit_by_dsl.import_resource(...) on a rigged .fbx, then inspect the Model GUID.)

// 2. add_vfx_source with the StandardAnimatedMesh template.
//    (add_vfx_source is a command_type inside edit_by_dsl, not a top-level tool.)
await edit_by_dsl({commands: [{
  command_type: 'add_vfx_source',
  params: {
    name: '<EffectName>.vfxsrc',
    manifest: {effect: '<EffectName>'},
    shared_resources: {
      body:  {type: 'Mesh',      guid: '<SKINNED_MESH_GUID>'},
      clip:  {type: 'Animation', guid: '<ANIMATION_GUID>'},
      albedo:{type: 'Texture',   guid: '<ALBEDO_GUID>'},
    },
    systems: [{
      name: 'main',
      template: 'StandardAnimatedMesh',
      // Pick every number from the user's prompt — these are just a sensible start,
      // not values tied to any particular subject.
      defines: {LIFETIME_MIN: 4.0, LIFETIME_MAX: 6.0, SPEED_MIN: 1.0, SPEED_MAX: 2.5, GRAVITY: 0.0, SCALE: 1.0},
      uniforms: {init: [{name: 'capacity', type: 'Int', value: 64}]},
      resources: {mesh: {ref: 'body'}, animation: {ref: 'clip'}, Map0: {ref: 'albedo'}},
      runtime: {vat_fps: 30, play_mode: 'loop'},
    }],
  },
}]});
```

The motion (spawn placement, trajectory, scale, orientation) is authored in `init.comp` + `update.comp` from the user's prompt — the SAME way as any StandardMesh effect. The VAT just plays whatever clip the supplied mesh shipped. There is no per-subject path: a swarm, a single character, a field of waving plants are all this one call with different authored motion.

### Errors

| Error | Meaning | Recovery |
|---|---|---|
| `MISSING_REQUIRED_RESOURCE ... 'mesh' / 'animation'` | StandardAnimatedMesh needs both | Declare both in `resources` (and the matching `shared_resources`). |
| `AnimatedMesh: mesh '...' has no skin` | The mesh isn't skinned | Use a rigged mesh; a static mesh belongs in StandardMesh. |
| `AnimatedMesh: mesh '...' does not belong to ... animation` | mesh + animation are from different models | Use the mesh and animation from the SAME imported model. |

### Gotchas — what to get right when authoring AnimatedMesh

These are the things that make a VAT effect actually render AND animate. They are properties of the template/format, not of any particular asset — apply them to whatever mesh the user supplies.

1. **The mesh must be SKINNED (skeleton + skin weights).** VAT bakes a skeletal-animation clip. A mesh whose source file animates object/node TRANSFORMS (e.g. separate wing meshes parented and rotated) rather than skin weights has no skin — the bake refuses it (`has no skin`). After importing, the usable mesh is the sub-mesh whose `bonesCount > 0`. If the user's asset is transform-animated, it is NOT a VAT candidate; say so rather than forcing it.
2. **mesh + animation must come from the SAME imported model.** The importer resolves the animation's owning model and finds the mesh in it; a mesh + animation from different imports won't bake.
3. **The VAT bake, the `u_positionTexture`, and the `VAT_VERTEX_COUNT / VAT_FRAME_COUNT / VAT_TEXTURE_SIZE` defines are 100% importer-managed.** Declare `mesh` + `animation` + `Map0` and you get a working animated mesh. Do NOT set the VAT_* defines, do NOT bind `u_positionTexture` yourself, do NOT hand-author the texel-fetch math — the importer bakes the texture (storing per-vertex deltas + packed normal), persists it, binds it, and rewrites the defines.
4. **In `output.gles.vert`'s VAT SAMPLE section, you may tune PLAYBACK only.** Editable: `VAT_FPS` (speed), `playMode` (loop / pingpong / once), the age→frame mapping. Do NOT change the vertex composition `attPosition + vatPosition` — the VAT stores a DELTA from the rest pose (frame 0 = no displacement), so the animated vertex is the rest mesh vertex PLUS the sampled delta; using the sample alone collapses the mesh. Also leave the texel-index math alone (it mirrors the bake's `frame * vertexCount + gl_VertexID` layout).
5. **Movement vs animation are separate.** The particles' path / spread / orientation is authored in `init.comp` + `update.comp` exactly like StandardMesh (POSITION/VELOCITY/ROTATION INIT, FORCE COMPUTATION). The per-instance mesh clip (whatever the rigged asset animates) is the VAT, driven by each particle's `age`. They compose automatically — derive both from the user's prompt, never from a fixed subject.
6. **`vat_fps` / `play_mode` live in `system.runtime`** and are the normal knobs for "flap faster / slower", "play once and rest", etc.
7. **`Map0` = the model's OWN diffuse, and the mesh renders as a SOLID lit surface.** For a character/creature to look right, bind the diffuse texture that ships with the imported model (find it via `list_resources` / the model's sub-assets) as the `Map0` resource — not an arbitrary sprite, and not a transparent-background PNG (those wash out / make the solid mesh see-through). The mesh output is opaque + depth-writing + lit (sRGB), and the diffuse feeds the `BaseTexture` sampler; you don't gate it on texture alpha. This is the same as StandardMesh (§3.2) — AnimatedMesh inherits it.
