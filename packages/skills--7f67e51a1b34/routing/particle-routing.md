# 粒子特效玩法指南

## 能力指引

- **内置 VFX**：适合火花、火焰、雪花、雨滴、湍流、简单爆炸等预设足够表达的效果。
- **VFXAuthoring**：适合需要自定义生产的粒子效果，包括：
  - 自定义 2D 粒子、贴图粒子、烟雾、光点、拖尾。
  - 3D 网格粒子，如石块、金属碎片、立体残片。
  - 物理粒子，如重力、碰撞、反弹、碎裂、落地停留或堆积。
  - 多阶段生命周期、多 system 联动或事件触发。
- **2D Fluid（ParticleEmitter2D）**：适合需要汇聚、流动的 2D 液体；水流、水池、黏液等进2d流体物理效果。
## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 简单火花、火焰、雪花、雨滴、一次性爆炸 | 内置 VFX | 读取 `skills_root/ability/VFX/SKILL.md` |
| 2D 液体汇聚、流动、水池或黏液 | ParticleEmitter2D | 读取 `skills_root/routing/physics-routing.md` |
| 自定义形状、贴图、颜色、生命周期或多 system 联动 | VFXAuthoring | 读取 `skills_root/assets/VFXAuthoring/SKILL.md` |
| 3D 网格碎片飞散、碎片落地、反弹或堆积 | VFXAuthoring | 读取 `skills_root/assets/VFXAuthoring/SKILL.md` |
