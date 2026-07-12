# tools-music-downloader

音乐搜索下载工具，数据来源为 `music.gdstudio.org`。项目同时提供桌面 GUI 和 CLI：GUI 适合日常搜索、选择、下载与失败重试，CLI 适合脚本化和批量使用。

## 功能特性

- 支持网易云、咪咕、酷我、YouTube Music、Tidal、Qobuz、Deezer、Spotify、QQ 音乐、喜马拉雅、Joox、Apple Music 等音乐源。
- 支持单曲、专辑、歌单搜索，可指定结果数量并自动分页。
- 支持 `128` / `192` / `320` / `flac` 音质；`flac` 会保存为 `.flac`。
- 下载完成后尽力写入标题、艺术家、专辑、曲目编号、封面和歌词等元数据。
- 元数据、封面或歌词写入失败不会删除已下载音频，也不会把歌曲判为失败。
- 已存在的目标音频文件会直接跳过，重复判断只看最终文件是否存在。
- GUI 每次启动都使用默认参数，不保存来源、搜索类型、数量、音质等用户选择。
- GUI 启动时显示品牌启动页和阶段化进度条；启动细节写入运行日志，不直接显示在启动页上。

## 环境要求

- Python 3.11+
- 系统已安装 Google Chrome
- 如需从源码重建 GUI 前端或打包 exe，需要安装 Node.js 和 npm
- Windows / macOS / Linux

运行依赖：`playwright`、`mutagen`、`rich`、`typer`、`pydantic`、`pywebview`。

开发依赖：`ruff`、`mypy`、`pytest`。

GUI 前端使用 Vite、Svelte、TypeScript、Flowbite Svelte、Tailwind CSS 和 `@lucide/svelte`，构建产物输出到 `music_downloader/gui/static/`，由 pywebview 加载。启动页由 `StartupScreen.svelte` 渲染，启动阶段文案和进度定义在 `src/lib/startup.ts`。

Windows 应用图标使用 `music_downloader/gui/assets/music_downloader.ico` 中的蓝底白色音符。源码运行时 pywebview 直接加载该图标；Nuitka 构建时通过 `--windows-icon-from-ico` 嵌入 EXE，同时用于窗口标题栏、任务栏和资源管理器。

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

GUI 默认下载根目录为项目目录下的 `downloads/`。主界面优先展示搜索框；音源、搜索类型和结果数量是常用设置，音质、歌词、封面、下载目录和环境检查位于“更多设置”中。中途修改只对当前运行有效，下次启动仍恢复默认值。

输入框和下拉框聚焦时使用品牌蓝边框与柔和光晕，并在标签和控件之间保留足够净空；使用键盘操作按钮、复选框和“更多设置”时仍会显示清晰的焦点外圈。下拉框保留原生选择行为，并使用统一的下拉箭头；在支持原生展开状态的环境中，箭头会向上旋转。

GUI 默认窗口大小为 `1280x800`，最小窗口大小为 `1024x720`。窗口宽度低于 `1180px` 时，下载状态和运行日志会从结果区右侧移到下方；日志默认折叠，可按需展开并复制内容。主界面使用固定外壳：宽屏保持四边 `16px`、窄屏保持四边 `12px` 的等距边界，展开“更多设置”时压缩下方工作区，结果、日志和窄屏工作区在各自区域内部滚动，不再出现窗口级滚动条。

搜索结果采用紧凑音乐库布局：每行保持 `60px`，歌曲/歌手、专辑和来源/状态使用内容加权的弹性列，时长使用兼容长时长的 `64px` 右对齐列；音源显示中文名称，未知时长显示为破折号。选中项使用浅蓝底和左侧品牌色标记，总数与已选数量集中显示在结果区标题下方；下载按钮文字保持稳定为“下载选中”，避免选择数量变化挤动操作区。搜索完成后封面逐张加载，不阻塞结果返回；单张封面解析失败时继续显示默认图标。

鼠标取消选择后不会残留整行焦点框，键盘导航时仍保留清晰的整行焦点轮廓。空搜索提示始终相对结果卡片的实际剩余空间居中，“更多设置”展开后也不会因固定最小高度向下偏移。

GUI 使用与工作台主题一致的全局关闭确认弹窗：无论当前是否正在下载，点击窗口关闭按钮都会显示“关闭音乐下载器？”和“确定要关闭应用吗？”。选择“继续使用”、按 `Esc` 或点击遮罩都会返回应用；只有选择“关闭应用”才执行窗口销毁和资源清理。搜索框通过 `aria-label="搜索关键词"` 提供明确的辅助技术名称。

GUI 启动时会先显示品牌启动页，依次展示“连接桌面接口”“加载基础配置”“准备浏览器”“验证访问环境”等阶段化进度。启动页不显示底层日志；如果初始化失败，会停留在启动页并提供“重试”按钮，详细原因可在进入主界面后的运行日志中查看。

