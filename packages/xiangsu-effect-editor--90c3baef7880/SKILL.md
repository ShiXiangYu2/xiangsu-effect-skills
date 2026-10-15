---
name: xiangsu-effect-editor
description: 当用户需要生成、制作、修改或调试特效时使用，作为像塑操作入口，统一负责连接像塑，操作、编辑像塑工程，以及特效AI工作流的制作。
metadata:
  version: "1.0.1"
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
