#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "desktop-electron/node_modules" ]]; then
  echo "Installing Electron desktop dependencies..."
  npm --prefix desktop-electron install
fi

if [[ ! -d "frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  npm --prefix frontend install
fi

echo "Launching DND VTT desktop (Electron + bundled backend)..."
env -u ELECTRON_RUN_AS_NODE npm --prefix desktop-electron run dev
