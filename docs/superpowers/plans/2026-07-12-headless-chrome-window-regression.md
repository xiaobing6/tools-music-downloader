# Headless Chrome 白窗回归修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 GUI 启动时由 headless Chrome 平台窗口造成的不可交互白窗，并让实际默认窗口尺寸与代码及文档统一。

**Architecture:** 保留 GUI 现有 `launch_persistent_context` 和独立 `.chrome-profile/`，在 `music_downloader/gui/bridge.py` 内集中生成与 headless 状态相关的 Chrome 参数；headless 模式把平台窗口移到屏幕外，headed Cloudflare 回退不使用该参数。窗口尺寸仍由 `settings.load_config()` 提供，但其默认值必须与 `app.DEFAULT_WINDOW_SIZE` 保持一致。

**Tech Stack:** Python 3.11、Playwright sync API、pywebview、pytest、ruff、mypy、Vite/Svelte 前端验证。

## Global Constraints

- 继续使用系统 Google Chrome，`channel="chrome"`，不切换到 Playwright Chromium。
- 继续使用 `launch_persistent_context` 和项目根目录 `.chrome-profile/`。
- headless 模式加入 `--window-position=-32000,-32000`；headed 模式不得加入。
- 默认 GUI 窗口必须为 `1280x800`，最小窗口必须为 `1024x720`。
- 不改变 Cloudflare 回退、API 签名、搜索、下载、标签写入或成功语义。
- GUI 启动页不展示 `Cloudflare`、`Playwright`、`Chrome`、堆栈或 trace 等底层诊断词。
- 所有相关文档必须同步，不能只更新 README。

## File Map

- Modify: `music_downloader/gui/bridge.py` — 为 GUI 的 persistent context 生成 headless/headed 启动参数。
- Modify: `tests/test_gui_bridge.py` — 覆盖首次 headless 启动与 Cloudflare headed 回退的参数边界。
- Modify: `music_downloader/gui/settings.py` — 把实际默认窗口尺寸改为 `1280x800`。
- Modify: `tests/test_gui_settings.py` — 跨模块断言 settings 默认尺寸等于 app 窗口常量。
- Modify: `tests/test_gui_documentation.py` — 锁定 README 与 AGENTS 的白窗兼容说明。
- Modify: `README.md` — 记录正常行为和白窗排错信息。
- Modify: `AGENTS.md` — 记录 headless/headed 参数约束。
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md` — 补充实际默认配置与窗口常量一致性要求。
- Modify: `docs/superpowers/plans/2026-07-12-music-workbench-frontend.md` — 记录原窗口任务遗漏 settings 的更正说明。
- Modify: `docs/superpowers/specs/2026-07-12-headless-chrome-window-regression-design.md` — 实施完成后更新状态和验证结果。
- Modify: `docs/superpowers/plans/2026-07-12-headless-chrome-window-regression.md` — 勾选已完成步骤并记录最终验证。

---

### Task 1: 把 headless Chrome 平台窗口移到屏幕外

**Files:**
- Modify: `tests/test_gui_bridge.py`
- Modify: `music_downloader/gui/bridge.py`

**Interfaces:**
- Consumes: `_PlaywrightThread.start_browser(*, headless: bool = True, user_data_dir: str | None = None) -> bool`。
- Produces: `_browser_launch_args(*, headless: bool) -> list[str]` 和常量 `HEADLESS_WINDOW_POSITION_ARG`。

- [ ] **Step 1: 写入失败的浏览器启动回归测试**

在 `tests/test_gui_bridge.py` 中追加以下测试夹具和用例：

```python
class _FakePage:
    def goto(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeContext:
    def __init__(self) -> None:
        self.pages = [_FakePage()]
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, calls: list[dict[str, object]]) -> None:
        self.calls = calls

    def launch_persistent_context(self, **kwargs: object) -> _FakeContext:
        self.calls.append(kwargs)
        return _FakeContext()


class _FakePlaywright:
    def __init__(self, calls: list[dict[str, object]]) -> None:
        self.chromium = _FakeChromium(calls)


