<script lang="ts">
  import { Search } from "@lucide/svelte";

  interface Props {
    keyword: string;
    searching: boolean;
    disabled: boolean;
    resultCount: number;
    onKeyword: (keyword: string) => void;
    onSearch: () => void;
  }

  let {
    keyword,
    searching,
    disabled,
    resultCount,
    onKeyword,
    onSearch
  }: Props = $props();

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    onSearch();
  }
</script>

<form class="flex w-full items-center gap-3" onsubmit={handleSubmit}>
  <div class="relative flex-1">
    <Search
      class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      size={18}
      aria-hidden="true"
    />
    <input
      id="searchInput"
      class="h-11 w-full rounded-lg border border-slate-300 bg-white pl-10 pr-4 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-slate-100"
      type="search"
      value={keyword}
      placeholder="搜索歌曲、歌手、专辑..."
      disabled={disabled || searching}
      oninput={(event) => onKeyword(event.currentTarget.value)}
    />
  </div>
  <button
    id="searchBtn"
    class="inline-flex h-11 items-center gap-2 rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
    type="submit"
    disabled={disabled || searching}
  >
    <Search size={17} aria-hidden="true" />
    {searching ? "搜索中" : "搜索"}
  </button>
  {#if resultCount > 0}
    <span class="whitespace-nowrap text-sm text-slate-500">共 {resultCount} 首</span>
  {/if}
</form>
