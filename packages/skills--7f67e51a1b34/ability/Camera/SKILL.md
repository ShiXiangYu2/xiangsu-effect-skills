---
name: Camera
description: 处理相机朝向、视锥与可见范围、世界/屏幕/视口坐标转换、触屏检测和相机画面捕获。
---

# Camera

## Camera Orientation & Euler Convention

The default camera is at position **(0, 0, 40)** with euler **(0, 0, 0)**, looking toward the origin along **-Z**.

| Euler axis | Positive value | Negative value |
|------------|---------------|----------------|
| **X (pitch)** | Look **UP** (toward sky / +Y) | Look **DOWN** (toward ground / -Y) |
| **Y (yaw)** | Turn **left** (CCW from above) | Turn **right** (CW from above) |
| **Z (roll)** | Tilt counter-clockwise | Tilt clockwise |

> **WARNING — pitch is opposite of Unity**: In Unity positive X pitch looks **down**; in this runtime positive X pitch looks **UP**.

### Camera Background for 3D Scenes

Only two `clearType` values should be used: `DEPTH` (default — keeps live phone camera feed) or `COLOR_DEPTH` (solid color background for explicitly camera-hidden experiments). **Never use `COLOR` alone — depth must always be cleared.**

For scenes that should keep the live camera feed, keep `DEPTH`. For deliberately camera-hidden experiments, set `COLOR_DEPTH` and `clearColor`:

```json
"properties": {
  "clearType": "COLOR_DEPTH",
  "clearColor": {"r": 0.6, "g": 0.8, "b": 0.95, "a": 1}
}
```

### Isometric View Recipe

Camera above the scene looking down at the origin from the (+X, +Y, +Z) quadrant:

```
Position: (15, 25, 15)
Euler:    (-50, 45, 0)   // pitch DOWN 50°, yaw LEFT 45°
```

## Camera Frustum & Visibility

### Perspective Projection Formula

For a **perspective** camera, the visible area at distance `D` from the camera along its forward axis:

```
visible_height = 2 * D * tan(FOV / 2)
visible_width  = visible_height * aspect_ratio
```

This formula is **scale-invariant** — it works regardless of scene scale. If you double all object sizes and distances, the framing stays the same.

**Example**: Camera at height 30 looking down, FOV=60°, 9:16 aspect:
- Distance to ground along forward ≈ 30 / cos(tilt_angle)
- visible_height = 2 × D × tan(30°) ≈ 1.15 × D

### Orthographic Projection

For an **orthographic** camera, visible area is constant regardless of distance:

```
visible_height = orthoHeight * 2
visible_width  = visible_height * aspect_ratio
```

### Sizing Camera Offsets for Follow-Cameras

When writing scripts with camera-follow logic (e.g., camera tracks player with a fixed offset), calculate the offset from the scene layout:

1. Determine the required visible span: how many objects / how much distance the player needs to see ahead
2. Apply the projection formula to derive the required camera distance
3. Use the isometric recipe euler angles (-50, 45, 0) and scale the position offset proportionally

Use `screenshot()` to verify camera framing visually. The screenshot shows the actual preview output — always trust the image over computed estimates.

### Dual-Instance Note

There are two instances: **Editor** (static scene state, modified by DSL tools) and **Preview** (runtime scripts). `get_scene` returns editor-state positions. If a script modifies the camera at runtime (e.g., camera-follow in onUpdate), the actual preview view may differ.

**Best practice**: verify camera framing during Phase 4 scene build, before adding scripts. If the camera will be script-controlled, ensure the script's offset values are derived from the projection formula — don't guess.

## Camera Output Capture

Use `APJS.CaptureFrameHelper.captureCameraOutput(camera, cropRect, resolutionRatio)` to copy a Camera's current `renderTexture` into a Texture. The Camera must have a `renderTexture`; the returned Texture is available immediately, while its pixels are filled after the Camera's next `AFTER_RENDER` event.

`cropRect` uses normalized texture coordinates, so it can capture the full frame or a selected region. Bind the returned Texture to an Image or Material. Keeping captures across updates provides the basis for temporal effects, while combining captures from different regions provides the basis for region-based camera effects. Keep any capture history bounded because each call creates a destination Texture.

