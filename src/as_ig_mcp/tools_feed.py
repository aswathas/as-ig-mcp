"""ig_feed: posts, reels, tagged, saved, archive, notifications and more."""

from __future__ import annotations

from typing import Any

from . import client
from .cache import DEFAULT_TTL, Cache, make_key
from .serialize import plain, plain_list

KINDS = {
    "posts",
    "reels",
    "tagged",
    "saved",
    "archive",
    "notifications",
    "collections",
    "tray",
    "guides",
    "liked",
}

MEDIA_KINDS = {"posts", "reels", "tagged"}

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "posts_page",
    "reels_page",
    "tagged_page",
    "saved_collections",
    "archived",
    "notifications",
    "following",
    "stories",
    "guides",
    "liked",
    "comments",
)

CAPTION_LIMIT = 300


def media_item(media: Any) -> dict[str, Any]:
    """Flatten one media object to the fields an agent needs."""
    pk = client.field_value(media, "pk")
    code = client.field_value(media, "code")
    if code:
        permalink = f"https://www.instagram.com/p/{code}/"
    elif pk:
        permalink = f"https://www.instagram.com/p/{pk}/"
    else:
        permalink = None
    caption = client.field_value(media, "caption_text") or ""
    owner = client.field_value(media, "user")
    return {
        "pk": str(pk) if pk is not None else None,
        "media_type": client.field_value(media, "media_type"),
        "taken_at": plain(client.field_value(media, "taken_at")),
        "caption": str(caption)[:CAPTION_LIMIT],
        "like_count": client.field_value(media, "like_count"),
        "comment_count": client.field_value(media, "comment_count"),
        "permalink": permalink,
        "thumbnail_url": plain(client.field_value(media, "thumbnail_url")),
        "owner_username": client.field_value(owner, "username"),
    }


def _collection_item(collection: Any) -> dict[str, Any]:
    collection_id = client.field_value(collection, "id")
    return {
        "id": str(collection_id) if collection_id is not None else None,
        "name": client.field_value(collection, "name"),
        "media_count": client.field_value(collection, "media_count"),
    }


def _notification_items(result: Any) -> list[Any]:
    if isinstance(result, dict):
        items: list[Any] = []
        for key in ("new_stories", "old_stories"):
            items.extend(result.get(key) or [])
        return items
    return list(result or [])


def _attach_comments(instagram: Any, items: list[dict], amount: int = 50) -> None:
    for item in items[:5]:
        pk = item.get("pk")
        if pk is None:
            continue
        comments = client.call_feature(instagram, "comments", media_id=pk, amount=amount)
        item["comments"] = plain_list(comments, amount)


def _tray(instagram: Any, settings: dict[str, Any]) -> list[dict[str, Any]]:
    own_id = client.resolve_user_id(instagram, settings=settings)
    following = client.call_feature(instagram, "following", user_id=own_id, amount=10)
    items = []
    for user in list(following or [])[:10]:
        user_id = client.field_value(user, "pk")
        username = client.field_value(user, "username")
        try:
            stories = client.call_feature(instagram, "stories", user_id=user_id)
            story_pks = [str(client.field_value(story, "pk")) for story in stories or []]
        except Exception:
            story_pks = []
        items.append(
            {
                "user_id": str(user_id) if user_id is not None else None,
                "username": username,
                "story_pks": story_pks,
            }
        )
    return items


def _dispatch(
    instagram: Any,
    settings: dict[str, Any],
    kind: str,
    username: str | None,
    user_id: Any,
    cursor: str | None,
    limit: int,
    include: str,
) -> dict[str, Any]:
    next_cursor = None

    if kind in MEDIA_KINDS:
        account = client.resolve_user_id(instagram, username, user_id, settings)
        feature = {"posts": "posts_page", "reels": "reels_page", "tagged": "tagged_page"}[kind]
        result = client.call_feature(
            instagram, feature, user_id=account, amount=limit, end_cursor=cursor or ""
        )
        media, next_cursor = client.split_page(result)
        # "posts" means every post on the account, photos and reels alike.
        # Filtering reels out here emptied the list on accounts that only post
        # reels, so the split is: posts = everything, reels = the clips subset.
        items = [media_item(item) for item in media][:limit]
    elif kind in {"saved", "collections"}:
        collections = client.call_feature(instagram, "saved_collections")
        items = [_collection_item(item) for item in collections or []][:limit]
    elif kind == "archive":
        media = client.call_feature(instagram, "archived", amount=limit)
        items = [media_item(item) for item in media or []][:limit]
    elif kind == "notifications":
        result = client.call_feature(instagram, "notifications", mark_as_seen=False)
        items = plain_list(_notification_items(result), limit)
    elif kind == "tray":
        items = _tray(instagram, settings)[:limit]
    elif kind == "guides":
        account = client.resolve_user_id(instagram, username, user_id, settings)
        guides = client.call_feature(instagram, "guides", user_id=account)
        items = plain_list(guides, limit)
    else:  # liked
        media = client.call_feature(instagram, "liked", amount=limit)
        items = [media_item(item) for item in media or []][:limit]

    wanted = {part.strip().lower() for part in str(include or "").split(",") if part.strip()}
    if "comments" in wanted and kind in MEDIA_KINDS | {"archive", "liked"}:
        _attach_comments(instagram, items)

    return {"ok": True, "kind": kind, "items": items, "next_cursor": next_cursor}


def ig_feed(
    kind: str = "posts",
    username: str | None = None,
    user_id: Any = None,
    cursor: str | None = None,
    limit: int = 12,
    include: str = "",
) -> dict[str, Any]:
    """Return one feed kind as a list of plain items."""
    try:
        kind = str(kind or "posts").strip().lower()
        if kind not in KINDS:
            raise ValueError(f"unknown kind: {kind!r}")
        limit = max(int(limit or 12), 1)

        cache = Cache()
        key = make_key(
            "ig_feed",
            {
                "kind": kind,
                "username": username,
                "user_id": user_id,
                "cursor": cursor,
                "limit": limit,
                "include": include,
            },
        )
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

        instagram, settings = client.open_client()
        result = _dispatch(
            instagram, settings, kind, username, user_id, cursor, limit, include
        )
        cache.set(key, result, ttl=DEFAULT_TTL)
        return result
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
