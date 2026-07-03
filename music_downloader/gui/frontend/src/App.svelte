<script lang="ts">
  import { onMount } from "svelte";
  import SettingsPanel from "./lib/components/SettingsPanel.svelte";
  import SearchBar from "./lib/components/SearchBar.svelte";
  import ResultList from "./lib/components/ResultList.svelte";
  import DownloadProgress from "./lib/components/DownloadProgress.svelte";
  import LogPanel from "./lib/components/LogPanel.svelte";
  import EnvironmentModal from "./lib/components/EnvironmentModal.svelte";
  import {
    getPywebviewApi,
    onPythonLog,
    onPythonProgress,
    waitForPywebview
  } from "./lib/api";
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
  let selectedIndices = $state<Set<number>>(new Set());
  let failedIndices = $state<Set<number>>(new Set());
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
  let activeDownloadIndices = $state<number[]>([]);
  let progress = $state<DownloadProgressState>({
    visible: false,
    current: 0,
    total: 0,
    label: "准备下载..."
  });

  let nextLogId = 1;
  let hideProgressTimer: ReturnType<typeof setTimeout> | null = null;
  const MAX_LOG_ENTRIES = 500;

  let busy = $derived(initializing || searching);
  let canDownload = $derived(browserReady && !busy && currentTaskId === null);

  function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
  }

  function addLog(message: string, level: LogEntry["level"] = "info") {
    logs = [
      ...logs,
      {
        id: nextLogId++,
        time: timeLabel(),
        message,
        level
      }
    ].slice(-MAX_LOG_ENTRIES);
  }

  async function initialize() {
    initializing = true;
    loadingText = "正在连接桌面接口...";
    addLog("正在启动音乐下载器...", "info");

    try {
      await waitForPywebview();
      const pyApi = getPywebviewApi();
      api = pyApi;

      loadingText = "正在加载配置...";
      options = await pyApi.get_valid_options();
      config = await pyApi.get_config();

      loadingText = "正在初始化浏览器...";
      addLog("正在初始化浏览器...", "info");
      const result = await pyApi.init_browser();
      browserReady = result.ready;

      if (result.ready) {
        addLog("浏览器已就绪", "success");
      } else {
        addLog("浏览器初始化失败，请检查 Chrome 和网络环境", "error");
      }
    } catch (error) {
      browserReady = false;
      addLog(`初始化失败: ${errorMessage(error)}`, "error");
    } finally {
      initializing = false;
      loadingText = "";
    }
  }

  function handleProgress(detail: ProgressDetail) {
    if (detail.type !== "start" && (!currentTaskId || detail.task_id !== currentTaskId)) {
      return;
    }

    if (detail.type === "start") {
      const taskId = detail.task_id.trim();
      if (!taskId || activeDownloadIndices.length === 0) {
        return;
      }
      if (currentTaskId !== null && currentTaskId !== taskId) {
        return;
      }
      currentTaskId = taskId;
      clearHideProgressTimer();
      progress = {
        visible: true,
        current: 0,
        total: detail.total,
        label: "准备下载..."
      };
      return;
    }

    if (detail.type === "progress") {
      const activeIndex = activeDownloadIndices[detail.current] ?? detail.current;
      statuses = {
        ...statuses,
        [activeIndex]: { state: "downloading" }
      };
      progress = {
        visible: true,
        current: detail.current,
        total: detail.total,
        label: detail.song_name ? `下载中: ${detail.song_name}` : "下载中..."
      };
      return;
    }

    if (detail.type === "song_done") {
      const state = detail.result;
      statuses = {
        ...statuses,
        [detail.index]: {
          state,
          reason: detail.reason,
          path: detail.path
        }
      };

      const nextFailed = new Set(failedIndices);
      if (state === "fail") {
        nextFailed.add(detail.index);
      } else {
        nextFailed.delete(detail.index);
      }
      failedIndices = nextFailed;

      progress = {
        visible: true,
        current: detail.current,
        total: detail.total,
        label: progress.label
      };
      return;
    }

    const total = detail.success + detail.fail + detail.skip;
    progress = {
      visible: true,
      current: total,
      total,
      label: "下载完成"
    };
    currentTaskId = null;
    activeDownloadIndices = [];
    addLog(
      `下载完成: 成功 ${detail.success} / 失败 ${detail.fail} / 跳过 ${detail.skip}`,
      detail.fail > 0 ? "warn" : "success"
    );
    clearHideProgressTimer();
    hideProgressTimer = setTimeout(() => {
      progress = { ...progress, visible: false };
      hideProgressTimer = null;
    }, 2000);
  }

  function clearHideProgressTimer() {
    if (hideProgressTimer) {
      clearTimeout(hideProgressTimer);
      hideProgressTimer = null;
    }
  }

  function shutdownApi() {
    const pyApi = api;
    if (!pyApi) {
      return;
    }
    void pyApi.shutdown().catch(() => undefined);
  }

  function warnConfigSaveFailed() {
    addLog("save_config 返回 false，设置未保存", "warn");
  }

  function markQueued(downloadIndices: number[]): Map<number, SongStatus | undefined> {
    const previousStatuses = new Map<number, SongStatus | undefined>();
    const nextStatuses = { ...statuses };
    for (const index of downloadIndices) {
      if (index >= 0 && index < songs.length) {
        previousStatuses.set(index, statuses[index]);
        nextStatuses[index] = { state: "queued" };
      }
    }
    statuses = nextStatuses;
    return previousStatuses;
  }

  function rollbackQueuedStatuses(previousStatuses: Map<number, SongStatus | undefined>) {
    const nextStatuses = { ...statuses };
    for (const [index, previousStatus] of previousStatuses) {
      if (nextStatuses[index]?.state !== "queued") {
        continue;
      }
      if (previousStatus) {
        nextStatuses[index] = previousStatus;
      } else {
        delete nextStatuses[index];
      }
    }
    statuses = nextStatuses;
  }

  async function handleConfigChange(nextConfig: GuiConfig) {
    config = nextConfig;
    try {
      await saveCurrentConfig();
    } catch (error) {
      addLog(`保存设置失败: ${errorMessage(error)}`, "error");
    }
  }

  async function saveCurrentConfig(): Promise<boolean> {
    if (!api || !config) {
      return false;
    }
    const saved = await api.save_config(config);
    if (!saved) {
      warnConfigSaveFailed();
    }
    return saved;
  }

  async function search() {
    if (!api || !config) {
      addLog("应用尚未初始化完成", "warn");
      return;
    }

    const query = keyword.trim();
    if (!query) {
      addLog("请输入搜索关键词", "warn");
      return;
    }

    searching = true;
    loadingText = "正在搜索...";
    try {
      await saveCurrentConfig();
      const results = await api.search(query, config.source, config.search_type, config.number);
      songs = results;
      selectedIndices = new Set();
      failedIndices = new Set();
      statuses = {};
      addLog(`找到 ${results.length} 首歌曲`, "success");
    } catch (error) {
      addLog(`搜索失败: ${errorMessage(error)}`, "error");
    } finally {
      searching = false;
      loadingText = "";
    }
  }

  function toggleSelection(index: number) {
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

  async function startDownload(indices: Set<number> = selectedIndices) {
    if (!api || !config) {
      addLog("应用尚未初始化完成", "warn");
      return;
    }

    const pickedSongs = selectedSongs(songs, indices);
    if (pickedSongs.length === 0) {
      addLog("请先选择要下载的歌曲", "warn");
      return;
    }

    const downloadIndices = pickedSongs
      .map((song) => song._gui_index)
      .filter((index): index is number => typeof index === "number");
    activeDownloadIndices = downloadIndices;
    const previousStatuses = markQueued(downloadIndices);

    try {
      const taskId = await api.start_download(
        pickedSongs,
        config.source,
        config.bitrate,
        config.download_lyric,
        config.download_cover,
        config.output_dir
      );
      const normalizedTaskId = taskId.trim();
      if (!normalizedTaskId) {
        throw new Error("后端未返回下载任务 ID");
      }
      currentTaskId = normalizedTaskId;
    } catch (error) {
      currentTaskId = null;
      activeDownloadIndices = [];
      rollbackQueuedStatuses(previousStatuses);
      addLog(`下载启动失败: ${errorMessage(error)}`, "error");
    }
  }

  async function retryFailed() {
    if (failedIndices.size === 0) {
      addLog("没有需要重试的失败歌曲", "warn");
      return;
    }
    const retryIndices = new Set(failedIndices);
    selectedIndices = retryIndices;
    await startDownload(retryIndices);
  }

  async function cancelDownload() {
    if (!api || !currentTaskId) {
      return;
    }
    addLog("正在取消下载...", "warn");
    try {
      await api.cancel_download(currentTaskId);
    } catch (error) {
      addLog(`取消下载失败: ${errorMessage(error)}`, "error");
    }
  }

  async function browseDirectory() {
    if (!api || !config) {
      return;
    }

    try {
      const path = await api.select_directory();
      if (!path) {
        return;
      }
      config = { ...config, output_dir: path };
      await saveCurrentConfig();
      addLog(`下载目录已更新: ${path}`, "success");
    } catch (error) {
      addLog(`选择目录失败: ${errorMessage(error)}`, "error");
    }
  }

  async function openDirectory() {
    if (!api || !config) {
      return;
    }

    try {
      await api.open_download_dir(config.output_dir);
    } catch (error) {
      addLog(`打开目录失败: ${errorMessage(error)}`, "error");
    }
  }

  async function checkEnvironment() {
    if (!api) {
      return;
    }

    try {
      const checks = await api.check_environment();
      environmentChecks = checks;
      environmentOpen = true;

      const failed = checks.filter((check) => !check.ok);
      if (failed.length > 0) {
        for (const check of failed) {
          addLog(`环境检查未通过: ${check.name} - ${check.detail}`, "error");
        }
      } else {
        addLog("环境检查通过", "success");
      }
    } catch (error) {
      addLog(`环境检查失败: ${errorMessage(error)}`, "error");
    }
  }

  onMount(() => {
    const removeLogListener = onPythonLog((detail) => addLog(detail.message, detail.level));
    const removeProgressListener = onPythonProgress(handleProgress);

    void initialize();

    return () => {
      removeLogListener();
      removeProgressListener();
      clearHideProgressTimer();
      shutdownApi();
    };
  });
</script>

{#if !config || !options}
  <main class="app-shell flex items-center justify-center bg-slate-100">
    <div class="rounded-lg border border-slate-200 bg-white px-8 py-6 text-center shadow-sm">
      <p class="text-base font-semibold text-slate-950">音乐下载器</p>
      <p class="mt-2 text-sm text-slate-500">{loadingText || "正在加载..."}</p>
    </div>
  </main>
{:else}
  <div class="app-shell overflow-hidden bg-slate-100 text-slate-950">
    <div class="flex h-full flex-col gap-4 p-5">
      <SettingsPanel
        {config}
        {options}
        disabled={busy || currentTaskId !== null}
        onConfigChange={handleConfigChange}
        onBrowseDirectory={browseDirectory}
        onOpenDirectory={openDirectory}
        onEnvironmentCheck={checkEnvironment}
      />

      <main class="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px] gap-4">
        <section class="flex min-h-0 flex-col gap-4">
          <SearchBar
            {keyword}
            {searching}
            disabled={initializing || currentTaskId !== null}
            resultCount={songs.length}
            onKeyword={(value) => {
              keyword = value;
            }}
            onSearch={search}
          />

          <div class="min-h-0 overflow-auto scrollbar-thin">
            <ResultList
              {songs}
              {selectedIndices}
              {failedIndices}
              {statuses}
              browserReady={canDownload}
              onToggle={toggleSelection}
              onSelectAll={selectAll}
              onDeselectAll={deselectAll}
              onDownloadSelected={() => startDownload()}
              onRetryFailed={retryFailed}
            />
          </div>
        </section>

        <aside class="flex min-h-0 flex-col gap-4">
          <DownloadProgress {progress} onCancel={cancelDownload} />
          <LogPanel
            {logs}
            collapsed={logCollapsed}
            onToggle={() => {
              logCollapsed = !logCollapsed;
            }}
          />
        </aside>
      </main>
    </div>

    <EnvironmentModal
      open={environmentOpen}
      checks={environmentChecks}
      onClose={() => {
        environmentOpen = false;
      }}
    />
  </div>
{/if}

{#if initializing || searching}
  <div
    id="loadingOverlay"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/20 backdrop-blur-[1px]"
  >
    <div class="rounded-lg bg-white px-6 py-4 text-sm font-medium text-slate-700 shadow-lg">
      {loadingText || "请稍候..."}
    </div>
  </div>
{/if}
