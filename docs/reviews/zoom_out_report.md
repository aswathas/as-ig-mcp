# Goldfish Review Report — Stage 5, Initial Zoom Out Review

**Target:** `C:\Users\aswat\Projects\as-ig-mcp\docs\superpowers\specs\2026-11-10-as-ig-mcp-v1-design.md` (490 lines)
**FeatureRange:** 1–382 (problem, scope, success criteria, constraints, approach, architecture, failure modes, test plan)
**DetailedRange:** 383–490 (implementation build order, risks, exit condition)
**Standard:** `zoom-out-standard` — `C:\Users\aswat\.claude\plugins\cache\egm\egm\0.1.1\resources\document_standards\zoom-out-standard.md`
**Personas:** `agents\zoom_out.md`, `agents\inventive_catalyst.md` (same plugin cache root)
**GoldfishContext:** `[]` — empty; no additional files were supplied to either reviewer
**Stage:** 5 — Initial Zoom Out Review
**Date:** 2026-11-10

## Reviewer Status

| Reviewer | Status | Instances run | Findings |
| --- | --- | --- | --- |
| `egm-zoom-out` | completed | 2 (initial + one retry) | 21 |
| `egm-inventive-catalyst` | completed | 2 (initial + one retry) | 18 |

Both reviewers were dispatched as fresh subagents of their registered types (`egm:egm-zoom-out`, `egm:egm-inventive-catalyst`) with the target path, the resolved line ranges, their persona file, the standard file and the empty GoldfishContext list. Both were strictly read-only; neither wrote to the target document.

Findings marked **ZO-n** are the zoom-out reviewer's. Findings marked **IC-n** are the inventive-catalyst reviewer's. Findings marked **X-n** were added during synthesis after verifying each one against `docs/study/`, `docs/reviews/capability-checklist.md`, `.claude/skills/as-ig-orchestrator/SKILL.md`, `.gitignore`, `pyproject.toml`, `src/as_ig_mcp/mapping.py` and the installed instagrapi 3.2.8 source. X-n findings are attributed to the lens that raised them.

## Severity Summary

| Severity | Zoom-out | Inventive catalyst | Total |
| --- | --- | --- | --- |
| 🔴 Blocker | 2 | 1 | 3 |
| 🟡 Major | 12 | 12 | 24 |
| 🟢 Nit | 7 | 5 | 12 |
| **Total** | **21** | **18** | **39** |

---

# Reviewer: `egm-zoom-out` (Skeptical Architect)

Standard applied: §0 context sufficiency · §1 root problem focus · §2 YAGNI, premature optimization, minimalist data flow, architectural dead-ends · §3 anti-weeds, right placement · §4 codebase and platform reuse, pattern consistency, anti-patterns.

**Context sufficiency (§0): passed.** The objective (line 11), the user (line 17), the measured root cause (lines 19–38) and the environment (lines 134–156) are all present. The failures below are failures of the *plan*, not of the *why*.

### ZO-1 — 🔴 Blocker — Scope is market parity, not the stated job

* **Affected Scope:** lines 39–43 vs. lines 49–63 and 278–285
* **Discrepancy:** The job is written as "on this machine, for this one business account" (lines 40–41). Two lines later the same paragraph adds "cover every capability the whole market covers, plus the ones nobody covers" (lines 42–43), and §2 turns that into 16 tools, roughly 40 capabilities and roughly 35 write kinds. One user, one account, one consumer does not need cutout stickers, quicksnap, IGTV, bulk comment delete, crosspost to Threads, collaboration invite, AI label, account category, close-friends, hashtag follow, inbox notes and on-post notes in v1. Every kind is a mapping entry, a confirm-gate branch, an audit case and an Instagram-side risk.
* **Rationale & Recommendation:** Under §2 (YAGNI) the v1 surface should be the dead reads, DM read, publish, comment, follow/unfollow. Cut the rest until a real need shows up. Note the reviewer's own caveat: if the market-parity clause was an explicit user requirement, this becomes a scope-confirmation question rather than a YAGNI finding — the spec should say explicitly which it is, because §1 currently asserts both in one paragraph.

### ZO-2 — 🔴 Blocker — Distribution as v1 scope contradicts the problem statement

* **Affected Scope:** lines 40–41 vs. lines 73–75 and 397
* **Discrepancy:** Nothing in §1 asks for a PyPI package, an official MCP registry entry, a Claude plugin marketplace entry, `server.json`, `plugin.json`, `claude plugin validate --strict` or a README of at least 40 words. The stated requirement is "this machine, this one account". Phase 8's acceptance test, "a stranger can install and run it in one command" (line 397), is a new requirement invented by the plan. A local install plus a README solves the actual problem; publishing can be a later phase.
* **Rationale & Recommendation:** §1 (root problem focus). Publishing is a distribution decision with its own risks (see IC-9), not part of the defect fix. Move Phase 8's registry and marketplace work to a v1.1 phase, keeping only README, LICENSE and a local install as v1 deliverables.

