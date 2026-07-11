# Vite Svelte GUI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-written GUI frontend with a Vite + Svelte + TypeScript + Flowbite Svelte frontend while keeping existing GUI behavior and fixing compiled-exe static asset lookup.

**Architecture:** pywebview remains the desktop shell and keeps exposing `MusicApi` to JavaScript. Vite builds Svelte source from `music_downloader/gui/frontend/` into `music_downloader/gui/static/`, which remains the runtime and Nuitka-packaged asset directory. The frontend uses typed wrappers around the existing pywebview API and listens to the existing `py-log` and `py-progress` custom events.

**Tech Stack:** Python 3.11+, pywebview, Nuitka, Vite, Svelte, TypeScript, Flowbite Svelte, Tailwind CSS, @lucide/svelte, pytest, ruff, mypy.

---

## Reference Docs Checked

- Flowbite Svelte quickstart: `https://flowbite-svelte.com/docs/pages/quickstart`
- Flowbite Svelte components: `Button`, `Input`, `Select`, `Checkbox`, `Badge`, `Progressbar`, `Modal`
- Tailwind CSS with Vite: `https://tailwindcss.com/docs/installation/using-vite`
- Svelte TypeScript support: `https://svelte.dev/docs/svelte/typescript`

## File Structure

- Modify: `.gitignore` to ignore frontend dependency folders.
- Create: `music_downloader/gui/frontend/package.json` for frontend scripts and npm dependencies.
- Create: `music_downloader/gui/frontend/tsconfig.json` for strict TypeScript checks.
- Create: `music_downloader/gui/frontend/vite.config.ts` to emit static assets to `../static`.
- Create: `music_downloader/gui/frontend/svelte.config.js` for Svelte preprocessing.
- Create: `music_downloader/gui/frontend/index.html` with the Svelte app mount.
- Create: `music_downloader/gui/frontend/src/main.ts` as the Svelte entry.
- Create: `music_downloader/gui/frontend/src/vite-env.d.ts` for Vite and Svelte typing.
- Create: `music_downloader/gui/frontend/src/app.css` for Tailwind, Flowbite, and app shell rules.
- Create: `music_downloader/gui/frontend/src/lib/types.ts` for GUI data contracts.
- Create: `music_downloader/gui/frontend/src/lib/api.ts` for the typed pywebview bridge.
- Create: `music_downloader/gui/frontend/src/lib/state.ts` for small pure UI helpers.
- Create: `music_downloader/gui/frontend/src/lib/components/*.svelte` for focused UI pieces.
- Create: `music_downloader/gui/frontend/src/App.svelte` as the app orchestrator.
- Replace generated static assets under `music_downloader/gui/static/` by running Vite.
- Modify: `music_downloader/gui/app.py` for static asset lookup and `1280x800` / `1200x750` sizing.
- Modify: `scripts/build_exe.ps1` to run the frontend build before Nuitka.
- Modify: `tests/test_gui_static.py` for generated Vite output and source feature checks.
- Create: `tests/test_gui_app.py` for static directory candidate resolution.
- Create: `tests/test_build_script.py` for build-script frontend integration assertions.
- Modify: `README.md` to document frontend build prerequisites and exe packaging behavior.

---

### Task 1: Add Frontend Scaffold And Dependency Boundaries

**Files:**
- Modify: `.gitignore`
- Create: `music_downloader/gui/frontend/package.json`
- Create: `music_downloader/gui/frontend/tsconfig.json`
- Create: `music_downloader/gui/frontend/vite.config.ts`
- Create: `music_downloader/gui/frontend/svelte.config.js`
- Create: `music_downloader/gui/frontend/index.html`
- Create: `music_downloader/gui/frontend/src/main.ts`
- Create: `music_downloader/gui/frontend/src/vite-env.d.ts`
- Create: `music_downloader/gui/frontend/src/app.css`

- [ ] **Step 1: Add the dependency ignore rule**

Append this block to `.gitignore` near the existing dependency/cache sections:

```gitignore
# Frontend dependencies
music_downloader/gui/frontend/node_modules/
```

- [ ] **Step 2: Create `package.json`**

Create `music_downloader/gui/frontend/package.json`:

```json
{
  "name": "music-downloader-gui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "svelte-check --tsconfig ./tsconfig.json && vite build",
    "check": "svelte-check --tsconfig ./tsconfig.json",
    "preview": "vite preview --host 127.0.0.1"
  },
    "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "latest",
    "@tsconfig/svelte": "latest",
    "@tailwindcss/vite": "latest",
    "flowbite": "latest",
    "flowbite-svelte": "latest",
    "@lucide/svelte": "latest",
    "svelte": "latest",
    "svelte-check": "latest",
    "tailwindcss": "latest",
    "typescript": "latest",
    "vite": "latest"
  }
}
```

- [ ] **Step 3: Create TypeScript config**

Create `music_downloader/gui/frontend/tsconfig.json`:

```json
{
  "extends": "@tsconfig/svelte/tsconfig.json",
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "resolveJsonModule": true,
    "allowJs": false,
    "checkJs": false,
    "isolatedModules": true,
    "moduleDetection": "force",
    "verbatimModuleSyntax": true,
    "strict": true
  },
  "include": ["src/**/*.ts", "src/**/*.svelte", "vite.config.ts", "svelte.config.js"],
  "references": []
}
```

- [ ] **Step 4: Verify dependency install**

Run:

```powershell
npm --prefix music_downloader/gui/frontend install
npm --prefix music_downloader/gui/frontend run check
```

Expected: dependency install succeeds. The check command fails because `src/App.svelte` has not been created yet.

- [ ] **Step 5: Create Vite config**

Create `music_downloader/gui/frontend/vite.config.ts`:

```ts
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  plugins: [svelte(), tailwindcss()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
    assetsDir: "assets"
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true
  }
});
```

- [ ] **Step 6: Create Svelte config**

Create `music_downloader/gui/frontend/svelte.config.js`:

```js
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

const config = {
  preprocess: vitePreprocess()
};

export default config;
```

- [ ] **Step 7: Create frontend HTML entry**

Create `music_downloader/gui/frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>音乐下载器</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 8: Create frontend entry files**

Create `music_downloader/gui/frontend/src/main.ts`:

```ts
import "./app.css";
import { mount } from "svelte";
import App from "./App.svelte";

const app = mount(App, {
  target: document.getElementById("app") as HTMLElement
});

