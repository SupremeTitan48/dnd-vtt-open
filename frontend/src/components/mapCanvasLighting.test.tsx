import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Snapshot } from "../types";
import { MapCanvas } from "./MapCanvas";

describe("MapCanvas lighting overlay", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders scene lighting overlay above map elements", () => {
    const snapshot: Snapshot = {
      map: {
        width: 4,
        height: 4,
        token_positions: { hero: [1, 1] },
        fog_enabled: false,
        revealed_cells: [],
        terrain_tiles: { "1:1": "stone" },
        blocked_cells: [],
        asset_stamps: {},
        visibility_cells_by_token: {},
        vision_radius_by_token: {},
        vision_mode_by_token: {},
        token_light_by_token: {},
        scene_lighting_preset: "night",
      },
      combat: { initiative_order: [], turn_index: 0, round_number: 1 },
      actors: {},
    };

    const { container } = render(
      <MapCanvas
        snapshot={snapshot}
        selectedTokens={[]}
        activeTool="move"
        terrainType="grass"
        assetId="tree"
        onToggleToken={vi.fn()}
        onMoveTokens={vi.fn()}
        onRevealCell={vi.fn()}
        onPaintTerrain={vi.fn()}
        onToggleBlocked={vi.fn()}
        onStampAsset={vi.fn()}
        onTokenContext={vi.fn()}
        canEditMap
        canMoveTokens
        canControlToken={() => true}
        useVisibilityMask={false}
        sceneLightingPreset="night"
        tokenLights={{}}
        tokenVisionModes={{}}
        movementBudgetCells={6}
        rulerPreset={null}
        clearRulerSignal={0}
        fogMode="reveal"
      />,
    );

    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    const overlay = container.querySelector('rect[data-testid="scene-lighting-overlay"]');
    expect(overlay).toBeTruthy();
    const terrain = container.querySelector('rect[data-testid="terrain-1:1"]');
    expect(terrain).toBeTruthy();
    expect(Array.from(svg!.children).indexOf(overlay!)).toBeGreaterThan(Array.from(svg!.children).indexOf(terrain!));
  });
});
