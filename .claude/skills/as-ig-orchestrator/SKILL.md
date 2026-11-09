---
name: as-ig-orchestrator
description: "Orchestrates building and verifying AS-IG-MCP. Claude Code is the orchestrator; cmd (Command Code) and agy (Antigravity, Windows and WSL) are the workers. Use when building, reviewing, finishing or verifying AS-IG-MCP, when the next build-plan phase needs a worker, or when a capability check fails."
---

# AS-IG-MCP orchestrator

Claude Code is the orchestrator. It decides what happens next and who does it. It
does not write implementation code by hand except for one-line fixes; bulk work
goes to a worker, and the orchestrator verifies the result itself.

**Project root:** `C:\Users\aswat\Projects\as-ig-mcp`
**WSL path to the same tree:** `/mnt/c/Users/aswath/Projects/as-ig-mcp`

## The three workers

| Worker | Command (Windows) | Where | Best at |
|---|---|---|---|
| Command Code | `"C:\Users\aswat\AppData\Roaming\npm\cmd.cmd" -p "<task>" --accept-edits --yolo --tools-all --add-dir <repo>` | Windows | bulk implementation, scaffolding, running the test suite |
| Antigravity | `agy --print "<task>" --mode accept-edits --dangerously-skip-permissions --add-dir <repo>` | Windows | implementation, and review personas via `--agent` |
| Antigravity (WSL) | `wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/aswath/Projects/as-ig-mcp && agy --print '<task>' --mode accept-edits --dangerously-skip-permissions"` | WSL | independent second opinion, Linux-side packaging checks |

Bare `cmd` on PATH is **Windows cmd.exe**, not Command Code — it opens a shell and does nothing.
Always call the npm `cmd.cmd` by full path. `cmdc` is the same CLI under another name.

`agy agents` lists the available Antigravity personas (the `egm-*` reviewers).
WSL prints a harmless `Unknown key 'networkingMode'` warning on every call; that
is not a failure.

## The loop

1. **Read the plan.** `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md`
   section 9 holds the build order. `docs/reviews/capability-checklist.md` holds
   the definition of done.
2. **Choose the next phase.** The first phase in the build order whose check is
   not yet green.
3. **Write the brief.** Name the exact files, the check that must pass, the
   tools the worker may touch, and the constraints (no Instagram write, no
   secrets in the prompt, no commits — the orchestrator commits).
4. **Dispatch one worker.** Wait for it to finish. Do not run two workers on the
   same files at once.
5. **Verify yourself.** Run the phase check in this session. A worker's claim
   that it passed is not evidence.
6. **Review.** After any phase that adds or changes tools, run the EGM critic
   stage on the touched code and spec (`/egm:egm-review`, stage 7), and read
   `docs/reviews/critic_report.md`.
7. **Commit.** One commit per phase, authored as `aswathas
   <aswathas20@gmail.com>`, message ending with the required attribution line.
8. **Update state.** Tick the phase in the capability checklist and append a
   line to `docs/reviews/build-log.md`: what ran, what the check printed, what
   the worker got wrong.

## Decision rules

- A phase check fails → re-dispatch the same worker with the failure output
  appended to the brief. Two failures in a row → switch worker (cmd ↔ agy).
- Two workers disagree → the orchestrator decides, and writes the reason into
  the build log. Never leave a disagreement unresolved.
- A check needs a real Instagram write → ask the user first. The only write
  allowed without a fresh go-ahead is one DM to the account owner's own
  thread, and only after the confirm gate is proven to block.
- The spec needs changing → stop, edit the spec, tell the user what changed
  and why, and get a new approval. A changed spec lapses the old approval.
- Instagram blocks us (429, challenge, dead endpoint) → record it in the build
  log, move to the next capability, retry that one at most twice.
- A worker wanders off scope → stop it, re-brief with a narrower file list.

## Definition of done

`docs/reviews/capability-checklist.md` lists every capability AS-IG-MCP
promises, with a check per row. The project is finished when every row is
green:

- reads: `ig_health` reports each class live, and one live call per class works;
- writes: the confirm gate blocks an unconfirmed write, and one approved DM to
  the owner's own thread lands exactly once;
- realtime: `ig_digest wait_s` returns an event, and the polling path still
  works with the socket off;
- insights: the numbers match Instagram's own (reach, impressions, likes on a
  known post);
- persistence: a restart completes a read with no email code;
- packaging: `claude plugin validate --strict` is clean, the PyPI build works,
  and the registry manifest is valid.

## Safety rules (never break)

- No Instagram write without the 6-digit confirm code — in any worker, ever.
- The session file stays DPAPI-encrypted; never commit it, never paste it into
  a worker prompt, never print it.
- Workers never receive the account password. Relogin is done by the user
  through the masked Windows dialog.
- One live read sweep per minute at most. The cache is on by default.
- Workers commit nothing. The orchestrator owns the git history.

## Files

| File | Purpose |
|---|---|
| `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md` | the approved plan |
| `docs/study/AS-IG-MCP - Capability Matrix.md` | what every vendor has, and what we promised to beat |
| `docs/reviews/capability-checklist.md` | the promise list and the definition of done |
| `docs/reviews/build-log.md` | what ran, what the checks printed, what broke |
| `docs/reviews/*.md` | EGM review reports per stage |
