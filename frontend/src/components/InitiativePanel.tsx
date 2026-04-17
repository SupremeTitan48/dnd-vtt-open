import type { Snapshot } from "../types";

type Props = {
  snapshot: Snapshot;
  onReorder: (nextOrder: string[]) => Promise<void>;
  canEdit: boolean;
  onFocusCombatant?: (tokenId: string) => void;
};

export function InitiativePanel({ snapshot, onReorder, canEdit, onFocusCombatant }: Props) {
  const { initiative_order, turn_index, round_number } = snapshot.combat;
  const active = initiative_order[turn_index];

  return (
    <div className="panel side-panel">
      <h3>Combat</h3>
      <div>Round: {round_number}</div>
      <div>Active: {active ?? "Not started"}</div>
      <ul className="list" style={{ paddingLeft: 0, listStyle: "none" }}>
        {initiative_order.map((actor, idx) => (
          <li
            key={actor}
            draggable={canEdit}
            onClick={() => onFocusCombatant?.(actor)}
            onDragStart={(e) => e.dataTransfer.setData("text/plain", actor)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={async (e) => {
              if (!canEdit) return;
              e.preventDefault();
              const dragged = e.dataTransfer.getData("text/plain");
              if (!dragged || dragged === actor) return;
              const order = [...initiative_order];
              const from = order.indexOf(dragged);
              const to = order.indexOf(actor);
              if (from < 0 || to < 0) return;
              order.splice(from, 1);
              order.splice(to, 0, dragged);
              await onReorder(order);
            }}
            style={{
              color: idx === turn_index ? "#9bc5ff" : undefined,
              padding: "4px 6px",
              border: "1px solid #3e4566",
              borderRadius: 6,
              marginTop: 6,
              cursor: "grab",
            }}
          >
            {actor}
          </li>
        ))}
      </ul>
      <div style={{ fontSize: 12, color: "#aab3dd", marginTop: 6 }}>
        {canEdit ? "Drag to reorder initiative." : "Read-only initiative view for current role."}
      </div>
    </div>
  );
}
