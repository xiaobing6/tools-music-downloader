# GUI 焦点状态与设置层级优化设计

**日期：** 2026-07-12  
**状态：** 已确认，待实施

## 背景

当前 GUI 对按钮、输入框、下拉框、文本域和折叠项统一使用 `3px` 外轮廓和 `2px` 间距。该样式满足键盘可访问性，但输入框和下拉框在鼠标点击后也会出现较硬的外圈，与音乐工作台其余柔和边框和阴影语言不一致。

## 目标

- 输入框、下拉框和文本域聚焦时使用柔和的蓝色边框与低透明度光晕。
- 按钮、复选框、单选框和折叠项继续保留清晰的键盘焦点环。
- 常用设置顺序改为“音源 / 类型 / 结果数量”，音质移到“更多设置”中原结果数量的位置。
- 音源、类型、结果数量、音质和下载目录的标签与控件之间保留 `10px` 净空，避免聚焦光晕遮挡文字。
- 不删除焦点反馈，不引入 JavaScript 输入设备判断。
- 除数量与音质换位外，不改变网格列数、控件尺寸、交互、表单语义或业务逻辑。
- 同步测试、前端静态构建产物和相关设计文档。

## 方案比较

### 方案 A：删除全局焦点环

视觉最安静，但键盘用户无法可靠判断当前位置，不符合现有可访问性基线，不采用。

### 方案 B：JavaScript 输入模式跟踪

监听 `pointerdown` 和键盘事件，可以精确区分鼠标与键盘焦点，但会为一次样式优化引入全局状态和事件生命周期，不采用。

### 方案 C：CSS 分层焦点（采用）

文本字段统一使用 `:focus`：移除默认 outline，把边框改为品牌蓝，并添加 `3px`、约 10% 透明度的蓝色光晕。按钮、summary、checkbox 和 radio 使用 `:focus-visible` 的 `2px` 品牌蓝外轮廓和 `2px` 间距。

该方案不依赖浏览器对文本输入 `:focus-visible` 的设备启发式差异；鼠标和键盘聚焦文本字段时都保持柔和但清晰的字段状态，离散操作控件则继续提供醒目的键盘定位提示。

## 选择器边界

文本字段选择器只覆盖：

```css
:where(input:not([type="checkbox"]):not([type="radio"]), select, textarea)
```

离散操作控件选择器覆盖：

```css
:where(button, summary, input[type="checkbox"], input[type="radio"]):focus-visible
```

这样不会把文本字段的边框和阴影规则错误应用到复选框和单选框。

## 设置层级与间距

当前第三个常用设置由“音质”改为“结果数量”。`numberInput` 连同现有数值归一化逻辑移到 quick settings 第三列；`bitrateSelect` 连同音质选项移到 advanced settings 第一列。两者只交换视觉位置，不改变 `GuiConfig` 字段、事件处理或默认值。

为字段标签与聚焦光晕提供稳定净空，在 `app.css` 新增：

```css
.field-stack {
  display: grid;
  gap: 10px;
}
```

`field-stack` 应用于音源、类型、结果数量、音质和下载目录的外层容器，替换这些位置的 `space-y-1.5`。下载封面、下载歌词等横向复选框继续使用现有 `inline-flex` 与 `gap-2`，不受影响。

## 视觉参数

- 聚焦边框：`var(--color-track)`，当前为 `#2563eb`。
- 字段光晕：`0 0 0 3px color-mix(in srgb, var(--color-track) 10%, transparent)`。
- 离散控件焦点环：`2px solid var(--color-track)`。
- 焦点环间距：`2px`。
- 继续遵守现有 reduced-motion 约定；本次不新增动画。

## 测试与文档

- 先修改 `music_downloader/gui/frontend/tests/workbench.test.mjs`，要求字段焦点包含品牌边框、柔和 box-shadow，并排除旧的统一 `3px` outline。
- 同一测试要求按钮、summary、checkbox 和 radio 仍有 `:focus-visible` 外轮廓。
- 更新设置层级测试，要求 `numberInput` 位于 `<details>` 之前、`bitrateSelect` 位于 `<details>` 之后，并保持音源、类型、数量的顺序。
- 增加字段间距测试，要求 `.field-stack` 使用 `10px` gap，且五个指定字段容器均使用该语义类。
- 观察测试失败后，再修改 `music_downloader/gui/frontend/src/app.css` 使其通过。
- 修改 `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte` 完成数量/音质换位和 field-stack 应用。
- 更新 `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md` 和 `AGENTS.md` 的焦点视觉约定。
- 运行 Node 测试、Svelte check、Vite build、GUI 静态产物测试和全量 Python 验证。

## 验收标准

- 点击输入框或下拉框时，不再出现原来的硬质 `3px` 外轮廓。
- 字段通过蓝色边框和低透明度光晕清晰表达聚焦状态。
- 使用 Tab 聚焦按钮、折叠项、复选框或单选框时仍有清晰外圈。
- 常用设置依次为音源、类型、结果数量；音质位于更多设置第一列。
- 五个指定字段的标签与控件间距均为 `10px`，聚焦光晕不遮挡标签。
- 前端构建和全部自动测试通过，静态产物已刷新。
