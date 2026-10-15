---
name: PostProcess
description: 后处理效果：使用内置对象搭建 Bloom、暗角、色差、扭曲等屏幕效果，并在脚本中调节或开关。每种效果都要单独创建，并放在专用的 Post Effect 渲染组中。
---

# PostProcess

`PostProcess` is a component that hosts an ordered chain of `PostEffect`
sub-objects (`Bloom`, `Vignette`, `ChromaticAberration`, `Distort`,
`BokehBlur`, `Fxaa`, `Grain`, `LensFlare`, `MotionBlur`, `Custom`). At
runtime each effect is exposed via a typed accessor on the component:
`pp.bloom`, `pp.vignette`, `pp.chromaticAberration`, `pp.distort`, etc.
Each accessor is `null` if the effect is not instantiated, otherwise a
live `PostEffect` subclass instance with `.enabled` plus its own
properties.

## CRITICAL #1 — the render-group gotcha

The PostProcess pipeline only renders to the screen when its host
camera lives in a **dedicated `Post Effect` render group**. Adding
`PostProcess` as a component to a regular scene Camera (in the General
group) compiles cleanly and the script's `pp.bloom.enabled = true`
flag flips, but the engine never composites the post-process pass onto
the screen — the user sees no visual change.

The required structure is:

- **General render group**: a normal Camera that renders the 3D scene.
- **Post Effect render group**: a separate Camera carrying the `PostProcess`
  component. Its `inputTexture` reads the General-group output; its
  `renderTexture` is the special `SceneOutputRT` ("Final Render Output").

The editor sets this split up automatically when you create one of the
post-process builtin objects in a project:

```
add_builtin_object(object_type="Bloom")
  → creates a SceneObject with Camera + PostProcess in a "Post Effect" render group.
```

## CRITICAL #2 — one builtin per effect (the postProcessList constraint)

`PostProcess.postProcessList` is the array of effect names that *appears*
to control which typed accessors (`pp.bloom`, `pp.vignette`, …) are
non-null at runtime. **In practice it is editor-time only.** The engine
reads it once when the SceneObject is created and instantiates sub-effects
based on what's there. Mutating it later via `set_component` updates the
array but does NOT retro-instantiate the new sub-effects:

```ts
// Project authored with: add_builtin_object("Bloom")
//   → postProcessList: ["Bloom"]
//   → pp.bloom is alive, pp.vignette / pp.distort / … are all null.
//
// Then via DSL:
//   set_component(pp_guid, postProcessList: ["Bloom", "Vignette", "Distort", ...])
//   → postProcessList field updates as expected
//   → pp.bloom STAYS alive (already instantiated)
//   → pp.vignette / pp.distort STAY NULL (silent no-op on every assignment)
```

**The practical rule: one PostProcess builtin per effect you want to demo.**
If you need Bloom, use `add_builtin_object("Bloom")`. If you need
Vignette, use `add_builtin_object("Vignette")` instead. Each creates
its own Camera + PostProcess SceneObject in its own Post Effect render
group, and only the matching typed accessor is alive on that PostProcess.

To switch which effect a script demos, **rebuild the SceneObject with
the matching builtin name and access the matching accessor**:

| Builtin name | Live accessor |
|---|---|
| `add_builtin_object("Bloom")` | `pp.bloom: APJS.Bloom` |
| `add_builtin_object("Vignette")` | `pp.vignette: APJS.Vignette` |
| `add_builtin_object("Chromatic Aberration")` | `pp.chromaticAberration: APJS.ChromaticAberration` |
| `add_builtin_object("Distort")` | `pp.distort: APJS.Distort` |
| `add_builtin_object("Bokeh Blur")` | `pp.bokehBlur: APJS.BokehBlur` |
| `add_builtin_object("Grain")` | `pp.grain: APJS.Grain` |
| `add_builtin_object("Lens Flare")` | `pp.lensFlare: APJS.LensFlare` |
| `add_builtin_object("Motion Blur")` | `pp.motionBlur: APJS.MotionBlur` |
| `add_builtin_object("Filter")` | LUT-based color grading via `FilterV2` (different component) |
| `add_builtin_object("AI Filter")` | AI stylization via `AIFilter` (different component) |

## What works (and what doesn't) via MCP

**Reliable starting points:**

1. **`add_builtin_object("<EffectName>")` in a project that already has
   the default scene Camera.** This is the canonical setup. The General
   Camera renders the 3D scene; the PostEffect-group Camera composites
   the post-process pass; the matching `pp.<effect>` accessor is alive.
2. **One effect per PostProcess SceneObject.** If a demo needs Bloom +
   Vignette, add two separate builtins. They live in two separate
   Post Effect render groups but compose correctly because each writes
   to the same `Final Render Output` SceneOutputRT in render-group order.

**Don't attempt:**

- Adding `PostProcess` as a component to an existing scene Camera in the
  General group. The script-side API works (you can mutate
  `bloom.intensity`, etc.) but visually nothing renders.
- Mutating `postProcessList` to add additional effect names after the
  PostProcess is created. The new sub-effects stay null and every
  property assignment silently no-ops.
- Manually wiring `Camera.renderTexture` and `Camera.inputTexture`
  between a General-group Camera and a Post Effect-group Camera. The
  texture types involved (`SceneOutputRT`, `ScreenTexture`) are
  special — `Camera.renderTexture` rejects regular `Render Texture`
  resources, and there's only one `SceneOutputRT` ("Final Render
  Output") per project.

