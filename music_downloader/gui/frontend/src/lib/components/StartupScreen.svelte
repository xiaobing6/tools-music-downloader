<script lang="ts">
  import { Music2, RefreshCw } from "@lucide/svelte";
  import type { StartupStage } from "../startup";

  interface Props {
    stage: StartupStage;
    onRetry: () => void;
  }

  let { stage, onRetry }: Props = $props();
</script>

<main class="startup-hero app-shell">
  <div class="startup-wave" aria-hidden="true"></div>

  <section class="startup-content">
    <div class="startup-mark-wrap" aria-hidden="true">
      <div class="startup-sound-bars startup-sound-bars-left">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span class="startup-mark">
        <Music2 size={92} strokeWidth={2.15} />
      </span>
      <div class="startup-sound-bars startup-sound-bars-right">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>

    <h1 class="startup-title">音乐下载器</h1>
    <p class="startup-subtitle">本地音乐搜索与下载工具</p>

    <div class="startup-status" aria-live="polite">
      <div class="startup-status-row">
        <p class={stage.isError ? "startup-stage startup-stage-error" : "startup-stage"}>
          {stage.label}
        </p>
        <p class={stage.isError ? "startup-percent startup-percent-error" : "startup-percent"}>
          {stage.progress}%
        </p>
      </div>

      <div
        class="startup-progress"
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={stage.progress}
        aria-label={stage.label}
      >
        <div
          class={stage.isError ? "startup-progress-fill startup-progress-fill-error" : "startup-progress-fill"}
          style={`width: ${stage.progress}%`}
        ></div>
      </div>

      <p class="startup-description">{stage.description}</p>

      {#if stage.isError}
        <button class="startup-retry" type="button" onclick={onRetry}>
          <RefreshCw size={17} aria-hidden="true" />
          重试
        </button>
      {/if}
    </div>
  </section>
</main>

<style>
  .startup-hero {
    position: relative;
    overflow: hidden;
    color: #111827;
    background:
      linear-gradient(180deg, rgba(248, 251, 255, 0.92) 0%, rgba(255, 255, 255, 0.98) 48%),
      #f8fbff;
  }

  .startup-hero::before {
    position: absolute;
    inset: 0;
    content: "";
    background:
      radial-gradient(circle at 50% 33%, rgba(59, 130, 246, 0.13), transparent 25%),
      radial-gradient(circle at 8% 4%, rgba(125, 161, 219, 0.12), transparent 24%),
      linear-gradient(180deg, rgba(248, 250, 252, 0.1), rgba(255, 255, 255, 0.9));
    pointer-events: none;
  }

  .startup-content {
    position: relative;
    z-index: 1;
    width: 610px;
    margin: 0 auto;
    padding-top: 300px;
    text-align: center;
  }

  .startup-mark-wrap {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 420px;
    height: 164px;
    margin: 0 auto;
  }

  .startup-mark {
    display: flex;
    width: 156px;
    height: 156px;
    align-items: center;
    justify-content: center;
    color: #2563eb;
    background: linear-gradient(145deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid rgba(191, 219, 254, 0.95);
    border-radius: 32px;
    box-shadow:
      0 22px 42px rgba(37, 99, 235, 0.18),
      0 2px 8px rgba(15, 23, 42, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
  }

  .startup-sound-bars {
    position: absolute;
    top: 48px;
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .startup-sound-bars-left {
    right: 276px;
    transform: rotate(180deg);
  }

  .startup-sound-bars-right {
    left: 276px;
  }

  .startup-sound-bars span {
    display: block;
    width: 8px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(59, 130, 246, 0.2), rgba(191, 219, 254, 0.04));
  }

  .startup-sound-bars span:nth-child(1) {
    height: 18px;
    opacity: 0.2;
  }

  .startup-sound-bars span:nth-child(2) {
    height: 42px;
    opacity: 0.34;
  }

  .startup-sound-bars span:nth-child(3) {
    height: 82px;
    opacity: 0.48;
  }

  .startup-sound-bars span:nth-child(4) {
    height: 116px;
    opacity: 0.4;
  }

  .startup-title {
    margin: 36px 0 0;
    color: #111827;
    font-size: 58px;
    font-weight: 800;
    line-height: 1.1;
  }

  .startup-subtitle {
    margin: 12px 0 0;
    color: #536579;
    font-size: 29px;
    line-height: 1.35;
  }

  .startup-status {
    width: 610px;
    margin: 82px auto 0;
    text-align: left;
  }

  .startup-status-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 23px;
  }

  .startup-stage {
    margin: 0;
    color: #111827;
    font-size: 24px;
    font-weight: 800;
    line-height: 1;
  }

  .startup-percent {
    margin: 0;
    color: #2563eb;
    font-size: 24px;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .startup-progress {
    height: 17px;
    overflow: hidden;
    background: #dde5ef;
    border-radius: 999px;
  }

  .startup-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb 0%, #2f7cf6 100%);
    border-radius: inherit;
    box-shadow: 0 0 18px rgba(37, 99, 235, 0.3);
    transition: width 500ms ease;
  }

  .startup-description {
    min-height: 34px;
    margin: 28px 0 0;
    color: #536579;
    font-size: 23px;
    line-height: 1.45;
  }

  .startup-stage-error,
  .startup-percent-error {
    color: #b91c1c;
  }

  .startup-progress-fill-error {
    background: #ef4444;
    box-shadow: 0 0 18px rgba(239, 68, 68, 0.24);
  }

  .startup-retry {
    display: inline-flex;
    height: 42px;
    align-items: center;
    gap: 8px;
    margin-top: 20px;
    padding: 0 18px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    background: #2563eb;
    border: 0;
    border-radius: 8px;
    box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
  }

  .startup-wave {
    position: absolute;
    left: -8%;
    right: -8%;
    bottom: -40px;
    height: 350px;
    pointer-events: none;
    background:
      repeating-radial-gradient(
        ellipse 880px 250px at 84% 78%,
        transparent 0,
        transparent 16px,
        rgba(96, 165, 250, 0.1) 17px,
        transparent 19px
      ),
      radial-gradient(ellipse 86% 44% at 50% 82%, rgba(219, 234, 254, 0.72), transparent 72%);
    opacity: 0.88;
  }

  .startup-wave::before {
    position: absolute;
    inset: 28px -4% 44px;
    content: "";
    background: linear-gradient(169deg, transparent 0 37%, rgba(255, 255, 255, 0.96) 37.3% 39.6%, transparent 40%),
      linear-gradient(188deg, transparent 0 43%, rgba(219, 234, 254, 0.58) 43.3% 82%, transparent 82.4%);
  }
</style>
