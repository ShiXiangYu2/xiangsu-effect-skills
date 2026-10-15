---
name: Lighting
description: 灯光 — 为 3D 场景选择和布置方向光、点光、聚光灯与环境光，并通过脚本处理运行时灯光切换和预览调光等。
---

# Lighting

Patterns for lighting 3D content. APJS exposes four light types as components,
each created by adding a corresponding builtin object. The cheapest way to
"swap lighting" at runtime is to toggle the SceneObjects holding the lights
on and off — disabling a SceneObject also disables its components, so the
light stops contributing to the scene.

## Light type tradeoffs

| Type | Object_type | Position | Aim | Use for |
|------|-------------|----------|-----|---------|
| `DirectionalLight` | `"Directional Light"` | irrelevant | yes (Transform euler) | Sun/key light. Parallel rays — no falloff. |
| `PointLight` | `"Point Light"` | yes | no (omnidirectional) | Soft fill. Falls off with distance. |
| `SpotLight` | `"Spot Light"` | yes | yes (Transform euler) | Rim light, focused beam. Cone-shaped. |
| `EnvironmentLight` | `"Environment Light"` | irrelevant | irrelevant | Global ambient wash. Always-on baseline. |

> A fresh project comes with an auto-created `Directional Light` + `Environment Light`. To use a custom lighting rig, set `visible: false` on the auto-created Directional Light (don't delete it — the engine relies on it being present). Keep the Environment Light enabled across most setups so unlit areas still read against the camera-feed background.

## Three-point lighting setup

The classic portrait rig — drop a key, fill, and back light around a subject at the origin:

```
add_builtin_object(object_type="Directional Light", name="KeyLight")
  Transform.localPosition = (8, 6, 8)            // front-right
  Transform.localEulerAngles = (-25, 35, 0)      // pitched down 25°, yawed 35°

add_builtin_object(object_type="Point Light", name="FillLight")
  Transform.localPosition = (-6, 1, 4)           // camera-left, near subject height

add_builtin_object(object_type="Spot Light", name="BackLight")
  Transform.localPosition = (0, 4, -6)           // behind, slightly above
  Transform.localEulerAngles = (30, 180, 0)      // rotated to aim at subject from behind
```

This produces a recognizable Classic 3-Point look: the directional key
defines form, the soft point fill lifts the shadow side, and the spot
behind the subject creates a rim edge that separates it from the
background.

## Runtime light toggle (the cheapest "swap")

To cycle through lighting setups without recreating components, toggle each
light SceneObject's enabled-in-hierarchy flag. This disables the SceneObject
**and** all its components, including the light itself, so each toggle stops
the engine from doing the lighting work for that source.

```typescript
@component()
export class LightingDirector extends APJS.BasicScriptComponent {
  @serializeProperty keyLight!: APJS.SceneObject;
  @serializeProperty fillLight!: APJS.SceneObject;
  @serializeProperty backLight!: APJS.SceneObject;

  // Each setup is a 3-bit pattern over [key, fill, back]: true = on, false = off.
  private static readonly SETUPS = [
    { name: "Key only",        key: true,  fill: false, back: false },
    { name: "Classic 3-Point", key: true,  fill: true,  back: true  },
    { name: "Soft Point fill", key: false, fill: true,  back: false },
    { name: "Rim only",        key: false, fill: false, back: true  },
  ];

  private cycleIndex = 0;

  apply(): void {
    const s = LightingDirector.SETUPS[this.cycleIndex];
    this.keyLight.setEnabledInHierarchy(s.key);
    this.fillLight.setEnabledInHierarchy(s.fill);
    this.backLight.setEnabledInHierarchy(s.back);
  }

  advance(): void {
    this.cycleIndex = (this.cycleIndex + 1) % LightingDirector.SETUPS.length;
    this.apply();
  }
}
```

> Why `setEnabledInHierarchy(false)` over `light.enabled = false`: the SceneObject method updates effective hierarchy visibility and descendant lifecycle notifications without rewriting descendants' local flags. It's also stable across Lighting subclasses — you don't need to know whether the SceneObject carries `DirectionalLight`, `PointLight`, or `SpotLight`.

## Wiring lights to scripts

Lights are valid `@serializeProperty SceneObject` targets. Wire each light's
SceneObject (not its component) so the script can call
`setEnabledInHierarchy()` directly without first looking up the Light
component.

```ts
@serializeProperty keyLight!: APJS.SceneObject;     // a Directional / Point / Spot SceneObject
```

Storing each Light as `@serializeProperty <ComponentSubclass>` (e.g.
`APJS.DirectionalLight`) does NOT persist — Component-subclass serialization
silently reverts. Use `SceneObject` and look up the component at runtime
only if you need to mutate component-level properties (intensity, color,
range).

## Matching a setup to camera framing

Lights aimed at the world origin produce the cleanest framing when the
subject sits at the origin. If you move the subject, also reposition the
lights — they don't track. For follow-the-subject lighting, parent the
lights under the subject's Transform.

A rough subject-light distance budget:

- **Directional** — ignored, set the angle and forget the position.
- **Point** — distance ~6–10 units works for a ~3-unit subject. Closer = harsher highlight.
- **Spot** — keep the cone wide enough to land on the subject; ~6 units back is a good starting point.

## Common mistakes

1. **Forgetting Environment Light** — disabling all key/fill/back lights *and* the environment leaves a near-black frame. Keep `EnvironmentLight` enabled across most setups so unlit areas still register.
2. **Auto-created Directional Light competing** — a fresh project's auto Directional Light is at `(-30, 20, -20)` with `localEulerAngles=(338, 0, 0)` (pitched up). Leaving it enabled while your custom lights are also active produces a muddier look. Set `visible: false` on the auto light when you want the custom rig to dominate.
3. **Tiny subject vs. far camera** — at default Camera z=40, a subject at origin scale 1 is small. Pull the Camera to z=14 or scale the subject up before judging whether your lighting reads correctly.
4. **Multiple Cameras** — adding a sphere (or any primitive) to a scene without a camera auto-creates a Camera. If you already had a Camera, you now have two competing renders. Always check `get_scene` after first object creation and delete duplicates.

## Rules

1. Use `add_builtin_object` to create lights — never build them via raw component composition.
2. `setEnabledInHierarchy(true|false)` on the light's SceneObject is the canonical runtime on/off toggle.
3. Wire lights as `@serializeProperty SceneObject`, not as component subclasses.
4. Keep `EnvironmentLight` enabled in setups that disable all directional contributions, or the frame goes near-black.
5. The auto-created Directional Light should be hidden (`visible: false`) when you author a custom rig.
