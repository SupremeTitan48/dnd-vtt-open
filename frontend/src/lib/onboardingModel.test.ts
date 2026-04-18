import { describe, expect, it } from "vitest";
import { getOnboardingSteps, getOnboardingStorageKey, isOnboardingStepComplete } from "./onboardingModel";

describe("onboardingModel", () => {
  it("returns host flow steps for GM role", () => {
    const steps = getOnboardingSteps("GM");
    expect(steps).toHaveLength(4);
    expect(steps[0].title).toContain("Create");
  });

  it("returns player flow steps for Player role", () => {
    const steps = getOnboardingSteps("Player");
    expect(steps).toHaveLength(4);
    expect(steps[0].title).toContain("Join");
  });

  it("builds stable storage key for replay tracking", () => {
    expect(getOnboardingStorageKey("peer-a", "Player")).toBe("dnd:onboarding:peer-a:Player");
  });

  it("requires initiative entry for host final step completion", () => {
    expect(
      isOnboardingStepComplete("GM", 3, {
        hasSelectedToken: true,
        hasUsedRuler: true,
        hasInitiativeEntry: false,
      }),
    ).toBe(false);
    expect(
      isOnboardingStepComplete("GM", 3, {
        hasSelectedToken: true,
        hasUsedRuler: true,
        hasInitiativeEntry: true,
      }),
    ).toBe(true);
  });

  it("requires token selection and ruler usage for player final step", () => {
    expect(
      isOnboardingStepComplete("Player", 3, {
        hasSelectedToken: true,
        hasUsedRuler: false,
        hasInitiativeEntry: false,
      }),
    ).toBe(false);
    expect(
      isOnboardingStepComplete("Player", 3, {
        hasSelectedToken: true,
        hasUsedRuler: true,
        hasInitiativeEntry: false,
      }),
    ).toBe(true);
  });
});
