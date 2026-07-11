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
