---
name: Lifecycle
description: APJS脚本组件的生命周期： 编写 BasicScriptComponent 脚本，说明生命周期执行顺序、初始化时机、监听器清理和 @serializeProperty 引用的安全用法。
---

# Script Lifecycle

All user scripts must extend `APJS.BasicScriptComponent` and use the `@APJS.component()` decorator (or just `@component()` with the APJS import).

## Script Template

APJS and `@component()` are globally available — do NOT use `import APJS from 'APJS'`.

```typescript
@component()
export class MyScript extends APJS.BasicScriptComponent {
  onStart(): void {
    // Called once before the first frame update
  }

  onUpdate(deltaTime: number): void {
    // Called once per frame. deltaTime is in seconds.
  }

  onLateUpdate(deltaTime: number): void {
    // Called after all onUpdate calls in the frame
  }

  onDestroy(): void {
    // Called when the script is destroyed. Clean up event listeners here.
  }
}
```

## Lifecycle Methods

| Method | When Called | Use For |
|--------|-----------|---------|
| `onStart()` | Once, before first frame | Initialization, getting component references, registering event listeners |
| `onUpdate(deltaTime)` | Every frame | Continuous updates, frame-based animation, input polling |
| `onLateUpdate(deltaTime)` | Every frame, after all onUpdate | Camera follow, position corrections after physics |
| `onDestroy()` | When script is destroyed | Cleaning up event listeners, releasing resources |
| `onEnable()` | When component is enabled | Re-registering listeners |
| `onDisable()` | When component is disabled | Pausing behavior |
| `onInit()` | Before onStart | Early initialization |

## Rules

1. **MUST** use `@component()` decorator on the class (or `@APJS.component()`)
2. **MUST** extend `APJS.BasicScriptComponent`
3. **MUST** clean up event listeners in `onDestroy()` — failing to do so causes memory leaks
4. `deltaTime` is in seconds (e.g., ~0.016 for 60fps)
5. Access the owning SceneObject via `this.getSceneObject()`
6. Access components via `this.getSceneObject().getComponent("ComponentType") as APJS.ComponentType`
7. **No `APJS.Time` API** — there is no `APJS.Time.time` or equivalent. For all timing (elapsed time, reaction timers, cooldowns), accumulate `deltaTime` in `onUpdate()`:
   ```typescript
   private elapsed: number = 0;
   onUpdate(deltaTime: number): void {
     this.elapsed += deltaTime; // elapsed time in seconds since start
   }
   ```
8. **No `setTimeout` / `setInterval` / `Promise`** — these browser/Node APIs do not exist in APJS. Use `onUpdate(deltaTime)` with frame-based timers for delays and intervals.
9. **No ES6 collections (`Set`, `Map`, `WeakMap`, `Promise`)** — APJS target does not support modern JS collections. Use arrays and boolean flags instead:
   ```typescript
   // WRONG — compile error
   private hitTargets: Set<string> = new Set();
   // CORRECT — use array or boolean flags
   private hitTargets: string[] = [];
   ```
10. **Use `private static readonly` for class-level constants** — state IDs, durations, colors, and other invariants belong on the class, not on each instance. Reference them as `ClassName.FIELD`:
   ```typescript
   @component()
   export class MyGame extends APJS.BasicScriptComponent {
     private static readonly STATE_IDLE = 0;
     private static readonly STATE_PLAYING = 1;
     private static readonly FADE_DURATION = 0.35;
     private static readonly WHITE = new APJS.Color(1, 1, 1, 1);

     private currentState: number = MyGame.STATE_IDLE;

     onUpdate(deltaTime: number): void {
       if (this.currentState === MyGame.STATE_PLAYING) { /* ... */ }
     }
   }
   ```
   Use instance-level `private readonly` only for per-instance values (e.g., a serialized config wired in by the editor).

## @serializeProperty — Binding External Objects

Use `@serializeProperty` to bind references to other SceneObjects set via `set_component` after script creation.

