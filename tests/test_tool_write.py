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
