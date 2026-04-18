import { useEffect, useMemo, useRef, useState } from "react";
import { ActorPanel } from "./components/ActorPanel";
import { CharacterImportPanel } from "./components/CharacterImportPanel";
import { CommandPalette, type CommandItem } from "./components/CommandPalette";
import { DMToolsPanel } from "./components/DMToolsPanel";
import { HandoutPanel } from "./components/HandoutPanel";
import { InitiativePanel } from "./components/InitiativePanel";
import { JournalPanel } from "./components/JournalPanel";
import { MapCanvas } from "./components/MapCanvas";
import { MapToolsPanel, type FogMode, type MapTool } from "./components/MapToolsPanel";
import { MacroPanel } from "./components/MacroPanel";
import { OnboardingOverlay } from "./components/OnboardingOverlay";
import { PermissionsPanel } from "./components/PermissionsPanel";
import { PluginPanel } from "./components/PluginPanel";
import { RollTemplatePanel } from "./components/RollTemplatePanel";
import { SessionLobbyPanel } from "./components/SessionLobbyPanel";
import { ShortcutsOverlay } from "./components/ShortcutsOverlay";
import { StatusRail } from "./components/StatusRail";
import { TutorialPanel } from "./components/TutorialPanel";
import { AppShell } from "./components/layout/AppShell";
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
  hideCell,
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
import { getDesktopConfigSync, listenDesktopBackendStatus, type DesktopBackendStatus } from "./lib/desktopBridge";
import { emitUxEvent } from "./lib/uxTelemetry";
import { buildSessionIdHash, getRolePolicy, isActionAllowedForRole, type StatusKey } from "./lib/uxPolicy";
import { addTokenToInitiative } from "./lib/combatUtils";
import { getOnboardingSteps, getOnboardingStorageKey, isOnboardingStepComplete } from "./lib/onboardingModel";
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
  const [tokenHudAnchor, setTokenHudAnchor] = useState<{ tokenId: string; x: number; y: number } | null>(null);
  const [openCommandPalette, setOpenCommandPalette] = useState(false);
  const [openShortcuts, setOpenShortcuts] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingStepIndex, setOnboardingStepIndex] = useState(0);
  const [rulerPreset, setRulerPreset] = useState<{ start: { x: number; y: number }; end: { x: number; y: number }; nonce: number } | null>(
    null,
  );
  const [activeTool, setActiveTool] = useState<MapTool>("move");
  const [terrainType, setTerrainType] = useState("grass");
  const [assetId, setAssetId] = useState("tree");
  const [movementBudgetCells, setMovementBudgetCells] = useState(6);
  const [visionRadiusInput, setVisionRadiusInput] = useState(6);
  const [clearRulerSignal, setClearRulerSignal] = useState(0);
  const [fogMode, setFogMode] = useState<FogMode>("reveal");
  const [previewPlayerView, setPreviewPlayerView] = useState(false);
  const [status, setStatus] = useState("Starting session...");
  const [currentPeerId, setCurrentPeerId] = useState("dm-web");
  const [currentPeerToken, setCurrentPeerToken] = useState<string | undefined>(undefined);
  const [loadingSession, setLoadingSession] = useState(false);
  const [desktopBackendStatus, setDesktopBackendStatus] = useState<DesktopBackendStatus | null>(() => {
    const config = getDesktopConfigSync();
    if (!config) return null;
    return { state: config.backendState, message: config.backendMessage };
  });
  const snapshotRevisionRef = useRef(0);
  const [sessionIdHash, setSessionIdHash] = useState("nosession0000");

  useEffect(() => {
    const unsubscribe = listenDesktopBackendStatus((nextStatus) => {
      setDesktopBackendStatus(nextStatus);
    });
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);

  useEffect(() => {
    snapshotRevisionRef.current = snapshot.revision ?? 0;
  }, [snapshot]);

  function readContext(overrides?: { actor_peer_id?: string; actor_token?: string }) {
    return {
      actor_peer_id: overrides?.actor_peer_id ?? currentPeerId,
      actor_token: overrides?.actor_token ?? currentPeerToken,
    };
  }

  const currentRole = useMemo<"GM" | "AssistantGM" | "Player" | "Observer">(() => {
    if (!session) return "Observer";
    if (session.peer_roles && session.peer_roles[currentPeerId]) return session.peer_roles[currentPeerId];
    if (currentPeerId === session.host_peer_id) return "GM";
    return "Player";
  }, [session, currentPeerId]);

  async function refreshSessionData(sessionId: string, contextOverride?: { actor_peer_id?: string; actor_token?: string }) {
    const context = readContext(contextOverride);
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
  const isHostAdmin = session ? currentPeerId === session.host_peer_id : false;
  const rolePolicy = useMemo(() => getRolePolicy(currentRole, isHostAdmin), [currentRole, isHostAdmin]);
  const canUseGMTools = isActionAllowedForRole(rolePolicy, "useAdvancedMapTools");
  const canMutateWithPolicy = isActionAllowedForRole(rolePolicy, "mutateSession");
  const canEditMap = canUseGMTools;
  const visibilityMaskActive = !canUseGMTools && Object.keys(snapshot.map.visibility_cells_by_token ?? {}).length > 0;
  const ownedActorIds = useMemo(() => new Set(Object.keys(snapshot.actors)), [snapshot.actors]);

  useEffect(() => {
    if (!session) {
      setSessionIdHash("nosession0000");
      return;
    }
    const salt = String(import.meta.env.VITE_TELEMETRY_SALT ?? "dev-salt");
    void buildSessionIdHash(salt, session.session_id).then((hash) => setSessionIdHash(hash));
  }, [session]);

  useEffect(() => {
    if (!session) return;
    const key = getOnboardingStorageKey(currentPeerId, currentRole);
    const done = window.localStorage.getItem(key) === "done";
    setShowOnboarding(!done);
    setOnboardingStepIndex(0);
  }, [session, currentPeerId, currentRole]);

  function canControlToken(tokenId: string): boolean {
    if (!canMutateWithPolicy) return false;
    if (canUseGMTools) return true;
    return ownedActorIds.has(tokenId);
  }

  async function handleHostSession(sessionName: string, hostPeerId: string) {
    setLoadingSession(true);
    try {
      const created = await createSession(sessionName, hostPeerId);
      setCurrentPeerId(hostPeerId);
      setCurrentPeerToken(created.host_peer_token);
      await refreshSessionData(created.session_id, { actor_peer_id: hostPeerId, actor_token: created.host_peer_token });
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
      await refreshSessionData(created.session_id, { actor_peer_id: hostPeerId, actor_token: created.host_peer_token });
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
      await refreshSessionData(sessionId, { actor_peer_id: peerId, actor_token: joined.peer_token });
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
      if (!canMutateWithPolicy) return;
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
  }, [session, selectedTokens, snapshot, activeTool, canMutateWithPolicy, currentPeerId, currentRole]);

  useEffect(() => {
    function closeMenu() {
      setContextMenu(null);
    }
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpenCommandPalette((prev) => !prev);
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void handleSave();
        return;
      }
      if (e.key === "?") {
        e.preventDefault();
        setOpenShortcuts((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
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
    if (!canMutateWithPolicy) return;
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
    if (fogMode === "rehide") {
      const resp = await hideCell(session.session_id, x, y, commandContext());
      setSnapshot(resp.state);
      setStatus(`Re-hid ${x},${y}`);
      return;
    }
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
    if (!snapshot.map.token_positions[selectedLeadToken]) {
      setStatus(`Cannot set vision radius: token "${selectedLeadToken}" is not currently placed on the map.`);
      return;
    }
    const radius = Math.max(0, Math.floor(visionRadiusInput));
    try {
      const resp = await setTokenVisionRadius(session.session_id, selectedLeadToken, radius, commandContext());
      setSnapshot(resp.state);
      setStatus(`Set vision radius ${radius} for ${selectedLeadToken}`);
    } catch (err) {
      setStatus(`Set vision radius failed: ${(err as Error).message}`);
    }
  }

  async function handleReorderInitiative(nextOrder: string[]) {
    if (!session) return;
    if (!canUseGMTools) return;
    const resp = await setInitiative(session.session_id, nextOrder, commandContext());
    setSnapshot(resp.state);
  }

  async function handleAddLeadTokenToInitiative() {
    if (!session || !canUseGMTools) return;
    const nextOrder = addTokenToInitiative(snapshot.combat.initiative_order, selectedLeadToken);
    if (nextOrder === snapshot.combat.initiative_order) return;
    const resp = await setInitiative(session.session_id, nextOrder, commandContext());
    setSnapshot(resp.state);
    setStatus(`Added ${selectedLeadToken} to initiative`);
  }

  async function handleHideAllFog() {
    if (!session || !canUseGMTools) return;
    if (!snapshot.map.fog_enabled) {
      const resp = await setFog(session.session_id, true, commandContext());
      setSnapshot(resp.state);
    }
    setStatus("Hide all enabled (fog on). Re-hide now persists via hide-cell.");
  }

  function handleFocusCombatant(tokenId: string) {
    setSelectedTokens([tokenId]);
    setStatus(`Focused combatant ${tokenId}`);
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
    if (!canMutateWithPolicy) return;
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

  async function handleTokenHudAction(action: "open-sheet" | "damage" | "heal" | "condition" | "initiative" | "ping") {
    if (!tokenHudAnchor) return;
    if (action === "open-sheet") {
      setStatus(`Opened details for ${tokenHudAnchor.tokenId}`);
      return;
    }
    if (action === "initiative") {
      if (!session || !canUseGMTools) return;
      const nextOrder = addTokenToInitiative(snapshot.combat.initiative_order, tokenHudAnchor.tokenId);
      const resp = await setInitiative(session.session_id, nextOrder, commandContext());
      setSnapshot(resp.state);
      setStatus(`Added ${tokenHudAnchor.tokenId} to initiative`);
      return;
    }
    if (action === "ping") {
      setStatus(`Pinged and focused ${tokenHudAnchor.tokenId}`);
      return;
    }
    if (!session) return;
    const actor = snapshot.actors[tokenHudAnchor.tokenId];
    if (action === "damage") {
      const resp = await updateActor(session.session_id, tokenHudAnchor.tokenId, Math.max(0, (actor?.hit_points ?? 1) - 3), undefined, undefined, commandContext());
      setSnapshot(resp.state);
      return;
    }
    if (action === "heal") {
      const resp = await updateActor(session.session_id, tokenHudAnchor.tokenId, Math.max(0, (actor?.hit_points ?? 1) + 3), undefined, undefined, commandContext());
      setSnapshot(resp.state);
      return;
    }
    if (action === "condition") {
      const resp = await updateActor(session.session_id, tokenHudAnchor.tokenId, undefined, undefined, "Marked", commandContext());
      setSnapshot(resp.state);
    }
  }

  const statusSignals = useMemo<StatusKey[]>(() => {
    const signals: StatusKey[] = [];
    const normalized = status.toLowerCase();
    if (desktopBackendStatus?.state === "error") signals.push("backend unavailable");
    if (normalized.includes("permission denied")) signals.push("permission denied");
    if (normalized.includes("reconnect")) signals.push("reconnecting");
    if (normalized.includes("sync")) signals.push("syncing");
    if (normalized.includes("replay")) signals.push("replay available");
    if (normalized.includes("saved")) signals.push("saved");
    if (signals.length === 0) signals.push("connected");
    return signals;
  }, [status, desktopBackendStatus]);

  const viewportMode = window.innerWidth >= 1360 ? "wideDesktop" : window.innerWidth >= 1024 ? "narrowDesktop" : window.innerWidth >= 900 ? "minSupportedWidth" : "unsupported";

  const rightSections = [
    {
      id: "session",
      title: "Session and Permissions",
      content: (
        <>
          <SessionLobbyPanel onHostSession={handleHostSession} onJoinSession={handleJoinSession} loading={loadingSession} />
          {isActionAllowedForRole(rolePolicy, "managePermissions") && (
            <PermissionsPanel
              peers={session?.peers ?? []}
              peerRoles={session?.peer_roles ?? {}}
              actorOwners={session?.actor_owners ?? {}}
              actorIds={Object.keys(snapshot.actors)}
              canManagePermissions
              onAssignRole={handleAssignRole}
              onAssignOwner={handleAssignOwner}
            />
          )}
        </>
      ),
    },
    {
      id: "content",
      title: "Content",
      content: (
        <>
          <ActorPanel snapshot={snapshot} />
          <JournalPanel
            entries={journalEntries}
            peers={session?.peers ?? []}
            canManage={canUseGMTools}
            onCreate={handleCreateJournalEntry}
            onUpdate={handleUpdateJournalEntry}
            onShare={handleShareJournalEntry}
          />
          <HandoutPanel
            handouts={handouts}
            peers={session?.peers ?? []}
            canManage={canUseGMTools}
            onCreate={handleCreateHandout}
            onUpdate={handleUpdateHandout}
            onShare={handleShareHandout}
          />
          <TutorialPanel tutorial={tutorial} />
        </>
      ),
    },
    {
      id: "gm-tools",
      title: "GM and Admin",
      content: (
        <>
          <CharacterImportPanel onImport={handleImport} canEdit={canUseGMTools} />
          <DMToolsPanel notes={notes} templates={templates} onSaveNotes={handleSaveNotes} onAddTemplate={handleAddTemplate} canEdit={canUseGMTools} />
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
        </>
      ),
    },
  ];

  const trayTabs = [
    {
      id: "combat",
      title: "Combat",
      content: <InitiativePanel snapshot={snapshot} onReorder={handleReorderInitiative} canEdit={canUseGMTools} onFocusCombatant={handleFocusCombatant} />,
    },
    {
      id: "chat",
      title: "Chat and Notes",
      content: (
        <div className="panel side-panel">
          <p>Chat tray placeholder. Journal and handout collaboration currently live in the right drawer.</p>
          <p>Latest status: {status}</p>
        </div>
      ),
    },
  ];

  const commandItems: CommandItem[] = [
    { id: "next-turn", group: "Combat", label: "Next turn", run: () => void handleNextTurn() },
    { id: "toggle-fog", group: "Map", label: "Toggle fog", run: () => void handleToggleFog() },
    { id: "hide-all-fog", group: "Map", label: "Hide all fog", run: () => void handleHideAllFog() },
    {
      id: "toggle-player-preview",
      group: "Map",
      label: previewPlayerView ? "Exit player preview" : "Preview player view",
      run: () => setPreviewPlayerView((prev) => !prev),
    },
    { id: "save-session", group: "Session", label: "Save session", shortcut: "Ctrl/Cmd+S", run: () => void handleSave() },
    { id: "add-selected-initiative", group: "Combat", label: "Add selected token to initiative", run: () => void handleAddLeadTokenToInitiative() },
    { id: "focus-selected-token", group: "Map", label: "Focus selected token", run: () => setStatus(`Focused token ${selectedLeadToken}`) },
    { id: "show-shortcuts", group: "Help", label: "Show keyboard shortcuts", shortcut: "?", run: () => setOpenShortcuts(true) },
    {
      id: "replay-onboarding",
      group: "Help",
      label: "Replay onboarding",
      run: () => {
        setOnboardingStepIndex(0);
        setShowOnboarding(true);
      },
    },
  ];
  const onboardingSteps = getOnboardingSteps(currentRole);
  const onboardingSignals = {
    hasSelectedToken: selectedTokens.length > 0,
    hasUsedRuler: activeTool === "ruler" || rulerPreset !== null,
    hasInitiativeEntry: snapshot.combat.initiative_order.length > 0,
  };
  const onboardingCanAdvance = isOnboardingStepComplete(currentRole, onboardingStepIndex, onboardingSignals);
  const onboardingHint =
    currentRole === "Player" && onboardingStepIndex === 3
      ? "Complete this step by selecting a token and using the ruler at least once."
      : (currentRole === "GM" || currentRole === "AssistantGM") && onboardingStepIndex === 3
        ? "Complete this step by adding at least one token to initiative."
        : undefined;

  if (!session) {
    return (
      <div className="app-shell app-shell-single" data-theme="grimdark">
        <div className="left-stack">
          {desktopBackendStatus && (
            <div className="status-line">
              <span className={`desktop-badge desktop-badge-${desktopBackendStatus.state}`}>Desktop backend: {desktopBackendStatus.state}</span>
              {desktopBackendStatus.message ? ` (${desktopBackendStatus.message})` : ""}
            </div>
          )}
          <div className="status-line">{status}</div>
          <SessionLobbyPanel onHostSession={handleHostSession} onJoinSession={handleJoinSession} loading={loadingSession} />
          <TutorialPanel tutorial={tutorial} />
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell" data-theme="grimdark">
      <AppShell
        role={currentRole}
        sessionIdHash={sessionIdHash}
        selectionContextId={selectedLeadToken}
        topBar={
          <>
            <span className="token-chip" id="topbar-session">Peer: {currentPeerId}</span>
            <span className="token-chip">Role: {currentRole}</span>
            <span className="token-chip" id="topbar-invite">Session: {session.session_id}</span>
            {visibilityMaskActive && <span className="token-chip">Visibility mask active</span>}
            <button
              disabled={loadingSession || !session.campaign_id || !isActionAllowedForRole(rolePolicy, "openAdminSettings")}
              onClick={() => {
                if (!isActionAllowedForRole(rolePolicy, "openAdminSettings")) {
                  emitUxEvent("role_policy_blocked_action", {
                    role: currentRole,
                    panelOrTabId: "openAdminSettings",
                    viewportMode,
                    sessionIdHash,
                    timestamp: Date.now(),
                  });
                  return;
                }
                void handleHostInCampaign("Reuse Campaign Session", currentPeerId, session.campaign_id ?? "");
              }}
            >
              Admin: Host Campaign Session
            </button>
          </>
        }
        leftRail={
          <>
            <div id="left-rail-tools">
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
              fogEnabled={snapshot.map.fog_enabled}
              fogMode={fogMode}
              previewPlayerView={previewPlayerView}
              onFogModeChange={setFogMode}
              onToggleFog={handleToggleFog}
              onHideAllFog={() => void handleHideAllFog()}
              onTogglePreviewPlayerView={() => setPreviewPlayerView((prev) => !prev)}
            />
            </div>
            <div className="panel side-panel">
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
            </div>
          </>
        }
        mapContent={
          <>
            <div id="map-canvas">
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
              onTokenDoubleClick={(tokenId) => {
                setSelectedTokens([tokenId]);
                setStatus(`Opened details for ${tokenId}`);
              }}
              onTokenScreenPoint={(point) => setTokenHudAnchor((prev) => (prev?.tokenId === point.tokenId && prev.x === point.x && prev.y === point.y ? prev : point))}
              canEditMap={canEditMap}
              canMoveTokens={canMutateWithPolicy}
              canControlToken={canControlToken}
              useVisibilityMask={!canUseGMTools || previewPlayerView}
              movementBudgetCells={movementBudgetCells}
              rulerPreset={rulerPreset}
              clearRulerSignal={clearRulerSignal}
              fogMode={fogMode}
            />
            </div>
            {contextMenu && (
              <div className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
                <button onClick={quickMeasureFromSelectedToContextToken}>Measure From Selected</button>
                <button onClick={() => void applyTokenQuickAction("damage")}>Apply Damage</button>
                <button onClick={() => void applyTokenQuickAction("heal")}>Heal</button>
                <button onClick={() => void applyTokenQuickAction("condition")}>Add Condition</button>
              </div>
            )}
            {tokenHudAnchor && (
              <div id="token-hud" className={`token-hud ${canUseGMTools ? "token-hud-gm" : "token-hud-player"}`} style={{ left: tokenHudAnchor.x + 12, top: tokenHudAnchor.y - 16 }}>
                <button onClick={() => void handleTokenHudAction("open-sheet")}>Sheet</button>
                <button onClick={() => void handleTokenHudAction("damage")}>-HP</button>
                <button onClick={() => void handleTokenHudAction("heal")}>+HP</button>
                <button onClick={() => void handleTokenHudAction("condition")}>Cond</button>
                <button onClick={() => void handleTokenHudAction("initiative")}>Init</button>
                {canUseGMTools && <button onClick={() => void handleTokenHudAction("ping")}>Ping</button>}
              </div>
            )}
          </>
        }
        rightSummary={<span>Selected: {selectedLeadToken}</span>}
        rightSections={rightSections}
        traySummary={
          <>
            <span id="tray-chat" className="token-chip">Chat unread: 0</span>
            <span id="tray-combat" className="token-chip">Combat turn: {snapshot.combat.turn_index + 1}</span>
            <span className="token-chip">Token: {selectedLeadToken}</span>
          </>
        }
        trayTabs={trayTabs}
        statusRail={<StatusRail role={currentRole} viewportMode={viewportMode} sessionIdHash={sessionIdHash} statuses={statusSignals} />}
      />
      <CommandPalette open={openCommandPalette} commands={commandItems} onClose={() => setOpenCommandPalette(false)} />
      <ShortcutsOverlay open={openShortcuts} onClose={() => setOpenShortcuts(false)} />
      <OnboardingOverlay
        open={showOnboarding}
        roleLabel={currentRole === "Player" ? "Player" : "Host"}
        steps={onboardingSteps}
        stepIndex={onboardingStepIndex}
        canAdvance={onboardingCanAdvance}
        completionHint={onboardingHint}
        onBack={() => setOnboardingStepIndex((prev) => Math.max(0, prev - 1))}
        onSkip={() => {
          window.localStorage.setItem(getOnboardingStorageKey(currentPeerId, currentRole), "done");
          setShowOnboarding(false);
        }}
        onNext={() => {
          if (onboardingStepIndex >= onboardingSteps.length - 1) {
            window.localStorage.setItem(getOnboardingStorageKey(currentPeerId, currentRole), "done");
            setShowOnboarding(false);
            return;
          }
          setOnboardingStepIndex((prev) => prev + 1);
        }}
        onReplay={() => {
          setOnboardingStepIndex(0);
          setShowOnboarding(true);
        }}
        canReplay={!showOnboarding}
      />
    </div>
  );
}