export default app;
```

Create `music_downloader/gui/frontend/src/vite-env.d.ts`:

```ts
/// <reference types="svelte" />
/// <reference types="vite/client" />
```

- [ ] **Step 9: Create base CSS**

Create `music_downloader/gui/frontend/src/app.css`:

```css
@import "tailwindcss";
@plugin "flowbite/plugin";
@source "../node_modules/flowbite-svelte/dist";
@source "../node_modules/flowbite/dist";

:root {
  color: #111827;
  background: #f3f4f6;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "Microsoft YaHei", sans-serif;
}

html,
body,
#app {
  height: 100%;
}

body {
  margin: 0;
  overflow: hidden;
  user-select: none;
}

button,
input,
select,
textarea {
  font: inherit;
}

.app-shell {
  height: 100vh;
  min-width: 1200px;
  min-height: 750px;
}

.scrollbar-thin::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
```

- [ ] **Step 10: Run dependency install and create lockfile**

Run:

```powershell
npm --prefix music_downloader/gui/frontend install
```

Expected: `music_downloader/gui/frontend/package-lock.json` is created and `node_modules/` is ignored by git.

- [ ] **Step 11: Commit the scaffold**

```powershell
git add .gitignore music_downloader/gui/frontend
git commit -m "build(gui): add vite svelte frontend scaffold"
```

---

### Task 2: Add Typed Pywebview Contracts And Pure State Helpers

**Files:**
- Create: `music_downloader/gui/frontend/src/lib/types.ts`
- Create: `music_downloader/gui/frontend/src/lib/api.ts`
- Create: `music_downloader/gui/frontend/src/lib/state.ts`

- [ ] **Step 1: Create GUI types**

Create `music_downloader/gui/frontend/src/lib/types.ts`:

```ts
export interface GuiConfig {
  source: string;
  search_type: string;
  bitrate: string;
  number: number;
  output_dir: string;
  download_cover: boolean;
  download_lyric: boolean;
  window_width?: number;
  window_height?: number;
}

export interface OptionItem {
  value: string;
  label: string;
}

export interface SelectItem {
  value: string;
  name: string;
  disabled?: boolean;
}

export interface ValidOptions {
  sources: OptionItem[];
  bitrates: string[];
  search_types: string[];
  formats: string[];
}

export interface Song {
  name?: string;
  artist?: string;
  album?: string;
  duration?: string;
  cover?: string;
  source?: string;
  bitrate?: string;
  _gui_index?: number;
  [key: string]: unknown;
}

export interface EnvironmentCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface LogEntry {
  id: number;
  time: string;
  message: string;
  level: "info" | "success" | "warn" | "error";
}

export interface PyLogDetail {
  message: string;
  level: LogEntry["level"];
}

export type ProgressDetail =
  | { type: "start"; task_id: string; total: number }
  | {
      type: "progress";
      task_id: string;
      current: number;
      total: number;
      song_name?: string;
    }
  | {
      type: "song_done";
      task_id: string;
      index: number;
      result: "success" | "skip" | "fail";
      reason?: string;
      path?: string;
      current: number;
      total: number;
    }
  | {
      type: "complete";
      task_id: string;
      success: number;
      fail: number;
      skip: number;
    };

export interface SongStatus {
  state: "queued" | "downloading" | "success" | "skip" | "fail";
  reason?: string;
  path?: string;
}

export interface DownloadProgressState {
  visible: boolean;
  current: number;
  total: number;
  label: string;
}

export interface PywebviewApi {
  get_valid_options(): Promise<ValidOptions>;
  get_config(): Promise<GuiConfig>;
  save_config(config: GuiConfig): Promise<boolean>;
  init_browser(): Promise<{ ready: boolean }>;
  search(keyword: string, source: string, searchType: string, number: number): Promise<Song[]>;
  start_download(
    songs: Song[],
    source: string,
    bitrate: string,
    downloadLyric: boolean,
    downloadCover: boolean,
    outputDir: string
  ): Promise<string>;
  cancel_download(taskId: string): Promise<void>;
  open_download_dir(path?: string): Promise<void>;
  select_directory(): Promise<string>;
  check_environment(): Promise<EnvironmentCheck[]>;
  get_history(): Promise<Record<string, unknown>[]>;
  shutdown(): Promise<void>;
}
```

- [ ] **Step 2: Create typed API wrapper**

Create `music_downloader/gui/frontend/src/lib/api.ts`:

```ts
import type { ProgressDetail, PyLogDetail, PywebviewApi } from "./types";

declare global {
  interface Window {
    pywebview?: {
      api: PywebviewApi;
    };
  }
}

export function getPywebviewApi(): PywebviewApi {
  const api = window.pywebview?.api;
  if (!api) {
    throw new Error("pywebview 未就绪，请在桌面窗口中运行");
  }
  return api;
}

export function waitForPywebview(): Promise<PywebviewApi> {
  if (window.pywebview?.api) {
    return Promise.resolve(window.pywebview.api);
  }

  return new Promise((resolve) => {
    window.addEventListener(
      "pywebviewready",
      () => {
        resolve(getPywebviewApi());
      },
      { once: true }
    );
  });
}

export function onPythonLog(handler: (detail: PyLogDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<PyLogDetail>).detail);
  };
  window.addEventListener("py-log", listener);
  return () => window.removeEventListener("py-log", listener);
}

export function onPythonProgress(handler: (detail: ProgressDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<ProgressDetail>).detail);
  };
  window.addEventListener("py-progress", listener);
  return () => window.removeEventListener("py-progress", listener);
}
```

- [ ] **Step 3: Create state helpers**

Create `music_downloader/gui/frontend/src/lib/state.ts`:

```ts
import type { GuiConfig, OptionItem, SelectItem, Song } from "./types";

export function toSelectItems(options: OptionItem[]): SelectItem[] {
  return options.map((item) => ({ value: item.value, name: item.label }));
}

export function toSimpleSelectItems(values: string[]): SelectItem[] {
  return values.map((value) => ({ value, name: value }));
}

export function normalizeNumber(value: string | number, fallback: number): number {
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return parsed;
}

export function withConfigValue<K extends keyof GuiConfig>(
  config: GuiConfig,
  key: K,
  value: GuiConfig[K]
): GuiConfig {
  return { ...config, [key]: value };
}

export function selectedSongs(songs: Song[], selectedIndices: Set<number>): Song[] {
  return Array.from(selectedIndices)
    .filter((index) => index >= 0 && index < songs.length)
    .map((index) => ({ ...songs[index], _gui_index: index }));
}

