import { useMemo, useState } from "react";
import type { Snapshot } from "../types";
import type { MapTool } from "./MapToolsPanel";

type ContextTarget = { tokenId: string; clientX: number; clientY: number };

type Props = {
  snapshot: Snapshot;
  selectedTokens: string[];
  activeTool: MapTool;
  terrainType: string;
  assetId: string;
  onToggleToken: (tokenId: string, multi: boolean) => void;
  onMoveTokens: (tokenIds: string[], toX: number, toY: number) => void;
  onRevealCell: (x: number, y: number) => void;
  onPaintTerrain: (x: number, y: number, terrainType: string) => void;
  onToggleBlocked: (x: number, y: number) => void;
  onStampAsset: (x: number, y: number, assetId: string) => void;
  onTokenContext: (target: ContextTarget) => void;
  canEditMap: boolean;
  canMoveTokens: boolean;
  canControlToken: (tokenId: string) => boolean;
};

const TERRAIN_COLORS: Record<string, string> = {
  grass: "#2a5f36",
  stone: "#575d6e",
  water: "#2a4f78",
  lava: "#7f3028",
};

const ASSET_LABELS: Record<string, string> = {
  tree: "T",
  rock: "R",
  crate: "C",
  altar: "A",
};

export function MapCanvas({
  snapshot,
  selectedTokens,
  activeTool,
  terrainType,
  assetId,
  onToggleToken,
  onMoveTokens,
  onRevealCell,
  onPaintTerrain,
  onToggleBlocked,
  onStampAsset,
  onTokenContext,
  canEditMap,
  canMoveTokens,
  canControlToken,
}: Props) {
  const size = 26;
  const width = snapshot.map.width * size;
  const height = snapshot.map.height * size;

  const [dragToken, setDragToken] = useState<string | null>(null);
  const [dragGhost, setDragGhost] = useState<{ x: number; y: number } | null>(null);

  const revealed = useMemo(
    () => new Set(snapshot.map.revealed_cells.map(([x, y]) => `${x}:${y}`)),
    [snapshot.map.revealed_cells],
  );
  const blocked = useMemo(
    () => new Set(snapshot.map.blocked_cells.map(([x, y]) => `${x}:${y}`)),
    [snapshot.map.blocked_cells],
  );

  function cellFromPointer(clientX: number, clientY: number, rect: DOMRect) {
    const x = Math.max(0, Math.min(snapshot.map.width - 1, Math.floor((clientX - rect.left) / size)));
    const y = Math.max(0, Math.min(snapshot.map.height - 1, Math.floor((clientY - rect.top) / size)));
    return { x, y };
  }

  function applyCellTool(x: number, y: number) {
    if (!canEditMap) return;
    if (activeTool === "reveal") {
      onRevealCell(x, y);
      return;
    }
    if (activeTool === "terrain") {
      onPaintTerrain(x, y, terrainType);
      return;
    }
    if (activeTool === "block") {
      onToggleBlocked(x, y);
      return;
    }
    if (activeTool === "asset") {
      onStampAsset(x, y, assetId);
    }
  }

  return (
    <div className="panel" style={{ overflow: "auto", padding: 8 }}>
      <svg
        width={width}
        height={height}
        style={{ background: "#191c2a", borderRadius: 10 }}
        onClick={(e) => {
          if (activeTool === "move" || !canEditMap) return;
          const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const { x, y } = cellFromPointer(e.clientX, e.clientY, rect);
          applyCellTool(x, y);
        }}
        onMouseMove={(e) => {
          if (!dragToken || activeTool !== "move" || !canMoveTokens) return;
          const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          setDragGhost(cellFromPointer(e.clientX, e.clientY, rect));
        }}
        onMouseUp={(e) => {
          if (!dragToken || activeTool !== "move" || !canMoveTokens) return;
          if (!canControlToken(dragToken)) return;
          const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const pos = cellFromPointer(e.clientX, e.clientY, rect);
          const selectedControlled = selectedTokens.filter((tokenId) => canControlToken(tokenId));
          const group = selectedControlled.includes(dragToken) ? selectedControlled : [dragToken];
          onMoveTokens(group, pos.x, pos.y);
          setDragToken(null);
          setDragGhost(null);
        }}
      >
        {Object.entries(snapshot.map.terrain_tiles).map(([key, terrain]) => {
          const [x, y] = key.split(":").map(Number);
          return <rect key={`terrain-${key}`} x={x * size} y={y * size} width={size} height={size} fill={TERRAIN_COLORS[terrain] ?? "#2a5f36"} opacity={0.85} />;
        })}

        {Array.from({ length: snapshot.map.width + 1 }, (_, x) => (
          <line key={`vx-${x}`} x1={x * size} y1={0} x2={x * size} y2={height} stroke="#323754" strokeWidth={1} />
        ))}
        {Array.from({ length: snapshot.map.height + 1 }, (_, y) => (
          <line key={`hy-${y}`} x1={0} y1={y * size} x2={width} y2={y * size} stroke="#323754" strokeWidth={1} />
        ))}

        {snapshot.map.fog_enabled &&
          Array.from({ length: snapshot.map.width }).flatMap((_, x) =>
            Array.from({ length: snapshot.map.height }).map((_, y) => {
              const isRevealed = revealed.has(`${x}:${y}`);
              return isRevealed ? null : (
                <rect key={`fog-${x}-${y}`} x={x * size} y={y * size} width={size} height={size} fill="rgba(6, 7, 12, 0.78)" />
              );
            }),
          )}

        {Array.from(blocked).map((key) => {
          const [x, y] = key.split(":").map(Number);
          return (
            <g key={`blocked-${key}`}>
              <rect x={x * size + 2} y={y * size + 2} width={size - 4} height={size - 4} fill="rgba(90,20,20,0.45)" />
              <line x1={x * size + 4} y1={y * size + 4} x2={(x + 1) * size - 4} y2={(y + 1) * size - 4} stroke="#ff8a8a" strokeWidth={2} />
              <line x1={(x + 1) * size - 4} y1={y * size + 4} x2={x * size + 4} y2={(y + 1) * size - 4} stroke="#ff8a8a" strokeWidth={2} />
            </g>
          );
        })}

        {Object.entries(snapshot.map.asset_stamps).map(([key, asset]) => {
          const [x, y] = key.split(":").map(Number);
          return (
            <text key={`asset-${key}`} x={x * size + size / 2} y={y * size + size / 2 + 5} textAnchor="middle" fill="#f6e5b7" fontWeight={700} fontSize={14}>
              {ASSET_LABELS[asset] ?? "*"}
            </text>
          );
        })}

        {Object.entries(snapshot.map.token_positions).map(([tokenId, [x, y]]) => {
          const selected = selectedTokens.includes(tokenId);
          return (
            <g
              key={tokenId}
              onMouseDown={(e) => {
                e.stopPropagation();
                onToggleToken(tokenId, e.shiftKey || e.metaKey || e.ctrlKey);
                if (activeTool === "move" && canMoveTokens && canControlToken(tokenId)) {
                  setDragToken(tokenId);
                  setDragGhost({ x, y });
                }
              }}
              onContextMenu={(e) => {
                e.preventDefault();
                if (!canMoveTokens || !canControlToken(tokenId)) return;
                onTokenContext({ tokenId, clientX: e.clientX, clientY: e.clientY });
              }}
            >
              <circle cx={x * size + size / 2} cy={y * size + size / 2} r={selected ? 10 : 9} fill={selected ? "#78c6ff" : "#89e889"} stroke="#101218" strokeWidth={2} />
              <text x={x * size + size / 2} y={y * size + size / 2 + 4} textAnchor="middle" fill="#101218" fontWeight={700} fontSize={12}>
                {tokenId.slice(0, 1).toUpperCase()}
              </text>
            </g>
          );
        })}

        {dragGhost && activeTool === "move" && (
          <circle cx={dragGhost.x * size + size / 2} cy={dragGhost.y * size + size / 2} r={11} fill="rgba(120, 198, 255, 0.35)" stroke="#9ed7ff" strokeDasharray="4 3" />
        )}
      </svg>
      <div style={{ marginTop: 8, fontSize: 12, color: "#aab3dd" }}>
        Active tool: {activeTool}. Shift/Cmd-click multi-select tokens. Right-click token for quick actions.
      </div>
    </div>
  );
}