### ZO-3 — 🟡 Major — Realtime is a second message-sync client, for a push nobody consumes

* **Affected Scope:** lines 315–325, 396, 429, 449–451
* **Discrepancy:** The spec's own assumptions say the payload shape may change without notice, that it ships behind a flag with polling as default (lines 427–429), and that instagrapi has no reconnect logic so the server must add reconnect-with-backoff, a ping watchdog and its own event normalisation (lines 320–323). That is the single largest new-code item in the project, and the polling digest already ships in v1 and already answers "what changed" (line 269).
* **Rationale & Recommendation:** Ship the digest, measure its latency, add the socket only if latency is actually a problem. This is also the cheapest way to dissolve ZO-8 and X-9 together.

### ZO-4 — 🟡 Major — Two scheduling systems with two sources of truth

* **Affected Scope:** lines 64–65, 212, 272, 340, 354, 435–436
* **Discrepancy:** Native `schedule_at` plus a local queue with recurrence, overdue detection and recurrence-maths tests. The native one is better — server-side, survives sleep, no local state to corrupt — while the local queue adds a file, a scheduler, a failure mode ("item overdue at next start", line 340) and a test.
* **Rationale & Recommendation:** Ship `schedule_at` in v1; add the local queue when drafts and recurrence are actually requested. See also IC-5, which reaches the same conclusion via a different route, and X-1 for the deeper problem — the local queue has no trigger at all.

### ZO-5 — 🟡 Major — §6's method list is a weed that will drift

* **Affected Scope:** lines 206, 287–313
* **Discrepancy:** The spec states `mapping.py` is "the single place to change when Instagram moves" (line 287), then lists roughly 60 instagrapi method names in the document body (lines 288–313). That is a second copy of the table, written at the wrong altitude for a design section, guaranteed to disagree with the code.
* **Rationale & Recommendation:** §3 (anti-weeds). Keep the rule in the spec ("one canonical method per feature, one REST fallback"); keep the table in `mapping.py`. This is not hypothetical: `src/as_ig_mcp/mapping.py` already exists as a feature-keyed `FEATURE_METHODS` dict with the same content, so the drift has already begun.

### ZO-6 — 🟡 Major — The confirm gate covers trivial writes

* **Affected Scope:** lines 41, 278–285, 338
* **Discrepancy:** The requirement is "nothing published or sent without a human confirm code" (line 41). The design applies the gate to `mark_seen`, `react` and `toggle_comments` too — two extra round trips and a 6-digit code to react to a message.
* **Rationale & Recommendation:** Gate send, publish, comment, delete, follow/block/report and crosspost; run `mark_seen` and `react` directly. This is the same allowlist IC-3 proposes as a cushioning measure.

### ZO-7 — 🟡 Major — `pycryptodomex` contradicts the spec's own assumption, and the pins do not match

* **Affected Scope:** lines 138 and 197 vs. A4 lines 411–412; `pyproject.toml` lines 10 and 13–17
* **Discrepancy:** §4 pins `pycryptodomex`; A4 says "DPAPI through `ctypes` is enough to protect the session cookie; no third-party crypto dependency needed". `pyproject.toml` line 16 already ships the dependency. Additionally, §6 line 197 and §4 line 138 describe the dependency set as "pinned", but `pyproject.toml` line 15 leaves `mcp` unpinned, and `pyproject.toml` line 10 declares `requires-python = ">=3.11"` while §4 line 137 pins the venv to Python 3.14 — a support range nothing tests, and instagrapi 3.2.8 predates 3.13/3.14.
* **Rationale & Recommendation:** Either a crypto library is needed — state what it protects that DPAPI does not — or it is dead weight in a package that will be published to PyPI. Pin `mcp`. Set `requires-python` to the interpreter instagrapi 3.2.8 is actually exercised on.

### ZO-8 — 🟡 Major — File-shared state versus one realtime thread per process

* **Affected Scope:** lines 146–148 vs. 315 and 344
* **Discrepancy:** The design promises shared file state because several Claude Code sessions run at once (lines 146–148), yet realtime is "one daemon thread per server run" (line 315). Two sessions means two socket subscriptions, two ping watchdogs, two writers to `events.jsonl`, and the failure row "digest markers merge by timestamp" (line 344) with no defined mechanism. The spec has already rejected the shared daemon (lines 177–180).
* **Rationale & Recommendation:** Pick one: realtime stays off by default, or it becomes a single shared process. See IC-1 for the same contradiction from the contradiction-elimination lens.

### ZO-9 — 🟡 Major — The cache layer duplicates the digest

