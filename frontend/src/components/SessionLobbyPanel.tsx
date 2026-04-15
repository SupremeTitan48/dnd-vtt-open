import { useState } from "react";

type Props = {
  onHostSession: (sessionName: string, hostPeerId: string) => Promise<void>;
  onJoinSession: (sessionId: string, peerId: string) => Promise<void>;
  loading: boolean;
};

export function SessionLobbyPanel({ onHostSession, onJoinSession, loading }: Props) {
  const [sessionName, setSessionName] = useState("Web UI Session");
  const [hostPeerId, setHostPeerId] = useState("dm-web");
  const [joinSessionId, setJoinSessionId] = useState("");
  const [joinPeerId, setJoinPeerId] = useState("player-web");

  return (
    <div className="panel side-panel">
      <h3>Session Lobby</h3>
      <div className="form-row">
        <label>Session Name</label>
        <input value={sessionName} onChange={(e) => setSessionName(e.target.value)} />
      </div>
      <div className="form-row">
        <label>Host Peer Id</label>
        <input value={hostPeerId} onChange={(e) => setHostPeerId(e.target.value)} />
      </div>
      <button
        disabled={loading || !sessionName.trim() || !hostPeerId.trim()}
        onClick={() => void onHostSession(sessionName.trim(), hostPeerId.trim())}
      >
        Host Session
      </button>
      <div className="divider" />
      <div className="form-row">
        <label>Join Session Id</label>
        <input value={joinSessionId} onChange={(e) => setJoinSessionId(e.target.value)} />
      </div>
      <div className="form-row">
        <label>Join Peer Id</label>
        <input value={joinPeerId} onChange={(e) => setJoinPeerId(e.target.value)} />
      </div>
      <button
        disabled={loading || !joinSessionId.trim() || !joinPeerId.trim()}
        onClick={() => void onJoinSession(joinSessionId.trim(), joinPeerId.trim())}
      >
        Join Session
      </button>
    </div>
  );
}
