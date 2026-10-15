---
name: VFXAuthoring
description: 自定义粒子特效制作：基于 V4 `.vfxsrc` 模板创建火焰、烟雾、爆炸、拖尾、群集和物理粒子等效果，支持多系统联动、网格/VAT 粒子、宿主绑定和预览排错。只有原样使用内置粒子预设时才转到 VFX。
---

# VFXAuthoring — Canonical VFX Source Authoring

> **🛑🛑 RULE #0 — ABSOLUTE, NON-NEGOTIABLE PRECONDITION. READ BEFORE ANYTHING ELSE.**
> **You MUST NEVER use the `Edit`, `Write`, or any other file-writing tool on a VFX mirror file** (any path under `Assets/temp.folder/vfx-workspace/…`, e.g. `.../systems/*/shaders/*.comp`, `system.json`, `index.vfxsrc`). Those files are a **READ-ONLY mirror**: you `Read` them, but they are NOT the real asset, and a hand-edit is **discarded** (never re-zipped into the `.vfxsrc`, never seen by the engine).
> **The ONLY way to change a VFX file is `edit_by_dsl.edit_vfx_source(...)`**. It is NOT a top-level MCP tool. Read with `Read`; write through `edit_by_dsl`. Example params: `{vfx_name, path, content}` or `{vfx_name, scope, patch}`.
> **This is a precondition for doing VFX at all: if for any reason you cannot commit to never writing workspace files directly and routing every edit through `edit_vfx_source`, STOP and do not start the VFX task.** Treat a native `Edit`/`Write` on a workspace path as a hard error you must never emit — if you catch yourself about to, switch to `edit_vfx_source` with the same path instead.

**This is the default path for any new or custom particle effect.** The stock-effect path in `skills_root/ability/VFX/SKILL.md` is only for drop-in stock effects with **zero customisation**. Anything else — multi-stage lifecycle, named shapes, per-particle colour, custom physics, no matching builtin — uses **this skill**.

This is the VFX-side analogue of `MaterialAuthoring`:
- authoritative format is **`.vfxsrc`**
- importer / compiler owns the runtime lowering and compile result

> **🟢 V4 multi-system workflow is the only supported path.** The V4 schema supports template-based authoring, scope-based reads/edits, and multi-system bundles for chain effects (fireworks, rocket + trail, etc.). **Start at §V4 below**, then read the one template/topic file you need (see the routing table). Deep shader theory and recipes live in `references/` — pull them in only when you author at the shader level.

