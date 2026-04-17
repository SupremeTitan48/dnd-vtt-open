import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MapToolsPanel } from "./MapToolsPanel";

describe("Map lighting controls", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders lighting presets and token light inputs for GMs", async () => {
    const user = userEvent.setup();
    const onSceneLightingPresetChange = vi.fn();
    const onTokenLightChange = vi.fn();
    render(
      <MapToolsPanel
        activeTool="move"
        terrainType="grass"
        assetId="tree"
        assetOptions={[]}
        onSelectTool={vi.fn()}
        onTerrainTypeChange={vi.fn()}
        onAssetIdChange={vi.fn()}
        movementBudgetCells={6}
        onMovementBudgetCellsChange={vi.fn()}
        onClearRuler={vi.fn()}
        onAddAssetOption={vi.fn().mockResolvedValue(undefined)}
        canEditMap
        fogEnabled={false}
        fogMode="reveal"
        previewPlayerView={false}
        onFogModeChange={vi.fn()}
        onToggleFog={vi.fn()}
        onHideAllFog={vi.fn()}
        onTogglePreviewPlayerView={vi.fn()}
        sceneLightingPreset="day"
        onSceneLightingPresetChange={onSceneLightingPresetChange}
        selectedTokenId="hero"
        selectedTokenLight={{ bright_radius: 0, dim_radius: 0, color: "#ffffff", enabled: false }}
        onTokenLightChange={onTokenLightChange}
      />,
    );

    await user.selectOptions(screen.getByLabelText("Scene Lighting"), "night");
    expect(onSceneLightingPresetChange).toHaveBeenCalledWith("night");

    await user.click(screen.getByLabelText("Token Light Enabled"));
    expect(onTokenLightChange).toHaveBeenCalled();
    expect(screen.getByLabelText("Light Color")).toBeTruthy();
    expect(screen.getByLabelText("Bright Radius")).toBeTruthy();
    expect(screen.getByLabelText("Dim Radius")).toBeTruthy();
  });
});
