# Phase 2 brief — server, status, health, session import

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 4, 6, 9),
`docs/reviews/capability-checklist.md`, and the existing `src/as_ig_mcp/` code from Phase 1.

Build the runnable server skeleton with three tools, the cache layer, and a way to
import the session we already have. No read tools yet, no writes yet.

## What to create or change

```
src/as_ig_mcp/__init__.py     (export the public names)
src/as_ig_mcp/server.py       (new)
src/as_ig_mcp/cache.py        (new)
src/as_ig_mcp/cli.py          (new)
src/as_ig_mcp/tools_status.py (new)
src/as_ig_mcp/tools_health.py (new)
src/as_ig_mcp/tools_session.py(new)
tests/test_cache.py           (new)
tests/test_server_smoke.py    (new)
```

## `cache.py`

- `Cache` class over a JSON file (`state.cache_path()`), entries `{key: {"value":..., "expires_at": <epoch>}}`.
- `get(key)` — returns the value when present and unexpired, else `None`; expired entries are dropped on read.
- `set(key, value, ttl=90)` — writes atomically through `state.atomic_write_bytes`.
- `invalidate(key=None)` — remove one key, or clear everything when `key` is `None`.
- `stats()` — total keys, live keys, expired keys.
- Keys are namespaced by feature: `"{feature}:{param_hash}"`. Provide `make_key(feature, params)`.
- Must be safe when two processes write the same file: catch `json.JSONDecodeError` and
  treat a corrupt cache file as empty rather than raising.

## `tools_status.py`

`ig_status()` returns a dict with:
- `session`: `{"present": bool, "username": str|None, "user_id": str|None, "source": "file"|"none"}`
- `account`: when a session is present, `username`, `user_id`, `followers`, `following`, `media_count`,
  `is_business` — read through the mapping table (`profile` feature), and cached for 90 seconds.
  When no session is present, return `None` for `account` and say why.
- `cache`: the `stats()` output.
- `realtime`: `{"enabled": False, "state": "not implemented in v1 phase 2"}`.
- `health`: a one-line summary, e.g. `"unknown"` until `ig_health` has run, then the last summary
  the health module computed.
- `version`: the package version.

Never raise out of this tool: if the profile read fails, return the error text inside the dict.

## `tools_health.py`

`ig_health()` probes one representative call per capability class and reports each as
`live` or `dead` with the reason. Use `client.call_feature` with these features and arguments:

| class | feature | arguments |
|---|---|---|
| profile | `profile` | the session's own user id |
| followers | `followers` | own user id |
| posts | `posts` | own user id |
| insights_media | `post_insights` | the newest own media pk, or `None` if unknown |
| account_insights | `account_insights` | none |
| dm_threads | `thread_list` | none |
| dm_presence | `presence` | none |
| notifications | `notifications` | none |
| discovery | `hashtag_info` | `"chennai"` |
| business_dm_box | `business_dm_box` | none |

- When no session is present, every class is `dead` with the reason `"no session"`.
- Never let one failing probe abort the rest: catch per probe.
- Return `{"classes": {...}, "summary": "n/m live", "checked_at": <epoch>}`.
- Store the last summary in memory so `ig_status` can show it.

## `tools_session.py`

`ig_session(action)`:
- `status` — session presence, username, user id, cache stats, whether the token can be fetched.
- `cache_clear` — clears the cache, returns what it cleared.
- `export` — returns the session settings as JSON with the cookie values **redacted**
  (`sessionid` and `csrftoken` replaced by `"<redacted>"`).
- `relogin` — for this phase return `{"ok": False, "error": "relogin lands in phase 5"}`.
  Do not attempt a login.

## `server.py`

- A stdio MCP server using the `mcp` Python package (FastMCP is fine):
  `FastMCP("as-ig")`, tools registered with `@mcp.tool()`, run with `mcp.run()`.
- Register exactly three tools for this phase: `ig_status`, `ig_health`, `ig_session`.
- Every tool description starts with the literal text `[AS-IG-MCP]` and one line saying what the
  tool is for. Keep descriptions under 400 characters.
- `ig_session` takes one parameter `action` with default `status`.
- Tool results are plain JSON-serialisable dicts. Catch every exception inside the tool and return
  `{"ok": False, "error": "<type>: <message>"}` instead of raising.
- The server must not print anything to stdout except what the MCP transport writes.

## `cli.py`

`python -m as_ig_mcp <command>`:
- `session import <path-to-settings.json>` — read a settings JSON file, validate it has a
  `cookies` dict with a `sessionid`, then save it through `session.save_session` (DPAPI encrypted).
  Print `{"ok": true, "username": ..., "user_id": ...}`.
- `session status` — same as the tool.
- `health` — runs the health probe and prints it.
- `status` — same as the tool.
- Add `__main__.py` so `python -m as_ig_mcp` works.

## Tests

`tests/test_cache.py`
- set then get returns the value; after the TTL it returns `None`;
- `stats()` counts live and expired;
- `invalidate` removes one key and the clear-all path works;
- a corrupt cache file is treated as empty, not an exception;
- two different keys do not collide.

`tests/test_server_smoke.py`
- Spawn the server as a subprocess using the same stdio JSON-RPC handshake Claude Code uses:
  send `initialize`, then `notifications/initialized`, then `tools/list`.
- Assert the tool list contains `ig_status`, `ig_health`, `ig_session`, and that each description
  starts with `[AS-IG-MCP]`.
- Call `ig_status` and assert it returns a dict with the keys `session`, `account`, `cache`,
  `realtime`, `health`, `version`.
- The smoke test must not need a session: point `%APPDATA%` at a temp directory for the child
  process so `ig_status` reports "no session" instead of touching the real one.
- Kill the child process at the end of the test.

## Environment

- `.venv` already exists at the project root. Use `.venv/Scripts/python.exe`.
- Install anything new with `.venv/Scripts/python.exe -m pip install <pkg>`.

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass (the 13 existing ones plus the new ones), zero network calls.
Then print the pytest summary line as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp`.
- Do not create any file that holds a real session, password or token.
- Do not run git write commands — the orchestrator commits.
- Keep `instagrapi==3.2.8` pinned. If something does not fit that version, report it, do not
  downgrade the pin.
