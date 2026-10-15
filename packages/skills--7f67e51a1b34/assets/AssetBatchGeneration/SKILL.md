---
name: AssetBatchGeneration
description: 批量生成多张图片、多段音频或两者的组合，等待全部任务结束后汇总各项结果。只需要单个资产时使用对应的图片或音频生成 Skill。
---

# AssetBatchGeneration

`generate_assets_batch` 用来一次生成多张图片、多段音频，或图音混合资产。每个成功项都会导入当前工程。

> **范围**
> - 这是 `generate_image` 和 `generate_audio` 的批量版。
> - 只要同一请求或同一完整效果预计需要 2 个或更多 AIGC 图片 / 音频资产，就优先使用本 skill。
> - 一次工具调用会等待所有资产完成或失败。
> - 等待期间不要创建占位图片或占位 MP3。
> - 返回结果会保留每个资产的原始 `prompt`，方便回看和验收。`name` 保持短、清楚、可读，不能把完整 prompt 塞进资产名。
> - 如果宿主支持子 agent，把本 skill 的工具调用和素材初验交给子 agent。没有子 agent 时，当前 agent 直接调用 `generate_assets_batch`，等完整结果返回后再进入下一步

## 什么时候用

满足任一条件时使用本 skill：

- 一次请求需要 2 个或更多 AIGC 资产。
- 同一批里同时有图片和音频。
- 完整特效制作中已能预见多个图片 / 音频资产，即使它们分属 UI、角色、道具、BGM 和 SFX，也先列入同一个批次。
- 用户明确说“批量”“一次生成完”，或希望拿到一份汇总结果。

如果只生成一张图片，走 `ImageGeneration`。如果只生成一段音频，走 `AudioGeneration`。

## 解决什么问题

本 skill 解决的是批量编排问题，不是单个模型请求的耗时问题：

- 减少多个资产串行等待。
- 把多个资产的生成集中到一次工具调用里。
- 宿主支持子 agent 时，可以让子 agent 负责等待和资产级验收。
- 不会让单张图片或单段音频的模型生成天然变快。

## 最小流程

1. 先把需求整理成一个 `assets` 数组。完整特效制作时先列本轮预计需要的新图片、BGM、SFX 和反馈音，再一次提交；不要边搭场景边逐个调用 `generate_image` / `generate_audio` 补资产。
2. 如果宿主支持子 agent，启动子 agent 负责本批资产。子 agent 调用 `generate_assets_batch({assets:[...]})`，等待完整结果，检查素材是否可用，再把可用项和需重试项回报给主 agent。
3. 如果没有子 agent，当前 agent 调用一次 `generate_assets_batch({assets:[...]})`，等待完整结果。
4. 工具返回后逐项验收：
   - 按资产名、prompt、用途、视角 / 朝向、透明要求、风格检查完成项；`success=true` 或状态完成不等于资产可用。
   - 只继续使用已经能判断合格的资产。
   - 如果返回结果不足以判断某个资产，再只对这个资产调用 `inspect` 或 `preview_asset`。
   - 这里做的是资源级验收。场景绑定和运行态验证还要在后续流程里完成。
   - 失败或跑偏的资产要调整 prompt 重新生成，不能把不合格资产硬挂进场景。

## 格子、棋盘和车道类资产

格子、车道、棋盘、草坪、土块类玩法，默认要拆成可组合素材包，而不是一张承载布局的完整插画。

推荐拆分：

- 局部玩法底板或玩法岛。
- 可复用的单个格子、土块或地块。
- 行分隔、车道分隔、边缘条或端帽。
- 可选的分数栏、信息板、按钮底板。
- 可选的局部装饰、角标、遮罩或高亮块。

规则：

- **局部玩法承载件语义**：局部玩法底板只在 Brief 明确指出，或玩法几何确实需要连续承载结构时才生成。
- 具体 prompt 约束沿用 `ImageGeneration` 的 `Large local playfield base` 模板。
- 是否允许全屏背景及人像保留要求，统一按 `context.workspace.rules/scene-common.md` 的“摄像头与背景”判断。
- 影响点击区域、占位、车道读取、生成 / 失败对齐、视觉校准的图层，都要单独生成。
- 可复用组件通常使用 `need_seg=true`；图片 prompt 的通用写法沿用 `ImageGeneration`，至少写清资产角色、主体、风格 / 材质、视角 / 构图、背景 / 透明要求，以及和玩法相关的关键约束。
- 对于格子、泥土块、分隔件、车道块、底板等可复用组件，prompt 里必须明确 `单个主体`、`无透视`、`俯视图` / `正交游戏视角`、`居中构图` 等约束；朝向会影响可读性或玩法时，再补充朝向、旋转策略和是否允许镜像。
- UI 面板、信息条、卡片和按钮仍要生成实体填充底板；装饰元素拆成独立实体素材，不要做一圈包住全屏的闭合边框。

