# Changelog

## 20261011-104500 ins分屏边框从零制作实战沉淀
- 新增 references/from-scratch-playbook.md：空白工程从零制作全流程（handoff 记录→save_plan→批量资产→骨架→分段验收），含 ins分屏边框完整案例
- 沉淀高频坑：MCP 端点无状态直连、长 JSON 必须文件传参、Enum 属性必须 {"type":"Enum","data":...} 格式、set_scene_object 不支持 renderOrder、2D Text 被 Screen Image 盖住的根因与 move_scene_object 正解、编辑器场景视图 RT 占位图属正常
- 沉淀性能优化清单（RT 降分辨率 75%、贴图手动压缩 Size128/256/512）与原创度优化清单（原创文案+AI 贴纸），对应平台"帧率低/玩法雷同"两类警告
- 沉淀可复用分屏相框场景骨架（RT+双白框+装饰+文字层级）与 MCP helper 三件套（mcpcall/mcpraw/mcpcap）
- SKILL.md 增加「从零制作实战」入口；版本 1.1.0 → 1.2.0

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
