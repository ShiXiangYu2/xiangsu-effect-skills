---
name: Prefab
description: Prefab创建和使用 - 把场景对象制作成 Prefab，并在运行时实例化和复用对象。涵盖 Prefab 与 clone() 对象池的选择、绑定、排序和重置问题。
---

# Prefab

A **Prefab** is a reusable scene-object template stored as a project asset. Instantiating a prefab spawns a fresh SceneObject with the same hierarchy, components, and property values as the original.

Use prefabs when you need **pools of repeated objects** — enemies, coins, obstacles, bullets. Authoring once and instantiating N times is faster than building each copy from scratch. Use `duplicate_scene_object` for one-off clones.

> Note: instances are auto-unpacked at spawn (see "Auto-unpack behavior" below) — editing the prefab asset later does **not** propagate to already-spawned instances.

## Object-Pool Sources: `Prefab` vs `clone()`

For gameplay work, the important distinction is the **source of pooled instances**:

- **JIT instantiate**: call `prefab.instantiate()` only when one new actor is needed
- **`Prefab`-based object pool**: pre-instantiate or grow a reusable pool whose members come from an `APJS.Prefab`
- **`clone()`-based object pool**: pre-create or grow a reusable pool whose members come from a hidden in-scene template `SceneObject`

Use a `clone()`-based object pool when:

- the source object already exists in the scene and does not need to become a persisted prefab asset
- the repeated actor is 2D / `Screen Image` / UI-derived and `@serializeProperty APJS.Prefab` is not a stable binding path in the current build
- you only need an effect-local template for the current game and do not need a reusable project asset

The acquire / release logic is the same in both patterns; only the source of the instances changes.

Default runtime path:

- for repeated runtime actors, wire a script field as `@serializeProperty APJS.Prefab`
- spawn with `prefab.instantiate(parent)`
- use `instantiate_prefab` only for a small number of build-time placements or prefab-content checks

## Two-step workflow

The canonical path uses DSL commands inside `edit_by_dsl`. `create_prefab_from_object` and `instantiate_prefab` are **command_type names inside the batch**, not standalone MCP tools.

1. **Build the source object** in the scene the way you want the prefab to look.
2. Run **`create_prefab_from_object`** in the batch → returns a prefab **asset GUID**.
3. Run **`instantiate_prefab`** with that asset GUID → returns a new **SceneObject GUID** per call.

> Important: the asset GUID (step 2) and the instance SceneObject GUIDs (step 3) are different kinds of GUIDs. `set_component` / `move_scene_object` work on the instance GUIDs; `inspect(guid)` on the asset GUID attaches `rootSceneObject` — the prefab's stored hierarchy with unified component names and mesh bounds. Pass `summary: true` when the prefab is deep and only the tree shape is needed.

## Pool of enemies — canonical example

```json
edit_by_dsl({
  intention: "Create 5 enemies from a single prefab for the level",
  commands: [
    { "command_type": "add_scene_object", "params": { "type": "Cube", "name": "Enemy" }, "alias": "src" },
    { "command_type": "set_component", "params": {
        "guid": { "$ref": "src", "component_type": "Transform" },
        "properties": { "localScale": { "x": 0.5, "y": 0.5, "z": 0.5 } } } },
    { "command_type": "create_prefab_from_object", "params": { "guid": { "$ref": "src" }, "consume_source": true }, "alias": "enemyPrefab" },

    { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "enemyPrefab" } }, "alias": "e1" },
    { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "enemyPrefab" } }, "alias": "e2" },
    { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "enemyPrefab" } }, "alias": "e3" },
    { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "enemyPrefab" } }, "alias": "e4" },

    { "command_type": "set_component", "params": {
        "guid": { "$ref": "e1", "component_type": "Transform" },
        "properties": { "localPosition": { "x": -4, "y": 0, "z": 0 } } } },
    { "command_type": "set_component", "params": {
        "guid": { "$ref": "e2", "component_type": "Transform" },
        "properties": { "localPosition": { "x": -2, "y": 0, "z": 0 } } } },
    { "command_type": "set_component", "params": {
        "guid": { "$ref": "e3", "component_type": "Transform" },
        "properties": { "localPosition": { "x":  2, "y": 0, "z": 0 } } } },
    { "command_type": "set_component", "params": {
        "guid": { "$ref": "e4", "component_type": "Transform" },
        "properties": { "localPosition": { "x":  4, "y": 0, "z": 0 } } } }
  ]
})
```

