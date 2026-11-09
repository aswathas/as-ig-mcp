"""Filesystem paths, the SQLite state file and atomic JSON helpers."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

APP_NAME = "as-ig-mcp"
DB_NAME = "state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT,
    expires_at REAL
);
CREATE TABLE IF NOT EXISTS digest (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS queue (
    id TEXT PRIMARY KEY,
    payload TEXT,
    scheduled_at REAL,
    state TEXT,
    idempotency_key TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS presets (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    updated_at REAL
);
"""


def app_dir() -> Path:
    """Return the state directory, reading APPDATA at call time."""
    base = os.environ.get("APPDATA") or ""
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".as-ig-mcp"


def db_path() -> Path:
    """The one SQLite file holding the cache, the digest and the queue."""
    return app_dir() / DB_NAME


def session_path() -> Path:
    return app_dir() / "session.enc"


def cache_path() -> Path:
    return db_path()


def digest_path() -> Path:
    return db_path()


def events_path() -> Path:
    return app_dir() / "events.jsonl"


def audit_path() -> Path:
    return app_dir() / "audit.jsonl"


def queue_path() -> Path:
    return db_path()


def presets_path() -> Path:
    return db_path()


def style_path() -> Path:
    return app_dir() / "style.json"


def media_dir() -> Path:
    return app_dir() / "media"


def ensure_app_dir() -> Path:
    directory = app_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the state database with WAL and a ten-second busy wait.

    A second process writing at the same time waits for the lock instead of
    failing, and WAL lets readers run while a writer holds the write lock.
    The schema is created when missing, so every caller gets a usable file.
    """
    target = Path(path) if path is not None else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=10000")
    connection.executescript(_SCHEMA)
    connection.commit()
    return connection


def init_db(path: str | Path | None = None) -> Path:
    """Create the state tables if they do not exist and return the file path."""
    target = Path(path) if path is not None else db_path()
    connection = connect(target)
    connection.close()
    return target


def atomic_write_bytes(path: str | Path, data: bytes) -> None:
    """Write bytes via a unique temp file in the same directory, then replace."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json(path: str | Path, default: Any = None) -> Any:
    target = Path(path)
    if not target.exists():
        return default
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, obj: Any) -> None:
    payload = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    atomic_write_bytes(path, payload)
