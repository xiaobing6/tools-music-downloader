# AGENTS.md

> 面向协作者与 AI 编码助手。面向终端用户的文档见 [README.md](./README.md)，请先阅读它了解项目使用方式。

## 项目概述

这是一个音乐搜索下载工具，数据来源为 `music.gdstudio.org`。项目同时提供：

- 桌面 GUI：pywebview 加载 Vite/Svelte 构建出的静态资源。
- CLI：Typer 公开入口，和 GUI 同级放在 `music_downloader/cli/`。
- 单一打包入口：`music_download.py`，生成的 exe 同时支持 GUI 和 CLI。

底层通过 Playwright 启动系统已安装的 Google Chrome，访问站点并调用 API 搜索、下载音频文件，再使用 `mutagen` 尽力写入 MP3/FLAC 元数据。

## 技术栈

- **语言**：Python 3.11+
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
music_downloader/gui/                  # pywebview GUI 后端桥接
music_downloader/gui/frontend/         # Vite/Svelte 前端源码
music_downloader/gui/frontend/src/lib/startup.ts # GUI 启动阶段、文案和进度
music_downloader/gui/frontend/src/lib/components/StartupScreen.svelte # GUI 品牌启动页
music_downloader/gui/frontend/tests/startup.test.mjs # 启动页与启动文案测试
music_downloader/gui/assets/music_downloader.ico # Windows 应用图标（多尺寸）
music_downloader/gui/static/           # GUI 静态构建产物
music_downloader/core/config.py        # 共享常量、默认值、支持平台
music_downloader/core/console.py       # rich/plain console 输出
tests/                                 # pytest 测试
scripts/build_exe.ps1                  # Windows exe 构建脚本
```

## 核心架构

### API 交互流程

1. 启动 Playwright 浏览器，优先无头模式访问 `music.gdstudio.org`。GUI 的 headless persistent context 必须带 `--window-position=-32000,-32000`，防止新版 Chrome 的平台窗口被 Windows 合成到桌面。
2. 检查 `cf_clearance` cookie，失败后尝试打开可见 Chrome 窗口；headed 回退不得带屏幕外位置参数，否则用户无法完成人工验证。
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
- GUI 启动体验由 `App.svelte` 编排、`src/lib/startup.ts` 提供阶段模型、`StartupScreen.svelte` 渲染品牌启动页；不要把启动期浏览器、站点验证或调试细节直接展示在启动页上，详细信息继续进入运行日志。
- Windows 应用图标统一使用 `music_downloader/gui/assets/music_downloader.ico`；源码运行通过 `webview.start(icon=...)` 加载，Nuitka 构建必须保留 `--windows-icon-from-ico` 和对应 `--include-data-file`，确保窗口、任务栏和 EXE 使用同一品牌图标。
- GUI 主界面保持“搜索优先”的音乐工作台结构：音源、类型、结果数量为常用设置，音质及其余选项位于“更多设置”；默认窗口为 `1280x800`、最低为 `1024x720`，在 `1180px` 以下把活动栏移到结果区下方，不要重新引入无断点的固定 `360px` 右栏。
- 主界面使用固定外壳并禁用窗口级滚动：宽屏 `.workbench-frame` 四边保持 `16px`、低于 `1180px` 时四边保持 `12px` 等距边界；展开“更多设置”时压缩下方工作区，结果列表、日志和窄屏 `.workbench-main` 在内部滚动。不要用 `scrollbar-gutter`、隐藏滚动条或 JavaScript 宽度补偿重新解决窗口抖动。
- 搜索结果保持紧凑音乐库形态：使用 `60px` 六列行对齐复选框、`40px` 封面、歌曲/歌手、专辑、来源/状态和时长；三个文本信息区采用内容加权弹性列，时长固定为 `64px` 并右对齐。音源显示中文名，未知时长显示为破折号，选中项使用浅蓝底与左侧品牌色标记。总数和已选数只在结果区集中显示，下载按钮文字保持稳定为“下载选中”，不要在搜索栏或按钮中重复显示动态数量。搜索完成后封面逐张加载，不得阻塞结果返回；单张封面解析失败时继续显示默认图标。
- 结果行的整行焦点轮廓只响应复选框的 `:focus-visible`，不要用无条件 `:focus-within` 让鼠标点击后残留外框。空状态使用实际剩余高度居中，不要重新添加会在“更多设置”展开时溢出的固定最小高度。
- GUI 使用 Svelte 主题化全局关闭确认，不使用 Windows 原生 `MessageBox`。原生 `closing` 是锁定式同步事件，处理函数返回 `False` 才表示取消关闭：首次关闭必须返回 `False`，再从后台线程发送 `py-close-request`，不得在该回调中同步调用 `evaluate_js`；前端确认接口先设置一次性许可并返回，窗口销毁稍后异步执行，避免 pywebview 在 API 回传时访问已释放的 WebView2，确认后的 `closing` 返回 `True`。清理逻辑只绑定 `window.events.closed`。弹窗初始焦点落在无轮廓的说明文本，按钮仅在用户键盘导航后显示焦点环；文案保持简短，并支持“继续使用”、`Esc` 和遮罩取消。搜索输入框保留 `aria-label="搜索关键词"`，不要只依赖 placeholder 作为可访问名称。
- 音源、类型、结果数量、音质和下载目录使用 `.field-stack`，标签与控件之间保持 `10px` 净空；下拉框保留原生 `<select>` 行为，统一使用装饰性下拉箭头，并在浏览器暴露展开状态时向上旋转；文本字段通过 `:focus` 显示品牌蓝边框和柔和光晕，按钮、summary、checkbox 和 radio 通过 `:focus-visible` 保留清晰的 `2px` 键盘焦点环。
- 运行日志默认折叠，但日志、下载目录和歌曲信息必须可选择复制；动态搜索与下载状态使用适度的辅助技术播报。

### Chrome profile 隔离

- 默认通过 `launch_persistent_context` 启动，把 user data 放在项目根目录 `.chrome-profile/`，与系统 Chrome profile 隔离。
- GUI 只在 headless 模式使用屏幕外窗口位置；headed 验证窗口保持正常位置。不要用禁用 GPU、隐藏 GUI 或删除 persistent profile 的方式替代这一兼容措施。
- GUI 浏览器初始化失败、验证失败或超时时，必须在 Playwright 所属线程关闭并清空 page/context/ready 状态；重试不得复用失败会话或继续锁住 profile。
- `cf_clearance` 跨 profile 失效属预期副作用。
- 如果用户主动指定 `--user-data-dir`，CLI 会透传，并打印当前目录位置。

### 下载与成功语义

- 默认下载根目录是项目根目录的 `downloads/`。
- 重复判断只看最终目标文件是否已经存在。
- 音频文件落盘成功即可认定单曲下载成功。
- 音频响应在最终文件替换前只做保守校验：拒绝明确的 HTML、JSON 或 XML 错误文档；`audio/*`、`application/octet-stream`、缺失或未知 MIME 的非错误二进制内容继续接受。不要把严格容器签名或 Mutagen 可解析性作为成功前置条件。
- 元数据、歌词或封面处理失败只记录 warning，不删除已下载音频，不把歌曲判为失败。
- 不要重新引入“写入 ID3/FLAC 失败就删除音频文件”的逻辑。
- GUI 下载后台任务的正常、取消、目录失败、超时和未预期异常都必须恰好发送一次 complete 事件，并在 `finally` 中从任务表移除；取消不得把尚未处理的歌曲误报为失败。

## 常见修改场景

- **新增音乐源**：音源只在 `music_downloader/domain/enums.py` 的 `Source` 中维护 API 值和展示名；`VALID_SOURCES` 自动从 `Source` 派生，CLI、GUI API 和前端结果行均消费这份目录，不要另建音源 ID 或展示名映射。
- **修改默认设置**：调整 `DEFAULT_KEYWORD`、`DEFAULT_SOURCE`、`DEFAULT_NUMBER`、`DEFAULT_BITRATE`。
- **调整搜索逻辑**：优先修改 `music_downloader/services/search.py` 和 `music_downloader/infrastructure/gdstudio.py`。
- **调整下载行为**：优先修改 `music_downloader/infrastructure/downloader.py`，保持“文件存在即跳过”和“元数据失败 warning-only”语义。
- **调整文件命名/默认目录**：修改 `music_downloader/infrastructure/files.py`。
- **调整 ID3/FLAC 标签**：修改 `music_downloader/infrastructure/tags.py`。
- **API 签名变更**：修改 `music_downloader/infrastructure/gdstudio.py` 的 `compute_signature`，并更新 README 的 401 排错说明。
- **交互模式命令解析**：见 `music_downloader/cli/interactive.py` 和 `workflow.py`。
- **CLI 参数**：见 `music_downloader/cli/app.py`，所有变更要同步更新 `README.md` 参数表。
- **GUI 功能**：修改 `music_downloader/gui/api.py`、`bridge.py` 和 `gui/frontend/src/`；构建产物输出到 `gui/static/`，不要直接手改静态构建产物；GUI 参数选择不应持久化到用户目录。涉及布局、窗口尺寸或交互约定时，同步更新前端 Node 测试、Python GUI 测试、`README.md`、本文件和相关设计文档。
- **GUI 启动页/启动阶段**：修改 `music_downloader/gui/frontend/src/lib/startup.ts`、`StartupScreen.svelte` 和 `App.svelte`；同步更新 `music_downloader/gui/frontend/tests/startup.test.mjs`、`README.md`，再运行前端构建刷新 `gui/static/`。
- **打包资源**：GUI 静态资源仍在 `music_downloader/gui/static/`，构建脚本需保留 `--include-data-dir=music_downloader/gui/static=music_downloader/gui/static`。

## 约定

- Python 3.11+ 语法和工具链基线；用 PEP 604 `X | None`，避免 `Optional[X]`。
- 业务日志统一走 `music_downloader.core.console.console.print`，不要用 `print` 直出；`gui/app.py` 找不到静态资源时的 stderr 提示除外。
- CLI 输出和文档使用中文。
- GUI 启动页文案保持用户友好，不直接出现 `Cloudflare`、`Playwright`、`Chrome`、堆栈、trace 等底层诊断词；这类信息只进入运行日志。
- 单测不要访问真实音乐站点；端到端功能验证靠 `python music_download.py --check-env` 加一次本地真实搜索。
- 下载目录 `downloads/`、Chrome profile `.chrome-profile/`、构建产物 `dist/` 已由 `.gitignore` 忽略。
- 修改 `scripts/build_exe.ps1` 时，保持 onefile 和 standalone 的产物语义不变。
- 保持 staging/回滚、打包后 `--help` 冒烟测试和 `SHA256SUMS.txt` 生成逻辑。
- 发版验证包含构建脚本测试，并至少执行一次 onefile `-SkipInstall` 构建。
- 发版前跑：`ruff check .`、`ruff format --check .`、`mypy music_downloader`、`python -m py_compile music_download.py`、`python music_download.py --check-env`，再加一次真实搜索。
