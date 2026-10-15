# 分割特效玩法指南

## 能力指引

以下分组按主要用途组织能力，不是互斥分类；
分割通常作为遮罩层，与跟踪、材质、粒子或后处理组合。

### 区域遮罩

- **分割遮罩合成**：按抠图目标选择遮罩，支持人像、主体、头部、脸部、
  头发、手部、眼睛、天空等区域，用于局部换色、描边和混合。
  具体对象按目标区域和承载方式选择；脸部区域的分割贴纸使用
  `FaceImageSegmentation`，普通 3D 图片跟脸使用 `FaceImageV2`。

### 背景与前后景

- **背景处理**：背景替换、虚化、变暗、变色、风格化，通常是后处理或材质合成。
- **前后景遮挡**：让粒子、贴纸、模型在人物或主体前后正确分层，
  重点是遮罩和渲染顺序。

## 快速判断

按目标查询对应的 Segmentation 对象知识；需要自定义遮罩合成时，
再读 `skills_root/assets/MaterialAuthoring/SKILL.md`。
主体分割提取画面中的显著主体，不限于人物。

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 人像抠图、保留人物、替换人物背景 | Portrait Segmentation | 查询 Portrait Segmentation 对象知识 |
| 提取显著主体、主体局部效果或遮挡 | Subject Segmentation | 查询 Subject Segmentation 对象知识 |
| 头部、脸部或头发抠图 | 分割遮罩合成 | 分别查询 Head / Face / Hair Segmentation 对象知识 |
| 带背景分割的区域贴纸 | `FaceImageSegmentation` | 查询 Face Segmentation 对象知识 |
| 眼睛、耳朵、嘴唇或牙齿区域抠图 | 分割遮罩合成 | 查询对应区域分割对象 |
| 手部抠图、局部换色、描边或遮挡 | Hand Segmentation | 查询 Hand Segmentation 对象知识 |
| 皮肤、衣服或宠物抠图 | 分割遮罩合成 | 分别查询 Skin / Clothing / Pet Segmentation 对象知识 |
| 天空、地面或建筑区域抠图 | 分割遮罩合成 | 查询对应 Sky / Ground / Building Segmentation |
| 背景虚化、背景变色、人物描边 | 分割遮罩 + 后处理 | 查询 PostProcess / MaterialAuthoring |
| 只需要一张替换背景图 | 图片资产 | 不在本指南展开，按 `assets/` 检索图片生成能力 |

分割对象输出的是区域遮罩，不等于关键点或姿态跟踪，
也不直接提供脸部、身体或模型的几何形变。
