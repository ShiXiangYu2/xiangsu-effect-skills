# AR 玩法指南

## 能力指引

- **相机透传叠加**：在真实画面上叠加模型、贴纸、玩法底板或粒子；背景限制按 `context.workspace.rules/scene-common.md` 的“摄像头与背景”。
- **空间点击/平面放置**：通过触摸点、相机射线和平面求交确定 3D 世界位置。
- **AR 物理玩法**：篮球、足球、弹球、击倒、拖拽等需要物理或伪物理决策。
- **环境融合**：通过灯光、材质、阴影和尺度调整，让虚拟对象和真实画面更一致。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 点击地面放置模型或道具 | Touch + Camera | 读取 `skills_root/ability/Touch/SKILL.md`、`skills_root/ability/Camera/SKILL.md` |
| 透传画面上叠加 3D 模型、赛道、底板 | ModelImport + SceneEditing | 读取 `skills_root/ability/ModelImport/SKILL.md` |
| AR 篮球、足球、弹球、击倒 | Physics 或 Movement | 读取 `skills_root/routing/physics-routing.md` |
| AR 空间粒子、环绕、爆发、落地反馈 | 粒子能力 | 读取 `skills_root/routing/particle-routing.md` |
| 真实环境里的可见性、光照、融合感 | Lighting | 读取 `skills_root/ability/Lighting/SKILL.md` |
