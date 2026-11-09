"""ig_insight: media, account, best, best-time, compare and demographics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from . import client
from .serialize import plain

KINDS = ("media", "account", "best", "best_time", "compare", "demographics")

TIME_FRAMES = (
    "ONE_WEEK",
    "ONE_MONTH",
    "THREE_MONTHS",
    "SIX_MONTHS",
    "ONE_YEAR",
    "TWO_YEARS",
)

ORDER_BY = (
    "REACH_COUNT",
    "IMPRESSION_COUNT",
    "PROFILE_VIEW",
    "VIDEO_VIEW_COUNT",
    "SAVE_COUNT",
    "SHARE_COUNT",
    "BIO_LINK_CLICK",
    "FOLLOW",
    "COMMENT_COUNT",
    "LIKE_COUNT",
)

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = ("post_insights", "account_insights", "best_posts", "posts")

_FRAME_DAYS = {
    "ONE_WEEK": 7,
    "ONE_MONTH": 30,
    "THREE_MONTHS": 90,
    "SIX_MONTHS": 180,
    "ONE_YEAR": 365,
    "TWO_YEARS": 730,
}

_MEDIA_METRICS: dict[str, tuple[str, ...]] = {
    "reach": ("reach", "reach_count", "total_reach"),
    "impressions": ("impressions", "impression_count", "impressions_count", "total_impressions"),
    "likes": ("likes", "like_count", "likes_count", "total_likes"),
    "comments": ("comments", "comment_count", "comments_count", "total_comments"),
    "saves": ("saves", "save_count", "saves_count", "total_saves"),
    "shares": ("shares", "share_count", "shares_count", "total_shares"),
    "profile_views": (
        "profile_views",
        "profile_view",
        "profile_view_count",
        "profile_visits",
        "profile_visits_count",
    ),
    "follower_gain": (
        "follower_gain",
        "followers_gained",
        "new_followers",
        "follows",
        "follow_count",
    ),
    "hashtag_impressions": (
        "hashtag_impressions",
        "hashtag_impression_count",
        "hashtag_impressions_count",
    ),
}

_ORDER_METRIC = {
    "REACH_COUNT": "reach",
    "IMPRESSION_COUNT": "impressions",
    "PROFILE_VIEW": "profile_views",
    "VIDEO_VIEW_COUNT": "video_views",
    "SAVE_COUNT": "saves",
    "SHARE_COUNT": "shares",
    "BIO_LINK_CLICK": "bio_link_clicks",
    "FOLLOW": "follows",
    "COMMENT_COUNT": "comments",
    "LIKE_COUNT": "likes",
}

_ORDER_CANDIDATES = {
    "video_views": ("video_views", "video_view_count", "video_views_count"),
    "bio_link_clicks": ("bio_link_clicks", "bio_link_click", "bio_link_click_count"),
    "follows": ("follows", "follow_count", "new_followers"),
}

_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

_BANDS = ("0-7d", "8-30d", "31-90d", "91-180d", "181-365d", "365d+", "unknown")


def _pairs(node: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key), value
            if isinstance(value, (dict, list, tuple)):
                yield from _pairs(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _pairs(item)


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        for key in ("value", "count", "total", "amount"):
            if key in value:
                found = _number(value[key])
                if found is not None:
                    return found
    return None


def _metric(payload: Any, candidates: Iterable[str]) -> int | float | None:
    names = {name.lower() for name in candidates}
    for key, value in _pairs(payload):
        if key.lower() in names:
            found = _number(value)
            if found is not None:
                return found
    return None


def _value(payload: Any, names: Iterable[str]) -> Any:
    wanted = {name.lower() for name in names}
    for key, value in _pairs(payload):
        if key.lower() in wanted:
            return plain(value)
    return None


def _missing(payload: Any, fields: dict[str, Any], source: str) -> list[str]:
    notes = []
    for name, value in fields.items():
        if value is None:
            notes.append(f"{name} was not returned by Instagram ({source})")
    return notes


def _taken_at_epoch(post: Any) -> float | None:
    value = client.field_value(post, "taken_at")
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return None


def _age_days(post: Any, now: float) -> float | None:
    epoch = _taken_at_epoch(post)
    if epoch is None:
        return None
    return max((now - epoch) / 86400.0, 0.0)


def _band(days: float | None) -> str:
    if days is None:
        return "unknown"
    if days <= 7:
        return "0-7d"
    if days <= 30:
        return "8-30d"
    if days <= 90:
        return "31-90d"
    if days <= 180:
        return "91-180d"
    if days <= 365:
        return "181-365d"
    return "365d+"


def _resolve_media_pk(
    instagram: Any,
    media_pk: Any,
    username: str | None,
    user_id: Any,
    settings: dict[str, Any],
) -> str:
    if media_pk not in (None, ""):
        return str(media_pk)
    target = client.resolve_user_id(instagram, username, user_id, settings)
    posts, _cursor = client.split_page(
        client.call_feature(instagram, "posts", user_id=target, amount=1)
    )
    if not posts:
        raise ValueError("the account has no posts to measure")
    pk = client.field_value(posts[0], "pk")
    if pk is None:
        raise ValueError("the newest post has no pk")
    return str(pk)


def _media_data(instagram: Any, pk: str) -> dict[str, Any]:
    raw = client.call_feature(instagram, "post_insights", media_pk=pk)
    fields = {
        name: _metric(raw, candidates) for name, candidates in _MEDIA_METRICS.items()
    }
    impressions_source = _value(
        raw, ("impressions_source", "impression_sources", "impressions_breakdown")
    )
    data: dict[str, Any] = {"media_pk": pk, **fields, "impressions_source": impressions_source}
    notes = _missing(raw, fields, "insights_media")
    if impressions_source is None:
        notes.append("impressions_source was not returned by Instagram (insights_media)")
    return {"data": data, "notes": notes}


def _account_data(instagram: Any) -> dict[str, Any]:
    raw = client.call_feature(instagram, "account_insights")
    fields = {
        "profile_visits": _metric(
            raw, ("profile_visits", "profile_views", "profile_view_count", "profile_visits_count")
        ),
        "follower_growth": _metric(
            raw, ("follower_growth", "followers_gained", "new_followers", "follows", "follow_count")
        ),
        "story_count": _metric(raw, ("stories_count", "story_count", "stories")),
        "top_posts": _value(raw, ("top_posts", "top_posts_unit")),
        "follower_breakdown": _value(
            raw,
            (
                "follower_breakdown",
                "followers_breakdown",
                "follower_demographics",
                "audience_breakdown",
            ),
        ),
    }
    notes = _missing(raw, fields, "insights_account")
    return {"data": fields, "notes": notes}


def _best(instagram: Any, time_frame: str, order_by: str, limit: int) -> dict[str, Any]:
    raw = client.call_feature(
        instagram,
        "best_posts",
        time_frame=time_frame,
        data_ordering=order_by,
        count=max(limit, 0),
    )
    items = [plain(item) for item in (raw or [])]
    if limit:
        items = items[:limit]
    notes = [] if items else ["Instagram returned no ranked posts for this window."]
    return {
        "items": items,
        "time_frame": time_frame,
        "order_by": order_by,
        "notes": notes,
    }


def _best_time(
    instagram: Any,
    user_id: str,
    time_frame: str,
    limit: int,
) -> dict[str, Any]:
    notes: list[str] = []
    account_raw: Any = None
    try:
        account_raw = client.call_feature(instagram, "account_insights")
    except Exception as exc:  # account insights are supporting data, not required
        notes.append(f"account_insights unavailable: {type(exc).__name__}")

    posts, _cursor = client.split_page(
        client.call_feature(instagram, "posts", user_id=user_id, amount=max(limit, 12) * 5)
    )
    cutoff = datetime.now().timestamp() - _FRAME_DAYS[time_frame] * 86400
    by_window: dict[tuple[int, int], dict[str, float]] = {}
    by_day: dict[int, dict[str, float]] = {}
    by_hour: dict[int, dict[str, float]] = {}
    measured = 0

    for post in posts:
        epoch = _taken_at_epoch(post)
        if epoch is None or epoch < cutoff:
            continue
        pk = client.field_value(post, "pk")
        if pk is None:
            continue
        try:
            raw = client.call_feature(instagram, "post_insights", media_pk=str(pk))
        except Exception:
            continue
        reach = _metric(raw, _MEDIA_METRICS["reach"])
        if reach is None:
            continue
        moment = datetime.fromtimestamp(epoch)
        key = (moment.weekday(), moment.hour)
        measured += 1
        for bucket, index in (
            (by_window, key),
            (by_day, moment.weekday()),
            (by_hour, moment.hour),
        ):
            entry = bucket.setdefault(index, {"posts": 0, "total_reach": 0.0})
            entry["posts"] += 1
            entry["total_reach"] += float(reach)

    def rows(source: dict, name: str) -> list[dict[str, Any]]:
        result = []
        for key, entry in source.items():
            count = int(entry["posts"])
            total = entry["total_reach"]
            row = {
                name: _WEEKDAYS[key] if name == "weekday" else key,
                "posts": count,
                "total_reach": total,
                "average_reach": round(total / count, 2) if count else None,
            }
            if name == "weekday":
                row["weekday_index"] = key
            result.append(row)
        result.sort(key=lambda row: (row["total_reach"], row["posts"]), reverse=True)
        return result[:limit]

    items = []
    for (weekday, hour), entry in by_window.items():
        count = int(entry["posts"])
        total = entry["total_reach"]
        items.append(
            {
                "weekday": _WEEKDAYS[weekday],
                "weekday_index": weekday,
                "hour": hour,
                "posts": count,
                "total_reach": total,
                "average_reach": round(total / count, 2) if count else None,
            }
        )
    items.sort(key=lambda row: (row["total_reach"], row["posts"]), reverse=True)

    if not measured:
        notes.append(
            "no per-post reach was returned for posts inside this time frame, "
            "so no best window can be computed"
        )

    return {
        "items": items[:limit],
        "best_days": rows(by_day, "weekday"),
        "best_hours": rows(by_hour, "hour"),
        "posts_measured": measured,
        "time_frame": time_frame,
        "method": (
            "summed reach from insights_media for our own posts inside time_frame, "
            "bucketed by the post's taken_at weekday (Monday=0) and local hour; "
            "account_insights supplies the account context, never a guessed number"
        ),
        "account": plain(account_raw) if isinstance(account_raw, dict) else None,
        "notes": notes,
    }


def _compare(
    instagram: Any,
    user_id: str,
    order_by: str,
    limit: int,
) -> dict[str, Any]:
    notes: list[str] = []
    metric = _ORDER_METRIC[order_by]
    candidates = _ORDER_CANDIDATES.get(metric, _MEDIA_METRICS.get(metric, (metric,)))
    posts, _cursor = client.split_page(
        client.call_feature(instagram, "posts", user_id=user_id, amount=max(limit, 1))
    )
    now = datetime.now().timestamp()
    rows: list[dict[str, Any]] = []

    for post in posts:
        pk = client.field_value(post, "pk")
        if pk is None:
            continue
        try:
            raw = client.call_feature(instagram, "post_insights", media_pk=str(pk))
        except Exception as exc:
            notes.append(f"insights unavailable for post {pk}: {type(exc).__name__}")
            value = None
        else:
            value = _metric(raw, candidates)
        days = _age_days(post, now)
        rows.append(
            {
                "media_pk": str(pk),
                "taken_at": plain(client.field_value(post, "taken_at")),
                "age_days": round(days, 1) if days is not None else None,
                "age_band": _band(days),
                "metric": metric,
                "value": value,
            }
        )

    # Rank only against posts of similar age: never a fresh post against an old one.
    for band in _BANDS:
        band_rows = [row for row in rows if row["age_band"] == band]
        band_rows.sort(
            key=lambda row: (row["value"] is not None, row["value"] or 0),
            reverse=True,
        )
        for index, row in enumerate(band_rows, start=1):
            row["rank_in_band"] = index
    rows.sort(
        key=lambda row: (
            _BANDS.index(row["age_band"]),
            row["rank_in_band"],
        )
    )
    if not rows:
        notes.append("the account has no posts to compare")
    return {
        "items": rows,
        "order_by": order_by,
        "compared_by_age_band": True,
        "bands": _BANDS,
        "notes": notes,
    }


def _demographics(instagram: Any) -> dict[str, Any]:
    raw = client.call_feature(instagram, "account_insights")
    fields = {
        "age": _value(raw, ("age", "age_range", "age_buckets", "audience_age")),
        "gender": _value(raw, ("gender", "gender_split", "audience_gender")),
        "city": _value(raw, ("city", "cities", "top_cities", "audience_city")),
        "country": _value(raw, ("country", "countries", "top_countries", "audience_country")),
    }
    notes = _missing(raw, fields, "insights_account")
    if all(value is None for value in fields.values()):
        notes.append(
            "Instagram returned no audience demographics; this needs a business or "
            "creator account with enough followers for audience data"
        )
    return {"data": fields, "notes": notes}


def ig_insight(
    kind: str = "media",
    media_pk: Any = None,
    username: str | None = None,
    user_id: Any = None,
    time_frame: str = "ONE_WEEK",
    order_by: str = "REACH_COUNT",
    limit: int = 10,
) -> dict[str, Any]:
    """Measure one post, the account, Instagram's ranking or our own history."""
    name = str(kind or "media").strip().lower()
    if name not in KINDS:
        return {
            "ok": False,
            "kind": name,
            "error": f"unknown kind: {name!r}; valid kinds: {', '.join(KINDS)}",
        }
    if name in ("best", "best_time"):
        if time_frame not in TIME_FRAMES:
            return {
                "ok": False,
                "kind": name,
                "error": f"unknown time_frame: {time_frame!r}; valid: {', '.join(TIME_FRAMES)}",
            }
    if name in ("best", "compare"):
        if order_by not in ORDER_BY:
            return {
                "ok": False,
                "kind": name,
                "error": f"unknown order_by: {order_by!r}; valid: {', '.join(ORDER_BY)}",
            }

    try:
        limit = max(int(limit), 0)
    except (TypeError, ValueError):
        limit = 10

    try:
        instagram, settings = client.open_client()
        if name == "media":
            pk = _resolve_media_pk(instagram, media_pk, username, user_id, settings)
            body = _media_data(instagram, pk)
        elif name == "account":
            body = _account_data(instagram)
        elif name == "best":
            body = _best(instagram, time_frame, order_by, limit)
        elif name == "best_time":
            target = client.resolve_user_id(instagram, username, user_id, settings)
            body = _best_time(instagram, target, time_frame, limit)
        elif name == "compare":
            target = client.resolve_user_id(instagram, username, user_id, settings)
            body = _compare(instagram, target, order_by, limit)
        else:
            body = _demographics(instagram)
    except Exception as exc:
        return {"ok": False, "kind": name, "error": f"{type(exc).__name__}: {exc}"}

    result: dict[str, Any] = {"ok": True, "kind": name}
    result.update(body)
    result.setdefault("notes", [])
    return result
