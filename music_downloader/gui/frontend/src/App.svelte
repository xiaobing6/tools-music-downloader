<script lang="ts">
  import { Music2 } from "@lucide/svelte";
  import { onMount } from "svelte";
  import SettingsPanel from "./lib/components/SettingsPanel.svelte";
  import SearchBar from "./lib/components/SearchBar.svelte";
  import ResultList from "./lib/components/ResultList.svelte";
  import DownloadProgress from "./lib/components/DownloadProgress.svelte";
  import LogPanel from "./lib/components/LogPanel.svelte";
  import EnvironmentModal from "./lib/components/EnvironmentModal.svelte";
  import StartupScreen from "./lib/components/StartupScreen.svelte";
  import CloseConfirmModal from "./lib/components/CloseConfirmModal.svelte";
  import {
    getPywebviewApi,
    onCloseRequest,
    onPythonCover,
    onPythonLog,
    onPythonProgress,
    waitForPywebview
  } from "./lib/api";
  import { selectedSongs, timeLabel } from "./lib/state";
  import { startupProgressForStage, type StartupStageKey } from "./lib/startup";
  import type {
    CoverDetail,
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
  let loadingText = $state("");
  let searchFeedback = $state("");
  let searchAnnouncement = $state("");
  let startupStageKey = $state<StartupStageKey>("launch");
  let currentTaskId = $state<string | null>(null);
  let logCollapsed = $state(true);
  let environmentOpen = $state(false);
  let environmentChecks = $state<EnvironmentCheck[]>([]);
  let closeConfirmOpen = $state(false);
  let activeDownloadIndices = $state<number[]>([]);
  let downloadStarting = $state(false);
  let progress = $state<DownloadProgressState>({
    current: 0,
    total: 0,
    label: "准备下载…"
  });

  let nextLogId = 1;
  let activePreviousStatuses = new Map<number, SongStatus | undefined>();
  const MAX_LOG_ENTRIES = 500;

  let busy = $derived(initializing || searching);
  let startupStage = $derived(startupProgressForStage(startupStageKey));
  let showStartup = $derived(initializing || startupStageKey === "failed" || !config || !options);
  let downloadActive = $derived(
    downloadStarting || currentTaskId !== null || activeDownloadIndices.length > 0
  );
  let canDownload = $derived(browserReady && !busy && !downloadActive);
  const STARTUP_VERIFY_DELAY_MS = 900;
  const STARTUP_READY_DELAY_MS = 220;

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
    loadingText = "";
    startupStageKey = "bridge";
    browserReady = false;
    addLog("正在启动音乐下载器…", "info");

    try {
      await waitForPywebview();
      const pyApi = getPywebviewApi();
      api = pyApi;

      startupStageKey = "config";
      const [validOptions, currentConfig] = await Promise.all([
        pyApi.get_valid_options(),
        pyApi.get_config()
      ]);
      options = validOptions;
      config = currentConfig;

      startupStageKey = "browser";
      const verifyTimer = setTimeout(() => {
        if (startupStageKey === "browser") {
          startupStageKey = "verify";
        }
      }, STARTUP_VERIFY_DELAY_MS);

      try {
        const result = await pyApi.init_browser();
        startupStageKey = "verify";
        browserReady = result.ready;
      } finally {
        clearTimeout(verifyTimer);
      }

      if (!browserReady) {
        startupStageKey = "failed";
        addLog("初始化失败: 浏览器未就绪", "error");
        return;
      }

      startupStageKey = "ready";
      await new Promise((resolve) => setTimeout(resolve, STARTUP_READY_DELAY_MS));
    } catch (error) {
      browserReady = false;
      startupStageKey = "failed";
      addLog(`初始化失败: ${errorMessage(error)}`, "error");
    } finally {
      initializing = false;
      loadingText = "";
    }
  }

  function retryInitialize() {
    void initialize();
  }

  function handleCover(detail: CoverDetail) {
    songs = songs.map((song) =>
      String(song.id ?? "") === detail.id && String(song.source ?? "") === detail.source
        ? { ...song, cover: detail.cover }
        : song
    );
  }

  function handleProgress(detail: ProgressDetail) {
    if (
      detail.type !== "start" &&
      (!currentTaskId || detail.task_id !== currentTaskId || activeDownloadIndices.length === 0)
    ) {
      return;
    }

    if (detail.type === "start") {
      const taskId = detail.task_id.trim();
      if (!taskId || activeDownloadIndices.length === 0) {
        return;
      }
      if (currentTaskId !== null) {
        return;
      }
      currentTaskId = taskId;
      downloadStarting = false;
      progress = {
        current: 0,
        total: detail.total,
        label: "准备下载…"
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
        current: detail.current,
        total: detail.total,
        label: detail.song_name ? `下载中: ${detail.song_name}` : "下载中…"
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
        current: detail.current,
        total: detail.total,
        label: progress.label
      };
      return;
    }

    const total = detail.success + detail.fail + detail.skip;
    restoreUnfinishedActiveStatuses();
    progress = {
      current: total,
      total,
      label: "下载完成"
    };
    clearActiveDownloadState();
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

  function restoreUnfinishedActiveStatuses() {
    const nextStatuses = { ...statuses };
    let changed = false;

    for (const index of activeDownloadIndices) {
      const state = nextStatuses[index]?.state;
      if (state !== "queued" && state !== "downloading") {
        continue;
      }

      const previousStatus = activePreviousStatuses.get(index);
      if (previousStatus) {
        nextStatuses[index] = previousStatus;
      } else {
        delete nextStatuses[index];
      }
      changed = true;
    }

    if (changed) {
      statuses = nextStatuses;
    }
  }

  function clearActiveDownloadState() {
    currentTaskId = null;
    downloadStarting = false;
    activeDownloadIndices = [];
    activePreviousStatuses = new Map();
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
      searchFeedback = "请输入搜索关键词";
      searchAnnouncement = searchFeedback;
      addLog("请输入搜索关键词", "warn");
      return;
    }

    searchFeedback = "";
    searchAnnouncement = "正在搜索";
    searching = true;
    loadingText = "正在搜索…";
    try {
      await saveCurrentConfig();
      const results = await api.search(query, config.source, config.search_type, config.number);
      browserReady = true;
      songs = results;
      selectedIndices = new Set();
      failedIndices = new Set();
      statuses = {};
      searchAnnouncement =
        results.length > 0
          ? `搜索完成，共找到 ${results.length} 首歌曲`
          : "搜索完成，未找到歌曲";
    } catch (error) {
      searchFeedback = "搜索失败，请稍后重试或查看运行日志";
      searchAnnouncement = "搜索失败";
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

    if (downloadActive) {
      addLog("已有下载任务正在运行", "warn");
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
    activePreviousStatuses = markQueued(downloadIndices);
    downloadStarting = true;

    try {
      const taskId = await api.start_download(
        pickedSongs,
        config.source,
        config.bitrate,
        config.download_lyric,
        config.download_cover,
        config.output_dir,
        keyword.trim()
      );
      const normalizedTaskId = taskId.trim();
      if (!normalizedTaskId) {
        throw new Error("后端未返回下载任务 ID");
      }
      if (activeDownloadIndices.length > 0 && currentTaskId === null) {
        currentTaskId = normalizedTaskId;
      }
      downloadStarting = false;
    } catch (error) {
      restoreUnfinishedActiveStatuses();
      clearActiveDownloadState();
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
    addLog("正在取消下载…", "warn");
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

  async function confirmAppClose() {
    await getPywebviewApi().confirm_close();
  }

  onMount(() => {
    const removeLogListener = onPythonLog((detail) => addLog(detail.message, detail.level));
    const removeProgressListener = onPythonProgress(handleProgress);
    const removeCoverListener = onPythonCover(handleCover);
    const removeCloseRequestListener = onCloseRequest(() => {
      closeConfirmOpen = true;
    });

    void initialize();

    return () => {
      removeLogListener();
      removeProgressListener();
      removeCoverListener();
      removeCloseRequestListener();
      shutdownApi();
    };
  });
</script>

{#if showStartup}
  <StartupScreen stage={startupStage} onRetry={retryInitialize} />
{:else if config && options}
  <div class="app-shell workbench-shell text-slate-950">
    <div class="workbench-frame">
      <header class="workbench-command">
        <div class="command-brand">
          <span class="brand-mark no-select" aria-hidden="true">
            <Music2 size={24} strokeWidth={2.25} />
          </span>
          <div class="min-w-0">
            <p class="brand-kicker">LOCAL MUSIC WORKBENCH</p>
            <h1 class="workbench-title">音乐下载器</h1>
          </div>
          <div class="music-track no-select" aria-hidden="true">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <span class="workbench-state no-select">搜索与下载已就绪</span>
        </div>

        <SearchBar
          {keyword}
          {searching}
          feedback={searchFeedback}
          disabled={initializing || downloadActive}
          onKeyword={(value) => {
            keyword = value;
            if (searchFeedback) {
              searchFeedback = "";
              searchAnnouncement = "";
            }
          }}
          onSearch={search}
        />

        <SettingsPanel
          {config}
          {options}
          disabled={busy || downloadActive}
          onConfigChange={handleConfigChange}
          onBrowseDirectory={browseDirectory}
          onOpenDirectory={openDirectory}
          onEnvironmentCheck={checkEnvironment}
        />
      </header>

      <main class="workbench-main items-stretch">
        <section class="results-workspace flex min-h-0 flex-col">
          <div class="min-h-0 flex-1">
            <ResultList
              {songs}
              {selectedIndices}
              {failedIndices}
              {statuses}
              sourceOptions={options.sources}
              searchAnnouncement={searchAnnouncement}
              browserReady={canDownload}
              onToggle={toggleSelection}
              onSelectAll={selectAll}
              onDeselectAll={deselectAll}
              onDownloadSelected={() => startDownload()}
              onRetryFailed={retryFailed}
            />
          </div>
        </section>

        <aside class="activity-rail">
          <DownloadProgress {progress} cancelable={downloadActive} onCancel={cancelDownload} />
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

<CloseConfirmModal bind:open={closeConfirmOpen} onConfirm={confirmAppClose} />

{#if searching}
  <div
    id="loadingOverlay"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/20 backdrop-blur-[1px]"
  >
    <div class="rounded-lg bg-white px-6 py-4 text-sm font-medium text-slate-700 shadow-lg">
      {loadingText || "请稍候…"}
    </div>
  </div>
{/if}
