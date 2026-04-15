# DND VTT

Open-source, modular, Python-first virtual tabletop MVP focused on accessible online play.

## MVP features
- 2D top-down map and token state
- Initiative, HP, conditions, and held item tracking
- Character import normalization
- ORC/OGL-friendly content pack loading
- Signaling service and P2P-ready sync events
- Starter tutorial map for DMs

## Development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Architecture
See `docs/architecture.md` and `docs/roadmap.md`.
