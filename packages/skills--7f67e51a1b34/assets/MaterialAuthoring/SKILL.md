---
name: MaterialAuthoring
description: Use this skill for custom materials, AUSL, Raster Pipeline OMTL, ShaderToy mainImage/mainCubemap and PostProcess workflows. Covers built-in versus authored materials, native OMTL editing, structured ShaderToy material creation, exact compile verification, MeshRenderer/PostProcess binding, safe templates and recipes.
---

# MaterialAuthoring — Custom Shader & Material Authoring

Use this skill when the user needs a **custom visual effect** that cannot be produced by only changing uniforms on a built-in material (Standard PBR / Unlit / etc.).

## Choose the authoring path

First distinguish an existing OMTL edit from new material creation:

| Task                                                                                               | Authoring path                                                                                                |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Modify any existing `.omtl`, traditional or Pipeline                                               | Read the file, edit it natively, then run `get_material_status` in `edit_by_dsl`                              |
| Create a traditional Mesh/Surface AUSL material                                                    | Start from the validated template, write the file natively, then run `get_material_status` in `edit_by_dsl`   |
| Create a non-ShaderToy Raster Pipeline using ordinary AUSL passes                                  | Read `references/OMTL-Raster-Pipeline.md`, write the file, then run `get_material_status` in `edit_by_dsl`    |
| Create a ShaderToy `mainImage` / `mainCubemap` effect, including Buffer passes and feedback        | Read `references/ShaderToy-Material-Content.md`, then run `create_shadertoy_material` in `edit_by_dsl`        |
| Put a ShaderToy Pipeline result on geometry that must bend, ripple, inflate, or otherwise deform   | Create it as above, then add `Pipeline.Display` following `references/OMTL-Raster-Pipeline.md` and recompile  |
| Combine persistent feedback, Buffer/Cubemap output, or another Pipeline-only effect with deforming geometry | Create the Pipeline first, then add `Pipeline.Display`; a traditional one-pass material cannot preserve both parts |
| Import a generic single-pass fullscreen `void main()` GLSL shader as a legacy PostProcess material | Use the `import_glsl` DSL command                                                                             |
| The user already supplied complete OMTL text                                                       | Preserve its architecture, write it natively, then run `get_material_status` in `edit_by_dsl`                 |

For a ShaderToy URL, do not invent source from the title. Obtain the complete pass source and channel relationships first. If the available tools cannot read the page, ask the user for the source instead of generating an unrelated approximation.

Then decide whether custom authoring is needed:

1. **Just color / texture / tiling** → built-in material, no custom shader needed.

   - `add_builtin_resource` (e.g., `"Standard PBR"` or `"Unlit"`) → `set_resource_properties(matGuid, {_AlbedoColor: {r,g,b,a}, _AlbedoTexture: {guid}})`
   - Follow with `set_component(meshRendererGuid, {materials: [{guid: matGuid}]})`.

2. **Dynamic runtime uniform changes** (color pulse, scroll, blink) → built-in material + APJS script.

   - Use built-in material. In `onUpdate`, call `material.setColor/setFloat/setVector`. See `MeshRendererScript` skill for the runtime API.

3. **Custom mesh-local per-pixel math** (dissolve, outline, custom blend, vertex displacement) → **create a traditional `.omtl` file with a native file tool**.

   - Write the complete OMTL under `Assets/Materials/`, run `get_material_status` through `edit_by_dsl`, then assign the returned material GUID via `set_component`. See "Writing OMTL" below.

4. **Post processing** → write custom AUSL that samples the PostProcess input, then bind it with `configure_post_process_custom`. For generic single-pass `void main()` GLSL, use `import_glsl`. See "PostProcess materials" below.

5. **ShaderToy output plus object deformation** → first create the ShaderToy Pipeline, then edit the generated OMTL to add a custom `Pipeline.Display`. The Display is the geometry-facing AUSL pass: it samples `_OmtlPipelineOutput` in `fragment()` and performs the requested deformation in `vertex()`. Re-run `get_material_status` after the edit.

