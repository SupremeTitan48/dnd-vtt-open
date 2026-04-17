import { useState } from "react";

export type MapTool = "move" | "reveal" | "terrain" | "block" | "asset" | "ruler";
export type FogMode = "reveal" | "rehide";

type Props = {
  activeTool: MapTool;
  terrainType: string;
  assetId: string;
  assetOptions: { asset_id: string; name: string }[];
  onSelectTool: (tool: MapTool) => void;
  onTerrainTypeChange: (terrainType: string) => void;
  onAssetIdChange: (assetId: string) => void;
  movementBudgetCells: number;
  onMovementBudgetCellsChange: (cells: number) => void;
  onClearRuler: () => void;
  onAddAssetOption: (assetId: string, name: string, uri: string) => Promise<void>;
  canEditMap: boolean;
  fogEnabled: boolean;
  fogMode: FogMode;
  previewPlayerView: boolean;
  onFogModeChange: (mode: FogMode) => void;
  onToggleFog: () => void;
  onHideAllFog: () => void;
  onTogglePreviewPlayerView: () => void;
  sceneLightingPreset: "day" | "dim" | "night";
  onSceneLightingPresetChange: (preset: "day" | "dim" | "night") => void;
  selectedTokenId: string;
  selectedTokenLight: { bright_radius: number; dim_radius: number; color: string; enabled: boolean };
  onTokenLightChange: (light: { bright_radius: number; dim_radius: number; color: string; enabled: boolean }) => void;
};

