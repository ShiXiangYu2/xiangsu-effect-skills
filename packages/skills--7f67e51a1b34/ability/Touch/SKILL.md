---
name: Touch
description: 实现点击、按钮命中、3D 对象点击、拖拽跟随、多点触控锁定、轨迹绘制和手势事件。
---

# Touch Events

Touch events are received via the global event emitter using `APJS.EventType.Touch`.

## TouchData Properties

| Property | Type | Description |
|----------|------|-------------|
| `phase` | `APJS.TouchPhase` | Current touch phase |
| `position` | `APJS.Vector2f` | Normalized touch position (0-1 range, origin top-left) |
| `force` | `number` | Touch pressure (0-1) |
| `touchId` | `number` | Unique touch identifier |
| `touchCount` | `number` | Number of active touches |

## TouchPhase Values

| Phase | Description |
|-------|-------------|
| `APJS.TouchPhase.Began` | Finger touched screen |
| `APJS.TouchPhase.Moved` | Finger moved on screen |
| `APJS.TouchPhase.Ended` | Finger lifted |
| `APJS.TouchPhase.Canceled` | Touch was canceled by system |

## Rules

1. **Position conversion**: `position` is normalized (0-1) with origin at TOP-LEFT. To convert to screen space (720x1280, bottom-left origin):
   ```typescript
   const screenPos = new APJS.Vector2f(touchInfo.position.x * 720, (1.0 - touchInfo.position.y) * 1280);
   ```
2. **MUST** store callback reference for cleanup in `onDestroy()`
3. **MUST** unregister in `onDestroy()` using `.off()` with the same callback and context
4. **Button/icon taps (2D Images)**: Use `APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, imageComponent)` for hit detection. **Only works for `APJS.Image` components**; it handles the Y-flip internally so pass `touchInfo.position` unchanged.
5. **3D object taps (tiles, cards, ground-plane spawns, anything rendered by a Camera in the General render group)**: `TouchUtils.isScreenPointOnImage` does NOT apply — those aren't Images. Use `Camera.viewportPointToRay` + plane intersection (or `Physics3D.raycast` if colliders exist) — see `Camera/SKILL.md` *"3D Hit Detection via Ray-Cast"*. **You MUST flip Y** (`1 - touchInfo.position.y`) before handing the touch to any `Camera.*` method; forgetting it mirrors every hit to the wrong screen half.
6. **Full-screen tap**: only when ANY screen touch should trigger the action.
7. **Preview record-button keep-out zone**: On `ShootingEffect`-style previews, do not place required taps, bottom cards, drag handles, or start / retry buttons inside the lower-center record-button zone. On a 720x1280 preview, reserve roughly the bottom 180 px for the host UI: normalized top-origin touches with `y >= 0.86`, or `ScreenTransform`-anchored interactive elements with centered `y <= -460`, should be treated as unsafe by default.

## Full-Screen Tap Pattern

Use when **any screen touch** should trigger the action (e.g., "tap to start", "tap anywhere to continue").

```typescript
@component()
export class TapHandler extends APJS.BasicScriptComponent {
  private touchCallback: (event: APJS.IEvent) => void;

  onStart(): void {
    this.touchCallback = (event: APJS.IEvent) => {
      const touchInfo = event.args[0] as APJS.TouchData;
      if (touchInfo.phase === APJS.TouchPhase.Began) {
        // Handle tap
        this.onTap();
      }
    };
    APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch, this.touchCallback, this);
  }

  private onTap(): void {
    // Tap logic here
  }

  onDestroy(): void {
    if (this.touchCallback) {
      APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch, this.touchCallback, this);
    }
  }
}
```

## Button Tap Pattern (Hit-Test)

Use when the tap should only register **within a specific UI element's bounds** (button, icon, card). Uses `APJS.TouchUtils.isScreenPointOnImage()` — pass the touch position and the button's Image component directly, no coordinate conversion needed.

```typescript
@component()
export class ButtonTapHandler extends APJS.BasicScriptComponent {
  @serializeProperty
  private buttonObj: APJS.SceneObject;

  private buttonImage!: APJS.Image;
  private initialized: boolean = false;

  private touchCallback = (event: APJS.IEvent) => {
    if (!this.initialized) return;
    const touchInfo = event.args[0] as APJS.TouchData;
    if (touchInfo.phase === APJS.TouchPhase.Began) {
      if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.buttonImage)) {
        this.onButtonTap();
      }
    }
  };

  onUpdate(dt: number): void {
    if (!this.initialized && this.buttonObj) {
      this.buttonImage = this.buttonObj.getComponent("Image") as APJS.Image;
      APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch, this.touchCallback);
      this.initialized = true;
    }
  }

  private onButtonTap(): void {
    // Button tap logic here
  }

  onDestroy(): void {
    APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch, this.touchCallback);
  }
}
```

### Multiple Buttons

```typescript
if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.startBtnImage)) {
  this.onStartTap();
} else if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.settingsBtnImage)) {
  this.onSettingsTap();
}
```

