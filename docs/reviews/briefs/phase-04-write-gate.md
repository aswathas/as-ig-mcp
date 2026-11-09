# Phase 4 brief — the write gate, the audit journal, idempotency

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 7, 8),
`docs/reviews/capability-checklist.md`, `src/as_ig_mcp/{client,mapping,cache,state,server}.py`.

Build the only path that can change anything on the account: `ig_write`.
Nothing in this phase may perform a real Instagram write — the tests use a fake client.

## 1. Fix the fallback for writes first

`client.call_write` currently still allows the REST↔GraphQL fallback. A write must
never fall back: if Instagram accepted the request and only the response failed to
parse, a fallback would send it twice.

- `call_write(client, feature, **kwargs)` must call the mapped method exactly once,
  with no fallback, and re-raise whatever it raises.
- `call_feature(..., allow_write=True)` keeps its current behaviour for reads, but
  when the feature is a write it must also skip the fallback.
- Add a test: a fake client whose primary method raises a retryable error and whose
  fallback method would succeed — after `call_write`, the fallback must not have been
  called.

## 2. `src/as_ig_mcp/writes.py` — the gate

State file: `%APPDATA%\as-ig-mcp\pending.json` (plain JSON is fine — it holds no
secret, only a hash of the code).

Each pending entry:

```
handle            unique id, e.g. "w-3f9a2c"
feature           the mapping feature, e.g. "send_message"
args              the arguments for the call (no credentials)
preview           one human-readable line describing exactly what will happen
code_hash         sha256 of the 6-digit code plus a per-entry salt
created_at        epoch seconds
expires_at        epoch seconds, created_at + 360
state             "pending" | "approved" | "rejected" | "failed" | "expired"
idempotency_key   optional, from the caller
result            short summary after execution
```

Functions:

- `make_preview(feature, args) -> str` — a single line a human can check, e.g.
  `DM to @pravss.23: "Solu da"`. Include the target and the text. Never include a
  code, a password or a cookie.
- `generate_code() -> str` — six digits, from `secrets`.
- `hash_code(code, salt) -> str`.
- `request_write(feature, args, idempotency_key=None) -> dict` — creates the entry,
  generates the code, shows it, stores only the hash, returns
  `{"ok": False, "needs_confirm": True, "handle": ..., "preview": ..., "expires_in_s": 360,
  "approve_via": "popup" | "cli"}`. **The returned dict must never contain the code.**
- `confirm_write(handle, code, client) -> dict` — checks the handle, the expiry and the
  code hash (constant-time compare), then executes exactly one call through
  `client.call_write`, journals the result and returns it.
- `reject_write(handle, reason) -> dict` — marks the entry rejected and journals it.
- `pending_list() -> list` — the open entries, without codes.
- `show_code(handle) -> str` — used only by the CLI: returns the code for display.
  It is the only function that can produce the code, and it is never reachable from
  an MCP tool.

### Showing the code to the owner

- Primary: a Windows popup. Use `ctypes` and `user32.MessageBoxW` to show the preview
  and the code, e.g. title "AS-IG-MCP — confirm write" and the body
  `"<preview>\n\nCode: 123456"`. This is the account owner's screen, not the agent's.
- Fallback when there is no interactive desktop (the popup raises): the code is **not**
  written to any file. Instead the entry is marked `approve_via = "cli"`, and the human
  runs `python -m as_ig_mcp approve <handle>`, which generates a fresh code, prints it
  in that terminal, stores its hash, and exits. The human then types the code in chat.
- The code is never written to `pending.json`, `audit.jsonl`, a log file, or any file
  the agent can read. Only its hash is stored.

### Audit journal

`%APPDATA%\as-ig-mcp\audit.jsonl`, one JSON object per line, appended atomically:

```
{"ts": epoch, "handle": ..., "feature": ..., "args_summary": "...", "preview": "...",
 "state": "requested|approved|rejected|failed|expired", "code_attempts": 0,
 "idempotency_key": ..., "result_summary": "..."}
```

Never write the code. Never write a cookie. `args_summary` is a short description,
not the raw arguments.

### Idempotency

- If `idempotency_key` is given and an entry with that key already exists in state
  `approved`, return `{"ok": True, "already_done": True, "handle": ..., "result": ...}`
  and do **not** execute again.
- The key is checked before the code is verified, so a replay after success is a no-op
  even if the code is wrong.

## 3. The `ig_write` tool

`ig_write(kind, action_args..., confirm=None, handle=None, idempotency_key=None)`

- `kind` selects the mapping feature (`send_message`, `send_media`, `send_voice`,
  `send_file`, `react`, `unsend`, `mark_seen`, `share`, `publish`, `schedule`,
  `first_comment`, `comment`, `bulk_delete_comments`, `toggle_comments`, `follow`,
  `unfollow`, `block`, `unblock`, `mute`, `report`, `remove_follower`, `close_friend`,
  `follow_hashtag`, `highlight`, `note`, `profile`, `category`, `ai_label`,
  `crosspost`, `collaborate`, `thread_hide`, `thread_title`, `thread_group_members`,
  `follow_request_approve`, `follow_request_decline`).
- Every other argument is passed through to the instagrapi method named by the
  mapping. Document the required arguments per kind in the tool description.
- First call (no `confirm`): build the entry, show the code, return `needs_confirm` +
  handle + preview. **No Instagram call happens.**
- Second call (`confirm` + `handle`): verify and execute.
- An unknown `kind` returns an error listing the valid kinds. It never raises.
- `kind="schedule"` takes `schedule_at`; the item is confirmed at enqueue time like any
  other write, and the queue stores the confirmed handle.

## 4. CLI additions

- `python -m as_ig_mcp approve <handle>` — shows the code in the terminal and stores its
  hash (the no-desktop path). Also `python -m as_ig_mcp pending` to list open handles.

## 5. Tests

`tests/test_writes.py`
- `request_write` returns `needs_confirm`, a handle and a preview, and **no 6-digit
  code appears anywhere in the returned dict** (assert with a regex over the JSON dump).
- the pending file on disk contains no code (regex over the file text).
- `confirm_write` with the wrong code makes no Instagram call and journals `rejected`.
- `confirm_write` with the right code calls the fake client exactly once.
- an expired handle is refused and journals `expired`.
- a replayed `idempotency_key` returns `already_done` and makes no second call.
- the audit journal has one line per state transition, and no line contains a code.

`tests/test_client.py` (extend)
- `call_write` does not use the fallback when the primary raises.
- `call_feature` with `allow_write=True` on a write feature does not use the fallback.

`tests/test_tool_write.py`
- `ig_write` with an unknown kind returns an error.
- `ig_write` without `confirm` returns `needs_confirm` and the fake client recorded no call.
- `ig_write` with `confirm` and a valid handle calls the fake client once.
- the preview mentions the target.

## Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 59. Print the pytest summary line
as your last output.

## Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Every test uses a fake client.
- Do not read or write `C:\Users\aswat\AppData\Roaming\as-ig-mcp` — tests use a temp
  APPDATA.
- Do not commit anything, and do not change the `instagrapi==3.2.8` pin.
- If the Windows popup cannot be shown in your environment, say so in your final message
  and make sure the CLI path works — that is the fallback that matters.
