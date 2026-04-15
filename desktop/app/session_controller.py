from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from engine.game_state import GameStateEngine
from engine.map_state import MapState
from engine.session_store import SessionStore


@dataclass
class SessionController:
    active_session_name: Optional[str] = None
    active_session_id: Optional[str] = None
    engine: Optional[GameStateEngine] = None
    _store: SessionStore = field(default_factory=lambda: SessionStore(Path(".sessions")))

    def start_local_session(self, session_name: str, width: int = 30, height: int = 20) -> None:
        self.active_session_name = session_name
        self.active_session_id = session_name.lower().replace(" ", "-")
        self.engine = GameStateEngine(map_state=MapState(width=width, height=height))

    def save_active_session(self) -> Path:
        if not self.active_session_id or not self.engine:
            raise ValueError("No active session to save")
        return self._store.save(self.active_session_id, self.engine)

    def load_session(self, session_id: str) -> None:
        self.engine = self._store.load(session_id)
        self.active_session_id = session_id
        self.active_session_name = session_id.replace("-", " ").title()

    def end_session(self) -> None:
        self.active_session_name = None
        self.active_session_id = None
        self.engine = None