```typescript
@serializeProperty
private scoreText: APJS.SceneObject;

@serializeProperty
private targetObjects: APJS.SceneObject[] = [];
```

### CRITICAL: Null Guard Required

`@serializeProperty` fields may be **null in `onStart()`** if the binding is set after the script is attached. This is the #1 cause of `cannot read property 'getComponent' of null` errors.

**Pattern: Lazy initialization in onUpdate**
```typescript
@serializeProperty
private scoreText: APJS.SceneObject;

private textComp: APJS.Text | null = null;
private initialized: boolean = false;

onUpdate(deltaTime: number): void {
  // Lazy init — wait until serializeProperty is resolved
  if (!this.initialized && this.scoreText) {
    this.textComp = this.scoreText.getComponent("Text") as APJS.Text;
    this.initialized = true;
  }
  if (!this.initialized) return;

  // Safe to use this.textComp here
}
```

**Why this happens**: In the current script-create flow, MCP creates or attaches the script component first and only then wires `@serializeProperty` fields via `set_component`. That means the binding can happen after the script's `onStart()` has already run, so the field is still null at `onStart()` time. This still happens through `edit_by_dsl` with the `add_script` command_type, so the same ordering trap applies to the current script-creation flow.

**Rule**: NEVER call `.getComponent()` on a `@serializeProperty` field in `onStart()`. Use lazy init in `onUpdate()` with a null guard.

### Updating an existing script file

Before using the script-create flow below, decide whether you're creating a new file or updating an existing one:

- If the target script file already exists, replace it with
  `edit_by_dsl(edit_script)` using its Script resource GUID, check the compilation result returned
  by the command, then run `get_script_logs()` as needed
- Use `add_script` only for first-time creation of a brand-new script file
- Do **not** create numbered variants like `FooV2.ts`, `FooV3.ts`, `FooNew.ts`, or `FooFinal.ts` just to bypass an earlier version; keep the same file/class unless the user explicitly asked for a parallel variant

### Wiring @serializeProperty via MCP

For the current script-create flow, wire each `@serializeProperty` field to its target object only after the script component exists. Here `add_script` means the `edit_by_dsl` command_type, not a standalone MCP tool:

```
1. add_script(script_name, code)                → create SourceFile
2. add_component(scene_object, type: className) → attach; response includes component GUID
3. set_component(
     guid: <script_component_guid>,
     properties: {
       "earthObj": { "guid": "<earth_guid>", "type": "SceneObject" },
       "bgTex":    { "guid": "<texture_guid>", "type": "Texture2D" }
     }
   )
```

- The property name must match the `@serializeProperty` field name in the script (e.g., `earthObj`)
- **GUID references on script components MUST include `"type"`** — script properties are user-defined so types cannot be auto-inferred (unlike built-in components):
  - `APJS.SceneObject` → `{ "guid": "...", "type": "SceneObject" }`
  - `APJS.Texture` → `{ "guid": "...", "type": "Texture2D" }`
  - `APJS.Transform` → `{ "guid": "...", "type": "Transform" }`
- For arrays (`@serializeProperty targets: SceneObject[] = []`), value is `[{ "guid": "<guid1>", "type": "SceneObject" }, ...]`
- Number/boolean/string values are passed directly — types auto-inferred as usual

## Common Patterns

### Getting references in onStart
```typescript
onStart(): void {
  // SAFE: this.getSceneObject() is always available — it's the object the script is attached to
  const transform = this.getSceneObject().getTransform();
  const meshRenderer = this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;

  // UNSAFE: do NOT access @serializeProperty objects here — they may be null!
}
```

### Frame-based animation in onUpdate
```typescript
private elapsed: number = 0;

onUpdate(deltaTime: number): void {
  this.elapsed += deltaTime;
  const transform = this.getSceneObject().getTransform();
  // Rotate 90 degrees per second around Y axis
  const currentEuler = transform.localEulerAngles;
  transform.localEulerAngles = new APJS.Vector3f(currentEuler.x, currentEuler.y + 90 * deltaTime, currentEuler.z);
}
```
