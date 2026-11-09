# Phase 3a brief — the core read tools

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 8),
`docs/reviews/capability-checklist.md`, `src/as_ig_mcp/{mapping,client,cache,session,tools_health,server}.py`.

Build four read tools: `ig_person`, `ig_people`, `ig_search`, `ig_feed`.
No writes. No realtime. No DM threads yet (that is phase 3b).

## New shared helpers — put them in `src/as_ig_mcp/serialize.py`

- `plain(obj)` — turn instagrapi objects into JSON-serialisable data.
  - pydantic models (instagrapi `types.py`): `model_dump()`.
  - `datetime`: `isoformat()`.
  - `list` / `tuple`: map over them.
  - `dict`: map over the values.
  - anything else: `str(obj)`.
- `plain_list(items, limit=None)` — `plain` over a list, truncated to `limit`.

## `src/as_ig_mcp/tools_people.py` — `ig_person` and `ig_people`

`ig_person(username=None, user_id=None, include="")`

- Resolve the account: if `user_id` is given use it; if only `username` is given, resolve it
  through the `user_search` feature (or `user_info_by_username`) and take the id.
  If neither is given, use the logged-in account.
- Return `{"ok": True, "user_id": ..., "username": ..., "profile": {...}, "includes": {...}}`.
- `profile` holds: full name, biography, follower count, following count, media count,
  is_private, is_business, external url, category, pk.
- `include` is a comma-separated list. Support: `followers`, `following`, `posts`,
  `stories`, `highlights`, `comments`, `suggestions`, `about`. Each present key holds a
  list (or dict for `about`). Unknown names are ignored, not an error.
- `comments` means the comments on the account's newest media.
- Cap every list at 50 items unless the caller asks for more.

`ig_people(username=None, user_id=None, kind="followers", cursor=None, limit=50)`

- `kind` is one of `followers`, `following`, `suggested`, `requests`.
- `requests` returns the follow requests (empty list is a valid answer).
- `cursor` is passed to the underlying pagination when the method supports it; when the
  method does not, return the first page and say `"cursor_supported": false`.
- Return `{"ok": True, "kind": ..., "items": [...], "next_cursor": ..., "cursor_supported": bool}`.
- Each item: username, full name, pk, is_private, followed_by_me when known.

## `src/as_ig_mcp/tools_discovery.py` — `ig_search`

`ig_search(kind="user", query="", limit=20)`

- `kind` is one of `user`, `hashtag`, `place`, `music`, `post`, `message`, `account`.
- `user` → the `user_search` feature; return users with username, full name, pk, followers.
- `hashtag` → the `hashtag_info` feature; return name, media count, id.
- `place` → the `place_search` feature, falling back to `location_search`; return name, id, lat, lng.
  If the account has no coordinates configured, return
  `{"ok": False, "error": "place search needs IG_PLACES_LAT and IG_PLACES_LNG"}`.
- `music` → the `music_search` feature; return title, artist, id.
- `post` → the `top_search` feature; return whatever it gives, flattened to plain data.
- `message` → the `dm_search` feature; return thread id, snippet, participants.
- `account` → the `user_search` feature, but treat the query as our own handle and return
  the profile summary.
- Return `{"ok": True, "kind": ..., "query": ..., "items": [...]}`.

## `src/as_ig_mcp/tools_feed.py` — `ig_feed`

`ig_feed(kind="posts", username=None, user_id=None, cursor=None, limit=12, include="")`

- `kind` is one of `posts`, `reels`, `tagged`, `saved`, `archive`, `notifications`,
  `collections`, `tray`, `guides`, `liked`.
- `posts` / `reels` / `tagged` → the account's media, filtered to photo or video when
  the kind says so. `tagged` uses the tagged-media method.
- `saved` → the saved collections; each item is a collection with its name, id and media count.
- `archive` → the archived media.
- `notifications` → the `news_inbox_v1` feature; return the activity items flattened.
- `collections` → the collection list with media counts.
- `tray` → the stories tray: the accounts we follow that have active stories, and for each
  one its story pks. Use the following list plus the per-user stories feature. Keep it to
  the first 10 accounts.
- `guides` → the guides of the account, when the method exists; an empty list is a valid answer.
- `liked` → the media we liked.
- `include="comments"` adds the comments of the newest five media items.
- Return `{"ok": True, "kind": ..., "items": [...], "next_cursor": ...}`.
- Each media item: pk, media type, taken at, caption (truncated to 300 characters),
  like count, comment count, permalink, thumbnail url, owner username.

## Mapping additions

Add the read-only features these tools need, if they are not there yet. Look the method
name up in the installed source at
`C:\Users\aswat\Downloads\Projects\whatsapp-mcp-venv\Lib\site-packages\instagrapi\mixins\`
before you use it, and set `read_only` correctly. Candidates:

- `user_search` → `search_users`
- `tagged` → the tagged-media method in `media.py` or `user.py` (find its real name)
- `saved_collections` → `collections`
- `saved_media` → `collection_medias`
- `liked` → `liked_medias`
- `archived` → the archived-media method
- `top_search` → `fbsearch_topsearch_v2`
- `notes` → `get_notes` (already mapped)

If a method you need does not exist in this instagrapi version, do not invent it: return an
empty list with a `"reason"` key saying the endpoint is unavailable, and list it in your
final message.

## Wiring

- Register the four tools in `server.py` with descriptions that start with `[AS-IG-MCP]`
  and one line each.
- Every tool takes the same shape: keyword arguments with sensible defaults, returns a dict,
  never raises. On error return `{"ok": False, "error": "<type>: <message>"}`.
- Every tool must go through `client.call_feature` so the read-only guard applies.
- Reads go through the cache: use `cache.make_key(feature, params)` and the 90 second TTL.
  `ig_feed`, `ig_people` and `ig_search` are cacheable. `ig_person` caches the profile only.

## Tests

- `tests/test_serialize.py` — pydantic model, datetime, list, dict, nested, and a plain
  string all come out JSON-serialisable.
- `tests/test_tools_people.py` — with a fake client: `ig_person` resolves a username,
  returns a profile, and honours `include`; `ig_people` returns each kind; an unknown
  kind returns an error rather than raising.
- `tests/test_tools_discovery.py` — each `kind` dispatches to the right feature; the
  `place` kind without coordinates returns the documented error.
- `tests/test_tools_feed.py` — each `kind` dispatches to the right feature; unknown kind
  errors; media items are flattened to plain dicts.
- `tests/test_read_tools_are_read_only.py` — collect every feature name that the four
  tools can dispatch to, and assert each one is `read_only: True` in the mapping. This
  test is the safety net: it fails if anyone wires a mutator into a read tool.

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 33. Print the pytest summary line
as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp`.
- Do not add a write path. Everything here reads.
- Do not change the `instagrapi==3.2.8` pin.
- Do not run git write commands.
- If you find that a method you assumed exists does not, say so in your final message
  instead of working around it silently.
