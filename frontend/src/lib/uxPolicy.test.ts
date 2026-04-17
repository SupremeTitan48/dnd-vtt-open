import { describe, expect, it } from "vitest";
import {
  buildSessionIdHash,
  getPrimaryStatus,
  getRolePolicy,
  isActionAllowedForRole,
  type StatusSignal,
} from "./uxPolicy";

describe("uxPolicy", () => {
  it("chooses highest severity status as primary", () => {
    const primary = getPrimaryStatus(["connected", "saved", "reconnecting", "syncing"]);
    expect(primary).toBe("reconnecting");
  });

  it("keeps permission denied sticky when active", () => {
    const signals: StatusSignal[] = [
      { key: "permission denied", sticky: true },
      { key: "connected", sticky: false },
    ];
    const primary = getPrimaryStatus(signals.map((item) => item.key));
    expect(primary).toBe("permission denied");
  });

  it("hashes session IDs with salt and truncates output", async () => {
    const hash = await buildSessionIdHash("salt123", "session-abc");
    expect(hash).toHaveLength(12);
    expect(hash).toMatch(/^[0-9a-f]+$/);
  });

  it("denies host admin actions to player role", () => {
    const player = getRolePolicy("Player", false);
    expect(isActionAllowedForRole(player, "openAdminSettings")).toBe(false);
  });
});
