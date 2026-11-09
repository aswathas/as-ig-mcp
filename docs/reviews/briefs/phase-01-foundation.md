# Phase 1 brief — foundation

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 4, 6 and 9) and
`docs/reviews/capability-checklist.md`.

Build **only** the foundation. No tools yet. No Instagram calls.

## What to create

```
pyproject.toml
.venv/                       (create it, do not commit it)
src/as_ig_mcp/__init__.py
src/as_ig_mcp/state.py
src/as_ig_mcp/session.py
src/as_ig_mcp/client.py
src/as_ig_mcp/mapping.py
tests/test_session.py
tests/test_client.py
tests/test_mapping.py
```

## `pyproject.toml`

- name `as-ig-mcp`, version `0.1.0`, requires-python `>=3.11`, MIT licence.
- dependencies: `instagrapi==3.2.8`, `mcp`, `pycryptodomex`.
- build backend: setuptools with `src` layout, package `as_ig_mcp`.
- Add `*.enc`, `.venv/`, `__pycache__/`, `*.pyc` to `.gitignore`.

## `state.py`

- `APP_DIR = %APPDATA%/as-ig-mcp` (use `os.environ["APPDATA"]`, fall back to `~/.as-ig-mcp`).
- Path constants: `session_path()`, `cache_path()`, `digest_path()`, `events_path()`,
  `audit_path()`, `queue_path()`, `presets_path()`.
- `ensure_app_dir()` — create the directory if missing.
- `atomic_write_bytes(path, data)` — write to a temp file in the same directory, then
  `os.replace` it over the target. Must be safe to call from two processes.
- `read_json(path, default=None)` and `write_json(path, obj)` built on the atomic write.
- No printing of secrets.

## `session.py`

- `encrypt_bytes(data: bytes, entropy: bytes = b"as-ig-mcp") -> bytes` and
  `decrypt_bytes(blob: bytes, entropy: bytes = b"as-ig-mcp") -> bytes` using Windows DPAPI
  through `ctypes` (`CryptProtectData` / `CryptUnprotectData`, `CRYPTPROTECT_LOCAL_MACHINE` NOT
  set — bind to the current user). Implement the `DATA_BLOB` struct correctly and free the
  memory that `LocalFree` expects.
- `save_session(settings: dict) -> None` — JSON-encode the settings, encrypt, write atomically to
  `session_path()`.
- `load_session() -> dict | None` — decrypt and JSON-decode, return `None` when the file is
  missing, and raise a clear `SessionError` when decryption fails (wrong Windows user, corrupt file).
- `clear_session() -> None` — delete the file if it exists.
- `SessionError(Exception)`.

## `client.py`

- `build_client(settings: dict)` — return `instagrapi.Client` with `load_settings` applied from the
  given dict. Use `Client(settings=...)` or `set_settings`; do NOT call `load_settings(path)` with
  `override_app_version=True` — the app profile must stay as it was at login.
- `ensure_dtsg(cl)` — call `cl.fetch_fb_dtsg()` once and cache the result on the client object
  (attribute `_asig_dtsg`). Return the token. Raise a clear error if it comes back None.
- `call_feature(cl, feature: str, **kwargs)` — look the feature up in `mapping.FEATURE_METHODS`,
  call the method, and on `ClientGraphqlError` / `ClientJSONDecodeError` / `ClientError` retry once
  with the fallback method listed for that feature (if any), then re-raise.
- `ClientError` handling must not swallow errors: re-raise the original error type.

## `mapping.py`

- `FEATURE_METHODS: dict[str, dict]` — one entry per feature, each with:
  - `method`: the instagrapi method name (string),
  - `fallback`: an optional second method name,
  - `transport`: `"rest"` or `"graphql"`,
  - `summary`: one line saying what it does.
