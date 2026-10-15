---
name: Movement
description: 运动 — 实现不依赖帧率的脚本运动，适合匀速、插值、振荡、不参与碰撞的跳跃轨迹和伪 3D 运动。需要真实碰撞、重力、弹跳或堆叠时改用 2D物理或3D物理
---

# Movement — Manual Physics & Motion

Patterns for frame-independent movement using `onUpdate(dt)`. These are for non-colliding decorative motion, deterministic tweens, UI/visual feedback, or mechanics the physics engine cannot express cleanly.

If the object needs collision, gravity, bouncing, stacking, knockdown, trigger contact, or other physical behavior, use `Physics2D` / `Physics3D` with RigidBody + Collider instead of manual position updates.

**Pseudo-3D 2D exception**: some portrait sports/arcade games are visually 2D UI sprites but must read like a 3D field, lane, or court. If Rigidbody motion would fight the authored screen-space perspective, use script-driven logical motion plus scene-authored Collider2D hit zones. Keep the bounce/goal math manual, use colliders as editable geometry, and read `Physics2D` "Scene-authored hit zones for pseudo-3D 2D games" before building.

## Gravity + Jump (Parabolic Arc)

```typescript
private velY = 0;
private readonly GRAVITY = 20;     // units/s²
private readonly JUMP_VEL = 15;    // units/s upward
private readonly GROUND_Y = 0;
private isGrounded = true;

onUpdate(dt: number): void {
  if (!this.isGrounded) {
    this.velY -= this.GRAVITY * dt;
    const pos = this.transform.localPosition;
    pos.y += this.velY * dt;

    if (pos.y <= this.GROUND_Y) {
      pos.y = this.GROUND_Y;
      this.velY = 0;
      this.isGrounded = true;
    }
    this.transform.localPosition = pos;
  }
}

private jump(): void {
  if (this.isGrounded) {
    this.velY = this.JUMP_VEL;
    this.isGrounded = false;
  }
}
```

## Power Jump (Variable Strength)

Charge power while holding, launch on release:

```typescript
private power = 0;
private isCharging = false;
private readonly CHARGE_SPEED = 1.0;  // 0→1 in 1 second
private readonly MAX_VEL = 25;

onUpdate(dt: number): void {
  if (this.isCharging) {
    this.power = Math.min(1, this.power + this.CHARGE_SPEED * dt);
  }
  // ... apply gravity as above
}

private startCharge(): void {
  this.isCharging = true;
  this.power = 0;
}

private release(): void {
  this.isCharging = false;
  this.velY = this.power * this.MAX_VEL;
  this.isGrounded = false;
}
```

## Oscillation (Ping-Pong)

Smooth back-and-forth motion for meters, bobbing, pulsing:

```typescript
private _elapsed = 0;
private readonly PERIOD = 1.5;  // seconds per full cycle

onUpdate(dt: number): void {
  this._elapsed += dt;
  // Triangle wave: 0 → 1 → 0 → 1 ...
  const phase = (this._elapsed % this.PERIOD) / this.PERIOD;
  const level = phase < 0.5 ? phase * 2 : 2 - phase * 2;

  // Apply to scale, position, opacity, etc.
  const s = this.transform.localScale;
  s.y = level * this.maxScaleY;
  this.transform.localScale = s;
}
```

## Elapsed Time Tracking

**No `APJS.Time.time` exists.** Accumulate manually:

```typescript
private _elapsed = 0;

onUpdate(dt: number): void {
  this._elapsed += dt;
}
```

## Linear Movement

```typescript
private velocity = new APJS.Vector3f(5, 0, 0);  // 5 units/s rightward

onUpdate(dt: number): void {
  const pos = this.transform.localPosition;
  pos.x += this.velocity.x * dt;
  pos.y += this.velocity.y * dt;
  pos.z += this.velocity.z * dt;
  this.transform.localPosition = pos;
}
```

## 2D Platformer (Physics-Based)

For 2D platformers using RigidBody2D + BoxCollider2D, use Physics2D instead of manual script movement. This gives real collision, friction, and gravity.

**Scene setup (DSL)**:

- Player: Screen Image + RigidBody2D (`useGravity=true`, `mass=1`, `freezeZ=true`) + BoxCollider2D
- Ground/Platforms: Screen Image + RigidBody2D (`static=true`) + BoxCollider2D
- Moving platforms: RigidBody2D (`static=false`, `useGravity=false`, `mass=100`) — see `Physics2D/SKILL.md`

**⚠️ Critical**: `rb.position` is always `(0, 0)` for 2D ScreenTransform objects. Use `screenTransform.localPosition` instead — it gives world-unit coordinates that track physics movement, no PPU conversion needed.

**Jump + raycast ground detection**:

```typescript
// localPosition = world units, tracks physics (inherited from Transform)
const lp = this.st.localPosition;

// Raycast ground check from bottom edge of player
const origin = new APJS.Vector3f(lp.x, lp.y - halfHeight, 0);
const ray = new APJS.Ray(origin, new APJS.Vector3f(0, -1, 0));
const hits = APJS.Physics2D.raycast2D(ray, 0.5, false);
// Filter self-hits, set isGrounded

// Jump on tap (when grounded)
rb.addForce(new APJS.Vector2f(0, 12), APJS.ForceMode2D.Impulse);
```

Jump force reference (mass=1, gravity=9.8): `force=10` → ~3 world units, `force=15` → ~5 units.

See `Physics2D/SKILL.md` for full raycast pattern and `platformer_jump_ground_detect` example.

**World scrolling (camera follow alternative)**: 2D games can't use traditional camera follow. Instead, scroll all platforms/obstacles left while the player stays at fixed X (`freezeX=true`). Platforms use dynamic RigidBody2D + `rb.velocity` for physics-correct scrolling — player rides them via friction. See `Physics2D/SKILL.md` "World Scrolling" section and `world_scroll_platformer` example.

## Rules

1. Always multiply by `dt` for frame-independent motion
2. Read `localPosition` into a variable, modify, then assign back (direct `.x =` doesn't trigger update)
3. No `APJS.Time.time` — use `_elapsed += dt` for timers
4. Preview deltaTime accumulates ~10-15% slower than real time — add buffer for timing-sensitive mechanics
5. For 2D objects: use `screenTransform.localPosition` for world-unit position (physics/raycast), `anchoredPosition` for pixel-unit position (UI layout). Never use `rb.position` (always 0,0)
6. For pseudo-3D 2D games, keep logical motion separate from visual projection (`scale`, `visualY`, guide rotation), and author stable start/goal/hit-zone values in scene components
