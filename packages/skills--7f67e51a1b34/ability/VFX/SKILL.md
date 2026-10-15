---
name: VFX
description: 视觉特效 - 使用 Tween、VisualEffect、ParticleEmitter2D 和 AnimatedTexture 实现补间动画、原样内置粒子预设、2D 流体和序列帧播放，也涵盖相机震动与得分反馈。新建或定制粒子系统时转到 VFXAuthoring。
---

# VFX — Visual Effects, Tween, Particles

Patterns for reusable visual feedback: tween animations, particle effects, camera shake, and score fly-up.

For particle preset routing and stock-effect boundaries, read
`skills_root/routing/particle-routing.md`. If the request needs
custom meshes, physics, collision, fracture, pile-up, or multi-stage particle
systems, stop using this skill and route to
`skills_root/assets/VFXAuthoring/SKILL.md`.

## Tween Animation

The engine has a built-in Tween system. Add a `Tween` component via DSL, then control it in scripts.

### DSL Setup

1. `add_component(scene_object, type="Tween")` — adds Tween component
2. In script: access via `getComponent("Tween") as APJS.Tween`
3. Default `tweenType` is **TransformPath** — use `TweenTransformPath` API (not `TweenTransform`)

> **CRITICAL**: The Tween component defaults to `TweenType.TransformPath` (not `Transform`). `tweenType` cannot be changed at runtime — the setter updates the enum but `start()` won't work after switching. Always use the `TweenTransformPath` API: `pointsPathVector3`, `durations`, `fixedDuration`.

### TweenTransformPath — Position/Rotation/Scale (default mode)

```typescript
const tween = this.getSceneObject().getComponent("Tween") as APJS.Tween;
const anim = tween.tweenAnimation as APJS.TweenTransformPath;

// Scale bounce: 1 → 1.5 → back to 1
anim.targetType = APJS.TweenTargetType.Scale;
anim.pointsPathVector3 = [
  new APJS.Vector3f(1, 1, 1),   // start
  new APJS.Vector3f(1.5, 1.5, 1.5),  // peak
];
anim.durations = [0.3];           // 0.3s per segment
anim.fixedDuration = true;
anim.pathType = APJS.TweenPathType.Straight;
anim.playMode = APJS.TweenPlayMode.PingPongOnce;  // forward + back, then stop
anim.easingFunction = APJS.TweenEasingFunction.Quadratic;
anim.easingType = APJS.TweenEasingType.Out;
anim.start();  // re-callable — each start() restarts the animation
```

Position tween example:
```typescript
anim.targetType = APJS.TweenTargetType.Position;
anim.pointsPathVector3 = [
  new APJS.Vector3f(0, 0, 0),
  new APJS.Vector3f(5, 3, 0),
];
anim.durations = [1.0];
anim.fixedDuration = true;
anim.pathType = APJS.TweenPathType.Straight;
anim.playMode = APJS.TweenPlayMode.LoopOnce;
anim.easingFunction = APJS.TweenEasingFunction.Quadratic;
anim.easingType = APJS.TweenEasingType.Out;
anim.start();
```

### TweenTargetType

| Target | Animates |
|--------|----------|
| `Position` | localPosition (Vector3f) |
| `Rotation` | localEulerAngles (Vector3f, degrees) |
| `Scale` | localScale (Vector3f) |
| `AlbedoColor` | Material base color (via TweenMaterial) |
| `EmissionColor` | Material emission color (via TweenMaterial) |
| `UV` | Material UV offset (via TweenMaterial) |

### TweenPlayMode

| Mode | Behavior |
|------|----------|
| `Loop` | Repeat forever |
| `LoopOnce` | Play once, stop at end |
| `PingPong` | Bounce back and forth forever |
| `PingPongOnce` | Bounce once (forward + backward) |

### TweenEasingFunction

`Linear`, `Quadratic`, `Cubic`, `Quartic`, `Quintic`, `Sinusoidal`, `Exponential`, `Circular`, `Elastic`, `Back`, `Bounce`

Combined with `TweenEasingType`: `In` (accelerate), `Out` (decelerate), `InOut` (both).

### TweenMaterial — Color/UV Animation

```typescript
const tween = obj.getComponent("Tween") as APJS.Tween;
tween.tweenType = APJS.TweenType.Material;
const anim = tween.tweenAnimation as APJS.TweenMaterial;
anim.targetType = APJS.TweenTargetType.AlbedoColor;
anim.startColor = new APJS.Color(1, 1, 1, 1);
anim.endColor = new APJS.Color(1, 0, 0, 1); // fade to red
anim.duration = 0.5;
anim.playMode = APJS.TweenPlayMode.PingPongOnce;
anim.start();
```

