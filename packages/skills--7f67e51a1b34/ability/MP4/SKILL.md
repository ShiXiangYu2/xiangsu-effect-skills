---
name: MP4
description: MP4的使用 —  把 MP4 作为视频纹理绑定到 Image，并控制播放状态、结束事件和独立音轨同步。视频的播放控制器来自纹理本身。
---

# MP4 — Video Texture Playback

MP4 video plays through an **Image component's texture**, not a separate "Video" component. The Image's `texture` field accepts an `mp4Tex` resource; at runtime you call `image.texture.getControl()` to get a `Mp4TextureProvider` and drive playback from there.

> **MP4 has no embedded audio playback.** If the source video has sound, import the audio track as a separate `.mp3` and play it through an `AudioComponent` synced to the video — see `skills_root/ability/Audio/SKILL.md`.

## The one rule that's easy to miss

```typescript
// ❌ WRONG — Image.texture is a Texture, not the player.
img.texture.play();                            // not a method
APJS.EventManager.getObjectEmitter(img.texture).on(APJS.VideoEvent.Finished, ...);  // no such enum

// ✅ RIGHT — getControl() returns the Mp4TextureProvider that drives playback.
const mp4 = img.texture.getControl() as APJS.Mp4TextureProvider;
mp4.play();
APJS.EventManager.getObjectEmitter(img.texture).on(APJS.Mp4Event.PlayEnd, this.onEnd, this);
```

Notes on the split:
- **Control methods** live on the `Mp4TextureProvider` (`mp4.play/pause/resume/stop`).
- **Events** are emitted by the **texture resource** (`getObjectEmitter(img.texture)`), not the provider. You listen on the texture; you call methods on the provider.
- `Mp4TextureProvider` has **no `seek()` / `setCurrentTime()`**. `currentTime` is read-only. To restart from frame 0, call `mp4.stop()` then `mp4.play()` — `play()` restarts from the beginning.

## DSL Setup

```
// 1) Import the .mp4. edit_by_dsl.import_resource(...) produces a Texture resource of type mp4Tex
//    (rttiType: "Texture", JSClassName: "Mp4TextureProvider"). It also creates
//    a backing .video asset referenced from the mp4Tex.
edit_by_dsl.import_resource({path:"videos/intro.mp4"})              → Texture r=<introMp4Tex>

// 2) Create a 2D Image SceneObject to host the video. Use whatever 2D-Image
//    builtin your scene uses (e.g. "2D Image" / "Image"); the key is that the
//    resulting SceneObject has an Image component.
add_builtin_object(object_type="2D Image", name="IntroVideoScreen")
                                                       → SceneObject s=<screenObj>, Image c=<screenImg>

// 3) Wire the texture. Image.texture is a Texture reference — pass the mp4Tex GUID.
set_component(guid=<screenImg>, properties={texture: {guid: "<introMp4Tex>"}})

// 4) (Optional) Set loop count directly on the resource. -1 = infinite.
set_resource_properties(guid=<introMp4Tex>, properties={loopCount: 1})
```

`loopCount` on the resource is the **default** loop count at scene load. You can also set it from script at runtime via `mp4.loopCount = -1`.

> **Use `add_builtin_object` for the host Image, not a raw `MeshRenderer` + plane.** Video textures are designed to flow through the `Image` component path. If you don't see your existing 2D-Image builtin name, `query_knowledge(category="object", query="2D image")` will list it.

## Script Playback

`@serializeProperty` references resolve **after** `onStart()`. Don't grab `image.texture.getControl()` in `onStart()` — `image.texture` may be `null` for the first frame. Lazy-init in `onUpdate`.

```typescript
@component()
export class IntroPlayer extends APJS.BasicScriptComponent {
  // Always serialize the SceneObject, not the Image. Component-subclass
  // @serializeProperty fields silently revert to null — see skills_root/general/SerializeProperty.
  @serializeProperty videoScreenObj!: APJS.SceneObject;

  private image!: APJS.Image;
  private mp4!: APJS.Mp4TextureProvider;
  private mp4Ready: boolean = false;
  private onPlayEnd = (_e: APJS.IEvent) => {
    console.log("[Intro] PlayEnd");
    // ... advance game state here
  };

  onUpdate(_dt: number): void {
    if (this.mp4Ready) return;
    if (!this.videoScreenObj) return;

    const img = this.videoScreenObj.getComponent("Image") as APJS.Image;
    if (!img || !img.texture) return;            // texture not yet bound — try next tick

    this.image = img;
    this.mp4 = img.texture.getControl() as APJS.Mp4TextureProvider;

    // Listen for PlayEnd on the TEXTURE resource, not the provider.
    APJS.EventManager.getObjectEmitter(img.texture).on(
      APJS.Mp4Event.PlayEnd, this.onPlayEnd, this,
    );

    this.mp4.stop();   // freeze on frame 0 until something explicitly starts playback
    this.mp4Ready = true;
  }

  onDestroy(): void {
    if (this.mp4Ready && this.image && this.image.texture) {
      APJS.EventManager.getObjectEmitter(this.image.texture).off(
        APJS.Mp4Event.PlayEnd, this.onPlayEnd, this,
      );
    }
  }

  // Public control surface for other scripts.
  restart(): void { if (this.mp4Ready) this.mp4.play(); }   // play() restarts from start
  stop(): void    { if (this.mp4Ready) this.mp4.stop(); }   // freezes on frame 0
  pause(): void   { if (this.mp4Ready) this.mp4.pause(); }
  resume(): void  { if (this.mp4Ready) this.mp4.resume(); }
}
```

