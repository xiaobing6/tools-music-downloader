# Build Script Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Windows onefile and standalone builds correct, reproducible, recoverable, and verifiable while raising the project minimum to Python 3.11.

**Architecture:** Keep `scripts/build_exe.ps1` as the single build entry. Build into `dist-staging/`, validate the mode-specific executable, smoke-test it, generate a deterministic checksum manifest, then promote it to `dist/` with rollback through `dist-backup/`. Keep source-install requirements ranged, but constrain release-build direct dependencies in a dedicated constraints file.

**Tech Stack:** PowerShell, Python 3.11+, pytest, Nuitka 4.1.3, npm 11/package-lock v3, Vite/Svelte.

## Global Constraints

- Minimum supported Python is 3.11.
- Default build mode is `onefile`; `standalone` remains supported and retains the complete `music_download.dist/` directory.
- `-SkipInstall` skips Python and frontend dependency installation but still builds the frontend.
- Default Nuitka parallelism is `min(logical_processor_count, 8)` and `-Jobs` accepts positive integers.
- Normal frontend installation uses `npm ci` and the committed `package-lock.json`.
- Release constraints pin: playwright 1.60.0, mutagen 1.48.0, rich 15.0.0, typer 0.26.8, pydantic 2.13.4, pywebview 6.2.1, Nuitka 4.1.3, ordered-set 4.1.0, zstandard 0.25.0.
- Automated tests must not access the real music site.
- Nuitka must continue to include `music_downloader/gui/static` and must not bundle Playwright browsers.

---

### Task 1: Raise the Python baseline to 3.11

**Files:**
- Modify: `tests/test_environment_checks.py`
- Modify: `music_downloader/infrastructure/environment.py:24-31`
- Modify: `pyproject.toml:10-53`

**Interfaces:**
- Consumes: existing `check_python_version(version_info: tuple[int, int, int]) -> EnvironmentCheck`.
- Produces: a Python 3.11 boundary shared by runtime checks, package metadata, Ruff, and mypy.

- [ ] **Step 1: Write the failing Python-boundary tests**

Add these imports and tests to `tests/test_environment_checks.py`:

```python
import tomllib
from pathlib import Path

import pytest

from music_downloader.infrastructure.environment import (
    EnvironmentCheck,
    check_python_version,
    run_environment_checks,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("version", "expected_ok"),
    [((3, 10, 99), False), ((3, 11, 0), True)],
)
def test_python_version_requires_311(
    version: tuple[int, int, int], expected_ok: bool
) -> None:
    check = check_python_version(version)

    assert check.ok is expected_ok
    if not expected_ok:
        assert "需要 Python 3.11+" in check.detail


def test_python_tooling_targets_311() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["requires-python"] == ">=3.11"
    assert config["tool"]["ruff"]["target-version"] == "py311"
    assert config["tool"]["mypy"]["python_version"] == "3.11"
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run:

```powershell
python -m pytest tests/test_environment_checks.py -q
```

Expected: FAIL because Python 3.10 is still accepted and `pyproject.toml` still declares 3.10.

- [ ] **Step 3: Implement the 3.11 runtime and tooling baseline**

Change `check_python_version` to:

```python
def check_python_version(
    version_info: tuple[int, int, int] = sys.version_info[:3],
) -> EnvironmentCheck:
    """检查 Python 版本是否 >= 3.11。"""
    ok = version_info >= (3, 11, 0)
    version = ".".join(str(part) for part in version_info)
    detail = f"Python {version}" if ok else f"需要 Python 3.11+，当前为 Python {version}"
    return EnvironmentCheck("Python 版本", ok, detail)
