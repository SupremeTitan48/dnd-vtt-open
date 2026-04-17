import { useState, type ReactNode } from "react";
import { emitUxEvent, type ViewportMode } from "../../lib/uxTelemetry";

type RightDrawerProps = {
  role: string;
  viewportMode: ViewportMode;
  sessionIdHash: string;
  selectionContextId: string;
  compactSummary: ReactNode;
  sections: Array<{ id: string; title: string; content: ReactNode }>;
};

export function RightDrawer({ role, viewportMode, sessionIdHash, selectionContextId, compactSummary, sections }: RightDrawerProps) {
  const [expandedSectionId, setExpandedSectionId] = useState<string | null>(sections[0]?.id ?? null);

  function toggleSection(sectionId: string) {
    setExpandedSectionId((current) => {
      const next = current === sectionId ? null : sectionId;
      emitUxEvent(next ? "drawer_opened" : "drawer_collapsed", {
        role,
        panelOrTabId: sectionId,
        viewportMode,
        sessionIdHash,
        timestamp: Date.now(),
      });
      if (!next && selectionContextId) {
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
    <aside className="ux-right-drawer panel">
      <div className="ux-compact-summary">{compactSummary}</div>
      {sections.map((section) => (
        <section key={section.id} className="ux-drawer-section">
          <button
            className="ux-section-toggle"
            aria-expanded={expandedSectionId === section.id}
            onClick={() => toggleSection(section.id)}
          >
            {section.title}
          </button>
          {expandedSectionId === section.id && <div className="ux-section-content">{section.content}</div>}
        </section>
      ))}
    </aside>
  );
}
