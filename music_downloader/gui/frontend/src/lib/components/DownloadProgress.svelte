<script lang="ts">
  import { Progressbar } from "flowbite-svelte";
  import type { DownloadProgressState } from "../types";
  import { progressPercent } from "../state";

  interface Props {
    progress: DownloadProgressState;
    onCancel: () => void;
  }

  let { progress, onCancel }: Props = $props();
  let percent = $derived(progressPercent(progress.current, progress.total));
</script>

{#if progress.visible}
  <section id="downloadPanel" class="rounded-lg border border-blue-200 bg-blue-50 p-4">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <p id="progressLabel" class="text-sm font-semibold text-blue-950">{progress.label}</p>
        <p id="progressText" class="mt-0.5 text-xs text-blue-700">
          {progress.current} / {progress.total}（{percent}%）
        </p>
      </div>
      <button
        id="cancelDownloadBtn"
        class="rounded-lg border border-blue-300 bg-white px-3 py-2 text-sm font-medium text-blue-800 hover:bg-blue-100"
        type="button"
        onclick={onCancel}
      >
        取消
      </button>
    </div>
    <Progressbar progress={percent} color="blue" size="h-2.5" />
  </section>
{/if}
