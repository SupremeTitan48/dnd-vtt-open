import { useEffect, useMemo, useRef, useState } from "react";
import { ActorPanel } from "./components/ActorPanel";
import { CharacterImportPanel } from "./components/CharacterImportPanel";
import { DMToolsPanel } from "./components/DMToolsPanel";
import { HandoutPanel } from "./components/HandoutPanel";
import { InitiativePanel } from "./components/InitiativePanel";
import { JournalPanel } from "./components/JournalPanel";
import { MapCanvas } from "./components/MapCanvas";
import { MapToolsPanel, type MapTool } from "./components/MapToolsPanel";
import { MacroPanel } from "./components/MacroPanel";
import { PermissionsPanel } from "./components/PermissionsPanel";
import { PluginPanel } from "./components/PluginPanel";
import { RollTemplatePanel } from "./components/RollTemplatePanel";
import { SessionLobbyPanel } from "./components/SessionLobbyPanel";
import { TutorialPanel } from "./components/TutorialPanel";
import {
  addEncounterTemplate,
  addAssetLibraryItem,
  assignActorOwnership,
  assignSessionRole,
  createHandout,
  createJournalEntry,
  createMacro,
  createRollTemplate,
  type CommandContext,
  createSession,
  createSessionInCampaign,
  executePluginHook,
  getSession,
  getEncounterTemplates,
  getSessionNotes,
  getState,
  getTutorial,
  importCharacter,
  joinSession,
  listAssets,
  listCharacters,
  listHandouts,
  listJournalEntries,
  listMacros,
  listPlugins,
  listRollTemplates,
  loadSession,
  moveToken,
  nextTurn,
  paintTerrain,
  revealCell,
  saveSession,
  registerPlugin,
  renderRollTemplate,
  runMacro,
  setFog,
  setInitiative,
  setSessionNotes,
  setTokenVisionRadius,
  shareHandout,
  shareJournalEntry,
  stampAsset,
  toggleBlocked,
  updateHandout,
  updateJournalEntry,
  updateActor,
} from "./lib/apiClient";
import { connectSessionEvents } from "./realtime/sessionRealtime";
import type { AssetLibraryItem, CharacterSheet, EncounterTemplate, Handout, JournalEntry, Macro, Plugin, RollTemplate, Session, Snapshot, Tutorial } from "./types";

const EMPTY_STATE: Snapshot = {
  map: {
    width: 30,
    height: 20,
    token_positions: {},
    fog_enabled: false,
    revealed_cells: [],
    terrain_tiles: {},
    blocked_cells: [],
    asset_stamps: {},
    visibility_cells_by_token: {},
    vision_radius_by_token: {},
  },
  combat: { initiative_order: [], turn_index: 0, round_number: 1 },
  actors: {},
};