* **Affected Scope:** lines 208, 233, 249, 344
* **Discrepancy:** `cache.json` (per-endpoint TTL) and `digest.json` (last-seen markers) both answer "what did we see last time", with different invalidation rules and a silent last-writer-wins race between sessions (line 344). The stated purpose of the cache is throttling (line 151), which instagrapi's delay range plus the digest's own fetch set already partly covers.
* **Rationale & Recommendation:** One marker file, one rule. §2 (minimalist data flow). Pairs with IC-4, which identifies the concurrency defect inside the digest half of the duplication.

### ZO-10 — 🟡 Major — "Capabilities nobody in the market has" mostly re-lists native Instagram features

* **Affected Scope:** lines 66–70
* **Discrepancy:** Best-post ranking is Instagram's own `insights_media_feed_all` (lines 290, 120–121). Best-time-to-post is Instagram's own feature. Per-post comparison by age is a query over the same insights endpoint. Competitor benchmarking has no tool, no component and no mapping anywhere in §6 — scope that was never architected.
* **Rationale & Recommendation:** Re-label these as "existing endpoint, exposed" so a reader knows which are real work. See X-2, which shows the project's own market research already contradicts the "nobody has this" framing.

### X-1 — 🟡 Major — The local publish queue has no mechanism that can fire it

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §2 lines 64–65; §3 criterion 11 lines 122–124; §6 line 212 and line 272, state line 253; §7 line 340; §9 Phase 6 line 395; D2 lines 435–436
* **Discrepancy:** `ig_queue` promises "list, schedule, cancel, recurring posts". The architecture has no timer, no trigger, no OS-level scheduler and no long-lived process. §4 line 144 sets the transport to stdio (process lifetime = Claude Code session lifetime), and §5 lines 177–180 explicitly reject "a separate long-running daemon for v1". §7 line 340 concedes the consequence — an overdue item is "item overdue at next start" and "publishes late", i.e. a post fires only if a human opens Claude Code and calls a tool. §8 test 10 (lines 374–375) only asserts the item "sits in `queue.json`" and can be cancelled; it never asserts that a post is published at the scheduled time.
* **Rationale & Recommendation:** A capability promised in scope, in the tool surface, in the success criteria and in the acceptance checklist (W7) that cannot execute is a false promise. Ship only Instagram's native `schedule_at` in v1 and drop the local queue, or add the missing trigger (Windows Task Scheduler entry or an explicit daemon) and reverse the §5 rejection with the reason for the reversal. Also change §8 test 10 to assert publication, not file presence.

