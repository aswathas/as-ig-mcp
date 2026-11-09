"""ig_write: the only tool that can change anything on the account."""

from __future__ import annotations

import json
from typing import Any

from . import writes

#: kind -> the mapping feature it selects.
WRITE_KINDS: dict[str, str] = {
    "send_message": "send_message",
    "send_media": "send_media",
    "send_voice": "send_voice",
    "send_file": "send_file",
    "react": "react",
    "unsend": "unsend",
    "mark_seen": "mark_seen",
    "share": "share",
    "publish": "publish_photo",
    "schedule": "publish_photo",
    "first_comment": "comment_reply",
    "comment": "comment_reply",
    "bulk_delete_comments": "comment_bulk_delete",
    "toggle_comments": "toggle_comments",
    "follow": "follow",
    "unfollow": "unfollow",
    "block": "block",
    "unblock": "unblock",
    "mute": "mute",
    "report": "report",
    "remove_follower": "remove_follower",
    "close_friend": "close_friend",
    "follow_hashtag": "hashtag_follow",
    "highlight": "highlight_create",
    "note": "note_create",
    "profile": "profile_edit",
    "category": "category",
    "ai_label": "ai_label",
    "crosspost": "crosspost",
    "collaborate": "collaborate",
    "thread_hide": "thread_hide",
    "thread_title": "thread_title",
    "thread_group_members": "thread_group_members",
    "follow_request_approve": "follow_request_approve",
    "follow_request_decline": "follow_request_decline",
    "download": "media_download",
}

#: Kinds that remove or destroy something; the tool declares destructiveHint.
DESTRUCTIVE_KINDS = frozenset(
    {"unfollow", "block", "unsend", "bulk_delete_comments", "remove_follower", "delete"}
)

_KIND_ARGUMENTS = """
send_message(user_ids/thread_ids, text) · send_media(user_ids/thread_ids, path) ·
send_voice(user_ids/thread_ids, path) · send_file(user_ids/thread_ids, path) ·
react(thread_id, message_id, emoji) · unsend(thread_id, message_id) ·
mark_seen(thread_id, message_id) · share(user_ids/thread_ids, media_id) ·
publish(path, caption) · schedule(path, caption, schedule_at) ·
first_comment(media_id, text) · comment(media_id, text[, replied_to_comment_id]) ·
bulk_delete_comments(media_id, comment_pks) · toggle_comments(media_id, enabled) ·
follow(user_id) · unfollow(user_id) · block(user_id) · unblock(user_id) ·
mute(user_id) · report(user_id) · remove_follower(user_id) · close_friend(user_id) ·
follow_hashtag(hashtag) · highlight(title, story_ids) · note(text) ·
profile(full_name/biography/external_url) · category(category) · ai_label(value) ·
crosspost(media_id, setting) · collaborate(path, coauthor_user_ids) ·
thread_hide(thread_id) · thread_title(thread_id, title) ·
thread_group_members(thread_id, user_ids) · follow_request_approve(user_id) ·
follow_request_decline(user_id) · download(media_id)
""".strip()

IG_WRITE_DESCRIPTION = (
    "[AS-IG-MCP] Write to Instagram. The account owner approves by clicking Yes in a dialog "
    "on their own screen; the agent cannot approve on their behalf. "
    "kind selects the action and the other arguments go to it.\n\n"
    f"{_KIND_ARGUMENTS}\n\n"
    "Pass idempotency_key to make a repeated call report already_done without a dialog or "
    "a second write. Unknown kinds return an error listing the valid kinds."
)


def _valid_kinds_error(kind: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": f"unknown kind: {kind!r}; valid kinds: {', '.join(WRITE_KINDS)}",
        "kinds": list(WRITE_KINDS),
    }


def _action_args(args: dict[str, Any]) -> dict[str, Any]:
    """Accept flat kwargs, or an ``args`` object from the MCP boundary."""
    values = dict(args)
    values.pop("confirm", None)
    nested = values.pop("args", None)
    if isinstance(nested, str):
        try:
            nested = json.loads(nested)
        except json.JSONDecodeError:
            nested = None
    if isinstance(nested, dict):
        merged = dict(nested)
        merged.update(values)
        return merged
    return values


def ig_write(
    kind: str,
    idempotency_key: str | None = None,
    **args: Any,
) -> dict[str, Any]:
    """Approve and perform one write. There is no confirmation code."""
    if not isinstance(kind, str):
        return _valid_kinds_error(str(kind))
    name = kind.strip().lower()
    feature = WRITE_KINDS.get(name)
    if feature is None:
        return _valid_kinds_error(name)
    try:
        return writes.perform_write(
            feature,
            _action_args(args),
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
