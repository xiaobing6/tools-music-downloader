import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import ts from "typescript";

async function loadStartupModule() {
  const sourceUrl = new URL("../src/lib/startup.ts", import.meta.url);
  const source = await readFile(sourceUrl, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022
    }
  });
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(output.outputText).toString(
    "base64"
  )}`;
  return import(moduleUrl);
}

async function readStartupScreenSource() {
  return readFile(new URL("../src/lib/components/StartupScreen.svelte", import.meta.url), "utf8");
}

test("startup stages expose brand-safe progress without diagnostic details", async () => {
  const { STARTUP_STAGES } = await loadStartupModule();

  assert.deepEqual(
    STARTUP_STAGES.map((stage) => [stage.key, stage.progress, stage.label]),
    [
      ["launch", 8, "正在启动"],
      ["bridge", 15, "连接桌面接口"],
      ["config", 35, "加载基础配置"],
      ["browser", 65, "准备浏览器"],
      ["verify", 90, "验证访问环境"],
      ["ready", 100, "进入首页"],
      ["failed", 100, "启动未完成"]
    ]
  );

  const userFacingCopy = STARTUP_STAGES.map(
    (stage) => `${stage.label} ${stage.description}`
  ).join(" ");
  assert.equal(/Cloudflare|Playwright|Chrome|堆栈|trace/i.test(userFacingCopy), false);
});

test("startup stage lookup falls back to the launch stage for unknown input", async () => {
  const { startupProgressForStage } = await loadStartupModule();

  assert.equal(startupProgressForStage("browser").progress, 65);
  assert.equal(startupProgressForStage("missing-stage").key, "launch");
});

test("startup screen matches the approved hero-style mockup without exposing logs", async () => {
  const source = await readStartupScreenSource();

  assert.match(source, /startup-hero/);
  assert.match(source, /startup-mark/);
  assert.match(source, /startup-sound-bars/);
  assert.match(source, /startup-progress/);
  assert.match(source, /startup-wave/);
  assert.doesNotMatch(source, /startup-surface/);
  assert.equal(/日志|log|Cloudflare|Playwright|Chrome/i.test(source), false);
});

test("startup motion respects the user's reduced-motion preference", async () => {
  const source = await readStartupScreenSource();

  assert.match(source, /prefers-reduced-motion:\s*reduce/);
  assert.match(source, /transition-duration:\s*0\.01ms/);
});