### X-2 — 🟡 Major — Two claimed differentiators are contradicted by the project's own market study

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** lines 42–43, 49–51, 66–70
* **Discrepancy:** The spec claims "a first-class best-time tool; local competitor benchmarking" as capabilities nobody else has. `docs/study/AS-IG-MCP - Deep Study and Build Blueprint.md` §3.2 (line 155) lists Metricool MCP as shipping "posts/reels/stories, competitors … strong + best-time" and §3.6 (line 185) repeats "Metricool: best-time-to-post and competitor analysis". The study's own white-space list (§3.9, lines 205–215) has seven items and neither of these is among them. Separately, §1 and §2 claim coverage of "every capability the whole market covers", but the study's top-ten market list (§3.8, line 203) includes "media upload plus AI image/video generation", which the spec never mentions in either the in-scope or out-of-scope list.
* **Rationale & Recommendation:** Scope justified by a false premise. Either drop the two capabilities from the differentiator list or justify them on real grounds (e.g. best-time computed against this account's own history by age, which A8 already describes). Fix the superset claim or name the exclusion.

### X-3 — 🟡 Major — §9 contradicts the repo's own orchestrator convention

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §9 line 385 ("Agent implements") and the phase table lines 387–397; versus `.claude/skills/as-ig-orchestrator/SKILL.md` lines 8–10, 34–45, 52–63, 90
* **Discrepancy:** The repo's established pattern is explicit: "Claude Code is the orchestrator… It does not write implementation code by hand except for one-line fixes; bulk work goes to a worker" (skill lines 8–10); one worker per phase, the orchestrator verifies the check itself because "a worker's claim that it passed is not evidence" (lines 34–40); the orchestrator owns commits (line 90); the loop runs the EGM critic stage after any phase that touches tools (lines 41–43). §9 says "Agent implements", and its phase table has no worker, no verification step, no commit ownership and no review step.
* **Rationale & Recommendation:** §4 (pattern consistency). Rebuild the §9 table to the existing loop: phase → worker brief → check → self-verification → commit → checklist tick → build-log line, and state which phases need a real Instagram write (the skill's rule: only one DM to the account owner's own thread, and only after the confirm gate is proven to block).

### X-4 — 🟡 Major — Phase 8's check cannot be met with the repo as specified

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §4 lines 152–153; §9 Phase 8 line 397; §6 file tree lines 196–201; §10 M6 lines 461–464
* **Discrepancy:** §4 describes the repo as "git, local". Phase 8 publishes to PyPI, the official MCP registry and a Claude plugin marketplace, with the check "a stranger can install and run it in one command". Both the marketplace and the registry require a public repository and a GitHub-scoped name (`io.github.aswathas/as-ig-mcp`). The project's own study already prescribed the fixes and the spec dropped them: `docs/study/…` §6.1 item 3 ("Needs a public repo… either publish AS-IG-MCP as its own public repo or add a public marketplace repo"), item 1 (the registry verifies ownership by finding `mcp-name: io.github.aswathas/as-ig-mcp` in the package README), item 2 (the `server.json` schema, `$schema`, `io.github.` prefix and required fields). The spec carries none of it, and `.claude-plugin/marketplace.json` is absent from the §6 file tree (line 200 lists only `plugin.json`).
* **Rationale & Recommendation:** Add a §4 constraint ("the repo must be public at `github.com/aswathas/as-ig-mcp`") or drop the registry and marketplace rows from Phase 8. If they stay, add the `mcp-name` marker and `marketplace.json` to the tree, and spell out the `server.json` requirements — otherwise `claude plugin validate --strict` and the registry publish fail on facts the spec never states.

### X-5 — 🟡 Major — The confirm gate ignores the platform slot the research already identified

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 data flow step 6 lines 236–239; §6 tool table lines 259–276; §7 line 338; §10 M8 lines 468–470
* **Discrepancy:** `docs/study/…` §6.4 says: "Force approval on destructive writes with `_meta["anthropic/requiresUserInteraction"]: true` in the `tools/list` entry — Claude Code then prompts on every call even under `bypassPermissions`. **This is the right slot for our 6-digit confirm code.**" The spec never mentions `_meta`, `requiresUserInteraction`, or the per-tool `readOnlyHint` / `destructiveHint` / `idempotentHint` / `openWorldHint` annotations that the same pre-submission checklist (§6.3, line 446) requires for a social-posting plugin.
* **Rationale & Recommendation:** §4 (platform standards, anti-patterns). The annotations are free metadata on tools you are already declaring, they make the gate visible to the client rather than only to the server, and they satisfy part of the trust checklist that §10 M6 claims to meet.

### X-6 — 🟡 Major — The mapping table does not cover the scope §2 promises

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 lines 287–313; §2 lines 52–63; §8 test 1 lines 350–354
* **Discrepancy:** §2 promises message requests, spam box, group threads, follow-request approve/decline, thread title/hide/mute; the write-kind list (lines 278–285) promises `send_file`, `share`, `schedule`, `first_comment`, `bulk_delete_comments`, `toggle_comments`, `remove_follower`, `highlight`, `note`, `crosspost`, `collaborate`. The mapping table has no entry for `direct_pending_inbox`, `direct_spam_inbox`, `direct_pending_requests_preview`, `direct_request_approve`, `direct_thread_create`, `direct_thread_add_users`, `direct_thread_update_title`, `direct_thread_hide`, `direct_thread_mute`, `user_follow_requests`, `user_follow_request_approve`/`decline`, `media_save`/`media_unsave`, `photo_download*`, `story_download*`, `quicksnap_send`, `direct_send_cutout_sticker`, `media_note_delete`, `hashtag_unfollow`, `comment_unpin`, or `story_seen`/`story_like`. §8 test 1 then requires "mapping.py covers every feature in §6 exactly once", but §6 contains no enumerated feature list, so the test has nothing to assert against.
* **Rationale & Recommendation:** The whole design bets on `mapping.py` being the single change surface (A1, lines 403–405). It cannot be that until it covers every promised feature. Use the acceptance checklist as the machine-readable feature list and make test 1 iterate it. Uncovered features break silently. *Verification note:* every method name that **is** in the table was checked against the installed instagrapi 3.2.8 source and is real — the table is accurate, it is incomplete.

### ZO-11 — 🟢 Nit — `ig_preset` for one user

* **Affected Scope:** lines 213, 254, 273, 354
* **Discrepancy:** A caption/hashtag/first-comment template store with its own file, CRUD tool and tests, for templates an agent can hold in a memory file.
* **Rationale & Recommendation:** Cut in v1; it costs a component, a state file and a tool slot.

### ZO-12 — 🟢 Nit — Repo and doc drift around this spec

* **Affected Scope:** `README.md` lines 6 and 8; spec lines 30–37 and 98–100
* **Discrepancy:** `README.md` line 8 points to `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`, which does not exist (the file has `-v1-`), and line 6 says "Nothing implemented yet" while `pyproject.toml` and `src/as_ig_mcp/` exist. In the spec, criterion 1 refers to "the 13 formerly dead reads" (lines 98–100) but §1's table (lines 30–37) names only six probes, so the acceptance number is undefined inside the document.
* **Rationale & Recommendation:** Fix the path, the status line and the probe count.

### X-7 — 🟢 Nit — The dedicated venv is not git-ignored

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §4 lines 136–138; `.gitignore` line 1
* **Discrepancy:** `.gitignore` contains `venv/`, which matches a directory named exactly `venv` at any depth. §4 places the dedicated venv at `C:\Users\aswat\Projects\as-ig-mcp\.venv` — `.venv` does not match `venv/`. Phase 1 creates it inside the repo.
* **Rationale & Recommendation:** Add `.venv/` to `.gitignore`. Cheap now, expensive after the first commit.

### X-8 — 🟢 Nit — `ig_inbox` depends on an undefined "our style file"

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 line 262; §6 file tree lines 202–217; §6 state list lines 246–255; §8 test 1 lines 350–354
* **Discrepancy:** `ig_inbox` promises "optional suggested reply from our style file". The file tree has no style file, the state list does not name one, the test plan does not test it, and §10 lists no assumption about it. `docs/study/…` §10 open question 4 shows the style file arrived with comment auto-reply — a feature D5 (lines 441–442) parks as out of scope.
* **Rationale & Recommendation:** Name the artifact (path, format, owner) and add it to the tree and state list, or drop `suggest=true` from v1. A v1 tool that reads an undefined file fails at runtime, not at review.

### X-9 — 🟢 Nit — Confirm-code expiry is never stated

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §7 line 338; §8 test 1 line 352; §3 criterion 6 lines 109–110
* **Discrepancy:** §8 test 1 exercises an "expired code"; §7 says a wrong code is refused; but no expiry interval appears anywhere in the spec. `docs/study/…` §5.4 line 344 fixed it at 6 minutes.
* **Rationale & Recommendation:** State the number. Success criterion 6 and test 1 are otherwise unverifiable.

### X-10 — 🟢 Nit — `download` is a write kind in the checklist but not in the spec

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 tool table line 268 vs. write kinds lines 278–285; `docs/reviews/capability-checklist.md` R19
* **Discrepancy:** Checklist R19 checks `ig_write kind=download`, but the spec's write-kind list has no `download` and the §6 tool table puts download under `ig_story` (line 268).
* **Rationale & Recommendation:** Reconcile the two. One of them will fail the acceptance check as written.

### X-11 — 🟢 Nit — Dead references and a 13-vs-16 tool drift

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** header line 6; D1 lines 433–434; §2 lines 47–75
* **Discrepancy:** Line 6 points at "the Obsidian note `AS-IG-MCP/AS-IG-MCP - Capability Matrix.md`" and D1 says "The capability matrix is the acceptance list". Neither that note nor a "capability matrix" file exists in the repo. The real acceptance list is `docs/reviews/capability-checklist.md` (R1–R26, W1–W10, P1–P9). The study file is "Deep Study and Build Blueprint.md", whose §5.2 still specifies 13 tools while the spec specifies 16 — `ig_queue`, `ig_preset` and `ig_account` were added with no note of the change.
* **Rationale & Recommendation:** Fix the pointers and record the tool-count change. A fresh reader following line 6 or D1 lands nowhere, and the study's §5.7 vendor-to-our map no longer covers the surface.

---

# Reviewer: `egm-inventive-catalyst` (Inventive Catalyst)

**Contradiction-existence check:** genuine contradictions exist; step 0 does not return "No false compromise detected".

### IC-1 — 🟡 Major — File-shared state vs. one realtime subscriber per account

* **Affected Scope:** lines 146–148, 177–180, 315–325, 396
* **False Compromise:** The design treats "several Claude Code sessions share state via files" as free, then requires realtime, which needs one long-lived subscriber per account. Each session's stdio process opens its own MQTT subscription to the same Instagram account, so N sessions mean N sockets and duplicate events. The rejection of a daemon is deferred to "revisit only if concurrent sessions collide on rate limits" — realtime is what creates that collision.
* **Proposed Resolution:** **Extraction + Intermediary.** One socket owner writes `events.jsonl`; other sessions tail it with a cursor. A lock file with a heartbeat picks the owner and lets a survivor take over when the owner dies.
* **Secondary Liabilities:** One extra background process and its health check; event delivery now waits for a file poll interval; install steps get longer; a stale lock needs a recovery path.

### IC-2 — 🟡 Major — `direct_subscribe` may block the stdio responder

* **Affected Scope:** lines 315–320
* **False Compromise:** "On the main thread `rt.direct_subscribe()` runs once" reads as if subscribing were a cheap setup call. It reads `seq_id`/`snapshot_at_ms` from `direct_threads()` and then joins the MQTT stream; if it blocks, the stdio server stops answering tool calls, which breaks every other success criterion in §3. The spec never states whether the call blocks or returns.
* **Proposed Resolution:** **Extraction.** Keep the main thread a pure stdio responder. If the call blocks, run it inside the reader thread with a timeout and a readiness signal.
* **Secondary Liabilities:** A start race where early events are missed, and `ig_health` must distinguish "not yet subscribed" from "disconnected" or it will report false outages.

### IC-3 — 🔴 Blocker — The confirm code travels back through the agent, so the gate proves a two-step flow, not human consent

* **Affected Scope:** line 11, lines 71–72, 236–239, 255, 338; test plan line 351
* **False Compromise:** §1 promises "nothing published or sent without a human confirm code", but the 6-digit code is returned in the tool result to the same agent that asked for it. The agent can complete the write with no human present. The gate proves a two-step flow, not human consent. Related: pending confirmations are in-memory only (line 255) with no stated expiry, while §8 requires an "expired code" test.
* **Proposed Resolution:** **Inversion.** The code must not travel back through the agent: show it to the human out-of-band (a local console prompt or a local approval page) and let the agent report the outcome. Or **Beforehand Cushioning**: an allowlist of low-risk kinds (`react`, `mark_seen`) bypasses the gate while publish, DM and follow always take the human path. Move pending writes into the shared state file with an absolute expiry.
* **Secondary Liabilities:** A human round trip on every write; a local approval surface with its own failure modes; an expiry that can silently drop a pending write; an allowlist to maintain.

### IC-4 — 🟡 Major — Atomic writes stop torn files, not lost updates

* **Affected Scope:** lines 146–148, 249–250, 344
* **False Compromise:** Two sessions writing state at once produce "none (silent)" and "last writer wins for the cache; digest markers merge by timestamp". Atomic writes stop torn files, not lost updates, and merge-by-timestamp is undefined for markers rewritten wholesale (§6 step 5, lines 234–235, says the markers are *rewritten*). A lost marker update means a change is never reported — the flagship differentiator under-reports silently.
* **Proposed Resolution:** **Self-Service** with a single writer, or move markers and cache into one SQLite file with WAL so updates are transactional.
* **Secondary Liabilities:** SQLite becomes a runtime dependency and a migration away from the JSON files, plus lock contention and stale-lock recovery. The cheaper alternative is **Segmentation** — one marker file per entity, so concurrent sessions touch different files.

### IC-5 — 🟡 Major — Two schedulers, no rule for which one is used

* **Affected Scope:** lines 64–65, 122–124, 272, 340, 435–436 (D2)
* **False Compromise:** Two schedulers for one job with no stated rule for which one is used. The local queue only fires when the server runs, and the failure table resolves the missed slot by "publishes late, marks them, and tells the user". A post set for 9am can go out at 2pm after a wake.
* **Proposed Resolution:** **Beforehand Cushioning** with an explicit rule. Any post with a definite publish time goes to Instagram's native `schedule_at`; the local queue holds drafts and recurrence only, plus a lateness window — past the window, skip and notify.
* **Secondary Liabilities:** Skipped posts need a manual re-approve, two code paths to test, and recurrence still depends on the machine being awake.

### IC-6 — 🟡 Major — Success criterion 2 can be satisfied by a warm cache

* **Affected Scope:** lines 101–104, 233, 240–244, 379
* **False Compromise:** Criterion 2 ("read counts > 0 and stable across two consecutive calls") is satisfied by the 90-second cache, so a class that is dead upstream but has a warm cache entry still passes. The acceptance line "all 13 dead reads return data" (line 379) can be met without one live fetch.
* **Proposed Resolution:** Write the criteria against the bypass that already exists: one call with `fresh=true` (line 233) and one without, or lean on `ig_health`, which probes live (lines 240–244).
* **Secondary Liabilities:** Verification calls burn Instagram requests and hit rate limits, so the two calls must be spaced by the throttle delay.

### IC-7 — 🟡 Major — "Bump instagrapi" hands the fix to a third party's release schedule

* **Affected Scope:** lines 226–229, 287–313, 333, 403–405 (A1)
* **False Compromise:** "Endpoint breaks upstream again → bump instagrapi; no code change" hands the fix to a third-party maintainer's release schedule. The spec already owns the seam that fixes it locally: `mapping.py` plus the REST-variant fallback (lines 226–229), but that is described only as a runtime fallback, not as a place to patch.
* **Proposed Resolution:** **Beforehand Cushioning.** Declare `mapping.py` an explicit override point (feature → endpoint or query variant) and document the patch procedure in the README.
* **Secondary Liabilities:** The local patch layer drifts from upstream and must be reconciled on every bump, and it only helps where a REST variant exists.

### IC-8 — 🟡 Major — The full market superset is carried in v1 against an unstable upstream

* **Affected Scope:** lines 47–75, 96–133, 433–434 (D1), 468–470 (M8)
* **False Compromise:** v1 carries the full market superset plus white space — local publish queue with recurrence, presets, best-time tool, competitor benchmarking, per-post age comparison, realtime push — against an upstream that can change without notice. §5 defends the 16-tool split on schema-load cost, yet the same breadth lands as roughly 30 write kinds inside one `ig_write`. The measurable objective in §1 is much smaller: replace 13 dead reads and give a safe write path.
* **Proposed Resolution:** **Segmentation.** v1 keeps the reads that replace the dead vendor tools, the write gate with audit, and the polling digest. Realtime, queue/recurrence, presets, benchmarking and best-time move to v1.1 behind the flag mechanism D3 already uses. `mapping.py` stays the seam so each later feature is one entry.
* **Secondary Liabilities:** Some "nobody in the market has" features leave v1 and lose their edge, and the capability matrix needs a phase tag per row.

### IC-9 — 🟢 Nit — Publishing a ToS-violating session scraper to a public registry widens exposure

* **Affected Scope:** lines 73–75, 397, 461–464, 468–470
* **False Compromise:** v1 publishes to PyPI, the official MCP registry and the plugin marketplace, and asks that "a stranger can install and run it in one command", while M8 says the private-API liability is ours and the tool is a single local user on one Windows account with a DPAPI-bound session. Publishing to a public registry widens exposure from one user to everyone.
* **Proposed Resolution:** **Cheap Dispensables.** For v1, ship one channel (pip install from the repo, or a local plugin install). Keep registry entries as a later decision once the private-API path is settled.
* **Secondary Liabilities:** Early testers get no public install path, and the PyPI name and version reservation happens later.

### IC-10 — 🟢 Nit — `pycryptodomex` and the Python version pin contradict the spec

* **Affected Scope:** lines 138, 197, 411–412 (A4) versus `pyproject.toml` lines 10 and 16
* **False Compromise:** A4 says DPAPI through `ctypes` is enough and "no third-party crypto dependency needed", yet `pycryptodomex` is a declared dependency. §4 pins the venv to Python 3.14 while `pyproject.toml` declares `requires-python = ">=3.11"`, a support range nothing tests; instagrapi 3.2.8 predates 3.13 and 3.14.
* **Proposed Resolution:** Drop `pycryptodomex` (the stated mechanism needs no crypto package) or name the feature that needs it. Pin the venv to the interpreter instagrapi 3.2.8 is actually exercised on, and set `requires-python` to match.
* **Secondary Liabilities:** None beyond a smaller dependency surface and a narrower install range.

### IC-11 — 🟢 Nit — README points at a spec path that does not exist

* **Affected Scope:** `README.md` line 8 versus spec line 5
* **False Compromise:** The README links `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`. The file on disk and the spec's own canonical path is `2026-11-10-as-ig-mcp-v1-design.md`. The README also still says "Nothing implemented yet" while `pyproject.toml` and `src/as_ig_mcp/__init__.py` exist.
* **Proposed Resolution:** Fix the path and the status line in the README.
* **Secondary Liabilities:** None.

### X-12 — 🟡 Major — The realtime default directly contradicts the project's own research

* **Reviewer Lens:** `egm-inventive-catalyst`
* **Affected Scope:** lines 66–70, 125–126, 371–373, 429, 437–438, 449–451; `docs/study/…` §5.8 line 388 and §10 open question 3
* **False Compromise:** The study concluded "Realtime DM push | **not in v1** (private API has no push; the MQTT competitor needs a broker). Deferred deliberately", and listed it again as an open question ("Worth it only if DM latency matters daily"). The spec reversed that silently and now carries realtime as a headline white-space capability, a success criterion (§3 item 12), a live test (§8 item 9), a Phase 7 deliverable and a risk with its own mitigation — while D3 and A9 simultaneously ship it behind a flag with polling as the default. With the flag off, criterion 12 and test 9 cannot pass, because the polling digest cannot produce the typing/seen events test 9 requires (§6 line 321 lists the event kinds).
* **Proposed Resolution:** **Beforehand Cushioning**, applied to exactly one transport. Ship polling as the only v1 path and move the socket into a separate, explicitly-flagged module with its own acceptance criteria; or make the socket the default and treat polling as the cushioning path it already is. Either way, state the decision once and let §2, §3, §8 and Phase 7 agree with it.
* **Secondary Liabilities:** A flag adds a configuration surface, a second code path to keep alive and a class of launch-dependent defect. Shipping the socket by default puts an always-on background thread and a persistent connection in every Claude Code session, with the reconnect-backoff surface §6 line 320 already admits instagrapi does not provide.

### X-13 — 🟡 Major — Polling is not an equivalent fallback, and it is called one

* **Reviewer Lens:** `egm-inventive-catalyst`
* **Affected Scope:** lines 125–126, 234–235, 269, 315–325, 335–336
* **False Compromise:** The design treats polling as a drop-in substitute for the socket (§7 line 335: "reconnect with backoff; fall back to polling"). It is not a substitute: of the eight event kinds §6 line 321 lists, six (`receive`, `thread_update`, `iris`, `direct`, `typing`, `seen`) exist only on the socket, and §7 line 336's degradation rule — unknown events recorded as `unknown`, "the digest still works" — is a claim about the socket path, not about polling.
* **Proposed Resolution:** State what the polling digest actually delivers (fetch-and-diff over the same endpoints) and stop describing it as a fallback for realtime events. If the event kinds matter, the socket is not optional and X-12 must be resolved in favour of the socket.
* **Secondary Liabilities:** The "what changed" promise weakens in v1 and the marketing in §2 line 66 must be reworded; a user who waits on `wait_s` for a typing indicator will never get one.

---

# Cross-Reviewer Synthesis

Both lenses land on the same conclusion: **the root problem is solved correctly; the surrounding scope is over-claimed.**

The defect diagnosis is measured, the surface choice (private API over Graph, browser automation, a shim) is defended with reasons, and the mapping table was independently verified line by line against the installed instagrapi 3.2.8 source — every method name in it exists. That is a strong spec at the level of *why* and *how*.

The failures are at the level of *what gets built and what gets promised*.

**Four clusters account for most of the 39 findings.**

1. **The v1 surface is much larger than the stated job.** ZO-1, ZO-2, IC-8, X-2 and X-11 all say the same thing from different directions: the job is one account on one machine (line 40), the build is a market superset (lines 49–70), and two of the claimed differentiators are contradicted by the project's own market study. The consistent recommendation is the same — cut v1 to the dead reads, DM read, publish, comment, follow/unfollow, the confirm gate with audit, and the polling digest; move the rest behind the flag mechanism D3 already defines.

2. **Three promises the architecture cannot keep.** The local publish queue has no trigger (X-1, ZO-4, IC-5). Realtime is a mandatory acceptance criterion in a configuration where it is switched off (ZO-3, ZO-8, IC-1, IC-2, X-12, X-13). The digest's concurrency safety rests on a merge that a whole-file atomic write cannot perform (ZO-9, IC-4). Each is fixable by *removing* a promise or *adding* one trigger — not by adding code.

3. **The trust model has a hole.** IC-3 is the sharpest single finding in the review: the 6-digit code is returned in the tool result to the same agent that requested it, so the gate proves a two-step flow rather than human consent, while §1 promises "nothing published or sent without a human confirm code". ZO-6 (gate applied to `mark_seen` and `react`), X-5 and X-9 sit around it. The fix is a combination the platform already supports: `_meta["anthropic/requiresUserInteraction"]`, per-tool `destructiveHint`/`idempotentHint`, an out-of-band human prompt for the code, and a low-risk allowlist.

4. **The plan does not match the repo's conventions or its own research.** §9 "Agent implements" contradicts `as-ig-orchestrator/SKILL.md` (X-3). The packaging facts the registry and marketplace require — public repo, `mcp-name` marker, `io.github.` prefix, `marketplace.json` — were identified in the study and dropped from the spec (X-4). The platform mechanisms for the confirm gate were likewise identified and dropped (X-5). `pycryptodomex` and the Python pin contradict A4 and `pyproject.toml` (ZO-7, IC-10). The pointers drift (ZO-12, X-11, IC-11), `.venv` is not git-ignored (X-7), and the `ig_write kind=download` discrepancy will fail the acceptance check as written (X-10).

**Recommended order of work, largest return first.**

1. Decide the three broken promises — queue trigger, realtime default, digest concurrency — and edit the spec so each capability has exactly one stated mechanism. *Blocking for Phase 6, 7 and the digest.*
2. Re-cut §2 and §3 against the study: drop or justify best-time, competitor benchmarking and the superset claim; make realtime's default explicit; fix criterion 2 so it cannot be satisfied by a warm cache (IC-6).
3. Fix the trust model: out-of-band code delivery or the platform's `requiresUserInteraction`, a low-risk allowlist, a stated code expiry, and pending writes moved out of memory with an absolute deadline.
4. Add the platform metadata to §6 and the packaging facts to §4 and Phase 8.
5. Rewrite §9 to the orchestrator skill's loop; extend `mapping.py` to the acceptance checklist and make §8 test 1 iterate the checklist rather than an unstated feature list.
6. Fix the pointers, the tool-count drift, the `download` kind, the style file and `.gitignore`.

**What passed and should not be re-litigated:** context sufficiency, the root-cause diagnosis, the surface choice, the rejection of a shim and of browser automation, the file-based state model as a direction, the 90-second cache, the idempotency key, the audit journal, the whole mapping table, and the decision to pin instagrapi rather than fork it.

**Residual risk if none of this changes:** Phase 6 (queue), Phase 7 (realtime) and Phase 8 (packaging) each contain a check the current design cannot pass, and the write gate's headline promise is weaker than stated — so the build stops at the first one, and the cause is diagnosed late.

**Not checked:** the delegated reviewers did not read `docs/study/` or the full capability checklist, so their scope findings rest on the spec text alone; the synthesis pass closed that gap for X-2 and X-11 but not exhaustively. The `.venv` had no instagrapi installed at review time, so the Python 3.14 and `direct_subscribe` blocking claims (IC-2, IC-10) are unverified against the library. No live Instagram call was made.
