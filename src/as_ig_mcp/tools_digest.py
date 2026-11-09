"""ig_digest: delta digest reporting what changed since the last call."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from . import client, events, realtime, session, state
from .serialize import plain

FEATURES = (
    "thread_list",
    "profile",
    "followers",
    "posts_page",
    "posts",
    "stories",
)

MAX_TIMEOUT_S = 60.0


def _parse_iso(iso_str: str) -> float | None:
    try:
        clean = iso_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _to_epoch(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # If milliseconds:
        if val > 1e11:
            return val / 1000.0
        return float(val)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return val.timestamp()
    if isinstance(val, str):
        return _parse_iso(val)
    return None


def read_inbox(instagram: Any, settings: dict[str, Any] | None = None, fresh: bool = True) -> list[Any]:
    """Underlying read for inbox threads."""
    try:
        threads = client.call_feature(instagram, "thread_list", amount=20)
        return list(threads or [])
    except Exception:
        return []


def read_followers(instagram: Any, user_id: str, fresh: bool = True) -> tuple[int, list[dict[str, Any]]]:
    """Underlying read for followers count and follower accounts."""
    count = 0
    accounts: list[dict[str, Any]] = []
    try:
        user = client.call_feature(instagram, "profile", user_id=user_id)
        raw_count = client.field_value(user, "follower_count")
        if raw_count is not None:
            count = int(raw_count)
    except Exception:
        pass

    try:
        flist = client.call_feature(instagram, "followers", user_id=user_id, amount=50)
        users = flist[0] if isinstance(flist, tuple) else flist
        for u in users or []:
            pk = client.field_value(u, "pk") or client.field_value(u, "user_id")
            uname = client.field_value(u, "username")
            if pk is not None:
                accounts.append({"user_id": str(pk), "username": uname})
        if count == 0 and accounts:
            count = len(accounts)
    except Exception:
        pass

    return count, accounts


def read_posts(instagram: Any, user_id: str, limit: int = 12, fresh: bool = True) -> list[Any]:
    """Underlying read for user's recent posts."""
    try:
        if hasattr(instagram, "user_medias_paginated_v1"):
            res = client.call_feature(instagram, "posts_page", user_id=user_id, amount=limit)
            items, _ = client.split_page(res)
            return items
        if hasattr(instagram, "user_medias_v1"):
            res = client.call_feature(instagram, "posts", user_id=user_id, amount=limit)
            items, _ = client.split_page(res)
            return items
        res = client.call_feature(instagram, "posts_page", user_id=user_id, amount=limit)
        items, _ = client.split_page(res)
        return items
    except Exception:
        return []


def read_stories(instagram: Any, user_id: str, fresh: bool = True) -> list[Any]:
    """Underlying read for user's active stories."""
    try:
        res = client.call_feature(instagram, "stories", user_id=user_id)
        if isinstance(res, (list, tuple)):
            return list(res)
        return []
    except Exception:
        return []


def _load_markers() -> tuple[dict[str, Any] | None, float | None]:
    with state.connect() as conn:
        row = conn.execute(
            "SELECT value, updated_at FROM digest WHERE key = 'markers'"
        ).fetchone()
        if row is None or not row["value"]:
            return None, None
        try:
            return json.loads(row["value"]), row["updated_at"]
        except Exception:
            return None, None


