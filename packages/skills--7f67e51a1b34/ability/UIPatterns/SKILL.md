---
name: UIPatterns
description: 游戏 UI 布局模式 - 搭建按钮、HUD、进度条、弹窗和网格等常见游戏 UI，统一处理节点层级、渲染顺序、尺寸和触控状态。
---

# 游戏 UI 布局模式

游戏开发中的高层 UI 组合模式。单个 Image/Text 的 API 细节见 `ScreenTransform/SKILL.md`。

## 按钮模式（Image + Text + Touch）

一个可点击的按钮是一个 Screen Image（背景）加上一个**子节点** 2D Text（标签），配合脚本中的触控命中检测。

### 场景结构（通过 MCP 搭建）

```
ButtonContainer（Screen Image — 背景，纯色）
  └── ButtonLabel（2D Text — "开始"，相对于父节点居中）
```

**为什么用子节点？** 当 2D Text 需要显示在 Screen Image 上方时——按钮、面板、卡片、对话框、HUD 元素、横幅——Text 必须是该 Image 的子节点。这确保：(1) 标签获得比背景更高的 `renderOrder`，(2) 标签随背景自动移动。**永远不要把文字和其背景 Image 作为兄弟节点放置**，除非你显式验证了 `renderOrder`；文字可能渲染在 Image 后面而不可见。

**按钮的祖先层级也很重要。** 当按钮属于面板、卡片、对话框或覆盖层内容区域时，按钮的 Screen Image 必须是该容器 UI 对象的子节点，标签必须是按钮 Image 的子节点：

```
PanelOrOverlayContent（Screen Image 或 Empty）
  └── ButtonContainer（Screen Image — 按钮背景）
      └── ButtonLabel（2D Text — 按钮标签）
```

预期的渲染顺序是 `PanelOrOverlayContent renderOrder < ButtonContainer renderOrder < ButtonLabel renderOrder`。创建为面板/覆盖层的兄弟节点的按钮可能渲染在面板后面，即使位置看起来正确。先用 `move_scene_object(parent=...)` 将按钮设为子节点；如果兄弟层叠不可避免，用 `move_scene_object(parent=..., above_scene_object=...)` 重排并验证最终的 `renderOrder`。

**标签适配是模式的一部分。** 标签的 `sizeDelta` 应小于按钮背景（四周留可见边距），渲染的文本不能溢出按钮边框或出现在背景 Image 之外。如果如"再来一次"这样的标签比按钮宽，请放大按钮、缩小字体或拆分标签；不要接受溢出作为视觉通过。

### MCP 搭建 — 创建按钮

```
commands = [
  // 1. 创建按钮背景（纯色）
  { command_type: "add_builtin_object", params: { object_type: "Screen Image" }, alias: "btn" },
  { command_type: "set_scene_object", params: { guid: { $ref: "btn" }, properties: { name: "开始按钮" } } },
  { command_type: "set_component", params: {
    guid: { $ref: "btn", component_type: "ScreenTransform" },
    properties: { anchoredPosition: { x: 0, y: -400 }, sizeDelta: { x: 280, y: 80 } }
  }},
  { command_type: "set_component", params: {
    guid: { $ref: "btn", component_type: "Image" },
    properties: { texture: { guid: "00000000-0000-0000-0000-000000001543" }, stretchMode: "Stretch", color: { r: 0.2, g: 0.5, b: 1, a: 1 } }
  }},
  // 2. 创建标签作为按钮的 CHILD — 更高的 renderOrder，随父节点移动
  { command_type: "add_builtin_object", params: { object_type: "2D Text", name: "按钮标签" }, alias: "btn_label" },
  { command_type: "move_scene_object", params: { guid: { $ref: "btn_label" }, parent: { $ref: "btn" } } },
  { command_type: "set_component", params: {
    guid: { $ref: "btn_label", component_type: "ScreenTransform" },
    properties: { anchoredPosition: { x: 0, y: 0 }, sizeDelta: { x: 240, y: 56 } }
  }}
]
```

### 圆角（2D Mask）

