---
name: SerializeProperty
description: 脚本组件的属性绑定及暴露 - 通过 @serializeProperty 把场景对象、资产和可调参数暴露给编辑器，说明支持类型、Inspector 控件、数组绑定和初始化限制。
---

# @serializeProperty — Editor Bindings

The `@serializeProperty` decorator exposes class fields as configurable slots in the editor. This is the **primary way** to connect scripts to scene objects, textures, and configuration values.

## Basic Usage

```typescript
@component()
export class MyScript extends APJS.BasicScriptComponent {
  @serializeProperty
  private target: APJS.SceneObject; // Drag a scene object here in editor

  @serializeProperty
  private speed: number = 5; // Number field with default

  @serializeProperty
  private auto: boolean = true; // Boolean toggle

  @serializeProperty
  private label: string = 'Hello'; // Text input
}
```

## Supported Types

`@serializeProperty` reliably round-trips for **scalars, the SceneObject hierarchy, and asset-resource references**. Component-subclass references (e.g. `APJS.Camera`, `APJS.RigidBody`) are **NOT** supported — see "Unsupported types" below.

| TypeScript Declaration                    | Wire Type         | Editor UI                        |
| ----------------------------------------- | ----------------- | -------------------------------- |
| `number`                                  | Number            | Number input                     |
| `boolean`                                 | Boolean           | Toggle                           |
| `string`                                  | String            | Text input                       |
| `APJS.Color`                              | Color             | Color picker                     |
| `APJS.Vector2f` / `Vector3f` / `Vector4f` | Vector struct     | Multi-axis input                 |
| `APJS.Quaternionf`                        | Quaternion struct | Rotation input                   |
| `APJS.SceneObject`                        | SceneObject       | Object slot (drag & drop)        |
| `APJS.Transform`                          | Transform         | Transform slot                   |
| `APJS.Texture`                            | Texture           | Texture slot                     |
| `APJS.Material`                           | Material          | Asset slot                       |
| `APJS.JsonAsset`                          | JsonAsset         | Asset slot (drag a `.json` file) |
| `APJS.AudioAsset`                         | AudioAsset        | Asset slot (drag an `.mp3`)      |
| `APJS.SceneObject[]`                      | Array             | Object array                     |
| `APJS.Texture[]`                          | Array             | Texture array                    |

`APJS.Texture` can reference `Texture2D`, `AIDrawTexture`, `AnimatedTexture`, and other texture resources; these examples are not exhaustive, so choose the resource that matches the property's actual meaning.

## Unsupported types (silently revert to null)

The following TypeScript field types **look** valid in the editor — `set_component` returns success — but the wired GUID does not persist; subsequent `inspect()` and runtime reads see `null`. **Do not use these as `@serializeProperty` types**:

- **Component subclasses** — `APJS.Camera`, `APJS.RigidBody`, `APJS.RigidBody2D`, `APJS.Image`, `APJS.Text`, `APJS.Animator`, `APJS.AudioComponent`, `APJS.MeshRenderer`, `APJS.BoxCollider`, every other `Component`-derived class.
- **`APJS.Prefab` for Screen-Image-derived prefabs.** 3D-mesh prefabs round-trip in current builds, but a Prefab created from a Screen Image / 2D UI subtree silently nulls the wire on save. Confirmed during APJS-tutorial pilot (P4 Physics 2D).

### Workaround: serialize the SceneObject, look up the component at runtime

This is the pattern used across every verified worked example (`ar_plane_tap_to_place`, `joystick_drag_input`, `tile_tap_detection`, the P1–P5 tutorials):

```typescript
// WRONG — Component-subclass field, wiring silently nulls
@serializeProperty cam!: APJS.Camera;
@serializeProperty rb!: APJS.RigidBody;

// CORRECT — host SceneObject + getComponent at runtime
@serializeProperty
@tooltip("SceneObject that owns the Camera component.")
private camObj: APJS.SceneObject;

@serializeProperty
@tooltip("SceneObject that owns the RigidBody component.")
private bodyObj: APJS.SceneObject;

private cam!: APJS.Camera;
private rb!: APJS.RigidBody;

onStart(): void {
  this.cam = this.camObj.getComponent("Camera") as APJS.Camera;
  this.rb = this.bodyObj.getComponent("RigidBody") as APJS.RigidBody;
}
```

For Screen-Image-derived prefabs that won't wire as `APJS.Prefab`, build a **hidden template** SceneObject with the same component stack, wire it as `APJS.SceneObject`, and clone at runtime via `SceneObject.clone()`:

