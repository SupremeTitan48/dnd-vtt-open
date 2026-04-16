import { useMemo, useState } from "react";
import type { Macro } from "../types";

type Props = {
  macros: Macro[];
  canManage: boolean;
  onCreate: (name: string, template: string) => Promise<void>;
  onRun: (macroId: string, variables: Record<string, string>) => Promise<string>;
};

function parseVariables(raw: string): { values: Record<string, string>; invalid: string[] } {
  const invalid: string[] = [];
  const values = raw
    .split(/[\n,]/)
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((acc, entry) => {
      const [k, ...rest] = entry.split("=");
      if (!k || rest.length === 0) {
        invalid.push(entry);
        return acc;
      }
      acc[k.trim()] = rest.join("=").trim();
      return acc;
    }, {});
  return { values, invalid };
}

export function MacroPanel({ macros, canManage, onCreate, onRun }: Props) {
  if (!canManage) {
    return null;
  }

  const [name, setName] = useState("");
  const [template, setTemplate] = useState("");
  const [runningMacroId, setRunningMacroId] = useState<string>("");
  const [variablesInput, setVariablesInput] = useState("actor=Nyx,spell=Magic Missile");
  const [lastOutput, setLastOutput] = useState("");
  const [validationError, setValidationError] = useState("");
  const [runtimeError, setRuntimeError] = useState("");
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const macroOptions = useMemo(() => macros.map((m) => ({ id: m.macro_id, label: m.name })), [macros]);

  return (
    <div className="panel side-panel">
      <h3>Macros</h3>
      <input placeholder="Macro name" value={name} onChange={(e) => setName(e.target.value)} disabled={!canManage} style={{ width: "100%" }} />
      <input
        placeholder="Template: {actor} casts {spell}."
        value={template}
        onChange={(e) => setTemplate(e.target.value)}
        disabled={!canManage}
        style={{ width: "100%", marginTop: 6 }}
      />
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || saving}
        onClick={async () => {
          if (!name.trim() || !template.trim()) return;
          setSaving(true);
          setRuntimeError("");
          try {
            await onCreate(name.trim(), template.trim());
            setName("");
            setTemplate("");
          } catch (err) {
            setRuntimeError(err instanceof Error ? err.message : "Failed to create macro.");
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? "Creating..." : "Create Macro"}
      </button>

      <div style={{ marginTop: 10, fontSize: 12, color: "#aab3dd" }}>Run macro</div>
      <select
        value={runningMacroId}
        onChange={(e) => setRunningMacroId(e.target.value)}
        style={{ width: "100%", marginTop: 6 }}
        disabled={!canManage || macroOptions.length === 0}
      >
        <option value="">Select macro</option>
        {macroOptions.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      <textarea
        value={variablesInput}
        onChange={(e) => setVariablesInput(e.target.value)}
        placeholder="Variables (key=value per line or comma separated)"
        style={{ width: "100%", marginTop: 6 }}
        rows={3}
        disabled={!canManage}
      />
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || !runningMacroId || running}
        onClick={async () => {
          setRunning(true);
          setRuntimeError("");
          try {
            const parsed = parseVariables(variablesInput);
            if (parsed.invalid.length) {
              setValidationError(`Invalid entries: ${parsed.invalid.join(", ")}`);
              return;
            }
            setValidationError("");
            const output = await onRun(runningMacroId, parsed.values);
            setLastOutput(output);
          } catch (err) {
            setRuntimeError(err instanceof Error ? err.message : "Failed to run macro.");
          } finally {
            setRunning(false);
          }
        }}
      >
        {running ? "Running..." : "Run Macro"}
      </button>
      {validationError && <div style={{ marginTop: 8, fontSize: 12, color: "#ff9b9b" }}>{validationError}</div>}
      {runtimeError && <div style={{ marginTop: 8, fontSize: 12, color: "#ff9b9b" }}>{runtimeError}</div>}
      {lastOutput && <div style={{ marginTop: 8, fontSize: 12 }}>Last output: {lastOutput}</div>}
    </div>
  );
}
