"""ig_person and ig_people: profiles and relationship lists."""

from __future__ import annotations

from typing import Any

from . import client
from .cache import DEFAULT_TTL, Cache, make_key
from .serialize import plain, plain_list
from .tools_feed import media_item

PEOPLE_KINDS = {"followers", "following", "suggested", "requests"}

#: Every feature these tools can dispatch to. The read-only test checks this set.
FEATURES = (
    "user_by_username",
    "profile",
    "followers_page",
    "following_page",
    "requests_page",
    "suggestions",
    "posts_page",
    "stories",
    "highlights",
    "comments",
    "about",
)

SUPPORTED_INCLUDES = {
    "followers",
    "following",
    "posts",
    "stories",
    "highlights",
    "comments",
    "suggestions",
    "about",
}


def _pk(value: Any) -> str | None:
    return str(value) if value is not None else None


def person_item(user: Any) -> dict[str, Any]:
    """Flatten one follower, following or suggested account."""
    friendship = client.field_value(user, "friendship_status")
    return {
        "username": client.field_value(user, "username"),
        "full_name": client.field_value(user, "full_name"),
        "pk": _pk(client.field_value(user, "pk")),
        "is_private": client.field_value(user, "is_private"),
        "followed_by_me": client.field_value(friendship, "following"),
    }


def _profile(user: Any) -> dict[str, Any]:
    category = (
        client.field_value(user, "category")
        or client.field_value(user, "category_name")
        or client.field_value(user, "business_category_name")
    )
    return {
        "pk": _pk(client.field_value(user, "pk")),
        "username": client.field_value(user, "username"),
        "full_name": client.field_value(user, "full_name"),
        "biography": client.field_value(user, "biography"),
        "follower_count": client.field_value(user, "follower_count"),
        "following_count": client.field_value(user, "following_count"),
        "media_count": client.field_value(user, "media_count"),
        "is_private": client.field_value(user, "is_private"),
        "is_business": client.field_value(user, "is_business"),
        "external_url": plain(client.field_value(user, "external_url")),
        "category": category,
    }


def _suggested_users(result: Any) -> list[Any]:
    if isinstance(result, dict):
        for key in ("users", "items"):
            value = result.get(key)
            if isinstance(value, list):
                return value
        return []
    return list(result or [])


def _includes(instagram: Any, user_id: str, include: str, limit: int) -> dict[str, Any]:
    wanted = {part.strip().lower() for part in str(include or "").split(",") if part.strip()}
    wanted &= SUPPORTED_INCLUDES
    includes: dict[str, Any] = {}

    if "followers" in wanted:
        users, _ = client.split_page(
            client.call_feature(instagram, "followers_page", user_id=user_id, max_amount=limit)
        )
        includes["followers"] = [person_item(user) for user in users][:limit]

    if "following" in wanted:
        users, _ = client.split_page(
            client.call_feature(instagram, "following_page", user_id=user_id, max_amount=limit)
        )
        includes["following"] = [person_item(user) for user in users][:limit]

    if "posts" in wanted:
        media, _ = client.split_page(
            client.call_feature(instagram, "posts_page", user_id=user_id, amount=limit)
        )
        includes["posts"] = [media_item(item) for item in media][:limit]

    if "stories" in wanted:
        stories = client.call_feature(instagram, "stories", user_id=user_id)
        includes["stories"] = plain_list(stories, limit)

    if "highlights" in wanted:
        highlights = client.call_feature(instagram, "highlights", user_id=user_id)
        includes["highlights"] = plain_list(highlights, limit)

    if "comments" in wanted:
        media, _ = client.split_page(
            client.call_feature(instagram, "posts_page", user_id=user_id, amount=1)
        )
        if media:
            media_pk = client.field_value(media[0], "pk")
            comments = client.call_feature(
                instagram, "comments", media_id=media_pk, amount=limit
            )
            includes["comments"] = plain_list(comments, limit)
        else:
            includes["comments"] = []

    if "suggestions" in wanted:
        result = client.call_feature(instagram, "suggestions", user_id=user_id)
        includes["suggestions"] = [
            person_item(user) for user in _suggested_users(result)
        ][:limit]

    if "about" in wanted:
        includes["about"] = plain(
            client.call_feature(instagram, "about", user_id=user_id)
        )

    return includes


def ig_person(
    username: str | None = None,
    user_id: Any = None,
    include: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Return one account's profile, with optional relationship and media lists."""
    try:
        limit = max(int(limit or 50), 1)
        instagram, settings = client.open_client()
        account = client.resolve_user_id(instagram, username, user_id, settings)

        cache = Cache()
        key = make_key("ig_person", {"user_id": account})
        profile = cache.get(key)
        if not isinstance(profile, dict):
            user = client.call_feature(instagram, "profile", user_id=account)
            profile = _profile(user)
            cache.set(key, profile, ttl=DEFAULT_TTL)

        return {
            "ok": True,
            "user_id": account,
            "username": profile.get("username")
            or (username.lstrip("@") if username else None),
            "profile": profile,
            "includes": _includes(instagram, account, include, limit),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def ig_people(
    username: str | None = None,
    user_id: Any = None,
    kind: str = "followers",
    cursor: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return one page of followers, following, suggestions or follow requests."""
    try:
        kind = str(kind or "followers").strip().lower()
        if kind not in PEOPLE_KINDS:
            raise ValueError(f"unknown kind: {kind!r}")
        limit = max(int(limit or 50), 1)

        cache = Cache()
        key = make_key(
            "ig_people",
            {
                "username": username,
                "user_id": user_id,
                "kind": kind,
                "cursor": cursor,
                "limit": limit,
            },
        )
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

        instagram, settings = client.open_client()
        next_cursor = None
        cursor_supported = True

        if kind == "followers":
            account = client.resolve_user_id(instagram, username, user_id, settings)
            result = client.call_feature(
                instagram,
                "followers_page",
                user_id=account,
                max_amount=limit,
                max_id=cursor or "",
            )
            users, next_cursor = client.split_page(result)
        elif kind == "following":
            account = client.resolve_user_id(instagram, username, user_id, settings)
            result = client.call_feature(
                instagram,
                "following_page",
                user_id=account,
                max_amount=limit,
                max_id=cursor or "",
            )
            users, next_cursor = client.split_page(result)
        elif kind == "requests":
            result = client.call_feature(
                instagram, "requests_page", max_amount=limit, max_id=cursor or ""
            )
            users, next_cursor = client.split_page(result)
        else:  # suggested
            account = client.resolve_user_id(instagram, username, user_id, settings)
            result = client.call_feature(instagram, "suggestions", user_id=account)
            users, next_cursor = _suggested_users(result), None
            cursor_supported = False

        payload = {
            "ok": True,
            "kind": kind,
            "items": [person_item(user) for user in users][:limit],
            "next_cursor": next_cursor,
            "cursor_supported": cursor_supported,
        }
        cache.set(key, payload, ttl=DEFAULT_TTL)
        return payload
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