```

Update `pyproject.toml` exactly as follows:

```toml
requires-python = ">=3.11"
```

Remove `Programming Language :: Python :: 3.10`, set Ruff `target-version = "py311"`, and set mypy `python_version = "3.11"`.

- [ ] **Step 4: Run focused verification**

Run:

```powershell
python -m pytest tests/test_environment_checks.py -q
python -m ruff check music_downloader/infrastructure/environment.py tests/test_environment_checks.py
python -m mypy music_downloader/infrastructure/environment.py
```

Expected: all commands pass.

- [ ] **Step 5: Commit the Python baseline**

```powershell
git add pyproject.toml music_downloader/infrastructure/environment.py tests/test_environment_checks.py
git commit -m "build: require Python 3.11 or newer"
```

---

### Task 2: Implement the reliable build contract

**Files:**
- Create: `requirements-build-constraints.txt`
- Modify: `.gitignore`
- Modify: `tests/test_build_script.py`
- Modify: `scripts/build_exe.ps1`

**Interfaces:**
- Consumes: the existing PowerShell build entry and `requirements-build.txt`.
- Produces: exact direct-dependency constraints, executable build-script contract tests, and staged onefile/standalone artifacts.

- [ ] **Step 1: Write failing build-contract tests**

Replace `tests/test_build_script.py` with tests that retain the current assertions and add these focused contracts:

```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")


def test_build_script_runs_frontend_build_before_nuitka() -> None:
    assert '$frontendDir = Join-Path $ProjectRoot "music_downloader/gui/frontend"' in SCRIPT
    assert '$staticIndex = Join-Path $ProjectRoot "music_downloader/gui/static/index.html"' in SCRIPT
    assert "Get-Command npm.cmd" in SCRIPT
    assert "npm.cmd --prefix $frontendDir ci" in SCRIPT
    assert "npm.cmd --prefix $frontendDir run build" in SCRIPT
    assert "Frontend dependencies are missing" in SCRIPT
    assert "Frontend build failed" in SCRIPT
    assert "Frontend build did not produce expected artifact: $staticIndex" in SCRIPT

    frontend_build_position = SCRIPT.index("npm.cmd --prefix $frontendDir run build")
    static_check_position = SCRIPT.index("Frontend build did not produce expected artifact")
    nuitka_command_position = SCRIPT.index("python -m nuitka --mode=")
    assert frontend_build_position < static_check_position < nuitka_command_position


def test_build_script_keeps_required_nuitka_options() -> None:
    for argument in (
        "--disable-plugin=pywebview",
        "--include-module=webview.platforms.winforms",
        "--include-module=webview.platforms.win32",
        "--include-module=webview.platforms.edgechromium",
        "--include-module=webview.platforms.mshtml",
        "--playwright-include-browser=none",
        "--windows-console-mode=hide",
        "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static",
    ):
        assert argument in SCRIPT
    assert "--windows-console-mode=attach" not in SCRIPT


def test_build_script_has_reproducible_and_bounded_inputs() -> None:
    assert "[ValidateRange(1, 256)]" in SCRIPT
    assert "[Math]::Min([System.Environment]::ProcessorCount, 8)" in SCRIPT
    assert "requirements-build-constraints.txt" in SCRIPT
    assert "python -m pip install -r requirements-build.txt -c $constraintsFile" in SCRIPT
    assert "sys.version_info < (3, 11)" in SCRIPT
    assert "python -m nuitka --version" in SCRIPT


def test_build_script_stages_and_promotes_mode_specific_outputs() -> None:
    assert '$stagingDir = Join-Path $ProjectRoot "dist-staging"' in SCRIPT
    assert '$backupDir = Join-Path $ProjectRoot "dist-backup"' in SCRIPT
    assert '$standaloneDir = Join-Path $stagingDir "music_download.dist"' in SCRIPT
    assert '$stagedExe = Join-Path $standaloneDir "music_download.exe"' in SCRIPT
    assert '$stagedExe = Join-Path $stagingDir "music_download.exe"' in SCRIPT
    assert "Move-Item -LiteralPath $stagingDir -Destination $distDir" in SCRIPT


