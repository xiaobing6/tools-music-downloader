<script lang="ts">
  import { Badge, Modal } from "flowbite-svelte";
  import { CheckCircle2, XCircle } from "@lucide/svelte";
  import type { EnvironmentCheck } from "../types";

  interface Props {
    open: boolean;
    checks: EnvironmentCheck[];
    onClose: () => void;
  }

  let { open, checks, onClose }: Props = $props();
</script>

<Modal {open} title="环境检查" dismissable={false} placement="center" size="lg">
  <div id="envModalBody" class="max-h-[60vh] space-y-3 overflow-y-auto overscroll-contain pr-1">
    {#each checks as check}
      <div class="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            {#if check.ok}
              <CheckCircle2 class="text-emerald-600" size={18} aria-hidden="true" />
            {:else}
              <XCircle class="text-red-600" size={18} aria-hidden="true" />
            {/if}
            <p class="font-medium text-slate-950">{check.name}</p>
          </div>
          <p class="mt-1 break-words text-sm text-slate-500">{check.detail}</p>
        </div>
        <Badge color={check.ok ? "green" : "red"} rounded>{check.ok ? "通过" : "失败"}</Badge>
      </div>
    {:else}
      <p class="text-sm text-slate-500">暂无检查结果</p>
    {/each}
  </div>

  {#snippet footer()}
    <button
      class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
      type="button"
      onclick={onClose}
    >
      关闭
    </button>
  {/snippet}
</Modal>