Image 在任何绘制模式下都没有圆角属性——`Ellipse` 产生的是完整椭圆，不是圆角矩形。要给按钮、面板、卡片或头像添加圆角，用 **2D Mask** 包裹它，Mask 会将子节点裁剪为圆角矩形。

```
开始按钮（2D Mask — 拥有按钮的外矩形 + 圆角半径）
  └── ButtonBg（Screen Image — 精确填充 Mask）
      └── ButtonLabel（2D Text — 背景的子节点，一如既往）
```

**Mask 必须是独立对象。** Mask 与 Image 和 Text 互斥——三者不能共享一个对象——所以它不能放在按钮的 Screen Image 上。用 `add_builtin_object(object_type: "2D Mask")` 创建，并将视觉元素作为子节点。Mask 也依赖 ScreenTransform，是它的 ScreenTransform——Mask 自身的 `anchoredPosition` 和 `sizeDelta`——定义了裁剪区域。Mask 对象成为你定位和调整大小的对象；子背景的 `sizeDelta` 应与其匹配，使彩色区域延伸到圆角边缘。

| 属性 | 类型 / 范围 | 作用 |
|---|---|---|
| `cornerRadius` | Number, 0–1（默认 0） | 圆角量。**归一化，非像素**——0 是直角，1 是最大圆角（正方形上为圆形，矩形上为胶囊形）。 |
| `maskedCorners` | `Array<Number>`，默认 `[1, 2, 4, 8]` | 哪些角圆角：`1` 左上，`2` 右上，`4` 左下，`8` 右下。传子集做单边圆角，如 `[1, 2]` 做标签页或面板头部。 |
| `maskFeather` | Vector2f，每轴 0–500（默认 `{x: 0, y: 0}`） | 柔化 Mask 边缘。按钮保持 0 做清晰边缘；提高做发光或渐晕衰减。 |
| `maskOpacity` | Number, 0–1（默认 1） | Mask 施加的整体透明度。实体按钮保持 1。 |

```
commands = [
  // 1. Mask 拥有外矩形和圆角
  { command_type: "add_builtin_object", params: { object_type: "2D Mask", name: "开始按钮" }, alias: "btn" },
  { command_type: "set_component", params: {
    guid: { $ref: "btn", component_type: "Mask" },
    properties: { cornerRadius: 0.4 }
  }},
  // 2. 背景填充 Mask — 圆角外的所有内容被裁剪
  { command_type: "add_builtin_object", params: { object_type: "Screen Image", name: "ButtonBg" }, alias: "btn_bg" },
  { command_type: "move_scene_object", params: { guid: { $ref: "btn_bg" }, parent: { $ref: "btn" } } },
  { command_type: "set_component", params: {
    guid: { $ref: "btn_bg", component_type: "Image" },
    properties: { texture: { guid: "00000000-0000-0000-0000-000000001543" }, stretchMode: "Stretch", color: { r: 0.2, g: 0.5, b: 1, a: 1 } }
  }},
  // 3. 标签在背景下，与普通按钮模式完全相同
  { command_type: "add_builtin_object", params: { object_type: "2D Text", name: "按钮标签" }, alias: "btn_label" },
  { command_type: "move_scene_object", params: { guid: { $ref: "btn_label" }, parent: { $ref: "btn_bg" } } },
]
```

**Mask 还需设置 ScreenTransform**：Mask 的 `anchoredPosition` 和 `sizeDelta` 决定了裁剪区域。别忘了在创建 Mask 后设置其 ScreenTransform。

**因为半径是归一化的，它会随 Mask 的尺寸缩放。** 两个不同尺寸的按钮用相同的 `cornerRadius` 不会共享像素半径——较小的按钮看起来更圆。要在一组按钮间保持一致的视觉效果，要么保持尺寸相等，要么对照预览截图逐个调整每个半径。

**Mask 改变的是绘制内容，不是命中区域。** `isScreenPointOnImage` 仍然检测背景 Image 的完整矩形，所以裁剪掉的角仍然可点击。对普通按钮无害；但当圆角按钮靠得足够近以至于矩形重叠时，一个按钮的角可能会吞掉相邻按钮的点击。