def test_build_script_smoke_tests_and_hashes_artifacts() -> None:
    assert "& $stagedExe --help" in SCRIPT
    assert "Get-FileHash -LiteralPath $filePath -Algorithm SHA256" in SCRIPT
    assert '$manifestPath = Join-Path $stagingDir "SHA256SUMS.txt"' in SCRIPT
    assert "Write-Sha256Manifest" in SCRIPT


def test_build_constraints_pin_direct_dependencies() -> None:
    constraints = (ROOT / "requirements-build-constraints.txt").read_text(encoding="utf-8")
    expected = {
        "playwright==1.60.0",
        "mutagen==1.48.0",
        "rich==15.0.0",
        "typer==0.26.8",
        "pydantic==2.13.4",
        "pywebview==6.2.1",
        "nuitka==4.1.3",
        "ordered-set==4.1.0",
        "zstandard==0.25.0",
    }
    assert expected <= set(constraints.splitlines())
```

- [ ] **Step 2: Run the build-contract tests and verify failure**

Run:

```powershell
python -m pytest tests/test_build_script.py -q
```

Expected: FAIL because `npm ci`, constraints, staging, `-Jobs`, smoke testing, and checksum generation are absent.

- [ ] **Step 3: Add exact direct-dependency constraints and ignored staging paths**

Create `requirements-build-constraints.txt`:

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

Add these repository-root entries to `.gitignore` next to `dist/`:

```gitignore
dist-staging/
dist-backup/
```

- [ ] **Step 4: Re-run the focused test to keep it red for script behavior**

Run:

```powershell
python -m pytest tests/test_build_script.py -q
```

Expected: the constraints test passes; build-script behavior tests still fail.

- [ ] **Step 5: Add parameter and helper foundations**

Change the parameter block and add helpers with these exact signatures:

```powershell
param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile",
    [switch]$SkipInstall,
    [ValidateRange(1, 256)]
    [int]$Jobs = [Math]::Min([System.Environment]::ProcessorCount, 8)
)

function Assert-ExitCode {
    param([string]$Stage, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Stage failed with exit code $ExitCode"
    }
}

