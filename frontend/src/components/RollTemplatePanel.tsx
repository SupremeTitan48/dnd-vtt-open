import { useMemo, useState } from "react";
import type { RollTemplate } from "../types";

type Props = {
  rollTemplates: RollTemplate[];
  canManage: boolean;
  onCreate: (name: string, template: string, actionBlocks: Record<string, string>) => Promise<void>;
  onRender: (rollTemplateId: string, variables: Record<string, string>) => Promise<string>;
};

function parseKeyValue(raw: string): { values: Record<string, string>; invalid: string[] } {
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

export function RollTemplatePanel({ rollTemplates, canManage, onCreate, onRender }: Props) {
  if (!canManage) {
    return null;
  }

  const [name, setName] = useState("");
  const [template, setTemplate] = useState("");
  const [actionBlocksInput, setActionBlocksInput] = useState("attack=Longsword,roll=1d20+5");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [variablesInput, setVariablesInput] = useState("actor=Nyx");
  const [renderedOutput, setRenderedOutput] = useState("");
  const [validationError, setValidationError] = useState("");
  const [saving, setSaving] = useState(false);
  const [rendering, setRendering] = useState(false);

  const options = useMemo(() => rollTemplates.map((t) => ({ id: t.roll_template_id, label: t.name })), [rollTemplates]);

  return (
    <div className="panel side-panel">
      <h3>Roll Templates</h3>
      <input placeholder="Template name" value={name} onChange={(e) => setName(e.target.value)} disabled={!canManage} style={{ width: "100%" }} />
      <input
        placeholder="Template: {actor} uses {attack} to roll {roll}."
        value={template}
        onChange={(e) => setTemplate(e.target.value)}
        disabled={!canManage}
        style={{ width: "100%", marginTop: 6 }}
      />
      <textarea
        placeholder="Action blocks (key=value per line or comma separated)"
        value={actionBlocksInput}
        onChange={(e) => setActionBlocksInput(e.target.value)}
        disabled={!canManage}
        style={{ width: "100%", marginTop: 6 }}
        rows={3}
      />
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || saving}
        onClick={async () => {
          if (!name.trim() || !template.trim()) return;
          const parsed = parseKeyValue(actionBlocksInput);
          if (parsed.invalid.length) {
            setValidationError(`Invalid action blocks: ${parsed.invalid.join(", ")}`);
            return;
          }
          setSaving(true);
          try {
            setValidationError("");
            await onCreate(name.trim(), template.trim(), parsed.values);
            setName("");
            setTemplate("");
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? "Creating..." : "Create Roll Template"}
      </button>

      <div style={{ marginTop: 10, fontSize: 12, color: "#aab3dd" }}>Render template</div>
      <select
        value={selectedTemplateId}
        onChange={(e) => setSelectedTemplateId(e.target.value)}
        style={{ width: "100%", marginTop: 6 }}
        disabled={!canManage || options.length === 0}
      >
        <option value="">Select roll template</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      <textarea
        value={variablesInput}
        onChange={(e) => setVariablesInput(e.target.value)}
        placeholder="Runtime variables (key=value per line or comma separated)"
        style={{ width: "100%", marginTop: 6 }}
        disabled={!canManage}
        rows={2}
      />
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || !selectedTemplateId || rendering}
        onClick={async () => {
          const parsed = parseKeyValue(variablesInput);
          if (parsed.invalid.length) {
            setValidationError(`Invalid runtime variables: ${parsed.invalid.join(", ")}`);
            return;
          }
          setRendering(true);
          try {
            setValidationError("");
            const output = await onRender(selectedTemplateId, parsed.values);
            setRenderedOutput(output);
          } finally {
            setRendering(false);
          }
        }}
      >
        {rendering ? "Rendering..." : "Render"}
      </button>
      {validationError && <div style={{ marginTop: 8, fontSize: 12, color: "#ff9b9b" }}>{validationError}</div>}
      {renderedOutput && <div style={{ marginTop: 8, fontSize: 12 }}>Rendered: {renderedOutput}</div>}
    </div>
  );
}