**Performance warning**: Do not call `captureCameraOutput` every frame from `onUpdate`. Every call allocates a new destination Texture, and the API does not accept an existing Texture for reuse. Capture once and reuse the returned Texture when possible. For temporal or region effects, trigger captures at a controlled interval, keep a strict fixed upper bound on retained textures, and replace old entries instead of growing capture history indefinitely.

## Coordinate Conversion

Camera is used for converting between world, viewport, and screen coordinate spaces. This is essential for touch-based hit detection and positioning objects relative to the screen.

## Getting a Camera Reference

Always get the Camera through a `@serializeProperty` SceneObject reference:

```typescript
@serializeProperty
private cameraObject: APJS.SceneObject;

private camera: APJS.Camera;

onStart(): void {
  this.camera = this.cameraObject.getComponent("Camera") as APJS.Camera;
}
```

## Coordinate Spaces

| Space | Range | Description |
|-------|-------|-------------|
| **World** | Unbounded | 3D world coordinates |
| **Viewport** | (0,0)-(1,1) | Normalized screen space, bottom-left origin |
| **Screen** | Pixel coordinates | Device pixel coordinates |

## Key Methods

### worldToViewportPoint(worldPos: Vector3f): Vector3f
Converts world position to viewport coordinates (0-1 range). Returns Vector3f where x,y are viewport coords.

### worldToScreenPoint(worldPos: Vector3f): Vector2f
Converts world position to screen pixel coordinates.

### screenToWorldPoint(screenPos: Vector2f): Vector3f
Converts screen pixel coordinates to world position.

### viewportPointToRay(viewportPos: Vector2f): Ray
Returns a `Ray { origin, direction }` from the camera position through the viewport point. Useful for hit-testing arbitrary 3D geometry where you don't have a known list of `worldToViewportPoint`-projectable centers (e.g., placing a ball on a clicked spot of a ground plane, hit-testing a 3x3 sliding-puzzle grid by ray-casting against a flat plane).

> **Same Y-flip rule applies**: pass `(touch.x, 1 - touch.y)`, not `touch` directly. See the next section.

## Touch Hit Detection Pattern

The most common use case: detecting which object was tapped by comparing touch position (viewport space) with object positions.

**IMPORTANT**: Touch Y coordinate must be inverted: `1 - touchInfo.position.y`

```typescript
@serializeProperty
private cameraObject: APJS.SceneObject;

@serializeProperty
private targetObjects: APJS.SceneObject[] = [];

private camera: APJS.Camera;
private objectHalfSize: APJS.Vector2f = new APJS.Vector2f(0.1, 0.1);

onStart(): void {
  this.camera = this.cameraObject.getComponent("Camera") as APJS.Camera;
}

private getClickedObjectIndex(touchPosition: APJS.Vector2f): number {
  for (let i = 0; i < this.targetObjects.length; i++) {
    const obj = this.targetObjects[i];
    if (!obj.isEnabledInHierarchy()) continue;

    const worldPos = obj.getTransform().getWorldPosition();
    const viewportPos = this.camera.worldToViewportPoint(worldPos);

    if (
      touchPosition.x >= viewportPos.x - this.objectHalfSize.x &&
      touchPosition.x <= viewportPos.x + this.objectHalfSize.x &&
      touchPosition.y >= viewportPos.y - this.objectHalfSize.y &&
      touchPosition.y <= viewportPos.y + this.objectHalfSize.y
    ) {
      return i;
    }
  }
  return -1;
}

private onTouch = (event: APJS.IEvent) => {
  const touchInfo = event.args[0] as APJS.TouchData;
  if (touchInfo.phase === APJS.TouchPhase.Began) {
    // IMPORTANT: Invert Y coordinate
    const touchPos = new APJS.Vector2f(touchInfo.position.x, 1 - touchInfo.position.y);
    const index = this.getClickedObjectIndex(touchPos);
    if (index !== -1) {
      // Handle tap on object at index
    }
  }
};
```

## 3D Hit Detection via Ray-Cast

