# 像塑换壳实战 Playbook（reskin）

本文件沉淀自三次模板换壳任务的真实实践，是 `SKILL.md`（连接/入口）之上的**制作层**补充。
覆盖：出方案 → 定主题 → 资产制作 → 绑定 → 预览验收 → 发布 的全流程，以及所有踩坑点。

---

## 0. 一句话结论

像塑模板换壳有两条**完全不同**的资产路径，选错路会浪费大量时间：

| 资产类型 | 做法 | 能不能用 AI 生图 |
|---|---|---|
| 跟脸/跟头 **贴纸**（paster/sticker） | AI 生图 → import 绑定 | ✅ 能，对齐由像塑跟踪点负责 |
| **UV 面部贴图**（eye/blusher/lips） | **PIL 本地调色**（见 §3.1） | ❌ 不能，AI 生图无法对齐脸部 UV |
| **模型贴图**（.omtl 绑定的 PNG） | **PNG 原路径覆盖 + 重新 import**（见 §3.2） | ❌ 不能，且材质二进制不可手改 |

---

## 1. 换壳总流程（7 步）

1. **出方案**：参考用户当前打开的模板，给一个同类型但换主题的特效方案（主题名 + 视觉关键词 + 涉及的组件）。
2. **定主题**：用 AskUserQuestion 让用户确认主题（一次收敛，不要反复问）。
3. **save_plan**：把方案落成计划，用户确认后实施。
4. **资产制作**：按 §3 的两条路径分别产出（AI 生图 or PIL 调色）。
5. **绑定**：用 `edit_by_dsl` 的 `set_component` / `import_resource` 把资产挂到组件（见 §4、§5）。
6. **预览验收**：`set_preview_video` + `interact_by_dsl` 截图 + PIL 分区放大核对（见 §6）。
7. **收尾**：提醒用户在编辑器里 **保存并发布/提交审核**；提交失败按 §7 排查。

> 节奏原则：先用一台预览视频跑通主视觉，再补第二台（宠物猫/双源）做兼容验收。

---

## 2. 关键约束（铁律，违反必返工）

- **UV 面部贴图绝不 AI 生图**：脸部 UV 网格是固定的，AI 生成的图无法对齐，结果会糊脸/错位。必须 PIL 本地按饱和度加权旋转色相。
- **.omtl 材质是二进制**（TTEH 头），**不可手改**；模型换色只能改它引用的 PNG，然后**同路径重新 import_resource** 刷新。
- **import_resource 是 edit_by_dsl 的子命令**，不是独立工具；参数只传 `path`，不要传多余字段。
- **绑定时优先用组件 GUID（cXX）**：对象 GUID（sXX）在 `set_component` 上经常解析失败，换组件 GUID（cXX）直连即过。
- **调色前先跑色相分布**（见 §3.1 `uv_recolor.py --analyze`），**按实测阈值分桶**，不要凭视觉猜分支（曾因把"绿蒂"误判为 <90° 整片转粉，全毁后从备份恢复）。
- **预览截图用分区放大**核对，肉眼看全屏截图容易漏掉"眼镜过淡""兔须遮眼"这类细节。

---

## 3. 资产制作两条路径

### 3.1 路径 A：UV 面部贴图 → PIL 本地调色

调用 `scripts/uv_recolor.py`。

**sat_rotate 模式**（妆容/伪素颜整体推色）：
```bash
# 先跑分布定阈值
python scripts/uv_recolor.py --analyze --src Assets/temp.folder/eye.png

# 按饱和度加权旋转色相：S=0 转 0°，S=1 转 35°；降饱和到 0.72，明度不变
python scripts/uv_recolor.py --mode sat_rotate \
  --src Assets/temp.folder/eye.png --dst eye_peach.png \
  --rot-base 0 --rot-full 35 --sat-mul 0.72 --val-add 0
```
> 经验：唇色中位若偏黄（如 46°），需 +35° 转橘棕（目标 ~30°），并降饱和 ~28%，否则会发黄。

**range_remap 模式**（模型贴图换色，按色相区间分桶）：
```bash
python scripts/uv_recolor.py --mode range \
  --src 香蕉_1_color.png --dst 香蕉_strawberry.png --spec banana_spec.json
```
`banana_spec.json` 示例（58° 为黄皮/绿蒂分界，<45° 棕柄保留）：
```json
[
  {"hmin":48,"hmax":58,"hue":345,"sat_mul":0.42,"val_add":0.14},
  {"hmin":58,"hmax":78,"hue":155,"sat_mul":1.0,"val_add":0.0},
  {"hmin":30,"hmax":45,"keep":true}
]
```
> 阈值必须来自 `--analyze` 的真实分布；同一模型若有多份贴图路径（如 `Assets/香蕉/` 与 `Assets/香蕉 (1)/`），**每份都要改**。

