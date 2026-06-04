# tools-music-downloader

命令行音乐搜索下载工具，支持从多个主流音乐平台搜索并下载歌曲，自动嵌入封面图和歌词。

## 功能特性

- **多平台支持**：网易云、QQ 音乐、酷我、咪咕、YouTube Music、Spotify、Tidal、Qobuz、Deezer 等 12 个音乐源
- **自动元数据**：下载完成后写入标题、艺术家、专辑、曲目编号、封面图、歌词等元数据
- **灵活搜索**：支持单曲、专辑、歌单搜索，可指定结果数量并自动分页
- **音质选择**：支持 128kbps / 192kbps / 320kbps / FLAC；`flac` 会保存为 `.flac`
- **交互模式**：浏览器保持运行，可反复搜索下载，无需重复启动
- **Cloudflare 处理**：检测验证状态，失效时自动刷新；无头模式失败后会尝试打开可见 Chrome 窗口

## 环境要求

- Python 3.9+
- 已安装 Google Chrome 浏览器
- Windows / macOS / Linux

> 代码默认通过 Playwright 启动系统里的 Google Chrome：`channel="chrome"`。不要求额外安装 Playwright 自带 Chromium。

## 安装

```bash
git clone https://github.com/xiaobing6/tools-music-downloader.git
cd tools-music-downloader

pip install -r requirements.txt
```

如需运行测试和静态检查：

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` 会同时安装运行依赖和开发工具。

## 快速开始

```bash
# 搜索并下载默认关键词（Beyond，网易云，320kbps，20 首）
python music_download.py

# 指定关键词搜索并下载
python music_download.py -k "周杰伦"

# 搜索并选择要下载的歌曲
python music_download.py -k "张学友" --select

# 仅搜索，不下载
python music_download.py -k "邓紫棋" --search-only

# 切换音乐源
python music_download.py -k "Taylor Swift" -s spotify

# 搜索专辑
python music_download.py -k "周杰伦" -t album

# 下载 FLAC
python music_download.py -k "林俊杰" -b flac

# 下载到指定目录
python music_download.py -k "林俊杰" -o "D:\MyMusic"

# 交互模式
python music_download.py -i

# 检查本地运行环境
python music_download.py --check-env

# 也可以使用模块入口
python -m music_downloader -h
```

> **下载目录建议**：默认输出在仓库根的 `downloads/`，已加入 `.gitignore`。为避免被 IDE 索引或被同步盘误抓，**建议把 `-o` 指到仓库外**，例如 `D:\MyMusic`。

## 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `-k / --keyword` | 搜索关键词 | `Beyond` |
| `-s / --source` | 音乐源 | `netease` |
| `-n / --number` | 结果数量，必须是正整数 | `20` |
| `-t / --type` | 搜索类型：`song` / `album` / `playlist` | `song` |
| `-o / --output` | 下载目录 | `./downloads/` |
| `-f / --format` | 输出格式：`table` / `list` / `json` | `table` |
| `-b / --bitrate` | 音质：`128` / `192` / `320` / `flac` | `320` |
| `--search-only` | 仅搜索，不下载 | - |
| `--select` | 搜索后手动选择要下载的歌曲 | - |
| `--no-lyric` | 不下载歌词 | - |
| `--no-cover` | 不嵌入封面图 | - |
| `--check-env` | 检查依赖和系统 Chrome，不访问音乐站点 | - |
| `-i / --interactive` | 交互模式 | - |
| `--user-data-dir` | 自定义 Chrome 用户数据目录；默认在脚本同级 `.chrome-profile/`，与系统 Chrome 隔离 | - |
| `--no-isolated-profile` | 不创建项目内 profile（会污染系统 Chrome profile，仅排错时使用） | - |
| `--mk-version` | 手动指定 mkPlayer 版本号，覆盖 `FALLBACK_VERSION`（默认 `2026.5.10`） | - |

## 支持的音乐源

| 值 | 平台 |
|---|---|
| `netease` | 网易云音乐 |
| `migu` | 咪咕音乐 |
| `kuwo` | 酷我音乐 |
| `ytmusic` | YouTube Music |
| `spotify` | Spotify |
| `tidal` | Tidal |
| `qobuz` | Qobuz |
| `deezer` | Deezer |
| `tencent` | QQ 音乐 |
| `ximalaya` | 喜马拉雅 |
| `joox` | Joox |
| `apple` | Apple Music |

## 文件结构

```text
.
├── music_download.py           # CLI 入口
├── music_downloader/           # 核心包
│   ├── api.py                  # API 请求、签名、Cloudflare 处理
│   ├── cli.py                  # 参数解析、交互模式、主流程
│   ├── env.py                  # 本地环境检查
│   ├── downloader.py           # 下载、重试、临时文件
│   ├── metadata.py             # MP3/FLAC 元数据写入
│   ├── display.py              # 输出格式
│   ├── console.py              # rich 终端输出
│   ├── __main__.py             # python -m music_downloader 入口
│   ├── utils.py                # 通用工具
│   └── config.py               # 常量配置
├── tests/                      # 单元测试
├── .github/workflows/ci.yml    # GitHub Actions 检查
├── .gitattributes              # 换行规则
├── pyproject.toml              # pytest/ruff/mypy 配置
├── requirements.txt            # 运行依赖
├── requirements-dev.txt        # 开发依赖
└── README.md
```

## 开发

```bash
python music_download.py -h
python -m music_downloader -h
python music_download.py --check-env
python -m pytest
python -m ruff check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

