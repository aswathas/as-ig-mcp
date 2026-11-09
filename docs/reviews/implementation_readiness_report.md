# EGM Stage 9 — Implementation Readiness Report

**Target:** `C:\Users\aswat\Projects\as-ig-mcp\docs\superpowers\specs\2026-11-10-as-ig-mcp-v1-design.md`
**Range:** lines 538–716 (`## 9. Implementation ownership` → end of file)
**Standard:** `resources/document_standards/implementation-readiness-standard.md`
**Goldfish context:** `docs/reviews/loop.md`, `docs/reviews/capability-checklist.md`, `docs/reviews/build-log.md`
**Codebase under test:** `src/as_ig_mcp/` (state, session, client, mapping, cache, serialize, server, cli, `tools_*`), 73 offline tests in `tests/`

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `implementation-readiness` | completed |
| `codebase-details` | completed |
| `style` | completed |

---

## 1. `implementation-readiness` (persona: `agents/implementation_readiness.md`)

### Blockers

**IR-B1 — The phase table has no status column; phases 1, 2, 3 and part of 5 are already built.**
Lines 546–556.
- **Discrepancy:** The table says phase 1 builds `session.py`, `client.py`, `mapping.py`, `state.py`; phase 2 builds the eight read tools plus `ig_health`; phase 3 registers in Claude Code; phase 5 builds `ig_account`. Every one of those modules already exists in `src/as_ig_mcp/`: `session.py`, `client.py`, `mapping.py`, `state.py`, `cache.py`, `serialize.py`, `server.py`, `cli.py`, `__main__.py`, `tools_status.py`, `tools_health.py`, `tools_session.py`, `tools_people.py`, `tools_discovery.py`, `tools_feed.py`, `tools_threads.py`, `tools_inbox.py`, `tools_story.py`, `tools_account.py`. All ten read/session tools are registered at `src/as_ig_mcp/server.py:38-172`; `ig_account` is registered at `server.py:171`. Registration is done — `docs/reviews/build-log.md:118-120` records "claude mcp list shows `as-ig … Connected`".
- **Rationale:** `loop.md:8-10` instructs the orchestrator to pick "the first phase in the spec's build order (section 9) whose check is not yet green". With no status column, the next worker is sent to rebuild phase 1. Add a `Status` column ("done — commit 962e584", "done — phase 2b", "done — phase 3a/3b") and fold `cache.py`, `serialize.py`, `server.py`, `cli.py`, `__main__.py` into the phase 1/2 rows so the file boundary matches the tree that exists.

**IR-B2 — M15 claims the SQLite state fix is done; the code has no SQLite, and §9 has no phase for it.**
Lines 660–664 (M15) and the table at 546–556.
- **Discrepancy:** M15 states "State moved to one SQLite file (standard library), so the MCP server, the queue runner and a second session can write at once." `src/as_ig_mcp/state.py` imports no `sqlite3`; it exposes `cache_path()` (`state.py:26`) pointing at `cache.json`, plus `digest_path()` (`:30`), `queue_path()` (`:42`), `presets_path()` (`:46`). `src/as_ig_mcp/cache.py` implements `Cache._read()` (`:39`) and `Cache._write()` (`:52`) as whole-file read/modify/write of `cache.json` — exactly the last-writer-clobbers behaviour M15 says is fixed. A grep for `sqlite` across `src/` and `tests/` returns zero matches. §4 line 166 still says "State lives in files, not in one process, so several Claude Code sessions share it safely".
- **Rationale:** An implementer reads §9, believes the race is closed, and never schedules the work — while phase 6's queue runner (§5 line 373) depends on it. Add an explicit phase (as already scoped in `docs/reviews/briefs/phase-05a-state-insights.md:11-42`: `%APPDATA%\as-ig-mcp\state.db`, WAL, `timeout=10`) or reword M15 to "planned in phase 5a".

**IR-B3 — The plan's own governing documents still mandate the 6-digit confirm code that D7/M10/M16 removed.**
Lines 542, 552, 606–612 (D7), 653–659 (M10), 665–669 (M16).
- **Discrepancy:** §9 line 542 points at the loop; phase 4 (line 552) says "`ig_write` + confirm gate + idempotency + `audit.py`" without saying "no code". But `docs/reviews/loop.md:52` still says "**No Instagram write without the 6-digit confirm code — in any worker, ever.**", and `docs/reviews/capability-checklist.md:55-56` (W1, W2) still expect `needs_confirm` and a code-bearing send. Spec §3 criterion 6 (line 124) reads "`ig_write` with the correct code sends exactly one message".
- **Rationale:** A worker that reads the plan plus `loop.md` rebuilds the flow M10 forbids. Phase 4 must state the negative explicitly ("no confirm code, no `confirm` parameter, no `needs_confirm` state; the human clicks Yes in a dialog"), and `loop.md:52` plus checklist W1/W2 must be edited in the same change.

**IR-B4 — Phase 2's check is unverifiable and counts the wrong thing.**
Line 550.
- **Discrepancy:** The check reads "the 13 dead reads return data; health green". `src/as_ig_mcp/tools_health.py:11-22` defines 10 probe classes (`PROBES`), and health is green at 10/10 (`capability-checklist.md:70`; `build-log.md:113-116`). "13 dead reads" is never enumerated in the spec — §3 criterion 1 (line 109) uses the phrase without a list; the list lives in `docs/study/AS-IG-MCP - Deep Study and Build Blueprint.md:305`. The checklist's read rows are not green: R2, R3, R6, R7, R8, R9, R12, R14 are `doing`; R4, R11, R13, R15, R16, R17, R18, R22 are `todo` (`capability-checklist.md:25-49`).
- **Rationale:** Replace the check with the rows it means (e.g. "R1–R18 green"), state where the 13-item list lives, and note that health-green (10 classes) and read-green (checklist rows) are two different gates.

### Major

**IR-M1 — Phase 6 omits the queue runner that D8/M11 require.**
Lines 554, 613–614 (D8), 680–683 (M11).
- **Discrepancy:** Phase 6 says "`ig_queue`, `ig_preset`, native `schedule_at` | queue test passes; native schedule accepted". §5 line 373 says "The local queue needs a runner: a Windows Scheduled Task that runs `python -m as_ig_mcp queue tick` every five minutes". No such command exists — `src/as_ig_mcp/cli.py:13-20` (USAGE) lists only `session import`, `session status`, `status`, `health`, `serve` (`cli.py:74-78`). No runner module exists in `src/as_ig_mcp/`.
- **Rationale:** Phase 6 must name the runner file and the exact `schtasks /create` command, plus a check that a queued item fires with the server closed — the M11 failure mode. Add `cli.py` to the phase's file list.

