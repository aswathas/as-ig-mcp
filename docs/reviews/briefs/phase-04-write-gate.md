# Phase 4 brief — the write gate: a human clicks, the agent never approves

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 7, 8),
`docs/reviews/capability-checklist.md`, `src/as_ig_mcp/{client,mapping,cache,state,server}.py`.

Build the only path that can change anything on the account: `ig_write`.
**This design changed after an adversarial review.** The earlier plan used a
6-digit code that the owner typed into chat. That failed review: the owner
types it *to the agent*, so the code lands in the agent's context, and a CLI
fallback let the agent read the code itself. There is no code now. The human
approves by clicking.

No test may touch the real desktop or Instagram.

## 1. `client.call_write` must not fall back

`call_write(client, feature, **kwargs)` calls the mapped method exactly once,
with no REST↔GraphQL fallback, and re-raises whatever it raises. A write whose
response failed to parse may already have been accepted by Instagram, so it is
never retried by us. `call_feature(..., allow_write=True)` behaves the same when
the feature is a write.

Test: a fake client whose primary method raises a retryable error and whose
fallback would succeed — after `call_write`, the fallback must not have run.

## 2. `src/as_ig_mcp/writes.py` — the approval dialog

- `make_preview(feature, args) -> str` — one line a human can check, e.g.
  `DM to @pravss.23: "Solu da"`. Include the target and the text. Never a
  cookie, a password or a code.
- `show_approval(preview: str, timeout_s: int = 300) -> bool` — the only function
  that touches the desktop.
  - Use `ctypes` and `user32.MessageBoxW` with `MB_YESNO` (and `MB_SETFOREGROUND`
    so it comes to the front): title `AS-IG-MCP - approve write`, body
    `"<preview>\n\nYes = approve and do it now. No = do not do it."`
  - `IDYES` → `True`, `IDNO` → `False`.
  - Run it on a **separate thread** so the caller's thread is not the one
    blocked by a modal window, and wait for the result with a timeout of
    `timeout_s` (default 300, configurable by `AS_IG_REALTIME_TIMEOUT`… no —
    use a dedicated `AS_IG_APPROVE_TIMEOUT`, default 300).
  - If the dialog cannot be shown at all (no desktop session, the call raises),
    return `None` — distinct from "the human said No".
  - If the timeout expires, return `False` (treated as a denial).
  - The function must be injectable for tests: `show_approval` is looked up on
    the module, so a test can replace it with a stub.
- `perform_write(feature, args, idempotency_key=None, dialog=show_approval) -> dict`:
  1. Build the preview.
  2. If an `idempotency_key` was given and a completed entry with that key
     exists, return `{"ok": True, "already_done": True, "preview": ...}` and
     **do not show a dialog and do not call Instagram**.
  3. Ask the dialog. If it returns `None` → journal `failed` with the reason
     "no interactive desktop" and return
     `{"ok": False, "error": "no interactive desktop - a write needs a person at the keyboard"}`.
  4. If it returns `False` → journal `denied` and return
     `{"ok": False, "denied": True, "preview": ...}`.
  5. If it returns `True` → journal `approved`, then call the mapped method
     **exactly once** through `client.call_write`, journal the outcome
     (`approved` on success, `failed` with the error text on failure) and return
     the result.
- `approve_pending` / `pending.json` / a confirm code / `python -m as_ig_mcp approve`
  **do not exist**. One call, one decision, one execution.

## 3. The audit journal

`%APPDATA%\as-ig-mcp\audit.jsonl`, one JSON object per line, appended atomically:

```
{"ts": epoch, "feature": "...", "args_summary": "...", "preview": "...",
 "state": "approved|denied|failed", "idempotency_key": ..., "result_summary": "..."}
```

Never write a cookie, a password or an approval code. `args_summary` is a short
description, not the raw arguments. A denied write is journalled too — the
journal is the record of every attempt, not only the ones that went through.

## 4. The `ig_write` tool

`ig_write(kind, confirm=None, idempotency_key=None, **args)`

- `kind` selects the mapping feature. The full list, with the arguments each one
  needs, goes in the tool description: `send_message`, `send_media`,
  `send_voice`, `send_file`, `react`, `unsend`, `mark_seen`, `share`, `publish`,
  `schedule`, `first_comment`, `comment`, `bulk_delete_comments`,
  `toggle_comments`, `follow`, `unfollow`, `block`, `unblock`, `mute`, `report`,
  `remove_follower`, `close_friend`, `follow_hashtag`, `highlight`, `note`,
  `profile`, `category`, `ai_label`, `crosspost`, `collaborate`, `thread_hide`,
  `thread_title`, `thread_group_members`, `follow_request_approve`,
  `follow_request_decline`, `download`.
- `confirm` is **not** a parameter — there is no code. Remove it.
- The tool description must say, in one line, that the account owner approves by
  clicking in a dialog on their own screen, and that the agent cannot approve on
  their behalf.
- Unknown `kind` → an error listing the valid kinds. It never raises.
- The tool must declare the standard annotations: `readOnlyHint=false`,
  `destructiveHint` true for the destructive kinds (unfollow, block, unsend,
  bulk_delete_comments, remove_follower, delete), `idempotentHint=true`,
  `openWorldHint=true`. If the MCP package in use supports per-tool metadata,
  also set `_meta["anthropic/requiresUserInteraction"]` on `ig_write` so
  Claude Code asks the user before the call runs.

## 5. Tests

`tests/test_writes.py`
- the dialog is shown with a preview that mentions the target and the text;
- the human says No → no Instagram call, result `denied`, journal has one
  `denied` line;
- the dialog returns `None` (no desktop) → no Instagram call, result carries
  the "no interactive desktop" error, journal `failed`;
- the human says Yes → the fake client is called exactly once, journal `approved`;
- a repeated `idempotency_key` → `already_done`, no dialog, no call;
- a failing write → journal `failed` with the error text, and no second attempt;
- the journal never contains the string "sessionid" or "csrftoken".

`tests/test_client.py` (extend) — `call_write` does not use the fallback when the
primary raises; `call_feature` with `allow_write=True` on a write feature does
not use the fallback either.

`tests/test_tool_write.py`
- unknown kind → an error, no call;
- the stub dialog is consulted exactly once per write;
- the preview reaches the dialog.

Every test injects a stub for the dialog. No test may open a real window.

## 6. Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, zero real dialogs, count higher than 73.
Print the pytest summary line as your last output.

## 7. Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Every test uses a fake client.
- Do not read or write `C:\Users\aswat\AppData\Roaming\as-ig-mcp` — tests use a
  temp APPDATA.
- Do not commit anything, and do not change the `instagrapi==3.2.8` pin.
- Do not implement a confirm code, a pending file, or a CLI approve path. The
  review that produced this brief removed them on purpose.