When tiles, cards, or other 3D objects sit on a flat plane (e.g., a 3x3 sliding-puzzle grid at `z=0`, or any other "play surface" you don't want to hand a list of object world-centers to), use **`viewportPointToRay` + plane intersection**. The pattern is:

1. Convert touch coords (top-origin) → viewport coords (bottom-origin) by flipping Y. **Same rule as the 2D pattern above.**
2. Cast a ray from the camera through that viewport point.
3. Intersect that ray with the play-surface plane (e.g., `z=0`) to get the world hit point.
4. Convert world → object-parent-local if your objects are children of a transformed parent (scale / offset).
5. Find which object the hit point lies inside (distance test, grid index lookup, or AABB).

```typescript
@serializeProperty private cameraObject!: APJS.SceneObject;
@serializeProperty private gridObjects: APJS.SceneObject[] = [];

private camera!: APJS.Camera;
// Grid parent has localScale 0.5 and localPosition.y -10.7 → object-local coords
private static readonly PARENT_SCALE = 0.5;
private static readonly PARENT_OFFSET_Y = -10.7;
private static readonly LOCAL_POS = [
  { x: -8, y: 0 }, { x: 0, y: 0 }, { x: 8, y: 0 },
  { x: -8, y: 8 }, { x: 0, y: 8 }, { x: 8, y: 8 },
  // …
];

onStart(): void {
  this.camera = this.cameraObject.getComponent("Camera") as APJS.Camera;
}

private onTouch = (event: APJS.IEvent) => {
  const t = event.args[0] as APJS.TouchData;
  if (t.phase !== APJS.TouchPhase.Began) return;

  // 1. Flip Y — TouchData.position is top-origin; viewportPointToRay is bottom-origin.
  //    Forgetting this step makes every tap land at the wrong world-Y mirror image.
  const viewportPos = new APJS.Vector2f(t.position.x, 1 - t.position.y);

  // 2. Ray from camera through that viewport point.
  const ray = this.camera.viewportPointToRay(viewportPos);
  const o = ray.origin;
  const d = ray.direction;

  // 3. Intersect with the play-surface plane (z = 0 here).
  if (Math.abs(d.z) < 1e-6) return;   // ray parallel to plane — no hit
  const tt = -o.z / d.z;
  const worldX = o.x + d.x * tt;
  const worldY = o.y + d.y * tt;

  // 4. World → grid-parent-local (account for parent scale + offset).
  const localX = worldX / GridGame.PARENT_SCALE;
  const localY = (worldY - GridGame.PARENT_OFFSET_Y) / GridGame.PARENT_SCALE;

  // 5. Closest tile.
  let bestIdx = -1;
  let bestDist = 1e9;
  for (let i = 0; i < GridGame.LOCAL_POS.length; i++) {
    const lp = GridGame.LOCAL_POS[i];
    const dist = Math.hypot(lp.x - localX, lp.y - localY);
    if (dist < bestDist) { bestDist = dist; bestIdx = i; }
  }
  // Reject if the tap clearly missed every tile (tiles are 8 local-units apart; half that is a generous threshold).
  if (bestDist > 5) return;

  // Apply game logic to bestIdx.
};
```

### When to choose ray-cast vs. project-and-AABB

| Pattern | Best for |
|---|---|
| **`worldToViewportPoint` + AABB** (2D Touch Hit Detection Pattern above) | A handful of distinct objects with known world centers — buttons, score popups, randomly-positioned spawn targets. You already iterate the list to render them; you may as well iterate it to hit-test. |
| **`viewportPointToRay` + plane intersection** (this section) | A grid or play-surface where you'd rather convert the tap to a world coordinate once and then look up which cell it landed in. Cleaner when the "cells" share a parent transform and you want to invert that transform once. |

### Alternative: Physics3D collider raycast

If your 3D objects already have `BoxCollider3D` / `SphereCollider3D` attached, use `APJS.Physics3D.raycast(origin, direction, maxDistance)` with the same ray from `viewportPointToRay`. That returns the actual collider that was hit — most useful when objects are irregularly placed, when they overlap in Z, or when colliders already exist for other reasons (physics, drag-and-drop). See `Physics3D/SKILL.md`.

> **The Y-flip rule is universal**: ANY time a `TouchData.position` (or any top-origin screen coord) goes into a `Camera.*` method that expects viewport coords — `worldToViewportPoint`-comparison, `viewportPointToRay`, `screenToWorldPoint` — flip Y first. The 2D-only convention in `TouchUtils.isScreenPointOnImage` is the exception, not the rule, because it does the flip internally.

## Perspective Depth Lookup Table (viewport Y → world Z)

When converting 2D screen positions to 3D world positions along a tilted trajectory (e.g., a ball flying from the bottom of the screen toward a goal at the top), **do NOT use a linear viewport-to-depth mapping**. In perspective projection, the relationship between viewport Y and world Z is non-linear — a small viewport Y change near the top of the screen corresponds to a much larger Z change than the same change near the bottom.

**Symptom**: Objects near the far end of the trajectory (e.g., coins near the goal) are unreachable because the ball overshoots past them.

**Fix**: Precompute a lookup table (LUT) by sampling points along the trajectory and recording their viewport Y positions. Then reverse-lookup from viewport Y to get the correct Z.

```typescript
// ---- Build the LUT in onStart/init ----
private readonly LUT_SIZE: number = 20;
private lutVYs: number[] = [];
private lutZs: number[] = [];
private lutDepths: number[] = [];

private buildLUT(): void {
  const cam = this.cameraObject.getComponent("Camera") as APJS.Camera;
  const startZ = 29;   // near position (e.g., ball)
  const endZ = -5;     // far position (past the goal)
  const startY = -6.5; // height at start
  const endY = 5;      // height at end
  const camZ = 50;     // camera Z position

  for (let i = 0; i <= this.LUT_SIZE; i++) {
    const frac = i / this.LUT_SIZE;
    const z = startZ + (endZ - startZ) * frac;
    const h = startY + (endY - startY) * frac;
    const vp = cam.worldToViewportPoint(new APJS.Vector3f(0, h, z));
    this.lutVYs.push(vp.y);
    this.lutZs.push(z);
    this.lutDepths.push(camZ - z);
  }
}

// ---- Use the LUT to convert viewport Y → world Z ----
private viewportYToWorldZ(vy: number): { z: number, depth: number } {
  // Clamp to LUT range
  if (vy <= this.lutVYs[0]) return { z: this.lutZs[0], depth: this.lutDepths[0] };
  if (vy >= this.lutVYs[this.LUT_SIZE]) return { z: this.lutZs[this.LUT_SIZE], depth: this.lutDepths[this.LUT_SIZE] };

  // Binary-style search (linear for small LUT)
  for (let i = 0; i < this.LUT_SIZE; i++) {
    if (vy >= this.lutVYs[i] && vy <= this.lutVYs[i + 1]) {
      const t = (vy - this.lutVYs[i]) / (this.lutVYs[i + 1] - this.lutVYs[i]);
      return {
        z: this.lutZs[i] + (this.lutZs[i + 1] - this.lutZs[i]) * t,
        depth: this.lutDepths[i] + (this.lutDepths[i + 1] - this.lutDepths[i]) * t
      };
    }
  }
  return { z: this.lutZs[this.LUT_SIZE], depth: this.lutDepths[this.LUT_SIZE] };
}
```

**When to use**: Any game mechanic that maps 2D screen input (touch, drag) to 3D world positions along a trajectory that isn't perpendicular to the camera. For example: drawing a flight path, placing objects along a tilted field, or projecting touch points onto a non-flat surface.

## Rules

1. **MUST** invert touch Y: use `1 - touchInfo.position.y` for **any** Camera method that takes viewport coords (`worldToViewportPoint` comparison, `viewportPointToRay`, `screenToWorldPoint`). `TouchData.position` is top-origin (y=0 top); all Camera viewport APIs are bottom-origin (y=0 bottom). The exception is `TouchUtils.isScreenPointOnImage`, which does the flip internally.
2. Get Camera reference via `@serializeProperty` SceneObject, not by name lookup
3. `worldToViewportPoint` returns (0,0) at bottom-left, (1,1) at top-right
4. For AABB hit detection on a handful of distinct objects, use the `worldToViewportPoint` pattern. For grids / play-surfaces, use the `viewportPointToRay` + plane-intersection pattern.
5. For 3D objects with existing colliders, prefer `Physics3D.raycast` over manual ray-plane math.
6. **NEVER** use linear interpolation for viewport Y → depth mapping on tilted trajectories — use a precomputed LUT (see above)
