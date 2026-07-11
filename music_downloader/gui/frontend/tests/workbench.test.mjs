import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = (relativePath) =>
  readFile(new URL(`../src/${relativePath}`, import.meta.url), "utf8");

test("workbench styles define the approved tokens and responsive activity rail", async () => {
  const css = await source("app.css");
  assert.match(css, /--color-canvas:\s*#f3f7fc/i);
  assert.match(css, /--color-ink:\s*#102033/i);
  assert.match(css, /--color-track:\s*#2563eb/i);
  assert.match(css, /\.workbench-main/);
  assert.match(css, /\.activity-rail/);
  assert.match(css, /@media\s*\(max-width:\s*1179px\)/);
});

test("interactive controls have a focus-visible baseline and body text stays selectable", async () => {
  const css = await source("app.css");
  assert.match(css, /:focus-visible/);
  assert.doesNotMatch(css, /body\s*\{[^}]*user-select:\s*none/s);
  assert.match(css, /\.no-select[^}]*user-select:\s*none/s);
});

test("the main workbench presents search before settings", async () => {
  const app = await source("App.svelte");
  assert.ok(app.indexOf("<SearchBar") < app.indexOf("<SettingsPanel"));
  assert.match(app, /class="music-track/);
  assert.match(app, /class="workbench-command/);
});

test("settings separate quick controls from advanced controls", async () => {
  const settings = await source("lib/components/SettingsPanel.svelte");
  assert.match(settings, /<details/);
  assert.match(settings, /<summary[^>]*>\s*更多设置/);
  assert.ok(settings.indexOf("sourceSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("typeSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("bitrateSelect") < settings.indexOf("<details"));
  assert.ok(settings.indexOf("numberInput") > settings.indexOf("<details"));
});

test("search and settings controls expose stable form metadata", async () => {
  const search = await source("lib/components/SearchBar.svelte");
  const settings = await source("lib/components/SettingsPanel.svelte");
  assert.match(search, /name="keyword"/);
  assert.match(search, /autocomplete="off"/);
  assert.match(search, /搜索歌曲、歌手、专辑…/);
  for (const name of [
    "source",
    "search_type",
    "bitrate",
    "number",
    "download_cover",
    "download_lyric",
    "output_dir"
  ]) {
    assert.match(settings, new RegExp(`name="${name}"`));
  }
});

test("results and activity panels expose stable responsive hooks", async () => {
  const app = await source("App.svelte");
  assert.match(app, /class="workbench-main/);
  assert.match(app, /class="results-workspace/);
  assert.match(app, /class="activity-rail/);
  assert.match(app, /let logCollapsed = \$state\(true\)/);
});

test("download progress is announced without making the entire log live", async () => {
  const progress = await source("lib/components/DownloadProgress.svelte");
  const logs = await source("lib/components/LogPanel.svelte");
  assert.match(progress, /aria-live="polite"/);
  assert.match(progress, /aria-atomic="true"/);
  assert.doesNotMatch(logs, /aria-live=/);
  assert.match(logs, /select-text/);
});

test("album art reserves space and loads lazily", async () => {
  const results = await source("lib/components/ResultList.svelte");
  assert.match(results, /<img[^>]*width="48"[^>]*height="48"[^>]*loading="lazy"/s);
});

test("search overlay exposes an assistive status", async () => {
  const app = await source("App.svelte");
  assert.match(app, /id="loadingOverlay"[^>]*role="status"[^>]*aria-live="polite"/s);
});

test("user-facing loading copy uses the single ellipsis character", async () => {
  const app = await source("App.svelte");
  for (const outdated of [
    "准备下载...",
    "正在启动音乐下载器...",
    "下载中...",
    "正在搜索...",
    "正在取消下载...",
    "请稍候..."
  ]) {
    assert.equal(app.includes(outdated), false);
  }
});
