<script lang="ts">
  import { Badge } from "flowbite-svelte";
  import type { LogEntry } from "../types";

  interface Props {
    logs: LogEntry[];
    collapsed: boolean;
    onToggle: () => void;
  }

  let { logs, collapsed, onToggle }: Props = $props();

  const labels: Record<LogEntry["level"], string> = {
    info: "信息",
    success: "成功",
    warn: "警告",
    error: "错误"
  };

  const colors: Record<LogEntry["level"], "blue" | "green" | "yellow" | "red"> = {
    info: "blue",
    success: "green",
    warn: "yellow",
    error: "red"
  };

  const expandedPanelClass =
    "flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white";
  const collapsedPanelClass = "shrink-0 rounded-lg border border-slate-200 bg-white";
</script>

<section class={collapsed ? collapsedPanelClass : expandedPanelClass}>
  <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
    <div>
      <h2 class="text-sm font-semibold text-slate-950">运行日志</h2>
      <p class="mt-0.5 text-xs text-slate-500">{logs.length} 条记录</p>
    </div>
    <button
      id="toggleLogBtn"
      class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      type="button"
      onclick={onToggle}
    >
      {collapsed ? "展开" : "折叠"}
    </button>
  </div>

  {#if !collapsed}
    <div
      id="logContent"
      class="select-text min-h-0 flex-1 space-y-2 overflow-auto p-4 scrollbar-thin"
    >
      {#each logs as log (log.id)}
        <div class="grid grid-cols-[72px_auto_1fr] items-start gap-2 text-xs">
          <span class="data-text pt-0.5 text-slate-400">{log.time}</span>
          <Badge color={colors[log.level]} rounded>{labels[log.level]}</Badge>
          <p class="min-w-0 break-words text-slate-700">{log.message}</p>
        </div>
      {:else}
        <p class="text-sm text-slate-500">暂无日志</p>
      {/each}
    </div>
  {/if}
</section>
