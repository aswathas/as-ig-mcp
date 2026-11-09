"""ig_session: status, cache clear, export and the relogin placeholder."""

from __future__ import annotations

from typing import Any

from . import session
from .cache import Cache
from .session import settings_identity

REDACTED = "<redacted>"
SECRET_KEYS = {"sessionid", "csrftoken"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if key in SECRET_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _status() -> dict[str, Any]:
    cache = Cache()
    result: dict[str, Any] = {
        "ok": True,
        "session": {
            "present": False,
            "username": None,
            "user_id": None,
            "source": "none",
        },
        "cache": cache.stats(),
        "token": {"fetchable": False, "kind": "fb_dtsg"},
    }

    try:
        settings = session.load_session()
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    if settings is None:
        return result

    identity = settings_identity(settings)
    result["session"] = {
        "present": True,
        "username": identity["username"],
        "user_id": identity["user_id"],
        "source": "file",
    }
    result["token"] = {
        "fetchable": bool(identity["sessionid"]),
        "kind": "fb_dtsg",
    }
    return result


def ig_session(action: str = "status") -> dict[str, Any]:
    """Inspect the session or manage the local cache."""
    action = (action or "status").strip().lower()

    if action == "status":
        return _status()

    if action == "cache_clear":
        try:
            cache = Cache()
            cleared = cache.invalidate()
            return {
                "ok": True,
                "action": action,
                "cleared": cleared,
                "cache": cache.stats(),
            }
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if action == "export":
        try:
            settings = session.load_session()
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if settings is None:
            return {"ok": False, "error": "no session"}
        return {"ok": True, "settings": _redact(settings)}

    if action == "relogin":
        return {"ok": False, "error": "relogin lands in phase 5"}

    return {"ok": False, "error": f"unknown action: {action}"}
