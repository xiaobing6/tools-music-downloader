export type StartupStageKey =
  | "launch"
  | "bridge"
  | "config"
  | "browser"
  | "verify"
  | "ready"
  | "failed";

export interface StartupStage {
  key: StartupStageKey;
  progress: number;
  label: string;
  description: string;
  isError?: boolean;
}

export const STARTUP_STAGES: StartupStage[] = [
  {
    key: "launch",
    progress: 8,
    label: "正在启动",
    description: "正在准备音乐下载器"
  },
  {
    key: "bridge",
    progress: 15,
    label: "连接桌面接口",
    description: "正在建立本地应用连接"
  },
  {
    key: "config",
    progress: 35,
    label: "加载基础配置",
    description: "正在读取下载与搜索设置"
  },
  {
    key: "browser",
    progress: 65,
    label: "准备浏览器",
    description: "正在准备搜索与下载环境"
  },
  {
    key: "verify",
    progress: 90,
    label: "验证访问环境",
    description: "正在确认服务可用性"
  },
  {
    key: "ready",
    progress: 100,
    label: "进入首页",
    description: "准备完成"
  },
  {
    key: "failed",
    progress: 100,
    label: "启动未完成",
    description: "请重试，或稍后再打开应用",
    isError: true
  }
];

export function startupProgressForStage(stageKey: StartupStageKey | string): StartupStage {
  return STARTUP_STAGES.find((stage) => stage.key === stageKey) ?? STARTUP_STAGES[0];
}
