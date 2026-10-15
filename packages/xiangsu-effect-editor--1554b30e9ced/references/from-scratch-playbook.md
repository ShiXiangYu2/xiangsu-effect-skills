# 从零制作新特效 Playbook（20261011 ins分屏边框实战沉淀）

适用场景：在像塑**新建的空白工程**里从零搭一个完整特效（区别于 reskin-playbook 的换壳场景）。
本案例：官方任务【创新】ins分屏边框 —— 上下错列双屏拍立得白框 + Render Texture 实时摄像头画面 + 贴纸/波点/英文文字装饰，纯配置零脚本。

## 0. 流程总览

1. 连接（按 SKILL.md）→ get_project_context 核对 → 读 AGENTS.md + rules（general/scene-common/validation/anti-patterns）+ skills_root/SKILL.md 路由
2. `update_handoff_context` 逐字记录用户原文消息链（必须先于一切工程查询）
3. 出方案 → save_plan（status=confirmed 需用户确认或明确授权"直接操作实施制作"）
4. 执行顺序：预览输入确认 → generate_assets_batch 一次生成全部资产 → 搭骨架 → 接资产 → capture_preview 分段验收 → 修问题 → 提醒用户保存
5. 用户确认"新建工程后我继续"后：轮询 `list_instances` 等新实例/工程出现（has_active_project=true），拿到新 instance_id 后全部调用换新 ID

## 1. 实战坑速查（每条都踩过，直接复用结论）

### MCP / 工具层
- **宿主工具列表可能没有像塑 DSL 工具**：直接 HTTP JSON-RPC 调 `http://127.0.0.1:17320/mcp`（见 rpc-fallback.md）。实测该端点**无状态**，不需要 initialize/session id，直接 `tools/call` 即可；响应是 SSE 格式时取 `data:` 行。
- **参数含中文/特殊符号的长 JSON 走 argv 会被 shell 弄坏**：一律写成 JSON 文件再传（`python mcpcall.py edit_by_dsl cmd.json`）；helper 脚本三件套见 §4。
- **inspect 返回超 ~4000 字符会截断**导致 JSON 解析失败：用 `grep -o '"type": "组件类型", "guid": "[a-z0-9]*"'` 提取关键 GUID。
- **`edit_by_dsl` 一次 batch 首条命令失败时后续全部 skipped**（不算 executed）：失败也要读首条 error，别只看 failed 数。
- **Enum 属性只能用 `{"type":"Enum","data":"Custom"}` 对象格式**：裸字符串 `"Custom"` 和数字 `2` 都报 `Invalid data to deserialize`。
- **`set_scene_object` 不支持 renderOrder**；`set_component` 的 guid 参数不支持"场景对象GUID+顶层component_type"组合，$ref 只认本批次 alias 或**组件**真实 GUID（场景对象 GUID + component_type 内嵌 $ref 格式才行：`{"$ref":"alias","component_type":"Image"}`）。

### 场景层
- **2D Text 会被 Screen Image 盖住**（最高频坑）：`add_builtin_object("2D Text")` 自动挂到"2D摄像机"下，sibling 序号靠前（renderOrder 2/3），而后建的 Screen Image 是 4+。`set_scene_object` 改不了 renderOrder → **正解：`move_scene_object` 把文字挂到"最后绘制"的对象下当子级**（子级在父级之后绘制），anchoredPosition 按父级中心重新换算（目标屏幕位 - 父级屏幕位）。
- **编辑器 Scene 视图（get_scene_view）里 Render Texture 显示"导入素材查看效果"占位图是正常现象**——编辑态不跑预览；只有 capture_preview 的运行态截图才能验证 RT 内容。别误判为绑定失败。
- **纯色圆点/色块**：Image 默认纹理是图片，靠 color 染色会显示成"小照片"。正解：本地生成纯白圆 PNG（Python zlib 手写 PNG 即可）→ import_resource → texture 绑它 + color 染色 + drawMode Ellipse。
- **RT 分屏画面**：add_builtin_resource "Render Texture" → 新建相机 set renderTexture → Screen Image 的 Image.texture 绑 RT 资源 GUID，stretchMode="Fill" 裁切填充。**无需脚本**。
- **空 Screen Image 的默认 sizeDelta 是 336x336**，不是全屏；2D Text 默认 72 号字。

## 2. 性能优化清单（平台检测"帧率低"警告的对策）

| 项 | 做法 |
| --- | --- |
| Render Texture 分辨率 | `set_resource_properties` RT：sizeMode=Custom、customWidth/Height 按显示尺寸减半（360x640 即省 75% 像素），msaaMode=NONE |
| 贴图压缩 | PNGImage 资源：compressionType=Manual、compressQuality=Medium、compressMaxResolution 按显示尺寸选 Size256/512/128（显示 ≤110px 的贴纸用 256 足够） |
| 结构 | 能用纯配置就不用脚本；避免序列帧、美妆小项、多余相机通道 |

## 3. 原创度优化（平台"玩法雷同"提示的对策）

- 文案避免大众模板词（summer memo / GOLDEN HOUR 撞车率高），换主题化原创短句（film diary / 24 frames of today / double frame my memo）
- 贴纸用 generate_assets_batch 原创生成（prompt 写明 retro ins scrapbook / flat vector / transparent background），不用平台重复素材
- 资产批量生成 prompt 模板：`single <主体> sticker, <风格> style, <配色>, flat vector, front view, centered, transparent background` + `need_seg:true`，尺寸 512/960

## 4. MCP helper 三件套（本次验证可用，可复制进工作目录）

