# Source Catalog and Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复六项已确认的可靠性与可访问性问题，并让 13 个音源的 API 值和展示名只在 Python `Source` 枚举中维护一次。

**Architecture:** `Source` 枚举作为唯一音源目录，配置、CLI 和 GUI API 都从它派生，Svelte 只消费后端选项。浏览器与下载任务分别收敛为单一清理/完成出口；音频下载在原子替换前执行保守 MIME 与内容嗅探。GUI 在不改变工作台布局的前提下增加可见搜索反馈和统一的礼貌播报。

**Tech Stack:** Python 3.11、Pydantic 2、Playwright sync API、pytest、Typer/Rich、Svelte 5、TypeScript、Vite、Node test runner。

## Global Constraints

- Python 语法基线为 3.11+，使用 PEP 604 `X | None`。
- CLI 参数、模型和上游请求继续使用原始音源 ID；中文名只用于面向用户的展示。
- 默认音源、下载文件命名、文件存在即跳过和“元数据失败 warning-only”语义不变。
- 音频校验只拒绝明确 HTML/JSON/XML 错误文档，不要求固定音频魔数或 Mutagen 可解析。
- Playwright 对象只能在专用 Playwright 线程创建和销毁。
- GUI 前端静态产物只能通过 `npm run build` 生成，禁止直接编辑 `music_downloader/gui/static/`。
- GUI 仍使用原生 `<select>`、固定工作台外壳、内部滚动和当前关闭确认流程。
- 单元测试不访问真实音乐站点；真实搜索仅用于最终本地集成验证。

---

## File Map

- `music_downloader/domain/enums.py`：唯一音源目录及 `source_label()`。
- `music_downloader/core/config.py`：从 `Source` 派生 `VALID_SOURCES`。
- `music_downloader/infrastructure/files.py`：CLI 表格/列表规范化时解析音源展示名。
- `music_downloader/cli/app.py`、`music_downloader/cli/workflow.py`：帮助、搜索提示和交互提示使用统一展示名。
- `music_downloader/gui/api.py`：从 `Source` 生成 GUI 音源选项，删除 `_SOURCE_LABELS`。
- `music_downloader/gui/bridge.py`：浏览器失败清理、GUI 日志音源展示、下载任务单一完成出口。
- `music_downloader/infrastructure/downloader.py`：保守音频响应校验。
- `music_downloader/gui/frontend/src/App.svelte`：搜索反馈/播报状态编排，并传递后端音源选项。
- `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte`：可见校验/失败提示。
- `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`：消费后端音源选项并播报搜索状态。
- `tests/` 与 `music_downloader/gui/frontend/tests/`：各项回归测试。
- `README.md`、`AGENTS.md`：音源列表、维护方式和酷狗限制。
- `music_downloader/gui/static/`：Vite 重建产物。

### Task 1: 建立单一音源目录并统一 CLI/GUI 展示

**Files:**
- Modify: `music_downloader/domain/enums.py`
- Modify: `music_downloader/core/config.py`
- Modify: `music_downloader/infrastructure/files.py`
- Modify: `music_downloader/cli/app.py`
- Modify: `music_downloader/cli/workflow.py`
- Modify: `music_downloader/gui/api.py`
- Modify: `music_downloader/gui/bridge.py`
- Test: `tests/test_domain_models.py`
- Test: `tests/test_file_rules.py`
- Test: `tests/test_cli_app.py`
- Test: `tests/test_gui_settings.py`
- Test: `tests/test_gui_bridge.py`

**Interfaces:**
- Produces: `Source.label: str` 和 `source_label(value: object, fallback: str = "未知") -> str`。
- Produces: `VALID_SOURCES == [source.value for source in Source]`，包含新增 `kugou`。
- Consumes later: GUI `ValidOptions.sources` 继续保持 `{value, label}` 结构。

- [ ] **Step 1: 写音源目录和展示路径的失败测试**