### Script-Based Tween (No Component)

For simple cases without the Tween component, interpolate manually in `onUpdate`:

```typescript
private tweenProgress = 0;
private tweening = false;
private startPos!: APJS.Vector3f;
private endPos!: APJS.Vector3f;
private tweenDuration = 0.5;

startTween(from: APJS.Vector3f, to: APJS.Vector3f): void {
  this.startPos = from;
  this.endPos = to;
  this.tweenProgress = 0;
  this.tweening = true;
}

onUpdate(dt: number): void {
  if (!this.tweening) return;
  this.tweenProgress += dt / this.tweenDuration;
  if (this.tweenProgress >= 1) {
    this.tweenProgress = 1;
    this.tweening = false;
  }
  // Ease-out quadratic
  const t = 1 - (1 - this.tweenProgress) * (1 - this.tweenProgress);
  const transform = this.getSceneObject().getComponent("Transform") as APJS.Transform;
  transform.localPosition = new APJS.Vector3f(
    this.startPos.x + (this.endPos.x - this.startPos.x) * t,
    this.startPos.y + (this.endPos.y - this.startPos.y) * t,
    this.startPos.z + (this.endPos.z - this.startPos.z) * t
  );
}
```

## VisualEffect (GPU Particles)

GPU particle systems using VFX Graph assets. 10 built-in templates available.

### DSL Setup

```
add_builtin_object(object_type="Basic Particles")       — generic billboard particles (sparkle, glow)
add_builtin_object(object_type="Physics Particles")     — 3D sphere particles with physics (debris, balls)
add_builtin_object(object_type="Fire Particles")        — realistic fire effect (built-in textures)
add_builtin_object(object_type="Rain Particles")        — falling rain streaks
add_builtin_object(object_type="Snow Particles")        — falling snowflakes
add_builtin_object(object_type="Explosion Particles")   — explosion burst
add_builtin_object(object_type="Firework Particles")    — firework bursts
add_builtin_object(object_type="Fog Particles")         — fog/smoke haze
add_builtin_object(object_type="Lightning Particles")   — lightning bolts
add_builtin_object(object_type="Turbulence Particles")  — swirling turbulence
```

Position and scale via Transform. The VisualEffect component auto-plays on creation.

### Stock Preset Routing

Stock particles are only appropriate when the user accepts the preset look and
no custom shape, texture, color, density, layer, or motion is required.

- Do not use `Fog Particles` as a finished cinematic smoke treatment by default.
- If the request specifies a particular smoke style, bottom-only placement,
  soft edges, custom texture, color, density, or motion, route to a verified
  transparent image asset or `VFXAuthoring`.
- If another foreground asset already contains fog or haze, do not add a second
  stock fog layer with the same visual role.
- A stock VFX must pass a runtime screenshot review for scale, coverage,
  occlusion, and visual style before it can be accepted.

### Script Playback Control

```typescript
const vfx = this.getSceneObject().getComponent("VisualEffect") as APJS.VisualEffect;

vfx.play();    // Start or resume
vfx.pause();   // Freeze particles in place
vfx.stop();    // Stop emitting + clear all particles
vfx.stop(APJS.VFXStopBehavior.StopEmitting);  // Stop emitting, let existing particles fade
vfx.reset();   // Reset to initial state
vfx.emit();    // Emit a burst of particles

// State queries
if (vfx.isPlaying) { /* ... */ }
if (vfx.isEmitting) { /* ... */ }

// Particle count (enable first)
vfx.enableAliveParticleCount = true;
const counts = vfx.aliveParticleCounts; // number[]
```

### Runtime Parameter Control

Each VFX asset exposes named parameters accessible via `asset.getXxx/setXxx`:

```typescript
const asset = vfx.asset;

// Basic Particles — available parameters:
asset.setFloat("Lifetime", 0.5);                    // Particle lifespan (seconds)
asset.setVector("Min", new APJS.Vector3f(-3, 2, -1)); // Min random velocity
asset.setVector("Max", new APJS.Vector3f(3, 5, 1));   // Max random velocity
asset.setTexture("MainTexture", myTexture);          // Change particle texture (color + shape)

// Physics Particles — available parameters:
asset.setFloat("Radius", 5);        // Collision sphere radius
asset.setFloat("Bounce", 0.8);      // Bounciness (0-1)
asset.setFloat("Friction", 0.3);     // Surface friction (0-1)
asset.setVector("Force", new APJS.Vector3f(0, -10, 0));  // Gravity/force direction
asset.setVector("Position", new APJS.Vector3f(0, 5, 0)); // Collision sphere position

// Check if a parameter exists before using it
if (asset.hasFloatKey("Lifetime")) { /* safe to use */ }
if (asset.hasColorKey("Color_0_0")) { asset.setColor("Color_0_0", new APJS.Color(1, 0, 0, 1)); }
```