export function progressPercent(current: number, total: number): string {
  if (total <= 0) {
    return "0";
  }
  return String(Math.min(100, Math.max(0, Math.round((current / total) * 100))));
}

export function timeLabel(date = new Date()): string {
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}
```

- [ ] **Step 4: Run frontend type check**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run check
```

Expected: it fails only because `src/App.svelte` does not exist yet.

- [ ] **Step 5: Commit the typed bridge layer**

```powershell
git add music_downloader/gui/frontend/src/lib
git commit -m "feat(gui): add typed frontend bridge contracts"
```

---

### Task 3: Build Focused Svelte Components

**Files:**
- Create: `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/DownloadProgress.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/LogPanel.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/EnvironmentModal.svelte`
- Create: `music_downloader/gui/frontend/src/lib/components/EmptyState.svelte`

- [ ] **Step 1: Create `SearchBar.svelte`**

```svelte
<script lang="ts">
  import { Button, Input } from "flowbite-svelte";
  import { Search } from "@lucide/svelte";

  interface Props {
    keyword: string;
    searching: boolean;
    disabled: boolean;
    resultCount: number;
    onKeyword: (value: string) => void;
    onSearch: () => void;
  }

  let { keyword, searching, disabled, resultCount, onKeyword, onSearch }: Props = $props();

  function submit(event: SubmitEvent) {
    event.preventDefault();
    onSearch();
  }
</script>

<form class="flex items-center gap-3 border-b border-gray-200 bg-white px-5 py-4" onsubmit={submit}>
  <div class="relative min-w-0 flex-1">
    <Input
      id="searchInput"
      size="lg"
      class="ps-10"
      value={keyword}
      placeholder="搜索歌曲、歌手、专辑..."
      disabled={disabled}
      autofocus
      oninput={(event) => onKeyword((event.currentTarget as HTMLInputElement).value)}
    />
    <Search class="pointer-events-none absolute left-3 top-3 h-5 w-5 text-gray-400" />
  </div>
  <Button id="searchBtn" type="submit" size="lg" loading={searching} disabled={disabled || searching}>
    搜索
  </Button>
  <div class="w-24 text-right text-sm text-gray-500">
    {#if resultCount > 0}
      共 {resultCount} 首
    {/if}
  </div>
</form>
```

- [ ] **Step 2: Create `SettingsPanel.svelte`**

```svelte
<script lang="ts">
  import { Button, Checkbox, Input, Label, Select } from "flowbite-svelte";
  import { FolderOpen, HardDrive, ShieldCheck } from "@lucide/svelte";
  import type { GuiConfig, SelectItem, ValidOptions } from "../types";
  import { normalizeNumber, toSelectItems, toSimpleSelectItems, withConfigValue } from "../state";

  interface Props {
    config: GuiConfig;
    options: ValidOptions;
    disabled: boolean;
    onConfigChange: (config: GuiConfig) => void;
    onBrowseDirectory: () => void;
    onOpenDirectory: () => void;
    onEnvironmentCheck: () => void;
  }

  let {
    config,
    options,
    disabled,
    onConfigChange,
    onBrowseDirectory,
    onOpenDirectory,
    onEnvironmentCheck
  }: Props = $props();

  const sourceItems: SelectItem[] = $derived(toSelectItems(options.sources));
  const bitrateItems: SelectItem[] = $derived(toSimpleSelectItems(options.bitrates));
  const typeItems: SelectItem[] = [
    { value: "song", name: "单曲" },
    { value: "album", name: "专辑" },
    { value: "playlist", name: "歌单" }
  ];

  function update<K extends keyof GuiConfig>(key: K, value: GuiConfig[K]) {
    onConfigChange(withConfigValue(config, key, value));
  }
</script>

<aside class="flex h-full w-72 shrink-0 flex-col border-r border-gray-200 bg-gray-50 px-4 py-4">
  <div class="mb-5">
    <h1 class="text-lg font-semibold text-gray-950">音乐下载器</h1>
    <p class="mt-1 text-xs text-gray-500">搜索、选择、下载与失败重试</p>
  </div>

  <div class="space-y-4">
    <Label class="space-y-2">
      <span>音乐源</span>
      <Select
        id="sourceSelect"
        items={sourceItems}
        value={config.source}
        disabled={disabled}
        onchange={(event) => update("source", (event.currentTarget as HTMLSelectElement).value)}
      />
    </Label>

    <Label class="space-y-2">
      <span>搜索类型</span>
      <Select
        id="typeSelect"
        items={typeItems}
        value={config.search_type}
        disabled={disabled}
        onchange={(event) => update("search_type", (event.currentTarget as HTMLSelectElement).value)}
      />
    </Label>

    <Label class="space-y-2">
      <span>音质</span>
      <Select
        id="bitrateSelect"
        items={bitrateItems}
        value={config.bitrate}
        disabled={disabled}
        onchange={(event) => update("bitrate", (event.currentTarget as HTMLSelectElement).value)}
      />
    </Label>

    <Label class="space-y-2">
      <span>数量</span>
      <Input
        id="numberInput"
        type="number"
        min="1"
        max="999"
        value={String(config.number)}
        disabled={disabled}
        oninput={(event) => update("number", normalizeNumber((event.currentTarget as HTMLInputElement).value, 20))}
      />
    </Label>

    <div class="grid grid-cols-2 gap-3 pt-1">
      <Checkbox
        id="coverCheck"
        checked={config.download_cover}
        disabled={disabled}
        onchange={(event) => update("download_cover", (event.currentTarget as HTMLInputElement).checked)}
      >
        下载封面
      </Checkbox>
      <Checkbox
        id="lyricCheck"
        checked={config.download_lyric}
        disabled={disabled}
        onchange={(event) => update("download_lyric", (event.currentTarget as HTMLInputElement).checked)}
      >
        下载歌词
      </Checkbox>
    </div>

    <Label class="space-y-2">
      <span>下载目录</span>
      <div class="flex gap-2">
        <Input id="outputDirInput" value={config.output_dir} readonly class="min-w-0 flex-1" />
        <Button id="browseDirBtn" color="alternative" class="shrink-0 px-3" onclick={onBrowseDirectory}>
          <FolderOpen class="h-4 w-4" />
          <span class="sr-only">浏览</span>
        </Button>
      </div>
    </Label>
  </div>

  <div class="mt-auto space-y-2 border-t border-gray-200 pt-4">
    <Button id="openDirBtn" color="alternative" class="w-full justify-center" onclick={onOpenDirectory}>
      <HardDrive class="mr-2 h-4 w-4" />
      打开下载目录
    </Button>
    <Button id="envCheckBtn" color="light" class="w-full justify-center" onclick={onEnvironmentCheck}>
      <ShieldCheck class="mr-2 h-4 w-4" />
      环境检查
    </Button>
  </div>
</aside>
```

