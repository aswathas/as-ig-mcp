"""TTL cache on disk, shared safely between processes."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

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
    """A JSON-file cache of ``{key: {"value": ..., "expires_at": <epoch>}}``."""

    def __init__(
        self,
        path: str | Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._path = Path(path) if path is not None else state.cache_path()
        self._clock = clock

    def _read(self) -> dict[str, dict]:
        try:
            raw = self._path.read_bytes()
        except OSError:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {key: entry for key, entry in data.items() if isinstance(entry, dict)}

    def _write(self, entries: dict[str, dict]) -> None:
        payload = json.dumps(entries, ensure_ascii=False).encode("utf-8")
        state.atomic_write_bytes(self._path, payload)

    def get(self, key: str) -> Any:
        """Return the value when present and unexpired; drop it when expired."""
        entries = self._read()
        entry = entries.get(key)
        if entry is None:
            return None
        if entry.get("expires_at", 0) <= self._clock():
            del entries[key]
            self._write(entries)
            return None
        return entry.get("value")

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        entries = self._read()
        entries[key] = {"value": value, "expires_at": self._clock() + ttl}
        self._write(entries)

    def invalidate(self, key: str | None = None) -> int:
        """Remove one key, or every key when ``key`` is ``None``.

        Returns the number of entries removed.
        """
        entries = self._read()
        if key is None:
            removed = len(entries)
            self._write({})
            return removed
        if key in entries:
            del entries[key]
            self._write(entries)
            return 1
        return 0

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove every key that starts with ``prefix``.

        Returns the number of entries removed.
        """
        entries = self._read()
        matching = [key for key in entries if key.startswith(prefix)]
        if not matching:
            return 0
        for key in matching:
            del entries[key]
        self._write(entries)
        return len(matching)

    def stats(self) -> dict[str, int]:
        entries = self._read()
        now = self._clock()
        live = sum(1 for entry in entries.values() if entry.get("expires_at", 0) > now)
        return {"total": len(entries), "live": live, "expired": len(entries) - live}
