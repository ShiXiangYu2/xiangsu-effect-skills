---
name: Timing
description: 时机判定玩法：适用于转盘或滑条定点停止、蓄力释放、精准切割等需要抓准时机的交互。玩家确认操作时记录当前角度、位置或进度，再按与目标的偏差给出 PERFECT、GOOD、MISS 等结果。
---

# Timing — Hit-Window Scoring

Patterns for games where the user's input arrives in continuous time and the score is a function of *how close* to an ideal moment that input lands. Common shapes: tap-to-stop a moving indicator, swipe through a moving target with the right angle/length, hold-and-release to freeze a charge meter near a target ratio.

## When to use

- "Tap when the wheel is on the red sector"
- "Stop the bar inside the green window"
- "Hold to charge, release at full power"
- "Swipe the line at the right angle"
- "Cut at the exact moment the fruit crosses the blade"

If the outcome is randomly drawn and the user only triggers reveal, that's `Randomizer/SKILL.md`. If the user controls a continuous pose (drag, drive a character) without a discrete commit moment, that's `Touch/SKILL.md` or the relevant physics skill. Timing always has a **single discrete commit** that captures one continuous value and buckets it.

## Pattern 1 — Hit-window scoring

The decision rule shared by every timing game: capture one offset at commit time, take its absolute value (or shortest-distance value for circular spaces), and bucket into named tiers.

```typescript
function scoreHit(offset: number, perfect: number, good: number): "PERFECT" | "GOOD" | "MISS" {
  const d = Math.abs(offset);
  if (d < perfect) return "PERFECT";
  if (d < good) return "GOOD";
  return "MISS";
}
```

**Choosing the thresholds.** The window widths set the difficulty curve. Default starting points, tunable per game:

| Tier | Linear (px / sec / units) | Angular (degrees) | Normalized (0-1) |
|---|---|---|---|
| PERFECT | < 5% of full range | < 8° | < 0.05 |
| GOOD | < 15% of full range | < 25° | < 0.15 |
| MISS | else | else | else |

Tighten PERFECT to make the game harder; widen GOOD to make it more forgiving. Always playtest — a "PERFECT < 8°" wheel feels different at 0.5 rev/sec vs 2 rev/sec because the player has more or less time to react.

**Circular spaces — use shortest angular distance.** When the offset is in a wrapping space (degrees, normalized [0, 1] of a circle), `Math.abs(angle - target)` is wrong at the seam. Wrap first:

```typescript
let d = Math.abs(angle - target);
if (d > 180) d = 360 - d;     // shortest path on a 360° circle
// (or: if (d > 0.5) d = 1 - d;  for normalized [0, 1])
```

Without the wrap, a target at 5° and an angle at 355° report a distance of 350° (looks like a MISS) when the visual gap is 10° (a GOOD hit).

**Threshold-as-data, not magic numbers.** Pin the thresholds to `@serializeProperty` fields so designers can re-tune from the inspector without re-editing the script:

```typescript
@serializeProperty perfectThreshold: number = 8;
@serializeProperty goodThreshold: number = 25;
```

## Pattern 2 — Stop-on-target (tap-to-freeze a moving indicator)

A continuously moving indicator (rotating wheel, sliding bar, sweeping spotlight) freezes when the player taps. The captured position is scored against a target.

### 2a. Two stop styles

| Style | Behavior on tap | Fits |
|---|---|---|
| **Instant freeze** | indicator stops immediately at the current frame | tight reaction games (sub-second window), stop-the-bar, bullet-hit |
| **Damped stop** | indicator decelerates over ~0.5–1.0s, lands somewhere ahead of the tap point | wheel-of-fortune feel, slower stop-the-spinner, "physics-y" idle games |

**Pick instant for v1.** It removes the "predict the post-tap drift" cognitive load — the player is scored on what they saw at tap time, not what the engine drifted to. Use damped only when the genre demands a wheel-spin feel (gambling-game UX), and document the deceleration distance in the skill output so the player can learn it.

### 2b. Instant-freeze loop

