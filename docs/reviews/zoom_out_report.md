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
| `egm-zoom-out` | completed | 2 | 31 |
| `egm-inventive-catalyst` | completed | 2 | 20 |

Both reviewers were dispatched as fresh subagents of their registered types (`egm:egm-zoom-out`, `egm:egm-inventive-catalyst`) with the target path, the resolved line ranges, their persona file, the standard file and the empty GoldfishContext list. Both were strictly read-only; neither wrote to the target document.

Findings marked **ZO-n** are the zoom-out reviewer's. Findings marked **IC-n** are the inventive-catalyst reviewer's. Findings marked **X-n** were added during synthesis after verifying each one against `docs/study/`, `docs/reviews/capability-checklist.md`, `.claude/skills/as-ig-orchestrator/SKILL.md`, `.gitignore`, `pyproject.toml`, `src/as_ig_mcp/mapping.py`, the installed instagrapi 3.2.8 source, `C:\Users\aswat\Projects\ig-mcp-probe`, `C:\Users\aswat\Downloads\Projects\everyhand-tests` and `C:\Users\aswat\Downloads\Projects\TradeMCP`. X-n findings are attributed to the lens that raised them.

## Severity Summary

| Severity | Zoom-out | Inventive catalyst | Total |
| --- | --- | --- | --- |
| 🔴 Blocker | 2 | 2 | 4 |
| 🟡 Major | 18 | 13 | 31 |
| 🟢 Nit | 11 | 5 | 16 |
| **Total** | **31** | **20** | **51** |

---

# Reviewer: `egm-zoom-out` (Skeptical Architect)

Standard applied: §0 context sufficiency · §1 root problem focus · §2 YAGNI, premature optimization, minimalist data flow, architectural dead-ends · §3 anti-weeds, right placement · §4 codebase and platform reuse, pattern consistency, anti-patterns.

**Context sufficiency (§0): passed.** The objective (line 11), the user (line 17), the measured root cause (lines 19–38) and the environment (lines 134–156) are all present. The failures below are failures of the *plan*, not of the *why*.

### ZO-1 — 🔴 Blocker — Scope is market parity, not the stated job

* **Affected Scope:** lines 39–43 vs. lines 49–63 and 278–285
* **Discrepancy:** The job is written as "on this machine, for this one business account" (lines 40–41). Two lines later the same paragraph adds "cover every capability the whole market covers, plus the ones nobody covers" (lines 42–43), and §2 turns that into 16 tools, roughly 40 capabilities and roughly 35 write kinds. One user, one account, one consumer does not need cutout stickers, quicksnap, IGTV, bulk comment delete, crosspost to Threads, collaboration invite, AI label, account category, close-friends, hashtag follow, inbox notes and on-post notes in v1. Every kind is a mapping entry, a confirm-gate branch, an audit case and an Instagram-side risk. Nothing in the document says the account owner uses any of these from Claude Code.
* **Rationale & Recommendation:** Under §2 (YAGNI) the v1 surface should be the dead reads, DM read, publish, comment, follow/unfollow — roughly the 13 tools of the study blueprint, not a market census. Cut the rest until a real need shows up. Note the reviewer's own caveat: if the market-parity clause was an explicit user requirement, this becomes a scope-confirmation question rather than a YAGNI finding — the spec should say explicitly which it is, because §1 currently asserts both in one paragraph.

### ZO-2 — 🔴 Blocker — Distribution as v1 scope contradicts the problem statement

* **Affected Scope:** lines 40–41 vs. lines 73–75 and 397
* **Discrepancy:** Nothing in §1 asks for a PyPI package, an official MCP registry entry, a Claude plugin marketplace entry, `server.json`, `plugin.json`, `claude plugin validate --strict` or a README of at least 40 words. The stated requirement is "this machine, this one account". Phase 8's acceptance test, "a stranger can install and run it in one command" (line 397), is a new requirement invented by the plan. For a server whose session is DPAPI-bound to one Windows user and whose login needs an emailed code, a stranger cannot run it in one command. The registry and marketplace steps are also a public, semi-permanent commitment that the doc's own M8 (line 468) says carries ToS liability. `docs/study/…` line 420 also notes a marketplace entry needs a public repo, which this repo is not.
* **Rationale & Recommendation:** §1 (root problem focus). Publishing is a distribution decision, not part of the defect fix. Move Phase 8's registry and marketplace work to a v1.1 phase, keeping only README, LICENSE and a local install as v1 deliverables — or state what the stranger is expected to do without a session.

### ZO-3 — 🟡 Major — Realtime is a second message-sync client, for a push nobody consumes

* **Affected Scope:** lines 315–325, 396, 429, 449–451
* **Discrepancy:** The spec's own assumptions say the payload shape may change without notice, that it ships behind a flag with polling as default (lines 427–429), and that instagrapi has no reconnect logic so the server must add reconnect-with-backoff, a ping watchdog and its own event normalisation (lines 320–323). That is the single largest new-code item in the project, and the polling digest already ships in v1 and already answers "what changed" (line 269). You are paying the full complexity of the most fragile surface in the product — your own M2 says so — for a code path that is off by default.
* **Rationale & Recommendation:** Defer `realtime.py`, `events.py` and the `wait_s` path to v2 and ship the polling digest alone; it already satisfies criterion 7 (lines 111–112). This is also the cheapest way to dissolve ZO-8 and X-12 together.

### ZO-4 — 🟡 Major — Two scheduling systems with two sources of truth

* **Affected Scope:** lines 64–65, 212, 272, 340, 354, 435–436
* **Discrepancy:** Native `schedule_at` plus a local queue with recurrence, overdue detection and recurrence-maths tests. The native one is better — server-side, survives sleep, no local state to corrupt — while the local queue adds a file, a scheduler, a failure mode ("item overdue at next start", line 340) and a test.
* **Rationale & Recommendation:** Ship `schedule_at` in v1; add the local queue when drafts and recurrence are actually requested. See also IC-5, which reaches the same conclusion via a different route, and X-1 for the deeper problem — the local queue has no trigger at all.

### ZO-5 — 🟡 Major — `mapping.py` cannot be the fix if the stated remedy is a version bump, and the table is duplicated in the spec

