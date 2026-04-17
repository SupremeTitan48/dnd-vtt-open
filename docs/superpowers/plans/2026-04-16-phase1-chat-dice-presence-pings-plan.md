# Phase 1 – Chat, Dice, Presence, Pings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement chat log, dice/roll pipeline, presence roster, and map pings with authoritative backend, WS/replay integration, and configurable visibility (global config + per-session overrides), following the Phase 1 design.

**Architecture:** Backend remains authoritative for all state mutations (commands → `SessionService` → events). New chat/roll/ping capabilities are expressed as commands and events, filtered per-viewer via `SessionService.filter_event_for_view`. Frontend receives already-filtered WS events and renders ChatPanel, presence roster, and ping markers, with GM-only settings UI updating per-session feature flags.

**Tech Stack:** Python 3 backend (FastAPI style HTTP, existing websocket signaling), Pydantic schemas and contracts, in-memory session store + JSONL event log, React + TypeScript frontend with Vite, existing `sessionRealtime` WS client, Vitest/RTL for frontend tests, pytest for backend tests.

---

## Task 1: Global Config and Session Feature Flags

**Files:**
- Modify: `app/session_store_config.py` (or existing config module if present)
- Modify: `app/services/session_service.py`
- Modify: `engine/game_state.py` or other session model definition site (where session dict/schema lives)
- Test: `tests/test_session_store_config.py`, `tests/test_session_store.py`

- [ ] **Step 1: Add global feature defaults**

```python
# app/session_store_config.py

from pydantic import BaseSettings


class SessionFeatureDefaults(BaseSettings):
    chat_enabled: bool = True
    dice_enabled: bool = True
    pings_enabled: bool = True
    presence_enabled: bool = True

    chat_visible_to_players: bool = True
    whispers_show_contents_to_non_participants: bool = False
    dice_breakdown_visible_to_players: bool = True
    presence_visible_to_players: bool = True
    pings_visible_to_players: bool = True


SESSION_FEATURE_DEFAULTS = SessionFeatureDefaults()
```

- [ ] **Step 2: Extend session model to include feature flags**

```python
# engine/game_state.py (or wherever Session data structure is defined)

from typing import Dict, Any
from app.session_store_config import SESSION_FEATURE_DEFAULTS


def create_default_session(session_id: str) -> Dict[str, Any]:
    session: Dict[str, Any] = {
        # ... existing fields ...
        "feature_flags": {
            "chat_visible_to_players": SESSION_FEATURE_DEFAULTS.chat_visible_to_players,
            "whispers_show_contents_to_non_participants": SESSION_FEATURE_DEFAULTS.whispers_show_contents_to_non_participants,
            "dice_breakdown_visible_to_players": SESSION_FEATURE_DEFAULTS.dice_breakdown_visible_to_players,
            "presence_visible_to_players": SESSION_FEATURE_DEFAULTS.presence_visible_to_players,
            "pings_visible_to_players": SESSION_FEATURE_DEFAULTS.pings_visible_to_players,
        },
    }
    return session
```

- [ ] **Step 3: Add helper methods on SessionService for reading/updating feature flags**

```python
# app/services/session_service.py

from typing import Any, Dict


class SessionService:
    # existing methods...

    def get_feature_flags(self, session: Dict[str, Any]) -> Dict[str, Any]:
        return session.get("feature_flags", {})

    def update_feature_flags(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        session = self._get_session_or_error(session_id)
        flags = session.setdefault("feature_flags", {})
        flags.update(updates)
        # persist session in store as needed
        return flags
```

- [ ] **Step 4: Add tests for defaults and overrides**

```python
# tests/test_session_store_config.py

from app.session_store_config import SESSION_FEATURE_DEFAULTS


def test_session_feature_defaults_values():
    assert SESSION_FEATURE_DEFAULTS.chat_enabled is True
    assert SESSION_FEATURE_DEFAULTS.dice_enabled is True
    assert SESSION_FEATURE_DEFAULTS.pings_enabled is True
    assert SESSION_FEATURE_DEFAULTS.presence_enabled is True
```

```python
# tests/test_session_store.py

from engine.game_state import create_default_session


def test_session_starts_with_feature_flags_defaults():
    session = create_default_session("s1")
    flags = session["feature_flags"]
    assert flags["chat_visible_to_players"] is True
    assert flags["dice_breakdown_visible_to_players"] is True
    assert flags["presence_visible_to_players"] is True
```

- [ ] **Step 5: Run backend tests for config/session store**

