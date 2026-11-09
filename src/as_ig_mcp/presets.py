"""Caption, hashtag, first-comment and DM-reply presets in ``state.db``.

Preset content is the owner's own text. It is never written to the audit
journal; the journal records write attempts, not stored templates.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import sqlite3

from . import state

PRESET_KINDS = ("caption", "hashtags", "first_comment", "dm_reply")


class PresetError(ValueError):
    """Raised when a preset request is missing a required field."""


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch).isoformat()


def _record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "name": row["name"],
        "kind": row["kind"],
        "content": row["content"],
        "updated_at": _iso(row["updated_at"]),
        "updated_epoch": row["updated_at"],
    }


class PresetStore:
    """CRUD over the ``presets`` table. No new file, no new dependency."""

    def __init__(
        self,
        path: str | Path | None = None,
        clock: Any = time.time,
    ) -> None:
        self._path = Path(path) if path is not None else state.db_path()
        self._clock = clock

    @contextmanager
    def _open(self) -> Iterator[sqlite3.Connection]:
        connection = state.connect(self._path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def set(
        self,
        name: Any,
        kind: Any = "caption",
        content: Any = None,
    ) -> dict[str, Any]:
        """Store or replace one preset, keyed by name."""
        if name in (None, "") or not str(name).strip():
            raise PresetError("name is required to save a preset")
        preset_kind = str(kind or "caption").strip().lower()
        if preset_kind not in PRESET_KINDS:
            raise PresetError(
                f"unknown kind: {preset_kind!r}; valid kinds: {', '.join(PRESET_KINDS)}"
            )
        if content is None:
            raise PresetError("content is required to save a preset")
        key = str(name).strip()
        updated_at = float(self._clock())
        with self._open() as connection:
            connection.execute(
                """
                INSERT INTO presets (name, kind, content, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    kind = excluded.kind,
                    content = excluded.content,
                    updated_at = excluded.updated_at
                """,
                (key, preset_kind, str(content), updated_at),
            )
        return self.get(key) or {}

    def get(self, name: Any) -> dict[str, Any] | None:
        if name in (None, ""):
            return None
        with self._open() as connection:
            row = connection.execute(
                "SELECT * FROM presets WHERE name = ?", (str(name).strip(),)
            ).fetchone()
        return _record(row) if row is not None else None

    def list(self) -> list[dict[str, Any]]:
        with self._open() as connection:
            rows = connection.execute(
                "SELECT * FROM presets ORDER BY kind ASC, name ASC"
            ).fetchall()
        return [_record(row) for row in rows]

    def delete(self, name: Any) -> bool:
        """Remove one preset. Returns True when a row was removed."""
        if name in (None, ""):
            return False
        with self._open() as connection:
            cursor = connection.execute(
                "DELETE FROM presets WHERE name = ?", (str(name).strip(),)
            )
            return max(cursor.rowcount, 0) > 0
