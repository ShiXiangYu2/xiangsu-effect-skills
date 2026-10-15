---
name: Animation
description: 动画效果实现方法，包括通过 onUpdate 驱动的逐帧动画、Animator 组件播放，以及旋转、弹跳、缩放、淡入淡出等常见运动模式。
---

# Animation

APJS supports two animation approaches:
1. **Frame-based animation** via `onUpdate(deltaTime)` — for custom/procedural animation
2. **Animator component** — for playing pre-built animation clips

> **Not in scope here**: image-sequence animation (sprite sheets, confetti loops, ribbon overlays, glitter bursts on a 2D `Image`). "Frame-based animation" in this skill means transform/opacity/color tweens driven by `deltaTime`, not `Image.texture` cycling. For frame-by-frame texture playback, use the built-in **AnimatedTexture** asset and assign it to `Image.texture` — the engine handles playback. See the "Sprite Sheet / Frame-Sequence Animation" section of `skills_root/ability/VFX/SKILL.md`. If you find yourself wiring an `APJS.Texture[]` of PNGs to cycle on a timer, you're using the wrong tool.

## Frame-Based Animation (onUpdate)

Use `deltaTime` (in seconds) to create smooth, frame-rate-independent animation.

### Continuous Rotation

```typescript
@component()
export class ContinuousRotation extends APJS.BasicScriptComponent {
  private speed: number = 90; // degrees per second

  onUpdate(deltaTime: number): void {
    const transform = this.getSceneObject().getTransform();
    const euler = transform.localEulerAngles;
    transform.localEulerAngles = new APJS.Vector3f(
      euler.x,
      euler.y + this.speed * deltaTime,
      euler.z
    );
  }
}
```

### Bounce / Oscillation (sine wave)

```typescript
@component()
export class BounceAnimation extends APJS.BasicScriptComponent {
  private elapsed: number = 0;
  private amplitude: number = 0.5;  // units
  private frequency: number = 2;     // cycles per second
  private startY: number = 0;

  onStart(): void {
    this.startY = this.getSceneObject().getTransform().localPosition.y;
  }

  onUpdate(deltaTime: number): void {
    this.elapsed += deltaTime;
    const offset = Math.sin(this.elapsed * this.frequency * Math.PI * 2) * this.amplitude;
    const pos = this.getSceneObject().getTransform().localPosition;
    this.getSceneObject().getTransform().localPosition = new APJS.Vector3f(pos.x, this.startY + offset, pos.z);
  }
}
```

### Scale Pulse

```typescript
@component()
export class ScalePulse extends APJS.BasicScriptComponent {
  private elapsed: number = 0;
  private minScale: number = 0.8;
  private maxScale: number = 1.2;
  private speed: number = 2;

  onUpdate(deltaTime: number): void {
    this.elapsed += deltaTime;
    const t = (Math.sin(this.elapsed * this.speed * Math.PI * 2) + 1) / 2;
    const s = this.minScale + (this.maxScale - this.minScale) * t;
    this.getSceneObject().getTransform().localScale = new APJS.Vector3f(s, s, s);
  }
}
```

### Smooth Movement (Lerp)

```typescript
// Move from current position to target over time
private moveToTarget(transform: APJS.Transform, target: APJS.Vector3f, speed: number, deltaTime: number): void {
  const current = transform.localPosition;
  const t = Math.min(speed * deltaTime, 1);
  transform.localPosition = APJS.Vector3f.lerp(current, target, t);
}
```

### Triangle Wave for Press / Tap Reaction

A button-press animation should scale up and back down in one go. A sine wave overshoots and feels rubbery; a linear up-then-down triangle wave gives a crisp, snappy "punch" — perfect for tap feedback.

```typescript
private readonly PRESS_DURATION: number = 0.25;
private animTimer: number = 0;

private animateButtonReaction(deltaTime: number): void {
  this.animTimer += deltaTime;
  const t = Math.min(this.animTimer / this.PRESS_DURATION, 1);

  // Triangle wave: 0 → 1 → 0 over t ∈ [0, 1]
  const wave = t < 0.5 ? t * 2 : 2 - t * 2;

  const scaleMul = 1.0 + 0.15 * wave;   // up to 115% mid-animation
  const tintVal  = 1.0 - 0.30 * wave;   // dim to 70% mid-animation

  const orig = this.originalScale;
  this.transform.localScale = new APJS.Vector3f(orig.x * scaleMul, orig.y * scaleMul, orig.z);
  this.image.color = new APJS.Color(tintVal, tintVal, tintVal, 1);

  if (t >= 1) {
    // Snap back to clean state — don't trust the wave to land exactly at 0.
    this.transform.localScale = orig.clone();
    this.image.color = new APJS.Color(1, 1, 1, 1);
    this.transitionTo(NEXT_STATE);
  }
}
```