```typescript
@serializeProperty template!: APJS.SceneObject;  // hidden source object

private spawn(): APJS.SceneObject | null {
  const inst = this.template.clone();
  if (!inst) return null;
  inst.setEnabledInHierarchy(true);  // clone inherits source's hidden state
  // …position, kick, etc.
  return inst;
}
```

The clone gets a deep copy of all components on the template, including `RigidBody2D`, `BoxCollider2D`, and any wired `PhysicsMaterial`. See `APJS/examples/object_pool_clone.json`.

### Reading a JsonAsset

`APJS.JsonAsset` exposes a single read-only getter, `.json`, that returns the parsed payload as `any`. Always coalesce so a missing or empty asset doesn't throw.

```typescript
@serializeProperty
private questionData: APJS.JsonAsset;

private parsed: any;

onStart(): void {
  this.parsed = this.questionData?.json ?? {};
  // Now treat `this.parsed` like any plain object — index by key, iterate arrays, etc.
}
```

**Why this matters:** the editor unblocks parallel work (a designer authors questions / level data in JSON, the script consumes it). Schema changes don't recompile — only the JSON asset changes. The 1 KB CloudData cap doesn't apply here; JsonAssets can be as large as the asset bundle allows.

## Numeric parameter constraints (REQUIRED for creator-editable numbers)

Every numeric `@serializeProperty` is an Inspector box a creator can type **any** value into — including `99999999`, negatives, or decimals where whole units are expected. Unbounded, these make the effect behave meaninglessly. **Constrain every numeric `@serializeProperty` on two layers:**

**1. Editor constraint — pick `@slider` or `@spinBox`** (with a `@tooltip` stating the range; choose min/max from what's meaningful for the effect, not the type's full range):

| Field kind                                                           | Decorator                  | Example                 |
| -------------------------------------------------------------------- | -------------------------- | ----------------------- |
| Continuous / tunable feel (threshold, speed, scale, intensity)       | `@slider(min, max, step)`  | `@slider(0.1, 30, 0.1)` |
| Integer / discrete / bounded count (minutes, day index, −1/0/1 mode) | `@spinBox(min, max, step)` | `@spinBox(0, 99, 1)`    |

**2. Runtime clamp — defense in depth (do NOT skip).** The widget guides _new_ input, but a serialized value can still be out of range via existing saved data, copy/paste, or manual edits. Validate every numeric field before use:

```typescript
@serializeProperty
@tooltip("Whole minutes, 0–99.")
@spinBox(0, 99, 1)
private startMin: number = 10;

private safeStartMinutes(): number {
  const v = this.startMin;
  if (!Number.isFinite(v)) return 10;                 // NaN / Infinity → default
  return Math.floor(Math.min(99, Math.max(0, v)));    // clamp to range, floor integers
}
```

Patterns: `Number.isFinite(v) ? v : DEFAULT`; `Math.min(max, Math.max(min, v))` to clamp; `Math.floor` for integer-only; cross-field caps where one bound depends on another (e.g. `Math.min(neutralThreshold, rollThreshold)`). Log once when a value is normalized so QA can see it.

> Numeric `@serializeProperty` fields should usually pair with `@slider` or `@spinBox` so creators get bounded controls. Apply this rule manually during native edits and any future script-creation flow.

## Keep creator-facing script parameters concise

`@serializeProperty` is not a dumping ground for every tuning number in a script. A GameManager with dozens of numeric fields becomes impossible for creators to understand, and it often hides layout values that should have been authored visually in the scene.

Keep field names short because the Inspector has a narrow label column. Treat the field name as a compact label and the `@tooltip` as the long-form explanation:

| Prefer | Avoid |
| ------ | ----- |
| `durationSec` | `gameDurationSeconds` |
| `winGoal` | `firstToRoundWins` |
| `holdSec` | `feedbackHoldSeconds` |
| `btnNormal` | `buttonNormalTexture` |
| `startBtn` | `startButtonObject` |

Common abbreviations are fine when obvious (`sec`, `ms`, `min`, `max`, `btn`, `img`, `tex`, `obj`). Do not compress meaning into unreadable names like `tLenS` or `spwnIvl`.

Use this split:

| Value kind                                   | Put it where                                                  | Example                                                               |
| -------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------- |
| External object / asset references           | `@serializeProperty`                                          | ball object, result title, retry button, blocker array                |
| Broad creator-facing feel knobs              | `@serializeProperty` with tooltip + slider/spinBox            | kick speed, blocker range, countdown step seconds                     |
| Scene layout that does not change at runtime | Scene components, read once from `ScreenTransform` / Collider | blocker row Y, ball start position, goal bounds, collider size        |
| Internal algorithm invariants                | private readonly or derived locals                            | cooldown seconds, row speed ratios, damping constants, safety margins |

