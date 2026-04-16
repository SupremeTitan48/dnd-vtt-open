import { useState } from "react";
import type { Plugin } from "../types";

type Props = {
  plugins: Plugin[];
  canManage: boolean;
  onRegister: (name: string, version: string, capabilities: string[]) => Promise<void>;
  onExecuteHook: (pluginId: string, hookName: string, payload: Record<string, unknown>) => Promise<string>;
};

function parseCapabilities(raw: string): { values: string[]; invalid: string[] } {
  const invalid: string[] = [];
  const values = raw
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => {
      const parts = item.split(":", 2);
      const ok = parts.length === 2 && parts[0].trim().length > 0 && parts[1].trim().length > 0;
      if (!ok) invalid.push(item);
      return ok;
    });
  return { values, invalid };
}

export function PluginPanel({ plugins, canManage, onRegister, onExecuteHook }: Props) {
  if (!canManage) {
    return null;
  }

  const [name, setName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [capabilitiesInput, setCapabilitiesInput] = useState("macro:run,roll_template:render");
  const [hookName, setHookName] = useState("after_event");
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [selectedPluginId, setSelectedPluginId] = useState("");
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [lastHookStatus, setLastHookStatus] = useState("");
  const [validationError, setValidationError] = useState("");
  const [runtimeError, setRuntimeError] = useState("");

  return (
    <div className="panel side-panel">
      <h3>Plugins</h3>
      <input placeholder="Plugin name" value={name} onChange={(e) => setName(e.target.value)} disabled={!canManage} style={{ width: "100%" }} />
      <input placeholder="Version" value={version} onChange={(e) => setVersion(e.target.value)} disabled={!canManage} style={{ width: "100%", marginTop: 6 }} />
      <textarea
        placeholder="Capabilities (one per line or comma separated)"
        value={capabilitiesInput}
        onChange={(e) => setCapabilitiesInput(e.target.value)}
        disabled={!canManage}
        style={{ width: "100%", marginTop: 6 }}
        rows={3}
      />
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || saving}
        onClick={async () => {
          if (!name.trim() || !version.trim()) return;
          const parsed = parseCapabilities(capabilitiesInput);
          if (parsed.invalid.length) {
            setValidationError(`Invalid capabilities (expected domain:action): ${parsed.invalid.join(", ")}`);
            return;
          }
          setSaving(true);
          setRuntimeError("");
          try {
            setValidationError("");
            await onRegister(name.trim(), version.trim(), parsed.values);
            setName("");
          } catch (err) {
            setRuntimeError(err instanceof Error ? err.message : "Failed to register plugin.");
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? "Registering..." : "Register Plugin"}
      </button>

      <div style={{ marginTop: 10, fontSize: 12, color: "#aab3dd" }}>Execute hook</div>
      <select
        value={selectedPluginId}
        onChange={(e) => setSelectedPluginId(e.target.value)}
        style={{ width: "100%", marginTop: 6 }}
        disabled={!canManage || plugins.length === 0}
      >
        <option value="">Select plugin</option>
        {plugins.map((plugin) => (
          <option key={plugin.plugin_id} value={plugin.plugin_id}>
            {plugin.name}@{plugin.version}
          </option>
        ))}
      </select>
      <input value={hookName} onChange={(e) => setHookName(e.target.value)} disabled={!canManage} style={{ width: "100%", marginTop: 6 }} />
      <label style={{ display: "block", marginTop: 6, fontSize: 12 }}>
        <input type="checkbox" checked={simulateFailure} onChange={(e) => setSimulateFailure(e.target.checked)} disabled={!canManage} /> Simulate failure
      </label>
      <button
        style={{ marginTop: 8 }}
        disabled={!canManage || !selectedPluginId || !hookName || executing}
        onClick={async () => {
          setExecuting(true);
          setRuntimeError("");
          try {
            const status = await onExecuteHook(selectedPluginId, hookName, { event_type: "manual_trigger", simulate_failure: simulateFailure });
            setLastHookStatus(status);
          } catch (err) {
            setRuntimeError(err instanceof Error ? err.message : "Failed to execute plugin hook.");
          } finally {
            setExecuting(false);
          }
        }}
      >
        {executing ? "Executing..." : "Execute Hook"}
      </button>
      {validationError && <div style={{ marginTop: 8, fontSize: 12, color: "#ff9b9b" }}>{validationError}</div>}
      {runtimeError && <div style={{ marginTop: 8, fontSize: 12, color: "#ff9b9b" }}>{runtimeError}</div>}
      {lastHookStatus && <div style={{ marginTop: 8, fontSize: 12 }}>Last hook status: {lastHookStatus}</div>}

      <ul className="list" style={{ marginTop: 8 }}>
        {plugins.map((plugin) => (
          <li key={plugin.plugin_id}>
            <strong>{plugin.name}</strong> {plugin.version}
            <div style={{ fontSize: 12, color: "#aab3dd" }}>{plugin.capabilities.join(", ") || "No capabilities"}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
