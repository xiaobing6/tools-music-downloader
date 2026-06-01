# AGENTS.md

## 项目概述

这是一个命令行音乐搜索下载工具，数据来源为 `music.gdstudio.org`。通过 Playwright 启动系统已安装的 Google Chrome，访问站点并调用 API 搜索、下载音频文件，再使用 `mutagen` 写入 MP3/FLAC 元数据。

## 技术栈

- **语言**：Python 3.8+
- **运行依赖**：`playwright`、`mutagen`、`rich`
- **开发依赖**：`pytest`、`ruff`、`mypy<2`
- **构建依赖**：`nuitka`、`ordered-set`、`zstandard`
- **浏览器要求**：系统已安装 Google Chrome，代码使用 `channel="chrome"`

## 项目结构

```text
music_download.py           # 轻量 CLI 入口
music_downloader/config.py  # 常量、默认值、支持的平台
music_downloader/api.py     # 签名、Cloudflare 检查、API 请求
music_downloader/cli.py     # 参数解析、交互模式、主流程
music_downloader/env.py     # 本地环境检查
music_downloader/display.py # 表格、列表、JSON 输出
music_downloader/console.py # rich 终端输出
music_downloader/__main__.py # python -m music_downloader 入口
music_downloader/downloader.py # 下载、重试、临时文件和文件命名
music_downloader/metadata.py   # MP3/FLAC 元数据写入
music_downloader/utils.py      # 通用工具函数
tests/                      # 单元测试
.github/workflows/ci.yml     # GitHub Actions 检查
.gitattributes               # 换行规则
pyproject.toml               # pytest/ruff/mypy 配置
requirements-build.txt       # Nuitka 构建依赖
scripts/build_exe.ps1        # Windows exe 构建脚本
```

## 运行方式

```bash
pip install -r requirements.txt
python music_download.py -k "关键词"
python music_download.py -k "Beyond" --search-only
python music_download.py -k "Beyond" --select
python music_download.py -k "Beyond" -b flac
python music_download.py --check-env
python -m music_downloader -h
python music_download.py -i
```

## 开发检查

```bash
pip install -r requirements-dev.txt
python music_download.py -h
python -m music_downloader -h
python music_download.py --check-env
python -m pytest
python -m ruff check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

## EXE 构建

```powershell
pip install -r requirements-build.txt
.\scripts\build_exe.ps1
.\dist\music_download.exe --check-env
```

默认使用 Nuitka onefile 模式，产物为 `dist/music_download.exe`，分发时只复制这个 exe 即可。脚本通过 `--playwright-include-browser=none` 排除 Playwright 浏览器。遇到依赖排查问题时，先运行 standalone 模式，目录模式产物需要整个 `dist/music_download.dist/` 一起复制：

```powershell
.\scripts\build_exe.ps1 -Mode standalone
.\dist\music_download.dist\music_download.exe --check-env
```

目标机器仍需安装 Google Chrome；如缺少 Visual C++ 运行库，请安装 Microsoft Visual C++ Redistributable for Visual Studio 2015-2022。

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

- 使用 `python music_download.py ...` 作为脚本入口，也支持 `python -m music_downloader ...`。
- CLI 输出和文档使用中文。
- 自动化测试不要访问真实音乐站点，使用 fake page/context 覆盖逻辑。
- 下载目录 `downloads/` 已由 `.gitignore` 忽略。