> **Note**: `isScreenPointOnImage` requires the Image to be rendered by an Orthographic camera — this is the default for all 2D/UI objects (Screen Image, 2D Text).

## 3D Object Tap Pattern (No Image Component)

`TouchUtils.isScreenPointOnImage` is `APJS.Image`-only. For taps on 3D objects rendered by a Perspective camera in the General render group — tiles in a sliding puzzle, cards on a table, a target on a wall — there's no Image to hit-test, so use one of two camera-based patterns instead.

### Decision

| Situation | Pattern | Where it's documented |
|---|---|---|
| A handful of distinct 3D objects you already iterate to render | `Camera.worldToViewportPoint(obj.worldPos)` + AABB compare | `Camera/SKILL.md` → *Touch Hit Detection Pattern* |
| A grid / play surface where you'd rather convert tap → world point once and look up the cell | `Camera.viewportPointToRay(viewportPos)` + plane intersection + parent-local mapping | `Camera/SKILL.md` → *3D Hit Detection via Ray-Cast* |
| Objects already have `BoxCollider3D` / `SphereCollider3D` (physics, drag-and-drop, irregular layout) | `Physics3D.raycast(ray.origin, ray.direction, maxDistance)` against the same ray from `viewportPointToRay` | `Physics3D/SKILL.md` |

### The single rule you must not forget

**Flip the touch Y before any Camera method.** `TouchData.position` is top-origin (y=0 top), every `Camera.*` method that takes viewport coords is bottom-origin (y=0 bottom). Pass `(touch.x, 1 - touch.y)` — not `touch.position` directly. Forgetting this mirrors every tap to the wrong half of the screen and you'll see ZERO hits on the puzzle even though the tap event fires correctly. (Yes, this happens every time someone tries to write a 3D tap handler from scratch. Yes, this rule applies to `viewportPointToRay` too, not just `worldToViewportPoint`.)

`TouchUtils.isScreenPointOnImage` does the flip internally — that's why the 2D pattern doesn't show it.

## Drag / Follow Finger Pattern

```typescript
@component()
export class DragObject extends APJS.BasicScriptComponent {
  private touchCallback: (event: APJS.IEvent) => void;
  private isDragging: boolean = false;

  onStart(): void {
    this.touchCallback = (event: APJS.IEvent) => {
      const touchInfo = event.args[0] as APJS.TouchData;
      const screenPos = new APJS.Vector2f(
        touchInfo.position.x * 720,
        (1.0 - touchInfo.position.y) * 1280
      );

      if (touchInfo.phase === APJS.TouchPhase.Began) {
        this.isDragging = true;
      } else if (touchInfo.phase === APJS.TouchPhase.Moved && this.isDragging) {
        // Move object to touch position (for 2D ScreenTransform objects)
        const st = this.getSceneObject().getComponent("ScreenTransform") as APJS.ScreenTransform;
        if (st) {
          const centeredPos = screenPos.clone().subtract(new APJS.Vector2f(360, 640));
          st.anchoredPosition = centeredPos;
        }
      } else if (touchInfo.phase === APJS.TouchPhase.Ended || touchInfo.phase === APJS.TouchPhase.Canceled) {
        this.isDragging = false;
      }
    };
    APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch, this.touchCallback, this);
  }

  onDestroy(): void {
    if (this.touchCallback) {
      APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch, this.touchCallback, this);
    }
  }
}
```

## Multi-Touch Filter (First-Finger Lock)

Mobile devices fire `Touch` events for EVERY finger on screen in parallel. Any stroke-drawing, drag, or single-tap mechanic will misbehave when the player puts down a second finger (deliberately or by accident):

- **iOS**: events from the two fingers interleave. If your drawing code reads every `Moved` event regardless of which finger it came from, the rendered stroke connects the two fingers — drawing a filled polygon / bad-shaped plane between them.
- **Android**: the second finger's events still arrive, but the system may silently drop the primary stroke's updates — the stroke just stops appearing.

**Fix**: during the DRAWING state, claim the first finger's `touchId` on its `Began`, drop every event whose `touchId` doesn't match, release the lock on the owner's `Ended` / `Canceled`. Reset the lock when entering DRAWING so stale state from a prior round doesn't carry over.

**CRITICAL — scope the lock to the drawing state, NOT globally**. The reason is a cross-platform touch-propagation difference:

- On **Android**, the native **preview record button** fires a regular `TouchPhase.Began` event to the engine's touch listener when the player presses it. If you claim the lock globally on the first `Began` seen, the record-button finger wins the lock in TUTORIAL/IDLE, and then when DRAWING starts the actual drawing finger's `Began` is rejected.
- On **iOS**, the record button is consumed in the native UI layer and never reaches APJS, so a global filter happens to work — but you can't rely on this.

Scoping the filter to DRAWING lets the record-button finger's events pass through `onTouch` untouched in other states, while still rejecting rival fingers once the stroke begins. When DRAWING is entered the lock is already reset, so the first `Began` *in-state* claims input — which will always be the drawing finger, since the record-button finger already fired its `Began` in a prior state.

