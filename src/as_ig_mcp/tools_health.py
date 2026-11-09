"""ig_health: probe one representative call per capability class."""

from __future__ import annotations

import time
from typing import Any

from . import client, mapping, session
from .session import settings_identity

PROBES: tuple[tuple[str, str], ...] = (
    ("profile", "profile"),
    ("followers", "followers"),
    ("posts", "posts"),
    ("insights_media", "post_insights"),
    ("account_insights", "account_insights"),
    ("dm_threads", "thread_list"),
    ("dm_presence", "presence"),
    ("notifications", "notifications"),
    ("discovery", "hashtag_info"),
    ("business_dm_box", "business_dm_box"),
)

_LAST_SUMMARY = "unknown"


def last_summary() -> str:
    """The summary from the last in-process health run, or ``"unknown"``."""
    return _LAST_SUMMARY


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _probe_args(feature: str, user_id: str | None, media_pk: Any) -> dict[str, Any]:
    if feature in {"profile", "followers"}:
        return {"user_id": user_id}
    if feature == "posts":
        # amount=0 asks Instagram for everything and comes back as a generic
        # "something went wrong". A small page is enough to prove the path works.
        return {"user_id": user_id, "amount": 5}
    if feature == "post_insights":
        return {"media_pk": media_pk}
    if feature == "hashtag_info":
        return {"name": "chennai"}
    return {}


def _all(classes: dict[str, dict], status: str, reason: str) -> None:
    for label, _feature in PROBES:
        classes[label] = {"status": status, "reason": reason}


def ig_health() -> dict[str, Any]:
    """Run every probe and report each class live or dead."""
    global _LAST_SUMMARY

    classes: dict[str, dict] = {}
    try:
        settings = session.load_session()
        session_error = None
    except Exception as exc:  # malformed or undecryptable session
        settings = None
        session_error = f"{type(exc).__name__}: {exc}"

    if settings is None:
        _all(classes, "dead", "no session")
        summary = f"0/{len(PROBES)} live"
        _LAST_SUMMARY = summary
        result = {"classes": classes, "summary": summary, "checked_at": int(time.time())}
        if session_error:
            result["session_error"] = session_error
        return result

    identity = settings_identity(settings)
    user_id = identity["user_id"]

    try:
        instagram = client.build_client(settings)
    except Exception as exc:
        _all(classes, "dead", f"{type(exc).__name__}: {exc}")
        summary = f"0/{len(PROBES)} live"
        _LAST_SUMMARY = summary
        return {"classes": classes, "summary": summary, "checked_at": int(time.time())}

    media_pk = None
    for label, feature in PROBES:
        spec = mapping.FEATURE_METHODS.get(feature)
        if not spec or not spec.get("read_only", False):
            classes[label] = {"status": "dead", "reason": "feature is a write"}
            continue
        if feature == "post_insights" and media_pk is None:
            classes[label] = {
                "status": "dead",
                "reason": "no own media pk available to ask for insights",
            }
            continue
        try:
            result = client.call_feature(
                instagram, feature, **_probe_args(feature, user_id, media_pk)
            )
            classes[label] = {"status": "live", "reason": "ok"}
            if feature == "posts" and isinstance(result, (list, tuple)) and result:
                pk = _value(result[0], "pk")
                media_pk = int(pk) if pk is not None else None
        except Exception as exc:
            classes[label] = {
                "status": "dead",
                "reason": f"{type(exc).__name__}: {exc}",
            }

    live = sum(1 for entry in classes.values() if entry["status"] == "live")
    summary = f"{live}/{len(PROBES)} live"
    _LAST_SUMMARY = summary
    return {"classes": classes, "summary": summary, "checked_at": int(time.time())}
