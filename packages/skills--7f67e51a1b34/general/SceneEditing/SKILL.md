---
name: SceneEditing
description: 场景编辑操作说明 - 使用 edit_by_dsl 批量创建和修改场景对象、组件、资源及 RenderGroup，包含 alias/$ref 引用、Prefab、材质、脚本、VFX 和失败恢复规则。
---

# SceneEditing

Use this skill whenever you need to create or modify scene objects, components, assets, render groups, prefab instances, material resources, VFX source resources, or script registrations through `edit_by_dsl`.

This skill is the entry point for scene-editing DSL usage. Do not use `query_knowledge` to discover DSL command syntax; `query_knowledge` is only for object, component, and resource facts.

`edit_by_dsl` runs a JSON `commands` array. Each command must include:

- `command_type`: the logical edit action
- `params`: command payload
- `alias` is optional; later commands can reference it with `$ref`

`commands` must be a native JSON array of command objects. Stringified JSON,
single-object shorthand, unknown command fields, and unknown command parameters
are rejected.

This skill focuses on scene, component, asset, render-group, material, and VFX editing. It does not include template-specific or library-based flows.

## Command Shape

`edit_by_dsl` receives:

```json
{
  "commands": [
    {
      "command_type": "add_builtin_object",
      "params": {},
      "alias": "optional_alias"
    }
  ]
}
```

Each command must include `command_type` and `params`. `alias` is optional and can be referenced later in the same batch with `$ref`.

`set_component` accepts these target forms:

- `guid: "<component-guid>"`
- `guid: {"$ref":"<scene-object-alias>", "component_type":"Image"}`

When starting from a scene object, use an alias plus `$ref` and `component_type` so the DSL can resolve the component GUID. A plain `{guid, component_type}` object is not accepted.

## alias / $ref

`edit_by_dsl` supports sequential alias references inside one batch:

- `{ "$ref": "host" }` -> resolve the aliased result GUID
- `{ "$ref": "host", "component_type": "Transform" }` -> resolve the component GUID on that object
- `{ "$ref": "bundle", "field": "_auto_created" }` -> extract GUID or GUID array from a prior result field
- `{ "$ref": "host", "type": "SceneObject" }` -> preserve a typed ref object for serialized property wiring

Do not use dot syntax inside the `$ref` string to combine alias and component type, such as `"bg.ScreenTransform"`. `component_type` must be passed as a separate field. The `$ref` string itself can only be an alias or literal GUID.

If `$ref` does not match a prior alias, the tool treats the ref string as a literal existing GUID. For `component_type` lookups, it falls back to `GetSceneObject(guid)` when the aliased result itself does not carry a `components` array.

## Supported Commands

| command_type | Purpose | Key params |
| --- | --- |
| `add_builtin_object` | Create a menu builtin/object-template scene object, including `Empty Object` | `object_type`, `name?`, `parent?` |
| `add_scene_object` | Create a low-level scene object | `name`, `parent?`, `type?`; use `type:"Transform"` only for raw Transform hosts, not `type:"Empty Object"` |
| `add_scene_object_from_asset` | Instantiate an object from an asset | `asset` |
| `set_scene_object` | Update scene-object properties | `guid`, `properties[]` |
| `delete_scene_object` | Delete a scene object | `guid` |
| `duplicate_scene_object` | Duplicate a scene object | `guid` |
| `move_scene_object` | Re-parent or reorder a scene object | `guid`, `parent`, `above_scene_object?` |
| `add_component` | Add a component to an existing scene object | `scene_object`, `type` |
| `set_component` | Update properties on an existing component; never adds components | `guid`, `properties[]` |
| `delete_component` | Delete a component | `guid` |
| `import_resource` | Import a local source asset into the project | `path` |
| `add_builtin_resource` | Create a built-in resource | `resource_type`, `name?` |
| `create_prefab_from_object` | Create a prefab asset from an existing scene object | `guid`, `consume_source?` |
| `instantiate_prefab` | Instantiate a prefab asset into the current scene | `guid`, `parent?` |
| `set_resource_properties` | Update asset/resource properties | `guid`, `properties[]` |
| `delete_resource` | Delete an asset/resource | `guid` |
| `move_asset` | Move or reorganize an asset/resource | `guid`, `folder` |
| `add_render_group` | Create a render group | `name`, `type?` |
| `set_render_group` | Edit render-group properties | `guid`, `properties[]` |
| `delete_render_group` | Delete a render group | `guid` |
| `duplicate_render_group` | Duplicate a render group | `guid` |
| `move_render_group` | Reorder or relocate a render group | `guid`, `target?` |
| `create_shadertoy_material` | Create and compile a ShaderToy Raster Pipeline material | `material_path`, `content`, `overwrite?` |
| `get_material_status` | Wait for the compile result matching the current `.omtl` file bytes | `material_path`, `timeout_ms?` |
| `import_glsl` | Convert a single-pass fullscreen GLSL shader into a PostProcess custom material | `glsl`, `material_name?` |
| `configure_post_process_custom` | Enable `Custom` on a PostProcess component and bind the material | `guid`, `material_guid`, `mesh_guid?` |
| `add_vfx_source` | Create a `.vfxsrc` resource | `name`, `manifest.effect?`, `systems[]`, `shared_resources?` |
| `edit_vfx_source` | Edit a `.vfxsrc` file entry | whole-file: `vfx_name`, `path`, `content`; scoped JSON/text edit: `vfx_name`, `scope`, `patch|content`; system ops: `vfx_name`, `op:add_system|delete_system`, `system_name`, `template?`, `defines?`, `uniforms?`, `resources?`, `events?`, `shared_pool_with?`, `shader_overrides?`, `runtime?` |
| `add_script` | Create and register a new script file | `script_name`, `code`, `target_guid?` |
| `edit_script` | Replace and compile an existing script resource | `guid`, `code` |
| `delete_script` | Delete an unattached script asset | `guid` |

