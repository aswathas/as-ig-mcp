# Phase 5b brief — the publish queue, presets, and the queue runner

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` (sections 3, 6, 7, 8),
`docs/reviews/capability-checklist.md`, `src/as_ig_mcp/{state,cache,session,client,mapping,writes,server,cli}.py`.

Build the publish queue, the presets store, and the runner that fires queued posts.

## 1. `ig_queue`

`ig_queue(action="list", kind=None, when=None, text=None, media_path=None, caption=None, schedule_at=None, recurrence=None, item_id=None)`

Actions:

- `list` — the queued items: id, kind, caption or a short summary, the time it is
  due, its state, and its idempotency key.
- `schedule` — queue an item. `when` is an ISO datetime. `recurrence` is one of
  `none`, `daily`, `weekly`, `monthly`. The item is created in state `pending`.
  **Queueing an item is a write to Instagram's scheduler, so it goes through
  `writes.perform_write`** — the owner approves on their screen at the moment
  they queue it, and the approval travels with the item. That is the whole
  point: the five-minute runner publishes an already-approved item instead of
  creating a new one.
- `cancel` — cancel a `pending` item. Cancelling is not an Instagram write, so
  it needs no approval; it only changes our own queue.
- `native` — hand the post to **Instagram's own scheduler** instead of our
  queue: the upload carries `schedule_at` and Instagram publishes it, so it
  survives our machine being off. This is a write and goes through
  `writes.perform_write` like any other.

Queue states: `pending` → `publishing` → `done`, or `pending` → `cancelled`.

**Crash-safe.** The runner must set the state to `publishing` **before** it
calls Instagram, and only then to `done`. A crash between the Instagram call
and the state update leaves an item in `publishing`; on the next run those
items are reported as "possibly published — check before retrying" and are never
published again automatically. Republishing a post by accident is worse than
missing one.

Each item carries an idempotency key, so a repeated attempt with the same key
does not post twice.

## 2. `ig_preset`

`ig_preset(action="list", name=None, content=None, kind="caption")`

- Presets are saved text templates the agent reuses: a caption, a hashtag set,
  a first comment, a DM reply.
- `list` returns the presets: name, kind, content, updated time.
- `set` stores or replaces one: `name`, `kind` (`caption`, `hashtags`,
  `first_comment`, `dm_reply`), `content`.
- `delete` removes one.
- `get` returns one.
- Storage: a `presets` table in the same SQLite file (`state.db`), created by
  `state.init_db()`. No new file, no new dependency.
- Preset content is user text, not a secret, but it is still personal data:
  never write it to the audit journal.

## 3. The runner

- `python -m as_ig_mcp queue tick` — publish every `pending` item whose time has
  come. It must be safe to run every five minutes: two ticks at once must not
  publish the same item twice (the state change to `publishing` is the lock).
- `python -m as_ig_mcp queue list` — the same list as the tool.
- `python -m as_ig_mcp queue install-task` — register the Windows Scheduled Task
  that runs the tick every five minutes:
  `schtasks /create /tn "AS-IG-MCP queue" /sc minute /mo 5 /tr "<python> -m as_ig_mcp queue tick"`.
  Use the venv's python path, and report clearly if the task cannot be created
  (it may need a different account or elevation). Print the exact command it
  ran and whether it succeeded. Do not run `schtasks` in a test.

## 4. `ig_write` needs the queue kinds

The `ig_write` tool's kind list must include `schedule` (queue through our own
queue) and `native_schedule` (hand it to Instagram's scheduler). Both go
through the approval dialog.

## 5. Tests

`tests/test_queue.py`
- a queued item is `pending` with the right time and key;
- cancelling a pending item works and needs no approval;
- the tick publishes a due item exactly once and leaves a future item alone;
- two ticks in a row publish once;
- an item left in `publishing` is reported as possibly published and is never
  published again;
- a repeated idempotency key does not create a second item;
- queueing goes through the approval dialog (assert the stub dialog was called
  and that a denial leaves no item).

`tests/test_presets.py`
- set, get, list, delete;
- a preset survives a new connection to the same database;
- updating a preset replaces it rather than duplicating it.

`tests/test_cli_queue.py`
- `queue list` prints the items;
- `queue tick` with no due items does nothing and says so;
- `install-task` reports the command it would run without running it (the
  function that builds the command is separate from the function that runs it,
  so the test can check the command).

All tests use a temporary APPDATA and a fake Instagram client. No network, no
real scheduled task.

## 6. Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
```

All tests pass, zero network calls, count higher than 110. Print the pytest
summary line as your last output.

## 7. Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not make any Instagram or network call. Do not read or write
  `C:\Users\aswat\AppData\Roaming\as-ig-mcp` — tests use a temporary APPDATA.
- Do not run `schtasks` for real, and do not create a real scheduled task.
- Do not change the `instagrapi==3.2.8` pin, and do not run git write commands.
