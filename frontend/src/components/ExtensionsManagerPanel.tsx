import { useMemo, useState } from "react";
import type { ModulePack } from "../types";

type Props = {
  modules: ModulePack[];
  canManage: boolean;
  onInstall: (manifestJson: string) => Promise<void>;
  onToggle: (moduleId: string, enabled: boolean) => Promise<void>;
};

export function ExtensionsManagerPanel({ modules, canManage, onInstall, onToggle }: Props) {
  const [manifestJson, setManifestJson] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyModuleId, setBusyModuleId] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);
  const sortedModules = useMemo(() => [...modules].sort((a, b) => a.name.localeCompare(b.name)), [modules]);

  if (!canManage) return null;

  return (
    <div className="panel side-panel">
      <h3>Extensions / Modules</h3>
      <textarea
        value={manifestJson}
        onChange={(event) => {
          setManifestJson(event.target.value);
          if (error) setError(null);
        }}
        placeholder="Paste pack manifest JSON"
        rows={6}
      />
      <button
        disabled={installing}
        onClick={async () => {
          setError(null);
          if (!manifestJson.trim()) {
            setError("Manifest JSON is required.");
            return;
          }
          setInstalling(true);
          try {
            await onInstall(manifestJson);
            setManifestJson("");
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setInstalling(false);
          }
        }}
      >
        Install Pack
      </button>
      {error && <div className="error-text">{error}</div>}
      <ul className="list">
        {sortedModules.map((module) => (
          <li key={module.module_id}>
            <div>{module.name} ({module.version})</div>
            <button
              disabled={busyModuleId === module.module_id}
              onClick={async () => {
                setError(null);
                setBusyModuleId(module.module_id);
                try {
                  await onToggle(module.module_id, !module.enabled);
                } catch (err) {
                  setError((err as Error).message);
                } finally {
                  setBusyModuleId(null);
                }
              }}
            >
              {module.enabled ? "Disable" : "Enable"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