**同一模式的其他用途**：圆形头像或头像图（正方形 Mask，`cornerRadius: 1`），圆角卡片或对话框面板，仅顶部边缘圆角的面板（`maskedCorners: [1, 2]`），以及将大图裁剪为小窗口。

两项代价需要权衡：圆角按钮多一个对象，2D Mask 将特效的最低 SDK 提升到 18.0.0。对于从不在对比边缘上看到的背景，普通直角仍然可以。

### 触控命中检测

使用 `APJS.TouchUtils.isScreenPointOnImage()` 检测触摸是否在按钮的 Image 边界内。直接传入 `touchInfo.position`——无需坐标转换。

如果按钮包裹在 2D Mask 中，将 `@serializeProperty` 绑定到**子背景 Image**，而不是 Mask 对象——2D Mask 不能承载 Image，对它调用 `getComponent("Image")` 返回 null。

```typescript
@serializeProperty
private buttonObj: APJS.SceneObject;

private buttonImage!: APJS.Image;

private touchCallback = (event: APJS.IEvent) => {
  const touchInfo = event.args[0] as APJS.TouchData;
  if (touchInfo.phase !== APJS.TouchPhase.Began) return;

  if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.buttonImage)) {
    this.onButtonTap();
  }
};
```

### 按钮状态（按压 / 正常）

在按下/释放时改变按钮颜色以提供视觉反馈：

```typescript
private touchCallback = (event: APJS.IEvent) => {
  const touchInfo = event.args[0] as APJS.TouchData;
  const inside = APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.buttonImage);

  if (touchInfo.phase === APJS.TouchPhase.Began && inside) {
    // 按压状态
    this.buttonImage.color = new APJS.Color(0.7, 0.7, 0.7, 1);  // 变暗
  } else if (touchInfo.phase === APJS.TouchPhase.Ended) {
    // 释放 — 恢复正常状态
    this.buttonImage.color = new APJS.Color(1, 1, 1, 1);
    if (inside) {
      this.onButtonTap();
    }
  }
};
```

### 多个按钮

对多个按钮，用 `isScreenPointOnImage` 检测每个按钮的 Image：

```typescript
@serializeProperty
private btn1Obj: APJS.SceneObject;
@serializeProperty
private btn2Obj: APJS.SceneObject;

private btn1Image!: APJS.Image;
private btn2Image!: APJS.Image;

private handleTouch(touchInfo: APJS.TouchData): void {
  if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.btn1Image)) {
    this.onButton1Tap();
  } else if (APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, this.btn2Image)) {
    this.onButton2Tap();
  }
}
```

## HUD 布局（状态栏）

HUD（Heads-Up Display）在游戏区域上方叠加游戏信息——分数、计时器、生命。

### 场景结构

```
HUD（Empty — 应比游戏对象有更高的 renderOrder）
  ├── ScoreText（2D Text — "分数：0"，左上）
  ├── TimerText（2D Text — "60"，顶部居中）
  ├── LivesContainer（Empty — 右上）
  │   ├── Life1（Screen Image — 心形图标）
  │   ├── Life2（Screen Image — 心形图标）
  │   └── Life3（Screen Image — 心形图标）
  └── BottomBar（Empty — 底部区域）
      ├── ActionBtn1（Screen Image）
      │   └── Btn1Label（2D Text — 按钮的子节点）
      └── ActionBtn2（Screen Image）
          └── Btn2Label（2D Text — 按钮的子节点）
```

### MCP 搭建 — 定位 HUD 元素

使用 ScreenTransform 的 `anchoredPosition` 定位 HUD 元素（中心为 0,0，屏幕为 720x1280）。

**重要 — TikTok 安全区**：TikTok 的录制画面在顶部（Y > 500）、右侧（X > 260）和底部（Y < -400）有永久 UI 覆盖层。屏幕边缘的 HUD 会被遮挡。使用安全位置：

