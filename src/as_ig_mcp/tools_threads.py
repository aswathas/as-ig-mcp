"""ig_thread: read DM thread messages, participants and presence."""

from __future__ import annotations

from typing import Any

from . import client, session
from .cache import DEFAULT_TTL, Cache, make_key
from .serialize import plain

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "thread_detail",
    "thread_messages",
    "presence",
    "users_presence",
)

MEDIA_ITEM_TYPES = {
    "media",
    "raven_media",
    "clip",
    "voice_media",
    "visual_media",
    "video",
    "animated_media",
    "reel_share",
    "story_share",
}


def _extract_participants(thread: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    raw_users = client.field_value(thread, "users") or []
    participants: list[dict[str, Any]] = []
    user_pk_to_name: dict[str, str] = {}
    for u in raw_users:
        pk = client.field_value(u, "pk")
        pk_str = str(pk) if pk is not None else None
        username = client.field_value(u, "username")
        full_name = client.field_value(u, "full_name")
        is_private = client.field_value(u, "is_private")
        participants.append(
            {
                "username": username,
                "full_name": full_name,
                "pk": pk_str,
                "is_private": is_private,
            }
        )
        if pk_str and username:
            user_pk_to_name[pk_str] = username
    return participants, user_pk_to_name


def _extract_messages(
    thread: Any,
    own_id: str,
    own_username: str | None,
    user_pk_to_name: dict[str, str],
) -> list[dict[str, Any]]:
    raw_messages = client.field_value(thread, "messages")
    if raw_messages is None:
        raw_messages = client.field_value(thread, "items") or []

    messages: list[dict[str, Any]] = []
    for msg in raw_messages:
        msg_id = client.field_value(msg, "id")
        sender_id = client.field_value(msg, "user_id")
        if sender_id is None:
            sender_id = client.field_value(msg, "sender_id")
        sender_id_str = str(sender_id) if sender_id is not None else None

        sender_username = client.field_value(msg, "username")
        if not sender_username and sender_id_str:
            if own_id and sender_id_str == own_id:
                sender_username = own_username
            else:
                sender_username = user_pk_to_name.get(sender_id_str)

        timestamp = client.field_value(msg, "timestamp")
        text = client.field_value(msg, "text") or ""
        item_type = client.field_value(msg, "item_type") or "text"

        is_sent_by_viewer = client.field_value(msg, "is_sent_by_viewer")
        if is_sent_by_viewer is not None:
            is_ours = bool(is_sent_by_viewer)
        elif own_id and sender_id_str:
            is_ours = sender_id_str == own_id
        else:
            is_ours = False

        has_media = bool(
            client.field_value(msg, "media")
            or client.field_value(msg, "visual_media")
            or client.field_value(msg, "has_media")
            or str(item_type).lower() in MEDIA_ITEM_TYPES
            or (not text and str(item_type).lower() != "text")
        )
        if has_media and not text:
            text = ""

        messages.append(
            {
                "id": str(msg_id) if msg_id is not None else None,
                "sender_id": sender_id_str,
                "username": sender_username,
                "timestamp": plain(timestamp),
                "text": str(text),
                "item_type": str(item_type),
                "is_ours": is_ours,
                "has_media": has_media,
            }
        )
    return messages


def _fetch_presence(
    instagram: Any, participants: list[dict[str, Any]], own_id: str
) -> dict[str, Any] | None:
    other_ids = [
        int(p["pk"])
        for p in participants
        if p.get("pk") and p["pk"] != own_id and str(p["pk"]).isdigit()
    ]
    if not other_ids:
        return None

    try:
        pres_res = client.call_feature(instagram, "users_presence", user_ids=other_ids)
        if isinstance(pres_res, dict) and "user_presence" in pres_res:
            res_dict = pres_res["user_presence"]
            return plain(res_dict) if res_dict else None
        if isinstance(pres_res, dict) and pres_res:
            return plain(pres_res)
    except Exception:
        pass

    try:
        pres_res = client.call_feature(instagram, "presence")
        if isinstance(pres_res, dict) and pres_res:
            return plain(pres_res)
    except Exception:
        pass

    return None


def ig_thread(
    thread_id: Any,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Read thread messages, participants, presence, and pagination cursor."""
    try:
        if thread_id in (None, ""):
            return {"ok": False, "error": "thread_id is required"}

        thread_id_str = str(thread_id).strip()
        limit = max(int(limit or 20), 1)

        cache = Cache()
        cache_key = make_key(
            "ig_thread_data",
            {"thread_id": thread_id_str, "cursor": cursor, "limit": limit},
        )
        cached_data = cache.get(cache_key)

        instagram, settings = client.open_client()
        identity = session.settings_identity(settings or {})
        own_id = str(identity.get("user_id") or "")
        own_username = identity.get("username")

        if isinstance(cached_data, dict):
            participants = cached_data.get("participants", [])
            messages = cached_data.get("messages", [])
            next_cursor = cached_data.get("next_cursor")
        else:
            kwargs: dict[str, Any] = {"thread_id": thread_id_str, "amount": limit}
            if cursor is not None:
                kwargs["cursor"] = cursor

            try:
                thread_result = client.call_feature(
                    instagram, "thread_detail", **kwargs
                )
            except TypeError as exc:
                if "cursor" in str(exc) and "cursor" in kwargs:
                    del kwargs["cursor"]
                    thread_result = client.call_feature(
                        instagram, "thread_detail", **kwargs
                    )
                else:
                    raise
            except Exception as exc:
                err_str = str(exc).lower()
                type_name = type(exc).__name__.lower()
                if "notfound" in type_name or "not found" in err_str:
                    return {"ok": False, "error": f"thread not found: {thread_id_str}"}
                raise

            if thread_result is None:
                return {"ok": False, "error": f"thread not found: {thread_id_str}"}

            thread_obj = thread_result
            next_cursor = None
            if isinstance(thread_result, tuple) and len(thread_result) == 2:
                thread_obj, next_cursor = thread_result
            else:
                next_cursor = (
                    client.field_value(thread_obj, "next_cursor")
                    or client.field_value(thread_obj, "oldest_cursor")
                    or client.field_value(thread_obj, "cursor")
                )

            participants, user_pk_to_name = _extract_participants(thread_obj)
            messages = _extract_messages(
                thread_obj, own_id, own_username, user_pk_to_name
            )

            cache.set(
                cache_key,
                {
                    "participants": participants,
                    "messages": messages,
                    "next_cursor": next_cursor,
                },
                ttl=DEFAULT_TTL,
            )

        # Presence must not be cached
        presence = _fetch_presence(instagram, participants, own_id)

        return {
            "ok": True,
            "thread_id": thread_id_str,
            "participants": participants,
            "messages": messages[:limit],
            "presence": presence,
            "next_cursor": next_cursor,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
