---
name: AudioGeneration
description: 为当前工程生成并导入单段音频，说明如何描述音源、时长和响度，以及如何编写 BGM 或音效提示词。多段音频使用 AssetBatchGeneration，场景绑定和播放控制使用 Audio。
---

# AudioGeneration

`generate_audio` creates **one** audio asset and imports it into the current
project.

If the request contains **multiple** new clips, or a mixed image/audio asset
set, switch to `AssetBatchGeneration` and keep this skill only for per-clip
prompt design.

> **Scope:**
> - This is a **single-asset** workflow.
> - For multiple audio clips or mixed image/audio requests, use
>   `AssetBatchGeneration`.
> - Put duration guidance directly in the `prompt`.
> - Describe background music, looping ambience, or a long bed track directly
>   in the prompt.
> - It does not create placeholder assets or parse long design briefs.

## When to use this skill

Use this skill when the job is "make me a sound":

- menu / reward / fail / click / hit / explosion / whoosh / alert SFX
- ambient loop or scene bed
- one background music cue

**BGM Opt-In:** Do not generate BGM by default. Treat a request as BGM only
when the user explicitly asks for background music, ambience, a loop, or a
long bed track.

If the clip must then be attached to an `AudioComponent`, switch to
`skills_root/ability/Audio/SKILL.md` after generation. This skill is about **prompting the
generator**, not scene wiring.

## Minimal workflow

1. Decide whether the requested clip is **SFX** or **BGM**. Default to SFX
   unless BGM is explicit.
2. Write a short prompt that matches the requested clip role, names the heard
   sound first, and includes duration.
3. Call `generate_audio(name, prompt)`.
4. If the user wants the clip used in-scene, follow up with the `Audio` skill.

For multiple clips, prepare each prompt the same way, then hand the full list
to `generate_assets_batch` through `AssetBatchGeneration`.

## Prompt writing

- **Prompt Structure (CRITICAL):** The prompt MUST faithfully match the
  requested audio asset and stay aligned with its usage and role.
  - BGM: `带基调与场景感的背景音乐（可选: 声学纹理或节奏描述, 循环自然, <时长约束>）`。
  - SFX: `即刻响起 + 时长词 + 带声学质感的声源（可轻量包含事件语义, 可选: 声学细节, 响度词, <时长约束>）`。
- **Source-First Principle (CRITICAL):** The source description is the primary
  driver of the generated audio. The source outside parentheses should already
  convey the core identity; parenthesized content only refines it.
  - GoodCase: `即刻响起一声清脆的鸟鸣声（清晰, 约1s）`
  - GoodCase: `即刻响起一声深沉的金属撞击声（响亮, 约1s）`
  - BadCase: `清晰, 穿透力强, 高频颤音（一阵鸟鸣声, 约2s）`
- **BGM Anchor Quality (CRITICAL):** For BGM, the source anchor should carry
  both tonal identity and scene feel, not just a generic category label.
  - GoodCase: `温暖明亮的轻松氛围背景音乐`
  - GoodCase: `神秘低沉的洞穴探索背景音乐`
  - BadCase: `背景音乐`
  - BadCase: `主界面背景音乐`
- **Minimal Sufficiency (CRITICAL):** Use the lightest prompt that already
  disambiguates the sound. Do not stack extra acoustic details just for
  completeness.
  - GoodCase: `即刻响起一阵清脆的鸟鸣声（清晰, 自然衰减, 约2s）`
  - BadCase: `即刻响起一阵清脆的鸟鸣声（高频颤音, 短促跳跃的鸣叫, 复杂的空间混响, 细碎回声, 清晰, 穿透力强, 约2s）`
- **Parenthesized Grouping (CRITICAL):** Everything inside parentheses refines
  the source sound. Never put independent sound elements inside the same
  parentheses.
  - GoodCase: `即刻响起一阵轻快的煽动翅膀声（清晰, 穿透力强, 约2s）`
  - BadCase: `煽动翅膀声, 噗噗声, 扫频, 清晰, 穿透力强, 约2s`
- **Concrete Acoustic Language (CRITICAL):** Prefer specific audible source
  descriptions over vague, abstract, or purely functional labels.
  - GoodCase: `清脆的鸟鸣声`
  - GoodCase: `深沉的低频雷声轰鸣`
  - BadCase: `一个很好听的声音`
  - BadCase: `悬疑的氛围`
