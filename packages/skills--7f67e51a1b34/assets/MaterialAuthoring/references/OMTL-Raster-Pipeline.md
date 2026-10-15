# OMTL Raster Pipeline reference

Read this file before creating or structurally editing an OMTL document with a `Pipeline` header. A Pipeline material is still one Material asset, but it can run several raster steps through internal render textures.

## Mental model

| OMTL field           | Meaning                                                                                                                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `Pass`               | A shader program definition. A Pass may be reused by Steps.                                                                        |
| `Pipeline.Steps`     | Ordered executions of Pass programs. Array order is execution order.                                                               |
| `Pipeline.Resources` | Internal RenderTexture2D or RenderTextureCube targets passed between Steps. They are not project assets and have no resource GUID. |
| `Inputs`             | Texture edges entering one Step.                                                                                                   |
| `ColorOutputs`       | The destination written by one Step.                                                                                               |
| `Current`            | This frame's value. Its writer must be an earlier Step.                                                                            |
| `Previous`           | Last frame's value. The Resource must use `History: 1`.                                                                            |
| `Builtin: "Screen"`  | The single final output of the Pipeline.                                                                                           |
| `Pipeline.Display`   | Optional. The pass drawn on the object, which samples that output. Omitted, it is generated as a flat UV mapping.                  |

The editor expands this graph into ordinary Material passes and RenderTextures. The engine executes the flattened pass list; `OmtlPipelineSystem` updates dynamic ShaderToy uniforms and History bindings on device.

## Document shape

Pipeline mode is selected by the presence of the top-level `Pipeline` field:

```text
JSON header containing Pass[] and Pipeline
---ENDJSON

---BEGIN UIPROPERTY
...
---END UIPROPERTY

---BEGIN Common
optional shared source
---END Common

---BEGIN BufferA
source used by Pass.Ausl = BufferA
---END BufferA

---BEGIN Image
...
---END Image
```

Source blocks can appear in any order. Every `Pass.Ausl` and `Pass.SharedSources[]` name must match a block exactly.

## Pass

```json
{
  "Id": "ImageProgram",
  "Ausl": "Image",
  "SharedSources": ["Common"],
  "Profile": "ShaderToy",
  "FullScreenShading": "On"
}
```

`Id` must be unique. `Profile: "ShaderToy"` wraps `mainImage` or `mainCubemap` in the required AUSL vertex/fragment shell. An ordinary AUSL Pipeline Pass omits that adaptation and provides its own complete AUSL entry points.

## Resources

Relative 2D target:

```json
"BufferA": {
  "Kind": "RenderTexture2D",
  "Size": {"RelativeTo": "Output", "Scale": [1.0, 1.0]},
  "Format": "RGBA16F",
  "ColorSpace": "Linear",
  "Mipmaps": "None",
  "History": 1,
  "InitialColor": [0.0, 0.0, 0.0, 1.0]
}
```

Absolute Cubemap target:

```json
"GeneratedCube": {
  "Kind": "RenderTextureCube",
  "Size": {"Width": 128, "Height": 128},
  "Format": "RGBA8",
  "ColorSpace": "Linear",
  "Mipmaps": "None",
  "History": 0
}
```

Supported values:

| Field            | Values / constraints                                          |
| ---------------- | ------------------------------------------------------------- |
| `Kind`           | `RenderTexture2D`, `RenderTextureCube`                        |
| Relative `Scale` | Two values greater than 0 and at most 16                      |
| Absolute size    | Integer 1–16384; Cubemap width and height must match          |
| `Format`         | `RGBA8`, `RGBA16F`, `RGBA32F`                                 |
| `ColorSpace`     | `Linear`, `SRGB`; SRGB requires RGBA8                         |
| `Mipmaps`        | `None`, `Generate`; generated Cubemap mipmaps are unsupported |
| `History`        | `0` or `1`                                                    |
| `InitialColor`   | Four finite numeric components                                |

`History: 1` creates two internal textures. It does not create a project RenderTexture asset.

## Steps and outputs

```json
{
  "Id": "WriteBufferA",
  "Pass": "BufferAProgram",
  "ColorOutputs": [{"Slot": 0, "Resource": "BufferA"}]
}
```

Final output:

```json
{
  "Id": "Image",
  "Pass": "ImageProgram",
  "ColorOutputs": [{"Slot": 0, "Builtin": "Screen"}]
}
```

Current implementation requires exactly one ColorOutput per raster Step, one writer per Resource, and exactly one Screen writer in the Pipeline.

## Inputs

Read an earlier same-frame Resource:

```json
"iChannel0": {
  "Resource": "BufferA",
  "Frame": "Current"
}
```

Read the last frame:

```json
"iChannel0": {
  "Resource": "BufferA",
  "Frame": "Previous"
}
```

Read an editor-visible texture property:

```json
"iChannel1": {
  "Property": "_Background",
  "Sampler": {
    "Filter": "Linear",
    "MipFilter": "None",
    "WrapU": "Repeat",
    "WrapV": "Repeat",
    "VFlip": false
  }
}
```

Declare that Property in UIPROPERTY:

```text
_Background (Background, 2D) = "Textures/background.png"
_Environment (Environment, TextureCube) = "Textures/environment.hdr"
```

Each Input must select exactly one of `Property`, `Resource` or `Provider`. Provider is a reserved runtime seam; no general provider source ships in the current implementation. Do not use it unless a known host supplies that provider.

