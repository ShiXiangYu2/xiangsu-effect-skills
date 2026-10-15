# Codex 运行适配（优先于包内 WorkBuddy 调度语法）
先使用 xiangsu-effect-editor 连接全局像塑 MCP，核对 instance_id 并读取当次工程手册。历史能力文档仅供参考，当前工程 API/schema 为准。
六阶段为策划、设计、创意、素材、特效、验证。七份团队职责文件在 references/team-roles/。WorkBuddy 的 TeamCreate 和 subagent_type 不能直接在 Codex 调用；改用当前 collaboration.spawn_agent 调度阶段子代理，将对应角色文件全文和前序产物作为输入。主代理承担总监职责，不另建侧栏聊天。遵守当前并发上限，各专业阶段由子代理交付；工程修改串行，所有像塑调用显式传 instance_id。
本机客户端只读复用原 WorkBuddy 技能 .env，不将密钥复制进候选、日志或报告。来源缺失时用环境变量；JEV 无密钥时按 agent_self 模式做定性判断，不编造概率。外部模型路由为源包配置，本次未验证服务可用性。图片生成遵守宿主 image_gen 要求，生成视频不能作为真实工程预览证据。
知识底座为同级 xiangsu-effects-production-lineage 和 xiangsu-effect-practitioner-lineage。agents/ 内保留角色技能、能力和 API 参考；它们不是自动注册的 Codex 原生角色。当前实例操作手册优先，不用历史 rpc-fallback 绕过 MCP。
可上线判定需要真实工程预览和交互验证；未运行工程时明确待验证。
