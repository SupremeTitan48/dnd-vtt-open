import { useMemo, useState } from "react";
import type { ChatKind, RollVisibilityMode } from "../lib/apiClient";
import type { ChatMessage } from "../types";

type Props = {
  messages: ChatMessage[];
  currentPeerId: string;
  canPost: boolean;
  onSend: (payload: { content: string; kind: ChatKind; visibility_mode: RollVisibilityMode; whisper_targets: string[] }) => Promise<void>;
};

const KIND_LABEL: Record<ChatKind, string> = {
  ic: "IC",
  ooc: "OOC",
  emote: "/me",
  system: "SYSTEM",
  whisper: "WHISPER",
  roll: "ROLL",
};

function formatVisibilityLabel(message: ChatMessage): string {
  if (message.kind === "roll") {
    if (message.visibility_mode === "private") return "roll: private";
    if (message.visibility_mode === "gm_only") return "roll: gm only";
    return "roll: public";
  }
  return message.visibility_mode;
}

function formatWhisperContext(message: ChatMessage): string | null {
  if (message.kind !== "whisper") return null;
  const targets = (message.whisper_targets ?? []).filter(Boolean);
  if (targets.length === 0) return "to hidden recipients";
  return `to ${targets.join(", ")}`;
}

export function ChatPanel({ messages, currentPeerId, canPost, onSend }: Props) {
  const [content, setContent] = useState("");
  const [kind, setKind] = useState<ChatKind>("ic");
  const [visibilityMode, setVisibilityMode] = useState<RollVisibilityMode>("public");
  const [whisperTargets, setWhisperTargets] = useState("");

  const sorted = useMemo(() => [...messages].sort((a, b) => (a.revision ?? 0) - (b.revision ?? 0)), [messages]);

  async function submit() {
    const trimmed = content.trim();
    if (!trimmed || !canPost) return;
    let parsedKind: ChatKind = kind;
    let parsedContent = trimmed;
    let parsedVisibility: RollVisibilityMode = visibilityMode;
    if (trimmed.startsWith("/me ")) {
      parsedKind = "emote";
      parsedContent = trimmed.slice(4).trim();
    } else if (trimmed.startsWith("/ooc ")) {
      parsedKind = "ooc";
      parsedContent = trimmed.slice(5).trim();
    } else if (trimmed.startsWith("/pr ")) {
      parsedKind = "roll";
      parsedVisibility = "private";
      parsedContent = trimmed.slice(4).trim();
    } else if (trimmed.startsWith("/roll ")) {
      parsedKind = "roll";
      parsedContent = trimmed.slice(6).trim();
    } else if (trimmed.startsWith("/r ")) {
      parsedKind = "roll";
      parsedContent = trimmed.slice(3).trim();
    }
    if (!parsedContent) return;
    await onSend({
      content: parsedContent,
      kind: parsedKind,
      visibility_mode: parsedVisibility,
      whisper_targets: whisperTargets
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
    setContent("");
  }

  return (
    <div className="panel side-panel chat-panel">
      <div className="chat-log">
        {sorted.map((message) => (
          <div key={`${message.message_id}-${message.revision ?? "none"}`} className={`chat-message chat-kind-${message.kind}`}>
            <span className="chat-kind-badge">{KIND_LABEL[message.kind]}</span>
            <span className={`chat-visibility chat-visibility-${message.visibility_mode}`}>{formatVisibilityLabel(message)}</span>
            <span className="chat-author">{message.sender_peer_id ?? "system"}</span>
            {message.sender_peer_id === currentPeerId ? <span className="chat-self">(you)</span> : null}
            {formatWhisperContext(message) ? <span className="chat-target-context">{formatWhisperContext(message)}</span> : null}
            <div className="chat-content">{message.content || "(hidden)"}</div>
          </div>
        ))}
      </div>
      <div className="chat-compose">
        <select value={kind} onChange={(e) => setKind(e.target.value as ChatKind)} disabled={!canPost}>
          <option value="ic">In character</option>
          <option value="ooc">Out of character</option>
          <option value="emote">Emote (/me)</option>
          <option value="whisper">Whisper</option>
          <option value="roll">Roll note</option>
        </select>
        <select value={visibilityMode} onChange={(e) => setVisibilityMode(e.target.value as RollVisibilityMode)} disabled={!canPost}>
          <option value="public">Public</option>
          <option value="private">Private</option>
          <option value="gm_only">GM only</option>
        </select>
        {kind === "whisper" ? (
          <input
            placeholder="Whisper targets (peer ids, comma separated)"
            value={whisperTargets}
            onChange={(e) => setWhisperTargets(e.target.value)}
            disabled={!canPost}
          />
        ) : null}
        <input value={content} onChange={(e) => setContent(e.target.value)} placeholder="Type message..." disabled={!canPost} />
        <button onClick={() => void submit()} disabled={!canPost || !content.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