> **🛑 HARD RULE — CAMERA: two different cameras, two opposite rules. Don't conflate them.**
>
> **(1) The user's BACKGROUND camera — never touch its background.** Particle effects live ON TOP of whatever background the user already has in the current scene. **Never** call `set_component` on a `Camera` to change `clearType` / `clearColor` (e.g. to `"COLOR_DEPTH"`) or related background fields, and never add a replacement background just to "make the particles look good against a dark sky". A prompt for "fireworks" / "night sky particles" describes the **particles**, not the background — it stays the current scene background unless the user separately asks for a background task. Violating this paints a black scene the user never asked for.
>
> **(2) Your VERIFICATION camera — you MUST frame the particles, or you'll misread an empty screenshot.** Particles spawn at the **world origin**; in a throwaway verification scene the default camera often doesn't point there, so the screenshot is empty **even when the effect is working**. An empty/black verification frame is NOT "no particles" — first check the camera is framing the origin (e.g. set the verification scene camera's Transform `localPosition ≈ {0,0,40}`, `localEulerAngles {0,0,0}`). This is about your verification harness, never the user's effect — it does not touch background fields, so it does not violate rule (1). See §Verification's empty-screen triage.

---


# §V4 — Multi-System Authoring (default for new effects)

## V4 Quick Start (60-second mental model)

V4 .vfxsrc bundles = **manifest + one or more systems**. Each system picks a **template** (StandardQuad / StandardMesh / StandardAnimatedMesh / PhysicsMesh), provides:
- `defines` — numeric tunables. Names that are **runtime exposed parameters** for the template (speed/lifetime/gravity/size/tint etc. — see `references/asset-inspector.md` §3) are routed to the parameter's runtime DEFAULT (the asset-panel starting value, user-tunable live); all other names are compile-time substituted as before
- `uniforms` — per-stage runtime uniforms (spawn rate, capacity, etc.)
- `resources` — mesh/material/texture GUID references via `shared_resources`. StandardMesh / StandardAnimatedMesh / PhysicsMesh accept an OPTIONAL `material` resource (any editor .omtl / material-graph material → real PBR/lit shading replaces the generated unlit output; see §3.2 "Optional: bind a real editor material")
- `events` — cross-system spawn (active — see §2 below)
- `runtime` — non-uniform per-system settings, all template-specific (colliders/forces/cluster for PhysicsMesh, `emit_source` for mesh emission, `color_ramp`, etc. — see the relevant files). NOTE: there is **no blend-mode field** — additive/glow and keying out a black sprite background are done in the FRAG (`color0 = vec4(tint*alpha, 0.0)`), see `references/dimension-basis.md` §3.

**Asset inspector**: every generated `.vfxsrc` automatically gets a per-system editor panel derived from system.json — runtime parameter sliders, Spawn Rate / Particle Count, Texture/Mesh/Animation/Material resource pickers, compute-stage sampler pickers (MaskTex / sdf volumes — "Sampling" group), an Emission Mesh picker when you record `runtime.emit_source`, and a Flipbook group (Sheet Columns/Rows + FPS) when the sheet defines are present — all swappable/persistent. What you author DECIDES what the user can self-serve afterwards. **Read `references/asset-inspector.md`** for: the per-template exposed-parameter lists, the defines→runtime-default routing rule, what stays compile-time, resource/picker conventions, and the system-naming rule for multi-system assets (system names are user-visible panel headers — use `rocket`/`explosion`, never `main`, when there are 2+ systems).

**Currently implemented**: `StandardQuad` (camera-facing 2D quads), `StandardMesh` (per-particle 3D mesh instances with TRS + tint), `StandardAnimatedMesh` (per-particle SKINNED mesh playing a baked animation clip — any rigged mesh whose geometry deforms over time; see §3.3), `PhysicsMesh` (GPU physics particles — gravity, colliders, bounce, rigid/soft bodies, fracture; see §3.5), and **multi-system event chains** between them. **V1/V2/V3 manifests are no longer supported** — the importer rejects them with `INVALID_VERSION`. Use `add_vfx_source` for every new effect; do not hand-construct `source_files` maps with V3 layout.

The V4 author loop is:

```
1. pick a template per system     ← from the "VFX template catalog" table below (no command — it's documented here)
2. `edit_by_dsl.add_vfx_source({...})`    ← server expands templates → importer validates
3. (optional iterate)
   inspect(vfx_guid)                ← get vfx_workspace.files[].read_path
   Read(read_path[, offset, limit])  ← native Read tool: open one file (offset/limit big shaders)
   `edit_by_dsl.edit_vfx_source({path, content})` ← replace one whole file you just Read, OR …
   `edit_by_dsl.edit_vfx_source({scope, patch})`  ← deep-merge a JSON segment, OR …
   `edit_by_dsl.edit_vfx_source({op:"add_system"|"delete_system", ...})`
```

You read individual files (native `Read` on the mirror `read_path`s) and write them back through `edit_vfx_source`. There is no "full source_files map". Get authoritative `read_path`s from `inspect(vfx_guid).vfx_workspace.files[]`; edit responses also return the changed file's `read_path`.

> **Reminder (full statement = RULE #0 at the top):** the mirror `read_path`s are a READ-ONLY copy — `Read` them, but route every change through `edit_vfx_source`, never `Edit`/`Write`.

> **🛑 HARD RULE — author from THIS skill + the MCP tools ONLY. Never spelunk the filesystem.**
> - **ALWAYS read files with the native `Read` tool — NEVER `cat`/`head`/`tail`/`sed`/`grep` or any Bash command.** This applies to *everything* you read: this `SKILL.md`, the `templates/*` and `references/*` docs, and your workspace `read_path`s. `Read` takes `offset`/`limit` for large files, so there is never a reason to `cat … | head -N`. Reading through the shell is forbidden and, because Bash commands (especially compound `cd … && …` forms) are not auto-approved, it also triggers a permission prompt — `Read` on these files does not. If you catch yourself about to `cat` a file, call `Read` on the same path instead.
> - **The ONLY files you may `Read` are the mirror `read_path`s returned for your own bundle** (from `inspect(vfx_guid).vfx_workspace.files` or the changed-file `read_path` in an edit response) **plus this skill's own docs (`SKILL.md` / `templates/` / `references/`)**. **Do NOT use `Read` (or any tool) on the project, the editor install, Backup folders, raw `.vfxsrc` zips, or any OTHER effect** to locate assets, inspect bundles, or "understand how something works". The MCP DSL tools are the interface for everything else: `list_resources` (find existing assets by name), `inspect` (read a resource's sub-assets/GUIDs — and, for a `.vfxsrc`, its `vfx_workspace.files`), `edit_by_dsl.import_resource({...})` (bring in user-provided local assets), `get_scene`. If a tool seems insufficient, call it differently — never drop to the shell. (Shell-hunting the disk for a mesh or finding `*.fbx` is the #1 cause of slow, repetitive runs.)
> - **The only templates are the ones in the "VFX template catalog" table below** (StandardQuad / StandardMesh / StandardAnimatedMesh / PhysicsMesh). Named effects like "Fireworks", "explode", "onflow", etc. are NOT templates and NOT references — do not open, read, or copy any existing effect / `.vfxsrc` / `.vg` / controller to "learn the pattern". Everything you need (controller behaviour, spawn semantics, slot layout, shader section contracts) is documented in this skill; if something seems missing, re-read the relevant §, don't go spelunking other assets.
> - **To inspect YOUR bundle, use `inspect(vfx_guid)` → `vfx_workspace.files`, then `Read` the listed `read_path`s** — never read the raw `.vfxsrc` zip directly (it is a packed archive), and never write to the mirror files by hand (those edits are not re-zipped; all writes go through `edit_vfx_source`). The engine importer re-mirrors on every import, so the listing always reflects the current bundle.
> - **Spawn semantics (so you never need to look them up elsewhere):** the ONE density knob is **`originalSpawnRate`** (particles/sec). The controller derives the engine rate from it each frame and OVERWRITES any `spawnRateMin/Max`/`delay` you set, so setting those by hand does nothing — just set `originalSpawnRate` to your target. **`originalSpawnRate: 0` means OFF** (no particles); any positive value works at any magnitude (the engine accumulates fractional spawns, so even `0.5`/sec emits correctly). Steady-state alive ≈ `rate × lifetime`, capped by `capacity`; `capacity / lifetime_min` is the max sustainable rate (see §2.X). That's the whole model — no controller file needs reading.

## V4 DSL commands

In prose, this skill writes DSL calls as `edit_by_dsl.xxx(...)` / `interact_by_dsl.xxx(...)`. Those are documentation shorthands, not top-level MCP tools. Executable code examples still use the full `edit_by_dsl({commands:[...]})` / `interact_by_dsl({commands:[...]})` shape.

The surface is **2 commands** (reading needs no command, and the template list is documented in the catalog below — not a command):

| Command | Purpose |
|---|---|
| `add_vfx_source(name, manifest, systems[], shared_resources)` | Create a brand-new V4 package. `systems[i]` = `{name, template, defines?, uniforms?, resources?, events?}`. Server expands templates, imports the bundle, and returns a compact file index. |
| `edit_vfx_source(vfx_name, <one op>)` | **Write path.** Exactly one of: `{path, content}` (replace one whole file), `{scope, patch\|content}` (deep-merge JSON segment / replace by scope), `{op:"add_system", system_name, template, …}`, or `{op:"delete_system", system_name}`. Returns the changed file path and its mirror `read_path`. |

**Reading is not a command.** `add_vfx_source` returns `workspace_root` plus a compact `files:[{rel, role, bytes}]` index. `edit_vfx_source` returns the changed file's `read_path`. To inspect every current file, call `inspect(vfx_guid)` → `vfx_workspace.files[]`, then open the listed paths with the native `Read` tool.

## VFX template catalog

These are the ONLY templates. Pick one per system, then supply its `required_resources` (as GUIDs via `shared_resources` + `resources.<key>.ref`) and any `required_defines`. (Authoritative list — keep it in sync with `VFX_SOURCE_TEMPLATES` in `commands/vfxUtils.ts`; there is no `list_vfx_templates` command.)

| Template | pipeline / output | particle_size | required_defines | required_resources | Use for |
|---|---|---|---|---|---|
| `StandardQuad` | Standard / Quad | 12 | none | `Map0` | fire, smoke, sparks, simple 2D billboard effects |
| `StandardMesh` | Standard / Mesh | 32 | none | `mesh`, `Map0` | confetti, debris, falling rocks, projectile / coin swarms (per-particle 3D mesh) |
| `StandardAnimatedMesh` | Standard / AnimatedMesh | 32 | none | `mesh`, `animation`, `Map0` | a rigged mesh that deforms over time (skinned / baked VAT clip) |
| `PhysicsMesh` | Physics / PhysicsMesh | 32 | `GRAVITY_Y`, `RESTITUTION`, `FRICTION`, `PARTICLE_RADIUS`, `GROUND_Y`, `SCALE_START`, `SCALE_END`, `FRACTURE_Y` | `mesh`, `Map0` | bouncing balls, falling rocks, GPU physics debris |

`Map0` defaults to a builtin sprite when you omit it on Quad/Strip; Mesh templates default `Map0` to builtin white. Read the matching `templates/<Template>.md` for the full define/uniform/shader contract before authoring.

`{op:"add_system"}` takes the same fields as one `add_vfx_source.systems[]` entry. `{op:"delete_system"}` refuses if another system's `events` still target it (orphaning). Registering a shared resource = `{scope:"manifest", patch:{shared_resources:{<key>:{type, guid}}}}` (short-id GUIDs resolved).

## Scope DSL

Used by the `edit_vfx_source` JSON-patch op (`{scope, patch|content}`). For **reading**, take a `read_path` from `inspect`'s `vfx_workspace` or the latest edit response and use the native `Read` — it handles line ranges (`offset`/`limit`) on big shaders, which scope cannot.

| Scope | Targets |
|---|---|
| `manifest` | The `index.vfxsrc` manifest JSON (e.g. `shared_resources`) |
| `system:<name>` | The system's full `system.json` |
| `system:<name>:defines` | Just the `defines` block |
| `system:<name>:resources` | Just the `resources` block |
| `system:<name>:uniforms` | Just the `uniforms` block (all 4 stages) |
| `system:<name>:events` | Just the `events` array |
| `system:<name>:runtime` | Just the `runtime` block |
| `system:<name>:shader:<filename>` | Single shader file's full text (e.g. `shader:init.comp`); or use the `{path, content}` op with the workspace `read_path` |
| `resources:<subdir>/<filename>` | Single resource file's text |

**Patch semantics** for `edit_vfx_source`:
- JSON segments: `patch` is deep-merged. Arrays are replaced wholesale (no element-level merging).
- Files: `content` (scope mode) or the `{path, content}` op replaces the whole file.
- Identity fields (`manifest.format`, `manifest.version`, `system.name`, `system.template`) are forbidden — patches touching them throw `USE_DELETE_AND_RE_ADD`. To change the template, `delete_system` + `add_system`.
- **⚠️ Exposed parameters after creation**: the defines→runtime-default routing happens ONLY at `add_vfx_source` / `op:"add_system"` (template expansion). On an EXISTING system, patching an exposed name into `system:<name>:defines` fails with `INVALID_UNIFORMS` (a name cannot be both a define and an exposed parameter). To change an exposed parameter's default later: read `system.json` (via workspace), modify the wanted `exposed_parameters[].default` entries, and patch the **whole `exposed_parameters` array** back at scope `system:<name>` (arrays replace wholesale). Verified live: the new default applies after the re-import.
- **⚠️ Patches cannot DELETE keys** (setting a key to `null` is schema-rejected). To REMOVE a key from a JSON segment (e.g. a wrong key written into `defines`), **full-replace the whole file via the `{path, content}` op** — it overwrites rather than deep-merges, so the key is gone. This is the simplest recovery. (`op:"delete_system"`+`op:"add_system"` also works but can be blocked by event-target orphaning or the last-system rule.) Note: a compile-FAILED edit now **auto-rolls-back** to the last compiling version (you'll see `rolled_back: true` in the response), so a bad patch no longer corrupts the bundle — fix it and retry. Still, double-check defines patches BEFORE submitting.

## V4 — API syntax reference (not a recipe to copy)

> **This block exists only to show the call shape of `add_vfx_source`.** It is NOT a starter template for "make a particle effect". The right way to build effects is to read the template's shader files and write shader code that does what the user prompt asks. Don't copy this block — copy *the call shape* and supply your own defines/resources/shader edits driven by the user's actual prompt.

```typescript
await edit_by_dsl({commands: [{
  command_type: 'add_vfx_source',
  params: {
    name: '<YourEffect>.vfxsrc',
    manifest: {effect: '<YourEffect>'},
    shared_resources: {
      // one entry per Mesh/Material/Texture you need; agent gets the GUID
      // from prior list_resources / inspect / edit_by_dsl.import_resource(...).
      main_tex: {type: 'Texture', guid: '<your_texture_guid>'},
    },
    systems: [{
      name: 'main',
      template: 'StandardQuad',
      // Pick numbers that match the effect you want — there is no canonical default
      // for "an effect"; defaults are only the canonical starting point of the template.
      defines: {
        SIZE_START: 0.35, SIZE_END: 0.75,
        LIFETIME_MIN: 2.0, LIFETIME_MAX: 2.75,
        SPEED_MIN: 2.5, SPEED_MAX: 5.0,
        GRAVITY: 3.5,
      },
      resources: {Map0: {ref: 'main_tex'}},
      // Optional: uniforms / events / runtime
    }],
  },
}]});
```

### Binding a vfxsrc to its host — create the host GRAPH-FREE

A `.vfxsrc` renders only when bound to a `VisualEffect` (engine type `VFXEffectBlock`)
component. **The host VisualEffect is required, and for a vfxsrc it MUST be created
without a default VFX Graph** — otherwise every effect leaves an orphaned "Basic
Particles" `.vg` asset in the project. Create a plain Transform host, add the
low-level component, then bind the vfxsrc profile GUID:

```typescript
await edit_by_dsl({commands: [
  // 1. Create the host object (or reuse an existing SceneObject).
  { command_type: 'add_scene_object', params: { name: 'MyEffect', type: 'Transform' }, alias: 'host' },
  // 2. Add the VisualEffect host GRAPH-FREE — means no
  //    default VFX Graph is attached, so no stray .vg asset is created.
  { command_type: 'add_component',
    params: { scene_object: { $ref: 'host' }, type: 'VFXEffectBlock' },
    alias: 'vfx' },
  // 3. Bind the imported vfxsrc profile GUID returned by add_vfx_source.
  { command_type: 'set_component',
    params: { guid: { $ref: 'vfx' },
      properties: { vfxProfile: { guid: '<vfxprofile_guid>', type: 'VisualEffectAsset' } } } },
]});
```

> `add_component` requires the engine component type `VFXEffectBlock`; `VisualEffect`
> is the APJS class name and must not be passed as the DSL type. Adding
> `VFXEffectBlock` directly does not create a default graph. Normal Visual Effect
> creation through `add_builtin_object` is unaffected. Note: a `.vfxsrc` asset can ONLY be added through
> `add_vfx_source`/`edit_vfx_source`; it is intentionally not
> importable from the editor's manual asset-import dialog.

After `add_vfx_source`, the typical author loop is:

1. Call `inspect(vfx_guid)`, then `Read` the relevant shader's `read_path` (e.g. the `init.comp` entry).
2. Understand the section contracts (see §3.1 below).
3. Write GLSL that satisfies the contract and produces the user's requested behavior.
4. Push it back with `edit_by_dsl.edit_vfx_source({...})`, for example `{vfx_name, path:<that read_path>, content:<new_text>}`, or `scope:"system:main:shader:init.comp"`.
5. Re-bind the VFX component via `edit_by_dsl.set_component({...})`, then verify with `interact_by_dsl`.


## How this skill is organised — read the file you need (do NOT pre-load all)

This SKILL.md is the **router**: it holds the V4 workflow, the DSL, the scope grammar, the decision tree, the supply-budget model, the verification ladder, and the post-edit re-bind rule. The per-template guides and deep references live in separate files — **read the one that matches the template/topic you picked**, not all of them.

| You are authoring / need | Read this file |
|---|---|
| **ANY new effect from a creative brief** — the ~10 design axes, measured size/speed/density calibration anchors, additive-glow recipe, palettes, adjective→axes mapping. Read it right after picking the template, BEFORE choosing numbers. | `skills_root/assets/VFXAuthoring/references/dimension-basis.md` |
| **Design workflow & quality bar** — visual-spec-first method, pass-based building (structure→look→polish), the per-capture critique rubric, two complete worked derivations (fireworks chain, magic vortex — process traces to imitate, NOT visual targets; the quality bar is always the current brief's own spec). Read for any effect that must LOOK good, not just compile. | `skills_root/assets/VFXAuthoring/references/design-process.md` |
| **StandardQuad** (camera-facing 2D quads) — §3.0–§3.1 | `skills_root/assets/VFXAuthoring/templates/StandardQuad.md` |
| **StandardMesh** (per-particle 3D mesh) — §3.2 | `skills_root/assets/VFXAuthoring/templates/StandardMesh.md` |
| **StandardAnimatedMesh** (skinned / VAT clip) — §3.3 | `skills_root/assets/VFXAuthoring/templates/StandardAnimatedMesh.md` |
| **PhysicsMesh** (GPU PBD: gravity/colliders/bounce/cluster/fracture/soft body) — §3.5 | `skills_root/assets/VFXAuthoring/templates/PhysicsMesh.md` |
| **Multi-system event chains** (fireworks, rocket→trail, rain→splash) — §2 | `skills_root/assets/VFXAuthoring/references/events-multisystem.md` |
| **Particle supply budget** — the conservation law that decides whether spawns silently drop (`self_demand + inbound ≤ supply`); worked examples + how to fix `SPAWN_DEMAND_EXCEEDS_SUPPLY`. Read when a system spawns fewer particles than expected, or before any high-rate / multi-system bundle. | `skills_root/assets/VFXAuthoring/references/supply-budget.md` |
| **Shader-level authoring** (the universal framework + the general model capabilities: reshaping/reorienting the billboard incl. ground-plane/3D placement, `totaltime` time-based authoring & cross-system sync, particle-formation/shape assembly, multi-look channel encoding; boids/cross-particle reads; AUSL syntax; shader hard-constraints) | `skills_root/assets/VFXAuthoring/references/shader-theory.md` |
| **Recipes** (sprite-sheet flipbook, worked examples) | `skills_root/assets/VFXAuthoring/references/recipes.md` |
| **Custom buffer (VFXBuffer)** — GPU particles → CPU/game logic: count particle hits/score into a buffer (`custom_buffers` + `kill_count_into`), read it live from a script, drive game state (health/score/triggers). For "shoot/hit/collect/count → something reacts" effects (bullets vs enemy, scoreboards, impact-driven health). | `skills_root/assets/VFXAuthoring/references/custom-buffer.md` |

**Section-anchor legend** — when any file says "see §X", it means: asset panel → `references/asset-inspector.md`; §2 → `references/events-multisystem.md`; §3.0–§3.1 → `templates/StandardQuad.md`; §3.2 → `templates/StandardMesh.md`; §3.3 → `templates/StandardAnimatedMesh.md`; §3.5 → `templates/PhysicsMesh.md`; §2.X (supply budget) is in THIS file below.

> The `references/shader-theory.md` and `references/recipes.md` files are template-agnostic shader guides: apply their techniques through `edit_by_dsl.edit_vfx_source({scope:"system:<name>:shader:<file>", content})` for shader text and the same command with `scope:"system:<name>:defines"` for tunables; never hand-construct bundles.

## §2.X — Particle supply budget (universal mechanism)

Every system enforces a particle conservation law. Get it wrong and **spawns
drop silently** — the symptom is "bursts work for a moment then stop" or
"rocket explodes but no burst appears, sometimes". The rule, for every system,
every effect, every trigger kind:

```
self_demand = spawnRate / delay          # delay is SECONDS BETWEEN BATCHES, not start-delay
inbound     = Σ event contributions      # see supply-budget.md for the per-trigger formulas
supply      = capacity / lifetime_min    # max sustainable rate before the dead-list saturates

    self_demand + inbound ≤ supply       # (validator allows up to ~1.2× before throwing)
```

Violate it and the dead-list empties; further spawn requests find no slot and
are dropped (no queue, no retry). The validator throws `SPAWN_DEMAND_EXCEEDS_SUPPLY`
at `add_vfx_source` time for the worst cases — but reason about it BEFORE
writing systems. **Full model + worked examples (Fireworks) + how to fix each
validator failure → `references/supply-budget.md`.**


## Decision tree

Trigger this skill (instead of the stock-object path in `skills_root/ability/VFX`) when **any** of the following matches the prompt:

1. **No exact builtin** — user names a phenomenon not in `Basic / Physics / Fire / Rain / Snow / Explosion / Firework / Fog / Lightning / Turbulence Particles` (e.g. laser, portal, comet, plasma, electric arc, magic rune, glitch sparkle, fluid splash, ribbon trail).

2. **Builtin name matches, but the prompt adds qualifiers a single emitter can't deliver**:
   - multi-stage lifecycle: "fireworks **launch with trail then explode**", "rain **that turns to snow**", "explosion **with shockwave ring**"
   - per-particle variation: "fireworks **of different colours and shapes**", "fire **with random size embers**"
   - custom physics / spawn shape: "particles **spawn along a circle**", "particles **follow the camera**"
   - custom blend / colour ramp / lifetime curve

3. **User asks to edit / version / own** the effect's source files later.

4. **User asks to author `.vg` / graph topology** → still **use this skill** (`.vfxsrc`). Do not hand-edit `.vg`.

**Worked example.** Prompt: *"Add a new particle effect to create a fireworks effect: multiple particles launch upward from below with trailing flames, then explode in the sky into fireworks of different colors and shapes."* This has (a) multi-stage launch→explode, (b) per-particle colour, (c) named shapes, (d) trailing flames. Even though a stock `"Firework Particles"` object may exist, every qualifier requires source-level control → **use this skill, not the stock-object path**.

When the prompt is *only* "make some sparkles" or *only* "add fire" with no qualifiers, the matching builtin in `skills_root/ability/VFX/SKILL.md` is fine — `.vfxsrc` is overkill for those.

## Mental model

Think of `.vfxsrc` as:

**editable source bundle** → **importer / compiler consumes it** → **runtime VFX assets + compile status**

The Agent's job is:
1. write a valid source bundle
2. package it as `.vfxsrc`
3. hand it to the normal importer / compile pipeline

The Agent should **not**:
- author `.vg` as the source of truth
- patch generated export folders directly
- skip required source files and hope the importer fills them in


## edit_vfx_source — REQUIRED post-edit re-bind step

`edit_vfx_source` writes the new bundle to disk AND triggers a fresh import (the VFXProfile asset gets a brand-new in-memory object). **But the bound `VisualEffect` component on your scene host keeps pointing at the OLD profile** — the binding doesn't auto-refresh on `AssetUpdated`. Symptom: `edit_vfx_source` succeeds, the file on disk is updated, but the preview keeps showing the pre-edit visual; the agent looks at the screenshot, sees no change, and wrongly assumes the edit failed.

**Always pair every `edit_vfx_source` with a `set_component` re-bind** on every host using the asset — re-issue `set_component` with the same `vfxProfile` GUID to force the component to re-fetch from the now-updated ResourceItem. Then verify with a `reset_preview`+`wait`+`screenshot` timeline — see §Verification.

```js
await edit_by_dsl({commands: [
  {command_type: 'edit_vfx_source', params: {vfx_name, scope: 'system:main:shader:init.comp', content: newGlsl}},
  {command_type: 'set_component', params: {
    guid: vfxCompGuid,
    properties: {vfxProfile: {guid: vfxAssetGuid, type: 'VisualEffectAsset'}},
  }},
]});

await interact_by_dsl({commands: [
  {command_type: 'reset_preview'},
  {command_type: 'wait', params: {ms: 600}},
  {command_type: 'screenshot'},
  {command_type: 'wait', params: {ms: 1200}},
  {command_type: 'screenshot'},
]});
```

If you didn't track which scene objects hold the binding, use `get_scene` to enumerate `VisualEffect` components and re-bind any whose `vfxProfile` GUID matches the edited asset. (Engine-level limitation; the workaround is reliable and cheap — do not skip it.)

## Verification

After import, verify in this order:
1. the `.vfxsrc` archive writes successfully
2. the VFX resource appears in the project
3. import or shader errors surface through the VFX importer path
4. the imported asset can bind to a `VFXEffectBlock` and render visible preview output

**⚠️ Check the VFX command result itself.** VFX uses its own importer/compiler path,
separate from material `import_glsl`; it does not participate in `_compile_check`.
Import or shader failures are returned as command errors. There is no separate
trustworthy `compiled` boolean on successful responses. A failed edit can leave the
PREVIOUS shader rendering, so an unchanged preview does not prove the new source was
accepted. Cross-shader (GLES translation) errors can also appear in the editor error
toast and engine log.

**⚠️ Dead-preview detector — check BEFORE trusting any capture.** If consecutive
screenshots come back **byte-identical** (with a live preview background even two
frames are never identical), the preview process has crashed/frozen — every
screenshot from it is a stale frame and proves NOTHING (a frozen empty frame is
not "no particles"; a frozen old frame is not "my edit didn't apply"). This can
happen after many rapid VFX reload cycles. Recovery requires an editor restart —
report it rather than looping more edits/screenshots against a dead preview.

**Visual verification = TIMELINE CAPTURE, not a single screenshot.** Particles are
motion — one frame cannot show spawn rhythm, build-up, decay, or whether anything
moves at all. The canonical method: in ONE `interact_by_dsl` call, batch
`reset_preview` (restart the simulation cleanly from t=0) followed by several
`wait`+`screenshot` pairs at increasing times (each frame returns as a separate image;
see timeline-capture guidance in `skills_root/general/PreviewInteraction/SKILL.md`). Pick the wait ladder from the
effect's time constants — birth (~0.5s), mid-life, steady state (≥ one full lifetime) —
and judge the SEQUENCE against the brief: does it ramp as designed, do particles move
between frames, is steady-state density right? *(Verified working on this branch: a
`reset_preview`+`wait`+`screenshot` batch returns every frame with no hang.)*

**`wait` is part of the interactive verification path.** If timeline capture still cannot advance on the current branch, fire **several isolated `screenshot` calls spaced over real wall-clock** and judge the most-developed; remember that a sparse early frame is then a CAPTURE artifact, NOT "low spawn rate" (triage #3 vs #4). Do **not** substitute `capture_preview` for a failed timeline ladder — see the historical note.

**Historical note — the `reset_preview` "wedge" is FIXED; don't avoid reset.** Older
guidance said `reset_preview` (and `capture_preview`, which resets internally) wedges the
preview loop, recoverable only by restarting orionkit. That was real but a *symptom*: a
cap crashed while collecting export dependencies for a **graph-free `.vfxsrc`** (null
`vfxGraph.scriptContent`), killing the preview loop. It is fixed on this branch (the cap
falls back to `vfxControllerContent`), and `reset_preview` is verified working again — so
use the reset-based timeline above rather than dancing around it. Your safety net is the
dead-preview detector: if consecutive screenshots come back **byte-identical** after a
reset, you've hit that class of crash → restart orionkit and report; don't loop more
captures. (Also: don't batch a valid preview command with an invalid one — the action
mutex can wedge the first while it waits on the second.)

### ⚠️ Empty / black / unchanged screenshot — triage in THIS order

A blank or "nothing happened" frame almost never means "my shader is wrong". Walk
these causes top-down (most common first); each has a one-line fix:

1. **Dead / wedged preview** — consecutive screenshots **byte-identical** (with a
   live preview background, two real frames are never identical). The preview
   crashed/froze (rare now — a crash-class bug, or many rapid reload cycles; see the
   Historical note). The frame proves NOTHING. → **restart orionkit**; never loop more
   captures against it.
2. **Camera not framing the origin** — particles spawn at world origin; your
   verification camera may not point there. → aim the **verification** camera
   (`localPosition ≈ {0,0,40}`, euler `{0,0,0}`). (See the camera HARD RULE (2) — this is the verification camera, not the user's background.)
3. **Sparse / near-empty frame = CAPTURE TIMING, not spawn** — only 1–3 particles
   visible while config looks fine. If `wait` is unavailable (gated), your
   screenshots land near t≈0 before the burst develops. → sample **5–8 isolated
   screenshots** over real time and judge the most-developed; do NOT bump spawn/size
   off one early frame (that's chasing a non-bug). Rule out this one BEFORE #4.
4. **Spawn rate genuinely too low** — `originalSpawnRate` is THE knob (template default
   ~2/sec ≈ invisible). ⚠️ The controller OVERWRITES `spawnRateMin/Max` and `delayMin/Max`
   every frame from `originalSpawnRate`, so setting `spawnRateMin/Max` alone does NOTHING
   (this is the #1 invisible-effect trap). Just set `originalSpawnRate` to your target
   particles/sec (e.g. 200–700) — it works at any magnitude, and **`0` means OFF**. Also
   raise `capacity`. For event-target / `shared_pool_with` systems use the **epsilon spawn**
   uniforms (`references/events-multisystem.md`).
5. **Compile failed but the previous effect still renders** — inspect the VFX command
   error, then check the editor error toast / engine log for cross-shader (GLES) errors.
6. **Parasitic / zero real spawn** — a mystery emitter at screen centre is the
   importer's default-spawner fallback firing on a system with no/zero spawn
   uniforms (`references/events-multisystem.md`); or the supply budget starved your
   spawns (§2.X → `references/supply-budget.md`).
7. **Particles render as hard squares / wrong shape** — `USE_TEX_ALPHA` defaults to
   1.0, so an opaque texture renders as a square. → soft dots need
   `Default-Particle.png` (default alpha) or white texture + `USE_TEX_ALPHA:0`
   (`references/dimension-basis.md` §2).
8. **Opaque sprite shows a BLACK BOX around it** — a texture with a solid black
   background (lightning/fire/spark flipbook, imported PNG with no alpha) renders
   its black bg as an opaque square. → in the output frag's FINAL OUTPUT use
   `color0 = vec4(tint * alpha, 0.0)` (additive `alpha=0`): black texel → `tint=0`
   → keyed out, bright pixels glow. NOT a config/blend-mode field
   (`references/dimension-basis.md` §3).


## Common errors

The authoritative, current error tables live next to the feature that raises them:
- **Event-chain validator errors** (cycles, unknown target, N-to-1, forbidden target template): see §2 in `references/events-multisystem.md`.
- **Per-template schema / compile errors and pitfalls**: see the "Gotchas" / "Common pitfalls" section of the relevant `templates/<Template>.md`.
- **`INVALID_VERSION`**: a V1/V2/V3 manifest reached the importer. V4 is the only supported format — recreate via `add_vfx_source`.
