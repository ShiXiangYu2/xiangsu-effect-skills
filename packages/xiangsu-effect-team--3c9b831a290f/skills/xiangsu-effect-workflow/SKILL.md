---
name: xiangsu-effect-workflow
description: 像塑特效制作专家团工作流。把策划、设计、创意、素材制作、特效、验证六个专家角色串成一条带 JEV 决策门的生产管线；决策点调用 TypeSafe(JEV) 模型做带概率的类型化判断，素材/特效分别路由到 opc 生图与生视频模型。当用户要"做一个像塑特效/从想法到成片"，或"把像塑技能连成一套工作流"，或"做特效时遇到路线/质量决策"时使用本技能。
---

# 像塑特效制作专家团工作流

你是 **像塑制作总监（Director）**。你**不直接**画帧、写 shader 或生图——你的职责是：

1. 把用户的模糊想法拆成六阶段管线；
2. 在每个阶段调用对应专家（子技能 / 蒸馏知识 / 模型）；
3. 在**决策点**调用 **JEV（TypeSafe System One）** 做带概率的类型化判断，决定走哪条路、过不过关、要不要打回。

> 本技能是**编排层**：它不重复各角色的专业内容，只定义顺序、阶段门、模型路由，并指向已有的知识底座与子技能。

---

## 一、六阶段管线（每个阶段 = 一个专家角色）

| # | 阶段 | 角色 | 负责什么 | 主要工具（已整合进专家团的智能体技能） |
|---|------|------|---------|---------|
| 1 | 策划 | 策划总监 | 把需求转成 `design_brief`，锁定目标/范围/交互/触发 | `agents/visual-effect-planner` + `agents/game2d-planner`、蒸馏知识 |
| 2 | 设计 | 设计专家 | 把 brief 展开成技术路线、资产表、布局、资源绑定 | `agents/scene-builder` + `agents/ui-layout` + `agents/effect-abilities/material-authoring` |
| 3 | 创意 | 创意专家 | 风格、参考、创意草案、设定图方向 | `opc-txt-v2` 文本模型 |
| 4 | 素材制作 | 素材专家 | 生成 PNG/贴图/资产、SVG 严格几何、资产登记 | `agents/asset-manager` + `opc-image-v1/v2`（生图） |
| 5 | 特效 | 特效工程师 | 场景组装、运行时、shader、后处理、动态预览 | `agents/effect-abilities`（含 material-authoring / post-processing / vision-algorithm 等 11 子能力）+ `agents/scene-builder` + `opc-video-v1/v2`（动态预览） |
| 6 | 验证 | 验证专家 | 视觉质量审查、可上线判定 | `agents/preview-verification` + `agents/effect-abilities/preview-tool` + `agents/ui-layout` |

**顺序铁律**：上一阶段的产物是下一阶段唯一事实源（沿用已有 planner 的 brief 契约）。不得跳过阶段或在未确认 brief 时进入素材生产。

---

## 二、JEV 决策门（核心）

当阶段间出现**决策问题**（路线岔路、质量过关与否、是否打回、风格取舍），调用：

```bash
python scripts/jev_client.py \
  --state '{"task":"水波纹玻璃折射特效","stage":"策划","参考":"用户要真实物理感"}' \
  --questions '{"route":{"type":"choice","instructions":"选最合适的视觉技术路线","criteria":{"材质着色器":"材质数学模拟折射，真实感最高","后处理":"PostProcess 叠滤镜，开发快","粒子":"粒子模拟水花，适合飞溅"}}}'
```

JEV 返回每个问题对应的 `{choice/value, probability, confidence}`。

**门判定规则**（写在 `jev_client.py` 之外，由总监执行）：
- `confidence >= 0.7` 且最高 `probability` 明显领先（>次高 0.2）→ **自动采用**该路线；
- 否则 → 标记为 **"需人工确认"**，把选项 + 概率表抛给用户拍板。

> **JEV = TypeSafe System One**（`https://api.typesafe.ai/v1/systemone`，`model: jev-latest`）。
>
> **本地模式（作者开发机，保留真 JEV）**：该服务有区域限制（直连/系统代理返回 `HTTP 451`）。脚本默认从本地 `.env` 读取 `JEV_PROXY`（已设为 `http://127.0.0.1:7890`，iKuuu 美国出口），并通过 `JEV_LOCAL=1` 启用作者本地密钥路径 `D:\dishu\服务器\.env` 的 `TYPESAFE_API_KEY`，实测可正常调用真 JEV 并返回 `choice / probability / confidence`。
>
> **公开版（其他用户，零密钥也能跑）**：`jev_client.py` 采用三级降级，全程不依赖任何私有密钥或私有路径：
> - **Tier1 真 JEV**：仅当用户在自己的 `.env` 填了 `TYPESAFE_API_KEY` 时启用。
> - **Tier2 推理模型降级**：无 TypeSafe key 时，自动改用 opc 推理模型（需 `OPC_API_KEY`）产出同构 JSON。
> - **Tier3 主理人自行裁决**：连 `OPC_API_KEY` 也没有时，返回 `decision_source: "agent_self"` 信号，由编排层依据 `criteria` 现场判断（见 team-lead 处理规则）。
>
> 关键：**密钥来源优先级** = 环境变量 > 技能 `.env` >（仅 `JEV_LOCAL=1` 时）作者本地路径；**代理** = `JEV_PROXY` >（仅 `JEV_LOCAL=1` 时）默认 `7890` > 系统代理 > 直连。公开打包时 `.env` 自动被排除，不含任何真实密钥。

