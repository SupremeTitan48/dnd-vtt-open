import type { Snapshot } from "../types";

type Props = {
  snapshot: Snapshot;
};

export function ActorPanel({ snapshot }: Props) {
  const actors = Object.entries(snapshot.actors);

  return (
    <div className="panel side-panel">
      <h3>Actor State</h3>
      {actors.length === 0 ? (
        <div>No actor state yet.</div>
      ) : (
        actors.map(([actorId, state]) => (
          <div key={actorId} style={{ marginBottom: 10 }}>
            <strong>{actorId}</strong>
            <div>HP: {state.hit_points}</div>
            <div>Items: {state.held_items.join(", ") || "None"}</div>
            <div>Conditions: {state.conditions.join(", ") || "None"}</div>
          </div>
        ))
      )}
    </div>
  );
}
