import { useState } from "react";
import type { Handout } from "../types";

type Props = {
  handouts: Handout[];
  peers: string[];
  canManage: boolean;
  onCreate: (title: string, body: string) => Promise<void>;
  onUpdate: (handoutId: string, title: string, body: string) => Promise<void>;
  onShare: (
    handoutId: string,
    sharedRoles: string[],
    sharedPeerIds: string[],
    editableRoles: string[],
    editablePeerIds: string[],
  ) => Promise<void>;
};

export function HandoutPanel({ handouts, peers, canManage, onCreate, onUpdate, onShare }: Props) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [sharePeerId, setSharePeerId] = useState(peers[0] ?? "");

  return (
    <div className="panel side-panel">
      <h3>Handouts</h3>
      <input placeholder="Handout title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <textarea
        placeholder="Handout body"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
        style={{ width: "100%", marginTop: 6 }}
      />
      <button
        style={{ marginTop: 6 }}
        disabled={!canManage || !title.trim() || !body.trim()}
        onClick={() => void onCreate(title.trim(), body.trim())}
      >
        Create Handout
      </button>
      <ul className="list" style={{ marginTop: 8 }}>
        {handouts.map((handout) => (
          <li key={handout.handout_id} style={{ marginBottom: 8 }}>
            <div>
              <strong>{handout.title}</strong>
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{handout.body}</div>
            {canManage && (
              <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                <button onClick={() => void onUpdate(handout.handout_id, `${handout.title} (edited)`, handout.body)}>Quick Edit</button>
                <select value={sharePeerId} onChange={(e) => setSharePeerId(e.target.value)} disabled={!peers.length}>
                  {peers.map((peerId) => (
                    <option key={peerId} value={peerId}>
                      {peerId}
                    </option>
                  ))}
                </select>
                <button onClick={() => void onShare(handout.handout_id, ["Player"], [sharePeerId], [], [])}>Share To Player + Peer</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