**IR-M2 — Realtime default contradicts itself inside §10 and against the rest of the spec.**
Lines 588–589 (A9), 597 (D3), 676–679 (M18), phase row 555.
- **Discrepancy:** A9 — "ships behind a flag with polling as the default fallback"; D3 — "Realtime ships behind a flag, with the polling digest as the default"; M18 — "Realtime ships on by default (`AS_IG_REALTIME=0` turns it off)". §7 line 453 sides with M18 ("It is **on by default**; set `AS_IG_REALTIME=0` to turn it off"); the build log sides with D3 (`build-log.md:19-20`).
- **Rationale:** Phase 7's check depends on which is true, and the flag default is an install-time decision. Choose one (M18 + §7 agree) and rewrite D3 and A9 in the same edit.

**IR-M3 — Phases 2, 4, 5, 6, 7 name tools, not files; the required file boundary does not exist for them.**
Lines 549–556.
- **Discrepancy:** Phase 4 names one file (`audit.py`) and no file for the gate itself; phases 5–7 name tools and the two runtime modules `realtime.py`, `events.py`. §6's tree (spec lines 235–262) lists `writes.py`, `audit.py`, `digest.py`, `realtime.py`, `events.py`, `queue.py`, `presets.py` — but its `tools_*.py` list stops at `tools_account.py` (lines 253–262), so no file owns the wrappers for `ig_write`, `ig_insight`, `ig_queue`, `ig_preset`, `ig_digest`. The codebase convention is one `tools_<area>.py` per tool (`tools_status.py`, `tools_health.py`, `tools_session.py`, `tools_people.py`, `tools_discovery.py`, `tools_feed.py`, `tools_threads.py`, `tools_inbox.py`, `tools_story.py`, `tools_account.py`).
- **Rationale:** The implementer otherwise picks module names — a design choice the plan must make.

**IR-M4 — Phase 4 omits the "no retry on write" rule, and the current code violates it.**
Line 552 against `src/as_ig_mcp/client.py:69-87`.
- **Discrepancy:** `client.call_write` (`client.py:85-87`) delegates to `call_feature(..., allow_write=True)`, and `call_feature` performs the REST↔GraphQL fallback (`client.py:69-82`). The phase-4 brief requires the opposite — "A write whose response failed to parse may already have been accepted by Instagram, so it is never retried by us" (`docs/reviews/briefs/phase-04-write-gate.md:16-25`).
- **Rationale:** A worker following the spec alone keeps the retrying writer while the phase check still goes green. Put the rule in §9 phase 4 (`client.call_write`: call the mapped method exactly once, no fallback, re-raise).

**IR-M5 — Phase 5's relogin mechanism is undecided, and the repo contradicts itself on it.**
Lines 553, 565–567 (A2).
- **Discrepancy:** A2 offers two unresolved paths — "one emailed code through `ig_session relogin`, **or** a browser-cookie fallback if a checkpoint blocks the scripted path". `docs/reviews/loop.md:55-56` says "Relogin is done by the user through the masked Windows dialog"; `docs/reviews/briefs/phase-05a-state-insights.md:79-92` decides a terminal flow (`python -m as_ig_mcp session relogin` with `getpass`, the MCP tool only pointing at the command). Code today: `src/as_ig_mcp/tools_session.py:93-94` returns `{"ok": False, "error": "relogin lands in phase 5"}`, and `cli.py` has no `session relogin`/`session login` command (`cli.py:84-95`).
- **Rationale:** §9 phase 5 must state one mechanism (terminal `getpass` + emailed code, per the brief), say the MCP tool only points at the CLI, and drop or trigger-mark the browser-cookie branch in A2.