## Traditional OMTL format

A traditional single-program `.omtl` normally has these parts, separated by literal delimiter lines. Pipeline OMTL can contain multiple named source blocks and `SharedSources`; read `references/OMTL-Raster-Pipeline.md` before creating or changing one.

```
<JSON header>
---ENDJSON

---BEGIN UIPROPERTY
<property declarations>
---END UIPROPERTY

---BEGIN <auslID>
<inline AUSL shader code>
---END <auslID>
```

The `auslID` in `---BEGIN` / `---END` must match `Pass.Ausl` in the JSON header. Convention: `"a1"`.

### JSON header minimum

```json
{
  "Shader": "MyCustomUnlit",
  "RenderQueue": 1000,
  "Pass": [
    {
      "Ausl": "a1",
      "Cull": "Back",
      "DepthTestEnable": "True",
      "DepthWriteEnable": "True",
      "ZTest": "LessEqual",
      "BlendMode": "DISABLED"
    }
  ]
}
```

Queue values: Opaque=1000, AlphaTest=2450, Transparent=3000.
BlendMode values: `DISABLED`, `ALPHA_TEST`, `NORMAL`, `MULTIPLY`, `SCREEN`, `ADD`, `SUBTRACT`, `OVERLAY`, `DARKEN`, `LIGHTEN`, `COLOR_DODGE`, `COLOR_BURN`.

| Optional Pass field | Default      | Effect                                                                                                                                                                                |
| ------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"InstanceCount"`   | (absent = 1) | Number of GPU instances for `gl_InstanceID`. Each instance draws the same mesh; the vertex shader uses `gl_InstanceID` to vary per-instance behavior (e.g., shell extrusion for fur). |

### UIPROPERTY block

Declares editor-visible uniforms and their defaults. Groups with built-in `$omtl_...$` tokens; conditional children with `[ParentMacro]`.

```
---BEGIN UIPROPERTY
    $omtl_albedo$
    _AlbedoColor (omtl_color, Color) = [1.0, 1.0, 1.0, 1.0]
    AlbedoTexture (omtl_texture_on, Defs) = 0
    [AlbedoTexture] _AlbedoTexture (omtl_texture, 2D) = "Default_Material_Texture_Icon"
---END UIPROPERTY
```

**Inspector naming rule:** the left-side labels are driven by the `omtl_*` metadata keys and `$omtl_*$` group tokens. Reuse built-in semantic keys from engine materials; do **not** invent placeholders like `omtl_float` or custom groups like `$omtl_flame$`, or the Inspector can fall back to showing those raw tokens instead of friendly names.

| UIType           | Uniform type     | Default example                                                 |
| ---------------- | ---------------- | --------------------------------------------------------------- |
| `Color`          | `vec4`           | `_TintColor (omtl_color, Color) = [1, 1, 1, 1]`                 |
| `2D`             | `sampler2D`      | `_MainTex (omtl_texture, 2D) = "Default_Material_Texture_Icon"` |
| `Vec2`           | `vec2`           | `_Tiling (omtl_tiling, Vec2) = [1, 1]`                          |
| `Vec3`           | `vec3`           | `_WindDir (omtl_direction, Vec3) = [0, 1, 0]`                   |
| `Vec4`           | `vec4`           | `_Bounds (omtl_vector, Vec4) = [0, 0, 0, 0]`                    |
| `Range(min,max)` | `float` (slider) | `_GlowIntensity (omtl_intensity, Range(0, 1)) = 0.5`            |
| `Float`          | `float`          | `_ShellCount (omtl_fur_shell_count, Float) = 48.0`              |
| `Defs`           | macro toggle     | `UseNoise (omtl_texture_on, Defs) = 1`                          |

Common semantic float keys from built-in materials include `omtl_intensity`, `omtl_strength`, `omtl_power`, `omtl_scale`, `omtl_width`, `omtl_rotation`, `omtl_tiling`, `omtl_offset`, and `omtl_roughness`. Pick the closest built-in key for the parameter's meaning instead of falling back to a generic invented token.

### AUSL block — structural rules

Every AUSL block MUST contain, in order:

- `#version 300 es` — **first non-empty line** of the block, no exceptions
- `#pragma only_renderers glsl30 metal`
- `#pragma multi_compile AE_AMAZING_USE_BONES` (required; bone path toggles off via 0 default but must exist)
- `#pragma shader_feature <MACRO>` — **one per UIPROPERTY `Defs` macro**. Without this, `#ifdef <MACRO>` branches stay disabled even when the UIPROPERTY toggle is ON.
- `#pragma input attributes … #pragma end`
- `#pragma varying varyings … #pragma end` (can be empty; variables have **no `in`/`out` prefix** — bare declarations only)
- `#pragma output targets … #pragma end`
- `#pragma vs attributes varyings … #pragma end` (uniforms + `#include`s for vertex stage)
- `#pragma fs varyings targets … #pragma end` (uniforms + `#include`s for fragment stage)
- `void vertex() { ... }` — vertex entry, **name is fixed**
- `void fragment() { ... }` — fragment entry, **name is fixed**

