import type { GuiConfig, OptionItem, SelectItem, Song } from "./types";

export function toSelectItems(options: OptionItem[]): SelectItem[] {
  return options.map((item) => ({ value: item.value, name: item.label }));
}

export function toSimpleSelectItems(values: string[]): SelectItem[] {
  return values.map((value) => ({ value, name: value }));
}

export function normalizeNumber(value: string | number, fallback: number): number {
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }
  return parsed;
}

export function withConfigValue<K extends keyof GuiConfig>(
  config: GuiConfig,
  key: K,
  value: GuiConfig[K]
): GuiConfig {
  return { ...config, [key]: value };
}

export function selectedSongs(songs: Song[], selectedIndices: Set<number>): Song[] {
  return Array.from(selectedIndices)
    .filter((index) => index >= 0 && index < songs.length)
    .map((index) => ({ ...songs[index], _gui_index: index }));
}

export function progressPercent(current: number, total: number): string {
  if (total <= 0) {
    return "0";
  }
  return String(Math.min(100, Math.max(0, Math.round((current / total) * 100))));
}

export function timeLabel(date = new Date()): string {
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}
