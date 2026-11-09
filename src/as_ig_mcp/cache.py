"""TTL cache in the shared SQLite state file, safe between processes."""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

import sqlite3

from . import state

DEFAULT_TTL = 90


def make_key(feature: str, params: Any = None) -> str:
    """Build a namespaced cache key: ``feature:<hash of the params>``."""
    payload = json.dumps(
        params if params is not None else {},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{feature}:{digest}"


class Cache:
    """A TTL cache backed by the ``cache`` table in ``state.db``.

    Each key is one row, so two processes writing different keys cannot lose
    each other's entries the way the old whole-file JSON rewrite could.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._path = Path(path) if path is not None else state.db_path()
        self._clock = clock

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = state.connect(self._path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def get(self, key: str) -> Any:
        """Return the value when present and unexpired; drop it when expired."""
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            expires_at = row["expires_at"]
            if expires_at is None or expires_at <= self._clock():
                connection.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            try:
                return json.loads(row["value"])
            except (TypeError, ValueError):
                return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        expires_at = self._clock() + ttl
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO cache (key, value, expires_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    expires_at = excluded.expires_at
                """,
                (key, payload, expires_at),
            )

    def invalidate(self, key: str | None = None) -> int:
        """Remove one key, or every key when ``key`` is ``None``.

        Returns the number of entries removed.
        """
        with self._connection() as connection:
            if key is None:
                cursor = connection.execute("DELETE FROM cache")
            else:
                cursor = connection.execute("DELETE FROM cache WHERE key = ?", (key,))
            return max(cursor.rowcount, 0)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove every key that starts with ``prefix``.

        Returns the number of entries removed. ``substr`` compares the literal
        prefix, so SQL wildcards in a key never widen the match.
        """
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM cache WHERE substr(key, 1, ?) = ?",
                (len(prefix), prefix),
            )
            return max(cursor.rowcount, 0)

    def stats(self) -> dict[str, int]:
        now = self._clock()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END), 0) AS live
                FROM cache
                """,
                (now,),
            ).fetchone()
        total = int(row["total"])
        live = int(row["live"])
        return {"total": total, "live": live, "expired": total - live}
