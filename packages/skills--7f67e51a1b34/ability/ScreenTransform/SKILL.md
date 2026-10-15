---
name: ScreenTransform
description: 配置 2D UI 的锚点、尺寸、偏移和布局约束，并在 APJS 中正确读取和更新屏幕坐标。也用于排查 UI 不可见、文字溢出和克隆后布局异常。
---

# ScreenTransform

2D objects use ScreenTransform for positioning. There are **two contexts** with different rules:

1. **DSL scene setup** (via `set_component` in `edit_by_dsl`)
2. **APJS script runtime** — use `getWorldPosition()`/`setWorldPosition()` with camera coordinate conversion

## DSL Scene Setup (MCP)

### Model

A ScreenTransform's layout is defined by four knobs, applied in order:

1. **`anchors`** — `Vector4f` `(left, right, bottom, top)` mapped to `(x, y, z, w)` (i.e. `{x=hMin, y=hMax, z=vMin, w=vMax}`), each value normalized to `[0, 1]` of the parent rect. Picks an **anchor rectangle** inside the parent.
2. **`sizeDelta`** — `Vector2f` element size, interpreted differently depending on whether the anchor rectangle is a point or a span:
   - **Point anchor** (`anchors.x == anchors.y` and `anchors.z == anchors.w`, e.g. `(0.5, 0.5, 0.5, 0.5)`) → `sizeDelta` is the element's **absolute pixel size**.
   - **Stretch anchor** (`anchors.x != anchors.y` or `anchors.z != anchors.w`, e.g. `(0, 1, 0, 1)`) → `sizeDelta` is the **element size minus the anchor rectangle size**. `0` = match the rectangle; negative = element is inset from the anchor edges; positive = larger.
3. **`pivot`** — `Vector2f` `0..1`, the origin point inside the element used for rotation/scaling/positioning. `(0.5, 0.5)` = center (default), `(0, 0)` = bottom-left, `(1, 1)` = top-right.
4. **`anchoredPosition`** — `Vector2f` pixel offset from the **anchor center** to the element's **pivot**, where `anchorCenter = (Lerp(anchors.x, anchors.y, pivot.x), Lerp(anchors.z, anchors.w, pivot.y))` in normalized parent space. Not clamped. Applies last.

Other knobs (pivot-centered, independent of the layout rectangle):

- **`rotation`** — degrees. `0` = element's local +X aligned with parent +X; **positive values rotate counter-clockwise** as viewed on screen (`+90` lifts the right edge to the top).
- **`scale`** — `Vector2f`, default `(1, 1)`.
- **`pixelsPerUnit`** — `Number`, default `32`, used for pixel↔world-unit conversion.

> **Coordinate convention**: For both `anchors` and all pixel vectors, **X+ is right and Y+ is up**. `(0, 0)` is the parent's bottom-left in normalized anchor space.

### Constraint enums are anchor classifiers

`horizontalConstraint` and `verticalConstraint` are **labels** the engine derives from the current anchor rectangle — they don't control behavior independently. You can either set the enum (the engine picks canonical anchor values) or set `anchors` directly (the engine re-classifies the enum). Expect the enum you read back to be whatever fits the stored rectangle.

| Horizontal enum | Anchor pattern |
|---|---|
| `FIXED` | `hMin == hMax` at an interior value (not `0` or `1`) — point anchor away from the edges |
| `LEFT_AND_FIXED` | `hMin = hMax = 0` — point anchor at parent's left edge |
| `RIGHT_AND_FIXED` | `hMin = hMax = 1` — point anchor at parent's right edge |
| `STRETCH` | `hMin = 0, hMax = 1` — full-width spread |
| `LEFT` / `RIGHT` / `LEFT_AND_RIGHT` | Partial spread (left half / right half / interior range) |

Vertical enum is the mirror: `TOP_AND_FIXED` / `BOTTOM_AND_FIXED` point at parent's top/bottom edge, `STRETCH` / `TOP` / `BOTTOM` / `BOTTOM_AND_TOP` are vertical spreads.

