# Architecture

The app is split into bounded modules:

- `engine/`: deterministic game state and combat logic
- `content/`: import and tutorial pack loading
- `app/services/`: session application services (orchestration boundary)
- `api/`: HTTP and WebSocket API routes and request/response schemas
- `net/`: FastAPI app entrypoint and service composition
- `frontend/`: React + Vite modern tabletop UI
- `api_contracts/`: shared event and DTO contract definitions
- `desktop/`: legacy Tkinter client (temporary fallback during migration)

## Runtime flow

1. Frontend calls REST endpoints in `api/http_api.py`.
2. API delegates state mutations to `app/services/session_service.py`.
3. Service layer uses `engine/` and `engine/session_store.py`.
4. API broadcasts session updates over WebSocket channel `/api/sessions/{id}/events`.

All gameplay state ownership remains in Python backend modules.
