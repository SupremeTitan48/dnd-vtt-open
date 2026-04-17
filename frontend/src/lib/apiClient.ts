import type {
  AssetLibraryItem,
  CharacterSheet,
  EncounterTemplate,
  Handout,
  JournalEntry,
  Macro,
  MacroExecution,
  Plugin,
  RollTemplate,
  RollTemplateRender,
  Session,
  SessionEvent,
  Snapshot,
  Tutorial,
} from "../types";
import { getDesktopConfigSync } from "./desktopBridge";

function getApiBase(): string {
  const desktopApiBase = getDesktopConfigSync()?.apiBaseUrl;
  if (desktopApiBase) return desktopApiBase;
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (typeof envBase === "string" && envBase.trim()) return envBase.trim();
  return "/api";
}
export type CommandContext = {
  actor_peer_id?: string;
  actor_token?: string;
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
  const resp = await fetch(`${getApiBase()}${path}`, {
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

export function createSessionInCampaign(sessionName: string, hostPeerId: string, campaignId: string): Promise<Session> {
  return request<Session>("/sessions", {
    method: "POST",
    body: JSON.stringify({ session_name: sessionName, host_peer_id: hostPeerId, campaign_id: campaignId }),
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

export function hideCell(
  sessionId: string,
  x: number,
  y: number,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/hide-cell`, {
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

export function listJournalEntries(sessionId: string, context?: ReadContext): Promise<{ session_id: string; journal_entries: JournalEntry[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/journal-entries`, context));
}

export function createJournalEntry(
  sessionId: string,
  title: string,
  content: string,
  command?: CommandContext,
): Promise<{ session_id: string; entry: JournalEntry; revision: number }> {
  return request(`/sessions/${sessionId}/journal-entries`, {
    method: "POST",
    body: JSON.stringify({ title, content, command }),
  });
}

export function updateJournalEntry(
  sessionId: string,
  entryId: string,
  title: string,
  content: string,
  command?: CommandContext,
): Promise<{ session_id: string; entry: JournalEntry; revision: number }> {
  return request(`/sessions/${sessionId}/journal-entries/${entryId}`, {
    method: "PUT",
    body: JSON.stringify({ title, content, command }),
  });
}

export function shareJournalEntry(
  sessionId: string,
  entryId: string,
  sharedRoles: string[],
  sharedPeerIds: string[],
  editableRoles: string[],
  editablePeerIds: string[],
  command?: CommandContext,
): Promise<{ session_id: string; entry: JournalEntry; revision: number }> {
  return request(`/sessions/${sessionId}/journal-entries/${entryId}/share`, {
    method: "POST",
    body: JSON.stringify({
      shared_roles: sharedRoles,
      shared_peer_ids: sharedPeerIds,
      editable_roles: editableRoles,
      editable_peer_ids: editablePeerIds,
      command,
    }),
  });
}

export function listHandouts(sessionId: string, context?: ReadContext): Promise<{ session_id: string; handouts: Handout[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/handouts`, context));
}

export function createHandout(
  sessionId: string,
  title: string,
  body: string,
  command?: CommandContext,
): Promise<{ session_id: string; handout: Handout; revision: number }> {
  return request(`/sessions/${sessionId}/handouts`, {
    method: "POST",
    body: JSON.stringify({ title, body, command }),
  });
}

export function updateHandout(
  sessionId: string,
  handoutId: string,
  title: string,
  body: string,
  command?: CommandContext,
): Promise<{ session_id: string; handout: Handout; revision: number }> {
  return request(`/sessions/${sessionId}/handouts/${handoutId}`, {
    method: "PUT",
    body: JSON.stringify({ title, body, command }),
  });
}

export function shareHandout(
  sessionId: string,
  handoutId: string,
  sharedRoles: string[],
  sharedPeerIds: string[],
  editableRoles: string[],
  editablePeerIds: string[],
  command?: CommandContext,
): Promise<{ session_id: string; handout: Handout; revision: number }> {
  return request(`/sessions/${sessionId}/handouts/${handoutId}/share`, {
    method: "POST",
    body: JSON.stringify({
      shared_roles: sharedRoles,
      shared_peer_ids: sharedPeerIds,
      editable_roles: editableRoles,
      editable_peer_ids: editablePeerIds,
      command,
    }),
  });
}

export function listAssets(sessionId: string, context?: ReadContext): Promise<{ session_id: string; assets: AssetLibraryItem[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/assets`, context));
}

export function addAssetLibraryItem(
  sessionId: string,
  item: Omit<AssetLibraryItem, "created_at">,
  command?: CommandContext,
): Promise<{ session_id: string; asset: AssetLibraryItem; revision: number }> {
  return request(`/sessions/${sessionId}/assets`, {
    method: "POST",
    body: JSON.stringify({
      asset_id: item.asset_id,
      name: item.name,
      asset_type: item.asset_type,
      uri: item.uri,
      tags: item.tags,
      license: item.license,
      command,
    }),
  });
}

export function setTokenVisionRadius(
  sessionId: string,
  tokenId: string,
  radius: number,
  command?: CommandContext,
): Promise<{ session_id: string; state: Snapshot }> {
  return request(`/sessions/${sessionId}/token-vision`, {
    method: "POST",
    body: JSON.stringify({ token_id: tokenId, radius, command }),
  });
}

export function listMacros(sessionId: string, context?: ReadContext): Promise<{ session_id: string; macros: Macro[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/macros`, context));
}

export function createMacro(
  sessionId: string,
  name: string,
  template: string,
  command?: CommandContext,
): Promise<{ session_id: string; macro: Macro; revision: number }> {
  return request(`/sessions/${sessionId}/macros`, {
    method: "POST",
    body: JSON.stringify({ name, template, command }),
  });
}

export function runMacro(
  sessionId: string,
  macroId: string,
  variables: Record<string, string>,
  command?: CommandContext,
): Promise<{ session_id: string; macro_id: string; result: string; execution: MacroExecution; revision: number }> {
  return request(`/sessions/${sessionId}/macros/${macroId}/run`, {
    method: "POST",
    body: JSON.stringify({ variables, command }),
  });
}

export function listRollTemplates(sessionId: string, context?: ReadContext): Promise<{ session_id: string; roll_templates: RollTemplate[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/roll-templates`, context));
}

export function createRollTemplate(
  sessionId: string,
  name: string,
  template: string,
  actionBlocks: Record<string, string>,
  command?: CommandContext,
): Promise<{ session_id: string; roll_template: RollTemplate; revision: number }> {
  return request(`/sessions/${sessionId}/roll-templates`, {
    method: "POST",
    body: JSON.stringify({ name, template, action_blocks: actionBlocks, command }),
  });
}

export function renderRollTemplate(
  sessionId: string,
  rollTemplateId: string,
  variables: Record<string, string>,
  command?: CommandContext,
): Promise<{ session_id: string; roll_template_id: string; rendered: string; render: RollTemplateRender; revision: number }> {
  return request(`/sessions/${sessionId}/roll-templates/${rollTemplateId}/render`, {
    method: "POST",
    body: JSON.stringify({ variables, command }),
  });
}

export function listPlugins(sessionId: string, context?: ReadContext): Promise<{ session_id: string; plugins: Plugin[] }> {
  return request(appendReadContext(`/sessions/${sessionId}/plugins`, context));
}

export function registerPlugin(
  sessionId: string,
  name: string,
  version: string,
  capabilities: string[],
  command?: CommandContext,
): Promise<{ session_id: string; plugin: Plugin; revision: number }> {
  return request(`/sessions/${sessionId}/plugins`, {
    method: "POST",
    body: JSON.stringify({ name, version, capabilities, command }),
  });
}

export function executePluginHook(
  sessionId: string,
  pluginId: string,
  hookName: string,
  payload: Record<string, unknown>,
  command?: CommandContext,
): Promise<{ session_id: string; plugin_id: string; hook_name: string; status: string; error?: string; revision: number }> {
  return request(`/sessions/${sessionId}/plugins/${pluginId}/hooks/${hookName}/execute`, {
    method: "POST",
    body: JSON.stringify({ payload, command }),
  });
}
