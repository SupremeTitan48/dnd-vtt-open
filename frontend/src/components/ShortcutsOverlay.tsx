type ShortcutsOverlayProps = {
  open: boolean;
  onClose: () => void;
};

export function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
  if (!open) return null;
  return (
    <div className="ux-overlay-backdrop" onClick={onClose}>
      <div className="ux-overlay-card panel" onClick={(e) => e.stopPropagation()}>
        <h3>Keyboard Shortcuts</h3>
        <ul className="list">
          <li>Ctrl/Cmd + K: Open command palette</li>
          <li>Arrow keys: Move selected token(s)</li>
          <li>Right click token: Context actions</li>
          <li>Double click token: Open details drawer</li>
          <li>Shift/Cmd click token: Multi-select</li>
        </ul>
      </div>
    </div>
  );
}
