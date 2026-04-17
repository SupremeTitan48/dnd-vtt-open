export type RuntimeRole = "GM" | "AssistantGM" | "Player" | "Observer";
export type StatusKey =
  | "connected"
  | "reconnecting"
  | "syncing"
  | "saved"
  | "permission denied"
  | "replay available"
  | "backend unavailable";

export type RoleAction =
  | "managePermissions"
  | "useAdvancedMapTools"
  | "openAdminSettings"
  | "mutateSession"
  | "runGmAutomation";

export type StatusSignal = {
  key: StatusKey;
  sticky: boolean;
};

type RolePolicy = {
  role: RuntimeRole;
  isHostAdmin: boolean;
  allow: Record<RoleAction, boolean>;
};

const STATUS_SEVERITY: Record<StatusKey, number> = {
  "backend unavailable": 0,
  "permission denied": 1,
  reconnecting: 2,
  syncing: 3,
  "replay available": 4,
  saved: 5,
  connected: 6,
};

export function getPrimaryStatus(statuses: StatusKey[]): StatusKey {
  if (statuses.length === 0) return "connected";
  return [...statuses].sort((a, b) => STATUS_SEVERITY[a] - STATUS_SEVERITY[b])[0];
}

export function getRolePolicy(role: RuntimeRole, isHostAdmin: boolean): RolePolicy {
  const gmLike = role === "GM" || role === "AssistantGM";
  return {
    role,
    isHostAdmin,
    allow: {
      mutateSession: role !== "Observer",
      useAdvancedMapTools: gmLike,
      runGmAutomation: gmLike,
      managePermissions: gmLike,
      openAdminSettings: gmLike && isHostAdmin,
    },
  };
}

export function isActionAllowedForRole(policy: RolePolicy, action: RoleAction): boolean {
  return policy.allow[action];
}

export async function buildSessionIdHash(telemetrySalt: string, sessionId: string): Promise<string> {
  const input = `${telemetrySalt}:${sessionId}`;
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hash = Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
  return hash.slice(0, 12);
}
