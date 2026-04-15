from dataclasses import dataclass
from typing import Optional


@dataclass
class SessionController:
    active_session_name: Optional[str] = None

    def start_local_session(self, session_name: str) -> None:
        self.active_session_name = session_name

    def end_session(self) -> None:
        self.active_session_name = None
