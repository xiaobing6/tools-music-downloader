<script lang="ts">
  import { Search } from "@lucide/svelte";

  interface Props {
    keyword: string;
    searching: boolean;
    feedback: string;
    disabled: boolean;
    onKeyword: (keyword: string) => void;
    onSearch: () => void;
  }

  let {
    keyword,
    searching,
    feedback,
    disabled,
    onKeyword,
    onSearch
  }: Props = $props();

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    onSearch();
  }
</script>

<form class="w-full" role="search" onsubmit={handleSubmit}>
  <div class="flex w-full flex-wrap items-center gap-3">
    <div class="relative flex-1">
      <Search
        class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
        size={18}
        aria-hidden="true"
      />
      <input
        id="searchInput"
        class="h-12 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-base text-slate-900 shadow-sm transition-[border-color,box-shadow] focus-visible:border-blue-500 disabled:cursor-not-allowed disabled:bg-slate-100"
        type="search"
        name="keyword"
        aria-label="搜索关键词"
        aria-describedby={feedback ? "searchFeedback" : undefined}
        aria-invalid={Boolean(feedback)}
        autocomplete="off"
        value={keyword}
        placeholder="搜索歌曲、歌手、专辑…"
        disabled={disabled || searching}
        oninput={(event) => onKeyword(event.currentTarget.value)}
      />
    </div>
    <button
      id="searchBtn"
      class="inline-flex h-12 items-center gap-2 rounded-xl bg-blue-600 px-6 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      type="submit"
      disabled={disabled || searching}
    >
      <Search size={17} aria-hidden="true" />
      {searching ? "搜索中" : "搜索"}
    </button>
  </div>
  {#if feedback}
    <p id="searchFeedback" class="mt-2 text-sm font-medium text-red-600" role="alert">
      {feedback}
    </p>
  {/if}
</form>
