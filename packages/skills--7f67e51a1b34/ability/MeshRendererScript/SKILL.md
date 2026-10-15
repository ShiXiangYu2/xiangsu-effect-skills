---
name: MeshRendererScript
description: 介绍如何在脚本中使用 MeshRenderer — 包括读取材质，修改颜色、浮点数和向量参数等
---

# MeshRenderer — Material Scripting

Patterns for changing 3D object materials and their properties at runtime.

## Getting MeshRenderer

```typescript
const renderer = this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;
```

### Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `mesh` | Mesh | The mesh geometry |
| `materials` | Material[] | Shared materials array (stable — always reflects the editor binding) |
| `mainMaterial` | Material \| null | Shortcut for `materials[0]`, **can spuriously return null** — see below |
| `mainPass` | Pass \| null | First pass of the main material |

### Getting the material — `materials[0]` with `mainMaterial` fallback

`mainMaterial` is a convenience getter that is typed `Material | null`. It **can return null even when a material is assigned in the editor**, especially right after OMTL reimport cycles or during the first frame while the renderer finishes binding. Reading from `materials[0]` is more reliable. Prefer this pattern in any script that touches a material:

```typescript
function getMat(r: APJS.MeshRenderer): APJS.Material | null {
    // materials[0] is the stable access; fall back to mainMaterial for older
    // engine builds that surface the material only via the convenience getter.
    const mats = r.materials;
    if (mats && mats.length > 0 && mats[0]) return mats[0];
    return r.mainMaterial ?? null;
}
```

## Changing Material Properties

`Material` exposes `setColor`, `setVector`, `setFloat`, `setInt`, `setMatrix`, and `setTexture` to write named shader uniforms. For Standard PBR colors, **prefer `setColor` with an `APJS.Color`** — it's the most direct API. `setVector` with a `Vector4f` also works for colors but requires the extra conversion step.

```typescript
@component()
export class MaterialController extends APJS.BasicScriptComponent {
  @serializeProperty
  private targetColor: APJS.Color = new APJS.Color(1, 0, 0, 1);

  onStart(): void {
    const renderer = this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;
    if (!renderer) return;
    const mat = renderer.materials && renderer.materials.length > 0
        ? renderer.materials[0]
        : renderer.mainMaterial;
    if (!mat) return;
    // Set albedo color — use setVector with Vector4f (NOT setVector4, it doesn't exist)
    mat.setVector(
      "_AlbedoColor",
      new APJS.Vector4f(this.targetColor.r, this.targetColor.g, this.targetColor.b, this.targetColor.a)
    );
  }
}
```

### Material Methods

| Method | Params | Description |
|--------|--------|-------------|
| `setColor(key, value)` | string, Color | Set a Color uniform — preferred for PBR color slots |
| `setVector(key, value)` | string, Vector2f \| Vector3f \| Vector4f | Set a vector uniform |
| `setFloat(key, value)` | string, number | Set a float property (metallic, roughness) |
| `setInt(key, value)` | string, number | Set an integer property |
| `setTexture(key, texture)` | string, Texture | Swap a texture slot (e.g. `_AlbedoTexture`) |
| `setMatrix(key, value)` | string, Matrix4x4f | Set a matrix uniform |
| `getColor(key)` / `getVector(key)` / `getFloat(key)` | string | Read the current value (or `undefined` if not set) |

### Common PBR Material Properties

| Key | Method | Description |
|-----|--------|-------------|
| `_AlbedoColor` | setColor (or setVector with Vector4f) | Base color |
| `_MRAOMetallic` | setFloat | Metallic (0–1) |
| `_MRAORoughness` | setFloat | Roughness (0–1) |
| `_EmissiveColor` | setColor (or setVector with Vector4f) | Emissive color |
| `_EmissiveIntensity` | setFloat | Emissive intensity |
| `_AlbedoTexture` | setTexture | Base color texture (also flip `_EnableAlbedoTexture` macro) |
| `_NormalTexture` | setTexture | Normal map texture |

> `MaterialPropertyBlock` (used for per-instance overrides) has `setVector` / `setFloat` / `setTexture` but **no** `setColor`. Use `setVector` with a `Vector4f` there.

### Wiring a Material directly to a script

`Material` is a valid `@serializeProperty` resource type. Wire the asset
directly so the script can mutate it without first looking up the
MeshRenderer:

```typescript
@serializeProperty material!: APJS.Material;
// Then in onUpdate() or an event handler: this.material.setColor("_AlbedoColor", color);
```

The same Material instance is shared across every MeshRenderer that
references it, so a single mutation updates every visible copy.

## Color Animation Example

```typescript
@component()
export class ColorCycle extends APJS.BasicScriptComponent {
    private renderer!: APJS.MeshRenderer;
    private elapsed = 0;

    onStart(): void {
        this.renderer = this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;
    }

    onUpdate(dt: number): void {
        if (!this.renderer) return;
        // Resolve material every frame — `materials[0]` is stable even across
        // OMTL reimport cycles. Cache only if profiling shows it matters.
        const mats = this.renderer.materials;
        const mat = (mats && mats.length > 0) ? mats[0] : this.renderer.mainMaterial;
        if (!mat) return;

        this.elapsed += dt;
        const r = Math.sin(this.elapsed * 2) * 0.5 + 0.5;
        const g = Math.sin(this.elapsed * 2 + 2) * 0.5 + 0.5;
        const b = Math.sin(this.elapsed * 2 + 4) * 0.5 + 0.5;
        mat.setVector("_AlbedoColor", new APJS.Vector4f(r, g, b, 1));
    }
}
```

## Rules
1. **Always resolve material via `materials[0]`, not `mainMaterial`** — the latter is a convenience shortcut that can return null during OMTL reimport cycles or first-frame binding. If you must use `mainMaterial`, treat null as "not ready, try again next frame", not "fatal".
2. Prefer `Material.setColor(name, color)` for color slots — it takes `APJS.Color` directly. `setVector(name, Vector4f)` is the older equivalent and still works.
3. Use `MaterialPropertyBlock.setVector(name, Vector4f)` for per-instance color overrides — `MaterialPropertyBlock` does not expose `setColor`.
4. Always null-check `renderer` and `renderer.mainMaterial` before use
5. `Material` is a valid `@serializeProperty` resource type — wire the asset directly when one script mutates it
6. `getBoundingBox()` returns AABB for spatial queries
