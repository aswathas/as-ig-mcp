"""Append-only audit journal of every write attempt.

One JSON object per line in ``%APPDATA%\as-ig-mcp\audit.jsonl``. The journal is
the record of every attempt, not only the ones that went through, so a denied
or failed write is written too. It never holds a cookie, a password or an
approval code.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from . import state

_LOCK = threading.Lock()

EXECUTING = "executing"
COMPLETED = "completed"


def _path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else state.audit_path()


def append_entry(entry: dict[str, Any]) -> None:
    """Append one JSON line to the journal with a single atomic write."""
    target = _path()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    data = line.encode("utf-8")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    with _LOCK:
        handle = os.open(str(target), flags)
        try:
            os.write(handle, data)
            os.fsync(handle)
        finally:
            os.close(handle)


def read_entries(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Read the journal, skipping blank or malformed lines."""
    try:
        raw = _path(path).read_bytes()
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def has_completed(idempotency_key: str | None) -> bool:
    """True when an approved, completed entry carries this idempotency key."""
    if not idempotency_key:
        return False
    for entry in reversed(read_entries()):
        if entry.get("idempotency_key") != idempotency_key:
            continue
        if entry.get("state") != "approved":
            continue
        if entry.get("result_summary") != EXECUTING:
            return True
    return False
