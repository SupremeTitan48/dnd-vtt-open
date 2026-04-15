import { useState } from "react";

type Role = "GM" | "AssistantGM" | "Player" | "Observer";

type Props = {
  peers: string[];
  peerRoles: Record<string, Role>;
  actorOwners: Record<string, string[]>;
  actorIds: string[];
  canManagePermissions: boolean;
  onAssignRole: (peerId: string, role: Role) => Promise<void>;
  onAssignOwner: (actorId: string, peerId: string) => Promise<void>;
};

export function PermissionsPanel({
  peers,
  peerRoles,
  actorOwners,
  actorIds,
  canManagePermissions,
  onAssignRole,
  onAssignOwner,
}: Props) {
  const [selectedPeer, setSelectedPeer] = useState<string>(peers[0] ?? "");
  const [selectedRole, setSelectedRole] = useState<Role>("Player");
  const [selectedActor, setSelectedActor] = useState<string>(actorIds[0] ?? "");
  const [selectedOwnerPeer, setSelectedOwnerPeer] = useState<string>(peers[0] ?? "");

  return (
    <div className="panel side-panel">
      <h3>Permissions</h3>
      <div className="form-row">
        <label>Peer</label>
        <select value={selectedPeer} onChange={(e) => setSelectedPeer(e.target.value)} disabled={!peers.length}>
          {peers.map((peerId) => (
            <option key={peerId} value={peerId}>
              {peerId}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>Role</label>
        <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value as Role)}>
          <option value="GM">GM</option>
          <option value="AssistantGM">Assistant GM</option>
          <option value="Player">Player</option>
          <option value="Observer">Observer</option>
        </select>
      </div>
      <button disabled={!canManagePermissions || !selectedPeer} onClick={() => void onAssignRole(selectedPeer, selectedRole)}>
        Assign Role
      </button>

      <div className="divider" />
      <div className="form-row">
        <label>Actor</label>
        <select value={selectedActor} onChange={(e) => setSelectedActor(e.target.value)} disabled={!actorIds.length}>
          {actorIds.map((actorId) => (
            <option key={actorId} value={actorId}>
              {actorId}
            </option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>Owner Peer</label>
        <select value={selectedOwnerPeer} onChange={(e) => setSelectedOwnerPeer(e.target.value)} disabled={!peers.length}>
          {peers.map((peerId) => (
            <option key={peerId} value={peerId}>
              {peerId}
            </option>
          ))}
        </select>
      </div>
      <button disabled={!canManagePermissions || !selectedActor || !selectedOwnerPeer} onClick={() => void onAssignOwner(selectedActor, selectedOwnerPeer)}>
        Assign Actor Owner
      </button>

      <div style={{ marginTop: 10, fontSize: 12, color: "#aab3dd" }}>Current roles</div>
      <ul className="list">
        {peers.map((peerId) => (
          <li key={`role-${peerId}`}>
            {peerId}: {peerRoles[peerId] ?? "Player"}
          </li>
        ))}
      </ul>

      <div style={{ marginTop: 10, fontSize: 12, color: "#aab3dd" }}>Actor owners</div>
      <ul className="list">
        {actorIds.map((actorId) => (
          <li key={`owner-${actorId}`}>
            {actorId}: {(actorOwners[actorId] ?? []).join(", ") || "none"}
          </li>
        ))}
      </ul>
    </div>
  );
}