- [ ] **Step 3: Create `ResultList.svelte`**

```svelte
<script lang="ts">
  import { Badge, Button, Checkbox } from "flowbite-svelte";
  import { Check, Download, Minus, Music, X } from "@lucide/svelte";
  import EmptyState from "./EmptyState.svelte";
  import type { Song, SongStatus } from "../types";

  interface Props {
    songs: Song[];
    selectedIndices: Set<number>;
    failedIndices: Set<number>;
    statuses: Record<number, SongStatus>;
    browserReady: boolean;
    onToggle: (index: number) => void;
    onSelectAll: () => void;
    onDeselectAll: () => void;
    onDownloadSelected: () => void;
    onRetryFailed: () => void;
  }

  let {
    songs,
    selectedIndices,
    failedIndices,
    statuses,
    browserReady,
    onToggle,
    onSelectAll,
    onDeselectAll,
    onDownloadSelected,
    onRetryFailed
  }: Props = $props();

  function statusClass(status: SongStatus | undefined): string {
    if (!status) return "text-gray-300";
    if (status.state === "success") return "text-green-600";
    if (status.state === "skip") return "text-gray-400";
    if (status.state === "fail") return "text-red-600";
    return "text-blue-600";
  }
</script>

<section class="flex min-h-0 flex-1 flex-col bg-white">
  <div class="flex items-center gap-2 border-b border-gray-200 px-4 py-3">
    <Button
      id="downloadSelectedBtn"
      data-testid="download-selected"
      size="sm"
      disabled={!browserReady || selectedIndices.size === 0}
      onclick={onDownloadSelected}
    >
      下载选中{selectedIndices.size > 0 ? ` (${selectedIndices.size})` : ""}
    </Button>
    <Button
      id="retryFailedBtn"
      data-testid="retry-failed"
      size="sm"
      color="alternative"
      disabled={failedIndices.size === 0}
      onclick={onRetryFailed}
    >
      重试失败{failedIndices.size > 0 ? ` (${failedIndices.size})` : ""}
    </Button>
    <Button id="selectAllBtn" size="sm" color="light" disabled={songs.length === 0} onclick={onSelectAll}>全选</Button>
    <Button id="deselectAllBtn" size="sm" color="light" disabled={songs.length === 0} onclick={onDeselectAll}>取消全选</Button>
  </div>

  {#if songs.length === 0}
    <EmptyState />
  {:else}
    <div id="resultList" class="scrollbar-thin min-h-0 flex-1 overflow-auto">
      {#each songs as song, index}
        <button
          type="button"
          class="grid w-full grid-cols-[32px_52px_minmax(0,1fr)_96px_42px] items-center gap-3 border-b border-gray-100 px-4 py-3 text-left hover:bg-gray-50 {selectedIndices.has(index) ? 'bg-blue-50 hover:bg-blue-50' : ''}"
          onclick={() => onToggle(index)}
        >
          <Checkbox class="pointer-events-none" checked={selectedIndices.has(index)} aria-label={`选择 ${song.name ?? "未知歌曲"}`} />
          <div class="flex h-11 w-11 items-center justify-center overflow-hidden rounded-md bg-gray-100 text-gray-400">
            {#if typeof song.cover === "string" && song.cover.length > 10}
              <img src={song.cover} alt={song.name ?? ""} class="h-full w-full object-cover" loading="lazy" />
            {:else}
              <Music class="h-5 w-5" />
            {/if}
          </div>
          <div class="min-w-0">
            <div class="flex min-w-0 items-center gap-2">
              <span class="truncate text-sm font-semibold text-gray-950">{song.name ?? "未知歌曲"}</span>
              {#if song.source}
                <Badge color="gray" border>{song.source}</Badge>
              {/if}
              {#if song.bitrate === "flac" || song.bitrate === "999"}
                <Badge color="yellow" border>Hi-Res</Badge>
              {/if}
            </div>
            <div class="mt-1 truncate text-xs text-gray-500">
              {song.artist ?? "未知歌手"}{song.album ? ` · ${song.album}` : ""}
            </div>
          </div>
          <div class="text-right text-xs tabular-nums text-gray-500">{song.duration ?? ""}</div>
          <div class="flex justify-center {statusClass(statuses[index])}">
            {#if statuses[index]?.state === "success"}
              <Check class="h-5 w-5" />
            {:else if statuses[index]?.state === "skip"}
              <Minus class="h-5 w-5" />
            {:else if statuses[index]?.state === "fail"}
              <X class="h-5 w-5" />
            {:else if statuses[index]?.state === "queued" || statuses[index]?.state === "downloading"}
              <Download class="h-5 w-5" />
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</section>
```

- [ ] **Step 4: Create utility components**

Create `music_downloader/gui/frontend/src/lib/components/EmptyState.svelte`:

```svelte
<script lang="ts">
  import { Music } from "@lucide/svelte";
</script>

<div class="flex h-full flex-col items-center justify-center text-gray-400">
  <Music class="mb-3 h-14 w-14" />
  <p class="text-sm">输入关键词开始搜索</p>
</div>
```

Create `music_downloader/gui/frontend/src/lib/components/DownloadProgress.svelte`:

```svelte
<script lang="ts">
  import { Button, Progressbar } from "flowbite-svelte";
  import { X } from "@lucide/svelte";
  import type { DownloadProgressState } from "../types";
  import { progressPercent } from "../state";

  interface Props {
    progress: DownloadProgressState;
    onCancel: () => void;
  }

  let { progress, onCancel }: Props = $props();
  const percent = $derived(progressPercent(progress.current, progress.total));
</script>

{#if progress.visible}
  <div id="downloadPanel" class="border-t border-gray-200 bg-white px-4 py-3">
    <div class="flex items-center gap-3">
      <div id="progressLabel" class="w-64 truncate text-sm text-gray-600">{progress.label}</div>
      <Progressbar progress={percent} class="min-w-0 flex-1" />
      <div id="progressText" class="w-16 text-right text-sm tabular-nums text-gray-500">{progress.current}/{progress.total}</div>
      <Button id="cancelDownloadBtn" color="red" size="sm" onclick={onCancel}>
        <X class="mr-1 h-4 w-4" />
        取消
      </Button>
    </div>
  </div>
{/if}
```

