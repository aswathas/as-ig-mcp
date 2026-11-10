"""ig_inbox: DM threads awaiting reply with optional style suggested replies."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from . import client, session, state
from .serialize import plain

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "thread_list",
    "thread_detail",
    "business_dm_box",
    "pending_requests",
    "spam_inbox",
)

DEFAULT_TEMPLATE = "Thanks for reaching out! I'll get back to you shortly."


def _parse_time(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # handle seconds vs milliseconds vs microseconds
        ts = float(val)
        if ts > 1e14:  # microseconds
            ts /= 1e6
        elif ts > 1e11:  # milliseconds
            ts /= 1e3
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return None
    return None


def sanitize_suggested_reply(reply: str) -> str:
    """Ensure suggested reply has no links, phone numbers, emails, and at most 2 sentences."""
    if not reply:
        return DEFAULT_TEMPLATE

    text = str(reply)

    # 1. Strip email addresses
    text = re.sub(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", "", text)

    # 2. Strip URLs and domain links
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"\b[a-zA-Z0-9.-]+\.(?:com|org|net|io|co|ai|dev|app|me|info|biz)\b\S*", "", text)

    # 3. Strip phone numbers (e.g. +1-555-123-4567, 555-1234, etc.)
    text = re.sub(r"\+?\b(?:\d[\s\-\(\).]*){7,}\d\b", "", text)

    # 4. Clean extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    # 5. Limit to at most 2 sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) > 2:
        text = " ".join(sentences[:2])
    elif sentences:
        text = " ".join(sentences)
    else:
        text = DEFAULT_TEMPLATE

    return text.strip()


def build_suggested_reply(username: str, last_message_text: str = "") -> tuple[str, str]:
    """Return (suggested_reply, suggested_source)."""
    style_path = state.style_path()
    styles = state.read_json(style_path, default={})
    if not isinstance(styles, dict):
        styles = {}

    clean_username = str(username or "").strip().lstrip("@").lower()
    entry = None
    for k, v in styles.items():
        if k.strip().lstrip("@").lower() == clean_username and isinstance(v, dict):
            entry = v
            break

    if not entry:
        return DEFAULT_TEMPLATE, "default template"

    formality = str(entry.get("formality", "")).lower()
    resp_style = entry.get("response_style", "")

    if "casual" in formality or "informal" in formality:
        raw_reply = "Hey! Got your message, will catch up with you soon."
    elif "formal" in formality:
        raw_reply = "Hello. Thank you for your message. I will review and reply at my earliest convenience."
    elif resp_style:
        raw_reply = f"Thanks for reaching out! {resp_style}"
    else:
        raw_reply = "Thanks for reaching out! I'll get back to you shortly."

    reply = sanitize_suggested_reply(raw_reply)
    return reply, "style.json"


def _extract_item(
    thread: Any,
    own_id: str,
    suggest: bool = False,
) -> dict[str, Any] | None:
    thread_id = client.field_value(thread, "id") or client.field_value(thread, "pk")
    if thread_id is None:
        return None
    thread_id_str = str(thread_id)

    raw_messages = client.field_value(thread, "messages")
    if raw_messages is None:
        raw_messages = client.field_value(thread, "items") or []

    if not raw_messages:
        return None

    # Get latest message
    latest_msg = raw_messages[0]
    for msg in raw_messages:
        t_curr = _parse_time(client.field_value(msg, "timestamp"))
        t_lat = _parse_time(client.field_value(latest_msg, "timestamp"))
        if t_curr and t_lat and t_curr > t_lat:
            latest_msg = msg

    # Determine if last message is ours
    is_sent_by_viewer = client.field_value(latest_msg, "is_sent_by_viewer")
    sender_id = client.field_value(latest_msg, "user_id")
    if sender_id is None:
        sender_id = client.field_value(latest_msg, "sender_id")
    sender_id_str = str(sender_id) if sender_id is not None else None

    if is_sent_by_viewer is not None:
        is_ours = bool(is_sent_by_viewer)
    elif own_id and sender_id_str:
        is_ours = sender_id_str == own_id
    else:
        is_ours = False

    # Find the other participant's username
    users = client.field_value(thread, "users") or []
    other_username = None
    for u in users:
        pk = str(client.field_value(u, "pk")) if client.field_value(u, "pk") is not None else ""
        if pk and pk != own_id:
            other_username = client.field_value(u, "username")
            if other_username:
                break
    if not other_username:
        other_username = (
            client.field_value(latest_msg, "username")
            or client.field_value(thread, "thread_title")
            or "unknown"
        )

    last_text = client.field_value(latest_msg, "text") or ""
    last_time = client.field_value(latest_msg, "timestamp")

    read_state = client.field_value(thread, "read_state")
    is_seen = client.field_value(thread, "is_seen")
    unread = (read_state == 1) or (is_seen is False)

    item: dict[str, Any] = {
        "thread_id": thread_id_str,
        "username": other_username,
        "last_message_text": str(last_text),
        "last_message_time": plain(last_time),
        "unread": bool(unread),
        "message_count": len(raw_messages),
        "is_ours": is_ours,
    }

    if suggest:
        reply_str, reply_source = build_suggested_reply(other_username, str(last_text))
        item["suggested_reply"] = reply_str
        item["suggested_source"] = reply_source

    return item


def ig_inbox(
    hours: int = 48,
    limit: int = 10,
    suggest: bool = False,
    thread_id: Any = None,
    box: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    """List threads waiting for a reply, or check a specific thread."""
    try:
        hours = max(int(hours or 48), 1)
        limit = max(int(limit or 10), 1)

        if box is not None and box not in ("general", "primary", "requests", "spam"):
            return {
                "ok": False,
                "error": f"unknown box: {box}; valid: general, primary, requests, spam",
            }
        if kind and kind != "groups":
            return {
                "ok": False,
                "error": f"unknown kind: {kind}; valid: groups",
            }

        if box is not None or kind == "groups":
            instagram, settings = client.open_client()
            identity = session.settings_identity(settings or {})
            own_id = str(identity.get("user_id") or "")

            if box is not None:
                if box in ("general", "primary"):
                    threads = client.call_feature(
                        instagram, "thread_list", amount=limit, box=box
                    )
                elif box == "requests":
                    threads = client.call_feature(
                        instagram, "pending_requests", amount=limit
                    )
                else:
                    threads = client.call_feature(
                        instagram, "spam_inbox", amount=limit
                    )
            else:
                threads = client.call_feature(
                    instagram, "thread_list", amount=max(limit * 3, 20)
                )

            if not isinstance(threads, list):
                threads = list(threads or [])

            items: list[dict[str, Any]] = []
            for thread in threads:
                if kind == "groups" and not client.field_value(thread, "is_group"):
                    continue
                item = _extract_item(thread, own_id, suggest=suggest)
                if not item:
                    continue
                item["is_group"] = bool(client.field_value(thread, "is_group"))
                item.pop("is_ours", None)
                items.append(item)
                if len(items) >= limit:
                    break

            return {
                "ok": True,
                "box": box or None,
                "kind": kind or None,
                "items": items,
            }

        instagram, settings = client.open_client()
        identity = session.settings_identity(settings or {})
        own_id = str(identity.get("user_id") or "")

        # When thread_id is given, return that one thread
        if thread_id not in (None, ""):
            thread_id_str = str(thread_id).strip()
            thread = client.call_feature(
                instagram, "thread_detail", thread_id=thread_id_str, amount=10
            )
            item = _extract_item(thread, own_id, suggest=suggest)
            if not item:
                return {"ok": False, "error": f"thread not found: {thread_id_str}"}
            # Remove helper key
            item.pop("is_ours", None)
            return {
                "ok": True,
                "thread_id": thread_id_str,
                "thread": item,
                "items": [item],
            }

        # Otherwise list threads awaiting reply
        threads = client.call_feature(instagram, "thread_list", amount=max(limit * 3, 20))
        if not isinstance(threads, list):
            threads = list(threads or [])

        now = datetime.now(timezone.utc)
        items: list[dict[str, Any]] = []

        for thread in threads:
            item = _extract_item(thread, own_id, suggest=suggest)
            if not item:
                continue

            # Must NOT be ours
            if item.get("is_ours"):
                continue

            # Must have arrived within hours
            msg_dt = _parse_time(item["last_message_time"])
            if msg_dt:
                if msg_dt.tzinfo is None:
                    msg_dt = msg_dt.replace(tzinfo=timezone.utc)
                age = (now - msg_dt).total_seconds()
                if age > hours * 3600:
                    continue

            item.pop("is_ours", None)
            items.append(item)
            if len(items) >= limit:
                break

        return {"ok": True, "hours": hours, "limit": limit, "items": items}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