* **Affected Scope:** lines 205–206, 287–313, against line 333 and A1 lines 403–405
* **Discrepancy:** `mapping.py` is described as "THE table … the single place to change when Instagram moves" (lines 205–206, 287), but the doc's own remedy for a broken endpoint is "bump instagrapi; no code change" (line 333) and A1 says the fix is "a version bump — `mapping.py` exists precisely so that absorbing a change is one file" (lines 403–405). These cannot both be true: if the fix is a version bump, the fix is not in your table. The table is a second, hand-maintained index of a library that already indexes itself, and it will drift from the pinned version it claims to stabilise. Separately, the spec then lists roughly 60 method names in the document body (lines 288–313) — a third copy, written at the wrong altitude for a design section.
* **Rationale & Recommendation:** §3 (anti-weeds) and §4 (codebase reuse — the library is the index). Either drop the table and call the instagrapi method directly, with the fallback in `client.py` where §6 line 228 already puts it, or state precisely which class of breakage it absorbs that a version bump cannot — "GraphQL → REST fallback per feature" is a real and different concern from method renames. Keep the rule in the spec; keep the table in `mapping.py`. The drift has already begun: `src/as_ig_mcp/mapping.py` exists as a feature-keyed `FEATURE_METHODS` dict with the same content. Add one offline test that every name in the table resolves on the installed client, so typos fail before Phase 2 ships.

### ZO-6 — 🟡 Major — The confirm gate covers trivial writes

* **Affected Scope:** lines 41, 278–285, 338
* **Discrepancy:** The requirement is "nothing published or sent without a human confirm code" (line 41). The design applies the gate to `mark_seen`, `react` and `toggle_comments` too — two extra round trips and a 6-digit code to react to a message.
* **Rationale & Recommendation:** Gate send, publish, comment, delete, follow/block/report and crosspost; run `mark_seen` and `react` directly. This is the same allowlist IC-3 proposes as a cushioning measure.

### ZO-7 — 🟡 Major — `pycryptodomex` contradicts the spec's own assumption, and the pins do not match

* **Affected Scope:** lines 138 and 197 vs. A4 lines 411–412; `pyproject.toml` lines 10 and 13–17
* **Discrepancy:** §4 pins `pycryptodomex`; A4 says "DPAPI through `ctypes` is enough to protect the session cookie; no third-party crypto dependency needed". `pyproject.toml` line 16 already ships it as a direct dependency — and it does not need to be: instagrapi 3.2.8 already requires it (`instagrapi-3.2.8.dist-info/METADATA`: `Requires-Dist: pycryptodomex<4,>=3.23.0`), so it should be dropped from the direct dependency list. Additionally, §6 line 197 and §4 line 138 describe the dependency set as "pinned", but `pyproject.toml` line 15 leaves `mcp` unpinned, and `pyproject.toml` line 10 declares `requires-python = ">=3.11"` while §4 line 137 pins the venv to Python 3.14 — a support range nothing tests, and instagrapi 3.2.8 predates 3.13/3.14.
* **Rationale & Recommendation:** Drop `pycryptodomex` from the direct deps, drop or justify it in A4, pin `mcp`, and set `requires-python` to the interpreter instagrapi 3.2.8 is actually exercised on.

### ZO-8 — 🟡 Major — File-shared state versus one realtime thread per process

* **Affected Scope:** lines 146–148 vs. 315 and 344
* **Discrepancy:** The design promises shared file state because several Claude Code sessions run at once (lines 146–148), yet realtime is "one daemon thread per server run" (line 315). Two sessions means two socket subscriptions, two ping watchdogs, two writers to `events.jsonl`, and the failure row "digest markers merge by timestamp" (line 344) with no defined mechanism. The spec has already rejected the shared daemon (lines 177–180).
* **Rationale & Recommendation:** Pick one: realtime stays off by default, or it becomes a single shared process. See IC-1 for the same contradiction from the contradiction-elimination lens.

### ZO-9 — 🟡 Major — The cache layer duplicates the digest and is never invalidated by a write

* **Affected Scope:** lines 233, 235–236, 246–255; §3 criteria 2, 5, 7 (lines 101–112)
* **Discrepancy:** Two problems. First, `cache.json` (per-endpoint TTL) and `digest.json` (last-seen markers) are two overlapping staleness mechanisms for the same job — both answer "what did I last see" — with different invalidation rules and a silent last-writer-wins race between sessions (line 344). The stated purpose of the cache is throttling (line 151), which instagrapi's delay range plus the digest's own fetch set already partly covers. Second, §6 never says a write invalidates the cache. Criterion 5's verification — "read the thread afterwards and finding nothing new" (lines 106–108) — can therefore read the pre-write cached value and pass even if the write went through, which removes the acceptance test for the one property the whole safety story rests on. Criterion 2 ("counts > 0 and stable across two consecutive calls") is likewise satisfied by the cache rather than by a live endpoint.
* **Rationale & Recommendation:** §2 (minimalist data flow). Write-through or invalidate on write, and either drop the cache or drop the digest's overlap. Pairs with IC-4 (the concurrency defect inside the digest half) and IC-16 (the cache hollowing out the digest's own criterion).

### ZO-10 — 🟡 Major — "Capabilities nobody in the market has" mostly re-lists native Instagram features

* **Affected Scope:** lines 66–70
* **Discrepancy:** Best-post ranking is Instagram's own `insights_media_feed_all` (lines 290, 120–121). Best-time-to-post is Instagram's own feature and duplicates `ig_insight kind=best` (line 270). Per-post comparison by age is a query over the same insights endpoint. Competitor benchmarking has no tool, no component and no mapping anywhere in §6 — scope that was never architected.
* **Rationale & Recommendation:** Re-label these as "existing endpoint, exposed" so a reader knows which are real work. See X-2, which shows the project's own market research already contradicts the "nobody has this" framing.

### X-1 — 🟡 Major — The local publish queue has no mechanism that can fire it

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §2 lines 64–65; §3 criterion 11 lines 122–124; §6 line 212 and line 272, state line 253; §7 line 340; §9 Phase 6 line 395; D2 lines 435–436
* **Discrepancy:** `ig_queue` promises "list, schedule, cancel, recurring posts". The architecture has no timer, no trigger, no OS-level scheduler and no long-lived process. §4 line 144 sets the transport to stdio (process lifetime = Claude Code session lifetime), and §5 lines 177–180 explicitly reject "a separate long-running daemon for v1". §7 line 340 concedes the consequence — an overdue item is "item overdue at next start" and "publishes late", i.e. a post fires only if a human opens Claude Code and calls a tool. Recurring posts, the one thing the local queue exists for that Instagram's own `schedule_at` cannot do, never publish on time. §8 test 10 (lines 374–375) only asserts the item "sits in `queue.json`" and can be cancelled; it never asserts that a post is published at the scheduled time.
* **Rationale & Recommendation:** A capability promised in scope, in the tool surface, in the success criteria and in the acceptance checklist (W7) that cannot execute is a false promise, and an architectural dead-end: the design deliberately removed the only component that could execute it. Ship only Instagram's native `schedule_at` in v1 (already in the mapping, line 299) and drop the local queue, or name the runner — Windows Task Scheduler is the platform-native answer on Windows 11 — and accept the process cost the spec rejected. Also change §8 test 10 to assert publication, not file presence.

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
* **Rationale & Recommendation:** §4 (platform standards, anti-patterns). The annotations are free metadata on tools you are already declaring, they make the gate visible to the client rather than only to the server, and they satisfy part of the trust checklist that §10 M6 claims to meet. *Reuse, verified:* the author's own sibling MCP server already implements exactly this — `C:\Users\aswat\Downloads\Projects\TradeMCP\src\trademcp\tools\common.py` lines 32–42 defines `tool_annotations(title)` returning `ToolAnnotations(title=..., read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)`. Copy that pattern; do not design a new one.

