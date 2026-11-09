"""The write gate: a human clicks Yes, the agent never approves.

There is no confirmation code anywhere. ``show_approval`` is the only function
that touches the desktop; it shows a yes/no message box on its own thread and
the caller waits. A write happens only after a click on the owner's screen.
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Any, Callable

from . import audit, client, mapping
from .serialize import plain

TITLE = "AS-IG-MCP - approve write"
BODY_HINT = "Yes = approve and do it now. No = do not do it."
DEFAULT_APPROVE_TIMEOUT = 300

MB_YESNO = 0x00000004
MB_SETFOREGROUND = 0x00010000
IDYES = 6
IDNO = 7
IDCANCEL = 2

NO_DESKTOP_ERROR = "no interactive desktop - a write needs a person at the keyboard"

_SECRET_TERMS = (
    "sessionid",
    "csrftoken",
    "password",
    "passwd",
    "cookie",
    "secret",
)
_SECRET_KEY_PARTS = frozenset(
    {"sessionid", "csrftoken", "password", "passwd", "cookie", "cookies", "secret", "token"}
)

_TARGET_KEYS = (
    "username",
    "user_ids",
    "user_id",
    "recipient",
    "thread_ids",
    "thread_id",
    "media_id",
    "media_pk",
    "comment_pks",
    "comment_id",
    "hashtag",
    "highlight_id",
    "story_ids",
    "url",
    "path",
    "file",
    "file_path",
)
_TARGET_PREFIXES = {
    "user_ids": "user ",
    "user_id": "user ",
    "recipient": "user ",
    "thread_ids": "thread ",
    "thread_id": "thread ",
    "media_id": "post ",
    "media_pk": "post ",
    "comment_pks": "comment ",
    "comment_id": "comment ",
    "highlight_id": "highlight ",
    "story_ids": "story ",
    "path": "file ",
    "file": "file ",
    "file_path": "file ",
    "url": "url ",
}
_TEXT_KEYS = (
    "text",
    "message",
    "caption",
    "comment",
    "note",
    "title",
    "description",
    "biography",
    "bio",
    "new_text",
    "value",
    "name",
    "category",
    "emoji",
)

_PREVIEW_LABELS = {
    "send_message": "DM to",
    "send_media": "Send media to",
    "send_voice": "Send a voice note to",
    "send_file": "Send a file to",
    "react": "React to",
    "unsend": "Unsend",
    "mark_seen": "Mark as seen",
    "share": "Share to",
    "publish_photo": "Publish",
    "publish_video": "Publish",
    "publish_reel": "Publish",
    "publish_album": "Publish",
    "publish_story": "Publish",
    "comment_reply": "Comment on",
    "comment_bulk_delete": "Delete comments on",
    "comment_pin": "Pin a comment on",
    "toggle_comments": "Toggle comments on",
    "follow": "Follow",
    "unfollow": "Unfollow",
    "block": "Block",
    "unblock": "Unblock",
    "mute": "Mute",
    "report": "Report",
    "remove_follower": "Remove follower",
    "close_friend": "Add to close friends",
    "hashtag_follow": "Follow hashtag",
    "highlight_create": "Create highlight",
    "highlight_edit": "Edit highlight",
    "note_create": "Create note",
    "profile_edit": "Edit profile",
    "category": "Set category",
    "ai_label": "Set AI label",
    "crosspost": "Crosspost",
    "collaborate": "Invite collaborators",
    "thread_hide": "Hide thread",
    "thread_title": "Set thread title",
    "thread_group_members": "Change group members",
    "follow_request_approve": "Approve follow request",
    "follow_request_decline": "Decline follow request",
    "media_download": "Download",
    "save_media": "Save",
}


def _redact(text: Any) -> str:
    result = str(text)
    for term in _SECRET_TERMS:
        result = re.sub(term, "<redacted>", result, flags=re.IGNORECASE)
    return result


def _one_line(value: Any, limit: int = 160) -> str:
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[: max(limit - 1, 0)] + "\u2026"
    return text


def _is_secret_key(key: str) -> bool:
    lowered = str(key).lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def _first(args: dict[str, Any], keys: tuple[str, ...]) -> tuple[str | None, Any]:
    for key in keys:
        if _is_secret_key(key):
            continue
        value = args.get(key)
        if value not in (None, "", [], ()):
            return key, value
    return None, None


def _format_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value]
        shown = ", ".join(items[:3])
        if len(items) > 3:
            shown += f" +{len(items) - 3}"
        return shown
    return str(value)


def _target(args: dict[str, Any]) -> str:
    key, value = _first(args, _TARGET_KEYS)
    if key is None:
        return ""
    if key == "username":
        return "@" + str(value).strip().lstrip("@")
    if key == "hashtag":
        return "#" + str(value).strip().lstrip("#")
    return _TARGET_PREFIXES.get(key, "") + _format_value(value)


def _text(args: dict[str, Any]) -> str:
    key, value = _first(args, _TEXT_KEYS)
    if key is None:
        return ""
    return _one_line(value, 120)


def _label(feature: str) -> str:
    label = _PREVIEW_LABELS.get(feature)
    if label:
        return label
    summary = mapping.FEATURE_METHODS.get(feature, {}).get("summary", feature)
    return str(summary).rstrip(".")


def make_preview(feature: str, args: dict[str, Any] | None) -> str:
    """One line a human can check: the target and the text, never a secret."""
    values = dict(args or {})
    label = _label(feature)
    target = _target(values)
    text = _text(values)
    if target and text:
        line = f'{label} {target}: "{text}"'
    elif target:
        line = f"{label} {target}"
    elif text:
        line = f'{label}: "{text}"'
    else:
        line = label
    return _redact(_one_line(line, 200))


def make_args_summary(feature: str, args: dict[str, Any] | None) -> str:
    """A short description of the attempt, not the raw arguments."""
    values = dict(args or {})
    parts = [feature]
    target = _target(values)
    if target:
        parts.append(target)
    text = _text(values)
    if text:
        parts.append(f"text {len(text)} chars")
    return _redact(_one_line(" ".join(parts), 240))


def _approve_timeout(timeout_s: float = DEFAULT_APPROVE_TIMEOUT) -> float:
    if timeout_s != DEFAULT_APPROVE_TIMEOUT:
        try:
            return max(float(timeout_s), 0.0)
        except (TypeError, ValueError):
            pass
    raw = os.environ.get("AS_IG_APPROVE_TIMEOUT", str(DEFAULT_APPROVE_TIMEOUT))
    try:
        return max(float(raw), 0.0)
    except (TypeError, ValueError):
        return float(DEFAULT_APPROVE_TIMEOUT)


def show_approval(preview: str, timeout_s: float = DEFAULT_APPROVE_TIMEOUT) -> bool | None:
    """Show the yes/no dialog on its own thread and wait for the click.

    Returns ``True`` for Yes, ``False`` for No, Cancel or a timeout, and
    ``None`` when no dialog could be shown at all (for example, no desktop
    session).
    """
    timeout = _approve_timeout(timeout_s)
    body = f"{preview}\n\n{BODY_HINT}"
    outcome: dict[str, Any] = {}

    def run_dialog() -> None:
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            user32.MessageBoxW.argtypes = [
                wintypes.HWND,
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.UINT,
            ]
            user32.MessageBoxW.restype = ctypes.c_int
            outcome["value"] = int(
                user32.MessageBoxW(
                    None,
                    body,
                    TITLE,
                    MB_YESNO | MB_SETFOREGROUND,
                )
            )
        except BaseException as exc:  # no desktop, no user32, a broken session
            outcome["error"] = exc

    worker = threading.Thread(target=run_dialog, name="as-ig-approve", daemon=True)
    try:
        worker.start()
    except BaseException:
        return None

    worker.join(timeout)
    if worker.is_alive():
        return False
    if "error" in outcome:
        return None

    value = outcome.get("value")
    if value == IDYES:
        return True
    if value == IDNO or value == IDCANCEL:
        return False
    return None


def _journal(
    feature: str,
    args: dict[str, Any],
    preview: str,
    state_name: str,
    idempotency_key: str | None,
    result_summary: str,
) -> None:
    audit.append_entry(
        {
            "ts": time.time(),
            "feature": feature,
            "args_summary": make_args_summary(feature, args),
            "preview": preview,
            "state": state_name,
            "idempotency_key": _redact(idempotency_key) if idempotency_key else None,
            "result_summary": _redact(_one_line(result_summary, 200)),
        }
    )


_INITIAL_SHOW_APPROVAL = show_approval


def perform_write(
    feature: str,
    args: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    dialog: Callable[[str], bool | None] | None = show_approval,
) -> dict[str, Any]:
    """Approve and execute one write. One call, one decision, one execution."""
    values = dict(args or {})
    if feature not in mapping.FEATURE_METHODS:
        return {"ok": False, "error": f"unknown feature: {feature!r}"}

    preview = make_preview(feature, values)

    if idempotency_key and audit.has_completed(idempotency_key):
        return {"ok": True, "already_done": True, "preview": preview}

    if dialog is None or dialog is _INITIAL_SHOW_APPROVAL:
        dialog = show_approval

    decision = dialog(preview)

    if decision is None:
        _journal(feature, values, preview, "failed", idempotency_key, "no interactive desktop")
        return {"ok": False, "error": NO_DESKTOP_ERROR, "preview": preview}

    if decision is False:
        _journal(feature, values, preview, "denied", idempotency_key, "denied by the account owner")
        return {"ok": False, "denied": True, "preview": preview}

    _journal(feature, values, preview, "approved", idempotency_key, audit.EXECUTING)
    try:
        instagram, _settings = client.open_client()
        result = client.call_write(instagram, feature, **values)
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        _journal(feature, values, preview, "failed", idempotency_key, message)
        return {"ok": False, "error": message, "preview": preview}

    _journal(feature, values, preview, "approved", idempotency_key, audit.COMPLETED)
    return {"ok": True, "preview": preview, "result": plain(result)}