| 位置 | anchoredPosition (x, y) | 说明 |
|------|------------------------|------|
| HUD 左上 | (-240, 480) | 分数 — 顶部栏下方，侧边栏左侧 |
| HUD 顶部居中 | (0, 480) | 计时器 — 顶部栏下方 |
| HUD 右上 | (220, 480) | 生命 — 顶部栏下方，侧边栏左侧 |
| 中心 | (0, 0) | 游戏区域中心 |
| 底部操作 | (0, -320) | 开始/重新开始按钮 — 停止圈上方（顶部 ≈ Y=-400） |

**避免**：Y > 500（顶部栏），Y < -400（停止圈），X > 260（右侧栏）。

**游戏背景上的可读性**：分数、计时器、生命和结果文字必须在实际截图中显而易见，而不仅仅是存在于场景树中。在明亮或杂乱的背景上（草地、天空、粒子、相机画面），将 HUD 文字放在高对比度的背景 Image 上，或选择强烈对比的文字颜色/粗细。不要在明亮草地或天空上直接放置黄色/白色文字，除非截图证明它立即可读。

### 生命图标（显示/隐藏模式）

```typescript
@serializeProperty
private lifeIcons: APJS.SceneObject[] = [];

private currentLives: number = 3;

private updateLives(): void {
  for (let i = 0; i < this.lifeIcons.length; i++) {
    this.lifeIcons[i].setEnabledInHierarchy(i < this.currentLives);
  }
}

private loseLife(): void {
  this.currentLives--;
  this.updateLives();
  if (this.currentLives <= 0) {
    this.onGameOver();
  }
}
```

### 分数 + 计时器 HUD 脚本

```typescript
@serializeProperty
private scoreTextObj: APJS.SceneObject;
@serializeProperty
private timerTextObj: APJS.SceneObject;

private scoreText!: APJS.Text;
private timerText!: APJS.Text;
private score: number = 0;
private remainingTime: number = 60;
private isPlaying: boolean = false;

private updateScore(points: number): void {
  this.score += points;
  if (this.scoreText) {
    this.scoreText.text = "分数：" + this.score;
  }
}

private updateTimer(dt: number): void {
  if (!this.isPlaying) return;
  this.remainingTime -= dt;
  if (this.remainingTime <= 0) {
    this.remainingTime = 0;
    this.onTimeUp();
  }
  if (this.timerText) {
    this.timerText.text = Math.ceil(this.remainingTime).toString();
  }
}
```

## 进度条（Image Filled 模式）

进度条使用 DrawMode 设置为 "Filled" 的 Image。

### MCP 搭建

1. 创建一个 Screen Image 作为进度条背景（全宽，深色）
2. 创建一个 Screen Image 作为进度条填充（相同位置，强调色）
3. 通过 `set_component` 将填充 Image 的 DrawMode 设为 "Filled"：

```
set_component(guid=fillImageComponent, properties={ "drawMode": "Filled" })
```

### 场景结构

```
ProgressBarContainer（Empty）
  ├── BarBackground（Screen Image — 深灰色，全宽）
  └── BarFill（Screen Image — 绿色/蓝色，DrawMode=Filled）
```

### 填充方向参考

`_filledType` 设置轴向，`_startPoint` 设置填充区域起始位置（沿该轴 0–1）。填充区域从 `_startPoint` 到 `_startPoint + _filledRange`，钳制到 [0, 1]。

| `_filledType` | 方向 | `_startPoint` 含义 |
|---------------|------|-------------------|
| `0`（水平） | 从左到右填充 | 0.0 = 左边缘，1.0 = 右边缘 |
| `1`（垂直） | 从上到下填充 | 0.0 = 上边缘，1.0 = 下边缘 |

**关键洞察**：`_startPoint` 是位置偏移，不是方向反转。设置 `_startPoint:1.0` 配合 `_filledRange:0.5` 会填充 [1.0, 1.5]，被裁剪为空。要反向填充，必须**动态同时调整** `_startPoint` 和 `_filledRange`。

### 脚本控制 — 水平进度条（计时器、血量）