测试不会访问真实音乐站点，避免网络和 Cloudflare 影响结果。

## 打包 EXE

本项目推荐使用 Nuitka 打包 Windows 可执行文件。打包后的 exe 会包含 Python 运行时和 Python 依赖，但仍然使用用户系统里已安装的 Google Chrome，不会把 Playwright 浏览器一起打包进去。

安装构建依赖：

```bash
pip install -r requirements-build.txt
```

默认构建单文件 exe，后续分发时只需要复制这个文件：

```powershell
.\scripts\build_exe.ps1
```

单文件产物：

```text
dist/music_download.exe
```

如需先用目录模式排查依赖问题：

```powershell
.\scripts\build_exe.ps1 -Mode standalone
```

输出目录：

```text
dist/
```

目录模式产物需要整个目录一起复制，仅用于排查：

```text
dist/music_download.dist/music_download.exe
```

打包后建议先检查环境：

```powershell
.\dist\music_download.exe --check-env
# 或目录模式：
.\dist\music_download.dist\music_download.exe --check-env
```

如果目标机器缺少 Visual C++ 运行库，请安装 Microsoft Visual C++ Redistributable for Visual Studio 2015-2022。Nuitka 会尽量打包可用运行库，但在部分构建环境下仍可能需要目标机器预装。

## 注意事项

- 下载的歌曲仅供个人学习交流使用，请尊重版权。
- 部分平台（如 Spotify、Tidal）可能需要可访问对应服务的网络环境。
- 如提示缺少 `playwright`、`mutagen` 或 `rich`，请运行 `pip install -r requirements.txt`。
- 如提示无法启动 Google Chrome，请确认系统已安装 Chrome。
- 已存在的文件会自动跳过，不会重复下载。

## 常见问题

**Q: 为什么不执行 `playwright install chromium`？**

本项目默认启动系统已安装的 Google Chrome，不使用 Playwright 下载的 Chromium。

**Q: 提示 `Cloudflare 验证未通过` 怎么办？**

程序会先用无头模式尝试，通过不了会打开可见 Chrome 窗口。请在窗口中完成验证后继续。

**Q: 提示 HTTP 401 (签名验证失败) 怎么办？**

- 站点更新了 `mkPlayer.version` 而代码里 `FALLBACK_VERSION` 没跟上 → 升级到最新版；如果最新版也不可用，运行 `python music_download.py -k "x" --mk-version 2026.x.y` 手动指定版本号。
- 站点**整体**更换了签名算法 → 请到 [issues](https://github.com/xiaobing6/tools-music-downloader/issues) 反馈。

**Q: 为什么 Cloudflare 每次启动都要重新过？**

`cf_clearance` 与 IP、UA、TLS 指纹绑定。本工具使用隔离的 `.chrome-profile/` 目录，与系统 Chrome profile 不共享 cookie；只要换 IP、换 UA 或换 profile，就要重新过验证，这是 Cloudflare 的预期行为。

**Q: 为什么用隔离的 `.chrome-profile/`？**

避免读取你已登录的系统 Chrome profile（避免 session 污染和 SingletonLock 冲突）。如果你**确实**要复用系统 profile 的状态，用 `--user-data-dir "%LOCALAPPDATA%\Google\Chrome\User Data"`，但要清楚这会让工具读到你的 Google 账号登录态。

**Q: 跨盘移动文件失败 (`os.replace` 报错)？**

把 `-o` 输出目录指到和系统盘（一般是 C 盘）相同盘符下。Windows 上 `os.replace` 跨盘符不支持。

**Q: 如何查看所有参数？**

```bash
python music_download.py -h
```