### X-6 — 🟡 Major — The mapping table does not cover the scope §2 promises

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 lines 287–313; §2 lines 52–64; §6 tool table lines 261–276; §8 test 1 line 351
* **Discrepancy:** Missing from the table but promised in scope: message requests (`direct_pending_inbox`, `direct_requests`, `direct_pending_approve`), spam box (`direct_spam_inbox`), group threads (`direct_thread_create`), story viewers and likers (`story_viewers`, `story_likers` — promised at §2 line 55 and line 268; the table only has `user_stories_web`), collections and liked (`collections`, `liked_medias`), guides (`user_guides_v1`), quicksnap (`quicksnap_send`), IGTV (`igtv_upload`), cutout sticker (`photo_upload_to_cutout_sticker`), share (`direct_media_share`), and follow-request approve/decline (`user_follow_request_approve` / `_decline`, promised at line 265). All of these exist in the installed instagrapi 3.2.8 — each mixin was checked. The test plan cannot catch this: line 351 asserts "mapping.py covers every feature in §6 exactly once", which tests the table against itself, not against §2.
* **Rationale & Recommendation:** The whole design bets on `mapping.py` being the single change surface (A1, lines 403–405). It cannot be that until it covers every promised feature. Use the acceptance checklist (`docs/reviews/capability-checklist.md`, R1–R26 / W1–W10 / P1–P9) as the machine-readable feature list and make test 1 iterate it. Uncovered features break silently. *Verification note:* every method name that **is** in the table was checked against the installed instagrapi 3.2.8 source and is real — the table is accurate, it is incomplete. IC-12 is the exception that matters: one of the names that resolves is a mutator, not a reader.

### X-14 — 🟡 Major — Tool-table promises with no backing method: "quota" and "linked accounts"

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 tool table lines 261, 275–276; §2 lines 86–88; `docs/study/…` line 284
* **Discrepancy:** `ig_status` promises "quota" (line 261), but the installed instagrapi 3.2.8 has **no quota method at all** — the whole package was searched and the study says the same at line 284: "Publishing quota / limit endpoint — limits are implicit 429s". Any quota value the tool prints would be fabricated. Separately, both `ig_session` and `ig_account` advertise "linked accounts" (lines 275–276) while §2 lines 86–88 put multi-account out of scope, "Paused by user on 2026-11-10".
* **Rationale & Recommendation:** A tool that prints a fabricated number is worse than a tool that omits it — the caller cannot tell the difference. Drop "quota" from `ig_status` and report rate-limit state from the 429 the client actually sees, or drop "linked accounts" from both tools and restore multi-account to scope if it is genuinely wanted. The same sweep should be run over every cell of the §6 tool table: each promised capability needs a named method behind it.

### X-15 — 🟡 Major — The repo relocation silently dropped the one-login rule, which is M1's exact concern

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §4 lines 151–153; §9 Phase 7 line 396; §10 A1–A2 lines 403–408; `docs/study/…` lines 358, 499, 530
* **Discrepancy:** The spec relocates the implementation from the repo the study decided on (study line 530: "The existing `everyhand-tests` repo, new component `mcp/as-ig-mcp/`") to a new local repo, and drops the study's Phase 7 ("Inject our session into the vendor daemon", study line 499) and its §5.6 one-login rule (study line 358: "One — inject our session into the vendor daemon"). The consequence is not stated anywhere: the account may end up with **two separate Instagram sessions** — one for the vendor binary, one for us — which is exactly what M1 (account flagged for scripted use, line 446) is about. Also unrecorded: the tool count moved 13 → 16, and realtime moved from "deferred deliberately" to "in scope". The D-list (lines 431–442) is the place for those, and it does not mention them.
* **Rationale & Recommendation:** §1 (root problem focus) and §4 (pattern consistency). Two live sessions against one account roughly doubles the scripted-use surface that M1 is trying to reduce. State in §4 whether the vendor server keeps running against the same account, and if it does, say how the session is shared or why the risk is accepted. Add the tool-count change and the realtime reversal to the D-list.

### X-16 — 🟡 Major — Two reusable assets on this machine are ignored by the plan

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §9 Phase 1 line 390; §4 lines 152–155; §10 M5 line 458
* **Discrepancy:** §4 (codebase reuse) requires the design to search for components that already solve the problem. Two exist. First, `C:\Users\aswat\Projects\ig-mcp-probe` holds the probe work this spec's measurements came from — `probe.py`, `probe_reads.py`, `ig_probe.py`, `ig_328_test.py`, `ig_login_test.py`, `ig_insights_test.py`, `white_space_test.py`, `side_by_side.py` — including the canonical-method probes and a working session. Phase 1 should promote them, not rewrite them. Second, `C:\Users\aswat\Downloads\Projects\everyhand-tests\tools\check_no_secrets.py` is a working repository secret scanner, directly relevant to "the session cookie is a live credential — never in git" (line 155) and to M5 (line 458); the spec's Phase 1 creates a repo and never mentions a secret check. A third reusable pattern: `TradeMCP/src/trademcp/` is the author's established layout for exactly this kind of server (`app.py` holding the server instance, a `tools/` package, `config.py`), against the spec's fourteen-module tree (§6 lines 202–217).
* **Rationale & Recommendation:** §4 (codebase reuse, pattern consistency, platform standards). The probe repo is the cheapest possible source of the canonical-method map and the live session fixture for offline tests; the secret scanner is a one-line CI addition against a stated risk; the TradeMCP layout is the house style for a stdio MCP server. The spec's module count (fourteen) and its omission of the scanner are both avoidable.

### ZO-11 — 🟢 Nit — `ig_preset` for one user

* **Affected Scope:** lines 213, 254, 273, 354
* **Discrepancy:** A caption/hashtag/first-comment template store with its own file, CRUD tool and tests, for templates an agent can hold in a memory file.
* **Rationale & Recommendation:** Cut in v1; it costs a component, a state file and a tool slot.