GUI 的后台 Chrome 默认以 headless 模式运行。为避免新版 Chrome 在 Windows 上把本应隐藏的平台窗口显示为不可交互的白色窗口，程序会把该平台窗口放到屏幕外；如果站点验证需要人工处理，程序仍会重新打开正常可见的 Chrome 窗口。

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
| `-s / --source` | 音乐源：`netease` / `migu` / `kuwo` / `ytmusic` / `tidal` / `qobuz` / `deezer` / `spotify` / `tencent` / `ximalaya` / `joox` / `apple` | `netease` |
| `-n / --number` | 结果数量，必须是正整数 | `20` |
| `-t / --type` | 搜索类型：`song` / `album` / `playlist` | `song` |
| `-o / --output` | 下载目录 | `./downloads/` |
| `-f / --format` | 输出格式：`table` / `json` / `list` | `table` |
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
  services/                       # CLI 和 GUI 共用的搜索服务
  gui/                            # pywebview 桌面 GUI、Vite/Svelte 前端源码与静态构建产物
scripts/build_exe.ps1             # Windows Nuitka 打包脚本
tests/                            # pytest 测试
```

## 打包 EXE

如需单独重建 GUI 静态资源：

```powershell
npm.cmd --prefix music_downloader/gui/frontend install
npm.cmd --prefix music_downloader/gui/frontend run build
```

构建脚本支持以下常用方式：

```powershell
.\scripts\build_exe.ps1
.\scripts\build_exe.ps1 -Mode standalone
.\scripts\build_exe.ps1 -Jobs 4
.\scripts\build_exe.ps1 -SkipInstall
```

如果系统因 `Restricted` 执行策略拒绝直接运行 `.ps1`，可只为本次构建进程指定策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

该参数仅对本次 PowerShell 进程生效，不会修改用户级或计算机级策略。受组织策略管理的设备请按组织批准的流程执行；不要通过 `Set-ExecutionPolicy` 修改用户级或计算机级策略。

未指定 `-Mode` 时默认构建 onefile；standalone 保留完整的 `.dist` 布局。

`-SkipInstall` 会跳过 Python 和前端依赖安装，但仍会执行前端构建；因此需要已经存在 `music_downloader/gui/frontend/node_modules/`。

不同模式的输出布局如下：

```text
onefile:
dist/music_download.exe
dist/SHA256SUMS.txt

standalone:
dist/music_download.dist/music_download.exe
dist/SHA256SUMS.txt
```

生成的 `music_download.exe` 同时支持 GUI 和 CLI：

```powershell
.\dist\music_download.exe
.\dist\music_download.exe --gui
.\dist\music_download.exe -h
.\dist\music_download.exe --check-env
```

正常构建会使用 `requirements-build-constraints.txt` 约束 Python 构建依赖，并通过 `npm ci` 安装前端依赖。所有产物先在 staging 目录中构建，打包后的 `--help` 会通过冒烟测试后才发布到 `dist/`；构建失败时会保留上一次成功的 `dist/`。

构建脚本会在 Nuitka 打包前自动运行 Vite 前端构建，并继续把 `music_downloader/gui/static/` 打包进 exe；`node_modules/` 只用于前端构建，不会被打包进 exe。Chrome 不会被打包，运行时仍使用用户系统已安装的 Google Chrome。

## 开发检查

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
python music_download.py --check-env
```

修改 GUI 前端或启动页后，建议额外运行：

```powershell
cd music_downloader/gui/frontend
node --test tests/startup.test.mjs tests/workbench.test.mjs
npm.cmd run check
npm.cmd run build
```

端到端搜索会访问真实音乐站点，请在本地手动验证，不要写入 CI。

## 常见问题

**为什么不执行 `playwright install chromium`？**

本项目默认通过 Playwright 启动系统已安装的 Google Chrome，即 `channel="chrome"`，不使用 Playwright 下载的 Chromium。

**为什么 Cloudflare 有时需要重新验证？**

`cf_clearance` 与 IP、UA、TLS 指纹和 Chrome profile 相关。工具默认使用项目目录下隔离的 `.chrome-profile/`，不会读取系统 Chrome profile。

**为什么 GUI 旁边出现不可交互的白色窗口？**

新版 Chrome 的 headless 模式仍会创建平台窗口，正常情况下该窗口不会显示。GUI 会在 headless 启动时把它放到屏幕外；如果白窗再次出现，请确认 `music_downloader/gui/bridge.py` 的 headless persistent context 仍使用屏幕外位置参数，并检查系统 Chrome 与 Playwright 版本。不要通过隐藏 GUI 或禁用整个浏览器来规避，因为搜索和下载仍依赖该浏览器会话。

**遇到 HTTP 401 签名验证失败怎么办？**

这通常表示站点版本或签名算法发生了变化。当前签名通过页面里的 `crc32` 计算；如果持续出现 401，请检查 `music_downloader/infrastructure/gdstudio.py` 中的 `compute_signature` 是否仍与站点前端一致。

**下载成功但没有标签怎么办？**

这说明音频文件已经落盘，但元数据、歌词或封面写入失败。现在这类失败只作为警告处理，不会删除音频文件；再次下载时如果目标文件已存在会跳过。
