"""ig_status: session, account, cache, realtime and health at a glance."""

from __future__ import annotations

from typing import Any

from . import __version__, client, session, tools_health
from .cache import Cache, make_key
from .session import settings_identity

ACCOUNT_TTL = 90


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _account_from_user(user: Any) -> dict[str, Any]:
    pk = _value(user, "pk")
    if pk is None:
        pk = _value(user, "user_id")
    return {
        "username": _value(user, "username"),
        "user_id": str(pk) if pk is not None else None,
        "followers": _value(user, "follower_count"),
        "following": _value(user, "following_count"),
        "media_count": _value(user, "media_count"),
        "is_business": _value(user, "is_business"),
    }


def _read_account(settings: dict[str, Any], user_id: str | None) -> dict[str, Any]:
    cache = Cache()
    key = make_key("profile", {"user_id": user_id})
    cached = cache.get(key)
    if isinstance(cached, dict):
        return cached

    if not user_id:
        raise RuntimeError("session has no user id")

    instagram = client.build_client(settings)
    user = client.call_feature(instagram, "profile", user_id=user_id)
    account = _account_from_user(user)
    cache.set(key, account, ttl=ACCOUNT_TTL)
    return account


def _status() -> dict[str, Any]:
    cache = Cache()
    result: dict[str, Any] = {
        "session": {
            "present": False,
            "username": None,
            "user_id": None,
            "source": "none",
        },
        "account": None,
        "quota": "unknown - instagrapi exposes no quota endpoint",
        "cache": cache.stats(),
        "realtime": {"enabled": False, "state": "not implemented in v1 phase 2"},
        "health": tools_health.last_summary(),
        "version": __version__,
    }

    try:
        settings = session.load_session()
    except Exception as exc:
        result["account_error"] = f"{type(exc).__name__}: {exc}"
        return result

    if settings is None:
        result["account_error"] = "no session"
        return result

    identity = settings_identity(settings)
    result["session"] = {
        "present": True,
        "username": identity["username"],
        "user_id": identity["user_id"],
        "source": "file",
    }

    try:
        result["account"] = _read_account(settings, identity["user_id"])
    except Exception as exc:
        result["account"] = None
        result["account_error"] = f"{type(exc).__name__}: {exc}"

    return result


def ig_status() -> dict[str, Any]:
    """Return session, account, cache, realtime and health state."""
    try:
        return _status()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
