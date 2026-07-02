import type { ProgressDetail, PyLogDetail, PywebviewApi } from "./types";

declare global {
  interface Window {
    pywebview?: {
      api: PywebviewApi;
    };
  }
}

export function getPywebviewApi(): PywebviewApi {
  const api = window.pywebview?.api;
  if (!api) {
    throw new Error("pywebview 未就绪，请在桌面窗口中运行");
  }
  return api;
}

export function waitForPywebview(): Promise<PywebviewApi> {
  if (window.pywebview?.api) {
    return Promise.resolve(window.pywebview.api);
  }

  return new Promise((resolve) => {
    window.addEventListener(
      "pywebviewready",
      () => {
        resolve(getPywebviewApi());
      },
      { once: true }
    );
  });
}

export function onPythonLog(handler: (detail: PyLogDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<PyLogDetail>).detail);
  };
  window.addEventListener("py-log", listener);
  return () => window.removeEventListener("py-log", listener);
}

export function onPythonProgress(handler: (detail: ProgressDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<ProgressDetail>).detail);
  };
  window.addEventListener("py-progress", listener);
  return () => window.removeEventListener("py-progress", listener);
}
