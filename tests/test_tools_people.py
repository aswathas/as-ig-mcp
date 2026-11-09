"""Offline tests for ig_person and ig_people with a fake client."""

from __future__ import annotations

from datetime import datetime

from as_ig_mcp import client, session, tools_people


class FakeClient:
    """Records the instagrapi method names the tools call."""

    def __init__(self, results: dict[str, object]) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.results = results

    def __getattr__(self, name: str):
        def handler(**kwargs):
            self.calls.append((name, kwargs))
            return self.results.get(name, [])

        return handler

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def _install(monkeypatch, results: dict[str, object]) -> FakeClient:
    fake = FakeClient(results)
    monkeypatch.setattr(client, "build_client", lambda settings: fake)
    monkeypatch.setattr(
        session,
        "load_session",
        lambda: {
            "username": "me",
            "user_id": "1",
            "cookies": {"sessionid": "1_x", "ds_user_id": "1"},
            "authorization_data": {"user_id": "1"},
        },
    )
    return fake


PROFILE = {
    "pk": "42",
    "username": "target",
    "full_name": "Target Account",
    "biography": "hello",
    "follower_count": 242,
    "following_count": 17,
    "media_count": 5,
    "is_private": False,
    "is_business": True,
    "external_url": "https://example.com",
    "category": "Creator",
}

MEDIA = {
    "pk": "9",
    "code": "abc123",
    "media_type": 1,
    "taken_at": datetime(2026, 11, 1, 8, 0, 0),
    "caption_text": "a post",
    "like_count": 12,
    "comment_count": 3,
    "thumbnail_url": "https://cdn.example/thumb.jpg",
    "user": {"username": "target"},
    "product_type": "feed",
}

USER = {
    "pk": "7",
    "username": "fan",
    "full_name": "Fan Account",
    "is_private": False,
    "friendship_status": {"following": True},
}


def test_ig_person_resolves_username_and_honours_include(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {
            "user_info_by_username": {"pk": "42", "username": "target"},
            "user_info_v1": PROFILE,
            "user_followers_v1_chunk": ([USER], "cursor-1"),
            "user_medias_paginated_v1": ([MEDIA], ""),
            "user_suggested_profiles": {"users": [{**USER, "pk": "8", "username": "sug"}]},
            "user_about_v1": {"username": "target", "country": "IN"},
        },
    )

    result = tools_people.ig_person(
        username="target",
        include="followers,posts,suggestions,about,unknown",
        limit=10,
    )

    assert result["ok"] is True
    assert result["user_id"] == "42"
    assert result["username"] == "target"
    assert result["profile"]["follower_count"] == 242
    assert result["profile"]["biography"] == "hello"
    assert result["profile"]["category"] == "Creator"
    assert result["includes"]["followers"][0]["username"] == "fan"
    assert result["includes"]["followers"][0]["followed_by_me"] is True
    assert result["includes"]["posts"][0]["pk"] == "9"
    assert result["includes"]["posts"][0]["caption"] == "a post"
    assert result["includes"]["suggestions"][0]["username"] == "sug"
    assert result["includes"]["about"]["country"] == "IN"
    assert "unknown" not in result["includes"]
    assert "user_info_by_username" in fake.names()
    assert "user_info_v1" in fake.names()


def test_ig_person_without_arguments_uses_the_logged_in_account(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(monkeypatch, {"user_info_v1": PROFILE})

    result = tools_people.ig_person()

    assert result["ok"] is True
    assert result["user_id"] == "1"


def test_ig_people_returns_each_kind(tmp_path, monkeypatch):
    cases = (
        ("followers", "user_followers_v1_chunk", ([USER], "next"), True),
        ("following", "user_following_v1_chunk", ([USER], "next"), True),
        ("requests", "user_follow_requests_chunk", ([USER], "next"), True),
        ("suggested", "user_suggested_profiles", {"users": [USER]}, False),
    )

    for kind, method, value, cursor_supported in cases:
        monkeypatch.setenv("APPDATA", str(tmp_path / kind))
        fake = _install(monkeypatch, {method: value})

        result = tools_people.ig_people(kind=kind)

        assert result["ok"] is True, result
        assert result["kind"] == kind
        assert result["cursor_supported"] is cursor_supported
        assert result["items"][0]["username"] == "fan"
        assert result["items"][0]["pk"] == "7"
        assert method in fake.names(), (kind, fake.names())


def test_ig_people_unknown_kind_returns_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    result = tools_people.ig_people(kind="strangers")

    assert result["ok"] is False
    assert "unknown kind" in result["error"]