## 输入格式

每个资产项都要声明 `kind`。

图片项：

- `kind="image"`
- `name`
- `prompt`
- 可选：`width`、`height`、`need_seg`、`reference_image_paths`、`timeout_ms`

音频项：

- `kind="audio"`
- `name`
- `prompt`
- 可选：`timeout_ms`

## 分流规则

- 多张图片：使用本 skill。
- 多段音频：使用本 skill。
- 图片和音频混合：默认使用本 skill。
- 单个资产需要反复调 prompt：优先使用单资产 skill。

## 返回结果怎么看

批量结果包含：

- 整体状态：`completed` 或 `completed_with_failures`。
- 每个资产的状态。
- 每个资产的原始生成 prompt。
- 成功和失败数量。
- 成功项的导入资产信息。

不要只凭猜测的名字开始绑定资产。必须等返回结果里有真实导入信息，再结合预览、试听或元信息判断资产是否可用。

批量完成只说明资产文件已经生成并导入，不代表这些资产已经适合直接放进场景。

如果某个生成结果在视觉或语义上跑偏，改 prompt 后重新生成。不要靠缩放、透明度或运行时遮罩去掩盖一个错误素材。

## 示例

### 生成一批图音混合资产

```json
{
  "assets": [
    {
      "kind": "image",
      "name": "EnemyDrone",
      "prompt": "original red and orange hostile drone fighter sticker, top-down arcade shooter view, compact body, transparent background",
      "width": 1024,
      "height": 1024,
      "need_seg": true
    },
    {
      "kind": "audio",
      "name": "BattleBGM",
      "prompt": "紧张压迫的街机空战背景音乐（响亮, 循环自然, 约20s）"
    }
  ]
}
```

### 生成适合布局的棋盘素材包

```json
{
  "assets": [
    {
      "kind": "image",
      "name": "GardenBoardBasePanel",
      "prompt": "single garden strategy board base panel, local gameplay island only, orthographic gameplay view, centered, readable silhouette, transparent background",
      "width": 1024,
      "height": 1536,
      "need_seg": true
    },
    {
      "kind": "image",
      "name": "GardenInfoBarPanel",
      "prompt": "single strategy game HUD info bar panel, light cartoon garden theme, front view, centered, solid filled shape, not hollow, transparent background",
      "width": 1024,
      "height": 320,
      "need_seg": true
    },
    {
      "kind": "image",
      "name": "DirtCellTile",
      "prompt": "single garden dirt patch tile, orthographic gameplay view, no perspective, centered, transparent background",
      "width": 1024,
      "height": 1024,
      "need_seg": true
    },
    {
      "kind": "image",
      "name": "LaneDivider",
      "prompt": "single lawn row divider strip for a strategy board game, orthographic gameplay view, no perspective, transparent background",
      "width": 1024,
      "height": 256,
      "need_seg": true
    },
    {
      "kind": "image",
      "name": "GardenCornerAccent",
      "prompt": "single sunny garden corner ornament cluster, small decorative foliage accent, front-facing game UI decoration, solid shapes, transparent background",
      "width": 768,
      "height": 768,
      "need_seg": true
    },
    {
      "kind": "audio",
      "name": "PlantPlaceSFX",
      "prompt": "一声清脆柔和的植物放置音效（明亮, 有反馈感, 约1s）"
    },
    {
      "kind": "audio",
      "name": "HitRewardSFX",
      "prompt": "一声轻快的命中奖励音效（清晰, 明亮, 约1s）"
    }
  ]
}
```

## 失败处理

如果批量结果是 `completed_with_failures`：

- 保留已经成功的输出。
- 只重试失败项。
- 如果用户想针对某个资产单独调 prompt，重试时可以回到 `generate_image` 或 `generate_audio`。

## 交接

`generate_assets_batch` 返回完整结果后：

- 只有少数从批量结果里看不清的输出，才补 `preview_asset`。
- 然后切回 `AssetWorkflow`，或切到对应的场景、材质、VFX skill 做绑定和验证。