Create `music_downloader/gui/frontend/src/lib/components/LogPanel.svelte`:

```svelte
<script lang="ts">
  import { Button, Badge } from "flowbite-svelte";
  import type { LogEntry } from "../types";

  interface Props {
    logs: LogEntry[];
    collapsed: boolean;
    onToggle: () => void;
  }

  let { logs, collapsed, onToggle }: Props = $props();

  function colorFor(level: LogEntry["level"]): "gray" | "green" | "yellow" | "red" {
    if (level === "success") return "green";
    if (level === "warn") return "yellow";
    if (level === "error") return "red";
    return "gray";
  }
</script>

<section class="border-t border-gray-200 bg-gray-50 {collapsed ? 'h-10' : 'h-40'}">
  <div class="flex h-10 items-center justify-between px-4">
    <span class="text-xs font-semibold text-gray-500">日志</span>
    <Button id="toggleLogBtn" size="xs" color="light" onclick={onToggle}>{collapsed ? "展开" : "折叠"}</Button>
  </div>
  {#if !collapsed}
    <div id="logContent" class="scrollbar-thin h-[120px] overflow-auto px-4 pb-3 font-mono text-xs">
      {#each logs as entry}
        <div class="flex gap-2 py-0.5">
          <span class="w-20 shrink-0 text-gray-400">[{entry.time}]</span>
          <Badge color={colorFor(entry.level)} border class="h-5 shrink-0">{entry.level}</Badge>
          <span class="min-w-0 break-all text-gray-600">{entry.message}</span>
        </div>
      {/each}
    </div>
  {/if}
</section>
```

Create `music_downloader/gui/frontend/src/lib/components/EnvironmentModal.svelte`:

```svelte
<script lang="ts">
  import { Badge, Modal } from "flowbite-svelte";
  import type { EnvironmentCheck } from "../types";

  interface Props {
    open: boolean;
    checks: EnvironmentCheck[];
    onClose: () => void;
  }

  let { open, checks, onClose }: Props = $props();
</script>

<Modal {open} size="lg" title="环境检查" onclose={onClose}>
  <div id="envModalBody" class="space-y-3">
    {#each checks as check}
      <div class="flex items-start justify-between gap-4 rounded-lg border border-gray-200 p-3">
        <div class="min-w-0">
          <div class="font-semibold text-gray-950">{check.name}</div>
          <div class="mt-1 break-all text-sm text-gray-500">{check.detail}</div>
        </div>
        <Badge color={check.ok ? "green" : "red"} border>{check.ok ? "通过" : "失败"}</Badge>
      </div>
    {/each}
  </div>
</Modal>
```

