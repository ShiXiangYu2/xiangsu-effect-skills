# Recipe: UV Tiling, Offset & Scrolling

> Loaded on demand from `skills_root/assets/MaterialAuthoring/SKILL.md`. **Prerequisite**: you've already read the SKILL.md starter template — this file shows only the deltas you apply on top of it.

## What this produces

- Editor-exposable `_Tiling` (Vec2) and `_UVOffset` (Vec2) uniforms guarded by a `UvControl` macro toggle.
- A runtime APJS script that animates `_UVOffset` to make the texture scroll.

## UIPROPERTY delta

Add after the starter's `_AlbedoTexture` line:

```
    $omtl_uv_control$
    UvControl (omtl_uv_control, Defs) = 1
    [UvControl] _Tiling (omtl_tiling, Vec2) = [1.0, 1.0]
    [UvControl] _UVOffset (omtl_offset, Vec2) = [0.0, 0.0]
```

## AUSL deltas

Add to the `#pragma shader_feature` declarations at top (each `Defs` macro needs one):

```glsl
#pragma shader_feature UvControl
```

Add to `#pragma fs varyings targets`:

```glsl
#ifdef UvControl
uniform lowp vec2 _Tiling;
uniform lowp vec2 _UVOffset;
#endif
```

Replace the `fragment()` body with:

```glsl
void fragment() {
    vec2 uv = v_uv;
#ifdef UvControl
    uv = uv * _Tiling + _UVOffset;
#endif
    vec4 color = _AlbedoColor;
#ifdef AlbedoTexture
    color *= texture(_AlbedoTexture, uv);
#endif
    o_fragColor = color;
}
```

## Animated scrolling — APJS script

**Do NOT put time math in the shader.** Drive `_UVOffset` from a script that runs each frame:

```typescript
@component()
export class ScrollUV extends APJS.BasicScriptComponent {
    @serializeProperty renderer!: APJS.MeshRenderer;
    @serializeProperty speed: APJS.Vector2f;
    private t = 0;

    onUpdate(dt: number) {
        if (!this.renderer) return;
        // Prefer materials[0] over mainMaterial — the latter can return null
        // during OMTL reimport cycles. See skills_root/ability/MeshRendererScript.
        const mats = this.renderer.materials;
        const mat = (mats && mats.length > 0) ? mats[0] : this.renderer.mainMaterial;
        if (!mat) return;
        this.t += dt;
        mat.setVector('_UVOffset', new APJS.Vector2f(this.t * this.speed.x, this.t * this.speed.y));
    }
}
```

## Verification

After native OMTL creation + `get_material_status` + `set_component` + `add_script` + attach:

- `get_material_status` returns `state: "succeeded"` for the current file content.
- `interact_by_dsl` with two screenshots 500 ms apart — the texture position should visibly shift between them.
- If the texture doesn't move: `get_script_logs` to verify `ScrollUV` is running (runtime script log is captured normally — the log-buffer limitation only affects material import errors).