```bash
cd /Users/jkoch/DND
python -m pytest tests/test_session_store_config.py tests/test_session_store.py -q
```

Expected: tests pass.

---

## Task 2: Chat Events, Schemas, Commands, and SessionService.send_chat_message

**Files:**
- Modify: `api_contracts/events.py`
- Modify: `api/schemas.py`
- Modify: `api_contracts/commands.py`
- Modify: `app/commands/dispatcher.py`
- Modify: `app/services/session_service.py`
- Modify: `api/http_api.py`
- Test: `tests/test_signaling_service.py`

- [ ] **Step 1: Add ChatMessageEvent DTO**

```python
# api_contracts/events.py

from typing import List, Optional
from pydantic import BaseModel


class ChatMessageEvent(BaseModel):
    id: str
    session_id: str
    author_peer_id: str
    author_role: str
    text: str
    gm_only: bool = False
    targets: Optional[List[str]] = None  # whisper recipients
    kind: str = "plain"  # "plain" | "system" | "roll"
    created_at: float
```

- [ ] **Step 2: Add SendChatMessageRequest schema**

```python
# api/schemas.py

from typing import List, Optional
from pydantic import BaseModel


class SendChatMessageRequest(BaseModel):
    text: str
    gm_only: bool = False
    targets: Optional[List[str]] = None
```

- [ ] **Step 3: Add SendChatMessageCommand contract**

```python
# api_contracts/commands.py

from typing import List, Optional
from pydantic import BaseModel


class SendChatMessageCommand(BaseModel):
    session_id: str
    author_peer_id: str
    text: str
    gm_only: bool = False
    targets: Optional[List[str]] = None
```

- [ ] **Step 4: Wire command through dispatcher**

```python
# app/commands/dispatcher.py

from api_contracts.commands import SendChatMessageCommand


class CommandDispatcher:
    # ...

    def send_chat_message(self, cmd: SendChatMessageCommand) -> None:
        session = self.session_service.get_session(cmd.session_id)
        self.session_service.send_chat_message(
            session=session,
            author_peer_id=cmd.author_peer_id,
            text=cmd.text,
            gm_only=cmd.gm_only,
            targets=cmd.targets or [],
        )
```

- [ ] **Step 5: Implement SessionService.send_chat_message and event emission**

```python
# app/services/session_service.py

from typing import List, Dict, Any
import time
from api_contracts.events import ChatMessageEvent


class SessionService:
    # existing methods...

    def send_chat_message(
        self,
        session: Dict[str, Any],
        author_peer_id: str,
        text: str,
        gm_only: bool,
        targets: List[str],
    ) -> None:
        now = time.time()
        author_role = self._get_peer_role(session, author_peer_id)
        event = ChatMessageEvent(
            id=self._new_event_id(),
            session_id=session["id"],
            author_peer_id=author_peer_id,
            author_role=author_role,
            text=text,
            gm_only=gm_only,
            targets=targets or None,
            kind="plain",
            created_at=now,
        )
        self._append_event_and_broadcast(session, event)
        # optionally maintain in-session chat log for quick access
        log = session.setdefault("chat_log", [])
        log.append(event.dict())
```

- [ ] **Step 6: Add /chat/send endpoint**

```python
# api/http_api.py

from fastapi import APIRouter, Depends
from api.schemas import SendChatMessageRequest
from api_contracts.commands import SendChatMessageCommand


router = APIRouter()


@router.post("/api/sessions/{session_id}/chat/send")
async def send_chat_message_endpoint(
    session_id: str,
    body: SendChatMessageRequest,
    context=Depends(get_request_context),
):
    dispatcher = context.dispatcher
    cmd = SendChatMessageCommand(
        session_id=session_id,
        author_peer_id=context.peer_id,
        text=body.text,
        gm_only=body.gm_only,
        targets=body.targets,
    )
    dispatcher.send_chat_message(cmd)
    return {"status": "ok"}
```

- [ ] **Step 7: Add basic backend tests for chat send**

```python
# tests/test_signaling_service.py

def test_send_chat_message_emits_event_and_broadcasts(client, session_factory):
    session_id, peer_id, auth_headers = session_factory()
    resp = client.post(
        f"/api/sessions/{session_id}/chat/send",
        json={"text": "hello world"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # optionally assert event log length increased or inspect last event via helper
```

- [ ] **Step 8: Run relevant backend tests**

```bash
cd /Users/jkoch/DND
python -m pytest tests/test_signaling_service.py -q
```

Expected: tests pass.

