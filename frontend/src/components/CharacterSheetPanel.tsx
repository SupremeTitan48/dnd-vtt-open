import { useMemo, useState } from "react";
import type { CharacterSheet } from "../types";

type RollActionType = "ability" | "save" | "skill" | "attack" | "spell";
type AdvantageMode = "normal" | "advantage" | "disadvantage";
type VisibilityMode = "public" | "private" | "gm_only";

type Props = {
  characters: CharacterSheet[];
  canRoll: boolean;
  onRoll: (payload: {
    actor_id: string;
    action_type: RollActionType;
    action_key: string;
    advantage_mode: AdvantageMode;
    visibility_mode: VisibilityMode;
  }) => Promise<void>;
  onUpdateSheet?: (actorId: string, updates: {
    concentration?: boolean;
    spell_slots?: Record<string, { max: number; current: number }>;
    inventory_add?: string;
    inventory_remove?: string;
  }) => Promise<void>;
};

function titleFromKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

export function CharacterSheetPanel({ characters, canRoll, onRoll, onUpdateSheet }: Props) {
  const [advantageMode, setAdvantageMode] = useState<AdvantageMode>("normal");
  const [visibilityMode, setVisibilityMode] = useState<VisibilityMode>("public");
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [inventoryInput, setInventoryInput] = useState<Record<string, string>>({});
  const display = useMemo(() => characters, [characters]);

  async function runRoll(actorId: string, actionType: RollActionType, actionKey: string) {
    if (!canRoll) return;
    const key = `${actorId}:${actionType}:${actionKey}`;
    setBusyKey(key);
    try {
      await onRoll({
        actor_id: actorId,
        action_type: actionType,
        action_key: actionKey,
        advantage_mode: advantageMode,
        visibility_mode: visibilityMode,
      });
    } finally {
      setBusyKey(null);
    }
  }

  async function runUpdate(actorId: string, updateKey: string, updates: {
    concentration?: boolean;
    spell_slots?: Record<string, { max: number; current: number }>;
    inventory_add?: string;
    inventory_remove?: string;
  }) {
    if (!canRoll || !onUpdateSheet) return;
    const key = `${actorId}:update:${updateKey}`;
    setBusyKey(key);
    try {
      await onUpdateSheet(actorId, updates);
    } finally {
      setBusyKey(null);
    }
  }

  if (!display.length) return null;

  return (
    <div className="panel side-panel">
      <h3>Character Sheet</h3>
      <label>
        Advantage
        <select value={advantageMode} onChange={(e) => setAdvantageMode(e.target.value as AdvantageMode)}>
          <option value="normal">Normal</option>
          <option value="advantage">Advantage</option>
          <option value="disadvantage">Disadvantage</option>
        </select>
      </label>
      <label>
        Visibility
        <select value={visibilityMode} onChange={(e) => setVisibilityMode(e.target.value as VisibilityMode)}>
          <option value="public">Public</option>
          <option value="private">Private</option>
          <option value="gm_only">GM Only</option>
        </select>
      </label>
      {display.map((character) => {
        const actorId = character.actor_id ?? character.name.toLowerCase().replace(/\s+/g, "-");
        const abilityKeys = Object.keys(character.abilities ?? {});
        const saveKeys = Object.keys(character.saves ?? {});
        const skillKeys = Object.keys(character.skills ?? {});
        const attackKeys = Object.keys(character.attacks ?? {});
        const spellKeys = Object.keys(character.spells ?? {});
        const slotKeys = Object.keys(character.spell_slots ?? {}).sort();
        const inventoryList = character.inventory ?? character.items ?? [];
        const pendingItem = inventoryInput[actorId] ?? "";
        return (
          <div key={`${character.name}-${actorId}`} style={{ borderTop: "1px solid #333", marginTop: 8, paddingTop: 8 }}>
            <strong>{character.name}</strong> AC {character.armor_class ?? 10} HP {character.current_hit_points ?? character.hit_points}/
            {character.max_hit_points ?? character.hit_points}
            <div style={{ marginTop: 6 }}>
              <button
                disabled={!canRoll || busyKey !== null || !onUpdateSheet}
                onClick={() => void runUpdate(actorId, "concentration", { concentration: !character.concentration })}
              >
                {character.concentration ? "End Concentration" : "Start Concentration"}
              </button>
            </div>
            <div>
              {(abilityKeys.length ? abilityKeys : ["str"]).slice(0, 6).map((key) => (
                <button key={`ability-${key}`} disabled={!canRoll || busyKey !== null} onClick={() => void runRoll(actorId, "ability", key)}>
                  {titleFromKey(key)}
                </button>
              ))}
              {(saveKeys.length ? saveKeys : ["dex"]).slice(0, 6).map((key) => (
                <button key={`save-${key}`} disabled={!canRoll || busyKey !== null} onClick={() => void runRoll(actorId, "save", key)}>
                  {titleFromKey(key)} Save
                </button>
              ))}
              {(skillKeys.length ? skillKeys : ["perception"]).slice(0, 8).map((key) => (
                <button key={`skill-${key}`} disabled={!canRoll || busyKey !== null} onClick={() => void runRoll(actorId, "skill", key)}>
                  {titleFromKey(key)}
                </button>
              ))}
              {(attackKeys.length ? attackKeys : ["primary"]).slice(0, 4).map((key) => (
                <button key={`attack-${key}`} disabled={!canRoll || busyKey !== null} onClick={() => void runRoll(actorId, "attack", key)}>
                  Attack: {titleFromKey(key)}
                </button>
              ))}
              {(spellKeys.length ? spellKeys : ["spell_attack"]).slice(0, 4).map((key) => (
                <button key={`spell-${key}`} disabled={!canRoll || busyKey !== null} onClick={() => void runRoll(actorId, "spell", key)}>
                  Spell: {titleFromKey(key)}
                </button>
              ))}
            </div>
            {slotKeys.length > 0 && (
              <div style={{ marginTop: 6 }}>
                {slotKeys.map((slotKey) => {
                  const slot = character.spell_slots?.[slotKey];
                  if (!slot) return null;
                  const spendCurrent = Math.max(0, slot.current - 1);
                  const restoreCurrent = Math.min(slot.max, slot.current + 1);
                  return (
                    <div key={`slot-${slotKey}`}>
                      <span>{titleFromKey(slotKey)}: {slot.current}/{slot.max}</span>
                      <button
                        disabled={!canRoll || busyKey !== null || !onUpdateSheet || slot.current <= 0}
                        onClick={() => void runUpdate(actorId, `slot-spend-${slotKey}`, {
                          spell_slots: { ...(character.spell_slots ?? {}), [slotKey]: { ...slot, current: spendCurrent } },
                        })}
                      >
                        Spend
                      </button>
                      <button
                        disabled={!canRoll || busyKey !== null || !onUpdateSheet || slot.current >= slot.max}
                        onClick={() => void runUpdate(actorId, `slot-restore-${slotKey}`, {
                          spell_slots: { ...(character.spell_slots ?? {}), [slotKey]: { ...slot, current: restoreCurrent } },
                        })}
                      >
                        Restore
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
            <div style={{ marginTop: 6 }}>
              <div>Inventory: {inventoryList.join(", ") || "Empty"}</div>
              <input
                value={pendingItem}
                onChange={(e) => setInventoryInput((prev) => ({ ...prev, [actorId]: e.target.value }))}
                placeholder="Inventory item"
              />
              <button
                disabled={!canRoll || busyKey !== null || !onUpdateSheet || !pendingItem.trim()}
                onClick={() => void runUpdate(actorId, "inventory-add", { inventory_add: pendingItem.trim() })}
              >
                Add Item
              </button>
              <button
                disabled={!canRoll || busyKey !== null || !onUpdateSheet || !pendingItem.trim()}
                onClick={() => void runUpdate(actorId, "inventory-remove", { inventory_remove: pendingItem.trim() })}
              >
                Remove Item
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
