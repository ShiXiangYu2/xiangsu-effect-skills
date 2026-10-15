---
name: Physics2D
description: 2D物理脚本编写 - 使用 2D 刚体、碰撞器、关节和射线实现移动、碰撞、触发器与物理约束。重点说明像素和世界单位换算、摩擦与弹性、碰撞形状校准，以及重力、时间速度和运行时重置。
---

# Physics2D — 2D Physics Scripting

Patterns for controlling 2D physics: rigid body movement, collision detection, joints, raycasting.

## Quick reference

| If you're doing…                 | Jump to                                                         |
| -------------------------------- | --------------------------------------------------------------- |
| Sizing colliders / boundaries    | [Collider2D](#collider2d) · [Wall Boundaries](#wall-boundaries) |
| Detecting hits / triggers        | [Collision Events](#collision-events)                           |
| Moving with forces or velocity   | [Moving a RigidBody2D](#moving-a-rigidbody2d)                   |
| Friction / bounciness            | [Physics Matter](#physics-matter-friction--bounciness)          |
| Pendulum / door / spring         | [2D Joints](#2d-joints)                                         |
| Ground / line-of-sight detection | [Raycast2D](#raycast2d)                                         |
| Reset on record start            | [RecordStart Reset](#recordstart-reset-for-2d-physics)          |
| Projectile / pool / spawning     | [Common Patterns](#common-patterns)                             |
| Gravity / slow-mo                | [Physics2D World Settings](#physics2d-world-settings)           |

## Rules (MUST follow)

1. **Collider2D `size`, `offset`, and `radius` are in WORLD UNITS (meters), NOT pixels.** Divide pixel sizes by `pixelsPerUnit` (default 32). A 100×80 px paddle needs `size = (3.125, 2.5)`. Setting `(100, 100)` creates a collider 3200×3200 pixels — much bigger than your sprite.
2. **`RigidBody2D.rotation` is in RADIANS, not degrees.** `rb.rotation = 45` rotates ~2578° (45 radians), not 45°. Use `Math.PI / 4` for 45°. (`ScreenTransform.rotation` is the opposite convention — degrees.)
3. **MUST set `collider.emitCollisionEvent = true` in the script's `onStart`** before listening — runtime-only, not DSL-settable.
4. **MUST use `EventManager.getObjectEmitter(collider)` for collision events** — NOT `getGlobalEmitter()`.
5. **MUST clean up event listeners in `onDestroy()`** — duplicate listeners cause N× event firing per RecordStart.
6. Use `isTangible = false` for trigger zones (detect overlap, no solid blocking).
7. `static = true` on RigidBody2D for immovable walls/barriers.
8. Both colliding objects need Collider2D; at least one needs RigidBody2D for collision events.
9. **Assign Physics Matter resource** for friction/bounciness — not scriptable at runtime.
10. **`Physics2D.gravity` is read-only at runtime** — configure in Effect Settings at design time. Default `(0, -9.8)` m/s². `Physics2D.timeSpeed` IS runtime-settable.
11. Use object pooling (show/hide + position reset) instead of clone/destroy for frequent spawning.

## DSL vs Runtime — boundary

Some Physics2D properties can be set both via `set_component`/`edit_by_dsl` _and_ in script; others are **runtime-only** (must be set in `onStart` from APJS). Trying to set a runtime-only property via DSL is silently rejected — the schema diff shows no change and the agent often retries the same call.

| Component                              | DSL-settable                                                                                   | Runtime-only (set in script)                                               |
| -------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `RigidBody2D`                          | `static`, `useGravity`, `mass`, `damping`, `angularDamping`, `gravityScale`, `force`, `torque` | `velocity`, `angularVelocity`, `rotation`, `freezeX`, `freezeY`, `freezeZ` |
| `BoxCollider2D` / `CircleCollider2D`   | `size` / `radius`, `offset`, `isTangible`, `physicsMaterial`                                   | `emitCollisionEvent`, `fitImage` (CircleCollider2D)                        |
| `EdgeCollider2D` / `PolygonCollider2D` | `offset`, `isTangible`, `physicsMaterial`                                                      | `points`, `emitCollisionEvent`                                             |
| Physics Matter (resource)              | `dynamicFrictionCoef`, `staticFrictionCoef`, `restitutionCoef` (set on the resource)           | —                                                                          |

If a DSL `set_component` returns `Unknown property 'X' on Y` for a runtime-only field, set it from `onStart()` instead. Cross-confirmed in `physics-2d` experiments E1, E2, E6.

## RigidBody2D

Get via `getComponent("RigidBody2D") as APJS.RigidBody2D`.

### Key Properties

| Property                 | Type     | Description                                                                                                                                                                                                                           |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `static`                 | boolean  | Static bodies don't move but can collide. _(DSL)_                                                                                                                                                                                     |
| `useGravity`             | boolean  | Whether affected by gravity. _(DSL)_                                                                                                                                                                                                  |
| `mass`                   | number   | Mass in kg. _(DSL)_                                                                                                                                                                                                                   |
| `gravityScale`           | number   | Per-body gravity multiplier. `0` = float, `1` = normal, `2` = doubled. Stored even when `useGravity = false`. _(DSL + runtime)_                                                                                                       |
| `position`               | Vector2f | Live physics-world position in **meters**, origin at the **screen center** (X+ right, Y+ up). Writing **teleports** the body, bypassing velocity/force. See [Position semantics](#position-semantics-rbposition-vs-anchoredposition). |
| `rotation`               | number   | Rotation in **radians**, counter-clockwise from +X (Rule #2). Setting teleports rotation. **runtime-only**                                                                                                                            |
| `velocity`               | Vector2f | Linear velocity (m/s). Live read; write overrides current value. **runtime-only**                                                                                                                                                     |
| `angularVelocity`        | number   | Angular velocity in rad/s, positive = counter-clockwise. **runtime-only**                                                                                                                                                             |
| `damping`                | number   | Linear damping (air resistance, typically 0–1). _(DSL)_                                                                                                                                                                               |
| `angularDamping`         | number   | Angular damping (typically 0–1). _(DSL)_                                                                                                                                                                                              |
| `freezeX` / `freezeY`    | boolean  | Lock horizontal / vertical movement. **runtime-only**                                                                                                                                                                                 |
| `freezeZ`                | boolean  | Lock rotation. **runtime-only**                                                                                                                                                                                                       |
| `force`                  | Vector2f | Continuous force (N). Setting **replaces** the previous continuous force; does NOT affect impulses added via `addForce`. _(DSL)_                                                                                                      |
| `torque`                 | number   | Continuous torque (N·m). Same replacement semantics as `force`. _(DSL)_                                                                                                                                                               |
| `initialVelocity`        | Vector2f | Serialized startup velocity, applied on body creation. Use this for "set once," not `velocity`. _(DSL)_                                                                                                                               |
| `initialAngularVelocity` | number   | Serialized startup angular velocity (rad/s). _(DSL)_                                                                                                                                                                                  |

> **Record / Reset semantics**: On record start, `position`, `rotation`, and `velocity` reset to initial values. Configuration properties (`mass`, `damping`, `static`, `freeze*`, `gravityScale`, etc.) are preserved.

### Position semantics: `rb.position` vs `anchoredPosition`

These two coexist on a physics-bound SceneObject and are easy to confuse. Rules:

| Purpose                                              | Use                                  | Notes                                                                                                                                                                                      |
| ---------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Teleport a physics body                              | **Write `rb.position`** (meters)     | Engine syncs `anchoredPosition` next frame. Writing `anchoredPosition` instead does NOT move a static body (see [static-body trap](#static-body-position-cache-trap)).                     |
| Read current physics position during gameplay        | **Read `rb.position`**               | Authoritative live value. Skip for `static` bodies — those don't move, so `anchoredPosition` is identical.                                                                                 |
| Cache the AUTHORED start position before play begins | **Read `anchoredPosition`** (pixels) | `rb.position` may return `(0, 0)` before the first physics step; `anchoredPosition` always returns the design-time placement. Convert when needed: `worldX = (anchoredX) / pixelsPerUnit`. |
| Read screen-pixel position for UI alignment          | **Read `anchoredPosition`**          | Pixels, parent-local.                                                                                                                                                                      |

**Coordinate conversion** (viewport 720×1280, default `pixelsPerUnit=32`):

| From → to                                                         | Formula                              |
| ----------------------------------------------------------------- | ------------------------------------ |
| pixels (bottom-left origin) → world meters                        | `(px - 360) / 32`, `(py - 640) / 32` |
| world meters → pixels (bottom-left origin)                        | `wx * 32 + 360`, `wy * 32 + 640`     |
| pixels (screen-center origin / `anchoredPosition`) → world meters | `px / 32`, `py / 32`                 |
| world meters → pixels (screen-center origin)                      | `wx * 32`, `wy * 32`                 |

### Moving a RigidBody2D

```typescript
const rb = obj.getComponent('RigidBody2D') as APJS.RigidBody2D;

// Continuous velocity (m/s)
rb.velocity = new APJS.Vector2f(speed, 0);

// Teleport (meters, origin = screen center). E.g. spawn at pixel (200, 800)
// from bottom-left origin: (200-360)/32 = -5.0, (800-640)/32 = 5.0
rb.position = new APJS.Vector2f(-5.0, 5.0);
```

#### `addForce()` and ForceMode2D

```typescript
// One-shot impulse (jump, push, explosion)
rb.addForce(new APJS.Vector2f(0, 500), APJS.ForceMode2D.Impulse);

// Continuous force (applied each physics step while set)
rb.addForce(new APJS.Vector2f(100, 0), APJS.ForceMode2D.Force);
```

| ForceMode2D      | Behavior              | Mass         | Use Case             |
| ---------------- | --------------------- | ------------ | -------------------- |
| `Force`          | Continuous, each step | Uses mass    | Wind, thrust         |
| `Acceleration`   | Continuous, each step | Ignores mass | Uniform movement     |
| `Impulse`        | One-shot, instant     | Uses mass    | Jump, hit, explosion |
| `VelocityChange` | One-shot, instant     | Ignores mass | Teleport-like push   |

`rb.force = vec` **replaces** the accumulated force; `addForce()` **adds** to it. For one-shot effects (tap to jump), always use `addForce(vec, APJS.ForceMode2D.Impulse)`.

#### Static-body position-cache trap

If the body is `static`, writing `anchoredPosition` alone does NOT move the physics body — the cached position stays where the body was authored. Symptoms: visual teleports but `addForce`/gravity has no effect, or body slowly drifts in from the authored position once you flip `static = false`.

**Fix**: write **both** `anchoredPosition` (pixels) and `rb.position` (meters), then flip `static = false`. Matters most for pool patterns reusing authored offscreen bodies, and for aim/preview balls that freeze before launch. Full recipe in `skills_root/general/Prefab/SKILL.md` → "The static-body position-cache trap".

#### Multiple objects from a script

```typescript
@component()
export class TapPushAll extends APJS.BasicScriptComponent {
  @serializeProperty blocks: APJS.SceneObject[] = [];

  private onTouch = (event: APJS.IEvent) => {
    const touch = event.args[0] as APJS.TouchData;
    if (touch.phase !== APJS.TouchPhase.Began) return;
    for (const obj of this.blocks) {
      const rb = obj.getComponent('RigidBody2D') as APJS.RigidBody2D;
      if (rb)
        rb.addForce(
          new APJS.Vector2f((Math.random() - 0.5) * 200, 300 + Math.random() * 200),
          APJS.ForceMode2D.Impulse
        );
    }
  };

  onStart(): void {
    APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch, this.onTouch);
  }
  onDestroy(): void {
    APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch, this.onTouch);
  }
}
```

## Collider2D

> ⚠️ **All `size`, `offset`, and `radius` values below are in WORLD UNITS (meters), NOT pixels.** With default `pixelsPerUnit=32`, divide pixel measurements by 32. See [Rule #1](#rules-must-follow).

### BoxCollider2D

```typescript
const collider = this.getSceneObject().getComponent('BoxCollider2D') as APJS.BoxCollider2D;
// World units. A 100×80 PX paddle needs (100/32, 80/32) = (3.125, 2.5):
collider.size = new APJS.Vector2f(3.125, 2.5);
collider.offset = new APJS.Vector2f(0, 0); // also world units
```

### CircleCollider2D

```typescript
const collider = this.getSceneObject().getComponent('CircleCollider2D') as APJS.CircleCollider2D;
// World units. A 64 PX diameter ball = 32 PX radius = 32/32 = 1.0 wu:
collider.radius = 1.0;
collider.fitImage = true; // Auto-size to attached image (runtime-only)
```

### EdgeCollider2D — open polyline / terrain

For arbitrary 2D terrain (slopes, ramps, hills, valleys, half-pipes). The `points` array defines a connected polyline **in world units** in the SceneObject's local frame. **`points` is runtime-only** — set from `onStart()`, not via DSL.

```typescript
const edge = this.getSceneObject().getComponent('EdgeCollider2D') as any;
// 3-point downward slope, in world units (meters):
edge.points = [new APJS.Vector2f(-10, 5), new APJS.Vector2f(0, 0), new APJS.Vector2f(10, -5)];
```

Endpoints behave as **corner collision features** — a ball reaching the polyline's last point bounces in BOTH X and Y. To make a smooth fall-off, extend the polyline further off-screen instead of stopping abruptly. Drop-in recipe: `APJS/examples/edge_collider_terrain_roll.json`.

### PolygonCollider2D — closed irregular polygon

For convex closed shapes (triangles, pentagons, custom convex platforms) AND concave shapes (L, T, star) — the latter render visually correctly but physics collision uses the convex hull. **`points` IS DSL-settable** via `set_component` — the MCP layer auto-injects the required coupled properties (`convexIndices`, `subConvexVertexCount`) so the editor's gizmo renderer and physics both work.

```
// Build a triangle (3 vertices, convex)
add_component("hostObj", "PolygonCollider2D")  → alias "poly"
set_component("poly", { points: [
  {x: 0, y: 1.25},      // top apex
  {x: -1.25, y: -1.25}, // bottom-left
  {x: 1.25, y: -1.25},  // bottom-right
]})
// auto-injected:  convexIndices: [0,1,2],  subConvexVertexCount: [3]
```

**Defaults**: a fresh PolygonCollider2D has 4 default vertices (`[(0,-10),(10,0),(0,10),(-10,0)]` — a diamond). Always set custom `points` immediately after `add_component` for any real polygon shape.

**Concave shapes** (L, Z, star, arrow, any non-convex polygon): just send the perimeter vertices in order (clockwise or counter-clockwise). **The editor runs its own convex decomposer synchronously at set time** and produces a valid `convexIndices`/`subConvexVertexCount` from your `originalPoints` — you never need to compute or supply a triangulation. The MCP auto-injection of `convexIndices: [0..N-1]` / `subConvexVertexCount: [N]` exists as belt-and-suspenders defaults but the editor immediately overrides them with its own decomposition (proved live: `set_component` returns your submitted indices as "applied"; the next `inspect` shows different values — the auto-decomposer ran in between). Net effect: the agent's contract is "supply perimeter vertices in order", and the editor handles all triangulation.

### Aligning a polygon collider to a generated sprite

When the sprite comes from a generated or externally sourced texture, **its actual content proportions almost never exactly match the prompt** (vertical bar width, foot height, etc. drift by 5-15%). Don't try to size the collider from prompt specs alone — use this iteration loop with `get_scene_view`:

1. **Initial estimate**: set points from prompted shape (rough — won't be perfect)
2. **`get_scene_view`** on the host's guid → returns the Scene panel image (with green collider wireframe drawn) + JSON `colliderPoints[]` in screen-pixel coords
3. **Compare**:
   - Visually: does the green outline trace the visible sprite edges?
   - Numerically: are `colliderPoints` at the sprite's actual pixel boundaries?
4. **Adjust** one edge at a time (e.g. "vertical bar right edge x: -1.0 → -0.85" to widen by 0.15wu)
5. **Re-screenshot, re-compare** — typically 2-4 iterations converges

**For sub-pixel precision** on small/detailed colliders: ask the user to zoom the Scene panel to 300-350% before your verification screenshot. `get_scene_view` captures whatever the panel currently shows, so a zoomed editor view gives you ~3× more pixels per world-unit and lets you iterate down to ~1-2 px alignment instead of ~3-5 px.

**Don't confuse the selection box with the collider**: the editor draws a **white rectangle with corner handles** around the ScreenTransform host (always rectangular, follows `sizeDelta`). The **green outline** is the actual polygon collider. The white box being bigger than the L is expected — it's the host's bbox, not the collider.

### Iterating with `move_polygon_points`

Rewriting the full `points` array via `set_component` is wasteful when you're nudging one vertex. Use `move_polygon_points` instead — it reads the current `originalPoints` (the canonical agent-ordered geometry; see invariant below), patches only the indices you specify, writes the full array back to both `points` and `originalPoints`. Vertex count stays the same so `convexIndices`/`subConvexVertexCount` companion auto-injection is unnecessary.

**Why `originalPoints` and not `points`?** On project load the editor regenerates `points` + `convexIndices` from `originalPoints` via its own convex decomposer. The decomposed `points` array is in a different order than the agent ever set. So indices must refer to `originalPoints` — that's what's preserved across save/reload.

```
{
  command_type: "move_polygon_points",
  params: {
    collider_guid: "c12",                              // the PolygonCollider2D component guid
    updates: [
      {index: 0, x: 0,    y: 1.85},                    // pull top tip down 0.05wu
      {index: 5, x: 0,    y: -1.0}                     // deepen bottom inner V
    ]
  }
}
```

Returns `{component_type, guid, totalPoints, changes: [{index, oldValue, newValue}, …]}`. Out-of-range indices throw with the valid range.

### Persistence: DSL changes are in-memory only until saved

`set_component` / `add_component` / `move_polygon_points` all go through the editor's `StartAction`/`EndAction` wrap, which makes them undoable AND marks the project dirty. **But the project is not auto-saved.** If you restart the editor (or open another project) before saving, all your DSL changes vanish — the next load reads the old `.ehproj` from disk. Symptom: every polygon collider you set comes back as the default 4-point diamond after restart, even though you confirmed the points via `inspect` earlier.

Fix: explicitly call `save_project` at the end of any DSL batch you want to keep. Cheap (~10–20 ms). Recommended pattern:
```
edit_by_dsl({commands: [...your collider edits...]})
save_project()  // commit to disk
```

### The `originalPoints` survival invariant

`PolygonCollider2D` stores **two** parallel vertex arrays:
- `points` — used by physics + gizmo rendering at runtime
- `originalPoints` — the canonical geometry; **on project LOAD the editor resets `points` from `originalPoints`**

If you set only `points` and leave `originalPoints` at its constructor default (the 4-point diamond), the `.ehproj` looks fine on disk (your `points` are there) — but every collider reverts to the default diamond on the next project open because load reads `originalPoints` first. This is the cause of the "I saved, why did everything revert to diamonds?" mystery.

**Now auto-handled by the MCP layer** — `set_component { points: [...] }` automatically writes `originalPoints` in lockstep (same code path as `convexIndices`/`subConvexVertexCount` auto-injection). `move_polygon_points` does the same after applying its index-level patches. The user-facing API stays the same: you write `points`, the persistence-critical companion fields are wired up for you. Don't manually set `originalPoints` separately.

**The editor regenerates `points` and `convexIndices` from `originalPoints` synchronously at every `set_component`.** This is NOT a load-time behavior — it happens immediately when you set `points` (proved: `set_component` returns the indices you submitted as `newValue`, but the next `inspect` shows different values — the auto-decomposer ran in between). The decomposed `points` array is in a different order than what you submitted. This means:
- Visible shape is always correct (`originalPoints` is the canonical source)
- The agent's submitted `convexIndices`/`subConvexVertexCount` are never the live values — they're overridden immediately. Useful as defaults to keep the engine happy, but no point computing custom decompositions
- The agent's index ordering of `points` is NOT stable — never index `points` for iteration. **Index `originalPoints`** instead (this is what `move_polygon_points` does)

### Inspector cache lag

The right-hand Inspector panel **caches its displayed values** and doesn't auto-refresh when you change a component via DSL. The engine state IS updated (the gizmo will redraw correctly; `inspect` returns the new values; physics uses the new collider). But the inspector keeps showing the OLD values until you click off the object and click it back in the Hierarchy — that forces a fresh read.

This makes debugging confusing: you'll write 10 points via DSL, the user opens the inspector and sees the default 4-point diamond, thinks the DSL silently failed. Tell users to click-off-click-on first when they doubt DSL changes landed. The source of truth is `inspect` (live engine read), not the inspector panel.

### Math-derived collider vs generated sprite — the symmetry limit

Computing star/oval vertices from idealized polar formulas (`R·sinθ, R·cosθ` at uniform angles) produces a perfectly symmetric mathematical shape. Generated sprites are **not symmetric** — they have generation noise, may be slightly off-center inside the frame, can be horizontally squished when their natural aspect ratio doesn't match the ScreenTransform, and have anti-aliased edges that soften the tip pixels. The result: a math-perfect collider sits a few pixels off the actual sprite corners at every vertex, and you can't fix it by tweaking a single radius — different vertices need different distances from center.

Two paths when this matters:
1. **Manual drag in the editor** is the right tool for tight AIGC alignment — the user can drag each handle onto each visible corner with pixel-perfect feedback. Save the project after.
2. **Per-vertex iteration via `move_polygon_points` + zoomed `get_scene_view`** can close the gap but is slow (DSL → screenshot → eyeball → DSL). Practical alignment ceiling without manual drag is ~3–5 px at 100% zoom.

### `stretchMode` default is `Fit`, not `Stretch`

A fresh `Screen Image` has `Image.stretchMode = "Fit"` — the sprite is letterboxed inside the ScreenTransform (preserves aspect, may leave transparent padding inside the host). If your collider is sized to the ScreenTransform extent, this means **the collider extends past the visible sprite edges**. For a collider that should hug the sprite, set `stretchMode: "Stretch"` on the Image right after creating it.

### Common Collider2D Properties

| Property | Type | Description |
|---|---|---|
| `offset` | Vector2f | Center position offset (**world units**) *(DSL)* |
| `isTangible` | boolean | `true` = solid; `false` = trigger (pass-through, still fires events) *(DSL)* |
| `emitCollisionEvent` | boolean | **Must be `true` to receive collision callbacks** — runtime-only |
| `points` (Polygon) | Vector2f[] | Polygon perimeter vertices (**world units**) — **DSL-settable**, coupled properties auto-injected. Default is 4-vertex diamond. |
| `points` (Edge) | Vector2f[] | Polyline vertices (**world units**) — runtime-only (no DSL support yet) |

## Collision Events

The collision event flow:

1. Set `collider.emitCollisionEvent = true` in `onStart` (Rule #3 — DSL won't do it)
2. Get the per-object emitter: `EventManager.getObjectEmitter(collider)` (Rule #4 — NOT `getGlobalEmitter`)
3. Register listener; clean up in `onDestroy` (Rule #5)

```typescript
@component()
export class CollisionHandler extends APJS.BasicScriptComponent {
  private cb: (event: APJS.IEvent) => void;
  private collider: APJS.BoxCollider2D;

  onStart(): void {
    this.collider = this.getSceneObject().getComponent('BoxCollider2D') as APJS.BoxCollider2D;
    if (!this.collider) return;
    this.collider.emitCollisionEvent = true; // Rule #3

    this.cb = (event: APJS.IEvent) => {
      const infos = event.args[0] as APJS.CollisionInfo2D[];
      for (const info of infos) {
        if (info.otherObject) console.log('Hit: ' + info.otherObject.name);
        // info.point  — contact point in world space
        // info.normal — contact normal in world space
      }
    };
    APJS.EventManager.getObjectEmitter(this.collider).on(APJS.CollisionEvent2D.Enter, this.cb, this);
  }

  onDestroy(): void {
    if (this.cb && this.collider)
      APJS.EventManager.getObjectEmitter(this.collider).off(APJS.CollisionEvent2D.Enter, this.cb, this);
  }
}
```

| Event                    | When Fired                   |
| ------------------------ | ---------------------------- |
| `CollisionEvent2D.Enter` | First frame of contact       |
| `CollisionEvent2D.Stay`  | Every frame while in contact |
| `CollisionEvent2D.Exit`  | First frame after separation |

`CollisionInfo2D` fields: `point` (Vector2f), `normal` (Vector2f), `otherObject` (SceneObject).

### Collision Response Patterns

- **Scoring**: increment counter on `Enter`, update Text display.
- **Health/lives**: decrement on `Enter`, hide/remove at zero, show game-over.
- **Destroy on hit**: `this.scene.removeSceneObject(info.otherObject)`.
- **Bounce**: handled by physics — set via Physics Matter resource.
- **Trigger zone**: set `collider.isTangible = false` — fires events without solid contact. Good for checkpoints, score zones, pickups.

### Scene-authored hit zones for pseudo-3D 2D games

Use this when a game is built from 2D UI sprites but should read as a 3D court, field, or lane. Example: a soccer free-kick where the ball visually shrinks and drops toward a goal, blockers move horizontally in rows, and a full Rigidbody2D simulation would not match the designed perspective.

The right split:

1. Add Collider2D components to the ball, blockers, goal, and miss/score zones so hit geometry is editable in the scene.
2. Keep those colliders `isTangible=false` unless you want engine blocking.
3. Author blocker hit zones as the believable 3D contact area, not the whole sprite. A player sprite might be 165x200 px, but its BoxCollider2D can be a compact centered body zone such as 2x1.6 world units.
4. Read collider `size`, `radius`, and `offset` from the scene and convert through `ScreenTransform.pixelsPerUnit` for script math.
5. Drive ball/blocker motion manually in screen space, then use circle-vs-rect or circle-vs-zone overlap against those scene-authored hit zones.

This pattern still uses colliders, but the bounce response is scripted. It avoids the bad fake-3D result where the visible bottom/feet edge of a large 2D blocker sprite bounces the ball like a flat wall.

If you need **engine** `CollisionEvent2D.Enter` as the authoritative source of contact, Rule #8 still applies: at least one of the objects needs a `RigidBody2D`. If the prompt or design explicitly says no Rigidbody, use Collider2D as editable hit-zone data and make the script's overlap check the authoritative game logic.

### Zone-Based Hit Detection

For target/bullseye games with different scoring areas:

1. **DSL**: concentric trigger objects (inner=100pts, middle=50pts, outer=10pts), each with Collider2D `isTangible=false`. Don't set `emitCollisionEvent` here — runtime-only.
2. **Naming**: name objects by points ("Zone_100", "Zone_50") — script parses the name.
3. **Script**: in each zone-handler's `onStart`, set `emitCollisionEvent = true`, register `Enter` on the collider. On hit, look up points by zone name.
4. **Prevent double-scoring**: projectile may pass through multiple overlapping zones. Use a flag (`hasScored`) on the projectile to count only the first (innermost) hit.

## Physics Matter (Friction & Bounciness)

Physics Matter is a **resource** controlling friction and elasticity. Created via DSL, assigned to a collider's `physicsMaterial` property.

**DSL setup**:

1. `add_builtin_resource(resource_type="Physics Matter")` → resource
2. `set_resource_properties(guid, properties)` → friction/bounciness values
3. `set_component(collider_guid, {"physicsMaterial": {guid: "..."}})` → assign

**Resource properties**:

| Property              | Type   | Default | Description                                             |
| --------------------- | ------ | ------- | ------------------------------------------------------- |
| `dynamicFrictionCoef` | number | 0.6     | Friction during movement (0 = ice, 1 = sticky)          |
| `staticFrictionCoef`  | number | 0.61    | Friction when stationary (slightly higher than dynamic) |
| `restitutionCoef`     | number | 0.3     | Bounciness (0 = no bounce, 1 = perfect)                 |

**Typical presets**:

- **Ice/slippery**: dynamicFriction=0.05, staticFriction=0.1, restitution=0.2
- **Rubber/bouncy**: dynamicFriction=0.8, staticFriction=0.9, restitution=0.9
- **Metal**: dynamicFriction=0.4, staticFriction=0.5, restitution=0.3

> **DSL wire format — single-resource fields**: `physicsMaterial` (and other single-resource fields like `texture`) require the literal `{guid: "<id>"}` form and **reject** the array-style `{$ref: "alias"}` shorthand. Capture the alias-resolved GUID from the previous `add_builtin_resource` response, then pass it in a follow-up `set_component`. Example: `APJS/examples/physics_matter_bounce.json`. Verified: `restitutionCoef=0.85` produces measured rebound 0.82 ± 0.01 across 5 bounces; same Matter on both colliders does not double-count.

Physics Matter is NOT scriptable at runtime — set values before scene runs.

## Wall Boundaries

Create screen-edge walls using static RigidBody2D + BoxCollider2D. **Always create all 4 walls** (left, right, top, bottom) — missing a wall causes objects to fly off-screen.

**DSL setup** (no script needed):

1. Create a Screen Image object for each wall
2. Add `RigidBody2D` with `static = true`
3. Add `BoxCollider2D` with **world-unit** `size` (Rule #1)
4. Position walls at screen edges via ScreenTransform

**Sizing guide**: 2D Camera with `orthoScale = 20` shows ±20 units vertically. Screen aspect 9:16 gives ±11.25 units horizontally. Place walls just outside these bounds with thick colliders (size 1–2 units thick, spanning the full edge length).

> **Canonical recipe — `APJS/examples/screen_walls.json`**: drop-in DSL-only build for 4 walls (top/bottom = 800×80 px = 25×2.5 wu, left/right = 80×1400 px = 2.5×43.75 wu, positioned at ±680 px / ±400 px from center). Verified to fully contain a dynamic ball: per-axial restitution ratio 0.96 with `restitutionCoef=1.0` (the ~4% gap is the engine's per-contact integrator loss). Pair with a single bouncy Physics Matter resource assigned to all 4 walls AND the dynamic body via `physicsMaterial: {guid: "<id>"}`.

## Physics2D World Settings

```typescript
// gravity: read-only at runtime (configure in Effect Settings)
// timeSpeed: runtime-settable, defaults to 1.0
APJS.Physics2D.timeSpeed = 0.5; // slow motion
APJS.Physics2D.timeSpeed = 2.0; // fast forward
APJS.Physics2D.timeSpeed = 1.0; // restore

// Read current world gravity (for projectile math, etc.)
const g = -APJS.Physics2D.gravity.y; // positive magnitude (m/s²)
```

### Gravity

- **Default**: `(0, -9.8)` m/s² — Earth gravity. **Y+ is up.**
- **Configured at design time** in Effect Settings. Assigning `APJS.Physics2D.gravity = ...` at runtime compiles and doesn't throw, but the simulator keeps the scene-load snapshot — **the assignment has no effect**.
- **Per-body multiplier**: `RigidBody2D.gravityScale` (DSL + runtime). `0` = float, `1` = normal, `2` = doubled.
- **Custom per-body gravity**: set `rb.useGravity = false`, then `rb.addForce(customG.multiplyScalar(rb.mass), APJS.ForceMode2D.Force)` each frame (or set `rb.force = customG.multiplyScalar(rb.mass)`).
- **Unit-scale gotcha**: gravity is in m/s². A 9.8 m/s² fall traverses `9.8 × 32 ≈ 314 pixels per second²` on the 720×1280 viewport. If a fall "looks too slow" in pixels, the issue is usually coordinate-space mismatch, not gravity strength — read `rb.position` (meters) and compare to world-unit bounds, OR adjust Effect Settings gravity (e.g. `(0, -50)`) if you want dramatic pixel-space falls. **Don't try to overwrite `Physics2D.gravity` at runtime** — no-op.

### `timeSpeed`

- Defaults to `1.0`. Values <1 = slow motion, >1 = fast forward.
- **Not reset by `resetPhysics()`** on record start — whatever value you set persists across record cycles. Reset to `1.0` explicitly if you don't want slow-mo to leak between takes.
- Scales BOTH gravity acceleration AND velocity-driven displacement uniformly. Verified: at `timeSpeed=0.3`, gravity dropped from 10.5 wu/s² to 3.0 wu/s² (measured ratio 0.286). Restoring to `1.0` resumes full-rate physics on the next physics step. Composes cleanly with Physics Matter restitution. Recipe: `APJS/examples/physics2d_slowmo_on_hit.json`.

### Raycast2D

Cast a ray in 2D space to detect objects along a line:

```typescript
const origin = new APJS.Vector3f(0, 10, 0); // world units (meters)
const direction = new APJS.Vector3f(0, -1, 0);
const ray = new APJS.Ray(origin, direction);
const hits = APJS.Physics2D.raycast2D(ray, 100, true); // nearest hit within 100 units
if (hits.length > 0) {
  console.log('Hit: ' + hits[0].colliderObject.name);
}
```

**Raycast ground detection** (platformer pattern):

```typescript
// rb.position is in meters; cast short ray downward from player's bottom edge:
const wp = rb.position;
const origin = new APJS.Vector3f(wp.x, wp.y - halfHeight, 0);
const ray = new APJS.Ray(origin, new APJS.Vector3f(0, -1, 0));
const hits = APJS.Physics2D.raycast2D(ray, 0.5, false);

// Filter out self-hits (raycast can hit player's own collider).
// Extract colliderObject to local — TS strictNullChecks won't narrow through
// repeated property access:
let isGrounded = false;
for (let i = 0; i < hits.length; i++) {
  const co = hits[i].colliderObject;
  if (co && co.name !== myObj.name) {
    isGrounded = true;
    break;
  }
}
```

`RaycastHit2D` fields: `point` (Vector2f), `normal` (Vector2f), `collider` (Collider2D), `colliderObject` (SceneObject).

## 2D Joints

Joints connect two RigidBody2D objects with a physical constraint. Query the selected component's knowledge, then add it through DSL `add_component`. Use a separate static RigidBody2D as a fixed support; use 3D joints for 3D bodies. A joint provides the motion constraint; visible ropes or chains need separate artwork.

| Type              | Purpose                                                                | Key Properties                                                               |
| ----------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `HingeJoint2D`    | Rotation around anchor (door hinge, rotating arm)                      | `useLimits`, `minAngle`, `maxAngle`                                          |
| `SpringJoint2D`   | Soft pin / compliant constraint (sub-wu compliance, NOT a true bungee) | `damping` (default 0.7, range [0,1]), `tolerance` (default 0.5, range [0,1]) |
| `DistanceJoint2D` | Fixed distance — **use for pendulum/swing**                            | anchor/connectedAnchor                                                       |
| `FixedJoint2D`    | Rigid weld                                                             | `breakable`, `breakingForce`                                                 |

### Common Properties (all Joint2D)

| Property          | Type     | Description                             |
| ----------------- | -------- | --------------------------------------- |
| `anchor`          | Vector2f | Local anchor on this body (world units) |
| `connectedAnchor` | Vector2f | Anchor on connected body (world units)  |
| `breakable`       | boolean  | Can joint break under load              |
| `breakingForce`   | number   | Force threshold (default 9999)          |
| `breakingTorque`  | number   | Torque threshold (default 9999)         |

### DSL Setup

```
add_builtin_object("Screen Image", name="Anchor")     → alias "anchor"
add_component("anchor", "RigidBody2D")                 → set static=true
add_builtin_object("Screen Image", name="Bob")         → alias "bob"
add_component("bob", "RigidBody2D")                    → set useGravity=true

add_component("bob", "DistanceJoint2D")                → alias "joint"
set_component("joint", { connectedBody: { guid: {$ref: "anchor"} } })
```

> **Pendulum**: use `DistanceJoint2D`. Position bob to the side of anchor — gravity pulls bob down, distance constraint makes it swing. `HingeJoint2D` instead pins one body's anchor to the other and lets the body rotate around it (use for doors, not free-swinging pendulums).

> **DSL wire format — `connectedBody`** (uniform across all four joint types): the schema reports the field as `ScreenTransform`, but the DSL **accepts a SceneObject GUID** (`{guid: "<scene-object-id>"}` or `{guid: {$ref: "<alias>"}}`) and auto-resolves to that object's ScreenTransform reference. The `set_component` response confirms the resolution. Cross-confirmed in DistanceJoint2D (`pendulum_distance_joint`), HingeJoint2D (`hinge_door_swing`), SpringJoint2D (`spring_bungee`), FixedJoint2D (`fixed_breakable_link`).

### Per-type DSL surface (verified in `physics-2d/experiments/`)

| Type              | Settable via `set_component`                                                                                                      | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DistanceJoint2D` | `connectedBody`, `anchor`, `connectedAnchor`, `breakable`, `breakingForce`                                                        | Distance auto-captured at attach time; no `distance` knob.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `HingeJoint2D`    | `connectedBody`, `anchor`, `connectedAnchor`, `useLimits`, `minAngle`, `maxAngle`, `breakable`, `breakingForce`, `breakingTorque` | `anchor` in **world units** in body's local frame — for a 5-wu wide door pivoting at its left edge, `anchor=(-2.5, 0)`. Angle limits enforced strictly: E7 door reached +28° under gravity, never exceeded +30° max.                                                                                                                                                                                                                                                                                                                                                 |
| `SpringJoint2D`   | `connectedBody`, `anchor`, `connectedAnchor`, `breakable`, `breakingForce`, `damping`, `tolerance`                                | **No `distance`/`restLength`/`frequency`/`stiffness`** — rest length captured at attach. **Both `damping` and `tolerance` clamped to `[0, 1]`; DSL silently accepts out-of-range, but `tolerance ≥ 1` SUPPRESSES spring force** (bob free-falls). Within range, achievable oscillation is sub-wu (≤ ~0.03 wu / ~1 px) — `SpringJoint2D` is a soft pin, NOT a true bungee. For large stretch-and-snap-back, use a script-controlled spring model and verify the intended stretch; `DistanceJoint2D` remains fixed-length. Tuning: `(0.0, 0.7)` = lock; `(0.5, 0.7)` = near-rigid pin (default); `(0.9, 0.0)` = max micro-oscillation. |
| `FixedJoint2D`    | `connectedBody`, `anchor`, `connectedAnchor`, `breakable`, `breakingForce`, `breakingTorque`                                      | Pure rigid weld — no compliance knobs. Set `breakable=true` + finite `breakingForce` for an overload-snap weld; otherwise indestructible.                                                                                                                                                                                                                                                                                                                                                                                                                            |

> **Joint break is silent**. When `breakable=true` and load exceeds threshold, the joint disappears with NO event fired. Detect via position-drift sampling OR by polling `obj.getComponent("FixedJoint2D")` for `null` in `onUpdate`.

### APJS Access

```typescript
const hinge = obj.getComponent("HingeJoint2D") as APJS.HingeJoint2D;
hinge.useLimits = true;
hinge.minAngle = -45;
hinge.maxAngle = 45;

const spring = obj.getComponent("SpringJoint2D") as APJS.SpringJoint2D;
// damping default 0.7 (range [0, 1]); tolerance default 0.5 (range [0, 1]).
// Out-of-range silently disables the spring at runtime.

// Detect FixedJoint2D break (silent — no callback fires on break):
onUpdate(dt: number) {
  if (obj.getComponent("FixedJoint2D") === null) {
    // The joint snapped this frame.
  }
}
```

> **2D rotation read** (E7): `ScreenTransform.rotation` is a **scalar number in degrees** (positive = counter-clockwise). Do NOT use the 3D-style `transform.localEulerAngle.z` on a ScreenTransform — `localEulerAngle` is undefined on ScreenTransform and `.z` throws `cannot read property 'z' of undefined`. For 2D angle reads on bodies under HingeJoint2D, prefer `screenTransform.rotation`.

### Canonical examples (one per joint type)

- `APJS/examples/pendulum_distance_joint.json` — `DistanceJoint2D` rigid pendulum (E2).
- `APJS/examples/hinge_door_swing.json` — `HingeJoint2D` + `useLimits` swinging door (E7).
- `APJS/examples/spring_bungee.json` — `SpringJoint2D` soft pin (E8/E10). Naming historical; behaves as compliant pin, not bungee.
- `APJS/examples/fixed_breakable_link.json` — `FixedJoint2D` overload-snap weld (E9).

## Common Patterns

### Projectile

1. **DSL setup**: build a fully-configured source — RigidBody2D + Collider2D + visuals — kept as a hidden in-scene template (clone path) or a prefab (`create_prefab_from_object`). Source-choice rule: `skills_root/general/Prefab/SKILL.md` "Choosing between prefab.instantiate and SceneObject.clone".
2. **Launch**: spawn, position via `rb.position` (meters), apply `addForce(vec, APJS.ForceMode2D.Impulse)`.
3. **Collision**: register `CollisionEvent2D.Enter` on the spawn's collider → score, destroy, or bounce.
4. **Cleanup**: in `onUpdate`, check bounds and hide-and-recycle.

```typescript
// Clone path — projectileTemplate is a @serializeProperty SceneObject
const proj = this.projectileTemplate.clone();
proj.setEnabledInHierarchy(true);
const rb = proj.getComponent('RigidBody2D') as APJS.RigidBody2D;
// Teleport via rb.position (meters, origin = screen center) — see Position semantics.
// E.g. spawn at screen-center pixel (100, 200): (100/32, 200/32) = (3.125, 6.25)
rb.position = new APJS.Vector2f(3.125, 6.25);
rb.addForce(new APJS.Vector2f(forceX, forceY), APJS.ForceMode2D.Impulse);

// Off-screen cleanup in onUpdate — viewport extends y=-20..+20 in world units
if (rb.position.y > 25 || rb.position.y < -25) {
  proj.setEnabledInHierarchy(false); // pool: hide instead of destroy
}
```

For the prefab path, swap `clone()` for `bullet.instantiate(host)` — full script in `APJS/examples/runtime_prefab_spawn.json`.

> **Clone-and-spawn pitfalls** (verified in `experiments/E5-coin-spawn-falling.md`):
>
> 1. **`rb.velocity` getter is stale in the same frame as `addForce()`** — the impulse integrates on the NEXT physics step. Reading `rb.velocity` immediately after `addForce()` returns the pre-impulse value (typically `(0, 0)`). Defer the read to the next `onUpdate(dt)` if you need to observe post-impulse velocity.
> 2. **`clone.getComponent("ScreenTransform").anchoredPosition = ...` is silently overridden when the clone has a `RigidBody2D`** — the body's cached position (inherited from the template) wins, so the clone spawns AT THE TEMPLATE'S POSITION regardless of post-clone repositioning. **Workaround**: pre-position the template at the desired spawn location, hide with `template.setEnabledInHierarchy(false)` in `onStart()`, randomise spawn variation through `addForce(Vector2f(jitterX, impulseY), Impulse)` rather than per-clone repositioning. Drop-in: `APJS/examples/coin_spawn_falling.json`.

### Swipe-to-Launch (Parabolic Arc)

For sports games (free kick, slingshot): track drag → compute angle + force → apply impulse. Gravity creates the parabolic arc automatically.

```typescript
// In touch handler:
if (touch.phase === APJS.TouchPhase.Began) {
  this.startTouch = new APJS.Vector2f(touch.position.x, touch.position.y);
}
if (touch.phase === APJS.TouchPhase.Ended) {
  const dx = touch.position.x - this.startTouch.x;
  const dy = -(touch.position.y - this.startTouch.y); // invert Y: swipe up = +Y force
  const dragDist = Math.sqrt(dx * dx + dy * dy);
  const forceMag = Math.min(dragDist / 0.4, 1.0) * maxForce; // clamp to max
  rb.addForce(new APJS.Vector2f((dx / dragDist) * forceMag, (dy / dragDist) * forceMag), APJS.ForceMode2D.Impulse);
}
```

- Touch positions are normalized (0–1). Invert Y delta so swipe-up = positive force.
- Force magnitude scales with drag distance (longer swipe = stronger).
- Gravity handles the arc — no manual trajectory math.
- Reset ball: `rb.velocity = new APJS.Vector2f(0, 0)`, restore `rb.position`.

### Moving Platform

Use a **dynamic** RigidBody2D (not static) with `useGravity=false` and high mass. Set `rb.velocity` each frame for physics-correct movement that carries the player via friction:

```typescript
// Platform setup:
//   DSL:    static=false, useGravity=false, mass=100
//   Script: rb.freezeZ = true  (in onStart — runtime-only)
// In onUpdate:
const ap = screenTransform.anchoredPosition; // pixels for bounds check
if (ap.x >= maxX) direction = -1;
if (ap.x <= minX) direction = 1;
rb.velocity = new APJS.Vector2f(speed * direction, 0);
```

No kinematic mode exists — high mass (100) prevents the player (mass=1) from pushing the platform.

### World Scrolling (Camera Follow Alternative)

2D games use ScreenTransform; traditional camera follow doesn't work. Instead, **scroll the world while the player stays at a fixed screen position**:

- Player: `freezeX=true` on RigidBody2D — locked at a fixed X position
- Platforms: dynamic RigidBody2D (`static=false`, `useGravity=false`, `mass=100`)
- Ground: static RigidBody2D (extra wide)

Script pattern — `WorldScroller` (attached to any object, references platforms via `@serializeProperty`):

```typescript
@serializeProperty platforms: APJS.SceneObject[] = [];
@serializeProperty scrollSpeed: number = 3;

// In onUpdate: scroll all platforms left via rb.velocity
for (const pd of this.platformData) {
  pd.rb.velocity = new APJS.Vector2f(-this.scrollSpeed, 0);

  // Wrap: recycle platforms that scroll off-screen left → right side
  const ap = pd.st.anchoredPosition;
  if (ap.x < -500) {
    pd.rb.position = new APJS.Vector2f(
      (600 + Math.random() * 200) / 32,   // respawn off-screen right (meters)
      (-300 + Math.random() * 300) / 32,  // random Y height (meters)
    );
  }
}
```

`rb.velocity` on dynamic platforms means physics collision and friction work — the player rides naturally. `freezeX=true` prevents horizontal drift while allowing vertical jump/fall. Raycast ground detection works on moving platforms because position tracks physics in real time.

See `world_scroll_platformer` example for complete two-script implementation (WorldScroller + ScrollJumper).

### Dynamic Spawn System

For games that spawn targets/obstacles at intervals with increasing difficulty:

1. **Object pool**: pre-create N identical objects (build-time DSL — `examples/timed_spawn_system.json`) or grow on demand from a `@serializeProperty Prefab` (runtime — `examples/timed_spawn_difficulty_prefab.json`). Pool authoring details in `skills_root/general/Prefab/SKILL.md`.
2. **Spawn timer** (`onUpdate`): accumulate `dt`, spawn when timer exceeds interval.
3. **Spawn**: cycle through pool, set `visible=true`, reset position/velocity.
4. **Despawn**: track age per object, hide when lifetime expires.
5. **Difficulty progression**: every N seconds, reduce spawn interval and/or lifetime.

```typescript
private spawnInterval = 2.0;
private spawnTimer = 0;
private poolIndex = 0;

onUpdate(dt: number): void {
  this.spawnTimer += dt;
  if (this.spawnTimer >= this.spawnInterval) {
    this.spawnTimer = 0;
    const obj = this.pool[this.poolIndex % this.pool.length];
    this.poolIndex++;
    obj.setEnabledInHierarchy(true);
    const rb = obj.getComponent("RigidBody2D") as APJS.RigidBody2D;
    if (rb) {
      rb.velocity = new APJS.Vector2f(0, 0);
      // World-unit (meters) position, origin = screen center:
      rb.position = new APJS.Vector2f((Math.random() - 0.5) * 20, spawnY);
    }
  }
  this.spawnInterval = Math.max(0.5, this.spawnInterval - 0.001 * dt);
}
```

**Pool vs clone vs clone-and-destroy** — ranked for frequent 2D spawning:

1. **Prefab pool** (preferred) — fixed/bounded counts; source reusable across scenes.
2. **Clone pool** — hide-and-recycle, source is an in-scene SceneObject. Use when no need to persist an asset.
3. **Clone-and-destroy** (avoid for frequent spawns) — GC cost is real; use only for true one-offs.

Details + comparison table: `skills_root/general/Prefab/SKILL.md` "Choosing between prefab.instantiate and SceneObject.clone".

## RecordStart Reset for 2D Physics

When your script controls a `RigidBody2D` (slingshot ball, moving platform, projectile, falling target, …), every game-loop accumulation — position offsets from velocity, lingering velocity from the last impulse, spent ammo / pool occupancy — survives across record stop/start unless you actively reset it. Bind `RecordStart` and apply this canonical reset block. `GameState/SKILL.md` covers the listener wiring; this section is the **single source of truth for the physics reset order**.

### Cache start state once

Snapshot startPosition / start rotation / start gravity flag the first time `onUpdate` runs (or in your lazy init). **Read `anchoredPosition`, not `rb.position`** — `rb.position` can return `(0, 0)` before any physics step has fired (see [Position semantics](#position-semantics-rbposition-vs-anchoredposition)).

```typescript
private startPos: APJS.Vector2f;
private startGravityOn: boolean = true;

private rb!: APJS.RigidBody2D;
private st!: APJS.ScreenTransform;
private inited = false;

onUpdate(dt: number): void {
  if (!this.inited) {
    const obj = this.getSceneObject();
    this.rb = obj.getComponent("RigidBody2D") as APJS.RigidBody2D;
    this.st = obj.getComponent("ScreenTransform") as APJS.ScreenTransform;
    if (!this.rb || !this.st) return;
    // Cache from anchoredPosition (always returns the authored placement):
    this.startPos = new APJS.Vector2f(this.st.anchoredPosition.x, this.st.anchoredPosition.y);
    this.startGravityOn = this.rb.useGravity;
    this.inited = true;
  }
  // ... your normal update logic
}
```

### Reset block — call from `onRecordStart`

Apply in this exact order:

```typescript
private onRecordStart = (_event: APJS.IEvent) => {
  if (!this.inited) return;                              // safe-guard against pre-init RecordStart
  // 1. zero linear and angular velocity FIRST so the body stops integrating
  this.rb.velocity = new APJS.Vector2f(0, 0);
  // 2. zero direction / scripted velocity helpers your script owns
  this.direction = 1;                                    // e.g. MovingPlatform's direction toggle
  // 3. teleport ScreenTransform back to startPos (pixels — anchoredPosition is authoritative for caches)
  this.st.anchoredPosition = new APJS.Vector2f(this.startPos.x, this.startPos.y);
  // 4. restore gravity flag if your script toggled it during play
  this.rb.useGravity = this.startGravityOn;
  // 5. zero per-instance accumulators (score, combo, fireIndex, blockCounted, spent ammo, …)
  this.score = 0;
  this.fireIndex = 0;
};
```

### Pool reset — reset every body, not just the host

For pools (projectiles, ammo, scrolling platforms), iterate the pool and apply the 5-step reset to each entry. Cache each entry's `startPos` at the same time you cache the host's:

```typescript
private poolStartPos: APJS.Vector2f[] = [];

// In init:
for (const obj of this.pool) {
  const st = obj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  this.poolStartPos.push(new APJS.Vector2f(st.anchoredPosition.x, st.anchoredPosition.y));
}

// In onRecordStart:
for (let i = 0; i < this.pool.length; i++) {
  const obj = this.pool[i];
  const rb = obj.getComponent("RigidBody2D") as APJS.RigidBody2D;
  const st = obj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  if (rb) rb.velocity = new APJS.Vector2f(0, 0);
  if (st) st.anchoredPosition = new APJS.Vector2f(this.poolStartPos[i].x, this.poolStartPos[i].y);
  obj.setEnabledInHierarchy(true);                       // un-hide if pool members were hidden on use
}
this.poolIndex = 0;
this.spawnTimer = 0;
```

### Runtime-spawned bodies (clones / prefab instances)

The reset block above only covers objects that exist when `onUpdate` first runs — anything you create later via `template.clone()` or `prefab.instantiate(host)` has no entry in `startPos` / `poolStartPos[]` and survives RecordStart with stale physics state. Track every spawn in a private `activeClones: APJS.SceneObject[]` array, then on RecordStart either drain (Pattern A — destroy) or hide-and-recycle (Pattern B):

| Dimension         | Pattern A — destroy                               | Pattern B — hide-and-recycle                                                    |
| ----------------- | ------------------------------------------------- | ------------------------------------------------------------------------------- |
| Use case          | Bullets, particles, score-fly-ups, true one-shots | Bounded spawn pools you intentionally re-issue across plays                     |
| RecordStart cost  | O(N) `removeSceneObject`                          | O(N) velocity-zero + position-snap + `setEnabledInHierarchy(false)`             |
| Author complexity | Low — one array, one drain loop                   | Medium — parallel `activeClones` + `cloneStartPos` arrays + spawn pointer reset |
| Pick by default   | ✅                                                | only when bounded re-issue is the gameplay design                               |

Full code for both patterns (touch-spawn / timed-spawn 2D variants), the 6-row mistakes table, and drop-in references live in the runtime-spawn sections of this skill plus the APJS examples that match your mechanic.

### Why the order matters

- **velocity → position**: setting position while velocity is still non-zero lets one physics step push the body off-target before the next velocity assignment lands.
- **angularVelocity zeroing**: a spinning body that gets teleported but keeps spinning looks wrong.
- **`useGravity` last**: if the body was floating at start and your script flipped it true during play, restoring it last keeps the body from falling between the position teleport and the gravity restore.

### Common mistakes

| Mistake                                                 | Symptom                                                                              | Fix                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Cached startPos in `onRecordStart` instead of init      | Body resets to current position (no-op)                                              | Cache in init, NOT `onRecordStart`                                           |
| Cached from `rb.position` instead of `anchoredPosition` | Body resets to `(0,0)` (before first physics step, `rb.position` may return `(0,0)`) | Cache from `anchoredPosition`                                                |
| Reset called before `inited` flag flipped               | NPE on `rb.velocity`                                                                 | Add `if (!this.inited) return;` guard                                        |
| Forgot pool members                                     | First take's pool members stay where they fell                                       | Iterate the pool, reset each                                                 |
| Listener registered twice (no matching `.off`)          | Reset runs 2× / 3× / N× per RecordStart                                              | Match every `.on(RecordStart, h)` with `.off(RecordStart, h)` in `onDestroy` |

See `GameState/SKILL.md` §"RecordStart / RecordEnd Lifecycle" for the listener wiring and the optional `RecordEnd` decision tree.
