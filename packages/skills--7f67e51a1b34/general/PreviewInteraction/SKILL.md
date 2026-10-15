---
name: PreviewInteraction
description: 预览交互验证：从已知初始状态刷新预览，通过点击、拖拽、临时属性和分时截图验证动态过程。静态编辑结果使用 capture_preview。
---

# PreviewInteraction — interact_by_dsl Commands

Drive live interactive preview actions: taps, drags, holds, timed waits, pause/resume, the record lifecycle, and dual-instance transport. Execute via `interact_by_dsl`. No alias/$ref. Sequential execution with fail-fast.

> **Choose capture by what you are verifying.** Use `capture_preview` after static edits: it performs `reset_preview → screenshot`. For dynamic effects, interactions, or non-initial states, start a verification sequence with `reset_preview` in `interact_by_dsl`, then enter a known state, trigger actions, and take screenshots along the same runtime sequence. Acceptance requirements are defined in `context.workspace.rules/validation.md`.

> **Keep the target state alive until capture.** After a touch or `transport_preview_property`, use `screenshot` inside `interact_by_dsl`. Calling `capture_preview` or `reset_preview` at that point discards the runtime state. A fresh reset belongs at the start of the next independent verification sequence.

> **Use the effect's state transitions to control visibility.** Start with the script's defined initial state so result pages and other inactive state groups are hidden as intended. Temporary editor visibility changes may isolate a bug, but restore them and any debug overrides before final verification from the real entry path. Do not hide required overlapping objects just to obtain a clean screenshot.

> **Prefer fast-state jumps over long waits.** If a target screen/state (countdown-end, first hit, win/lose, result) is more than about 3 seconds away by natural play, do not use long `wait`s, a full-round countdown, or a 30-second recording as the default proof path. Expose a temporary debug / force-show / serialized state field in the script, then jump there via `transport_preview_property` or a direct trigger and verify that frame. Keep per-check waiting to short settle windows.

> **Prepare the preview input before making the effect.** Select a suitable video before scene construction, tracking setup, or gameplay scripting, and recheck it when resuming work or changing input dependencies. Follow `context.workspace.rules/validation.md` and the source-selection steps below. Acceptance requires footage that actually exercises the effect's subject and actions.

> **Use exact command names; do not blind-probe aliases.** Unsupported guesses include `record`, `record_start`, `start_record`, `resume`, `play`, `start_preview`, `record_preview`, `start_recording`, `resume_recording`, `start_record_preview`, and `record_control`. Map your intent onto the table below instead. Also remember the high-frequency parameter shapes: `wait(ms)`, `touch(x,y)` with normalized `[0,1]` coords, `drag(x1,y1,x2,y2,duration_ms?)`.

> **Reserve the preview record-button keep-out zone.** In `ShootingEffect`-style previews, the native preview Record button occupies the lower-center interaction area. Do not design required taps, bottom cards, start / retry CTA, drag handles, or major HUD into that zone. On a 720x1280 preview, default to reserving the bottom ~180 px: avoid normalized top-origin `y >= 0.86` for required taps, and keep `ScreenTransform`-anchored interactive elements above centered `y = -460` unless you have an explicit reason and have revalidated the layout.

## Commands