```python
# mcpcall.py —— 调工具，参数从 JSON 文件读（避免 shell 转义），stdout 截断 4000 字符
# mcpraw.py —— 同上但完整结果写文件：python mcpraw.py <tool> <args.json> <out.json>
# mcpcap.py —— capture_preview 并把截图 base64 落盘为 shot_1.png（配合 Read 看图）
```

核心调用（无状态 JSON-RPC）：

```python
import json,urllib.request
def call(name,args):
    req=urllib.request.Request("http://127.0.0.1:17320/mcp",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":name,"arguments":args}}).encode(),
        headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
    r=urllib.request.urlopen(req,timeout=180).read().decode()
    for line in r.splitlines():
        if line.startswith("data:"): r=line[5:].strip(); break
    d=json.loads(r)
    return d.get("result",{})
```

截图验收：capture_preview 返回 content 里 `type:"image"` 的 base64（jpeg），解码存 PNG 后用多模态 Read 看图，肉眼验收布局/文字/占位残留。

## 5. 本案例最终场景结构（可复用的分屏相框骨架）

```
分屏相机 (Camera, renderTexture=RT r5, renderOrder 10)
2D 摄像机 (自动创建)
├─ 上框_白底 (Screen Image 500x640, pos(-90,330), rot -5)
│   ├─ 上框_画面 (Screen Image 440x470, pos(0,55), texture=RT, Fill)
│   └─ 上框_文字 (2D Text, pos(0,-262), Typewriter 30, 深灰)  ← 子级随父绘制，不被盖
├─ 下框_白底 (Screen Image 500x640, pos(90,-310), rot 4)
│   ├─ 下框_画面 (同上)
│   └─ 下框_文字
├─ 胶片条/星星/爱心/笑脸贴纸 (renderOrder 10-13)
├─ 圆点x4 (白色圆纹理+染色+Ellipse, renderOrder 14-17)
└─ 标题/副文字 (2D Text, 挂在最后的圆点下保证最上层)
```

## 6. 验收闭环

- [ ] capture_preview 运行态截图：RT 显示摄像头画面、无默认纹理/占位残留
- [ ] get_scene_view 编辑态截图：核对文字渲染与布局（编辑态 RT 占位属正常）
- [ ] 文字可读性：深色字避免落在头发/深色衣物上（预览人像会动，留余量）
- [ ] 宿主安全区：文字/交互避开底部 ~180px 录制按钮区
- [ ] run_otsc_check：纯配置工程无 tsconfig 属预期，不算失败
- [ ] 平台性能检测 + 原创度提示，按 §2/§3 处理后重测

## 20261011 二次回流：新版 MCP 网关（xiangsu-mcp-manager 1.0.0）差异
- **项目类工具必须带 `instance_id`**（如 `{"instance_id":"1"}`），否则报 `Unknown gateway MCP tool`——极像"服务挂了"，实为路由参数缺失。先 `health`/`list_instances` 确认实例在。
- **edit_by_dsl 参数结构**：`{"instance_id","commands":[{"command_type","params","alias"}],"intention"}`。各命令参数名与旧版不同：`import_resource` 用 **path**；`add_builtin_resource` 用 **resource_type**；`add_builtin_object` 用 **object_type**；`set_resource_properties`/`set_component` 的目标参数都叫 **guid**。`set_component` 只接受 `guid`+`properties`（无 component_type，组件按属性名自动匹配）。
- **set_component 必须传组件 GUID**（inspect 场景对象拿 `components[].guid`），传场景对象 GUID 报 `Cannot find ComponentObjectEditor`。**alias 跨批次无效**，且 alias $ref 解析资源时曾出现全部解析到同一错误 GUID 的坑——**贴图绑定一律用 inspect/list_resources 查到的真实 GUID 直写**（`{"type":"Texture2D","guid":"r85"}`），不要依赖资源 alias。
- **`move_scene_object` 同父移动是 no-op**；跨父移动语义是**插到最前**（后移动的 renderOrder 更小）。要重排顺序：全部挪到临时父级再按"绘制顺序的逆序"逐个中转回挂。
- **算法层（GAN/美妆/滤镜）不会渲染进 Render Texture**：RT 相机只能拍到原始相机画面，美妆模板上做 RT 分屏会出现"未美妆鬼影叠脸"。改用半透明白圆角矩形做毛玻璃卡片更稳。
- 编辑器可能在 save_project 时断开 MCP（instanceCount 变 0），保存前先确认；断开后未保存的 DSL 改动会丢。

## 20261011 三次回流：性能检测"禁了还不过"的真凶
- **`set_scene_object` 禁用父对象不会级联停用子对象**（至少对 GAN/FaceMask 组）：禁了「韩系甜妹 s5」后其子级「GAN摄像机 s6/韩系甜妹 s7/形变 s8」仍然 ON 继续跑满算法；「韩国学妹 s31」关了子级「美瞳 s32/唇部妆容 s33」也在跑。**禁用算法组必须逐个列出全部子对象核对 enabled 状态**（get_scene summary 会打印每个对象的 visible，OFF/ON 一眼可见）。
- 排查口诀：性能检测反复不过时，先 `get_scene` 全树 grep "ON "，列出所有仍在运行的算法对象，通常能抓到 2-4 个漏网子级。
- 编辑器崩溃重建后，之前设置的 enabled=false 可能回退（分屏相机 s48 复活）——重建后必须重新核查全部禁用项。
- 模板自带"全屏前景贴纸"（retouch_* 系列 720x1307）会与自制装饰冲突，先核对再决定保留/禁用。
