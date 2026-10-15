# 材质效果玩法指南

## 能力指引

- **内置材质调参**：颜色、贴图、透明度、粗糙度、金属度等基础 PBR/Unlit 参数，
  不需要新建 Shader；适合只调整已有材质参数的简单效果。

### 自定义材质

- **自定义 OMTL/AUSL**：使用像塑内部 OMTL 材质格式和 AUSL Shader 体系；
  可实现对象表面或屏幕空间效果，溶解、描边、发光、折射、扭曲、流光只是常见示例。
- **ShaderToy/Pipeline**：使用兼容外部 OpenGL / ShaderToy 的自定义材质方式；
  支持 ShaderToy、Buffer、Cubemap、反馈链路、程序化画面和复杂合成。

两种实现方式具有共通能力：都可以制作对象表面效果、屏幕空间效果、程序化画面、
复杂合成和部分后处理；主要差异是内部 OMTL/AUSL 格式与外部 OpenGL / ShaderToy 兼容路径。

### 后处理与运行时控制

- **后处理材质**：全屏滤镜、模糊、色散、背景变色等屏幕级效果。
- **运行时材质控制**：脚本动态调整颜色、强度、偏移、贴图或开关。

后处理描述的是屏幕级渲染目标，可以使用内置后处理材质，也可以使用自定义材质实现；
运行时控制描述的是参数控制方式，可以作用于内置或自定义材质。

复杂度和时间驱动的判断：

- 简单颜色、贴图、透明度或基础光照变化，优先使用内置材质。
- 只需要已有材质参数随时间变化时，内置材质配合 `MeshRendererScript` 即可。
- 需要 UV 滚动、顶点变形、噪声计算、程序化图案、反馈或复杂合成时，使用自定义材质。
- 时间相关本身不是自定义材质的充分条件；
  关键在于是否需要 Shader 逻辑或自定义数据通道。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 只改基础颜色、贴图或数值 | 内置材质 | 读取 `skills_root/assets/MaterialAuthoring/SKILL.md` |
| 对象表面溶解、描边、发光、折射、扭曲 | 自定义 OMTL/AUSL | 读取 MaterialAuthoring |
| ShaderToy、Buffer、Cubemap、反馈 Pipeline | ShaderToy/Pipeline | 读取 MaterialAuthoring |
| 全屏滤镜、背景变色、模糊、色散 | 后处理材质 | 读取 `skills_root/ability/PostProcess/SKILL.md` |
| 运行时动画化材质参数 | MeshRendererScript | 读取 `skills_root/ability/MeshRendererScript/SKILL.md` |
| 简单材质参数随时间变化 | 内置材质 + MeshRendererScript | 读取 MeshRendererScript |
| UV、顶点、噪声或复杂合成随时间变化 | 自定义材质 | 读取 MaterialAuthoring |