Built-in resources already shipped by the editor do not appear in `list_resources`.
Query them by exact name, for example
`query_knowledge(category="resource", resource_type="Sphere.mesh")`, and use the
returned GUID directly. Use `add_builtin_resource` only for resource types that the
knowledge result explicitly marks as creatable.

Traditional OMTL authoring no longer goes through a dedicated add/edit material DSL command. Edit `Assets/Materials/**/*.omtl` natively, then run `get_material_status` through `edit_by_dsl` before binding or previewing that file. Use `create_shadertoy_material` only for first creation of ShaderToy Pipeline materials, and `import_glsl` only for single-pass fullscreen GLSL import.

For menu objects such as `Empty Object`, `2D Scene Object`, `Screen Image`, `2D Text`, `Audio Player`, `Cube`, `Sphere`, `Camera`, or lights, prefer `add_builtin_object`. Do not replace a known menu object with `add_scene_object + add_component`.

Use `add_scene_object(type:"Transform")` only when you need a plain Transform host, such as a VFX host object that will receive a `VFXEffectBlock` component.

## Prefab Conventions

- Two-step workflow: `create_prefab_from_object` produces a **prefab asset GUID**; `instantiate_prefab` consumes that asset GUID and returns a **SceneObject GUID**. The two GUIDs are different kinds of ids.
- Prefer prefabs over `duplicate_scene_object` when you need a pool of identical actors such as enemies, coins, bullets, obstacles, or fish.
- One batch, many instances: use `alias` + `$ref` to create one prefab and spawn N copies in the same `edit_by_dsl` call. Prefer `consume_source: true` when the source object is only a temporary authoring scaffold.
- If the project already contains a prefab, do not recreate it. Use `list_resources({ type_filter: "Prefab" })`, then feed that GUID directly to `instantiate_prefab`.
- Runtime spawning is a separate path from build-time DSL fan-out: wire a script field as `@serializeProperty APJS.Prefab`, then call `prefab.instantiate(parent)` in TypeScript.
- Library-style prefab-package import flows are out of scope for this skill. 当前像塑工具集支持本地 Prefab 创建、实例化和工程内复用。

### Example: one source object -> one prefab asset -> many scene instances

```json
[
  { "command_type": "add_builtin_object", "params": { "object_type": "Cube", "name": "Enemy" }, "alias": "src" },
  { "command_type": "create_prefab_from_object", "params": { "guid": { "$ref": "src" }, "consume_source": true }, "alias": "pf" },
  { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "pf" } }, "alias": "e1" },
  { "command_type": "instantiate_prefab", "params": { "guid": { "$ref": "pf" } }, "alias": "e2" }
]
```

### Example: runtime prefab spawn in script

