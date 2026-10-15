---
name: Audio
description: 音频能力，涵盖音频组件的播放模式（Once、Loop、Infinity）、BGM/SFX 模式，音量控制和 声音检测能力（节拍、音量、音高、声音频谱、关键词检测等）。
---

# Audio — Sound Playback

Patterns for background music, sound effects, and audio detection.

> **Acceptance rule:** treat script logs as the source of truth for whether audio actually triggered. Preview screenshot / MP4 paths are for visual proof, not reliable audio acceptance. For BGM / SFX, log play / stop / missing-binding / finished events and verify them with `get_script_logs(after_time=...)`.

## AudioComponent (Sound)

Play background music and sound effects. Audio files must be imported via `edit_by_dsl` with command_type `import_resource`.

### DSL Setup

1. `edit_by_dsl({commands:[{command_type:"import_resource", params:{path:"path/to/sound.mp3"}}]})` — imports the file as an `AudioAsset` resource. **Returns an AudioAsset only — does NOT auto-create a host SceneObject** (verified `interactive/music-rhythm` E1; the prior copy of this skill that said otherwise was wrong).
2. Create a host SceneObject for the AudioComponent. Two options:
   - `add_builtin_object(object_type="Audio Player", name="<MyPlayer>")` — auto-creates `Transform` + `AudioComponent` (with a placeholder `audioRef`)
   - `add_component(scene_object="<existing>", type="AudioComponent")` — attach AudioComponent to any existing SceneObject
3. `set_component(<audioComponentGuid>, properties={audioRef:{guid:"<importedAudioAssetGuid>", type:"AudioAsset"}, playMode:"Infinity", volume:50, autoPlay:true})` — bind the imported asset and configure playback.

### Play Mode (DSL)

AudioComponent has a `playMode` property that controls looping behavior:

| playMode | Behavior |
|----------|----------|
| `"Once"` | Play once and stop (default) |
| `"Loop"` | Repeat `loopCount` times |
| `"Infinity"` | Loop forever |

Set via DSL `set_component`:

```
// BGM: loop forever
set_component(guid=bgmAudioComponent, properties={playMode: "Infinity", volume: 50, autoPlay: true})

// SFX: play once (default)
set_component(guid=sfxAudioComponent, properties={playMode: "Once", volume: 100})

// Loop 3 times
set_component(guid=audioComponent, properties={playMode: "Loop", loopCount: 3})
```

### Script Playback

```typescript
const audio = this.getSceneObject().getComponent("AudioComponent") as APJS.AudioComponent;

// Play / Pause / Resume / Stop
audio.play();
audio.pause();
audio.resume();
audio.stop();

// Volume (0-100)
audio.volume = 80;

// Loop count (positive integers, used when playMode is "Loop")
audio.loopCount = 3; // loop 3 times

// Check state
if (audio.isFinished) {
  console.log("Audio done, duration was: " + audio.duration);
}
```

### BGM + SFX Pattern

For BGM, set `playMode: "Infinity"` via DSL on the AudioComponent. In scripts, just call `play()`.

**DSL setup:**
```
// 1) Import the audio files (returns AudioAsset resources, not host objects).
edit_by_dsl(import_resource path="sounds/bgm.mp3")          → AudioAsset r=<bgmAsset>
edit_by_dsl(import_resource path="sounds/hit.mp3")          → AudioAsset r=<sfxAsset>

// 2) Create the host SceneObjects (Audio Player builtin auto-creates an AudioComponent).
add_builtin_object(object_type="Audio Player", name="BgmPlayer")  → SceneObject s=<bgmObj>, AudioComponent c=<bgmAC>
add_builtin_object(object_type="Audio Player", name="SfxPlayer")  → SceneObject s=<sfxObj>, AudioComponent c=<sfxAC>

// 3) Wire each AudioComponent to its AudioAsset and set play behavior.
set_component(guid=<bgmAC>, properties={audioRef:{guid:<bgmAsset>, type:"AudioAsset"}, playMode:"Infinity", volume:50, autoPlay:true})
set_component(guid=<sfxAC>, properties={audioRef:{guid:<sfxAsset>, type:"AudioAsset"}, playMode:"Once",     volume:100})
```