**Why explicit reset on `t >= 1`:** floating-point drift means the wave is rarely *exactly* zero at the end. Without the reset the button stays slightly off-scale / off-tint forever, and small errors compound across consecutive presses.

### Original-Value Snapshot Before Reactive Animations

Reactive animations (press, hover, shake) need to know the resting value to lerp away from and back to. Snapshot it **once** in init using `.clone()` — never read "current" position/scale/color mid-animation, because it already includes the animation's own offset.

```typescript
private originalScales: APJS.Vector3f[];

private initializeUI(): void {
  this.originalScales = this.buttons.map(obj => obj.getTransform().localScale.clone());
  // ^ .clone() is essential — Vector3f references are shared, so without
  //   the clone, mutating localScale later would also mutate originalScales.
}

// On reset (e.g., RecordEnd cleanup):
for (let i = 0; i < this.buttons.length; i++) {
  this.buttons[i].getTransform().localScale = this.originalScales[i].clone();
  // ^ Clone again on assignment so future animations don't write back into
  //   the snapshot.
}
```

**Pitfall:** assigning `originalScale = transform.localScale` (no clone) stores a *reference*. The next frame's localScale write mutates the snapshot in place, so the "original" value tracks the animation. Always `.clone()` on capture **and** when assigning the snapshot back.

### Two-Phase Fade Swap (Replace Content During Transparency)

To replace a Text or Image's content (e.g., question → feedback, level title → next-level title) without an ugly mid-string flicker: fade the renderer to opacity 0, swap the content while it's invisible, fade back to 1.

```typescript
private readonly FADE_DURATION: number = 0.35;

// Phase 1 — fade out the current content.
private animateFadeOut(deltaTime: number): void {
  this.animTimer += deltaTime;
  const t = Math.min(this.animTimer / this.FADE_DURATION, 1);
  this.text.opacity = 1 - t;

  if (t >= 1) {
    // Swap content while fully transparent — viewer sees nothing change here.
    this.text.text = this.nextString;
    this.text.color = this.nextColor;
    this.transitionTo(STATE_FADE_IN);
  }
}

// Phase 2 — fade the new content in.
private animateFadeIn(deltaTime: number): void {
  this.animTimer += deltaTime;
  const t = Math.min(this.animTimer / this.FADE_DURATION, 1);
  this.text.opacity = t;
  if (t >= 1) this.transitionTo(STATE_HOLD);
}
```

**Key insight:** the swap happens *exactly* when `opacity === 0`, which is also the moment the renderer's color/text values are not visible. This makes the swap atomic from the viewer's perspective — they see only "old fades out, new fades in", never a one-frame flash of the new content over the old style.

**Use this for:**
- Question → answer / feedback text replacement.
- Level title cards between rounds.
- Score display when the value jumps by a large amount and a counter would feel slow.
- Any UI swap where the old and new content share the same renderer.

## Animator Component Playback

For pre-built animation clips attached to an Animator component.

### Basic Usage

```typescript
const animator = obj.getComponent("Animator") as APJS.Animator;
animator.play("walk", APJS.AnimationWrapMode.Repeat, 1.0);
```

### AnimationWrapMode

| Mode | Value | Description |
|------|-------|-------------|
| `Once` | 1 | Play once and stop |
| `Repeat` | 0 | Loop continuously |
| `PingPong` | -1 | Play forward then backward |
| `ClampForever` | -2 | Play once, hold last frame |

### Accessing Animation Clips

```typescript
// Get all clips as an array
const animations: APJS.Animation[] = animator.animations;
// Each clip has: .name (string), .duration (number in seconds)

// Find clip by name
const walkClip = animations.find(a => a.name.includes("walk"));
```

### Checking Current Playback State

```typescript
// animator.playback gives the currently playing clip
if (animator.playback && animator.playback.name !== targetClip.name) {
  animator.play(targetClip.name, APJS.AnimationWrapMode.Repeat, 1);
}
```

### One-Shot Animations with Auto-Return

Play an animation once, then return to idle after its duration:

```typescript
private idleReturnTimer: number = 0;

private playOnce(animator: APJS.Animator, clipName: string): void {
  const clip = animator.animations.find(a => a.name.includes(clipName));
  if (!clip) return;
  animator.play(clip.name, APJS.AnimationWrapMode.Once, 1);
  this.idleReturnTimer = clip.duration; // set timer to auto-return
}

onUpdate(deltaTime: number): void {
  if (this.idleReturnTimer > 0) {
    this.idleReturnTimer -= deltaTime;
    if (this.idleReturnTimer <= 0) {
      this.idleReturnTimer = 0;
      animator.play("idle", APJS.AnimationWrapMode.Repeat, 1);
    }
  }
}
```

### CrossFade (Blend Transitions)