If a script's `pp.<effect>` accessor is null at runtime when you expect
it to be alive, **do not try to fix it from script**. Re-author the
SceneObject with the matching builtin name; that's the only path that
produces a live accessor.

## Runtime API — the canonical pattern

A script attached to the same SceneObject as the `PostProcess` component
(the Bloom-spawned camera) accesses the live sub-effect, configures
properties once, then toggles `.enabled` per state:

```typescript
@component()
export class FilterStack extends APJS.BasicScriptComponent {
  @serializeProperty statusText!: APJS.SceneObject;

  private pp!: APJS.PostProcess;
  private bloom!: APJS.Bloom;
  private inited = false;

  onUpdate(_dt: number): void {
    if (!this.inited) {
      // PostProcess and the script live on the same SceneObject —
      // a single getComponent resolves the chain.
      this.pp = this.getSceneObject().getComponent("PostProcess") as APJS.PostProcess;
      if (!this.pp) return;
      this.bloom = this.pp.bloom as APJS.Bloom;
      if (!this.bloom) {
        // Misconfiguration check — pp.bloom is null only when the
        // SceneObject was NOT created via add_builtin_object("Bloom"),
        // or when postProcessList was mutated post-creation.
        console.log("[Filter] pp.bloom is null — re-author the SceneObject via add_builtin_object('Bloom').");
        return;
      }

      // One-time tuning. Properties stay set when .enabled flips on/off.
      this.bloom.threshold = 0.2;
      this.bloom.intensity = 5;
      this.bloom.diffuse = 4.5;
      this.bloom.softKnee = 0.5;
      this.bloom.color = new APJS.Color(1.0, 0.9, 0.7, 1.0);

      this.inited = true;
    }
  }

  toggleBloom(on: boolean): void {
    if (!this.bloom) return;
    this.bloom.enabled = on;
  }
}
```

Same pattern for any other effect — replace `pp.bloom` with
`pp.vignette` / `pp.distort` / `pp.bokehBlur` / etc. Each accessor's
type is the matching `PostEffect` subclass with its own property surface.

## Per-effect property reference

| Effect | Useful runtime properties |
|--------|---------------------------|
| `Bloom` | `intensity`, `threshold`, `softKnee`, `clamp`, `diffuse`, `color`, `anamorphicRatio`, `fastMode` |
| `Vignette` | `power`, `contrast` |
| `ChromaticAberration` | `intensity` (`fastMode` and `spectralLUT` are deprecated) |
| `Distort` | `amplitude` (Vector2f), `frequency` (Vector2f), `offset` (Vector2f), `speed` (Vector2f), `barrelPower`, `rotation`, `zoom` |
| `Grain` | `strength`, `color`, `speed` |
| `BokehBlur` | `size`, `iterations`, `downsample`, `shape` (`BokehBlurShapeType.Circle` / `Hexagon`), `fastCircle` |
| `MotionBlur` | `intensity` |
| `LensFlare` | `intensity`, `position` (`Vector2f` in normalized 0–1 screen coords) |

Every effect derives from `PostEffect` and has an `enabled` flag.

## Sample tunings (lifted from upstream API examples)

Drop-in starting values for each effect:

```ts
// Bloom
bloom.threshold = 0.2;
bloom.intensity = 1.5;
bloom.diffuse = 4.5;
bloom.softKnee = 0.5;
bloom.color = new APJS.Color(1.0, 0.8, 0.6, 1.0);
bloom.fastMode = true;

// Vignette
vignette.power = 1.2;
vignette.contrast = 1.5;

// ChromaticAberration
chromaticAberration.intensity = 3;

// Distort
distort.barrelPower = -0.2;
distort.zoom = 0.2;
distort.amplitude = new APJS.Vector2f(0.1, 0.05);
distort.frequency = new APJS.Vector2f(8, 4);
distort.speed = new APJS.Vector2f(0.5, 0);

// BokehBlur
bokehBlur.size = 5;
bokehBlur.iterations = 3;
bokehBlur.shape = APJS.BokehBlurShapeType.Hexagon;
bokehBlur.downsample = 2;

// Grain
grain.strength = 0.5;
grain.color = 1.0;
grain.speed = 3.0;

// LensFlare
lensFlare.intensity = 0.8;
lensFlare.position = new APJS.Vector2f(0.7, 0.3);

// MotionBlur
motionBlur.intensity = 0.9;
```

## Rules

1. PostProcess only renders to the screen when its Camera is in a `Post Effect` render group. Don't add it as a component to a General-group Camera.
2. **One builtin per effect.** `add_builtin_object("<EffectName>")` is the only way to make `pp.<effectName>` non-null. Mutating `postProcessList` post-creation does NOT instantiate sub-effects.
3. To demo multiple effects, add multiple PostProcess builtins (one per effect). Each gets its own Post Effect render group; they compose in render-group order.
4. Wire the PostProcess camera so the script lives on the **same SceneObject** as the `PostProcess` component. `getSceneObject().getComponent("PostProcess")` then resolves the chain — no cross-object reference field needed.
5. If `pp.<effect>` is null at runtime, the SceneObject was misconfigured at authoring time. Don't try to fix it from script — re-author with the right builtin name.
6. If you can't get the pipeline to render at all (everything looks like baseline), check first whether `pp.<effect>.enabled` writes are silently no-op'ing because `pp.<effect>` is null. Add a `console.log` of `!!this.pp.<effect>` during init to confirm.
