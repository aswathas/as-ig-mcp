# Phase 2b brief — reads can never mutate (safety fix)

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/reviews/briefs/phase-02-server-health.md` (what Phase 2 built),
`src/as_ig_mcp/mapping.py`, `src/as_ig_mcp/client.py`, `src/as_ig_mcp/tools_health.py`,
`src/as_ig_mcp/tools_status.py`.

**Why this brief exists.** The mapping table listed instagrapi's
`notification_likes`, `notification_comments`, `notification_new_follower` and
`notification_user_tagged` as notification *readers*. They are not. Their
signature is `setting_value: SETTING_VALUE = "off"` and they POST to
`notifications/change_notification_settings/`. A live health probe called one of
them and turned that notification category off on the real account. The account
was repaired by setting the four categories back to `"everyone"`. That must never
happen again, so this phase makes it structurally impossible for a read to
mutate anything.

## Changes

### 1. `mapping.py` — every feature declares whether it reads or writes

- Add a `read_only: bool` field to every entry in `FEATURE_METHODS`.
- `read_only=True` for methods that only fetch.
- `read_only=False` for every method that changes something. The list of
  mutators to mark false (check each one in the installed instagrapi source
  before you decide, do not guess):

```
user_follow user_unfollow user_block user_unblock user_report user_remove_follower
mute_posts_from_follow mute_stories_from_follow
close_friend_add close_friend_remove
hashtag_follow hashtag_unfollow
direct_send direct_send_photo direct_send_video direct_send_voice direct_send_file
direct_send_reaction direct_delete_reaction direct_message_delete direct_message_unsend
direct_message_seen direct_send_seen direct_indicate_activity
direct_thread_create direct_thread_add_users direct_thread_remove_users
direct_thread_update_title direct_thread_hide direct_thread_mute direct_thread_unmute
direct_thread_mark_unread direct_thread_mark_read direct_thread_mute_video_call
direct_thread_unmute_video_call direct_pending_approve direct_request_approve
direct_thread_create
photo_upload photo_configure video_upload video_configure clip_upload clip_configure
album_upload album_configure igtv_upload igtv_configure
photo_upload_to_story photo_upload_to_story_with_music video_upload_to_story
photo_upload_to_cutout_sticker video_upload_to_cutout_sticker
photo_configure_to_story photo_configure_to_cutout_sticker
media_comment comment_like comment_unlike comment_pin comment_unpin
comment_bulk_delete media_note_create media_note_delete create_note delete_note
highlight_create highlight_edit highlight_change_title highlight_change_cover
highlight_add_stories highlight_remove_stories highlight_delete
account_edit account_set_biography account_set_private account_set_public
account_change_picture account_set_ai_info account_convert_to_professional
account_convert_to_business account_convert_to_creator
set_external_url remove_bio_links media_save media_unsave
notification_settings notification_likes notification_comments notification_new_follower
notification_user_tagged notification_disable notification_mute_all
media_share_to_threads_config media_share_to_fb_unified_config
```

- **Replace the notifications feature.** The `notifications` feature must map to
  `news_inbox_v1` (an actual reader: `private_request("news/inbox/")`, returns old
  and new stories). Set `transport="rest"`, `read_only=True`, and a summary that
  says it is the activity feed. The four `notification_*` mutators must not be
  reachable through any read feature — you may keep them in the table with
  `read_only=False`, but no read path may select them.
- Add a helper `MUTATING_FEATURES` (a frozenset of feature names whose method is
  in the mutator list) so the guard does not depend on a hand-maintained list of
  feature names.
- `FEATURES_BY_AREA` must still cover every feature exactly once.

### 2. `client.py` — the guard

- `call_feature(cl, feature, allow_write=False, **kwargs)`:
  - look the feature up in the mapping;
  - if the entry is not `read_only` and `allow_write` is False → raise
    `WriteNotAllowedError` (define it in `client.py`, subclass of `Exception`)
    with a message naming the feature and the method;
  - otherwise call the method, with the existing one-shot fallback behaviour
    unchanged;
  - the fallback must also refuse a non-read-only fallback when `allow_write` is
    False.
- Add `call_write(cl, feature, **kwargs)` that calls `call_feature` with
  `allow_write=True`. Only the write tool module will use it.
- `WriteNotAllowedError` must be importable from `as_ig_mcp.client`.

### 3. `tools_health.py` — only readers

- The health probe must only use features whose mapping entry is `read_only=True`.
  Add a guard in the probe itself: before calling, assert the feature is
  read-only, and if it is not, mark that class `dead` with the reason
  `"feature is a write"`.
- Replace the `notifications` class probe with the `news_inbox_v1` feature
  (the mapping change already does this, so the probe code may stay as it is).

### 4. `tools_status.py` — no invented numbers

- `ig_status` currently promises a quota. instagrapi has no quota endpoint, so
  report `"quota": "unknown - instagrapi exposes no quota endpoint"` instead of
  a number. Never print a number we did not read.

### 5. Cache correctness (small, do it now)

- `cache.py`: add `Cache.invalidate_prefix(prefix)` and make sure a write path
  can clear the affected keys. The write tool module lands in a later phase, so
  just add the method and a test.

## Tests

`tests/test_mapping.py` (extend)
- every entry has a `read_only` key that is a bool;
- `MUTATING_FEATURES` matches the entries whose method is in the mutator list;
- the `notifications` feature maps to `news_inbox_v1` and is read-only;
- no read-only feature maps to a method from the mutator list.

`tests/test_client.py` (extend)
- calling a read-only feature works;
- calling a mutating feature without `allow_write` raises `WriteNotAllowedError`
  and the underlying method is never called (use a fake client that records calls);
- `call_write` on a mutating feature does call it;
- a mutating feature with a fallback still refuses without `allow_write`.

`tests/test_server_smoke.py` (extend)
- the health tool, when run with a session present in a temp APPDATA, returns
  `dead` for any class whose feature is not read-only — assert that no mutating
  method was called on the fake client.

`tests/test_cache.py` (extend)
- `invalidate_prefix` removes only the matching keys.

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, and the count is higher than 22. Print the
pytest summary line as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp`.
- Do not change the `instagrapi==3.2.8` pin.
- Do not run git write commands.
- When you decide whether a method reads or writes, read the installed source at
  `C:\Users\aswat\Downloads\Projects\whatsapp-mcp-venv\Lib\site-packages\instagrapi\mixins\`
  and say in your final message which methods you had to look up. If a method's
  name is ambiguous, mark it `read_only=False` — the safe default.
