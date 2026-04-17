import { useState, type ReactNode } from "react";
import { emitUxEvent, type ViewportMode } from "../../lib/uxTelemetry";

type BottomTrayProps = {
  role: string;
  viewportMode: ViewportMode;
  sessionIdHash: string;
  selectionContextId: string;
  compactSummary: ReactNode;
  tabs: Array<{ id: string; title: string; content: ReactNode }>;
};

export function BottomTray({ role, viewportMode, sessionIdHash, selectionContextId, compactSummary, tabs }: BottomTrayProps) {
  const [activeTabId, setActiveTabId] = useState<string | null>(tabs[0]?.id ?? null);

  function selectTab(tabId: string) {
    setActiveTabId((current) => {
      const next = current === tabId ? null : tabId;
      emitUxEvent(next ? "tray_opened" : "tray_collapsed", {
        role,
        panelOrTabId: tabId,
        viewportMode,
        sessionIdHash,
        timestamp: Date.now(),
      });
      if (next) {
        emitUxEvent("tray_tab_switched", {
          role,
          panelOrTabId: tabId,
          viewportMode,
          sessionIdHash,
          timestamp: Date.now(),
        });
      } else if (selectionContextId) {
        emitUxEvent("selection_persisted_after_collapse", {
          role,
          panelOrTabId: selectionContextId,
          viewportMode,
          sessionIdHash,
          timestamp: Date.now(),
        });
      }
      return next;
    });
  }

  return (
    <section className="ux-bottom-tray panel">
      <div className="ux-compact-summary">{compactSummary}</div>
      <div className="ux-tray-tabs">
        {tabs.map((tab) => (
          <button key={tab.id} className="ux-tab-toggle" aria-expanded={activeTabId === tab.id} onClick={() => selectTab(tab.id)}>
            {tab.title}
          </button>
        ))}
      </div>
      {tabs.map((tab) =>
        activeTabId === tab.id ? (
          <div key={tab.id} className="ux-tray-content">
            {tab.content}
          </div>
        ) : null,
      )}
    </section>
  );
}