### Changing Particle Color/Shape via Texture

Swap `MainTexture` to change particle appearance. Use `stop()` first to clear old particles:

```typescript
// Get texture from a hidden Image object (bound via @serializeProperty)
const img = this.texHolder.getComponent("Image") as APJS.Image;
const asset = vfx.asset;

vfx.stop();  // Clear old particles
asset.setTexture("MainTexture", img.texture);  // Set new texture
vfx.play();  // Restart with new appearance
```

DSL setup for the texture holder:
```
add_builtin_object(object_type="Screen Image", name="TexHolder")
set_scene_object(guid=texHolder, properties={visible: false})              // Hide it
set_component(guid=texHolderImage, properties={texture: {guid: "..."}})  // Assign texture
```

### Event-Triggered VFX Pattern (Explosion on Hit)

```typescript
@serializeProperty explosionVFX!: APJS.SceneObject;

triggerExplosion(): void {
  const vfx = this.explosionVFX.getComponent("VisualEffect") as APJS.VisualEffect;
  vfx.stop();  // Reset
  vfx.asset.setFloat("Lifetime", 0.5);  // Short burst
  vfx.play();
}
```

## ParticleEmitter2D (2D Fluid)

2D fluid simulation for flowing or pooled liquids, fountains, droplets, slime, and oil. Query `ParticleEmitter2D` component knowledge before configuring it; it is not a general-purpose emitter for smoke, sparks, or debris.

### DSL Setup

Use `edit_by_dsl` to create a `2D Scene Object` and add `ParticleEmitter2D`. Use the returned scene-object GUID for `scene_object`, and the returned component GUID for `set_component`. Keep the emitter separate from `RigidBody2D`, which is mutually exclusive on the same object:

```
add_builtin_object(object_type="2D Scene Object", name="流体发射源")
add_component(scene_object=waterSource, type="ParticleEmitter2D")
```

### DSL Property Control

Use the property names returned by `query_knowledge`, without `_target` suffixes. For continuous Line emission, enable `useLifetime` when old particles should disappear:

```
set_component(guid=particleEmitter2D, properties={
  emitterType: "Line",                 // Continuous line emission
  spawnRate: 20,                       // Particles per second
  gravityScale: 3,                     // Gravity strength
  renderScale: 8,                      // Particle size
  initialVelocity: {x: 0, y: 5},        // Initial direction
  tintColor: {r: 1, g: 0.3, b: 0, a: 1}, // Orange particles
  edgeColor: {r: 1, g: 0.5, b: 0, a: 1}, // Orange edges
  useLifetime: true,                   // Enable lifetime
  lifetime: 2,                         // 2 second lifespan
  viscousScale: 0.5,                   // Liquid viscosity
  dampingScale: 0.5,                   // Slow down over time
  enableCollision: true               // Enable particle collision
})
```

### Property Reference

| Property | Type | Default | Range | Description |
|----------|------|---------|-------|-------------|
| `emitterType` | Enum | Line | Line / Polygon | Line: continuous emission; Polygon: pre-filled region |
| `spawnRate` | Number | 5 | 0-999 | Particles per second |
| `gravityScale` | Number | 1 | 0-999 | Gravity multiplier |
| `dampingScale` | Number | 1 | 0-2 | Speed decay |
| `viscousScale` | Number | 0 | 0-2 | Viscosity (0=water, 2=thick) |
| `renderScale` | Number | 5 | 0-99 | Particle size |
| `initialVelocity` | Vector2f | (0,0) | - | Initial velocity direction |
| `length` | Number | 1 | 0-999 | Emission width |
| `originalPoints` | Vec2Vector | — | — | Polygon boundary; configure valid points before verifying a pre-filled region |
| `startEmit` | Boolean | true | - | Auto-start emission |
| `enableCollision` | Boolean | true | - | Particle collision |
| `useLifetime` | Boolean | false | - | Enable particle lifetime |
| `lifetime` | Number | 1 | 0.1-999 | Particle lifespan (seconds) |
| `tintColor` | Color | (0.63,0.9,1,1) | RGBA 0-1 | Particle color |
| `edgeColor` | Color | (1,1,1,1) | RGBA 0-1 | Edge/surface color |