### 3.2 路径 B：模型贴图 → PNG 原路径覆盖 + 重新 import

模型（头套/道具）的贴图是 `.omtl` 材质引用的 PNG，**直接覆盖原路径文件**，再 `import_resource` 同路径刷新：

```json
// edit_by_dsl → import_resource
{ "path": "Assets/香蕉/纹理/香蕉_1_color.png" }
```
> 要点：覆盖后必须 re-import 才会刷新；改的是 PNG 像素，不是 .omtl。深棕蒂、奶黄等附属色同样走 range_remap。

---

## 4. edit_by_dsl 命令速查

`edit_by_dsl` 统一收一个 `command` 字段，常见子命令：

| command | 用途 | 关键参数 |
|---|---|---|
| `set_component` | 改组件属性（texture / color / tint 等） | 组件 GUID、属性名、值 |
| `import_resource` | 导入/刷新资源（**子命令，只传 path**） | `path` |
| `delete_resource` | 删除冗余资源（清理 V1 废稿） | 资源 GUID/路径 |

> ⚠️ 不要把 `import_resource` 当独立 MCP 工具调用，会失败；它只能作为 `edit_by_dsl` 的子命令。

---

## 5. 绑定与 GUID 规则

- **组件 GUID 形如 `cXX`**（如 `c26`），**对象 GUID 形如 `sXX`**（如 `s13`）。
- 绑定贴图/改色用 **`set_component` 传组件 GUID**。
- 实测：某次用对象 GUID `s13` 绑定眼睛贴图解析失败，改用组件 GUID `c26` 直连 `set_component` 立即成功。
- 同一资产要挂到多个跟踪点（如 5 个跟头贴纸槽）时，逐个组件绑定，注意槽位 GUID 列表。

---

## 6. 预览验收

```text
1) set_preview_video  →  选预览视频（单人 / 宠物猫 / 双源）
2) interact_by_dsl    →  reset_preview  →  wait(帧进度)  →  screenshot(落盘)
3) 用 scripts/crop_regions.py 按区域放大核对：
     python scripts/crop_regions.py --src shot.png \
       --regions regs.json --outdir ./tiles --scale 3
```
`regs.json` 关注区（比例坐标 0~1）：
```json
[{"name":"eye","x":0.30,"y":0.32,"w":0.18,"h":0.10},
 {"name":"lips","x":0.40,"y":0.62,"w":0.20,"h":0.12},
 {"name":"headgear","x":0.35,"y":0.02,"w":0.30,"h":0.22}]
```
验收清单：眼镜/边框是否够明显、兔须是否上扬遮眼、妆容是否发黄、头套色是否均匀、吉祥物位置是否出框。

---

## 7. 提交审核失败排查

用户报"提交审核一直不成功"时（非工程问题，多为网络）：

1. **查编辑器日志**（路径形如 `C:/Users/18168/AppData/Local/DouyinAR/Logs/.../editor.log`），grep：
   - `ENOTFOUND mcs.snssdk.com` → DNS 解析失败
   - `code:28` / `timeout` → 请求超时
2. **DNS 一秒判定**：`nslookup <任意域名> 223.5.5.5`，能解析说明是本机 DNS/代理问题，不是服务器问题。
3. **查双网关抖动**：`route print` 看是否有两条默认网关（如 `192.168.10.1` metric 291 与 `192.168.89.1` metric 50），双网关会造成间歇抖动。
4. **结论**：若日志是间歇性 `ENOTFOUND`/超时，多为本机网络抖动，**让用户重试即可**，不要动工程文件。已实测：用户重试一次即成功提交。

> 排障顺序铁律：**联通性（DNS/网关）→ 功能 → 官方脚本 → AI 辅助**。

---

## 8. 反模式（不要做）

- ❌ 用 AI 生图去"对齐脸部 UV"——不可能成功。
- ❌ 手改 `.omtl` 二进制——改不了，且易损坏。
- ❌ 凭视觉猜色相分支阈值——先 `--analyze` 跑真实分布。
- ❌ 用对象 GUID `sXX` 做 `set_component`——换 `cXX`。
- ❌ 把 `import_resource` 当独立工具调用——它是 `edit_by_dsl` 子命令。
- ❌ 只肉眼看全屏截图就判定通过——分区放大逐区核对。
- ❌ 提交失败时去改工程文件——先查日志/网络，多半是抖动，重试即可。