**Switching a constraint enum preserves the visual.** The engine re-expresses the current rectangle in the new mode — it never repositions or resizes. To get a "fresh" layout after a mode switch, set `anchors` + `anchoredPosition` + `sizeDelta` explicitly in the same call.

### Writable properties

All of `anchors`, `anchoredPosition`, `sizeDelta`, `pivot`, `rotation`, `scale`, `pixelsPerUnit`, `horizontalConstraint`, `verticalConstraint`, `offsets` are settable via `set_component`.

`offsets` is a `Vector4f` using the same `{x=left, y=right, z=bottom, w=top}` convention as `anchors` — signed pixel distances from the anchor center to each of the four edges of the element. It is **derived** from `anchoredPosition`, `sizeDelta`, and `pivot` (not stored independently), per the formulas:

```
left   = anchoredPosition.x - sizeDelta.x * pivot.x
right  = anchoredPosition.x + sizeDelta.x * (1 - pivot.x)
bottom = anchoredPosition.y - sizeDelta.y * pivot.y
top    = anchoredPosition.y + sizeDelta.y * (1 - pivot.y)
```

Writing `offsets` back-calculates and updates `sizeDelta` and `anchoredPosition` accordingly (`sizeDelta = (right - left, top - bottom)`). Prefer the knob that most directly matches your intent:

- **Want an explicit pixel size?** → `sizeDelta`
- **Want to shift from center?** → `anchoredPosition`
- **Want signed pixel insets from each of the four anchor edges?** → `offsets` (especially clear for STRETCH-mode insets and asymmetric edge bars)

### Defaults on a fresh `Screen Image` (720×1280 parent)

```
horizontalConstraint: FIXED   verticalConstraint: FIXED
anchors:          {x: 0.5, y: 0.5, z: 0.5, w: 0.5}   (point at parent's center)
anchoredPosition: {x: 0, y: 0}
sizeDelta:        {x: 720, y: 1280}
pivot:            {x: 0.5, y: 0.5}
```

### Verified recipes

All recipes below were verified end-to-end on a live 720×1280 scene (set → `capture_preview` → visual inspection). Each is a single `set_component` call.

**Fullscreen (two ways)**

```js
// Point-anchor form — no constraint-enum dependence
{ anchors: {x:0.5, y:0.5, z:0.5, w:0.5}, sizeDelta: {x:720, y:1280}, anchoredPosition: {x:0, y:0}, pivot: {x:0.5, y:0.5} }
// Spread-anchor form — also adapts if parent ever resizes
{ horizontalConstraint: "STRETCH", verticalConstraint: "STRETCH",
  anchors: {x:0, y:1, z:0, w:1}, sizeDelta: {x:0, y:0}, anchoredPosition: {x:0, y:0}, pivot: {x:0.5, y:0.5} }
```

**Centered fixed-size box (W × H)**

```js
{ horizontalConstraint: "FIXED", verticalConstraint: "FIXED",
  anchors: {x:0.5, y:0.5, z:0.5, w:0.5}, sizeDelta: {x:W, y:H}, anchoredPosition: {x:0, y:0}, pivot: {x:0.5, y:0.5} }
```

**Full-width top bar, 120 px tall**

```js
{ horizontalConstraint: "STRETCH", verticalConstraint: "TOP_AND_FIXED",
  anchors: {x:0, y:1, z:1, w:1},          // full width, point at top edge
  sizeDelta: {x:0, y:120},                // width matches parent, height 120
  pivot: {x:0.5, y:1},                    // pivot at bar's top-center — kisses the anchor
  anchoredPosition: {x:0, y:0} }
```

Mirror for bottom bar: `verticalConstraint: "BOTTOM_AND_FIXED"`, `anchors: {x:0, y:1, z:0, w:0}`, `pivot: {x:0.5, y:0}`.

**Left column, 200 px wide, full height**

```js
{ horizontalConstraint: "LEFT_AND_FIXED", verticalConstraint: "STRETCH",
  anchors: {x:0, y:0, z:0, w:1},
  sizeDelta: {x:200, y:0}, pivot: {x:0, y:0.5}, anchoredPosition: {x:0, y:0} }
```

