from fastapi.testclient import TestClient

from net.signaling_service import app


def test_signal_queue_and_poll() -> None:
    client = TestClient(app)
    payload = {
        "session_id": "s1",
        "sender_id": "dm",
        "target_id": "p1",
        "payload": {"offer": "abc"},
    }
    assert client.post("/signal", json=payload).status_code == 200
    resp = client.get("/signal/p1")
    assert resp.status_code == 200
    assert len(resp.json()["messages"]) == 1
