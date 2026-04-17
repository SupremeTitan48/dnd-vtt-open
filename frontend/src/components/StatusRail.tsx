import { useEffect } from "react";
import { emitUxEvent, type ViewportMode } from "../lib/uxTelemetry";
import type { StatusKey } from "../lib/uxPolicy";
import { getPrimaryStatus } from "../lib/uxPolicy";

type StatusRailProps = {
  role: string;
  viewportMode: ViewportMode;
  sessionIdHash: string;
  statuses: StatusKey[];
};

export function StatusRail({ role, viewportMode, sessionIdHash, statuses }: StatusRailProps) {
  const primary = getPrimaryStatus(statuses);
  const secondary = statuses.filter((item) => item !== primary);

  useEffect(() => {
    emitUxEvent("status_visible", {
      role,
      panelOrTabId: primary,
      viewportMode,
      sessionIdHash,
      timestamp: Date.now(),
    });
    emitUxEvent("status_priority_resolved", {
      role,
      panelOrTabId: primary,
      viewportMode,
      sessionIdHash,
      timestamp: Date.now(),
    });
  }, [role, viewportMode, sessionIdHash, primary]);

  return (
    <footer className="ux-status-rail panel">
      <span className="token-chip status-primary">{primary}</span>
      {secondary.map((item) => (
        <span key={item} className="token-chip">
          {item}
        </span>
      ))}
    </footer>
  );
}