type ContextMenuState = { tokenId: string; x: number; y: number } | null;

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot>(EMPTY_STATE);
  const [tutorial, setTutorial] = useState<Tutorial | null>(null);
  const [characters, setCharacters] = useState<CharacterSheet[]>([]);
  const [notes, setNotes] = useState("");
  const [templates, setTemplates] = useState<EncounterTemplate[]>([]);
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([]);
  const [handouts, setHandouts] = useState<Handout[]>([]);
  const [assetLibrary, setAssetLibrary] = useState<AssetLibraryItem[]>([]);
  const [macros, setMacros] = useState<Macro[]>([]);
  const [rollTemplates, setRollTemplates] = useState<RollTemplate[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [selectedTokens, setSelectedTokens] = useState<string[]>(["hero"]);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>(null);
  const [rulerPreset, setRulerPreset] = useState<{ start: { x: number; y: number }; end: { x: number; y: number }; nonce: number } | null>(
    null,
  );
  const [activeTool, setActiveTool] = useState<MapTool>("move");
  const [terrainType, setTerrainType] = useState("grass");
  const [assetId, setAssetId] = useState("tree");
  const [movementBudgetCells, setMovementBudgetCells] = useState(6);
  const [visionRadiusInput, setVisionRadiusInput] = useState(6);
  const [clearRulerSignal, setClearRulerSignal] = useState(0);
  const [status, setStatus] = useState("Starting session...");
  const [currentPeerId, setCurrentPeerId] = useState("dm-web");
  const [currentPeerToken, setCurrentPeerToken] = useState<string | undefined>(undefined);
  const [loadingSession, setLoadingSession] = useState(false);
  const snapshotRevisionRef = useRef(0);

  useEffect(() => {
    snapshotRevisionRef.current = snapshot.revision ?? 0;
  }, [snapshot]);

  function readContext() {
    return { actor_peer_id: currentPeerId, actor_token: currentPeerToken };
  }

  const currentRole = useMemo<"GM" | "AssistantGM" | "Player" | "Observer">(() => {
    if (!session) return "Observer";
    if (session.peer_roles && session.peer_roles[currentPeerId]) return session.peer_roles[currentPeerId];
    if (currentPeerId === session.host_peer_id) return "GM";
    return "Player";
  }, [session, currentPeerId]);

  async function refreshSessionData(sessionId: string) {
    const context = readContext();
    const [sessionResp, stateResp, tutorialResp, notesResp, templatesResp, charsResp] = await Promise.all([
      getSession(sessionId, context),
      getState(sessionId, context),
      getTutorial(),
      getSessionNotes(sessionId, context),
      getEncounterTemplates(sessionId, context),
      listCharacters(sessionId, context),
    ]);
    const [journalResp, handoutsResp, assetsResp] = await Promise.all([
      listJournalEntries(sessionId, context),
      listHandouts(sessionId, context),
      listAssets(sessionId, context),
    ]);
    const role =
      (sessionResp.peer_roles && sessionResp.peer_roles[currentPeerId]) ||
      (currentPeerId === sessionResp.host_peer_id ? "GM" : "Player");
    if (role === "GM" || role === "AssistantGM") {
      const [macrosResp, rollTemplatesResp, pluginsResp] = await Promise.all([
        listMacros(sessionId, context),
        listRollTemplates(sessionId, context),
        listPlugins(sessionId, context),
      ]);
      setMacros(macrosResp.macros);
      setRollTemplates(rollTemplatesResp.roll_templates);
      setPlugins(pluginsResp.plugins);
    } else {
      setMacros([]);
      setRollTemplates([]);
      setPlugins([]);
    }
    setSession(sessionResp);
    setSnapshot(stateResp.state);
    setTutorial(tutorialResp);
    setNotes(notesResp.notes);
    setTemplates(templatesResp.encounter_templates);
    setCharacters(charsResp.characters);
    setJournalEntries(journalResp.journal_entries);
    setHandouts(handoutsResp.handouts);
    setAssetLibrary(assetsResp.assets);
    setStatus(`Active session: ${sessionResp.session_name} as ${currentPeerId}`);
  }

  function commandContext(): CommandContext {
    return {
      actor_peer_id: currentPeerId,
      actor_token: currentPeerToken,
      actor_role: currentRole,
    };
  }

  const canMutate = currentRole !== "Observer";
  const canUseGMTools = currentRole === "GM" || currentRole === "AssistantGM";
  const canEditMap = canUseGMTools;
  const visibilityMaskActive = !canUseGMTools && Object.keys(snapshot.map.visibility_cells_by_token ?? {}).length > 0;
  const ownedActorIds = useMemo(() => new Set(Object.keys(snapshot.actors)), [snapshot.actors]);

  function canControlToken(tokenId: string): boolean {
    if (!canMutate) return false;
    if (canUseGMTools) return true;
    return ownedActorIds.has(tokenId);
  }

  async function handleHostSession(sessionName: string, hostPeerId: string) {
    setLoadingSession(true);
    try {
      const created = await createSession(sessionName, hostPeerId);
      setCurrentPeerId(hostPeerId);
      setCurrentPeerToken(created.host_peer_token);
      await refreshSessionData(created.session_id);
    } catch (err) {
      setStatus(`Host error: ${(err as Error).message}`);
    } finally {
      setLoadingSession(false);
    }
  }

  async function handleHostInCampaign(sessionName: string, hostPeerId: string, campaignId: string) {
    setLoadingSession(true);
    try {
      const created = await createSessionInCampaign(sessionName, hostPeerId, campaignId);
      setCurrentPeerId(hostPeerId);
      setCurrentPeerToken(created.host_peer_token);
      await refreshSessionData(created.session_id);
    } catch (err) {
      setStatus(`Host error: ${(err as Error).message}`);
    } finally {
      setLoadingSession(false);
    }
  }

  async function handleJoinSession(sessionId: string, peerId: string) {
    setLoadingSession(true);
    try {
      const joined = await joinSession(sessionId, peerId);
      setCurrentPeerId(peerId);
      setCurrentPeerToken(joined.peer_token);
      await refreshSessionData(sessionId);
    } catch (err) {
      setStatus(`Join error: ${(err as Error).message}`);
    } finally {
      setLoadingSession(false);
    }
  }

  useEffect(() => {
    if (!session || !currentPeerToken) return;
    return connectSessionEvents(
      session.session_id,
      () => snapshotRevisionRef.current,
      readContext,
      {
        onSnapshot: setSnapshot,
        onCharacters: setCharacters,
        onStatus: setStatus,
      },
    );
  }, [session, currentPeerId, currentPeerToken]);

  const selectedLeadToken = selectedTokens[0] ?? "hero";

  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if (!session || activeTool !== "move") return;
      if (!canMutate) return;
      if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) return;
      e.preventDefault();
      void (async () => {
        const dx = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
        const dy = e.key === "ArrowUp" ? -1 : e.key === "ArrowDown" ? 1 : 0;
        for (const tokenId of selectedTokens) {
          const [x, y] = snapshot.map.token_positions[tokenId] ?? [0, 0];
          const nextX = Math.max(0, Math.min(snapshot.map.width - 1, x + dx));
          const nextY = Math.max(0, Math.min(snapshot.map.height - 1, y + dy));
          await moveToken(session.session_id, tokenId, nextX, nextY, commandContext());
        }
        const resp = await getState(session.session_id, readContext());
        setSnapshot(resp.state);
      })();
    }

    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, [session, selectedTokens, snapshot, activeTool, canMutate, currentPeerId, currentRole]);

  useEffect(() => {
    function closeMenu() {
      setContextMenu(null);
    }
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  const tokenIds = useMemo(() => {
    const ids = Object.keys(snapshot.map.token_positions);
    if (ids.length === 0) return [selectedLeadToken];
    return ids;
  }, [snapshot, selectedLeadToken]);

  function toggleTokenSelection(tokenId: string, multi: boolean) {
    setSelectedTokens((prev) => {
      if (!multi) return [tokenId];
      if (prev.includes(tokenId)) {
        const filtered = prev.filter((id) => id !== tokenId);
        return filtered.length ? filtered : [tokenId];
      }
      return [...prev, tokenId];
    });
  }

  async function handleMoveTokens(tokenIdsToMove: string[], toX: number, toY: number) {
    if (!session || tokenIdsToMove.length === 0) return;
    if (!canMutate) return;
    const controllableTokens = tokenIdsToMove.filter((tokenId) => canControlToken(tokenId));
    if (!controllableTokens.length) return;
    const lead = controllableTokens[0];
    const [leadX, leadY] = snapshot.map.token_positions[lead] ?? [toX, toY];
    const dx = toX - leadX;
    const dy = toY - leadY;

    for (const tokenId of controllableTokens) {
      const [x, y] = snapshot.map.token_positions[tokenId] ?? [0, 0];
      const nextX = Math.max(0, Math.min(snapshot.map.width - 1, x + dx));
      const nextY = Math.max(0, Math.min(snapshot.map.height - 1, y + dy));
      await moveToken(session.session_id, tokenId, nextX, nextY, commandContext());
    }
    const resp = await getState(session.session_id, readContext());
    setSnapshot(resp.state);
  }

  async function handleNextTurn() {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await nextTurn(session.session_id, commandContext());
    setSnapshot(resp.state);
  }

  async function handleSave() {
    if (!session) return;
    const resp = await saveSession(session.session_id);
    setStatus(`Saved to ${resp.saved_to}`);
  }

  async function handleLoad() {
    if (!session) return;
    const resp = await loadSession(session.session_id);
    setSnapshot(resp.state);
    await refreshSessionData(session.session_id);
    setStatus("Loaded from saved session file");
  }

  async function handleImport(importFormat: string, payload: string, tokenId?: string) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await importCharacter(session.session_id, importFormat, payload, tokenId, commandContext());
    setSnapshot(resp.state);
    const chars = await listCharacters(session.session_id, readContext());
    setCharacters(chars.characters);
    setSelectedTokens([resp.token_id]);
    setStatus(`Imported ${resp.character.name} as ${resp.token_id}`);
  }

  async function handleSaveNotes(nextNotes: string) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await setSessionNotes(session.session_id, nextNotes, commandContext());
    setNotes(resp.notes);
    setStatus("Session notes saved");
  }

  async function handleAddTemplate(name: string, description: string) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await addEncounterTemplate(session.session_id, name, description, commandContext());
    setTemplates(resp.encounter_templates);
    setStatus("Encounter template added");
  }

  async function handleCreateJournalEntry(title: string, content: string) {
    if (!session || !canUseGMTools) return;
    await createJournalEntry(session.session_id, title, content, commandContext());
    const resp = await listJournalEntries(session.session_id, readContext());
    setJournalEntries(resp.journal_entries);
  }

  async function handleUpdateJournalEntry(entryId: string, title: string, content: string) {
    if (!session || !canUseGMTools) return;
    await updateJournalEntry(session.session_id, entryId, title, content, commandContext());
    const resp = await listJournalEntries(session.session_id, readContext());
    setJournalEntries(resp.journal_entries);
  }

  async function handleShareJournalEntry(
    entryId: string,
    sharedRoles: string[],
    sharedPeerIds: string[],
    editableRoles: string[],
    editablePeerIds: string[],
  ) {
    if (!session || !canUseGMTools) return;
    await shareJournalEntry(session.session_id, entryId, sharedRoles, sharedPeerIds, editableRoles, editablePeerIds, commandContext());
    const resp = await listJournalEntries(session.session_id, readContext());
    setJournalEntries(resp.journal_entries);
  }

  async function handleCreateHandout(title: string, body: string) {
    if (!session || !canUseGMTools) return;
    await createHandout(session.session_id, title, body, commandContext());
    const resp = await listHandouts(session.session_id, readContext());
    setHandouts(resp.handouts);
  }

  async function handleUpdateHandout(handoutId: string, title: string, body: string) {
    if (!session || !canUseGMTools) return;
    await updateHandout(session.session_id, handoutId, title, body, commandContext());
    const resp = await listHandouts(session.session_id, readContext());
    setHandouts(resp.handouts);
  }

  async function handleShareHandout(
    handoutId: string,
    sharedRoles: string[],
    sharedPeerIds: string[],
    editableRoles: string[],
    editablePeerIds: string[],
  ) {
    if (!session || !canUseGMTools) return;
    await shareHandout(session.session_id, handoutId, sharedRoles, sharedPeerIds, editableRoles, editablePeerIds, commandContext());
    const resp = await listHandouts(session.session_id, readContext());
    setHandouts(resp.handouts);
  }

  async function handleAddAssetLibraryItem(nextAssetId: string, name: string, uri: string) {
    if (!session || !canUseGMTools) return;
    await addAssetLibraryItem(
      session.session_id,
      { asset_id: nextAssetId, name, asset_type: "stamp", uri, tags: [], license: null },
      commandContext(),
    );
    const resp = await listAssets(session.session_id, readContext());
    setAssetLibrary(resp.assets);
    setAssetId(nextAssetId);
  }

  async function handleCreateMacro(name: string, template: string) {
    if (!session || !canUseGMTools) return;
    await createMacro(session.session_id, name, template, commandContext());
    const resp = await listMacros(session.session_id, readContext());
    setMacros(resp.macros);
  }

  async function handleRunMacro(macroId: string, variables: Record<string, string>): Promise<string> {
    if (!session || !canUseGMTools) return "";
    const resp = await runMacro(session.session_id, macroId, variables, commandContext());
    setStatus(`Macro executed by ${resp.execution.actor_peer_id ?? "unknown actor"}`);
    return resp.result;
  }

  async function handleCreateRollTemplate(name: string, template: string, actionBlocks: Record<string, string>) {
    if (!session || !canUseGMTools) return;
    await createRollTemplate(session.session_id, name, template, actionBlocks, commandContext());
    const resp = await listRollTemplates(session.session_id, readContext());
    setRollTemplates(resp.roll_templates);
  }

  async function handleRenderRollTemplate(rollTemplateId: string, variables: Record<string, string>): Promise<string> {
    if (!session || !canUseGMTools) return "";
    const resp = await renderRollTemplate(session.session_id, rollTemplateId, variables, commandContext());
    setStatus(`Roll template rendered by ${resp.render.actor_peer_id ?? "unknown actor"}`);
    return resp.rendered;
  }

  async function handleRegisterPlugin(name: string, version: string, capabilities: string[]) {
    if (!session || !canUseGMTools) return;
    await registerPlugin(session.session_id, name, version, capabilities, commandContext());
    const resp = await listPlugins(session.session_id, readContext());
    setPlugins(resp.plugins);
  }

  async function handleExecutePluginHook(pluginId: string, hookName: string, payload: Record<string, unknown>): Promise<string> {
    if (!session || !canUseGMTools) return "forbidden";
    const resp = await executePluginHook(session.session_id, pluginId, hookName, payload, commandContext());
    setStatus(`Plugin hook ${hookName} result: ${resp.status}`);
    return resp.status;
  }

  async function handleToggleFog() {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await setFog(session.session_id, !snapshot.map.fog_enabled, commandContext());
    setSnapshot(resp.state);
  }

  async function handleRevealCell(x: number, y: number) {
    if (!session || !snapshot.map.fog_enabled) return;
    if (!canUseGMTools) return;
    const resp = await revealCell(session.session_id, x, y, commandContext());
    setSnapshot(resp.state);
  }

  async function handlePaintTerrain(x: number, y: number, terrain: string) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await paintTerrain(session.session_id, x, y, terrain, commandContext());
    setSnapshot(resp.state);
  }

  async function handleToggleBlocked(x: number, y: number) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await toggleBlocked(session.session_id, x, y, commandContext());
    setSnapshot(resp.state);
  }

  async function handleStampAsset(x: number, y: number, nextAssetId: string) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await stampAsset(session.session_id, x, y, nextAssetId, commandContext());
    setSnapshot(resp.state);
  }

  async function handleSetTokenVisionRadius() {
    if (!session || !canUseGMTools) return;
    if (!selectedLeadToken) return;
    const radius = Math.max(0, Math.floor(visionRadiusInput));
    const resp = await setTokenVisionRadius(session.session_id, selectedLeadToken, radius, commandContext());
    setSnapshot(resp.state);
    setStatus(`Set vision radius ${radius} for ${selectedLeadToken}`);
  }

  async function handleReorderInitiative(nextOrder: string[]) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await setInitiative(session.session_id, nextOrder, commandContext());
    setSnapshot(resp.state);
  }

  async function handleAssignRole(peerId: string, role: "GM" | "AssistantGM" | "Player" | "Observer") {
    if (!session || !canUseGMTools) return;
    await assignSessionRole(session.session_id, peerId, role, commandContext());
    await refreshSessionData(session.session_id);
    setStatus(`Assigned ${peerId} as ${role}`);
  }

  async function handleAssignOwner(actorId: string, peerId: string) {
    if (!session || !canUseGMTools) return;
    await assignActorOwnership(session.session_id, actorId, peerId, commandContext());
    await refreshSessionData(session.session_id);
    setStatus(`Assigned ${peerId} as owner of ${actorId}`);
  }

  async function applyTokenQuickAction(action: "damage" | "heal" | "condition") {
    if (!session || !contextMenu) return;
    if (!canMutate) return;
    const tokenId = contextMenu.tokenId;
    if (!canControlToken(tokenId)) {
      setContextMenu(null);
      return;
    }
    const actor = snapshot.actors[tokenId];

    if (action === "damage") {
      const amount = Number(window.prompt("Damage amount", "3") ?? "0");
      if (!Number.isFinite(amount) || amount <= 0) return;
      const nextHp = Math.max(0, (actor?.hit_points ?? 1) - amount);
      const resp = await updateActor(session.session_id, tokenId, nextHp, undefined, undefined, commandContext());
      setSnapshot(resp.state);
    }

    if (action === "heal") {
      const amount = Number(window.prompt("Heal amount", "3") ?? "0");
      if (!Number.isFinite(amount) || amount <= 0) return;
      const nextHp = Math.max(0, (actor?.hit_points ?? 1) + amount);
      const resp = await updateActor(session.session_id, tokenId, nextHp, undefined, undefined, commandContext());
      setSnapshot(resp.state);
    }

    if (action === "condition") {
      const condition = window.prompt("Condition name", "Poisoned") ?? "";
      if (!condition.trim()) return;
      const resp = await updateActor(session.session_id, tokenId, undefined, undefined, condition.trim(), commandContext());
      setSnapshot(resp.state);
    }

    setContextMenu(null);
  }

  function quickMeasureFromSelectedToContextToken() {
    if (!contextMenu) return;
    const sourceId = selectedLeadToken;
    const targetId = contextMenu.tokenId;
    const source = snapshot.map.token_positions[sourceId];
    const target = snapshot.map.token_positions[targetId];
    if (!source || !target) {
      setStatus("Unable to start measurement: source or target token is missing.");
      setContextMenu(null);
      return;
    }
    setActiveTool("ruler");
    setRulerPreset({
      start: { x: source[0], y: source[1] },
      end: { x: target[0], y: target[1] },
      nonce: Date.now(),
    });
    setStatus(`Measured from ${sourceId} to ${targetId}`);
    setContextMenu(null);
  }

  if (!session) {
    return (
      <div className="app-shell app-shell-single">
        <div className="left-stack">
          <div className="status-line">{status}</div>
          <SessionLobbyPanel onHostSession={handleHostSession} onJoinSession={handleJoinSession} loading={loadingSession} />
          <TutorialPanel tutorial={tutorial} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="left-stack">
        <div className="panel toolbar">
          <span className="token-chip">Peer: {currentPeerId}</span>
          <span className="token-chip">Role: {currentRole}</span>
          {visibilityMaskActive && <span className="token-chip">Visibility mask active</span>}
          <span className="token-chip">Session: {session.session_id}</span>
          {canUseGMTools && (
            <>
              <input
                type="number"
                min={0}
                value={visionRadiusInput}
                onChange={(e) => setVisionRadiusInput(Number(e.target.value))}
                style={{ width: 72 }}
              />
              <button onClick={() => void handleSetTokenVisionRadius()}>Set Vision Radius</button>
            </>
          )}
          <select value={selectedLeadToken} onChange={(e) => setSelectedTokens([e.target.value])}>
            {tokenIds.map((tokenId) => (
              <option key={tokenId} value={tokenId}>
                {tokenId}
              </option>
            ))}
          </select>
          <button onClick={handleNextTurn} disabled={!canUseGMTools}>Next Turn</button>
          <button onClick={handleSave}>Save Session</button>
          <button onClick={handleLoad}>Load Session</button>
          <button onClick={handleToggleFog} disabled={!canUseGMTools}>{snapshot.map.fog_enabled ? "Disable Fog" : "Enable Fog"}</button>
          <span className="token-chip">Keyboard: Arrow keys</span>
          <span className="token-chip">Mouse: Drag token(s)</span>
          <span className="token-chip">Select: Shift/Cmd click</span>
        </div>
        <div className="status-line">{status}</div>
        <MapCanvas
          snapshot={snapshot}
          selectedTokens={selectedTokens}
          activeTool={activeTool}
          terrainType={terrainType}
          assetId={assetId}
          onToggleToken={toggleTokenSelection}
          onMoveTokens={handleMoveTokens}
          onRevealCell={handleRevealCell}
          onPaintTerrain={handlePaintTerrain}
          onToggleBlocked={handleToggleBlocked}
          onStampAsset={handleStampAsset}
          onTokenContext={(target) => setContextMenu({ tokenId: target.tokenId, x: target.clientX, y: target.clientY })}
          canEditMap={canEditMap}
          canMoveTokens={canMutate}
          canControlToken={canControlToken}
          useVisibilityMask={!canUseGMTools}
          movementBudgetCells={movementBudgetCells}
          rulerPreset={rulerPreset}
          clearRulerSignal={clearRulerSignal}
        />
      </div>
      <div className="side-stack">
        <SessionLobbyPanel onHostSession={handleHostSession} onJoinSession={handleJoinSession} loading={loadingSession} />
        <button
          disabled={loadingSession || !session.campaign_id}
          onClick={() => void handleHostInCampaign("Reuse Campaign Session", currentPeerId, session.campaign_id ?? "")}
        >
          Host New Session In Campaign
        </button>
        <PermissionsPanel
          peers={session.peers}
          peerRoles={session.peer_roles ?? {}}
          actorOwners={session.actor_owners ?? {}}
          actorIds={Object.keys(snapshot.actors)}
          canManagePermissions={canUseGMTools}
          onAssignRole={handleAssignRole}
          onAssignOwner={handleAssignOwner}
        />
        <MapToolsPanel
          activeTool={activeTool}
          terrainType={terrainType}
          assetId={assetId}
          assetOptions={assetLibrary.map((asset) => ({ asset_id: asset.asset_id, name: asset.name }))}
          onSelectTool={setActiveTool}
          onTerrainTypeChange={setTerrainType}
          onAssetIdChange={setAssetId}
          movementBudgetCells={movementBudgetCells}
          onMovementBudgetCellsChange={setMovementBudgetCells}
          onClearRuler={() => setClearRulerSignal((prev) => prev + 1)}
          onAddAssetOption={handleAddAssetLibraryItem}
          canEditMap={canEditMap}
        />
        <InitiativePanel snapshot={snapshot} onReorder={handleReorderInitiative} canEdit={canUseGMTools} />
        <ActorPanel snapshot={snapshot} />
        <CharacterImportPanel onImport={handleImport} canEdit={canUseGMTools} />
        <DMToolsPanel
          notes={notes}
          templates={templates}
          onSaveNotes={handleSaveNotes}
          onAddTemplate={handleAddTemplate}
          canEdit={canUseGMTools}
        />
        <JournalPanel
          entries={journalEntries}
          peers={session.peers}
          canManage={canUseGMTools}
          onCreate={handleCreateJournalEntry}
          onUpdate={handleUpdateJournalEntry}
          onShare={handleShareJournalEntry}
        />
        <HandoutPanel
          handouts={handouts}
          peers={session.peers}
          canManage={canUseGMTools}
          onCreate={handleCreateHandout}
          onUpdate={handleUpdateHandout}
          onShare={handleShareHandout}
        />
        <MacroPanel macros={macros} canManage={canUseGMTools} onCreate={handleCreateMacro} onRun={handleRunMacro} />
        <RollTemplatePanel
          rollTemplates={rollTemplates}
          canManage={canUseGMTools}
          onCreate={handleCreateRollTemplate}
          onRender={handleRenderRollTemplate}
        />
        <PluginPanel
          plugins={plugins}
          canManage={canUseGMTools}
          onRegister={handleRegisterPlugin}
          onExecuteHook={handleExecutePluginHook}
        />
        <TutorialPanel tutorial={tutorial} />
        <div className="panel side-panel">
          <h3>Imported Characters</h3>
          <ul className="list">
            {characters.map((c) => (
              <li key={`${c.name}-${c.level}`}>
                {c.name} (Lvl {c.level} {c.character_class})
              </li>
            ))}
          </ul>
        </div>
      </div>

      {contextMenu && (
        <div className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <button onClick={quickMeasureFromSelectedToContextToken}>Measure From Selected</button>
          <button onClick={() => void applyTokenQuickAction("damage")}>Apply Damage</button>
          <button onClick={() => void applyTokenQuickAction("heal")}>Heal</button>
          <button onClick={() => void applyTokenQuickAction("condition")}>Add Condition</button>
        </div>
      )}
    </div>
  );
}