```python
EXPECTED_SOURCES = {
    "netease": "网易云音乐",
    "migu": "咪咕音乐",
    "kugou": "酷狗音乐",
    "kuwo": "酷我音乐",
    "ytmusic": "YouTube Music",
    "tidal": "Tidal",
    "qobuz": "Qobuz",
    "deezer": "Deezer",
    "spotify": "Spotify",
    "tencent": "QQ音乐",
    "ximalaya": "喜马拉雅",
    "joox": "JOOX",
    "apple": "Apple Music",
}

def test_source_catalog_is_complete_and_labeled() -> None:
    assert {item.value: item.label for item in Source} == EXPECTED_SOURCES
    assert VALID_SOURCES == list(EXPECTED_SOURCES)
    assert source_label("kugou") == "酷狗音乐"
    assert source_label("future-source") == "future-source"
```

同时增加以下明确断言：`normalize_song_dict({"source": "netease"})["source"] == "网易云音乐"`；CLI 搜索/交互输出包含 `网易云音乐 (netease)`；`MusicApi().get_valid_options()["sources"] == [{"value": item.value, "label": item.label} for item in Source]`；GUI 搜索日志包含 `来源: 网易云音乐 (netease)`。

- [ ] **Step 2: 运行定向测试确认失败**

Run: `pytest tests/test_domain_models.py tests/test_file_rules.py tests/test_cli_app.py tests/test_gui_settings.py tests/test_gui_bridge.py -q`

Expected: FAIL，至少显示 `Source` 没有 `label`、`kugou` 不在目录、展示仍为原始 ID。

- [ ] **Step 3: 实现带标签的字符串枚举和派生配置**

```python
class Source(str, Enum):
    label: str

    def __new__(cls, value: str, label: str) -> Source:
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    NETEASE = ("netease", "网易云音乐")
    MIGU = ("migu", "咪咕音乐")
    KUGOU = ("kugou", "酷狗音乐")
    KUWO = ("kuwo", "酷我音乐")
    YTMUSIC = ("ytmusic", "YouTube Music")
    TIDAL = ("tidal", "Tidal")
    QOBUZ = ("qobuz", "Qobuz")
    DEEZER = ("deezer", "Deezer")
    SPOTIFY = ("spotify", "Spotify")
    TENCENT = ("tencent", "QQ音乐")
    XIMALAYA = ("ximalaya", "喜马拉雅")
    JOOX = ("joox", "JOOX")
    APPLE = ("apple", "Apple Music")


def source_label(value: object, fallback: str = "未知") -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        return fallback
    try:
        return Source(text).label
    except ValueError:
        return text
```

在 `core/config.py` 导入 `Source` 并设置 `VALID_SOURCES = [source.value for source in Source]`。所有表格、列表、交互提示和 GUI 日志调用 `source_label()`；CLI 帮助使用 `value（label）`；`MusicApi.get_valid_options()` 使用枚举推导并删除 `_SOURCE_LABELS`。

- [ ] **Step 4: 运行定向测试确认通过**

Run: `pytest tests/test_domain_models.py tests/test_file_rules.py tests/test_cli_app.py tests/test_gui_settings.py tests/test_gui_bridge.py -q`

Expected: PASS。

- [ ] **Step 5: 提交音源目录改动**

```powershell
git add music_downloader/domain/enums.py music_downloader/core/config.py music_downloader/infrastructure/files.py music_downloader/cli/app.py music_downloader/cli/workflow.py music_downloader/gui/api.py music_downloader/gui/bridge.py tests/test_domain_models.py tests/test_file_rules.py tests/test_cli_app.py tests/test_gui_settings.py tests/test_gui_bridge.py
git commit -m "feat: 统一音乐源目录与展示名称"
```

### Task 2: 清理失败的浏览器初始化状态

**Files:**
- Modify: `music_downloader/gui/bridge.py`
- Test: `tests/test_gui_bridge.py`

