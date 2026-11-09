"""Offline tests for ig_search with a fake client."""

from __future__ import annotations

from as_ig_mcp import client, session, tools_discovery


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


def test_ig_search_dispatches_each_kind(tmp_path, monkeypatch):
    cases = (
        (
            "user",
            "search_users",
            [{"pk": "7", "username": "target", "full_name": "Target", "follower_count": 50}],
        ),
        ("hashtag", "hashtag_info", {"id": "123", "name": "chennai", "media_count": 900}),
        ("place", "fbsearch_places", [{"pk": 55, "name": "Marina Beach", "lat": 13.05, "lng": 80.28}]),
        ("music", "search_music", [{"id": "t1", "title": "Song", "display_artist": "Artist"}]),
        ("post", "fbsearch_topsearch_v2", {"users": [{"username": "target"}], "hashtags": []}),
        (
            "message",
            "direct_message_search",
            [({"text": "hello there"}, {"id": "t1", "users": [{"username": "bob"}]})],
        ),
        ("account", "search_users", [{"pk": "1", "username": "me", "full_name": "Me", "follower_count": 10}]),
    )

    for kind, method, value in cases:
        monkeypatch.setenv("APPDATA", str(tmp_path / kind))
        monkeypatch.setenv("IG_PLACES_LAT", "13.05")
        monkeypatch.setenv("IG_PLACES_LNG", "80.28")
        fake = _install(monkeypatch, {method: value})

        result = tools_discovery.ig_search(kind=kind, query="me" if kind == "account" else "target")

        assert result["ok"] is True, (kind, result)
        assert result["kind"] == kind
        assert method in fake.names(), (kind, fake.names())
        assert isinstance(result["items"], list)
        assert result["items"]


def test_ig_search_results_are_flattened(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "user"))
    _install(
        monkeypatch,
        {
            "search_users": [
                {"pk": "7", "username": "target", "full_name": "Target", "follower_count": 50}
            ]
        },
    )
    users = tools_discovery.ig_search(kind="user", query="target")
    assert users["items"][0] == {
        "username": "target",
        "full_name": "Target",
        "pk": "7",
        "followers": 50,
    }

    monkeypatch.setenv("APPDATA", str(tmp_path / "message"))
    _install(
        monkeypatch,
        {
            "direct_message_search": [
                ({"text": "hello there"}, {"id": "t1", "users": [{"username": "bob"}]})
            ]
        },
    )
    messages = tools_discovery.ig_search(kind="message", query="hello")
    assert messages["items"][0] == {
        "thread_id": "t1",
        "snippet": "hello there",
        "participants": ["bob"],
    }


def test_place_without_coordinates_returns_the_documented_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("IG_PLACES_LAT", raising=False)
    monkeypatch.delenv("IG_PLACES_LNG", raising=False)

    result = tools_discovery.ig_search(kind="place", query="chennai")

    assert result == {
        "ok": False,
        "error": "place search needs IG_PLACES_LAT and IG_PLACES_LNG",
    }


def test_unknown_kind_returns_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    result = tools_discovery.ig_search(kind="nothing", query="x")

    assert result["ok"] is False
    assert "unknown kind" in result["error"]