**Script:**
```typescript
@component()
export class AudioManager extends APJS.BasicScriptComponent {
  @serializeProperty
  bgmObject!: APJS.SceneObject;
  @serializeProperty
  sfxHitObject!: APJS.SceneObject;

  private bgm!: APJS.AudioComponent;
  private sfxHit!: APJS.AudioComponent;
  private initialized = false;

  onUpdate(dt: number): void {
    if (!this.initialized && this.bgmObject) {
      this.bgm = this.bgmObject.getComponent("AudioComponent") as APJS.AudioComponent;
      this.sfxHit = this.sfxHitObject.getComponent("AudioComponent") as APJS.AudioComponent;
      if (!this.bgm) return;

      // Start BGM (playMode already set to "Infinity" via DSL)
      this.bgm.play();
      this.initialized = true;
    }
  }

  playHitSound(): void {
    // play() alone restarts the sample. Do NOT call stop() first — see
    // the rapid-fire rule below.
    console.log("[audio] action=play channel=hit");
    this.sfxHit.play();
  }
}
```

If audio is part of the acceptance path, add the same style of log around BGM start / stop and any missing-binding guard:

```typescript
if (!this.bgm) {
  console.log("[audio] missing channel=bgm");
  return;
}
console.log("[audio] action=play channel=bgm");
this.bgm.play();
```

## Rapid-fire SFX (coin pickups, taps, hits): `play()` alone — never `stop()`-then-`play()`

For short SFX that can retrigger multiple times per second (coin collect, click, hit, spark), **call `play()` alone**. `play()` on an already-playing AudioComponent restarts the sample from the beginning — which is exactly what you want.

Do NOT `stop()` then `play()` in the same frame. The engine collapses the queued stop-then-play pair into "do nothing" for that frame, and the sound never fires. This makes a row of rapid coin pickups sound like only the first one played.

```typescript
// ✅ Correct — play() restarts the sample cleanly on every hit
private onCoinCollected(): void {
  this.coinAudio.play();
}

// ❌ Wrong — rapid consecutive calls get silently collapsed
private onCoinCollected(): void {
  this.coinAudio.stop();
  this.coinAudio.play();  // never actually plays on rapid retriggers
}
```

For BGM or long one-shots where you genuinely want to abort the previous playback before starting a new track, put the `stop()` and `play()` in **different frames** (e.g. call `stop()` on a state-change event, then `play()` on the next `onUpdate` tick).

## Audio Detection (live signal analysis)

The `APJS.AudioDetectionModule` namespace exposes seven real-time analyzers that read an audio stream. Used for music-rhythm tap games, clap/shout detection, sing-on-pitch challenges, and keyword-triggered FX. This section records reusable API shape only. Detection-heavy flows such as beat / pitch / keyword analysis still need host- and build-specific validation before being treated as default guidance.

### Detector types

`APJS.AudioDetectionType` enum (declared in `AudioComponent.d.ts`):

| Enum | `getResult()` returns | Use for |
|---|---|---|
| `Pitch` (0) | number — Hz, range [40, 650] | sing-on-pitch challenges, voice-controlled instruments |
| `Beat` (1) | number — 1/2/3/4 cycling for 4/4 (or 1/2/3 for 3/4); -1 between beats | tap-on-beat scoring, beat-driven note spawners |
| `Onset` (2) | number — incrementing index per detected onset (threshold-driven) | continuous-signal alternative to Beat (no 4/4 quantization), good for percussive cues |
| `Spectrum` (3) | number[] — 8 frequency bands, magnitudes 0–255 | EQ-style visualizers, frequency-bucket reactive VFX |
| `Volume` (4) | number — amplitude, range [0, 1] | clap/shout games, loudness-driven combo multiplier |
| `SoundEvent` (5) | SoundEventResult[] — `{type, similarity}` | trigger FX on whistle / cough / clap / specific sound classes |
| `Keyword` (6) | event-driven via `IEventEmitter` (NOT polled) — fires `KeywordHit` / `KeywordMiss` events with the matched word(s) | voice-command effects ("hello", "stop", custom phrase list) |

