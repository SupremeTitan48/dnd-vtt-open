# DND VTT

Open-source, modular, Python-first virtual tabletop MVP focused on accessible online play.

## Current default UI
The project now defaults to a modern web UI stack:
- React + Vite frontend (`frontend/`)
- FastAPI backend API (`net/signaling_service.py` + `api/`)
- Websocket session events for live tabletop updates

Legacy Tkinter UI remains available during transition.

## MVP features
- 2D top-down map and token state
- Initiative, HP, conditions, and held item tracking
- Character import normalization
- ORC/OGL-friendly content pack loading
- Session save/load for local DM workflows
- Signaling + relay ticket endpoints for P2P negotiation
- Realtime session event stream (WebSocket)
- Starter tutorial map for DMs

## Development setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
npm --prefix frontend install
```

## Run (default modern UI)
```bash
bash scripts/run_modern_ui.sh
```

- Backend API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend UI: `http://127.0.0.1:5173`

## Legacy fallback (Tkinter)
```bash
bash scripts/run_legacy_tk.sh
```

## Tests and builds
```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run build
```

## Architecture
See `docs/architecture.md` and `docs/roadmap.md`.
