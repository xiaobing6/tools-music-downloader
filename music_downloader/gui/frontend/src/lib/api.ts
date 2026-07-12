import type { CoverDetail, ProgressDetail, PyLogDetail, PywebviewApi } from "./types";

export const PYWEBVIEW_READY_TIMEOUT_MS = 15000;
const PYWEBVIEW_NOT_READY_MESSAGE = "pywebview 未就绪，请在桌面窗口中运行";

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
    throw new Error(PYWEBVIEW_NOT_READY_MESSAGE);
  }
  return api;
}

export function waitForPywebview(timeoutMs = PYWEBVIEW_READY_TIMEOUT_MS): Promise<PywebviewApi> {
  if (window.pywebview?.api) {
    return Promise.resolve(window.pywebview.api);
  }

  return new Promise((resolve, reject) => {
    let timer: ReturnType<typeof setTimeout>;

    const cleanup = () => {
      window.removeEventListener("pywebviewready", listener);
      clearTimeout(timer);
    };

    const listener = () => {
      cleanup();
      try {
        resolve(getPywebviewApi());
      } catch (error) {
        reject(error);
      }
    };

    timer = setTimeout(() => {
      cleanup();
      reject(new Error(PYWEBVIEW_NOT_READY_MESSAGE));
    }, timeoutMs);

    window.addEventListener("pywebviewready", listener);
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

export function onPythonCover(handler: (detail: CoverDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<CoverDetail>).detail);
  };
  window.addEventListener("py-cover", listener);
  return () => window.removeEventListener("py-cover", listener);
}

export function onCloseRequest(handler: () => void): () => void {
  const listener = () => handler();
  window.addEventListener("py-close-request", listener);
  return () => window.removeEventListener("py-close-request", listener);
}
