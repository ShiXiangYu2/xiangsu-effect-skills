---
name: API
description: APJS的API说明： 编写 APJS 脚本前，从 workspace 中查找准确的 TypeScript 类型定义和示例，并判断何时使用 query_knowledge 或本地定义文件。
---

# Type Definitions

## When to Use
- Before writing APJS scripts, look up the exact class/interface definitions
- When you need method signatures, property types, or enum values for runtime scripting
- When you need to know the APJS class name for a component

## How to Look Up Types

When a project is attached, the `.mcp_agent` sidecar workspace should sync an `APJS/` reference pack by default.

Resolve `context.workspace.APJS` from the project's `context.json` using the
path rules in its `AGENTS.md`, then use that absolute directory for every
`APJS/...` path below. It is independent of the Agent's current working
directory. In the search examples, replace `<resolved_apjs_dir>` with that
directory before calling the file tool.

1. **Use synced `APJS/*.d.ts` files for exact signatures**
   - `APJS/APJS.d.ts` — core APJS runtime surface
   - `APJS/APJS_runtime.d.ts` — runtime-only declarations used by compile/version checks
   - `APJS/effect.d.ts` — effect runtime declarations
   - The pack also includes supplemental `.d.ts` files such as `AudioComponent.d.ts`, `PostProcess.d.ts`, `OrionDecorators.d.ts`
   - Search examples:
     - `Grep("class MeshRenderer", path="<resolved_apjs_dir>")`
     - `Grep("interface TouchData", path="<resolved_apjs_dir>")`
     - `Grep("enum AppEventType", path="<resolved_apjs_dir>")`

2. **Use synced `APJS/examples/*.json` for concrete patterns**
   - `Grep("rotation", path="<resolved_apjs_dir>/examples")`
   - `Grep("touch", path="<resolved_apjs_dir>/examples")`
   - `Grep("physics", path="<resolved_apjs_dir>/examples")`

3. **Use `query_knowledge` only for component-side hints**
   - `query_knowledge(category="component", component_type="X")` → get `set_component` property names/types and APJS class-name hints
   - API / script guide routing should come from `skills_root/SKILL.md` + `skills_root/routing/skill_manifest.json`, not `query_knowledge`
   - `query_knowledge` does not return the full APJS runtime surface for methods, enums, overloads, or editor/runtime-only members

4. **If `APJS/` is unexpectedly missing**
   - Treat that as a workspace-sync failure, not as expected behavior
   - Re-read the current project context and check the resolved APJS directory.
   - If the reference pack is still missing, stop API-dependent script edits
     and report the missing path so the host can restore workspace sync.
   - Do not fall back to a development repository's `Resources/` directory or
     another Agent workspace; neither is the current effect's reference pack.

5. **Use related guides for usage patterns**
   - `ComponentAccess` — getComponent patterns, null guards, property access
   - `Lifecycle` — onStart/onUpdate, `@component`, script template
   - `Touch` — touch events, drag patterns
   - `Animation` — frame-based animation, Animator playback

## query_knowledge vs .d.ts

`query_knowledge(category="component", component_type="X")` returns property names and types for `set_component`. However, it does **not** include APJS-only methods such as `mainMaterial`, `mainPass`, `getBoundingBox()`, or the complete enum/overload surface. Use `.d.ts` files as the source of truth for the full runtime API.

## Naming Conventions

Many math types use an `f` suffix (float precision). If a search fails, try appending `f`:

| Common Name | APJS Type |
| :--- | :--- |
| Vector2 | **Vector2f** |
| Vector3 | **Vector3f** |
| Vector4 | **Vector4f** |
| Quaternion | **Quaternionf** |
| Matrix3x3 | **Matrix3x3f** |
| Matrix4x4 | **Matrix4x4f** |