Expose **3–8 numeric tuning knobs** per script — this is a budget, not a target; fewer significant knobs beat many marginal ones. Exceed 8 only when the user explicitly asked for that many controls. Apply the same standard during native edits: merge detailed constants into broad knobs when they are perceived as one behavior. One `blockerMoveSpeed` plus row ratios is better than exposing three row speeds; one `reboundStrength` is better than exposing restitution, tangent damping, push, and curve impulse separately. Never duplicate the same knob per difficulty variant (`easySpeed` / `mediumSpeed` / `hardSpeed`) — one knob plus a difficulty `@dropDown` or a private ratio table covers it.

Do not hardcode scene-authored positions in script. If a designer should be able to move a blocker row, goal, ball start, button, or hit zone in the editor, the script should read that object's component values:

```typescript
@serializeProperty
private lowerBlocker: APJS.SceneObject;

private lowerY = 0;
private lowerHalfW = 1;
private lowerHalfH = 1;

private readSceneAuthoredLayout(): void {
  const st = this.lowerBlocker.getComponent("ScreenTransform") as APJS.ScreenTransform;
  const col = this.lowerBlocker.getComponent("BoxCollider2D") as APJS.BoxCollider2D;
  this.lowerY = st.anchoredPosition.y;
  this.lowerHalfW = col.size.x * st.pixelsPerUnit * 0.5;
  this.lowerHalfH = col.size.y * st.pixelsPerUnit * 0.5;
}
```

Private constants are fine for values that only make sense inside the algorithm and should not be tweaked independently. Add a short comment before the block when the constants preserve a tuned feel.

## Optional Decorators

```typescript
@serializeProperty
@tooltip("Movement speed in units per second")
private speed: number = 5;

@serializeProperty
@slider(0, 100, 1)                         // continuous drag — best for tunable feel values
private health: number = 100;

@serializeProperty
@spinBox(1, 100, 1)                        // up/down stepper — best for integer counts / day indices
private startDay: number = 1;

@serializeProperty
@dropDown([
  ["Easy", 0],
  ["Medium", 1],
  ["Hard", 2],
])                                          // predefined choices, returns the second element of the pair
private difficulty: number = 1;

@serializeProperty
@textArea(5)                                // multi-line input, height in lines (default 3)
private storyIntro: string = "";

@header("Movement Settings")               // visual section header — improves dense inspectors
@serializeProperty
private moveSpeed: number = 5;

@serializeProperty
private enableEffect: boolean = false;

@serializeProperty
@showIf("enableEffect", true)              // hidden in inspector unless `enableEffect === true`
private effectIntensity: number = 0.5;

@separator()                                // horizontal rule between groups

@groupBegin("Visual Settings")
@serializeProperty
private mainColor: APJS.Color = new APJS.Color(1, 1, 1, 1);

@serializeProperty
private glowIntensity: number = 0.5;
@groupEnd()
```

> **Field order**: declaration order is Inspector order. Declare groups consistently as swappable Theme & Assets → numeric Gameplay Tuning → Advanced — Scene Wiring.

### Choosing the Inspector control

Every serialized field maps to one standard Inspector input. Pick the declaration by what KIND of value the creator edits — the control follows automatically:

| Value kind | Declare as | Inspector control | Example |
| --- | --- | --- | --- |
| Whole number, count, index, degrees (retry limit, rounds, rotation) | `number` + `@spinBox(min, max, step)` | Stepper arrows + direct typing | `@spinBox(0, 10, 1) retryLimit = 3;` |
| Precise continuous decimal, especially normalized 0–1 (opacity, animation speed, sensitivity) | `number` + `@slider(min, max, step)` with a fine step | Drag slider with live feedback | `@slider(0, 1, 0.05) opacity = 0.5;` |
| Position / offset / any multi-axis value | `APJS.Vector2f` / `APJS.Vector3f` | Per-axis X/Y/Z labeled inputs | `offset: APJS.Vector2f;` |
| A few fixed choices (difficulty, mode, preset style) | `number` + `@dropDown([[label, value], …])` | Labeled dropdown | `@dropDown([["Tap", 0], ["Hold", 1]]) inputMode = 0;` |
| Swappable asset (texture, audio, prefab) | Typed resource ref: `APJS.Texture`, `APJS.AudioAsset`, `APJS.Prefab` (or arrays) | Native asset picker | `heroTex: APJS.Texture;` |
| Color | `APJS.Color` | Swatch + hex input | `tint: APJS.Color = new APJS.Color(1, 1, 1, 1);` |
| Optional feature on/off | `boolean` | Checkbox toggle | `enableCombo: boolean = false;` |
| Long free text (story intro, quiz question) | `string` + `@textArea(lines)` | Multi-line text box | `@textArea(5) storyIntro: string = "";` |