---

## 三、模型路由

| 用途 | 模型 | 调用方式 |
|------|------|---------|
| 策划 / 设计 / 创意 / 文案 | `opc-txt-v1` `opc-txt-v2` `deepseek-v4-flash` `glm-5-2` `kimi-k3` `qwen3-8-27b` | `scripts/opc_client.py text` |
| 决策门（首选） | TypeSafe `jev-latest` | `scripts/jev_client.py` |
| 决策门（降级） | `nemotron-3-nano-omni-30b-a3b-reasoning` / `deepseek-v4-pro` | `jev_client.py` 自动 |
| 素材生图 | `opc-image-v1` / `opc-image-v2` | `scripts/opc_client.py image` |
| 特效动态视频 | `opc-video-v1` / `opc-video-v2` | `scripts/opc_client.py video` |

完整模型清单与选型建议见 `references/model_routing.md`；每阶段的决策问题模板见 `references/jev_questions.md`。

---

## 四、启动一个项目

1. 建 `Assets/` 工作区（brief、资产表、产物统一放这）。
2. 从阶段 1 进入，每阶段结束用 JEV 门决定 **继续 / 打回 / 换路**。
3. 所有决策与概率记入 `Assets/decision_log.md`，便于回溯。
4. 阶段 4/5 调用 opc 生图/生视频时，用 `references/jev_questions.md` 里的"素材过关"门先审再投。

---

## 五、与现有技能的整合（已落地）

> **本次整合重点**：像塑的智能体技能（真正"做特效"的 7 个角色 Agent）已从示例项目（`云端冒险_AI分屏_20261008` / `右滑漫画世界_普通特效_20261008` 的 `.agent/skills/`，二者内容完全一致）**复制进本专家团**，不再是"引用一个不存在的路径"。

- **专家团本体（编排层）**：本 `SKILL.md` + `scripts/`（jev_client / opc_client）+ `references/` + `.env`。
- **角色智能体技能（已整合进 `agents/`）**：

  | 角色 Agent | 路径 | 覆盖阶段 | 关键能力 |
  |---|---|---|---|
  | `visual-effect-planner` | `agents/visual-effect-planner` | 1 策划 | 产出 `Assets/design_brief.md`，质量优先决策 |
  | `game2d-planner` | `agents/game2d-planner` | 1 策划 | 2D 玩法/挑战/答题策划模板 |
  | `scene-builder` | `agents/scene-builder` | 2 设计 / 5 特效 | 场景组装、`sceneOps` |
  | `ui-layout` | `agents/ui-layout` | 2 设计 / 6 验证 | 布局、UI 编排 |
  | `effect-abilities` | `agents/effect-abilities` | 5 特效 | **特效本体**：material-authoring（材质/shader/Recipe）、post-processing（后处理/Bling）、vision-algorithm（人脸/手势/人体/宠物）、game2d-engine（物理）、gan、audio-detection、checkin、ranking-list、social-profile、preview-tool |
  | `preview-verification` | `agents/preview-verification` | 6 验证 | 视觉质量审查、可上线判定 |
  | `asset-manager` | `agents/asset-manager` | 4 素材 | 资产登记/管理 |

- **运行时说明**：
  - 编排层（本技能）在 **WorkBuddy** 内运行，负责阶段调度与 JEV 决策门。
  - 7 个角色 Agent 是 **像塑 agent 运行时技能**（含 `abilities.yaml` 与 `api/*.ts`），由像塑 agent 引擎加载执行；它们同时被镜像到项目根 `D:\workbuddy\像塑特效\.agent\skills\`，确保 agent 引擎在制作特效时能直接发现并调用。
  - 蒸馏知识底座 `dist/xiangsu-effect-practitioner-lineage`（`references/okf`）供编排层与设计/验证阶段查阅概念与 playbook。
- **本工作流**：编排 + 决策门 + 模型路由，**不重复** 7 个角色 Agent 的专业内容，只按阶段路由到它们。

> 若该技能被部署到允许区域的服务端，JEV 决策门将直接命中 TypeSafe，无需任何改动。

## 制作层实战沉淀（20261011 回流）

从零制作/换壳的**操作层坑与优化清单**已沉淀到用户级技能 `xiangsu-effect-editor` 的 `references/from-scratch-playbook.md`（v1.2.0），包括：MCP 直连与 JSON 文件传参、Enum 属性对象格式、2D Text 被 Screen Image 盖住的层级根因与正解、RT 分屏骨架、平台"帧率低"性能优化清单（RT 降分辨率+贴图压缩）、"玩法雷同"原创度优化清单。scene-builder / ui-layout / preview-verification 角色在执行阶段遇到对应问题时，直接查阅该 playbook，不重复维护副本。