### ZO-12 — 🟢 Nit — Repo and doc drift around this spec

* **Affected Scope:** `README.md` lines 6 and 8; spec lines 3, 30–37 and 98–100
* **Discrepancy:** `README.md` line 8 points to `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`, which does not exist (the file has `-v1-`), and line 6 says "Status: spec approved pending" while the spec header says "Status: Draft for user review". The study (line 20) repeats the wrong spec path. In the spec, criterion 1 refers to "the 13 formerly dead reads" (lines 98–100) but §1's table (lines 30–37) names only six probes, so the acceptance number is undefined inside the document.
* **Rationale & Recommendation:** Fix the path, the status line and the probe count.

### X-7 — 🟢 Nit — The dedicated venv is not git-ignored

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §4 lines 136–138; `.gitignore` line 1
* **Discrepancy:** `.gitignore` contains `venv/`, which matches a directory named exactly `venv` at any depth. §4 places the dedicated venv at `C:\Users\aswat\Projects\as-ig-mcp\.venv` — `.venv` does not match `venv/`. Phase 1 creates it inside the repo.
* **Rationale & Recommendation:** Add `.venv/` to `.gitignore`. Cheap now, expensive after the first commit.

### X-8 — 🟢 Nit — `ig_inbox` depends on an undefined "our style file"

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 line 262; §6 file tree lines 202–217; §6 state list lines 246–255; §8 test 1 lines 350–354
* **Discrepancy:** `ig_inbox` promises "optional suggested reply from our style file". The file tree has no style file, the state list does not name one, the test plan does not test it, and §10 lists no assumption about it. `presets.py` (line 213) is caption/hashtag/first-comment templates, a different thing. `docs/study/…` §10 open question 4 shows the style file arrived with comment auto-reply — a feature D5 (lines 441–442) parks as out of scope.
* **Rationale & Recommendation:** Name the artifact (path, format, owner) and add it to the tree and state list, or drop the promise. A v1 tool that reads an undefined file fails at runtime, not at review.

### X-9 — 🟢 Nit — Confirm-code expiry is never stated

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §7 line 338; §8 test 1 line 352; §3 criterion 6 lines 109–110
* **Discrepancy:** §8 test 1 exercises an "expired code"; §7 says a wrong code is refused; but no expiry interval appears anywhere in the spec. `docs/study/…` §5.4 line 344 fixed it at 6 minutes.
* **Rationale & Recommendation:** State the number. Success criterion 6 and test 1 are otherwise unverifiable. See IC-18 for the same gap plus the missing attempt cap.

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

### X-17 — 🟢 Nit — The `mcp` dependency is unpinned, and `mcp` 2.x removed `FastMCP`

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §4 line 138; §6 line 197; `pyproject.toml` line 15
* **Discrepancy:** The `mcp` dependency has no version, although the same sentence claims the deps are pinned. That matters on this machine: the `mcp` 2.x line removed `FastMCP` (`mcp/server/fastmcp.py` now raises "Removed in mcp 2: `FastMCP` is now `mcp.server.mcpserver.MCPServer`"). The author's other MCP server already uses the surviving API and pins `mcp>=2.3,<3` (`TradeMCP/pyproject.toml` line 15; `TradeMCP/src/trademcp/app.py`).
* **Rationale & Recommendation:** Reuse that pattern — pin `mcp>=2.3,<3` and build on `mcp.server.mcpserver.MCPServer`. An unpinned `mcp` will resolve to 2.x on a fresh install and fail at import.

### X-18 — 🟢 Nit — `ig_search kind=place` has no coordinate source

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §3 criterion 15 line 131; §6 line 266; `docs/study/…` lines 67 and 531
* **Discrepancy:** `ig_search kind=place` needs coordinates — the vendor errors with "lat and lng required for places" (study line 67) and the study's decision log (line 531) settled on `IG_PLACES_LAT` / `IG_PLACES_LNG` env vars, unanswered. The spec never says where coordinates come from, so criterion 15 covers a feature with no configuration path.
* **Rationale & Recommendation:** Carry the env-var decision into §4 and §6, or move places into the named-out list. `fbsearch_places` also has a hardcoded default lat/lng in the library, which is New York — worth not shipping silently.

### X-19 — 🟢 Nit — The server id is stated two ways

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §1 line 9 vs. §3 criterion 14 line 130
* **Discrepancy:** The server id is `as-ig` (line 9); criterion 14 checks for "`instagram-fixed`/`as-ig`" in `claude mcp list`.
* **Rationale & Recommendation:** Pick one name. The criterion is the thing that gets run, and it cannot pass while it accepts two.

### X-20 — 🟢 Nit — Fourteen modules for one account's server, against the author's own layout

* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** §6 file tree lines 196–218
* **Discrepancy:** Fourteen modules plus 16 tools for one account's server. `state.py` (line 217) holds only paths; `audit.py`, `events.py`, `presets.py` are each a few dozen lines. The author's established layout for exactly this kind of server is `src/<pkg>/app.py` (one server instance) plus a `tools/` package plus `config.py` (`TradeMCP/src/trademcp/`).
* **Rationale & Recommendation:** §4 (pattern consistency). Fewer files, same separation. Revisit the module count once the v1 scope is cut — the modules that exist for realtime, queue and presets disappear with their features.

---

# Reviewer: `egm-inventive-catalyst` (Inventive Catalyst)

**Contradiction-existence check:** genuine contradictions exist; step 0 does not return "No false compromise detected".

### IC-12 — 🔴 Blocker — The notifications "read" maps to four methods that mute notifications

