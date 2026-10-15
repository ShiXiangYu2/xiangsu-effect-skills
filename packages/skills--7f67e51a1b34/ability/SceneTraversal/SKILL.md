---
name: SceneTraversal
description: 通过脚本实现场景遍历 - 在运行时查找和遍历场景层级、切换对象可见性、克隆对象、管理对象池，以及动态增删组件。
---

# Scene Traversal

Patterns for navigating and manipulating the scene hierarchy at runtime.

## SceneObject Hierarchy Methods

| Method / Property | Returns | Description |
|-------------------|---------|-------------|
| `getChildren()` | SceneObject[] | All direct children |
| `getChild(name)` | SceneObject \| null | First child with matching name |
| `getTransform().getParent()` | Transform | Parent's transform |
| `enabled` | boolean | Read local/self state; not the effective hierarchy state |
| `isEnabledInHierarchy()` | boolean | Read effective runtime visibility through ancestors |
| `setEnabledInHierarchy(value)` | void | Canonical SceneObject show/hide API |
| `name` | string | Object name |

## Getting Children

```typescript
const children = this.getSceneObject().getChildren();
for (const child of children) {
  console.log(child.name);
}
```

## Finding a Child by Name

```typescript
const label = this.getSceneObject().getChild("Label");
if (label) {
  const text = label.getComponent("Text") as APJS.Text;
  text.text = "Found!";
}
```

**NOTE**: `getChild()` only searches direct children, not recursive. For deeper nesting, chain calls:
```typescript
const grandchild = this.getSceneObject().getChild("Parent")?.getChild("Child");
```

## Toggle Visibility of Children

```typescript
@component()
export class ToggleChildren extends APJS.BasicScriptComponent {
  @serializeProperty
  private container: APJS.SceneObject;

  private showChildren: boolean = true;

  toggle(): void {
    this.showChildren = !this.showChildren;
    const children = this.container.getChildren();
    for (const child of children) {
      child.setEnabledInHierarchy(this.showChildren);
    }
  }
}
```

## Show/Hide Specific Children by Index

```typescript
@serializeProperty
private items: APJS.SceneObject[] = [];

private showOnly(index: number): void {
  for (let i = 0; i < this.items.length; i++) {
    this.items[i].setEnabledInHierarchy(i === index);
  }
}
```

## Iterate and Get Components from Children

```typescript
onStart(): void {
  const children = this.getSceneObject().getChildren();
  for (const child of children) {
    const image = child.getComponent("Image") as APJS.Image;
    if (image) {
      image.opacity = 0.5;
    }
  }
}
```

## Local vs Hierarchy State

- Use `sceneObject.setEnabledInHierarchy(false)` to hide a SceneObject at runtime. Descendants become effectively hidden without changing their local `enabled` flags.
- `setEnabledInHierarchy(value)` also updates that SceneObject's own local `enabled` flag to `value`.
- Read `sceneObject.enabled` when a pool or state machine needs the object's local requested state.
- Use `sceneObject.isEnabledInHierarchy()` when logic needs to know whether the object is effectively visible through its ancestor chain.
- `component.enabled` is still the correct API when intentionally toggling one component rather than its SceneObject.

## Scene-Level API

Access via `this.getSceneObject().scene`.

| Method | Returns | Description |
|--------|---------|-------------|
| `scene.findSceneObject(name)` | SceneObject \| null | Find by name (searches entire scene) |
| `scene.getAllSceneObjects()` | SceneObject[] | All objects in the scene |
| `scene.createSceneObject(name)` | SceneObject | Create new empty object (parent=null) |
| `scene.removeSceneObject(obj)` | boolean | Destroy an object |

## Runtime Clone & Object Pooling

### SceneObject.clone()

`clone()` creates a deep copy of the object including all components.

```typescript
const original = this.getSceneObject();
const copy = original.clone();
// copy has same parent, same components, same properties
```

**WARNING**: `clone()` copies ALL components including scripts. If the script triggers cloning, this creates infinite recursion and crashes the preview. **Always put the cloning script on a separate controller object, NOT on the template being cloned.**

### Object Pool Pattern

Pre-create hidden clones, show/hide to reuse:

```typescript
@component()
export class Pool extends APJS.BasicScriptComponent {
  @serializeProperty
  template!: APJS.SceneObject;

  private pool: APJS.SceneObject[] = [];
  private initialized = false;

  onUpdate(dt: number): void {
    if (!this.initialized && this.template) {
      this.initialized = true;
      for (let i = 0; i < 10; i++) {
        const obj = this.template.clone();
        obj.setEnabledInHierarchy(false);
        this.pool.push(obj);
      }
      this.template.setEnabledInHierarchy(false);
    }
  }

  acquire(x: number, y: number): APJS.SceneObject | undefined {
    if (this.pool.length === 0) return undefined;
    const obj = this.pool.pop()!;
    obj.setEnabledInHierarchy(true);
    const st = obj.getComponent("ScreenTransform") as APJS.ScreenTransform;
    if (st) st.anchoredPosition = new APJS.Vector2f(x, y);
    return obj;
  }

  release(obj: APJS.SceneObject): void {
    obj.setEnabledInHierarchy(false);
    this.pool.push(obj);
  }
}
```

### Runtime addComponent / removeComponent

```typescript
const rb = obj.addComponent("RigidBody2D"); // returns Component | null
obj.removeComponent(rb);                     // returns boolean
```

## Rules

1. `getChild(name)` is direct children only — not recursive
2. `getChildren()` returns a snapshot array — safe to modify children while iterating
3. Prefer `@serializeProperty` for known references; use `getChild()`/`getChildren()` for dynamic content
4. Setting `enabled = false` on a parent hides all descendants
5. `clone()` copies ALL components including scripts — put cloning logic on a separate controller object
6. Use `scene.findSceneObject(name)` to find objects by name — NOT `scene.getSceneObject()`
7. Use `scene.removeSceneObject(obj)` to destroy objects — NOT `obj.destroy()`
