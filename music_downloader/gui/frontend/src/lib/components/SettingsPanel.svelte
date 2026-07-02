<script lang="ts">
  import { Folder, HardDrive, ShieldCheck } from "@lucide/svelte";
  import type { GuiConfig, SelectItem, ValidOptions } from "../types";
  import {
    normalizeNumber,
    toSelectItems,
    toSimpleSelectItems,
    withConfigValue
  } from "../state";

  interface Props {
    config: GuiConfig;
    options: ValidOptions;
    disabled: boolean;
    onConfigChange: (config: GuiConfig) => void;
    onBrowseDirectory: () => void;
    onOpenDirectory: () => void;
    onEnvironmentCheck: () => void;
  }

  let {
    config,
    options,
    disabled,
    onConfigChange,
    onBrowseDirectory,
    onOpenDirectory,
    onEnvironmentCheck
  }: Props = $props();

  const typeLabels: Record<string, string> = {
    song: "单曲",
    album: "专辑",
    playlist: "歌单"
  };

  let sourceItems: SelectItem[] = $derived(toSelectItems(options.sources));
  let typeItems: SelectItem[] = $derived(
    options.search_types.map((value) => ({ value, name: typeLabels[value] ?? value }))
  );
  let bitrateItems: SelectItem[] = $derived(toSimpleSelectItems(options.bitrates));

  function update<K extends keyof GuiConfig>(key: K, value: GuiConfig[K]) {
    onConfigChange(withConfigValue(config, key, value));
  }
</script>

<section class="space-y-5 rounded-lg border border-slate-200 bg-white p-5">
  <div>
    <h1 class="text-xl font-semibold text-slate-950">音乐下载器</h1>
    <p class="mt-1 text-sm text-slate-500">搜索、选择并下载音乐文件</p>
  </div>

  <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
    <label class="space-y-1.5 text-sm font-medium text-slate-700" for="sourceSelect">
      音源
      <select
        id="sourceSelect"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        value={config.source}
        disabled={disabled}
        onchange={(event) => update("source", event.currentTarget.value)}
      >
        {#each sourceItems as item}
          <option value={item.value} disabled={item.disabled}>{item.name}</option>
        {/each}
      </select>
    </label>

    <label class="space-y-1.5 text-sm font-medium text-slate-700" for="typeSelect">
      类型
      <select
        id="typeSelect"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        value={config.search_type}
        disabled={disabled}
        onchange={(event) => update("search_type", event.currentTarget.value)}
      >
        {#each typeItems as item}
          <option value={item.value}>{item.name}</option>
        {/each}
      </select>
    </label>

    <label class="space-y-1.5 text-sm font-medium text-slate-700" for="bitrateSelect">
      音质
      <select
        id="bitrateSelect"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        value={config.bitrate}
        disabled={disabled}
        onchange={(event) => update("bitrate", event.currentTarget.value)}
      >
        {#each bitrateItems as item}
          <option value={item.value}>{item.name}</option>
        {/each}
      </select>
    </label>

    <label class="space-y-1.5 text-sm font-medium text-slate-700" for="numberInput">
      数量
      <input
        id="numberInput"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        type="number"
        min="1"
        value={config.number}
        disabled={disabled}
        onchange={(event) => update("number", normalizeNumber(event.currentTarget.value, config.number))}
      />
    </label>
  </div>

  <div class="flex flex-wrap gap-5">
    <label class="inline-flex items-center gap-2 text-sm font-medium text-slate-700" for="coverCheck">
      <input
        id="coverCheck"
        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
        type="checkbox"
        checked={config.download_cover}
        disabled={disabled}
        onchange={(event) => update("download_cover", event.currentTarget.checked)}
      />
      下载封面
    </label>
    <label class="inline-flex items-center gap-2 text-sm font-medium text-slate-700" for="lyricCheck">
      <input
        id="lyricCheck"
        class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
        type="checkbox"
        checked={config.download_lyric}
        disabled={disabled}
        onchange={(event) => update("download_lyric", event.currentTarget.checked)}
      />
      下载歌词
    </label>
  </div>

  <div class="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
    <label class="space-y-1.5 text-sm font-medium text-slate-700" for="outputDirInput">
      下载目录
      <input
        id="outputDirInput"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
        type="text"
        value={config.output_dir}
        disabled={disabled}
        onchange={(event) => update("output_dir", event.currentTarget.value)}
      />
    </label>
    <button
      id="browseDirBtn"
      class="inline-flex h-10 items-center justify-center gap-2 self-end rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
      type="button"
      disabled={disabled}
      onclick={onBrowseDirectory}
    >
      <Folder size={17} aria-hidden="true" />
      浏览
    </button>
    <button
      id="openDirBtn"
      class="inline-flex h-10 items-center justify-center gap-2 self-end rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-100"
      type="button"
      disabled={disabled}
      onclick={onOpenDirectory}
    >
      <HardDrive size={17} aria-hidden="true" />
      打开
    </button>
    <button
      id="envCheckBtn"
      class="inline-flex h-10 items-center justify-center gap-2 self-end rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      type="button"
      disabled={disabled}
      onclick={onEnvironmentCheck}
    >
      <ShieldCheck size={17} aria-hidden="true" />
      环境检查
    </button>
  </div>
</section>
