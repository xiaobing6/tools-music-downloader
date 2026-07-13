# README GUI 双图预览 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 GitHub README 增加实际 GUI 启动页截图，并按“启动页面 → 主工作台”的顺序纵向展示两张预览图。

**Architecture:** 从现有 `dist/music_download.exe` 启动真实 pywebview GUI，选择品牌、阶段文案和进度条均清晰完整的正常启动阶段并捕获完整窗口为 PNG。README 继续使用仓库相对路径和居中的全宽图片标签，不修改应用代码或现有主工作台截图。

**Tech Stack:** pywebview GUI、Windows Graphics Capture/桌面截图、PNG、GitHub Markdown/HTML、Pillow（Codex 工作区运行时，仅用于验证图片）

## Global Constraints

- 新图片路径必须是 `docs/images/gui-startup.png`。
- 现有 `docs/images/gui-main.png` 不得覆盖或重新拍摄。
- README 必须先展示启动页，再展示主工作台。
- 启动页不得出现 Cloudflare、Playwright、Chrome、堆栈或 trace 等底层诊断词。
- 截图必须只包含应用窗口，不包含桌面背景、其他应用或用户隐私信息。
- 两张图片都使用 PNG、居中布局、`width="100%"` 和准确的替代文本。

---

### Task 1: 捕获并验证启动页截图

**Files:**
- Create: `docs/images/gui-startup.png`
- Preserve: `docs/images/gui-main.png`

**Interfaces:**
- Consumes: `dist/music_download.exe` 的实际启动流程。
- Produces: 可由 GitHub README 相对路径加载的 `docs/images/gui-startup.png`。

- [ ] **Step 1: 记录现有主工作台图片校验值**

Run:

```powershell
Get-FileHash docs/images/gui-main.png -Algorithm SHA256
```

Expected: 输出一个非空 SHA256；完成任务后该值保持不变。

- [ ] **Step 2: 启动真实 GUI 并观察启动页**

使用 `computer-use` 启动绝对路径：

```text
E:\code\tools\tools_music_downloader\dist\music_download.exe
```

Expected: 出现标题为“音乐下载器”的窗口，并在初始化过程中显示品牌图标、阶段文案和进度条。

- [ ] **Step 3: 在信息完整的正常启动阶段捕获窗口**

将完整应用窗口保存为：

```text
E:\code\tools\tools_music_downloader\docs\images\gui-startup.png
```

Expected: PNG 仅包含音乐下载器窗口，品牌、正常阶段文案和进度条完整可见；当前采用 90% 的“验证访问环境”画面。

- [ ] **Step 4: 验证新图片并确认主工作台图片未改变**

Run:

```powershell
& 'C:\Users\biosens\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "from pathlib import Path; from PIL import Image; p=Path(r'docs\images\gui-startup.png'); img=Image.open(p); img.verify(); assert img.format == 'PNG'; assert img.size[0] >= 1024 and img.size[1] >= 720; print(img.format, img.size, p.stat().st_size)"
Get-FileHash docs/images/gui-main.png -Algorithm SHA256
```

Expected: 新图片输出 `PNG`、至少 `1024x720` 且文件大小非零；主工作台图片 SHA256 与 Step 1 一致。

- [ ] **Step 5: 关闭 GUI**

使用应用自身的关闭流程，选择“关闭应用”。

Expected: `music_download.exe` 不再出现在可控制窗口列表中。

### Task 2: 按产品流程更新 README

**Files:**
- Modify: `README.md`
- Test: `README.md` 中的图片路径与 `docs/images/*.png`

**Interfaces:**
- Consumes: `docs/images/gui-startup.png` 和现有 `docs/images/gui-main.png`。
- Produces: GitHub 可直接渲染的纵向双图“界面预览”章节。

- [ ] **Step 1: 修改“界面预览”章节**

将现有章节替换为：

```markdown
## 界面预览

### 启动页面

<p align="center">
  <img src="docs/images/gui-startup.png" alt="音乐下载器 GUI 启动页面" width="100%">
</p>

### 主工作台

<p align="center">
  <img src="docs/images/gui-main.png" alt="音乐下载器 GUI 主工作台" width="100%">
</p>
```

- [ ] **Step 2: 验证 README 图片顺序和本地资源**

Run:

```powershell
& 'C:\Users\biosens\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "from pathlib import Path; r=Path('README.md').read_text(encoding='utf-8'); startup=r.index('docs/images/gui-startup.png'); main=r.index('docs/images/gui-main.png'); assert startup < main; assert Path('docs/images/gui-startup.png').is_file(); assert Path('docs/images/gui-main.png').is_file(); print('README preview order verified')"
git diff --check
```

Expected: 输出 `README preview order verified`，且 `git diff --check` 无输出并返回 0。

- [ ] **Step 3: 检查最终差异**

Run:

```powershell
git status --short
git diff -- README.md
git diff --stat
```

Expected: 仅出现计划文件、`README.md` 和新增的 `docs/images/gui-startup.png`；现有 `docs/images/gui-main.png` 不在差异中。

- [ ] **Step 4: 提交实现**

Run:

```powershell
git add README.md docs/images/gui-startup.png docs/superpowers/plans/2026-07-13-readme-gui-previews.md
git commit -m "docs: 增加 GUI 启动页预览"
```

Expected: 提交包含启动页 PNG、README 双图顺序和本实施计划，不包含应用代码改动。