### Audio source types

`APJS.AudioSourceType` enum (declared in `APJS.d.ts:497`):

| Enum | Source | Notes |
|---|---|---|
| `None` (0) | (placeholder) | Don't use directly |
| `Microphone` (1) | device microphone | On-device only; preview availability should be re-validated on the current build. Use `setDetectorSource(Microphone, null)`. |
| `Music` (2) | the device's currently-playing music source | Reads the device's current music source when that host path is available. Treat preview behavior as branch-specific and re-validate before relying on it. Use `setDetectorSource(Music, null)`. |
| `ExternalFile` (3) | a bundled `AudioComponent`'s clip | Pass the AudioComponent reference: `setDetectorSource(ExternalFile, audioComponent)`. Re-verify the exact behavior on the current build when detection is central to the task. |

### BeatDetector lifecycle (verified)

```typescript
// 1. Build the detector in onInit. Calling builder.build() outside onInit returns null.
onInit(): void {
  if (!this.audio) return;  // pre-condition: AudioComponent ref is bound
  const builder = APJS.AudioDetectionModule
    .getOrCreateAudioDetectionBuilder(APJS.AudioDetectionType.Beat) as APJS.BeatDetectorBuilder | null;
  if (!builder) return;
  builder.setDetectorSource(APJS.AudioSourceType.ExternalFile, this.audio);
  this.detector = builder.build();
}

// 2. Poll BeatDetector.getResult() each frame in onUpdate.
onUpdate(dt: number): void {
  if (!this.detector) return;
  const result = this.detector.getResult();
  if (result !== this.lastResult && result > 0) {
    // new beat detected
    this.handleBeat(result);
  }
  this.lastResult = result;
}
```

### Detector-specific result handling

All detector builders must be created with `APJS.AudioDetectionModule.getOrCreateAudioDetectionBuilder(...)`, and `builder.build()` must run in `onInit()`. Do **not** copy the Beat-specific `result > 0` polling logic blindly:

- `Beat`, `Onset`, `Pitch`, `Volume`: numeric `getResult()` values; pick a threshold/window that matches the detector.
- `Spectrum`: `getResult()` returns a `number[]`; iterate bands or derive a band aggregate.
- `SoundEvent`: when checking for a known target, prefer `getSimilarityByType(APJS.SoundEventType.X)`. It returns that target's current-frame similarity directly. Results are trigger-like and can be absent in adjacent frames, so accept one qualifying result instead of requiring a sustained duration.
- `Keyword`: event-driven, not polled; set `targetKeywords` and listen on `keywordDetector.eventEmitter` for `KeywordHit` / `KeywordMiss`.

#### Volume value bands

For human voice detected from microphone input, use these evaluated reference targets when turning the normalized `VolumeDetector.getResult()` value into user-facing loudness bands:

| Band | Target value |
|---|---|
| `SOFT` | `0.05` |
| `MEDIUM` | `0.10` |
| `LOUD` | `0.15` |
| `VERY LOUD` | `0.20` |

These microphone voice values are much lower than the theoretical maximum of `1`. Do not use thresholds such as `0.5` for ordinary microphone voice interactions. Other source types or non-speech audio may need separately calibrated thresholds.

#### SoundEvent `getSimilarityByType` usage

`getSimilarityByType(type)` accepts an `APJS.SoundEventType` member and returns the current frame's similarity for that target:

