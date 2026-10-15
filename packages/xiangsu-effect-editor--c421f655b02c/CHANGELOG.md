## 1.3.0（候选，2026-10-11）
新增月亮打盹猫、一键剃光头（含按钮修复）、蜘蛛贴脸闭环实践和3个脚本快照；修正材质编辑泛化表述，补充证据边界与来源检查。

# Changelog

## 20261009-165700 换壳实战沉淀
- 新增 references/reskin-playbook.md：换壳 7 步流程、两条资产路径（AI 生图 vs PIL 调色）、edit_by_dsl 速查、GUID 规则、预览验收、提交失败排查、反模式
- 新增 references/case-studies.md：兔兔甜品师 / 蜜桃乌龙妆 / 草莓奶昔蕉 三案例与精确参数
- 新增 references/rpc-fallback.md：直连 127.0.0.1:17320/mcp 的等效通道（MCP 管理器未暴露 DSL 工具时）
- 新增 scripts/uv_recolor.py：UV/模型贴图本地调色（sat_rotate / range_remap / --analyze 色相分布）
- 新增 scripts/crop_regions.py：预览截图分区放大裁剪验收
- SKILL.md 增加「换壳实战（制作层）」入口与铁律速记
- manifest 标记 official_skill_content_unmodified=false，新增 local_practice 来源；版本 1.0.0 → 1.1.0

## 20261008-131022 WorkBuddy 迁移
- 从 Codex (~/.codex/skills) 迁移安装至 WorkBuddy 用户级技能目录
- lifecycle.py 安装白名单追加 ~/.workbuddy/skills（平台适配，其余内容未改动）
