"""ig_story: story and highlight details, viewers, likers, and download."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import client, state
from .cache import DEFAULT_TTL, Cache, make_key
from .serialize import plain, plain_list

ACTIONS = {"info", "viewers", "likers", "download"}

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "story_info",
    "story_viewers",
    "story_likers",
    "story_download",
    "highlight_info",
)


def _story_item(story: Any) -> dict[str, Any]:
    pk = client.field_value(story, "pk")
    user = client.field_value(story, "user")
    owner = client.field_value(user, "username") or (
        str(client.field_value(user, "pk")) if user else None
    )
    media_url = (
        client.field_value(story, "video_url")
        or client.field_value(story, "thumbnail_url")
    )
    is_seen = client.field_value(story, "is_seen")
    if is_seen is None:
        is_seen = client.field_value(story, "seen")
    return {
        "pk": str(pk) if pk is not None else None,
        "owner": owner,
        "taken_at": plain(client.field_value(story, "taken_at")),
        "media_url": plain(media_url),
        "seen": bool(is_seen),
    }


def ig_story(
    story_id: Any = None,
    highlight_id: Any = None,
    action: str = "info",
) -> dict[str, Any]:
    """Inspect story/highlight info, viewers, likers, or download media."""
    try:
        action = str(action or "info").strip().lower()
        if action not in ACTIONS:
            return {"ok": False, "error": f"unknown action: {action!r}"}

        if story_id in (None, "") and highlight_id in (None, ""):
            return {"ok": False, "error": "missing story_id or highlight_id"}

        instagram, _settings = client.open_client()

        # If highlight_id is provided and no story_id is given
        if highlight_id not in (None, "") and story_id in (None, ""):
            hl_id_str = str(highlight_id).strip()
            hl = client.call_feature(
                instagram, "highlight_info", highlight_pk=hl_id_str
            )
            raw_items = client.field_value(hl, "items") or []
            stories = [_story_item(s) for s in raw_items]

            if action == "info":
                return {
                    "ok": True,
                    "action": "info",
                    "highlight_id": hl_id_str,
                    "title": client.field_value(hl, "title"),
                    "stories": stories,
                }
            if not stories:
                if action in {"viewers", "likers"}:
                    return {
                        "ok": True,
                        "action": action,
                        "highlight_id": hl_id_str,
                        action: [],
                    }
                return {
                    "ok": False,
                    "error": f"highlight {hl_id_str} contains no stories",
                }
            target_story_id = stories[0]["pk"]
        else:
            target_story_id = str(story_id).strip()

        if action == "info":
            cache = Cache()
            cache_key = make_key(
                "ig_story_info", {"story_id": target_story_id}
            )
            cached = cache.get(cache_key)
            if isinstance(cached, dict):
                return cached

            story = client.call_feature(
                instagram, "story_info", story_pk=target_story_id
            )
            item = _story_item(story)
            result = {
                "ok": True,
                "action": "info",
                "story_id": target_story_id,
                "story": item,
            }
            cache.set(cache_key, result, ttl=DEFAULT_TTL)
            return result

        if action == "viewers":
            # Viewers must not be cached
            try:
                pk_val = int(target_story_id)
            except ValueError:
                pk_val = target_story_id
            viewers = client.call_feature(
                instagram, "story_viewers", story_pk=pk_val
            )
            return {
                "ok": True,
                "action": "viewers",
                "story_id": target_story_id,
                "viewers": plain_list(viewers),
            }

        if action == "likers":
            try:
                pk_val = int(target_story_id)
            except ValueError:
                pk_val = target_story_id
            likers = client.call_feature(
                instagram, "story_likers", story_pk=pk_val
            )
            return {
                "ok": True,
                "action": "likers",
                "story_id": target_story_id,
                "likers": plain_list(likers),
            }

        # action == "download"
        media_folder = state.media_dir()
        media_folder.mkdir(parents=True, exist_ok=True)
        out_path = client.call_feature(
            instagram,
            "story_download",
            story_pk=target_story_id,
            folder=media_folder,
        )
        resolved_out = Path(out_path).resolve()
        resolved_base = media_folder.resolve()
        if resolved_base not in resolved_out.parents and resolved_out != resolved_base:
            return {
                "ok": False,
                "error": f"download path {resolved_out} is outside media directory",
            }

        return {
            "ok": True,
            "action": "download",
            "story_id": target_story_id,
            "path": str(resolved_out),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
