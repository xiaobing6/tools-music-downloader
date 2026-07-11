# Headless Chrome 白窗回归修复设计

**日期：** 2026-07-12  
**状态：** 实施中

## 背景

执行 `python .\music_download.py` 后，桌面 GUI 能正常显示，但同时出现一个不可点击、不可拖动的白色窗口。该窗口会随音乐下载器退出而消失，并且在本轮前端改版后的实际运行中可稳定复现。

## 已确认根因

诊断按组件边界进行了三次单变量验证：

1. 仅把实际 GUI 尺寸统一为 `1280×800`，白窗仍然出现，排除窗口尺寸为直接根因。
2. 保留同一套 Svelte 前端和 pywebview，但临时跳过 `MusicApi.init_browser()`，白窗消失，确认问题来自 Playwright/Chrome 初始化链路。
3. 恢复真实 Playwright、持久化 Chrome profile 和站点初始化，仅在 headless 启动时增加 `--window-position=-32000,-32000`，GUI 正常进入首页且白窗消失。

新版 Chrome headless 会创建但原则上不显示平台窗口。当前 Windows 环境错误地把 `launch_persistent_context` 创建的隐藏 Chrome 窗口合成到了桌面；现场窗口句柄的约 `1280×720` 尺寸也与该 Chrome 平台窗口一致。

此外发现一个独立但相关的配置一致性缺陷：`music_downloader/gui/app.py` 和文档已把默认窗口尺寸改为 `1280×800`，但 `music_downloader/gui/settings.py` 仍返回 `1266×1013`。因此真实启动尺寸与代码常量、测试和文档互相矛盾。

## 目标

- 正常源码启动只显示音乐下载器 GUI，不出现不可交互的白窗。
- 保留持久化 Chrome profile、Cookie 和 Cloudflare 状态。
- headless 模式始终把 Chrome 平台窗口放到屏幕外。
- 需要人工验证而回退到 headed 模式时，Chrome 窗口仍在正常屏幕位置显示。
- 实际 GUI 默认尺寸与代码和文档统一为 `1280×800`，最小尺寸保持 `1024×720`。
- 相关测试和项目文档不再保留矛盾信息。

## 方案比较

### 方案 A：仅将 headless 平台窗口移到屏幕外（采用）

为 `launch_persistent_context` 生成与模式相关的启动参数：headless 模式加入 `--window-position=-32000,-32000`，headed 模式不加入。

优点：已经现场验证；改动小；不改变 profile、Cookie、签名、Cloudflare 重试或下载语义。缺点：这是针对 Chrome/Windows 平台窗口行为的显式兼容措施。

### 方案 B：改用 `launch()` 和普通 context

普通 `launch()` 可避免持久化上下文强制创建默认页面，但不能直接维持现有 user data dir 语义，需要额外设计 storage state 和 Cookie 持久化。

该方案改变核心浏览器生命周期且风险较高，不用于本次回归修复。

### 方案 C：禁用 GPU 或 DirectComposition

禁用 GPU 可能改变合成路径，但并不消除 Chrome 平台窗口，且可能影响 WebView2、Chrome 渲染和运行稳定性。该方案未通过现场验证，不采用。

## 实现设计

### 浏览器启动参数

在 `music_downloader/gui/bridge.py` 内集中定义 headless 窗口位置参数，并通过一个小型纯函数按 `headless` 状态返回启动参数。

实际实现使用 `HEADLESS_WINDOW_POSITION_ARG` 和 `_browser_launch_args(*, headless: bool)`；两个 GUI persistent context 调用都显式传入该函数的结果。

所有 GUI `launch_persistent_context` 调用使用该函数：

- 首次 headless 启动包含屏幕外位置参数。
- Cloudflare 检查失败后的 headed 重启不包含该参数。
- CLI 浏览器启动行为不在本次范围内；CLI 没有嵌入 GUI，也没有观察到同类白窗回归。

### 窗口尺寸一致性

把 `music_downloader/gui/settings.py` 中的 `window_width`、`window_height` 更新为 `1280`、`800`。`music_downloader/gui/app.py` 的 `DEFAULT_WINDOW_SIZE = (1280, 800)` 和 `MIN_WINDOW_SIZE = (1024, 720)` 保持不变。

测试必须跨模块检查默认配置与窗口常量一致，避免以后分别修改却都能独立通过。

### 生命周期与错误处理

浏览器关闭、回退和异常处理保持现状。屏幕外参数只影响 headless Chrome 平台窗口的位置，不改变页面、context、profile 或清理流程。headed 回退继续由现有逻辑负责打开可见 Chrome。

## 测试设计

实施遵循 TDD：

1. 先新增测试，断言 headless 启动参数包含屏幕外位置，headed 启动参数不包含；观察测试因缺少实现而失败。
2. 新增跨模块测试，断言 GUI 默认配置尺寸等于 `DEFAULT_WINDOW_SIZE`；观察测试因 `1266×1013` 与 `1280×800` 不一致而失败。
3. 实现最小代码使测试通过。
4. 运行 GUI 相关 pytest、全量 pytest、ruff、mypy 和 Python 编译检查。
5. 构建前端静态资源并运行前端测试，确认本次 Python 修复没有造成构建产物或文档偏差。
6. 最终执行一次真实 `python .\music_download.py` 启动验证，确认 GUI 正常且无白窗；若站点触发人工验证，同时确认 headed Chrome 仍可见。

## 文档同步

同步更新以下资料：

- `README.md`：说明 GUI 默认/最小尺寸和 headless Chrome 窗口抑制行为，并补充白窗排错说明。
- `AGENTS.md`：在浏览器初始化和 GUI 修改约定中记录 headless/headed 参数边界。
- 当前设计文档与随后生成的实施计划：记录验证证据和最终实现。
- 既有音乐工作台设计/计划只在存在冲突时更新；不复制无关内容。

## 非目标

- 不切换 pywebview、WebView2 或 Playwright 技术栈。
- 不改变 CLI 的浏览器启动方式。
- 不改变 Cloudflare 回退、API 签名、搜索、下载、标签写入或成功语义。
- 不以禁用 GPU、隐藏整个 GUI 或延迟初始化来掩盖问题。

## 验收标准

- 正常启动只出现一个音乐下载器 GUI 窗口。
- headless Chrome 的平台窗口不可见。
- GUI 可完成初始化并进入首页。
- headed 回退仍能显示 Chrome 供用户验证。
- 默认窗口实际为 `1280×800`，最小尺寸为 `1024×720`。
- 新增回归测试以及现有 Python、前端和文档测试全部通过。
