"""Offline tests for ig_thread with a fake client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from as_ig_mcp import client, session, tools_threads


class FakeClient:
    """Records the instagrapi method names the tools call."""

    def __init__(self, results: dict[str, Any]) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.results = results

    def __getattr__(self, name: str):
        def handler(**kwargs):
            self.calls.append((name, kwargs))
            val = self.results.get(name)
            if isinstance(val, Exception):
                raise val
            return val

        return handler

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def _install(monkeypatch, results: dict[str, Any]) -> FakeClient:
    fake = FakeClient(results)
    monkeypatch.setattr(client, "build_client", lambda settings: fake)
    monkeypatch.setattr(
        session,
        "load_session",
        lambda: {
            "username": "my_account",
            "user_id": "100",
            "cookies": {"sessionid": "100_x", "ds_user_id": "100"},
        },
    )
    return fake


SAMPLE_USER_1 = {
    "pk": "200",
    "username": "alice",
    "full_name": "Alice Smith",
    "is_private": False,
}

SAMPLE_USER_2 = {
    "pk": "300",
    "username": "bob",
    "full_name": "Bob Jones",
    "is_private": True,
}

SAMPLE_THREAD = {
    "id": "thread_123",
    "thread_id": "thread_123",
    "users": [SAMPLE_USER_1, SAMPLE_USER_2],
    "oldest_cursor": "cur_abc456",
    "messages": [
        {
            "id": "msg_1",
            "user_id": "200",
            "timestamp": datetime(2026, 11, 10, 2, 0, 0, tzinfo=timezone.utc),
            "text": "Hello there!",
            "item_type": "text",
            "is_sent_by_viewer": False,
        },
        {
            "id": "msg_2",
            "user_id": "100",
            "timestamp": datetime(2026, 11, 10, 2, 5, 0, tzinfo=timezone.utc),
            "text": "Hey Alice!",
            "item_type": "text",
            "is_sent_by_viewer": True,
        },
        {
            "id": "msg_3",
            "user_id": "200",
            "timestamp": datetime(2026, 11, 10, 2, 10, 0, tzinfo=timezone.utc),
            "text": None,
            "item_type": "media",
            "is_sent_by_viewer": False,
            "media": {"pk": "m_99"},
        },
    ],
}


def test_thread_resolves_and_formats_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {
            "direct_thread": SAMPLE_THREAD,
            "direct_users_presence": {"user_presence": {"200": {"is_active": True}}},
        },
    )

    result = tools_threads.ig_thread("thread_123", limit=10)

    assert result["ok"] is True
    assert result["thread_id"] == "thread_123"
    assert result["next_cursor"] == "cur_abc456"

    # Participants
    assert len(result["participants"]) == 2
    p0 = result["participants"][0]
    assert p0["username"] == "alice"
    assert p0["full_name"] == "Alice Smith"
    assert p0["pk"] == "200"
    assert p0["is_private"] is False

    # Messages
    assert len(result["messages"]) == 3
    m1 = result["messages"][0]
    assert m1["id"] == "msg_1"
    assert m1["sender_id"] == "200"
    assert m1["username"] == "alice"
    assert m1["text"] == "Hello there!"
    assert m1["item_type"] == "text"
    assert m1["is_ours"] is False
    assert m1["has_media"] is False
    assert "2026-11-10" in m1["timestamp"]

    m2 = result["messages"][1]
    assert m2["id"] == "msg_2"
    assert m2["sender_id"] == "100"
    assert m2["is_ours"] is True

    # Media message without text
    m3 = result["messages"][2]
    assert m3["id"] == "msg_3"
    assert m3["text"] == ""
    assert m3["has_media"] is True

    # Presence
    assert result["presence"] == {"200": {"is_active": True}}

    # Crucial safety check: no call to direct_message_seen or any seen mutator
    for call_name in fake.names():
        assert "seen" not in call_name
        assert call_name != "direct_message_seen"


def test_unknown_thread_id_returns_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    class DirectThreadNotFound(Exception):
        pass

    fake = _install(
        monkeypatch,
        {"direct_thread": DirectThreadNotFound("Thread does not exist")},
    )

    result = tools_threads.ig_thread("nonexistent_999")
    assert result["ok"] is False
    assert result["error"] == "thread not found: nonexistent_999"


def test_cursor_is_passed_to_underlying_pagination(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {"direct_thread": SAMPLE_THREAD},
    )

    result = tools_threads.ig_thread("thread_123", cursor="cursor_page_2")
    assert result["ok"] is True

    # Check that direct_thread was called with cursor="cursor_page_2"
    direct_calls = [c for c in fake.calls if c[0] == "direct_thread"]
    assert len(direct_calls) == 1
    assert direct_calls[0][1].get("cursor") == "cursor_page_2"


def test_unreadable_presence_returns_null_not_guess(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {
            "direct_thread": SAMPLE_THREAD,
            "direct_users_presence": RuntimeError("Presence service down"),
            "direct_active_presence": RuntimeError("Presence service down"),
        },
    )

    result = tools_threads.ig_thread("thread_123")
    assert result["ok"] is True
    assert result["presence"] is None
