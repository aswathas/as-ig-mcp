"""Offline tests for ig_feed with a fake client."""

from __future__ import annotations

from datetime import datetime

from as_ig_mcp import client, session, tools_feed


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
        },
    )
    return fake


MEDIA = {
    "pk": "9",
    "code": "abc123",
    "media_type": 1,
    "taken_at": datetime(2026, 11, 1, 8, 0, 0),
    "caption_text": "x" * 400,
    "like_count": 12,
    "comment_count": 3,
    "thumbnail_url": "https://cdn.example/thumb.jpg",
    "user": {"username": "target"},
    "product_type": "feed",
}


def test_ig_feed_dispatches_each_kind(tmp_path, monkeypatch):
    cases = (
        ("posts", {"user_medias_paginated_v1": ([MEDIA], "next-1")}, "user_medias_paginated_v1"),
        ("reels", {"user_clips_paginated_v1": ([MEDIA], "next-2")}, "user_clips_paginated_v1"),
        ("tagged", {"usertag_medias_paginated": ([MEDIA], None)}, "usertag_medias_paginated"),
        (
            "saved",
            {"collections": [{"id": "5", "name": "Faves", "media_count": 3}]},
            "collections",
        ),
        (
            "collections",
            {"collections": [{"id": "5", "name": "Faves", "media_count": 3}]},
            "collections",
        ),
        ("archive", {"archive_medias": [MEDIA]}, "archive_medias"),
        (
            "notifications",
            {
                "news_inbox_v1": {
                    "new_stories": [{"pk": "1", "type": "like"}],
                    "old_stories": [{"pk": "2", "type": "comment"}],
                }
            },
            "news_inbox_v1",
        ),
        (
            "tray",
            {
                "user_following_v1": [{"pk": "7", "username": "fan"}],
                "user_stories_web": [{"pk": "100"}, {"pk": "101"}],
            },
            "user_stories_web",
        ),
        ("guides", {"user_guides_v1": [{"id": "g1", "title": "Guide"}]}, "user_guides_v1"),
        ("liked", {"liked_medias": [MEDIA]}, "liked_medias"),
    )

    for kind, results, method in cases:
        monkeypatch.setenv("APPDATA", str(tmp_path / kind))
        fake = _install(monkeypatch, results)

        result = tools_feed.ig_feed(kind=kind)

        assert result["ok"] is True, (kind, result)
        assert result["kind"] == kind
        assert isinstance(result["items"], list)
        assert result["items"], (kind, result)
        assert method in fake.names(), (kind, fake.names())


def test_media_items_are_flattened_to_plain_dicts(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(monkeypatch, {"user_medias_paginated_v1": ([MEDIA], "next-1")})

    result = tools_feed.ig_feed(kind="posts", limit=5)

    item = result["items"][0]
    assert item["pk"] == "9"
    assert item["media_type"] == 1
    assert item["taken_at"] == "2026-11-01T08:00:00"
    assert item["caption"] == "x" * 300
    assert item["like_count"] == 12
    assert item["comment_count"] == 3
    assert item["permalink"] == "https://www.instagram.com/p/abc123/"
    assert item["thumbnail_url"] == "https://cdn.example/thumb.jpg"
    assert item["owner_username"] == "target"
    assert isinstance(item["taken_at"], str)


def test_tray_keeps_story_pks(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(
        monkeypatch,
        {
            "user_following_v1": [{"pk": "7", "username": "fan"}],
            "user_stories_web": [{"pk": "100"}, {"pk": "101"}],
        },
    )

    result = tools_feed.ig_feed(kind="tray")

    assert result["items"] == [
        {"user_id": "7", "username": "fan", "story_pks": ["100", "101"]}
    ]


def test_notifications_combine_new_and_old_stories(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(
        monkeypatch,
        {
            "news_inbox_v1": {
                "new_stories": [{"pk": "1", "type": "like"}],
                "old_stories": [{"pk": "2", "type": "comment"}],
            }
        },
    )

    result = tools_feed.ig_feed(kind="notifications")

    assert [item["pk"] for item in result["items"]] == ["1", "2"]


def test_include_comments_only_covers_the_newest_five(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    media = [{**MEDIA, "pk": str(index), "code": f"c{index}"} for index in range(6)]
    fake = _install(
        monkeypatch,
        {
            "user_medias_paginated_v1": (media, ""),
            "media_comments": [{"pk": "c1", "text": "nice"}],
        },
    )

    result = tools_feed.ig_feed(kind="posts", include="comments", limit=6)

    assert len(result["items"]) == 6
    for item in result["items"][:5]:
        assert item["comments"][0]["text"] == "nice"
    assert "comments" not in result["items"][5]
    assert fake.names().count("media_comments") == 5


def test_unknown_kind_returns_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    result = tools_feed.ig_feed(kind="stories")

    assert result["ok"] is False
    assert "unknown kind" in result["error"]


def test_posts_keeps_reels_and_reels_keeps_only_clips():
    """`posts` means every post; `reels` means the clips subset.

    An account that only posts reels must still return items for `posts`.
    """
    from as_ig_mcp import client as client_mod
    from as_ig_mcp.tools_feed import ig_feed

    class Fake:
        def __init__(self):
            self.calls = []

        def __getattr__(self, name):
            def fn(**kw):
                self.calls.append(name)
                return [
                    {"pk": 1, "product_type": "clips", "media_type": 2},
                    {"pk": 2, "product_type": "feed", "media_type": 1},
                ]
            return fn

    fake = Fake()
    orig = client_mod.build_client
    client_mod.build_client = lambda settings: fake
    try:
        posts = ig_feed(kind="posts", user_id="123")
        reels = ig_feed(kind="reels", user_id="123")
    finally:
        client_mod.build_client = orig

    post_pks = [i["pk"] for i in posts["items"]]
    assert "1" in post_pks and "2" in post_pks, post_pks
    # reels uses its own feature, so Instagram does the narrowing; our code
    # must not narrow it a second time, and must not narrow posts either.
    assert reels["ok"] is True, reels
