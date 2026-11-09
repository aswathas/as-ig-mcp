"""The local publish queue: pending items, the runner and recurrence.

An item is approved by the account owner once, when it is queued. The five
minute runner then publishes the already-approved item. The state change from
``pending`` to ``publishing`` is the lock, so two ticks cannot publish the same
item. An item left in ``publishing`` is reported as possibly published and is
never retried automatically.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator

import sqlite3

from . import client, state, writes

QUEUE_KINDS = ("photo", "video", "reel", "carousel", "album", "story")
RECURRENCES = ("none", "daily", "weekly", "monthly")
STATES = ("pending", "publishing", "done", "cancelled")

#: media kind -> (mapping feature, the instagrapi argument that carries the file)
PUBLISH_FEATURES: dict[str, tuple[str, str]] = {
    "photo": ("publish_photo", "path"),
    "video": ("publish_video", "path"),
    "reel": ("publish_reel", "path"),
    "carousel": ("publish_album", "paths"),
    "album": ("publish_album", "paths"),
    "story": ("publish_story", "path"),
}

TASK_NAME = "AS-IG-MCP queue"
TASK_INTERVAL_MINUTES = 5


class QueueError(ValueError):
    """Raised when a queue request cannot be accepted as given."""


def _connection(path: str | Path | None = None) -> Any:
    target = Path(path) if path is not None else state.db_path()
    return state.connect(target)


@contextmanager
def _open(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = _connection(path)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).isoformat()


def parse_when(value: Any) -> datetime:
    """Parse an ISO datetime, or accept a datetime unchanged."""
    if isinstance(value, datetime):
        return value
    if value in (None, ""):
        raise QueueError("a due time is required; pass an ISO datetime")
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        raise QueueError(f"not an ISO datetime: {value!r}") from None


def normalize_kind(kind: Any) -> str:
    name = str(kind or "photo").strip().lower()
    if name not in PUBLISH_FEATURES:
        raise QueueError(
            f"unknown kind: {name!r}; valid kinds: {', '.join(QUEUE_KINDS)}"
        )
    return name


def normalize_recurrence(recurrence: Any) -> str:
    name = str(recurrence or "none").strip().lower()
    if name not in RECURRENCES:
        raise QueueError(
            f"unknown recurrence: {name!r}; valid: {', '.join(RECURRENCES)}"
        )
    return name


def next_occurrence(moment: datetime, recurrence: str) -> datetime | None:
    """The moment after ``moment`` for a recurrence, or ``None`` for one-off."""
    if recurrence == "daily":
        return moment + timedelta(days=1)
    if recurrence == "weekly":
        return moment + timedelta(days=7)
    if recurrence == "monthly":
        year = moment.year + (moment.month // 12)
        month = moment.month % 12 + 1
        day = min(moment.day, calendar.monthrange(year, month)[1])
        return moment.replace(year=year, month=month, day=day)
    return None


def default_key(
    kind: str,
    media_path: Any,
    caption: Any,
    when_iso: Any,
    recurrence: str,
) -> str:
    """A stable idempotency key for one queued post."""
    payload = json.dumps(
        [kind, str(media_path or ""), str(caption or ""), str(when_iso), recurrence],
        separators=(",", ":"),
    )
    return "queue-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _summary(payload: dict[str, Any]) -> str:
    caption = payload.get("caption")
    if caption:
        text = " ".join(str(caption).split())
        return text[:80] + ("\u2026" if len(text) > 80 else "")
    path = payload.get("media_path")
    return Path(str(path)).name if path else "(no media)"


def _publish_args(payload: dict[str, Any]) -> dict[str, Any]:
    kind = payload.get("kind", "photo")
    feature, argument = PUBLISH_FEATURES[kind]
    media_path = payload.get("media_path")
    args: dict[str, Any] = (
        {argument: [media_path]} if argument == "paths" else {argument: media_path}
    )
    caption = payload.get("caption")
    if caption not in (None, ""):
        args["caption"] = caption
    return args


def _item(row: sqlite3.Row) -> dict[str, Any]:
    try:
        payload = json.loads(row["payload"] or "{}")
    except (TypeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    state_name = row["state"]
    item = {
        "id": row["id"],
        "kind": payload.get("kind", "photo"),
        "summary": _summary(payload),
        "caption": payload.get("caption"),
        "media_path": payload.get("media_path"),
        "recurrence": payload.get("recurrence", "none"),
        "scheduled_at": row["scheduled_at"],
        "due": _iso(row["scheduled_at"]) if row["scheduled_at"] is not None else None,
        "state": state_name,
        "idempotency_key": row["idempotency_key"],
        "created_at": row["created_at"],
    }
    if state_name == "publishing":
        item["possibly_published"] = True
        item["note"] = "possibly published - check before retrying"
    return item


class Queue:
    """The queue table in ``state.db``. Safe between processes."""

    def __init__(
        self,
        path: str | Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._path = Path(path) if path is not None else state.db_path()
        self._clock = clock

    def find_by_key(self, idempotency_key: str) -> dict[str, Any] | None:
        connection = _connection(self._path)
        try:
            row = connection.execute(
                "SELECT * FROM queue WHERE idempotency_key = ? "
                "ORDER BY created_at ASC LIMIT 1",
                (idempotency_key,),
            ).fetchone()
        finally:
            connection.close()
        return _item(row) if row is not None else None

    def get(self, item_id: str) -> dict[str, Any] | None:
        connection = _connection(self._path)
        try:
            row = connection.execute(
                "SELECT * FROM queue WHERE id = ?", (str(item_id),)
            ).fetchone()
        finally:
            connection.close()
        return _item(row) if row is not None else None

    def list_items(self, kind: str | None = None) -> list[dict[str, Any]]:
        target = None
        if kind not in (None, ""):
            target = normalize_kind(kind)
        connection = _connection(self._path)
        try:
            rows = connection.execute(
                "SELECT * FROM queue ORDER BY scheduled_at ASC, created_at ASC"
            ).fetchall()
        finally:
            connection.close()
        items = [_item(row) for row in rows]
        if target is not None:
            items = [item for item in items if item["kind"] == target]
        return items

    def schedule_item(
        self,
        kind: Any = "photo",
        when: Any = None,
        media_path: Any = None,
        caption: Any = None,
        recurrence: Any = "none",
        idempotency_key: str | None = None,
        dialog: Callable[[str], bool | None] | None = None,
    ) -> dict[str, Any]:
        """Queue a post after the owner approves it. Never publishes it here."""
        media_kind = normalize_kind(kind)
        repeat = normalize_recurrence(recurrence)
        moment = parse_when(when)
        if media_path in (None, ""):
            raise QueueError("media_path is required to queue a post")

        key = idempotency_key or default_key(
            media_kind, media_path, caption, moment.isoformat(), repeat
        )
        existing = self.find_by_key(key)
        if existing is not None:
            return {
                "ok": True,
                "already_exists": True,
                "item": existing,
                "message": "an item with this idempotency key is already queued",
            }

        feature, _argument = PUBLISH_FEATURES[media_kind]
        gate = writes.perform_write(
            feature,
            {"path": media_path, "caption": caption},
            idempotency_key=key,
            dialog=dialog,
            execute=False,
        )
        if not gate.get("ok"):
            return gate

        item_id = uuid.uuid4().hex
        payload = {
            "kind": media_kind,
            "media_path": str(media_path),
            "caption": caption,
            "recurrence": repeat,
        }
        created_at = self._clock()
        with _open(self._path) as connection:
            connection.execute(
                "INSERT INTO queue (id, payload, scheduled_at, state, idempotency_key, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item_id,
                    json.dumps(payload, ensure_ascii=False),
                    moment.timestamp(),
                    "pending",
                    key,
                    created_at,
                ),
            )
        return {
            "ok": True,
            "approved": True,
            "item": self.get(item_id),
        }

    def native_schedule(
        self,
        kind: Any = "photo",
        schedule_at: Any = None,
        media_path: Any = None,
        caption: Any = None,
        idempotency_key: str | None = None,
        dialog: Callable[[str], bool | None] | None = None,
    ) -> dict[str, Any]:
        """Hand the post to Instagram's own scheduler, carrying ``schedule_at``."""
        media_kind = normalize_kind(kind)
        moment = parse_when(schedule_at)
        if media_path in (None, ""):
            raise QueueError("media_path is required to schedule a post natively")

        feature, argument = PUBLISH_FEATURES[media_kind]
        args = _publish_args(
            {"kind": media_kind, "media_path": media_path, "caption": caption}
        )
        args["schedule_at"] = moment
        key = idempotency_key or default_key(
            media_kind, media_path, caption, moment.isoformat(), "native"
        )
        return writes.perform_write(
            feature, args, idempotency_key=key, dialog=dialog
        )

    def cancel_item(self, item_id: Any) -> dict[str, Any]:
        """Cancel a pending item. This changes our queue only, so no approval."""
        if item_id in (None, ""):
            raise QueueError("item_id is required to cancel an item")
        target = str(item_id)
        with _open(self._path) as connection:
            cursor = connection.execute(
                "UPDATE queue SET state = 'cancelled' WHERE id = ? AND state = 'pending'",
                (target,),
            )
            changed = max(cursor.rowcount, 0)
        if changed:
            return {"ok": True, "cancelled": target, "item": self.get(target)}
        item = self.get(target)
        if item is None:
            return {"ok": False, "error": f"no queue item with id {target!r}"}
        return {
            "ok": False,
            "item": item,
            "error": f"item is {item['state']}; only a pending item can be cancelled",
        }

    def _claim(self, item_id: str) -> bool:
        connection = _connection(self._path)
        try:
            with connection:
                cursor = connection.execute(
                    "UPDATE queue SET state = 'publishing' "
                    "WHERE id = ? AND state = 'pending'",
                    (item_id,),
                )
                return max(cursor.rowcount, 0) == 1
        finally:
            connection.close()

    def _mark_done(self, item: dict[str, Any]) -> None:
        payload = {
            "kind": item["kind"],
            "media_path": item["media_path"],
            "caption": item["caption"],
            "recurrence": item["recurrence"],
        }
        with _open(self._path) as connection:
            connection.execute(
                "UPDATE queue SET state = 'done' WHERE id = ?", (item["id"],)
            )
            if item["recurrence"] != "none" and item["scheduled_at"] is not None:
                moment = next_occurrence(
                    datetime.fromtimestamp(item["scheduled_at"]), item["recurrence"]
                )
                if moment is not None:
                    key = f"{item['idempotency_key']}#{int(moment.timestamp())}"
                    existing = connection.execute(
                        "SELECT 1 FROM queue WHERE idempotency_key = ?", (key,)
                    ).fetchone()
                    if existing is None:
                        connection.execute(
                            "INSERT INTO queue "
                            "(id, payload, scheduled_at, state, idempotency_key, created_at) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                uuid.uuid4().hex,
                                json.dumps(payload, ensure_ascii=False),
                                moment.timestamp(),
                                "pending",
                                key,
                                self._clock(),
                            ),
                        )

    def _possibly_published(self) -> list[dict[str, Any]]:
        connection = _connection(self._path)
        try:
            rows = connection.execute(
                "SELECT * FROM queue WHERE state = 'publishing' "
                "ORDER BY scheduled_at ASC"
            ).fetchall()
        finally:
            connection.close()
        return [_item(row) for row in rows]

    def due_items(self, now: float | None = None) -> list[dict[str, Any]]:
        moment = self._clock() if now is None else float(now)
        connection = _connection(self._path)
        try:
            rows = connection.execute(
                "SELECT * FROM queue WHERE state = 'pending' AND scheduled_at <= ? "
                "ORDER BY scheduled_at ASC",
                (moment,),
            ).fetchall()
        finally:
            connection.close()
        return [_item(row) for row in rows]

    def publish_due(
        self,
        now: float | None = None,
        opener: Callable[[], tuple[Any, dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Publish every pending item whose time has come. Never twice.

        The ``pending`` to ``publishing`` transition is the lock: a second tick
        sees zero rows changed and skips the item. A failure after the claim
        leaves the item in ``publishing`` so it is reported and never retried.
        """
        moment = self._clock() if now is None else float(now)
        open_client = opener or client.open_client
        published: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        overdue = 0

        for candidate in self.due_items(moment):
            if not self._claim(candidate["id"]):
                continue
            item = self.get(candidate["id"])
            if item is None:  # pragma: no cover - the row was just claimed
                continue
            if item["scheduled_at"] is not None and item["scheduled_at"] < moment:
                overdue += 1
            feature, _argument = PUBLISH_FEATURES[item["kind"]]
            try:
                instagram, _settings = open_client()
                result = client.call_write(instagram, feature, **_publish_args(
                    {
                        "kind": item["kind"],
                        "media_path": item["media_path"],
                        "caption": item["caption"],
                    }
                ))
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                errors.append(
                    {
                        "id": item["id"],
                        "error": message,
                        "note": "possibly published - check before retrying",
                    }
                )
                continue
            self._mark_done(item)
            published.append(
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "summary": item["summary"],
                    "result": _plain(result),
                }
            )

        possibly = self._possibly_published()
        report: dict[str, Any] = {
            "ok": True,
            "published": published,
            "possibly_published": possibly,
            "errors": errors,
            "overdue": overdue,
        }
        if not published and not possibly and not errors:
            report["message"] = "nothing due"
        return report


def _plain(value: Any) -> Any:
    from .serialize import plain

    return plain(value)


def build_install_task_command(
    python_exe: str | None = None,
    task_name: str = TASK_NAME,
    interval_minutes: int = TASK_INTERVAL_MINUTES,
) -> list[str]:
    """The exact ``schtasks`` command; building it never runs anything."""
    executable = python_exe or sys.executable
    command = f'"{executable}" -m as_ig_mcp queue tick'
    return [
        "schtasks",
        "/create",
        "/tn",
        task_name,
        "/sc",
        "minute",
        "/mo",
        str(interval_minutes),
        "/tr",
        command,
    ]


def install_task(
    command: list[str] | None = None,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Register the Windows Scheduled Task and report exactly what happened."""
    argv = list(command) if command is not None else build_install_task_command()
    printable = subprocess.list2cmdline(argv)
    execute = runner or subprocess.run
    try:
        completed = execute(argv, capture_output=True, text=True)
    except Exception as exc:
        return {
            "ok": False,
            "command": printable,
            "error": f"{type(exc).__name__}: {exc}",
        }
    output = (getattr(completed, "stdout", "") or "").strip()
    error = (getattr(completed, "stderr", "") or "").strip()
    code = getattr(completed, "returncode", 1)
    result: dict[str, Any] = {
        "ok": code == 0,
        "command": printable,
        "returncode": code,
    }
    if output:
        result["stdout"] = output
    if error:
        result["stderr"] = error
    if code != 0:
        result["error"] = (
            "the scheduled task could not be created; it may need a different "
            "account or elevation. Run the command above in an elevated prompt."
        )
    return result
