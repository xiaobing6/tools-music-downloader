<script lang="ts">
  import { Music } from "@lucide/svelte";
</script>

<div class="flex min-h-64 flex-1 flex-col items-center justify-center gap-3 text-slate-500">
  <div class="rounded-full bg-slate-100 p-4 text-slate-400">
    <Music size={36} aria-hidden="true" />
  </div>
  <p class="text-sm font-semibold text-slate-700">搜索歌曲或歌手</p>
  <p class="text-xs text-slate-500">结果会显示在这里</p>
</div>
