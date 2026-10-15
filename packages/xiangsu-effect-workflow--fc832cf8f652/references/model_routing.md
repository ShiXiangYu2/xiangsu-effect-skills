# 模型路由表

来源：用户提供的 opc.fiime.cn 模型清单 + TypeSafe(JEV)。

## 网关与密钥
- **opc 文本/生图/生视频**：`https://opc.fiime.cn/api/model-service/v1/{chat/completions | images/generations | videos}`，密钥 `OPC_API_KEY`（见技能 `.env`）。
- **JEV（TypeSafe）**：`https://api.typesafe.ai/v1/systemone`，模型 `jev-latest`，密钥 `TYPESAFE_API_KEY`（自动读 `D:\dishu\服务器\.env`），经 `JEV_PROXY` 代理访问。

## 按用途路由

| 用途 | 推荐模型 | 备注 |
|------|---------|------|
| 策划 / 设计 / 创意 / 文案 | `opc-txt-v2` | 综合最强，默认 |
| 快速文案 / 草稿 | `opc-txt-v1` | 轻量 |
| 决策推理（JEV 降级用） | `nemotron-3-nano-omni-30b-a3b-reasoning` | 多模态推理，输出概率判断 |
| 强力推理 / 复杂决策 | `deepseek-v4-pro` | 重任务 |
| 快推理 | `deepseek-v4-flash` / `deepseek-v4-flash-0731` | 低延迟 |
| 中文创意 / 文案 | `glm-5-2` / `glm-5-2-l` | 中文语感好 |
| 长文 / 复杂理解 | `kimi-k3` | 长上下文 |
| 通用兜底 | `qwen3-8-27b` | 开源稳 |
| 代码 / 脚本 | `north-mini-code` | 生成运行时代码 |
| 素材生图 | `opc-image-v1` / `opc-image-v2` | 视觉资产、贴图、角色 |
| 特效动态视频 | `opc-video-v1` / `opc-video-v2` | 动态预览、成片 |
| 决策门（首选） | TypeSafe `jev-latest` | 带概率类型化判断 |

## 其它可用模型（按需）
`sensenova-6-8-flash-lite`、`sensenova-u1-fast`、`mixmodel`、`dots-3-note-preview`、`laguna-xs-2-1`、`nemotron-3-ultra-550b-a55b`、`space-bunny-alpha` —— 可作为特定场景的备选（轻量对话、笔记、超大上下文等）。

## 调用约定
- 文本/图片/视频统一走 `scripts/opc_client.py`（自动带密钥）。
- 决策统一走 `scripts/jev_client.py`（自动带代理 + TypeSafe 密钥 + 降级）。
- 不要直连写死密钥；改 `.env` 或环境变量即可换模型/换代理。
