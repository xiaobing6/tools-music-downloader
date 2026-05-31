# tools-music-downloader

命令行音乐搜索下载工具，支持从多个主流音乐平台搜索并下载歌曲，自动嵌入封面图和歌词。

## 功能特性

- 🎵 **多平台支持**：网易云、QQ音乐、酷我、咪咕、YouTube Music、Spotify、Tidal、Qobuz、Deezer 等 12 个音乐源
- 📄 **自动元数据**：下载完成后自动将歌曲标题、艺术家、专辑、曲目编号、封面图、歌词嵌入 MP3 文件的 ID3v2 标签
- 🔍 **灵活搜索**：支持单曲、专辑、歌单搜索，可指定结果数量（自动分页）
- 🎛️ **音质选择**：支持 128kbps / 192kbps / 320kbps / FLAC
- 🖥️ **交互模式**：浏览器保持运行，可反复搜索下载，无需重复启动
- ☁️ **Cloudflare 处理**：内置 Cloudflare 验证绕过机制，自动处理验证过期

## 环境要求

- Python 3.8+
- Google Chrome 浏览器
- Windows / macOS / Linux

## 安装

```bash
# 克隆项目
git clone https://github.com/xiaobing6/tools-music-downloader.git
cd tools-music-downloader

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（只需执行一次）
playwright install chromium
```

## 快速开始

```bash
# 搜索并下载默认关键词（Beyong，网易云，320kbps，20 首）
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

# 下载到指定目录
python download.py -k "林俊杰" -o "D:\MyMusic"

# 交互模式（反复搜索，无需重启）
python download.py -i
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `-k / --keyword` | 搜索关键词 | "Beyond" |
| `-s / --source` | 音乐源 | "netease" |
| `-n / --number` | 结果数量 | 20 |
| `-t / --type` | 搜索类型：`song` / `album` / `playlist` | song |
| `-o / --output` | 下载目录 | `./downloads/` |
| `-f / --format` | 输出格式：`table` / `list` / `json` | table |
| `-b / --bitrate` | 音质：`128` / `192` / `320` / `flac` | 320 |
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
| `tencent` | QQ音乐 |
| `ximalaya` | 喜马拉雅 |
| `joox` | Joox |
| `apple` | Apple Music |

## 文件结构

```
.
├── download.py          # 主程序
├── requirements.txt     # 依赖列表
├── downloads/           # 下载目录（自动创建，gitignore 已忽略）
└── README.md
```

## 注意事项

- 下载的歌曲仅供个人学习交流使用，请尊重版权
- 部分平台（如 Spotify、Tidal）可能需要科学上网
- 如遇 Cloudflare 验证失败，程序会自动重试；若持续失败请稍后再试
- 已存在的文件会自动跳过，不会重复下载

## 常见问题

**Q: 提示 `Cloudflare 验证未通过` 怎么办？**
程序会自动尝试有头模式（弹出浏览器窗口手动验证），请在打开的浏览器中完成验证后，程序会继续执行。

**Q: 如何查看所有参数？**
```bash
python download.py -h
```
