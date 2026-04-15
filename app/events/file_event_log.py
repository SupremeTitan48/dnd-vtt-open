from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlEventLogSink:
    def __init__(self, base_dir: Path | None = None):
        self._base_dir = base_dir or Path('.sessions/events')
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: dict[str, Any]) -> None:
        session_id = event['session_id']
        log_path = self._base_dir / f'{session_id}.jsonl'
        with log_path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(event))
            fh.write('\n')

    def read_after_revision(self, session_id: str, after_revision: int) -> list[dict[str, Any]]:
        log_path = self._base_dir / f'{session_id}.jsonl'
        if not log_path.exists():
            return []
        events: list[dict[str, Any]] = []
        with log_path.open('r', encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                parsed = json.loads(line)
                revision = parsed.get('revision')
                if isinstance(revision, int) and revision > after_revision:
                    events.append(parsed)
        return events
