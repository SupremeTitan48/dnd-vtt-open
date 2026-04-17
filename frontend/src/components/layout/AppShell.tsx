import { useMemo, type ReactNode } from "react";
import type { ViewportMode } from "../../lib/uxTelemetry";
import { BottomTray } from "./BottomTray";
import { RightDrawer } from "./RightDrawer";

type AppShellProps = {
  role: string;
  sessionIdHash: string;
  selectionContextId: string;
  topBar: ReactNode;
  leftRail: ReactNode;
  mapContent: ReactNode;
  rightSummary: ReactNode;
  rightSections: Array<{ id: string; title: string; content: ReactNode }>;
  traySummary: ReactNode;
  trayTabs: Array<{ id: string; title: string; content: ReactNode }>;
  statusRail: ReactNode;
};

function getViewportMode(width: number): ViewportMode {
  if (width >= 1360) return "wideDesktop";
  if (width >= 1024) return "narrowDesktop";
  if (width >= 900) return "minSupportedWidth";
  return "unsupported";
}

export function AppShell({
  role,
  sessionIdHash,
  selectionContextId,
  topBar,
  leftRail,
  mapContent,
  rightSummary,
  rightSections,
  traySummary,
  trayTabs,
  statusRail,
}: AppShellProps) {
  const viewportMode = useMemo(() => getViewportMode(window.innerWidth), []);
  return (
    <div className={`ux-shell mode-${viewportMode}`}>
      <header className="ux-topbar panel">{topBar}</header>
      <div className="ux-main-grid">
        <div className="ux-left-rail panel">{leftRail}</div>
        <main className="ux-map-surface">{mapContent}</main>
        <RightDrawer
          role={role}
          viewportMode={viewportMode}
          sessionIdHash={sessionIdHash}
          selectionContextId={selectionContextId}
          compactSummary={rightSummary}
          sections={rightSections}
        />
      </div>
      <BottomTray
        role={role}
        viewportMode={viewportMode}
        sessionIdHash={sessionIdHash}
        selectionContextId={selectionContextId}
        compactSummary={traySummary}
        tabs={trayTabs}
      />
      {viewportMode === "unsupported" && <div className="status-line">Window is below supported width for desktop-first shell.</div>}
      {statusRail}
    </div>
  );
}
