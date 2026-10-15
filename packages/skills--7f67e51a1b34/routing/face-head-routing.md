# 脸部/头部玩法指南

## 能力指引

### 跟脸与头部绑定

- **Head Tracker**：用于 3D 物体跟随头部或脸部部位，也可读取头部姿态；
  但贴脸程度不如 Face Mask。
- **Face Sticker（`FaceImageV2`）**：用于带 Face Binding 的 3D 图片跟脸移动，
  是“贴一个图跟脸走”的首选；不等同于分割型 `FaceImageSegmentation`。

### 美妆与外观覆盖

- **Face Mask**：用于妆容、全脸纹理和 2D 睫毛等贴脸效果；
  通常比贴纸更贴脸，但依赖合适素材且调参成本更高。
- **Eye Color**：用于美瞳、瞳色、虹膜图案；不要先用普通脸贴代替。
- **3D Eye**：用于有体积、深度、反光或替换效果的 3D 眼球；
  适合异形眼、科幻眼、立体瞳孔等。
- **3D Eyelashes**：用于跟随眼睑的 3D 睫毛网格，可调样式、长度、卷翘、
  密度和颜色；仅需要 2D 睫毛纹理时使用 Face Mask /
  Eyelash Effect。

### 人脸形变

- **FaceDistortionEntity**：Agent 默认的人脸美型入口；
  适合精细调整脸型、眼睛、鼻子、嘴巴等五官，不要用贴纸或 Face Mask 模拟几何形变。
- **FaceDistortion3DEntity**：Agent 默认的 3D 人脸形变入口；
  适合整体脸型和立体五官参数调整，与局部美型分开选择。

### 其他脸部能力

- **FaceFitting3D**：用于面部贴花和脸部表面贴合效果；
  不按通用 3D 人脸拟合网格理解，也不是头部跟踪或分割抠图能力。
- **FaceTransfer**：使用 `FaceBindingV2` 贴合 3D 脸部网格，
  用于人脸纹理或外观迁移；它不是通用跟踪能力，也不是抠图能力。
- **3D 面具（`FaceShapeV2`）**：用于贴合脸部表面的 3D 面具或自定义脸部网格；
  它不是普通 3D 头饰，也不等同于 2D `Face Mask`。
- **Face Inset**：用于把眼睛、嘴巴等五官抠出并放到其他对象或固定位置；
  它不是头部跟踪方案，也不是美妆/贴纸的默认载体。

## 快速判断

按最终玩法和视觉载体选择能力，不要因为出现“脸部跟踪”就默认使用 Head Tracker。

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 3D 头饰、帽子、耳朵、头顶光环、刚性模型 | Head Tracker | 读取 HeadTracker 指南 |
| 摇头、转头、点头控制玩法 | Head Tracker + 人脸姿态数据 | 读取 HeadTracker 指南 |
| `FaceImageV2` 3D 图片跟脸移动 | FaceImageV2 | 查询 `FaceImageV2` 对象知识 |
| 快速做简单面具，不要求精确贴合脸部形变 | `FaceImageV2` | 查询 FaceImageV2 对象知识 |
| 全脸妆容、面绘、脸谱、面具、全脸纹理 | Face Mask | 查询 Face Mask 知识 |
| 脸部美型、精细五官调整或局部修饰 | `FaceDistortionEntity` | 查询 FaceDistortionEntity 对象知识 |
| 3D 脸型或立体五官调整 | `FaceDistortion3DEntity` | 查询 FaceDistortion3DEntity 对象知识 |
| 面部贴花或脸部表面贴合效果 | `FaceFitting3D` | 查询 FaceFitting3D 对象知识 |
| 人脸纹理或外观迁移 | `FaceTransfer` | 查询 FaceTransfer 和 Face Binding 知识 |
| 3D 面具或贴合脸部表面的自定义网格 | `FaceShapeV2` | 查询 FaceShapeV2 对象知识 |
| 美瞳、瞳色、虹膜图案 | Eye Color | 查询 Eye Color 知识 |
| 有体积、深度、反光或替换效果的 3D 眼球 | 3D Eye | 查询 `3D Eye` 和 `Eye3D` 知识 |
| 立体睫毛、卷翘睫毛、可调密度的 3D 睫毛 | 3D Eyelashes | 查询对象和组件知识 |
| 2D 睫毛纹理或睫毛妆效 | Face Mask / Eyelash Effect | 查询 Eyelash Effect，勿选 3D Eyelashes |
| 头部、脸部或眼睛区域的遮罩、换色、描边 | 分割遮罩合成 | 读取 segmentation 指南 |
| 抠取眼睛、嘴巴等五官并放到其他对象或固定位置 | Face Inset | 查询 Face Inset 知识 |
