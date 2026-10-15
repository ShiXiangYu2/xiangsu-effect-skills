# 物理效果玩法指南

## 能力指引

- **Physics2D**：用于屏幕/2D 世界中的刚体、碰撞、触发器、弹跳和平台类玩法。
- **Physics3D**：用于 3D 物体的碰撞、重力、反弹、堆叠、击倒、拖拽和射线检测。
- **2D 关节**：连接 RigidBody2D，用于定长摆锤、门轴、柔性连接和固定连接；按需要限制的相对运动选择关节。
- **3D 关节**：连接 RigidBody，用于单轴铰链、可自由转动的点连接、弹性连接和固定连接；先确定连接对象、锚点和转轴。
- **Soft Body（SoftBodyActor）**：用于果冻、软挂件等模型的柔软变形和晃动，可将局部顶点固定到跟踪对象或骨骼；同一对象需有 MeshRenderer 和可用网格。
- **2D Fluid（ParticleEmitter2D）**：用于水流、水池、喷泉、液滴和黏液等 2D 流体；Line 持续发射，Polygon 预填区域，主要调整重力、黏度、阻尼和表面颜色。
- **Movement**：用于轨迹、跟随、振荡、漂浮、循环运动和需要精确控制的伪物理。
- **PhysicsMesh**：用于大量碎片或粒子的重力、碰撞、反弹、落地堆积，属于粒子制作能力。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 2D 小球、平台、边界、触发器 | Physics2D | 读取 `skills_root/ability/Physics2D/SKILL.md` |
| 3D 球体、方块、模型碰撞、堆叠、击倒 | Physics3D | 读取 `skills_root/ability/Physics3D/SKILL.md` |
| 2D 定长摆锤、门轴、柔性约束或焊接 | DistanceJoint2D / HingeJoint2D / SpringJoint2D / FixedJoint2D | 读取 `skills_root/ability/Physics2D/SKILL.md` 的 2D Joints 部分，并查询选中组件的知识 |
| 3D 门铰链、万向点连接、弹性约束或焊接 | HingeJoint / PointJoint / SpringJoint / FixedJoint | 读取 `skills_root/ability/Physics3D/SKILL.md` 的 3D Joints 部分，并查询选中组件的知识 |
| 果冻模型、软挂件、局部固定后随运动变形 | SoftBodyActor | 查询 SoftBodyActor 和 MeshRenderer 组件知识 |
| 2D 水流、水池、喷泉、液滴或黏液 | ParticleEmitter2D | 查询 ParticleEmitter2D 组件知识，再读 `skills_root/ability/VFX/SKILL.md` 的 2D Fluid 部分 |
| 精确落点、固定轨迹、装饰漂浮、可控反弹 | Movement | 读取 `skills_root/ability/Movement/SKILL.md` |
| 大量碎片或粒子落地、反弹、堆积 | PhysicsMesh | 读取 `skills_root/routing/particle-routing.md` |

同一对象上，SoftBodyActor 与 RigidBody 互斥，ParticleEmitter2D 与 RigidBody2D 互斥；按组件 schema 选择载体和碰撞配置。烟雾、火花、碎片等通用粒子仍走粒子指南。

关节只约束运动；绳索、链条等可见外观需另外制作。2D 与 3D 关节使用各自维度的刚体和锚点，不能混接。
