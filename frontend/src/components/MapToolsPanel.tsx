export type MapTool = "move" | "reveal" | "terrain" | "block" | "asset";

type Props = {
  activeTool: MapTool;
  terrainType: string;
  assetId: string;
  onSelectTool: (tool: MapTool) => void;
  onTerrainTypeChange: (terrainType: string) => void;
  onAssetIdChange: (assetId: string) => void;
  canEditMap: boolean;
};

export function MapToolsPanel({
  activeTool,
  terrainType,
  assetId,
  onSelectTool,
  onTerrainTypeChange,
  onAssetIdChange,
  canEditMap,
}: Props) {
  return (
    <div className="panel side-panel">
      <h3>Map Tools</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>
        <button className={activeTool === "move" ? "active-tool" : ""} onClick={() => onSelectTool("move")}>Move</button>
        <button className={activeTool === "reveal" ? "active-tool" : ""} onClick={() => onSelectTool("reveal")} disabled={!canEditMap}>Reveal</button>
        <button className={activeTool === "terrain" ? "active-tool" : ""} onClick={() => onSelectTool("terrain")} disabled={!canEditMap}>Terrain</button>
        <button className={activeTool === "block" ? "active-tool" : ""} onClick={() => onSelectTool("block")} disabled={!canEditMap}>Block</button>
        <button className={activeTool === "asset" ? "active-tool" : ""} onClick={() => onSelectTool("asset")} disabled={!canEditMap}>Asset</button>
      </div>

      {activeTool === "terrain" && (
        <select value={terrainType} onChange={(e) => onTerrainTypeChange(e.target.value)} style={{ marginTop: 8, width: "100%" }} disabled={!canEditMap}>
          <option value="grass">Grass</option>
          <option value="stone">Stone</option>
          <option value="water">Water</option>
          <option value="lava">Lava</option>
          <option value="clear">Clear</option>
        </select>
      )}

      {activeTool === "asset" && (
        <select value={assetId} onChange={(e) => onAssetIdChange(e.target.value)} style={{ marginTop: 8, width: "100%" }} disabled={!canEditMap}>
          <option value="tree">Tree</option>
          <option value="rock">Rock</option>
          <option value="crate">Crate</option>
          <option value="altar">Altar</option>
          <option value="clear">Clear</option>
        </select>
      )}
    </div>
  );
}