Keep the built-in `unlitMat` and `blitMat` for standard color and edge rendering. Use `skills_root/ability/Physics2D/SKILL.md` when configuring separate 2D colliders or boundaries. Verify flow, pooling, and collisions with a fresh runtime sequence and timed screenshots according to `skills_root/general/PreviewInteraction/SKILL.md`.

### Score Fly-Up Pattern

For "+10" text flying up and fading when scoring:

1. Create a 2D Text object (hidden initially)
2. On score: show text, set position to score location, animate upward + fade out via script tween
3. Hide after animation completes

```typescript
showScoreFlyUp(text: string, startY: number): void {
  this.flyText.setEnabledInHierarchy(true);
  const textComp = this.flyText.getComponent("Text") as APJS.Text;
  textComp.text = text;
  const st = this.flyText.getComponent("ScreenTransform") as APJS.ScreenTransform;
  st.anchoredPosition = new APJS.Vector2f(0, startY);

  // Animate upward over 1 second
  this.flyStartY = startY;
  this.flyProgress = 0;
  this.isFlying = true;
}

// In onUpdate:
if (this.isFlying) {
  this.flyProgress += dt / 1.0; // 1 second duration
  if (this.flyProgress >= 1) {
    this.flyText.setEnabledInHierarchy(false);
    this.isFlying = false;
  } else {
    const st = this.flyText.getComponent("ScreenTransform") as APJS.ScreenTransform;
    st.anchoredPosition = new APJS.Vector2f(0, this.flyStartY + this.flyProgress * 100);
    // Scale down as it flies up
    st.scale = new APJS.Vector2f(1 - this.flyProgress * 0.5, 1 - this.flyProgress * 0.5);
  }
}
```

## Camera Shake

Shake the camera on hit/collision for impact feedback:

```typescript
@component()
export class CameraShake extends APJS.BasicScriptComponent {
  @serializeProperty
  camera!: APJS.SceneObject;

  private shakeTimer = 0;
  private shakeDuration = 0.3;
  private shakeIntensity = 0.5;
  private originalPos!: APJS.Vector3f;
  private camTransform!: APJS.Transform;

  onStart(): void {
    this.camTransform = this.camera.getComponent("Transform") as APJS.Transform;
    this.originalPos = this.camTransform.localPosition.clone();
  }

  shake(intensity = 0.5, duration = 0.3): void {
    this.shakeIntensity = intensity;
    this.shakeDuration = duration;
    this.shakeTimer = duration;
  }

  onUpdate(dt: number): void {
    if (this.shakeTimer <= 0) return;
    this.shakeTimer -= dt;

    if (this.shakeTimer <= 0) {
      // Reset to original position
      this.camTransform.localPosition = this.originalPos.clone();
      return;
    }

    // Random offset that decays over time
    const decay = this.shakeTimer / this.shakeDuration;
    const offsetX = (Math.random() - 0.5) * 2 * this.shakeIntensity * decay;
    const offsetY = (Math.random() - 0.5) * 2 * this.shakeIntensity * decay;
    this.camTransform.localPosition = new APJS.Vector3f(
      this.originalPos.x + offsetX,
      this.originalPos.y + offsetY,
      this.originalPos.z
    );
  }
}
```

## Game Juice Combo — Multiple Effects on One Event

Combine multiple feedback effects into a single `triggerJuice()` call for satisfying game feel:

**5 simultaneous effects:**

| # | Effect | Implementation | Duration |
|---|--------|---------------|----------|
| 1 | Camera shake | Random offset on camera Transform, decays over time | 0.3s |
| 2 | Particle burst | `vfx.stop()` → `setFloat("Lifetime", 0.5)` → `vfx.play()` | 0.5s |
| 3 | Sound effect | `audio.stop()` → `audio.loopCount = 1` → `audio.play()` | instant |
| 4 | Scale bounce | Manual sine ease-out: pop to 1.3x then settle back | 0.3s |
| 5 | Score fly-up | Show 2D Text, animate upward + shrink, hide on complete | 0.8s |

**Key pattern — manual onUpdate tween for scale bounce:**

