<script lang="ts">
  import { Progressbar } from "flowbite-svelte";
  import type { DownloadProgressState } from "../types";
  import { progressPercent } from "../state";

  interface Props {
    progress: DownloadProgressState;
    cancelable: boolean;
    onCancel: () => void;
  }

  let { progress, cancelable, onCancel }: Props = $props();
  let percent = $derived(progressPercent(progress.current, progress.total));
</script>

<section id="downloadPanel" class="rounded-lg border border-blue-200 bg-blue-50 p-4">
  <div class="mb-3 flex items-center justify-between gap-3">
    <div class="min-w-0">
      <p id="progressLabel" class="truncate text-sm font-semibold text-blue-950">{progress.label}</p>
      <p id="progressText" class="mt-0.5 text-xs text-blue-700">
        {progress.current} / {progress.total}（{percent}%）
      </p>
    </div>
    {#if cancelable}
      <button
        id="cancelDownloadBtn"
        class="shrink-0 rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-medium text-blue-800 hover:bg-blue-100"
        type="button"
        onclick={onCancel}
      >
        取消
      </button>
    {/if}
  </div>
  <Progressbar progress={percent} color="blue" size="h-2.5" />
</section>
