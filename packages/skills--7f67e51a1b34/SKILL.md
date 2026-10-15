---
name: SkillsRouter
description: 像塑 Skill 的总入口，根据任务目标选择 workflow、assets、ability 或 general 下的具体 Skill。这里只负责定位，不提供实施规则。
---

## 路径约定

- `skills_root` 是共享 context 的 `agentAssets.skillPackRoot`，也就是连接结果中的 `context.workspace.skills_root`；它已经指向 Skill 包根目录。下文 `skills_root/...` 要替换为真实路径，不要再拼一层 `skills/`，也不要相对 Agent 的当前工作目录读取。
- 跨 Skill 或路由引用统一写为 `skills_root/<分类>/<名称>/...`。某个 Skill 内的 `references/...`、`templates/...` 和 Markdown 相对链接按该 Skill / 引用文件注明的基准解析。
- manifest 的 `route_doc` 相对 `skills_root`；`query_knowledge` 返回的相关 Skill 路径可以直接读取。
- 项目 workspace 是像塑工程的 `.mcp_agent` 目录，可以与 Agent 自己的 workspace 不同。规则、APJS 和工程路径按项目 `AGENTS.md` 解析；不要在 Agent 当前目录下寻找同名目录。

## 路由步骤

1. 所有任务先按「工作流指南」选择 workflow，并在 workflow 约束下推进。
2. 按实际行为拆解能力需求，例如跟踪谁、驱动什么、是否需要真实碰撞、是否依赖新资产；题材关键词只用于找到候选指南。
3. 按「技能/任务指南」拆解任务涉及的实际能力，确定主能力和全部强相关的配合能力，并读取对应 Skill。一个任务涉及多个能力时，相关 Skill 必须全部读取，不能只读取主能力 Skill；已经确定的能力不必在指南之间反复跳转。动画、脚本等未单列的能力按「Skill目录指南」定位。
4. 仍不能定位时，读取 `skills_root/routing/skill_manifest.json` 获取全部 Skill 摘要；也可以结合 `query_knowledge` 查找 object/component/resource 相关知识。最终以具体 `SKILL.md` 正文为准。

能力指南负责选择能力，工作流负责推进交付；进入某个能力 Skill 不等于切换工作流。

## 工作流指南

| 交付范围                     | 进入 workflow                   | 定位方式                                                    |
| ------------------------ | ----------------------------- | ------------------------------------------------------- |
| 复杂视觉目标、完整效果、多系统联动、需要验收闭环 | `EffectWorkflow`    | 读取 `skills_root/workflow/EffectWorkflow/SKILL.md`                   |
| 仅生成、导入、转换资产，或只做轻量挂载      | `AssetWorkflow`     | 读取 `skills_root/workflow/AssetWorkflow/SKILL.md`，再按资产类型补读 `skills_root/assets/` |
| 改参数、改名、调整层级、添加少量简单对象     | `QuickEditWorkflow` | 读取 `skills_root/workflow/QuickEditWorkflow/SKILL.md`                |

当 Agent 已在某个 workflow 中执行时，按以下规则判断是否需要切换：

| 当前 workflow       | 切换条件                                           | 目标 workflow    |
| ----------------- | ---------------------------------------------- | -------------- |
| AssetWorkflow     | 目标扩大到完整效果、材质或粒子系统、后处理、脚本或运行态交互；简单节点创建与轻量挂载仍按 AssetWorkflow | EffectWorkflow |
| QuickEditWorkflow | 需要先补新资产                                        | AssetWorkflow  |
| QuickEditWorkflow | 需要先解释需求、对齐目标、列步骤                               | EffectWorkflow |

## 技能/任务指南

命中特效玩法或题材时读取对应指南。下表只列常见玩法入口；通用知识按「Skill目录指南」检索。

| 任务描述                                              | 指南路径                                     |
| ------------------------------------------------- | ---------------------------------------- |
| 需要粒子视觉，包括爆炸、烟雾、火花、碎片或物理粒子                         | `skills_root/routing/particle-routing.md`     |
| 需要脸部/头部能力，包括头饰、3D 挂件、头控玩法、美妆、贴纸、面具或瞳色             | `skills_root/routing/face-head-routing.md`         |
| 需要手部特效，包括跟踪、摄像头手势、多指交互、关键点控制区域、指尖绘画或手部抠图       | `skills_root/routing/hand-routing.md`              |
| 需要足部特效，包括脚踝跟随、鞋子试穿、踩点、踢踏或双脚交互                       | `skills_root/routing/foot-routing.md`              |
| 需要身体能力，包括身体美型、身体点位跟踪、全身模型驱动、身体抠图、描边、画笔或姿态交互 | `skills_root/routing/body-routing.md`              |
| 需要模型、Prefab、全身替身或复杂骨骼驱动                           | `skills_root/routing/model-routing.md`              |
| 需要物理行为，包括碰撞、重力、反弹、2D / 3D 关节、堆叠、弹射、拖拽、触发器、柔体变形或 2D 流体 | `skills_root/routing/physics-routing.md`      |
| 需要分割能力，包括人像、主体、头部、手部、眼睛、天空等抠图，或背景替换、遮挡合成         | `skills_root/routing/segmentation-routing.md` |
| 需要 AR 能力，包括相机透传、平面放置、空间点击、环境融合或 3D 场景叠加           | `skills_root/routing/ar-routing.md`           |
| 需要音频能力，包括音乐、BGM、音效、节拍玩法、声音驱动或音频检测                 | `skills_root/routing/music-routing.md`        |
| 需要材质效果，包括 ShaderToy、Shader、OMTL、溶解、描边、发光、折射或后处理材质 | `skills_root/routing/material-routing.md`     |

## Skill目录指南

| 分类          | 负责内容                                            | 何时进入                               |
| ----------- | ----------------------------------------------- | ---------------------------------- |
| `workflow/` | 任务流程、方案确认、执行阶段、验证闭环。                            | 需要完整推进、用户确认、快速编辑、节点搭建或可验收效果。       |
| `assets/`   | 图片、音频、材质、VFX 等资产的生成、导入、制作和绑定准备。                 | 目标是获得或处理资产源文件，或需要先生产资产再接入场景。       |
| `ability/`  | 场景、交互、动画、物理、相机、渲染、媒体等具体能力。                      | 已明确要实现的功能，需要查组件用法、运行时行为或能力边界。      |
| `general/`  | 场景编辑、APJS API、组件访问、生命周期、序列化、调试、预览、Prefab 等基础规则。 | 实现中需要补充工程基础、DSL 场景编辑、脚本规则、调试或验证方法。 |
