---
name: ComponentAccess
description: 在 APJS 脚本中获取 SceneObject 的组件、Transform 和父子节点，并安全访问常用组件属性。
---

# Component Access

## Getting Components

Use `getComponent(typeName)` with a string type name and cast with `as`:

```typescript
const transform = this.getSceneObject().getTransform();
const meshRenderer = this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;
const image = this.getSceneObject().getComponent("Image") as APJS.Image;
const text = this.getSceneObject().getComponent("Text") as APJS.Text;
const screenTransform = this.getSceneObject().getComponent("ScreenTransform") as APJS.ScreenTransform;
const camera = this.getSceneObject().getComponent("Camera") as APJS.Camera;
const rigidBody2D = this.getSceneObject().getComponent("RigidBody2D") as APJS.RigidBody2D;
const boxCollider2D = this.getSceneObject().getComponent("BoxCollider2D") as APJS.BoxCollider2D;
const animator = this.getSceneObject().getComponent("Animator") as APJS.Animator;
```

> Use the APJS class name in `getComponent()`: `getComponent("Text")`, `getComponent("MeshRenderer")`, `getComponent("Camera")`, etc.

## SceneObject API

| Method / Property | Type | Description |
|-------------------|------|-------------|
| `getComponent(type)` | `Component \| null` | Get component by type string |
| `getComponents(type?)` | `Component[]` | Get all components (optionally filtered by type) |
| `addComponent(type)` | `Component \| null` | Add a new component |
| `removeComponent(comp)` | `boolean` | Remove a component |
| `getTransform()` | `Transform` | Shortcut for Transform component |
| `getChild(name)` | `SceneObject \| null` | Find child by name |
| `getChildren()` | `SceneObject[]` | Get all direct children |
| `parent` | `SceneObject \| null` | Get/set parent |
| `enabled` | `boolean` | Read the local/self flag; do not assign it for SceneObject show/hide |
| `isEnabledInHierarchy()` | `boolean` | Read effective runtime visibility through the ancestor chain |
| `setEnabledInHierarchy(value)` | `void` | Canonical SceneObject show/hide API |
| `name` | `string` | Object name (read-only) |
| `clone()` | `SceneObject` | Deep clone the object |
| `layer` | `number` | Get/set render layer |

## Transform (3D)

| Property | Type | Description |
|----------|------|-------------|
| `localPosition` | `Vector3f` | Position relative to parent |
| `localRotation` | `Quaternionf` | Rotation relative to parent |
| `localEulerAngles` | `Vector3f` | Euler angles in degrees (see convention below) |
| `localScale` | `Vector3f` | Scale relative to parent |

> **Euler angle convention** (degrees): X = pitch (+UP / -DOWN), Y = yaw (+LEFT / -RIGHT), Z = roll. This means positive X rotates the object's forward direction upward. For a Camera, positive X looks toward the sky. See `skills_root/ability/Camera/SKILL.md` for details.
| `getWorldPosition()` | `Vector3f` | World-space position |
| `setWorldPosition(pos)` | `void` | Set world-space position |
| `getWorldRotation()` | `Quaternionf` | World-space rotation |
| `setWorldRotation(rot)` | `void` | Set world-space rotation |
| `getWorldEulerAngles()` | `Vector3f` | World-space euler angles |
| `setWorldEulerAngles(euler)` | `void` | Set world-space euler angles |
| `getWorldScale()` | `Vector3f` | World-space scale |

## Common Component Properties

### MeshRenderer
- `materials`: Material[]
- `mainMaterial`: Material | null — shortcut for materials[0]
- `mesh`: Mesh
- `enabled`: boolean
- For material color: `renderer.mainMaterial?.setVector("_AlbedoColor", new APJS.Vector4f(r, g, b, a))` — NOT `setVector4` (doesn't exist)

### Image
- `color`: Color
- `sprite`: Texture
- `enabled`: boolean

## Rules

1. **MUST** use string type names with `getComponent()`, not class references
2. **MUST** cast the result with `as APJS.TypeName`
3. **Always** null-check after `getComponent()` before using
4. For Transform, prefer `getTransform()` shortcut over `getComponent("Transform")`
5. When setting vector properties, create new instances: `transform.localPosition = new APJS.Vector3f(x, y, z)`
6. Do NOT modify vector components in-place — always assign a new vector
7. For SceneObject visibility, write with `setEnabledInHierarchy()`. Read `.enabled` for local state or `isEnabledInHierarchy()` for effective visibility; component-level `.enabled` remains valid.

### Correct vs Incorrect

```typescript
// CORRECT — assign new vector
const pos = transform.localPosition;
transform.localPosition = new APJS.Vector3f(pos.x + 1, pos.y, pos.z);

// INCORRECT — in-place modification won't work
transform.localPosition.x += 1; // This does NOT update the transform!
```

## Accessing Other Objects

```typescript
// By parent/child hierarchy
const parent = this.getSceneObject().parent;
const child = this.getSceneObject().getChild("ChildName");
const children = this.getSceneObject().getChildren();

// Recursive component search
const allColliders = this.getSceneObject().getComponentsRecursive("BoxCollider2D");
```