- `[0, 1]`: a valid result; higher means a stronger match.
- `0`: the detector produced a frame, but the target type was not predicted.
- `-1`: the detector is disabled, no extractor result is available, or the requested type is invalid.

Sound-event classification is strict, especially when a person imitates an animal sound. For that scenario, treat a value greater than `0.01` as a valid match. Detection is **trigger-like**, not a continuous state: a qualifying value may appear in one frame and be absent in following frames. Latch the first qualifying result; do not require the value to remain above the threshold for a duration or for consecutive frames.

```typescript
private catDetected = false;

onUpdate(_dt: number): void {
  if (!this.soundEventDetector || this.catDetected) {
    return;
  }

  const similarity = this.soundEventDetector.getSimilarityByType(
    APJS.SoundEventType.Cat,
  );
  if (similarity > 0.01) {
    this.catDetected = true;
    this.handleCatSound();
  }
}
```

**Note on the namespace function name** — the API doc string on the seven `*Detector` classes in `APJS.d.ts` mistakenly says `APJS.AudioDetectionModule.getAudioDetectionBuilder(...)`. The actual exported name (declared in `AudioComponent.d.ts:85`) is **`getOrCreateAudioDetectionBuilder`** with the `getOrCreate` prefix. Calls using the JSDoc'd name fail TypeScript compilation with `Property 'getAudioDetectionBuilder' does not exist on type 'typeof AudioDetectionModule'`. (Tracked as `interactive/music-rhythm` G13.)

### Worked example — tap-in-window scoring (BeatDetector + Touch)

See `context.workspace.APJS/examples/beat_tap_scoring.json`. This example is BeatDetector-specific: maintain a `pendingBeats: Array<{time, beat, judged}>` queue, push to it on each new `getResult() > 0`, and on every `Touch.Began` look up the closest unjudged beat in window. Inside `±0.15 s` → PERFECT (+100); inside `±0.30 s` → GOOD (+50); outside or no candidate → MISS-tap (combo reset). Each frame, also auto-MISS any unjudged beat where the window has fully closed.

### Loop-wrap caveat (G14)

When the source AudioComponent's clip restarts under `playMode: "Infinity"`, `BeatDetector` momentarily desyncs — verified in `interactive/music-rhythm` E2 as a single `~1.88 s` gap between consecutive beat reports right after the clip wrap (vs the steady-state `~0.46 s`). For tap-in-window scoring this means the player gets ~1 s of "free pass" each loop. Mitigations: (a) suppress scoring for ~1 s after each `audio.duration` boundary, or (b) use `OnsetDetector` (continuous threshold-driven, may not have the same gap).

## Rules

1. AudioComponent `volume` range is 0-100 (not 0-1)
2. Use `playMode: "Infinity"` via DSL for BGM infinite loop — do NOT use `loopCount = -1`
3. `loopCount` only applies when `playMode` is `"Loop"` — it must be a positive integer (range 1-99999999)
4. For rapid-fire SFX, call `play()` alone — never `stop()`-then-`play()` in the same frame (engine collapses the pair; see the rapid-fire section above).
5. For BGM, configure `playMode` and `volume` via DSL `set_component`, then just `play()` in scripts
6. **`edit_by_dsl.import_resource(...)` returns an AudioAsset only** — it does NOT create a host SceneObject. Always pair with `add_builtin_object("Audio Player", ...)` (or `add_component(..., "AudioComponent")` on an existing object), then `set_component(audioRef={guid, type:"AudioAsset"})` to wire them.
7. **Audio Detection** — always build the detector in `onInit` (not `onStart` or constructor), use `getOrCreateAudioDetectionBuilder` (not `getAudioDetectionBuilder`), and prefer `AudioSourceType.ExternalFile` for in-effect BGM analysis. BeatDetector + ExternalFile, Volume value bands, and SoundEvent acceptance behavior are verified; Pitch / Onset / Spectrum / Keyword remain ⚠️ until live-tested.