**Interfaces:**
- Produces: `_PlaywrightThread._cleanup_browser() -> None`，只在 Playwright 线程调用。
- Preserves: `_browser_launch_args(headless=True)` 仅返回屏幕外位置；headed 返回空列表。

- [ ] **Step 1: 写失败清理和重试测试**

```python
def test_gui_browser_cleans_failed_context_before_retry(tmp_path, monkeypatch) -> None:
    first = _FakeContext(goto_error=RuntimeError("navigation failed"))
    second = _FakeContext()
    session = _session_with_contexts([first, second], monkeypatch)

    assert session.start_browser(headless=True, user_data_dir=str(tmp_path)) is False
    assert first.closed is True
    assert session.context is None
    assert session.page is None
    assert session.ready is False

    assert session.start_browser(headless=True, user_data_dir=str(tmp_path)) is True
    assert session.context is second
```

再参数化覆盖 launch、`goto`、Cloudflare 未通过和 headed 回退异常；断言每次失败后 context/page/ready 都清空。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_gui_bridge.py -k "browser and (clean or retry or failure)" -q`

Expected: FAIL，旧 context 仍被引用或未关闭。

- [ ] **Step 3: 实现线程内统一清理出口**

```python
def _cleanup_browser(self) -> None:
    context = self._context
    self._context = None
    self._page = None
    self._browser_ready.clear()
    if context is not None:
        with contextlib.suppress(Exception):
            context.close()
```

`_run()` 退出时复用该方法。`start_browser()` 的 `_open()` 先清理旧失败状态，在异常和 Cloudflare 最终失败的 `finally` 分支清理；headless 转 headed 前先清理。只有验证通过才设置 `_browser_ready`。外层 submit 超时设置本次打开的取消标记，使 `_open()` 从阻塞调用返回后不再发布 ready，并执行清理。

- [ ] **Step 4: 运行浏览器桥接测试确认通过**

Run: `pytest tests/test_gui_bridge.py -k browser -q`

Expected: PASS，且既有 headless/headed 参数测试仍通过。

- [ ] **Step 5: 提交浏览器生命周期修复**

```powershell
git add music_downloader/gui/bridge.py tests/test_gui_bridge.py
git commit -m "fix: 清理失败的 GUI 浏览器会话"
```

### Task 3: 拒绝伪装成音频的错误响应

**Files:**
- Modify: `music_downloader/infrastructure/downloader.py`
- Create: `tests/test_downloader.py`

**Interfaces:**
- Produces: `_audio_response_error(content_type: str, body: bytes) -> str | None`；`None` 表示保守接受，字符串为拒绝原因。
- Consumes: `_download_body_to_file()` 在写临时文件前调用该函数。

- [ ] **Step 1: 写 MIME 和内容嗅探失败测试**

```python
@pytest.mark.parametrize("content_type", [
    "text/html; charset=utf-8",
    "application/json",
    "application/problem+json",
    "application/xml",
    "application/problem+xml",
])
def test_download_rejects_explicit_error_documents(tmp_path, content_type) -> None:
    context = _FakeRequestContext(_FakeResponse(content_type, b"x" * 12_000))
    assert _download_body_to_file(context, "https://example", tmp_path / "a.tmp", tmp_path / "a.mp3") is False
    assert not (tmp_path / "a.mp3").exists()

@pytest.mark.parametrize("content_type", ["audio/mpeg", "application/octet-stream", "", "application/x-download"])
def test_download_accepts_conservative_binary_responses(tmp_path, content_type) -> None:
    body = b"ID3" + b"\x00" * 12_000
    context = _FakeRequestContext(_FakeResponse(content_type, body))
    assert _download_body_to_file(context, "https://example", tmp_path / "a.tmp", tmp_path / "a.mp3") is True
```

另增加未知 MIME 下以 BOM/空白开头的 HTML、JSON、XML 嗅探测试，以及失败不覆盖已有最终文件的测试。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_downloader.py -q`

