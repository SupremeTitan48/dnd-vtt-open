import { useState } from "react";
import type { JournalEntry } from "../types";

type Props = {
  entries: JournalEntry[];
  peers: string[];
  canManage: boolean;
  onCreate: (title: string, content: string) => Promise<void>;
  onUpdate: (entryId: string, title: string, content: string) => Promise<void>;
  onShare: (
    entryId: string,
    sharedRoles: string[],
    sharedPeerIds: string[],
    editableRoles: string[],
    editablePeerIds: string[],
  ) => Promise<void>;
};

export function JournalPanel({ entries, peers, canManage, onCreate, onUpdate, onShare }: Props) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sharePeerId, setSharePeerId] = useState(peers[0] ?? "");

  return (
    <div className="panel side-panel">
      <h3>Journal</h3>
      <input placeholder="Entry title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <textarea
        placeholder="Entry content"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={4}
        style={{ width: "100%", marginTop: 6 }}
      />
      <button
        style={{ marginTop: 6 }}
        disabled={!canManage || !title.trim() || !content.trim()}
        onClick={() => void onCreate(title.trim(), content.trim())}
      >
        Create Entry
      </button>
      <ul className="list" style={{ marginTop: 8 }}>
        {entries.map((entry) => (
          <li key={entry.entry_id} style={{ marginBottom: 8 }}>
            <div>
              <strong>{entry.title}</strong>
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{entry.content}</div>
            {canManage && (
              <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                <button onClick={() => void onUpdate(entry.entry_id, `${entry.title} (edited)`, entry.content)}>Quick Edit</button>
                <select value={sharePeerId} onChange={(e) => setSharePeerId(e.target.value)} disabled={!peers.length}>
                  {peers.map((peerId) => (
                    <option key={peerId} value={peerId}>
                      {peerId}
                    </option>
                  ))}
                </select>
                <button onClick={() => void onShare(entry.entry_id, ["Player"], [sharePeerId], [], [])}>Share To Player + Peer</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