Sampler defaults are `Linear`, `None`, `Clamp`, `Clamp`, and no VFlip.

## Valid dataflow patterns

### Same-frame chain

```text
WriteA -> BufferA Current -> WriteB -> BufferB Current -> Image
```

The writer must appear earlier in `Steps`.

### Feedback

```text
BufferA Previous -> WriteA -> BufferA
BufferA Current -> Image
```

Set `BufferA.History` to `1`. A Step cannot read and write the same Resource as Current.

### Ping-pong and cycles

If Buffer A reads Buffer B before B has run this frame, A must read B as Previous. If B later reads A, B can read A as Current. Every Resource read as Previous needs History.

### Cubemap

A Cubemap Step writes one `RenderTextureCube`; a later Image Step samples it as a Resource. Internally it is stored as a six-face vertical atlas, but generated ShaderToy source exposes it as a cubemap sampler. Do not manually apply the atlas layout in ShaderToy code.

## ShaderToy builtins

`Profile: "ShaderToy"` supplies:

```text
iResolution, iTime, iTimeDelta, iFrameRate, iFrame
iMouse, iDate
iChannelTime[0..3], iChannelResolution[0..3]
iChannel0, iChannel1, iChannel2, iChannel3 when bound
```

`iResolution.xy` is the output size and `.z` is the pixel aspect ratio, which is 1 for every target a pipeline renders into. `iChannelTime` advances for internal Resource inputs and remains zero for static Property inputs. `iMouse` uses pixel coordinates and ShaderToy click-origin sign semantics.

## Pipeline.Display — customizing the surface pass

Steps render full-screen into offscreen targets. What the object actually draws is a separate pass the compiler appends, which samples the pipeline output and maps it flat over the mesh's UVs. That pass is the only one that sees the object's geometry and `u_MVP`, so it is where a pipeline can move vertices.

Declare `Pipeline.Display` to write it yourself. Omit it and the generated flat mapping is used, exactly as before.

```json
"Pipeline": {
  "Display": {
    "Ausl": "Display",
    "SharedSources": ["DisplayCommon"],
    "Cull": "None"
  },
  "Resources": {},
  "Steps": [...]
}
```

`Ausl` and `SharedSources` name source blocks, the same as a Pass. `Cull`, `DepthWriteEnable`, `DepthTestEnable`, `BlendMode` and `ZTest` override the pass's render state; nothing else in the pass is author-controlled.

The block holds a complete AUSL pass, not ShaderToy source — `Profile` is not configurable here. Sample the pipeline's result from `_OmtlPipelineOutput`:

```glsl
#pragma vs attributes varyings
    precision highp float;
    uniform highp mat4 u_MVP;
    uniform highp float iTime;
#pragma end
#pragma fs varyings targets
    precision highp float;
    uniform highp sampler2D _OmtlPipelineOutput;
#pragma end

void vertex()
{
    vUv = attTexcoord0;
    highp vec3 p = attPosition;
    p.y += sin(iTime * 2.0 + attPosition.x * 4.0) * 0.1;
    gl_Position = u_MVP * vec4(p, 1.0);
}

void fragment() { o_fragColor = texture(_OmtlPipelineOutput, vUv); }
```

The ShaderToy builtins below are fed to a Display too, in both stages, under their plain names. Declare every builtin used by that stage in its pragma block, as the example does for vertex-stage `iTime`. They describe the pipeline output it samples, not the object: `iResolution` is that texture's size, and the channel builtins stay at their defaults because a Display has no `Inputs`.

A Display that positions vertices itself and never reads `u_MVP` still gets the uniform and a guard that cannot fire injected into its vertex function — the Scene view's free camera culls any object whose material has a pass without `u_MVP` in its reflection.

## Structural editing checklist

After any native edit:

1. Preserve matching `Pass.Id`, `Step.Pass`, `Pass.Ausl` and source block names.
2. Keep Steps in dependency order.
3. Add History for every Previous read.
4. Keep exactly one Screen writer.
5. Run `get_material_status` through `edit_by_dsl` for the exact current file.
6. A compile failure stops that DSL batch; fix the returned diagnostics before binding or previewing.

Use `create_shadertoy_material` through `edit_by_dsl` for first creation of ShaderToy Profile content. Later edits use native text editing plus `get_material_status` through `edit_by_dsl`.

## Editing generated ShaderToy OMTL

The creation command does not own later edits. Generated identifiers are stable and readable: `Common`, `BufferA`, `BufferAProgram`, `WriteBufferA`, `GeneratedCube`, `ImageProgram` and `Image`.

| Change                             | Edit                                                          |
| ---------------------------------- | ------------------------------------------------------------- |
| Color, motion or procedural effect | `Image`, `Buffer*` or `Cubemap` source block                  |
| Shared helper                      | `Common` source block                                         |
| Channel source or sampling         | The matching Step `Inputs.iChannelN`                          |
| Feedback                           | Use `Frame: "Previous"` and set that Resource to `History: 1` |
| Intermediate size/precision        | `Pipeline.Resources`                                          |
| Add a Buffer                       | Add its Pass, source block, Resource and Step together        |
| How the result maps onto the mesh  | Add `Pipeline.Display` plus its source block                  |

Preserve the relationships in the structural checklist. External Texture2D and Cubemap channel sources are generated as UIPROPERTY texture fields so they can be changed after creation.
