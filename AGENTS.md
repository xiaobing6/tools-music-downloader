# AGENTS.md

## 项目概述

这是一个命令行音乐搜索下载工具，数据来源为 `music.gdstudio.org`。通过 Playwright 绕过 Cloudflare 防护，调用站点 API 搜索、下载 MP3 文件，并自动写入完整的元数据（ID3 标签、封面图、歌词）。

## 技术栈

- **语言**：Python 3
- **依赖库**：`playwright`（无头浏览器，用于绕过 Cloudflare 和调用 API）、`mutagen`（MP3 ID3 标签读写）
- **测试框架**：目前未配置

## 项目结构

```
download.py          # 主脚本 — 所有逻辑均在此文件中（搜索、下载、ID3 标签写入、命令行界面）
requirements.txt     # Python 依赖
downloads/           # 下载目录，用于存放 MP3 文件（已加入 .gitignore）
```

## 运行方式

```bash
pip install -r requirements.txt
playwright install chromium
python download.py -k "关键词"              # 搜索并下载（默认：网易云，320kbps，20 条结果）
python download.py -k "Beyond" --search-only # 仅搜索，不下载
python download.py -k "Beyond" --select      # 搜索后选择要下载的歌曲
python download.py -i                        # 交互模式
```

## 核心架构

### API 交互流程

1. 启动 Playwright 浏览器 → 访问 `music.gdstudio.org` → 通过 Cloudflare 验证
2. 从页面提取 `mkPlayer.version`（用于签名计算）
3. 所有 API 调用通过 POST 发送到 `/api.php`，附带的签名由 `compute_signature` 生成
4. 签名算法：`MD5(hostname | 补零版本号 | timestamp[:9] | search_id)[-8:].upper()`

### `download.py` 核心函数

| 函数 | 功能 |
|---|---|
| `compute_signature()` | 生成 API 请求签名 |
| `search_with_pagination()` | 分页搜索歌曲（每页最多 99 条，自动翻页） |
| `get_play_url()` | 获取歌曲的 MP3 播放链接 |
| `get_lyric()` | 获取歌曲歌词 |
| `get_pic_url()` | 获取歌曲封面图链接 |
| `download_song()` | 下载 MP3 + 嵌入 ID3 标签（封面、歌词、元数据） |
| `embed_id3_tags()` | 写入 ID3v2 标签（TIT2、TPE1、TALB、TRCK、APIC、USLT） |
| `interactive_mode()` | 交互式循环，可反复搜索下载 |

### 支持的音乐源

`netease`（网易云）、`migu`（咪咕）、`kuwo`（酷我）、`ytmusic`（YouTube Music）、`tidal`、`qobuz`、`deezer`、`spotify`、`tencent`（QQ音乐）、`ximalaya`（喜马拉雅）、`joox`、`apple`

### 命令行参数

| 参数 | 说明 |
|---|---|
| `-k / --keyword` | 搜索关键词（默认："Beyond"） |
| `-s / --source` | 音乐源（默认："netease"） |
| `-n / --number` | 结果数量（默认：20） |
| `-t / --type` | 搜索类型：song（单曲）/album（专辑）/playlist（歌单） |
| `-o / --output` | 下载目录 |
| `-f / --format` | 输出格式：table（表格）/json/list（列表） |
| `-b / --bitrate` | 音质：128/192/320/flac |
| `--search-only` | 仅搜索，不下载 |
| `--select` | 搜索后选择要下载的歌曲 |
| `--no-lyric` | 不嵌入歌词 |
| `--no-cover` | 不嵌入封面图 |
| `-i / --interactive` | 交互模式 |

## 代码规范

- 单文件架构 — 所有逻辑集中在 `download.py`
- 注释和 CLI 输出均使用中文
- 无外部配置文件，所有常量定义在文件顶部
- 错误处理：HTTP 403 时重试并刷新 Cloudflare；下载失败最多重试 2 次
- 文件名中非法字符（`\/:*?"<>|`）替换为 `_`
- 下载文件命名格式：`[歌曲ID] 歌手 - 歌名.mp3`

## 常见修改场景

- **新增音乐源**：在 `VALID_SOURCES` 列表中添加源名称，API 端路由由服务端处理
- **修改默认设置**：调整 `DEFAULT_KEYWORD`、`DEFAULT_SOURCE`、`DEFAULT_NUMBER` 常量
- **调整 ID3 标签写入**：修改 `embed_id3_tags()` — 当前写入 TIT2、TPE1、TALB、TRCK、APIC、USLT
- **修改下载行为**：修改 `download_song()` — 重试逻辑、代理 URL 规则、临时文件处理
- **API 签名变更**：若站点调整签名算法，更新 `compute_signature()` 中的逻辑