**Full-parent stretch with symmetric inset (shrink 50 px horizontal, 100 px vertical)**

```js
{ horizontalConstraint: "STRETCH", verticalConstraint: "STRETCH",
  anchors: {x:0, y:1, z:0, w:1},
  sizeDelta: {x:-100, y:-200},            // total shrink = 100 horiz + 200 vert; pivot (0.5,0.5) splits symmetrically
  anchoredPosition: {x:0, y:0}, pivot: {x:0.5, y:0.5} }
```

**Shift a stretched rectangle without resizing** (e.g. slide a full-width bar 100 px right, 200 px up)

```js
// Start from the stretch form, then only change anchoredPosition. sizeDelta stays the same.
{ anchoredPosition: {x:100, y:200} }
```

**Sub-rectangle (e.g. Portrait occupies bottom-right quadrant of parent)**

```js
// anchor rectangle = right half × bottom half of parent
{ anchors: {x:0.5, y:1, z:0, w:0.5},      // hMin=0.5 hMax=1  vMin=0 vMax=0.5
  sizeDelta: {x:0, y:0}, anchoredPosition: {x:0, y:0}, pivot: {x:0.5, y:0.5} }
// The engine will auto-classify this as horizontalConstraint=RIGHT, verticalConstraint=BOTTOM.
```

### Tips

- **Edge-flushing via pivot**: set pivot to the touching corner (e.g. `(0, 1)` for top-left, `(1, 0)` for bottom-right) and `anchoredPosition: (0, 0)` — the element kisses that edge without half-size math.
- **In STRETCH mode, `anchoredPosition` is a rigid shift** of the already-stretched rectangle, not a repositioning of a point-anchored element.
- **Don't mix `offsets` with `anchoredPosition` / `sizeDelta` in the same `set_component` call** — `offsets` wins and the others get recomputed from it. Use one knob per call.

## APJS Script Runtime

In scripts, screen space is **720×1280 with origin at bottom-left, X+ right, Y+ up**. `rotation` has the same meaning as in the DSL: `0` points along +X, positive is counter-clockwise, and a child's on-screen angle is the sum of its own `rotation` and every ancestor's.

### Three rules for position reads and writes

**1. If the object has a `RigidBody2D`, the physics body owns the authoritative position.** Do NOT modify `ScreenTransform.anchoredPosition` (or `rotation`) directly on a physics body — the engine overwrites it on the next frame. Use `rb.position` / `rb.velocity` / `rb.addForce(...)` (or `rb.rotation` / `rb.addTorque(...)`).

```typescript
const rb = this.getComponent("RigidBody2D") as APJS.RigidBody2D;
// rb.position is in 2D physics world units (meters), with origin at the SCREEN CENTER (X+ right, Y+ up).
// Screen pixel space, by contrast, has origin at the BOTTOM-LEFT
// (0..720 horizontally, 0..1280 vertically). To convert:
//   worldX = (pixelX - 360) / pixelsPerUnit       // 360 = 720 / 2
//   worldY = (pixelY - 640) / pixelsPerUnit       // 640 = 1280 / 2
// `pixelsPerUnit` defaults to 32. rb.position represents the body's center of mass;
// setting it teleports the body to the specified position. To move the body smoothly while respecting physics simulation,
// use `rb.addForce(...)` or `rb.addTorque(...)` instead.
rb.position = new APJS.Vector2f((pixelX - 360) / 32, (pixelY - 640) / 32);
// if the origin of Screen pixel space is (0, 0), then:
rb.position = new APJS.Vector2f(pixelX / 32, pixelY / 32);
```

**2. `anchoredPosition` is parent-local.** It only equals screen space when the ScreenTransform is a root under the 2D Camera. Under any other parent, prefer world-space APIs:

```typescript
// Read world-space position of any ScreenTransform, hierarchy-safe.
const worldPos = transform.getWorldPosition();

// Write world-space position. Convert from screen space via the camera first.
const aspect = this.camera.renderTexture.getWidth() / 720.0;
const worldTarget = this.camera.screenToWorldPoint(
  new APJS.Vector3f(screenSpacePos.x * aspect, screenSpacePos.y * aspect, 40),  // z=40 (default camera distance) for ortho 2D
);
transform.setWorldPosition(worldTarget);
```

