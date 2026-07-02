export interface GuiConfig {
  source: string;
  search_type: string;
  bitrate: string;
  number: number;
  output_dir: string;
  download_cover: boolean;
  download_lyric: boolean;
  window_width?: number;
  window_height?: number;
}

export interface OptionItem {
  value: string;
  label: string;
}

export interface SelectItem {
  value: string;
  name: string;
  disabled?: boolean;
}

export interface ValidOptions {
  sources: OptionItem[];
  bitrates: string[];
  search_types: string[];
  formats: string[];
}

export interface Song {
  name?: string;
  artist?: string;
  album?: string;
  duration?: string;
  cover?: string;
  source?: string;
  bitrate?: string;
  _gui_index?: number;
  [key: string]: unknown;
}

export interface EnvironmentCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface LogEntry {
  id: number;
  time: string;
  message: string;
  level: "info" | "success" | "warn" | "error";
}

export interface PyLogDetail {
  message: string;
  level: LogEntry["level"];
}

export type ProgressDetail =
  | { type: "start"; task_id: string; total: number }
  | {
      type: "progress";
      task_id: string;
      current: number;
      total: number;
      song_name?: string;
    }
  | {
      type: "song_done";
      task_id: string;
      index: number;
      result: "success" | "skip" | "fail";
      reason?: string;
      path?: string;
      current: number;
      total: number;
    }
  | {
      type: "complete";
      task_id: string;
      success: number;
      fail: number;
      skip: number;
    };

export interface SongStatus {
  state: "queued" | "downloading" | "success" | "skip" | "fail";
  reason?: string;
  path?: string;
}

export interface DownloadProgressState {
  visible: boolean;
  current: number;
  total: number;
  label: string;
}

export interface PywebviewApi {
  get_valid_options(): Promise<ValidOptions>;
  get_config(): Promise<GuiConfig>;
  save_config(config: GuiConfig): Promise<boolean>;
  init_browser(): Promise<{ ready: boolean }>;
  search(keyword: string, source: string, searchType: string, number: number): Promise<Song[]>;
  start_download(
    songs: Song[],
    source: string,
    bitrate: string,
    downloadLyric: boolean,
    downloadCover: boolean,
    outputDir: string
  ): Promise<string>;
  cancel_download(taskId: string): Promise<void>;
  open_download_dir(path?: string): Promise<void>;
  select_directory(): Promise<string>;
  check_environment(): Promise<EnvironmentCheck[]>;
  get_history(): Promise<Record<string, unknown>[]>;
  shutdown(): Promise<void>;
}
