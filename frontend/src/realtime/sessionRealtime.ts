import { getEventReplayWithContext, getState, listCharacters, type ReadContext } from "../lib/apiClient";
import { getDesktopConfigSync } from "../lib/desktopBridge";
import type { CharacterSheet, SessionEvent, Snapshot } from "../types";

type RealtimeHandlers = {
  onSnapshot: (snapshot: Snapshot) => void;
  onCharacters: (characters: CharacterSheet[]) => void;
  onEvent?: (event: SessionEvent) => void;
  onStatus?: (status: string) => void;
};

export function connectSessionEvents(
  sessionId: string,
  getCurrentRevision: () => number,
  getReadContext: () => ReadContext,
  handlers: RealtimeHandlers,
): () => void {
  let isClosed = false;
  let lastAppliedRevision = getCurrentRevision();
  const bufferedByRevision = new Map<number, true>();
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;
  let redactionNoticeShown = false;
  function buildWsUrl(): { url: string; hasAuthContext: boolean } {
    const readContext = getReadContext();
    const wsParams = new URLSearchParams();
    if (readContext.actor_peer_id) wsParams.set("actor_peer_id", readContext.actor_peer_id);
    if (readContext.actor_token) wsParams.set("actor_token", readContext.actor_token);
    if (readContext.actor_role) wsParams.set("actor_role", readContext.actor_role);
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const apiHost = getDesktopConfigSync()?.wsHost ?? import.meta.env.VITE_API_WS_HOST ?? `${window.location.hostname}:8000`;
    const query = wsParams.toString();
    return {
      url: `${protocol}://${apiHost}/api/sessions/${sessionId}/events${query ? `?${query}` : ""}`,
      hasAuthContext: Boolean(readContext.actor_peer_id && readContext.actor_token),
    };
  }

  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let activeConnectionNonce = 0;

  async function refreshSnapshotAndCharacters() {
    const context = getReadContext();
    const stateResp = await getState(sessionId, context);
    if (isClosed) return;
    handlers.onSnapshot(stateResp.state);
    lastAppliedRevision = stateResp.state.revision ?? lastAppliedRevision;
    const charsResp = await listCharacters(sessionId, context);
    if (isClosed) return;
    handlers.onCharacters(charsResp.characters);
  }

  function scheduleRefresh() {
    if (refreshTimer) {
      return;
    }
    refreshTimer = setTimeout(() => {
      refreshTimer = null;
      void refreshSnapshotAndCharacters().catch((error) => {
        const messageText = error instanceof Error ? error.message : "Unknown realtime sync failure";
        handlers.onStatus?.(`Realtime sync error: ${messageText}`);
      });
    }, 25);
  }

  function drainContiguousBufferedEvents() {
    let advanced = false;
    while (bufferedByRevision.has(lastAppliedRevision + 1)) {
      bufferedByRevision.delete(lastAppliedRevision + 1);
      lastAppliedRevision += 1;
      advanced = true;
    }
    if (advanced) {
      scheduleRefresh();
    }
  }

  async function applyReplay() {
    const replay = await getEventReplayWithContext(sessionId, lastAppliedRevision, getReadContext());
    if (!replay.events.length) {
      return;
    }
    replay.events
      .map((event) => event.revision)
      .filter((revision): revision is number => typeof revision === "number")
      .sort((a, b) => a - b)
      .forEach((revision) => {
        if (revision > lastAppliedRevision) {
          bufferedByRevision.set(revision, true);
        }
      });
    drainContiguousBufferedEvents();
  }

  function connect() {
    const connectionNonce = ++activeConnectionNonce;
    const { url, hasAuthContext } = buildWsUrl();
    ws = new WebSocket(url);
    ws.onopen = () => {
      if (isClosed || connectionNonce !== activeConnectionNonce) return;
      reconnectAttempts = 0;
      ws?.send("subscribed");
      handlers.onStatus?.("Realtime connected");
      void applyReplay().catch((error) => {
        const messageText = error instanceof Error ? error.message : "Unknown replay sync failure";
        handlers.onStatus?.(`Realtime replay error: ${messageText}`);
      });
    };

    ws.onmessage = async (message) => {
      if (isClosed || connectionNonce !== activeConnectionNonce) return;
      const event = JSON.parse(message.data) as { revision?: number; event_type?: string; payload?: Record<string, unknown> };
      handlers.onEvent?.(event as SessionEvent);
      lastAppliedRevision = Math.max(lastAppliedRevision, getCurrentRevision());

      if (!redactionNoticeShown && event.payload && Object.keys(event.payload).length === 0 && typeof event.event_type === "string") {
        redactionNoticeShown = true;
        handlers.onStatus?.("Some realtime updates are hidden by your current role/ownership permissions.");
      }

      if (typeof event.revision === "number" && event.revision <= lastAppliedRevision) {
        return;
      }

      try {
        if (typeof event.revision !== "number") {
          scheduleRefresh();
          return;
        }
        if (event.revision === lastAppliedRevision + 1) {
          lastAppliedRevision = event.revision;
          drainContiguousBufferedEvents();
          scheduleRefresh();
          return;
        }
        if (event.revision > lastAppliedRevision + 1) {
          bufferedByRevision.set(event.revision, true);
          await applyReplay();
          return;
        }
      } catch (error) {
        const messageText = error instanceof Error ? error.message : "Unknown realtime sync failure";
        handlers.onStatus?.(`Realtime sync error: ${messageText}`);
      }
    };

    ws.onerror = () => {
      if (isClosed || connectionNonce !== activeConnectionNonce) return;
      handlers.onStatus?.("Realtime connection error");
    };
    ws.onclose = (event) => {
      if (connectionNonce !== activeConnectionNonce) return;
      if (isClosed) return;
      if (!hasAuthContext) {
        handlers.onStatus?.("Realtime waiting for valid session token...");
      }
      if (event.code === 1008) {
        // Authentication/authorization close: back off harder to reduce noisy reconnect churn.
        reconnectAttempts = Math.max(reconnectAttempts, 3);
      } else {
        reconnectAttempts += 1;
      }
      const waitMs = Math.min(5000, 250 * 2 ** reconnectAttempts);
      handlers.onStatus?.(`Realtime reconnecting in ${Math.max(1, Math.round(waitMs / 1000))}s`);
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, waitMs);
    };
  }
  connect();

  return () => {
    isClosed = true;
    activeConnectionNonce += 1;
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    ws?.close();
  };
}
