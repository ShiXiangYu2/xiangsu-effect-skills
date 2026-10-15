---
name: ScriptDebug
description: 排查 APJS 脚本的编译、绑定和运行时问题，配合 run_otsc_check、get_script_logs 和预览交互定位常见错误。
---

# Script Debugging

> **Current debugging split:**
> - `edit_by_dsl(add_script)` and `edit_by_dsl(edit_script)` wait for editor compilation.
>   Read `_compile_check.has_errors` for the batch verdict and the failed
>   `results[i].error` for the full compiler diagnostic.
> - On this branch, compile diagnostics and runtime logs are split: prefer `run_otsc_check()` for TypeScript compile checks, and use `get_script_logs()` for runtime / console fallout.
> - Use `edit_script(guid, code)` to replace an existing live
>   `Assets/**/*.ts|js` file. `add_script` is only for first-time creation of a
>   brand-new script asset.
> - Game scripts should emit stable, queryable observability logs for key interactions and state changes. Treat logs as the source of truth for audio playback and internal game-state transitions that screenshots alone cannot prove.

## Retrieving Compile Errors

When you want authoritative TypeScript compile diagnostics, run `run_otsc_check()`. It returns `stdout` / `stderr`, exit code, timeout state, and truncation info for the active project or an explicit script workspace path.

When a script change appears to succeed but the script doesn't behave correctly, call `get_script_logs()` to inspect recent runtime errors or verify your `console.log` output. The log surface now supports `query`, `min_level`, `tag`, `env`, and `after_time`, so you can narrow to compile fallout (`env=COMPILE`) or runtime issues (`env=RUNTIME`) without rereading the whole buffer.

## Required Observability for Game Scripts

For gameplay or multi-state scripts, do not leave runtime behavior implicit. Log the minimum set of events needed to prove the build works:

- key interactions that should advance the game, for example `[input] action=plant lane=2 col=3`
- state transitions, for example `[state] menu -> playing`
- critical guards, for example `[guard] place blocked lane=2 col=3 reason=occupied`
- score / timer / win-lose commits when they are part of acceptance
- audio trigger results, for example `[audio] action=play channel=bgm` or `[audio] missing channel=hit`

Use consistent prefixes so `get_script_logs(query="[state]", after_time=...)` or `query="[audio]"` can isolate the exact slice you need. Do not log every frame; log the moment a meaningful event happens.

### Audio Validation Rule

Preview screenshots prove UI. They do **not** prove whether audio really fired, and preview recordings may not be a reliable acceptance surface for sound. For BGM / SFX / voice cues, validate through script logs:

```typescript
private bgmFinishedLogged = false;

private playBgm(): void {
  if (!this.bgm) {
    console.log("[audio] missing channel=bgm");
    return;
  }
  console.log("[audio] action=play channel=bgm");
  this.bgm.play();
  this.bgmFinishedLogged = false;
}

private playHit(): void {
  if (!this.sfxHit) {
    console.log("[audio] missing channel=hit");
    return;
  }
  console.log("[audio] action=play channel=hit");
  this.sfxHit.play();
}

onUpdate(_dt: number): void {
  if (this.bgm && this.bgm.isFinished && !this.bgmFinishedLogged) {
    console.log("[audio] finished channel=bgm");
    this.bgmFinishedLogged = true;
  }
}
```

This gives `get_script_logs()` a deterministic surface for acceptance: did the trigger happen, was the channel bound, and did the clip reach a terminal state.

## Common Compile Errors and Fixes

### 1. `getParent()` does not exist on SceneObject
- **Wrong**: `this.getSceneObject().getParent()`
- **Correct**: `this.getSceneObject().parent` (it's a property getter, not a method)

### 2. Class-level APJS object initialization
- **Wrong**: `private colors: APJS.Color[] = [new APJS.Color(1,0,0,1)]`
- **Correct**: Initialize in `onStart()`:
```typescript
private colors: APJS.Color[] = [];
onStart(): void {
  this.colors = [new APJS.Color(1, 0, 0, 1)];
}
```

### 3. `for...of` on APJS arrays
Some APJS array types don't support `for...of` iteration.
- **Safer**: Use index-based loops:
```typescript
for (let i = 0; i < items.length; i++) {
  const item = items[i];
}
```

### 4. Spread operator on APJS arrays
- **Wrong**: `const copy = [...apjsArray]`
- **Correct**: Manual copy:
```typescript
const copy: number[] = [];
for (let i = 0; i < arr.length; i++) { copy.push(arr[i]); }
```

### 5. `null` assignment — strictNullChecks is ON
The APJS tsconfig has `"strict": true`. You **cannot** assign `null` to non-nullable types.
- **Wrong**: `@serializeProperty target: APJS.SceneObject = null;` → TS2322
- **Correct**: `@serializeProperty target: APJS.SceneObject;` (no initializer needed)
- **Wrong**: `this.someObject = null;` in reset logic → TS2322
- **Correct**: Use boolean flags or reset transforms, not null references

### 6. `mainMaterial` typed access
```typescript
const renderer = obj.getComponent("MeshRenderer") as APJS.MeshRenderer;
if (renderer && renderer.mainMaterial) {
  renderer.mainMaterial.setColor("_AlbedoColor", new APJS.Color(1, 0, 0, 1));
}
```

## Script Fix Retry Flow

When a script has compile errors or runtime bugs:

1. `run_otsc_check()` — read the current OTSC compile result and TS diagnostics
2. Identify the issue in the code
3. `Edit("Assets/<path>.ts", ...)` / `MultiEdit` / `apply_patch` — apply the fix to the live script (works for any patch size).
4. `run_otsc_check()` — verify the recompile succeeded
5. `get_script_logs()` — inspect runtime output or post-compile fallout if behavior still looks wrong
6. Common fixes: missing `f` suffix on math types (Vector3f not Vector3), wrong APJS class name, using `import` (not needed)

## Catching Transient Runtime State

`console.log` traces what code ran; screenshots show what's on screen. The gap — transient on-screen state (combo labels, particle bursts, mid-tween poses, "+10" popups, state-machine transition flashes) — needs `pause_preview` to capture deterministically. Recipes: `skills_root/general/PreviewInteraction/SKILL.md` Pattern 4 (single transient frame) and Pattern 2 (multi-step verification loop).

`pause_preview` is debugger-on-frame, not a substitute for `get_script_logs()`. Use logs to confirm the code path ran; use pause + screenshot to confirm what that code put on screen. For state-machine debugging where each step's outcome must be isolated, escalate to the **pause-inspect-act loop** detailed in `skills_root/general/PreviewInteraction/SKILL.md` Pattern 2.