**3. When comparing positions (range checks, collision math), put everything in the same coordinate system.** World-space numbers are not in pixels — convert with `camera.worldToScreenPoint(...)` and divide by `aspect` before comparing against screen pixel bounds like `[0, 720] × [0, 1280]`. Never mix world coords and screen pixel bounds in the same expression, and never assume `anchoredPosition` gives you screen pixels unless you've verified the element is a 2D-Camera root.

## VERIFICATION
<ScreenTransform_validation>
- [ ] **Pick the right API for the parent chain**: `anchoredPosition` is correct for DSL layout setup and for ScreenTransform elements rooted directly under a 2D Camera (where parent-local equals screen-local). When an element has a non-trivial parent chain and you need its on-screen world-coordinate position, use `getWorldPosition()` / `setWorldPosition()` instead of guessing from nested `anchoredPosition` values.
- [ ] **Don't mix coordinate frames**: when comparing or computing positions, keep everything in the same frame — either world-space (use `worldToScreenPoint` / `screenToWorldPoint` to convert) or screen-pixel space (only valid when reading from a 2D-Camera-rooted ScreenTransform).
- [ ] **Camera reference for conversions**: when converting between world and screen space in scripts, always go through a camera component (`screenToWorldPoint`, `worldToScreenPoint`); never approximate the conversion arithmetic.
- [ ] **Frame-fit check for HUD / text**: after any 2D UI layout edit, verify the element is fully inside the 720×1280 frame with a small edge margin; no clipping, no overlap with sibling HUD, no accidental off-screen anchor drift.
- [ ] **Contrast check against the real screenshot**: verify HUD / title / result text is clearly separated from the actual background. If white or yellow text blends into bright water / sky / camera feed / particles, add a backing Image or choose a stronger text treatment before accepting the layout.
- [ ] **Budget for the longest likely runtime text**: don't size a text box only for the current placeholder. Reserve room for longer score / timer / hint / result strings, or treat the layout as unfinished.
- [ ] **Prefer a worst-case sample-string check**: for dynamic HUD text, temporarily preview the longest likely string (for example `分数 9999` or `最终得分 9999 / 9999`) instead of only reasoning abstractly from the placeholder width.
</ScreenTransform_validation>

## Common Pitfalls (read FIRST when debugging "UI not visible")

### Pitfall 1: Parent SceneObject is being disabled at runtime — child UI is hidden by cascade

`setEnabledInHierarchy(false)` on a parent **also hides every child**, regardless of the children's own `enabled`/`visible` state. So if you wired a UI element correctly, the texture is right, the position/size are right, the `Image` is enabled, and `set_scene_object visible: true` reports success — and yet the element doesn't show — **check what the script is doing to the parent SceneObject**.

Common culprit in games: a `ScoreUI` / `ResultUI` / `WinScreen` parent that the script toggles on/off across game states. Any child of that parent inherits the visibility.

**Diagnostic checklist** when a UI element doesn't show up at runtime:

1. Walk up the hierarchy from the missing element to the root. For each ancestor, search the script for `<parentName>.setEnabledInHierarchy(false)` or `setEnabledInHierarchy(true)` calls. If any ancestor is conditionally hidden in the state(s) you expected the child to be visible, you found it.
2. Check static (editor-time) visibility with `get_scene()` — the `visible` field IS effective visibility (false if this object or any ancestor is editor-hidden via `set_scene_object({visible: false})`). If `visible: false` here, an editor-side cascade is at work.
3. Check runtime cascades — if `get_scene()` says `visible: true` but the element is still missing, a script is calling `setEnabledInHierarchy(false)` on an ancestor at runtime. `get_scene()` reads editor state, so it won't reflect runtime toggles. Read the script's state-machine code: which states call `parent.setEnabledInHierarchy(false)`? Or instrument with `console.log(parent.isEnabledInHierarchy())` and read via `get_script_logs()`.

