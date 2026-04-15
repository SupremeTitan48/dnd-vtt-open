import type { CharacterSheet, EncounterTemplate, Session, SessionEvent, Snapshot, Tutorial } from "../types";

const API_BASE = "/api";
export type CommandContext = {
  actor_peer_id?: string;
  actor_role?: "GM" | "AssistantGM" | "Player" | "Observer";
  expected_revision?: number;
  idempotency_key?: string;
};
export type ReadContext = {
  actor_peer_id?: string;
  actor_token?: string;
  actor_role?: "GM" | "AssistantGM" | "Player" | "Observer";
};
export type JoinSessionResponse = {
  session_id: string;
  peers: string[];
  peer_token: string;
};
export type RoleAssignmentResponse = {
  session_id: string;
  peer_id: string;
  role: "GM" | "AssistantGM" | "Player" | "Observer";
  revision: number;
};
export type ActorOwnershipResponse = {
  session_id: string;
  actor_id: string;
  owners: string[];
  revision: number;
};

function appendReadContext(path: string, context?: ReadContext): string {
  if (!context?.actor_peer_id && !context?.actor_role) {
    return path;
  }
  const params = new URLSearchParams();
  if (context.actor_peer_id) params.set("actor_peer_id", context.actor_peer_id);
  if (context.actor_token) params.set("actor_token", context.actor_token);
  if (context.actor_role) params.set("actor_role", context.actor_role);
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}${params.toString()}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`API ${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

export function createSession(sessionName: string, hostPeerId: string): Promise<Session> {
  return request<Session>("/sessions", {
    method: "POST",
    body: JSON.stringify({ session_name: sessionName, host_peer_id: hostPeerId }),
  });
}

export function getSession(sessionId: string, context?: ReadContext): Promise<Session> {
  return request(appendReadContext(`/sessions/${sessionId}`, context));
}

export function joinSession(sessionId: string, peerId: string): Promise<JoinSessionResponse> {
  return request(`/sessions/${sessionId}/join`, {
    method: "POST",
    body: JSON.stringify({ peer_id: peerId }),
  });
}

export function getState(sessionId: string, context?: ReadContext): Promise<{ session_id: string; state: Snapshot }> {
  return request(appendReadContext(`/sessions/${sessionId}/state`, context));
}

export function getEventReplay(sessionId: string, afterRevision: number): Promise<{ session_id: string; events: SessionEvent[] }> {
  return request(`/sessions/${sessionId}/events/replay?after_revision=${afterRevision}`);
}

export function getEventReplayWithContext(
  sessionId: string,
  afterRevision: number,
  context: ReadContext,
): Promise<{ session_id: string; events: SessionEvent[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/events/replay?after_revision=${afterRevision}`, context));
}

export function moveToken(
  sessionId: string,
  tokenId: string,
  x: number,
  y: number,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/move-token`, {
    method: "POST",
    body: JSON.stringify({ token_id: tokenId, x, y, command }),
  });
}

export function assignSessionRole(
  sessionId: string,
  peerId: string,
  role: "GM" | "AssistantGM" | "Player" | "Observer",
  command?: CommandContext,
): Promise<RoleAssignmentResponse> {
  return request(`/sessions/${sessionId}/roles`, {
    method: "POST",
    body: JSON.stringify({ peer_id: peerId, role, command }),
  });
}

export function assignActorOwnership(
  sessionId: string,
  actorId: string,
  peerId: string,
  command?: CommandContext,
): Promise<ActorOwnershipResponse> {
  return request(`/sessions/${sessionId}/actor-ownership`, {
    method: "POST",
    body: JSON.stringify({ actor_id: actorId, peer_id: peerId, command }),
  });
}

export function nextTurn(sessionId: string, command?: CommandContext): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/next-turn`, { method: "POST", body: JSON.stringify({ command }) });
}

export function setInitiative(
  sessionId: string,
  order: string[],
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/initiative`, {
    method: "POST",
    body: JSON.stringify({ order, command }),
  });
}

export function updateActor(
  sessionId: string,
  actorId: string,
  hitPoints?: number,
  addItem?: string,
  addCondition?: string,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/actor-state`, {
    method: "POST",
    body: JSON.stringify({ actor_id: actorId, hit_points: hitPoints, add_item: addItem, add_condition: addCondition, command }),
  });
}

export function setFog(sessionId: string, enabled: boolean, command?: CommandContext): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/fog`, {
    method: "POST",
    body: JSON.stringify({ enabled, command }),
  });
}

export function revealCell(
  sessionId: string,
  x: number,
  y: number,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/reveal-cell`, {
    method: "POST",
    body: JSON.stringify({ x, y, command }),
  });
}

export function paintTerrain(
  sessionId: string,
  x: number,
  y: number,
  terrainType: string,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/paint-terrain`, {
    method: "POST",
    body: JSON.stringify({ x, y, terrain_type: terrainType, command }),
  });
}

export function toggleBlocked(
  sessionId: string,
  x: number,
  y: number,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/toggle-blocked`, {
    method: "POST",
    body: JSON.stringify({ x, y, command }),
  });
}

export function stampAsset(
  sessionId: string,
  x: number,
  y: number,
  assetId: string,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/stamp-asset`, {
    method: "POST",
    body: JSON.stringify({ x, y, asset_id: assetId, command }),
  });
}

export function saveSession(sessionId: string): Promise<{ session_id: string; saved_to: string }> {
  return request(`/sessions/${sessionId}/save`, { method: "POST" });
}

export function loadSession(sessionId: string): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/load`, { method: "POST" });
}

export function getTutorial(): Promise<Tutorial> {
  return request(`/tutorial`);
}

export function importCharacter(
  sessionId: string,
  importFormat: string,
  payload: string,
  tokenId?: string,
  command?: CommandContext,
): Promise<{ session_id: string; character: CharacterSheet; token_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/characters/import`, {
    method: "POST",
    body: JSON.stringify({ import_format: importFormat, payload, token_id: tokenId, command }),
  });
}

export function listCharacters(sessionId: string, context?: ReadContext): Promise<{ session_id: string; characters: CharacterSheet[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/characters`, context));
}

export function setSessionNotes(
  sessionId: string,
  notes: string,
  command?: CommandContext,
): Promise<{ session_id: string; notes: string }> {
  return request(`/sessions/${sessionId}/notes`, {
    method: "PUT",
    body: JSON.stringify({ notes, command }),
  });
}

export function getSessionNotes(sessionId: string, context?: ReadContext): Promise<{ session_id: string; notes: string }> {
  return request(appendReadContext(`/sessions/${sessionId}/notes`, context));
}

export function addEncounterTemplate(
  sessionId: string,
  templateName: string,
  description: string,
  command?: CommandContext,
): Promise<{ session_id: string; encounter_templates: EncounterTemplate[] }> {
  return request(`/sessions/${sessionId}/encounter-templates`, {
    method: "POST",
    body: JSON.stringify({ template_name: templateName, description, command }),
  });
}

export function getEncounterTemplates(sessionId: string, context?: ReadContext): Promise<{ session_id: string; encounter_templates: EncounterTemplate[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/encounter-templates`, context));
}