Each `instantiate_prefab` result is a new SceneObject — reposition it with a normal `set_component` on its Transform, just like any other object.

## Attaching instances to a specific parent

```json
{ "command_type": "instantiate_prefab", "params": {
    "guid": { "$ref": "enemyPrefab" },
    "parent": "<some-container-guid>"
  } }
```

`parent` may be a SceneObject GUID or a RenderGroup GUID. It must belong to the current scene.

## Finding existing prefabs in the project

If the user opens a project that already contains prefabs (authored earlier, or imported by a previous step), discover them before spawning:

```json
// Standalone MCP tool — not inside edit_by_dsl
list_resources({ type_filter: "Prefab" })
```

Response shape:
```json
{
  "totalCount": 1,
  "resources": {
    "Prefab": [
      { "guid": "r1", "name": "Bullet" }
    ]
  }
}
```

Pick a `guid` from `resources.Prefab[]` and feed it directly to `instantiate_prefab`:

```json
edit_by_dsl({ commands: [
  { "command_type": "instantiate_prefab", "params": { "guid": "r1" } }
] })
```

Use this flow whenever the user says *"use the existing prefab"*, *"spawn more of the X prefab"*, or *"make a pool of the cat"* — don't re-create something that already exists.

## Importing prefab packages

Library-based prefab-package import is not available through the current toolset. Use one of these instead:

- if the prefab already exists in the project, discover it with `list_resources({ type_filter: "Prefab" })`
- if it does not exist yet, create it from a scene object or import the underlying model/resource through the supported path first, then come back to this skill

## Auto-unpack behavior

`instantiate_prefab` currently **auto-unpacks** each spawned instance — the resulting SceneObject is a standalone copy of the prefab's hierarchy, not a live link back to the asset. Consequences:

- Editing the prefab asset later **does not** update already-spawned instances.
- Instances behave like any regular SceneObject and can themselves be passed to `create_prefab_from_object`.
- Prefabs are still the right choice for **spawn-time** deduplication (one source of truth at authoring, cheap fan-out at spawn). If you need "edit once, propagate to live instances", that's not currently supported through the DSL.

## Runtime instantiation (in scripts)

Use this when you need to spawn instances **while the effect is running** — bullets fired on tap, enemies appearing on a timer, fragments emitted on a hit. The DSL workflow above happens at build time and produces a fixed N instances; runtime instantiation produces them on demand from inside an APJS script.

### Default for 3D: just-in-time `prefab.instantiate()` per spawn

For most tap-driven 3D games (drop one item, again, again), **call `prefab.instantiate()` at the moment of spawn**. Each call returns a brand-new SceneObject — including a fresh `RigidBody` that is dynamic from frame 1 and ready to receive forces. No pool to manage, no `rb.static` toggle, no position-cache trap.

```typescript
@serializeProperty cubePrefab!: APJS.Prefab;
@serializeProperty spawnAnchor!: APJS.SceneObject;   // where new spawns get parented

private spawn(x: number, y: number, z: number): void {
  if (!this.cubePrefab || !this.spawnAnchor) return;
  const cube = this.cubePrefab.instantiate(this.spawnAnchor);
  if (!cube) return;
  const t = cube.getComponent("Transform") as APJS.Transform;
  if (t) t.localPosition = new APJS.Vector3f(x, y, z);
  // rb is fresh + dynamic. Gravity carries from here — no further toggling.
}
```