* **Affected Scope:** §6 mapping table lines 300–301; §6 tool surface line 267; §6 health probe lines 240–244; §3 criterion 1 lines 98–100; §2 safety lines 71–72
* **False Compromise:** The spec treats `mapping.py` as a flat "feature → canonical instagrapi method" table, and the read tools and the health probe resolve through that same table. Nothing in the table says which entries mutate. The damage is at lines 300–301, where the read for `notifications` maps to `notification_likes`, `notification_comments`, `notification_new_follower`, `notification_user_tagged`. In instagrapi 3.2.8 all four are **settings mutators, not readers**: each calls `notification_settings(content_type, setting_value)`, which POSTs to `notifications/change_notification_settings/`, and each wrapper defaults to `setting_value="off"` (`instagrapi/mixins/notification.py` lines 43–53, 107–123, 143, 161, 215). So `ig_feed kind=notifications` (line 267) and the `notifications` class in `ig_health` (line 243) would **mute the account's like, comment, follower and tag notifications**. The mutation leaves through the read path, never touching the confirm gate in `writes.py`, which breaks §3 criterion 5 outright. The library has no notification reader at all; `news_inbox_v1` (`instagrapi/mixins/account.py` lines 399–412) hits `news/inbox/` and returns the stories/news tray.
* **Proposed Resolution:** **Extraction.** Split the table into two named sections inside `mapping.py`, `READ_METHODS` and `WRITE_METHODS`, so the tool layer resolves a read tool only against `READ_METHODS` and a write only against `WRITE_METHODS` through `writes.py`. A read with no read method becomes an explicit gap rather than a silent mutation. Then source a real reader for the notifications feature, or move it to the named-out list in §2 alongside the other exclusions, so §3 criterion 1 stops counting a class it cannot actually read.
* **Secondary Liabilities:** Every one of the roughly sixty rows needs a read or write tag before the first call goes out. The health probe needs a read-tagged method per class or it must report "no read-only probe exists" for that class. One named capability may drop out of v1 scope, which touches §2 and D1. A second, weaker gate at the resolve step is still worth keeping, so a future mis-tagged row is refused rather than executed.
* **Verification (this review):** confirmed directly against the installed `instagrapi 3.2.8`. Every method in `instagrapi/mixins/notification.py` is a mutator posting to `notifications/change_notification_settings/`; there is no notification reader anywhere in the package. The error originates upstream in `docs/study/…` line 253, which lists these names under "Notifications (~30 **readers**)" — the spec inherited the mistake.

### IC-3 — 🔴 Blocker — The confirm code travels back through the agent, so the gate proves a two-step flow, not human consent

* **Affected Scope:** line 11, lines 71–72, 236–239, 255, 338; test plan line 351
* **False Compromise:** §1 promises "nothing published or sent without a human confirm code", but the 6-digit code is returned in the tool result to the same agent that asked for it. The agent can complete the write with no human present. The gate proves a two-step flow, not human consent. Related: pending confirmations are in-memory only (line 255) with no stated expiry, while §8 requires an "expired code" test.
* **Proposed Resolution:** **Inversion.** The code must not travel back through the agent: show it to the human out-of-band (a local console prompt or a local approval page) and let the agent report the outcome. Or **Beforehand Cushioning**: an allowlist of low-risk kinds (`react`, `mark_seen`) bypasses the gate while publish, DM and follow always take the human path. Move pending writes into the shared state file with an absolute expiry.
* **Secondary Liabilities:** A human round trip on every write; a local approval surface with its own failure modes; an expiry that can silently drop a pending write; an allowlist to maintain.

### IC-1 — 🟡 Major — File-shared state vs. one realtime subscriber per account

* **Affected Scope:** lines 146–148, 177–180, 315–325, 396
* **False Compromise:** The design treats "several Claude Code sessions share state via files" as free, then requires realtime, which needs one long-lived subscriber per account. Each session's stdio process opens its own MQTT socket to Instagram with the same device id and sessionid, so N sessions mean N live sockets and N subscribe calls, and each one appends the same DM events to the same shared `events.jsonl` (line 251). The digest at line 234 and the `wait_s` tail at line 269 then see duplicates, and there is no event id or dedupe rule anywhere in the spec. The realtime class is also the one place Instagram sees the tool's real behaviour, and M1 names an account block as the top risk.
* **Proposed Resolution:** **Extraction + Intermediary.** One socket owner writes `events.jsonl`; other sessions tail it with a cursor. A lock file with a heartbeat picks the owner and lets a survivor take over when the owner dies.
* **Secondary Liabilities:** The lease file needs a heartbeat and a stale-owner takeover, or a killed owner leaves realtime dark until someone notices. Event delivery waits for a file poll interval. Install steps get longer. Realtime is dead whenever no session owns it, which the polling path must already cover.

### IC-2 — 🟡 Major — `direct_subscribe` may block the stdio responder

* **Affected Scope:** lines 315–320
* **False Compromise:** "On the main thread `rt.direct_subscribe()` runs once" reads as if subscribing were a cheap setup call. The library implementation calls `self.client.direct_threads(amount=amount)` and then joins the MQTT stream (`instagrapi/realtime/client.py` lines 127–135). If it blocks, the stdio server stops answering tool calls, which breaks every other success criterion in §3. The spec never states whether the call blocks or returns.
* **Proposed Resolution:** **Extraction.** Keep the main thread a pure stdio responder. If the call blocks, run it inside the reader thread with a timeout and a readiness signal.
* **Secondary Liabilities:** A start race where early events are missed, and `ig_health` must distinguish "not yet subscribed" from "disconnected" or it will report false outages.

### IC-13 — 🟡 Major — The realtime thread and the request handler share one client's mutable state

* **Affected Scope:** lines 315–325; §6 modules lines 205 and 210
* **False Compromise:** `direct_subscribe` reads `seq_id` and `snapshot_at_ms` out of `self.client.last_json` (`instagrapi/realtime/client.py` lines 129–130), and `last_json` is a single slot on the client that every private request overwrites (`instagrapi/mixins/private.py` lines 158, 480, 541, 557). The realtime thread and the MCP request handler both run in one process against one client, and that client also shares a single `requests.Session` (`instagrapi/mixins/private.py` lines 163–165), which is not thread-safe. Between `direct_threads()` returning and `last_json` being read, any concurrent tool call can overwrite the slot, and `direct_subscribe` then raises `RuntimeError("Direct inbox did not return realtime sync state")`. The spec never says the socket uses a separate client instance.
* **Proposed Resolution:** **Extraction.** Give the realtime reader its own instagrapi client instance and its own HTTP session, so socket bookkeeping and request traffic never share mutable state. Elect exactly one process as socket owner with a lease file under `%APPDATA%\as-ig-mcp` (see IC-1). Add a dedupe key to the normalised event shape at line 322 — `ts`, `event`, `thread_id`, `value` as a tuple — so a resubscribe after reconnect does not replay old events into the log.
* **Secondary Liabilities:** The lease file needs a heartbeat and stale-owner takeover. A separate client means a second session-cookie load and a second device fingerprint visible to Instagram, which nudges M1 rather than settling it. Dedupe by content can drop two genuinely identical messages sent close together. The owner-only model means realtime is dead whenever no session owns it.

### IC-4 — 🟡 Major — Atomic writes stop torn files, not lost updates, and "merge by timestamp" is undefined for the markers

