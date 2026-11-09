"""ig_queue: list, schedule, cancel, recurring posts and native scheduling."""

from __future__ import annotations

from typing import Any

from .queue import (
    QUEUE_KINDS,
    RECURRENCES,
    Queue,
    QueueError,
)

ACTIONS = ("list", "schedule", "cancel", "native")


def ig_queue(
    action: str = "list",
    kind: str | None = None,
    when: str | None = None,
    text: str | None = None,
    media_path: str | None = None,
    caption: str | None = None,
    schedule_at: str | None = None,
    recurrence: str | None = None,
    item_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Read or change the local publish queue. Scheduling asks the owner first."""
    name = str(action or "list").strip().lower()
    queue = Queue()

    try:
        if name == "list":
            items = queue.list_items(kind)
            return {
                "ok": True,
                "items": items,
                "possibly_published": [
                    item["id"] for item in items if item["state"] == "publishing"
                ],
            }

        if name == "schedule":
            result = queue.schedule_item(
                kind=kind or "photo",
                when=when,
                media_path=media_path,
                caption=caption if caption is not None else text,
                recurrence=recurrence or "none",
                idempotency_key=idempotency_key,
            )
            result.setdefault("kinds", list(QUEUE_KINDS))
            return result

        if name == "cancel":
            return queue.cancel_item(item_id)

        if name == "native":
            result = queue.native_schedule(
                kind=kind or "photo",
                schedule_at=schedule_at if schedule_at not in (None, "") else when,
                media_path=media_path,
                caption=caption if caption is not None else text,
                idempotency_key=idempotency_key,
            )
            return result
    except QueueError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "kinds": list(QUEUE_KINDS),
            "recurrences": list(RECURRENCES),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": False,
        "error": f"unknown action: {name!r}; valid: {', '.join(ACTIONS)}",
        "actions": list(ACTIONS),
    }
