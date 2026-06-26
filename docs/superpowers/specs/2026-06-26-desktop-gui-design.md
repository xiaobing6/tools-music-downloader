# 桌面 GUI 设计文档

> 日期：2026-06-26
> 状态：已确认

## 概述

为现有命令行音乐下载工具增加桌面 GUI 界面，最终打包为单个 Windows EXE。GUI 默认启动，命令行参数完全兼容现有 CLI 模式，核心下载逻辑复用现有 Python 代码。

## 技术决策总结

| 决策项 | 选择 |
|---|---|
| GUI 框架 | pywebview（Windows 上使用系统 WebView2） |
| 架构 | pywebview 直接暴露 Python API 给前端 JS |
| 前端技术 | 纯 TypeScript + HTML + CSS（无前端框架） |
| 视觉风格 | 浅色简洁风，紫色主色调（#4f46e5） |
| 窗口布局 | 左右分栏（左侧设置面板，右侧结果+进度+日志） |
| CLI 兼容 | GUI 为主，无参数启动 GUI，带参数走现有 CLI |
| 功能范围 | 全功能增强版：搜索、下载、手动选歌、下载历史、设置持久化 |

## 架构

### 分层

```
┌─────────────────────────────────────────────────────┐
│  前端 (HTML/CSS/TS)                                 │
│  - 界面渲染、用户交互                                │
│  - 通过 window.pywebview.api 调用 Python 方法       │
└──────────────────────┬──────────────────────────────┘
                       │ pywebview JS Bridge
┌──────────────────────▼──────────────────────────────┐
│  music_downloader/gui/api.py (MusicApi 类)          │
│  - 暴露给前端的方法：search、download、getConfig 等  │
│  - 事件回调：log、progress、downloadComplete        │
└──────────────────────┬──────────────────────────────┘
                       │ 调用
┌──────────────────────▼──────────────────────────────┐
│  music_downloader/gui/bridge.py (桥接层)            │
│  - 封装现有 api.py/search_with_pagination           │
│  - 封装现有 downloader.py/download_song             │
│  - 线程管理（避免阻塞 UI），进度/日志转发            │
└──────────────────────┬──────────────────────────────┘
                       │ 复用现有代码（不修改）
┌──────────────────────▼──────────────────────────────┐
│  现有核心模块（完全复用，零修改）                     │
│  api.py / downloader.py / metadata.py / config.py  │
│  Playwright 浏览器管理、签名、下载、元数据写入       │
└─────────────────────────────────────────────────────┘
```

### 文件结构

```text
music_download.py              # 入口修改：无参数/--gui 启动 GUI
music_downloader/
├── ...（现有文件全部保留，核心逻辑零修改）
└── gui/                         # 🆕 GUI 模块
    ├── __init__.py
    ├── app.py                   # GUI 应用入口：创建 pywebview 窗口
    ├── api.py                   # 暴露给前端的 Python API 类
    ├── bridge.py                # 桥接层：封装现有逻辑 + 线程管理
    └── static/                  # 前端静态资源
        ├── index.html
        ├── css/style.css
        └── js/app.js
requirements.txt               # 新增 pywebview 依赖
scripts/build_exe.ps1          # 更新打包配置
```

### 核心设计原则

1. **不修改现有核心代码**：`api.py`、`downloader.py`、`metadata.py`、`cli.py` 等完全不动
2. **CLI 完全兼容**：现有命令行参数（`-k`、`-s`、`-b`、`-i`、`--check-env` 等）行为不变
3. **桥接层隔离**：GUI 通过 bridge 间接调用，不直接耦合核心逻辑
4. **线程安全**：下载操作在 Python 后台线程执行，通过 pywebview 的事件机制通知前端，不阻塞 UI

## 入口逻辑

修改 `music_download.py` 和 `music_downloader/cli.py` 的入口判断：

```python
# cli.py main() 入口逻辑
def main(argv=None):
    args = parse_args(argv)
    if args.check_env:
        sys.exit(check_environment())

    # 新增：判断是否启动 GUI
    # 条件：无参数 或 明确指定 --gui
    is_gui_mode = (len(sys.argv) <= 1) or args.gui
    if is_gui_mode:
        from music_downloader.gui.app import run_gui
        run_gui()
        return

    return_code = run_with_browser(args)
    if return_code:
        sys.exit(return_code)
```

命令行新增 `--gui` 参数，显式启动 GUI 模式。

## Python API 设计（暴露给前端）

`music_downloader/gui/api.py` 中的 `MusicApi` 类，通过 pywebview 暴露给前端：

