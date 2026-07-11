# GUI 焦点状态与设置层级优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用柔和字段光晕替代输入框和下拉框的硬质统一外圈，交换结果数量与音质的位置，并为五个指定字段提供 10px 标签净空。

**Architecture:** 只修改现有 `SettingsPanel.svelte` 的视觉顺序和语义类，并在全局 `app.css` 用两组选择器区分文本字段与离散控件。业务配置键、事件处理、默认值和 pywebview API 保持不变；静态资源仍由 Vite 生成到 `music_downloader/gui/static/`。

**Tech Stack:** Svelte 5、TypeScript、Tailwind CSS、Node test runner、svelte-check、Vite、pytest。

## Global Constraints

- 常用设置必须依次为“音源 / 类型 / 结果数量”，音质位于“更多设置”第一列。
- 音源、类型、结果数量、音质和下载目录必须使用 `.field-stack { display: grid; gap: 10px; }`。
- 文本字段聚焦必须使用品牌蓝边框和 `3px`、10% 透明度光晕，不再使用旧的统一 `3px` outline。
- 按钮、summary、checkbox 和 radio 必须保留 `2px` 的 `:focus-visible` 品牌蓝外轮廓及 `2px` 间距。
- 不引入 JavaScript 输入设备判断，不改变 `GuiConfig` 字段、默认值、事件处理或业务逻辑。
- 更新 README、AGENTS、当前音乐工作台设计、新焦点设计和相关测试，不能只修改前端源码。
- 修改前端后必须运行 Node 测试、svelte-check、Vite build 和全量 Python 验证。

## File Map

- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs` — 锁定焦点选择器、字段顺序和 10px 间距。
- Modify: `music_downloader/gui/frontend/src/app.css` — 实现字段光晕、离散控件键盘外圈和 `.field-stack`。
- Modify: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte` — 交换数量/音质并应用字段语义类。
- Modify: `tests/test_gui_documentation.py` — 锁定 README 与 AGENTS 的新设置层级描述。
- Modify: `README.md` — 更新用户可见的常用/更多设置说明和字段焦点表现。
- Modify: `AGENTS.md` — 更新 GUI 设置层级和焦点视觉约定。
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md` — 更新工作台设置层级与焦点基线。
- Modify: `docs/superpowers/specs/2026-07-12-focus-state-refinement-design.md` — 记录实施状态与验证结果。
- Generate: `music_downloader/gui/static/index.html` 与 `music_downloader/gui/static/assets/*` — Vite 构建产物。

---

### Task 1: 用 TDD 实现字段顺序、净空和分层焦点

**Files:**
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte`

**Interfaces:**
- Consumes: `GuiConfig.number`、`GuiConfig.bitrate`、`normalizeNumber()`、`bitrateItems` 和现有 `update()`。
- Produces: `.field-stack`、文本字段 `:focus` 光晕、离散控件 `:focus-visible` 外圈，以及新的设置视觉顺序。

- [ ] **Step 1: 先修改前端测试以表达新行为**

把 `interactive controls have a focus-visible baseline and body text stays selectable` 测试替换为：

```js
test("form fields use a soft halo while discrete controls retain keyboard focus", async () => {
  const css = await source("app.css");
  assert.match(
    css,
    /:where\(\s*input:not\(\[type="checkbox"\]\):not\(\[type="radio"\]\),\s*select,\s*textarea\s*\):focus\s*\{[^}]*outline:\s*none[^}]*border-color:\s*var\(--color-track\)[^}]*box-shadow:\s*0 0 0 3px color-mix\(in srgb, var\(--color-track\) 10%, transparent\)/s
  );
  assert.match(
    css,
    /:where\(button, summary, input\[type="checkbox"\], input\[type="radio"\]\):focus-visible\s*\{[^}]*outline:\s*2px solid var\(--color-track\)[^}]*outline-offset:\s*2px/s
  );
  assert.doesNotMatch(css, /:where\(button, input, select, textarea, summary\):focus-visible/);
  assert.doesNotMatch(css, /body\s*\{[^}]*user-select:\s*none/s);
  assert.match(css, /\.no-select[^}]*user-select:\s*none/s);
});
```

把设置层级测试改为：

```js
test("settings place result count in quick controls and bitrate in advanced controls", async () => {
  const settings = await source("lib/components/SettingsPanel.svelte");
  const detailsIndex = settings.indexOf("<details");
  assert.match(settings, /<summary[^>]*>\s*更多设置/);
  assert.ok(settings.indexOf("sourceSelect") < settings.indexOf("typeSelect"));
  assert.ok(settings.indexOf("typeSelect") < settings.indexOf("numberInput"));
  assert.ok(settings.indexOf("numberInput") < detailsIndex);
  assert.ok(settings.indexOf("bitrateSelect") > detailsIndex);
});
```

追加字段净空测试：

```js
test("field stacks reserve ten pixels between labels and controls", async () => {
  const css = await source("app.css");
  const settings = await source("lib/components/SettingsPanel.svelte");
  assert.match(css, /\.field-stack\s*\{[^}]*display:\s*grid[^}]*gap:\s*10px/s);
  assert.equal((settings.match(/class="field-stack/g) ?? []).length, 5);
});
```

- [ ] **Step 2: 运行测试并确认旧实现失败**

Run from `music_downloader/gui/frontend`:

```powershell
node --test tests/workbench.test.mjs
```

Expected: FAIL，缺少新的字段选择器和 `.field-stack`，且 `numberInput` 仍位于 `<details>` 后。

- [ ] **Step 3: 实现分层焦点和字段净空**

在 `src/app.css` 中用以下规则替换旧统一 `:focus-visible`：

```css
:where(
  input:not([type="checkbox"]):not([type="radio"]),
  select,
  textarea
):focus {
  outline: none;
  border-color: var(--color-track);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-track) 10%, transparent);
}

:where(button, summary, input[type="checkbox"], input[type="radio"]):focus-visible {
  outline: 2px solid var(--color-track);
  outline-offset: 2px;
}

.field-stack {
  display: grid;
  gap: 10px;
}
```

- [ ] **Step 4: 交换数量与音质并应用 field-stack**

在 `SettingsPanel.svelte` 中：

- quick settings 保留 `sourceSelect`、`typeSelect`，第三项改为现有 `numberInput` 及其完整 `normalizeNumber()` onchange。
- advanced settings 第一项改为现有 `bitrateSelect` 及其完整 `bitrateItems` 循环。
- 音源、类型、结果数量、音质四个 `<label>` 和下载目录外层 `<div>` 的 class 以 `field-stack` 开头，移除这些位置的 `space-y-1.5`。
- 从文本输入和 select 的 class 中移除 `focus-visible:border-blue-500`，避免覆盖全局品牌蓝边框。
- 复选框 class 和横向 `gap-2` 保持不变。

- [ ] **Step 5: 运行前端测试并确认转绿**

Run:

```powershell
node --test tests/startup.test.mjs tests/workbench.test.mjs
```

Expected: 现有 15 项加新增字段净空测试，共 16 项全部 PASS。

- [ ] **Step 6: 提交前端源码和测试**

```powershell
git add music_downloader/gui/frontend/src/app.css music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte music_downloader/gui/frontend/tests/workbench.test.mjs
git commit -m "feat: refine GUI field focus states"
```

---

### Task 2: 同步设置层级和焦点文档

**Files:**
- Modify: `tests/test_gui_documentation.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `docs/superpowers/specs/2026-07-12-focus-state-refinement-design.md`

**Interfaces:**
- Consumes: Task 1 的最终字段顺序、10px 净空和焦点选择器。
- Produces: 与当前 GUI 一致的用户说明、协作者约定和设计状态。

- [ ] **Step 1: 先更新文档测试期望**

在 `test_current_gui_docs_match_workbench_contract` 中追加：

```python
    assert "音源、搜索类型和结果数量是常用设置" in readme
    assert "音质" in readme and "更多设置" in readme
    assert "音源、类型、结果数量为常用设置" in agents
    assert "10px" in agents
```

- [ ] **Step 2: 运行文档测试并确认旧文案失败**

Run:

```powershell
pytest tests/test_gui_documentation.py::test_current_gui_docs_match_workbench_contract -v
```

Expected: FAIL，README 和 AGENTS 仍把音质描述为常用设置，也没有 10px 字段净空约定。

- [ ] **Step 3: 更新 README、AGENTS 和相关设计**

- `README.md`：把 GUI 使用说明改为“音源、搜索类型和结果数量是常用设置，音质、歌词、封面、下载目录和环境检查位于更多设置”；追加字段聚焦使用蓝色边框与柔和光晕、键盘操作控件保留清晰外圈。
- `AGENTS.md`：把主界面约定更新为“音源、类型、结果数量为常用设置”，并记录五个 `.field-stack` 使用 10px、文本字段与离散控件分别使用 `:focus`/`:focus-visible`。
- 音乐工作台设计：同步设置层级、10px 净空和分层焦点基线。
- 焦点优化设计：状态更新为“实施中”，写入实际 CSS/Svelte 实现位置；最终验证结果留到 Task 3。

- [ ] **Step 4: 运行文档测试和旧文案扫描**

Run:

```powershell
pytest tests/test_gui_documentation.py -v
rg -n "音源、搜索类型和音质是常用设置|音源、类型、音质为常用设置|space-y-1\.5" README.md AGENTS.md docs/superpowers music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte
```

Expected: 文档测试全部 PASS；旧设置层级文案和五个目标字段的旧间距均不存在。

- [ ] **Step 5: 提交文档同步**

```powershell
git add README.md AGENTS.md tests/test_gui_documentation.py docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md docs/superpowers/specs/2026-07-12-focus-state-refinement-design.md
git commit -m "docs: align GUI settings and focus guidance"
```

---

### Task 3: 构建、视觉检查与完整验证

**Files:**
- Generate: `music_downloader/gui/static/index.html`
- Generate: `music_downloader/gui/static/assets/*`
- Modify: `docs/superpowers/specs/2026-07-12-focus-state-refinement-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-focus-state-refinement.md`

**Interfaces:**
- Consumes: Tasks 1–2 的前端源码、测试和文档。
- Produces: 最新静态产物、真实 GUI 验收和可复查验证记录。

- [ ] **Step 1: 串行运行前端检查和构建**

Run from `music_downloader/gui/frontend`，不要并行争用 `.vite-temp`：

```powershell
node --test tests/startup.test.mjs tests/workbench.test.mjs
npm.cmd run check
npm.cmd run build
```

Expected: Node 16 项全部 PASS；svelte-check 0 errors/0 warnings；Vite build 成功并刷新 static。

- [ ] **Step 2: 运行 Python 和静态产物验证**

Run from repository root:

```powershell
pytest
ruff check .
ruff format --check .
mypy music_downloader
python -m py_compile music_download.py
git diff --check
```

Expected: pytest 全部 PASS；ruff、mypy、py_compile 和 diff check 退出码均为 0。

- [ ] **Step 3: 启动真实 GUI 做视觉验收**

Run:

```powershell
python .\music_download.py
```

检查：

- 常用设置顺序为音源、类型、结果数量。
- 音质位于更多设置第一列。
- 点击五个字段时，标签不被光晕遮挡。
- 输入框和下拉框只有蓝色边框与柔和光晕，不再出现硬质 3px 外圈。
- Tab 聚焦按钮、复选框和“更多设置”时仍有清晰 2px 外圈。

- [ ] **Step 4: 更新状态和验证记录**

把焦点设计状态改为“已实施”，记录 Node、Svelte、Vite、pytest、ruff、mypy、编译和真实 GUI 结果；在本计划勾选完成项并追加 Execution Record。

- [ ] **Step 5: 提交静态产物和验证记录**

```powershell
git add music_downloader/gui/static docs/superpowers/specs/2026-07-12-focus-state-refinement-design.md docs/superpowers/plans/2026-07-12-focus-state-refinement.md
git commit -m "feat: deliver refined GUI focus states"
```

- [ ] **Step 6: 确认工作区干净**

Run:

```powershell
git status --short
git log -6 --oneline
```

Expected: 工作区干净，最近提交包含前端实现、文档同步和最终验证记录。
