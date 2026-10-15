# 足部特效玩法指南

## 能力指引

- **脚踝跟随（BodyBindingJS）**：简单贴纸、光点或粒子跟随左/右脚踝，可用 2D Keypoint Tracker；脚踝位置不能代替完整足部姿态。
- **Foot Tracker（FootTrackingJS）**：用于鞋子等模型随足部姿态运动，内置对象会创建左右脚跟踪节点和遮挡层。
- **脚本统一控制**：踩点、踢踏、双脚联动等交互较强的玩法，优先由脚本统一读取跟踪数据、转换坐标并管理交互状态。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 简单贴纸、光点或粒子跟随脚踝 | 2D Keypoint Tracker | 查询对象及 BodyBindingJS 组件知识，使用 LeftAnkle / RightAnkle 锚点 |
| 鞋子试穿、模型跟随足部姿态 | Foot Tracker | 查询 Foot Tracker 对象和 FootTrackingJS 组件知识 |
| 踩点、踢踏、脚部控制区域或双脚联动 | 脚本统一控制 | 查项目 APJS 定义及相关示例，确认能取得玩法所需的跟踪数据 |
| 踢球并产生真实碰撞、反弹 | 跟踪数据 + 物理 | 另读 `skills_root/routing/physics-routing.md` |

脚本直接查 `context.workspace.APJS` 下的足部定义（包括 `APJS_runtime.d.ts`），并在其 `examples/` 中检索相关示例；以当前可调用接口和实际算法输出为准。

交互需处理跟踪丢失、左右脚身份和重复触发；制作前切到双脚可见、包含所需动作的全身预览视频（`body`），按 `skills_root/general/PreviewInteraction/SKILL.md` 验证。
