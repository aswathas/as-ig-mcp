"""Offline tests for ig_inbox with a fake client."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from as_ig_mcp import client, session, tools_inbox


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
            "username": "me",
            "user_id": "1",
            "cookies": {"sessionid": "1_x", "ds_user_id": "1"},
        },
    )
    return fake


def test_thread_whose_last_message_is_ours_is_not_listed(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    now = datetime.now(timezone.utc)
    # Thread 1: last message is from other user (waiting reply)
    t1 = {
        "id": "t1",
        "users": [{"pk": "2", "username": "alice"}],
        "read_state": 1,
        "messages": [
            {
                "id": "m1",
                "user_id": "2",
                "timestamp": now,
                "text": "Are you available?",
                "is_sent_by_viewer": False,
            }
        ],
    }
    # Thread 2: last message is from ourselves (NOT waiting reply)
    t2 = {
        "id": "t2",
        "users": [{"pk": "3", "username": "bob"}],
        "read_state": 0,
        "messages": [
            {
                "id": "m2",
                "user_id": "1",
                "timestamp": now,
                "text": "Thanks, talk soon!",
                "is_sent_by_viewer": True,
            }
        ],
    }

    _install(monkeypatch, {"direct_threads": [t1, t2]})

    result = tools_inbox.ig_inbox(hours=48)
    assert result["ok"] is True
    assert len(result["items"]) == 1
    assert result["items"][0]["thread_id"] == "t1"
    assert result["items"][0]["username"] == "alice"
    assert result["items"][0]["last_message_text"] == "Are you available?"


def test_thread_id_returns_exactly_that_thread(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    now = datetime.now(timezone.utc)
    t_specific = {
        "id": "t_specific",
        "users": [{"pk": "5", "username": "carol"}],
        "read_state": 0,
        "messages": [
            {
                "id": "m_spec",
                "user_id": "5",
                "timestamp": now,
                "text": "Cross-check message body",
                "is_sent_by_viewer": False,
            }
        ],
    }

    _install(monkeypatch, {"direct_thread": t_specific})

    result = tools_inbox.ig_inbox(thread_id="t_specific")
    assert result["ok"] is True
    assert result["thread_id"] == "t_specific"
    assert result["thread"]["thread_id"] == "t_specific"
    assert result["thread"]["username"] == "carol"
    assert result["thread"]["last_message_text"] == "Cross-check message body"


def test_suggested_reply_constraints_and_sources(tmp_path, monkeypatch):
    # Setup style.json with dangerous content: links, emails, phone numbers, and > 2 sentences
    app_dir = tmp_path / "as-ig-mcp"
    app_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APPDATA", str(tmp_path))

    style_data = {
        "alice": {
            "relationship": "client",
            "language": "en",
            "formality": "casual",
            "personality_notes": "busy founder",
            "topics": ["code", "design"],
            "response_style": "Reach me at test@example.com or visit https://spam.com or call +1-555-867-5309! First sentence. Second sentence. Third sentence should be removed.",
        }
    }
    (app_dir / "style.json").write_text(json.dumps(style_data), encoding="utf-8")

    now = datetime.now(timezone.utc)
    t_alice = {
        "id": "t_alice",
        "users": [{"pk": "2", "username": "alice"}],
        "messages": [
            {
                "id": "m_a",
                "user_id": "2",
                "timestamp": now,
                "text": "Hey there",
                "is_sent_by_viewer": False,
            }
        ],
    }
    t_stranger = {
        "id": "t_stranger",
        "users": [{"pk": "99", "username": "stranger"}],
        "messages": [
            {
                "id": "m_s",
                "user_id": "99",
                "timestamp": now,
                "text": "Hello",
                "is_sent_by_viewer": False,
            }
        ],
    }

    _install(monkeypatch, {"direct_threads": [t_alice, t_stranger]})

    result = tools_inbox.ig_inbox(suggest=True)
    assert result["ok"] is True
    items = {item["username"]: item for item in result["items"]}

    # Alice has a style entry
    alice_item = items["alice"]
    assert alice_item["suggested_source"] == "style.json"
    reply_alice = alice_item["suggested_reply"]

    # Verify safety constraints:
    # 1. No links
    assert "http" not in reply_alice
    assert "https" not in reply_alice
    assert "spam.com" not in reply_alice
    # 2. No email
    assert "@" not in reply_alice
    # 3. No phone number
    assert "555" not in reply_alice
    assert "867" not in reply_alice
    # 4. At most 2 sentences
    sentences = [s.strip() for s in reply_alice.split(".") if s.strip()]
    assert len(sentences) <= 2

    # Stranger has no style entry -> default template
    stranger_item = items["stranger"]
    assert stranger_item["suggested_source"] == "default template"
    assert stranger_item["suggested_reply"] == tools_inbox.DEFAULT_TEMPLATE


def test_sanitize_suggested_reply_directly():
    raw = (
        "Check this out: https://example.com/promo or email support@site.org or dial +1 800 555 0199. "
        "We are happy to assist. Here is another sentence. And a fourth sentence."
    )
    sanitized = tools_inbox.sanitize_suggested_reply(raw)
    assert "http" not in sanitized
    assert "@" not in sanitized
    assert "800" not in sanitized
    assert "555" not in sanitized
    assert "fourth" not in sanitized


def test_box_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    now = datetime.now(timezone.utc)
    thread = {
        "id": "t_req",
        "users": [{"pk": "10", "username": "requester"}],
        "messages": [
            {
                "id": "m_req",
                "user_id": "10",
                "timestamp": now,
                "text": "Can I message you?",
                "is_sent_by_viewer": False,
            }
        ],
    }
    fake = _install(monkeypatch, {"direct_pending_inbox": [thread]})

    result = tools_inbox.ig_inbox(box="requests")
    assert result["ok"] is True
    assert result["box"] == "requests"
    assert len(result["items"]) == 1
    assert result["items"][0]["thread_id"] == "t_req"
    assert ("direct_pending_inbox", {"amount": 10}) in fake.calls


def test_box_general(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    now = datetime.now(timezone.utc)
    thread = {
        "id": "t_gen",
        "users": [{"pk": "20", "username": "general_user"}],
        "messages": [
            {
                "id": "m_gen",
                "user_id": "20",
                "timestamp": now,
                "text": "General thread message",
                "is_sent_by_viewer": False,
            }
        ],
    }
    fake = _install(monkeypatch, {"direct_threads": [thread]})

    result = tools_inbox.ig_inbox(box="general")
    assert result["ok"] is True
    assert result["box"] == "general"
    assert len(result["items"]) == 1
    assert result["items"][0]["thread_id"] == "t_gen"
    assert ("direct_threads", {"amount": 10, "box": "general"}) in fake.calls


def test_kind_groups(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    now = datetime.now(timezone.utc)
    t_dm = {
        "id": "t_dm",
        "is_group": False,
        "users": [{"pk": "30", "username": "single_user"}],
        "messages": [
            {
                "id": "m_dm",
                "user_id": "30",
                "timestamp": now,
                "text": "1-on-1 message",
                "is_sent_by_viewer": False,
            }
        ],
    }
    t_grp = {
        "id": "t_grp",
        "is_group": True,
        "users": [
            {"pk": "31", "username": "group_user1"},
            {"pk": "32", "username": "group_user2"},
        ],
        "messages": [
            {
                "id": "m_grp",
                "user_id": "31",
                "timestamp": now,
                "text": "Group message",
                "is_sent_by_viewer": False,
            }
        ],
    }
    fake = _install(monkeypatch, {"direct_threads": [t_dm, t_grp]})

    result = tools_inbox.ig_inbox(kind="groups")
    assert result["ok"] is True
    assert result["kind"] == "groups"
    assert len(result["items"]) == 1
    assert result["items"][0]["thread_id"] == "t_grp"
    assert result["items"][0]["is_group"] is True
    assert ("direct_threads", {"amount": 30}) in fake.calls


def test_unknown_box():
    result = tools_inbox.ig_inbox(box="invalid_box")
    assert result["ok"] is False
    assert result["error"] == "unknown box: invalid_box; valid: general, primary, requests, spam"