def test_gui_browser_hides_only_headless_platform_window(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    cloudflare_results = iter([False, True])
    session = bridge_module._PlaywrightThread()
    session._playwright = _FakePlaywright(calls)
    monkeypatch.setattr(session, "submit", lambda func, timeout=None: func())
    monkeypatch.setattr(
        bridge_module,
        "wait_for_cloudflare",
        lambda _page: next(cloudflare_results),
    )

    assert session.start_browser(headless=True, user_data_dir=str(tmp_path)) is True
    assert calls[0]["headless"] is True
    assert calls[0]["args"] == ["--window-position=-32000,-32000"]
    assert calls[1]["headless"] is False
    assert calls[1]["args"] == []
```

- [ ] **Step 2: 运行测试并确认因缺少启动参数失败**

Run:

```powershell
pytest tests/test_gui_bridge.py::test_gui_browser_hides_only_headless_platform_window -v
```

Expected: FAIL，`calls[0]` 不包含 `args`，证明测试能捕获当前白窗回归。

- [ ] **Step 3: 写入最小实现**

在 `music_downloader/gui/bridge.py` 的 callback 类型别名附近加入：

```python
HEADLESS_WINDOW_POSITION_ARG = "--window-position=-32000,-32000"


def _browser_launch_args(*, headless: bool) -> list[str]:
    return [HEADLESS_WINDOW_POSITION_ARG] if headless else []
```

把第一次 `launch_persistent_context` 调用补充为：

```python
self._context = self._playwright.chromium.launch_persistent_context(
    user_data_dir=final_user_data_dir,
    channel="chrome",
    headless=final_headless,
    user_agent=USER_AGENT,
    args=_browser_launch_args(headless=final_headless),
)
```

把 Cloudflare headed 回退调用补充为：

```python
self._context = self._playwright.chromium.launch_persistent_context(
    user_data_dir=final_user_data_dir,
    channel="chrome",
    headless=False,
    user_agent=USER_AGENT,
    args=_browser_launch_args(headless=False),
)
```

- [ ] **Step 4: 运行回归测试和 bridge 测试**

Run:

```powershell
pytest tests/test_gui_bridge.py -v
```

Expected: 全部 PASS，首次启动参数包含屏幕外位置，headed 回退参数为空。

- [ ] **Step 5: 提交浏览器窗口修复**

```powershell
git add music_downloader/gui/bridge.py tests/test_gui_bridge.py
git commit -m "fix: hide headless Chrome platform window"
```

---

### Task 2: 统一真实 GUI 默认窗口尺寸

**Files:**
- Modify: `tests/test_gui_settings.py`
- Modify: `music_downloader/gui/settings.py`

**Interfaces:**
- Consumes: `music_downloader.gui.app.DEFAULT_WINDOW_SIZE: tuple[int, int]`。
- Produces: `DEFAULT_CONFIG["window_width"] == 1280` 和 `DEFAULT_CONFIG["window_height"] == 800`。

- [ ] **Step 1: 把 settings 测试改为跨模块一致性断言**

在 `tests/test_gui_settings.py` 顶部加入：

```python
from music_downloader.gui import app as app_module
```

把 `test_load_config_returns_defaults_each_time` 的尺寸断言替换为：

```python
    assert (config["window_width"], config["window_height"]) == app_module.DEFAULT_WINDOW_SIZE
```

- [ ] **Step 2: 运行测试并确认旧配置触发失败**

Run:

```powershell
pytest tests/test_gui_settings.py::test_load_config_returns_defaults_each_time -v
```

Expected: FAIL，实际 `(1266, 1013)` 不等于 `(1280, 800)`。

- [ ] **Step 3: 更新真实默认配置**

在 `music_downloader/gui/settings.py` 中修改：

```python
    "window_width": 1280,
    "window_height": 800,
```

- [ ] **Step 4: 运行窗口和 settings 测试**

Run:

```powershell
pytest tests/test_gui_app.py tests/test_gui_settings.py -v
```

Expected: 全部 PASS；默认值 `1280x800`，低于最小尺寸的输入仍被钳制到 `1024x720`。

- [ ] **Step 5: 提交尺寸一致性修复**

```powershell
git add music_downloader/gui/settings.py tests/test_gui_settings.py
git commit -m "fix: align GUI default window size"
```

---

### Task 3: 同步所有相关文档并锁定文档契约

**Files:**
- Modify: `tests/test_gui_documentation.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-music-workbench-frontend.md`
- Modify: `docs/superpowers/specs/2026-07-12-headless-chrome-window-regression-design.md`

**Interfaces:**
- Consumes: Task 1 的 headless/headed 行为和 Task 2 的真实窗口默认值。
- Produces: 用户文档、协作者约定和历史设计记录一致的浏览器窗口行为说明。

- [ ] **Step 1: 先增加失败的文档测试**

在 `tests/test_gui_documentation.py` 追加：

```python
def test_gui_docs_cover_headless_window_regression() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "不可交互的白色窗口" in readme
    assert "--window-position=-32000,-32000" in agents
    assert "headed" in agents
```

- [ ] **Step 2: 运行测试并确认文档说明缺失**

Run:

```powershell
pytest tests/test_gui_documentation.py::test_gui_docs_cover_headless_window_regression -v
```

Expected: FAIL，README 和 AGENTS 尚未包含新的兼容约定。

- [ ] **Step 3: 更新 README 和 AGENTS**

在 `README.md` 的 GUI 启动说明中增加：

```markdown
GUI 的后台 Chrome 默认以 headless 模式运行。为避免新版 Chrome 在 Windows 上把本应隐藏的平台窗口显示为不可交互的白色窗口，程序会把该平台窗口放到屏幕外；如果站点验证需要人工处理，程序仍会重新打开正常可见的 Chrome 窗口。
```

在 `README.md` 排错章节增加：如果再次出现不可交互白窗，应确认 headless 启动仍带屏幕外位置参数，并检查 Chrome/Playwright 版本；不要通过隐藏 GUI 或禁用整个浏览器规避。

在 `AGENTS.md` 的 API 交互流程中把 headless/visible 步骤补充为：

```markdown
- GUI 的 headless persistent context 必须带 `--window-position=-32000,-32000`，防止新版 Chrome 的平台窗口被 Windows 合成到桌面。
- headed Cloudflare 回退不得带该参数，否则用户无法完成人工验证。
```

- [ ] **Step 4: 更新相关设计和历史计划**

在音乐工作台设计的“窗口与桌面集成”中补充 `settings.DEFAULT_CONFIG` 必须与 `app.DEFAULT_WINDOW_SIZE` 同步。

在音乐工作台历史计划的 Task 1 前增加更正说明：原计划只修改了 `app.py` 和 `test_gui_app.py`，遗漏 `settings.py`；该遗漏由本修复计划覆盖。

在白窗修复设计文档中补充最终采用的实现位置；状态保持“实施中”，真实 GUI 验证结果留到 Task 4 完成后填写。

- [ ] **Step 5: 运行文档测试和矛盾扫描**

Run:

```powershell
pytest tests/test_gui_documentation.py -v
rg -n "1266x1013|1266×1013|window_width.*1266|window_height.*1013" README.md AGENTS.md music_downloader/gui tests docs/superpowers
```

Expected: 文档测试全部 PASS；旧尺寸只允许出现在本次回归设计/计划对历史缺陷的说明中，不得出现在当前配置、README、AGENTS 或有效断言中。

- [ ] **Step 6: 提交文档同步**

```powershell
git add README.md AGENTS.md tests/test_gui_documentation.py docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md docs/superpowers/plans/2026-07-12-music-workbench-frontend.md docs/superpowers/specs/2026-07-12-headless-chrome-window-regression-design.md
git commit -m "docs: document headless Chrome window handling"
```

---

### Task 4: 完整验证与真实 GUI 验收

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-headless-chrome-window-regression-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-headless-chrome-window-regression.md`
- Verify: 全仓 Python、前端源码和静态构建产物。

**Interfaces:**
- Consumes: Tasks 1–3 的代码、测试和文档。
- Produces: 可复查的最终验证记录和干净工作区。

- [ ] **Step 1: 运行 Python 回归套件**

Run:

```powershell
pytest
ruff check .
ruff format --check .
mypy music_downloader
python -m py_compile music_download.py
```

Expected: pytest 全部 PASS；ruff、mypy、py_compile 均以退出码 0 完成。

- [ ] **Step 2: 运行前端测试和构建**

Run from `music_downloader/gui/frontend`:

```powershell
npm test
npm run check
npm run build
```

Expected: Node 测试全部 PASS，Svelte check 无 error/warning，Vite 构建成功；`music_downloader/gui/static/` 与源码一致。

- [ ] **Step 3: 检查构建后差异**

Run:

```powershell
git status --short
git diff --check
```

Expected: 只有本计划和验证记录的预期改动；不得出现临时探针文件或无关静态差异。

- [ ] **Step 4: 启动真实 GUI 验收**

Run:

```powershell
python .\music_download.py
```

Expected:

- 正常进入音乐下载器首页。
- 桌面只出现音乐下载器 GUI，不出现不可交互白窗。
- 后台 Chrome profile 和页面初始化正常。
- 如果 Cloudflare 需要人工验证，headed Chrome 在屏幕内正常显示。
- 关闭 GUI 后 Chrome、Playwright 和 WebView2 子进程按现有清理流程退出。

- [ ] **Step 5: 写入最终验证结果并提交**

在本计划勾选完成项，把对应设计文档状态更新为“已实施”，记录实际命令和结果，然后运行：

```powershell
git add docs/superpowers/specs/2026-07-12-headless-chrome-window-regression-design.md docs/superpowers/plans/2026-07-12-headless-chrome-window-regression.md
git commit -m "docs: record headless Chrome fix verification"
```

- [ ] **Step 6: 确认最终工作区状态**

Run:

```powershell
git status --short
git log -5 --oneline
```

Expected: 工作区干净，最近提交依次包含浏览器窗口修复、尺寸一致性修复、文档同步和验证记录。
