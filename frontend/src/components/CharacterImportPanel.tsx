import { useMemo, useState } from "react";

type Props = {
  onImport: (importFormat: string, payload: string, tokenId?: string) => Promise<void>;
  canEdit: boolean;
};

export function CharacterImportPanel({ onImport, canEdit }: Props) {
  const [step, setStep] = useState(1);
  const [importFormat, setImportFormat] = useState("json_schema");
  const [tokenId, setTokenId] = useState("");
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("Aria");
  const [characterClass, setCharacterClass] = useState("Rogue");
  const [level, setLevel] = useState(2);
  const [hitPoints, setHitPoints] = useState(14);
  const [items, setItems] = useState("Dagger, Rope");

  const payload = useMemo(() => {
    if (importFormat === "json_schema") {
      return JSON.stringify(
        {
          name,
          character_class: characterClass,
          level,
          hit_points: hitPoints,
          items: items.split(",").map((x) => x.trim()).filter(Boolean),
        },
        null,
        2,
      );
    }

    if (importFormat === "dndbeyond_json") {
      return JSON.stringify(
        {
          name,
          classes: [{ name: characterClass, level }],
          baseHitPoints: hitPoints,
          inventory: items.split(",").map((x) => ({ name: x.trim() })).filter((x) => x.name),
        },
        null,
        2,
      );
    }

    if (importFormat === "csv_basic") {
      return `name,class,level,hit_points,items
${name},${characterClass},${level},${hitPoints},${items.replace(/,/g, ";")}`;
    }

    return `Name: ${name}
Class: ${characterClass}
Level: ${level}
HP: ${hitPoints}
Items: ${items}`;
  }, [importFormat, name, characterClass, level, hitPoints, items]);

  return (
    <div className="panel side-panel">
      <h3>Character Import Wizard</h3>
      <div style={{ fontSize: 12, color: "#aab3dd", marginBottom: 8 }}>Step {step} of 3</div>

      {step === 1 && (
        <>
          <label>Format</label>
          <select value={importFormat} onChange={(e) => setImportFormat(e.target.value)} disabled={!canEdit}>
            <option value="json_schema">json_schema</option>
            <option value="dndbeyond_json">dndbeyond_json</option>
            <option value="csv_basic">csv_basic</option>
            <option value="pdf_parse">pdf_parse</option>
          </select>
          <button style={{ marginTop: 8 }} onClick={() => setStep(2)} disabled={!canEdit}>Next</button>
        </>
      )}

      {step === 2 && (
        <>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Character name" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <input value={characterClass} onChange={(e) => setCharacterClass(e.target.value)} placeholder="Class" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <input value={String(level)} onChange={(e) => setLevel(Number(e.target.value || 1))} placeholder="Level" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <input value={String(hitPoints)} onChange={(e) => setHitPoints(Number(e.target.value || 1))} placeholder="Hit points" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <input value={items} onChange={(e) => setItems(e.target.value)} placeholder="Items (comma separated)" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <input value={tokenId} onChange={(e) => setTokenId(e.target.value)} placeholder="Optional token id" style={{ width: "100%", marginBottom: 6 }} disabled={!canEdit} />
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => setStep(1)}>Back</button>
            <button onClick={() => setStep(3)} disabled={!canEdit}>Preview</button>
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <pre style={{ maxHeight: 150, overflow: "auto", background: "#1f2437", padding: 8, borderRadius: 8 }}>{payload}</pre>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button onClick={() => setStep(2)}>Back</button>
            <button
              disabled={busy || !canEdit}
              onClick={async () => {
                setBusy(true);
                try {
                  await onImport(importFormat, payload, tokenId || undefined);
                  setStep(1);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {!canEdit ? "Import disabled for role" : busy ? "Importing..." : "Import Character"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
