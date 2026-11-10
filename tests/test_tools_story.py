"""Offline tests for ig_story with a fake client."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from as_ig_mcp import client, session, tools_story


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
            if callable(val):
                return val(**kwargs)
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


SAMPLE_STORY = {
    "pk": "story_123",
    "user": {"pk": "99", "username": "creator"},
    "taken_at": datetime(2026, 11, 10, 1, 0, 0, tzinfo=timezone.utc),
    "thumbnail_url": "https://cdn.example/thumb.jpg",
    "video_url": None,
    "is_seen": True,
}


def test_each_action_dispatches_to_the_right_feature(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    fake_download_path = tmp_path / "as-ig-mcp" / "media" / "story_123.jpg"

    def fake_download(**kwargs):
        folder = Path(kwargs.get("folder", tmp_path))
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{kwargs.get('story_pk')}.jpg"
        target.write_text("fake media content", encoding="utf-8")
        return target

    results = {
        "story_info": SAMPLE_STORY,
        "story_viewers": [{"pk": "10", "username": "viewer1"}],
        "story_likers": [{"pk": "20", "username": "liker1"}],
        "story_download": fake_download,
    }
    fake = _install(monkeypatch, results)

    # 1. info
    res_info = tools_story.ig_story(story_id="story_123", action="info")
    assert res_info["ok"] is True
    assert res_info["action"] == "info"
    assert res_info["story"]["pk"] == "story_123"
    assert res_info["story"]["owner"] == "creator"
    assert res_info["story"]["seen"] is True
    assert "story_info" in fake.names()

    # 2. viewers
    res_viewers = tools_story.ig_story(story_id="story_123", action="viewers")
    assert res_viewers["ok"] is True
    assert res_viewers["action"] == "viewers"
    assert len(res_viewers["viewers"]) == 1
    assert res_viewers["viewers"][0]["username"] == "viewer1"
    assert "story_viewers" in fake.names()

    # 3. likers
    res_likers = tools_story.ig_story(story_id="story_123", action="likers")
    assert res_likers["ok"] is True
    assert res_likers["action"] == "likers"
    assert len(res_likers["likers"]) == 1
    assert res_likers["likers"][0]["username"] == "liker1"
    assert "story_likers" in fake.names()

    # 4. download
    res_dl = tools_story.ig_story(story_id="story_123", action="download")
    assert res_dl["ok"] is True
    assert res_dl["action"] == "download"
    assert "media" in res_dl["path"]
    assert "story_download" in fake.names()


def test_missing_id_returns_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(monkeypatch, {})

    res = tools_story.ig_story(action="info")
    assert res["ok"] is False
    assert "missing story_id or highlight_id" in res["error"]


def test_highlight_id_resolves_to_stories(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    sample_highlight = {
        "pk": "hl_555",
        "title": "Summer Vibes",
        "items": [
            SAMPLE_STORY,
            {
                "pk": "story_456",
                "user": {"pk": "99", "username": "creator"},
                "taken_at": datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc),
                "thumbnail_url": "https://cdn.example/thumb2.jpg",
                "video_url": None,
                "is_seen": False,
            },
        ],
    }

    fake = _install(monkeypatch, {"highlight_info": sample_highlight})

    res = tools_story.ig_story(highlight_id="hl_555", action="info")
    assert res["ok"] is True
    assert res["highlight_id"] == "hl_555"
    assert res["title"] == "Summer Vibes"
    assert len(res["stories"]) == 2
    assert res["stories"][0]["pk"] == "story_123"
    assert res["stories"][1]["pk"] == "story_456"
    assert "highlight_info" in fake.names()


def test_download_path_stays_inside_media_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    # Test path escaping attempt
    evil_path = tmp_path.parent / "escape.txt"
    _install(monkeypatch, {"story_download": str(evil_path)})

    res = tools_story.ig_story(story_id="story_123", action="download")
    assert res["ok"] is False
    assert "outside media" in res["error"]


def test_story_viewers_key_error_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(monkeypatch, {"story_viewers": KeyError("viewers")})

    res = tools_story.ig_story(story_id="story_123", action="viewers")
    assert res["ok"] is True
    assert res["action"] == "viewers"
    assert res["story_id"] == "story_123"
    assert res["viewers"] == []
    assert "viewers" in res["note"]
    assert "story_viewers" in fake.names()


def test_story_viewers_value_error_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(monkeypatch, {"story_viewers": ValueError("bad payload")})

    res = tools_story.ig_story(story_id="story_123", action="viewers")
    assert res["ok"] is True
    assert res["action"] == "viewers"
    assert res["story_id"] == "story_123"
    assert res["viewers"] == []
    assert "note" in res
    assert "viewers" in res["note"]
    assert "story_viewers" in fake.names()