Language-level contracts (violations silently break the shader):

- **Only `//` single-line comments** — `/* ... */` is not supported by the AUSL preprocessor.
- **Macro guards use `#ifdef <MACRO>`** — `#if <MACRO>` is **not supported** for toggle checks.
- **Dynamic macros (`multi_compile`) must start with `AE_`** — engine convention.
- **`#include` lines belong inside `#pragma vs` / `#pragma fs` blocks**, not at top level.

See "AUSL language reference" at the bottom of this skill for the full pragma grammar and variant-cost rules — consult it when you need a pragma not used by the starter/recipes.

### Engine-reserved uniforms (DO NOT rename)

These uniform names are set automatically by the engine every frame. Use **exactly these names** in your `#pragma vs` block:

| Name                  | Type           | Meaning                                                                                                                                                                                        |
| --------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `u_MVP`               | `highp mat4`   | Model-View-Projection matrix. **Use `u_MVP`, never `u_MVPMatrix`** — the latter is an LLM hallucination and the engine will not bind it (gl_Position ends up zero → object becomes invisible). |
| `u_Model`             | `highp mat4`   | Model matrix (object → world)                                                                                                                                                                  |
| `u_View`              | `mediump mat4` | View matrix (world → camera)                                                                                                                                                                   |
| `u_Projection`        | `mediump mat4` | Projection matrix                                                                                                                                                                              |
| `u_TransposeInvModel` | `highp mat4`   | For transforming normals to world space                                                                                                                                                        |

For skeletal animation, include the canonical bone UBO and use the provided helper:

```glsl
#ifdef AE_AMAZING_USE_BONES
const int MAX_BONES = 100;
struct BoneMatrix {
    highp mat4 u_Bone[MAX_BONES];
};
layout(std140) uniform highp u_PalatteBuffer {
    BoneMatrix boneMatrix;
};
#endif
#include "Packages/3D/Utilities/VertexTransform.glsl"
```

`VertexTransform.glsl` provides: `getBoneTransform()`, `get_bm_postiton()`, `get_posWS()`, `get_gl_Position()`. Use `get_gl_Position()` — never multiply by `u_MVP` yourself.

### Defs macros — the chain that must be complete

For a `Defs` UIPROPERTY toggle to actually work, **four things must line up**:

1. **UIPROPERTY declaration**: `MyMacro (omtl_xxx, Defs) = 1`
2. **`#pragma shader_feature MyMacro`** at top of AUSL block (enables the macro path)
3. **`#ifdef MyMacro`** guards around the uniform declaration in `#pragma fs/vs`
4. **`#ifdef MyMacro`** guards around the usage in `vertex()` / `fragment()`

