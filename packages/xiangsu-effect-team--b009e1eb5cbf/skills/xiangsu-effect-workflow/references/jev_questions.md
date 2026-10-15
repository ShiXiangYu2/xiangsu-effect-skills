# JEV 决策门问题模板

每个阶段切换处如遇到决策问题，用 `scripts/jev_client.py` 投给 JEV。下面是可复用的 `--questions` JSON 片段，按阶段取用。

> 调用示例：
> ```bash
> python scripts/jev_client.py \
>   --state '{"task":"水波纹玻璃折射特效","stage":"策划","参考":"用户要真实物理感"}' \
>   --questions '<下方某个 JSON>'
> ```

---

## Gate P1 — 策划 → 设计（技术路线）
```json
{
  "route": {
    "type": "choice",
    "instructions": "判断该特效最适合的视觉技术路线",
    "criteria": {
      "材质着色器": "用材质数学模拟物理现象，真实感最高",
      "后处理": "用 PostProcess 叠加滤镜，开发快、可控",
      "粒子": "用粒子模拟飞溅/烟/光，适合动态发散",
      "视觉算法": "用检测/分割数据驱动画面，交互性强"
    }
  }
}
```

## Gate D1 — 设计 → 创意（风格方向）
```json
{
  "style": {
    "type": "choice",
    "instructions": "为特效选定整体视觉风格",
    "criteria": {
      "写实": "贴近真实物理与材质，可信度高",
      "二次元": "卡通描边、饱和色，年轻向",
      "国潮": "传统纹样与配色，文化感强",
      "极简科技": "低饱和、几何、未来感"
    }
  }
}
```

## Gate M1 — 创意 → 素材（资产生产路由）
```json
{
  "generator": {
    "type": "choice",
    "instructions": "为该视觉资产选择生产路由",
    "criteria": {
      "image-generator": "视觉语义与表面质量主导（角色/贴纸/插画/材质纹理）",
      "svg-generator": "硬性精度二维几何（边框/孔位/对称/槽位/mask）",
      "script-runtime": "由脚本或材质运行时生成，不产生 PNG"
    }
  }
}
```

## Gate E1 — 素材 → 特效（素材过关判定）
```json
{
  "material_pass": {
    "type": "choice",
    "instructions": "判断这批素材是否满足进入特效组装的质量门槛",
    "criteria": {
      "通过": "风格一致、透明通道正确、分辨率达标，可直接组装",
      "返工部分": "多数可用，个别资产需重生成（列出 key）",
      "整体返工": "风格/质量不达标，回到创意阶段"
    }
  }
}
```

## Gate V1 — 特效 → 验证（可上线判定）
```json
{
  "ship": {
    "type": "choice",
    "instructions": "判断成片是否达到可上线质量",
    "criteria": {
      "可上线": "视觉/性能/交互均达标",
      "小修": "有轻微瑕疵但不阻塞，记录后上线",
      "迭代": "核心体验不达标，回到对应阶段迭代"
    }
  }
}
```

## 通用打分门（质量分）
```json
{
  "quality": {
    "type": "score",
    "instructions": "对当前产物的整体质量打分(0-1)",
    "criteria": {"质量": "综合视觉真实性、交互连续性、参考一致性"}
  }
}
```