The `play()` method's 4th parameter `fadeInTime` controls blend transition duration:

```typescript
// Smooth transition from current animation to "run" over 0.3 seconds
animator.play("run", APJS.AnimationWrapMode.Repeat, 1, 0.3);
// Instant switch (no blend)
animator.play("idle", APJS.AnimationWrapMode.Repeat, 1, 0);
```

### Playback Control

```typescript
animator.stopAll();    // Stop all animations
animator.pauseAll();   // Pause all animations
animator.resumeAll();  // Resume paused animations
```

### Animation Events

```typescript
const emitter = animator.getEmitter("walk");
if (emitter) {
  emitter.on(APJS.AnimationEventType.AnimationEnd, (event: APJS.IEvent) => {
    // Animation finished — switch to next state
  }, this);
}
```

> `AnimationEventType.AnimationEnd` = 1002. `getEmitter()` returns null if the animation name doesn't exist.

### Common Patterns

- **Looping animations** (idle, walk, run): use `WrapMode.Repeat`
- **One-shot animations** (wave, dance, attack): use `WrapMode.Once` + duration timer to return to idle
- **Check before play**: always compare `playback.name` to avoid restarting the same animation
- **Animator object ref**: the Animator component is often on a child object (e.g., skeleton root), not the top-level object — use `@serializeProperty` to bind it

## Path Animation — Constant-Speed Flight Along Waypoints

When animating an object along a series of 3D waypoints (e.g., a ball following a drawn path), raw waypoints often produce **stuttering or speed spikes** because the distances between consecutive points are uneven. A 3-step pipeline fixes this:

### Step 1: Catmull-Rom Spline Smoothing

Eliminates sharp corners from noisy input (e.g., raw touch points) by generating a smooth curve through the control points:

```typescript
private catmullRom(
  p0: APJS.Vector3f, p1: APJS.Vector3f,
  p2: APJS.Vector3f, p3: APJS.Vector3f, t: number
): APJS.Vector3f {
  const t2 = t * t;
  const t3 = t2 * t;
  return new APJS.Vector3f(
    0.5*((2*p1.x)+(-p0.x+p2.x)*t+(2*p0.x-5*p1.x+4*p2.x-p3.x)*t2+(-p0.x+3*p1.x-3*p2.x+p3.x)*t3),
    0.5*((2*p1.y)+(-p0.y+p2.y)*t+(2*p0.y-5*p1.y+4*p2.y-p3.y)*t2+(-p0.y+3*p1.y-3*p2.y+p3.y)*t3),
    0.5*((2*p1.z)+(-p0.z+p2.z)*t+(2*p0.z-5*p1.z+4*p2.z-p3.z)*t2+(-p0.z+3*p1.z-3*p2.z+p3.z)*t3)
  );
}

private smoothPath(pts: APJS.Vector3f[], density: number): APJS.Vector3f[] {
  if (pts.length < 3) return pts;
  const out: APJS.Vector3f[] = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    for (let j = 0; j < density; j++) {
      out.push(this.catmullRom(p0, p1, p2, p3, j / density));
    }
  }
  out.push(pts[pts.length - 1]);
  return out;
}
```

### Step 2: Arc-Length Resampling

Redistributes waypoints so each pair is the same 3D distance apart. This is the **key to constant speed** — uniform time progression through equally-spaced waypoints produces uniform velocity:

```typescript
private resampleByArcLength(pts: APJS.Vector3f[], n: number): APJS.Vector3f[] {
  if (pts.length < 2 || n < 2) return pts;
  // Compute cumulative arc lengths
  const cumLen: number[] = [0];
  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i].x - pts[i-1].x;
    const dy = pts[i].y - pts[i-1].y;
    const dz = pts[i].z - pts[i-1].z;
    cumLen.push(cumLen[i-1] + Math.sqrt(dx*dx + dy*dy + dz*dz));
  }
  const totalLen = cumLen[pts.length - 1];
  if (totalLen < 0.01) return pts;
  // Place n points at equal distance intervals
  const out: APJS.Vector3f[] = [];
  let seg = 0;
  for (let i = 0; i < n; i++) {
    const target = (i / (n - 1)) * totalLen;
    while (seg < pts.length - 2 && cumLen[seg + 1] < target) seg++;
    const segLen = cumLen[seg + 1] - cumLen[seg];
    const t = segLen > 0.001 ? (target - cumLen[seg]) / segLen : 0;
    const a = pts[seg], b = pts[seg + 1];
    out.push(new APJS.Vector3f(
      a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t
    ));
  }
  return out;
}
```

### Step 3: Use Ease-Out (Not Smoothstep) for Flight Feel

With arc-length-parameterized waypoints, use a simple ease-out for a natural deceleration into the target. Avoid smoothstep `t²(3-2t)` which creates an S-curve that amplifies any remaining speed variation:

