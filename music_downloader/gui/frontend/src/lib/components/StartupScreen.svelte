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
        <Music2 size={76} strokeWidth={2.15} />
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
    display: flex;
    min-height: 100%;
    justify-content: center;
    overflow: hidden;
    color: var(--color-ink);
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
    width: min(560px, calc(100% - 40px));
    margin: 0 auto;
    padding: clamp(116px, 20vh, 190px) 0 clamp(44px, 6vh, 72px);
    text-align: center;
  }

  .startup-mark-wrap {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    width: min(360px, 100%);
    height: clamp(116px, 15vh, 136px);
    margin: 0 auto;
  }

  .startup-mark {
    display: flex;
    width: clamp(108px, 14vh, 128px);
    height: clamp(108px, 14vh, 128px);
    align-items: center;
    justify-content: center;
    color: var(--color-track);
    background: linear-gradient(145deg, #ffffff 0%, #f8fbff 100%);
    border: 1px solid rgba(191, 219, 254, 0.95);
    border-radius: 28px;
    box-shadow:
      0 16px 32px rgba(37, 99, 235, 0.16),
      0 2px 8px rgba(15, 23, 42, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
  }

  .startup-sound-bars {
    position: absolute;
    top: clamp(28px, 4vh, 40px);
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .startup-sound-bars-left {
    right: calc(50% + clamp(64px, 8vh, 78px));
    transform: rotate(180deg);
  }

  .startup-sound-bars-right {
    left: calc(50% + clamp(64px, 8vh, 78px));
  }

  .startup-sound-bars span {
    display: block;
    width: 6px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(59, 130, 246, 0.2), rgba(191, 219, 254, 0.04));
  }

  .startup-sound-bars span:nth-child(1) {
    height: 14px;
    opacity: 0.2;
  }

  .startup-sound-bars span:nth-child(2) {
    height: 32px;
    opacity: 0.34;
  }

  .startup-sound-bars span:nth-child(3) {
    height: 64px;
    opacity: 0.48;
  }

  .startup-sound-bars span:nth-child(4) {
    height: 90px;
    opacity: 0.4;
  }

  .startup-title {
    margin: clamp(22px, 3vh, 28px) 0 0;
    color: var(--color-ink);
    font-size: clamp(42px, 5vw, 48px);
    font-weight: 800;
    line-height: 1.1;
  }

  .startup-subtitle {
    margin: 8px 0 0;
    color: #536579;
    font-size: 20px;
    line-height: 1.35;
  }

  .startup-status {
    width: 100%;
    margin: clamp(36px, 6vh, 52px) auto 0;
    text-align: left;
  }

  .startup-status-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .startup-stage {
    margin: 0;
    color: var(--color-ink);
    font-size: 18px;
    font-weight: 800;
    line-height: 1;
  }

  .startup-percent {
    margin: 0;
    color: var(--color-track);
    font-size: 18px;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .startup-progress {
    height: 12px;
    overflow: hidden;
    background: #dde5ef;
    border-radius: 999px;
  }

  .startup-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-track) 0%, var(--color-wave) 100%);
    border-radius: inherit;
    box-shadow: 0 0 18px rgba(37, 99, 235, 0.3);
    transition: width 500ms ease;
  }

  .startup-description {
    min-height: 28px;
    margin: 18px 0 0;
    color: #536579;
    font-size: 17px;
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
    background: var(--color-track);
    border: 0;
    border-radius: 8px;
    box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
  }

  .startup-wave {
    position: absolute;
    left: -8%;
    right: -8%;
    bottom: -72px;
    height: clamp(190px, 28vh, 260px);
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
    opacity: 0.68;
  }

  .startup-wave::before {
    position: absolute;
    inset: 28px -4% 44px;
    content: "";
    background: linear-gradient(169deg, transparent 0 37%, rgba(255, 255, 255, 0.96) 37.3% 39.6%, transparent 40%),
      linear-gradient(188deg, transparent 0 43%, rgba(219, 234, 254, 0.58) 43.3% 82%, transparent 82.4%);
  }

  @media (prefers-reduced-motion: reduce) {
    .startup-progress-fill {
      transition-duration: 0.01ms;
    }
  }
</style>