### Mp4TextureProvider — full surface

| Member | Type | Notes |
|---|---|---|
| `play()` | void | Starts from the beginning. Calling on an already-playing video restarts it. |
| `pause()` | void | Hold on current frame. Pair with `resume()`, not `play()` (which rewinds). |
| `resume()` | void | Continue a paused video from where it was. |
| `stop()` | void | Stop and reset to the initial frame. Use this as the "freeze on frame 0" idiom. |
| `loopCount` | `number` (get/set) | `-1` = infinite, `1` = play once, `n` = repeat n times. |
| `duration` | `number` (read-only) | Total length in seconds. |
| `currentTime` | `number` (read-only) | Current playback time in seconds. **No setter — you cannot seek.** |

### Mp4Event — full enum

`APJS.Mp4Event.*` values for `getObjectEmitter(texture).on(...)`:

| Event | Fires when |
|---|---|
| `PlayBegin` | Playback starts (after `play()` or auto-loop). |
| `PlayEnd` | Playback finishes a pass. With `loopCount > 1` / `-1` it fires once per loop end. |
| `Pause` | `pause()` was called. |
| `Resume` | `resume()` was called. |
| `Stop` | `stop()` was called. |
| `KeyFrameInSecond` | Fired once per second of playback (timer hook for keyframed gameplay). |

Use `Mp4Event.PlayEnd` for "this clip is done, advance the game". `KeyFrameInSecond` is useful for per-second sync points without polling `currentTime`.

## Sync with audio

MP4 textures play picture only — the audio track is dropped on import. If the clip has sound, import the audio separately and play it on an AudioComponent that you `play()` / `stop()` alongside the video.

```typescript
// In your onPlay handler, start both at once:
this.mp4.play();
this.bgAudio.play();         // AudioComponent on a sibling SceneObject

// And on PlayEnd, stop the audio too:
private onPlayEnd = (_e: APJS.IEvent) => {
  this.bgAudio.stop();
  this.state = STATE_NEXT;
};
```

Tight A/V sync (within a frame or two) is fine for narrative clips. For frame-accurate sync, fire AudioComponent `play()` from the `Mp4Event.PlayBegin` handler so the audio waits for the engine to actually begin the video, not for your `play()` call.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Calling `image.texture.play()` / `pause()` directly | Call `image.texture.getControl() as APJS.Mp4TextureProvider`, then play/pause on that provider. |
| Listening for `APJS.VideoEvent.Finished`, `MediaEvent.Ended`, `PlaybackEvent.*` | None of those exist. The enum is **`APJS.Mp4Event`** and the finish event is **`PlayEnd`**. |
| `mp4.seek(0)` / `mp4.setCurrentTime(0)` to rewind | Neither exists. Use `mp4.stop()` to freeze on frame 0, or just `mp4.play()` — `play()` always restarts from the beginning. |
| Adding a separate `VideoComponent` to the SceneObject | There is no `VideoComponent`. Video lives on the `Image` component through its `texture`. |
| Grabbing `getControl()` in `onStart()` | `image.texture` is null on the first frame. Lazy-init in `onUpdate` with an `mp4Ready` guard. |
| `getObjectEmitter(mp4Provider)` for the listener | Events emit from the **texture** resource (`img.texture`), not the provider. Provider is for method calls only. |
| Assuming audio plays with the video | MP4 picture only. Import the audio track separately and play it on an `AudioComponent`. |
| `@serializeProperty image: APJS.Image` | Component-subclass serialize fields silently revert to null. Serialize the host `SceneObject` and resolve `getComponent("Image")` at runtime — see `skills_root/general/SerializeProperty`. |

## VERIFICATION

- [ ] `image.texture` is bound to an `mp4Tex` resource (`rttiType: "Texture"`, `JSClassName: "Mp4TextureProvider"`).
- [ ] All control calls go through `image.texture.getControl() as APJS.Mp4TextureProvider`.
- [ ] All event subscriptions are on `getObjectEmitter(image.texture)` with `APJS.Mp4Event.*` values.
- [ ] No `seek()`, `setCurrentTime`, or `VideoEvent`/`MediaEvent` symbols anywhere in the script.
- [ ] Provider access is gated behind a `ready`-style flag set inside `onUpdate`, not `onStart`.
- [ ] If the clip needs sound, an `AudioComponent` is wired and played from the same `play()` (or `Mp4Event.PlayBegin`) call.
- [ ] `onDestroy` calls `off()` on the same texture/event/handler used in `on()`.
