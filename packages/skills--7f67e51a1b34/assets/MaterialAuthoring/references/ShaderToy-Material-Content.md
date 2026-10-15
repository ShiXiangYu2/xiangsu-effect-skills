# ShaderToy material creation

Run the `create_shadertoy_material` command through `edit_by_dsl` to create an OMTL Raster Pipeline material from ShaderToy-style source. The command creates and compiles one Material asset and never changes the scene. It does not overwrite by default; set `overwrite: true` only when intentionally replacing the exact material path, including retrying a failed creation with corrected content.

Do not use this command to edit an existing OMTL. Read the file, edit it natively, then run `get_material_status` through `edit_by_dsl`.

## Minimal Image material

```json
{
  "material_path": "Effects/Plasma.omtl",
  "content": {
    "image": {
      "code": "void mainImage(out vec4 color, in vec2 coord) { color = vec4(coord / iResolution.xy, 0.0, 1.0); }"
    }
  }
}
```

`material_path` is relative to `Assets/Materials`. The Image pass is required because every Pipeline needs one final Screen writer.

## Content fields

```text
content
  common?       shared GLSL prepended to every pass
  buffers[]?    ordered Buffer passes
  cubemap?      optional mainCubemap pass
  image         required final mainImage pass
```

Buffer example:

```json
{
  "id": "A",
  "code": "void mainImage(out vec4 color, in vec2 coord) { ... }",
  "channels": [],
  "output": {
    "size": {"mode": "relative", "scale": [1, 1]},
    "format": "RGBA16F",
    "color_space": "Linear",
    "mipmaps": false,
    "initial_color": [0, 0, 0, 1]
  }
}
```

Buffers execute in array order, followed by Cubemap and Image.

## Channel sources

Channel numbers are 0–3 and correspond to `iChannel0`–`iChannel3`.

Earlier Buffer:

```json
{"channel": 0, "source": {"type": "buffer", "buffer": "A"}}
```

Generated Cubemap:

```json
{"channel": 1, "source": {"type": "cubemap_buffer"}}
```

Project Texture2D:

```json
{"channel": 2, "source": {"type": "texture2d", "guid": "<texture-guid>"}}
```

Project Cubemap:

```json
{"channel": 3, "source": {"type": "texture_cube", "guid": "<cubemap-guid>"}}
```

Use `list_resources` for an existing project texture. For a local image file, first call `edit_by_dsl.import_resource({path:"..."})`, then pass the returned GUID here. Do not pass a filesystem path where the schema requires a GUID.

External Texture2D and Cubemap channels become UIPROPERTY texture fields on the generated material. They remain editable after creation through material resource properties; the tool does not reinterpret any `iChannelN` as a special host input.

Optional sampler:

```json
{
  "filter": "Linear",
  "mip_filter": "None",
  "wrap_u": "Repeat",
  "wrap_v": "Repeat",
  "v_flip": false
}
```

## Current, Previous and History

Do not express these OMTL fields in tool input. The tool derives them from execution order:

| Relationship                       | Generated OMTL            |
| ---------------------------------- | ------------------------- |
| Read an earlier Buffer             | `Current`                 |
| Read the same Buffer being written | `Previous` + `History: 1` |
| Read a later Buffer                | `Previous` + `History: 1` |
| Image reads any Buffer/Cubemap     | normally `Current`        |

## Multi-buffer feedback example

```json
{
  "material_path": "Effects/Feedback.omtl",
  "content": {
    "buffers": [
      {
        "id": "A",
        "code": "void mainImage(out vec4 c, in vec2 f) { vec2 uv=f/iResolution.xy; c=texture(iChannel0,uv)*0.98+vec4(0.01,0.0,0.0,1.0); }",
        "channels": [{"channel": 0, "source": {"type": "buffer", "buffer": "A"}}],
        "output": {"format": "RGBA16F", "initial_color": [0, 0, 0, 1]}
      }
    ],
    "image": {
      "code": "void mainImage(out vec4 c, in vec2 f) { c=texture(iChannel0,f/iResolution.xy); }",
      "channels": [{"channel": 0, "source": {"type": "buffer", "buffer": "A"}}]
    }
  }
}
```

## Cubemap example

Generated Cubemap size must be absolute and square. When `output.size` is omitted, the tool uses `256 x 256`.

```json
{
  "material_path": "Effects/DirectionCube.omtl",
  "content": {
    "cubemap": {
      "code": "void mainCubemap(out vec4 c, in vec2 f, in vec3 ro, in vec3 rd) { c=vec4(normalize(rd)*0.5+0.5,1.0); }",
      "output": {"size": {"mode": "absolute", "width": 128, "height": 128}}
    },
    "image": {
      "code": "void mainImage(out vec4 c, in vec2 f) { vec2 p=(2.0*f-iResolution.xy)/min(iResolution.x,iResolution.y); c=texture(iChannel0,normalize(vec3(p,1.0))); }",
      "channels": [{"channel": 0, "source": {"type": "cubemap_buffer"}}]
    }
  }
}
```

## Supported ShaderToy surface

Supported by the current implementation:

```text
Common, Image, ordered Buffer passes, Cubemap
mainImage, mainCubemap
iResolution, iTime, iTimeDelta, iFrameRate, iFrame
iMouse, iDate, iChannelTime, iChannelResolution
up to four Buffer/Texture2D/TextureCube channel inputs per pass
same-frame chains, feedback, History, sampler state and VFlip
relative/absolute resources, RGBA8/16F/32F, Linear/SRGB, Mipmap for 2D resources
```

Not currently supplied by the OMTL runtime:

```text
ShaderToy Sound passes, iSampleRate/audio channels
keyboard channels
video or live-camera channels without a dedicated Provider host
multiple color outputs from one raster Step
generated Cubemap mipmaps
```

The command returns `UNSUPPORTED_FEATURE` or another structured input issue instead of silently degrading these cases.

## Result handling

Continue only when the result includes:

```json
{"success": true, "state": "succeeded", "guid": "...", "source_hash": "...", "attempt_id": "..."}
```

Compilation failure interrupts the `edit_by_dsl` batch and returns the authoritative diagnostics for the generated file. A timeout is also an error. The command does not bind the returned GUID to a component.

A successful creation result already covers compilation of the exact generated content. Do not run `get_material_status` again immediately. Use it only after a later native edit of the `.omtl` file.

If creation writes the file but compilation fails, correct the structured `content` and call `create_shadertoy_material` again with the same `material_path` and `overwrite: true`. This reruns conversion and compilation as one operation. Native editing plus `get_material_status` remains appropriate for later manual OMTL edits, but is not required merely to recover from a failed first creation.

## Editing the created material

Generated names are deterministic:

```text
Common
BufferA / BufferAProgram / WriteBufferA
Cubemap / CubemapProgram / WriteCubemap / GeneratedCube
Image / ImageProgram / Image
```

For source-only changes, edit the matching source block. For Buffer, channel, History or resource changes, read `OMTL-Raster-Pipeline.md` and preserve the Pass/Step/Resource relationships. After every native edit, run `get_material_status` through `edit_by_dsl`.

To place the Pipeline result on geometry that must visibly deform, add `Pipeline.Display` and a complete AUSL Display source block after creation. `create_shadertoy_material` intentionally keeps this geometry-specific pass out of its input schema. The Display samples `_OmtlPipelineOutput`, while its `vertex()` controls the mesh shape; see `OMTL-Raster-Pipeline.md`.
