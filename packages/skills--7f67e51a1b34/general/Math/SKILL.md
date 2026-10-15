---
name: Math
description: APJS的数学类型： 使用 Vector2f、Vector3f、Quaternionf 和 Color 处理位置、方向、旋转、插值与颜色计算。
---

# Math Types

## Vector2f

2D vector used for screen positions, UV coordinates, 2D physics.

```typescript
// Construction
const v = new APJS.Vector2f(x, y);
const zero = new APJS.Vector2f(0, 0);

// Operations (mutate and return this)
v.add(other)           // v += other
v.subtract(other)      // v -= other
v.multiply(scalar)     // v *= scalar (also accepts Vector2f for component-wise)
v.divide(other)        // v /= other
v.normalize()          // make unit length

// Non-mutating
v.clone()              // deep copy
v.magnitude()          // length
v.sqrMagnitude()       // length squared (faster, for comparisons)
v.distance(other)      // distance to other
v.dot(other)           // dot product
v.angleTo(other)       // angle in radians

// Static
APJS.Vector2f.lerp(a, b, t)  // linear interpolation, t in [0,1]
```

## Vector3f

3D vector for positions, rotations (euler), scales.

```typescript
// Construction
const v = new APJS.Vector3f(x, y, z);

// Operations (mutate and return this)
v.add(other)
v.subtract(other)
v.multiply(scalar)        // also accepts Vector3f
v.multiplyScalar(scalar)  // explicit scalar multiply
v.divide(scalar)          // also accepts Vector3f
v.normalize()
v.cross(other)            // cross product
v.inverse()               // negate
v.project(other)          // project onto other
v.projectOnPlane(normal)  // project onto plane
v.reflect(normal)         // reflect across normal

// Non-mutating
v.clone()
v.magnitude()
v.sqrMagnitude()
v.distance(other)
v.dot(other)

// Static
APJS.Vector3f.lerp(a, b, t)
APJS.Vector3f.max(a, b)   // component-wise max
APJS.Vector3f.min(a, b)   // component-wise min
```

## Quaternionf

Rotation in 3D space. Prefer euler angles for simple cases.

```typescript
// Construction
const q = new APJS.Quaternionf(x, y, z, w);

// Operations
q.multiply(other)        // combine rotations
q.multiplyVector(v)      // rotate a Vector3f
q.inverse()              // inverse rotation
q.normalize()
q.toEulerAngles()        // convert to Vector3f (degrees)
q.getAngle()             // rotation angle
q.getAxis()              // rotation axis

// Static
APJS.Quaternionf.lerp(a, b, t)
APJS.Quaternionf.slerp(a, b, t)  // spherical interpolation (smoother for rotations)
APJS.Quaternionf.angleBetween(a, b)
```

## Color

RGBA color with values in [0, 1] range.

```typescript
const color = new APJS.Color(r, g, b, a);  // all 0-1

// Common colors
new APJS.Color(1, 0, 0, 1)  // red
new APJS.Color(0, 1, 0, 1)  // green
new APJS.Color(0, 0, 1, 1)  // blue
new APJS.Color(1, 1, 1, 1)  // white
new APJS.Color(0, 0, 0, 1)  // black

color.clone()
color.equals(other)
```

## Rules

1. **`f` suffix**: Always use `Vector2f`, `Vector3f`, `Quaternionf` — not `Vector2`, `Vector3`, `Quaternion`
2. **Mutating methods**: `add()`, `subtract()`, `multiply()` etc. modify the vector in-place AND return `this`. Use `.clone()` first if you need the original:
   ```typescript
   const offset = original.clone().add(delta);  // original unchanged
   ```
3. **Euler angles** are in degrees (not radians). Convention: X = pitch (+UP / -DOWN), Y = yaw (+LEFT / -RIGHT), Z = roll. **Positive X pitches UP** (opposite of Unity)
4. **Color values** are 0-1 (not 0-255)
5. For rotation interpolation, prefer `Quaternionf.slerp()` over `lerp()` — slerp produces smoother results
