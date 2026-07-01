# Enhanced Core and GUI Refactor Design

## 背景

`tools-music-downloader` 目前同时提供 CLI 和 pywebview 桌面 GUI。CLI 路径功能相对完整，GUI 已具备基本搜索和下载能力，但浏览器会话、搜索、下载、结果去重、进度状态等编排逻辑在 CLI 和 GUI 之间存在重复。底层数据也大量使用 `dict[str, Any]`，导致类型边界不清晰，后续维护和修复 bug 时容易在两条入口之间产生行为差异。

本次重构选择增强路线：允许大幅调整项目结构，引入真正有价值的工具，但保留现有 CLI 和 GUI 的功能形式，用户使用体验应尽量与之前相似。GUI 继续作为 pywebview 桌面应用，不改成本地 Web 服务，不引入前端构建工具。

## 目标

- 抽出 CLI 和 GUI 共用的核心业务层，避免两套入口重复维护搜索、下载和浏览器流程。
- 引入 Pydantic 建模搜索参数、下载参数、歌曲对象、下载结果和 GUI API 入参出参。
- 引入 Typer 改善 CLI 参数定义、帮助文本和参数校验，同时保持现有命令行参数兼容。
- 引入 pytest，为重构提供不依赖真实音乐站点的单元测试保护网。
- 增强 GUI 功能和状态反馈，使 GUI 在搜索、下载进度、失败原因、失败项重试和环境诊断方面接近 CLI 的完整度。
- 调整下载成功语义：只要音频文件成功落盘，就认定该歌曲下载成功；歌词、封面、ID3 或 FLAC 元数据失败只记录警告。

## 非目标

- 不引入 FastAPI 或其他本地 HTTP 服务。
- 不引入 React、Vue、Vite 或其他前端构建工具。
- 不实现持久化下载数据库、下载历史索引、hash 去重或断点续传。
- 不把真实音乐站点访问写入 CI 或单元测试。
- 不改变 `music_download.py`、`python -m music_downloader`、`--gui` 等主要入口的使用方式。

## 用户可见行为

### CLI

- 保留现有参数语义，包括关键词、来源、数量、搜索类型、输出格式、音质、仅搜索、选择下载、歌词封面开关、交互模式、环境检查和自定义 Chrome profile。
- Typer 迁移后，原有短参数和长参数继续可用。
- 默认下载目录仍为项目根目录下的 `downloads/`。
- 已存在目标文件时直接跳过，逻辑只看最终文件路径是否存在。
- 元数据、歌词或封面处理失败不会导致已下载音频被删除，也不会把歌曲判为失败。

### GUI

- GUI 仍是 pywebview 桌面窗口，继续加载静态 HTML/CSS/JS。
- 每次启动 GUI 都使用默认参数，不保存来源、搜索类型、数量、音质、歌词开关、封面开关和输出目录等用户选择。
- 用户可在本次运行中临时修改参数，关闭后不持久化。
- GUI 默认下载目录与 CLI 一致，使用项目根目录下的 `downloads/`。
- 下载重复判断与 CLI 一致，只看目标文件是否存在。
- GUI 只保留本次运行内的任务结果展示，不实现持久化下载历史。真正的历史就是 `downloads/` 目录中的文件。
- GUI 需要显示每首歌的下载状态：等待、下载中、成功、跳过、失败、取消。
- GUI 需要显示单曲失败原因，并支持对失败项再次下载。

## 建议项目结构