- [ ] **Step 5: Run component type check**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run check
```

Expected: it fails only because `src/App.svelte` has not been created yet.

- [ ] **Step 6: Commit components**

```powershell
git add music_downloader/gui/frontend/src/lib/components
git commit -m "feat(gui): add svelte gui components"
```

---

### Task 4: Implement App State And Preserve Existing GUI Behavior

**Files:**
- Create: `music_downloader/gui/frontend/src/App.svelte`

- [ ] **Step 1: Create `App.svelte`**

Create `music_downloader/gui/frontend/src/App.svelte`:

```svelte
<script lang="ts">
  import { onMount } from "svelte";
  import { Spinner } from "flowbite-svelte";
  import DownloadProgress from "./lib/components/DownloadProgress.svelte";
  import EnvironmentModal from "./lib/components/EnvironmentModal.svelte";
  import LogPanel from "./lib/components/LogPanel.svelte";
  import ResultList from "./lib/components/ResultList.svelte";
  import SearchBar from "./lib/components/SearchBar.svelte";
  import SettingsPanel from "./lib/components/SettingsPanel.svelte";
  import { getPywebviewApi, onPythonLog, onPythonProgress, waitForPywebview } from "./lib/api";
  import { selectedSongs, timeLabel } from "./lib/state";
  import type {
    DownloadProgressState,
    EnvironmentCheck,
    GuiConfig,
    LogEntry,
    ProgressDetail,
    PywebviewApi,
    Song,
    SongStatus,
    ValidOptions
  } from "./lib/types";

  let api = $state<PywebviewApi | null>(null);
  let config = $state<GuiConfig | null>(null);
  let options = $state<ValidOptions | null>(null);
  let keyword = $state("");
  let songs = $state<Song[]>([]);
  let selectedIndices = $state(new Set<number>());
  let failedIndices = $state(new Set<number>());
  let statuses = $state<Record<number, SongStatus>>({});
  let logs = $state<LogEntry[]>([]);
  let browserReady = $state(false);
  let initializing = $state(true);
  let searching = $state(false);
  let loadingText = $state("正在启动...");
  let currentTaskId = $state<string | null>(null);
  let logCollapsed = $state(false);
  let environmentOpen = $state(false);
  let environmentChecks = $state<EnvironmentCheck[]>([]);
  let progress = $state<DownloadProgressState>({
    visible: false,
    current: 0,
    total: 0,
    label: "准备下载..."
  });
  let logCounter = 0;

  function addLog(message: string, level: LogEntry["level"] = "info") {
    logCounter += 1;
    logs = [...logs, { id: logCounter, time: timeLabel(), message, level }].slice(-500);
  }

  function saveConfig(nextConfig = config) {
    if (!api || !nextConfig) return;
    void api.save_config(nextConfig);
  }

  function setConfig(nextConfig: GuiConfig) {
    config = nextConfig;
    saveConfig(nextConfig);
  }

  async function initialize() {
    try {
      api = await waitForPywebview();
      options = await api.get_valid_options();
      config = await api.get_config();
      addLog("应用启动中...", "info");
      loadingText = "正在启动浏览器并通过 Cloudflare 验证...";
      const result = await api.init_browser();
      browserReady = result.ready;
      addLog(result.ready ? "浏览器就绪，可以开始搜索" : "浏览器初始化失败，请检查 Chrome", result.ready ? "success" : "error");
    } catch (error) {
      addLog(`初始化失败: ${String(error)}`, "error");
    } finally {
      initializing = false;
    }
  }

  async function doSearch() {
    if (!api || !config || searching) return;
    const trimmed = keyword.trim();
    if (!trimmed) {
      addLog("请输入搜索关键词", "warn");
      return;
    }
    searching = true;
    loadingText = "正在搜索...";
    saveConfig();
    try {
      const result = await api.search(trimmed, config.source, config.search_type, config.number);
      songs = result;
      selectedIndices = new Set();
      failedIndices = new Set();
      statuses = {};
      addLog(`找到 ${result.length} 首歌曲`, "success");
    } catch (error) {
      addLog(`搜索失败: ${String(error)}`, "error");
    } finally {
      searching = false;
    }
  }

  function toggleSong(index: number) {
    const next = new Set(selectedIndices);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    selectedIndices = next;
  }

  function selectAll() {
    selectedIndices = new Set(songs.map((_, index) => index));
  }

  function deselectAll() {
    selectedIndices = new Set();
  }

  async function startDownload(indices = selectedIndices) {
    if (!api || !config) return;
    const batch = selectedSongs(songs, indices);
    if (batch.length === 0) {
      addLog("请先选择要下载的歌曲", "warn");
      return;
    }
    addLog(`开始下载 ${batch.length} 首歌曲...`, "info");
    try {
      const taskId = await api.start_download(
        batch,
        config.source,
        config.bitrate,
        config.download_lyric,
        config.download_cover,
        config.output_dir
      );
      currentTaskId = taskId || null;
      const nextStatuses = { ...statuses };
      for (const song of batch) {
        if (typeof song._gui_index === "number") {
          nextStatuses[song._gui_index] = { state: "queued" };
        }
      }
      statuses = nextStatuses;
    } catch (error) {
      addLog(`下载启动失败: ${String(error)}`, "error");
    }
  }

  async function retryFailed() {
    if (failedIndices.size === 0) return;
    const retryIndices = new Set(failedIndices);
    selectedIndices = retryIndices;
    await startDownload(retryIndices);
  }

  function cancelDownload() {
    if (!api || !currentTaskId) return;
    void api.cancel_download(currentTaskId);
    addLog("正在取消下载...", "warn");
  }

  async function browseDirectory() {
    if (!api || !config) return;
    const path = await api.select_directory();
    if (path) {
      setConfig({ ...config, output_dir: path });
    }
  }

  function openDirectory() {
    if (!api || !config) return;
    void api.open_download_dir(config.output_dir);
  }

  async function showEnvironment() {
    if (!api) return;
    loadingText = "检查环境...";
    initializing = true;
    try {
      environmentChecks = await api.check_environment();
      environmentOpen = true;
    } catch (error) {
      addLog(`环境检查失败: ${String(error)}`, "error");
    } finally {
      initializing = false;
    }
  }

  function applyProgress(detail: ProgressDetail) {
    if (detail.type === "start") {
      progress = { visible: true, current: 0, total: detail.total, label: "准备下载..." };
      return;
    }
    if (detail.type === "progress") {
      progress = {
        visible: true,
        current: detail.current,
        total: detail.total,
        label: detail.song_name ? `下载中: ${detail.song_name}` : "下载中..."
      };
      return;
    }
    if (detail.type === "song_done") {
      const nextStatuses = { ...statuses };
      nextStatuses[detail.index] = {
        state: detail.result === "success" ? "success" : detail.result === "skip" ? "skip" : "fail",
        reason: detail.reason,
        path: detail.path
      };
      statuses = nextStatuses;

      const nextFailed = new Set(failedIndices);
      if (detail.result === "fail") {
        nextFailed.add(detail.index);
      } else {
        nextFailed.delete(detail.index);
      }
      failedIndices = nextFailed;
      progress = { ...progress, visible: true, current: detail.current, total: detail.total };
      return;
    }
    if (detail.type === "complete") {
      const total = detail.success + detail.fail + detail.skip;
      progress = { visible: true, current: total, total, label: "下载完成" };
      currentTaskId = null;
      addLog(`下载完成: 成功 ${detail.success} / 失败 ${detail.fail} / 跳过 ${detail.skip}`, detail.fail === 0 ? "success" : "warn");
      window.setTimeout(() => {
        progress = { visible: false, current: 0, total: 0, label: "准备下载..." };
      }, 2000);
    }
  }

  onMount(() => {
    const disposeLog = onPythonLog((detail) => addLog(detail.message, detail.level));
    const disposeProgress = onPythonProgress(applyProgress);
    void initialize();
    return () => {
      disposeLog();
      disposeProgress();
      try {
        getPywebviewApi().shutdown();
      } catch {
        return;
      }
    };
  });
</script>

