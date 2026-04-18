import { useMemo, useState } from "react";

export type CommandItem = {
  id: string;
  label: string;
  group?: string;
  shortcut?: string;
  run: () => void;
};

type CommandPaletteProps = {
  open: boolean;
  commands: CommandItem[];
  onClose: () => void;
};

export function CommandPalette({ open, commands, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const lower = query.toLowerCase();
    return commands.filter((cmd) => cmd.label.toLowerCase().includes(lower));
  }, [commands, query]);

  if (!open) return null;

  return (
    <div className="ux-overlay-backdrop" onClick={onClose}>
      <div className="ux-overlay-card panel" onClick={(e) => e.stopPropagation()}>
        <h3>Command Palette</h3>
        <input placeholder="Search commands" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="ux-command-list">
          {filtered.map((cmd) => (
            <button
              key={cmd.id}
              onClick={() => {
                cmd.run();
                onClose();
              }}
            >
              <span>{cmd.group ? `${cmd.group}: ` : ""}{cmd.label}</span>
              {cmd.shortcut ? <span className="ux-command-shortcut">{cmd.shortcut}</span> : null}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
