"""Offline tests for the caption and hashtag preset store."""

from __future__ import annotations

import pytest

from as_ig_mcp import state, tools_preset
from as_ig_mcp.presets import PresetError, PresetStore


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_set_get_list_and_delete(appdata):
    saved = tools_preset.ig_preset(
        action="set",
        name="launch",
        kind="caption",
        content="Shipping today.",
    )
    assert saved["ok"] is True
    assert saved["preset"]["name"] == "launch"
    assert saved["preset"]["kind"] == "caption"
    assert saved["preset"]["content"] == "Shipping today."
    assert saved["preset"]["updated_at"] is not None

    fetched = tools_preset.ig_preset(action="get", name="launch")
    assert fetched["ok"] is True
    assert fetched["preset"]["content"] == "Shipping today."

    listed = tools_preset.ig_preset(action="list")
    assert listed["ok"] is True
    assert [preset["name"] for preset in listed["presets"]] == ["launch"]

    removed = tools_preset.ig_preset(action="delete", name="launch")
    assert removed["ok"] is True
    assert removed["existed"] is True

    assert tools_preset.ig_preset(action="get", name="launch")["ok"] is False
    assert tools_preset.ig_preset(action="list")["presets"] == []


def test_a_preset_survives_a_new_connection_to_the_same_database(tmp_path):
    path = tmp_path / "state.db"
    first = PresetStore(path)
    first.set("hashtags", "hashtags", "#one #two #three")

    second = PresetStore(path)
    preset = second.get("hashtags")

    assert preset is not None
    assert preset["kind"] == "hashtags"
    assert preset["content"] == "#one #two #three"


def test_updating_a_preset_replaces_it_rather_than_duplicating_it(tmp_path):
    store = PresetStore(tmp_path / "state.db")
    store.set("reply", "dm_reply", "first draft")
    store.set("reply", "dm_reply", "second draft")

    presets = store.list()
    assert len(presets) == 1
    assert presets[0]["name"] == "reply"
    assert presets[0]["content"] == "second draft"


def test_all_four_kinds_are_accepted(appdata):
    for kind in ("caption", "hashtags", "first_comment", "dm_reply"):
        result = tools_preset.ig_preset(
            action="set", name=kind, kind=kind, content=f"text for {kind}"
        )
        assert result["ok"] is True, result
        assert result["preset"]["kind"] == kind


def test_an_unknown_kind_is_refused_and_nothing_is_stored(appdata):
    result = tools_preset.ig_preset(
        action="set", name="bad", kind="poem", content="verse"
    )

    assert result["ok"] is False
    assert "unknown kind" in result["error"]
    assert tools_preset.ig_preset(action="list")["presets"] == []


def test_a_missing_name_or_content_is_refused(appdata):
    assert tools_preset.ig_preset(action="set", kind="caption", content="x")["ok"] is False
    assert tools_preset.ig_preset(action="set", name="x", kind="caption")["ok"] is False


def test_preset_content_is_never_written_to_the_audit_journal(appdata):
    secret_text = "this preset text must not reach the audit journal"
    PresetStore().set("private", "caption", secret_text)

    journal = state.audit_path()
    assert not journal.exists() or secret_text not in journal.read_text(encoding="utf-8")


def test_the_presets_table_lives_in_the_shared_state_database(appdata):
    path = state.init_db()
    PresetStore(path).set("one", "caption", "hello")

    connection = state.connect(path)
    try:
        names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        row = connection.execute(
            "SELECT content FROM presets WHERE name = ?", ("one",)
        ).fetchone()
    finally:
        connection.close()

    assert "presets" in names
    assert row is not None and row["content"] == "hello"


def test_a_missing_preset_is_none(tmp_path):
    assert PresetStore(tmp_path / "state.db").get("absent") is None


def test_set_requires_a_kind_within_the_supported_set(tmp_path):
    with pytest.raises(PresetError):
        PresetStore(tmp_path / "state.db").set("x", "note", "y")