| Command | Params | Notes |
|---------|--------|-------|
| `screenshot` | `path?` | Capture the current runtime frame without reloading. Returns image inline. |
| `touch` | `x, y` (0–1 normalized) | Simulate tap (touchDown + 50ms + touchUp). |
| `touch_down` | `x, y` (0–1 normalized) | Begin touch without releasing. |
| `touch_up` | `x, y` (0–1 normalized) | Release touch. |
| `drag` | `x1, y1, x2, y2, steps?, duration_ms?` | Simulate drag gesture. |
| `wait` | `ms` (max 30000) | Pause between interactions. |
| `reset_preview` | — | Reload scene, reset all runtime state. |
| `start_preview_record` | — | Start simulated Record. Triggers RecordStart behavior; call it again to restart Record without stopping first. **Saves nothing to disk** — see `record_preview_video_mp4` for that. |
| `stop_preview_record` | — | Stop simulated Record. |
| `record_preview_video_mp4` | `duration_seconds` (0 < d ≤ 60), `path?` (defaults to `<tmp>/dyeh_preview_<ts>.mp4`; `.mp4` and `.mov` allowed) | **Save the live preview to an MP4/MOV file via VESDK** — the same encode path the in-app Record button uses (with audio). Calls `PreviewManager.startRecording` → wait → `endRecording` → `savingRecording`, then polls for the file. Blocks until the file is written. Does NOT fire RecordStart — pair with `start_preview_record` if your effect gates visuals on it. Returns `{path, duration_ms, total_elapsed_ms, mime_type}`. |
| `pause_preview` | — | Freeze the preview stream — engine stops ticking, scripts stop receiving Update. The current frame stays on screen so `screenshot` returns it deterministically. Touch events queue until `resume_preview`. |
| `resume_preview` | — | Resume a previously paused preview. |
| `transport_preview_property` | `scene_object_guid`, `component_type`, `property`, `value` | **Preview only:** push a scalar (or engine-serializable) onto a script field in the running preview via dual-instance (`PreviewSyncer.transportAProperty`). `scene_object_guid` is the **SceneObject** editor GUID; `component_type` is the script **class name** (e.g. `DualInstanceCubeProbe`). Does **not** save the project — use `edit_by_dsl` → `set_component` on the Script component to persist. Requires dual instance ready. |

## Preview Source Selection

Prepare the source before implementation, then recheck it before acceptance. Source categories and the current full-body-video choice for foot effects are defined in `context.workspace.rules/validation.md`.

1. Call `get_current_preview_video` to know what is currently loaded.
2. If the current source lacks the required subject or motion, call `list_preview_videos`; otherwise keep the matching source.
3. Choose an exact `video_name` or `resource_url` from the returned list when available; otherwise use its `tracking_type`. Select by the footage's actual content, not just its category label.
4. Call `set_preview_video` with the chosen selector, then confirm the selected source with `get_current_preview_video`. Do not carry an old `resource_url` or `video_name` into a category switch: they take precedence over `tracking_type`.
5. Continue implementation with the matching source. At verification, use `capture_preview` for initial-state checks or start a fresh `interact_by_dsl` sequence for interactive checks; changing the source requires a new verification sequence.
6. Record the selected source and the actions it covers in the verification result. If no single video covers a combined effect, verify its inputs with separate sources.

## Dual-instance preview (transport)

Use **`transport_preview_property`** when you want the **running preview** to see a new serialized field value **without** persisting. After resetting once at the start of a verification sequence, push the field and inspect it with `screenshot` / `get_script_logs`; further actions in that sequence must preserve the current runtime.

**Scalar property push** (uniform scale example — matches `DualInstanceCubeProbe.cubeScale`):

```json
[
  { "command_type": "reset_preview", "params": {} },
  { "command_type": "wait", "params": { "ms": 200 } },
  {
    "command_type": "transport_preview_property",
    "params": {
      "scene_object_guid": "<cube-scene-object-guid>",
      "component_type": "DualInstanceCubeProbe",
      "property": "cubeScale",
      "value": 2.5
    }
  },
  { "command_type": "wait", "params": { "ms": 100 } },
  { "command_type": "screenshot" }
]
```

## Fast-state verification

When the script already exposes a preview-only debug field or temporary state override, jump straight to the target screen instead of waiting for the full gameplay lifecycle:

```json
[
  { "command_type": "reset_preview", "params": {} },
  { "command_type": "start_preview_record", "params": {} },
  {
    "command_type": "transport_preview_property",
    "params": {
      "scene_object_guid": "<game-manager-guid>",
      "component_type": "MyGameManager",
      "property": "debugScreenIndex",
      "value": 2
    }
  },
  { "command_type": "wait", "params": { "ms": 120 } },
  { "command_type": "screenshot", "params": {} }
]
```

`start_preview_record` is optional here; use it only when the effect's real entry path is gated on `RecordStart`. The example's final `screenshot` captures the jumped state; do not follow it with `capture_preview`. The jump proves that state's appearance, so also run a separate sequence from the real initial state to prove the key interaction reaches it. Restore temporary debug fields after the check.

## Timeline capture