Expected: FAIL，200 且大于 10KB 的错误文档仍被保存。

- [ ] **Step 3: 实现保守校验并接入原子落盘前**

```python
def _audio_response_error(content_type: str, body: bytes) -> str | None:
    mime = content_type.partition(";")[0].strip().lower()
    if mime == "text/html" or mime in {"application/json", "application/problem+json"}:
        return f"响应类型为 {mime}"
    if mime in {"application/xml", "text/xml"} or mime.endswith("+xml"):
        return f"响应类型为 {mime}"

    prefix = body[:512].lstrip(b"\xef\xbb\xbf\x00\t\r\n ").lower()
    if prefix.startswith((b"<!doctype html", b"<html")):
        return "响应内容为 HTML"
    if prefix.startswith((b"{", b"[")):
        return "响应内容为 JSON"
    if prefix.startswith(b"<?xml"):
        return "响应内容为 XML"
    return None
```

在长度检查后、打开临时文件前读取 `resp.headers.get("content-type", "")` 并拒绝异常响应；清理 `.tmp`，记录原因，不调用 `os.replace()`。

- [ ] **Step 4: 运行下载器测试确认通过**

Run: `pytest tests/test_downloader.py -q`

Expected: PASS。

- [ ] **Step 5: 提交音频响应校验**

```powershell
git add music_downloader/infrastructure/downloader.py tests/test_downloader.py
git commit -m "fix: 拒绝伪装成音频的错误响应"
```

### Task 4: 收敛 GUI 下载任务的异常终态

**Files:**
- Modify: `music_downloader/gui/bridge.py`
- Test: `tests/test_gui_bridge.py`

**Interfaces:**
- Produces: `_run_download()` 对每个任务恰好一次 `complete`，并在 `finally` 中移除 `_tasks[task_id]`。
- Preserves: 取消时不把尚未处理的歌曲改成失败；未预期异常时把未产生终态的歌曲标为失败。

- [ ] **Step 1: 写异常、取消和目录失败的终态测试**

```python
def test_download_exception_completes_once_and_removes_task(tmp_path, monkeypatch) -> None:
    events = []
    bridge = MusicBridge(on_progress=events.append)
    bridge._session = _RaisingSession(RuntimeError("boom"))
    task = _download_task(tmp_path, songs=2)
    bridge._tasks[task.task_id] = task

    bridge._run_download(task)

    assert [event["type"] for event in events].count("complete") == 1
    assert events[-1] == {"type": "complete", "task_id": task.task_id, "success": 0, "fail": 2, "skip": 0}
    assert task.task_id not in bridge._tasks
```

再覆盖：正常、取消、目标目录创建失败均恰好一次 complete；异常后已成功歌曲不改写，只将当前及剩余歌曲发出 `song_done/fail`。

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_gui_bridge.py -k "download and (exception or complete or cancel or directory)" -q`

Expected: FAIL，异常路径缺少 complete 且任务仍在 `_tasks`。

- [ ] **Step 3: 实现单一完成出口**

```python
def _emit_download_complete(self, task: DownloadTask) -> None:
    self._emit_progress({
        "type": "complete",
        "task_id": task.task_id,
        "success": task.success,
        "fail": task.fail,
        "skip": task.skip,
    })


def _fail_unfinished_songs(
    self,
    task: DownloadTask,
    start_index: int,
    target_dir: str,
    reason: str,
) -> None:
    total = len(task.songs)
    for index in range(start_index, total):
        song = task.songs[index]
        try:
            gui_index = int(song.get("_gui_index", index))
        except (TypeError, ValueError):
            gui_index = index
        task.fail += 1
        self._emit_progress({
            "type": "song_done",
            "task_id": task.task_id,
            "index": gui_index,
            "result": "fail",
            "reason": reason,
            "path": build_output_path(target_dir, song, task.bitrate),
            "current": index + 1,
            "total": total,
        })
