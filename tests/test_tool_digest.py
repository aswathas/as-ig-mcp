"""Offline tests for ig_digest: first-run markers, deltas, live state and timeout."""

from __future__ import annotations

import time
from typing import Any

import pytest

from as_ig_mcp import cli, client, realtime, session, state, tools_digest


@pytest.fixture
def clean_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(
        session,
        "load_session",
        lambda: {
            "username": "tester",
            "user_id": "42",
            "cookies": {"sessionid": "42_cookie"},
        },
    )
    yield tmp_path
    realtime.stop()


class FakeClient:
    def __init__(self) -> None:
        self.threads: list[dict[str, Any]] = []
        self.follower_count = 50
        self.follower_list: list[dict[str, Any]] = [{"pk": "u1", "username": "alice"}]
        self.posts: list[dict[str, Any]] = []
        self.stories: list[dict[str, Any]] = []

    def direct_threads(self, amount: int = 20) -> list[dict[str, Any]]:
        return self.threads

    def user_info_v1(self, user_id: str) -> dict[str, Any]:
        return {"pk": user_id, "follower_count": self.follower_count}

    def user_followers_v1(self, user_id: str, amount: int = 50) -> list[dict[str, Any]]:
        return self.follower_list

    def user_medias_v1(self, user_id: str, amount: int = 12) -> list[dict[str, Any]]:
        return self.posts

    def user_stories(self, user_id: str) -> list[dict[str, Any]]:
        return self.stories


def test_first_call_reports_first_run_and_writes_markers(clean_appdata, monkeypatch):
    fake = FakeClient()
    fake.threads = [
        {
            "id": "t1",
            "messages": [
                {"id": "m1", "user_id": "u2", "text": "hello", "timestamp": time.time()}
            ],
        }
    ]
    fake.posts = [{"pk": "p1", "caption_text": "first post", "taken_at": time.time()}]
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    res = tools_digest.ig_digest()
    assert res["ok"] is True
    assert res.get("first_run") is True
    assert res["new_messages"] == []
    assert res["new_posts"] == []
    assert res["markers_updated_at"] is not None

    # Check markers written to SQLite
    with state.connect() as conn:
        row = conn.execute("SELECT value FROM digest WHERE key = 'markers'").fetchone()
        assert row is not None
        assert "t1" in row["value"]
        assert "p1" in row["value"]


def test_second_call_with_no_change_reports_nothing_changed(clean_appdata, monkeypatch):
    fake = FakeClient()
    fake.threads = [
        {
            "id": "t1",
            "messages": [
                {"id": "m1", "user_id": "u2", "text": "hello", "timestamp": time.time()}
            ],
        }
    ]
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    first = tools_digest.ig_digest()
    assert first["first_run"] is True

    # Call again with identical state
    second = tools_digest.ig_digest()
    assert second["first_run"] is False
    assert second["nothing_changed"] is True
    assert second["new_messages"] == []
    assert second["new_posts"] == []
    assert second["new_stories"] == []
    assert second["events"] == []


def test_changed_message_shows_up_in_new_messages(clean_appdata, monkeypatch):
    fake = FakeClient()
    now = time.time()
    fake.threads = [
        {
            "id": "t1",
            "messages": [
                {"id": "m1", "user_id": "u2", "text": "hello", "timestamp": now}
            ],
        }
    ]
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    tools_digest.ig_digest()

    # Now a new message arrives in thread t1
    fake.threads = [
        {
            "id": "t1",
            "messages": [
                {"id": "m2", "user_id": "u2", "text": "how are you?", "timestamp": now + 5}
            ],
        }
    ]

    second = tools_digest.ig_digest()
    assert second["first_run"] is False
    assert len(second["new_messages"]) == 1
    new_msg = second["new_messages"][0]
    assert new_msg["thread_id"] == "t1"
    assert new_msg["message_id"] == "m2"
    assert new_msg["text"] == "how are you?"
    assert new_msg["sender"] == "u2"


def test_digest_reads_live_state_not_cache_assert_fresh_is_true(clean_appdata, monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    fresh_calls: list[tuple[str, bool]] = []

    orig_read_inbox = tools_digest.read_inbox
    orig_read_followers = tools_digest.read_followers
    orig_read_posts = tools_digest.read_posts
    orig_read_stories = tools_digest.read_stories

    def spy_read_inbox(*args, **kwargs):
        fresh_calls.append(("inbox", kwargs.get("fresh", False)))
        return orig_read_inbox(*args, **kwargs)

    def spy_read_followers(*args, **kwargs):
        fresh_calls.append(("followers", kwargs.get("fresh", False)))
        return orig_read_followers(*args, **kwargs)

    def spy_read_posts(*args, **kwargs):
        fresh_calls.append(("posts", kwargs.get("fresh", False)))
        return orig_read_posts(*args, **kwargs)

    def spy_read_stories(*args, **kwargs):
        fresh_calls.append(("stories", kwargs.get("fresh", False)))
        return orig_read_stories(*args, **kwargs)

    monkeypatch.setattr(tools_digest, "read_inbox", spy_read_inbox)
    monkeypatch.setattr(tools_digest, "read_followers", spy_read_followers)
    monkeypatch.setattr(tools_digest, "read_posts", spy_read_posts)
    monkeypatch.setattr(tools_digest, "read_stories", spy_read_stories)

    res = tools_digest.ig_digest()
    assert res["ok"] is True

    # Assert every underlying read was called with fresh=True
    assert len(fresh_calls) == 4
    for name, fresh in fresh_calls:
        assert fresh is True, f"Underlying read {name} was not called with fresh=True"


def test_timeout_with_socket_off_returns_after_timeout_without_hanging(clean_appdata, monkeypatch):
    monkeypatch.setenv("AS_IG_REALTIME", "0")
    fake = FakeClient()
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    # Initialize first run
    tools_digest.ig_digest()

    t0 = time.time()
    res = tools_digest.ig_digest(timeout_s=0.1)
    elapsed = time.time() - t0

    assert res["ok"] is True
    assert res["events"] == []
    assert elapsed >= 0.08
    assert elapsed < 0.5


def test_cli_digest_and_realtime_commands(clean_appdata, monkeypatch, capsys):
    fake = FakeClient()
    monkeypatch.setattr(client, "build_client", lambda settings: fake)

    code = cli.main(["digest"])
    assert code == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out.lower()

    code_rt = cli.main(["realtime"])
    assert code_rt == 0
    out_rt = capsys.readouterr().out
    assert '"enabled"' in out_rt
