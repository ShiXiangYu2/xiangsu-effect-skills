---
name: ImageGeneration
description: 为当前工程生成并导入单张图片，重点指导提示词、尺寸、透明背景、参考图，以及适合场景布局的素材拆分。多张图片使用 AssetBatchGeneration。
---

# ImageGeneration

`generate_image` creates **one** image asset and imports it into the current
project.

If the request contains **multiple** new images, or a mixed image/audio asset
set, switch to `AssetBatchGeneration` and keep this skill only for per-image
prompt design.

> **Scope:**
> - This is a **single-image** workflow.
> - For multiple images or mixed image/audio requests, use
>   `AssetBatchGeneration`.
> - You write the prompt directly for the target asset. The prompt is recorded
>   in tool results for review, but it must not be used as the asset name.
> - Before generating a background or playfield, apply the scenario table in
>   `context.workspace.rules/scene-common.md` → “摄像头与背景”. It defines
>   which scenes prohibit full-screen backgrounds and which require person
>   preservation. This skill supplies prompt and asset-splitting techniques.
> - Use `need_seg=true` when the result should be imported as an isolated
>   transparent-background element. This requests transparent pixels in the
>   generated PNG; it is not permission to lower the placed object's opacity.
> - `need_seg=true` is for isolated subjects or local UI / gameplay pieces; do
>   **not** use segmentation to fake a person-derived full-screen background.
> - `reference_image_paths` only accepts real local file paths visible to the
>   agent. Existing project assets can inform the prompt via `preview_asset` or
>   `inspect`, but they are not direct reference paths unless you truly have
>   the underlying files.
> - It does not parse long design briefs or run moderation-recovery orchestration.

## When to use this skill

Use this skill when the job is "make me an image asset":

- icon / sticker / UI badge / prop art / portrait cutout
- 2D element with transparent background
- texture-like source image or material source image
- one reusable tile / cell / divider / board piece for later composition
- one reference-style concept image for later use

If the task is fundamentally vector geometry, prefer the SVG path. If the task
is shader or post-process authoring, switch to `MaterialAuthoring`.

## Minimal workflow

1. Decide the asset type and runtime use: isolated element, solid UI panel/card, texture, reusable layout piece, permitted replacement background, or standalone concept image. Check scene background rules before treating a full-frame image as a runtime asset.
2. Decide the intended aspect ratio and pass `width` / `height` when it matters.
3. Write a concise but complete prompt: **asset role -> subject -> style/material
   -> view/composition -> background/alpha -> quality constraints**.
4. If needed, attach `reference_image_paths`.
5. If the result should be a clean cutout, set `need_seg=true`.
6. Call `generate_image`.

## Prompt rules

### 1. Lead with the subject

The first phrase should tell the model what the image is.

- Better: `单个卡通火焰按钮图标，明亮橙红色，正视图，边缘清晰`
- Worse: `高质量，细节丰富，风格统一，明亮配色`

### 2. Keep a complete prompt, not a label

Do not pass only the asset label or a vague two-word description. The prompt
must include the facts needed to judge the output later. Keep it concise, but
cover the constraints that actually decide the image:

- intended use (`button base`, `fish sprite`, `hit effect`, `local playfield base`)
- subject
- style or material
- view / composition
- background / transparency expectation
- one or two important quality notes such as clean silhouette, readable inner
  area, high contrast, or no text

### 3. Say the view when composition matters

If the asset must be centered, orthographic, top-down, or front-facing, state
it explicitly.

Examples:

- `正视图`
- `俯视图`
- `居中构图`
- `无透视`
- `单个主体`

### 4. Ask for isolation when you need a cutout

For icons, stickers, UI elements, or props to be placed later, describe the
image as an isolated subject and set `need_seg=true`.

Good prompt core:

`单个机械宝箱，卡通渲染，正视图，主体完整，边缘清晰`

Only request a transparent background when the asset is meant to be a cutout,
sticker, UI plate, sprite, mask, or overlay. For opaque texture sources and
solid panels, keep the image itself opaque unless the plan explicitly says the
asset should be glass, smoke, glow, mask, or another transparent layer.

### 5. Use reference images as anchors, not as a substitute for prompt text

Reference images help lock style, silhouette, or palette. Still state the
target subject and composition in words.

### 6. Match the output size to the intended use