- **Narrative Meaning as Supplemental Context (CRITICAL):** Event or gameplay
  meaning may be folded into the source description when useful, but it must
  not replace the audible source.
  - GoodCase: `即刻响起一声清脆的任务成功奖励铃音`
  - BadCase: `任务完成提示音`
- **Presence / Loudness Anchoring (CRITICAL):** Include `1-2` presence,
  loudness, or intensity qualifiers unless the asset is intentionally quiet.
  Use `清晰/穿透力强` for sharp UI or alerts, `响亮/饱满` for heavy impacts,
  `近距离/清晰` for mechanical or tactile sounds, and `轻柔/柔和/低音量`
  for quiet ambience or soft cues.
- **Duration Control (CRITICAL):**
  - SFX with explicit user duration: use `约xs`.
  - Common SFX with no explicit duration: use `约1s`.
  - Heavier, staged, or tail-heavy SFX: use `约2s` or `约3s`.
  - BGM or ambience with explicit user duration: use `约xs`.
  - BGM or ambience with no explicit user duration: use `至少15s`.
- **Composite Sounds (Multi-Stage):** Use multi-stage prompts only when the
  clip truly has sequential stages. Keep stages in natural temporal order with
  `先是...随后...` or `先是...紧接着...`, and give each stage its own acoustic
  modifiers if needed.
  - GoodCase: `先是一声机械装填的咔哒声（清晰, 金属质感），紧接着一次重型炮弹发射的轰鸣声（响亮, 低频震撼）。整体响亮且富有冲击力，约2s。`
  - GoodCase: `即刻响起两声清脆的射击声（短促, 穿透力强, 约1s）`
  - BadCase: `装填炮弹发射声, 金属, 爆炸, 响亮, 约2s`
- **Alert/Error SFX Simplicity:** For warning, alert, error, or failure SFX,
  keep the prompt focused on `1-2` core sound elements.
  - GoodCase: `即刻响起一声刺耳的警报蜂鸣声（高频脉冲重复, 响亮, 穿透力强, 约1s）`
  - BadCase: `警报声, 断电噪声, 金属碰撞, 电流滋滋声, 低频嗡鸣中断, 合成器扫频`
- **Preflight Prompt Check:** Before calling `generate_audio`, remove repeated
  loudness words, unnecessary acoustic details, narrative phrases that
  overwhelm the sound source, abstract mood words beyond what the scene needs,
  and more than three competing sound layers. Intentional multi-stage
  composites count stages, not competing layers.

## Prompt templates

### SFX

Use the same structure as the audio composer workflow:

`即刻响起 + 时长词 + 带声学质感的声源（1-2 个声学修饰词, 约1s/2s/3s）`

Examples:

- `即刻响起一下清脆的按钮点击声（清晰, 穿透力强, 约1s）`
- `即刻响起一次沉闷的爆炸声（响亮, 低频轰鸣, 约2s）`
- `即刻响起一段空灵的魔法释放嗡鸣（清晰, 渐强回响, 约2s）`

### BGM

Use mood + scene + looping constraint:

`<情绪> + <场景>背景音乐（1-2 个声学锚点, 循环自然, 至少15s）`

Examples:

- `温暖轻松的主界面背景音乐（明亮, 循环自然, 至少15s）`
- `神秘低沉的洞穴探索背景音乐（幽静, 回响, 循环自然, 至少15s）`
- `紧张压迫的战斗背景音乐（响亮, 低频铜管, 循环自然, 约20s）`

## Tool-call examples

### Generate one SFX

```json
{
  "name": "reward_chime",
  "prompt": "即刻响起一声清脆的奖励铃音（清晰, 明亮, 约1s）"
}
```

### Generate one BGM

```json
{
  "name": "cave_bgm",
  "prompt": "神秘低沉的洞穴探索背景音乐（幽静, 回响, 循环自然, 至少15s）"
}
```

## Repair loop

If the first result is off:

- Wrong sound source: change the **main noun/verb** first.
- Too busy or muddy: remove extra layers and keep one primary source.
- Too long / too short: rewrite the duration phrase.
- Feels like music when it should be SFX: shorten the prompt and make the
  source more event-like.
- Feels like SFX when it should be BGM: add a scene anchor and `循环自然`,
  and state that it is background music.

## Hand-off

After `generate_audio` succeeds:

- Use `list_resources` / `inspect` if you need to confirm the imported MP3.
- Use `skills_root/ability/Audio/SKILL.md` if the asset must be played in-scene.
