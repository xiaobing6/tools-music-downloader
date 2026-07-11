# 音乐工作台前端改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GUI 重构为搜索优先、可响应到 `1024x720`、具有统一音乐品牌语言且满足既定可访问性基线的桌面工作台。

**Architecture:** 保持 `App.svelte` 中现有 pywebview 数据流和任务状态机不变，只重组展示层。`SearchBar` 负责首要搜索动作，`SettingsPanel` 负责常用与展开设置，`ResultList` 负责批量歌曲工作流，`DownloadProgress` 与 `LogPanel` 组成响应式活动区；全局设计令牌和断点集中在 `app.css`。

**Tech Stack:** Python 3.11、pywebview、Svelte 5、TypeScript、Vite、Tailwind CSS、Flowbite Svelte、Node test、pytest。

## Global Constraints

- 不修改 `window.pywebview.api` 的方法集合、参数和返回结构。
- 不修改搜索、下载、重试、文件命名或元数据成功语义。
- 默认窗口尺寸必须为 `1280x800`，最低窗口尺寸必须为 `1024x720`。
- `1180px` 及以上并排显示结果区与活动栏；更窄时活动栏移到结果区下方。
- 不引入外部字体、远程图标或新的前端依赖。
- GUI 启动页不得出现 `Cloudflare`、`Playwright`、`Chrome`、堆栈或 trace 等底层诊断词。
- 不直接编辑 `music_downloader/gui/static/`；只通过 Vite 构建刷新。
- 所有相关用户文档、开发者文档、历史设计记录中的有效性说明、测试和注释必须与最终实现一致。

---

## 文件结构