- square icon / sticker: use `width=1024`, `height=1024` unless another ratio is needed
- banner / wide plate: set a wider ratio explicitly
- tall portrait element: set a taller ratio explicitly

### 7. Keep layout-critical pieces reusable

If the image will become one cell / tile / divider / slot / mud block / lane
marker inside a strict board or lane layout:

- describe it as a **single reusable piece**
- state `无透视`, `俯视图`, `正交游戏视角`, or another explicit flat-view rule
- keep it centered and isolated
- prefer `need_seg=true`
- do **not** generate the whole board as one illustration unless that image is
  decorative only and does not determine gameplay alignment
- prefer independent gameplay elements by default; only use a local playfield
  base / board base / arena base when the Brief explicitly asks for it or the
  gameplay geometry truly needs a continuous structural carrier
- if generating a local playfield base / board base / arena base, describe it
  as a large local gameplay area for the safe region, not a tiny centered card;
  surrounding camera passthrough can stay blank or use sparse decorations
- keep a local playfield base **structural only**: no readable title / CTA /
  tutorial / rule copy, no player / enemy / projectile / collectible / hazard
  instances, and no pre-composed gameplay state; static grid / lane / slot /
  drop-zone markings are okay when they belong to the board itself

### 8. Direction-sensitive gameplay art must declare orientation

If the asset's direction affects readability, controls, or game rules, the
prompt must state:

- viewpoint (`正视图`, `俯视图`, `侧视图`, `正交游戏视角`, etc.)
- facing direction (`朝上`, `朝右`, `从左到右`, etc.)
- rotation policy (`只允许 0/180 度`, `不可任意旋转`, etc.)
- symmetry / mirroring allowance (`允许水平镜像` or `禁止镜像`)

Do not leave orientation implicit and expect downstream users to infer it from
the image.

### 9. UI containers must be solid, not hollow

For buttons, panels, info bars, cards, and CTA holders:

- ask for a solid filled shape with a readable interior area
- do **not** ask for hollow, outline-only, cutout, or glow-edge-only PNGs
- if you need decoration, generate separate solid corner / edge ornaments
  instead of one closed frame around the whole layout

### 10. Text in generated UI assets must stay readable

Prefer generating text-free UI bases, then place runtime `2D Text` on top for
rules, hints, scores, counters, and any multi-line or changing copy.

Only bake text into an image when it is a short fixed label, title, CTA, score
burst, or win/lose art text. In that case, the prompt must explicitly require:

- clear glyph edges and high contrast against the local background
- enough inner padding around the text
- no highlight, reflection, glow, flare, or particle streak crossing the glyph
  strokes in a way that makes the text hard to read

Glow, outline, reflection, and sweep-light effects are allowed as style, but the
generated result is unusable if those effects blur the strokes, overexpose the
letters, or merge the text into a busy background.

## Prompt templates

### Transparent-background element

Prompt shape:

`单个<主体>，<风格/材质>，<视角/构图>，主体完整，边缘清晰`

Tool guidance:

- set `need_seg=true`
- use a size close to the intended aspect ratio

Example:

`单个冰晶法杖图标，半写实卡通风格，正视图，居中构图，主体完整，边缘清晰`

### Solid UI panel / card

Prompt shape:

`单个<按钮/面板/信息栏/卡片>，<风格/材质>，正视图，居中构图，实体填充，留出干净文字区域，可读性优先，非镂空，非描边框，透明背景`

Tool guidance:

- set `need_seg=true`
- do **not** request outline-only or glow-only frames
- if extra decoration is needed, generate it as separate solid pieces

Example:

`单个开始按钮底板，轻卡通策略游戏 UI，正视图，居中构图，深绿色实体圆角按钮，留出干净文字区域，可读性优先，非镂空，非描边框，透明背景`

### Short fixed text UI asset

Prompt shape:

`<短文案> 文字资产，<风格>，字形边缘清晰，高对比，正视图，居中构图，反光和发光不遮挡笔画，透明背景`

Tool guidance:

- use only for short fixed labels or decorative art text
- do not use for rules, hints, dynamic scores, or multi-line copy
- if the preview text is blurry or partly covered by highlights, reject it and
  switch to a text-free base plus runtime `2D Text`

Example:

`“开始” 文字按钮资产，科幻街机 UI 风格，字形边缘清晰，亮青色文字，高对比，正视图，居中构图，轻微发光和金属反光但不遮挡笔画，透明背景`