export function MapToolsPanel({
  activeTool,
  terrainType,
  assetId,
  assetOptions,
  onSelectTool,
  onTerrainTypeChange,
  onAssetIdChange,
  movementBudgetCells,
  onMovementBudgetCellsChange,
  onClearRuler,
  onAddAssetOption,
  canEditMap,
  fogEnabled,
  fogMode,
  previewPlayerView,
  onFogModeChange,
  onToggleFog,
  onHideAllFog,
  onTogglePreviewPlayerView,
  sceneLightingPreset,
  onSceneLightingPresetChange,
  selectedTokenId,
  selectedTokenLight,
  onTokenLightChange,
}: Props) {
  const [newAssetId, setNewAssetId] = useState("");
  const [newAssetName, setNewAssetName] = useState("");
  const [newAssetUri, setNewAssetUri] = useState("");
  return (
    <div className="panel side-panel">
      <h3>Map Tools</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
        <button className={activeTool === "move" ? "active-tool" : ""} onClick={() => onSelectTool("move")}>Move</button>
        <button className={activeTool === "ruler" ? "active-tool" : ""} onClick={() => onSelectTool("ruler")}>Ruler</button>
        <button className={activeTool === "reveal" ? "active-tool" : ""} onClick={() => onSelectTool("reveal")} disabled={!canEditMap}>Reveal</button>
        <button className={activeTool === "terrain" ? "active-tool" : ""} onClick={() => onSelectTool("terrain")} disabled={!canEditMap}>Terrain</button>
        <button className={activeTool === "block" ? "active-tool" : ""} onClick={() => onSelectTool("block")} disabled={!canEditMap}>Block</button>
        <button className={activeTool === "asset" ? "active-tool" : ""} onClick={() => onSelectTool("asset")} disabled={!canEditMap}>Asset</button>
      </div>

      {activeTool === "ruler" && (
        <div style={{ marginTop: 8 }}>
          <label style={{ fontSize: 12, color: "#aab3dd" }}>
            Movement budget (cells)
            <input
              type="number"
              min={0}
              value={movementBudgetCells}
              onChange={(e) => onMovementBudgetCellsChange(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
              style={{ marginTop: 4, width: "100%" }}
            />
          </label>
          <button style={{ marginTop: 6, width: "100%" }} onClick={onClearRuler}>
            Clear Ruler
          </button>
        </div>
      )}

      {activeTool === "terrain" && (
        <select value={terrainType} onChange={(e) => onTerrainTypeChange(e.target.value)} style={{ marginTop: 8, width: "100%" }} disabled={!canEditMap}>
          <option value="grass">Grass</option>
          <option value="stone">Stone</option>
          <option value="water">Water</option>
          <option value="lava">Lava</option>
          <option value="clear">Clear</option>
        </select>
      )}

      <div className="divider" />
      <h3>Fog Workflow</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        <button onClick={onToggleFog} disabled={!canEditMap}>{fogEnabled ? "Disable Fog" : "Enable Fog"}</button>
        <button onClick={onHideAllFog} disabled={!canEditMap}>Hide All</button>
        <button className={fogMode === "reveal" ? "active-tool" : ""} onClick={() => onFogModeChange("reveal")} disabled={!canEditMap}>
          Reveal Area
        </button>
        <button className={fogMode === "rehide" ? "active-tool" : ""} onClick={() => onFogModeChange("rehide")} disabled={!canEditMap}>
          Re-hide Area
        </button>
      </div>
      <button style={{ marginTop: 6, width: "100%" }} onClick={onTogglePreviewPlayerView} disabled={!canEditMap}>
        {previewPlayerView ? "Exit Player Preview" : "Preview Player View"}
      </button>

      <div className="divider" />
      <h3>Lighting</h3>
      <label style={{ fontSize: 12, color: "#aab3dd", display: "block" }}>
        Scene Lighting
        <select
          aria-label="Scene Lighting"
          value={sceneLightingPreset}
          onChange={(e) => onSceneLightingPresetChange(e.target.value as "day" | "dim" | "night")}
          style={{ marginTop: 4, width: "100%" }}
          disabled={!canEditMap}
        >
          <option value="day">Day</option>
          <option value="dim">Dim</option>
          <option value="night">Night</option>
        </select>
      </label>
      <p style={{ marginTop: 8, marginBottom: 6, fontSize: 12, color: "#aab3dd" }}>Selected token: {selectedTokenId}</p>
      <label style={{ fontSize: 12, color: "#aab3dd", display: "flex", gap: 6, alignItems: "center" }}>
        <input
          aria-label="Token Light Enabled"
          type="checkbox"
          checked={selectedTokenLight.enabled}
          disabled={!canEditMap}
          onChange={(e) => onTokenLightChange({ ...selectedTokenLight, enabled: e.target.checked })}
        />
        Token Light Enabled
      </label>
      <label style={{ fontSize: 12, color: "#aab3dd", display: "block", marginTop: 6 }}>
        Light Color
        <input
          aria-label="Light Color"
          type="color"
          value={selectedTokenLight.color}
          disabled={!canEditMap}
          onChange={(e) => onTokenLightChange({ ...selectedTokenLight, color: e.target.value })}
          style={{ marginTop: 4, width: "100%" }}
        />
      </label>
      <label style={{ fontSize: 12, color: "#aab3dd", display: "block", marginTop: 6 }}>
        Bright Radius
        <input
          aria-label="Bright Radius"
          type="number"
          min={0}
          value={selectedTokenLight.bright_radius}
          disabled={!canEditMap}
          onChange={(e) =>
            onTokenLightChange({ ...selectedTokenLight, bright_radius: Math.max(0, Math.floor(Number(e.target.value) || 0)) })
          }
          style={{ marginTop: 4, width: "100%" }}
        />
      </label>
      <label style={{ fontSize: 12, color: "#aab3dd", display: "block", marginTop: 6 }}>
        Dim Radius
        <input
          aria-label="Dim Radius"
          type="number"
          min={0}
          value={selectedTokenLight.dim_radius}
          disabled={!canEditMap}
          onChange={(e) =>
            onTokenLightChange({ ...selectedTokenLight, dim_radius: Math.max(0, Math.floor(Number(e.target.value) || 0)) })
          }
          style={{ marginTop: 4, width: "100%" }}
        />
      </label>

      {activeTool === "asset" && (
        <>
          <select value={assetId} onChange={(e) => onAssetIdChange(e.target.value)} style={{ marginTop: 8, width: "100%" }} disabled={!canEditMap}>
            <option value="clear">Clear</option>
            {assetOptions.map((asset) => (
              <option key={asset.asset_id} value={asset.asset_id}>
                {asset.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Asset ID"
            value={newAssetId}
            onChange={(e) => setNewAssetId(e.target.value)}
            style={{ marginTop: 8, width: "100%" }}
            disabled={!canEditMap}
          />
          <input
            placeholder="Asset Name"
            value={newAssetName}
            onChange={(e) => setNewAssetName(e.target.value)}
            style={{ marginTop: 6, width: "100%" }}
            disabled={!canEditMap}
          />
          <input
            placeholder="Asset URI"
            value={newAssetUri}
            onChange={(e) => setNewAssetUri(e.target.value)}
            style={{ marginTop: 6, width: "100%" }}
            disabled={!canEditMap}
          />
          <button
            style={{ marginTop: 6 }}
            disabled={!canEditMap || !newAssetId.trim() || !newAssetName.trim() || !newAssetUri.trim()}
            onClick={async () => {
              await onAddAssetOption(newAssetId.trim(), newAssetName.trim(), newAssetUri.trim());
              setNewAssetId("");
              setNewAssetName("");
              setNewAssetUri("");
            }}
          >
            Add Asset To Library
          </button>
        </>
      )}
    </div>
  );
}
