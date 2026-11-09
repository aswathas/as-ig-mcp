# Phase 3b brief — DM threads, inbox, stories, account

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 8),
`docs/reviews/capability-checklist.md`, and the code Phase 3a built
(`src/as_ig_mcp/{tools_people,tools_discovery,tools_feed,serialize,client,mapping,cache}.py`).

Build four read tools: `ig_thread`, `ig_inbox`, `ig_story`, `ig_account`.
No writes. No realtime socket yet. The write gate is not in this phase — `ig_thread`
must not mutate anything here.

## `src/as_ig_mcp/tools_threads.py` — `ig_thread`

`ig_thread(thread_id, cursor=None, limit=20)`

- Return `{"ok": True, "thread_id": ..., "participants": [...], "messages": [...], "presence": {...}, "next_cursor": ...}`.
- `participants`: username, full name, pk, is_private for each participant.
- `messages`: id, sender id, username, timestamp, text, item type, whether it is ours.
  `text` may be empty when the message carries only media — say `"text": ""` and
  include `"has_media": true` rather than inventing text.
- `presence`: the online/last-active state for the other participants, when the
  underlying call returns it. If it cannot be read, return `null`, not a guess.
- `cursor`: pass it to the underlying pagination and return `next_cursor`.
- The thread must be resolved from the id; if the id is unknown, return
  `{"ok": False, "error": "thread not found: <id>"}`.
- **Do not mark anything as seen.** `mark_seen` is a write and belongs to `ig_write`.

## `src/as_ig_mcp/tools_inbox.py` — `ig_inbox`

`ig_inbox(hours=48, limit=10, suggest=False, thread_id=None)`

- Lists the threads that are waiting for a reply: the last message in each thread
  is not ours, and it arrived within `hours`.
- When `thread_id` is given, return that one thread instead of the list — the
  spec's cross-check compares `ig_inbox`'s last message with `ig_thread`'s.
- Each item: thread id, the other participant's username, last message text,
  last message time, unread flag, message count.
- `suggest=True` adds a `suggested_reply` string. It comes from the style file
  `%APPDATA%\as-ig-mcp\style.json` (an object keyed by username, each value
  holding `relationship`, `language`, `formality`, `personality_notes`,
  `topics`, `response_style`). When no style entry exists, return a neutral
  one-line template and set `"suggested_source": "default template"` so the
  caller can tell.
- The suggested reply must never contain a link, a phone number or an email
  address, and must be at most two sentences. Add a test for that.

## `src/as_ig_mcp/tools_story.py` — `ig_story`

`ig_story(story_id=None, highlight_id=None, action="info")`

- `action` is one of `info`, `viewers`, `likers`, `download`.
- `info`: the story's pk, owner, taken at, media url, and whether we have seen it.
- `viewers`: who saw it. Empty list is a valid answer.
- `likers`: who liked it.
- `download`: writes the story media into `%APPDATA%\as-ig-mcp\media\` and
  returns the local path. Nothing outside that folder.
- Without `story_id` or `highlight_id`, return an error naming what is missing.
- A highlight id resolves to its stories.

## `src/as_ig_mcp/tools_account.py` — `ig_account`

`ig_account()`

- Return `{"ok": True, "account": {...}, "insights": {...}, "linked_accounts": [...]}`.
- `account`: username, full name, pk, follower count, following count, media
  count, biography, category, is_business, is_private, external url, and the
  professional-account settings that can be read.
- `insights`: the account-level insights — profile visits, follower growth,
  top posts, stories count — read through the `account_insights` feature.
- `linked_accounts`: the accounts Instagram's own switcher lists for this login
  (the `featured_accounts_v1` and `get_account_family_v1` features). Each
  item: pk, username, full name. Say plainly when the list is empty.
- **No number may be invented.** If a value is not returned by Instagram, use
  `null` and say why in a `"notes"` field.

## Wiring

- Register the four tools in `server.py` with descriptions that start with
  `[AS-IG-MCP]` and one line each.
- Every tool returns a dict and never raises: on error return
  `{"ok": False, "error": "<type>: <message>"}`.
- Every tool goes through `client.call_feature`, so the read-only guard applies.
- Reads go through the cache where the result is stable: a thread's message list
  and a story's info may be cached for 90 seconds; presence and viewers must
  not be cached.

## Mapping additions

Add any read-only feature these tools need, if it is missing. Look the method
name up in the installed source at
`C:\Users\aswat\Downloads\Projects\whatsapp-mcp-venv\Lib\site-packages\instagrapi\mixins\`
before using it, and set `read_only` correctly. Likely candidates:
`thread_detail` → `direct_thread`, `thread_messages` → `direct_messages`,
`pending_requests` → `direct_pending_inbox`, `spam_inbox` → `direct_spam_inbox`,
`group_threads` → a group thread listing, `story_info` → `story_info`,
`story_viewers` → `story_viewers`, `story_likers` → `story_likers`,
`story_download` → `story_download`, `account_insights` → `insights_account`,
`linked_accounts` → `featured_accounts_v1`, `account_family` → `get_account_family_v1`.

If a method does not exist in this instagrapi version, do not invent it: return an empty
result with a `"reason"` key, and list it in your final message.

## Tests

- `tests/test_tools_threads.py` — thread resolves, messages come back with ids and
  timestamps, an unknown thread id returns an error, and **no call marks anything seen**
  (assert the fake client recorded no `direct_message_seen` call).
- `tests/test_tools_inbox.py` — a thread whose last message is ours is not listed as
  awaiting a reply; `thread_id` returns exactly that thread; the suggested reply is at
  most two sentences and contains no link, phone number or email address.
- `tests/test_tools_story.py` — each action dispatches to the right feature; a missing
  id returns a clear error; the download path stays inside the media folder.
- `tests/test_tools_account.py` — the account block, the insights block and the linked
  account list are all present; a missing value is `null` with a note, never a number.
- `tests/test_read_tools_are_read_only.py` (extend) — every feature the four new tools
  can dispatch to is `read_only: True`.

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 59. Print the pytest summary line
as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp`.
- Do not add a write path, and do not mark threads as seen.
- Do not change the `instagrapi==3.2.8` pin.
- Do not run git write commands.
- If a method you assumed exists does not, say so in your final message.