### Standalone concept / reference illustration

Prompt shape:

`<主体>，<风格>，<光线/氛围>，<构图>`

Use this for standalone concept/reference art or a full-frame illustration
permitted by `context.workspace.rules/scene-common.md` → “摄像头与背景”.
For a replacement background, generate the environment separately from the
person-preservation mask. Keep layout-critical gameplay pieces separate as
described in “Keep layout-critical pieces reusable”.

Example:

`梦幻水下神殿入口概念图，柔和蓝绿色氛围，体积光，电影感构图`

### Texture-like source image

Prompt shape:

`<材质> texture, seamless tile, even lighting, no perspective`

Example:

`aged bronze texture, seamless tile, even lighting, no perspective, medium detail`

### Reusable board / tile piece

Prompt shape:

`单个<格子/泥土块/分隔件>，<风格/材质>，无透视，<俯视图 / 正交游戏视角>，居中构图，透明背景`

Tool guidance:

- set `need_seg=true`
- keep the aspect ratio close to the intended piece

Example:

`单个花园泥土块，轻卡通策略游戏风格，无透视，正交游戏视角，居中构图，透明背景`

### Large local playfield base

Prompt shape:

`大型局部<棋盘/水池/赛道/玩法底板>，<风格/材质>，适合作为竖屏 AR 玩法主区域，正视图或正交视角，仅底板/平台结构，无文字，无角色，无运行态玩法对象，主体完整，边缘清晰，非全屏背景，透明背景`

Tool guidance:

- use this for the main usable playfield under camera passthrough
- use it only when the Brief explicitly asks for a carrier, or when the
  gameplay geometry truly needs one; otherwise prefer separate gameplay pieces
  and decorations instead of a big base image
- the asset is local, but it should visually read as the primary gameplay area,
  not a small decorative card
- keep it text-free, actor-free, and state-free; if the board needs grid lines,
  lane lines, slot outlines, or scoring zones, describe them as static
  structural markings instead of baked gameplay actors
- leave the area outside the asset to camera passthrough, blank space, or sparse
  independent decorations

Example:

`大型局部科幻飞行赛道底板，蓝青色能量跑道材质，适合作为竖屏 AR 玩法主区域，正交游戏视角，仅底板结构，无文字，无角色，无运行态玩法对象，主体完整，边缘清晰，非全屏背景，透明背景`

## Tool-call examples

### Generate an isolated prop

```json
{
  "name": "treasure_chest_icon",
  "prompt": "单个机械宝箱图标，卡通金属质感，正视图，居中构图，主体完整，边缘清晰",
  "width": 1024,
  "height": 1024,
  "need_seg": true
}
```

### Generate a style-guided character sticker

```json
{
  "name": "hero_sticker",
  "prompt": "单个少年冒险者贴纸形象，清爽二次元风格，正视图，居中构图，主体完整，边缘清晰",
  "width": 1024,
  "height": 1024,
  "need_seg": true,
  "reference_image_paths": [
    "/absolute/path/to/hero_reference.png"
  ]
}
```

### Generate a seamless texture

```json
{
  "name": "stone_floor_texture",
  "prompt": "weathered stone floor texture, seamless tile, even lighting, no perspective, medium detail",
  "width": 1024,
  "height": 1024
}
```

## Repair loop

If the first result is off:

- Wrong subject or silhouette: rewrite the first noun phrase.
- Wrong viewpoint: add `正视图` / `俯视图` / `无透视` / `居中构图`.
- Too much background: simplify the prompt and set `need_seg=true`. For
  camera-overlay gameplay, strip the background entirely instead of asking for
  a full-frame scene.
- Style drift: remove weak adjectives and add one stronger style phrase or a
  real reference image.
- Crop / framing mismatch: adjust `width` / `height` to the intended aspect.

## Hand-off

After `generate_image` succeeds:

- The returned result includes the prompt used for generation. Use it as the
  acceptance baseline, not as part of the asset name.
- Use `preview_asset` when the returned preview / metadata is not enough to
  judge the imported result.
- If the asset does not match the intended subject, style, view, transparent
  background requirement, readability, or reusable-layout constraints, revise
  the prompt and regenerate before binding it into the scene.
- Use `edit_by_dsl` or another asset skill if the image must be bound into a
  material, screen image, or scene object next.
