"""Offline tests for ig_account with a fake client."""

from __future__ import annotations

from typing import Any

from as_ig_mcp import client, session, tools_account


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
            "username": "my_biz_account",
            "user_id": "888",
            "cookies": {"sessionid": "888_x", "ds_user_id": "888"},
        },
    )
    return fake


def test_account_block_insights_and_linked_accounts_present(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    fake_profile = {
        "pk": "888",
        "username": "my_biz_account",
        "full_name": "My Business",
        "follower_count": 1250,
        "following_count": 300,
        "media_count": 45,
        "biography": "Official business account.",
        "category": "Entrepreneur",
        "is_business": True,
        "is_private": False,
        "external_url": "https://biz.example",
        "account_type": 2,
        "business_category_name": "Entrepreneur",
    }

    fake_insights = {
        "profile_visits": 540,
        "follower_growth": 35,
        "top_posts": [{"pk": "post_1", "reach": 1200}],
        "stories_count": 12,
    }

    fake_featured = {
        "accounts": [
            {"pk": "999", "username": "linked_personal", "full_name": "Personal Profile"}
        ]
    }

    fake = _install(
        monkeypatch,
        {
            "user_info_v1": fake_profile,
            "insights_account": fake_insights,
            "featured_accounts_v1": fake_featured,
        },
    )

    result = tools_account.ig_account()

    assert result["ok"] is True
    assert "account" in result
    assert "insights" in result
    assert "linked_accounts" in result

    # Check account block
    acc = result["account"]
    assert acc["username"] == "my_biz_account"
    assert acc["full_name"] == "My Business"
    assert acc["pk"] == "888"
    assert acc["follower_count"] == 1250
    assert acc["following_count"] == 300
    assert acc["media_count"] == 45
    assert acc["biography"] == "Official business account."
    assert acc["category"] == "Entrepreneur"
    assert acc["is_business"] is True
    assert acc["is_private"] is False
    assert acc["external_url"] == "https://biz.example"
    assert acc["professional_settings"]["account_type"] == 2

    # Check insights block
    ins = result["insights"]
    assert ins["profile_visits"] == 540
    assert ins["follower_growth"] == 35
    assert len(ins["top_posts"]) == 1
    assert ins["stories_count"] == 12

    # Check linked accounts
    linked = result["linked_accounts"]
    assert len(linked) == 1
    assert linked[0]["pk"] == "999"
    assert linked[0]["username"] == "linked_personal"
    assert linked[0]["full_name"] == "Personal Profile"


def test_missing_values_are_null_with_note_never_invented_number(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    # Sparse profile returning None for counts and category
    sparse_profile = {
        "pk": "888",
        "username": "sparse_acc",
        "full_name": "Sparse Profile",
        "follower_count": None,
        "following_count": None,
        "media_count": None,
        "biography": None,
        "category": None,
        "is_business": False,
        "is_private": False,
        "external_url": None,
    }

    # Insights fails or returns empty
    _install(
        monkeypatch,
        {
            "user_info_v1": sparse_profile,
            "insights_account": RuntimeError("Not a business account"),
            "featured_accounts_v1": {"accounts": []},
            "get_account_family_v1": {"accounts": []},
        },
    )

    result = tools_account.ig_account()
    assert result["ok"] is True

    acc = result["account"]
    # Must be None (null), NEVER 0 or invented
    assert acc["follower_count"] is None
    assert acc["following_count"] is None
    assert acc["media_count"] is None
    assert acc["biography"] is None
    assert acc["external_url"] is None

    # Must explain why in notes
    assert "follower_count" in acc["notes"]
    assert "following_count" in acc["notes"]
    assert "media_count" in acc["notes"]

    # Insights must have nulls with notes
    ins = result["insights"]
    assert ins["profile_visits"] is None
    assert ins["follower_growth"] is None
    assert "insights" in ins["notes"]

    # Linked accounts empty must say plainly
    assert result["linked_accounts"] == []
    assert "No linked accounts found" in result["notes"]["linked_accounts"]