```text
music_downloader/
  domain/
    models.py          # Song、SearchOptions、DownloadOptions、DownloadResult 等 Pydantic 模型
    enums.py           # Source、Bitrate、SearchType、OutputFormat、DownloadStatus
    errors.py          # 领域错误和错误分类
  services/
    search.py          # SearchService，负责搜索、分页、去重和模型转换
    download.py        # DownloadService，负责单曲和批量下载编排
    workflow.py        # CLI/GUI 共用的应用级工作流
  infrastructure/
    browser.py         # Playwright 持久化 context、Cloudflare 验证、页面生命周期
    gdstudio.py        # music.gdstudio.org API 客户端和签名调用
    files.py           # 文件名、路径、临时文件、重复判断
    metadata.py        # 元数据写入适配，失败返回 warning
    environment.py     # Python、依赖、Chrome 检查
  adapters/
    cli/
      app.py           # Typer 应用和主命令
      interactive.py   # 交互模式命令解析和循环
      display.py       # CLI 表格、列表、JSON 输出
    gui/
      app.py           # pywebview 窗口入口
      api.py           # 暴露给 JS 的 API
      bridge.py        # Playwright 线程和 GUI 任务桥接
      static/          # 现有 HTML/CSS/JS
  presentation/
    events.py          # LogEvent、ProgressEvent、DownloadEvent
    console.py         # rich console 和纯文本回退
```

迁移时可保留薄兼容模块，例如 `music_downloader/cli.py` 委托到 `adapters/cli/app.py`，`music_downloader/downloader.py` 委托到新的 `services.download` 或 `infrastructure.files`。这样外部入口和已有导入路径不会一次性断裂。

## 核心数据模型

- `Song`：规范化搜索结果字段，包含 `id`、`url_id`、`pic_id`、`lyric_id`、`name`、`artist`、`album`、`duration`、`source`、`has_hires`。
- `SearchOptions`：关键词、来源、搜索类型、数量、输出格式。
- `DownloadOptions`：来源、音质、输出根目录、是否下载歌词、是否下载封面、目标分组目录。
- `DownloadResult`：歌曲、状态、目标路径、失败原因、警告列表、文件大小。
- `AppSettings`：应用默认值。GUI 启动时读取默认值，不把用户临时选择写入磁盘。
- `EnvironmentCheck`：环境检查结果，用于 CLI 表格和 GUI 诊断面板。

Pydantic 用于边界输入校验和模型转换，内部服务尽量使用明确模型而不是裸字典。和 Playwright、mutagen、pywebview 接触的适配层可以保留 `Any`，但不向上泄漏。

## 数据流

```text
CLI 或 GUI 输入
  -> Pydantic options 校验
  -> BrowserSession 确保 Chrome 和 Cloudflare 状态
  -> GdStudioClient 搜索、获取播放链接、歌词、封面
  -> SearchService 分页、去重、转换为 Song
  -> DownloadService 批量编排
  -> FileStore 判断目标文件是否已存在
  -> FileDownloader 下载音频到目标文件
  -> MetadataWriter 尝试写歌词、封面、ID3/FLAC 标签
  -> DownloadResult 反馈给 CLI 或 GUI
```

GUI 的 Playwright 仍运行在专用后台线程，避免 pywebview 多线程调用 sync Playwright 时触发线程切换错误。CLI 可以直接在当前线程使用相同的 `BrowserSession`。

## 下载路径和重复判断

- 默认输出根目录为项目根目录下的 `downloads/`。
- CLI 按关键词建立子目录，保持现有行为。
- GUI 默认也使用 `downloads/`，下载任务需要使用与 CLI 相同的路径和文件名构造函数。
- 文件名格式保持现有规则：`[id] artist - name.ext`，FLAC 使用 `.flac`，其他音质使用 `.mp3`。
- 重复判断只检查最终目标文件是否存在。存在则返回 `skip`。
- 不引入下载数据库、下载历史 JSON、hash 校验或额外索引。

## 错误处理

### 阻断型错误

以下错误会阻止当前搜索或下载任务继续执行：

- Playwright 未安装或 Chrome 无法启动。
- Cloudflare 验证未通过。
- 搜索接口返回 HTTP 401、403、502 或无法解析的响应。
- 浏览器页面无法加载 `music.gdstudio.org`。

CLI 以中文错误提示输出。GUI 通过日志事件和任务状态展示原因。

### 单曲失败

以下错误只影响当前歌曲，不中断整批下载：

- 播放链接为空。
- 下载请求异常或 HTTP 状态失败。
- 下载内容小于最小音频大小阈值。
- 目标文件写入或移动失败。

结果状态为 `fail`，并记录失败原因。GUI 可以用失败结果生成“重试失败项”的候选列表。