```typescript
// Simpler and more reliable than Tween component for event-triggered bounces
private bounceTimer = -1;
private bounceDuration = 0.3;
private bounceScale = 1.3; // 1.3x pop

// In triggerJuice():
this.bounceTimer = 0;

// In onUpdate(dt):
private updateBounce(dt: number): void {
  if (this.bounceTimer < 0) return;
  this.bounceTimer += dt;
  const p = this.bounceTimer / this.bounceDuration;
  if (p >= 1) {
    this.targetTransform.localScale = this.baseScale.clone();
    this.bounceTimer = -1;
    return;
  }
  // Cosine ease-out: instant pop up, smooth settle back
  const factor = 1 + (this.bounceScale - 1) * Math.cos(p * Math.PI * 0.5);
  this.targetTransform.localScale = new APJS.Vector3f(
    this.baseScale.x * factor,
    this.baseScale.y * factor,
    this.baseScale.z * factor
  );
}
```

**DSL setup** (no Tween component needed):
```
add_builtin_object(object_type="Basic Particles")     — for burst VFX
add_builtin_object(object_type="Audio Player")        — for SFX
edit_by_dsl(import_resource path="sounds/sfx_pop.mp3")  — import audio file
add_builtin_object(object_type="2D Text") + set_scene_object(visible: false) — for fly-up text
```

**When to use which bounce approach:**
- **Manual onUpdate** (recommended for juice): simple, no component dependency, works with any object scale, re-triggerable without state issues
- **Tween component**: better for continuous/looping animations (idle bob, rotation), but harder to re-trigger cleanly on repeated events

> See `APJS/examples/game_juice_combo.json` for the complete working script.

## Sprite Sheet / Frame-Sequence Animation

For frame-by-frame animation on a 2D Image (confetti overlay, sparkle burst, ribbon cascade, animated icon, etc.), use the built-in **AnimatedTexture** asset. The engine drives playback — no script timer, no `Image.texture` cycling.

### Steps

1. Designer hands you a `<name>.animTex` plus its `<name>.otextureseq` pair (placed under `Assets/Animated Textures/` or anywhere in `Assets/`). The `.animTex` is a `Texture` resource whose provider is `AnimatedTexture`; the `.otextureseq` is the `SourceFile` holding the compressed frame bundle.
2. `list_resources()` → find the row whose provider is `AnimatedTexture` and grab its GUID.
3. `set_component(image_guid, { "texture": { "guid": "<animTex-guid>" } })` — same call you'd make for any Texture2D. The Image starts looping immediately based on the `.animTex`'s embedded `fps`, `loopCount`, `playMode`, and `reverse`.
4. Gate visibility by toggling the host SceneObject via `setEnabledInHierarchy(true/false)` (or by enabling/disabling an ancestor layer). The animation pauses with visibility.

### Tweaking playback at runtime

```ts
// Faster, ping-pong loop, infinite
set_resource_properties(animTexGuid, {
  fps: 20,
  playMode: "PingPong",
  loopCount: -1,
});
```

AnimatedTexture playback is controlled by the resource properties shown above (`fps`, `playMode`, `loopCount`, `reverse`). If you need the exact current values on an existing asset, inspect that AnimatedTexture resource before editing.

### Anti-patterns

- **DO NOT** use `edit_by_dsl.import_resource(...)` on a folder of numbered PNG frames and wire them into a `@serializeProperty Texture[]` to swap on a timer. Folder import yields one independent `Texture2D` per file — it does not produce a sequence. Use AnimatedTexture instead.
- **DO NOT** write `onUpdate` code that cycles `Image.texture = frames[(idx + 1) % len]`. The engine already does this for you once the texture is an AnimatedTexture.
- For manual frame-driven side effects (sound on a specific frame, despawn at the last frame), subscribe to `APJS.AnimatedTextureEvent`. Don't use it just to play the loop.

## Rules

1. Tween component must be added via DSL before accessing in scripts
2. `TweenAnimation.start()` must be called to begin playback — it doesn't auto-play
3. VisualEffect: 10 templates available — Basic Particles, Physics Particles, Fire, Rain, Snow, Explosion, Firework, Fog, Lightning, Turbulence. No need to import VFX assets separately
4. VisualEffect: to change particle color/shape, swap `MainTexture` via script — use `stop()` before `setTexture()` then `play()` so old particles clear first
5. VisualEffect: only parameters exposed by the VFX Graph are accessible via `asset.setFloat/setColor` — use `asset.hasFloatKey(name)` to check before setting
6. ParticleEmitter2D: use component-schema property names in `set_component`, such as `spawnRate` and `tintColor`; do not append `_target`.
7. ParticleEmitter2D: `tintColor` controls particle color, `edgeColor` controls fluid surface edge color.
8. Camera shake should restore original position when done — always save `originalPos` first
9. For script-based tweens, use `onUpdate(dt)` with progress accumulation, not `setInterval`
