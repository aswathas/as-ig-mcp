"""Offline tests for realtime socket manager, event normalisation and backoff."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from as_ig_mcp import events, realtime


@pytest.fixture
def clean_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("AS_IG_REALTIME", raising=False)
    yield tmp_path
    realtime.stop()


class FakeRealtimeClient:
    def __init__(self) -> None:
        self.call_log: list[str] = []
        self._handlers: dict[str, list[Any]] = {}
        self.is_connected = False
        self.read_once_error: Exception | None = None
        self.read_event = threading.Event()
        self.subscribe_count = 0

    def connect(self) -> None:
        self.call_log.append("connect")
        self.is_connected = True

    def disconnect(self) -> None:
        self.call_log.append("disconnect")
        self.is_connected = False

    def direct_subscribe(self) -> dict[str, Any]:
        self.call_log.append("direct_subscribe")
        self.subscribe_count += 1
        return {"seq_id": 123, "snapshot_at_ms": 1000}

    def on(self, event: str, handler: Any) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def realtime_read_once(self) -> Any:
        self.call_log.append("realtime_read_once")
        self.read_event.set()
        if self.read_once_error is not None:
            err = self.read_once_error
            self.read_once_error = None
            raise err
        time.sleep(0.01)
        return None

    def realtime_ping(self) -> bool:
        self.call_log.append("realtime_ping")
        return True

    def emit(self, event: str, payload: Any) -> None:
        for h in self._handlers.get(event, []):
            h(payload)


def test_start_calls_direct_subscribe_before_reader_thread_starts(clean_appdata):
    fake = FakeRealtimeClient()
    manager = realtime.RealtimeManager()

    manager.start(client_instance=fake)
    # Wait until read_once is called at least once
    assert fake.read_event.wait(timeout=1.0)
    manager.stop()

    # direct_subscribe MUST appear before realtime_read_once in call_log
    assert "direct_subscribe" in fake.call_log
    assert "realtime_read_once" in fake.call_log
    idx_sub = fake.call_log.index("direct_subscribe")
    idx_read = fake.call_log.index("realtime_read_once")
    assert idx_sub < idx_read
    # direct_subscribe called exactly once before reader thread
    assert fake.subscribe_count == 1


def test_socket_error_triggers_reconnect_with_backoff_and_resubscribe(clean_appdata, monkeypatch):
    monkeypatch.setattr(realtime, "BACKOFF_STEPS", (0.01, 0.02))

    fake = FakeRealtimeClient()
    fake.read_once_error = ConnectionError("socket dropped")
    manager = realtime.RealtimeManager()

    manager.start(client_instance=fake)
    # Wait for initial connect + reconnect after error
    for _ in range(50):
        if fake.subscribe_count >= 2:
            break
        time.sleep(0.02)
    manager.stop()

    assert fake.subscribe_count >= 2
    assert "connect" in fake.call_log


def test_events_are_normalised_to_documented_shape(clean_appdata):
    fake = FakeRealtimeClient()
    manager = realtime.RealtimeManager()
    manager.start(client_instance=fake)

    # Emit a typing event
    fake.emit("typing", {"thread_id": "thread_42", "activity_status": 1})
    manager.stop()

    evs = events.tail(offset=0)
    assert len(evs) == 1
    ev = evs[0]

    # documented shape: {"ts": epoch, "event": name, "thread_id": str|None, "value": any}
    assert set(ev.keys()) == {"ts", "event", "thread_id", "value"}
    assert isinstance(ev["ts"], (int, float))
    assert ev["event"] == "typing"
    assert ev["thread_id"] == "thread_42"
    assert ev["value"] == {"thread_id": "thread_42", "activity_status": 1}


def test_reaction_inside_message_is_classified_and_unclassifiable_keeps_raw(clean_appdata):
    fake = FakeRealtimeClient()
    manager = realtime.RealtimeManager()
    manager.start(client_instance=fake)

    # 1. Classified reaction
    fake.emit(
        "message",
        {
            "thread_id": "t1",
            "message": {
                "item_type": "reaction",
                "reaction_type": "❤️",
                "reaction_status": "created",
                "user_id": 999,
                "target_item_id": "msg_123",
            },
        },
    )

    # 2. Unclassifiable patch
    fake.emit(
        "message",
        {
            "thread_id": "t1",
            "message": {
                "unknown_opcode": 0xDEAD,
                "binary_blob": "obscure_instagram_experiment",
            },
        },
    )
    manager.stop()

    evs = events.tail(offset=0)
    assert len(evs) == 2

    # First event is classified reaction
    assert evs[0]["event"] == "message"
    assert "reaction" in evs[0]["value"]
    reaction = evs[0]["value"]["reaction"]
    assert reaction["reaction_type"] == "❤️"
    assert reaction["user_id"] == "999"

    # Second event is kept as raw
    assert evs[1]["event"] == "message"
    assert "raw" in evs[1]["value"]
    assert evs[1]["value"]["raw"]["message"]["unknown_opcode"] == 0xDEAD


def test_stop_closes_the_socket(clean_appdata):
    fake = FakeRealtimeClient()
    manager = realtime.RealtimeManager()

    manager.start(client_instance=fake)
    assert fake.read_event.wait(timeout=1.0)
    manager.stop()

    assert "disconnect" in fake.call_log
    assert not fake.is_connected
    assert manager.status()["connected"] is False


def test_with_as_ig_realtime_zero_nothing_starts(clean_appdata, monkeypatch):
    monkeypatch.setenv("AS_IG_REALTIME", "0")
    fake = FakeRealtimeClient()
    manager = realtime.RealtimeManager()

    manager.start(client_instance=fake)
    time.sleep(0.05)

    status = manager.status()
    assert status["enabled"] is False
    assert status["connected"] is False
    assert len(fake.call_log) == 0