{#if !config || !options}
  <div class="app-shell flex items-center justify-center bg-gray-100">
    <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-5 py-4 text-sm text-gray-600 shadow-sm">
      <Spinner size="6" />
      {loadingText}
    </div>
  </div>
{:else}
  <div class="app-shell flex bg-gray-100">
    <SettingsPanel
      {config}
      {options}
      disabled={searching}
      onConfigChange={setConfig}
      onBrowseDirectory={browseDirectory}
      onOpenDirectory={openDirectory}
      onEnvironmentCheck={showEnvironment}
    />

    <main class="flex min-w-0 flex-1 flex-col">
      <SearchBar
        {keyword}
        {searching}
        disabled={!browserReady}
        resultCount={songs.length}
        onKeyword={(value) => (keyword = value)}
        onSearch={doSearch}
      />
      <ResultList
        {songs}
        {selectedIndices}
        {failedIndices}
        {statuses}
        {browserReady}
        onToggle={toggleSong}
        onSelectAll={selectAll}
        onDeselectAll={deselectAll}
        onDownloadSelected={() => void startDownload()}
        onRetryFailed={() => void retryFailed()}
      />
      <DownloadProgress {progress} onCancel={cancelDownload} />
      <LogPanel {logs} collapsed={logCollapsed} onToggle={() => (logCollapsed = !logCollapsed)} />
    </main>

    <EnvironmentModal open={environmentOpen} checks={environmentChecks} onClose={() => (environmentOpen = false)} />

    {#if initializing || searching}
      <div id="loadingOverlay" class="fixed inset-0 z-50 flex items-center justify-center bg-white/65 backdrop-blur-sm">
        <div class="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-5 py-4 text-sm text-gray-600 shadow-sm">
          <Spinner size="6" />
          {loadingText}
        </div>
      </div>
    {/if}
  </div>
{/if}
```

- [ ] **Step 2: Run type check**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run check
```

Expected: PASS.

- [ ] **Step 3: Run production frontend build**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run build
```

Expected: PASS and `music_downloader/gui/static/index.html` exists with module assets under `music_downloader/gui/static/assets/`.

- [ ] **Step 4: Commit the application**

```powershell
git add music_downloader/gui/frontend/src music_downloader/gui/static
git commit -m "feat(gui): implement svelte desktop interface"
```

---

### Task 5: Fix Static Asset Lookup And Window Size

**Files:**
- Create: `tests/test_gui_app.py`
- Modify: `music_downloader/gui/app.py`

- [ ] **Step 1: Write static path and window size tests**

Create `tests/test_gui_app.py`:

```python
from __future__ import annotations

from pathlib import Path

from music_downloader.gui import app


def test_candidate_static_dirs_include_module_static_first(tmp_path: Path) -> None:
    module_file = tmp_path / "music_downloader" / "gui" / "app.py"
    executable = tmp_path / "dist" / "music_download.exe"

    candidates = app._candidate_static_dirs(module_file=module_file, executable=executable)

    assert candidates[0] == module_file.parent / "static"
    assert executable.parent / "music_downloader" / "gui" / "static" in candidates
    assert executable.parent / "static" in candidates


def test_get_static_dir_returns_existing_candidate(tmp_path: Path) -> None:
    static_dir = tmp_path / "music_downloader" / "gui" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    result = app._get_static_dir(
        module_file=tmp_path / "music_downloader" / "gui" / "app.py",
        executable=tmp_path / "dist" / "music_download.exe",
    )

    assert result == str(static_dir)


def test_window_size_constants_match_designed_minimum() -> None:
    assert app.DEFAULT_WINDOW_SIZE == (1280, 800)
    assert app.MIN_WINDOW_SIZE == (1200, 750)
```

- [ ] **Step 2: Run the tests and confirm failure**

Run:

```powershell
python -m pytest tests/test_gui_app.py -q
```

Expected: FAIL because `_candidate_static_dirs`, `DEFAULT_WINDOW_SIZE`, and `MIN_WINDOW_SIZE` do not exist yet.

- [ ] **Step 3: Replace `app.py` static path logic**

Modify `music_downloader/gui/app.py` to use this structure:

```python
"""GUI application entry point.

Creates the pywebview window, loads the frontend, and starts the event loop.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

DEFAULT_WINDOW_SIZE = (1280, 800)
MIN_WINDOW_SIZE = (1200, 750)


def _candidate_static_dirs(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> list[Path]:
    """Return possible GUI static directories for source and Nuitka builds."""
    module_path = Path(module_file if module_file is not None else __file__).resolve()
    executable_path = Path(executable if executable is not None else sys.argv[0]).resolve()

    candidates = [
        module_path.parent / "static",
        executable_path.parent / "music_downloader" / "gui" / "static",
        executable_path.parent / "static",
    ]

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            unique_candidates.append(candidate)
            seen.add(candidate)
    return unique_candidates


def _get_static_dir(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> str:
    """Resolve static resources for source, Nuitka standalone, and Nuitka onefile runs."""
    candidates = _candidate_static_dirs(module_file=module_file, executable=executable)
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return str(candidate)
    return str(candidates[0])


def _format_missing_static_message(html_path: str, candidates: list[Path]) -> str:
    checked = "\n".join(f"  - {candidate / 'index.html'}" for candidate in candidates)
    return f"错误: 找不到 GUI 资源文件: {html_path}\n已检查:\n{checked}"


def run_gui() -> None:
    """Start the desktop GUI application."""
    import webview

    from music_downloader.gui.api import MusicApi
    from music_downloader.gui.settings import load_config

    config = load_config()
    api = MusicApi()

    static_dir = _get_static_dir()
    html_path = os.path.join(static_dir, "index.html")

    if not os.path.exists(html_path):
        print(_format_missing_static_message(html_path, _candidate_static_dirs()), file=sys.stderr)
        print("请先构建 GUI 前端，或确认 music_downloader/gui/static/ 包含 index.html", file=sys.stderr)
        sys.exit(1)

    width = int(config.get("window_width", DEFAULT_WINDOW_SIZE[0]))
    height = int(config.get("window_height", DEFAULT_WINDOW_SIZE[1]))
    width = max(width, MIN_WINDOW_SIZE[0])
    height = max(height, MIN_WINDOW_SIZE[1])

    window = webview.create_window(
        title="音乐下载器",
        url=html_path,
        width=width,
        height=height,
        min_size=MIN_WINDOW_SIZE,
        resizable=True,
        js_api=api,
        text_select=True,
    )
    api.set_window(window)

    def on_closing() -> None:
        with contextlib.suppress(Exception):
            api.shutdown()

    if window is not None:
        window.events.closing += on_closing

    webview.start(debug=False)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_gui_app.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit path and window fix**

```powershell
git add music_downloader/gui/app.py tests/test_gui_app.py
git commit -m "fix(gui): resolve packaged static assets"
```

---

### Task 6: Integrate Frontend Build Into Nuitka Packaging

**Files:**
- Create: `tests/test_build_script.py`
- Modify: `scripts/build_exe.ps1`

- [ ] **Step 1: Add build script assertions**

Create `tests/test_build_script.py`:

```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_script_runs_frontend_build_before_nuitka() -> None:
    script = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")

    assert "$frontendDir" in script
    assert "npm --prefix $frontendDir install" in script
    assert "npm --prefix $frontendDir run build" in script
    assert "$staticIndex" in script
    assert "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static" in script
```

- [ ] **Step 2: Run the test and confirm failure**

Run:

```powershell
python -m pytest tests/test_build_script.py -q
```

Expected: FAIL because `scripts/build_exe.ps1` does not run the frontend build yet.

- [ ] **Step 3: Add frontend build phase**

Modify `scripts/build_exe.ps1` after the build dependency install block and before `$env:NUITKA_CACHE_DIR = ...`:

```powershell
$frontendDir = Join-Path $ProjectRoot "music_downloader/gui/frontend"
$staticIndex = Join-Path $ProjectRoot "music_downloader/gui/static/index.html"
if (Test-Path $frontendDir) {
    $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npmCommand) {
        throw "npm was not found. Install Node.js before building the GUI exe."
    }

    if (-not $SkipInstall) {
        npm --prefix $frontendDir install
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install frontend dependencies (exit $LASTEXITCODE)"
        }
    } elseif (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        throw "Frontend dependencies are missing. Run npm --prefix music_downloader/gui/frontend install, or build without -SkipInstall."
    }

    npm --prefix $frontendDir run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed (exit $LASTEXITCODE)"
    }

    if (-not (Test-Path $staticIndex)) {
        throw "Frontend build did not produce expected artifact: $staticIndex"
    }
} else {
    Write-Host "No frontend source directory found. Using existing GUI static assets." -ForegroundColor Yellow
}
```

- [ ] **Step 4: Run build-script test**

Run:

```powershell
python -m pytest tests/test_build_script.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit build integration**

```powershell
git add scripts/build_exe.ps1 tests/test_build_script.py
git commit -m "build(gui): compile svelte assets before nuitka"
```

---

### Task 7: Update Static Frontend Tests

**Files:**
- Modify: `tests/test_gui_static.py`

- [ ] **Step 1: Replace static test content**

Replace `tests/test_gui_static.py` with:

```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "music_downloader/gui/static"
FRONTEND_SRC = ROOT / "music_downloader/gui/frontend/src"


def test_vite_static_entry_exists() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="app"' in html
    assert 'type="module"' in html
    assert "assets/" in html


def test_vite_static_assets_exist() -> None:
    assets_dir = STATIC / "assets"

    assert assets_dir.exists()
    assert any(path.suffix == ".js" for path in assets_dir.iterdir())
    assert any(path.suffix == ".css" for path in assets_dir.iterdir())


def test_retry_failed_controls_exist_in_svelte_source() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SRC.rglob("*.svelte"))

    assert 'id="retryFailedBtn"' in source
    assert 'data-testid="retry-failed"' in source
    assert "failedIndices" in source
    assert "retryFailed" in source
```

- [ ] **Step 2: Build frontend**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run build
```

Expected: PASS.

- [ ] **Step 3: Run static tests**

Run:

```powershell
python -m pytest tests/test_gui_static.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit static tests and generated assets**

```powershell
git add tests/test_gui_static.py music_downloader/gui/static
git commit -m "test(gui): validate generated vite assets"
```

---

### Task 8: Update README And Project Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update dependency section**

In `README.md`, update the dependency paragraph to include Node.js for GUI source builds:

```markdown
运行依赖：`playwright`、`mutagen`、`rich`、`typer`、`pydantic`、`pywebview`。

如果需要从源码重建 GUI 前端或打包 exe，还需要安装 Node.js 和 npm。GUI 前端使用 Vite、Svelte、TypeScript、Flowbite Svelte、Tailwind CSS 和 @lucide/svelte，构建产物输出到 `music_downloader/gui/static/`。
```

- [ ] **Step 2: Add frontend build command**

In the development or build section, add:

````markdown
重建 GUI 静态资源：

```powershell
npm --prefix music_downloader/gui/frontend install
npm --prefix music_downloader/gui/frontend run build
```

源码运行 GUI 会加载 `music_downloader/gui/static/index.html`。打包脚本会在 Nuitka 之前自动运行前端构建，并继续把 `music_downloader/gui/static/` 打进 exe。
````

- [ ] **Step 3: Update GUI window size note**

Add this sentence near the GUI usage section:

```markdown
GUI 默认窗口大小为 `1280x800`，最小窗口大小为 `1200x750`。
```

- [ ] **Step 4: Commit README update**

```powershell
git add README.md
git commit -m "docs(gui): document svelte frontend build"
```

---

### Task 9: Run Verification Suite And Fix Integration Breakage

**Files:**
- Modify only files touched by earlier tasks if a verification command reports a concrete failure.

- [ ] **Step 1: Run frontend check**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run check
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
npm --prefix music_downloader/gui/frontend run build
```

Expected: PASS.

- [ ] **Step 3: Run Python tests**

Run:

```powershell
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Run Python lint and type checks**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

Expected: all commands PASS.

- [ ] **Step 5: Run local GUI source smoke check**

Run:

```powershell
python music_download.py --check-env
```

Expected: command completes and reports environment status without Python exceptions.

- [ ] **Step 6: Build exe without reinstalling dependencies**

Run:

```powershell
.\scripts\build_exe.ps1 -SkipInstall
```

Expected: PASS and `dist/music_download.exe` exists.

- [ ] **Step 7: Verify compiled exe can run a non-GUI command**

Run:

```powershell
.\dist\music_download.exe --check-env
```

Expected: command completes and does not print `找不到 GUI 资源文件`.

- [ ] **Step 8: Confirm verification did not leave uncommitted changes**

Run:

```powershell
git status --short
```

Expected: no output. If output appears, identify the failed verification command, return to the task that owns the changed file, make the smallest fix there, rerun that task's exact verification command, and commit with that task's file-specific `git add` command.

---

### Task 10: Manual GUI Smoke Test

**Files:**
- Modify only files with confirmed smoke-test failures.

- [ ] **Step 1: Launch source GUI**

Run:

```powershell
python music_download.py --gui
```

Expected: window opens at no smaller than `1200x750`, loads the Svelte UI, and shows the browser initialization state.

- [ ] **Step 2: Test search**

In the GUI:

```text
输入关键词: Beyond
音乐源: 网易云音乐
搜索类型: 单曲
数量: 20
点击: 搜索
```

Expected: results appear in the main list or a clear browser/Cloudflare error appears in logs.

- [ ] **Step 3: Test selection and download start**

In the GUI:

```text
选择第一首结果
点击: 下载选中
```

Expected: progress bar appears and the selected row moves through queued/downloading/success/skip/fail status.

- [ ] **Step 4: Test retry control**

If a row fails, click `重试失败`.

Expected: only failed rows are selected for retry and `重试失败` disables again when no failed rows remain.

- [ ] **Step 5: Test environment modal**

Click `环境检查`.

Expected: modal opens with each environment check and visible pass/fail badges.

- [ ] **Step 6: Launch compiled GUI**

Run:

```powershell
.\dist\music_download.exe
```

Expected: compiled GUI opens and does not print `找不到 GUI 资源文件`.

- [ ] **Step 7: Confirm smoke testing did not leave uncommitted changes**

Run:

```powershell
git status --short
```

Expected: no output. If output appears, identify the failed smoke-test step, return to the task that owns the changed file, make the smallest fix there, rerun that smoke-test step, and commit with that task's file-specific `git add` command.

---

## Self-Review Notes

- Spec coverage: tasks cover Svelte/Vite migration, TypeScript, Flowbite Svelte, pywebview retention, feature parity, window sizing, static output location, Nuitka resource packaging, README updates, automated verification, and manual smoke testing.
- Scope: the plan is one GUI/frontend migration project and does not change CLI or backend download semantics.
- Type consistency: frontend contracts use `GuiConfig`, `ValidOptions`, `Song`, `ProgressDetail`, `LogEntry`, and `EnvironmentCheck` consistently across API wrapper, state helpers, components, and `App.svelte`.
- Static-resource consistency: Vite emits to `music_downloader/gui/static/`, `app.py` resolves that directory, and `build_exe.ps1` keeps the existing Nuitka include-data directory.