Use timeline capture for effects whose quality depends on motion or time, such as particles, trails, delayed feedback, countdown transitions, and animated VFX. Put `reset_preview` and multiple `wait` + `screenshot` pairs in one `interact_by_dsl` call so every returned frame belongs to the same fresh runtime sequence:

```json
[
  { "command_type": "reset_preview", "params": {} },
  { "command_type": "wait", "params": { "ms": 200 } },
  { "command_type": "screenshot", "params": {} },
  { "command_type": "wait", "params": { "ms": 400 } },
  { "command_type": "screenshot", "params": {} },
  { "command_type": "wait", "params": { "ms": 800 } },
  { "command_type": "screenshot", "params": {} }
]
```

Judge the sequence, not a single frame: spawn timing, movement, density, decay, state change, and whether the effect appears in the expected screen area.

For an interaction, capture both the known initial state and the frames following the trigger. This example assumes the preview input is already suitable and the target position has been checked; omit `start_preview_record` when the effect does not use `RecordStart`:

```json
[
  { "command_type": "reset_preview", "params": {} },
  { "command_type": "start_preview_record", "params": {} },
  { "command_type": "wait", "params": { "ms": 120 } },
  { "command_type": "screenshot", "params": {} },
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 120 } },
  { "command_type": "screenshot", "params": {} },
  { "command_type": "wait", "params": { "ms": 400 } },
  { "command_type": "screenshot", "params": {} }
]
```

These frames show the pre-interaction state, early feedback, and its evolution in one run. Choose timing for the effect being tested and record each frame's state and trigger. For random targets or steps that require inspection before the next action, split into the pause-inspect-act batches below without resetting between them.

## Choosing an interaction style

**Default to the pause-inspect-act loop** for any sequence where per-step state matters (score / lives / screen switch / random-position targets). Only use a single-batch chain when the interaction is a continuous gesture that can't be paused mid-way, or when you only care about the next-step state.

| Style | Use when | Verification surface |
|---|---|---|
| **Pause-inspect-act loop** (multi-batch, pause between every interaction) | Score / lives / screen state change per step • Random-position targets (inspect to find, then tap) • Rhythm- or timing-gated decisions • A previous one-shot run failed and you need to bisect | Per-step screenshot + `get_script_logs()`. Failures isolate to one step. |
| **Single-shot trigger+capture** (one batch ending with screenshot) | One trigger, then check the final visual state | Final screenshot only |
| **Continuous gesture** (one batch, no internal screenshot or only post-gesture) | Drag, hold-to-charge, combo within a timing window where pausing would corrupt input | Whatever the gesture produces; verify after gesture completes |

## Patterns

### 1. Verify a single state

For a clean, deterministic frame after a build, prefer `capture_preview` (reset + screenshot in one call). Use a bare screenshot here only when you specifically want the *current* runtime frame without reloading:

```json
[{ "command_type": "screenshot" }]
```

### 2. Pause-inspect-act loop (the default for sequenced verification)

Each round is two batches with your own reasoning + `get_script_logs()` between them:

```json
// Inspect — freeze, capture, and read logs
[
  { "command_type": "pause_preview", "params": {} },
  { "command_type": "screenshot" }
]
// → call get_script_logs() separately
// → compare against the predicted post-state (score / visible HUD / active screen)
// → decide the next interaction from what's visible
```

```json
// Act — resume, interact, freeze again
[
  { "command_type": "resume_preview", "params": {} },
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 200 } },
  { "command_type": "pause_preview", "params": {} },
  { "command_type": "screenshot" }
]
// → call get_script_logs() again, compare, repeat
```

End the sequence with one `resume_preview` so the engine isn't left frozen.

### 3. Trigger + capture (single-shot)

For one trigger where only the post-trigger visual matters:

```json
[
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 500 } },
  { "command_type": "screenshot" }
]
```

### 4. Pause-to-freeze (single transient frame)

For visuals on screen for only a few hundred ms (combo labels, hit confirmations, particle bursts) where `wait` + `screenshot` is racy:

```json
[
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 80 } },
  { "command_type": "pause_preview", "params": {} },
  { "command_type": "screenshot" }
]
```
Next batch must start with `resume_preview` before continuing.

### 5. Continuous gesture (hold, drag, combo)

Continuous gestures **cannot** be split across batches without corrupting input — keep them in one batch. Verify after the gesture completes; use Pattern 2 if you need to step through what happens during multi-step sequences leading up to or after.

