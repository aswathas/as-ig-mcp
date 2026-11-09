"""ig_account: profile metrics, insights, and linked switcher accounts."""

from __future__ import annotations

from typing import Any

from . import client, session
from .serialize import plain

#: Every feature this tool can dispatch to. The read-only test checks this set.
FEATURES = (
    "profile",
    "account_info",
    "account_insights",
    "linked_accounts",
    "account_family",
)


def _extract_account_block(
    instagram: Any, own_id: str, settings: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    raw_user = None
    account_notes: dict[str, str] = {}

    if own_id:
        try:
            raw_user = client.call_feature(instagram, "profile", user_id=own_id)
        except Exception:
            pass

    if raw_user is None:
        try:
            raw_user = client.call_feature(instagram, "account_info")
        except Exception:
            pass

    username = client.field_value(raw_user, "username") or session.settings_identity(settings).get("username")
    full_name = client.field_value(raw_user, "full_name")
    pk = client.field_value(raw_user, "pk") or own_id
    follower_count = client.field_value(raw_user, "follower_count")
    following_count = client.field_value(raw_user, "following_count")
    media_count = client.field_value(raw_user, "media_count")
    biography = client.field_value(raw_user, "biography")
    category = client.field_value(raw_user, "category") or client.field_value(raw_user, "category_name")
    is_business = client.field_value(raw_user, "is_business")
    is_private = client.field_value(raw_user, "is_private")
    external_url = client.field_value(raw_user, "external_url")

    # Record notes for unreturned fields
    for field_name, val in [
        ("follower_count", follower_count),
        ("following_count", following_count),
        ("media_count", media_count),
        ("category", category),
        ("biography", biography),
        ("external_url", external_url),
    ]:
        if val is None:
            account_notes[field_name] = f"{field_name} was not returned by Instagram API"

    professional_settings: dict[str, Any] = {}
    for attr in (
        "account_type",
        "business_category_name",
        "business_contact_method",
        "public_email",
        "public_phone_number",
        "contact_phone_number",
        "show_text_post_app_badge",
    ):
        v = client.field_value(raw_user, attr)
        if v is not None:
            professional_settings[attr] = v

    account_data = {
        "username": username,
        "full_name": full_name,
        "pk": str(pk) if pk is not None else None,
        "follower_count": follower_count,
        "following_count": following_count,
        "media_count": media_count,
        "biography": biography,
        "category": category,
        "is_business": is_business,
        "is_private": is_private,
        "external_url": external_url,
        "professional_settings": professional_settings or None,
        "notes": account_notes,
    }
    return account_data, account_notes


def _extract_insights_block(instagram: Any) -> tuple[dict[str, Any], dict[str, str]]:
    insights_notes: dict[str, str] = {}
    try:
        raw_insights = client.call_feature(instagram, "account_insights")
    except Exception as exc:
        raw_insights = None
        insights_notes["insights"] = f"account_insights unavailable: {type(exc).__name__}"

    profile_visits = None
    follower_growth = None
    top_posts = None
    stories_count = None

    if isinstance(raw_insights, dict):
        profile_visits = (
            raw_insights.get("profile_visits")
            or raw_insights.get("profile_views")
            or raw_insights.get("account_summary_unit")
        )
        follower_growth = (
            raw_insights.get("follower_growth")
            or raw_insights.get("followers_unit")
        )
        top_posts = (
            raw_insights.get("top_posts")
            or raw_insights.get("top_posts_unit")
        )
        stories_count = (
            raw_insights.get("stories_count")
            or raw_insights.get("stories_unit")
        )

    for field_name, val in [
        ("profile_visits", profile_visits),
        ("follower_growth", follower_growth),
        ("top_posts", top_posts),
        ("stories_count", stories_count),
    ]:
        if val is None and field_name not in insights_notes:
            insights_notes[field_name] = f"{field_name} was not returned by Instagram API"

    insights_data = {
        "profile_visits": plain(profile_visits),
        "follower_growth": plain(follower_growth),
        "top_posts": plain(top_posts),
        "stories_count": plain(stories_count),
        "notes": insights_notes,
    }
    return insights_data, insights_notes


def _extract_linked_accounts(
    instagram: Any, own_id: str
) -> tuple[list[dict[str, Any]], str]:
    linked: list[dict[str, Any]] = []

    # Try featured_accounts_v1
    if own_id:
        try:
            res = client.call_feature(instagram, "linked_accounts", target_user_id=own_id)
            accounts = []
            if isinstance(res, dict):
                accounts = res.get("accounts") or res.get("featured_accounts") or []
            elif isinstance(res, list):
                accounts = res
            for acc in accounts:
                pk = client.field_value(acc, "pk")
                if pk:
                    linked.append(
                        {
                            "pk": str(pk),
                            "username": client.field_value(acc, "username"),
                            "full_name": client.field_value(acc, "full_name"),
                        }
                    )
        except Exception:
            pass

    # Try get_account_family_v1
    if not linked:
        try:
            res = client.call_feature(instagram, "account_family")
            accounts = []
            if isinstance(res, dict):
                accounts = (
                    res.get("accounts")
                    or res.get("child_accounts")
                    or res.get("family", {}).get("accounts")
                    or []
                )
                if not accounts and res.get("main_account"):
                    accounts = [res["main_account"]]
            elif isinstance(res, list):
                accounts = res
            for acc in accounts:
                pk = client.field_value(acc, "pk")
                if pk:
                    linked.append(
                        {
                            "pk": str(pk),
                            "username": client.field_value(acc, "username"),
                            "full_name": client.field_value(acc, "full_name"),
                        }
                    )
        except Exception:
            pass

    if not linked:
        note = "No linked accounts found for this login."
    else:
        note = f"{len(linked)} linked account(s) found."

    return linked, note


def ig_account() -> dict[str, Any]:
    """Return account profile, metrics, insights and linked accounts."""
    try:
        instagram, settings = client.open_client()
        identity = session.settings_identity(settings or {})
        own_id = str(identity.get("user_id") or "")

        account_block, account_notes = _extract_account_block(instagram, own_id, settings)
        insights_block, insights_notes = _extract_insights_block(instagram)
        linked_accounts, linked_note = _extract_linked_accounts(instagram, own_id)

        all_notes: dict[str, Any] = {
            "account": account_notes,
            "insights": insights_notes,
            "linked_accounts": linked_note,
        }

        return {
            "ok": True,
            "account": account_block,
            "insights": insights_block,
            "linked_accounts": linked_accounts,
            "notes": all_notes,
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
