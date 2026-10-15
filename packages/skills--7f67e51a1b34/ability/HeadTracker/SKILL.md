---
name: HeadTracker Guide
description: 制作跟随人脸的 3D 挂件、头部动作控制玩法和动态文字，解释 Head Tracker 的节点层级、尺寸、人脸姿态数据的方向约定
---

## What Head Tracker Creates

`add_builtin_object(object_type="Head Tracker")` creates a two-level hierarchy:

1. **Face Binding** (parent) — has `Face Binding` component, anchored to FaceCenter
2. **Head** (child) — has `Mesh Renderer` with a head occluder mesh that hides geometry behind the head

The Head child is the anchor point for all face decorations.

## Head Object Bounds

The Head object mesh is approximately **18 x 29 x 21 world units** (width x height x depth). Use these dimensions as reference when sizing child objects.

## AR Face Decoration Pattern

To attach 3D objects to the face, parent them to the **Head** child object. They will automatically follow face movement via the Face Binding tracking.

```
Face Binding          (Face Binding, anchored to FaceCenter)
  └── Head            (Mesh Renderer, occluder mesh)
      ├── LeftEar     (Cube, parented to Head)
      └── RightEar    (Cube, parented to Head)
```

### Steps

1. `add_builtin_object(object_type="Head Tracker")` — creates Face Binding + Head hierarchy
2. Create the decoration visual:
   - Prefer an existing imported accessory / prefab / project asset when a suitable face accessory already exists in the project.
   - Use `add_builtin_object(object_type="Cube")` / `"Sphere"` only for intentionally geometric/stylized decorations, invisible anchors, or quick prototypes.
3. `move_scene_object(guid=decoration_guid, parent=head_guid)` — parent it under Head
4. `set_component` — adjust Transform `localScale` and `localPosition` relative to Head

### Sizing Reference for Ear Decorations

- **Scale**: approximately `(0.4-0.6, 0.6-1.0, 0.3)` — small relative to the head
- **Position**: `x = +/-6 to 8` (left/right of center), `y = 14 to 16` (above center, near top of head)
- Adjust values based on desired decoration style (larger for exaggerated, smaller for subtle)

## Face Tracking Data for Game Control

Use `AlgorithmManager.getResult().getFaceBaseInfo(0)` to read head orientation each frame. The returned `Face106Interface` has three rotation angles (in radians):

| Property | What it measures | Positive value means |
|----------|-----------------|----------------------|
| `yaw` | Head turning left/right | User looks to **their right** |
| `roll` | Head tilting ear-to-shoulder | User tilts to **their left** (left ear toward shoulder) |
| `pitch` | Head nodding up/down | User **lowers** head (chin toward chest) |

**CRITICAL — yaw and roll have opposite conventions for screen mapping:**

- **yaw**: positive = user looks right → `face.yaw * sensitivity` moves player right ✓ (natural, no negation)
- **roll**: positive = user tilts LEFT → `face.roll * sensitivity` moves player RIGHT ✗ (inverted! must negate)

```typescript
// Roll-based control (tilt left/right) — MUST negate
const moveX = -face.roll * sensitivity;   // tilt left → roll positive → negated → moves LEFT ✓

// Yaw-based control (turn left/right) — do NOT negate for user-intent
const moveX = face.yaw * sensitivity;     // look right → yaw positive → moves RIGHT ✓
```

### Head Tilt Game Controller Pattern (roll-based)

Most AR games use **roll** (head tilt) for left/right control because it's more comfortable than turning the head:

```typescript
onUpdate(dt: number): void {
  const result = APJS.AlgorithmManager.getResult();
  if (result.getFaceCount() === 0) return;

  const face = result.getFaceBaseInfo(0);

  // Roll-based horizontal movement — negate for natural direction
  const moveX = -face.roll * this.sensitivity * dt;

  const pos = this.playerST.anchoredPosition;
  pos.x += moveX;
  pos.x = Math.max(-300, Math.min(300, pos.x));
  this.playerST.anchoredPosition = pos;
}
```

### Yaw-based Controller Pattern

For games where the user turns their head to look left/right:

```typescript
// Yaw: no negation needed — positive yaw = look right = move right
const moveX = face.yaw * this.sensitivity * dt;
```

> **Why the difference?** `yaw` positive = user's right, which matches screen right. `roll` positive = user tilts left, which is opposite to screen right. This asymmetry is inherent in the face tracking coordinate system.

See `APJS/examples/head_tilt_game_controller.json` for a complete working example.

## When to Use Head Tracker

Use Head Tracker when you need to build custom AR face decorations parented to the Head object. Real imported accessories are preferred for final visuals; primitive meshes are acceptable when the requested look is intentionally geometric or when they are only anchors/colliders/prototypes.

Library import is not available through the current toolset here. If a suitable face accessory already exists in the project, reuse that imported asset or prefab; otherwise build the decoration under Head directly.

## Head-Pinned Text — use 2D Text + worldscreen projection, NOT `3D Text Mesh`

For randomizers, captions, or any runtime-updated text that should follow the user's head, do **not** use `3D Text Mesh`. Its runtime is effectively read-only from JS:

- `inspect()` / `get_scene()` reports component type `'Text'`, but `getComponent('Text')` returns `null` because the actual runtime class is `Text3D`.
- Even with `getComponent('Text3D')`, assigning `comp.text = "…"` does not update what's rendered (the next-frame screenshot still shows the original text, while `console.log` confirms the new value internally). It compiles, runs without errors, and ships a screen that won't update.
- Setting `horizontalAlignment` / `verticalAlignment` via `set_component` may also fail to deserialize string enum values (e.g. `"VERTICAL_CENTER"`) — needs the numeric index instead.

Use this fallback pattern instead:

1. `add_builtin_object("2D Text", name="HeadLabel")` parented under the auto-created `2D Camera` (or a dedicated 2D screen container).
2. In your script, hold a `@serializeProperty` reference to a 3D anchor SceneObject parented to `Head Tracker → Head` (e.g. an `Empty Object` positioned above the head).
3. Each `onUpdate`, project the 3D anchor's world position into screen space and write to `headLabel.getComponent('ScreenTransform').anchoredPosition`. The 2D Text moves with the head, but `text` is freely settable at runtime.

The 3D anchor is what tracks the head; the 2D Text is what carries the runtime-mutable string. This decouples "follow the head" (3D, well-supported) from "update the text" (2D, settable at runtime).
