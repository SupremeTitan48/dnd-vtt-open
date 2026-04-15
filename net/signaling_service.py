from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="DND VTT Signaling Service")


class SignalMessage(BaseModel):
    session_id: str
    sender_id: str
    target_id: str
    payload: dict


_message_bus: dict[str, list[SignalMessage]] = {}


@app.post("/signal")
def signal(message: SignalMessage) -> dict:
    _message_bus.setdefault(message.target_id, []).append(message)
    return {"queued": True}


@app.get("/signal/{peer_id}")
def poll(peer_id: str) -> dict:
    queued = _message_bus.pop(peer_id, [])
    return {"messages": [m.model_dump() for m in queued]}
