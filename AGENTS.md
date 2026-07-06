# AGENTS.md

> 面向协作者与 AI 编码助手。面向终端用户的文档见 [README.md](./README.md)，请先阅读它了解项目使用方式。

## 项目概述

这是一个音乐搜索下载工具，数据来源为 `music.gdstudio.org`。项目同时提供：

- 桌面 GUI：pywebview 加载 Vite/Svelte 构建出的静态资源。
- CLI：Typer 公开入口，和 GUI 同级放在 `music_downloader/cli/`。
- 单一打包入口：`music_download.py`，生成的 exe 同时支持 GUI 和 CLI。

底层通过 Playwright 启动系统已安装的 Google Chrome，访问站点并调用 API 搜索、下载音频文件，再使用 `mutagen` 尽力写入 MP3/FLAC 元数据。

## 技术栈

- **语言**：Python 3.10+
- **运行依赖**：`playwright>=1.45`、`mutagen>=1.47`、`rich>=13`、`typer>=0.12`、`pydantic>=2.7`、`pywebview>=5.0`
- **开发依赖**：`ruff>=0.5`、`mypy>=1.10`、`pytest>=8.2`
- **构建依赖**（见 `requirements-build.txt`）：`nuitka>=2.5`、`ordered-set>=4.1`、`zstandard>=0.23`
- **浏览器要求**：系统已安装 Google Chrome，代码使用 `channel="chrome"`

## 项目结构

```text
music_download.py                         # 单一入口：源码运行和 exe 打包都使用它
music_downloader/__main__.py              # python -m music_downloader 入口
music_downloader/cli/app.py               # Typer CLI 公开入口
music_downloader/cli/workflow.py          # CLI 搜索/下载/交互编排
music_downloader/cli/display.py           # CLI 输出
music_downloader/cli/models.py            # CLI 运行选项
music_downloader/cli/selection.py         # CLI 选择解析
music_downloader/domain/enums.py          # Source/SearchType/Bitrate/DownloadStatus 等枚举
music_downloader/domain/models.py         # Song/SearchOptions/DownloadOptions 等模型
music_downloader/domain/formatting.py     # 纯格式化工具
music_downloader/services/search.py       # CLI 和 GUI 共用搜索、去重、归一化
music_downloader/infrastructure/gdstudio.py    # 上游 API 客户端
music_downloader/infrastructure/environment.py # 环境检查
music_downloader/infrastructure/files.py       # 文件命名、搜索结果归一化
music_downloader/infrastructure/downloader.py  # 下载、重试、临时文件、元数据附加
music_downloader/infrastructure/tags.py        # MP3/FLAC 标签写入
music_downloader/infrastructure/encoding.py    # 上游 API 编码
music_downloader/gui/                  # pywebview GUI
music_downloader/gui/static/           # GUI 静态资源
music_downloader/core/config.py        # 共享常量、默认值、支持平台
music_downloader/core/console.py       # rich/plain console 输出
tests/                                 # pytest 测试
scripts/build_exe.ps1                  # Windows exe 构建脚本
```

## 核心架构

### API 交互流程

1. 启动 Playwright 浏览器，优先无头模式访问 `music.gdstudio.org`。
2. 检查 `cf_clearance` cookie，失败后尝试打开可见 Chrome 窗口。
3. 从页面提取 `mkPlayer.version`，仅用于日志展示，不再参与签名。
4. 通过 POST 调用 `/api.php`，签名由 `compute_signature` 生成。
5. 签名算法通过 `page.evaluate` 调用页面自身的 `crc32(search_id)`，确保与站点当前逻辑保持一致。
6. `get_play_url` / `get_lyric` / `get_pic_url` 都走 `fetch_with_cf_retry` 共享的“签名 + Cloudflare 重试”逻辑。

### 分层约定

- `domain/` 放 Pydantic 模型、枚举和业务异常，不依赖 Playwright、pywebview 或 mutagen。
- `services/` 放 CLI 和 GUI 共用的搜索、去重和归一化逻辑，优先使用 `Song`、`SearchOptions`。
- `infrastructure/` 放文件系统、上游 API、环境检查、下载、元数据标签等外部集成。
- `cli/` 放 Typer CLI、交互命令解析和 CLI 搜索下载工作流，与 `gui/` 同级。
- `gui/` 保持 pywebview 桌面应用形态，前端源码使用 Vite/Svelte，构建产物输出到 `music_downloader/gui/static/`。

### Chrome profile 隔离

- 默认通过 `launch_persistent_context` 启动，把 user data 放在项目根目录 `.chrome-profile/`，与系统 Chrome profile 隔离。
- `cf_clearance` 跨 profile 失效属预期副作用。
- 如果用户主动指定 `--user-data-dir`，CLI 会透传，并打印当前目录位置。

### 下载与成功语义

- 默认下载根目录是项目根目录的 `downloads/`。
- 重复判断只看最终目标文件是否已经存在。
- 音频文件落盘成功即可认定单曲下载成功。
- 元数据、歌词或封面处理失败只记录 warning，不删除已下载音频，不把歌曲判为失败。
- 不要重新引入“写入 ID3/FLAC 失败就删除音频文件”的逻辑。

## 常见修改场景

- **新增音乐源**：修改 `music_downloader/core/config.py` 中的 `VALID_SOURCES`，并同步 `domain/enums.py` 的 `Source`。
- **修改默认设置**：调整 `DEFAULT_KEYWORD`、`DEFAULT_SOURCE`、`DEFAULT_NUMBER`、`DEFAULT_BITRATE`。
- **调整搜索逻辑**：优先修改 `music_downloader/services/search.py` 和 `music_downloader/infrastructure/gdstudio.py`。
- **调整下载行为**：优先修改 `music_downloader/infrastructure/downloader.py`，保持“文件存在即跳过”和“元数据失败 warning-only”语义。
- **调整文件命名/默认目录**：修改 `music_downloader/infrastructure/files.py`。
- **调整 ID3/FLAC 标签**：修改 `music_downloader/infrastructure/tags.py`。
- **API 签名变更**：修改 `music_downloader/infrastructure/gdstudio.py` 的 `compute_signature`，并更新 README 的 401 排错说明。
- **交互模式命令解析**：见 `music_downloader/cli/interactive.py` 和 `workflow.py`。
- **CLI 参数**：见 `music_downloader/cli/app.py`，所有变更要同步更新 `README.md` 参数表。
- **GUI 功能**：修改 `music_downloader/gui/api.py`、`bridge.py` 和 `gui/static/`；GUI 参数选择不应持久化到用户目录。
- **打包资源**：GUI 静态资源仍在 `music_downloader/gui/static/`，构建脚本需保留 `--include-data-dir=music_downloader/gui/static=music_downloader/gui/static`。

## 约定

- Python 3.10+ 语法；用 PEP 604 `X | None`，避免 `Optional[X]`。
- 业务日志统一走 `music_downloader.core.console.console.print`，不要用 `print` 直出；`gui/app.py` 找不到静态资源时的 stderr 提示除外。
- CLI 输出和文档使用中文。
- 单测不要访问真实音乐站点；端到端功能验证靠 `music_download.py --check-env` 加一次本地真实搜索。
- 下载目录 `downloads/`、Chrome profile `.chrome-profile/`、构建产物 `dist/` 已由 `.gitignore` 忽略。
- 发版前跑：`ruff check .`、`ruff format --check .`、`mypy music_downloader`、`py_compile music_download.py`、`music_download.py --check-env`，再加一次真实搜索。
