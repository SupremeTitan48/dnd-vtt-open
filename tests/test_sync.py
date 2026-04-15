from net.p2p_sync import P2PSyncBuffer


def test_sync_buffer_queue_and_flush() -> None:
    sync = P2PSyncBuffer()
    sync.queue_token_move("hero", 1, 2)
    sync.queue_combat_update("hero", 1)
    events = sync.flush()
    assert len(events) == 2
    assert sync.flush() == []