### 非阻断警告

以下错误不会改变 `success` 状态：

- 歌词获取失败。
- 封面获取失败。
- ID3 标签写入失败。
- FLAC 标签写入失败。
- mutagen 不可用或无法识别音频元数据。

这些情况只追加到 `DownloadResult.warnings`，CLI 打印 warning，GUI 在日志或单曲详情中展示。

## GUI 增强

GUI 保持当前单窗口工具形态，不改成网页应用。增强重点如下：

- 搜索区：来源、搜索类型、数量、音质、歌词和封面开关集中展示，本次运行内可修改。
- 结果区：显示歌曲名、歌手、专辑、时长、来源、ID 和状态。
- 批量选择：保留全选、取消选择，支持选择失败项重试。
- 下载进度：展示总体进度和每首歌状态，状态来自 `DownloadResult.status`。
- 日志区：显示浏览器启动、Cloudflare、搜索、下载、跳过、失败和 warning。
- 环境诊断：复用核心环境检查，展示 Python、playwright、mutagen、rich、pywebview、Chrome 状态。
- 下载目录：默认指向项目 `downloads/`，提供打开目录入口。本次运行中可临时选择其他目录，但不持久化。

## 依赖调整

运行依赖新增：

- `typer`：CLI 应用定义和帮助文本。
- `pydantic`：边界模型校验和数据转换。

开发依赖新增：

- `pytest`：单元测试。

保留现有依赖：

- `playwright`
- `mutagen`
- `rich`
- `rich-argparse` 可在 Typer 迁移后评估是否删除。
- `pywebview`

## 测试策略

新增 `tests/`，优先覆盖不访问真实音乐站点的逻辑：

- 模型测试：`Song` 从旧 API 字典转换，缺失字段有默认值，音质和来源校验失败时给出清晰错误。
- 路径测试：CLI 和 GUI 使用同一文件名规则，已存在目标文件返回 `skip`。
- 下载语义测试：音频落盘成功但元数据写入失败时返回 `success` 且包含 warning。
- 选择解析测试：保留 `1,3,5-7` 和反向区间处理。
- 服务编排测试：使用 fake `GdStudioClient` 和 fake `FileDownloader` 模拟成功、跳过、失败和重试失败项。
- GUI API 测试：入参校验、默认配置、启动不写用户配置文件。
- 环境检查测试：注入 fake Chrome checker，避免真实启动浏览器。

人工端到端验证仍按项目约定执行：

```bash
python music_download.py --check-env
python music_download.py -k "Beyond" --search-only
```

一次真实下载验证可以在发版前手动执行，不放入 CI 或单元测试。

## 迁移策略

1. 先新增模型、错误类型、路径工具和测试，不改变入口行为。
2. 把下载成功语义改为“文件落盘即成功，元数据失败只 warning”，并用测试固定。
3. 抽出 `GdStudioClient` 和 `BrowserSession`，让 CLI 继续通过兼容层调用。
4. 抽出 `SearchService` 和 `DownloadService`，让 GUI bridge 与 CLI 复用。
5. 迁移 CLI 到 Typer，保持原参数兼容。
6. 改造 GUI API，不保存用户参数选择，默认使用项目 `downloads/`。
7. 更新 README、AGENTS 中涉及结构、依赖、参数和排错的说明。

## 验收标准

- `python music_download.py -h` 和 `python -m music_downloader -h` 可用。
- 现有 CLI 参数和常用命令继续可用。
- `python music_download.py --check-env` 可用。
- GUI 可启动、搜索、选择歌曲、下载、取消、重试失败项、打开下载目录。
- GUI 每次启动加载默认参数，不写入用户参数选择记录。
- CLI 和 GUI 对同一歌曲生成一致的目标文件名和重复判断结果。
- 元数据写入失败不会删除已下载音频文件，结果仍为成功并记录 warning。
- 单元测试覆盖核心模型、路径、下载语义和服务编排。
- `ruff check .`、`ruff format --check .`、`mypy music_downloader`、`py_compile music_download.py` 在开发环境安装依赖后通过。