```typescript
const STATE_IDLE = 0, STATE_SPINNING = 1, STATE_RESULT = 2;

@component()
export class StopOnTarget extends APJS.BasicScriptComponent {
  @serializeProperty wheel!: APJS.SceneObject;
  @serializeProperty stopButton!: APJS.SceneObject;
  @serializeProperty resultText!: APJS.SceneObject;
  @serializeProperty stopLabel!: APJS.SceneObject;

  @serializeProperty targetSector: number = 0;     // which of the N sectors is the target
  @serializeProperty sectorCount: number = 6;
  @serializeProperty spinSpeed: number = 360;      // degrees per second (constant during SPINNING)
  @serializeProperty perfectThreshold: number = 8;  // degrees from sector center
  @serializeProperty goodThreshold: number = 25;

  private state: number = STATE_IDLE;

  private onTouch = (event: APJS.IEvent) => {
    const touch = event.args[0] as APJS.TouchData;
    if (touch.phase !== APJS.TouchPhase.Began) return;
    if (this.state === STATE_SPINNING || this.state === STATE_RESULT) {
      const btnImg = this.stopButton.getComponent("Image") as APJS.Image;
      if (btnImg && APJS.TouchUtils.isScreenPointOnImage(touch.position, btnImg)) {
        if (this.state === STATE_SPINNING) this.commit();
        else this.retry();
      }
    }
  };

  onUpdate(dt: number): void {
    if (this.state !== STATE_SPINNING) return;
    const st = this.wheel.getComponent("ScreenTransform") as APJS.ScreenTransform;
    if (st) st.rotation += this.spinSpeed * dt;
  }

  commit(): void {
    this.state = STATE_RESULT;
    const st = this.wheel.getComponent("ScreenTransform") as APJS.ScreenTransform;
    const finalAngle = st ? st.rotation : 0;
    const angle = ((finalAngle % 360) + 360) % 360;
    const sectorDeg = 360 / this.sectorCount;

    // Pattern 1 — shortest angular distance to target sector center.
    const targetCenter = this.targetSector * sectorDeg + sectorDeg / 2;
    let dist = Math.abs(angle - targetCenter);
    if (dist > 180) dist = 360 - dist;

    let verdict = "MISS";
    if (dist < this.perfectThreshold) verdict = "PERFECT!";
    else if (dist < this.goodThreshold) verdict = "GOOD";

    const rt = this.resultText.getComponent("Text") as APJS.Text;
    if (rt) rt.text = verdict;
    const lbl = this.stopLabel.getComponent("Text") as APJS.Text;
    if (lbl) lbl.text = "RETRY";
  }

  retry(): void {
    this.state = STATE_SPINNING;
    const rt = this.resultText.getComponent("Text") as APJS.Text;
    if (rt) rt.text = "";
    const lbl = this.stopLabel.getComponent("Text") as APJS.Text;
    if (lbl) lbl.text = "STOP!";
  }
}
```

Three things to keep separate: the **state** (drives flow), the **moving indicator's value** (`ScreenTransform.rotation` here, but could be `anchoredPosition.x` for a sliding bar), and the **scoring function** (Pattern 1 applied to the captured value).

### 2c. Variants

- **Sliding bar instead of wheel** — same skeleton; replace `st.rotation` with `st.anchoredPosition.x`, pingpong between min/max instead of unbounded rotation, and target a single x-coordinate (linear hit window, no wrap).
- **Multiple targets** — set `targetSector` to a random 0..N-1 each `retry()` for variety.
- **Damped stop** — change `commit` to set `state = STATE_STOPPING`, then in `onUpdate` decay `this.spinSpeed *= 0.93` per frame until below 5°/s before computing the final score. Adds ~0.7s of post-tap drift; players need a few rounds to learn the offset.

## Pattern 3 — Charge meter (hold-and-release)

The player holds the screen to fill a meter and releases when it crosses a target. The captured value is `fill ratio at touch-up time`.

```typescript
const STATE_READY = 0, STATE_CHARGING = 1, STATE_RESULT = 2;

@component()
export class ChargeMeter extends APJS.BasicScriptComponent {
  @serializeProperty meterFill!: APJS.SceneObject;     // Screen Image with drawMode=Filled, filledType=Horizontal
  @serializeProperty resultText!: APJS.SceneObject;

  @serializeProperty chargeRate: number = 0.6;          // fill per second
  @serializeProperty targetRatio: number = 0.7;         // ideal fill at release (0..1)
  @serializeProperty perfectThreshold: number = 0.05;   // ±5% PERFECT
  @serializeProperty goodThreshold: number = 0.15;      // ±15% GOOD

  private state: number = STATE_READY;
  private fillRatio: number = 0;

  private onTouch = (event: APJS.IEvent) => {
    const touch = event.args[0] as APJS.TouchData;
    if (touch.phase === APJS.TouchPhase.Began && this.state === STATE_READY) {
      this.state = STATE_CHARGING;
      this.fillRatio = 0;
    } else if (touch.phase === APJS.TouchPhase.Ended && this.state === STATE_CHARGING) {
      this.commit();
    }
  };

  onUpdate(dt: number): void {
    if (this.state !== STATE_CHARGING) return;
    this.fillRatio = Math.min(1, this.fillRatio + this.chargeRate * dt);
    const img = this.meterFill.getComponent("Image") as APJS.Image;
    if (img) img.filledRange = this.fillRatio;
    if (this.fillRatio >= 1) this.commit();   // overcharge auto-commits at full
  }

  commit(): void {
    this.state = STATE_RESULT;
    const offset = this.fillRatio - this.targetRatio;        // signed offset for under/over messaging
    const d = Math.abs(offset);
    let verdict = "MISS";
    if (d < this.perfectThreshold) verdict = "PERFECT!";
    else if (d < this.goodThreshold) verdict = offset > 0 ? "OVER" : "UNDER";
    const rt = this.resultText.getComponent("Text") as APJS.Text;
    if (rt) rt.text = verdict;
  }
}
```

