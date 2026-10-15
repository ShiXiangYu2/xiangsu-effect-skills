---
name: AssetWorkflow
description: 快速资产工作流 - 处理仅只需生成或轻量挂载图片、音频等资产的请求。目标扩大到完整场景、脚本或交互时，切换到 EffectWorkflow。
---

# 快速资产工作流

## 何时使用

满足全部条件时优先走这个工作流：

- 用户只要资产本身，或者只要把资产轻量挂到导航树 / 场景树指定父节点下
- 当前请求不要求继续挂到材质、粒子、后处理、脚本或运行态交互逻辑
- 当前目标是更快地产出可用素材，而不是完成整套特效闭环

典型场景：

- 生成图标、贴图、参考图、按钮素材、道具图
- 生成音效、BGM、提示音
- 导入现成素材做快速预览
- 导入或生成素材后，顺手把它挂到导航树里的某个简单节点上

## 边界约束

- 检索范围只限当前 sidecar workspace、当前 project root 和 MCP 已暴露的上下文；严禁检索 workspace 与工程之外的文件、代码、测试或 demo。
- 如果这次资产流程只停留在素材生成或 `preview_asset`，可以不做场景校准；但只要发生了导航树 / 场景树挂载或其他工程写操作，就必须补一次 `capture_preview`。
- 如果同一请求里要批量生成多张图片、多段音频，或图音混合资产，优先切到 `AssetBatchGeneration`；有子 agent 时让子 agent 负责资产生成和初验，没有子 agent 时当前 agent 等 `generate_assets_batch` 完整返回。不要自己发明占位图、占位音频或未声明的内部 agent runtime。
- 生成背景或玩法底板前，按 `context.workspace.rules/scene-common.md` 的“摄像头与背景”判断是否允许整屏资产，并按“局部玩法承载件边界”拆分素材；提示词写法见 `skills_root/assets/ImageGeneration/SKILL.md`。
- 对于摄像头透传玩法，按钮、面板、信息栏和卡片默认生成实体填充资产；禁止空心、镂空、仅轮廓或仅发光边缘的 PNG 边框。边缘装饰使用独立实心元素，不得使用整圈闭合边框。
- 对于方向会影响可读性或机制的玩法贴图，prompt 里必须明确视角、朝向、旋转策略和对称性；不要把朝向留给下游根据图片猜测。

## 快速路径

1. 先判断资产规模与类型：
   - 同一请求里如果有多张图、多段音频，或者图音混合，先走 `AssetBatchGeneration`；有子 agent 时交给子 agent，否则一次调用等完整结果
   - 单个图片、贴图、图标、参考图，走 `ImageGeneration`
   - 单个音频、音效、BGM，走 `AudioGeneration`
   - 已有本地素材导入，走资源导入或现有资源检查
2. 生成或导入后立刻做一次 `preview_asset`，确认内容正确。
3. 如果用户要求把资产轻量挂到导航树 / 场景树：
   - 用 `edit_by_dsl` 做最小挂载，只处理节点创建 / 资源实例化 / 父子关系 / 基础位置与可见性
   - 如果挂载宿主本身是已有菜单对象，例如 `Screen Image`、`Audio Player` 或其他内置对象，优先 `add_builtin_object`
   - 挂完后必须做一次 `capture_preview` 校准层级与挂载结果；`inspect` 只能作为补充检查
   - 验证完成后，在最终回复中明确提醒用户保存工程
4. 如果用户只要资产，或者只要这一步轻量挂载，到这里就可以结束，不要默认继续扩展成完整场景逻辑。
5. 只有当用户明确要求“把这个资产接进当前效果 / 材质 / 粒子 / 后处理 / 脚本”时，才切回 `EffectWorkflow`。

## 默认闭环

- 批量图音资产：`AssetBatchGeneration` -> 有子 agent 则子 agent 生成并初验；否则 `generate_assets_batch` 一次调用等待完整结果 -> 必要时 `preview_asset`
- 图片资产：`ImageGeneration` -> `generate_image` -> `preview_asset`
- 音频资产：`AudioGeneration` -> `generate_audio` -> `preview_asset`
- 现成资源：`list_resources` / `inspect` / `preview_asset`
- 轻量挂导航树：`AssetWorkflow` -> 生成 / 导入资产 -> `edit_by_dsl(add_builtin_object / add_scene_object_from_asset / move_scene_object / set_component)` -> `capture_preview`

## 切回完整特效制作的条件

切换条件见 `skills_root/SKILL.md` 工作流切换规则表。
