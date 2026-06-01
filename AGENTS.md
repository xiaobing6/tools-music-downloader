# AGENTS.md

## 项目概述

这是一个命令行音乐搜索下载工具，数据来源为 `music.gdstudio.org`。通过 Playwright 启动系统已安装的 Google Chrome，访问站点并调用 API 搜索、下载音频文件，再使用 `mutagen` 写入 MP3/FLAC 元数据。

## 技术栈

- **语言**：Python 3.8+
- **运行依赖**：`playwright`、`mutagen`
- **开发依赖**：`pytest`、`ruff`
- **浏览器要求**：系统已安装 Google Chrome，代码使用 `channel="chrome"`

## 项目结构

```text
download.py                 # 兼容旧用法的轻量 CLI 入口
music_downloader/config.py  # 常量、默认值、支持的平台
music_downloader/api.py     # 签名、Cloudflare 检查、API 请求
music_downloader/cli.py     # 参数解析、交互模式、主流程
music_downloader/display.py # 表格、列表、JSON 输出
music_downloader/downloader.py # 下载、重试、临时文件和文件命名
music_downloader/metadata.py   # MP3/FLAC 元数据写入
music_downloader/utils.py      # 通用工具函数
tests/                      # 单元测试
```

## 运行方式

```bash
pip install -r requirements.txt
python download.py -k "关键词"
python download.py -k "Beyond" --search-only
python download.py -k "Beyond" --select
python download.py -k "Beyond" -b flac
python download.py -i
```

## 开发检查

```bash
pip install -r requirements-dev.txt
python download.py -h
python -m pytest
python -m ruff check .
python -m py_compile download.py
```

## 核心架构

### API 交互流程

1. 启动 Playwright 浏览器，优先无头模式访问 `music.gdstudio.org`。
2. 检查 `cf_clearance` cookie，失败后尝试打开可见 Chrome 窗口。
3. 从页面提取 `mkPlayer.version`，用于签名计算。
4. 通过 POST 调用 `/api.php`，签名由 `compute_signature` 生成。
5. 签名算法：`MD5(hostname | 补零版本号 | timestamp[:9] | search_id)[-8:].upper()`。

### 常见修改场景

- **新增音乐源**：修改 `music_downloader/config.py` 中的 `VALID_SOURCES`。
- **修改默认设置**：调整 `DEFAULT_KEYWORD`、`DEFAULT_SOURCE`、`DEFAULT_NUMBER`。
- **调整 ID3/FLAC 标签**：修改 `music_downloader/metadata.py`。
- **修改下载行为**：修改 `music_downloader/downloader.py`。
- **API 签名变更**：修改 `music_downloader/api.py` 中的 `compute_signature`。

## 约定

- 保持 `python download.py ...` 入口兼容。
- CLI 输出和文档使用中文。
- 自动化测试不要访问真实音乐站点，使用 fake page/context 覆盖逻辑。
- 下载目录 `downloads/` 已由 `.gitignore` 忽略。