function Write-Sha256Manifest {
    param(
        [string]$Root,
        [string[]]$FilePaths,
        [string]$ManifestPath
    )

    $lines = foreach ($filePath in ($FilePaths | Sort-Object)) {
        $fullPath = [System.IO.Path]::GetFullPath($filePath)
        $relativePath = $fullPath.Substring($Root.Length).TrimStart([char[]]"\/")
        $relativePath = $relativePath.Replace('\', '/')
        $hash = Get-FileHash -LiteralPath $filePath -Algorithm SHA256
        "$($hash.Hash.ToLowerInvariant())  $relativePath"
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($ManifestPath, [string[]]$lines, $utf8NoBom)
}
```

- [ ] **Step 6: Add Python preflight, constrained installs, and tool reporting**

Inside a `Push-Location $ProjectRoot` / `try` block:

```powershell
$pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(sys.version_info < (3, 11))"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11+ is required. Current Python: $pythonVersion"
}

$constraintsFile = Join-Path $ProjectRoot "requirements-build-constraints.txt"
if (-not $SkipInstall) {
    python -m pip install -r requirements-build.txt -c $constraintsFile
    Assert-ExitCode "Build dependency installation" $LASTEXITCODE
}

$env:NUITKA_CACHE_DIR = Join-Path $ProjectRoot ".nuitka-cache"
$nodeVersion = node --version
Assert-ExitCode "Node.js version check" $LASTEXITCODE
$npmVersion = npm.cmd --version
Assert-ExitCode "npm version check" $LASTEXITCODE
$nuitkaVersion = python -m nuitka --version
Assert-ExitCode "Nuitka version check" $LASTEXITCODE
Write-Host "Python: $pythonVersion"
Write-Host "Node.js: $nodeVersion"
Write-Host "npm: $npmVersion"
Write-Host "Nuitka: $($nuitkaVersion -join ' ')"
```

Use `npm.cmd --prefix $frontendDir ci` for non-skip installs and retain the existing `node_modules` preflight for `-SkipInstall`.

- [ ] **Step 7: Build into staging with mode-specific paths**

Define:

```powershell
$distDir = Join-Path $ProjectRoot "dist"
$stagingDir = Join-Path $ProjectRoot "dist-staging"
$backupDir = Join-Path $ProjectRoot "dist-backup"
$standaloneDir = Join-Path $stagingDir "music_download.dist"
```

Fail if `dist-backup/` already exists, remove only `dist-staging/`, pass `--output-dir=$stagingDir` and `--jobs=$Jobs` to Nuitka, then select the expected executable:

```powershell
if ($Mode -eq "onefile") {
    python -m nuitka --mode=onefile @commonArgs
    $stagedExe = Join-Path $stagingDir "music_download.exe"
} else {
    python -m nuitka --mode=standalone @commonArgs
    $stagedExe = Join-Path $standaloneDir "music_download.exe"
}
Assert-ExitCode "Nuitka build" $LASTEXITCODE
if (-not (Test-Path -LiteralPath $stagedExe -PathType Leaf)) {
    throw "Build did not produce expected artifact: $stagedExe"
}
```

Remove `music_download.build/` and `music_download.onefile-build/`; remove `music_download.dist/` only in onefile mode.

- [ ] **Step 8: Smoke-test, hash, and promote with rollback**

Use this flow:

```powershell
& $stagedExe --help
Assert-ExitCode "Packaged executable smoke test" $LASTEXITCODE

$manifestPath = Join-Path $stagingDir "SHA256SUMS.txt"
if ($Mode -eq "onefile") {
    $artifactFiles = @($stagedExe)
} else {
    $artifactFiles = @(
        Get-ChildItem -LiteralPath $standaloneDir -File -Recurse |
            ForEach-Object { $_.FullName }
    )
}
Write-Sha256Manifest -Root $stagingDir -FilePaths $artifactFiles -ManifestPath $manifestPath

$distMovedToBackup = $false
try {
    if (Test-Path -LiteralPath $distDir) {
        Move-Item -LiteralPath $distDir -Destination $backupDir
        $distMovedToBackup = $true
    }
    Move-Item -LiteralPath $stagingDir -Destination $distDir
    if ($distMovedToBackup) {
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }
} catch {
    if ($distMovedToBackup) {
        if (Test-Path -LiteralPath $distDir) {
            Remove-Item -LiteralPath $distDir -Recurse -Force
        }
        Move-Item -LiteralPath $backupDir -Destination $distDir
    }
    throw
}
```

In the outer `finally`, remove leftover `dist-staging/`, restore the prior `NUITKA_CACHE_DIR`, and call `Pop-Location`. Do not delete `dist-backup/` in `finally`, because it is recovery data if restoration itself fails.

- [ ] **Step 9: Run focused tests and PowerShell parsing**

Run:

```powershell
python -m pytest tests/test_build_script.py -q
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path .\scripts\build_exe.ps1),
    [ref]$tokens,
    [ref]$errors
) | Out-Null
if ($errors.Count -ne 0) { $errors; exit 1 }
```

Expected: tests pass and PowerShell reports no parse errors.

- [ ] **Step 10: Commit the complete build contract**

```powershell
git add .gitignore requirements-build-constraints.txt tests/test_build_script.py scripts/build_exe.ps1
git commit -m "build: stage and verify Nuitka artifacts"
```

---

### Task 3: Synchronize user and contributor documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md`
- Modify: `docs/superpowers/plans/2026-07-06-cli-help-details.md`

**Interfaces:**
- Consumes: final `build_exe.ps1` parameters and artifact layout.
- Produces: accurate build and Python-version instructions for users and contributors.

- [ ] **Step 1: Update all active Python minimum declarations**

