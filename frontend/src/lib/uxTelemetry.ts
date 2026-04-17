export type ViewportMode = "wideDesktop" | "narrowDesktop" | "minSupportedWidth" | "unsupported";

export type UxEventName =
  | "drawer_opened"
  | "drawer_collapsed"
  | "tray_opened"
  | "tray_collapsed"
  | "tray_tab_switched"
  | "status_visible"
  | "status_priority_resolved"
  | "selection_persisted_after_collapse"
  | "role_policy_blocked_action";

export type UxTelemetryPayload = {
  role: string;
  panelOrTabId: string;
  viewportMode: ViewportMode;
  sessionIdHash: string;
  timestamp: number;
};

export function emitUxEvent(event: UxEventName, payload: UxTelemetryPayload): void {
  // Keep Phase 1 telemetry lightweight and local.
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("dnd:ux-event", { detail: { event, payload } }));
  }
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.info("[ux-event]", event, payload);
  }
}