---

## Task 3: Dice Engine, RollResult, Roll Endpoint, and Events

**Files:**
- Add: `engine/dice.py`
- Modify: `api_contracts/events.py`
- Modify: `api/schemas.py`
- Modify: `api_contracts/commands.py`
- Modify: `app/commands/dispatcher.py`
- Modify: `app/services/session_service.py`
- Modify: `api/http_api.py`
- Test: `tests/test_signaling_service.py`, add `tests/test_dice_engine.py`

- [ ] **Step 1: Implement minimal dice engine**

```python
# engine/dice.py

import random
import re
from typing import List
from pydantic import BaseModel


ROLL_RE = re.compile(r"^(?P<count>\d+)d(?P<sides>\d+)(?P<mod_sign>[+-])?(?P<mod>\d+)?$")


class RollResult(BaseModel):
    formula: str
    rolls: List[int]
    modifiers: List[int]
    total: int
    breakdown: str
    advantage: bool = False
    disadvantage: bool = False


def roll_formula(formula: str, *, advantage: bool = False, disadvantage: bool = False) -> RollResult:
    m = ROLL_RE.match(formula.strip())
    if not m:
        raise ValueError(f"Unsupported dice formula: {formula}")
    count = int(m.group("count"))
    sides = int(m.group("sides"))
    mod_sign = m.group("mod_sign")
    mod_raw = m.group("mod")
    modifier = int(mod_raw) if mod_raw is not None else 0
    if mod_sign == "-":
        modifier = -modifier

    # Simple NdM roll; advantage/disadvantage will roll twice and pick max/min die sum
    def single_roll() -> int:
        return sum(random.randint(1, sides) for _ in range(count))

    if advantage and not disadvantage:
        first = single_roll()
        second = single_roll()
        total_roll = max(first, second)
        rolls = [first, second]
    elif disadvantage and not advantage:
        first = single_roll()
        second = single_roll()
        total_roll = min(first, second)
        rolls = [first, second]
    else:
        # normal
        total_roll = single_roll()
        rolls = [total_roll]

    total = total_roll + modifier
    breakdown = f"{formula} -> {rolls} {modifier:+d} = {total}"

    return RollResult(
        formula=formula,
        rolls=rolls,
        modifiers=[modifier] if modifier else [],
        total=total,
        breakdown=breakdown,
        advantage=advantage,
        disadvantage=disadvantage,
    )
```

- [ ] **Step 2: Extend events with RollResultEvent**

```python
# api_contracts/events.py

from engine.dice import RollResult


class RollResultEvent(BaseModel):
    id: str
    session_id: str
    author_peer_id: str
    author_role: str
    result: RollResult
    gm_only: bool = False
    targets: Optional[List[str]] = None
    created_at: float
```

- [ ] **Step 3: Add RollRequest schema and RollDiceCommand**

```python
# api/schemas.py

class RollRequest(BaseModel):
    formula: str
    advantage: bool = False
    disadvantage: bool = False
```

```python
# api_contracts/commands.py

class RollDiceCommand(BaseModel):
    session_id: str
    author_peer_id: str
    formula: str
    advantage: bool = False
    disadvantage: bool = False
    gm_only: bool = False
    targets: Optional[List[str]] = None
```

- [ ] **Step 4: Wire RollDiceCommand through dispatcher**

```python
# app/commands/dispatcher.py

from api_contracts.commands import RollDiceCommand


class CommandDispatcher:
    # ...

    def roll_dice(self, cmd: RollDiceCommand) -> None:
        session = self.session_service.get_session(cmd.session_id)
        self.session_service.roll_dice(
            session=session,
            author_peer_id=cmd.author_peer_id,
            formula=cmd.formula,
            advantage=cmd.advantage,
            disadvantage=cmd.disadvantage,
            gm_only=cmd.gm_only,
            targets=cmd.targets or [],
        )
```

- [ ] **Step 5: Implement SessionService.roll_dice and event emission**

```python
# app/services/session_service.py

from engine.dice import roll_formula
from api_contracts.events import RollResultEvent


class SessionService:
    # ...

    def roll_dice(
        self,
        session: Dict[str, Any],
        author_peer_id: str,
        formula: str,
        advantage: bool,
        disadvantage: bool,
        gm_only: bool,
        targets: List[str],
    ) -> None:
        now = time.time()
        author_role = self._get_peer_role(session, author_peer_id)
        result = roll_formula(formula, advantage=advantage, disadvantage=disadvantage)
        event = RollResultEvent(
            id=self._new_event_id(),
            session_id=session["id"],
            author_peer_id=author_peer_id,
            author_role=author_role,
            result=result,
            gm_only=gm_only,
            targets=targets or None,
            created_at=now,
        )
        self._append_event_and_broadcast(session, event)
        # optional: also add a system chat entry
```

