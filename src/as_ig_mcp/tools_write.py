"""ig_write: the only tool that can change anything on the account."""

from __future__ import annotations

import json
from typing import Any

from . import tools_queue, writes

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
    "publish_photo": "publish_photo",
    "publish_video": "publish_video",
    "publish_reel": "publish_reel",
    "publish_album": "publish_album",
    "publish_story": "publish_story",
    "publish_story_music": "publish_story_music",
    "publish_story_video_music": "publish_story_video_music",
    "publish_igtv": "igtv_upload",
    "cutout_sticker": "cutout_sticker",
    "quicksnap": "quicksnap_send",
    "first_comment": "comment_reply",
    "comment": "comment_reply",
    "comment_pin": "comment_pin",
    "bulk_delete_comments": "comment_bulk_delete",
    "toggle_comments": "toggle_comments",
    "follow": "follow",
    "unfollow": "unfollow",
    "block": "block",
    "unblock": "unblock",
    "mute": "mute",
    "mute_stories": "mute_stories",
    "report": "report",
    "remove_follower": "remove_follower",
    "close_friend": "close_friend",
    "close_friend_remove": "close_friend_remove",
    "follow_hashtag": "hashtag_follow",
    "highlight": "highlight_create",
    "highlight_edit": "highlight_edit",
    "note": "note_create",
    "note_delete": "note_delete",
    "profile": "profile_edit",
    "category": "category",
    "ai_label": "ai_label",
    "crosspost": "crosspost",
    "collaborate": "collaborate",
    "thread_hide": "thread_hide",
    "thread_title": "thread_title",
    "thread_group_members": "thread_group_members",
    "approve_dm_request": "dm_request_approve",
    "follow_request_approve": "follow_request_approve",
    "follow_request_decline": "follow_request_decline",
    "download": "media_download",
    "save_media": "save_media",
    "delete_media": "media_delete",
    "delete_highlight": "highlight_delete",
}

#: Scheduling kinds are handled by the queue: `schedule` queues locally, and
#: `native_schedule` hands the upload to Instagram's own scheduler.
QUEUE_WRITE_KINDS: dict[str, str] = {
    "schedule": "schedule",
    "native_schedule": "native",
}

#: Kinds that remove or destroy something; the tool declares destructiveHint.
DESTRUCTIVE_KINDS = frozenset(
    {
        "unfollow",
        "block",
        "unsend",
        "bulk_delete_comments",
        "remove_follower",
        "delete",
        "delete_media",
        "delete_highlight",
        "note_delete",
    }
)

_KIND_ARGUMENTS = """
send_message(user_ids/thread_ids, text) · send_media(user_ids/thread_ids, path) ·
send_voice(user_ids/thread_ids, path) · send_file(user_ids/thread_ids, path) ·
react(thread_id, message_id, emoji) · unsend(thread_id, message_id) ·
mark_seen(thread_id, message_id) · share(user_ids/thread_ids, media_id) ·
publish(path, caption) · publish_photo(path, caption) ·
publish_video(path, caption[, thumbnail]) · publish_reel(path, caption[, thumbnail]) ·
publish_album(paths, caption) · publish_story(path, caption) ·
publish_story_music(path, caption, track) ·
publish_story_video_music(path, caption, track) · publish_igtv(path, caption) ·
cutout_sticker(path) · quicksnap(path, user_ids) ·
schedule(path, caption, when, recurrence[, media_kind]) ·
native_schedule(path, caption, schedule_at[, media_kind]) ·
first_comment(media_id, text) · comment(media_id, text[, replied_to_comment_id]) ·
comment_pin(media_id, comment_pk[, revert]) ·
bulk_delete_comments(media_id, comment_pks) · toggle_comments(media_id, enabled) ·
follow(user_id) · unfollow(user_id) · block(user_id) · unblock(user_id) ·
mute(user_id) · mute_stories(user_id) · report(user_id) · remove_follower(user_id) ·
close_friend(user_id) · close_friend_remove(user_id) ·
follow_hashtag(hashtag) · highlight(title, story_ids) · highlight_edit(highlight_pk, title) ·
delete_highlight(highlight_id) · save_media(media_id) ·
note(text) · note_delete(note_id) · profile(full_name/biography/external_url) · category(category) ·
ai_label(value) · crosspost(media_id, setting) · collaborate(path, coauthor_user_ids) ·
thread_hide(thread_id) · thread_title(thread_id, title) ·
thread_group_members(thread_id, user_ids) · follow_request_approve(user_id) ·
follow_request_decline(user_id) · approve_dm_request(thread_id) ·
download(media_id) · delete_media(media_id)
""".strip()

IG_WRITE_DESCRIPTION = (
    "[AS-IG-MCP] Write to Instagram. The account owner approves by clicking Yes in a dialog "
    "on their own screen; the agent cannot approve on their behalf. "
    "kind selects the action and the other arguments go to it.\n\n"
    f"{_KIND_ARGUMENTS}\n\n"
    "Pass idempotency_key to make a repeated call report already_done without a dialog or "
    "a second write. Unknown kinds return an error listing the valid kinds."
)


def _all_kinds() -> list[str]:
    return list(WRITE_KINDS) + list(QUEUE_WRITE_KINDS)


def _valid_kinds_error(kind: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": f"unknown kind: {kind!r}; valid kinds: {', '.join(_all_kinds())}",
        "kinds": _all_kinds(),
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


def _first_value(values: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = values.get(key)
        if value not in (None, ""):
            return value
    return None


def _queue_write(
    name: str,
    values: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    action = QUEUE_WRITE_KINDS[name]
    media_kind = _first_value(
        values, ("media_kind", "media_type", "publish_kind", "upload_kind")
    ) or "photo"
    media_path = _first_value(values, ("media_path", "path", "file", "file_path"))
    caption = _first_value(values, ("caption", "text"))
    key = idempotency_key or _first_value(values, ("idempotency_key",))
    common = {
        "action": action,
        "kind": media_kind,
        "media_path": media_path,
        "caption": caption,
        "idempotency_key": key,
    }
    if action == "schedule":
        return tools_queue.ig_queue(
            **common,
            when=_first_value(values, ("when", "schedule_at")),
            recurrence=_first_value(values, ("recurrence",)) or "none",
        )
    return tools_queue.ig_queue(
        **common,
        schedule_at=_first_value(values, ("schedule_at", "when")),
    )


def ig_write(
    kind: str,
    idempotency_key: str | None = None,
    **args: Any,
) -> dict[str, Any]:
    """Approve and perform one write. There is no confirmation code."""
    if not isinstance(kind, str):
        return _valid_kinds_error(str(kind))
    name = kind.strip().lower()
    if name in QUEUE_WRITE_KINDS:
        try:
            return _queue_write(name, _action_args(args), idempotency_key)
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    feature = WRITE_KINDS.get(name)
    if feature is None:
        return _valid_kinds_error(name)
    action_args = _action_args(args)
    if (
        feature == "highlight_delete"
        and "highlight_pk" not in action_args
        and "highlight_id" in action_args
    ):
        action_args["highlight_pk"] = action_args.pop("highlight_id")
    try:
        return writes.perform_write(
            feature,
            action_args,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
