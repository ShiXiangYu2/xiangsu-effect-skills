---
name: xiangsu-effect-editor
description: 当用户需要生成、制作、修改或调试特效时使用，作为像塑操作入口，统一负责连接像塑，操作、编辑像塑工程，以及特效AI工作流的制作。
metadata:
  version: "1.3.0"
  upstream-version: "1.0.0"
---

# 连接像塑

本 skill 负责与像塑建立连接，并强制读取当前像塑 MCP 返回的 `context.workspace.agents_file` 操作手册。只有读取该手册后，才能继续特效制作、规则加载或任务恢复。

## 连接实例

1. 必须使用 Agent 全局注册的 MCP server `xiangsu-mcp-manager`，不得使用会话内、项目内或临时注入的同名 MCP。初始工具列表中未发现它时，只通过 Agent 全局工具发现获取；仍不可用则报告 MCP 配置异常并停止。
2. 已知目标 `instance_id` 时，可直接进入工程核对；内嵌终端按已加载的项目 `AGENTS.md` 取得实例标识。连接失效时重新探测，不自动切换到其他工程。
3. 首次连接或重新探测时调用 `health` 和 `list_instances`。服务未就绪或没有实例时，告知用户“请先启动像塑并打开工程”，停止连接，不用本地文件推断连接状态。
4. 只有一个实例时自动选中；多个实例时，优先通过宿主的结构化选择 UI 展示返回的 `instance_id`、`project_name` 和 `project_path`，由用户选择。宿主没有选择 UI 时再用自然语言确认。

## 核对工程

1. 调用 `xiangsu-mcp-manager.get_project_context({instance_id})`，核对返回的 `context.identity.instance_id` 和 `context.identity.project_path` 与目标实例、工程一致。在核对通过前，不调用实例工具或猜测工程路径。
2. 上下文不可用、关键身份字段缺失或工程不匹配时，停止并说明“当前实例上下文不可见或不匹配”。不要依赖全局 active context，也不要设置全局当前实例来修正结果。
3. 后续像塑 MCP 调用始终显式携带选中的 `instance_id`。不要直接访问实例 runtime HTTP 或 Gateway REST 接口。

## 进入项目手册

1. `get_project_context` 核对成功后，下一步必须读取其返回的 `context.workspace.agents_file`。不得跳过，也不得用缓存、记忆或其他同名 `AGENTS.md` 替代。
2. 读取完成前，不得继续调用场景、资源、脚本或预览工具，也不得进入制作或任务恢复流程。
3. 路径缺失或文件不可读时立即停止并报告，不从 Agent 自己的 workspace 查找同名文件。

该路径不依赖 Agent 的当前工作目录，无需切换 workspace。把本次 `get_project_context` 的返回结果交给手册中的制作或恢复流程继续处理。

## 本地制作与发布经验扩展

此节是用户批准后生效的本地经验扩展，不是官方连接包新增规范。完成连接及返回手册初始化后，设计原创改款、交互提示、审核退回与发布准备时读取本机 `xiangsu-effects-production-lineage` 的 `references/local-practice.md`、`references/review-preflight.md` 和证据索引；没有该包时读取 [审核关键提醒](references/review-routing.md)。官方 API 和 MCP 定义仍只从官方安装配置获取，经验资料不能覆盖当前 MCP 手册/API/schema。

每次使用先用本机 Python 执行 `scripts/lifecycle.py check-sources --skill <本技能目录>`；来源变化准备候选，不自动覆盖。维护仍见 [维护规范](references/maintenance-policy.md)。

## 换壳实战（制作层）

连接与手册读取完成后，模板换壳的实际制作知识见以下参考（来自三次真实换壳任务的沉淀）：

- [reskin-playbook.md](references/reskin-playbook.md) — 换壳 7 步流程、两条资产路径、edit_by_dsl 速查、GUID 规则、预览验收、提交失败排查、反模式。
- [case-studies.md](references/case-studies.md) — 《兔兔甜品师》《蜜桃乌龙妆》《草莓奶昔蕉》三案例与精确参数。
- [rpc-fallback.md](references/rpc-fallback.md) — 历史记录，不授权绕过全局 MCP；历史直连 `http://127.0.0.1:17320/mcp` 的等效通道（实践中实际使用的路径）。

配套脚本：

- [scripts/uv_recolor.py](scripts/uv_recolor.py) — UV 面部/模型贴图本地调色（sat_rotate / range_remap / --analyze 色相分布）。
- [scripts/crop_regions.py](scripts/crop_regions.py) — 预览截图分区放大裁剪，用于逐区验收。

铁律速记：**UV 面部贴图绝不 AI 生图（用 PIL 调色）**；**先区分可编辑材质源与不透明二进制资源，按当前 MaterialAuthoring 编译；编译后复核纹理绑定**；**绑定用组件 GUID（cXX）而非对象 GUID（sXX）**；**import_resource 是 edit_by_dsl 子命令、只传 path**；**调色前先跑色相分布定阈值**。

上述历史经验不覆盖当前实例手册；rpc-fallback 仅留档，制作调用必须走全局 MCP。

## 从零自拍特效实战（2026-10-11）

完成工程核验和当前手册初始化后，按任务读取 [实践索引](references/practice-20261011/index.md)：
- 猫耳、猫须和透明挂件的人脸贴合：[月亮打盹猫](references/practice-20261011/mooncat.md)。
- 光头渐变、确认/恢复、拍摄按钮遮挡：[一键剃光头](references/practice-20261011/shave.md)。
- Blender骨骼动物、动态曲面路线、连续循环与提速：[蜘蛛爬脸](references/practice-20261011/spider.md)。
- 换工程恢复、组件引用、预览与交付：[实施与验收](references/practice-20261011/implementation.md)。

这些是本地实测经验，不覆盖当前API。示例尺寸、网格布局和坐标需要现场核验；编辑器通过不等于真机、活动审核或音效通过。用户已要求直接制作时，在已授权范围内推进，常规调参无需重复确认；技能安装/替换仍遵守下面的当前候选审批规则。

## 迁移维护
每次使用先运行 `scripts/lifecycle.py check-sources --skill <本技能目录>`。使用后根据实际问题准备优化候选；没有问题不制造升级。来源及逐文件 SHA256 见 manifest.json；[维护规范](references/maintenance-policy.md)要求安装当前候选前取得明确同意。
