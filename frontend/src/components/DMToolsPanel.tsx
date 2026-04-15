import { useEffect, useState } from "react";
import type { EncounterTemplate } from "../types";

type Props = {
  notes: string;
  templates: EncounterTemplate[];
  onSaveNotes: (notes: string) => Promise<void>;
  onAddTemplate: (name: string, description: string) => Promise<void>;
  canEdit: boolean;
};

export function DMToolsPanel({ notes, templates, onSaveNotes, onAddTemplate, canEdit }: Props) {
  const [draftNotes, setDraftNotes] = useState(notes);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [addingTemplate, setAddingTemplate] = useState(false);

  useEffect(() => {
    setDraftNotes(notes);
  }, [notes]);

  return (
    <div className="panel side-panel">
      <h3>DM Tools</h3>
      <div style={{ fontSize: 12, color: '#aab3dd', marginBottom: 6 }}>Quick rulings and session notes</div>
      <textarea
        value={draftNotes}
        onChange={(e) => setDraftNotes(e.target.value)}
        rows={5}
        disabled={!canEdit}
        style={{ width: '100%', background: '#1f2437', color: '#f4f6ff', border: '1px solid #454b66', borderRadius: 8, padding: 8 }}
      />
      <button
        style={{ marginTop: 8 }}
        onClick={async () => {
          setSavingNotes(true);
          try {
            await onSaveNotes(draftNotes);
          } finally {
            setSavingNotes(false);
          }
        }}
        disabled={!canEdit || savingNotes}
      >
        {savingNotes ? "Saving..." : "Save Notes"}
      </button>

      <div style={{ marginTop: 10, fontSize: 12, color: '#aab3dd' }}>Encounter templates</div>
      <input placeholder="Template name" value={templateName} onChange={(e) => setTemplateName(e.target.value)} style={{ width: '100%', marginTop: 6 }} disabled={!canEdit} />
      <input placeholder="Template description" value={templateDescription} onChange={(e) => setTemplateDescription(e.target.value)} style={{ width: '100%', marginTop: 6 }} disabled={!canEdit} />
      <button
        style={{ marginTop: 8 }}
        disabled={!canEdit || addingTemplate}
        onClick={async () => {
          if (!templateName || !templateDescription) return;
          setAddingTemplate(true);
          try {
            await onAddTemplate(templateName, templateDescription);
            setTemplateName("");
            setTemplateDescription("");
          } finally {
            setAddingTemplate(false);
          }
        }}
      >
        {addingTemplate ? "Adding..." : "Add Template"}
      </button>

      <ul className="list" style={{ marginTop: 8 }}>
        {templates.map((t) => (
          <li key={`${t.template_name}-${t.description}`}>
            <strong>{t.template_name}</strong>: {t.description}
          </li>
        ))}
      </ul>
    </div>
  );
}