```json
// Hold-to-charge
[
  { "command_type": "touch_down", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 800 } },
  { "command_type": "screenshot" },
  { "command_type": "touch_up", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 150 } },
  { "command_type": "screenshot" }
]
```

```json
// Drag (swipe / slider)
[
  { "command_type": "drag", "params": { "x1": 0.3, "y1": 0.5, "x2": 0.7, "y2": 0.5 } },
  { "command_type": "wait", "params": { "ms": 200 } },
  { "command_type": "screenshot" }
]
```

```json
// Rapid taps inside a combo window — only when per-tap verification is NOT needed
// (e.g. "5 fast taps shouldn't crash"). For "score should advance by 1 per tap", use Pattern 2 instead.
[
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 300 } },
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 300 } },
  { "command_type": "touch", "params": { "x": 0.5, "y": 0.5 } },
  { "command_type": "wait", "params": { "ms": 300 } },
  { "command_type": "screenshot" }
]
```

### 6. Simulated Record lifecycle

```json
[
  { "command_type": "start_preview_record", "params": {} },
  { "command_type": "wait", "params": { "ms": 300 } },
  { "command_type": "stop_preview_record", "params": {} }
]
```
Call `start_preview_record` again to restart the effect's RecordStart flow.
Use this to hit the effect's `RecordStart` reset or opening path, not as a substitute for proving a full gameplay lifecycle by waiting it out.

### 7. Record the preview to an MP4

> **`record_preview_video_mp4` vs `start_preview_record` — different jobs.**
> - `start_preview_record` / `stop_preview_record` **simulate** the user tapping the preview Record button. They fire `RecordStart` / `RecordEnd` to scripts and toggle the on-screen recording UI. **They do not save any file.**
> - `record_preview_video_mp4` **captures pixels** from the live preview and writes an MP4. It does not change recording-simulation state and does not fire `RecordStart`.
>
> If your effect gates visuals on `RecordStart`, use both together:
> ```json
> [
>   { "command_type": "start_preview_record", "params": {} },
>   { "command_type": "wait", "params": { "ms": 200 } },
>   { "command_type": "record_preview_video_mp4", "params": { "duration_seconds": 5 } },
>   { "command_type": "stop_preview_record", "params": {} }
> ]
> ```
> Otherwise call `record_preview_video_mp4` alone — it does not depend on the simulated-record state.

**Record a 5-second MP4 of the live preview**:
```json
[
  { "command_type": "wait", "params": { "ms": 300 } },
  { "command_type": "record_preview_video_mp4", "params": { "duration_seconds": 5 } }
]
```
Returns the saved file path plus `duration_ms` / `total_elapsed_ms`. The command blocks for `duration_seconds` plus VESDK encode + file-flush time (typically a few hundred ms for short clips). Encoding settings (codec, fps, quality, audio) match the in-app Record button — they are not configurable from the DSL. Requires `dual instance` to be ready and the preview to be VE-synced.

### 8. Random-position targets

When spawn positions are non-deterministic, **pause to read where they landed**, then plan the tap from the visible state — don't blind-guess coordinates.

```json
// Inspect spawn
[
  { "command_type": "wait", "params": { "ms": 1500 } },
  { "command_type": "pause_preview", "params": {} },
  { "command_type": "screenshot" }
]
// → read the screenshot to locate the spawned target's screen position
// → convert to normalized [0,1] coordinates for the next touch
```

```json
// Act on the visible position
[
  { "command_type": "resume_preview", "params": {} },
  { "command_type": "touch", "params": { "x": <target.x>, "y": <target.y> } },
  { "command_type": "wait", "params": { "ms": 200 } },
  { "command_type": "pause_preview", "params": {} },
  { "command_type": "screenshot" }
]
// → confirm the target reacted (score increment, target consumed, etc.)
```

To verify *that random behavior is actually random* (range, variance), run `reset_preview` × 3 and compare via `get_script_logs()`. If a spawn location is genuinely unreadable from the screenshot (off-screen, hidden by another sprite, color-on-color), fall back to `get_script_logs()` traces — have the script `console.log` the spawn coordinates so the agent can read them deterministically.
