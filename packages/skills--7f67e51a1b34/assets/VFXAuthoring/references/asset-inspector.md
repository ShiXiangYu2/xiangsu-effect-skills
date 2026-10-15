<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first. -->

# Asset Inspector — what your generated `.vfxsrc` exposes to the user

Every `.vfxsrc` you generate automatically gets an **asset-inspector panel** in the
editor. You never author the panel itself — it is derived from each system's
`system.json` at import. What you write in `add_vfx_source` therefore decides what
the USER can tune after generation, live, without you. Get this right and the user
self-serves; get it wrong and every tweak comes back to you as a new prompt.

## 1. What appears on the panel (per system)

| Panel entry | Derived from | Notes |
|---|---|---|
| Runtime parameter sliders / color swatches | the template's `exposed_parameters` (FIXED per template — see §3; you cannot add your own) | Live-tunable; edits do NOT recompile |
| `Spawn Rate` | `uniforms.spawn[].originalSpawnRate` | Live |
| `Particle Count` | `uniforms.init[].capacity` | Triggers an effect reload (GPU buffer resize) |
| `Texture` picker | output texture uniforms (`Map0`/`BaseTexture` via `resources`) | Hidden while a `material` is bound |
| `Mesh` picker | `resources.mesh` (mesh-output templates) | Swap is persistent (rewrites the package + reimports) |
| `Animation` picker | `resources.animation` (StandardAnimatedMesh) | Swap re-bakes the VAT |
| `Material` picker | `resources.material` (StandardMesh / StandardAnimatedMesh / PhysicsMesh; shows even when you didn't bind one) | `None` = the template's unlit output |
| `Physics` group (`Substeps` / `Position Iterations` / `Particle Collision` / `Max Particle Radius`) | PhysicsMesh only (solver uniforms) | Edits trigger a reload |
| `Sampling` group — compute-stage texture pickers (e.g. `MaskTex`, `u_sdf0`) | any `uniforms.init[]`/`uniforms.update[]` entry of `{type:"Texture", resource}` | The texture the SIMULATION samples (mask gating / colour bake / sdf collision volume). `Texture3D` shared resources (.vf) get a volume picker. Swap is persistent |
| `Sampling` group — `Emission Mesh` picker | `runtime.emit_source` (+ baked `runtime.emit_points`) | Swapping re-samples the picked mesh's surface and REBAKES init.comp automatically — see §5b |
| `Flipbook` group (`Sheet Columns` / `Sheet Rows` / `Playback FPS`) | `defines` containing `SHEET_COLS` + `SHEET_ROWS` | Define-backed: an edit rewrites the package defines + recompiles. `TOTAL_FRAMES` auto-recomputes = COLS×ROWS; `SHEET_W/H` auto-follow texture swaps — see §5c |
| `Sampling` group — SDF volume for `runtime.conform` | a `uniforms.update[]` `{type:"Texture", resource}` referenced by a `runtime.conform[].sampler` | Conform-to-SDF force: particles assemble onto the baked shape's surface; swapping the `Texture3D` picker re-shapes them — see §5d |

**Multi-system assets** (event chains — fireworks, trails): the panel groups by
**system name first**, then by parameter group. System names are USER-VISIBLE
headers — name them descriptively (`rocket`, `explosion`, `trail`), never `main` /
`sys1`, whenever the asset has more than one system.

## 2. THE core authoring rule — exposed params are authored via `defines`

The names listed in §3 are **runtime uniforms**, not compile-time constants. You
still write them in `defines` — the expander routes the value into the parameter's
runtime DEFAULT (the panel's starting value):

```json
"defines": {"LIFETIME_MIN": 8.0, "GRAVITY": -18.0}
```
means *"start at lifetime 8 / gravity -18, and the user can drag the slider later"*.
They are NEVER token-substituted into the shaders. Everything else in `defines`
(the per-template compile-time list, §4) behaves as before: baked at import,
changeable only via `edit_vfx_source` + reimport, NOT on the panel.

## 3. Per-template exposed (panel-tunable) parameters

| Template | Exposed (author via `defines`, user tunes live) |
|---|---|
| StandardQuad | `SPEED_MIN/MAX`, `LIFETIME_MIN/MAX`, `GRAVITY`, `SIZE_START/END`, `TINT_R/G/B/A` (one RGBA swatch), `USE_TEX_ALPHA` |
| StandardMesh | `SPEED_MIN/MAX`, `LIFETIME_MIN/MAX`, `GRAVITY`, `SCALE`, `SPIN`, `COLOR_R/G/B/A` (one RGBA swatch) |
| StandardAnimatedMesh | same as StandardMesh |
| PhysicsMesh | `LIFETIME_MIN/MAX`, `SPAWN_RADIUS`, `INITIAL_SPEED`, `BASE_COLOR_R/G/B` (swatch), `COLOR_VARIETY`, `SCALE_VARIETY`, `SPIN_VARIETY`, `ORIENT_RANDOM` |

> **Color ramp vs. the flat swatch — pick one per system.** When a system declares a
> `runtime.color_ramp`, the per-particle colour is driven entirely by the ramp (it
> replaces `v0.rgb` in the vert), so the flat colour swatch (`TINT_R/G/B/A` on
> StandardQuad, `COLOR_R/G/B/A` on StandardMesh) is **inert** — editing it in the panel
> has no visible effect. Don't add a `color_ramp` if you want the user to live-tune a
> single flat colour; choose one colour model or the other. (The swatch is still
> exposed — it backs shader uniforms — it just doesn't change the look while a ramp is
> active.)

You **cannot add custom exposed parameters** — the list is template-fixed. A
custom tunable must be a compile-time define or a shader edit (and then it is NOT
on the panel; tell the user so).

## 4. What stays compile-time (NOT on the panel)

Most notably PhysicsMesh's physics material: `GRAVITY_Y`, `RESTITUTION`,
`FRICTION`, `PARTICLE_RADIUS`, `GROUND_Y`, `SHAPE_STIFFNESS`, `FRACTURE_*`,
`SCALE_START/END`, plus every `reserved_defines` entry. (Exception: the flipbook
sheet tokens are compile-time too, but get a dedicated panel group that rewrites
the package and recompiles — see §5c.) If the user asks to "make
it bouncier" on an existing PhysicsMesh effect, that is an `edit` (defines change →
reimport), not a panel action — set expectations accordingly.

## 5. Resource conventions (they become pickers — keep them clean)

- Always declare resources through `shared_resources` + `{ref}` — every bound
  resource becomes a panel picker the user can swap later (persistent: the swap
  rewrites the package and reimports; your `shared_resources` keys are preserved).
- Bind an OPTIONAL `material` on the three mesh templates when the user wants real
  shading (PBR etc. — see StandardMesh §3.2 "Optional: bind a real editor
  material"). Even when you don't, the Material picker shows as `None` so the user
  can add one later — your generated unlit look is the `None` state.
- StandardAnimatedMesh: `mesh` + `animation` must be sub-assets of the SAME model.
  If the user later swaps them into a mismatched pair, the effect degrades to a
  STATIC mesh with a panel warning ("Animation disabled…") — the import never
  fails; fixing either resource restores the animation.

### 5a. Compute-stage samplers — EVERY sampler must route through resources

Any texture a compute stage samples (`MaskTex` spawn gating / colour bake, an
`sdfTexture` collider's `sampler3D`, …) MUST be declared as
`uniforms.<init|update>[] = {name, type:"Texture", resource:"<key>"}` with the
key bound in `resources` → `shared_resources`. That is what makes it appear as a
swappable picker (panel group "Sampling"). A sampler bound any other way can
never be replaced by the user — treat that as an authoring bug.

### 5b. Emission shape (`emit_source`) — declare the source, the server samples

To emit on a mesh surface, declare ONLY `runtime.emit_source` + the source mesh as
a resource. **The server samples the mesh and bakes `emit_points` for you** at
add_vfx_source / edit_vfx_source time — you never sample the mesh or write
`emit_points` yourself (see StandardQuad.md §3.0):

```json
"resources": {"emesh": {"ref": "esrc"}},
"runtime": {
  "emit_source": {"resource": "emesh", "count": 64, "mode": "surface", "scale": 2.0}
}
```
(`esrc` in `shared_resources` = an FBX model's GUID; `emesh` is the resource key.)
With `emit_source` present the panel also shows an **Emission Mesh** picker; a user
swap re-samples the new mesh's surface automatically. Source must be a binary FBX.

### 5c. Flipbook (sprite-sheet) panel

Author all six sheet tokens in `defines` exactly as the flipbook recipe says
(`SHEET_COLS/SHEET_ROWS/TOTAL_FRAMES/SHEET_W/SHEET_H/FPS` — measured, never
guessed). The panel then exposes the three a human should touch: **Sheet
Columns / Sheet Rows / Playback FPS**. The rest is automatic: editing a grid
count re-derives `TOTAL_FRAMES = COLS×ROWS` in the same write; swapping the
sheet texture (the `Texture` picker) auto-updates `SHEET_W/SHEET_H` from the
new texture's pixel size. Partial sheets (last row not full) need a direct
`TOTAL_FRAMES` define edit via `edit_vfx_source` — the panel assumes full grids.

### 5d. Conform to SDF (`runtime.conform`) — particles assemble into a shape

`runtime.conform` is the port of VFX Graph's **Conform to SDF** force: it pulls
particles onto the iso-surface of a baked signed-distance VOLUME texture (.vf /
`Texture3D`) so a particle cloud forms an arbitrary shape. StandardQuad /
StandardMesh / StandardAnimatedMesh only (the marker lives in their
`update.comp`; PhysicsMesh ignores it).

The SDF volume is just a compute-stage sampler, so it follows §5a — declare it
as an `update`-stage Texture uniform + a `Texture3D` resource and it becomes a
swappable **Sampling** picker for free:

```json
"resources": {"sdfVol": {"ref": "shape_sdf"}},
"uniforms":  {"update": [{"name": "SDF", "type": "Texture", "resource": "sdfVol"}]},
"runtime":   {"conform": [{
  "type": "sdf", "sampler": "SDF",
  "center": [0, 0, 0], "scale": [30, 30, 30],
  "speed": 5, "force": 20, "distance": 0.1, "stickiness": 50
}]}
```

(`shape_sdf` in `shared_resources` = the `.vf` Texture3D GUID; `sampler` MUST
equal the `uniforms.update` Texture `name`.) `center`/`scale`/`orientation`
place the SDF box in the emitter's LOCAL space (`scale` = full box size).
`speed`/`force`/`distance`/`stickiness` are the Graph defaults shown above —
omit to accept them; they're baked into the shader (not panel params). The user
can swap the **SDF** picker to re-shape live. Give the particles some initial
spread (e.g. a `PositionSphere`-style init or `emit_points`) so they have
somewhere to converge FROM, and a low `GRAVITY` so the conform force dominates.

## 6. Panel behaviors worth telling the user about (when relevant)

- Edits to init-stage params (speed / lifetime / colors / spawn radius) affect
  **newly spawned** particles; live particles finish their life on old values.
- Editing a **bound material's own properties** (its color/texture/macros on the
  material asset) auto-refreshes the particle effect within ~1s.
- A failed or degraded import NEVER blanks the panel: the user sees the last-good
  state plus a one-line warning banner; every swap is safely retryable.