This is the right shape for the 3D "tap to spawn a thing" cluster. Roughly any rate up to ~10 spawns/sec stays well inside the perf budget.

### For 2D: also JIT, plus a sortingOrder bump on every spawn

For 2D games, runtime `prefab.instantiate()` works fine — with one extra step. The engine's `autoSortingOrder` pass runs at scene-load and assigns each build-time `Renderer` a `sortingOrder` value; runtime spawns don't go through that pass, so they default to `sortingOrder = 0` and end up behind every build-time Image. After instantiating, opt the new SceneObject out of auto-sort and assign a sortingOrder high enough to render above the build-time scene.

```typescript
@serializeProperty fruitPrefab!: APJS.Prefab;
@serializeProperty spawnParent!: APJS.SceneObject;   // a non-Image container (Empty 2D / render-group root)

private spawn(xPx: number, yPx: number): void {
  if (!this.fruitPrefab || !this.spawnParent) return;
  const inst = this.fruitPrefab.instantiate(this.spawnParent);
  if (!inst) return;
  const st = inst.getComponent("ScreenTransform") as APJS.ScreenTransform;
  if (st) st.anchoredPosition = new APJS.Vector2f(xPx, yPx);
  // Required: opt out of auto-sort and set a sortingOrder above the build-time scene.
  // Cast `as any` until the public Renderer typings include these properties.
  const img = inst.getComponent("Image") as APJS.Image;
  if (img) { (img as any).autoSortingOrder = false; (img as any).sortingOrder = 100; }
}
```

A constant `sortingOrder = 100` is enough for most templates — the build-time scene typically tops out below 50. If multiple runtime spawn types need to render in a specific order relative to each other, give each its own value (e.g., bullets at 90, enemies at 100, particles at 110).

When to use the pool pattern instead:

- **High-rate spawns** (>10/sec sustained — bullets in a shooter, particle-like bursts) where the GC churn from constant `instantiate` calls becomes measurable. Pre-instantiated pool is faster.
- **Determinism for testing/replay** — fixed pool size makes the scene-tree shape predictable.
- **Memory-bounded scenes on low-end devices** — capping at N instances at scene-load is a hard ceiling.

The pool pattern below pre-instantiates members at scene-load and toggles enable/disable to acquire/release. Members get their sortingOrder from auto-sort at scene-load, so they don't need the manual bump — but they do need the static-body position-cache trap fix when teleported into position.

For rapid-fire 2D bullets, this pool pattern is the default runtime implementation. Keep the source as a Prefab asset, then prewarm or grow pooled members from that Prefab instead of reusing one singleton bullet or falling back to `clone()` first.

If the user asks for a **template-style pool**, interpret it as: "use the same pool acquire / release pattern, but source instances from a hidden template object instead of an `APJS.Prefab` asset." See `APJS/examples/object_pool_prefab.json` for the prefab-source version, and `APJS/examples/object_pool_clone.json` for the hidden-template `clone()` version.

The naive pool pattern uses `setEnabledInHierarchy` to toggle which member is active:

```typescript
@serializeProperty bullet!: APJS.Prefab;
private pool: APJS.SceneObject[] = [];
private poolReady = false;
private readonly POOL_SIZE = 20;

onUpdate(_dt: number): void {
  if (!this.poolReady && this.bullet) {
    for (let i = 0; i < this.POOL_SIZE; i++) {
      const obj = this.bullet.instantiate(this.getSceneObject());
      if (obj) {
        obj.setEnabledInHierarchy(false);
        this.pool.push(obj);
      }
    }
    this.poolReady = true;
  }
}

private acquire(): APJS.SceneObject | undefined {
  for (const obj of this.pool) {
    if (!obj.enabled) {
      obj.setEnabledInHierarchy(true);
      return obj;
    }
  }
  return undefined; // pool exhausted — grow it or drop the spawn
}
```

