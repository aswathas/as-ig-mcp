"""Filesystem paths and atomic JSON helpers for AS-IG-MCP state."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

APP_NAME = "as-ig-mcp"


def app_dir() -> Path:
    """Return the state directory, reading APPDATA at call time."""
    base = os.environ.get("APPDATA") or ""
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".as-ig-mcp"


def session_path() -> Path:
    return app_dir() / "session.enc"


def cache_path() -> Path:
    return app_dir() / "cache.json"


def digest_path() -> Path:
    return app_dir() / "digest.json"


def events_path() -> Path:
    return app_dir() / "events.jsonl"


def audit_path() -> Path:
    return app_dir() / "audit.jsonl"


def queue_path() -> Path:
    return app_dir() / "queue.json"


def presets_path() -> Path:
    return app_dir() / "presets.json"


def ensure_app_dir() -> Path:
    directory = app_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


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
