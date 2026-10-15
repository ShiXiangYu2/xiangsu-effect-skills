---
name: Physics3D
description: 3D物理脚本编写 - 用刚体、碰撞器、关节、射线和物理材质实现三维运动、碰撞与连接约束，涵盖高速运动、堆叠稳定和状态重置，并说明何时使用刚体、何时改用脚本模拟物理。
---

# Physics3D — 3D Physics Scripting

Patterns for controlling 3D physics at runtime: rigid body movement, collision detection, joints, force application, raycasting, stacking stability, and knockdown detection. For linked mechanisms, start with [3D Joints](#3d-joints).

## Choosing the approach: RigidBody vs Pseudo-Physics

This runtime supports two ways to simulate a moving body in a game:

| Approach | When to use | Why |
|----------|-------------|-----|
| **Pseudo-physics (script-driven)** | **Default for high-standard game physics** — slingshot/kick shots with specific landing spots, goal-frame rebounds, post deflections, pinball targets, drawn-path flights. Any shot where the player's success depends on *where the object lands*. | Deterministic motion, reliable collision callbacks at any speed, exact control over rebound feel. Avoids the RigidBody gotchas below. |
| **RigidBody + Collider** | Pile-ups, stacks, chain reactions, falling debris, ragdolls, ambient physics, short-lived VFX where exact trajectory doesn't matter. | Engine handles many-body interactions you wouldn't want to script by hand. |

Use `RigidBody` and the matching joint when the mechanism requires physical connection constraints. For gameplay-critical trajectories without joint constraints, **pick pseudo-physics first**. RigidBody has real problems that bite at speed or precision:

- `CollisionEvent.Enter` is silently dropped at high speed (see "High-Speed Collision" below) — physics still bounces, but damage/score/VFX triggers miss.
- `rb.position`/`rb.velocity`/`rb.rotation` setters are queued one step; same-frame read-after-write returns stale data.
- Position-teleport (`rb.position = ...` every frame) bypasses continuous collision detection; trigger events become late or unreliable.
- `APJS.Physics3D.gravity` scalar overrides can no-op at runtime (scene-load snapshot behavior).
- **All three world-level globals (`gravity`, `gravityFactor`, `timeScale`) are determined by Effect Settings at design time and cannot be changed dynamically from a script.** For custom gravity strength/direction on a single body, set `rb.useGravity = false` and apply a continuous `rb.force = customGravity * mass` (or `rb.addForce(..., ForceMode3D.Force)`) instead.
- Restitution and tangent damping feel random — RigidBody bounces have chaotic tangential components that make goalpost deflections feel unsatisfying.

Pseudo-physics is more code upfront, but it's 100% predictable and runs well. See the next section for the pattern.

## Pseudo-Physics Collision (script-driven, recommended)

Drop the RigidBody for the moving body and compute its trajectory from pure math (drawn path, easing curve, projectile formula, tween). Use the engine only for collision *detection* — `Collider + emitCollisionEvent` still fires `CollisionEvent.Enter` without a RigidBody driving the body. On impact, switch into a scripted rebound integrator for the rest of the flight.

### Ingredients

1. **Collider on the moving body** — SphereCollider / BoxCollider / MeshCollider. Set `emitCollisionEvent = true` from script (not DSL). NO RigidBody needed on this body; colliders fire overlap events on their own.
2. **Scripted position update each frame** — `transform.localPosition = nextWaypoint` along your pre-computed path.
3. **Previous-frame position snapshot** — BEFORE writing the new position each frame, stash the current `localPosition` to `lastX/lastY/lastZ` and the current `dt`. This is non-negotiable: `CollisionEvent.Enter` fires end-of-frame, by which time `transform.localPosition` already holds the NEW value — so `(curr - prev)/dt` would be zero. You need the PRE-write snapshot to estimate incoming velocity.
4. **Reflection on collision** — decompose the estimated velocity against the surface normal; perpendicular flips with `RESTITUTION`, tangential is lightly damped with `TANGENT_DAMP`.
5. **Post-collision branch** — stop following the scripted path; run a simple gravity + ground-damping integrator until a `resultDelay` elapses.

### Path-follow tick with pre-write snapshot

```typescript
private lastX = 0;  private lastY = 0;  private lastZ = 0;
private lastDt = 0.016;
private hasLastPos = false;

private tickFlying(dt: number): void {
  // ... compute nextPos (px, py, pz) from path / easing / formula ...

  // Snapshot PREVIOUS pose BEFORE applying the new one. Required so
  // onCollision can compute a valid (curr - prev)/dt velocity — the
  // event fires deferred, by which point localPosition already holds
  // the new value we're about to set.
  const prev = this.transform.localPosition;
  this.lastX = prev.x;  this.lastY = prev.y;  this.lastZ = prev.z;
  this.lastDt = dt;
  this.hasLastPos = true;

  this.transform.localPosition = new APJS.Vector3f(px, py, pz);
}
```

### Reflection math

Decompose the incoming velocity `v` into a component along the surface normal (perpendicular) and a component on the surface plane (tangential). `v = v_perp + v_tang`. Then:
- Flip `v_perp` with `RESTITUTION` (0.3–0.6) — how bouncy the rebound feels.
- Scale `v_tang` by `TANGENT_DAMP` (0.6–0.9) — preserves forward momentum on grazing hits, which is the "inner-post deflection still scores" feel.

```typescript
private readonly RESTITUTION = 0.5;
private readonly TANGENT_DAMP = 0.6;
private readonly MIN_IMPACT_SPEED = 6;  // floor so grazing hits pop off visibly

private onCollision = (event: APJS.IEvent): void => {
  if (this.collided || !this.hasLastPos) return;
  const infos = event.args[0] as APJS.CollisionInfo[];
  if (!infos || infos.length === 0) return;
  const n = infos[0].normal;

  // Estimate incoming velocity from the pre-write snapshot
  const curr = this.transform.localPosition;
  const dt = Math.max(this.lastDt, 0.001);
  const vx = (curr.x - this.lastX) / dt;
  const vy = (curr.y - this.lastY) / dt;
  const vz = (curr.z - this.lastZ) / dt;

  // v = v_perp + v_tang
  const dot   = vx*n.x + vy*n.y + vz*n.z;
  const perpX = dot*n.x, perpY = dot*n.y, perpZ = dot*n.z;
  const tangX = vx - perpX, tangY = vy - perpY, tangZ = vz - perpZ;

  // Rebound = -v_perp·RESTITUTION + v_tang·TANGENT_DAMP
  let rx = -perpX*this.RESTITUTION + tangX*this.TANGENT_DAMP;
  let ry = -perpY*this.RESTITUTION + tangY*this.TANGENT_DAMP;
  let rz = -perpZ*this.RESTITUTION + tangZ*this.TANGENT_DAMP;

  // Min-impact floor so near-grazing hits still pop off visibly
  const rspeed = Math.sqrt(rx*rx + ry*ry + rz*rz);
  if (rspeed < this.MIN_IMPACT_SPEED && rspeed > 0.01) {
    const k = this.MIN_IMPACT_SPEED / rspeed;
    rx *= k;  ry *= k;  rz *= k;
  }
  this.vx = rx;  this.vy = ry;  this.vz = rz;
  this.collided = true;
};
```

### Post-collision integration (gravity + ground damping)

After `collided = true`, switch your `onUpdate` branch from path-follow to the scripted rebound. Plain Euler integration with gravity, ground clamp, and damping coefficients:

```typescript
private readonly GRAVITY = 18;          // scene-scale, not 9.81 — tune visually
private readonly GROUND_BOUNCE = 0.35;  // vertical restitution on ground hit
private readonly GROUND_SCRUB  = 0.6;   // horizontal damping on ground hit

private applyPseudoPhysics(dt: number): void {
  const p = this.transform.localPosition;
  this.vy -= this.GRAVITY * dt;

  let nx = p.x + this.vx * dt;
  let ny = p.y + this.vy * dt;
  let nz = p.z + this.vz * dt;

  const groundY = this.getGroundY(nz);  // your field/ground function
  if (ny <= groundY) {
    ny = groundY;
    if (this.vy < 0) this.vy = -this.vy * this.GROUND_BOUNCE;
    this.vx *= this.GROUND_SCRUB;
    this.vz *= this.GROUND_SCRUB;
  }

  this.transform.localPosition = new APJS.Vector3f(nx, ny, nz);
}
```

### Tuning constants — starting points

| Constant | Typical | Effect |
|----------|---------|--------|
| `RESTITUTION` | 0.3–0.6 | Perpendicular rebound scale. Higher = bouncier. |
| `TANGENT_DAMP` | 0.6–0.9 | Tangential preservation. Higher = more "slide along the post" feel; inner-post deflections still carry forward. |
| `MIN_IMPACT_SPEED` | 4–8 | Floor so near-grazing hits pop off instead of dribbling. Scene-scale. |
| `GRAVITY` | 10–30 | Scene-scale, not real-world. Tune until the falling arc looks right — don't port Unity's 9.81. |
| `GROUND_BOUNCE` | 0.2–0.5 | Vertical damping on each ground hit. Ball settles in 2–4 bounces. |
| `GROUND_SCRUB` | 0.5–0.8 | Horizontal damping on each ground hit. Prevents infinite skidding. |
| `RESULT_DELAY` | 0.6–1.0s | Seconds to let the bounce play before transitioning to RESULT state. |

### Reference implementation

See `CurvingTheBallLogic.ts` in the "Curving the Ball" template — `onBallCollision`, `applyCollisionPhysics`, and the pre-write snapshot in `tickFlying` are the canonical pattern.

## RigidBody

Get via `getComponent("RigidBody") as APJS.RigidBody`.

### Key Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `static` | boolean | false | Body does not simulate. Blessed sleep flag — there is **no per-body auto-sleep**; flip this manually when a body should stop simulating. Static bodies still collide. |
| `useGravity` | boolean | true | Whether affected by gravity. |
| `mass` | number | 1.0 | Mass in kg. |
| `velocity` | Vector3f | (0,0,0) | Linear velocity (read/write). |
| `angularVelocity` | Vector3f | (0,0,0) | Angular velocity in rad/s. |
| `position` | Vector3f | (0,0,0) | World position (read/write, bypasses physics). |
| `rotation` | Quaternionf | identity | World rotation (read/write). |
| `eulerAngles` | Vector3f | (0,0,0) | Euler rotation in degrees. |
| `damping` | number | 0.0 | Linear damping (air resistance). |
| `angularDamping` | number | 0.0 | Angular damping. |
| `freezeX` / `freezeY` / `freezeZ` | boolean | false | Lock axis movement (intended for moving platforms, not sleep). |
| `force` | Vector3f | (0,0,0) | Continuous force (setting replaces accumulated). |
| `torque` | Vector3f | (0,0,0) | Continuous torque. |
| `inertiaTensor` | Vector3f | (1,1,1) | Rotational inertia. |
| `physicsAnimation` | boolean | false | Blend physics with animation. |

**No `gravityFactor` property on `RigidBody`.** Only a world-wide `APJS.Physics3D.gravityFactor` scalar exists, and setting it at runtime from a script has been observed to be a no-op (scene-load snapshot). For per-body gravity shaping, use `mass`, toggle `useGravity`, or apply explicit `rb.addForce(gravityForce, ForceMode3D.Force)` in `onStart`. To customize gravity for a body, the recommended pattern is:

```typescript
// onStart (once if using ForceMode3D.Force which is continuous):
rb.useGravity = false;                                       // disable engine gravity
const customG = new APJS.Vector3f(0, -10, 0);              // your desired gravity, a little stronger than real-world -9.80
rb.addForce(customG.multiplyScalar(rb.mass), APJS.ForceMode3D.Force);
// Equivalently: `rb.force = customG.multiplyScalar(rb.mass)` — `force` replaces, addForce adds.
// If you want to change the direction of gravity, set `customG` to the desired direction.
// If you want to change the strength of gravity, set `rb.mass` to the desired mass.
```

You can also just toggle `useGravity` to enable/disable the engine default for a single body, or scale `mass` to weight it more/less inside the (non-overridable) world gravity field.

### Reading Position

For a 3D `RigidBody`, `rb.position` is the world-space pose held by the physics engine (in meters); writing it teleports the body, bypassing velocity/force simulation. Do **not** modify `Transform.localPosition` directly on a physics-controlled object — the physics engine will overwrite it.

### Read-after-write lag (write-queued setters)

Reading `rb.position` / `rb.velocity` / `rb.angularVelocity` / `rb.rotation` immediately after assigning them returns the **pre-write cached snapshot** — writes are queued for the next physics step. Don't branch on read-after-write within the same callback. If you need to confirm a teleport, do it in the next `onUpdate`.

### Reset pattern

To snap a rigid body back to a known state (retry button, out-of-bounds, respawn), set all four properties in one callback:

```typescript
rb.velocity = new APJS.Vector3f(0, 0, 0);
rb.angularVelocity = new APJS.Vector3f(0, 0, 0);
rb.position = new APJS.Vector3f(0, 10, 0);        // target position
rb.rotation = APJS.Quaternionf.identity();        // target rotation
```

- **Order doesn't matter** — all four are queued for the next physics step together.
- **No `static` toggle needed** for simple teleports — direct assignment is reliable across all body states (bouncing, falling, settled).
- **`Quaternionf.identity()` is a method**, not a property — must call it with `()`. Also valid: `APJS.Quaternionf.makeFromEulerAngles(new APJS.Vector3f(0, 0, 0))`.

## RecordStart Reset for 3D Physics

When your script controls a `RigidBody` (slingshot ball, falling target, knockdown tower, hoop ball, …), every game-loop accumulation survives across record stop/start unless you actively reset it. Bind `RecordStart` and apply this canonical reset block. `GameState/SKILL.md` covers listener wiring; this section is the **single source of truth for the 3D physics reset order**.

The RigidBody-only reset block (§"Reset pattern" above) shows the four-line snap. This section extends it for: cached startState, pool iteration, and the `RestSleeper.wake()` interaction.

### Cache start state once

```typescript
private startPos!: APJS.Vector3f;
private startRot!: APJS.Quaternionf;
private startGravityOn: boolean = true;

private rb!: APJS.RigidBody;
private inited = false;

onUpdate(dt: number): void {
  if (!this.inited) {
    const obj = this.getSceneObject();
    this.rb = obj.getComponent("RigidBody") as APJS.RigidBody;
    if (!this.rb) return;
    this.startPos = new APJS.Vector3f(this.rb.position.x, this.rb.position.y, this.rb.position.z);
    this.startRot = this.rb.rotation;
    this.startGravityOn = this.rb.useGravity;
    this.inited = true;
  }
  // ... your normal update logic
}
```

### Reset block — call from `onRecordStart`

```typescript
private onRecordStart = (_event: APJS.IEvent) => {
  if (!this.inited) return;
  // 1. zero linear velocity
  this.rb.velocity = new APJS.Vector3f(0, 0, 0);
  // 2. zero angular velocity (otherwise the body keeps spinning after teleport)
  this.rb.angularVelocity = new APJS.Vector3f(0, 0, 0);
  // 3. teleport position to cached startPos (rb.position is reliable in 3D, unlike 2D)
  this.rb.position = new APJS.Vector3f(this.startPos.x, this.startPos.y, this.startPos.z);
  // 4. restore rotation
  this.rb.rotation = this.startRot;
  // 5. restore gravity flag if your script toggled it during play
  this.rb.useGravity = this.startGravityOn;
  // 6. zero any script-owned accumulators (score, combo, fireIndex, blockCounted, ammo, …)
  this.score = 0;
  this.fireIndex = 0;
};
```

> **Read-after-write reminder** (Physics3D §RigidBody §"Read-after-write lag"): don't read `rb.position` immediately after writing — you'll get the pre-write snapshot for one step. The reset still lands; just don't branch on it within the same callback.

### Pool reset (slingshot ammo, knockdown blocks)

For ammo pools / knockdown towers, iterate every body and apply the same reset. Cache each entry's pose at init:

```typescript
private poolStartPos: APJS.Vector3f[] = [];
private poolStartRot: APJS.Quaternionf[] = [];

// In init (after pool is wired via @serializeProperty):
for (const obj of this.pool) {
  const rb = obj.getComponent("RigidBody") as APJS.RigidBody;
  if (!rb) continue;
  this.poolStartPos.push(new APJS.Vector3f(rb.position.x, rb.position.y, rb.position.z));
  this.poolStartRot.push(rb.rotation);
}

// In onRecordStart:
for (let i = 0; i < this.pool.length; i++) {
  const obj = this.pool[i];
  const rb = obj.getComponent("RigidBody") as APJS.RigidBody;
  if (!rb) continue;
  rb.velocity = new APJS.Vector3f(0, 0, 0);
  rb.angularVelocity = new APJS.Vector3f(0, 0, 0);
  rb.position = new APJS.Vector3f(this.poolStartPos[i].x, this.poolStartPos[i].y, this.poolStartPos[i].z);
  rb.rotation = this.poolStartRot[i];
  obj.setEnabledInHierarchy(true);                       // un-hide if pool members were hidden on use
}
this.fireIndex = 0;
this.blockCounted = 0;
```

### `RestSleeper` interaction — must `.wake()` before resetting blocks

If your tower uses the **`RestSleeper` static-base + sleep lifecycle** (Physics3D §"Stacked Physics Stability"), each block flipped to `static = true` once it settled. Setting `rb.position` on a static body is allowed but the engine doesn't re-integrate it — the body stays where you put it but won't react to subsequent contacts. So **wake every block back to dynamic before applying the reset block above**:

```typescript
@serializeProperty private blocks: APJS.SceneObject[] = [];

private onRecordStart = (_event: APJS.IEvent) => {
  if (!this.inited) return;
  // 1. wake every block — flips static back to false
  for (const blk of this.blocks) {
    const sleeper = blk.getComponent("RestSleeper") as RestSleeper;
    if (sleeper) sleeper.wake();
  }
  // 2. NOW apply the canonical reset block to each block
  for (let i = 0; i < this.blocks.length; i++) {
    const rb = this.blocks[i].getComponent("RigidBody") as APJS.RigidBody;
    if (!rb) continue;
    rb.velocity = new APJS.Vector3f(0, 0, 0);
    rb.angularVelocity = new APJS.Vector3f(0, 0, 0);
    rb.position = this.blockStartPos[i];
    rb.rotation = this.blockStartRot[i];
  }
  // 3. let RestSleeper re-detect rest within ~60 frames (sleepFrames default)
  //    No need to manually flip static=true — RestSleeper does it automatically.
};
```

> **Reminder**: row-0 blocks that were `static=true` *in the editor* (per Physics3D §"Stacked Physics Stability" winning pattern) start asleep. `RestSleeper.wake()` already honors this — it only flips static if the block was awake at editor time. The reset still works because position assignment lands either way; the wake just ensures upper rows can re-settle physics-correctly.

### Runtime-spawned bodies (clones / prefab instances)

The reset block above only covers objects that exist when `onUpdate` first runs — anything you create later via `template.clone()` or `prefab.instantiate(host)` has no entry in `startPos` / `poolStartPos[]` / `poolStartRot[]` and survives RecordStart with stale physics state. If a `RestSleeper` flipped a runtime-spawned body to `static = true` mid-play, it's frozen at the sleep pose until you wake it. Track every spawn in a private `activeClones: APJS.SceneObject[]` array, then on RecordStart either drain (Pattern A — destroy) or hide-and-recycle (Pattern B):

| Dimension | Pattern A — destroy | Pattern B — hide-and-recycle |
|---|---|---|
| Use case | Impulse-launched spheres, knock-out cubes, debris, particles, true one-shots | Bounded spawn pools you intentionally re-issue across plays |
| RecordStart cost | O(N) `removeSceneObject` (+ `RestSleeper.wake()` first if static-base sleep is in play) | O(N) wake + 6-step reset + setEnabledInHierarchy(false) |
| Author complexity | Low — one array, one drain loop | Medium — parallel `activeClones` + `cloneStartPos` + `cloneStartRot` arrays + spawn pointer reset |
| Pick by default | ✅ | only when bounded re-issue is the gameplay design |

`RestSleeper`-flipped-static bodies MUST be `.wake()`-d **before** removal or repositioning — otherwise the engine treats the body as a static pose and may not honor the cleanup. The canonical references for both patterns are the runtime-spawn sections in this skill plus the APJS examples listed below.

### Why the order matters (3D)

- Same as 2D **plus**: `RestSleeper.wake()` MUST come **before** `rb.position = ...` for stacked towers, otherwise upper rows still sit on a static base that no longer matches their pose.
- **`useGravity` restore is last**: a body teleported to mid-air with gravity already on starts falling between teleport and the next physics step.

### Common mistakes (3D-specific)

| Mistake | Symptom | Fix |
|---|---|---|
| Forgot `RestSleeper.wake()` for stacked tower | Blocks teleport to startPos but stay static — ball flies through them | Call `.wake()` on every sleeper before the reset block |
| Read `rb.position` immediately after assignment to verify | Returns pre-write (often 0,0,0) | Recompute from your stored `startPos` instead |
| Used `Quaternionf.identity` (no parens) | TS compile error or wrong rotation | `APJS.Quaternionf.identity()` — it's a method |
| Pool iteration without `setEnabledInHierarchy(true)` | Pool members that got hidden on consumption stay invisible | Re-enable before reset |

See `GameState/SKILL.md` §"RecordStart / RecordEnd Lifecycle" for listener wiring and the optional `RecordEnd` decision tree.

## addForce() and ForceMode3D

**CRITICAL**: Always specify `ForceMode3D.Impulse` (or `VelocityChange`) for one-shot forces. The default `ForceMode3D.Force` applies a continuous force that persists — if it exceeds gravity the object flies away forever.

```typescript
const rb = this.getSceneObject().getComponent("RigidBody") as APJS.RigidBody;

// One-shot upward push (mass-dependent) — object will fall back down
rb.addForce(new APJS.Vector3f(0, 50, 0), APJS.ForceMode3D.Impulse);

// Continuous rightward force (applied every physics step while set)
rb.addForce(new APJS.Vector3f(10, 0, 0), APJS.ForceMode3D.Force);
```

| ForceMode3D | Behavior | Mass | Use Case |
|-------------|----------|------|----------|
| `Force` | Continuous, applied each step | Uses mass | Wind, thrust, conveyor |
| `Acceleration` | Continuous, applied each step | Ignores mass | Uniform movement |
| `Impulse` | One-shot, instant | Uses mass | Jump, hit, explosion |
| `VelocityChange` | One-shot, instant | Ignores mass | Teleport-like push, slingshot launch |

**Force magnitude reference** — the standard cm-scale gravity is about **980 u/s²** (`APJS.Physics3D.gravity ≈ (0, -980, 0)`, i.e. 100× `9.8`). Projectile impulses must scale correspondingly — do NOT port Unity numbers blindly. For human-scale scenes (1u ball, ~10u flight), override gravity per body at init:

> **Reference example**: `context.workspace.APJS/examples/physics3d_tap_impulse.json` — minimal "tap → ForceMode3D.Impulse" pattern with the lazy-init guard. Use as the starting skeleton when adapting impulse-based input (charge-meter, tap-throw, jump).

```typescript
// Per-body custom gravity (works at runtime; the world gravity scalar does not).
rb.useGravity = false;
rb.force = new APJS.Vector3f(0, -9.81 * rb.mass, 0);
```

### addTorque()

```typescript
rb.addTorque(new APJS.Vector3f(0, 10, 0), APJS.ForceMode3D.Impulse);  // Spin around Y
```

### addForceAt()

Apply force at a specific point (generates both force and torque):

```typescript
const pushForce = new APJS.Vector3f(0, 0, 10);
const pushPoint = new APJS.Vector3f(1, 0, 0);
rb.addForceAt(pushForce, pushPoint, true, APJS.ForceMode3D.Impulse);
```

### velocity

```typescript
const vel = rb.velocity;                              // read
rb.velocity = new APJS.Vector3f(0, 10, 0);            // write (queued for next step)
```

## Colliders (BoxCollider / SphereCollider / CapsuleCollider / MeshCollider)

### BoxCollider

```typescript
const col = obj.getComponent("BoxCollider") as APJS.BoxCollider;
col.size = new APJS.Vector3f(8, 8, 8);
col.center = new APJS.Vector3f(0, 0, 0);
```

### SphereCollider

```typescript
const col = obj.getComponent("SphereCollider") as APJS.SphereCollider;
col.radius = 4;
```

### CapsuleCollider

```typescript
const col = obj.getComponent("CapsuleCollider") as APJS.CapsuleCollider;
col.radius = 2;                                    // hemispherical end radius
col.height = 6;                                    // center cylinder height only
col.rotation = new APJS.Vector3f(0, 0, 90);        // euler degrees — orient the long axis
col.offset = new APJS.Vector3f(0, 0, 0);
```

**CapsuleCollider schema facts**:
- Fields: `radius`, `height`, `offset` (Vector3f), `rotation` (Vector3f euler degrees), `physicsMaterial`, `isTangible`, `showCollider`, `interactable`.
- **No `fitMesh`** — radius/height must be set manually.
- **No `direction`/`axis` enum** — orient the capsule via `rotation` (Vector3f euler).
- **Default unrotated axis is +Y** — with `rotation = (0,0,0)`, the capsule stands upright along the local Y axis.
- `height` is the center-cylinder length only, so the total tip-to-tip capsule length is `height + 2 * radius`.

**CapsuleCollider best practices**:
- Use `rotation` to align the collider to the mesh; for example, rotate 90° around X to align the capsule's long axis with Z.
- For an exact capsule match, keep the host Transform scale uniform (`x = y = z`), ideally `{1,1,1}`, and define the shape with `radius`, `height`, `offset`, and `rotation`.
- Non-uniform scale deforms the visual mesh, so a single CapsuleCollider can no longer match it exactly.
- Choose the simplest collider that satisfies gameplay: use CapsuleCollider for capsule-like behavior, BoxCollider when a coarse solid volume is enough, and MeshCollider only when primitive colliders are insufficient.

### MeshCollider

```typescript
const col = obj.getComponent("MeshCollider") as APJS.MeshCollider;
col.convex = true;
```

### Common Collider Properties

| Property | Type | Description |
|----------|------|-------------|
| `center` | Vector3f | Center position offset. |
| `isTangible` | boolean | true = solid collision; false = trigger (pass-through, still fires events). |
| `emitCollisionEvent` | boolean | **APJS runtime-only** — must be set from script (`col.emitCollisionEvent = true`). NOT settable via `set_component`. |
| `interactable` | boolean | Allow Physics Interactor node to drag this object. |
| `physicsMaterial` | PhysicsMaterial \| null | Friction/bounciness settings. Wire format: `{"guid": "<guid>"}` or `{"guid": {"$ref": "<alias>"}}` — property-level `{"$ref":…}` FAILS. |
| `rotation` | Quaternionf | Collider rotation. |
| `eulerAngles` | Vector3f | Collider rotation in degrees. |

### Collider scaling — dimensions inherit host Transform scale

`radius`, `height`, `size`, and `center` are in the **host object's local units**. If the host has `localScale=0.1`, the effective collider is 0.1× the value you set — applies to ALL collider types. Account for this when attaching to small or large hosts.

### DSL Setup

```json
[
  {"command_type":"add_component","params":{"scene_object":{"$ref":"ball"},"type":"BoxCollider"},"alias":"col"},
  {"command_type":"set_component","params":{"guid":{"$ref":"col"},"properties":{"fitMesh":true}}}
]
```

`fitMesh=true` auto-sizes BoxCollider / SphereCollider to the mesh bounds. CapsuleCollider has no `fitMesh` — set `radius` / `height` manually.

**Do NOT** set `emitCollisionEvent` via `set_component` — the engine rejects it. Set it from APJS at runtime, after `getComponent`.

**`add_builtin_object("Sphere"|"Cube")` does NOT auto-attach RigidBody+Collider.** Always follow with explicit `add_component` calls for RigidBody and the desired Collider. (Some early Cube/Ground creations appear to return physics components in the response payload, but that's return-shape noise — subsequent objects need explicit adds.)

## 3D Joints

Choose the joint by the relative motion the mechanism should allow. Query the selected component's knowledge before adding it through `edit_by_dsl`.

| Goal | Component | Main configuration |
| --- | --- | --- |
| Door, lever, or axle rotating around one axis | `HingeJoint` | `axis`, `useLimits`, `minAngle`, `maxAngle` |
| Common pivot with free relative rotation, such as linked rigid segments | `PointJoint` | `anchor`, `connectedAnchor`; aligns the two anchors, not a fixed-length rope |
| Compliant connection returning toward its initial separation | `SpringJoint` | `damping`, `tolerance`; start within `[0, 1]` and verify the actual stretch |
| Welded or breakable assembly with fixed relative pose | `FixedJoint` | `anchorType`, `breakingForce`, `breakingTorque` |

- Both endpoints need enabled `RigidBody` components. Bind `connectedBody` to the other body's `Transform` reference; leaving it empty does not create a world anchor. For a fixed support, create a separate body with `static=true`.
- `anchor` and `connectedAnchor` are local `Vector3f` positions on their respective bodies; `HingeJoint.axis` is a local rotation axis. Set these before initializing the joint. After editing anchors, reset the preview so the constraint is recreated. `FixedJoint` exposes manual anchors when `anchorType="Custom"`.
- Configure editor fields through `set_component`; for script control, check the project's APJS definitions for public setters and available examples. Do not assume every editor field is exposed at runtime.
- 3D joints have no `breakable` switch. `breakingForce=-1` disables positional break checks; `HingeJoint` and `FixedJoint` also use `breakingTorque` for their angular constraint. A broken constraint stops solving without freezing the bodies; a compound joint can lose one constraint while retaining the other.
- Verify a fresh initial state, movement under force, angle or stretch limits, and break behavior when required, using `skills_root/general/PreviewInteraction/SKILL.md`. Joint constraints do not create visible ropes or chains; author those visuals separately.

## PhysicsMaterial

Controls friction and bounciness on colliders.

### Creation

```json
[
  {"command_type":"add_builtin_resource","params":{"resource_type":"Physics Matter"},"alias":"mat"},
  {"command_type":"set_resource_properties","params":{"guid":{"$ref":"mat"},
    "properties":{"bounciness":0.7,"dynamicFriction":0.2,"staticFriction":0.2}}}
]
```

`resource_type` is `"Physics Matter"` (with space) — NOT `"PhysicsMaterial"`.

### Properties (APJS names)

| Property | Default | Range | Description |
|----------|---------|-------|-------------|
| `bounciness` | 0.3 | 0.0–1.0 | Restitution coefficient. |
| `dynamicFriction` | 0.6 | 0.0–999999 | Kinetic friction coefficient. |
| `staticFriction` | 0.61 | 0.0–999999 | Static friction coefficient. |

### Mount on collider

```json
{"command_type":"set_component","params":{"guid":{"$ref":"col"},
  "properties":{"physicsMaterial":{"guid":{"$ref":"mat"}}}}}
```

**Wire format** (single-resource shape, same as `Texture`):
- ✅ `{"guid": "<literal_guid>"}` — cross-batch
- ✅ `{"guid": {"$ref": "<alias>"}}` — same-batch (alias resolves inside `guid`)
- ❌ `{"$ref": "<alias>"}` — fails with `Cannot deserialize <alias> to PhysicsMaterial`; that's the material-LIST-item shape, not the single-resource shape.

Mounting on only one side of the contact (e.g. just the ball) is sufficient — the engine combines with the other side's default.

### Bounciness reference table

| `bounciness` | Behavior | When to use |
|--------------|----------|-------------|
| 0.0 | Dead stop — hits ground and stays. No visible rebound. | Floor/ground; dead weight. |
| 0.3 | Subtle bounce — peak ~5–10% of drop height; one bounce and rest. | Realistic ball-on-grass feel. |
| 0.7 | Clear single bounce — peak ~45–50% of drop height; prominent without chaos. | Bouncy rubber balls; satisfying impact. |
| 0.95 | High multi-bounce — peak ~90% of drop height; 2–3 visible bounces. | Pinball, pachinko, super-balls; dramatic. |

**Default restitution without PhysicsMaterial ≈ 0.288** — bodies still bounce a little even with no material attached.

#### Ball-on-thin-rim (1u sphere onto 0.1u-thick tangible bar; gravity = −9.81)

The above table is for ball-on-flat-ground. For sphere → thin tangible bar (e.g. a hoop's near-rim), the effective rebound is lower because ball-only restitution combines with rim-only restitution (≈ geometric mean). With the **default ball** (no PhysicsMaterial, ≈ 0.288) and the rim's `bounciness` swept:

| `bounciness` (rim) | Rebound height (% of drop) | Effective e | Read |
|--------------------|----------------------------|-------------|------|
| 0.10 | ~3.8% | 0.18 | "Absorbed" — wrong feel for a hoop. |
| 0.30 | ~8.3% | 0.27 | "Tipped" — too dead for a rim shot. |
| **0.60** | **~18.6%** | **0.42** | **Recommended for "ball clipped the rim"** — clear deflection, ball stays near the hoop. |
| 0.95 | ~36% | 0.59 | Pinball-feel — kicks ball far from hoop, rarely lands. |

For a "second-chance rim" feel on a basketball-style hoop: mount **`bounciness=0.6`** PhysicsMaterial on the rim's collider; leave the ball with the engine default. See `docs/game-coverage/interactive/projectile-3d/experiments/H4-bouncy-hoop-rim.md` for the sweep methodology + raw data.

**Caveat — `Enter` fires LATE on rim contacts.** Across the H4 sweep at 8.19 u/s impact, the `CollisionEvent.Enter` callback lagged the actual bounce moment by 0.59 s (b=0.10) up to 2.14 s (b=0.95) — the lag *grows* with rim bounciness because the post-bounce arc lengthens. If you need to play SFX/VFX *at the bounce moment*, drive it from velocity-sign-flip detection in `onUpdate` (`prev_vy < -1 && cur_vy > -0.5`) rather than the Enter callback. See *§High-Speed Collision*.

#### Bowling short-lane profile (verified B2)

The authoritative bowling reference project (`/Users/bytedance/Documents/AIBridge/bowling`, relearned 2026-05-13 to replace the earlier B1/B2 hybrid guidance) produced a reusable material/body stack for a believable short-lane roll:

| Element | Verified value | Read |
|---|---|---|
| World gravity | `-9.8` | Human-scale, not arcade-heavy. |
| Ball body | `mass=6`, `damping=0.02`, `angularDamping=0.01`, `freezeY=true` | Heavy roll, visible spin, no lane-hop. |
| Ball material | `dynamicFriction=0.5`, `staticFriction=0.5`, `bounciness=0.04` | Controlled roll with almost no rebound. |
| Lane material | `dynamicFriction=0.01`, `staticFriction=0.01`, `bounciness=0.02` | Long clean travel; preserves speed. |
| Pin body | `mass=0.22`, `damping=0.02`, `angularDamping=0.005` | Tips over instead of skating. |
| Pin material | `dynamicFriction=4.1`, `staticFriction=4.1`, `bounciness=0.1` | Quiet rack at rest; decisive topple on impact. |
| Wall material | `dynamicFriction≈0.6`, `bounciness=0.3` | One readable rebound on misses. |

Use this as the starting profile when the prompt wants **bowling realism** rather than a generic sports-ball bounce. The key ratio is not one literal number — it is the relationship: **lane friction << pin friction**, **ball bounce very low**, **wall bounce moderate**, and **ball mass >> pin mass**.

## Collision Events

**CRITICAL**: Two requirements for collision events to fire:
1. `collider.emitCollisionEvent = true` on the collider you're listening on — must be set from APJS at runtime (not via DSL).
2. Use `getObjectEmitter(collider)` — pass the **Collider component**, NOT the SceneObject.

```typescript
@component()
export class CollisionHandler extends APJS.BasicScriptComponent {
  private collisionCallback: (event: APJS.IEvent) => void;
  private collider: APJS.BoxCollider;
  private inited = false;

  onUpdate(dt: number): void {
    if (!this.inited) {
      const obj = this.getSceneObject();
      if (!obj) return;

      this.collider = obj.getComponent("BoxCollider") as APJS.BoxCollider;
      if (!this.collider) return;
      this.inited = true;

      this.collider.emitCollisionEvent = true;       // REQUIRED, runtime-only

      this.collisionCallback = (event: APJS.IEvent) => {
        const infos = event.args[0] as APJS.CollisionInfo[];
        for (const info of infos) {
          if (info.otherObject) console.log("Hit: " + info.otherObject.name);
        }
      };

      APJS.EventManager.getObjectEmitter(this.collider)
        .on(APJS.CollisionEvent.Enter, this.collisionCallback, this);
    }
  }

  onDestroy(): void {
    if (this.collisionCallback && this.collider) {
      APJS.EventManager.getObjectEmitter(this.collider)
        .off(APJS.CollisionEvent.Enter, this.collisionCallback, this);
    }
  }
}
```

> **Reference examples**: `context.workspace.APJS/examples/physics3d_collision_handler.json` — minimal Enter/Stay/Exit handler skeleton; reuse as the starting skeleton for hoop / target / score-zone patterns. `context.workspace.APJS/examples/physics3d_gravity_collision.json` — gravity-drop + ground-Enter handler with the lazy-init pattern; closest fit when an object lands on a surface and you want a one-shot landing event. `context.workspace.APJS/examples/hoop_shot_dual_trigger.json` — two `isTangible=false` BoxCollider triggers (top + bottom) with a single-vs-dual-trigger debounce window; verified end-to-end. Use as the canonical reference whenever you need pass-through detection (basketball hoop, dart, ring-toss, scoring gate). Cross-listed in `ProjectileGames/SKILL.md` §7.

### Collision Event Types

| Event | When Fired |
|-------|-----------|
| `CollisionEvent.Enter` | First frame of contact. |
| `CollisionEvent.Stay` | Every frame while in contact. |
| `CollisionEvent.Exit` | First frame after separation. |

### CollisionInfo Fields

| Field | Type | Description |
|-------|------|-------------|
| `point` | Vector3f | Contact point in world space (convert to camera-local with `Quaternionf.clone().inverse().multiplyVector` for comparisons against camera-parented colliders). |
| `normal` | Vector3f | Contact normal in world space. |
| `otherObject` | SceneObject \| null | The other colliding object. |

> **`point` is where the SPHERE SURFACE touched the box, NOT the sphere's center.** A ball with SphereCollider radius 11 entering the TOP of a BoxCollider will report `point.y ≈ box.topY` even when the ball's center is at `box.topY + 11`. Use this — it matches "where the ball visibly hit" — but don't mistake it for the ball's own position.

### Reading RigidBody position / velocity

Setting `ballRB.position = ...` then immediately reading `ballRB.position` or `Transform.localPosition` in the SAME frame can return stale / zero data — the setter defers sync to the next physics step. For logic that needs the just-applied position (e.g. a script-side catch test after position-teleport), recompute the world position from your source formula instead of re-reading the RigidBody.

### Position-teleport and trigger events

Writing `rigidBody.position = newPos` every frame (position-teleport) bypasses continuous collision detection. Trigger-collider events **do still fire** on discrete overlap, but they can be late or unreliable when the body jumps a large distance per frame (e.g. a fast projectile teleported past a thin trigger in a single step). For reliable detection of a teleported body entering a zone, add a script-side test that reads the zone's live `Transform.localPosition` + `Collider.size` and compares the teleported body's position each frame — keep the physics trigger as a secondary path.

### Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `getObjectEmitter(sceneObject)` | Callback never fires, no error. | Use `getObjectEmitter(collider)`. |
| `getGlobalEmitter()` for collision | Callback never fires. | Use `getObjectEmitter(collider)`. |
| `emitCollisionEvent: true` in DSL `set_component` | Engine rejects property. | Set from APJS runtime: `col.emitCollisionEvent = true`. |
| Forgot `emitCollisionEvent = true` | Callback never fires. | Set it before registering. |
| `addForce()` without Impulse mode | Object flies away forever. | Use `ForceMode3D.Impulse` or `VelocityChange` for one-shot forces. |
| `getSceneObject()` in `onStart()` | Returns undefined. | Use lazy init in `onUpdate()`. |
| `camRot.inverse()` then using `camRot` | Camera rotation silently mutated — scene breaks after first call. | Use `camRot.clone().inverse()`; `Quaternionf.inverse()` is in-place and returns the modified `this`. |
| Reading `rigidBody.position` right after setting it | Returns stale value (often 0,0,0). | Recompute from your source-of-truth formula, or wait one frame. |
| Hardcoded `g = 9.8` for projectile math at cm scale | Arcs overshoot ~100×. | Read `APJS.Physics3D.gravity.y` — positions are in cm, gravity is ~980. |

### High-Speed Collision — callback dropping (NOT physics tunneling)

The engine does NOT physics-tunnel at any tested velocity (10–200 u/s through a 1-unit wall). Internal swept detection halts fast bodies at colliders and applies correct restitution.

**BUT** the script-visible `CollisionEvent.Enter` callback is **silently suppressed at high speeds** when the per-step travel exceeds the target's thickness along the travel axis. Physics still bounces correctly, but damage / score / VFX / SFX triggers all miss.

**Formula**:
```
reliable_event_velocity ≈ collider_thickness / fixed_physics_dt
                        ≈ collider_thickness / 0.0167 s        (60 Hz physics)
                        ≈ 60 × collider_thickness              (u/s per unit thickness)
```

- ❌ `Enter` drops (guaranteed): `|v| × 0.0167 > thickness` (e.g. 100 u/s ↔ 1-unit wall).
- ⚠ `Enter` may fire: `|v| × 0.0167 ≤ thickness` — necessary but NOT sufficient. On thick walls (2u+) the callback drops at most speeds even below this threshold.

The formula is an **upper bound**, not a predictor. On a 2-unit wall, only one specific speed (30 u/s, where per-step travel equals ball radius 0.5u — frame-aligned with the wall surface) delivered the callback across a sweep of 25/30/35/40/50/70 u/s. Every other speed dropped it despite physics bouncing correctly. The likely mechanism is discrete-step alignment of ball position with wall geometry (sample-at-surface aliasing), not per-step overlap. Thickening the collider does NOT reliably fix the drop.

**Mitigations**:

| Mitigation | Effectiveness | Cost | When to use |
|------------|---------------|------|-------------|
| **Velocity cap** in projectile `onUpdate` (`if (\|v\| > max) v = v.normalize().mul(max)`) | ✅ Reliable | Trivial — ~3 lines. | Default for slingshot/pinball/plinko when designed max launch speed known. |
| Thicker collider (`thickness ≥ \|v_max\| × 0.0167`) | ⚠️ Partial | Design-time — bloats hitbox. | Last resort when velocity cap breaks gameplay. |
| Pre-step raycast (`Physics3D.raycast(pos, dir, \|v\|·dt + r)`) → dispatch your own event | ✅ Expected reliable | High — custom dispatch. | High-speed bullets/arrows needing precise one-shot damage. |

**Velocity-cap example** (keep headroom under 60 u/s for 1-unit targets):

```typescript
private readonly MAX_HIT_VELOCITY = 50;
onUpdate(dt: number): void {
  const v = this.rb.velocity;
  const s2 = v.x*v.x + v.y*v.y + v.z*v.z;
  if (s2 > this.MAX_HIT_VELOCITY * this.MAX_HIT_VELOCITY) {
    const s = this.MAX_HIT_VELOCITY / Math.sqrt(s2);
    this.rb.velocity = new APJS.Vector3f(v.x*s, v.y*s, v.z*s);
  }
}
```

### Enter timing caveats

1. **Enter fires LATE at high impact velocity.** If the first fast contact is dropped (formula above), `Enter` only registers on a subsequent slower contact — 8+ frames after physics actually bounced. Slow-mo-on-hit / dramatic-first-impact games will miss the moment.
2. **Contacts involving `static=true` bodies don't fire Enter** (observed in MVP) — even when `|v|×dt ≪ thickness`. If you need "ball hit stack" to trigger a script, the target must be dynamic (non-static) RigidBody at the moment of contact.

## Physics3D World Settings

Read global 3D physics state from `APJS.Physics3D`. **`gravity`, `gravityFactor` and `timeScale` are effectively read-only at runtime** (assignments after scene load do not take effect — the engine snapshots them at init).

```typescript
// Read-only at runtime — these calls compile and don't throw, but the simulator keeps the
// scene-load snapshot. Do NOT rely on them for runtime gravity changes.
// APJS.Physics3D.gravity = new APJS.Vector3f(0, -9.81, 0);   // ❌ no-op at runtime
// APJS.Physics3D.gravityFactor = 200;                        // ❌ no-op at runtime

// To customize gravity for a body, disable engine gravity and apply your own continuous force:
const rb = obj.getComponent("RigidBody") as APJS.RigidBody;
rb.useGravity = false;
rb.force = new APJS.Vector3f(0, -9.81 * rb.mass, 0);          // continuous, works at runtime

// Read current values (for projectile math etc.)
const g = -APJS.Physics3D.gravity.y;       // positive magnitude
const factor = APJS.Physics3D.gravityFactor;
```

> **Record / Reset semantics**: when recording starts, body positions/velocities, cloth/soft bodies,collision state are reset. ** Properties (like `mass`, `force` and `damping`) are NOT reset**.

> ### Units: positions are CENTIMETERS (AR/cm-scale scenes), gravity ≈ 980
>
> In cm-scale scenes (e.g. AR playables), all world-space values are centimeters — a ball with `Transform.localScale = (1,1,1)` and mesh bounds 22 is a 22 cm object (the size of a real soccer ball). Real-world gravity is 9.81 m/s² = **980 cm/s²**, which matches the APJS default `(0, -980, 0)` (= 9.8 × `gravityFactor` 100). At 1-unit-scale scenes (e.g. slingshot/projectile), `Physics3D.gravity` and `gravityFactor` cannot be overridden at runtime — either reconfigure them in scene settings (design-time), or use the `useGravity = false` + per-body `rb.force` pattern so impulses don't have to absorb the 100× scaling.
>
> **If you are writing projectile math** (parabola, ballistic arc, launch velocity to reach a target), **read `APJS.Physics3D.gravity` at runtime** rather than hardcoding `9.8` — at the cm-scale, using 9.8 underestimates gravity by a factor of 100 and shots will overshoot by ~100x their correct height. (Reading is fine; only writing is a no-op.)
>
> ```typescript
> const g = -APJS.Physics3D.gravity.y;  // positive magnitude, works at any scale
> const vY = (targetY - spawnY) / T + 0.5 * g * T;
> ```

### `timeScale` scales ONLY physics, NOT script dt

`Physics3D.timeScale` scales rigid-body integration and collision response. Script `dt`, UI animations, and event ticks continue at wallclock rate. Verified: mean script `dt` during `timeScale=0.3` slow-mo window (0.029s) is statistically indistinguishable from post-restore (0.032s), and accumulated `dt` during slow-mo matches wallclock span.

Implications:
- A dt-driven countdown `this._t += dt` ticks at real-time speed even with slowed physics.
- To slow everything together, multiply `timeScale` into your own `dt` accumulators.
- Preview `dt` is highly variable (0.002–0.180s observed across scenes). Clamp max `dt` in time-critical logic.

### Slow-Mo on Hit recipe

```typescript
@component()
export class SlowMoOnHit extends APJS.BasicScriptComponent {
  private slowmoElapsed = -1;
  private col!: APJS.SphereCollider;
  private inited = false;

  onUpdate(dt: number): void {
    if (!this.inited) {
      const obj = this.getSceneObject();
      if (!obj) return;
      this.col = obj.getComponent("SphereCollider") as APJS.SphereCollider;
      if (!this.col) return;
      this.col.emitCollisionEvent = true;
      this.inited = true;
      APJS.EventManager.getObjectEmitter(this.col).on(
        APJS.CollisionEvent.Enter,
        () => {
          if (this.slowmoElapsed < 0) {                // don't re-trigger on bounces
            APJS.Physics3D.timeScale = 0.3;
            this.slowmoElapsed = 0;
          }
        },
        this,
      );
    }
    if (this.slowmoElapsed >= 0) {
      this.slowmoElapsed += dt;                        // wallclock
      if (this.slowmoElapsed >= 0.5) {
        APJS.Physics3D.timeScale = 1.0;
        this.slowmoElapsed = -1;
      }
    }
  }
}
```

**Rules**:
1. Gate re-triggering with a sentinel — every bounce fires `Enter` again.
2. Always pair `timeScale = 0.3` with a matching `= 1.0` restore.
3. Remember the high-impact Enter-drop — the dramatic first hit at launch velocity may not trigger slow-mo at all; cap the projectile's speed or use pre-step raycast.

## Raycast3D

```typescript
const origin = new APJS.Vector3f(0, 10, 0);
const direction = new APJS.Vector3f(0, -1, 0);
const ray = new APJS.Ray(origin, direction);
const hits = APJS.Physics3D.raycast(ray, 100, true);      // nearest within 100 units
if (hits.length > 0) {
  console.log("Hit: " + hits[0].colliderObject.name);
  console.log("Point: " + hits[0].point.x + "," + hits[0].point.y + "," + hits[0].point.z);
}
```

**API**: `Physics3D.raycast(ray: Ray, maxDistance: number, nearest: boolean, layerMask?: number): RaycastHit3D[]`

**`APJS.Ray` constructor accepts endpoints, NOT a direction** — `new Ray(start, end)` derives a normalized `direction` getter from the two points. For stepped trajectory raycasts, pass segment start and segment end; no manual subtraction/normalization required. The `maxDistance` arg is still required — pass the Euclidean distance between the two endpoints.

`RaycastHit3D` fields (readonly): `point: Vector3f`, `normal: Vector3f`, `collider: Collider|null`, `colliderObject: SceneObject|null`.

**Performance note**: 10 raycasts/frame against a simple 1-collider scene was invisible in preview `dt` (~33ms both with and without raycast). Scale to denser previews (30+ segments) or complex scenes before concluding it's still cheap.

## Stacked Physics Stability

**There is no per-body auto-sleep API.** Dynamic bodies run full velocity/position integration every step regardless of `|v|` — stacked dynamic bodies drift indefinitely (~0.2–0.5u over 10s on a 2×3 tower), regardless of damping, friction, or PhysicsMaterial tuning.

**Winning pattern — static base + script-layer sleep lifecycle**:

1. **Row-0 blocks start `RigidBody.static = true` in editor** → engine skips integration → zero drift from frame 1.
2. **Per-block `RestSleeper` script** watches own velocity after any wake; when `|v| < 0.15` and `|ω| < 0.3` for 60 frames (~1s), flips `static = true` again.
3. **Controller (e.g. projectile) calls `sleeper.wake()` at action time** to flip `static = false` on every tower block just before the impact arrives. Ball then hits a fully-dynamic tower and physics does its thing.

Rationale: `static=true` is the engine-blessed "not simulating" flag (per `OrionPackages/caps/RigidBody`). The script-layer wake/sleep lifecycle implements the sleep state the engine doesn't expose as a callback.

### RestSleeper script (reusable)

```typescript
@component()
export class RestSleeper extends APJS.BasicScriptComponent {
  @serializeProperty linearThreshold: number = 0.15;
  @serializeProperty angularThreshold: number = 0.3;
  @serializeProperty sleepFrames: number = 60;

  private rb!: APJS.RigidBody;
  private inited = false;
  private lowFrames = 0;
  private asleep = false;

  onUpdate(dt: number): void {
    if (!this.inited) {
      const obj = this.getSceneObject();
      if (!obj) return;
      this.rb = obj.getComponent("RigidBody") as APJS.RigidBody;
      if (!this.rb) return;
      this.inited = true;
      if (this.rb.static) this.asleep = true;               // honor editor-set static
    }
    if (this.asleep) return;
    const v = this.rb.velocity;
    const a = this.rb.angularVelocity;
    const vmag2 = v.x*v.x + v.y*v.y + v.z*v.z;
    const amag2 = a.x*a.x + a.y*a.y + a.z*a.z;
    const lin2 = this.linearThreshold * this.linearThreshold;
    const ang2 = this.angularThreshold * this.angularThreshold;
    if (vmag2 < lin2 && amag2 < ang2) {
      this.lowFrames++;
      if (this.lowFrames >= this.sleepFrames) {
        this.rb.static = true;
        this.asleep = true;
      }
    } else {
      this.lowFrames = 0;
    }
  }

  public wake(): void {
    if (!this.inited || !this.asleep) return;
    this.rb.static = false;
    this.asleep = false;
    this.lowFrames = 0;
  }
}
```

### Why wake at action time, not proximity

Proximity polls (`if (ball.z < unlockZ) wakeAll()`) can fail at high velocity: a ball advancing ~0.84u per frame can jump past the unlock threshold between frames, firing wake too late (ball already rebounded off the static tower). Waking all blocks immediately when firing the projectile sidesteps the timing problem entirely.

### What does NOT work (tested and rejected)

| Approach | Result |
|---|---|
| `damping=0.5, angularDamping=0.8` (old skill recommendation) | Marginal — slight improvement on small 3-row stacks, made wider/taller stacks slightly worse. Never produced zero drift. |
| `damping=1.0` | Numerical instability → NaN positions. |
| 0.1u inter-layer gap to "let blocks settle" | Gives every upper block a frame-0 freefall impact → ~20% higher mean |v|. |
| High-friction PhysicsMaterial (0.95/0.85) on all blocks | Catastrophic — blocks lock in off-axis poses and cascade. Physics solver needs micro-slides to find equilibrium. |
| All-dynamic with `mass=10`+ at low gravity | Stable but destroys mass asymmetry — projectile can't push anything. |
| `freezeX/Y/Z=true` + proximity unlock | Semantically abusing `freeze` (meant for axis locks); ties wake to ball trajectory; dramatic topple was accidental side-effect of penetration-impulse release on unfreeze, not reliable. |
| `APJS.Physics3D.gravity = ...` / `APJS.Physics3D.gravityFactor = ...` at runtime | No-op at runtime — engine snapshots both at scene load. Use the per-body `useGravity = false` + continuous `rb.force` pattern instead, or configure them at design time in scene settings. |

### Knockdown game recipe (slingshot + tower)

- Tower blocks: `static=true` in editor + `RestSleeper` script.
- Projectile (ball): dynamic, `useGravity=false` pre-fire with per-frame re-assert of `position/velocity=0` (survives the record-start RigidBody state reset).
- On fire: call `wakeAll()` iterating tower blocks, then set ball velocity + `useGravity=true`.
- Shared `PhysicsMaterial` on blocks + ground at `bounciness=0.15, dynamicFriction=0.5, staticFriction=0.7` — sweet spot between muted and chaotic. Lower friction (0.5/0.4) causes runaway (blocks reach 280 u/s, never sleep). Higher (0.95/0.85) kills momentum too fast.
- Keep ball launch velocity under F2's `60 × thickness` Enter-drop threshold for any collision callbacks you rely on.

### Geometry > damping

The 18-pyramid top row reaches ~60+ u/s during any topple regardless of damping — it's a geometry problem. Mitigations: widen the top row (each block supported by 2 below), shorten the stack, or use higher `dynamicFriction` material (F1 knob) if chaos is tolerable.

## Knockdown Detection

Four candidate algorithms for "which blocks have been knocked down". Tested against a 3×3 wall with impulses 5–40 u/s:

| Alg | Signal | Latency | Blind spots |
|---|---|---|---|
| **A** | `y < startY - 0.5` | poll (~60 frames) | Row-0 (floor-resting) blocks can't fall below start-y. |
| **B** | `dot(startUp, currentUp) < 0.5` (>60° tilt) | poll (~60 frames) | Fires mid-tumble; no "settled" confirmation. |
| **C** | B **AND** `|v| < 0.1` for 30 consecutive frames | poll (~100 frames) | Late signal; waits ~1s after tumble stops. |
| **D** | `CollisionEvent.Enter` on Ground collider | event (~40 frames) | Double-counts row-0 initial contacts unless filtered (10-frame init window). High-speed Enter-drop (F2). Contacts with static bodies don't fire. |

All four agreed on the count across tested scenarios; differences are **when** they fire and **what they miss**.

**Recommended combined recipe**:
- **Scoring** (authoritative count): Algorithm C — "tilted >60° AND settled for 30 frames". Avoids counting blocks that tumble and re-settle upright.
- **Immediate feedback** (SFX/VFX/combo): Algorithm D — filter initial 10-frame ground contacts, count subsequent Enter events as fresh knockdowns.
- **Don't rely on A alone** — a rigid cluster translating without rotating (real outcome for tight-packed walls) leaves `dy≈0` on every block.

```typescript
// Per frame:
//   countC → authoritative score
// On D callback:
//   play thud SFX + particle, increment "HIT" counter (distinct from score)
// At round end: display countC as final score.
```

`Transform` has **no** `.up/.right/.forward` getters. Derive world-up via quaternion:

```typescript
const up = t.getWorldRotation().multiplyVector(new APJS.Vector3f(0, 1, 0));
```

## Script-driven Position + Collider-only RigidBody

Sometimes the visual arc must be scripted exactly (AR pseudo-physics, cinematic shots) while still using a trigger collider to detect when the projectile reaches a target region. Pattern:

```typescript
// At launch:
rb.useGravity = false;                              // script owns the motion
rb.velocity   = new APJS.Vector3f(0, 0, 0);
rb.position   = startWorldPos;                      // place immediately
obj.setEnabledInHierarchy(true);

// Each frame in onUpdate while flying:
const t  = flightTimer;
const pos = /* compute along your own parabola, spline, camera-local arc, etc. */;
rb.position = pos;                                  // physics collider follows
```

`BoxCollider`/`SphereCollider` trigger events (`CollisionEvent.Enter`) still fire whenever `rb.position` updates cause the collider to overlap with another collider — so `isTangible = false` trigger zones work exactly the same as for physics-driven projectiles. You get custom trajectories + physics collision detection in one go.

**Important**: when evaluating the hit, don't read `Transform.localPosition` — driving `rb.position` every frame can leave the Transform one tick stale. Re-compute the object's position from the same formula you use to drive the flight (store the spawn/velocity parameters on the component instance).

Use this pattern when a projectile should fly through world space on a frozen launch-time camera-local parabola while the trigger collider still fires naturally.

## Scene Setup Pattern (DSL)

Typical 3D physics scene setup:

1. **Camera**: reuse the existing default (`get_scene()`). Keep `clearType = "DEPTH"` for normal preview-background scenes unless the accepted plan explicitly hides the current background with rationale. Use `COLOR_DEPTH` + `clearColor` only for background-hidden experiments.
2. **Ground/colliders**: `add_builtin_object("Plane")`, rotate `localEulerAngles = {x: -90, y: 0, z: 0}` to lie flat, scale up; or use a flat `Cube` scaled thin for a thicker collider surface. Attach `RigidBody` (`static=true`) + `BoxCollider` (`fitMesh=true`). If the surface is visible in the final effect, replace or skin the primitive so it is not a grey placeholder.
3. **Dynamic objects**: `add_builtin_object("Cube"/"Sphere")`, position above ground. **Always follow with explicit `add_component` for RigidBody + collider** — builtin object creation does NOT auto-attach these. If the object is a final visible game piece, source/calibrate a real visual asset or intentionally style the geometry.

**Plane orientation**: Plane mesh faces the camera by default (XY plane). Rotate `eulerAngle.x = -90` to make it horizontal as a floor. For a thick collider surface, use a flat-scaled Cube instead — `Plane`'s BoxCollider `fitMesh` produces zero thickness, which can be tunneled by fast-dropping bodies.

## Rules

1. **MUST** use `ForceMode3D.Impulse` or `VelocityChange` for one-shot forces — default `Force` is continuous and will overpower gravity.
2. **MUST** set `collider.emitCollisionEvent = true` from APJS at runtime (NOT via DSL) before listening for collisions.
3. **MUST** use `getObjectEmitter(collider)` for collision events — NOT `getObjectEmitter(sceneObject)`, NOT `getGlobalEmitter()`.
4. **MUST** use lazy init in `onUpdate()` — `getSceneObject()` returns undefined in `onStart()` for MCP-created scripts.
5. **MUST** clean up listeners in `onDestroy()`.
6. **MUST** explicitly `add_component` RigidBody + collider after `add_builtin_object("Sphere"|"Cube")` — no auto-attach.
7. **MUST** cap projectile velocity at `60 × collider_thickness` (u/s) if collision callbacks matter — higher speeds silently drop `Enter`.
8. **MUST** treat `Quaternionf.identity()` as a method (call with `()`), not a property.
9. **MUST** scale impulses for the ~980 u/s² standard cm-scale gravity, or override `rb.useGravity = false` + `rb.force = (0, -9.81 * rb.mass, 0)` at init for human-scale scenes.
10. For stacked physics, use **`static=true` base + `RestSleeper` on upper rows** — damping/friction/gap tuning does not produce zero drift.
11. `APJS.Physics3D.{gravity, gravityFactor, timeScale}` runtime setter is a no-op (engine snapshots at load); there is NO per-body equivalent on `RigidBody`.
12. Don't branch on read-after-write — `rb.position`/`rb.velocity` read returns the pre-write snapshot for one step.
13. `Physics3D.timeScale` scales ONLY physics — script `dt` continues at wallclock rate. Multiply `timeScale` into your own dt if everything should slow together.
14. `isTangible = false` for trigger zones (detect overlap without blocking).
15. RigidBody `static = true` for immovable floors/walls.
16. Both colliding objects need a Collider; at least one needs a non-static RigidBody for collision events (contacts involving static-only bodies don't deliver Enter).
17. Plane mesh defaults to facing camera — rotate `localEulerAngles.x = -90` for horizontal ground.
