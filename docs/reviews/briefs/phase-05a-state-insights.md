# Phase 5a brief — SQLite state, the insights tool, relogin

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 4, 6, 7, 8),
`docs/reviews/capability-checklist.md`, `docs/reviews/loop.md`,
and the current `src/as_ig_mcp/{state,cache,session,client,mapping,server}.py`.

Three pieces: move the shared state into SQLite, build the `ig_insight` tool, and
give `ig_session` a working relogin.

## 1. SQLite state (replaces the loose JSON files)

The cache, the digest markers and the publish queue move into one SQLite file,
`%APPDATA%\as-ig-mcp\state.db`. `sqlite3` is in the standard library, so this
costs no dependency.

- `state.py`:
  - keep the existing path helpers (`cache_path`, `digest_path`, `queue_path`, and
    the rest) but point them at the new file, and add `db_path()`.
  - `ensure_app_dir()` stays.
  - keep `atomic_write_bytes` and `read_json`/`write_json` — other files still use
    them for the session and the audit journal.
  - add `connect()` returning a `sqlite3.Connection` with `journal_mode=WAL`,
    `timeout=10` (so a second process waits instead of failing), and
    `row_factory = sqlite3.Row`.
  - add `init_db()` creating the tables if they do not exist:
    `cache(key TEXT PRIMARY KEY, value TEXT, expires_at REAL)`,
    `digest(key TEXT PRIMARY KEY, value TEXT, updated_at REAL)`,
    `queue(id TEXT PRIMARY KEY, payload TEXT, scheduled_at REAL, state TEXT, idempotency_key TEXT, created_at REAL)`.
- `cache.py`: keep the same public API (`get`, `set`, `invalidate`,
  `invalidate_prefix`, `stats`, `make_key`) but back it with the `cache` table.
  - `set` writes one row (one key at a time), so two processes writing different
    keys cannot lose each other's entries.
  - `get` returns `None` for a missing or expired row and deletes the expired row.
  - `stats` returns total, live and expired counts.
  - `invalidate_prefix` deletes rows whose key starts with the prefix.
  - Wrap writes in a transaction and keep `timeout=10` so a concurrent writer
    waits rather than clobbering.
- `digest.py` (if it exists): same treatment on the `digest` table.
- A test that two `Cache` instances pointing at the same database see each
  other's writes, and that one process writing a key does not remove another
  process's key.

## 1b. Five promised write kinds have no mapping entry

`mapping.py` is missing entries for `igtv_upload` (IGTV), `quicksnap_send`
(disappearing photo), `cutout_sticker` (`photo_upload_to_cutout_sticker` /
`video_upload_to_cutout_sticker`), `mute_stories` (`mute_stories_from_follow`)
and `first_comment` (the same `media_comment` method with
`replied_to_comment_id` set). Add all five with `read_only: False`, each with
its instagrapi method name and a one-line summary. Look the method names up in
the installed source before using them.

## 2. `ig_insight`

`ig_insight(kind="media", media_pk=None, username=None, user_id=None, time_frame="ONE_WEEK", order_by="REACH_COUNT", limit=10)`

Kinds:

- `media` — one post's metrics. Needs `media_pk`, or the newest post of the
  account when `media_pk` is not given. Returns reach, impressions, likes,
  comments, saves, shares, profile views, follower gain, hashtag impressions, and
  where the impressions came from. Use the `post_insights` mapping feature
  (`insights_media`).
- `account` — the account units: profile visits, follower growth and breakdown,
  top posts, story count. Use `account_insights` (`insights_account`).
- `best` — Instagram's own ranked posts for the window, ordered by `order_by`.
  Use `best_posts` (`insights_media_feed_all`). `time_frame` is one of
  `ONE_WEEK`, `ONE_MONTH`, `THREE_MONTHS`, `SIX_MONTHS`, `ONE_YEAR`, `TWO_YEARS`.
  `order_by` is one of `REACH_COUNT`, `IMPRESSION_COUNT`, `PROFILE_VIEW`,
  `VIDEO_VIEW_COUNT`, `SAVE_COUNT`, `SHARE_COUNT`, `BIO_LINK_CLICK`, `FOLLOW`,
  `COMMENT_COUNT`, `LIKE_COUNT`.
- `best_time` — the posting-window recommendation computed from our own account
  insights: the hours and days on which our own posts got the most reach, per
  `time_frame`. It is a computation over `account_insights` and the per-post
  metrics — state the method in a `"method"` field.
- `compare` — our last `limit` posts ranked against each other by `order_by`,
  with a column of posts of similar age only. Never compare a fresh post with an
  old one; group by age band and say which band each row belongs to.
- `demographics` — follower age, gender and city/country when Instagram returns
  them. If a field is absent, return `null` and say why in `"notes"`. Never
  invent a number.

Every kind returns `{"ok": True, "kind": ..., "items"/"data": ..., "notes": ...}`.
No number is ever invented: a value Instagram did not return is `null`.

## 3. `ig_session` relogin, and a first-login flow for a stranger

- `ig_session(action="relogin")` — runs the Instagram login: it needs the
  account password, which the server never stores. So the flow is:
  `python -m as_ig_mcp session relogin` asks for the username and password on
  the terminal (use `getpass.getpass`, never an echo), logs in with instagrapi,
  and when Instagram sends a login code it prints "enter the code from the
  email or the app:" and waits for it, then saves the session through
  `session.save_session` and prints `{"ok": true, "username": ..., "user_id": ...}`.
  The MCP tool `ig_session action=relogin` returns a clear message pointing at
  that command, because the agent has no business typing a password.
- `python -m as_ig_mcp session login` — the same flow for a machine that has no
  session yet. This is how a stranger gets started.
- Handle the two-factor and email-code paths: instagrapi's `login` raises
  `TwoFactorRequired`; catch it, print the challenge choice, ask for the code,
  and call `login` again with the code. Keep it to one retry.
- Never print the password, never write the password to a file, never log it.
- `ig_session action=status` also reports whether the session was loaded from
  the password flow or imported from a file.

## 4. Tests

- `tests/test_state_db.py` — the schema is created; two connections to the same
  file see each other's rows; a write of one key does not remove another key;
  an expired cache row is not returned; `invalidate_prefix` removes only the
  matching keys; `stats` counts are right.
- `tests/test_tool_insight.py` — each kind dispatches to the right mapping
  feature; `best` passes `time_frame` and `order_by` through; `best_time`
  returns a `method` field; `demographics` returns `null` (not a number) when
  the payload has no demographics; `media` without a pk resolves the newest
  post of the account.
- `tests/test_session_login.py` — the login flow asks for the code when
  instagrapi raises `TwoFactorRequired` and completes with it; a wrong password
  returns an error; the password never appears in the captured output.

All tests use a temporary APPDATA and a fake Instagram client. No network.

## 5. Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 89. Print the pytest summary
line as your last output.

## 6. Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp` — tests use a temp APPDATA.
- Do not change the `instagrapi==3.2.8` pin.
- Do not run git write commands.
- If a method or a value you assumed exists does not, say so in your final message
  instead of working around it silently.
