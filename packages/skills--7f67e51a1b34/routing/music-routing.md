# 音乐玩法指南

## 能力指引

- **BGM 播放**：背景音乐的导入、绑定、循环、音量和播放/停止；
  `Audio_BGM` 是通用 BGM 播放对象。

- **SFX 播放**：事件音效、语音和提示音通常按事件触发；
  可使用一次性播放或独立音量，`Audio_Effect` 是对应对象。
- **音频素材生成**：当项目没有现成 BGM、环境音或反馈音效时，先生成音频资产。
- **音乐检测**：节拍、音量、音高、频谱、关键词等声音输入驱动玩法或视觉反馈。
- **节奏玩法**：踩点、判定窗口、连击、得分等需要 Timing 配合。

## 快速判断

| 目标 | 首选能力 | 指南 |
| --- | --- | --- |
| 生成一段 BGM、环境音或音效 | AudioGeneration | 读取 `skills_root/assets/AudioGeneration/SKILL.md` |
| 场景里循环播放 BGM | `Audio_BGM` | 查询 AudioComponent 和 Audio_BGM 对象知识 |
| 事件触发音效、语音或提示音 | `Audio_Effect` | 查询 AudioComponent 和 Audio_Effect 对象知识 |
| 节拍点击、踩点、音量/音高/频谱驱动 | Audio Detection | 读取 `skills_root/ability/Audio/SKILL.md` |
| 节奏判定、计分、连击、命中窗口 | Timing | 读取 `skills_root/ability/Timing/SKILL.md` |
| 音频驱动粒子、动画或视觉反馈 | Audio + 视觉能力 | 读取粒子或动画指南 |
