---
name: ModelImport
description: 导入并放置 FBX、GLB 或 GLTF 模型，重点处理格式兼容、尺寸校准、朝向、位置和导入后不可见等问题。
---

# ModelImport

Bringing an external 3D model into the project and getting it on screen **at a
size that makes sense**. This is the most common customization request there is
("put my character in this game"), and size is where it silently goes wrong.

> **Scope:** Automatic `instantiate_model` / target-size normalization is not
> available here. Use `edit_by_dsl.import_resource(...)` + `list_resources` /
> `inspect` + `add_scene_object_from_asset`, then verify and correct the root
> Transform scale manually.

## The one rule that always applies

> **A model's default size after import is never trustworthy — regardless of
> format, and regardless of where the file came from.** The size is whatever
> the export tool baked in, and identical-looking files disagree wildly: the
> same wolf mesh arrives ~100× larger from one FBX exporter version than from
> another, and AI-generated `.glb` characters routinely arrive so small they
> are invisible. Nothing errors. The model is just wrong on screen.
>
> Therefore: **every model placement ends with a size check.** Inspect the
> placed object, `capture_preview`, and look. A placement whose size you have
> not seen is not done.

There is no automatic size normalization step here. The same rule still
applies: after `add_scene_object_from_asset`, verify the result visually and
correct the root Transform scale until it reads correctly in the scene.

## Placement workflow

1. **Import**: `edit_by_dsl` → `import_resource(path)`. Read the result:
   - `_textureNote` → the model shipped external texture files that were NOT
     imported; it will render untextured until you wire them (the note carries
     the recipe).
   - After import, `list_resources(type_filter="Model")` shows the imported
     model asset; `inspect` shows sub-assets such as `Mesh` / `Animation`.
2. **Place**: `add_scene_object_from_asset(asset="<model-guid>")`.
   - Prefer the imported **Model** asset GUID when the goal is "put this model
     into the scene".
   - **Swapping an existing character/prop?** Read the replaced object's
     current world bounds before deleting it so you have a size reference.
3. **Verify visually**: `capture_preview` (`scale: 1`). Judge against intent:
   a character next to a person should read person-ish; a prop in a hand
   should read hand-sized. If wrong, multiply the root's `localScale`
   (`set_component` on the root's Transform) — never rescale bone nodes inside
   the hierarchy.
4. **Confirm the numbers once**: if you resized manually, note the final size
   so later turns have a reference.

## Format knowledge

**Importable directly**: `.fbx` (binary and ASCII, old and new versions),
`.glb`, `.gltf`.

**Everything else must be re-exported first.** `.blend`, `.dae`, `.obj`,
`.stl`, `.usdz`, `.max`, `.ma`, `.c4d`, … are not importable; the import error
says so and names the fix (export as FBX or glTF 2.0 from the source tool).
Expect these from users — Blender project files and Sketchfab/printing
downloads are common. Two things to keep in mind when a re-export happens:

| Fact | Consequence |
|---|---|
| Source formats carry different unit conventions (some are metres, some centimetres, some have no units at all — `.obj`/`.stl` are unitless by design) | The exporter applies its own unit conversion. **The re-exported file's scale is a new unknown**, not the "same model, same size". |
| Exporter version/settings change the baked scale even for the SAME mesh and SAME target format | Never carry a size assumption across files. Two FBX files of one model can differ ~100×. |
| AI model generators (text-to-3D services) emit `.glb` at arbitrary, often millimetre, scale | The most likely "my model doesn't show up" cause for user-provided glb files. Still verify after placement. |

So the knowledge is deliberately NOT a per-format size table — such a table
would be wrong often enough to be dangerous. The knowledge is: **formats and
exporters make size untrustworthy in principle, so the size check is
unconditional.** The workflow above is identical for every format; only the
"needs re-export first" step differs.

## Other placement paths — same rule

The size rule is about *models entering the scene*, not about one command:

- `add_scene_object_from_asset` of an imported Model — check the spawned
  object's size the same way (`inspect`, then preview).
- `instantiate_prefab` of a prefab that wraps an imported model — the prefab
  carries whatever scale it was authored at; verify on first spawn.
- A model already in the project from an earlier session — its current scale
  reflects someone's past decision; read it before reusing, don't re-derive.

## Failure modes and what they mean

| Symptom | Likely cause | Action |
|---|---|---|
| Import error naming a triangle-count limit | Model too dense for the engine | Tell the user; propose decimating in the source tool, then re-import |
| Import error "not an importable model format" | Unsupported extension | Re-export as FBX / glTF 2.0 (the error names the path) |
| Model renders grey/untextured | External textures not auto-imported | Follow `_textureNote`: import each texture, wire per material |
| Model in Scene panel but absent from preview | Skinned mesh was assembled by hand from sub-assets instead of instantiating the imported Model asset | Delete the hand-built object; place via `add_scene_object_from_asset` on the imported Model asset |
| Model invisible / absurdly large after placement | Raw exporter scale | Set the root scale from measured bounds and re-verify with preview |