**Fix options** (pick one):
- **Reparent**: move the UI element OUT of the conditionally-hidden parent into a stable parent (e.g., directly under the 2D Camera, as a sibling of the toggled UI panel). Independent visibility.
- **Keep parent enabled**: change the script so the parent stays enabled, and only toggle the child UI panels you actually want to hide.
- **Synchronize**: enable the parent at the same state-transition where you want the child visible.

Reparenting is usually safest for "always-visible during a specific moment" effects (goal celebrations, kill streaks, combo overlays) — it decouples your effect from any UI panel's lifecycle.

> **Trap — runtime cascades hide from editor reads**: when an ancestor is hidden by a script calling `setEnabledInHierarchy(false)` at runtime, `get_scene()` and `inspect` still report `enabled: true` and `visible: true` for the child (they read static editor state). Reading editor visibility alone won't reproduce the bug — you have to either trace the script's state machine or log `isEnabledInHierarchy()` and check `get_script_logs()`. Editor-side hides DO show up in `visible`; runtime-script hides do not.

### Pitfall 2: Default `sizeDelta = (720, 1280)` — full screen — is rarely what you want

Every fresh `Screen Image` and `2D Text` ships with `sizeDelta = (720, 1280)`. That's the entire screen. Most UI elements should be much smaller (a button is ~200×80, a coin icon is ~60×60, a HUD score is ~120×80). Always set an explicit `sizeDelta` after creating a 2D object.

For full-screen overlays that genuinely should cover the screen (background dimmers, full-screen FX, vignettes), the default 720×1280 is appropriate and is the natural baseline. Mention this when sizing such elements: "leave at the 720×1280 default" is meaningful documentation.

For element-shaped UI (buttons, icons, panels), explicitly size — never rely on the default.

```
// Element-shaped UI — explicit size
set_component(stGuid, { sizeDelta: { x: 200, y: 80 } })

// Full-screen overlay — default works, but document it
// (no sizeDelta change needed; it's already 720x1280)
```

### Pitfall 3: Cloning a decorated `Screen Image` does NOT make a clean panel

A `Screen Image` host may already carry a real texture, material, stretch mode,
or baked decorative treatment from the template object you cloned. If you clone
that object and only change `color` / `opacity`, the old art can still bleed
through. This is a common reason a supposed "plain HUD backplate" still looks
like a prototype card or default template.

For generic backplates, modal shades, HUD strips, and result cards:

1. Prefer a known-clean image host or blank/white texture.
2. If you must reuse an existing `Screen Image`, explicitly replace or clear the
   texture/material before tinting it.
3. Judge the result from `capture_preview()`, not from hierarchy state
   or the fact that the object is rectangular in the editor.

If a "pure color" panel still shows template art in the screenshot, treat that
as a failed verification, not as a cosmetic nit.

### Pitfall 4: Placeholder text fits, runtime text overflows

A HUD can look correct in the first screenshot and still break in gameplay because the initial string is short. Common failures:

- `分数 0` fits, but `分数 9999` hits the edge
- `点击开始` fits, but a longer开始提示 or结果提示 overflows
- `成功` fits, but `最终得分 9999 / 9999` exceeds the box

Do not treat "the current frame's text is visible" as sufficient proof. For scoreboards, hints, and result panels, budget width and placement for the longest likely runtime string. The safest path is to temporarily swap in a worst-case sample string, capture a frame, and only then sign off on the layout. If you cannot guarantee that, the layout is not done yet.

### Pitfall 5: Text technically exists, but visually melts into the background

Common on ocean / sky / camera-feed / particle-heavy backgrounds: the `Text` object is present, inside frame, and even sized correctly, but white or yellow glyphs merge into a bright or noisy backdrop so the player still cannot read them quickly.

Fix in this order:

1. Add a dark translucent `Screen Image` as a banner / pill / backplate behind the text.
2. If that is still weak, switch to a stronger-contrast text color or weight.
3. For score popup / combo / countdown / win-lose / result-title moments, if the project already has or can import a reusable `ArtTextAsset`, bind it to the Text component's `artText` property instead of keeping plain text.

Do not sign off from hierarchy or inspector state alone — judge this from `capture_preview()`.