Even with the lock implemented correctly, do not rely on custom gameplay buttons or card taps that sit inside the preview record-button zone. The right fix there is layout: move the interaction out of the host button's keep-out area, then revalidate touch behavior.

```typescript
// -1 = no finger currently owns input
private activeTouchId: number = -1;

private onTouch = (event: APJS.IEvent): void => {
  const touch = event.args[0] as APJS.TouchData;
  const phase = touch.phase;

  // Filter engaged ONLY during DRAWING. Outside drawing, any finger
  // taps through normally (tutorial dismiss, idle start, retry).
  if (this.currentState === this.STATE_DRAWING) {
    if (phase === APJS.TouchPhase.Began) {
      if (this.activeTouchId !== -1) return;   // another finger already owns input
      this.activeTouchId = touch.touchId;
    } else {
      if (touch.touchId !== this.activeTouchId) return;  // not the owner — drop
      if (
        phase === APJS.TouchPhase.Ended ||
        phase === APJS.TouchPhase.Canceled
      ) {
        this.activeTouchId = -1;   // release lock for the next stroke
      }
    }
  }

  // ... your normal state logic, drawing handler, button dispatch, etc.
};

// Reset the lock when entering the drawing state (e.g. each new round)
private enterDrawing(): void {
  this.activeTouchId = -1;
  // ... other per-round reset ...
}
```

**Android-specific failure mode** (why a globally-scoped filter produces silent misbehavior): the player presses record and immediately starts drawing with another finger. Drawing never registers because finger A (record button) owns the lock. The ball still "flies" because the 5-second draw timer auto-transitions DRAWING → FLYING with an empty path — it looks like a normal round that just happened to miss. The user experiences "drawing doesn't work sometimes on Android" with no obvious error.

**Use this filter when**:
- Stroke drawing (path drawing, signature capture, brush strokes) — see `context.workspace.APJS/examples/commandbuffer_paint_canvas.json` for the CommandBuffer paint pattern.
- Drag-to-target mechanics where a second finger would interfere.
- Single-tap flows (tutorial dismiss, tap-to-start, tap-to-retry) where the second finger shouldn't re-trigger anything.

**Skip it when**:
- Multi-touch is intentional (pinch to zoom, two-finger rotate, multi-touch drum pad, simultaneous aim + fire).

**Key property on `TouchData`**: `touchId` (unique per finger). `touchCount` is also available if you want to branch on "how many fingers are down right now" rather than lock to a specific one.

## Drawing / Path Recording Pattern (One-Stroke)

Record a single finger stroke as a series of 3D waypoints. Useful for "draw a flight path" mechanics. The key constraint: only one stroke is allowed — once the finger lifts, drawing is done.

```typescript
private drawing: boolean = false;
private path: APJS.Vector3f[] = [];
private touchCount: number = 0;

private onTouch = (event: APJS.IEvent): void => {
  const t = event.args[0] as APJS.TouchData;

  if (t.phase === APJS.TouchPhase.Began) {
    this.drawing = true;
    this.path = [];
    this.touchCount = 0;
    this.recordPoint(t.position);
  } else if (t.phase === APJS.TouchPhase.Moved && this.drawing) {
    this.recordPoint(t.position);
    this.touchCount++;
  } else if (t.phase === APJS.TouchPhase.Ended && this.drawing) {
    this.drawing = false;
    this.recordPoint(t.position);
    this.onDrawComplete(); // start ball flight, etc.
  }
};

private recordPoint(tp: APJS.Vector2f): void {
  const vy = 1 - tp.y; // invert Y to viewport space
  // Convert 2D touch → 3D world position using camera projection
  // See Camera/SKILL.md "Perspective Depth LUT" for the correct approach
  // on tilted trajectories.
  const worldPos = /* ... projection logic ... */;
  this.path.push(worldPos);
}
```

**Visual feedback**: render the stroke with the CommandBuffer brush pattern from `context.workspace.APJS/examples/commandbuffer_paint_canvas.json` — stamp a dab into the canvas RenderTexture at each recorded point (`paintTo`), and clear the canvas according to your gameplay timing (for example on each new gesture, or on commit when the ball launches). The waypoint array above is the gameplay *data*; the brush canvas is the *visual*.

**After recording**: Process the raw path through the Animation/SKILL.md smoothing pipeline (Catmull-Rom → arc-length resample) before animating an object along it.

**For visible stroke rendering** (drawing a brush line on screen as the finger moves): use the CommandBuffer stamp-accumulation pattern in `context.workspace.APJS/examples/commandbuffer_paint_canvas.json`. That is the rendering approach for every drawn-line request, transient or persistent.

**For multi-touch robustness** (iOS polygon-fill bug, Android stroke-drop bug): always pair drawing code with the Multi-Touch Filter above. A stroke-drawing mechanic without the first-finger lock will misbehave the moment the player rests a second finger on screen.

## Gesture Emitter

For higher-level gestures, use `APJS.EventManager.getGestureEmitter()`. Works the same as global emitter but emits gesture-specific events.