```typescript
@serializeProperty
private barFillObj: APJS.SceneObject;

private barImage!: APJS.Image;

onStart(): void {
  this.barImage = this.barFillObj.getComponent("Image") as APJS.Image;
  // 从左开始水平填充
  this.barImage.setMaterialProperty("_filledType", 0);     // 0=水平
  this.barImage.setMaterialProperty("_startPoint", 0.0);   // 从左开始
  this.barImage.setMaterialProperty("_filledRange", 1.0);  // 初始满
}

// 更新进度（0.0 到 1.0）— 从左到右填充
private setProgress(value: number): void {
  if (this.barImage) {
    this.barImage.setMaterialProperty("_filledRange", Math.max(0, Math.min(1, value)));
  }
}
```

### 脚本控制 — 垂直充能条（能量、充能）

对于从底部到顶部填充的充能/能量条，每帧动态设置 `_startPoint` 和 `_filledRange`：

```typescript
@serializeProperty
private chargeFillObj: APJS.SceneObject;

private chargeImage!: APJS.Image;

onStart(): void {
  this.chargeImage = this.chargeFillObj.getComponent("Image") as APJS.Image;
  this.chargeImage.setMaterialProperty("_filledType", 1);     // 1=垂直
  this.setCharge(0);  // 初始空
}

// 更新充能（0.0 = 空，1.0 = 满）— 从底部向上填充
private setCharge(value: number): void {
  if (this.chargeImage) {
    const v = Math.max(0, Math.min(1, value));
    // 填充区域 = [startPoint, startPoint + range] 钳制到 [0,1]
    // 底部到顶部：startPoint = 1-v, range = v → 填充 [1-v, 1] = 底部区域
    this.chargeImage.setMaterialProperty("_startPoint", 1.0 - v);
    this.chargeImage.setMaterialProperty("_filledRange", v);
  }
}
```

### 示例：倒计时条（水平）

```typescript
private updateTimerBar(dt: number): void {
  this.remainingTime -= dt;
  const ratio = this.remainingTime / this.maxTime;
  this.setProgress(ratio);

  // 时间不足时变红
  if (ratio < 0.25 && this.barImage) {
    this.barImage.color = new APJS.Color(1, 0.2, 0.2, 1);  // 红色警告
  }
}
```

## 弹窗 / 对话框

模态弹窗是一个半透明全屏覆盖层，上面有一个居中面板，包含按钮。

### 场景结构

```
PopupContainer（Empty — 初始隐藏）
  ├── Overlay（Screen Image — 黑色，不透明度 0.5，全屏）
  ├── DialogPanel（Screen Image — 白色/浅色，居中，较小）  ← 比 Overlay 更高的 renderOrder
  │   ├── DialogTitle（2D Text — "游戏结束！"）
  │   ├── DialogMessage（2D Text — "你的分数：42"）
  │   ├── ConfirmBtn（Screen Image — 绿色，DialogPanel 的子节点）
  │   │   └── ConfirmLabel（2D Text — "确定"）       ← 按钮的子节点 → 更高的 renderOrder
  │   └── CancelBtn（Screen Image — 灰色，DialogPanel 的子节点）
  │       └── CancelLabel（2D Text — "取消"）    ← 按钮的子节点 → 更高的 renderOrder
```

对话框中的按钮是面板的后代节点，而不是 PopupContainer 下未验证的顶层兄弟节点。验证弹窗栈为 `Overlay < DialogPanel < ConfirmBtn/CancelBtn < ConfirmLabel/CancelLabel`。

### MCP 搭建 — 全屏覆盖层

覆盖层 Image 应覆盖整个屏幕。使用默认 FIXED 约束配合全屏 sizeDelta：

```
set_component(guid=overlayScreenTransform, properties={ "anchoredPosition": { x: 0, y: 0 }, "sizeDelta": { x: 720, y: 1280 } })
```

设置覆盖层为纯色半透明黑色（White Texture + Stretch + color）：
```
set_component(guid=overlayImageComponent, properties={ "texture": { guid: "00000000-0000-0000-0000-000000001543" }, "stretchMode": "Stretch", "color": { r: 0, g: 0, b: 0, a: 1 }, "opacity": 0.5 })
```

