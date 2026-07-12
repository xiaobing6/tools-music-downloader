<script lang="ts">
  import { Music } from "@lucide/svelte";
</script>

<div class="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 px-6 text-center text-slate-500">
  <div class="rounded-full bg-slate-100 p-4 text-slate-400">
    <Music size={36} aria-hidden="true" />
  </div>
  <p class="max-w-xs text-sm font-semibold text-slate-700">输入歌名、歌手或专辑开始搜索</p>
  <p class="text-xs text-slate-500">结果会显示在这里</p>
</div>