Selection rules:

- **Never make a creator guess an encoding.** A fixed set of options is a `@dropDown` with plain-language labels — not a bare number. On/off is a `boolean` checkbox — not `0/1` or `"on"/"off"` strings. A color is `APJS.Color` — not separate r/g/b/a numbers or a hex string. An asset is a typed ref — not a path or GUID string.
- **Keep multi-axis values as vectors.** One `APJS.Vector2f` renders as labeled X/Y inputs; splitting it into `posX`/`posY` numbers loses the pairing.
- **`@spinBox` vs `@slider`**: an integer count like "starting day = 7" is much faster to type/step than dragging a slider to land on 7 exactly; a normalized decimal like animation speed is faster to feel out by dragging than to type.
- **Toggles gate their extras.** When a `boolean` enables an optional mini-feature, put its dependent fields behind `@showIf("<flag>", true)` so the Inspector stays short until the feature is on.

## Critical Rule: Always Use @serializeProperty for External References

**NEVER** hardcode object names or use `getChild("SomeName")` for objects that should be configurable:

```typescript
// WRONG — hardcoded name, breaks if object is renamed
onStart(): void {
  const obj = this.getSceneObject().getChild("ScoreText");
}

// CORRECT — editor binding, resilient to renames
@serializeProperty
@tooltip("Score text object.")
private scoreObj: APJS.SceneObject;
```

## Getting Components from Serialized Objects

Get component references in `onStart()`, not in the field declaration:

```typescript
@serializeProperty
@tooltip("Score text object.")
private scoreObj: APJS.SceneObject;

@serializeProperty
@tooltip("SceneObject that owns the Camera component.")
private camObj: APJS.SceneObject;

private scoreText: APJS.Text;
private camera: APJS.Camera;

onStart(): void {
  this.scoreText = this.scoreObj.getComponent("Text") as APJS.Text;
  this.camera = this.camObj.getComponent("Camera") as APJS.Camera;
}
```

## Array Bindings

Use arrays for multiple objects of the same kind:

```typescript
@serializeProperty
private targets: APJS.SceneObject[] = [];  // Multiple objects

@serializeProperty
private textures: APJS.Texture[] = [];     // Multiple textures

onStart(): void {
  for (const target of this.targets) {
    target.setEnabledInHierarchy(false);  // Hide all initially
  }
}
```

## Rules

1. **MUST** use `@serializeProperty` for all external object/texture references
2. **MUST** initialize arrays with `= []` (not undefined)
3. **MUST** get component references in `onStart()`, not at field declaration
4. Provide sensible defaults for number/boolean/string properties
5. Keep serialized field names short enough for the Inspector label column; use `@tooltip()` for the full explanation
6. Use `@slider()` for bounded numeric values
7. Group related properties with `@groupBegin()`/`@groupEnd()`
8. Keep creator-facing tuning fields concise; put stable layout in scene components and read it at runtime

## CRITICAL: No `null` — strictNullChecks is ON

The APJS compiler uses `"strict": true` (which includes `strictNullChecks`). Assigning `null` to a non-nullable type is a **compile error**.

```typescript
// WRONG — compile error TS2322: Type 'null' is not assignable to type 'SceneObject'
@serializeProperty
private target: APJS.SceneObject = null;

// CORRECT — no initializer needed (strictPropertyInitialization is OFF)
@serializeProperty
private target: APJS.SceneObject;
```

Non-serialized reference fields should also omit `null`:

```typescript
// WRONG
private scoreText: APJS.Text = null;

// CORRECT — use definite assignment assertion
private scoreText!: APJS.Text;
```

**Reset pattern**: Do NOT null out `@serializeProperty` references. Use boolean flags instead:

```typescript
// WRONG — compile error
onReset(): void {
  this.ballObject = null;
}

// CORRECT — use state flags
private isLaunched: boolean = false;

onReset(): void {
  this.isLaunched = false;
  // Reset transform, not the reference
  this.ballObject.getTransform().localPosition = this.startPos;
}
```
