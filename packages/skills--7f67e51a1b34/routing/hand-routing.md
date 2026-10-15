# 手部特效玩法指南

## 能力指引

- **Hand Tracker（`HandTrackerDYEH` / `HandCaptureDYEH`）**：
  适合单个对象仅跟随手掌、手腕或指尖锚点，如简单挂件、掌心光球、指尖粒子。
- **3D Hand Tracker（Hand3dAvatarDrive）**：用于手部模型随真实手势驱动骨骼。
- **Hand Segmentation**：提取摄像头画面的手部区域，用于手部抠图、局部换色、描边和遮挡合成。
- **脚本统一控制**：交互较强或涉及多个跟踪点时，优先由脚本统一读取手部关键点，共用坐标转换、平滑和交互状态。手指控制矩形区域、每根手指的多点跟踪、屏幕绘画等均走此路线。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 单个挂件、光球或粒子仅跟随一个手部锚点 | `HandTrackerDYEH` | 查询 HandTrackerDYEH 知识 |
| 仅让手部模型随手指弯曲、手掌姿态变化 | 3D Hand Tracker | 查询 3D Hand Tracker 对象和 Hand3dAvatarDrive 组件知识 |
| 手部抠图、手部区域换色、描边或遮挡 | Hand Segmentation | 读取 `skills_root/routing/segmentation-routing.md` |
| 握拳、张掌、比心、石头剪刀布等已有手势触发 | 脚本读取手势分类 | 查项目 APJS 定义及相关示例 |
| 手指关键点控制矩形区域、每根手指的多点跟踪 | 脚本统一控制 | 查项目 APJS 定义及相关示例 |
| 摄像头指尖驱动屏幕绘画、捏合抓取、双手联动或自定义手势 | 脚本统一控制 | 查项目 APJS 定义及相关示例 |
| 手指实际触碰屏幕进行点击、滑动或双指缩放 | Touch | 读取 `skills_root/ability/Touch/SKILL.md` |

编写手部脚本时，直接查 `context.workspace.APJS` 下的定义，并在其 `examples/` 中检索相关示例，如 `rock_paper_scissors.json`、`hand_catch_game.json`；关键点、手势类型和坐标约定以定义为准。

复杂交互需处理丢手、多手身份切换和手势防抖；制作前切到包含目标手势或手部动作的预览视频（`hand`），按 `skills_root/general/PreviewInteraction/SKILL.md` 验证。