**IR-M6 — Phase 8 bundles irreversible publishing with a subjective check and names no paths; the README already exists and is wrong.**
Line 556.
- **Discrepancy:** `README.md` exists but reads "Status: spec approved pending. Nothing implemented yet." and links `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`, a path that does not exist (the real file is `2026-11-10-as-ig-mcp-v1-design.md`). `LICENSE`, `tool-map.md`, `.claude-plugin/plugin.json`, `server.json` do not exist anywhere in the repo. `pyproject.toml:9,12` already set `readme = "README.md"` and `license = "MIT"`. "A stranger can install and run it in one command" is not a check any worker can execute; and PyPI/registry/marketplace publish is a live, one-way action with no gate (`loop.md:40-42` gates Instagram writes on the user, but says nothing about publishing).
- **Rationale:** Split into 8a (files: `LICENSE`, rewritten `README.md`, `docs/tool-map.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `server.json`) checked by "`claude plugin validate --strict` prints validation passed", and 8b (publishing) checked by M6's checklist with an explicit "ask the user before publishing" gate.

**IR-M7 — The phase numbering does not match the briefs driving the work, and there is no phase↔checklist mapping.**
Lines 546–556; `docs/reviews/briefs/`; `build-log.md:63-70`.
- **Discrepancy:** The briefs on disk are `phase-01-foundation.md`, `phase-02-server-health.md`, `phase-02b-read-only-guard.md`, `phase-03a-read-tools.md`, `phase-03b-dm-story-account.md`, `phase-04-write-gate.md`, `phase-05a-state-insights.md`. The spec's table is 0–8 with phase 2 = all read tools and phase 3 = registration. `build-log.md:63-67` records the orchestrator's split ("Phase 2 was therefore split… Phase 3 adds the read tools and registers") and says "No scope changed, so the spec still stands" — but the table was never updated and has no clause permitting subdivision.
- **Rationale:** A builder reading only §9 numbers phases differently from every brief workers receive. Either renumber the rows to match the briefs or add: "A phase may be split into sub-phases (e.g. 2a/2b); each sub-phase has its own brief and the same check."

**IR-M8 — Phase checks name no test files and no baseline.**
Lines 549, 552, 555.
- **Discrepancy:** The repo already has 14 offline test files under `tests/` (`test_session.py`, `test_client.py`, `test_cache.py`, `test_serialize.py`, `test_mapping.py`, `test_server_smoke.py`, `test_read_tools_are_read_only.py`, `test_tools_people.py`, `test_tools_discovery.py`, `test_tools_feed.py`, `test_tools_threads.py`, `test_tools_inbox.py`, `test_tools_story.py`, `test_tools_account.py`). "offline tests pass" is not a check; the phase-05a brief uses a numeric floor ("count higher than 73", brief line 120), a number §9 never records.
- **Rationale:** Give each phase its test file paths and the command `.venv\Scripts\python.exe -m pytest -q`, and state the current baseline count so a drop is visible.

**IR-M9 — Phase 0 is stale.**
Line 548.
- **Discrepancy:** No bug-report file exists (a grep for `aichargelabs|bug report` hits only `docs/`); the vendor is 0.2.7 (spec line 18) and `instagrapi==3.2.8` is already ours and pinned (`pyproject.toml:14`), so "if aichargelabs ships 3.2.8 the project can shrink to a config change" can no longer shrink anything; `build-log.md:14-17` records that patching the vendor is impossible because the defect sits in the frozen exe.
- **Rationale:** Close phase 0 with the reason, or name the path (`docs/reviews/vendor-bug-report.md`) and what "exists" means.

**IR-M10 — Phase 7's check needs a live human and has no deterministic acceptance criterion.**
Line 555 against §8 test 9 (lines 526–528) and checklist R23 (`capability-checklist.md:46`, still `todo`).
- **Discrepancy:** "realtime test passes" depends on "someone is active in a thread" at that moment — the owner must be present and typing. §8's test also says "with the socket stopped it returns without error", but that half is not a pass criterion for the realtime path.
- **Rationale:** Split the check into a deterministic part (fake client → event normalised into `events.jsonl` as `{"ts","event","thread_id","value"}` per §7 lines 461–463; socket-off path returns without error) and an owner-run live step recorded in the build log.

### Nits

- **IR-N1 — Nit — Risk numbering is out of order.** Lines 660–679: M15, M16, M17, M18 sit between M10 (line 680) and M11. Recommendation: renumber, or group them under a clearly separate "later review findings" heading so a reader does not read M15–M18 as M11–M14.
- **IR-N2 — Nit — A4 contradicts the packaging.** Lines 570–571: "DPAPI through `ctypes` is enough … no third-party crypto dependency needed." But `pyproject.toml:13-17` declares `pycryptodomex`, §4 line 158 lists it as a venv dep, and §6 line 230 says "no pycryptodomex". The code uses ctypes only (`src/as_ig_mcp/session.py:5-8,31-51,75,97`), so the dependency is unused. Recommendation: drop `pycryptodomex` or say in §10 what it is for.
- **IR-N3 — Nit — `mcp` is not pinned although §6 says it is.** `pyproject.toml:15` has bare `"mcp"`; §6 line 230 says "instagrapi==3.2.8, mcp (pinned)"; the venv has mcp 2.3.0. Phase 8 publishes the package. Recommendation: pin `mcp==2.3.0`.
- **IR-N4 — Nit — The §9 preamble does not carry the loop's actual steps, and the orchestrator skill it depends on is missing.** Lines 540–544 name two rules; `loop.md` has seven steps. `build-log.md:34` names `.claude/skills/as-ig-orchestrator/SKILL.md`; no `.claude` directory exists in the repo. Recommendation: state the brief path convention and the checklist/build-log updates as part of each phase's exit criteria; add the skill or delete the reference.
- **IR-N5 — Nit — §9 has no exit rule.** The file's Exit condition (lines 709–716) covers the spec, not the build. Add: "a phase is done only when its check was run by the orchestrator, the checklist rows are ticked, and the build log has an entry" — or point at `loop.md:60-63`.

---

## 2. `codebase-details` (persona: `agents/codebase_details.md`)

### Blockers

**CD-B1 — M15: "State moved to one SQLite file" is not in the code.**
Lines 660–664.
- **Discrepancy:** There is no SQLite anywhere in `src/`. `src/as_ig_mcp/state.py:26-28` still defines `cache_path()` as `cache.json`; `cache.py:28-54` is a JSON file cache whose every `set`/`get`/`invalidate` does read-modify-write of the whole file. `docs/reviews/briefs/phase-05a-state-insights.md:11-42` schedules the SQLite move as future work ("replaces the loose JSON files", `state.db`, `connect()` with `journal_mode=WAL`). The exact failure mode M15 describes (last writer clobbers the whole cache) is still live at `cache.py:52-54`.
- **Rationale:** Rewrite M15 as "planned in phase 5a, not yet built", or drop the SQLite claim until the code lands. §9 contains no phase that does this work.

**CD-B2 — M11: the Windows Scheduled Task that ticks the queue does not exist.**
Lines 680–683.
- **Discrepancy:** No task-definition file, no install script, no `queue.py`, and no `queue` command in `src/as_ig_mcp/cli.py:13-20`. Nothing in `src/` mentions a Scheduled Task. §9 has no phase that creates it — phase 6 says only "`ig_queue`, `ig_preset`, native `schedule_at` | queue test passes".
- **Rationale:** Mark M11 as open and add the task-definition file plus the install step to the phase 6 row, or say the task is installed by the user outside the repo.

**CD-B3 — M12: neither the write-invalidation nor the live-state digest exists.**
Lines 684–687.
- **Discrepancy:** There is no write path and no digest. `cache.Cache.invalidate_prefix` exists (`cache.py:89-101`) but has zero callers — the only cache mutation in the codebase is `tools_session.py:74` calling `invalidate()` to clear everything. There is no `digest.py` and no `tools_digest.py`.
- **Rationale:** Restate as planned, and name `cache.invalidate_prefix` as the mechanism so the worker reuses it instead of writing a new one.

**CD-B4 — M16: the threaded approval dialog is not built.**
Lines 665–669.
- **Discrepancy:** Only half true. The CLI fallback is indeed gone (`cli.py:13-20` has no `approve`/`pending` command), but the threaded dialog does not exist — there is no approval code in `src/` at all; the design lives only in `docs/reviews/briefs/phase-04-write-gate.md:27-60`, a brief for a phase that has not run. §9 phase 4 lists `audit.py` as the deliverable and says nothing about a dialog module.
- **Rationale:** Mark M16 as "specified, not built" until phase 4 lands.

**CD-B5 — D6: the exotic write kinds are not in the mapping, and the default would make them read-only.**
Lines 602–605.
- **Discrepancy:** `src/as_ig_mcp/mapping.py:62-179` (`FEATURE_METHODS`) has entries for crosspost (`media_share_to_threads_config`, line 128), category (`account_convert_to_professional`, line 175) and ai_label (`account_set_ai_info`, line 178) — but no entry for `igtv_upload`, `quicksnap_send`, `photo_upload_to_cutout_sticker`, `video_upload_to_cutout_sticker` or any collaboration method. `igtv_upload` and the cutout-sticker methods appear only inside `MUTATING_METHODS` (`mapping.py:43-46`), a name list, not a mapping entry; `quicksnap_send` appears nowhere. §6's "all three are in the mapping with `read_only=False`" (lines 394–395) is also false.
- **Rationale:** When phase 4 adds them, `_entry()` defaults `read_only=True` (`mapping.py:16`), so a mutating upload could be dispatched from a read path. Add the missing mapping entries with `read_only=False` now, or change D6 to say "to be added in phase 4" and require every new mutating entry to name itself in `MUTATING_METHODS`.

**CD-B6 — A4: "no third-party crypto dependency needed" contradicts `pyproject.toml`.**
Lines 570–571.
- **Discrepancy:** `pyproject.toml:13-17` declares `pycryptodomex` as a runtime dependency and it is installed in the venv (`pycryptodomex-3.24.2.dist-info`). Nothing in `src/` imports `Cryptodome` — the session really is DPAPI-only (`session.py:70-112`). The spec's own file tree says `pyproject.toml # instagrapi==3.2.8, mcp (pinned); no pycryptodomex` (line 230), so the spec and the repo disagree.
- **Rationale:** Drop `pycryptodomex` from `pyproject.toml` (an unused install-time dependency) or change A4 and line 230.

### Major

**CD-M1 — The phase table names no file for most phases, so it fails the file-boundary requirement and the Zero-Decision Rule.**
Lines 546–556.
- **Discrepancy:** Phase 2 names tools but not modules, although the codebase convention is one `tools_<area>.py` per tool (`server.py:12-23`, `tools_people.py`, `tools_feed.py`, `tools_threads.py`, `tools_inbox.py`, `tools_story.py`, `tools_discovery.py`, `tools_account.py`). §6's file tree (lines 235–262) lists `writes.py`, `queue.py`, `presets.py`, `digest.py`, `realtime.py`, `events.py`, `audit.py` but no `tools_write.py`, `tools_insight.py`, `tools_queue.py`, `tools_preset.py`, `tools_digest.py`, so where `ig_write`, `ig_insight`, `ig_queue`, `ig_preset` and `ig_digest` live and how they are registered is undecided.
- **Rationale:** Give every phase an explicit file list with Create/Modify/Delete marked (nothing in §9 is marked) and name the tools modules.

**CD-M2 — Phase 4 names `audit.py`; the brief that will execute names `writes.py`.**
Line 552 against `docs/reviews/briefs/phase-04-write-gate.md`.
- **Discrepancy:** §9 says phase 4 delivers `audit.py`. The brief puts the dialog, the preview and the journal in one module, `src/as_ig_mcp/writes.py` (brief lines 27-60, 64-76), and never mentions `audit.py`. Two different file boundaries for the same phase; the brief wins at execution time.
- **Rationale:** Change §9 to `writes.py` (plus the audit journal path `state.audit_path()`, already defined at `state.py:38-40`) so the two documents agree.

**CD-M3 — §9 defers to a loop that still mandates the abolished two-step write flow.**
Lines 540–544, 592–593, against `docs/reviews/loop.md:52` and `docs/reviews/capability-checklist.md:55-57`.
- **Discrepancy:** D1 says the capability checklist is the acceptance list. That loop still says "No Instagram write without the 6-digit confirm code — in any worker, ever" (`loop.md:52`), and the checklist still requires W1 "`ig_write kind=send_message` with no code returns `needs_confirm`", W2 "with the code, exactly one message appears", W3 "replaying the same idempotency key" — exactly the flow D7 (606–612) and M10 (653–659) abolish.
- **Rationale:** Under §9 as written, an orchestrator following `loop.md` would build the rejected two-step flow and the acceptance list could never pass. Add a phase that rewrites `loop.md` line 52 and checklist W1–W3, and name both files in the phase table.

**CD-M4 — A9 contradicts D3, M18 and §6 on the realtime default.**
Lines 586–588 against 596–597, 676–679 and 453–454.
- **Discrepancy:** A9 says realtime "ships behind a flag with polling as the default fallback" (off by default). M18 and §6 say it is on by default and `AS_IG_REALTIME=0` turns it off. The code currently reports realtime as off and unimplemented (`tools_status.py:63`: `"realtime": {"enabled": False, "state": "not implemented in v1 phase 2"}`).
- **Rationale:** Phase 7's check "realtime test passes; polling fallback intact" cannot be judged until the default is decided. Rewrite A9 to match M18.

**CD-M5 — Phase 0's check is red and the README is stale.**
Line 548 and the repo root.
- **Discrepancy:** No vendor bug report exists. The repo root holds only `README.md`, `pyproject.toml`, `docs/`, `src/`, `tests/`, `.venv/`; `docs/study/` mentions aichargelabs but no issue document was written. `README.md:6-8` still says "Status: spec approved pending. Nothing implemented yet." and links to `docs/superpowers/specs/2026-11-10-as-ig-mcp-design.md`, a file that does not exist (the real one is `...-v1-design.md`).
- **Rationale:** Write the bug report as a repo file and name its path in the phase table; fix the README link and status.

**CD-M6 — §9 phase numbering does not match the briefs or the build log.**
Lines 546–556; `docs/reviews/briefs/`; `build-log.md:118-122`.
- **Discrepancy:** The briefs are `phase-01-foundation`, `phase-02-server-health`, `phase-02b-read-only-guard`, `phase-03a-read-tools`, `phase-03b-dm-story-account`, `phase-04-write-gate`, `phase-05a-state-insights`. `loop.md:8-10` says the orchestrator picks "the first phase in the spec's build order (section 9) whose check is not yet green", so the two numbering schemes must be reconciled by hand. `build-log.md:118-122` records that registration happened inside phase 2, while §9 puts registration in phase 3 after the read tools; `build-log.md:63-67` records that split explicitly and says "the spec still stands" — but the spec was never updated.
- **Rationale:** Renumber §9 to match the brief names, or add a mapping line and fold the 2/2b/3a/3b split into §9.

### Nits

- **CD-N1 — Nit — Risk list order.** Lines 660–695: M1–M10, then M15–M18, then M11–M14. A reader following the numbers will mis-sequence the risks. Sort M11–M18 in numeric order.
- **CD-N2 — Nit — Phase 4 still says "confirm gate"** (line 552) while D7/M10 removed the confirm code (line 553). Call it "approval gate (click, no code)".
- **CD-N3 — Nit — Native `schedule_at` has a reel gap.** Line 554, D2 (594–595). In instagrapi 3.2.8, `photo_upload` (`instagrapi/mixins/photo.py:258`), `video_upload` (`video.py:444`) and `album_upload` (`album.py:138`) accept `schedule_at`; `clip_upload` (`clip.py:730`) does not. Reels therefore have no native scheduling — note it in D2 and in checklist row W6.
- **CD-N4 — Nit — Reuse opportunities the plan leaves open.** `state.py:22-55` already defines `session_path`, `cache_path`, `digest_path`, `events_path`, `audit_path`, `queue_path`, `presets_path`, `style_path`, `media_dir`, so `audit.py`, `events.py`, `queue.py`, `presets.py`, `digest.py` should reuse them rather than invent paths; `cache.py:89` `invalidate_prefix` is the natural M12 mechanism; `client.py:90` `field_value` already exists and is duplicated as a private `_value` in `tools_status.py:14-17` and `tools_health.py:32-35`. Name these in §9 so workers reuse them.
- **CD-N5 — Nit — `cli.py` usage text never lists `serve`.** Line 551. `cli.py:13-20` (USAGE) omits it, so `--help` does not show the entry point the spec tells users to run. Add `serve` to the usage text.
- **CD-N6 — Nit — §6's file tree still lists a `pending` CLI command** (line 238, referenced by §9), removed with the confirm-code flow. `cli.py` has no `pending` command. Drop it from the tree comment.

### Verified correct (no finding)

- Tool names in §9 match the registered tools: `server.py:35-172` registers `ig_status`, `ig_health`, `ig_session`, `ig_person`, `ig_people`, `ig_search`, `ig_feed`, `ig_thread`, `ig_inbox`, `ig_story`, `ig_account` — all phase-2 names exist.
- M9's `read_only` flag and `allow_write` guard are real (`mapping.py:11-26`, `client.py:51-82`) and covered by `tests/test_read_tools_are_read_only.py`.
- M13 is real (`tools_status.py:61`); M3's `[AS-IG-MCP]` prefix is on every tool description; M1's 90-second TTL is `cache.py:13`; M5's `%APPDATA%` location is `state.py:14-19`.
- D7/M10 agree with the phase-4 brief (`briefs/phase-04-write-gate.md:8-12, 32-46`).
- Phase 5's `ig_session relogin` matches the placeholder at `tools_session.py:93-94`.
- Phase 3's command is correct: `serve` exists (`cli.py:74-78`), the package is installed editable (`.venv\Lib\site-packages\__editable__.as_ig_mcp-0.1.0.pth`), and `build-log.md:118-120` shows it working.

---

## 3. `style` (persona: `agents/style.md`)

### Blockers

**ST-B1 — D3 and M18 give opposite instructions for the same flag.**
Lines 596–597 (D3) vs 676–679 (M18), also 453–454 (§6) and 184–186.
- **Discrepancy:** D3: "Realtime ships behind a flag, with the polling digest as the default." M18: "Realtime ships on by default (`AS_IG_REALTIME=0` turns it off) … and the polling digest stays as the fallback when the socket is down." §4's config table and §6's Realtime paragraph both agree with M18 (default on).
- **Rationale:** A builder reading section 10 alone gets two mutually exclusive defaults for one setting. Fix D3 to state the default explicitly; M18 then becomes a duplicate and should fold into D3.

**ST-B2 — The range's "no confirm code" position is contradicted by four other documents the range points at.**
Lines 606–612 (D7), 653–659 (M10), 665–669 (M16), 542, plus 82, 124–125, 505, and `docs/reviews/loop.md` line 52.
- **Discrepancy:** The range's position is "there is no confirm code; the human clicks Yes in a dialog." The rest of the system still mandates a code: §2 line 82 ("a 6-digit confirm code with a preview on every write"), §3 criterion 6 line 124 ("`ig_write` with the correct code sends exactly one message"), §8 test 1 line 505 ("confirm-code validation (wrong code, expired code, single use)"), `capability-checklist.md` W1/W2 lines 55–56 ("with no code returns `needs_confirm`", "with the code, exactly one message"), and `loop.md` line 52 ("No Instagram write without the 6-digit confirm code — in any worker, ever"). §9 line 542 points the builder at `loop.md` as the authoritative loop.
- **Rationale:** A builder that reads §9 then `loop.md` gets two opposite safety rules, and one is the loop's standing rule that would be violated in every worker. Fix the source of truth first — correct `loop.md` line 52, checklist W1/W2, §2 line 82, §3 criterion 6 and §8 test 1 — then add one line to D7: "This supersedes the code wording in §2, §3.6, §8.1, `loop.md` and checklist W1/W2; those say 'code' and are wrong."

### Major

**ST-M1 — Risk numbering is out of order.**
Lines 618–695.
- **Discrepancy:** The list runs M1..M10, M15, M16, M17, M18, M11, M12, M13, M14. The order breaks at M10→M15 and again at M18→M11. The cause is visible: M15–M18 are Stage 8 findings, M11–M14 are Stage 5 findings, so two revision batches were interleaved.
- **Rationale:** A numbered list that is not sorted cannot be scanned or cited by number. Move the M11–M14 block up so the list reads M1…M18. Do not renumber — the Stage 5 and Stage 8 review reports cite M-IDs (e.g. `zoom_out_report.md` cites "M8 (line 468)").

**ST-M2 — M17 and M18 are not risks.**
Lines 670–679 vs 592–614 (D1–D8).
- **Discrepancy:** M17 restates D1 plus D5 (market parity, public distribution) with a cost; M18 restates and contradicts D3.
- **Rationale:** The Risks list mixes open risks with mitigations, risks already fixed, and decisions already taken. Move M17 into Decisions as D9 (with the named cost); delete M18 once ST-B1 is fixed.

**ST-M3 — Risk entry format is inconsistent.**
Lines 618–695.
- **Discrepancy:** M1–M6 and M8 use "Mitigation: …". M7 has no mitigation clause. M9–M14, M16 use "Fixed: …". M17 uses "Accepted, not fixed." M18 uses "Accepted." There is no status field and no single sentence pattern.
- **Rationale:** A reader cannot tell at a glance which risks are still open. Give every entry one shape: `- Mx. <risk in one sentence>. Status: open | fixed | accepted. <mitigation or fix>`. M7 is the practical case: "Smithery's MCP Proxy and managed identity shut down 2026-10-31" is closed with no action, and "it survives only as a directory" is not an actionable sentence.

**ST-M4 — The Check column is not runnable as written.**
Lines 546–556.
- **Discrepancy:** Phase 1 "offline tests pass" (no command). Phase 2 "the 13 dead reads return data; health green" (neither term defined; "green" defined only in `capability-checklist.md`'s legend). Phase 4 "write-gate, audit and idempotency tests pass" (no test names). Phase 5 "insights match Instagram's numbers" (exact match impossible — §3 criterion 8 says ">=" plus a complete field set). Phase 7 "realtime test passes" (§8's item 9 uses `wait_s=10`; §3 criterion 12 uses `wait_s=5`). Phase 8 "a stranger can install and run it in one command" (not a check; a stranger has no session).
- **Rationale:** §9 promises "Each phase ends with a runnable check" and the standard requires a fresh implementer to execute without guessing. Give every row the exact command and the exact assertion.

**ST-M5 — The table has no file paths for most deliverables.**
Lines 546–556.
- **Discrepancy:** Phase 0 says "Vendor bug report" with check "exists in the repo" and no path. Phase 4 says "`ig_write` + confirm gate + idempotency + `audit.py`" but never names `writes.py` (the module §6 puts the gate in). Phase 8 names "tool-map.md", "plugin manifest", "LICENSE" with no paths, while §6's tree puts the manifest at `.claude-plugin/plugin.json`. `tool-map.md` exists nowhere in the repo and is not in §6's tree.
- **Rationale:** The standard requires an explicit list of repository-relative file paths per phase, suitable for a write allowlist, and §9's table is the only place a worker brief can get its file list from. Add a file column, or extend Build to full paths (`src/as_ig_mcp/writes.py`, `docs/tool-map.md`, `.claude-plugin/plugin.json`, `docs/reviews/vendor-bug-report.md`).

**ST-M6 — The Check column does not mark which checks need a human.**
Lines 546–556.
- **Discrepancy:** Phase 3 needs a human to open a clean Claude Code session; phase 5 needs the owner to enter an emailed code from Instagram; phases 6 and 8 need the owner to publish or install.
- **Rationale:** `loop.md`'s decision rule says a check needing a real Instagram write requires the user first, and "workers never commit" plus "the orchestrator runs the phase check itself". A worker reading "relogin works" as its own check would try to log in and be refused. Mark each check `machine` or `owner`, and for owner checks give the exact command the owner runs and what output counts as pass.

**ST-M7 — The heading promises ownership; the first sentence is ambiguous and there is no owner column.**
Lines 538–544.
- **Discrepancy:** The heading is "Implementation ownership" and the first word is "Agent implements", but the table has no owner column, and the sentence after it says a worker takes each phase. `loop.md` and the build log show the opposite: the orchestrator dispatches a worker (Command Code or Antigravity) and never writes implementation code itself; the build log's Phase 1, Phase 2 and Phase 2b entries were all worker-built. "Agent" is ambiguous between the orchestrator Claude Code session and the worker.
- **Rationale:** "Agent implements" is the first sentence a builder reads and it does not say who writes the code. Fix to "The agent implements, through one worker per phase; the orchestrator runs the check itself and owns the commit — see `docs/reviews/loop.md`." Then retitle the section or add an "Owner" column.

**ST-M8 — `loop.md`'s pointer to the phase list is wrong.**
Line 542 against `docs/reviews/loop.md` lines 8–11.
- **Discrepancy:** §9 says the loop "is `docs/reviews/loop.md`". `loop.md` step 1 says "First phase in the spec's build order (section 9) whose check is not yet green. The phase list lives in `docs/reviews/capability-checklist.md`." `capability-checklist.md` has no phase list — it has capability rows R1–R26, W1–W10, P1–P9. The phase list is the table in §9 itself.
- **Rationale:** A dead cross-reference to the wrong file sends the reader to a file that cannot answer the question. Fix `loop.md` to name the §9 table as the phase list.

**ST-M9 — The phase numbering does not match the briefs on disk, and there is no subdivision clause.**
Lines 546–556 against `docs/reviews/briefs\` and `build-log.md` lines 63–70.
- **Discrepancy:** The brief files on disk are phase-01, 02, 02b, 03a, 03b, 04, 05a. The spec's table is 0..8 with phase 2 = all read tools and phase 3 = registration. The build log records the orchestrator's split and says "No scope changed, so the spec still stands" — but the spec's table was not updated and has no clause permitting subdivision.
- **Rationale:** A builder reading only §9 numbers phases differently from every brief workers receive. Either renumber §9's rows to match the briefs (0, 1, 2, 2b, 3a, 3b, 4, 5, …) or add: "A phase may be split into sub-phases (e.g. 2a/2b); each sub-phase has its own brief and the same check."

**ST-M10 — D1–D8 and A1–A9 are never referenced by ID.**
Lines 590–614, 618–695.
- **Discrepancy:** The labels add lookup value only if something cites them. The only references to them anywhere in the repo are in review reports, and those cite them by line number ("A1 lines 403-405", "D2 lines 435-436"), which is now wrong after the edits.
- **Rationale:** Wire them in — §9's phase table should name the decisions and risks each phase discharges (phase 4 → D7, M10, M16; phase 7 → D3, M18; phase 6 → D8, M11) — or drop the labels and keep plain bullets.

**ST-M11 — D8 omits the approval rule that makes an unattended publish safe.**
Lines 613–614 (D8), 554 (phase 6), against §6 lines 312–318.
- **Discrepancy:** D8 says only that a Windows Scheduled Task ticks the queue every five minutes. The rule "Scheduled work is approved at enqueue time" is stated only in §6 step 7.
- **Rationale:** A builder reading D8 alone could gate at publish time, which no human is there to answer, and the queue would publish nothing or the agent would approve its own write. D8 must carry the approval-at-enqueue clause, and phase 6's check must assert it: "the runner publishes an item approved at enqueue without asking again."

**ST-M12 — D1 names the wrong acceptance artifact.**
Lines 592–593.
- **Discrepancy:** "The capability matrix is the acceptance list." There are two different artifacts: `docs/study/AS-IG-MCP - Capability Matrix.md` (the market study) and `docs/reviews/capability-checklist.md` (45 capability rows, each with a check). §2 line 54 names the checklist correctly.
- **Rationale:** Change D1 to "`docs/reviews/capability-checklist.md` is the acceptance list."

**ST-M13 — M5's mitigation promises a command that does not exist.**
Lines 630–632 (M5), 552 (phase 4).
- **Discrepancy:** M5's mitigation promises the audit journal and presets get "a clear-and-delete command". No such command exists in the tool surface: §6 lists `ig_session` as "status, relogin, cache clear, and `export`", and there is no delete tool anywhere.
- **Rationale:** A mitigation that names a feature the plan does not build is a promise the plan breaks. Add the command to the `ig_session` surface (and §6's tool table) or change M5's mitigation to what exists ("removal is deleting the files under `%APPDATA%\as-ig-mcp`").

**ST-M14 — Review findings are attributed to unnamed reports; "the CLI fallback" has no referent.**
Lines 660–679, 643–659.
- **Discrepancy:** M9–M18 attribute findings to "the EGM Stage 5 review" and "the EGM Stage 8 review" without a path. The reports exist: `docs/reviews/zoom_out_report.md` (Stage 5) and `docs/reviews/intermediate_zoom_out_report.md` (Stage 8). M16 refers to "the CLI fallback", a component not described anywhere in the range or in §6 — it existed only in the pre-Stage-8 design.
- **Rationale:** A builder reading M16 cannot tell what the CLI fallback was or where it lived. Name the reports by path and rewrite M16's fix as a statement about the current design.

**ST-M15 — §7's failure table is stale against M15.**
Lines 662–664 (M15) against line 497.
- **Discrepancy:** M15 says the loose-JSON clobbering "silently disabled the 90-second cache" and that state moved to SQLite. §7's last failure row still says "Two Claude Code sessions write state at once → last writer wins for the cache".
- **Rationale:** §7 is the table a builder reads when handling a failure; a row that contradicts the fix will produce the old behaviour. Update the §7 row to match the SQLite decision (M15's fix is right; §7 is stale).

**ST-M16 — The Exit condition does not test internal consistency, and the Status line is never gated.**
Lines 709–716.
- **Discrepancy:** It tests only three things: all ten sections filled, no `TBD`/`TODO`/placeholder, and the user said "approved". It does not require internal consistency, does not mention the Status field on line 3 (still "Status: Draft for user review"), and does not say where approval is recorded.
- **Rationale:** Section 10 currently contains a contradiction (ST-B1) and the range contradicts four other documents (ST-B2). Add: "and no numbered item in any section contradicts another; and every file it references agrees with it; and the Status line at the top reads `Approved` with the date."

**ST-M17 — The invalidation bullets are unnumbered and one of them is a scope change, not an invalidation.**
Lines 697–705.
- **Discrepancy:** Everything else in §10 is numbered; these three are not. The third ("The user decides DM reading does not matter — then the server shrinks to public reads plus publishing") is a scope change, not a spec invalidation.
- **Rationale:** Number them I1..I3, or fold each into the assumption it kills (I1 → A1/A3, I2 → A7, I3 → a scope-revision clause under D1).

### Nits

- **ST-N1 — Nit — A3 ends with a fragment.** Lines 562–569 (A1, A3). A3 ends "Observed 2026-11-10." on its own line — a date without saying what was observed. Rewrite: "Observed 2026-11-10: the scrape returned a live `fb_dtsg` token." A1's "instagrapi 3.2.8's endpoint set" → "the endpoint set instagrapi 3.2.8 uses".
- **ST-N2 — Nit — Undefined terms in A5/A6.** Lines 572–578. "our use" and "touchpoints" are undefined. Replace "our use" with the use it means (reading and publishing from one account on one machine) and "touchpoints" with the concrete list (a relogin code, a browser challenge, a mapping edit). A5 and A6 correctly label themselves "Reasoning, not measured" — keep that, and add the same label to A8.
- **ST-N3 — Nit — "Baked into this spec" and "any of them" over-claim.** Lines 590, 596–597, 606–612, 613–614. D4 (private API only) and D7 (a human click is the approval) cannot be flipped without a redesign. Use "**Decisions in this spec**" and name the reversible ones (D2, D3, D8).
- **ST-N4 — Nit — The same content appears up to three times.** Lines 606–612 (D7), 665–669 (M16), 602–605 (D6), 600–601 (D5) vs 670–675 (M17). Click-not-code is stated in D7, M10 and M16; parked features in D5 and M17; the unit-test-only rule in D6 and §6's "Verification depth". Keep the full statement in Decisions; in Risks keep "M16. The modal dialog blocked the calling thread. Fixed — see D7."
- **ST-N5 — Nit — M1's mitigation ends with a shrug.** Lines 618–620. "and the option to stop using the tool" is not a mitigation for an account block. Replace with a concrete control: "`AS_IG_REALTIME=0` plus a read-only session when the health probe reports a block."
- **ST-N6 — Nit — M6 names four undefined terms and an unnamed external document.** Lines 633–636. "the Anthropic pre-submission checklist — LICENSE, README over 40 words, pinned exact-version launcher, secrets via `userConfig` with `sensitive: true`". Phase 8 depends on it. Link the checklist by URL and define each term in one clause; drop the word count unless it comes from the checklist.
- **ST-N7 — Nit — The §10 heading omits "decisions".** Lines 558, 560–616. Heading is "Risks, assumptions, and what would invalidate this spec"; body order is Assumptions, Decisions, Risks, invalidation. Rename the heading to "## 10. Assumptions, decisions, risks, and what would invalidate this spec".
- **ST-N8 — Nit — Comma splice in the §9 preamble.** Lines 542–544. "the orchestrator runs the phase check itself and never accepts a worker's claim as evidence, and workers never commit." Split: "The orchestrator runs the phase check itself; a worker's claim that it passed is not evidence. Workers never commit."
- **ST-N9 — Nit — Phase 0's conditional is not a check.** Line 548. "if aichargelabs ships 3.2.8 the project can shrink to a config change" — our server uses its own pinned instagrapi 3.2.8, not the vendor's copy (§4, §6), so a vendor release changes nothing about our client. Rewrite the check as one action: "`docs/reviews/vendor-bug-report.md` exists, with the failing URL, a reproduction and the fix we tested."
- **ST-N10 — Nit — §3 criterion 14 names two server ids for one server.** Lines 551, 553, 555. It looks for "`instagram-fixed`/`as-ig`"; `instagram-fixed` is the vendor's id (the `everyhand` MCP's hand) and `as-ig` is ours (§ header line 9). §3 criterion 14 should name only `as-ig`. Phases 5 and 7 should cite the criterion numbers they prove (§3.8–§3.10, §3.12).
- **ST-N11 — Nit — The five-minute timeout knob is named inconsistently.** Lines 606–612, 665–669 and §4 line 185. §4's config table names it `AS_IG_REALTIME_TIMEOUT` ("seconds the approval dialog waits"); the Phase 4 brief already renamed it `AS_IG_APPROVE_TIMEOUT`. A variable named `AS_IG_REALTIME_TIMEOUT` that controls a write approval is a trap. Fix §4 to `AS_IG_APPROVE_TIMEOUT` (default 300) and have D7 name it.
- **ST-N12 — Nit — M14's fix has no mechanism or evidence.** Lines 691–695. §1 lines 27–29 says the vendor binary cannot be patched. The one-login guarantee (M1's exposure risk, §3 criterion 17) rests on this one line. Name the mechanism and the evidence: "`instagram-mcp.exe login --sessionid-env IG_SESSIONID` accepts the injected sessionid; verified by comparing the two session stores."
- **ST-N13 — Nit — "all ten sections above" needs the reader to count.** Lines 709–716. Say "all ten numbered sections above (1–10)". Decide whether the Exit condition is a section: number it 11 or state that the count excludes it.

---

## 4. Cross-reviewer synthesis

### Items that would block the build

**BLK-1 — The spec claims fixes that are not in the code.** M15 (SQLite state), M11 (Scheduled Task queue runner), M12 (write invalidation + live-state digest), M16 (threaded approval dialog) all read as done ("Fixed by…", "State moved to…"). None of them exist in `src/as_ig_mcp/`. Independently verified: `sqlite` returns zero matches across `src/`; `cache.py:52-54` still does whole-file read-modify-write of `cache.json`; `cache.py:89-101` `invalidate_prefix` has zero callers; there is no `digest.py`, no `queue.py`, no `realtime.py`, no `events.py`, no `audit.py`; `cli.py:13-20` has no `queue tick` command. §9 has no phase that produces any of them, and the phase table carries no status column to show what is missing. — *implementation-readiness B2/M1, codebase-details B1–B4, style F3 (M15 vs §7)*

**BLK-2 — The build order does not match the built code.** Phases 1, 2, 3 and `ig_account` (phase 5) already exist and are registered (`server.py:38-172`; `build-log.md:118-120`). Meanwhile the briefs on disk (`phase-01`, `02`, `02b`, `03a`, `03b`, `04`, `05a`) use a different numbering than §9's 0–8, and `loop.md:8-10` — the rule §9 defers to — points at the wrong file for the phase list. A worker dispatched by the current spec rebuilds finished work and skips the real work. — *implementation-readiness B1/M7, codebase-details M6, style M9/F10*

**BLK-3 — The governing documents still mandate the abolished confirm code.** D7/M10/M16 abolish it; `loop.md:52`, `capability-checklist.md` W1/W2, §2 line 82, §3 criterion 6 and §8 test 1 all still require it. §9 line 542 makes `loop.md` authoritative. An orchestrator following the spec as written builds the two-step flow the spec rejects — and the acceptance list could never pass. — *implementation-readiness B3, codebase-details M3, style B2*

**BLK-4 — The realtime default is stated two ways.** D3/A9 say "behind a flag, polling default"; M18 and §7 say on by default with `AS_IG_REALTIME=0` to disable. Phase 7's check depends on which is true. — *implementation-readiness M2, codebase-details M4, style B1*

**BLK-5 — Phase checks are not executable as written.** No command, no test file names, no baseline count, undefined terms ("13 dead reads" is never enumerated; health-green is 10 probes, a different gate), machine checks mixed with owner-only checks unmarked, phase 8's "a stranger can install and run it in one command" is not a check at all, phase 5's "insights match Instagram's numbers" cannot pass against §3's ">=" criterion, phase 7's check needs a live human with no deterministic half. §9 promises "Each phase ends with a runnable check" and the Standard's Zero-Decision Rule requires a fresh implementer to execute without guessing. — *implementation-readiness B4/M8/M10, codebase-details M5, style M4/M6*

**BLK-6 — No file boundary per phase.** §9 names one file for the whole plan (`audit.py`); phases 2, 4, 5, 6, 7 name tools, not modules. §6's tree omits `tools_write.py`, `tools_insight.py`, `tools_queue.py`, `tools_preset.py`, `tools_digest.py`, and the phase-4 brief puts the gate in `writes.py`, contradicting §9's `audit.py`. The implementer picks module names — a design choice the plan must make. — *implementation-readiness M3, codebase-details M1/M2, style M5*

**BLK-7 — D6's exotic write kinds are not in the mapping, and the mapping default makes them safe-looking but absent.** `mapping.py` has no `igtv_upload`, `quicksnap_send`, cutout-sticker or collaboration entries; they appear only in the `MUTATING_METHODS` name list (`mapping.py:43-46`), and `_entry()` defaults `read_only=True` (`mapping.py:16`). §6's "all three are in the mapping with `read_only=False`" is false. This is the M9 failure class the spec says is permanently fixed. — *codebase-details B5*

**BLK-8 — Phase 8 bundles an irreversible publish with a subjective check, and the README that ships is wrong.** `README.md` still says "Status: spec approved pending. Nothing implemented yet." and links a spec file that does not exist. `LICENSE`, `tool-map.md`, `.claude-plugin/plugin.json`, `server.json` are absent. `pyproject.toml` still declares the unused `pycryptodomex` that A4 says is not needed, and leaves `mcp` unpinned although §6 says it is pinned — phase 8 publishes that. — *implementation-readiness M6/N2/N3, codebase-details B6/M5, style N6*

### Strongly recommended, not build-stopping

- **R1 — Section 10's risk list is not scannable.** Out of order (M1–M10, M15–M18, M11–M14), mixed entry types (M17/M18 are decisions), inconsistent formats (Mitigation/Fixed/Accepted), and M7 has no mitigation at all. Sort M11–M18 into place without renumbering, give every entry one shape, and move M17 into Decisions.
- **R2 — D1–D8 and A1–A9 are never cited by ID** and the review reports cite them by stale line numbers. Wire them into §9's phase table or drop the labels.
- **R3 — Several fixes live in documents outside the reviewed range.** §7's "last writer wins" row contradicts M15; the invalidation bullets are unnumbered and one is a scope change; the §10 heading omits "decisions"; the Exit condition does not test internal consistency and never gates the `Status: Draft for user review` line at the top.
- **R4 — Phase 5's relogin mechanism is undecided** (terminal `getpass` per the brief vs masked dialog per `loop.md` vs browser-cookie fallback per A2), and D8 omits the approval-at-enqueue rule that makes unattended publishing safe.
- **R5 — Reuse is left open.** `state.py:22-55` already owns every path helper; `cache.py:89` `invalidate_prefix` is the M12 mechanism; `client.py:90` `field_value` is duplicated as a private `_value` in `tools_status.py:14-17` and `tools_health.py:32-35`. Name them in §9.
- **R6 — Small corrections:** phase 4's "confirm gate" wording → "approval gate (click, no code)"; `AS_IG_REALTIME_TIMEOUT` → `AS_IG_APPROVE_TIMEOUT` (§4 line 185 vs the phase-4 brief); drop `pending` from §6's `cli.py` tree comment (line 238) and add `serve` to `cli.py`'s usage text; §3 criterion 14 should name only `as-ig`, not `instagram-fixed`; `schedule_at` does not exist for `clip_upload` in instagrapi 3.2.8, so reels have no native scheduling and D2 should say so; `.claude/skills/as-ig-orchestrator/SKILL.md` (`build-log.md:34`) does not exist in the repo.

### Notes and limits of this review

- The 73-test count and "offline tests pass" were not re-run; test baselines are taken from the task brief and `build-log.md`.
- The vendor binary and the `everyhand` repo were not inspected, so M14's shared-login fix is unverified.
- `claude plugin validate --strict` and the registry/marketplace commands could not be exercised — no manifest exists in the repo yet.
- Live Instagram behaviour, the realtime transport, and the insights numbers were not exercised; those remain open assumptions (A1–A9) for the owner.
