# 像塑特效制作工作流（详细）

把一次"想法 → 成片"拆成 6 阶段，每阶段有明确的**输入契约 / 专家 / 工具 / 产出 / 决策门**。

## 阶段 1 · 策划（策划总监）
- **输入**：用户自然语言需求、参考图/视频、平台约束。
- **专家**：`visual-effect-planner`（视觉特效）/ `game2d-planner`（2D 互动）。
- **动作**：意图扩展 → 微澄清（必要时）→ 产出 `Assets/design_brief.md`（含效果目标、实现方案、输入数据流、技术架构、资产表）。
- **产出**：`design_brief.md`（下游唯一事实源）。
- **门 P1**：路线岔路时用 JEV（`references/jev_questions.md` Gate P1）选技术路线。

## 阶段 2 · 设计（设计专家）
- **输入**：`design_brief.md` + 蒸馏知识包 `references/okf`、`playbooks.md`、`concept_glossary.md`。
- **动作**：展开技术架构、资产表（PNG/SVG 严格几何）、布局、序列化资源绑定、脚本字段契约。
- **产出**：完整技术规格（可进入素材生产与场景组装）。
- **门 D1**：风格方向用 JEV Gate D1。

## 阶段 3 · 创意（创意专家）
- **输入**：技术规格 + 风格方向。
- **工具**：`opc-txt-v2`（创意草案、风格文案、设定图描述）。
- **动作**：产出风格板、设定图方向、文案。
- **门 M1**：资产生产路由用 JEV Gate M1（image-generator / svg-generator / script-runtime）。

## 阶段 4 · 素材制作（素材专家）
- **输入**：资产表 + 生产路由。
- **工具**：`opc-image-v1/v2`（生图，见 `scripts/opc_client.py image`）、`material-authoring`、`svg-generator`。
- **动作**：批量生成 PNG/贴图/严格几何 SVG，落 `Assets/`。
- **门 E1**：素材过关判定用 JEV Gate E1（通过 / 返工部分 / 整体返工）。

## 阶段 5 · 特效（特效工程师）
- **输入**：技术规格 + 已过关素材。
- **工具**：`scene-builder`、`effect-abilities/*`、`game2d-engine`；动态预览用 `opc-video-v1/v2`。
- **动作**：场景组装、运行时、shader、动态预览成片。
- **产出**：可运行特效 / 成片。

## 阶段 6 · 验证（验证专家）
- **输入**：成片 + brief。
- **工具**：`preview-verification`、`preview-tool`、`ui-layout`、`asset-manager`。
- **动作**：视觉质量审查、可上线判定。
- **门 V1**：可上线判定用 JEV Gate V1（可上线 / 小修 / 迭代）。

## 决策日志
每个 JEV 门的结果（问题、选项、概率、置信度、采用/打回）记入 `Assets/decision_log.md`，格式：
```
[阶段][门] 问题=route | 采用=材质着色器(p=0.82, conf=0.91) | 备注=自动采用
```
便于回溯为什么走了某条技术路线。

## 端到端示例（命令行）
```bash
# 1) 策划→设计：用 JEV 选技术路线
python scripts/jev_client.py \
  --state '{"task":"水波纹玻璃折射特效","stage":"策划"}' \
  --questions '{"route":{"type":"choice","instructions":"选最合适的视觉技术路线","criteria":{"材质着色器":"材质数学模拟折射","后处理":"PostProcess 滤镜","粒子":"粒子模拟"}}}'

# 2) 创意：用 opc 写设定图描述
python scripts/opc_client.py text --model opc-txt-v2 --prompt "为水波纹玻璃折射特效写一段设定图描述"

# 3) 素材：用 opc 生图
python scripts/opc_client.py image --model opc-image-v1 --prompt "透明玻璃水滴贴图，纯透明背景，高清" --size 512x512

# 4) 特效：动态预览视频
python scripts/opc_client.py video --model opc-video-v1 --prompt "水波纹玻璃折射动态预览"
```
