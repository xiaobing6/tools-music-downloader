# 构建脚本优化设计

## 目标

提高 Windows Nuitka 构建的正确性、可复现性和失败恢复能力，同时将项目最低 Python 版本从 3.10 提升到 3.11。

默认产物继续使用 onefile 单文件 exe，并保留可用于排查依赖问题的 standalone 模式。

## 范围

本次修改包括：

- 修复 standalone 模式的产物路径、校验和清理逻辑。
- 将项目、工具配置、环境检查和文档中的最低 Python 版本统一调整为 3.11。
- 改进前端和 Python 构建依赖的可复现性。
- 增加 staging 构建、并行度配置、构建环境输出、冒烟测试和 SHA256 清单。
- 扩充构建脚本和 Python 版本检查测试。

本次不包括：

- 代码签名。
- 自动创建 GitHub Release 或上传产物。
- 新增 CI 工作流。
- 访问真实音乐站点的自动端到端测试。

## Python 版本基线

项目最低支持版本统一为 Python 3.11：

- `pyproject.toml` 使用 `requires-python = ">=3.11"`。
- Ruff 使用 `target-version = "py311"`。
- mypy 使用 `python_version = "3.11"`。
- classifiers 删除 Python 3.10，保留 3.11 及以上版本。
- 环境检查要求 `sys.version_info >= (3, 11)`，错误文案显示“需要 Python 3.11+”。
- README、AGENTS 和仓库内已有设计/计划文档中的 Python 3.10+ 声明统一改为 Python 3.11+。

构建脚本仍从 `pyproject.toml` 读取应用版本。由于构建解释器最低版本已经是 3.11，可以直接使用标准库 `tomllib`，但脚本会在读取 TOML 前显式验证 Python 版本并输出实际解释器版本。

## 构建接口

`scripts/build_exe.ps1` 保留现有参数，并新增可配置并行度：

```powershell
.\scripts\build_exe.ps1 [-Mode onefile|standalone] [-SkipInstall] [-Jobs <int>]
```

- `Mode` 默认 `onefile`。
- `SkipInstall` 跳过 Python 和前端依赖安装，但仍执行前端构建。
- `Jobs` 必须为正整数，默认值为逻辑处理器数与 8 的较小值。

脚本只支持 Windows 构建，因为 Nuitka 参数明确使用 MSVC 和 Windows 元数据。

## 依赖安装与版本记录

正常构建执行：

1. 使用发布构建 constraints 文件安装 `requirements-build.txt`。
2. 使用 `npm ci --prefix <frontendDir>` 严格按 `package-lock.json` 安装前端依赖。
3. 输出 Python、Node、npm 和 Nuitka 版本，便于复现和诊断。

`-SkipInstall` 模式不安装依赖，但会检查 `node_modules` 是否存在，并继续输出工具版本。

发布 constraints 文件固定项目直接运行依赖和构建工具的以下已验证版本：

```text
playwright==1.60.0
mutagen==1.48.0
rich==15.0.0
typer==0.26.8
pydantic==2.13.4
pywebview==6.2.1
nuitka==4.1.3
ordered-set==4.1.0
zstandard==0.25.0
```

它不替代面向普通源码安装的 `requirements.txt`，后者继续表达项目允许的依赖范围。constraints 文件只固定直接依赖；传递依赖仍由这些直接依赖的元数据解析，因此本次提供的是受控构建基线，而不是带哈希的全量跨平台锁文件。

## staging 与产物布局

Nuitka 始终先输出到仓库根目录下的 staging 目录。旧的成功 `dist/` 在新构建完成前不会删除。

构建成功后的预期布局为：

```text
onefile:
  dist/
    music_download.exe
    SHA256SUMS.txt

standalone:
  dist/
    music_download.dist/
      music_download.exe
      ...运行所需 DLL、扩展模块和静态资源
    SHA256SUMS.txt
```

流程为：

1. 清理本次构建专用的 staging 目录。
2. 前端构建输出并校验 `music_downloader/gui/static/index.html`。
3. Nuitka 输出到 staging。
4. 按模式定位实际 exe。
5. 运行无网络冒烟测试。
6. 生成 SHA256 清单。
7. 删除旧 `dist/`，将通过验证的 staging 目录移动为新 `dist/`。

任何步骤失败时，staging 可以清理，但旧 `dist/` 保持不变。

## 冒烟测试与完整性清单

构建产物使用 `--help` 做默认冒烟测试。该命令不访问音乐站点，也不要求进行真实搜索；退出码非零时构建失败。

`SHA256SUMS.txt` 使用相对于 `dist/` 的路径：

- onefile 模式记录 `music_download.exe`。
- standalone 模式递归记录 `music_download.dist/` 中所有文件。
- 清单内容按相对路径排序，保证输出稳定。

构建完成时打印最终产物路径和清单路径。

## 状态恢复与错误处理

脚本使用 `Push-Location` / `Pop-Location` 或等价的 `try/finally` 结构，确保执行结束后恢复调用者的工作目录。

如果脚本覆盖 `NUITKA_CACHE_DIR`，会在结束时恢复原值；原值不存在时会删除本次设置的环境变量。

所有外部命令都检查退出码，错误信息包含失败阶段和退出码。产物路径检查按 onefile 和 standalone 分开处理，standalone 目录不会被当作中间目录删除。

## 测试策略

测试遵循先失败、后实现的顺序：

- 更新环境检查测试，先证明 Python 3.10 不再通过、Python 3.11 可以通过。
- 更新构建脚本测试，覆盖 `-Jobs`、`npm ci`、staging、版本检查、两种模式的产物路径、冒烟测试和 SHA256 清单。
- 保留前端必须在 Nuitka 前构建、静态资源必须存在、pywebview Windows 后端和 GUI 静态目录必须显式打包等已有断言。
- 运行 Python 单测、Ruff、mypy、Python 编译检查和前端测试/检查/构建。
- 不在自动测试中访问真实音乐站点。

完整 Nuitka 打包成本较高，最终验证至少执行 onefile `-SkipInstall` 构建；如果本机工具链条件允许，再执行 standalone 构建验证完整目录产物。

## 文档同步

README 更新以下内容：

- Python 3.11+ 环境要求。
- `-Mode standalone` 与 `-Jobs` 示例和产物布局。
- 正常构建使用锁文件/constraints，`-SkipInstall` 的行为保持不变。
- SHA256 清单和冒烟测试说明。

AGENTS 同步 Python 3.11+、构建参数和发版验证约定，避免后续修改重新引入 Python 3.10 基线。
