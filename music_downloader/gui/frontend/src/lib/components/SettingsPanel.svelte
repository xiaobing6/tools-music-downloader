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

<section class="settings-panel">
  <div class="quick-settings grid gap-3 sm:grid-cols-3">
    <label class="field-stack text-sm font-medium text-slate-700" for="sourceSelect">
      音源
      <select
        id="sourceSelect"
        name="source"
        autocomplete="off"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 transition-colors disabled:bg-slate-100"
        value={config.source}
        disabled={disabled}
        onchange={(event) => update("source", event.currentTarget.value)}
      >
        {#each sourceItems as item}
          <option value={item.value} disabled={item.disabled}>{item.name}</option>
        {/each}
      </select>
    </label>

    <label class="field-stack text-sm font-medium text-slate-700" for="typeSelect">
      类型
      <select
        id="typeSelect"
        name="search_type"
        autocomplete="off"
        class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 transition-colors disabled:bg-slate-100"
        value={config.search_type}
        disabled={disabled}
        onchange={(event) => update("search_type", event.currentTarget.value)}
      >
        {#each typeItems as item}
          <option value={item.value}>{item.name}</option>
        {/each}
      </select>
    </label>

    <label class="field-stack text-sm font-medium text-slate-700" for="numberInput">
      结果数量
      <input
        id="numberInput"
        name="number"
        autocomplete="off"
        class="data-text h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 transition-colors disabled:bg-slate-100"
        type="number"
        min="1"
        inputmode="numeric"
        value={config.number}
        disabled={disabled}
        onchange={(event) => update("number", normalizeNumber(event.currentTarget.value, config.number))}
      />
    </label>

  </div>

  <details class="advanced-settings mt-3 rounded-xl border border-slate-200 bg-slate-50/70">
    <summary
      class="no-select ml-auto flex min-h-10 w-fit cursor-pointer list-none items-center rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 hover:border-blue-200 hover:text-blue-700"
    >
      更多设置
    </summary>

    <div class="grid gap-4 border-t border-slate-200 p-4 lg:grid-cols-[140px_1fr]">
      <label class="field-stack text-sm font-medium text-slate-700" for="bitrateSelect">
        音质
        <select
          id="bitrateSelect"
          name="bitrate"
          autocomplete="off"
          class="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 transition-colors disabled:bg-slate-100"
          value={config.bitrate}
          disabled={disabled}
          onchange={(event) => update("bitrate", event.currentTarget.value)}
        >
          {#each bitrateItems as item}
            <option value={item.value}>{item.name}</option>
          {/each}
        </select>
      </label>

      <div class="flex flex-wrap items-end gap-5 pb-2">
        <label class="inline-flex items-center gap-2 text-sm font-medium text-slate-700" for="coverCheck">
          <input
            id="coverCheck"
            name="download_cover"
            class="h-4 w-4 rounded border-slate-300 text-blue-600 focus-visible:ring-blue-500"
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
            name="download_lyric"
            class="h-4 w-4 rounded border-slate-300 text-blue-600 focus-visible:ring-blue-500"
            type="checkbox"
            checked={config.download_lyric}
            disabled={disabled}
            onchange={(event) => update("download_lyric", event.currentTarget.checked)}
          />
          下载歌词
        </label>
      </div>

      <div class="field-stack text-sm font-medium text-slate-700 lg:col-span-2">
        <label for="outputDirInput">下载目录</label>
        <div class="grid gap-2 lg:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
          <input
            id="outputDirInput"
            name="output_dir"
            autocomplete="off"
            class="select-text h-10 w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 transition-colors disabled:bg-slate-100"
            type="text"
            value={config.output_dir}
            disabled={disabled}
            onchange={(event) => update("output_dir", event.currentTarget.value)}
          />
          <button
            id="browseDirBtn"
            class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-slate-100"
            type="button"
            disabled={disabled}
            onclick={onBrowseDirectory}
          >
            <Folder size={17} aria-hidden="true" />
            浏览
          </button>
          <button
            id="openDirBtn"
            class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-slate-100"
            type="button"
            disabled={disabled}
            onclick={onOpenDirectory}
          >
            <HardDrive size={17} aria-hidden="true" />
            打开
          </button>
          <button
            id="envCheckBtn"
            class="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            type="button"
            disabled={disabled}
            onclick={onEnvironmentCheck}
          >
            <ShieldCheck size={17} aria-hidden="true" />
            环境检查
          </button>
        </div>
      </div>
    </div>
  </details>
</section>
