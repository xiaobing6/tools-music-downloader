# tools-music-downloader

音乐搜索下载工具，数据来源为 `music.gdstudio.org`。项目同时提供桌面 GUI 和 CLI：GUI 适合日常搜索、选择、下载与失败重试，CLI 适合脚本化和批量使用。

## 功能特性

- 支持网易云、QQ 音乐、酷我、咪咕、YouTube Music、Spotify、Tidal、Qobuz、Deezer 等音乐源。
- 支持单曲、专辑、歌单搜索，可指定结果数量并自动分页。
- 支持 `128` / `192` / `320` / `flac` 音质；`flac` 会保存为 `.flac`。
- 下载完成后尽力写入标题、艺术家、专辑、曲目编号、封面和歌词等元数据。
- 元数据、封面或歌词写入失败不会删除已下载音频，也不会把歌曲判为失败。
- 已存在的目标音频文件会直接跳过，重复判断只看最终文件是否存在。
- GUI 每次启动都使用默认参数，不保存来源、搜索类型、数量、音质等用户选择。

## 环境要求

- Python 3.10+
- 系统已安装 Google Chrome
- Windows / macOS / Linux

运行依赖：`playwright`、`mutagen`、`rich`、`typer`、`pydantic`、`pywebview`。

开发依赖：`ruff`、`mypy`、`pytest`。

## 安装

```bash
git clone https://github.com/xiaobing6/tools-music-downloader.git
cd tools-music-downloader
pip install -r requirements.txt
```

开发检查工具：

```bash
pip install -r requirements-dev.txt
```

## GUI 使用

无参数启动默认打开桌面 GUI：

```bash
python music_download.py
```

也可以显式启动 GUI：

```bash
python music_download.py --gui
```

GUI 默认下载根目录为项目目录下的 `downloads/`。中途可以临时修改来源、搜索类型、数量、音质、歌词、封面和下载目录，但下次启动仍恢复默认值。

## CLI 使用

CLI 使用时传入 `-k`、`--check-env`、`-i` 等参数：

```bash
python music_download.py -k "周杰伦"
python music_download.py -k "Beyond" --search-only
python music_download.py -k "Taylor Swift" -s spotify -n 5
python music_download.py -k "林俊杰" -b flac
python music_download.py -k "张学友" --select
python music_download.py -i
python music_download.py --check-env
python -m music_downloader -h
```

CLI 默认下载到 `downloads/<关键词>/`。使用 `-o` 指定目录时，仍会在该目录下按关键词创建子目录。

## CLI 参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `-k / --keyword` | 搜索关键词 | `Beyond` |
| `-s / --source` | 音乐源 | `netease` |
| `-n / --number` | 结果数量，必须是正整数 | `20` |
| `-t / --type` | 搜索类型：`song` / `album` / `playlist` | `song` |
| `-o / --output` | 下载目录 | `./downloads/` |
| `-f / --format` | 输出格式：`table` / `list` / `json` | `table` |
| `-b / --bitrate` | 音质：`128` / `192` / `320` / `flac` | `320` |
| `--search-only` | 只搜索，不下载 | - |
| `--select` | 搜索后手动选择要下载的歌曲 | - |
| `--no-lyric` | 不下载歌词 | - |
| `--no-cover` | 不嵌入封面 | - |
| `--check-env` | 检查依赖和系统 Chrome，不访问音乐站点 | - |
| `-i / --interactive` | 交互模式 | - |
| `--gui` | 启动桌面 GUI | - |
| `--user-data-dir` | 自定义 Chrome 用户数据目录 | `.chrome-profile/` |

## 项目结构

```text
music_download.py                 # 单一入口，源码运行和 exe 打包都使用它
music_downloader/
  __main__.py                     # python -m music_downloader 入口
  core/                           # 共享配置、默认值、rich/plain console 输出
  cli/                            # Typer CLI 入口、命令工作流、选择解析、输出
  domain/                         # Pydantic 模型、枚举、格式化、业务异常
  infrastructure/                 # 文件规则、环境检查、浏览器、GdStudio API、下载、元数据
  services/                       # CLI 和 GUI 共用的搜索/下载服务
  gui/                            # pywebview 桌面 GUI 与静态 HTML/CSS/JS
scripts/build_exe.ps1             # Windows Nuitka 打包脚本
tests/                            # pytest 测试
```

## 打包 EXE

安装构建依赖：

```bash
pip install -r requirements-build.txt
```

生成单文件 exe：

```powershell
.\scripts\build_exe.ps1
```

已安装构建依赖时可跳过安装：

```powershell
.\scripts\build_exe.ps1 -SkipInstall
```

输出文件：

```text
dist/music_download.exe
```

生成的 `music_download.exe` 同时支持 GUI 和 CLI：

```powershell
.\dist\music_download.exe
.\dist\music_download.exe --gui
.\dist\music_download.exe -h
.\dist\music_download.exe --check-env
```

GUI 静态资源会由构建脚本打包进 exe；Chrome 不会被打包，运行时仍使用用户系统已安装的 Google Chrome。

## 开发检查

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
python music_download.py --check-env
```

端到端搜索会访问真实音乐站点，请在本地手动验证，不要写入 CI。

## 常见问题

**为什么不执行 `playwright install chromium`？**

本项目默认通过 Playwright 启动系统已安装的 Google Chrome，即 `channel="chrome"`，不使用 Playwright 下载的 Chromium。

**为什么 Cloudflare 有时需要重新验证？**

`cf_clearance` 与 IP、UA、TLS 指纹和 Chrome profile 相关。工具默认使用项目目录下隔离的 `.chrome-profile/`，不会读取系统 Chrome profile。

**下载成功但没有标签怎么办？**

这说明音频文件已经落盘，但元数据、歌词或封面写入失败。现在这类失败只作为警告处理，不会删除音频文件；再次下载时如果目标文件已存在会跳过。
