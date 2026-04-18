import { useEffect, useMemo, useState } from "react";
import type { Snapshot } from "../types";
import type { FogMode, MapTool } from "./MapToolsPanel";

type ContextTarget = { tokenId: string; clientX: number; clientY: number };
type TokenScreenPoint = { tokenId: string; x: number; y: number };

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
  onTokenDoubleClick?: (tokenId: string) => void;
  onTokenScreenPoint?: (point: TokenScreenPoint) => void;
  canEditMap: boolean;
  canMoveTokens: boolean;
  canControlToken: (tokenId: string) => boolean;
  useVisibilityMask: boolean;
  movementBudgetCells: number;
  rulerPreset: { start: { x: number; y: number }; end: { x: number; y: number }; nonce: number } | null;
  clearRulerSignal: number;
  fogMode: FogMode;
};

const TERRAIN_COLORS: Record<string, string> = {
  grass: "var(--map-terrain-grass)",
  stone: "var(--map-terrain-stone)",
  water: "var(--map-terrain-water)",
  lava: "var(--map-terrain-lava)",
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
  onTokenDoubleClick,
  onTokenScreenPoint,
  canEditMap,
  canMoveTokens,
  canControlToken,
  useVisibilityMask,
  movementBudgetCells,
  rulerPreset,
  clearRulerSignal,
  fogMode,
}: Props) {
  const size = 26;
  const width = snapshot.map.width * size;
  const height = snapshot.map.height * size;

  const [dragToken, setDragToken] = useState<string | null>(null);
  const [dragGhost, setDragGhost] = useState<{ x: number; y: number } | null>(null);
  const [rulerStart, setRulerStart] = useState<{ x: number; y: number } | null>(null);
  const [rulerEnd, setRulerEnd] = useState<{ x: number; y: number } | null>(null);

  const revealed = useMemo(
    () => new Set(snapshot.map.revealed_cells.map(([x, y]) => `${x}:${y}`)),
    [snapshot.map.revealed_cells],
  );
  const blocked = useMemo(
    () => new Set(snapshot.map.blocked_cells.map(([x, y]) => `${x}:${y}`)),
    [snapshot.map.blocked_cells],
  );
  const visibilityMask = useMemo(() => {
    if (!useVisibilityMask) return null;
    const byToken = snapshot.map.visibility_cells_by_token;
    if (!byToken) return null;
    const visible = new Set<string>();
    for (const cells of Object.values(byToken)) {
      for (const [x, y] of cells) visible.add(`${x}:${y}`);
    }
    return visible.size > 0 ? visible : null;
  }, [snapshot.map.visibility_cells_by_token, useVisibilityMask]);
  const visibilityMaskActive = useVisibilityMask && visibilityMask !== null;
  function isCellVisible(x: number, y: number): boolean {
    if (!visibilityMask) return true;
    return visibilityMask.has(`${x}:${y}`);
  }

  function cellFromPointer(clientX: number, clientY: number, rect: DOMRect) {
    const x = Math.max(0, Math.min(snapshot.map.width - 1, Math.floor((clientX - rect.left) / size)));
    const y = Math.max(0, Math.min(snapshot.map.height - 1, Math.floor((clientY - rect.top) / size)));
    return { x, y };
  }

  function applyCellTool(x: number, y: number) {
    if (!canEditMap) return;
    if (activeTool === "reveal") {
      if (fogMode === "reveal") onRevealCell(x, y);
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

  const rulerDistanceCells = useMemo(() => {
    if (!rulerStart || !rulerEnd) return null;
    const dx = Math.abs(rulerEnd.x - rulerStart.x);
    const dy = Math.abs(rulerEnd.y - rulerStart.y);
    return Math.max(dx, dy);
  }, [rulerStart, rulerEnd]);
  const rulerDistanceFeet = rulerDistanceCells === null ? null : rulerDistanceCells * 5;
  const withinBudget = rulerDistanceCells === null ? null : rulerDistanceCells <= movementBudgetCells;

  useEffect(() => {
    if (!rulerPreset) return;
    setRulerStart(rulerPreset.start);
    setRulerEnd(rulerPreset.end);
  }, [rulerPreset?.nonce]);
  useEffect(() => {
    setRulerStart(null);
    setRulerEnd(null);
  }, [clearRulerSignal]);

  return (
    <div className="panel" style={{ overflow: "auto", padding: 8 }}>
      <svg
        width={width}
        height={height}
        style={{ background: "var(--map-bg)", borderRadius: 10 }}
        onClick={(e) => {
          const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const { x, y } = cellFromPointer(e.clientX, e.clientY, rect);
          if (activeTool === "ruler") {
            if (!rulerStart) {
              setRulerStart({ x, y });
              setRulerEnd({ x, y });
            } else {
              setRulerEnd({ x, y });
            }
            return;
          }
          if (activeTool === "move" || !canEditMap) return;
          applyCellTool(x, y);
        }}
        onMouseMove={(e) => {
          if (activeTool === "ruler" && rulerStart) {
            const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
            setRulerEnd(cellFromPointer(e.clientX, e.clientY, rect));
            return;
          }
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
          if (!isCellVisible(x, y)) return null;
          return <rect key={`terrain-${key}`} x={x * size} y={y * size} width={size} height={size} fill={TERRAIN_COLORS[terrain] ?? "var(--map-terrain-grass)"} opacity={0.85} />;
        })}

        {Array.from({ length: snapshot.map.width + 1 }, (_, x) => (
          <line key={`vx-${x}`} x1={x * size} y1={0} x2={x * size} y2={height} stroke="var(--map-grid)" strokeWidth={1} />
        ))}
        {Array.from({ length: snapshot.map.height + 1 }, (_, y) => (
          <line key={`hy-${y}`} x1={0} y1={y * size} x2={width} y2={y * size} stroke="var(--map-grid)" strokeWidth={1} />
        ))}

        {snapshot.map.fog_enabled &&
          Array.from({ length: snapshot.map.width }).flatMap((_, x) =>
            Array.from({ length: snapshot.map.height }).map((_, y) => {
              const cellKey = `${x}:${y}`;
              const isRevealed = visibilityMask ? visibilityMask.has(cellKey) : revealed.has(cellKey);
              return isRevealed ? null : (
                <rect key={`fog-${x}-${y}`} x={x * size} y={y * size} width={size} height={size} fill="var(--map-fog)" />
              );
            }),
          )}

        {Array.from(blocked).map((key) => {
          const [x, y] = key.split(":").map(Number);
          if (!isCellVisible(x, y)) return null;
          return (
            <g key={`blocked-${key}`}>
              <rect x={x * size + 2} y={y * size + 2} width={size - 4} height={size - 4} fill="var(--map-blocked-fill)" />
              <line x1={x * size + 4} y1={y * size + 4} x2={(x + 1) * size - 4} y2={(y + 1) * size - 4} stroke="var(--map-blocked-stroke)" strokeWidth={2} />
              <line x1={(x + 1) * size - 4} y1={y * size + 4} x2={x * size + 4} y2={(y + 1) * size - 4} stroke="var(--map-blocked-stroke)" strokeWidth={2} />
            </g>
          );
        })}

        {Object.entries(snapshot.map.asset_stamps).map(([key, asset]) => {
          const [x, y] = key.split(":").map(Number);
          if (!isCellVisible(x, y)) return null;
          return (
            <text key={`asset-${key}`} x={x * size + size / 2} y={y * size + size / 2 + 5} textAnchor="middle" fill="var(--map-asset-text)" fontWeight={700} fontSize={14}>
              {ASSET_LABELS[asset] ?? "*"}
            </text>
          );
        })}

        {Object.entries(snapshot.map.token_positions).map(([tokenId, [x, y]]) => {
          if (!isCellVisible(x, y)) return null;
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
              onDoubleClick={() => onTokenDoubleClick?.(tokenId)}
            >
              <circle cx={x * size + size / 2} cy={y * size + size / 2} r={selected ? 10 : 9} fill={selected ? "var(--map-token-selected)" : "var(--map-token-default)"} stroke="var(--map-token-stroke)" strokeWidth={2} />
              <text x={x * size + size / 2} y={y * size + size / 2 + 4} textAnchor="middle" fill="var(--map-token-stroke)" fontWeight={700} fontSize={12}>
                {tokenId.slice(0, 1).toUpperCase()}
              </text>
              {selected && onTokenScreenPoint && (
                <rect
                  x={x * size + size / 2 - 1}
                  y={y * size + size / 2 - 1}
                  width={2}
                  height={2}
                  fill="transparent"
                  ref={(node) => {
                    if (!node) return;
                    const box = node.getBoundingClientRect();
                    onTokenScreenPoint({ tokenId, x: box.left + box.width / 2, y: box.top + box.height / 2 });
                  }}
                />
              )}
            </g>
          );
        })}

        {dragGhost && activeTool === "move" && (
          <circle cx={dragGhost.x * size + size / 2} cy={dragGhost.y * size + size / 2} r={11} fill="var(--map-ruler-ghost)" stroke="var(--map-ruler-ghost-stroke)" strokeDasharray="4 3" />
        )}

        {rulerStart && rulerEnd && (
          <g>
            <line
              x1={rulerStart.x * size + size / 2}
              y1={rulerStart.y * size + size / 2}
              x2={rulerEnd.x * size + size / 2}
              y2={rulerEnd.y * size + size / 2}
              stroke="var(--map-ruler)"
              strokeWidth={2}
              strokeDasharray="6 4"
            />
            <circle cx={rulerStart.x * size + size / 2} cy={rulerStart.y * size + size / 2} r={4} fill="var(--map-ruler)" />
            <circle cx={rulerEnd.x * size + size / 2} cy={rulerEnd.y * size + size / 2} r={4} fill="var(--map-ruler)" />
          </g>
        )}
      </svg>
      <div style={{ marginTop: 8, fontSize: 12, color: "var(--map-annotation)" }}>
        Active tool: {activeTool}. Shift/Cmd-click multi-select tokens. Right-click token for quick actions.
        {activeTool === "reveal" ? ` Fog mode: ${fogMode}.` : ""}
        {visibilityMaskActive ? " Visibility mask: active." : ""}
        {rulerDistanceCells !== null
          ? ` Ruler: ${rulerDistanceCells} cells (${rulerDistanceFeet} ft) - ${withinBudget ? "within" : "over"} budget (${movementBudgetCells}).`
          : ""}
      </div>
    </div>
  );
}
