# Recipe — Import a generic fullscreen GLSL shader as a legacy PostProcess effect

> Loaded on demand from `skills_root/assets/MaterialAuthoring/SKILL.md`. Use this for a generic single-pass `void main()` fragment shader that needs the legacy PostProcess shell. ShaderToy `mainImage`, Buffer, feedback or Cubemap content must use `create_shadertoy_material` and `references/ShaderToy-Material-Content.md` instead.

## When this applies

A **single-pass fullscreen fragment shader** in the generic `fragment_main` dialect is the intended path:

| Dialect         | Entry point                          | Builtins it expects                                                                                         |
| --------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `fragment_main` | `void main()` writing `gl_FragColor` | `time` / `u_time` / `iGlobalTime`, `resolution` / `u_resolution`, `mouse` / `u_mouse`, declared as uniforms |

The implementation still accepts a legacy single-pass `mainImage` input for compatibility, but new ShaderToy authoring must use `create_shadertoy_material` so native builtins and Raster Pipeline features remain available.

Out of scope — the command rejects with the reason: a **Buffer A–D** tab, `iChannel0` used as a buffer (feedback), `iChannel1-3`, cubemap, or audio (`iSampleRate`). Multi-buffer/feedback is the hard, deferred case; e.g. shaders whose Image tab is just `texture(iChannel0, uv)` where iChannel0 = Buffer A.

**HLSL is not GLSL.** `float4`/`lerp`/`tex2D`/`SV_Target` sources are a different language — the transplant assumes the body is already valid GLSL ES 3.0. Translate to GLSL first, then import.

## Why a dedicated path (vs. hand-writing AUSL)

The scaffolding is the error-prone part. `import_glsl` transplants the shader body into the **validated PostProcess skeleton** and does the deterministic remaps, so complexity in the shader _body_ doesn't raise the failure rate. You are far better at plain GLSL than at AUSL's pragma/precision quirks — let the converter own the scaffolding.

What the converter does automatically:

- Wraps the body in the fullscreen PostProcess OMTL skeleton
- `void main()` + `gl_FragColor` → the internal `mainImage` form (for the `fragment_main` dialect)
- `iResolution` ← `u_ScreenParams`; `iTime` ← a `_Time` uniform driven by a time-bridge script
- Dialect uniforms (`time`, `resolution`, `mouse`, `u_`-prefixed, `iGlobalTime`) are re-declared as globals under **their original names and types** and fed from the same engine sources — so a `vec2 resolution` stays a vec2 and the body needs no edits
- `fragCoord = v_uv * iResolution` with **no Y-flip** — the engine's fullscreen `v_uv` is already bottom-left origin, matching what these shaders assume. (Do not "fix" this by adding `1.0 - v_uv.y`: that was the original assumption and it rendered every import upside down. Verified with a `fragCoord.y` gradient probe in the live preview.)
- Normalizations: strips `/* block comments */`, `texture2D(`→`texture(`, `gl_FragCoord`→`fragCoord`
- Emits a time-bridge script (with a `baseTime` knob) when the shader uses time
- Warns (non-blocking) when the shader looks heavy (nested loops / raymarch) — desktop preview is fine, mobile may not be

Detection of the dialect uniforms keys off the **uniform declaration**, not bare identifier use: `time` is a very common local variable name, so a shader that merely has a local `float time` is not treated as animated.

## Flow

### 1. Create the material

```json
{"command_type": "import_glsl", "params": {"glsl": "<the full shader source>", "material_name": "Effects/MyImport.omtl"}}
```

Returns `{ guid, compiled, dialect, time_bridge_needed, bridge_script?, perf_warnings? }`.
On reject: `{ error, reasons: [...] }`.

> **Trust the preview, not `compiled`.** `compiled:false` with **no** `compile_error` is a false negative (the importer log poll didn't confirm, but the shader is fine). The authoritative signals are `compile_error` (if present → real AUSL error, fix it) and the rendered preview.

### 2. Bind to the camera's PostProcess

```json
[
  {
    "command_type": "add_component",
    "params": {"scene_object_guid": "<camera-guid>", "component_type": "PostProcess"},
    "alias": "pp"
  },
  {
    "command_type": "configure_post_process_custom",
    "params": {"guid": {"$ref": "pp"}, "material_guid": "<material-guid>"}
  }
]
```

### 3. Animate (only if `time_bridge_needed`)

Add the returned `bridge_script`, attach it to the camera, then **bind its `mat` property to the material in a separate `edit_by_dsl` call** (script refs need explicit `type`, and wiring must follow compilation):

```json
[
  {"command_type": "add_script", "params": {"script_name": "GlslTimeBridge", "code": "<bridge_script>"}},
  {
    "command_type": "add_component",
    "params": {"scene_object_guid": "<camera-guid>", "component_type": "GlslTimeBridge"},
    "alias": "bridge"
  }
]
```

then, in the next batch:

```json
{
  "command_type": "set_component",
  "params": {"guid": "<bridge-component-guid>", "properties": {"mat": {"guid": "<material-guid>", "type": "Material"}}}
}
```

Set `baseTime` on the bridge to start the shader partway into its timeline — many shaders look blank at t≈0 and only develop structure later (e.g. concentric ripples appear at large `iTime`).

## Verification & known gotchas

- **Switching a PostProcess material:** `capture_preview` runs `reset_preview`, which **reverts the live custom-material binding to the previously-bound material**. To _switch_ materials and confirm the new one, `configure_post_process_custom` then screenshot the **live** preview (`interact_by_dsl` → `screenshot`, no reset). Use `capture_preview` for a first clean render; re-apply the binding after any reset.
- **Component guids rotate on reset.** `reset_preview` reassigns component guids (PostProcess, script). Re-query `get_scene` after a reset before binding by guid. Material _asset_ guids are stable.
- **Aspect ratio.** These shaders are usually authored on a landscape 16:9 canvas; 像塑相机 is portrait 9:16. A shader normalized by `iResolution.y` or `min(res.x,res.y)` reframes accordingly — the composition may sit differently or crop outer detail. This is expected, not a conversion bug.
- **Heavy shaders.** Raymarch/volumetric imports (many nested loops per pixel) render in desktop preview but may miss the mobile frame budget — heed the `perf_warnings` and verify on device.

## iChannel0 texture input

A shader that samples `iChannel0` (as a static texture) is supported: the converter renames `iChannel0`→`_Channel0`, emits a Defs-guarded sampler (`Channel0` macro + `#pragma shader_feature` + `#ifdef`), and defaults it to the placeholder texture. To use a real image, set the material's `_iChannel0` after import:

```json
{
  "command_type": "set_resource_properties",
  "params": {"guid": "<material-guid>", "properties": {"_Channel0": {"guid": "<texture-guid>"}}}
}
```

`iChannelResolution[0..3]` is provided (all set to the screen resolution). Note: this treats `iChannel0` as a _texture_; a shader that expects `iChannel0` to be **Buffer A** (feedback) is the multi-buffer case and is out of scope.

## Scope boundary (v1)

Supported: single-pass fullscreen, `iResolution`/`iTime`/`iFrame`, one `iChannel0` static texture, `iMouse` (touch-driven — the input bridge feeds `interact_by_dsl` touch events into `_iMouse`).
Rejected: `iChannel1-3`, cubemap, audio (`iSampleRate`).
Deferred (v2+): multi-buffer (Buffer A–D) feedback, `iChannel` = live camera, cubemap/audio/video inputs, live `iMouse`/keyboard.