### 显示/隐藏弹窗

```typescript
@serializeProperty
private popupContainer: APJS.SceneObject;
@serializeProperty
private messageTextObj: APJS.SceneObject;

private messageText!: APJS.Text;

private showPopup(title: string, message: string): void {
  if (this.messageText) {
    this.messageText.text = message;
  }
  this.popupContainer.setEnabledInHierarchy(true);
}

private hidePopup(): void {
  this.popupContainer.setEnabledInHierarchy(false);
}
```

## 网格布局（N × M）

对于卡片游戏、拼图和棋盘类游戏，通过从行列索引计算位置来创建网格。

### MCP 搭建 — 计算网格位置

给定 N 列 × M 行的网格，计算每个格子的 `anchoredPosition`：

```
屏幕中心 = anchoredPosition (0, 0)
格子间距 = cellWidth + gap

对于 4×3 网格（4 列，3 行），120×160 格子，10px 间距：
  totalWidth = 4 * 120 + 3 * 10 = 510
  totalHeight = 3 * 160 + 2 * 10 = 500

  startX = -totalWidth/2 + cellWidth/2 = -195
  startY = totalHeight/2 - cellHeight/2 = 170

  cell[col][row].anchoredPosition = (
    startX + col * (cellWidth + gap),   // -195, -65, 65, 195
    startY - row * (cellHeight + gap)   //  170, 0, -170
  )
```

### 场景结构

```
Grid（Empty — 容器）
  ├── Cell_0_0（Screen Image — 卡片正面/背面）
  ├── Cell_1_0（Screen Image）
  ├── Cell_2_0（Screen Image）
  ├── Cell_3_0（Screen Image）
  ├── Cell_0_1（Screen Image）
  ├── ...（总共 N * M 个格子）
```

### 网格格子脚本模式

对于记忆匹配等游戏，每个格子需要状态（正面/背面）：

```typescript
@serializeProperty
private gridCells: APJS.SceneObject[] = [];

private readonly COLS: number = 4;
private readonly ROWS: number = 3;
private cellImages: APJS.Image[] = [];
private cellStates: boolean[] = [];  // true = 正面朝上

private initGrid(): void {
  for (let i = 0; i < this.gridCells.length; i++) {
    this.cellImages.push(this.gridCells[i].getComponent("Image") as APJS.Image);
    this.cellStates.push(false);
  }
}

// 将网格索引转换为 col/row
private indexToCol(i: number): number { return i % this.COLS; }
private indexToRow(i: number): number { return Math.floor(i / this.COLS); }

// 查找被点击的格子
private findTappedCell(nx: number, ny: number): number {
  const screenX = nx * 720;
  const screenY = (1.0 - ny) * 1280;

  const cellW = 120;
  const cellH = 160;
  const gap = 10;
  const totalW = this.COLS * cellW + (this.COLS - 1) * gap;
  const totalH = this.ROWS * cellH + (this.ROWS - 1) * gap;

  const gridLeft = (720 - totalW) / 2;
  const gridTop = (1280 - totalH) / 2;

  const col = Math.floor((screenX - gridLeft) / (cellW + gap));
  const row = Math.floor((screenY - gridTop) / (cellH + gap));

  if (col < 0 || col >= this.COLS || row < 0 || row >= this.ROWS) return -1;

  const cellStartX = gridLeft + col * (cellW + gap);
  const cellStartY = gridTop + row * (cellH + gap);
  if (screenX > cellStartX + cellW || screenY > cellStartY + cellH) return -1;

  return row * this.COLS + col;
}

// 切换格子状态（如翻牌）
private flipCell(index: number): void {
  this.cellStates[index] = !this.cellStates[index];
  if (this.cellImages[index]) {
    this.cellImages[index].color = this.cellStates[index]
      ? new APJS.Color(1, 1, 1, 1)   // 卡片正面
      : new APJS.Color(0.3, 0.3, 0.5, 1);  // 卡片背面
  }
}
```

### edit_by_dsl 网格创建（MCP）

