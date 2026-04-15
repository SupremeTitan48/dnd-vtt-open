from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from engine.game_state import GameStateEngine


@dataclass
class SessionStore:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, engine: GameStateEngine) -> Path:
        target = self.base_dir / f"{session_id}.json"
        target.write_text(json.dumps(engine.snapshot(), indent=2))
        return target

    def load(self, session_id: str) -> GameStateEngine:
        source = self.base_dir / f"{session_id}.json"
        payload = json.loads(source.read_text())
        return GameStateEngine.from_snapshot(payload)