### The static-body position-cache trap (pool pattern only — must read)

If your pool members start with `rb.static = true` (so they don't fall before the player taps), **writing only `ScreenTransform.anchoredPosition` does NOT move the physics body**. The static body keeps its cached position from authoring; the visual moves but `addForce` and gravity act on the cached spot.

Symptoms:
- "Candy visually teleports to the box but doesn't fall."
- "Force / velocity has no effect."
- "Object slowly drifts from offscreen toward the spawn point once `rb.static` flips."

Fix — write **both** `anchoredPosition` (visual, parent-local pixels) **and** `rb.position` (physics, world units, scaled by `pixelsPerUnit`), then flip `rb.static = false`. Centralize this in a helper so every spawn / despawn uses the same path:

```typescript
// pixelsPerUnit is on ScreenTransform; default is 32 for our 720×1280 stage.
private static readonly PPU = 32;

private teleport(obj: APJS.SceneObject, xPx: number, yPx: number): void {
  const st = obj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  const rb = obj.getComponent("RigidBody2D") as APJS.RigidBody2D;
  if (st) st.anchoredPosition = new APJS.Vector2f(xPx, yPx);
  if (rb) {
    rb.position = new APJS.Vector2f(xPx / Spawner.PPU, yPx / Spawner.PPU);
    rb.velocity = new APJS.Vector2f(0, 0);
    rb.angularVelocity = 0;
  }
}

private acquireAndDrop(boxX: number, boxY: number): void {
  const obj = this.acquire();
  if (!obj) return;
  this.teleport(obj, boxX, boxY - 30);   // both anchoredPosition AND rb.position
  const rb = obj.getComponent("RigidBody2D") as APJS.RigidBody2D;
  if (rb) {
    rb.static = false;                    // only after both positions are in sync
    rb.useGravity = true;
  }
}
```

Use the same helper for despawn (teleport the body offscreen + zero velocity before flipping back to static). This is the pattern `suika_merge`'s `teleportBall()` uses — see `templates/suika_merge.json` for a reference implementation.

> **TL;DR:** if you're reaching for the pool pattern, you also need this helper. If you don't need the helper (tap-driven low-rate spawn), use JIT `prefab.instantiate()` and skip the pool entirely.

### API

```typescript
class APJS.Prefab extends APJS.AObject {
  // Returns the spawned SceneObject, or null if instantiation fails.
  instantiate(parent: APJS.SceneObject): APJS.SceneObject | null;
}
```

`parent` is required and must be a SceneObject currently in the scene — typically `this.getSceneObject()` (the host of your script) or a `@serializeProperty` container you wired in advance.

### Wiring a Prefab into a script

A prefab asset enters a script via a `@serializeProperty APJS.Prefab` field, just like any other resource reference. The `SceneEditing` skill's `set_component` wiring uses the resource ref format `{guid, type: "Prefab"}`:

```typescript
@component()
export class BulletSpawner extends APJS.BasicScriptComponent {
  @serializeProperty
  bullet!: APJS.Prefab;          // wired by set_component after compile

  private touchCallback!: (e: APJS.IEvent) => void;
  private initialized = false;

  onStart(): void {
    this.touchCallback = (e: APJS.IEvent) => {
      const t = e.args[0] as APJS.TouchData;
      if (t.phase !== APJS.TouchPhase.Began) return;
      this.spawn();
    };
    APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch, this.touchCallback, this);
  }

  // Lazy-init guard — @serializeProperty fields are null in onStart, so any code
  // that touches `this.bullet` must run in onUpdate (after MCP wires the field).
  onUpdate(_dt: number): void {
    if (!this.initialized && this.bullet) this.initialized = true;
  }

  private spawn(): void {
    if (!this.bullet) return;             // wiring not ready yet
    const obj = this.bullet.instantiate(this.getSceneObject());
    if (!obj) return;                     // engine refused (rare — log and bail)
    // Position / configure the spawned instance like any SceneObject.
    const t = obj.getComponent("Transform") as APJS.Transform;
    if (t) t.localPosition = new APJS.Vector3f(0, 5, 0);
  }

  onDestroy(): void {
    APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch, this.touchCallback, this);
  }
}
```

DSL flow that wires this up - assume the `BulletSpawner` script class already
exists in the project. The example starts from "attach an existing script
component" and keeps `set_component` as a separate call for easier verification:

```json
// Call 1 — build source, prefab asset, host, attach an existing BulletSpawner component
edit_by_dsl({ commands: [
  { "command_type": "add_scene_object", "params": { "type": "Cube", "name": "Bullet" }, "alias": "src" },
  { "command_type": "create_prefab_from_object", "params": { "guid": { "$ref": "src" }, "consume_source": true }, "alias": "pf" },
  { "command_type": "add_scene_object", "params": { "type": "Transform", "name": "Spawner" }, "alias": "host" },
  { "command_type": "add_component", "params": { "scene_object": { "$ref": "host" }, "type": "BulletSpawner" }, "alias": "comp" }
]})

// Call 2 — wire the @serializeProperty field
edit_by_dsl({ commands: [
  { "command_type": "set_component", "params": {
      "guid": "<component-guid-from-call-1>",
      "properties": { "bullet": { "guid": "<prefab-guid-from-call-1>", "type": "Prefab" } } } }
]})
```

Create new scripts with `add_script`. Update existing scripts with `edit_script` using the Script resource GUID, and check its compilation result before wiring. Do not create versioned copies unless the user requests a parallel variant.

### Choosing between prefab.instantiate and SceneObject.clone

| | `prefab.instantiate(parent)` | `sceneObject.clone()` |
|---|---|---|
| Source | Prefab **asset** in the project (persists, editable, reusable) | A live SceneObject in the current scene |
| Authoring | Source can be hand-tuned in the editor before being made into a prefab | Source is just whatever's in the scene right now |
| Prefab-package imports | Required — when an earlier step already produced a Prefab asset | N/A |
| Cross-scene reuse | Works | Doesn't apply (no asset) |
| Recursion risk | None — asset is decoupled from script host | If the script lives on the cloned object, every clone runs the script and clones again — keep the script on a **separate** controller object |
| Cost / speed | Comparable — both spawn-time | Comparable |

**Rule of thumb**: when the source is something the user (or a previous DSL step) authored once and you want to fan out N copies of it, use `instantiate`. When you only need an in-scene "one more like that one" without persisting an asset, `clone` is fine. For imported prefab packages and any pre-existing Prefab asset, `instantiate` is the only path.

### Common runtime errors

- **`this.bullet` is null** — `@serializeProperty` fields haven't been wired yet (you're in `onStart`) or `set_component` was forgotten. Use the lazy-init guard above and verify the wire-up call ran.
- **`instantiate` returns null** — the engine refused (parent not in the scene, missing project, etc.). Log and skip; don't crash the update loop.
- **Spawn looks correct in logs but invisible** — the spawned object inherits the prefab's authored Transform. If the prefab was authored at the origin and your camera is elsewhere, reposition the spawn before it ticks.

## When NOT to use prefabs

- **One-off clone** (just need two copies, won't edit as a group) → `duplicate_scene_object` is simpler.
- **The source is already a prefab instance** → `create_prefab_from_object` will fail. Work from the original object or create the prefab from a fresh scratch hierarchy.
- **Effect nodes** are not prefab-compatible.

## Common errors (hints are included in the DSL result)

| Code | What it means | Fix |
|------|---------------|-----|
| `InvalidInputCannotBeEffectNode` | Source is an effect node | Pick a plain SceneObject |
| `NotSupportedInPrefabEditMode` | You're inside the prefab edit scene | Exit to main scene first |
| `InvalidInputCompatibilityNotPassed` | Some components aren't prefab-compatible | Inspect and remove/replace those components |