* **Affected Scope:** lines 146–148, 234–235, 249–250, 344
* **False Compromise:** Two sessions writing state at once produce "none (silent)" and "last writer wins for the cache; digest markers merge by timestamp". Two things are wrong. First, the cache is one file holding many keyed entries, so last-writer-wins does not mean one key loses, it means the whole cache is clobbered by whichever process wrote last — and the cache is named in M1 (line 447) as the main defence against Instagram blocking the account, so a silent wipe in exactly the multi-session case the design chose to support turns the top mitigation back off. Second, "merge by timestamp" has no meaning for the markers themselves: per the study doc (line 349) they are last message id per thread, follower count, last post pk and story ids. **Message ids are not timestamps and are not comparable across threads.** The spec never says whether a merge keeps the higher id or the newer file, and one of those two silently loses a change — the flagship differentiator under-reporting with no error.
* **Proposed Resolution:** **Intermediary**, with SQLite as the substrate. `sqlite3` is in the standard library, so this adds no dependency and it is a platform standard rather than a bespoke format. Move `cache.json`, `digest.json` and `queue.json` into one database file under `%APPDATA%\as-ig-mcp` in WAL mode; concurrent processes then serialise on real write transactions. Give the digest an explicit merge rule expressed in the marker itself — a per-thread upsert that keeps the greater message id — and store follower count and story ids as replace-on-newer rather than as one blob. Keep `events.jsonl` and `audit.jsonl` as plain JSONL, because append-only is genuinely correct for them and they should stay human-readable.
* **Secondary Liabilities:** The state file stops being a readable JSON blob, which changes how the operator inspects state during a problem. Schema and migration work appears that did not exist before. Digests need an explicit key column to upsert on instead of a whole-file rewrite. The cheaper alternative is **Segmentation** — one marker file per entity, so concurrent sessions touch different files.

### IC-14 — 🟡 Major — Confirmations are said to live in files and in memory, and the idempotency ledger is missing

* **Affected Scope:** lines 71–72, 146–148, 178, 236–239, 255, 338; §3 criteria 5 and 6 lines 106–110; §8 test 1 lines 352–353; §9 Phase 4 line 393
* **False Compromise:** Line 178 lists confirmations among the things that "live in files, so several Claude Code sessions share them". Line 255 then says the opposite: "Pending write confirmations: in-memory only, lost on restart = safe." The spec picks the file story in §5 and the memory story in §6 and never reconciles them, so §6 silently wins and the premise in §4 and §5 stops holding for the one mechanism that gates every mutation. The practical effect: the confirm gate is a two-call handshake and the spec never says both calls must land in the same process. If the second call lands in another Claude Code session, or the stdio server restarts between calls, the pending action is gone and the write cannot proceed — criteria 5 and 6 both assume the flow completes. There is also a hole in the state list itself: lines 248–255 enumerate every durable file and **no idempotency ledger is among them**, yet line 238 and criterion 6 promise that replaying a key reports "already done" and sends nothing. If that ledger is in memory, the promise holds only inside one process lifetime; if it lives in `audit.jsonl`, the spec has to say so, because the journal fields listed at criterion 13 are action, target, outcome and timestamp, with no key.
* **Proposed Resolution:** **Extraction**, into the same shared store as IC-4. Write the pending confirmation to disk with the preview, a hash of the code, the issue time, an expiry and the idempotency key. Keep the idempotency ledger durable too, keyed by idempotency key and holding the outcome, so a replay after a restart still reports "already done". Both then resolve from any process, which is what §5 already promises the reader.
* **Secondary Liabilities:** The pending record holds the exact message text on disk, so it extends the M5 privacy surface (line 458) to a new file and needs the same `%APPDATA%` placement and a documented clear-and-delete. Abandoned pending writes need a sweep or they accumulate. After a restart a code is now "expired" rather than "not found", which changes the error wording at line 338. Idempotency keys need an account namespace so a stale key from another account cannot report a false "already done".

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

### IC-16 — 🟡 Major — The digest reads through the cache, so criterion 7 mostly proves the cache is warm

* **Affected Scope:** lines 66–67, 111–113, 233–235, 249–251
* **False Compromise:** The "what changed" delta digest is the capability the spec claims no competitor has (line 67), and it is the reason §2 exists. Line 233 puts reads behind a 90-second TTL cache, and line 234 has the digest compare current state against `digest.json`. Those two cannot both hold. The digest reads through the cache, so a change that lands inside the 90-second window is served from the cached value and the digest reports nothing. Criterion 7 at lines 111–113 then reads "the second reports none, without re-fetching unchanged feeds" — which describes the cache serving the same answer, not the delta logic working. Read that way, criterion 7 mostly proves the cache is warm, and the flagship differentiator is untested.
* **Proposed Resolution:** **Preliminary Action**, applied to the digest only. Give the digest its own freshness rule: the marker-bearing reads it performs bypass the 90-second read cache, or use a much shorter TTL for those sources, while ordinary tool reads keep 90 seconds. Then state criterion 7 as two conditions: the first call reports the seeded change, and the second reports none **while the marker file shows the marker advanced**. That makes the criterion test change detection rather than cache warmth.
* **Secondary Liabilities:** The digest becomes the most Instagram-touching call and now bypasses the cache the cache was built to protect, so the digest needs its own conservative floor, such as a minimum interval between digests shared through the state store. Two sessions digesting at once each re-fetch, so a shared last-digest timestamp prevents duplicated work.

### IC-15 — 🟡 Major — The REST fallback is a second table the spec never enumerates

* **Affected Scope:** lines 206, 226–229, 287–313, 403–405 (A1); §3 criterion 3 lines 103–104; §6 cache line 233
* **False Compromise:** A1 (line 404) says absorbing an Instagram change is one file because `mapping.py` holds the answer. But the table has two tiers. `mapping.py` holds the canonical method, and `client.py` holds the fallback rule from lines 228–229: on a GraphQL or JSON error, refetch once, then fall back to "the api/v1 REST variant of that feature". The REST variant is **not derivable from the feature name**, because instagrapi names them per feature — `user_followers` has `_v1` and `_gql` variants, `user_info` has `_v1`, `hashtag_info` has `_v1` and `_gql`. So the fallback is really a second table living in `client.py` that the spec never enumerates, and the "one file absorbs a change" claim is false for exactly the case where the primary breaks. The second half of the same issue is the cache: line 233 keys reads through `cache.py`, and nothing says the key includes which method produced the payload. When the canonical GraphQL call fails and the REST variant answers, the response shape differs, but it lands under the same feature key. Criterion 3 at lines 103–104 cross-checks `ig_thread` against `ig_inbox` and `ig_person` against `ig_status`, and a mixed-shape cache entry is a direct way to fail that.
* **Proposed Resolution:** **Extraction**, pulling the fallback into the table. Give each row an ordered candidate list, each candidate carrying the method name and the error class that promotes it to the next. `client.py` then only walks the list and never holds feature knowledge. Separately, record the producing method on every cached value and include it in the cache key, so a REST-shaped payload is never served under a GraphQL key.
* **Secondary Liabilities:** The table stops being one method per row and needs an ordering field, and "the canonical method" becomes a concept the schema must express. Cache entries carry provenance, so the cache file grows. The error classes that promote a fallback must exclude auth, rate-limit and checkpoint failures, because promoting on a 429 would hide the rate limit and silently change methods — that trigger set is real maintenance.

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

