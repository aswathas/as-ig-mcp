"""Offline tests for the local publish queue and its runner."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from as_ig_mcp import state, writes
from as_ig_mcp.queue import Queue, QueueError, next_occurrence


class FakeClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    def photo_upload(self, **kwargs):
        self.calls.append(("photo_upload", kwargs))
        if self.error is not None:
            raise self.error
        return {"pk": "published-1"}

    def video_upload(self, **kwargs):
        self.calls.append(("video_upload", kwargs))
        return {"pk": "published-video"}


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def _queue(tmp_path) -> Queue:
    return Queue(tmp_path / "state.db")


def _approve(preview):
    return True


def _epoch(text: str) -> float:
    return datetime.fromisoformat(text).timestamp()


def _set_state(path, item_id: str, state_name: str) -> None:
    connection = state.connect(path)
    try:
        with connection:
            connection.execute(
                "UPDATE queue SET state = ? WHERE id = ?", (state_name, item_id)
            )
    finally:
        connection.close()


def test_a_queued_item_is_pending_with_the_right_time_and_key(appdata, tmp_path):
    q = _queue(tmp_path)
    when = "2030-01-02T03:04:05"

    result = q.schedule_item(
        kind="photo",
        when=when,
        media_path="C:/media/launch.jpg",
        caption="launch day",
        idempotency_key="key-launch",
        dialog=_approve,
    )

    assert result["ok"] is True
    item = result["item"]
    assert item["state"] == "pending"
    assert item["idempotency_key"] == "key-launch"
    assert item["scheduled_at"] == pytest.approx(_epoch(when))
    assert item["due"] == datetime.fromisoformat(when).isoformat()
    assert item["kind"] == "photo"
    assert item["summary"] == "launch day"


def test_cancelling_a_pending_item_works_and_needs_no_approval(
    appdata, tmp_path, monkeypatch
):
    q = _queue(tmp_path)
    created = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/a.jpg",
        caption="a",
        dialog=_approve,
    )
    dialogs: list[str] = []

    def refuse(preview):  # a cancel must never reach a dialog
        dialogs.append(preview)
        return False

    monkeypatch.setattr(writes, "show_approval", refuse)

    result = q.cancel_item(created["item"]["id"])

    assert result["ok"] is True
    assert result["item"]["state"] == "cancelled"
    assert dialogs == []


def test_cancelling_a_done_item_is_refused(appdata, tmp_path):
    q = _queue(tmp_path)
    created = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/a.jpg",
        caption="a",
        dialog=_approve,
    )
    _set_state(tmp_path / "state.db", created["item"]["id"], "done")

    result = q.cancel_item(created["item"]["id"])

    assert result["ok"] is False
    assert "only a pending item can be cancelled" in result["error"]


def test_the_tick_publishes_a_due_item_once_and_leaves_a_future_item_alone(appdata, tmp_path):
    q = _queue(tmp_path)
    past = q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/due.jpg",
        caption="due now",
        dialog=_approve,
    )
    future = q.schedule_item(
        kind="photo",
        when="2030-01-01T00:00:00",
        media_path="C:/media/later.jpg",
        caption="not yet",
        dialog=_approve,
    )
    fake = FakeClient()

    report = q.publish_due(opener=lambda: (fake, {}))

    assert len(report["published"]) == 1
    assert report["published"][0]["id"] == past["item"]["id"]
    assert report["overdue"] == 1
    assert fake.calls == [
        ("photo_upload", {"path": "C:/media/due.jpg", "caption": "due now"})
    ]

    items = {item["id"]: item for item in q.list_items()}
    assert items[past["item"]["id"]]["state"] == "done"
    assert items[future["item"]["id"]]["state"] == "pending"


def test_two_ticks_in_a_row_publish_once(appdata, tmp_path):
    q = _queue(tmp_path)
    q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/once.jpg",
        caption="once",
        dialog=_approve,
    )
    fake = FakeClient()

    first = q.publish_due(opener=lambda: (fake, {}))
    second = q.publish_due(opener=lambda: (fake, {}))

    assert len(first["published"]) == 1
    assert second["published"] == []
    assert second["message"] == "nothing due"
    assert len(fake.calls) == 1


def test_the_claim_is_the_lock_for_two_ticking_processes(appdata, tmp_path):
    q = _queue(tmp_path)
    created = q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/lock.jpg",
        caption="lock",
        dialog=_approve,
    )
    item_id = created["item"]["id"]

    assert q._claim(item_id) is True
    assert q._claim(item_id) is False
    assert q.get(item_id)["state"] == "publishing"


def test_an_item_left_publishing_is_reported_and_never_published_again(appdata, tmp_path):
    q = _queue(tmp_path)
    created = q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/maybe.jpg",
        caption="maybe",
        dialog=_approve,
    )
    _set_state(tmp_path / "state.db", created["item"]["id"], "publishing")
    fake = FakeClient()

    report = q.publish_due(opener=lambda: (fake, {}))

    assert report["published"] == []
    assert [item["id"] for item in report["possibly_published"]] == [
        created["item"]["id"]
    ]
    assert "possibly published" in report["possibly_published"][0]["note"]
    assert fake.calls == []
    assert q.get(created["item"]["id"])["state"] == "publishing"


def test_a_failed_publish_stays_publishing_and_is_not_retried(appdata, tmp_path):
    q = _queue(tmp_path)
    created = q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/boom.jpg",
        caption="boom",
        dialog=_approve,
    )
    fake = FakeClient(error=RuntimeError("the response did not parse"))

    first = q.publish_due(opener=lambda: (fake, {}))
    second = q.publish_due(opener=lambda: (fake, {}))

    assert first["published"] == []
    assert first["errors"][0]["id"] == created["item"]["id"]
    assert first["errors"][0]["note"] == "possibly published - check before retrying"
    assert len(first["possibly_published"]) == 1
    assert len(fake.calls) == 1
    assert second["published"] == []
    assert q.get(created["item"]["id"])["state"] == "publishing"


def test_a_repeated_idempotency_key_does_not_create_a_second_item(appdata, tmp_path):
    q = _queue(tmp_path)
    dialogs: list[str] = []

    def dialog(preview):
        dialogs.append(preview)
        return True

    first = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/same.jpg",
        caption="same",
        idempotency_key="same-key",
        dialog=dialog,
    )
    second = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/same.jpg",
        caption="same",
        idempotency_key="same-key",
        dialog=dialog,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert second["already_exists"] is True
    assert second["item"]["id"] == first["item"]["id"]
    assert len(q.list_items()) == 1
    assert len(dialogs) == 1


def test_queueing_goes_through_the_dialog_and_a_denial_leaves_no_item(
    appdata, tmp_path, monkeypatch
):
    q = _queue(tmp_path)
    seen: list[str] = []

    def stub_dialog(preview):
        seen.append(preview)
        return False

    monkeypatch.setattr(writes, "show_approval", stub_dialog)

    result = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/denied.jpg",
        caption="do not post this",
    )

    assert result["ok"] is False
    assert result["denied"] is True
    assert seen and "do not post this" in seen[0]
    assert q.list_items() == []


def test_the_dialog_is_required_to_create_an_item(appdata, tmp_path, monkeypatch):
    q = _queue(tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(
        writes, "show_approval", lambda preview: seen.append(preview) or True
    )

    result = q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/approved.jpg",
        caption="approved",
    )

    assert result["ok"] is True
    assert result["approved"] is True
    assert len(seen) == 1
    assert len(q.list_items()) == 1


def test_list_filters_by_kind_and_exposes_the_fields(appdata, tmp_path):
    q = _queue(tmp_path)
    q.schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/a.jpg",
        caption="a",
        dialog=_approve,
    )
    q.schedule_item(
        kind="reel",
        when="2030-02-02T03:04:05",
        media_path="C:/media/b.mp4",
        caption="b",
        dialog=_approve,
    )

    reels = q.list_items("reel")

    assert len(reels) == 1
    for field in ("id", "kind", "summary", "due", "state", "idempotency_key"):
        assert field in reels[0]
    assert reels[0]["kind"] == "reel"


def test_a_daily_recurrence_creates_the_next_item_after_publishing(appdata, tmp_path):
    q = _queue(tmp_path)
    q.schedule_item(
        kind="photo",
        when="2020-01-01T00:00:00",
        media_path="C:/media/daily.jpg",
        caption="daily",
        recurrence="daily",
        dialog=_approve,
    )
    fake = FakeClient()

    report = q.publish_due(opener=lambda: (fake, {}))
    items = q.list_items()

    assert len(report["published"]) == 1
    assert sorted(item["state"] for item in items) == ["done", "pending"]
    pending = next(item for item in items if item["state"] == "pending")
    assert pending["idempotency_key"].startswith(next(
        item["idempotency_key"] for item in items if item["state"] == "done"
    ))
    expected = next_occurrence(
        datetime.fromisoformat("2020-01-01T00:00:00"), "daily"
    )
    assert pending["scheduled_at"] == pytest.approx(expected.timestamp())


def test_next_occurrence_maths():
    moment = datetime(2026, 1, 31, 9, 30)

    assert next_occurrence(moment, "none") is None
    assert next_occurrence(moment, "daily") == datetime(2026, 2, 1, 9, 30)
    assert next_occurrence(moment, "weekly") == datetime(2026, 2, 7, 9, 30)
    assert next_occurrence(moment, "monthly") == datetime(2026, 2, 28, 9, 30)


def test_unknown_kind_and_recurrence_are_refused(appdata, tmp_path):
    q = _queue(tmp_path)

    with pytest.raises(QueueError, match="unknown kind"):
        q.schedule_item(
            kind="podcast", when="2030-01-01T00:00:00", media_path="x", dialog=_approve
        )

    with pytest.raises(QueueError, match="unknown recurrence"):
        q.schedule_item(
            kind="photo",
            when="2030-01-01T00:00:00",
            media_path="x",
            recurrence="hourly",
            dialog=_approve,
        )


def test_native_schedule_passes_schedule_at_through_the_dialog(appdata, tmp_path, monkeypatch):
    q = _queue(tmp_path)
    seen: list[str] = []
    monkeypatch.setattr(
        writes, "show_approval", lambda preview: seen.append(preview) or True
    )
    fake = FakeClient()
    monkeypatch.setattr("as_ig_mcp.client.open_client", lambda: (fake, {}))

    result = q.native_schedule(
        kind="photo",
        schedule_at="2030-01-02T03:04:05",
        media_path="C:/media/native.jpg",
        caption="native",
    )

    assert result["ok"] is True
    assert seen
    name, kwargs = fake.calls[0]
    assert name == "photo_upload"
    assert kwargs["path"] == "C:/media/native.jpg"
    assert kwargs["caption"] == "native"
    assert kwargs["schedule_at"] == datetime.fromisoformat("2030-01-02T03:04:05")


def test_ig_write_schedule_queues_through_the_dialog(appdata, monkeypatch):
    from as_ig_mcp import tools_write

    seen: list[str] = []
    monkeypatch.setattr(
        writes, "show_approval", lambda preview: seen.append(preview) or True
    )

    result = tools_write.ig_write(
        kind="schedule",
        path="C:/media/from-write.jpg",
        caption="from ig_write",
        when="2030-01-02T03:04:05",
        media_kind="photo",
    )

    assert result["ok"] is True
    assert result["item"]["state"] == "pending"
    assert result["item"]["summary"] == "from ig_write"
    assert seen
    assert len(Queue().list_items()) == 1


def test_ig_write_native_schedule_calls_the_upload_with_schedule_at(appdata, monkeypatch):
    from as_ig_mcp import tools_write

    fake = FakeClient()
    monkeypatch.setattr(writes, "show_approval", lambda preview: True)
    monkeypatch.setattr("as_ig_mcp.client.open_client", lambda: (fake, {}))

    result = tools_write.ig_write(
        kind="native_schedule",
        path="C:/media/native-from-write.jpg",
        caption="native from ig_write",
        schedule_at="2030-01-02T03:04:05",
        media_kind="photo",
    )

    assert result["ok"] is True
    name, kwargs = fake.calls[0]
    assert name == "photo_upload"
    assert kwargs["schedule_at"] == datetime.fromisoformat("2030-01-02T03:04:05")


def test_ig_write_lists_both_scheduling_kinds():
    from as_ig_mcp import tools_write

    kinds = tools_write._all_kinds()
    assert "schedule" in kinds
    assert "native_schedule" in kinds