```typescript
// In onUpdate:
const raw = Math.min(elapsed / duration, 1.0);
const t = 1 - (1 - raw) * (1 - raw);  // ease-out quadratic
const fi = t * (path.length - 1);
// ... interpolate between path[floor(fi)] and path[ceil(fi)]
```

### Full Pipeline Usage

```typescript
// In enterFlying:
const cleaned = this.resample(rawPoints, 15);      // reduce noise
const smoothed = this.smoothPath(cleaned, 4);       // smooth corners
this.path = this.resampleByArcLength(smoothed, 40); // constant speed
```

## Gravity Landing on Sloped Terrain

When an object falls via gravity onto a non-flat surface (e.g., a tilted soccer field), compute the ground height dynamically based on the object's position:

```typescript
private fallSpeed: number = 0;

private applyGravity(dt: number): void {
  const p = this.transform.localPosition;

  // Ground height varies with Z (field slopes from ball area to goal)
  const fieldFrac = Math.max(0, Math.min(1, (29 - p.z) / 29));
  const groundY = -6.5 + 9 * fieldFrac - 0.5;

  if (p.y > groundY) {
    this.fallSpeed += 10 * dt;
    this.transform.localPosition = new APJS.Vector3f(
      p.x, Math.max(groundY, p.y - this.fallSpeed * dt), p.z);
  }
  // else: on the ground — stop falling
}
```

**Key points:**
- `Math.max(groundY, ...)` prevents the object from penetrating the ground
- `fieldFrac` linearly interpolates the slope — replace the formula with your scene's actual terrain geometry
- Reset `fallSpeed = 0` when starting a new round

## Rules

1. Always use `deltaTime` for frame-rate-independent animation
2. Store initial values (position, scale) in `onStart()` for reference
3. For 3D objects, use `Transform` (localPosition, localEulerAngles, localScale)
4. For 2D objects, use `ScreenTransform` (refer to ScreenTransform SKILL)
5. Use `Vector3f.lerp()` / `Quaternionf.slerp()` for smooth interpolation
6. **Orbit plane**: Default camera is at (0,0,40) looking along -Z. For orbital animations visible from this camera, orbit in the **XY plane** (`x = cos(angle) * radius, y = sin(angle) * radius, z = 0`). XZ plane orbits appear as a horizontal line from this viewing angle.
7. **Path animation**: When moving an object along waypoints from touch input, always use arc-length resampling for constant speed. Raw touch points and index-based resampling produce uneven segment lengths that cause visible stuttering.
8. **Gravity landing**: When dropping objects onto terrain, compute ground height from position — don't use a fixed Y floor. Clamp with `Math.max(groundY, newY)` to prevent penetration.

## Gotchas

### Animating `Color` and `Vector2f` properties from a script — use the setter, not in-place mutation

When you animate `ScreenTransform.scale` (a `Vector2f`), `Image.color` / `Text.color` (a `Color`), or any other "object-typed" property at runtime, the getter returns a **fresh copy** of the underlying value, not a live reference. Two failure modes that both look "right" but don't work:

```typescript
// ❌ Throws `t.getNative is not a function` every frame — engine wraps the value and
//    looks for a missing native handle on a plain object literal.
cst.scale = { x: 1 - t * 0.95, y: 1 };

// ❌ Silent no-op — the getter returns a copy; mutating its fields never propagates
//    back to the engine, and the component keeps rendering at the previous value.
cst.scale.x = 1 - t * 0.95;
im.color.a = 0;
```

Both fail silently in different ways: literal-object assignment trashes the frame budget with exceptions; in-place mutation runs cleanly but the visual never updates. The shape that actually propagates is **construct a real APJS instance and assign through the setter**:

```typescript
// ✅ Squash-and-stretch on a 2D card during a flip animation
cst.scale = new APJS.Vector2f(1 - t * 0.95, 1);

// ✅ Fade-out on a 2D image (or text) — preserve the existing rgb, only change alpha
const oc = im.color;
im.color = new APJS.Color(oc.r, oc.g, oc.b, 0);

const olc = lab.color;
lab.color = new APJS.Color(olc.r, olc.g, olc.b, 0);
```

Primitive-typed properties (`number`, `string`, `boolean`) are unaffected — `st.rotation += spinSpeed * dt`, `txt.text = "..."`, and `component.enabled = false` all work directly. SceneObject visibility is the exception: use `obj.setEnabledInHierarchy(false)` so hierarchy propagation and lifecycle notification paths run. The class-instance allocation is only required for `Color`, `Vector2f`, `Vector3f`, `Quaternionf`, etc.

Verified W11 (randomizer/prediction, 2026-04-30) — reproduced both failure modes and the fix on `card_flip_reveal.json`'s `CardFlipReveal` script across three iterations.
