# Recipe: Dissolve Effect (Ramped Alpha Cutout)

> Loaded on demand from `skills_root/assets/MaterialAuthoring/SKILL.md`. **Prerequisite**: you've already read the SKILL.md starter template — this file shows only the deltas you apply on top of it.

## What this produces

- A `_DissolveAmount` slider (0.0 → 1.0) that gradually erases the object by discarding fragments where a noise texture is below the threshold.
- An optional `_DissolveNoise` texture guarded by a `Defs` macro — falls back to the default built-in texture.
- Uses alpha-test blend mode so the cutout is hard-edged and writes depth.

## Pass config override

The starter template uses `"BlendMode": "DISABLED"` and `"RenderQueue": 2000`. For dissolve, change the Pass JSON to:

```json
"Pass": [{"Ausl":"a1","Cull":"Back","DepthTestEnable":"True","DepthWriteEnable":"True","ZTest":"LessEqual","BlendMode":"ALPHA_TEST"}]
```

And set the top-level `"RenderQueue": 2450` (alpha-test queue — between opaque 2000 and transparent 3000).

## UIPROPERTY delta

Add to the starter's UIPROPERTY (inside `---BEGIN UIPROPERTY ... ---END UIPROPERTY`):

```
    $omtl_dissolve$
    _DissolveAmount (omtl_dissolve_area, Range(0.0, 1.0)) = 0.0
    AE_DissolveNoise (omtl_dissolve_noise_on, Defs) = 1
    [AE_DissolveNoise] _DissolveNoise (omtl_texture, 2D) = "Default_Material_Texture_Icon"
```

Use the built-in semantic key `omtl_dissolve_area` here — do **not** use a made-up fallback like `omtl_float`, or the Inspector may show the raw token instead of a friendly property label.

## AUSL deltas

Add to the `#pragma shader_feature` declarations at top:

```glsl
#pragma shader_feature AE_DissolveNoise
```

Add to `#pragma fs varyings targets`:

```glsl
uniform lowp float _DissolveAmount;
#ifdef AE_DissolveNoise
uniform lowp sampler2D _DissolveNoise;
#endif
```

Replace the `fragment()` body with:

```glsl
void fragment() {
    vec4 color = _AlbedoColor;
#ifdef AlbedoTexture
    color *= texture(_AlbedoTexture, v_uv);
#endif
#ifdef AE_DissolveNoise
    float n = texture(_DissolveNoise, v_uv).r;
    if (n < _DissolveAmount) discard;
#endif
    o_fragColor = color;
}
```

`discard` hard-cuts the fragment — combined with `BlendMode: ALPHA_TEST` and `DepthWriteEnable: True`, you get clean silhouettes that still occlude behind.

## Runtime animation (optional)

Animate `_DissolveAmount` from 0 → 1 over time for a burn-away effect:

```typescript
@component()
export class DissolveAnimator extends APJS.BasicScriptComponent {
    @serializeProperty renderer!: APJS.MeshRenderer;
    @serializeProperty duration: number = 2.0;
    private t = 0;

    onUpdate(dt: number) {
        if (!this.renderer) return;
        const mats = this.renderer.materials;
        const mat = (mats && mats.length > 0) ? mats[0] : this.renderer.mainMaterial;
        if (!mat) return;
        this.t = Math.min(this.t + dt, this.duration);
        mat.setFloat('_DissolveAmount', this.t / this.duration);
    }
}
```

## Verification

- `get_material_status` returns `state: "succeeded"` for the current file content.
- Start with `_DissolveAmount = 0.0` → object fully visible.
- Increase `_DissolveAmount` to `0.5` via `set_resource_properties` → roughly half the surface area visible with noise-textured holes.
- At `1.0` → object fully invisible.
- Edges should be hard (pixelated noise), not soft — if edges are soft, you're likely using `BlendMode: NORMAL` instead of `ALPHA_TEST`, or forgot `discard` in favor of setting `color.a`.
