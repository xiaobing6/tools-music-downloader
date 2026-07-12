<script lang="ts">
  import { Modal } from "flowbite-svelte";
  import { LogOut } from "@lucide/svelte";

  interface Props {
    open: boolean;
    onConfirm: () => Promise<void>;
  }

  let { open = $bindable(), onConfirm }: Props = $props();
  let confirming = $state(false);

  async function confirmClose() {
    if (confirming) {
      return;
    }
    confirming = true;
    try {
      await onConfirm();
    } finally {
      confirming = false;
    }
  }
</script>

<Modal
  bind:open
  title="关闭音乐下载器？"
  role="alertdialog"
  aria-describedby="closeConfirmDescription"
  dismissable={!confirming}
  placement="center"
  size="xs"
  class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
  headerClass="border-b-0 px-6 pb-2 pt-6 text-slate-950"
  bodyClass="px-6 py-3"
  footerClass="justify-end gap-2 border-t-0 bg-slate-50/80 px-6 py-4"
>
  <div class="flex items-center gap-3">
    <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
      <LogOut size={21} strokeWidth={2.25} aria-hidden="true" />
    </span>
    <p
      id="closeConfirmDescription"
      data-autofocus
      tabindex="-1"
      class="text-sm text-slate-600 focus:outline-none"
    >
      确定要关闭应用吗？
    </p>
  </div>

  {#snippet footer()}
    <button
      class="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
      type="button"
      disabled={confirming}
      onclick={() => {
        open = false;
      }}
    >
      继续使用
    </button>
    <button
      class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-300"
      type="button"
      disabled={confirming}
      onclick={confirmClose}
    >
      {confirming ? "正在关闭…" : "关闭应用"}
    </button>
  {/snippet}
</Modal>
