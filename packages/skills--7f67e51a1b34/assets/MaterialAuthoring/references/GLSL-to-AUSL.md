# Reference — Converting GLSL to AUSL

> Loaded on demand from `skills_root/assets/MaterialAuthoring/SKILL.md`. Use this when you have GLSL in hand — pasted by the user, copied from a shader site, or written by you because plain GLSL is easier to reason about than AUSL — and you need it running as 像素材质.

## The one thing to understand first

**AUSL is GLSL ES 3.0.** The per-pixel math you write in GLSL is already valid AUSL — `mix`, `smoothstep`, `fract`, noise functions, SDF loops, matrix math, all of it transfers unchanged. What differs is only the **shell**: how stages are declared, where uniforms live, what the entry points are called, and how the fragment result gets out.

So the reliable way to author a shader is: **write or take plain GLSL for the body, then drop it into a validated shell.** Do not try to write AUSL from scratch — the failure rate is in the shell, not the math, and the shells are already solved:

| Target                                                                                                 | Validated shell to copy                                                              | When                                                                                                            |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **Fullscreen / screen-space** — the effect processes the camera image or draws across the whole screen | `references/PostProcess-CustomMaterial-Reference.md` → "Full validated OMTL example" | Source GLSL computes a color from a screen coordinate, samples the previous frame, or has no notion of geometry |
| **Mesh material** — the effect shades an object's surface                                              | `SKILL.md` → "Safe starter template (textured Unlit)"                                | Source GLSL uses UVs, normals, or world position of a model; user asks to make an object look a certain way     |

Copy the **whole** shell, keep its pragma layout intact, and edit only the UIPROPERTY block, the stage uniform blocks, and the `fragment()` body.

**Fullscreen shaders use a dedicated path.** ShaderToy `mainImage` / `mainCubemap`, Buffer and feedback content goes through the `create_shadertoy_material` command in `edit_by_dsl`; read `references/ShaderToy-Material-Content.md`. Use `import_glsl` only for a generic single-pass `void main()` shader that needs the legacy PostProcess shell and builtin bridge. Hand-convert mesh-local or ordinary AUSL programs only.

**Screen-space orientation:** the engine's fullscreen `v_uv` is **bottom-left origin**, the same convention these shaders assume — so pixel coordinates are `v_uv * u_ScreenParams.xy` with no flip. Do not insert `1.0 - v_uv.y` "to correct for" a top-left origin; there isn't one, and doing so renders the effect upside down.

## Mechanical mapping

Apply these rewrites to the GLSL body as you move it into the shell. Every one of them is deterministic — no judgment required.

| GLSL (as written)                                                          | AUSL (as required)                                                                | Why                                                                                                   |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `void main()`                                                              | `void fragment()` (and `void vertex()` for the vertex stage)                      | Entry-point names are fixed; the preprocessor looks for these exact identifiers                       |
| `gl_FragColor = c;`                                                        | `o_fragColor = c;` with `out lowp vec4 o_fragColor;` in `#pragma output`          | ES 3.0 has no `gl_FragColor` — targets are declared                                                   |
| `texture2D(s, uv)` / `textureCube(s, d)`                                   | `texture(s, uv)` / `texture(s, d)`                                                | ES 1.0 sampling functions were removed in ES 3.0                                                      |
| `varying vec2 uv;` (in both stages)                                        | bare `highp vec2 v_uv;` inside `#pragma varying`                                  | The varying block generates the `out`/`in` pair for you — a manual qualifier is a syntax error        |
| `attribute vec3 pos;`                                                      | `in mediump vec3 attPosition;` inside `#pragma input`                             | ES 3.0 spelling, and attribute names are engine-fixed (`attPosition`, `attTexcoord0`, `attNormal`, …) |
| `uniform float x;` at file top level                                       | the same line inside `#pragma vs …` or `#pragma fs …`                             | Each stage has its own uniform environment; top-level uniforms are not visible to either              |
| `#include "..."` at file top level                                         | the same line inside the stage block that needs it                                | Includes are expanded per stage                                                                       |
| `/* block comment */`                                                      | `// line comment`                                                                 | The AUSL preprocessor rejects block comments                                                          |
| `#if USE_THING`                                                            | `#ifdef USE_THING`                                                                | `#if <MACRO>` is not supported as a toggle check                                                      |
| any custom MVP uniform name (`u_MVPMatrix`, `uMVP`, `modelViewProjection`) | `u_MVP`, or `get_gl_Position()` from `Packages/3D/Utilities/VertexTransform.glsl` | Only the engine's exact names get bound; a wrong name compiles and silently renders nothing           |
| a hand-rolled bone array `uniform mat4 bones[64];`                         | the `u_PalatteBuffer` UBO from the starter template                               | Same reason — the engine binds one specific shape                                                     |

Anything not in this table — your noise functions, raymarch loops, colour grading, easing — moves across **verbatim**. Resist the urge to "port" it.

