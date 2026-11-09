# AS-IG-MCP — the build loop

Plain doc, not a skill. This is the loop Claude Code runs until the product is
finished and tested.

## Loop

1. **Pick the next phase.** First phase in the spec's build order (section 9)
   whose check is not yet green. The phase list lives in
   `docs/reviews/capability-checklist.md`.
2. **Write the brief.** `docs/reviews/briefs/phase-NN-name.md`. Name the exact
   files, the check that must pass, the tools the worker may touch, and the
   constraints (no Instagram write, no secrets in the prompt, no git writes).
3. **Dispatch one worker.** Wait for it. Do not run two workers on the same files.
4. **Verify yourself.** Run the phase check in this session. A worker's claim
   that it passed is not evidence.
5. **Review.** After any phase that adds or changes tools, run the EGM critic
   stage on the touched code and spec, and read the report in `docs/reviews/`.
6. **Commit.** One commit per phase, author `aswathas <aswathas20@gmail.com>`,
   ending with the required attribution line.
7. **Update state.** Tick the rows in `capability-checklist.md`, append an entry
   to `build-log.md`.

## Workers

| Worker | Command (Windows) | Where |
|---|---|---|
| Command Code | `"C:\Users\aswat\AppData\Roaming\npm\cmd.cmd" -p "<task>" --accept-edits --yolo --tools-all --add-dir <repo>` | Windows |
| Antigravity | `agy --print "<task>" --mode accept-edits --dangerously-skip-permissions --add-dir <repo>` | Windows |
| Antigravity (WSL) | `wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/aswath/Projects/as-ig-mcp && agy --print '<task>' --mode accept-edits --dangerously-skip-permissions"` | WSL |

Bare `cmd` on PATH is Windows cmd.exe, not Command Code — it opens a shell and
does nothing. Always call the npm `cmd.cmd` by full path.

## Decision rules

- A phase check fails → re-dispatch the same worker with the failure output in
  the brief. Two failures in a row → switch worker (cmd ↔ agy).
- Two workers disagree → the orchestrator decides and writes the reason into
  the build log. Never leave it unresolved.
- A check needs a real Instagram write → ask the user first. The only write
  allowed without a fresh go-ahead is one DM to the account owner's own thread,
  and only after the confirm gate is proven to block.
- The spec needs changing → stop, edit the spec, tell the user what changed
  and why, get a new approval. A changed spec lapses the old approval.
- Instagram blocks us (429, challenge, dead endpoint) → record it, move to the
  next capability, retry that one at most twice.
- A worker wanders off scope → stop it, re-brief with a narrower file list.

## Safety rules

- No Instagram write without the account owner's approval click in the dialog on
  their own screen — in any worker, ever. There is no approval code to relay or fetch.
- The session file stays DPAPI-encrypted; never commit it, never paste it into
  a worker prompt, never print it.
- Workers never receive the account password. Relogin is done by the user
  through the masked Windows dialog.
- One live read sweep per minute at most. The cache is on by default.
- Workers commit nothing. The orchestrator owns the git history.

## Done means

Every row of `capability-checklist.md` is green, `claude plugin validate --strict`
is clean, the package builds and installs, and the registry manifest validates.