**Signed vs unsigned offset.** A charge meter has an axis (under-fill vs over-fill); preserve the sign so the UI can show "UNDER" / "OVER" as a hint instead of a flat "MISS". Pure tap-to-stop games are usually symmetric (early vs late are both just "off") and the sign is discarded.

**Auto-commit at the cap.** If the player holds past full, commit at full instead of waiting indefinitely. Otherwise a held-too-long touch never resolves and the result text never updates.

## Cross-leaf reuse

Three leaves use these patterns:

- **`interactive/precision-cut`** — Pattern 2 is the core (stop-the-wheel template `wheel_stop_target.json`, stop-the-bar variants).
- **`interactive/projectile-3d`** — Pattern 3 drives charge-shot variants; the projectile's launch impulse comes from the captured fill ratio. See `experiments/S5-trajectory-preview.md` for related charge-feedback work.
- **`interactive/runner-3d`** — Pattern 1 is reused for dodge timing windows: the offset is the time difference between obstacle-passing and tap, not a position; same bucket math, different captured value.

When a new genre needs timing logic, consume this skill — do not duplicate the bucket-thresholds reasoning.

## Gotchas

- **Reading `ScreenTransform.rotation` after script-driven writes is fine.** It's the editor-instance value the script just wrote; no dual-instance gotcha here. The dual-instance issue (`get_scene` showing stale values) only applies to MCP tools reading from outside the script.
- **Threshold drift across framerates.** Bucket thresholds are absolute (degrees, ratio); they don't depend on frame rate. But the *captured* value can drift if `spinSpeed * dt` is large — at 30 fps with `spinSpeed = 360°/s`, the wheel jumps 12° per frame, larger than the PERFECT window (8°). Cap `spinSpeed` so per-frame movement stays smaller than `perfectThreshold` to keep the game fair.
- **Don't seed RNG into the indicator phase.** `Math.random()` isn't reseeded across `reset_preview` (see `Randomizer/SKILL.md` Gotchas). If two sessions need to start at the same wheel angle, write the angle explicitly in `onStart`.
- **Tap before SPINNING starts wastes a tap.** If the screen accepts taps in IDLE that aren't the "start" tap, the player commits with `fillRatio=0` and gets a MISS they can't see causing. Gate every input on the current state.
- **RecordStart must reset the round.** Subscribe to `APJS.EventType.RecordStart` and reset state, screen visibility, indicator position, result text, and button labels. Otherwise users can start recording from a frozen RESULT state.
- **Target labels on rotating wheels need explicit render order.** If a Text marker rides inside the wheel, parent it under the wheel. To place it before a sibling, call `move_scene_object` with the wheel `parent` and that sibling as `above_scene_object`; otherwise the marker can exist in `get_scene()` but render under the colored sectors.
- **Damped-stop unfairness.** With damped stop, two players tapping at the same wheel angle still land at different final angles because `0.93^N` accumulates float error and the post-tap drift can drift by ±2-3° round to round. State this in the skill if your game uses it; players notice.

## Related

- Template: `game-templates/templates/wheel_stop_target.json` — full Intro + Main scene, 6-sector wheel, instant-freeze stop button, perfect/good/miss scoring against `targetSector` (default red), retry without leaving the screen.
- Companion skills: `Touch` (tap event registration, button hit-test), `Randomizer` (visual wheel composition pattern is shared with `wheel_spin`), `UIPatterns` (button + result text layout), `GameState` (IDLE → SPINNING → RESULT state machine), `Math` (Math.abs / wrap-around distance).
- Cross-leaf experiments: `interactive/precision-cut/experiments/E1-wheel-stop-target.md` (this skill's anchor experiment), `interactive/projectile-3d/experiments/S5-trajectory-preview.md` (charge meter + trajectory dots).
- Examples (orphans worth linking from a timing scene): `APJS/examples/ping_pong_ui_animation.json` (oscillating bar substrate), `APJS/examples/tile_tap_detection.json` and `APJS/examples/button_tap_hit_test.json` (in-region commit), `APJS/examples/countdown_timer.json` (round timer), `APJS/examples/scoring_system.json` and `APJS/examples/score_fly_up.json` (perfect/good/miss feedback).
