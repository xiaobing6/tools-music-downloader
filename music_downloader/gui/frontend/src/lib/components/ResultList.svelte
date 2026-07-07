<script lang="ts">
  import { Badge } from "flowbite-svelte";
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
  import type { Song, SongStatus } from "../types";

  type IndexCollection = Set<number> | number[];
  type StatusCollection = Map<number, SongStatus> | Record<number, SongStatus> | SongStatus[];

  interface Props {
    songs: Song[];
    selectedIndices: IndexCollection;
    failedIndices: IndexCollection;
    statuses: StatusCollection;
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

  let selectedCount = $derived(collectionSize(selectedIndices));
  let failedCount = $derived(collectionSize(failedIndices));

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

<section class="flex h-full min-h-0 flex-col rounded-lg border border-slate-200 bg-white">
  <div class="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
    <div>
      <h2 class="text-base font-semibold text-slate-950">搜索结果</h2>
      <p class="mt-0.5 text-xs text-slate-500">已选择 {selectedCount} 首</p>
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
    <div class="min-h-0 flex-1 divide-y divide-slate-100 overflow-auto scrollbar-thin">
      {#each songs as song, index}
        {@const status = statusFor(index)}
        <label
          class="grid w-full cursor-pointer grid-cols-[auto_48px_1fr_auto] items-center gap-3 px-4 py-3 text-left transition hover:bg-slate-50"
        >
          <input
            class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            type="checkbox"
            checked={hasIndex(selectedIndices, index)}
            aria-label={`选择 ${song.name ?? "歌曲"}`}
            onchange={() => {
              onToggle(index);
            }}
          />
          <span class="flex h-12 w-12 items-center justify-center overflow-hidden rounded-md bg-slate-100 text-slate-400">
            {#if song.cover}
              <img class="h-full w-full object-cover" src={song.cover} alt="" />
            {:else}
              <Music size={22} aria-hidden="true" />
            {/if}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-sm font-semibold text-slate-950">
              {song.name ?? "未知歌曲"}
            </span>
            <span class="mt-1 block truncate text-xs text-slate-500">
              {song.artist ?? "未知歌手"}{song.album ? ` / ${song.album}` : ""}
            </span>
            <span class="mt-2 flex flex-wrap items-center gap-2">
              {#if song.source}
                <Badge color="blue" rounded>{song.source}</Badge>
              {/if}
              {#if isHiRes(song)}
                <Badge color="green" rounded>Hi-Res</Badge>
              {/if}
              {#if status}
                <span class="inline-flex items-center gap-1 text-xs text-slate-500" title={status.reason}>
                  {#if status.state === "success"}
                    <CheckCircle2 class="text-emerald-600" size={15} aria-hidden="true" />
                  {:else if status.state === "skip"}
                    <SkipForward class="text-slate-500" size={15} aria-hidden="true" />
                  {:else if status.state === "fail"}
                    <XCircle class="text-red-600" size={15} aria-hidden="true" />
                  {:else if status.state === "downloading"}
                    <LoaderCircle class="animate-spin text-blue-600" size={15} aria-hidden="true" />
                  {:else}
                    <Clock3 class="text-amber-600" size={15} aria-hidden="true" />
                  {/if}
                  {statusLabel(status)}
                </span>
              {/if}
            </span>
          </span>
          <span class="whitespace-nowrap text-xs text-slate-500">{song.duration ?? ""}</span>
        </label>
      {/each}
    </div>
  {/if}
</section>