用一次批量调用 `edit_by_dsl` 创建所有网格格子：

```
commands = [
  // 对每个格子（i = 0 到 N*M-1）：
  { command_type: "add_builtin_object", params: { object_type: "Screen Image", name: "Cell_0_0" }, alias: "cell_0" },
  { command_type: "move_scene_object", params: { guid: { $ref: "cell_0" }, parent: { $ref: "grid" } } },
  { command_type: "set_component", params: {
    guid: { $ref: "cell_0", component_type: "ScreenTransform" },
    properties: { anchoredPosition: { x: -195, y: 170 }, sizeDelta: { x: 120, y: 160 } }
  }},
  // ... 对每个格子重复，使用计算出的位置
]
```

## 纯色背景（Screen Image）

Screen Image 有一个默认占位纹理（山脉图标）。要将其用作**纯色背景**（按钮、面板、行、覆盖层等），必须：

1. 将 `texture` 设为内置 **White Texture**（`00000000-0000-0000-0000-000000001543`）
2. 将 `stretchMode` 设为 `"Stretch"`（默认 `"Fit"` 保持宽高比，不会填充区域）
3. 将 `color` 设为所需颜色——它会染色白色纹理

```
set_component(guid=imageComponent, properties={
  "texture": { guid: "00000000-0000-0000-0000-000000001543" },
  "stretchMode": "Stretch",
  "color": { r: 0.2, g: 0.4, b: 0.8, a: 1 }
})
```

**永远不要把 texture 设为空 GUID**（`{guid: ""}`）——这会导致品红色"缺失纹理"瑕疵。

### Image stretchMode 选项

| 值 | 行为 | 何时使用 |
|---|------|---------|
| `Fit`（默认） | 缩放到适配 sizeDelta，保持宽高比。可能留空。 | 显示不能变形的图标或 Logo |
| `FitWidth` | 缩放到匹配宽度，保持宽高比。可能垂直溢出。 | 水平横幅，宽图 |
| `FitHeight` | 缩放到匹配高度，保持宽高比。可能水平溢出。 | 垂直横幅，高图 |
| `Stretch` | 拉伸填充整个 sizeDelta，忽略宽高比。 | **纯色背景**（按钮、面板、列表行、覆盖层、对话框、HUD 条）— 任何应作为纯色矩形的元素 |
| `Fill` | 缩放到覆盖整个 sizeDelta，保持宽高比。可能裁剪。 | 全屏背景图，卡片美术 |
| `FillAndCut` | 与 Fill 相同但裁剪溢出。 | 与 Fill 相同，当溢出必须不可见时 |

> **最常见陷阱**：将 Screen Image 用作 UI 背景时忘记设置 `stretchMode: "Stretch"`。默认 `"Fit"` 保持纹理宽高比，所以 1:1 的白色纹理在 600×70 的行上只会显示中心一个小方块，而不是填充整行。

## 编辑器 vs 脚本 — 谁拥有布局

**原则：布局属于场景，不属于脚本。** 在编辑器中编写静态位置、尺寸、锚点和轴心（通过场景编辑），以便可以调整。脚本拥有*数据*、*可见性*、*状态转换*和*真正由数据驱动的*布局（例如根据长短内容调整大小的卡片）。

**陷阱**：在 `onStart`/`onUpdate` 中设置 `ScreenTransform.anchoredPosition` 或 `sizeDelta` 的脚本会在运行时**覆盖编辑器值**。对象在编辑器中看起来正确，但脚本运行时却移动了——用户看不到为什么他们的手动调整"不起作用"。这是 UI 摩擦的最常见来源。

| 场景 | 在哪里设置 |
|------|-----------|
| 按钮、面板、HUD 元素的固定位置/尺寸 | **场景**（编辑器） |
| 固定颜色、字体或文字对齐 | **场景**（编辑器）— 不在脚本中硬编码 `Text.color = new APJS.Color(...)` |
| 状态变化时显示/隐藏或启用/禁用 | 脚本（`setEnabledInHierarchy`） |
| 文字内容，或由数据驱动的颜色/纹理切换 | 脚本 |
| 依赖数据的位置/尺寸（长短卡片） | 脚本 |
| 对另一个对象的引用（卡片、心形、目标） | `@serializeProperty` — 永远不用 `getChild("名称")` |