### IC-9 — 🟢 Nit — Publishing a ToS-violating session scraper to a public registry widens exposure

* **Affected Scope:** lines 73–75, 397, 461–464, 468–470
* **False Compromise:** v1 publishes to PyPI, the official MCP registry and the plugin marketplace, and asks that "a stranger can install and run it in one command", while M8 says the private-API liability is ours and the tool is a single local user on one Windows account with a DPAPI-bound session. Publishing to a public registry widens exposure from one user to everyone.
* **Proposed Resolution:** **Cheap Dispensables.** For v1, ship one channel (pip install from the repo, or a local plugin install). Keep registry entries as a later decision once the private-API path is settled.
* **Secondary Liabilities:** Early testers get no public install path, and the PyPI name and version reservation happens later.

### IC-10 — 🟢 Nit — `pycryptodomex` and the Python version pin contradict the spec

* **Affected Scope:** lines 138, 197, 411–412 (A4) versus `pyproject.toml` lines 10 and 16
* **False Compromise:** A4 says DPAPI through `ctypes` is enough and "no third-party crypto dependency needed", yet `pycryptodomex` is a declared dependency. §4 pins the venv to Python 3.14 while `pyproject.toml` declares `requires-python = ">=3.11"`, a support range nothing tests; instagrapi 3.2.8 predates 3.13 and 3.14.
* **Proposed Resolution:** Drop `pycryptodomex` (the stated mechanism needs no crypto package, and instagrapi already requires it transitively) or name the feature that needs it. Pin the venv to the interpreter instagrapi 3.2.8 is actually exercised on, and set `requires-python` to match.
* **Secondary Liabilities:** None beyond a smaller dependency surface and a narrower install range.

### IC-11 — 🟢 Nit — README points at a spec path that does not exist

* **Affected Scope:** `README.md` line 8 versus spec line 5
* **False Compromise:** The README links `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`. The file on disk and the spec's own canonical path is `2026-11-10-as-ig-mcp-v1-design.md`. The README also still says "Nothing implemented yet" while `pyproject.toml` and `src/as_ig_mcp/__init__.py` exist.
* **Proposed Resolution:** Fix the path and the status line in the README.
* **Secondary Liabilities:** None.

### IC-17 — 🟢 Nit — `ig_health` is expensive exactly when the account is most fragile

* **Affected Scope:** lines 240–244; §3 criterion 1 lines 98–100; §7 upstream-break row line 333; M1 lines 446–448
* **False Compromise:** `ig_health` calls one method per endpoint class, about twelve classes including DM write preview, insights and notifications (lines 240–244). The spec presents this as a cheap diagnostic and names it in M1 as a mitigation for an account block (line 447). It is the opposite of cheap under stress: Instagram rate limiting and checkpointing are the conditions that make the account most fragile, and the probe then adds twelve more calls to an account that is already struggling. instagrapi itself retries 429 and 5xx three times with a backoff factor of two (`instagrapi/mixins/private.py` lines 152–154, 194–208), so a failing probe can turn into roughly thirty-six upstream requests.
* **Proposed Resolution:** **Beforehand Cushioning.** Cache the verdict per class with the time it was taken, so `ig_health` normally reports "live as of 4 minutes ago" rather than re-probing everything. Add a force-refresh path and a per-class mode so an operator can check one suspect class instead of all twelve.
* **Secondary Liabilities:** A cached verdict can hide a fresh breakage, so the probe time has to be visible in the output and the operator has to know that a force-refresh exists. It stays a Nit only while health is called by hand; if anything calls it on a schedule it becomes Major against M1. Note the interaction with IC-12 — one of the twelve classes is the notifications read, which would itself mutate the account.

### IC-18 — 🟢 Nit — Confirm-code lifetime, attempt cap and realtime default are all unstated

* **Affected Scope:** lines 236–239, 315, 338; test plan line 352; A9 lines 427–429; D3 lines 437–438; §2 lines 67–68
* **False Compromise:** Three small gaps in one place. The test plan at line 352 asserts confirm-code validation covering "wrong code, expired code, single use", but §6 and §7 never state an expiry — the study does (line 344: single use, six minutes) and the spec dropped it, so the test asserts a rule the architecture section does not define. A six-digit code with no expiry and no attempt cap is a weaker gate than it looks, and the in-memory store makes a server restart a free reset of the attempt budget. Separately, A9 and D3 both say realtime ships behind a flag with polling as the default, while line 315 describes the socket thread as simply running and Phase 7 builds it unconditionally. §2 line 68 also sells realtime DM push as the capability nobody else has.
* **Proposed Resolution:** **Beforehand Cushioning** for the code and a single stated default for realtime. Write the confirm-code lifetime, the attempt cap and the single-use rule into §6 and reference them from §7. For realtime, pick one: if it ships off by default, say plainly in §2 that the white space is the polling digest and the socket is an opt-in extra, and move it out of the headline capability list; if it ships on, drop the flag language from D3 and A9 and keep the socket owner from IC-1.
* **Secondary Liabilities:** An attempt cap needs somewhere to count attempts, which means the pending record must become durable — which is IC-14's work anyway. Stating the realtime default honestly weakens the marketing line in §2, which is a product decision rather than a technical one.

---

# Cross-Reviewer Synthesis

Both lenses land on the same conclusion: **the root problem is solved correctly; the surrounding scope is over-claimed, and the safety story has a hole in it.**

The defect diagnosis is measured, the surface choice (private API over Graph, browser automation, a shim) is defended with reasons, and the mapping table was independently verified line by line against the installed instagrapi 3.2.8 source — every method name in it resolves. That is a strong spec at the level of *why* and *how*.

The failures are at the level of *what gets built and what gets promised*.

**Six clusters account for most of the 51 findings.**

