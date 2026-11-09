"""Realtime events storage: atomic JSON lines and tail with cursor and timeout."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from . import state

_LOCK = threading.Lock()
_CONDITION = threading.Condition(_LOCK)


def append(event: dict[str, Any]) -> None:
    """Append one JSON object per line to events.jsonl, appended atomically."""
    target = state.events_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
    data = line.encode("utf-8")
    with _CONDITION:
        with open(target, "ab") as handle:
            handle.write(data)
            handle.flush()
        _CONDITION.notify_all()


def count() -> int:
    """Return how many events are in the file."""
    target = state.events_path()
    with _LOCK:
        if not target.exists():
            return 0
        with open(target, "rb") as handle:
            return sum(1 for line in handle if line.strip())


def tail(
    offset: int = 0,
    timeout_s: float = 0.0,
    kinds: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return the events after offset.

    With timeout_s > 0, wait on a threading.Condition until a new event
    arrives or the timeout expires.
    """
    offset = max(int(offset or 0), 0)
    timeout_s = max(float(timeout_s or 0.0), 0.0)
    target = state.events_path()
    start_time = time.time()

    def _read_slice() -> tuple[int, list[dict[str, Any]]]:
        if not target.exists():
            return 0, []
        total = 0
        items: list[dict[str, Any]] = []
        with open(target, "r", encoding="utf-8", errors="replace") as handle:
            for idx, line in enumerate(handle):
                text = line.strip()
                if not text:
                    continue
                total += 1
                if idx >= offset:
                    try:
                        ev = json.loads(text)
                        if isinstance(ev, dict):
                            if kinds is None or ev.get("event") in kinds:
                                items.append(ev)
                    except json.JSONDecodeError:
                        continue
        return total, items

    with _CONDITION:
        while True:
            total_count, events = _read_slice()
            if total_count > offset or timeout_s <= 0.0:
                return events

            elapsed = time.time() - start_time
            remaining = timeout_s - elapsed
            if remaining <= 0.0:
                return events

            _CONDITION.wait(timeout=remaining)
