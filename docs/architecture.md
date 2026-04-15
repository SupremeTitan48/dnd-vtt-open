# Architecture

The app is split into bounded modules:
- `desktop/`: local app shell and session controls
- `engine/`: deterministic game state and combat logic
- `content/`: import and pack validation
- `net/`: signaling and P2P sync event transport
- `api_contracts/`: shared schemas and wire events

All modules communicate through DTOs from `api_contracts/`.
