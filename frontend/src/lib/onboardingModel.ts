export type OnboardingRole = "GM" | "AssistantGM" | "Player" | "Observer";

export type OnboardingStep = {
  anchorId: string;
  title: string;
  detail: string;
};

export type OnboardingSignals = {
  hasSelectedToken: boolean;
  hasUsedRuler: boolean;
  hasInitiativeEntry: boolean;
};

const HOST_STEPS: OnboardingStep[] = [
  { anchorId: "topbar-session", title: "Create Session", detail: "Create or reuse a session and confirm your host identity." },
  { anchorId: "left-rail-tools", title: "Load Map", detail: "Use map tools to place terrain/assets or load saved state." },
  { anchorId: "topbar-invite", title: "Invite Players", detail: "Share the session and assign initial player roles." },
  { anchorId: "tray-combat", title: "Start Sample Encounter", detail: "Open combat tray, add one token to initiative, and run the first turn." },
];

const PLAYER_STEPS: OnboardingStep[] = [
  { anchorId: "topbar-session", title: "Join Session", detail: "Join with session ID and confirm player identity." },
  { anchorId: "map-canvas", title: "Select Character", detail: "Click your token to select your character." },
  { anchorId: "token-hud", title: "Learn Core Actions", detail: "Use token HUD for HP, conditions, and quick details." },
  { anchorId: "tray-chat", title: "Complete Guided Sandbox", detail: "Move once, measure once, and check tray summaries for chat/combat state." },
];

export function getOnboardingSteps(role: OnboardingRole): OnboardingStep[] {
  if (role === "GM" || role === "AssistantGM") return HOST_STEPS;
  if (role === "Player") return PLAYER_STEPS;
  return PLAYER_STEPS;
}

export function getOnboardingStorageKey(peerId: string, role: OnboardingRole): string {
  return `dnd:onboarding:${peerId}:${role}`;
}

export function isOnboardingStepComplete(role: OnboardingRole, stepIndex: number, signals: OnboardingSignals): boolean {
  const hostLike = role === "GM" || role === "AssistantGM";
  if (hostLike && stepIndex === 3) {
    return signals.hasInitiativeEntry;
  }
  if (role === "Player" && stepIndex === 3) {
    return signals.hasSelectedToken && signals.hasUsedRuler;
  }
  return true;
}