- Cover **every** feature in this list, using exactly these instagrapi method names:
  profile→`user_info_v1`; followers→`user_followers_v1`; following→`user_following_v1`;
  posts→`user_medias_v1` (fallback `user_medias_gql`); best_posts→`insights_media_feed_all`;
  post_insights→`insights_media`; account_insights→`insights_account`; stories→`user_stories_web`;
  thread_list→`direct_threads`; business_dm_box→`direct_threads`; thread_messages→`direct_messages`;
  dm_search→`direct_message_search`; presence→`direct_active_presence`; send_message→`direct_send`;
  send_media→`direct_send_photo`; send_voice→`direct_send_voice`; send_file→`direct_send_file`;
  react→`direct_send_reaction`; unsend→`direct_message_unsend`; publish_photo→`photo_upload`;
  publish_video→`video_upload`; publish_reel→`clip_upload`; publish_album→`album_upload`;
  publish_story→`photo_upload_to_story`; comments→`media_comments`; comment_reply→`media_comment`;
  comment_bulk_delete→`comment_bulk_delete`; comment_pin→`comment_pin`; notifications→`notification_likes`;
  notes→`get_notes`; note_create→`create_note`; hashtag_info→`hashtag_info`;
  hashtag_top→`hashtag_medias_top`; hashtag_recent→`hashtag_medias_recent`; hashtag_follow→`hashtag_follow`;
  place_search→`fbsearch_places`; location_search→`location_search`; music_search→`search_music`;
  top_search→`fbsearch_topsearch_v2`; user_search→`search_users`; suggestions→`user_suggested_profiles`;
  highlights→`user_highlights_v1`; highlight_create→`highlight_create`; highlight_edit→`highlight_edit`;
  follow→`user_follow`; unfollow→`user_unfollow`; block→`user_block`; mute→`mute_posts_from_follow`;
  close_friend→`close_friend_add`; crosspost→`media_share_to_threads_config`;
  profile_edit→`account_edit`; category→`account_convert_to_professional`; ai_label→`account_set_ai_info`;
  media_download→`photo_download`; save_media→`media_save`.
- `FEATURE_METHODS` must be ordered by capability area and each entry must carry the `summary` line.
- Add `FEATURES_BY_AREA: dict[str, list[str]]` grouping the features into
  `profile`, `dm`, `publish`, `comments`, `stories`, `discovery`, `insights`, `account`, `media`.

## Tests (offline, no network, no Instagram)

`tests/test_session.py`
- encrypt then decrypt round trip returns the original bytes;
- decrypting a corrupted blob raises `SessionError`;
- `save_session` then `load_session` round trip (point `APPDATA` at a temp directory via monkeypatch
  of the environment variable, and make `state.py` read the env var at call time so the patch works);
- `clear_session` removes the file.

`tests/test_mapping.py`
- every feature in the required list exists in `FEATURE_METHODS`;
- every entry has `method`, `transport` in `{"rest","graphql"}` and a non-empty `summary`;
- every feature appears in exactly one `FEATURES_BY_AREA` group, and every group key is known;
- every `method` string exists as an attribute on `instagrapi.Client` (check with
  `hasattr(Client, name)`; `insights_media_feed_all` and the rest are mixin methods, so check
  `hasattr` on the class, not an instance).

`tests/test_client.py`
- `call_feature` dispatches to the mapped method on a fake client object and returns its result;
- when the primary method raises `ClientError`, the fallback is used;
- when the primary and the fallback both fail, the original error type is re-raised;
- `ensure_dtsg` caches the token and calls `fetch_fb_dtsg` once.

## Environment

- Create the venv with the system Python (3.14): `python -m venv .venv`
- Install: `.venv/Scripts/python.exe -m pip install instagrapi==3.2.8 mcp pycryptodomex pytest`
- Install the package in editable mode: `.venv/Scripts/python.exe -m pip install -e .`

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls. Then print the pytest summary line as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call.
- Do not create any file that holds a real session, password or token.
- Do not run `git commit`, `git add`, or any git write command — the orchestrator commits.
- Do not write to `C:\Users\aswat\AppData\Roaming\as-ig-mcp` with real data; tests must use a
  temporary directory.
- If instagrapi 3.2.8 does not install on Python 3.14, say so plainly in your final message and
  report the exact error, instead of silently downgrading the pin.