def _save_markers(markers: dict[str, Any], ts: float) -> None:
    with state.connect() as conn:
        conn.execute(
            """
            INSERT INTO digest (key, value, updated_at) VALUES ('markers', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (json.dumps(markers), ts),
        )


def ig_digest(
    since: str = "last",
    timeout_s: float = 0.0,
    kinds: list[str] | None = None,
    client_instance: Any = None,
) -> dict[str, Any]:
    """Compute and return what changed since the last call."""
    timeout_s = min(max(float(timeout_s or 0.0), 0.0), MAX_TIMEOUT_S)

    if client_instance is not None:
        instagram = client_instance
        settings: dict[str, Any] = {}
        identity = {"user_id": "0"}
    else:
        try:
            instagram, settings = client.open_client()
            identity = session.settings_identity(settings or {})
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    user_id = str(identity.get("user_id") or "0")

    # Underlying reads with fresh=True
    threads = read_inbox(instagram, settings=settings, fresh=True)
    follower_count, follower_accounts = read_followers(instagram, user_id=user_id, fresh=True)
    posts = read_posts(instagram, user_id=user_id, limit=12, fresh=True)
    stories = read_stories(instagram, user_id=user_id, fresh=True)

    # Build current state snapshots
    current_messages: dict[str, dict[str, Any]] = {}
    for t in threads:
        tid = client.field_value(t, "id") or client.field_value(t, "thread_id")
        if tid is None:
            continue
        tid_str = str(tid)
        msgs = client.field_value(t, "messages") or []
        if msgs:
            latest = msgs[0]
            mid = client.field_value(latest, "id")
            sender = client.field_value(latest, "user_id") or client.field_value(latest, "username") or ""
            text = client.field_value(latest, "text") or ""
            ts = client.field_value(latest, "timestamp")
            current_messages[tid_str] = {
                "message_id": str(mid) if mid is not None else None,
                "sender": str(sender),
                "text": str(text),
                "time": plain(ts),
                "epoch": _to_epoch(ts),
            }

    current_post_pks = []
    current_posts_map: dict[str, dict[str, Any]] = {}
    for p in posts:
        pk = client.field_value(p, "pk")
        if pk is None:
            continue
        pk_str = str(pk)
        current_post_pks.append(pk_str)
        caption = client.field_value(p, "caption_text") or client.field_value(p, "caption") or ""
        ts = client.field_value(p, "taken_at")
        current_posts_map[pk_str] = {
            "pk": pk_str,
            "caption": str(caption),
            "time": plain(ts),
            "epoch": _to_epoch(ts),
        }

    current_story_pks = []
    for s in stories:
        pk = client.field_value(s, "pk") or client.field_value(s, "id")
        if pk is not None:
            current_story_pks.append(str(pk))

    now = time.time()
    markers, prev_updated_at = _load_markers()

    # Determine if since is an ISO date
    since_ts: float | None = None
    if since != "last":
        since_ts = _parse_iso(since)

    # First run: no stored markers and since == "last"
    if markers is None and since_ts is None:
        initial_markers = {
            "messages": {tid: data["message_id"] for tid, data in current_messages.items()},
            "follower_count": follower_count,
            "follower_ids": [acc["user_id"] for acc in follower_accounts if "user_id" in acc],
            "posts": current_post_pks,
            "stories": current_story_pks,
            "event_offset": events.count(),
        }
        _save_markers(initial_markers, now)
        return {
            "ok": True,
            "first_run": True,
            "nothing_changed": True,
            "changed": False,
            "new_messages": [],
            "new_followers": {"count_change": 0, "accounts": []},
            "new_posts": [],
            "new_stories": [],
            "events": [],
            "markers_updated_at": now,
        }

    # Compare changes
    new_messages: list[dict[str, Any]] = []
    new_posts: list[dict[str, Any]] = []
    new_stories: list[str] = []

    if since_ts is not None:
        # Compare by ISO timestamp
        for tid, data in current_messages.items():
            if data.get("epoch") and data["epoch"] > since_ts:
                new_messages.append({
                    "thread_id": tid,
                    "message_id": data["message_id"],
                    "sender": data["sender"],
                    "text": data["text"],
                    "time": data["time"],
                })
        for pk_str, data in current_posts_map.items():
            if data.get("epoch") and data["epoch"] > since_ts:
                new_posts.append({
                    "pk": pk_str,
                    "caption": data["caption"],
                    "time": data["time"],
                })
        new_stories = list(current_story_pks)
        count_change = 0
        new_accounts: list[dict[str, Any]] = []
        event_offset = 0
    else:
        # Compare against stored markers
        prev_messages = markers.get("messages", {})
        for tid, data in current_messages.items():
            prev_mid = prev_messages.get(tid)
            if prev_mid is None or data["message_id"] != prev_mid:
                new_messages.append({
                    "thread_id": tid,
                    "message_id": data["message_id"],
                    "sender": data["sender"],
                    "text": data["text"],
                    "time": data["time"],
                })

        prev_posts_set = set(markers.get("posts", []))
        for pk_str, data in current_posts_map.items():
            if pk_str not in prev_posts_set:
                new_posts.append({
                    "pk": pk_str,
                    "caption": data["caption"],
                    "time": data["time"],
                })

        prev_stories_set = set(markers.get("stories", []))
        for pk_str in current_story_pks:
            if pk_str not in prev_stories_set:
                new_stories.append(pk_str)

        prev_count = markers.get("follower_count", follower_count)
        prev_ids = set(markers.get("follower_ids", []))
        count_change = follower_count - prev_count
        new_accounts = [acc for acc in follower_accounts if acc.get("user_id") not in prev_ids]
        event_offset = markers.get("event_offset", 0)

    new_followers = {
        "count_change": count_change,
        "accounts": new_accounts,
    }

    # Realtime events
    rt_status = realtime.status()
    socket_on = rt_status.get("enabled", True) and rt_status.get("connected", False)

    if socket_on:
        rt_events = events.tail(offset=event_offset, timeout_s=timeout_s, kinds=kinds)
    else:
        if timeout_s > 0.0:
            time.sleep(timeout_s)
        rt_events = []

    # Save new markers
    new_markers = {
        "messages": {tid: data["message_id"] for tid, data in current_messages.items()},
        "follower_count": follower_count,
        "follower_ids": [acc["user_id"] for acc in follower_accounts if "user_id" in acc],
        "posts": current_post_pks,
        "stories": current_story_pks,
        "event_offset": events.count(),
    }
    _save_markers(new_markers, now)

    has_changed = bool(
        new_messages
        or new_posts
        or new_stories
        or rt_events
        or count_change != 0
        or new_accounts
    )

    return {
        "ok": True,
        "first_run": False,
        "nothing_changed": not has_changed,
        "changed": has_changed,
        "new_messages": new_messages,
        "new_followers": new_followers,
        "new_posts": new_posts,
        "new_stories": new_stories,
        "events": rt_events,
        "markers_updated_at": now,
    }