- Modify: `music_downloader/gui/app.py` — 默认和最低窗口尺寸。
- Modify: `tests/test_gui_app.py` — 窗口尺寸契约。
- Create: `music_downloader/gui/frontend/tests/workbench.test.mjs` — 工作台结构、响应式和可访问性源码契约。
- Modify: `music_downloader/gui/frontend/tests/startup.test.mjs` — 启动页减少动效契约。
- Modify: `music_downloader/gui/frontend/src/app.css` — 设计令牌、焦点、文本选择、响应式工作台布局。
- Modify: `music_downloader/gui/frontend/src/App.svelte` — 搜索优先结构和响应式活动区。
- Modify: `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte` — 主搜索、动态状态和表单属性。
- Modify: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte` — 常用设置与可展开高级设置。
- Modify: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte` — 音乐列表层级、图片属性和批量操作。
- Modify: `music_downloader/gui/frontend/src/lib/components/DownloadProgress.svelte` — 音轨进度和动态播报。
- Modify: `music_downloader/gui/frontend/src/lib/components/LogPanel.svelte` — 可复制日志与焦点状态。
- Modify: `music_downloader/gui/frontend/src/lib/components/EmptyState.svelte` — 更明确的空状态引导。
- Modify: `music_downloader/gui/frontend/src/lib/components/EnvironmentModal.svelte` — 统一焦点样式和可滚动区域。
- Modify: `music_downloader/gui/frontend/src/lib/components/StartupScreen.svelte` — 统一令牌和减少动效。
- Modify: `README.md` — 用户可见的尺寸、布局和设置行为。
- Modify: `AGENTS.md` — 前端维护约定和响应式基线。
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md` — 清理后验收措辞，保持最终状态表述。
- Modify: `docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md` — 标注旧尺寸设计已被新规格取代。
- Generate: `music_downloader/gui/static/index.html` 与 `music_downloader/gui/static/assets/*` — Vite 构建产物。

---

### Task 1: 更新桌面窗口尺寸契约

**Files:**
- Modify: `tests/test_gui_app.py`
- Modify: `music_downloader/gui/app.py`

**Interfaces:**
- Consumes: `DEFAULT_WINDOW_SIZE: tuple[int, int]`、`MIN_WINDOW_SIZE: tuple[int, int]`。
- Produces: 默认 `(1280, 800)`、最低 `(1024, 720)` 的 pywebview 窗口配置。

- [ ] **Step 1: 先修改窗口测试期望**

将 `test_window_size_constants_match_designed_minimum` 改为：

```python
def test_window_size_constants_match_workbench_layout() -> None:
    assert app.DEFAULT_WINDOW_SIZE == (1280, 800)
    assert app.MIN_WINDOW_SIZE == (1024, 720)
```

把 `test_run_gui_uses_default_window_size` 的配置改为 `1280`、`800`，并断言：

```python
assert captured["width"] == 1280
assert captured["height"] == 800
assert captured["min_size"] == (1024, 720)
```

把 `test_run_gui_clamps_window_size_to_minimum` 的断言改为：

```python
assert captured["width"] == 1024
assert captured["height"] == 720
assert captured["min_size"] == (1024, 720)
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run: `python -m pytest tests/test_gui_app.py -q`

Expected: FAIL，实际常量仍为 `(1266, 1013)`。

- [ ] **Step 3: 修改生产常量**

在 `music_downloader/gui/app.py` 中设置：

```python
DEFAULT_WINDOW_SIZE = (1280, 800)
MIN_WINDOW_SIZE = (1024, 720)
```

- [ ] **Step 4: 运行窗口测试并确认通过**

Run: `python -m pytest tests/test_gui_app.py -q`

Expected: PASS。

- [ ] **Step 5: 提交窗口契约**

```bash
git add music_downloader/gui/app.py tests/test_gui_app.py
git commit -m "feat: resize GUI for responsive workbench"
```

---

### Task 2: 建立设计令牌、焦点和减少动效基线

**Files:**
- Create: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `music_downloader/gui/frontend/tests/startup.test.mjs`
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `music_downloader/gui/frontend/src/lib/components/StartupScreen.svelte`

**Interfaces:**
- Consumes: 现有 Tailwind/Flowbite 样式管线。
- Produces: CSS 变量、全局 `focus-visible`、选择策略、`1180px` 断点和减少动效规则。

- [ ] **Step 1: 添加会失败的全局样式测试**

创建 `workbench.test.mjs`，包含：

```js
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = (relativePath) =>
  readFile(new URL(`../src/${relativePath}`, import.meta.url), "utf8");

test("workbench styles define the approved tokens and responsive activity rail", async () => {
  const css = await source("app.css");
  assert.match(css, /--color-canvas:\s*#f3f7fc/i);
  assert.match(css, /--color-ink:\s*#102033/i);
  assert.match(css, /--color-track:\s*#2563eb/i);
  assert.match(css, /\.workbench-main/);
  assert.match(css, /\.activity-rail/);
  assert.match(css, /@media\s*\(max-width:\s*1179px\)/);
});

test("interactive controls have a focus-visible baseline and body text stays selectable", async () => {
  const css = await source("app.css");
  assert.match(css, /:focus-visible/);
  assert.doesNotMatch(css, /body\s*\{[^}]*user-select:\s*none/s);
  assert.match(css, /\.no-select[^}]*user-select:\s*none/s);
});
```

向 `startup.test.mjs` 添加：

```js
test("startup motion respects the user's reduced-motion preference", async () => {
  const source = await readStartupScreenSource();
  assert.match(source, /prefers-reduced-motion:\s*reduce/);
  assert.match(source, /transition-duration:\s*0\.01ms/);
});
```

- [ ] **Step 2: 运行 Node 测试并确认失败原因正确**

Run: `node --test tests/*.test.mjs`

Expected: FAIL，缺少设计变量、工作台布局类、选择策略和减少动效规则。

- [ ] **Step 3: 在 `app.css` 实现基础令牌与交互基线**

在 `:root` 定义批准的六个颜色变量和字体变量；移除 `body` 的 `user-select: none`；增加 `.no-select`；为 `button`、`input`、`select`、`summary` 添加统一的 `:focus-visible` 轮廓；为 `.workbench-main` 和 `.activity-rail` 添加宽窄布局规则。

焦点实现使用：

```css
:where(button, input, select, summary):focus-visible {
  outline: 3px solid color-mix(in srgb, var(--color-track) 28%, transparent);
  outline-offset: 2px;
}
```

- [ ] **Step 4: 在启动页实现减少动效降级**

在 `StartupScreen.svelte` 的组件样式末尾增加：

```css
@media (prefers-reduced-motion: reduce) {
  .startup-progress-fill {
    transition-duration: 0.01ms;
  }
}
```

同时把启动页的硬编码主色替换为对应 CSS 变量，但不改变阶段文案和品牌结构。

- [ ] **Step 5: 运行 Node 测试并确认通过**

Run: `node --test tests/*.test.mjs`

Expected: PASS。

- [ ] **Step 6: 提交样式基线**

```bash
git add music_downloader/gui/frontend/src/app.css music_downloader/gui/frontend/src/lib/components/StartupScreen.svelte music_downloader/gui/frontend/tests/startup.test.mjs music_downloader/gui/frontend/tests/workbench.test.mjs
git commit -m "feat: add workbench design foundations"
```

---

### Task 3: 重排为搜索优先的命令区和分层设置

**Files:**
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte`

**Interfaces:**
- Consumes: 现有 `GuiConfig`、`ValidOptions`、搜索回调和设置回调。
- Produces: 搜索优先的 DOM 顺序、常用设置行和原生 `<details>` 高级设置区。

- [ ] **Step 1: 添加会失败的命令区测试**

向 `workbench.test.mjs` 添加：

```js
test("the main workbench presents search before settings", async () => {
  const app = await source("App.svelte");
  assert.ok(app.indexOf("<SearchBar") < app.indexOf("<SettingsPanel"));
  assert.match(app, /class="music-track/);
  assert.match(app, /class="workbench-command/);
});

test("settings separate quick controls from advanced controls", async () => {
  const settings = await source("lib/components/SettingsPanel.svelte");
  assert.match(settings, /<details/);
  assert.match(settings, /<summary[^>]*>\s*更多设置/);
  assert.ok(settings.indexOf("sourceSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("typeSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("bitrateSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("numberInput") > settings.indexOf("<details"));
});

test("search and settings controls expose stable form metadata", async () => {
  const search = await source("lib/components/SearchBar.svelte");
  const settings = await source("lib/components/SettingsPanel.svelte");
  assert.match(search, /name="keyword"/);
  assert.match(search, /autocomplete="off"/);
  assert.match(search, /搜索歌曲、歌手、专辑…/);
  for (const name of [
    "source",
    "search_type",
    "bitrate",
    "number",
    "download_cover",
    "download_lyric",
    "output_dir"
  ]) {
    assert.match(settings, new RegExp(`name="${name}"`));
  }
});
```

- [ ] **Step 2: 运行目标测试并确认失败**

Run: `node --test tests/workbench.test.mjs`

Expected: FAIL，当前设置位于搜索之前，且没有 `<details>`、音轨类和完整表单元数据。

- [ ] **Step 3: 重排 `App.svelte` 顶部结构**

把标题、品牌音轨、`SearchBar` 和 `SettingsPanel` 放入 `.workbench-command`，确保源码和 DOM 中 `SearchBar` 位于 `SettingsPanel` 之前。保留原有 props 和回调，不复制状态。

- [ ] **Step 4: 改造 `SearchBar.svelte`**

保留 `<form>`；输入框增加 `name="keyword"`、`autocomplete="off"`，占位符改为 `搜索歌曲、歌手、专辑…`。结果数量和搜索中状态放进 `aria-live="polite"`、`aria-atomic="true"` 的状态容器。

- [ ] **Step 5: 改造 `SettingsPanel.svelte`**

常用区只保留音源、类型和音质。使用原生 `<details>`/`<summary>` 承载数量、封面、歌词、下载目录、浏览、打开和环境检查。所有字段增加稳定 `name`，非认证文本字段增加 `autocomplete="off"`，复选框维持标签包裹的完整点击区域。

- [ ] **Step 6: 运行目标测试与 Svelte 检查**

Run: `node --test tests/workbench.test.mjs`

Expected: PASS。

Run: `npm.cmd run check`

Expected: `0 errors and 0 warnings`。

- [ ] **Step 7: 提交命令区改造**

```bash
git add music_downloader/gui/frontend/src/App.svelte music_downloader/gui/frontend/src/lib/components/SearchBar.svelte music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte music_downloader/gui/frontend/tests/workbench.test.mjs
git commit -m "feat: make search primary in the GUI"
```

---

### Task 4: 完成结果区、活动区和可访问性细节

**Files:**
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/DownloadProgress.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/LogPanel.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/EmptyState.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/EnvironmentModal.svelte`

**Interfaces:**
- Consumes: `Song[]`、选择集合、`SongStatus`、`DownloadProgressState`、`LogEntry[]`。
- Produces: 响应式 `.workbench-main`/`.activity-rail`、可复制日志、稳定封面和动态下载播报。

- [ ] **Step 1: 添加会失败的活动区和内容测试**

向 `workbench.test.mjs` 添加：

```js
test("results and activity panels expose stable responsive hooks", async () => {
  const app = await source("App.svelte");
  assert.match(app, /class="workbench-main/);
  assert.match(app, /class="results-workspace/);
  assert.match(app, /class="activity-rail/);
  assert.match(app, /let logCollapsed = \$state\(true\)/);
});

test("download progress is announced without making the entire log live", async () => {
  const progress = await source("lib/components/DownloadProgress.svelte");
  const logs = await source("lib/components/LogPanel.svelte");
  assert.match(progress, /aria-live="polite"/);
  assert.match(progress, /aria-atomic="true"/);
  assert.doesNotMatch(logs, /aria-live=/);
  assert.match(logs, /select-text/);
});

test("album art reserves space and loads lazily", async () => {
  const results = await source("lib/components/ResultList.svelte");
  assert.match(results, /<img[^>]*width="48"[^>]*height="48"[^>]*loading="lazy"/s);
});

test("search overlay exposes an assistive status", async () => {
  const app = await source("App.svelte");
  assert.match(app, /id="loadingOverlay"[^>]*role="status"[^>]*aria-live="polite"/s);
});
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `node --test tests/workbench.test.mjs`

Expected: FAIL，当前缺少布局钩子、默认折叠、动态播报、可复制日志和图片属性。

- [ ] **Step 3: 实现响应式主体结构**

在 `App.svelte` 中用 `.workbench-main` 包裹 `.results-workspace` 和 `.activity-rail`。删除固定 `grid-cols-[minmax(0,1fr)_360px]`。搜索覆盖层增加 `role="status"`、`aria-live="polite"` 和 `aria-atomic="true"`。

- [ ] **Step 4: 优化结果列表**

保持列表结构和批量按钮语义。封面图片写为：

```svelte
<img
  class="h-full w-full object-cover"
  src={song.cover}
  alt=""
  width="48"
  height="48"
  loading="lazy"
/>
```

为时长和计数增加等宽数字类；保持长标题 `truncate` 和容器 `min-w-0`。

- [ ] **Step 5: 优化下载进度、日志和空状态**

`DownloadProgress.svelte` 的根区域增加 `aria-live="polite"`、`aria-atomic="true"`，应用音轨类和等宽数字。`LogPanel.svelte` 的日志内容增加 `select-text`，但不增加 `aria-live`，避免逐条播报。空状态文案改为“搜索歌曲或歌手，结果会显示在这里”，保持明确下一步。

- [ ] **Step 6: 统一环境弹窗交互**

为弹窗正文增加 `overscroll-behavior: contain` 对应类；关闭按钮使用全局焦点基线，不新增重复的局部 outline 规则。

- [ ] **Step 7: 运行 Node 测试和 Svelte 检查**

Run: `node --test tests/*.test.mjs`

Expected: PASS。

Run: `npm.cmd run check`

Expected: `0 errors and 0 warnings`。

- [ ] **Step 8: 提交工作区改造**

```bash
git add music_downloader/gui/frontend/src/App.svelte music_downloader/gui/frontend/src/lib/components music_downloader/gui/frontend/tests/workbench.test.mjs
git commit -m "feat: finish responsive music workbench"
```

---

### Task 5: 同步全部相关文档并建立一致性检查

**Files:**
- Create: `tests/test_gui_documentation.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md`

**Interfaces:**
- Consumes: 最终窗口、布局、设置和日志行为。
- Produces: 用户文档、维护约定和历史文档有效性说明一致。

- [ ] **Step 1: 添加会失败的文档契约测试**

创建 `tests/test_gui_documentation.py`：

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_gui_docs_match_workbench_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "1280x800" in readme
    assert "1024x720" in readme
    assert "搜索" in readme and "更多设置" in readme
    assert "1180px" in agents
    assert "日志默认折叠" in agents
    assert "1266x1013" not in readme


def test_superseded_gui_plan_points_to_current_design() -> None:
    old_plan = (
        ROOT / "docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md"
    ).read_text(encoding="utf-8")
    assert "2026-07-12-music-workbench-frontend-design.md" in old_plan
    assert "历史尺寸约定已被取代" in old_plan
```

- [ ] **Step 2: 运行文档测试并确认失败**

Run: `python -m pytest tests/test_gui_documentation.py -q`

Expected: FAIL，README 和 AGENTS 尚未描述工作台契约，旧计划尚未标记被取代。

- [ ] **Step 3: 更新当前用户和开发者文档**

在 `README.md` 更新：

- 默认窗口 `1280x800`、最低窗口 `1024x720`。
- 搜索优先的顶部命令区。
- 音源、类型、音质为常用设置，数量、封面、歌词、目录和环境检查位于“更多设置”。
- `1180px` 以下活动区移到结果下方，日志默认折叠。

在 `AGENTS.md` 增加维护约定：

- 不恢复固定 `360px` 无断点右栏。
- 保持 `1180px` 响应式切换和 `1024x720` 最低尺寸。
- 保持搜索优先、常用/高级设置分层、日志默认折叠、日志与路径可复制。
- 修改相关行为时同步 Node 测试、README、AGENTS 和静态构建产物。

- [ ] **Step 4: 处理历史文档和当前规格措辞**

在 `docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md` 顶部增加明确说明：

```markdown
> 历史说明：本文记录 2026-07-02 的实施方案，其中窗口尺寸等约定已被
> `../specs/2026-07-12-music-workbench-frontend-design.md` 取代；当前维护以新规格为准。
```

把当前设计规格的旧尺寸清理验收改成不重复旧值的表述：“再次搜索已废弃的窗口尺寸字面量和旧布局描述”。

- [ ] **Step 5: 运行文档测试和全仓文本审计**

Run: `python -m pytest tests/test_gui_documentation.py -q`

Expected: PASS。

Run:

```powershell
rg -n '1266\s*[x×,]\s*1013|1200\s*[x×,]\s*750|固定.*360px|日志默认展开' . -g '!music_downloader/gui/frontend/node_modules/**' -g '!music_downloader/gui/static/assets/**'
```

Expected: 只允许历史文档的已取代说明以及本实施计划的反向测试/清理命令出现旧约定；README、AGENTS、当前规格、生产代码和测试不得把旧值描述为当前行为。

- [ ] **Step 6: 提交文档同步**

```bash
git add README.md AGENTS.md docs/superpowers tests/test_gui_documentation.py
git commit -m "docs: align GUI guidance with workbench layout"
```

---

### Task 6: 刷新静态产物并进行最终验证

**Files:**
- Generate: `music_downloader/gui/static/index.html`
- Generate: `music_downloader/gui/static/assets/*`
- Verify: 所有前端源码、GUI 测试、文档和构建约定。

**Interfaces:**
- Consumes: 已通过源码测试和 Svelte 检查的前端。
- Produces: pywebview 实际加载的最新静态资源。

- [ ] **Step 1: 运行完整前端测试**

Run: `node --test tests/*.test.mjs`

Expected: 全部 PASS。

Run: `npm.cmd run check`

Expected: `0 errors and 0 warnings`。

- [ ] **Step 2: 构建并刷新静态资源**

Run: `npm.cmd run build`

Expected: Vite 成功输出到 `music_downloader/gui/static/`，不包含编译错误或警告。

- [ ] **Step 3: 运行 GUI 和文档相关 pytest**

Run:

```powershell
python -m pytest tests/test_gui_app.py tests/test_gui_static.py tests/test_gui_documentation.py tests/test_build_script.py -q
```

Expected: 全部 PASS。

- [ ] **Step 4: 运行代码质量检查**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

Expected: 全部退出码为 0。

- [ ] **Step 5: 用模拟桥接完成双尺寸视觉验证**

使用原生 Python Playwright 脚本注入与 `PywebviewApi` 同签名的内存实现，在 `1024x720` 和 `1280x800` 分别验证：

- 空状态无水平滚动。
- 搜索框在设置之前且可通过键盘聚焦。
- “更多设置”展开后仍可访问下载目录和环境检查。
- 搜索结果标题、歌手、专辑、状态和时长不互相覆盖。
- 宽窗口活动栏位于右侧，窄窗口活动栏位于结果下方。
- 日志默认折叠，展开后日志文字可选择。
- 控制台无应用 JavaScript 错误。

- [ ] **Step 6: 检查最终差异和过期信息**

Run:

```powershell
git diff --check
git status --short
rg -n '1266\s*[x×,]\s*1013|1200\s*[x×,]\s*750|日志默认展开' README.md AGENTS.md music_downloader tests docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md
```

Expected: `git diff --check` 无输出；旧尺寸和旧行为不再作为当前事实出现；只存在本计划范围内的改动。

- [ ] **Step 7: 提交静态产物和最终调整**

```bash
git add music_downloader/gui/static music_downloader/gui/frontend README.md AGENTS.md tests docs/superpowers
git commit -m "feat: deliver responsive music workbench GUI"
```