```typescript
@serializeProperty bullet!: APJS.Prefab;
@serializeProperty spawnAnchor!: APJS.SceneObject;

private spawnOne(): void {
  if (!this.bullet || !this.spawnAnchor) return;
  const obj = this.bullet.instantiate(this.spawnAnchor);
  if (!obj) return;
}
```

## Fast Path: Menu Builtin Objects

For object templates that already exist in the menu, such as `Empty Object`, `2D Scene Object`, `Sphere`, `Cube`, `Plane`, `Camera`, `Directional Light`, `Point Light`, `Spot Light`, `Environment Light`, `Screen Image`, `2D Text`, `Audio Player`, and host-supported built-in particles, prefer `add_builtin_object`.

- Do not degrade these requests into manual `add_scene_object + add_component` assembly.
- By default, converge creation into one `edit_by_dsl` batch.
- Only append `move_scene_object`, `set_scene_object`, or `set_component` in the same batch when parent-child adjustment or property updates are actually needed.

## UI Object Authoring Notes

These rules only describe command organization when creating UI objects through the DSL. Full visual requirements still come from the loaded workspace rules and current workflow.

- `Screen Image` is created with a built-in texture. Visible UI panels, buttons, icons, and gameplay backplates must bind real texture / backplate assets in the same logical concern. Transparent hit areas must hide the image or make it fully transparent. During acceptance, use `inspect` to compare the texture against the asset list, then verify by screenshot.
- Prefer semantic parent-child structure: button text under the button backplate, panel title / rules under the panel, icons and feedback under their owning carrier. Only siblings under the same parent should rely on creation order or `sortOrder` such as background / backplate / mask -> icon / button visuals -> text / transient feedback.

## Example: Create a Builtin Sphere

```json
{
  "commands": [
    {
      "command_type": "add_builtin_object",
      "params": {
        "object_type": "Sphere",
        "name": "PreviewSphere"
      }
    }
  ]
}
```

## Example: Create an Empty Host Object

```json
{
  "commands": [
    {
      "command_type": "add_builtin_object",
      "params": {
        "object_type": "Empty Object",
        "name": "PreviewRoot"
      },
      "alias": "root"
    },
    {
      "command_type": "set_component",
      "params": {
        "guid": {
          "$ref": "root",
          "component_type": "Transform"
        },
        "properties": {
          "localPosition": {
            "x": 0,
            "y": 1,
            "z": 0
          }
        }
      }
    }
  ]
}
```

## Example: Import and Bind a Resource

```json
{
  "commands": [
    {
      "command_type": "import_resource",
      "params": {
        "path": "/absolute/path/to/example.png"
      },
      "alias": "tex"
    },
    {
      "command_type": "set_component",
      "params": {
        "guid": "<component-guid>",
        "properties": [
          {
            "property": "mainTexture",
            "value": {
              "type": "Resource",
              "data": {
                "guid": {
                  "$ref": "tex"
                }
              }
            }
          }
        ]
      }
    }
  ]
}
```

## Component Targets

`set_component` only updates a component that already exists. It does not add a
missing component. The `component_type` field inside a `$ref` is only a lookup
hint used to resolve the existing component GUID:

```json
{
  "guid": {
    "$ref": "host",
    "component_type": "Image"
  },
  "properties": {
    "enabled": true
  }
}
```

Use `add_component` for an addable component that is missing. `Transform` and
`ScreenTransform` are object foundation types rather than interchangeable
optional components; create the object with the appropriate builtin object type
such as `2D Scene Object` or `Screen Image` instead of trying to add a
`ScreenTransform` to an incompatible object.

`set_component.params.guid` must be either a real component GUID or an object-plus-component resolver.

Correct:

```json
{
  "guid": {
    "$ref": "button",
    "component_type": "Text2D"
  },
  "properties": {
    "text": "Start"
  }
}
```

Correct with an existing scene-object GUID:

```json
{
  "guid": {"$ref": "<scene-object-guid>", "component_type": "Image"},
  "properties": {}
}
```

Do not pass a scene-object GUID as `guid` and put `component_type` beside it at the top level.
Top-level `component_type` does not convert an object GUID into a component GUID.

## Script And Material Boundaries

- `add_script` creates and registers a new script only.
- `edit_script` replaces an existing `Assets/**/*.ts|js` script. It does not
  create missing files or attach components. Pass the Script resource GUID,
  not a path or script name. The filename and exported class name must match.
