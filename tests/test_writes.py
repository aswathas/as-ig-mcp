"""Offline tests for the click-to-approve write gate and its audit journal."""

from __future__ import annotations

import pytest
from instagrapi.exceptions import ClientError

from as_ig_mcp import audit, client, state, writes


class FakeClient:
    def __init__(self, result=None, error=None):
        self.calls: list[dict] = []
        self.result = {"message_id": "m1"} if result is None else result
        self.error = error

    def direct_send(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def _use(monkeypatch, fake):
    monkeypatch.setattr(client, "open_client", lambda: (fake, {}))


def test_dialog_preview_mentions_the_target_and_the_text(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)
    seen: list[str] = []

    def dialog(preview):
        seen.append(preview)
        return False

    writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        dialog=dialog,
    )

    assert len(seen) == 1
    assert "pravss.23" in seen[0]
    assert "Solu da" in seen[0]


def test_no_means_no_instagram_call_and_one_denied_journal_line(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)

    result = writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        dialog=lambda preview: False,
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert fake.calls == []

    denied = [entry for entry in audit.read_entries() if entry["state"] == "denied"]
    assert len(denied) == 1


def test_no_desktop_is_distinct_from_no_and_journals_failed(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)

    result = writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        dialog=lambda preview: None,
    )

    assert result["ok"] is False
    assert "no interactive desktop" in result["error"]
    assert fake.calls == []

    failed = [entry for entry in audit.read_entries() if entry["state"] == "failed"]
    assert len(failed) == 1
    assert "no interactive desktop" in failed[0]["result_summary"]


def test_yes_calls_the_fake_client_exactly_once_and_journals_approved(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)

    result = writes.perform_write(
        "send_message",
        {"user_ids": ["123"], "text": "hello"},
        dialog=lambda preview: True,
    )

    assert result["ok"] is True
    assert fake.calls == [{"user_ids": ["123"], "text": "hello"}]

    entries = audit.read_entries()
    assert any(entry["state"] == "approved" for entry in entries)
    assert len([entry for entry in entries if entry["state"] == "approved"]) == 2


def test_a_repeated_idempotency_key_is_already_done_without_a_dialog_or_a_call(
    appdata, monkeypatch
):
    fake = FakeClient()
    _use(monkeypatch, fake)
    dialogs = []

    def dialog(preview):
        dialogs.append(preview)
        return True

    first = writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        idempotency_key="same-key",
        dialog=dialog,
    )
    second = writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        idempotency_key="same-key",
        dialog=dialog,
    )

    assert first["ok"] is True
    assert not first.get("already_done")
    assert second["ok"] is True
    assert second["already_done"] is True
    assert "Solu da" in second["preview"]
    assert len(dialogs) == 1
    assert len(fake.calls) == 1


def test_a_failing_write_journals_failed_and_is_not_retried(appdata, monkeypatch):
    fake = FakeClient(error=ClientError("the response did not parse"))
    _use(monkeypatch, fake)

    result = writes.perform_write(
        "send_message",
        {"username": "pravss.23", "text": "Solu da"},
        dialog=lambda preview: True,
    )

    assert result["ok"] is False
    assert "the response did not parse" in result["error"]
    assert len(fake.calls) == 1

    failed = [entry for entry in audit.read_entries() if entry["state"] == "failed"]
    assert len(failed) == 1
    assert "the response did not parse" in failed[0]["result_summary"]


def test_the_journal_never_contains_a_cookie_or_a_csrf_token(appdata, monkeypatch):
    fake = FakeClient()
    _use(monkeypatch, fake)

    writes.perform_write(
        "send_message",
        {
            "username": "pravss.23",
            "text": "hello",
            "sessionid": "super-secret-cookie",
            "csrftoken": "super-secret-csrf",
        },
        dialog=lambda preview: False,
    )

    journal = state.audit_path().read_text(encoding="utf-8").lower()
    assert "sessionid" not in journal
    assert "csrftoken" not in journal