1. **The safety story does not hold.** IC-12 is the most severe finding in the review: the notifications read maps to four instagrapi methods that POST to `notifications/change_notification_settings/` and default to `"off"`, so `ig_feed kind=notifications` and the `ig_health` notifications class would mute the business account's like, comment, follower and tag notifications — a mutation leaving through the read path, never touching the confirm gate, breaking §3 criterion 5. There is no notification reader in instagrapi at all. IC-3 sits beside it: the 6-digit code returns to the same agent that requested it, so the gate proves a two-step flow, not human consent. IC-14 shows the gate's state is in memory while §4 and §5 promise it is in files, and that the idempotency ledger §3 criterion 6 depends on is not in the state list at all. ZO-9 adds that the cache is never invalidated by a write, so criterion 5's verification can read the pre-write value and pass even if the write went through. ZO-6, X-5 and IC-18 complete the cluster.

2. **Promised capabilities with no backing method.** IC-12 (notifications), X-14 (`ig_status` "quota" — instagrapi has no quota endpoint at all, so any value printed would be fabricated; and "linked accounts" on two tools while multi-account is out of scope), X-6 (eleven promised features with no mapping row), X-18 (place search with no coordinate source). Each cell of the §6 tool table needs a named method behind it, and the spec's own test cannot check that.

3. **The v1 surface is much larger than the stated job.** ZO-1, ZO-2, IC-8, X-2 and X-11 all say the same thing from different directions: the job is one account on one machine (line 40), the build is a market superset (lines 49–70), and two of the claimed differentiators are contradicted by the project's own market study. The consistent recommendation is the same — cut v1 to the dead reads, DM read, publish, comment, follow/unfollow, the confirm gate with audit, and the polling digest; move the rest behind the flag mechanism D3 already defines.

4. **Three promises the architecture cannot keep.** The local publish queue has no trigger (X-1, ZO-4, IC-5). Realtime is a mandatory acceptance criterion in a configuration where it is switched off (ZO-3, ZO-8, IC-1, IC-2, IC-13, X-12, X-13). The digest's concurrency safety rests on a merge by timestamp over markers that are not timestamps (ZO-9, IC-4), and the digest reads through the cache that makes its own criterion prove nothing (IC-16, IC-6). Each is fixable by *removing* a promise or *adding* one trigger — not by adding code.

5. **Reusable assets and platform mechanisms are not used.** X-5 and X-16 (the platform's `requiresUserInteraction` and `ToolAnnotations` are already implemented in the author's own `TradeMCP/src/trademcp/tools/common.py` lines 32–42, and the spec omits them; the probe repo `C:\Users\aswat\Projects\ig-mcp-probe` already holds the canonical-method probes and a working session that Phase 1 would rewrite; `everyhand-tests/tools/check_no_secrets.py` is a ready secret scanner for the "never in git" promise; `TradeMCP/src/trademcp/` is the house layout for a stdio MCP server against the spec's fourteen modules). ZO-5 and X-17 cover the same ground from the other side — a hand-maintained index of a library that already indexes itself, and an unpinned `mcp` dependency on a machine where the sibling project already hit the `mcp` 2.x `FastMCP` removal.

6. **The plan does not match the repo's conventions or its own research.** §9 "Agent implements" contradicts `as-ig-orchestrator/SKILL.md` (X-3). The packaging facts the registry and marketplace require — public repo, `mcp-name` marker, `io.github.` prefix, `marketplace.json` — were identified in the study and dropped from the spec (X-4). `pycryptodomex` and the Python pin contradict A4 and `pyproject.toml` (ZO-7, IC-10). The silent repo relocation dropped the study's one-login rule, which leaves a real possibility of two Instagram sessions on one account — M1's exact concern (X-15). The pointers drift (ZO-12, X-11, IC-11), `.venv` is not git-ignored (X-7), the server id is stated two ways (X-19), and the `ig_write kind=download` discrepancy will fail the acceptance check as written (X-10).

**Recommended order of work, largest return first.**

1. **Fix the mapping table's read/write tags and the notifications row.** Split `mapping.py` into `READ_METHODS` and `WRITE_METHODS`, resolve reads only against the read set, and either source a real notifications reader or move notifications to the named-out list in §2. Add an offline test that every name in the table resolves on the installed client *and* that every read row points at a read method. *Blocking for Phase 2.*
2. **Repair the write path.** Out-of-band code delivery or the platform's `_meta["anthropic/requiresUserInteraction"]` and `ToolAnnotations`, a low-risk allowlist, a stated code lifetime and attempt cap, pending writes and the idempotency ledger moved to durable shared state with an explicit merge rule, and cache invalidation on every write. *Blocking for Phase 4.*
3. **Decide the three broken promises** — queue trigger, realtime default, digest concurrency and cache interaction — and edit the spec so each capability has exactly one stated mechanism. *Blocking for Phase 6 and Phase 7.*
4. **Re-cut §2 and §3 against the study:** drop or justify best-time, competitor benchmarking and the superset claim; make realtime's default explicit; fix criteria 2, 6 and 7 so they cannot be satisfied by a warm cache or an in-memory ledger; resolve the two-sessions question in §4.
5. **Sweep the §6 tool table for capabilities with no method behind them** — quota, linked accounts, places, download — and either give each one a named method or move it to the named-out list.
6. **Adopt the existing assets:** the probe repo's canonical-method probes and session fixture for Phase 1, `check_no_secrets.py` as the repo's secret gate, `TradeMCP`'s `ToolAnnotations` helper and `mcp>=2.3,<3` pin, and the `TradeMCP` module layout.
7. **Add the packaging facts to §4 and Phase 8**, and rewrite §9 to the orchestrator skill's loop.
8. **Fix the pointers, the tool-count drift, the `download` kind, the style file, the server id and `.gitignore`.**

**What passed and should not be re-litigated:** context sufficiency, the root-cause diagnosis, the surface choice, the rejection of a shim and of browser automation, the file-based state model as a direction, the 90-second cache as a concept, the idempotency-key *concept*, the audit journal, the whole mapping table's method *names*, and the decision to pin instagrapi rather than fork it.

**Residual risk if none of this changes:** Phase 2's health probe alone can mute the account's notifications; Phase 4's gate does not prove human consent, does not survive a restart, and can be passed by a stale cache; Phase 6 (queue), Phase 7 (realtime) and Phase 8 (packaging) each contain a check the current design cannot pass. The build stops at the first one and the cause is diagnosed late. The reviewer who raised IC-12 and X-1 puts it plainly: both are silent-failure defects — the tool will quietly change account settings, or quietly never post, and the current test plan catches neither.

**Not checked:** the delegated reviewers did not read the Obsidian capability matrix note (spec line 6) or the 13 vendor tool manifest JSONs in full; the synthesis pass closed the `docs/study/` gap for X-2 and X-11 but not exhaustively. The `.venv` had no instagrapi installed at review time, so the Python 3.14 claim (IC-10) is unverified against the library. No live Instagram call was made — every method-existence claim is from reading the installed `instagrapi 3.2.8` source.