```python
class MusicApi:
    # ── 配置与状态 ──

    def get_config(self) -> dict:
        """获取当前配置（音乐源、音质、下载目录等）和持久化设置"""

    def save_config(self, config: dict) -> None:
        """保存用户设置（下载目录、默认音乐源、默认音质等）到本地 JSON"""

    def check_environment(self) -> dict:
        """环境检查（复用 env.py），返回各项检查结果"""

    def open_download_dir(self) -> None:
        """用系统文件管理器打开下载目录"""

    # ── 搜索 ──

    def search(self, keyword: str, source: str, search_type: str,
               number: int) -> list[dict]:
        """搜索歌曲/专辑/歌单，返回结果列表"""

    # ── 下载 ──

    def start_download(self, songs: list[dict], source: str,
                       bitrate: str, download_lyric: bool,
                       download_cover: bool) -> str:
        """开始批量下载，返回任务 ID。下载在后台线程执行，通过事件通知进度"""

    def cancel_download(self, task_id: str) -> None:
        """取消正在进行的下载任务"""

    # ── 历史记录 ──

    def get_history(self) -> list[dict]:
        """获取下载历史记录"""

    def clear_history(self) -> None:
        """清空下载历史"""

    # ── 事件回调（由前端 JS 注册）──

    def on_log(self, message: str): ...       # 日志消息
    def on_progress(self, task_id: str, current: int, total: int,
                    song_name: str, status: str): ...  # 下载进度
    def on_download_complete(self, task_id: str, result: dict): ...  # 单首/全部完成
```

## 前端界面设计

### 窗口尺寸

- 默认大小：960×680
- 最小尺寸：800×560
- 可调整大小

### 左侧设置面板（宽 200px）

从上到下：
1. **搜索框 + 搜索按钮**
2. **音乐源选择**：下拉框（12 个音乐源）
3. **搜索类型**：单曲/专辑/歌单
4. **音质选择**：128/192/320/FLAC
5. **数量输入**：数字输入框
6. **复选框**：下载封面、下载歌词
7. **分隔线**
8. **下载目录选择**：显示当前目录 + "浏览"按钮
9. **分隔线**
10. **底部操作按钮**：打开下载目录、环境检查、设置

### 右侧主区域

- **顶部工具栏**：下载选中按钮、全选/反选、总结果数
- **搜索结果列表**：
  - 每行：复选框、封面缩略图、歌曲名、歌手、专辑、时长、来源标签、操作按钮（单独下载）
  - Hi-Res 标识
  - 下载状态图标（待下载/下载中/完成/失败）
- **进度条区域**：总进度条 + 当前下载歌曲名 + 百分比
- **日志面板**（底部，高 100px，可折叠）：带时间戳的日志输出，类似终端

### 下载历史

通过左侧面板的按钮打开一个模态框或独立区域，展示历史下载记录（歌曲名、歌手、来源、音质、下载时间、文件路径）。

### 设置持久化

保存到用户目录下的 `.music_downloader_config.json`，包括：
- 默认下载目录
- 默认音乐源
- 默认音质
- 默认搜索类型
- 是否下载封面/歌词
- 窗口大小和位置（可选）

## 线程模型

pywebview 在 Windows 上 UI 运行在主线程，所有 Python 代码如果阻塞主线程会导致界面卡死。因此：

1. **浏览器初始化**：Playwright 浏览器的启动和 Cloudflare 验证在后台线程进行，通过事件通知前端显示加载状态
2. **搜索操作**：在后台线程执行，完成后返回结果
3. **批量下载**：每首歌的下载在后台线程顺序执行（或支持有限并发），每完成/失败/跳过一首就通过事件通知前端更新进度
4. **取消机制**：使用 threading.Event 作为取消标志，下载循环中检查该标志

## 依赖变更

`requirements.txt` 新增：
```
pywebview>=5.0
```

注意：pywebview 在 Windows 上依赖 .NET 和 WebView2（Windows 10/11 已内置），无需额外安装 Chromium。

## 打包（Nuitka）

更新 `scripts/build_exe.ps1`，将 `music_downloader/gui/static/` 目录作为数据文件打包进 EXE：

```powershell
# 新增参数：包含 GUI 静态资源
--include-data-dir=music_downloader/gui/static=music_downloader/gui/static
```

Nuitka 打包单 EXE 时，`pywebview` 需要确保 WebView2 相关 DLL 正确包含。

## 错误处理

- Playwright/Chrome 未安装：启动时检测，环境检查面板显示友好提示
- Cloudflare 验证：首次启动时在 GUI 中提示，浏览器窗口弹出（有头模式），用户完成验证后回到 GUI
- 网络错误/API 错误：日志面板显示红色错误信息，不崩溃
- 下载失败：标记为失败状态，允许重试，不影响其他歌曲下载