```

将现有目录创建和逐首循环完整放入一个 `try`，在每个 `song_done` 后执行 `next_index = idx + 1`。目标目录失败时调用 `_fail_unfinished_songs(task, 0, target_dir, "无法创建下载目录")`；未预期异常时调用 `_fail_unfinished_songs(task, next_index, target_dir, "下载任务异常，请查看日志")`。最外层 `finally` 固定执行 `_emit_download_complete(task)` 和 `self._tasks.pop(task.task_id, None)`。取消分支只记录 warning 并 `break`，不调用失败助手。删除现有的两个提前 `complete/pop/return` 分支和函数末尾重复的 `complete/pop`。

- [ ] **Step 4: 运行 GUI bridge 全部测试确认通过**

Run: `pytest tests/test_gui_bridge.py -q`

Expected: PASS。

- [ ] **Step 5: 提交下载任务生命周期修复**

```powershell
git add music_downloader/gui/bridge.py tests/test_gui_bridge.py
git commit -m "fix: 保证 GUI 下载任务完整收尾"
```

### Task 5: 让 GUI 消费音源目录并提供可见搜索反馈

**Files:**
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `tests/test_gui_static.py`

**Interfaces:**
- Consumes: `options.sources: OptionItem[]`，来自 Task 1。
- Produces: `SearchBar.feedback: string`、`ResultList.sourceOptions: OptionItem[]`、`ResultList.searchAnnouncement: string`。

- [ ] **Step 1: 写前端源码契约失败测试**

```javascript
test("search feedback and source labels come from shared state", async () => {
  const app = await source("App.svelte");
  const search = await source("lib/components/SearchBar.svelte");
  const results = await source("lib/components/ResultList.svelte");

  assert.match(app, /let searchFeedback = \$state\(""\)/);
  assert.match(app, /searchAnnouncement=/);
  assert.match(app, /sourceOptions=\{options\.sources\}/);
  assert.match(search, /id="searchFeedback"/);
  assert.match(search, /aria-invalid=\{Boolean\(feedback\)\}/);
  assert.match(results, /aria-live="polite"/);
  assert.match(results, /sourceOptions/);
  assert.doesNotMatch(results, /netease:\s*"网易云音乐"/);
})
```

同步修改 Python 静态测试，删除“ResultList 必须硬编码酷我”等旧断言，改为断言 `options.sources` 被传入且没有本地 labels map。

- [ ] **Step 2: 运行前端测试确认失败**

Run: `node --test music_downloader/gui/frontend/tests/*.test.mjs`

Run: `pytest tests/test_gui_static.py -q`

Expected: FAIL，尚无可见反馈，ResultList 仍维护硬编码映射。

- [ ] **Step 3: 实现搜索状态与后端驱动的音源映射**

```typescript
let searchFeedback = $state("");
let searchAnnouncement = $state("");

async function search() {
  const query = keyword.trim();
  if (!query) {
    searchFeedback = "请输入搜索关键词";
    searchAnnouncement = searchFeedback;
    return;
  }
  searchFeedback = "";
  searchAnnouncement = "正在搜索";
  searching = true;
  try {
    const results = await api.search(query, config.source, config.search_type, config.number);
    songs = results;
    searchAnnouncement = results.length > 0
      ? `搜索完成，共找到 ${results.length} 首歌曲`
      : "搜索完成，未找到歌曲";
  } catch (error) {
    searchFeedback = "搜索失败，请稍后重试或查看运行日志";
    searchAnnouncement = "搜索失败";
    addLog(`搜索失败: ${errorMessage(error)}`, "error");
  } finally {
    searching = false;
  }
}
```

`SearchBar` 在输入框下显示 `feedback`，设置 `aria-describedby="searchFeedback"` 和 `aria-invalid`；输入改变时清除旧反馈。`ResultList` 通过 `$derived(new Map(sourceOptions.map((option) => [option.value, option.label])))` 解析展示名，未知值回退原值或破折号，并放置一个 `role="status" aria-live="polite" aria-atomic="true"` 的屏幕阅读器状态节点。删除 SearchBar 原有的重复 searching live region。

- [ ] **Step 4: 运行前端测试和类型检查确认通过**

Run: `node --test music_downloader/gui/frontend/tests/*.test.mjs`

Run: `pytest tests/test_gui_static.py -q`

Run: `npm run check --prefix music_downloader/gui/frontend`

Expected: 全部 PASS，Svelte 报告 0 errors/0 warnings。

- [ ] **Step 5: 提交 GUI 音源与反馈改动**

```powershell
git add music_downloader/gui/frontend/src/App.svelte music_downloader/gui/frontend/src/lib/components/SearchBar.svelte music_downloader/gui/frontend/src/lib/components/ResultList.svelte music_downloader/gui/frontend/tests/workbench.test.mjs tests/test_gui_static.py
git commit -m "fix: 完善 GUI 搜索反馈与音源展示"
```

### Task 6: 更新文档、重建静态产物并完整验证

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `music_downloader/gui/static/index.html`
- Modify/Create/Delete: `music_downloader/gui/static/assets/*`（仅 Vite 生成）
- Test: `tests/test_gui_documentation.py`（仅在现有文档契约需要同步时修改）

**Interfaces:**
- Consumes: 前五个任务的最终行为。
- Produces: 与源码一致的用户文档、协作约定和静态 GUI。

- [ ] **Step 1: 写文档契约并更新 README/AGENTS**

README 增加 13 个音源的 `API 值 / 展示名` 表，明确 `kugou / 酷狗音乐` 支持普通搜索但上游不保证专辑搜索；说明 CLI 参数仍传原始 ID。AGENTS 将“新增音乐源”改为：只修改 `domain/enums.py` 的 `Source`，`VALID_SOURCES`、CLI 和 GUI 选项自动派生，并补充保守音频响应校验约束。

- [ ] **Step 2: 运行文档与全量快速测试**

Run: `pytest tests/test_gui_documentation.py -q`

Run: `pytest -q`

Expected: PASS。

- [ ] **Step 3: 重建 GUI 静态产物**

Run: `npm run build --prefix music_downloader/gui/frontend`

Expected: `svelte-check found 0 errors and 0 warnings`，Vite 成功输出 `music_downloader/gui/static/`。

- [ ] **Step 4: 运行项目规定的静态与编译验证**

Run: `ruff check .`

Run: `ruff format --check .`

Run: `mypy music_downloader`

Run: `python -m py_compile music_download.py`

Run: `node --test music_downloader/gui/frontend/tests/*.test.mjs`

Run: `pytest -q`

Expected: 所有命令退出码 0。

- [ ] **Step 5: 运行环境与真实搜索验证**

Run: `python music_download.py --check-env`

Expected: Python、依赖和 Chrome 检查通过；网络检查结果如实记录。

Run: `python music_download.py --search-only --source netease --keyword Beyond --number 1 --format list`

Run: `python music_download.py --search-only --source kugou --keyword 周杰伦 --number 1 --format list`

Expected: 上游可用时两次搜索均正常返回并显示“网易云音乐”或“酷狗音乐”；若上游临时拒绝请求，记录 HTTP/验证证据，不伪造成功。

- [ ] **Step 6: 使用代码检查 skill 做最终复核**

使用 `superpowers:verification-before-completion` 核对所有验证输出，再使用 `superpowers:requesting-code-review` 检查需求覆盖、回归风险、重复音源目录和测试缺口。修复发现的问题后重新执行受影响测试。

- [ ] **Step 7: 提交文档和生成产物**

```powershell
git add README.md AGENTS.md music_downloader/gui/static tests/test_gui_documentation.py
git commit -m "docs: 更新音源目录与可靠性说明"
```

- [ ] **Step 8: 检查最终工作区**

Run: `git status --short`

Expected: 无未提交的本次改动；用户原有无关改动如存在则保持不动并单独说明。