- [ ] **Step 6: Add /roll endpoint**

```python
# api/http_api.py

from api.schemas import RollRequest
from api_contracts.commands import RollDiceCommand


@router.post("/api/sessions/{session_id}/roll")
async def roll_endpoint(
    session_id: str,
    body: RollRequest,
    context=Depends(get_request_context),
):
    dispatcher = context.dispatcher
    cmd = RollDiceCommand(
        session_id=session_id,
        author_peer_id=context.peer_id,
        formula=body.formula,
        advantage=body.advantage,
        disadvantage=body.disadvantage,
    )
    dispatcher.roll_dice(cmd)
    return {"status": "ok"}
```

- [ ] **Step 7: Add dice engine tests**

```python
# tests/test_dice_engine.py

from engine.dice import roll_formula


def test_simple_formula_produces_result():
    result = roll_formula("1d20+5")
    assert result.formula == "1d20+5"
    assert isinstance(result.total, int)
    assert result.breakdown.startswith("1d20+5")
```


- [ ] **Step 8: Add backend tests for /roll**

```python
# tests/test_signaling_service.py

def test_roll_endpoint_accepts_basic_formula(client, session_factory):
    session_id, peer_id, auth_headers = session_factory()
    resp = client.post(
        f"/api/sessions/{session_id}/roll",
        json={"formula": "1d20+5"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 9: Run backend tests**

```bash
cd /Users/jkoch/DND
python -m pytest tests/test_dice_engine.py tests/test_signaling_service.py -q
```

Expected: tests pass.

---

## Task 4: Map Ping Endpoint, Events, and SessionService.create_ping

**Files:**
- Modify: `api_contracts/events.py`
- Modify: `api/schemas.py`
- Modify: `api_contracts/commands.py`
- Modify: `app/commands/dispatcher.py`
- Modify: `app/services/session_service.py`
- Modify: `api/http_api.py`
- Test: `tests/test_signaling_service.py`

- [ ] **Step 1: Add MapPingEvent DTO**

```python
# api_contracts/events.py

class MapPingEvent(BaseModel):
    id: str
    session_id: str
    author_peer_id: str
    x: float
    y: float
    label: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: float
```

- [ ] **Step 2: Add PingRequest schema and CreatePingCommand**

```python
# api/schemas.py

class PingRequest(BaseModel):
    x: float
    y: float
    label: Optional[str] = None
    duration_ms: Optional[int] = None
```

```python
# api_contracts/commands.py

class CreatePingCommand(BaseModel):
    session_id: str
    author_peer_id: str
    x: float
    y: float
    label: Optional[str] = None
    duration_ms: Optional[int] = None
```

- [ ] **Step 3: Wire CreatePingCommand through dispatcher**

```python
# app/commands/dispatcher.py

from api_contracts.commands import CreatePingCommand


class CommandDispatcher:
    # ...

    def create_ping(self, cmd: CreatePingCommand) -> None:
        session = self.session_service.get_session(cmd.session_id)
        self.session_service.create_ping(
            session=session,
            author_peer_id=cmd.author_peer_id,
            x=cmd.x,
            y=cmd.y,
            label=cmd.label,
            duration_ms=cmd.duration_ms,
        )
```

- [ ] **Step 4: Implement SessionService.create_ping**

```python
# app/services/session_service.py

from api_contracts.events import MapPingEvent


class SessionService:
    # ...

    def create_ping(
        self,
        session: Dict[str, Any],
        author_peer_id: str,
        x: float,
        y: float,
        label: Optional[str],
        duration_ms: Optional[int],
    ) -> None:
        now = time.time()
        event = MapPingEvent(
            id=self._new_event_id(),
            session_id=session["id"],
            author_peer_id=author_peer_id,
            x=x,
            y=y,
            label=label,
            duration_ms=duration_ms,
            created_at=now,
        )
        self._append_event_and_broadcast(session, event)
```

- [ ] **Step 5: Add /ping endpoint**

```python
# api/http_api.py

from api.schemas import PingRequest
from api_contracts.commands import CreatePingCommand