- `add_script` and `edit_script` wait for editor compilation. A compile failure
  fails the batch, marks the command result as `status:"error"`, and exposes
  the full diagnostic once in that result item's `error` field.
  `_compile_check.has_errors` is the batch-level verdict. Both commands use a
  fixed 15-second compile timeout.
- Use `run_otsc_check` for an independent full-project compile verification,
  then use `get_script_logs` for runtime diagnostics.
- `delete_script` accepts only the Script resource `guid`. Remove attached
  script components before deleting the script asset.
- Traditional OMTL authoring uses native edits under
  `Assets/Materials/**/*.omtl`, followed by
  `edit_by_dsl.command_type="get_material_status"` for the exact current bytes.
- `create_shadertoy_material` is the first-creation path for ShaderToy pipeline
  materials. `import_glsl` accepts `glsl` and optional `material_name`.
- Material and script failures are reported on the matching batch result item.
  A result with `success:false` makes the batch fail.

## Batch Discipline

- One `edit_by_dsl` batch should cover one logical concern.
- Use small batches for unfamiliar components, imports, script registration, resource binding, VFX, prefab wiring, or parent changes.
- After a successful batch that changes visible objects, images, text, prefabs, masks, UI, or render order, verify with `capture_preview` before continuing to the next visual batch.
- Use `get_scene` / `inspect` to confirm GUIDs, components, parent-child relationships, render groups, and resource bindings. They do not replace screenshot validation.

## Failure Handling

When `edit_by_dsl` returns `success:false`, `failed > 0`, `status:"error"`, or `status:"partial"`:

1. Treat the current batch as not accepted.
2. Read the error message, failed command, and skipped count.
3. Classify the failure as JSON shape, parameter name, component type, GUID / `$ref`, resource binding, schema mismatch, compile failure, runtime fallout, or host capability.
4. If the failure is schema-related, query `query_knowledge` for the specific object, component, or resource schema with a complete English query.
5. Fix the DSL and retry the same logical concern.
6. If the failure proves the current implementation route is unsupported, read the relevant Skill, APJS type, or example, then re-plan with an internally supported route that preserves the original plan.

Do not call `capture_preview` to accept a failed or partially failed batch. Do not silently switch to a weaker visual or semantic substitute when the original route fails; if the target or user-visible result must change, stop and report the difference before continuing.

## Import And Binding

`import_resource` imports a local file into the project. It does not automatically bind the result to a scene object unless the command result explicitly says so. After import, capture the returned resource GUID, then bind it with the appropriate component or asset command.

Always verify visible Image / Text / Material / VFX / Audio bindings against the asset plan before screenshot acceptance.

## VFX Source Commands

`add_vfx_source` and `edit_vfx_source` are `command_type` values inside `edit_by_dsl`; they are not standalone MCP tools. Use the VFX or VFXAuthoring skill for effect-design decisions and template-specific authoring patterns.

Supported VFX source edit shapes include:

- whole-file edit: `vfx_name`, `path`, `content`
- scoped edit: `vfx_name`, `scope`, `patch|content`
- system ops: `vfx_name`, `op:add_system|delete_system`, `system_name`, optional `template`, `defines`, `uniforms`, `resources`, `events`, `runtime`
- structured `add_vfx_source` with `manifest.effect`, `systems[]`, and `shared_resources`

## Current Limits

- `instantiate_model` is not available through `edit_by_dsl`; use the ModelImport skill's `import_resource + list_resources / inspect + add_scene_object_from_asset` flow.
- Template-specific commands and planning helpers are outside SceneEditing. Use the corresponding ability or assets skill.
- `edit_vfx_source(scope/patch)` supports `manifest`, `system:<name>`, `system:<name>:defines|resources|uniforms|events|runtime`, `system:<name>:shader:<file>`, and `resources:<path>`.
- `edit_vfx_source(op:add_system|delete_system)` can add or remove systems; `add_system` expands the `StandardQuad / StandardMesh / StandardAnimatedMesh / PhysicsMesh` templates inside an existing `.vfxsrc`.
- `add_vfx_source({name, manifest, systems, shared_resources})` supports the bundled templates through each system's `template` field.
- `edit_vfx_source(delete_system)` deletes manifest and system files only. It does not automatically clean custom event adapter code inside existing system shaders; run compile and preview verification after deletion.
- If a required DSL command is missing, extend the DSL command registry instead of embedding ad hoc behavior into a skill.
