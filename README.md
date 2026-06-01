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

- Python 3.8+
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

## 快速开始

```bash
# 搜索并下载默认关键词（Beyond，网易云，320kbps，20 首）
python download.py

# 指定关键词搜索并下载
python download.py -k "周杰伦"

# 搜索并选择要下载的歌曲
python download.py -k "张学友" --select

# 仅搜索，不下载
python download.py -k "邓紫棋" --search-only

# 切换音乐源
python download.py -k "Taylor Swift" -s spotify

# 搜索专辑
python download.py -k "周杰伦" -t album

# 下载 FLAC
python download.py -k "林俊杰" -b flac

# 下载到指定目录
python download.py -k "林俊杰" -o "D:\MyMusic"

# 交互模式
python download.py -i
```

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
| `-i / --interactive` | 交互模式 | - |

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
├── download.py                 # 兼容旧用法的 CLI 入口
├── music_downloader/           # 核心包
│   ├── api.py                  # API 请求、签名、Cloudflare 处理
│   ├── cli.py                  # 参数解析、交互模式、主流程
│   ├── downloader.py           # 下载、重试、临时文件
│   ├── metadata.py             # MP3/FLAC 元数据写入
│   ├── display.py              # 输出格式
│   ├── utils.py                # 通用工具
│   └── config.py               # 常量配置
├── tests/                      # 单元测试
├── requirements.txt            # 运行依赖
├── requirements-dev.txt        # 开发依赖
└── README.md
```

## 开发

```bash
python download.py -h
python -m pytest
python -m ruff check .
python -m py_compile download.py
```

测试不会访问真实音乐站点，避免网络和 Cloudflare 影响结果。

## 注意事项

- 下载的歌曲仅供个人学习交流使用，请尊重版权。
- 部分平台（如 Spotify、Tidal）可能需要可访问对应服务的网络环境。
- 如提示缺少 `playwright` 或 `mutagen`，请运行 `pip install -r requirements.txt`。
- 如提示无法启动 Google Chrome，请确认系统已安装 Chrome。
- 已存在的文件会自动跳过，不会重复下载。

## 常见问题

**Q: 为什么不执行 `playwright install chromium`？**

本项目默认启动系统已安装的 Google Chrome，不使用 Playwright 下载的 Chromium。

**Q: 提示 `Cloudflare 验证未通过` 怎么办？**

程序会先用无头模式尝试，通过不了会打开可见 Chrome 窗口。请在窗口中完成验证后继续。

**Q: 如何查看所有参数？**

```bash
python download.py -h
```
