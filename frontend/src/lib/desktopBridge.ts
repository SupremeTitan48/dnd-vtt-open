export type DesktopBackendStatus = {
  state: "booting" | "ready" | "error";
  message?: string;
};

export type DesktopConfig = {
  isDesktop: boolean;
  apiBaseUrl: string;
  wsHost: string;
  backendState: DesktopBackendStatus["state"];
  backendMessage?: string;
};

type DesktopApi = {
  getConfig: () => Promise<DesktopConfig>;
  onBackendStatus: (callback: (status: DesktopBackendStatus) => void) => () => void;
};

declare global {
  interface Window {
    dndDesktop?: DesktopApi;
  }
}

let cachedConfig: DesktopConfig | null = null;

export function hasDesktopBridge(): boolean {
  return typeof window !== "undefined" && typeof window.dndDesktop !== "undefined";
}

export async function getDesktopConfig(): Promise<DesktopConfig | null> {
  if (!hasDesktopBridge()) return null;
  if (cachedConfig) return cachedConfig;
  cachedConfig = await window.dndDesktop!.getConfig();
  return cachedConfig;
}

export function setDesktopConfig(config: DesktopConfig | null): void {
  cachedConfig = config;
}

export function getDesktopConfigSync(): DesktopConfig | null {
  return cachedConfig;
}

export function listenDesktopBackendStatus(callback: (status: DesktopBackendStatus) => void): (() => void) | null {
  if (!hasDesktopBridge()) return null;
  return window.dndDesktop!.onBackendStatus(callback);
}
