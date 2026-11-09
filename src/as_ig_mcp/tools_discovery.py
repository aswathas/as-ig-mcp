"""ig_search: users, hashtags, places, music, posts, DMs and accounts."""

from __future__ import annotations

import os
from typing import Any

from . import client
from .cache import DEFAULT_TTL, Cache, make_key
from .serialize import plain, plain_list
from .session import settings_identity

KINDS = {"user", "hashtag", "place", "music", "post", "message", "account"}

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "user_search",
    "hashtag_info",
    "place_search",
    "location_search",
    "music_search",
    "top_search",
    "dm_search",
)

PLACE_ENV_ERROR = "place search needs IG_PLACES_LAT and IG_PLACES_LNG"


class PlaceCoordinatesMissing(Exception):
    """Raised when place search is used without configured coordinates."""


def _items(result: Any) -> list[Any]:
    if result is None:
        return []
    if isinstance(result, (list, tuple)):
        return list(result)
    return [result]


def _user_item(user: Any) -> dict[str, Any]:
    pk = client.field_value(user, "pk")
    return {
        "username": client.field_value(user, "username"),
        "full_name": client.field_value(user, "full_name"),
        "pk": str(pk) if pk is not None else None,
        "followers": client.field_value(user, "follower_count"),
    }


def _hashtag_item(tag: Any) -> dict[str, Any]:
    tag_id = client.field_value(tag, "id")
    return {
        "name": client.field_value(tag, "name"),
        "media_count": client.field_value(tag, "media_count"),
        "id": str(tag_id) if tag_id is not None else None,
    }


def _place_item(place: Any) -> dict[str, Any]:
    pk = client.field_value(place, "pk")
    if pk is None:
        pk = client.field_value(place, "id")
    return {
        "name": client.field_value(place, "name"),
        "id": str(pk) if pk is not None else None,
        "lat": client.field_value(place, "lat"),
        "lng": client.field_value(place, "lng"),
    }


def _music_item(track: Any) -> dict[str, Any]:
    artist = client.field_value(track, "display_artist") or client.field_value(
        track, "subtitle"
    )
    return {
        "title": client.field_value(track, "title"),
        "artist": artist,
        "id": client.field_value(track, "id"),
    }


def _message_item(pair: Any) -> dict[str, Any]:
    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
        message, thread = pair[0], pair[1]
    elif isinstance(pair, dict):
        message = pair.get("message") or pair
        thread = pair.get("thread") or {}
    else:
        message, thread = pair, {}

    thread_id = client.field_value(thread, "id")
    users = client.field_value(thread, "users") or []
    return {
        "thread_id": str(thread_id) if thread_id is not None else None,
        "snippet": client.field_value(message, "text"),
        "participants": [
            client.field_value(user, "username") for user in users
        ],
    }


def _coordinates() -> tuple[float, float] | None:
    lat = os.environ.get("IG_PLACES_LAT")
    lng = os.environ.get("IG_PLACES_LNG")
    if lat is None or lng is None or lat == "" or lng == "":
        return None
    return float(lat), float(lng)


def _place_search(instagram: Any, query: str, lat: float, lng: float) -> list[Any]:
    try:
        places = client.call_feature(
            instagram, "place_search", query=query, lat=lat, lng=lng
        )
    except Exception:
        places = []
    if places:
        return list(places)
    return list(
        client.call_feature(instagram, "location_search", lat=lat, lng=lng) or []
    )


def _dispatch(instagram: Any, settings: dict[str, Any], kind: str, query: str, limit: int) -> list[Any]:
    if kind in {"user", "account"}:
        if kind == "account" and not query:
            query = settings_identity(settings)["username"] or ""
            if not query:
                raise ValueError("the session has no username; pass query")
        users = _items(client.call_feature(instagram, "user_search", query=query))
        if kind == "account":
            exact = [
                user
                for user in users
                if str(client.field_value(user, "username")).lower() == query.lower()
            ]
            users = exact or users[:1]
        return [_user_item(user) for user in users][:limit]

    if kind == "hashtag":
        tag = client.call_feature(instagram, "hashtag_info", name=query)
        return [_hashtag_item(tag)] if tag is not None else []

    if kind == "place":
        coordinates = _coordinates()
        if coordinates is None:
            raise PlaceCoordinatesMissing(PLACE_ENV_ERROR)
        lat, lng = coordinates
        places = _place_search(instagram, query, lat, lng)
        return [_place_item(place) for place in places][:limit]

    if kind == "music":
        tracks = client.call_feature(instagram, "music_search", query=query)
        return [_music_item(track) for track in _items(tracks)][:limit]

    if kind == "post":
        result = client.call_feature(instagram, "top_search", query=query)
        flattened = plain(result)
        posts = flattened if isinstance(flattened, list) else [flattened]
        return posts[:limit]

    # message
    results = client.call_feature(instagram, "dm_search", query=query)
    return [_message_item(pair) for pair in _items(results)][:limit]


def ig_search(kind: str = "user", query: str = "", limit: int = 20) -> dict[str, Any]:
    """Search one Instagram surface and return plain items."""
    try:
        kind = str(kind or "user").strip().lower()
        if kind not in KINDS:
            raise ValueError(f"unknown kind: {kind!r}")
        query = str(query or "").strip()
        limit = max(int(limit or 20), 1)

        if kind == "place" and _coordinates() is None:
            return {"ok": False, "error": PLACE_ENV_ERROR}

        instagram, settings = client.open_client()
        if kind == "account" and not query:
            query = settings_identity(settings)["username"] or ""
            if not query:
                raise ValueError("the session has no username; pass query")

        cache = Cache()
        key = make_key("ig_search", {"kind": kind, "query": query, "limit": limit})
        cached = cache.get(key)
        if isinstance(cached, dict):
            return cached

        items = _dispatch(instagram, settings, kind, query, limit)
        payload = {"ok": True, "kind": kind, "query": query, "items": items}
        cache.set(key, payload, ttl=DEFAULT_TTL)
        return payload
    except PlaceCoordinatesMissing as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