Change `Python 3.10+` to `Python 3.11+` in README, AGENTS, and the two historical plans that declare the old tech-stack baseline. Keep migration statements and boundary tests in the new design/plan documents because their references to Python 3.10 describe the rejected old version rather than a supported baseline.

- [ ] **Step 2: Replace the README build section with exact commands and layouts**

Document these commands:

```powershell
.\scripts\build_exe.ps1
.\scripts\build_exe.ps1 -Mode standalone
.\scripts\build_exe.ps1 -Jobs 4
.\scripts\build_exe.ps1 -SkipInstall
```

Document these outputs:

```text
onefile:
dist/music_download.exe
dist/SHA256SUMS.txt

standalone:
dist/music_download.dist/music_download.exe
dist/SHA256SUMS.txt
```

State that normal builds use `requirements-build-constraints.txt` and `npm ci`, builds occur in staging, packaged `--help` is smoke-tested, and a failed build preserves the previous successful `dist/`.

- [ ] **Step 3: Update AGENTS build guidance**

Add these contributor rules:

```text
- Python 3.11+ syntax and tooling baseline.
- Preserve onefile and standalone artifact semantics when editing build_exe.ps1.
- Preserve staging/rollback, packaged --help smoke test, and SHA256SUMS.txt generation.
- Release verification includes both build-script tests and at least a onefile -SkipInstall build.
```

- [ ] **Step 4: Verify stale supported-version declarations are gone**

Run:

```powershell
rg -n "Python 3\.10\+|requires-python = \">=3\.10\"|target-version = \"py310\"|python_version = \"3\.10\"" README.md AGENTS.md pyproject.toml music_downloader docs/superpowers
```

Expected: no matches except prose in the new migration design/plan that deliberately discusses rejecting Python 3.10; the exact `3.10+` support declaration must have no matches.

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md AGENTS.md docs/superpowers/plans/2026-07-02-vite-svelte-gui-refactor.md docs/superpowers/plans/2026-07-06-cli-help-details.md
git commit -m "docs: document reliable Python 3.11 builds"
```

---

### Task 4: Run full verification and real package builds

**Files:**
- Verify: all modified files
- Generated ignored outputs: `music_downloader/gui/static/`, `dist/`, `.nuitka-cache/`

**Interfaces:**
- Consumes: completed Python baseline, build script, constraints, tests, and documentation.
- Produces: evidence that source checks, frontend build, onefile build, and standalone build work.

- [ ] **Step 1: Run the Python verification suite**

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

Expected: all commands pass.

- [ ] **Step 2: Run frontend verification**

```powershell
node --test music_downloader/gui/frontend/tests/startup.test.mjs
npm.cmd --prefix music_downloader/gui/frontend run check
npm.cmd --prefix music_downloader/gui/frontend run build
```

Expected: all commands pass and `music_downloader/gui/static/index.html` exists.

- [ ] **Step 3: Build and inspect onefile output**

```powershell
.\scripts\build_exe.ps1 -Mode onefile -SkipInstall
Test-Path .\dist\music_download.exe
Get-Content .\dist\SHA256SUMS.txt
```

Expected: build succeeds, exe exists, smoke test passes, and the checksum manifest contains `music_download.exe`.

- [ ] **Step 4: Build and inspect standalone output**

```powershell
.\scripts\build_exe.ps1 -Mode standalone -SkipInstall
Test-Path .\dist\music_download.dist\music_download.exe
Get-Content .\dist\SHA256SUMS.txt | Select-Object -First 5
```

Expected: build succeeds, the full `.dist` directory remains, and the manifest contains files below `music_download.dist/`.

- [ ] **Step 5: Confirm repository state and commit any verification-only fixes**

```powershell
git status --short
git diff --check
```

Expected: only intentional source/document changes remain; ignored build outputs do not appear. If verification required a source fix, repeat the failing check, apply the minimal fix, rerun the full relevant verification, and commit with a message describing that fix.
