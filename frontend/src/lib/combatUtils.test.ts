import { describe, expect, it } from "vitest";
import { addTokenToInitiative } from "./combatUtils";

describe("combatUtils", () => {
  it("adds token to initiative if missing", () => {
    expect(addTokenToInitiative(["hero"], "goblin")).toEqual(["hero", "goblin"]);
  });

  it("does not duplicate token already in initiative", () => {
    expect(addTokenToInitiative(["hero", "goblin"], "goblin")).toEqual(["hero", "goblin"]);
  });
});