@router.post("/api/sessions/{session_id}/ping")
async def ping_endpoint(
    session_id: str,
    body: PingRequest,
    context=Depends(get_request_context),
):
    dispatcher = context.dispatcher
    cmd = CreatePingCommand(
        session_id=session_id,
        author_peer_id=context.peer_id,
        x=body.x,
        y=body.y,
        label=body.label,
        duration_ms=body.duration_ms,
    )
    dispatcher.create_ping(cmd)
    return {"status": "ok"}
```

- [ ] **Step 6: Add backend tests for /ping**

```python
# tests/test_signaling_service.py

def test_ping_endpoint_creates_event(client, session_factory):
    session_id, peer_id, auth_headers = session_factory()
    resp = client.post(
        f"/api/sessions/{session_id}/ping",
        json={"x": 10.0, "y": 5.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 7: Run backend tests**

```bash
cd /Users/jkoch/DND
python -m pytest tests/test_signaling_service.py -q
```

Expected: tests pass.

---

## Task 5: Backend Visibility Filtering for Chat, Rolls, and Pings

**Files:**
- Modify: `app/services/session_service.py`
- Test: `tests/test_signaling_service.py`

- [ ] **Step 1: Extend filter_event_for_view to support ChatMessageEvent**

```python
# app/services/session_service.py

from api_contracts.events import ChatMessageEvent, RollResultEvent, MapPingEvent


class SessionService:
    # ...

    def filter_event_for_view(self, session: Dict[str, Any], viewer_peer_id: str, event: Any) -> Optional[Any]:
        flags = self.get_feature_flags(session)
        viewer_role = self._get_peer_role(session, viewer_peer_id)

        if isinstance(event, ChatMessageEvent):
            if event.gm_only and viewer_role not in ("GM", "AssistantGM"):
                if not flags.get("chat_visible_to_players", True):
                    return None
                # Optionally return a summary event instead; for now hide
                return None

            if event.targets:
                if viewer_peer_id != event.author_peer_id and viewer_peer_id not in event.targets:
                    if not flags.get("whispers_show_contents_to_non_participants", False):
                        return None
            return event

        # existing filtering for other event types...
        return event
```

- [ ] **Step 2: Extend filter_event_for_view to support RollResultEvent**

```python
# app/services/session_service.py

    def filter_event_for_view(self, session: Dict[str, Any], viewer_peer_id: str, event: Any) -> Optional[Any]:
        flags = self.get_feature_flags(session)
        viewer_role = self._get_peer_role(session, viewer_peer_id)

        if isinstance(event, RollResultEvent):
            if event.gm_only and viewer_role not in ("GM", "AssistantGM"):
                return None
            if event.targets:
                if viewer_peer_id != event.author_peer_id and viewer_peer_id not in event.targets:
                    if not flags.get("whispers_show_contents_to_non_participants", False):
                        return None
            if viewer_role not in ("GM", "AssistantGM") and not flags.get("dice_breakdown_visible_to_players", True):
                # hide breakdown but keep total
                clone = event.copy(deep=True)
                clone.result.breakdown = "hidden"
                clone.result.rolls = []
                clone.result.modifiers = []
                return clone
            return event

        # existing filtering...
        return event
```

- [ ] **Step 3: Extend filter_event_for_view to support MapPingEvent**

```python
# app/services/session_service.py

    def filter_event_for_view(self, session: Dict[str, Any], viewer_peer_id: str, event: Any) -> Optional[Any]:
        flags = self.get_feature_flags(session)
        viewer_role = self._get_peer_role(session, viewer_peer_id)

        if isinstance(event, MapPingEvent):
            if viewer_role not in ("GM", "AssistantGM") and not flags.get("pings_visible_to_players", True):
                return None
            return event

        # other cases...
        return event
```

- [ ] **Step 4: Add backend tests for visibility rules**

```python
# tests/test_signaling_service.py

def test_chat_gm_only_hidden_from_players(session_service, session_factory):
    session_id, gm_peer_id, _ = session_factory(role="GM")
    session = session_service.get_session(session_id)
    session_service.send_chat_message(
        session=session,
        author_peer_id=gm_peer_id,
        text="secret",
        gm_only=True,
        targets=[],
    )
    event = session["events"][-1]  # or use helper
    player_peer_id = "player-1"
    filtered = session_service.filter_event_for_view(session, player_peer_id, event)
    assert filtered is None
```

- [ ] **Step 5: Run backend tests**

```bash
cd /Users/jkoch/DND
python -m pytest tests/test_signaling_service.py -q
```

Expected: tests pass.

---

## Task 6: Frontend API Client Methods and Realtime Event Handling

**Files:**
- Modify: `frontend/src/lib/apiClient.ts`
- Modify: `frontend/src/realtime/sessionRealtime.ts`
- Test: `frontend/src/lib/apiClient.ts` tests if present or new `frontend/src/lib/apiClient.test.ts`

- [ ] **Step 1: Add chat, roll, and ping API client functions**

```ts
// frontend/src/lib/apiClient.ts

export async function sendChatMessage(sessionId: string, payload: { text: string; gmOnly?: boolean; targets?: string[] }) {
  await apiPost(`/api/sessions/${sessionId}/chat/send`, {
    text: payload.text,
    gm_only: payload.gmOnly ?? false,
    targets: payload.targets ?? null,
  });
}

export async function sendRoll(sessionId: string, payload: { formula: string; advantage?: boolean; disadvantage?: boolean }) {
  await apiPost(`/api/sessions/${sessionId}/roll`, {
    formula: payload.formula,
    advantage: payload.advantage ?? false,
    disadvantage: payload.disadvantage ?? false,
  });
}

export async function sendPing(sessionId: string, payload: { x: number; y: number; label?: string; durationMs?: number }) {
  await apiPost(`/api/sessions/${sessionId}/ping`, {
    x: payload.x,
    y: payload.y,
    label: payload.label ?? null,
    duration_ms: payload.durationMs ?? null,
  });
}
```

- [ ] **Step 2: Extend sessionRealtime to dispatch new events**

```ts
// frontend/src/realtime/sessionRealtime.ts

export type ChatMessageEvent = {
  id: string;
  session_id: string;
  author_peer_id: string;
  author_role: string;
  text: string;
  gm_only: boolean;
  targets?: string[] | null;
  kind: "plain" | "system" | "roll";
  created_at: number;
};

export type RollResultEvent = {
  id: string;
  session_id: string;
  author_peer_id: string;
  author_role: string;
  result: {
    formula: string;
    rolls: number[];
    modifiers: number[];
    total: number;
    breakdown: string;
    advantage: boolean;
    disadvantage: boolean;
  };
  gm_only: boolean;
  targets?: string[] | null;
  created_at: number;
};

export type MapPingEvent = {
  id: string;
  session_id: string;
  author_peer_id: string;
  x: number;
  y: number;
  label?: string | null;
  duration_ms?: number | null;
  created_at: number;
};

// in websocket message handler:
// detect event.type or shape and fan out to callbacks for ChatPanel / MapCanvas
```

- [ ] **Step 3: Add frontend tests for apiClient (optional but preferred)**

```ts
// frontend/src/lib/apiClient.test.ts

import { sendChatMessage } from "./apiClient";

it("calls chat endpoint with expected payload", async () => {
  // mock fetch / apiPost and assert body
});
```

- [ ] **Step 4: Run frontend unit tests**

```bash
cd /Users/jkoch/DND/frontend
npm test
```

Expected: tests pass.

---

## Task 7: ChatPanel Component and Dice Input UX

**Files:**
- Add: `frontend/src/components/ChatPanel.tsx`
- Modify: `frontend/src/components/layout/BottomTray.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/ChatPanel.test.tsx`

- [ ] **Step 1: Implement ChatPanel component**

```tsx
// frontend/src/components/ChatPanel.tsx

import React, { useState } from "react";
import { sendChatMessage, sendRoll } from "../lib/apiClient";

type ChatMessage = {
  id: string;
  kind: "plain" | "system" | "roll";
  text: string;
  authorLabel: string;
  createdAt: number;
};

interface ChatPanelProps {
  sessionId: string;
  messages: ChatMessage[];
  onSendLocal?: (msg: ChatMessage) => void;
  isGM: boolean;
}

export function ChatPanel({ sessionId, messages, isGM }: ChatPanelProps) {
  const [input, setInput] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    if (trimmed.startsWith("/roll ")) {
      const formula = trimmed.slice("/roll ".length).trim();
      await sendRoll(sessionId, { formula });
    } else {
      await sendChatMessage(sessionId, { text: trimmed });
    }

    setInput("");
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={`chat-line chat-line-${m.kind}`}>
            <span className="chat-author">{m.authorLabel}</span>
            <span className="chat-text">{m.text}</span>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="/roll 1d20+5 or say something..."
        />
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Integrate ChatPanel into BottomTray and App**

```tsx
// frontend/src/components/layout/BottomTray.tsx

import { ChatPanel } from "../ChatPanel";

// Add a tab for chat and render ChatPanel when active, wiring sessionId and messages from props/context
```

```tsx
// frontend/src/App.tsx

// maintain chat messages state from sessionRealtime and pass into BottomTray / ChatPanel
```

- [ ] **Step 3: Add ChatPanel tests**

```tsx
// frontend/src/components/ChatPanel.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import { ChatPanel } from "./ChatPanel";

test("submits /roll command via sendRoll", async () => {
  // mock sendRoll, render, type "/roll 1d20+5", submit, assert mock called
});
```

- [ ] **Step 4: Run frontend tests**

```bash
cd /Users/jkoch/DND/frontend
npm test -- ChatPanel
```

Expected: tests pass.

---

## Task 8: Presence Roster UI

**Files:**
- Modify: `frontend/src/components/StatusRail.tsx` (or `RightDrawer.tsx`, depending on UX choice)
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/StatusRail.test.tsx` or new test file

- [ ] **Step 1: Render peers with roles in StatusRail**

```tsx
// frontend/src/components/StatusRail.tsx

interface PeerInfo {
  id: string;
  name: string;
  role: string;
  connected: boolean;
}

interface StatusRailProps {
  peers: PeerInfo[];
  canSeePresence: boolean;
}

export function StatusRail({ peers, canSeePresence }: StatusRailProps) {
  return (
    <div className="status-rail">
      {/* existing content */}
      {canSeePresence && (
        <div className="presence-roster">
          {peers.map((p) => (
            <div key={p.id} className={`presence-entry ${p.connected ? "online" : "offline"}`}>
              <span className="presence-name">{p.name}</span>
              <span className="presence-role">{p.role}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Wire peers and visibility from App/sessionRealtime**

```tsx
// frontend/src/App.tsx

// derive peers from session state and visibility from feature flags
<StatusRail peers={peers} canSeePresence={featureFlags.presence_visible_to_players || isGM} />
```

- [ ] **Step 3: Add basic presence UI tests**

```tsx
// frontend/src/components/StatusRail.test.tsx

import { render, screen } from "@testing-library/react";
import { StatusRail } from "./StatusRail";

test("hides presence roster when canSeePresence is false", () => {
  render(<StatusRail peers={[]} canSeePresence={false} />);
  expect(screen.queryByText(/presence/i)).toBeNull();
});
```

- [ ] **Step 4: Run frontend tests**

```bash
cd /Users/jkoch/DND/frontend
npm test -- StatusRail
```

Expected: tests pass.

---

## Task 9: MapCanvas Ping UX

**Files:**
- Modify: `frontend/src/components/MapCanvas.tsx`
- Modify: `frontend/src/realtime/sessionRealtime.ts`
- Test: `frontend/src/components/MapCanvas.test.tsx`

- [ ] **Step 1: Emit ping on modifier-click**

```tsx
// frontend/src/components/MapCanvas.tsx

import { sendPing } from "../lib/apiClient";

export function MapCanvas(props: MapCanvasProps) {
  const { sessionId } = props;

  const handleMapClick = (event: React.MouseEvent) => {
    if (event.ctrlKey) {
      const { x, y } = screenToMapCoords(event.clientX, event.clientY);
      void sendPing(sessionId, { x, y });
      return;
    }
    // existing click behavior...
  };

  return (
    <canvas
      onClick={handleMapClick}
      // ...
    />
  );
}
```

- [ ] **Step 2: Render transient pings from realtime events**

```tsx
// frontend/src/components/MapCanvas.tsx

const [pings, setPings] = useState<MapPingEvent[]>([]);

useEffect(() => {
  const unsubscribe = sessionRealtime.onPing((event) => {
    setPings((current) => [...current, event]);
    const duration = event.duration_ms ?? 2000;
    setTimeout(() => {
      setPings((current) => current.filter((p) => p.id !== event.id));
    }, duration);
  });
  return unsubscribe;
}, []);

// in render path, draw pings over map using pings state
```

- [ ] **Step 3: Add MapCanvas ping tests**

```tsx
// frontend/src/components/MapCanvas.test.tsx

test("ctrl+click sends ping", () => {
  // mock sendPing, simulate ctrl+click, assert called
});
```

- [ ] **Step 4: Run frontend tests**

```bash
cd /Users/jkoch/DND/frontend
npm test -- MapCanvas
```

Expected: tests pass.

---

## Task 10: GM Feature Flag Endpoints and UI

**Files:**
- Modify: `api/schemas.py`
- Modify: `api/http_api.py`
- Modify: `app/services/session_service.py`
- Modify: `frontend/src/lib/apiClient.ts`
- Modify: `frontend/src/App.tsx` or relevant settings panel component
- Test: `tests/test_signaling_service.py`, frontend settings component tests

- [ ] **Step 1: Add UpdateFeatureFlagsRequest schema**

```python
# api/schemas.py

class UpdateFeatureFlagsRequest(BaseModel):
    chat_visible_to_players: Optional[bool] = None
    whispers_show_contents_to_non_participants: Optional[bool] = None
    dice_breakdown_visible_to_players: Optional[bool] = None
    presence_visible_to_players: Optional[bool] = None
    pings_visible_to_players: Optional[bool] = None
```

- [ ] **Step 2: Add GM-only endpoint to update feature flags**

```python
# api/http_api.py

from api.schemas import UpdateFeatureFlagsRequest


@router.post("/api/sessions/{session_id}/feature-flags")
async def update_feature_flags(
    session_id: str,
    body: UpdateFeatureFlagsRequest,
    context=Depends(get_request_context),
):
    # enforce GM-only
    if not context.is_gm:
        raise HTTPException(status_code=403, detail="GM only")

    flags_update = {k: v for k, v in body.dict().items() if v is not None}
    flags = context.session_service.update_feature_flags(session_id, flags_update)
    return {"feature_flags": flags}
```

- [ ] **Step 3: Add frontend client function for updating feature flags**

```ts
// frontend/src/lib/apiClient.ts

export async function updateSessionFeatureFlags(
  sessionId: string,
  updates: Partial<{
    chat_visible_to_players: boolean;
    whispers_show_contents_to_non_participants: boolean;
    dice_breakdown_visible_to_players: boolean;
    presence_visible_to_players: boolean;
    pings_visible_to_players: boolean;
  }>
) {
  const body: any = {};
  Object.entries(updates).forEach(([key, value]) => {
    if (value !== undefined) body[key] = value;
  });
  const res = await apiPost(`/api/sessions/${sessionId}/feature-flags`, body);
  return res.feature_flags;
}
```

- [ ] **Step 4: Add GM settings UI for toggles**

```tsx
// frontend/src/components/SessionSettingsPanel.tsx

import { updateSessionFeatureFlags } from "../lib/apiClient";

export function SessionSettingsPanel({ sessionId, featureFlags, isGM }: Props) {
  if (!isGM) return null;

  const toggle = async (key: keyof typeof featureFlags) => {
    const next = !featureFlags[key];
    await updateSessionFeatureFlags(sessionId, { [key]: next });
    // refresh feature flags via sessionRealtime or refetch
  };

  return (
    <div>
      <h3>Session Features</h3>
      <label>
        <input
          type="checkbox"
          checked={featureFlags.chat_visible_to_players}
          onChange={() => toggle("chat_visible_to_players")}
        />
        Players can see chat messages
      </label>
      {/* other toggles */}
    </div>
  );
}
```

- [ ] **Step 5: Add backend tests for GM-only update endpoint**

```python
# tests/test_signaling_service.py

def test_update_feature_flags_requires_gm_role(client, session_factory):
    session_id, peer_id, auth_headers = session_factory(role="Player")
    resp = client.post(
        f"/api/sessions/{session_id}/feature-flags",
        json={"chat_visible_to_players": False},
        headers=auth_headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 6: Add frontend tests for settings toggles (optional but preferred)**

```tsx
// frontend/src/components/SessionSettingsPanel.test.tsx

test("non-GM sees no session feature toggles", () => {
  // render with isGM=false and assert no checkbox
});
```

- [ ] **Step 7: Run backend and frontend tests**

```bash
cd /Users/jkoch/DND
python -m pytest -q

cd frontend
npm test
```

Expected: tests pass.

---

## Task 11: Update SESSION_HANDOFF.md and Final Verification

**Files:**
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Append summary of completed Phase 1 implementation**

Describe:
- Which endpoints and commands were added.
- How visibility and feature flags are wired.
- Where ChatPanel, presence roster, and ping UX live in the frontend.
- Which tests cover Phase 1.

- [ ] **Step 2: Run full test suites**

```bash
cd /Users/jkoch/DND
python -m pytest -q

cd frontend
npm test
npm run build
```

Expected: all tests and build succeed.

- [ ] **Step 3: Prepare for finishing-a-development-branch**

Once all tasks are complete and tests are passing:
- Use superpowers:finishing-a-development-branch to choose how to present/merge this work.

