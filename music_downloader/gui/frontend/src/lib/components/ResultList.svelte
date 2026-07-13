<script lang="ts">
  import {
    CheckCircle2,
    Clock3,
    Download,
    LoaderCircle,
    Music,
    RotateCcw,
    SkipForward,
    XCircle
  } from "@lucide/svelte";
  import EmptyState from "./EmptyState.svelte";
  import type { OptionItem, Song, SongStatus } from "../types";

  type IndexCollection = Set<number> | number[];
  type StatusCollection = Map<number, SongStatus> | Record<number, SongStatus> | SongStatus[];

  interface Props {
    songs: Song[];
    selectedIndices: IndexCollection;
    failedIndices: IndexCollection;
    statuses: StatusCollection;
    sourceOptions: OptionItem[];
    searchAnnouncement: string;
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
    sourceOptions,
    searchAnnouncement,
    browserReady,
    onToggle,
    onSelectAll,
    onDeselectAll,
    onDownloadSelected,
    onRetryFailed
  }: Props = $props();

  let selectedCount = $derived(collectionSize(selectedIndices));
  let failedCount = $derived(collectionSize(failedIndices));
  let sourceLabels = $derived(
    new Map<string, string>(
      sourceOptions.map((option) => [option.value.toLowerCase(), option.label])
    )
  );

  function hasIndex(collection: IndexCollection, index: number): boolean {
    return collection instanceof Set ? collection.has(index) : collection.includes(index);
  }

  function collectionSize(collection: IndexCollection): number {
    return collection instanceof Set ? collection.size : collection.length;
  }

  function statusFor(index: number): SongStatus | undefined {
    if (statuses instanceof Map) {
      return statuses.get(index);
    }
    return statuses[index];
  }

  function isHiRes(song: Song): boolean {
    const bitrate = String(song.bitrate ?? "").toLowerCase();
    return bitrate === "flac" || bitrate === "999";
  }

  function sourceLabel(source: unknown): string {
    const value = String(source ?? "").trim();
    if (!value) {
      return "—";
    }
    return sourceLabels.get(value.toLowerCase()) ?? value;
  }

  function durationLabel(duration: unknown): string {
    const value = String(duration ?? "").trim();
    return value && value !== "--:--" ? value : "—";
  }

  function statusLabel(status: SongStatus): string {
    const labels: Record<SongStatus["state"], string> = {
      queued: "排队中",
      downloading: "下载中",
      success: "成功",
      skip: "跳过",
      fail: "失败"
    };
    return labels[status.state];
  }

</script>

<section class="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
  <span class="sr-only" role="status" aria-live="polite" aria-atomic="true">
    {searchAnnouncement}
  </span>
  <div class="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
    <div>
      <h2 class="text-base font-semibold text-slate-950">搜索结果</h2>
      <p class="mt-0.5 text-xs text-slate-500">共 {songs.length} 首 · 已选择 {selectedCount} 首</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <button
        id="selectAllBtn"
        class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
        type="button"
        disabled={songs.length === 0}
        onclick={onSelectAll}
      >
        全选
      </button>
      <button
        id="deselectAllBtn"
        class="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
        type="button"
        disabled={selectedCount === 0}
        onclick={onDeselectAll}
      >
        取消选择
      </button>
      <button
        id="retryFailedBtn"
        data-testid="retry-failed"
        class="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
        type="button"
        disabled={failedCount === 0 || !browserReady}
        onclick={onRetryFailed}
      >
        <RotateCcw size={16} aria-hidden="true" />
        重试失败
      </button>
      <button
        id="downloadSelectedBtn"
        data-testid="download-selected"
        class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        type="button"
        disabled={selectedCount === 0 || !browserReady}
        onclick={onDownloadSelected}
      >
        <Download size={16} aria-hidden="true" />
        下载选中
      </button>
    </div>
  </div>

  {#if songs.length === 0}
    <EmptyState />
  {:else}
    <div class="result-columns" aria-hidden="true">
      <span></span>
      <span></span>
      <span>歌曲 / 歌手</span>
      <span>专辑</span>
      <span>来源 / 状态</span>
      <span class="text-right">时长</span>
    </div>
    <div class="min-h-0 flex-1 divide-y divide-slate-100 overflow-auto scrollbar-thin">
      {#each songs as song, index}
        {@const status = statusFor(index)}
        {@const selected = hasIndex(selectedIndices, index)}
        <label class="result-row" data-selected={selected}>
          <input
            class="h-4 w-4 rounded border-slate-300 text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
            type="checkbox"
            checked={selected}
            aria-label={`选择 ${song.name ?? "歌曲"}`}
            onchange={() => {
              onToggle(index);
            }}
          />
          <span class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-md bg-slate-100 text-slate-400">
            {#if song.cover}
              <img
                class="h-full w-full object-cover"
                src={song.cover}
                alt=""
                width="40"
                height="40"
                loading="lazy"
              />
            {:else}
              <Music size={20} aria-hidden="true" />
            {/if}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-sm font-semibold text-slate-950">
              {song.name ?? "未知歌曲"}
            </span>
            <span class="mt-0.5 block truncate text-xs text-slate-500">
              {song.artist ?? "未知歌手"}
            </span>
          </span>
          <span class="truncate text-xs text-slate-500" title={song.album ?? ""}>
            {song.album ?? "—"}
          </span>
          <span class="min-w-0 text-xs text-slate-500">
            <span class="flex min-w-0 items-center gap-1.5">
              <span class="truncate">{sourceLabel(song.source)}</span>
              {#if isHiRes(song)}
                <span class="shrink-0 font-medium text-emerald-700">Hi-Res</span>
              {/if}
            </span>
            {#if status}
              <span class="mt-0.5 inline-flex max-w-full items-center gap-1" title={status.reason}>
                {#if status.state === "success"}
                  <CheckCircle2 class="shrink-0 text-emerald-600" size={14} aria-hidden="true" />
                {:else if status.state === "skip"}
                  <SkipForward class="shrink-0 text-slate-500" size={14} aria-hidden="true" />
                {:else if status.state === "fail"}
                  <XCircle class="shrink-0 text-red-600" size={14} aria-hidden="true" />
                {:else if status.state === "downloading"}
                  <LoaderCircle class="shrink-0 animate-spin text-blue-600" size={14} aria-hidden="true" />
                {:else}
                  <Clock3 class="shrink-0 text-amber-600" size={14} aria-hidden="true" />
                {/if}
                <span class="truncate">{statusLabel(status)}</span>
              </span>
            {/if}
          </span>
          <span class="data-text whitespace-nowrap text-right text-xs text-slate-500">
            {durationLabel(song.duration)}
          </span>
        </label>
      {/each}
    </div>
  {/if}
</section>
