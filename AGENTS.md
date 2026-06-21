# AGENTS.md

> 面向协作者与 AI 编码助手。面向终端用户的文档见 [README.md](./README.md)，请先阅读它了解项目的使用方式。

## 项目概述

这是一个命令行音乐搜索下载工具，数据来源为 `music.gdstudio.org`。通过 Playwright 启动系统已安装的 Google Chrome，访问站点并调用 API 搜索、下载音频文件，再使用 `mutagen` 写入 MP3/FLAC 元数据。

## 技术栈

- **语言**：Python 3.10+
- **运行依赖**：`playwright>=1.45`、`mutagen>=1.47`、`rich>=13`
- **开发依赖**：`ruff>=0.5`、`mypy>=1.10`
- **构建依赖**（见 `requirements-build.txt`）：`nuitka>=2.5`、`ordered-set>=4.1`、`zstandard>=0.23`
- **浏览器要求**：系统已安装 Google Chrome，代码使用 `channel="chrome"`

## 项目结构

```text
music_download.py             # 轻量 CLI 入口
music_downloader/__init__.py  # 包标识
music_downloader/config.py    # 常量、默认值、支持的平台
music_downloader/api.py       # 签名、Cloudflare 检查、API 请求
music_downloader/cli.py       # 参数解析、交互模式、主流程
music_downloader/env.py       # 本地环境检查
music_downloader/display.py   # 表格、列表、JSON 输出
music_downloader/console.py   # rich 终端输出
music_downloader/__main__.py  # python -m music_downloader 入口
music_downloader/downloader.py  # 下载、重试、临时文件和文件命名
music_downloader/metadata.py    # MP3/FLAC 元数据写入
music_downloader/models.py      # RunOptions 数据类
music_downloader/utils.py       # 通用工具函数
.gitattributes                # 换行规则
.gitignore                    # 忽略规则
LICENSE                       # MIT 协议
README.md                     # 终端用户文档
pyproject.toml                # 项目元数据 + ruff/mypy 配置
requirements.txt              # 运行依赖
requirements-dev.txt          # 开发依赖（ruff/mypy）
requirements-build.txt        # 构建依赖（Nuitka 等）
scripts/build_exe.ps1         # Windows exe 构建脚本
```

## 核心架构

### API 交互流程

1. 启动 Playwright 浏览器，优先无头模式访问 `music.gdstudio.org`。
2. 检查 `cf_clearance` cookie，失败后尝试打开可见 Chrome 窗口。
3. 从页面提取 `mkPlayer.version`，仅用于日志展示，不再参与签名。
4. 通过 POST 调用 `/api.php`，签名由 `compute_signature` 生成。
5. 签名算法不再在 Python 端复现，而是通过 `page.evaluate` 直接调用页面自身的 `crc32(search_id)` 函数，确保与站点当前逻辑保持一致。
6. `get_play_url`/`get_lyric`/`get_pic_url` 三个 URL 类接口都走 `fetch_with_cf_retry` 共享的"签名 + Cloudflare 重试"逻辑。

### Chrome profile 隔离

- 默认通过 `launch_persistent_context` 启动，把 user data 放在脚本同级的 `.chrome-profile/`，与系统 Chrome profile 完全隔离。
- cf_clearance 跨 profile 失效属预期副作用；如果用户**主动**指定 `--user-data-dir`，CLI 会透传，并打印当前目录位置。

### 常见修改场景

- **新增音乐源**：修改 `music_downloader/config.py` 中的 `VALID_SOURCES`。
- **修改默认设置**：调整 `DEFAULT_KEYWORD`、`DEFAULT_SOURCE`、`DEFAULT_NUMBER`、`DEFAULT_BITRATE`。
- **调整 ID3/FLAC 标签**：修改 `music_downloader/metadata.py`。
- **修改下载行为**：修改 `music_downloader/downloader.py`。注意：metadata 写入失败会触发残缺文件清理并返回 fail，下次运行可重试——不要把"已存在即跳过"逻辑放到 `os.replace` 之前，否则残缺文件会永久卡住。
- **API 签名变更**：签名由页面自身的 `crc32` 函数生成，一般不需要在 Python 端改动。若站点不再暴露 `crc32`，需同步调整 `music_downloader/api.py` 中的 `compute_signature`；并更新 README 的 401 排错指引。
- **交互模式命令解析**：见 [cli.py](./music_downloader/cli.py) 的 `parse_interactive_command`。
- **CLI 参数**：见 `cli.parse_args`，所有变更要同步更新 `README.md` 的参数表。

## 约定

- Python 3.10+ 语法；用 PEP 604 `X | None`，避免 `Optional[X]`。
- 业务日志统一走 `music_downloader.console.console.print`，**不要**再用 `print` 直出。
- CLI 输出和文档使用中文。
- 端到端功能验证靠 `music_download.py --check-env` + 一次真实搜索；不要把对真实音乐站点的访问写进 CI 或单测。
- 下载目录 `downloads/` 与 Chrome profile `.chrome-profile/` 已由 `.gitignore` 忽略。
- 每次发版前跑过 `ruff check .`、`ruff format --check .`、`mypy music_downloader`、`py_compile music_download.py`，再加 `music_download.py --check-env` 和一次端到端搜索（确认 Chrome 能正常启动并拿到签名）。