### Uniforms you don't have to create

The engine binds these every frame. Declare them (in the right stage block) and use them; never write a script to feed them.

| Uniform                                                             | Stage    | Meaning                                                                                                                        |
| ------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `u_MVP`, `u_Model`, `u_View`, `u_Projection`, `u_TransposeInvModel` | vertex   | Standard transform matrices                                                                                                    |
| `u_ScreenParams`                                                    | either   | `.xy` = screen size in pixels — the source for texel size and for anything a GLSL shader would call `iResolution`/`resolution` |
| `_MainTex`                                                          | fragment | The camera output texture in a PostProcess pass                                                                                |

Traditional AUSL has **no automatic ShaderToy time uniform**. A legacy shader animated by `time` / `u_time` needs a `Float` UIPROPERTY plus an APJS script, as generated by `import_glsl`. This does not apply to `Profile: "ShaderToy"`: the OMTL Pipeline runtime supplies `iTime`, `iFrame`, `iMouse` and the other ShaderToy builtins without a companion script.

## Procedure

1. **Classify the source.** ShaderToy `mainImage` / Buffer / Cubemap → `create_shadertoy_material`. Generic fullscreen `void main()` → `import_glsl`. Otherwise pick the mesh shell from the table above.
2. **Copy the whole shell** for that target into your OMTL draft. Do not retype it; do not merge fragments from several recipes.
3. **Declare inputs in UIPROPERTY.** Every tunable the GLSL exposed as a uniform becomes a UIPROPERTY line, so the creator can edit it in the Inspector. Textures need the full Defs chain (`Defs` toggle → `#pragma shader_feature` → `#ifdef` around the sampler and its use) or the texmap will not bind.
4. **Move the body in,** applying the mapping table.
5. **Place uniforms** into `#pragma vs` / `#pragma fs` by which stage reads them.
6. **Write the complete `.omtl` with a native file tool**, then call `get_material_status`. Fix `error_message` until the current `source_hash` returns `state: "succeeded"`.
7. **Bind and look at it.** MeshRenderer via `set_component(materials:[{guid}])`; PostProcess via `configure_post_process_custom`. Then screenshot the preview — the rendered image is the real oracle.

## Traps the validator catches for you

Check the source against these known silent-failure patterns before debugging runtime behavior. They can compile while still rendering incorrectly.

| Code                     | Meaning                                                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `MAIN_ENTRY`             | `void main()` present — AUSL entry points are `vertex()` / `fragment()`                                                                                            |
| `LEGACY_TEXTURE_FN`      | `texture2D(` / `textureCube(` — use `texture(`                                                                                                                     |
| `GL_FRAGCOLOR`           | `gl_FragColor` — write to the declared `#pragma output` target                                                                                                     |
| `LEGACY_QUALIFIER`       | `varying` / `attribute` declarations — use `#pragma varying` (bare) / `#pragma input` (`in`)                                                                       |
| `IF_MACRO_TOGGLE`        | `#if <MACRO>` — use `#ifdef <MACRO>`                                                                                                                               |
| `VERSION_NOT_FIRST`      | `#version 300 es` is missing or not the first non-empty line of the AUSL block                                                                                     |
| `TOPLEVEL_INCLUDE`       | `#include` outside a `#pragma vs` / `#pragma fs` block                                                                                                             |
| `UNBOUND_BUILTIN`        | Source-convention builtins left unbound in traditional AUSL — route ShaderToy content through `create_shadertoy_material`, or map generic GLSL uniforms explicitly |
| `BAD_MVP_NAME`           | `u_MVPMatrix` — the engine binds `u_MVP`                                                                                                                           |
| `MISSING_SHADER_FEATURE` | A UIPROPERTY `Defs` macro with no matching `#pragma shader_feature` — the `#ifdef` never activates                                                                 |
| `BLOCK_COMMENT`          | `/* … */` — rewrite as `//`                                                                                                                                        |
| `BAD_INCLUDE_PATH`       | Invented `Packages/@amazing/orion-shader-library/…` prefix                                                                                                         |
| `BAD_BONE_UNIFORM`       | Hand-rolled bone array instead of the `u_PalatteBuffer` UBO                                                                                                        |

A clean `warnings[]` does not prove the shader is right — it proves it avoids the known mechanical traps. Correctness is still established by looking at the render.

## Read next

- `references/AUSL-Syntax.md` — full pragma grammar, when you need a block or pragma the shells don't demonstrate
- `references/PostProcess-CustomMaterial-Reference.md` — the fullscreen shell and its non-negotiable structure
- `references/PostProcess-CustomMaterial-Troubleshooting.md` — when a fullscreen effect renders black, unchanged, or inverted
- `references/recipes/Recipe-GLSLImport.md` — the automated path, and the time-bridge script pattern to copy for any animated material