If you declare a uniform (e.g., `_AlbedoTexture`) **without** a `Defs` macro guard, the engine still declares it but may not auto-bind the texture from the material's texmap. The safe pattern is: introduce a `Defs` macro that mirrors each optional feature, default it to `1` if you always want it on, and guard everything with `#ifdef`.

Every UIPROPERTY uniform must also appear in a `uniform` declaration inside `#pragma fs` (or `#pragma vs`) — the UIPROPERTY alone does not declare the uniform.

## Safe starter template (textured Unlit)

**This is the minimum viable material — use this as your base, then change only what you need.** It matches the real engine `Unlit_v1.asl` contract (uses `u_MVP`, the bone UBO, and `VertexTransform.glsl`), so the compiled shader is guaranteed to bind against engine-provided uniforms.

```json
{
  "Shader": "StarterUnlit",
  "RenderQueue": 2000,
  "Pass": [{"Ausl":"a1","Cull":"Back","DepthTestEnable":"True","DepthWriteEnable":"True","ZTest":"LessEqual","BlendMode":"DISABLED"}]
}
---ENDJSON

---BEGIN UIPROPERTY
    $omtl_albedo$
    _AlbedoColor (omtl_color, Color) = [1.0, 1.0, 1.0, 1.0]
    AlbedoTexture (omtl_texture_on, Defs) = 1
    [AlbedoTexture] _AlbedoTexture (omtl_texture, 2D) = "Default_Material_Texture_Icon"
---END UIPROPERTY

---BEGIN a1

    #version 300 es
    #pragma only_renderers glsl30 metal
    #pragma multi_compile AE_AMAZING_USE_BONES
    #pragma shader_feature AlbedoTexture

    #pragma input attributes
        in mediump vec3 attPosition;
        in highp vec2 attTexcoord0;
        #ifdef AE_AMAZING_USE_BONES
            in mediump vec4 attBoneIds;
            in highp vec4 attWeights;
        #endif
    #pragma end

    #pragma varying varyings
        highp vec2 v_uv;
    #pragma end

    #pragma output targets
        out lowp vec4 o_fragColor;
    #pragma end

    #pragma vs attributes varyings
        precision mediump float;
        #ifdef AE_AMAZING_USE_BONES
            const int MAX_BONES = 100;
            struct BoneMatrix {
                highp mat4 u_Bone[MAX_BONES];
            };
            layout(std140) uniform highp u_PalatteBuffer {
                BoneMatrix boneMatrix;
            };
        #endif
        uniform highp mat4 u_Model;
        uniform highp mat4 u_MVP;
        uniform highp mat4 u_TransposeInvModel;
        #include "Packages/3D/Utilities/VertexTransform.glsl"
    #pragma end

    #pragma fs varyings targets
        precision mediump float;
        uniform lowp vec4 _AlbedoColor;
        #ifdef AlbedoTexture
            uniform lowp sampler2D _AlbedoTexture;
        #endif
    #pragma end

    void vertex() {
        v_uv = attTexcoord0;
    #ifdef AE_AMAZING_USE_BONES
        highp mat4 boneTransform = getBoneTransform();
        vec4 bm_pos = get_bm_postiton(boneTransform, attPosition);
        gl_Position = get_gl_Position(bm_pos);
    #else
        gl_Position = get_gl_Position(attPosition);
    #endif
    }

    void fragment() {
        vec4 color = _AlbedoColor;
    #ifdef AlbedoTexture
        color *= texture(_AlbedoTexture, v_uv);
    #endif
        o_fragColor = color;
    }

---END a1
```

**Why this template works**:

- `u_MVP` + `get_gl_Position()` from `VertexTransform.glsl` = correct screen-space position
- Bone UBO `u_PalatteBuffer.boneMatrix.u_Bone[]` = real engine bone binding
- `AlbedoTexture` Defs macro + `#pragma shader_feature` + `#ifdef` in three places = texture actually binds from texmap
- Default `AlbedoTexture = 1` means new materials show the default texture immediately; toggle OFF in Inspector for a pure-color variant.

