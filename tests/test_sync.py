from net.p2p_sync import P2PSyncBuffer


def test_sync_buffer_queue_and_acknowledge() -> None:
    sync = P2PSyncBuffer()
    sync.queue_token_move("hero", 1, 2)
    sync.queue_combat_update("hero", 1)

    events = sync.flush()
    assert len(events) == 2
    assert events[0]["seq"] == 1
    assert events[1]["seq"] == 2

    sync.acknowledge(1)
    remaining = sync.flush()
    assert len(remaining) == 1
    assert remaining[0]["seq"] == 2