✅ 在场景中编写开始屏幕的按钮位置；在脚本中仅用 `setEnabledInHierarchy(false)` 隐藏它。
❌ 不要在 `onUpdate` 中每帧设置 `anchoredPosition` 来"居中"静态元素——在场景中一次居中。
❌ 不要在脚本中硬编码基础样式或引用——`this.label.color = new APJS.Color(1,0,0,1)` 属于编辑器中的 Text 组件，`getChild("重试按钮")` 应为绑定的 `@serializeProperty`。

## 规则

1. **触控命中检测**：使用 `APJS.TouchUtils.isScreenPointOnImage(touchInfo.position, imageComponent)` 进行按钮点击检测——直接传入按钮的 Image 组件，无需坐标转换。
2. **按钮状态**：改变 `Image.color` 提供按压/正常的视觉反馈。在 `TouchPhase.Ended` 时恢复。
3. **进度条**：Image DrawMode 必须为 "Filled"（通过 MCP `set_component` 设置）。在脚本中使用 `setMaterialProperty("_filledRange", value)`。
4. **弹窗**：使用 `setEnabledInHierarchy(true/false)` 显示/隐藏整个弹窗容器。
5. **网格定位**：从行列索引和格子尺寸计算 `anchoredPosition`。通过从屏幕中心偏移来居中网格。
6. **屏幕坐标**：ScreenTransform `anchoredPosition` 中心为 (0,0)。屏幕空间为 720x1280，(0,0) 在左下角。触摸归一化位置 (0,0) 在左上角。
7. **确保不同屏幕间的触控区域不重叠**——不同屏幕的按钮可能在归一化触摸空间中重叠。为每个屏幕的按钮分配不同的屏幕区域。
8. **渲染顺序（关键）**：使用 `get_scene()`、场景编辑响应或 `inspect(guid)` 返回的 `renderOrder` 作为唯一真值。更大的 `renderOrder` 渲染更晚/更上层。没有 z-index。常见模式：
   - **文字在 Image 上（按钮、面板、卡片、HUD、对话框、横幅）**：2D Text 必须是其背景 Screen Image 的**子节点**。子节点获得更高的 `renderOrder` 并随父节点移动。永远不要把文字和其背景 Image 作为兄弟节点放置，除非 `renderOrder` 证明标签在上方。
   - **面板/按钮/文字链**：对于面板、卡片、对话框或覆盖层内容区域内的按钮，将整个按钮 Screen Image 设为该容器的子节点，然后将标签设为按钮的子节点。预期顺序：`container < button Image < button Text`。
   - **覆盖层/弹窗**：模态栈应为 `game/background < Overlay < DialogPanel < Button Image < Button Text`。覆盖层在游戏之上，面板内容和按钮在覆盖层之上。如需重排，用 `move_scene_object(parent=..., above_scene_object=...)` 然后重新检查 `renderOrder`。
   - **兄弟节点重排**：使用 `move_scene_object(guid=A, parent=P, above_scene_object=B)` 使 A 移到父节点 P 下、排在 B 的**前面**；A 应报告比 B 更大的 `renderOrder`。
9. **标签容纳**：按钮/卡片/面板标签必须适配其背景 Image，留有边距。如果截图显示文字跨过边界、被裁剪或标签浮动在背景外，在审查前调整 Image 大小、缩小文字或拆分文字。
10. **sizeDelta 默认是全屏（720×1280）**：创建新的 Screen Image 或 2D Text 时，始终将 `sizeDelta` 设为所需像素尺寸。如果忘记，元素会填充整个屏幕。
11. **圆角来自 2D Mask，不是 Image**：没有任何 Image 绘制模式有圆角半径。将元素包裹在 `2D Mask` 对象中（`cornerRadius` 0–1，归一化），并将背景 Image 作为其子节点——Mask 不能与 Image 或 Text 共享对象。
