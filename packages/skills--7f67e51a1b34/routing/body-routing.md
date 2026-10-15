# 身体效果玩法指南

## 能力指引

- **身体美型**：使用 `BodyStretchEntity` / `BodyStretchComponent` 通过滑杆调整身体形态和比例。实时形变不要用贴图、分割或全身模型替代。
- **身体跟踪**：`2D Keypoint Tracker`（`BodyBindingJS`）跟踪手腕、膝盖、脚踝等 2D 身体关键点，适合挂载贴纸、光点、粒子或简单道具。关键点位置不等于完整 3D 姿态。
- **腕部穿戴跟踪**：使用 `WristwearTrackingRoot` 创建腕部跟踪根节点和遮挡子节点，
  适合手表、手环或其他腕部模型挂件；它不是普通 2D 关键点贴纸。
- **3D 全身驱动**：`FullBodyAvatar` / `FullBodyAvatarDrive` 将身体跟踪结果映射到人形骨骼，适合全身替身、姿态重定向和多关节联动。模型需要已有网格、蒙皮和匹配的骨骼结构。
- **身体抠图**：按目标区域选择 `Head Segmentation`、`Hand Segmentation`、`Skin Segmentation`、`Portrait Segmentation`、`Clothing Segmentation` 或 `Subject Segmentation`。
- **身体描边和画笔**：`Outline` 用于人体、皮肤、服装或主体轮廓；身体涂鸦、皮肤纹理和局部颜色通常使用分割遮罩，再配合材质、贴图或粒子。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 改变身体比例、轮廓或局部身体形变 | `BodyStretchEntity` | 查询 `BodyStretchComponent` 及 `NsItemType`，确认可用的形变项 |
| 贴纸、光点或粒子跟随手腕、膝盖、脚踝等身体点位 | `2D Keypoint Tracker` | 查询 `BodyBindingJS` 和 2D 身体关键点知识 |
| 手表、手环或其他模型跟随腕部并处理遮挡 | `WristwearTrackingRoot` | 查询 WristwearTrackingRoot 知识 |
| 全身 3D 替身随用户动作变形 | `FullBodyAvatar` | 查询 `FullBodyAvatar` / `FullBodyAvatarDrive`，确认全身模型骨骼和蒙皮 |
| 头部抠图 | `Head Segmentation` | 查询 `Head Segmentation` 对象知识 |
| 手部抠图 | `Hand Segmentation` | 查询 `Hand Segmentation` 对象知识 |
| 皮肤抠图、身体画笔、皮肤换色或皮肤纹理 | `Skin Segmentation` | 查询 `Skin Segmentation`，需要自定义材质时再查材质知识 |
| 人像抠图或保留整个人物 | `Portrait Segmentation` | 查询 `Portrait Segmentation` 对象知识 |
| 服装抠图、换装或衣物纹理 | `Clothing Segmentation` | 查询 `Clothing Segmentation` 对象知识 |
| 主体抠图，目标可能是人、宠物或道具 | `Subject Segmentation` | 查询 `Subject Segmentation` 对象知识 |
| 人体、皮肤、服装或主体轮廓描边 | `Outline` | 查询 `Outline` 对象知识，按目标选择轮廓类型 |
身体跟踪需要关注跟踪丢失、多人目标、左右侧镜像和关键点抖动。全身驱动还需检查模型骨骼、蒙皮和姿态映射是否匹配。
