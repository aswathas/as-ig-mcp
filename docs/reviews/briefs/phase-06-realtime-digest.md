# Phase 6 brief — realtime events and the digest

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 7, 8),
`docs/reviews/capability-checklist.md`, `src/as_ig_mcp/{client,mapping,cache,state,session,writes,server,cli}.py`.

Build the realtime socket reader and the "what changed" digest. This is the
feature no market tool has.

## 1. `src/as_ig_mcp/realtime.py`

The socket client already exists inside instagrapi
(`instagrapi/realtime/client.py`, class `RealtimeClient`); the mixin
`mixins/realtime.py` wraps it. Read both in the installed source at
`C:\Users\aswat\Downloads\Projects\whatsapp-mcp-venv\Lib\site-packages\instagrapi\`
before writing anything.

- `RealtimeManager` class:
  - `start(settings)` — builds its **own** instagrapi client from the same
    settings (a separate client from the one serving HTTP calls: instagrapi's
    client is not thread-safe, and the socket reader must never touch the HTTP
    client's state), then calls `rt.direct_subscribe()` **once on the calling
    thread** before starting the reader. `direct_subscribe()` is what fetches
    the `seq_id` and `snapshot_at_ms` and subscribes to the message-sync
    stream; without it the socket connects and no message ever arrives.
  - starts one daemon thread looping `rt.realtime_read_once()`.
  - pings every 15 seconds (`rt.realtime_ping()`); the transport's keep-alive is
    20 seconds.
  - on a socket error, reconnects with backoff (1, 2, 4, 8, 16 seconds, capped
    at 60), and re-subscribes after every reconnect.
  - normalises every event to `{"ts": epoch, "event": name, "thread_id": str|None,
    "value": any}` and appends it to `events.jsonl` through `events.py`.
  - event names to expect: `receive`, `message`, `thread_update`, `iris`,
    `direct`, `typing`, `seen`, `presence`, `send_response`, `iris_sub_response`,
    `realtime_sub`. There is **no** reaction event: a reaction arrives inside a
    `message` patch, so classify it from the payload and set
    `"value": {"reaction": ...}` when you can. If you cannot classify it, keep
    the raw patch under `"value": {"raw": ...}` rather than guessing.
  - `status()` — connected or not, when it connected, the last event time, the
    last error, the subscribe state, and how many events have been seen.
  - `stop()` — closes the socket and joins the thread.
- The realtime socket is **on by default**. `AS_IG_REALTIME=0` turns it off, and
  then everything behaves exactly as before. Nothing else changes.

## 2. `src/as_ig_mcp/events.py`

- `append(event: dict)` — one JSON object per line to `%APPDATA%\as-ig-mcp\events.jsonl`,
  appended atomically.
- `tail(offset: int = 0, timeout_s: float = 0.0, kinds: list[str] | None = None)` —
  return the events after `offset`. With `timeout_s` greater than zero, wait on
  a `threading.Condition` until a new event arrives or the timeout expires.
- `count()` — how many events are in the file, so a caller can use the count as
  the next offset.
- Events are read-only data. Nothing here writes to Instagram.

## 3. `src/as_ig_mcp/tools_digest.py` — `ig_digest`

`ig_digest(since="last", timeout_s=0, kinds=None)`

- `since="last"` compares against the markers from the previous call;
  `since` may also be an ISO date.
- Compares **live** state, never the cache: pass `fresh=True` to the underlying
  reads. A digest built from a warm cache would report "nothing changed" while
  Instagram moved on.
- Returns what changed since the last call:
  - `new_messages` — threads whose last message id is newer than the marker,
    with the sender, the text and the time;
  - `new_followers` — the follower count change and the accounts behind it when
    Instagram gives them;
  - `new_posts` — media pks newer than the marker, with the caption and the time;
  - `new_stories` — story pks newer than the marker;
  - `events` — the realtime events since the last call, when the socket is on;
  - `markers_updated_at`.
- Markers live in the `digest` table in `state.db` (the table already exists).
- With `timeout_s` greater than zero and the socket on, the call waits for a
  realtime event before returning, up to the timeout, and returns what it has
  when the timeout expires. Cap the timeout at 60 seconds.
- The first call has no previous markers: it returns the current state and
  writes the markers, and says so with `"first_run": true`.

## 4. Writes clear the cache

A successful write must not leave a stale cached read behind.

- In `writes.perform_write`, after a successful write, clear the cache entries
  that could hold the thing that just changed. The simplest correct rule: clear
  the whole cache. It is a cache; clearing it costs one extra read.

## 5. Wiring

- Register `ig_digest` on the server with a description that starts with
  `[AS-IG-MCP]`.
- The server starts the realtime manager when it starts, unless
  `AS_IG_REALTIME=0`, and stops it when it exits.
- `python -m as_ig_mcp digest` runs the digest from the terminal, and
  `python -m as_ig_mcp realtime` prints the realtime status.

## 6. Tests

`tests/test_events.py`
- append then tail returns the events in order; tail with a cursor returns only
  the newer ones; filtering by kind works; tail with a timeout returns what
  arrived and then gives up; the file holds one JSON object per line.

`tests/test_realtime.py`
- `start()` calls `direct_subscribe()` exactly once, before the reader thread
  starts (assert the call order with a fake client);
- a socket error triggers a reconnect with backoff and a re-subscribe;
- events are normalised to the documented shape;
- a reaction arriving inside a message patch is classified, and an
  unclassifiable patch keeps the raw value instead of a guess;
- `stop()` closes the socket;
- with `AS_IG_REALTIME=0` nothing starts.

`tests/test_tool_digest.py`
- the first call reports `first_run` and writes the markers;
- the second call with no change reports nothing changed;
- a changed message shows up in `new_messages`;
- the digest reads live state, not the cache (assert the underlying read was
  called with `fresh=True`);
- with `timeout_s` and the socket off, the call returns after the timeout with
  no events rather than hanging.

Every test uses a fake client and a temporary APPDATA. No network, no real
socket.

## 7. Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 145. Print the pytest
summary line as your last output.

## 8. Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not open a real socket.
- Do not read or write `C:\Users\aswat\AppData\Roaming\as-ig-mcp` — tests use a
  temporary APPDATA.
- Do not change the `instagrapi==3.2.8` pin, and do not run git write commands.
- If an instagrapi method or event name differs from what this brief says, use
  what the installed source actually says and say so in your final message.