## Recipes — extend the starter

Each recipe lives in its own file and shows only the delta applied on top of the starter template (UIPROPERTY additions, extra `#pragma shader_feature` lines, added uniforms, modified `fragment()` body, and any runtime script). Read the one you need via the Read tool — do not pre-load all of them.

For **complex PostProcess custom materials**, do not assemble the shader from scattered recipe fragments. First copy the full validated OMTL in `skills_root/assets/MaterialAuthoring/references/PostProcess-CustomMaterial-Reference.md`, keep that whole-file skeleton intact, and only then apply one focused recipe or your own effect logic on top of it.

| Need                                                                                 | Recipe file                                                                   | Summary                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UV tiling / offset / animated scrolling                                              | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-UVScroll.md`              | Adds `UvControl` Defs macro with `_Tiling` + `_UVOffset`; scrolling is driven by an APJS script setting `_UVOffset` each frame                                                                                                                                                |
| Dissolve / alpha-test burn-out                                                       | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-Dissolve.md`              | Adds `_DissolveAmount` slider + noise texture; uses `discard` with `BlendMode: ALPHA_TEST` and `RenderQueue: 2450`                                                                                                                                                            |
| Shell-based fur / procedural hair                                                    | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-FurShell.md`              | Complete replacement shader with vertex displacement, instanced shells (`InstanceCount` + `gl_InstanceID`), 3D noise strand generation, wrapped diffuse, AO, and rim lighting                                                                                                 |
| PostProcess custom Sobel edge                                                        | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-PostProcess-SobelEdge.md` | A concrete full-screen PostProcess example showing `_MainTex` sampling, `u_ScreenParams` texel-size derivation, Sobel edge extraction, and `configure_post_process_custom` binding                                                                                            |
| Soft brush dab for a paint canvas                                                    | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-AccumulationBrush.md`     | Procedural radial-alpha soft dab with FBO-read programmable blend (`BlendMode: Normal_v2` + `ApplyBlendMode`) so overlapping semi-transparent dabs accumulate into a RenderTexture without erasing. Pairs with the CommandBuffer brush canvas example `APJS/examples/commandbuffer_paint_canvas.json` |
| Import a generic fullscreen `void main()` GLSL shader as a legacy PostProcess effect | `skills_root/assets/MaterialAuthoring/references/recipes/Recipe-GLSLImport.md`            | Use `import_glsl` for the legacy PostProcess shell and builtin bridge. For ShaderToy `mainImage`, Buffer, feedback or Cubemap content, use `create_shadertoy_material` instead.                                                                                               |
| Create a ShaderToy Raster Pipeline material                                          | `skills_root/assets/MaterialAuthoring/references/ShaderToy-Material-Content.md`           | Describe Common, Buffer, Cubemap, Image and channel wiring; the command derives Pass, Step, Resource, Current/Previous and History.                                                                                                                                           |

If none of the above match, use the comprehensive AUSL example in `references/AUSL-Syntax.md` as a starting point and craft the `fragment()` logic from scratch.

> **Recipe scope**: Most recipes apply small deltas on top of the starter. Recipes marked "Complete replacement shader" replace the entire AUSL block — the starter template is not a prerequisite for those.

## Full Agent workflow

1. **Confirm custom shader is needed** — run the authoring-path table above. If rows 1 or 2 match, do not create a custom OMTL.
2. **For ShaderToy content**, read `references/ShaderToy-Material-Content.md` and run `create_shadertoy_material` through `edit_by_dsl`; skip the native creation steps below. Its successful result already confirms compilation, so do not immediately run `get_material_status` again.
3. **For traditional OMTL**, pick the closest recipe and write the complete file with a native file tool at `<project>/Assets/Materials/Effects/MyGlow.omtl`.
4. **Immediately run `get_material_status` through `edit_by_dsl`** with the project-relative path:
   ```json
   {
     "commands": [
       {
         "command_type": "get_material_status",
         "params": {"material_path": "Assets/Materials/Effects/MyGlow.omtl"},
         "alias": "material"
       }
     ]
   }
   ```
   The command reads the current file hash and waits for that exact content. On success it returns `state`, `has_working_version`, `source_hash`, `attempt_id`, and `guid`. An older successful compile cannot satisfy a newer edit.
5. **Fix failures before binding.** A failed compile stops the DSL batch and includes `state`, `error_message`, `source_hash`, and `attempt_id` in the command error. Correct the whole file with the native edit tool, then run `get_material_status` again. A timeout is also an error, not success. Do not use `_compile_check` or `get_script_logs` as the material verdict.
6. **Assign to MeshRenderer** using the `guid` returned by `get_material_status`:
   ```json
   {
     "command_type": "set_component",
     "params": {"guid": "<meshRendererGuid>", "properties": {"materials": [{"guid": "<materialGuid>"}]}}
   }
   ```
7. **Verify** with `capture_preview` (reloads the scene + screenshots the fresh runtime).

### Editing a material created by `create_shadertoy_material`

The creation command does not own later edits. Read the generated `.omtl`, then load the "Editing generated ShaderToy OMTL" section in `references/OMTL-Raster-Pipeline.md`. Edit natively and run `get_material_status` through `edit_by_dsl` for the exact new content.

### Uniform-only changes do not require source edits

If you only want to change a uniform value after creation, use `set_resource_properties`, not a full-file edit:

```json
{
  "command_type": "set_resource_properties",
  "params": {"guid": "<matGuid>", "properties": {"_AlbedoColor": {"r": 1, "g": 0, "b": 0, "a": 1}}}
}
```

Editing the `.omtl` rewrites and recompiles the shader source; reserve it for AUSL, Pass, Pipeline, or MultiPass changes.

### After a source edit, re-bind the material when needed

The engine side re-runs `createMaterialFromData` on every OMTL reimport. When a failed edit is repaired, the `APJS.Material` instance may be replaced and `MeshRenderer.materials[]` can become empty. After recovery from an error or a significant Pass/shader change, call `get_material_status`, then re-issue `set_component` with the returned material GUID.

```json
{
  "command_type": "set_component",
  "params": {
    "guid": "<meshRendererGuid>",
    "properties": {"materials": [{"guid": "<materialGuid>"}]}
  }
}
```

If the object renders as untextured or as a placeholder after a source edit, re-bind first. If that does not fix it: `delete_component` on the MeshRenderer → `add_component` → `set_component` materials.

## PostProcess materials

Use this path when the effect must sample the camera output rather than shade a mesh.

| Source shape                             | Create with                                                                                                                                    | Read on demand                                                    |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Traditional AUSL                        | Copy the complete validated PostProcess OMTL, change only its effect logic, write natively, then call `get_material_status`.                    | `references/PostProcess-CustomMaterial-Reference.md`              |
| Generic legacy `void main()` GLSL       | `import_glsl`                                                                                                                                    | `references/recipes/Recipe-GLSLImport.md`                          |

For every path, require a successful compile result, bind the material GUID with `configure_post_process_custom`, then use `capture_preview`.

`create_shadertoy_material` keeps external `iChannelN` texture inputs as editable UIPROPERTY values. It does not automatically reinterpret a Channel as the PostProcess input texture.

For a wrong, blank, or stale result, load `references/PostProcess-CustomMaterial-Troubleshooting.md`. For a concrete traditional AUSL effect delta, load `references/recipes/Recipe-PostProcess-SobelEdge.md`.

## Common errors — grep your OMTL before submitting

| Symptom                                                                                                                                                            | Root cause                                                                                                                                                                              | Fix                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `#pragma output targets` is empty but `fragment()` still writes `o_fragColor = ...`                                                                                | The output declaration drifted away from the validated PostProcess skeleton                                                                                                             | Restore the validated output block and keep `out highp vec4 o_fragColor;` declared explicitly.                                                                                                                                  |
| PostProcess helper functions were moved outside `#pragma fs varyings targets`                                                                                      | The generated shader no longer matches the validated branch structure                                                                                                                   | Put `_MainTex` / `u_ScreenParams`-dependent helpers back into the `#pragma fs varyings targets` block and keep only `vertex()` / `fragment()` top-level.                                                                        |
| **Object renders invisible / transparent** (most common failure)                                                                                                   | Using `u_MVPMatrix` instead of `u_MVP`                                                                                                                                                  | The engine only binds `u_MVP`. `u_MVPMatrix` stays at zero matrix → all vertices collapse to origin → nothing drawn. Use `u_MVP` + `get_gl_Position()` from `VertexTransform.glsl`.                                             |
| **Texture looks black / material renders transparent**                                                                                                             | Texture uniform declared without `Defs` macro guard                                                                                                                                     | Wrap the sampler with a `Defs` macro (e.g., `AlbedoTexture`), add `#pragma shader_feature AlbedoTexture`, default UIPROPERTY to `= 1`, guard `uniform lowp sampler2D _AlbedoTexture` and its usage with `#ifdef AlbedoTexture`. |
| **`Defs` toggle has no effect**                                                                                                                                    | Missing `#pragma shader_feature <MACRO>` at top of AUSL block                                                                                                                           | Add it — without the shader_feature pragma, `#ifdef` blocks stay disabled regardless of UIPROPERTY value.                                                                                                                       |
| `void main()`                                                                                                                                                      | AUSL entry names are fixed                                                                                                                                                              | Rename to `void vertex()` / `void fragment()`                                                                                                                                                                                   |
| UIPROPERTY declares `_Foo` but no `uniform … _Foo` in `#pragma fs/vs`                                                                                              | UIPROPERTY alone doesn't declare uniforms                                                                                                                                               | Add the `uniform <type> _Foo` declaration in the fs or vs block                                                                                                                                                                 |
| `---BEGIN al` (lowercase-L) vs `"Ausl": "a1"` (number-one)                                                                                                         | Case-sensitive typo                                                                                                                                                                     | Match exactly — the block id is case-sensitive                                                                                                                                                                                  |
| Missing `#pragma multi_compile AE_AMAZING_USE_BONES`                                                                                                               | Required even for non-skinned meshes                                                                                                                                                    | Keep it on; model either enables or disables the bone path                                                                                                                                                                      |
| Missing `---ENDJSON`                                                                                                                                               | Parser needs the literal line                                                                                                                                                           | Cannot omit                                                                                                                                                                                                                     |
| Transparent material renders opaque                                                                                                                                | Wrong Pass config                                                                                                                                                                       | Set `"BlendMode": "NORMAL"` AND `"RenderQueue": 3000` AND `"DepthWriteEnable": "False"`                                                                                                                                         |
| Uniform sets but has no visible effect                                                                                                                             | Not sampled in shader                                                                                                                                                                   | Use the uniform inside `vertex()` / `fragment()` — UIPROPERTY writes the value but shader code must sample it                                                                                                                   |
| Bones "work" on your local test but break for skinned models                                                                                                       | Declaring bones as `uniform mat4 u_BoneMatrixes[64]`                                                                                                                                    | Wrong — use the engine's UBO struct pattern (see the starter template's bone block)                                                                                                                                             |
| Vertex shader compile fails with `'getBoneTransform' : no matching overloaded function found` (or similar for `get_gl_Position` / `get_bm_postiton` / `get_posWS`) | `#include "Packages/@amazing/orion-shader-library/..."` — that prefix does not exist on disk, so the include expands to nothing                                                         | Use `#include "Packages/3D/Utilities/VertexTransform.glsl"`. The engine rewrites `Packages/` → `<OrionShaderLibrary_root>/`; the first path segment after `Packages/` must be a real subfolder (`3D/`, `core/`, `common/`).     |
| Object renders as placeholder / wrong material after a successful source edit                                                                                      | MeshRenderer.materials[] can end up empty when the engine re-runs `createMaterialFromData` on reimport, especially after recovering from a compile error.                               | Re-issue `set_component` with the GUID returned by `get_material_status`. If that still doesn't fix it, `delete_component` the MeshRenderer, `add_component` a fresh one, then `set_component` materials.                       |
| Script reads `renderer.mainMaterial` as null even though the material is bound in the editor                                                                       | `mainMaterial` is a convenience getter typed `Material \| null`; it can return null during the first frames of binding or around reimport cycles, even when `materials[0]` is populated | Access via `materials[0]` with `mainMaterial` as fallback: `const mat = r.materials && r.materials.length > 0 ? r.materials[0] : r.mainMaterial;`. See `skills_root/ability/MeshRendererScript`.                                             |
| Shader fails to compile after adding a comment                                                                                                                     | Used `/* block comment */`                                                                                                                                                              | AUSL only supports `//`. Rewrite as single-line comments.                                                                                                                                                                       |
| `#ifdef` branches flip unexpectedly or compile fails                                                                                                               | Used `#if MY_MACRO` instead of `#ifdef MY_MACRO`                                                                                                                                        | Toggle macros use `#ifdef` only. See "AUSL language reference" for full rules.                                                                                                                                                  |
| `#pragma multi_compile` doesn't take effect                                                                                                                        | Dynamic macro name doesn't start with `AE_`                                                                                                                                             | Rename to `AE_MY_MACRO`.                                                                                                                                                                                                        |
| `#include` line reports "file not found" or behaves unpredictably                                                                                                  | Placed `#include` at top level or outside vs/fs block                                                                                                                                   | Move it into `#pragma vs` or `#pragma fs`.                                                                                                                                                                                      |

