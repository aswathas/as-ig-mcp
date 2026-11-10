"""Offline tests for the ig_write tool: kinds, dialog wiring and annotations."""

from __future__ import annotations

import asyncio
import inspect
import json

import pytest

from as_ig_mcp import client, tools_write, writes
from as_ig_mcp.server import mcp


class FakeClient:
    def __init__(self):
        self.calls: list[dict] = []

    def direct_send(self, **kwargs):
        self.calls.append(kwargs)
        return {"message_id": "m1"}

    def media_delete(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def highlight_delete(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def delete_note(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def clip_upload(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def photo_upload_to_story(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def photo_upload_to_story_with_music(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def igtv_upload(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def photo_upload_to_cutout_sticker(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def quicksnap_send(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def comment_pin(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def media_save(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def mute_stories_from_follow(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def highlight_edit(self, **kwargs):
        self.calls.append(kwargs)
        return True

    def close_friend_remove(self, **kwargs):
        self.calls.append(kwargs)
        return True


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def _use(monkeypatch, fake):
    monkeypatch.setattr(client, "open_client", lambda: (fake, {}))


def test_unknown_kind_returns_an_error_and_touches_nothing(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    dialogs: list[str] = []
    monkeypatch.setattr(writes, "show_approval", lambda preview: dialogs.append(preview) or True)

    result = tools_write.ig_write(kind="not-a-real-kind")

    assert result["ok"] is False
    assert "valid kinds" in result["error"]
    assert "send_message" in result["error"]
    assert dialogs == []
    assert fake.calls == []


def test_the_dialog_is_consulted_exactly_once_per_write(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    dialogs: list[str] = []
    monkeypatch.setattr(writes, "show_approval", lambda preview: dialogs.append(preview) or True)

    result = tools_write.ig_write(
        kind="send_message",
        username="pravss.23",
        text="Solu da",
    )

    assert result["ok"] is True
    assert len(dialogs) == 1
    assert fake.calls == [{"username": "pravss.23", "text": "Solu da"}]


def test_the_preview_reaches_the_dialog(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    dialogs: list[str] = []
    monkeypatch.setattr(writes, "show_approval", lambda preview: dialogs.append(preview) or False)

    tools_write.ig_write(
        kind="send_message",
        username="pravss.23",
        text="Solu da",
    )

    assert dialogs == ["DM to @pravss.23: \"Solu da\""]


def test_confirm_is_not_a_parameter():
    assert "confirm" not in inspect.signature(tools_write.ig_write).parameters


def test_a_stray_confirm_key_is_ignored(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(
        kind="send_message",
        confirm="123456",
        username="pravss.23",
        text="Solu da",
    )

    assert result["ok"] is True
    assert fake.calls == [{"username": "pravss.23", "text": "Solu da"}]


def test_the_mcp_wire_path_accepts_the_args_envelope(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = asyncio.run(
        mcp.call_tool(
            "ig_write",
            {
                "kind": "send_message",
                "args": json.dumps({"username": "pravss.23", "text": "Solu da"}),
            },
        )
    )

    assert result.is_error is False
    assert fake.calls == [{"username": "pravss.23", "text": "Solu da"}]


def test_ig_write_declares_the_standard_annotations_and_metadata():
    tools = asyncio.run(mcp.list_tools())
    tool = next(item for item in tools if item.name == "ig_write")

    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.destructive_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is True
    assert tool.meta["anthropic/requiresUserInteraction"] is True
    assert "owner approves by clicking" in tool.description
    assert "cannot approve" in tool.description


def test_delete_media_calls_media_delete_with_media_id(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="delete_media", media_id="12345_67890")

    assert result["ok"] is True
    assert fake.calls == [{"media_id": "12345_67890"}]


def test_delete_highlight_calls_highlight_delete_with_highlight_pk(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="delete_highlight", highlight_id="17895485201104054")

    assert result["ok"] is True
    assert fake.calls == [{"highlight_pk": "17895485201104054"}]


def test_publish_reel_calls_clip_upload(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="publish_reel", path="video.mp4", caption="cool reel")

    assert result["ok"] is True
    assert fake.calls == [{"path": "video.mp4", "caption": "cool reel"}]


def test_publish_story_calls_photo_upload_to_story(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="publish_story", path="story.jpg", caption="my story")

    assert result["ok"] is True
    assert fake.calls == [{"path": "story.jpg", "caption": "my story"}]


def test_publish_story_music_calls_photo_upload_to_story_with_music(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(
        kind="publish_story_music",
        path="story.jpg",
        caption="my story",
        track={"audio_cluster_id": "123"},
    )

    assert result["ok"] is True
    assert fake.calls == [
        {"path": "story.jpg", "caption": "my story", "track": {"audio_cluster_id": "123"}}
    ]


def test_comment_pin_calls_comment_pin(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="comment_pin", media_id="123", comment_pk="456")

    assert result["ok"] is True
    assert fake.calls == [{"media_id": "123", "comment_pk": "456"}]


def test_save_media_calls_media_save(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="save_media", media_id="12345")

    assert result["ok"] is True
    assert fake.calls == [{"media_id": "12345"}]


def test_mute_stories_calls_mute_stories_from_follow(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="mute_stories", user_id="999")

    assert result["ok"] is True
    assert fake.calls == [{"user_id": "999"}]


def test_highlight_edit_calls_highlight_edit(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="highlight_edit", highlight_pk="111", title="New Title")

    assert result["ok"] is True
    assert fake.calls == [{"highlight_pk": "111", "title": "New Title"}]


def test_close_friend_remove_calls_close_friend_remove(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="close_friend_remove", user_id="999")

    assert result["ok"] is True
    assert fake.calls == [{"user_id": "999"}]


def test_publish_igtv_calls_igtv_upload(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="publish_igtv", path="video.mp4", caption="cool igtv")

    assert result["ok"] is True
    assert fake.calls == [{"path": "video.mp4", "caption": "cool igtv"}]


def test_cutout_sticker_calls_photo_upload_to_cutout_sticker(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="cutout_sticker", path="sticker.png")

    assert result["ok"] is True
    assert fake.calls == [{"path": "sticker.png"}]


def test_quicksnap_calls_quicksnap_send(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="quicksnap", path="snap.jpg", user_ids=["12345"])

    assert result["ok"] is True
    assert fake.calls == [{"path": "snap.jpg", "user_ids": ["12345"]}]


def test_note_delete_calls_delete_note_with_note_id(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)

    result = tools_write.ig_write(kind="note_delete", note_id="123456789")

    assert result["ok"] is True
    assert fake.calls == [{"note_id": "123456789"}]