## Converting GLSL to AUSL

Starting from GLSL — pasted by the user, lifted from a shader site, or written by you because plain GLSL is easier to reason about than the pragma layer — is a first-class path, not a workaround. The mechanical mapping (entry points, `gl_FragColor`, `texture2D`, `varying`/`attribute`, uniform placement, `#if` vs `#ifdef`), which validated shell to transplant into, the engine-provided uniforms you must not reinvent, and common static traps live in:

**`skills_root/assets/MaterialAuthoring/references/GLSL-to-AUSL.md`**

Read it before hand-writing AUSL for an effect you could express as GLSL.

## AUSL language reference

Deeper pragma grammar, variant-cost rules, `#include` placement, and a comprehensive `#pragma global` + `multi_compile` example live in a separate reference file. Read it only when you need a pragma or language construct the starter + recipes don't show:

**`skills_root/assets/MaterialAuthoring/references/AUSL-Syntax.md`**

Quick checklist of things it covers (so you know when to reach for it):

- Full `#pragma multi_compile` / `shader_feature` / `only_renderers` / `require` grammar
- Block pragmas (`input` / `varying` / `output` / `global` / `vs` / `fs`) and their arguments
- `#pragma global` for structs/consts shared between vs and fs
- Three-argument `#pragma vs <input> <varying> [global]` form
- Variant-count math (keep `multi_compile` lines ≤ 2)
- Comprehensive example combining `global`, multi-mode `multi_compile`, `shader_feature`, and cross-stage `#include`

If your task is covered by the starter or one of the recipes, you do not need to read it.

## Rules

- **Don't author PBR from scratch.** PBR needs 1600+ lines of light/tone-mapping code. Clone Standard PBR and modify uniforms instead.
- **Don't edit the OMTL for uniform-only tweaks.** Uniform values go through `set_resource_properties`.
- **Don't write `#include` paths as absolute.** Use `#include "Packages/…"` — the engine rewrites these at load/save time.
- **Don't skip the boneMatrix branch.** Even non-skinned models compile the `AE_AMAZING_USE_BONES`-off path; remove the branch and builds break for skinned meshes.
- **Don't edit the OMTL only to add a `Pass` option** — if a render-state toggle exists as UIPROPERTY already, let the user change it in the Inspector.
