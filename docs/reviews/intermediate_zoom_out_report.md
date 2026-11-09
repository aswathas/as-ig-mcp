# EGM Stage 8 — Intermediate Zoom Out Report

Target: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md`
Scope: full file
Context: `zoom_out_report.md` (Stage 5), `comprehension_report.md` (Stage 6), `critic_report.md` (Stage 7)
Reviewer: `egm-zoom-out` (read-only adapter — the parent persisted this report)

## Verdict

The high-level architecture holds: the root-cause diagnosis, the private-API
choice, the 16-tool intent split, the one-table-per-feature mapping with a
`read_only` guard, the digest, the audit journal and the file-backed state model
all cohere, and the Stage 5–7 fixes landed where they were cheap.

Two things did not hold. The confirm gate still did not prove human consent,
because the owner typed the code *to the agent* and the no-desktop fallback let
the agent fetch the code itself. And the fixes introduced new contradictions:
the confirm flow contradicted itself across sections 3, 6 and 7, the realtime
flag could not be set by the install command the spec gives, and the
spec/checklist/mapping still disagree on the tool contract.

Scope over-claim (market parity, public distribution in v1) was never revisited
and remains the largest architectural finding from Stage 5.

## New findings introduced by the fixes

- **Z8-1 — Blocker — the confirm code still reaches the agent.** §6 step 6 says
  "the owner reads the code, types it in chat, and the agent passes it back",
  so the code lands in the conversation. §3 criterion 5 and the §7 row both say
  the code "never reaches the agent". The stated purpose — "the agent cannot
  approve on the account owner's behalf" — was not achieved. *Fix: change the
  consent mechanism, not the display. The dialog carries Approve/Deny buttons
  and the server executes the approved write itself; no code exists anywhere
  and the second call disappears.*
- **Z8-2 — Blocker — the no-desktop fallback lets the agent read the code.** The
  agent runs on the same machine and can run
  `python -m as_ig_mcp approve <handle>` and read the code from stdout — the
  hole the earlier fix closed for a file, reopened on stdout. *Fix: the CLI
  must not be able to produce a code at all.*
- **Z8-3 — Major — the modal popup runs on the server's thread.** `MessageBoxW`
  blocks the calling thread; on the server's main thread nothing else is
  answered while the popup is up. *Fix: separate thread, Approve/Deny buttons,
  stated timeout semantics.*
- **Z8-4 — Major — confirmations live in files, in memory and in `pending.json`:
  three answers.** The spec says "in-memory only", §5 says "in files", the brief
  says a third thing. A handle may land in a different session or after a
  restart. *Fix: one answer, and say where a handle resolves.*
- **Z8-5 — Major — the realtime default cannot be reached by the install
  command.** Phase 3 gives `claude mcp add …` with no environment, so with the
  flag unset the realtime criteria cannot pass. *Fix: ship the socket on by
  default and keep the flag as an opt-out, or drop realtime from v1's criteria.*
- **Z8-6 — Major — no concurrency model for a client now shared by three
  actors.** One process holds an instagrapi client on the main thread and the
  realtime thread, the runner holds its own, and both write `cache.json`.
  instagrapi's client is not thread-safe, and "last writer wins" on a
  whole-file cache means the last writer discards the rest — the 90-second
  cache, the main defence against an account block, can be silently switched
  off mid-session. *Fix: one file per key or SQLite (stdlib) with real
  transactions, plus one lock around instagrapi calls per process.*
- **Z8-7 — Major — competitor benchmarking contradicts the out-of-scope list.**
  §2 puts "read-only scraping of other people's accounts" out of scope while §6
  puts competitor comparison in. *Fix: define the boundary in one sentence.*
- **Z8-8 — Major — the spec, the acceptance checklist and the mapping still
  disagree on the tool contract.** The checklist wants `ig_write kind=download`
  (no such kind), `ig_thread kind=requests|spam|group` (no such kind), and
  `ig_thread box=general` (not in the tool description); `collections`,
  `guides` and `liked` are in the tool description but not in the spec's
  mapping prose. *Fix: make the checklist the single feature list and derive
  the tool table and mapping from it.*
- **Z8-9 — Nit — fixes landed in §10 but not where the agent reads them.**
  `ig_status` still promises a quota the tool cannot produce; "export" and
  "linked accounts" are undefined.
- **Z8-10 — Nit — small inconsistencies.** Duplicate step number 9; `wait_s`
  5 versus 10; the server id stated two ways; "the realtime queue" names
  nothing; the §6 tree no longer matches the built code; the confirm-code TTL
  and attempt cap absent from the spec; `IG_PLACES_LAT`/`IG_PLACES_LNG` missing
  from the configuration.

## Earlier findings — resolved

Stage 5: the notifications mutators (now `news_inbox_v1` plus the `read_only`
guard), the queue with no trigger (Scheduled Task), the digest reading through
the cache, IGTV/quicksnap/cutout sticker missing from the mapping, the dropped
one-login rule (now in §6 as "One login, two servers").

Stage 6: the confirm gate only on `ig_write` (now every mutation routes through
`writes.py`), the queue contradicting the confirm rule (confirmed at enqueue),
the "roughly 40 capabilities" estimate (the 45-row list is named), the acceptance
artifact named three ways (paths given), criterion 17's mechanism (moved into
§6), `__eqmc`/`iglib`/`ig_manage`/relogin command/delay range/registration
command/realtime flag naming.

Stage 7: the confirm contract contradicting itself across three places, the REST
fallback double-sending a write, the row count, `ig_people`'s cell, and the risk
register sitting outside the feature range.

## Earlier findings — still open

**Blocker level.** Scope is market parity rather than the stated job, and it
includes public distribution: PyPI, the official registry and the plugin
marketplace are all v1, for a server whose session is bound to one Windows
user. Phase 8's check ("a stranger can install and run it in one command")
cannot pass: the repo is local, there is no `.claude-plugin/marketplace.json`,
and no first-login flow exists for a stranger.

**Major level.** Realtime is still the largest new-code item, still carries
acceptance criteria, and polling is still called a fallback for socket events it
cannot produce. No owner election for the socket, no dedupe key on the event
record, one shared client. `direct_subscribe()` still runs on the main thread.
"digest markers merge by timestamp" is undefined, and message ids are not
timestamps. Two schedulers with no rule for which one is used. The queue runner
has no crash-safe dedupe, so a crash between Instagram accepting the post and
`queue.json` updating republishes. Nothing can draft a reply: `ig_inbox
suggest=true` has no model and no component assigned. "Threads awaiting a
reply" has no predicate. Criteria 2, 5, 6, 8 and 10 are satisfiable from a
warm cache; none says `fresh=true`. The one-login rule depends on the vendor's
`--sessionid-env` flag against a binary the spec itself proves is broken.
Confirm-code TTL, attempt cap and an idempotency-key generator are missing
from the spec. §5 compares seven rejected alternatives in prose with no
cost/complexity axis, and omits the biggest choices (Scheduled Task vs
background thread vs detached process, file state vs SQLite vs daemon, popup vs
the platform's `requiresUserInteraction`, realtime vs polling-only).

**Nit level.** `pycryptodomex` is listed as a dependency while the spec says no
crypto dependency is needed; `mcp` is unpinned; `requires-python` disagrees with
the pinned 3.14 venv; the README still says "Nothing implemented yet" and names
the old spec file; `docs/study/AS-IG-MCP - Capability Matrix.md` is cited but
does not exist in the repo; no H3 headings and a 195-line §6; §5 has no
comparison table; the mapping is one long paragraph; the 17 criteria have no
ids; the tree fence has no language tag; absolute user paths in four places.

## Reuse sweep — assets on this machine still unused

- `C:\Users\aswat\Downloads\Projects\TradeMCP\src\trademcp\tools\common.py`
  lines 32–38 already define `tool_annotations()` with `ToolAnnotations(
  read_only_hint=True, destructive_hint=…, idempotent_hint=…, open_world_hint=…)`.
  The spec declares no tool annotations at all, and
  `requiresUserInteraction` — the platform slot the study named as the right
  home for the approval step — appears nowhere.
- `C:\Users\aswat\Downloads\Projects\TradeMCP\pyproject.toml` line 15 pins
  `mcp>=2.3,<3`; this repo pins nothing, and `mcp` 2.x removed `FastMCP`.
- `C:\Users\aswat\Projects\ig-mcp-probe` holds the probe scripts and a working
  session fixture that §9 phase 1 rewrites instead of promoting.
- `everyhand-tests/tools/check_no_secrets.py` is a ready secret scanner for
  §4's "never in git" and for the audit journal.
- `sqlite3` is standard library and settles Z8-6 with real transactions.

## What passed and should not be re-litigated

Context sufficiency; the measured root cause and the `__eqmc`/`fb_dtsg`
argument; the private-API-over-Graph choice; the rejection of a shim, browser
automation and a mega action tool; the 16-tool intent split with `kind`; the
mapping method names (all verified against installed instagrapi 3.2.8); the
`read_only` + `allow_write` guard; the 90-second cache; the idempotency key;
the audit journal; the polling digest; the pinned instagrapi decision; the
Windows Scheduled Task as the queue runner.

## Not checked, and the risk

No live Instagram call; the 55 method names were not re-verified in this pass
(they were in an earlier one); the full study document was not read in full, so
the market-set claims are judged on internal consistency only; the phase briefs
were not audited except where a contradiction was visible from the spec side.

Residual risk if nothing changes: the write gate cannot be implemented to the
property the spec claims, because every documented path delivers the approval
to the agent or lets it fetch one; phases 2 and 4 would both "pass" their
checks while the property is absent; realtime's criteria cannot be met by the
documented install command; and the spec, the checklist and the built mapping
keep disagreeing on the tool contract until the checklist becomes the single
source.

---

**Applied by the orchestrator.** Z8-1 and Z8-2 changed the design, not the
wording: the approval is now a click on the owner's screen, no code exists
anywhere, the CLI approve path is gone, and writes on a machine with no desktop
are refused. Z8-3: the dialog runs on its own thread with a five-minute
timeout. Z8-4: no pending store exists at all. Z8-5: realtime ships on by
default. Z8-6: state moves to SQLite. Z8-7: the competitor boundary is now one
sentence in §2. Z8-8: the checklist becomes the single feature list, and the
missing kinds are named. Z8-9 and Z8-10: quota dropped, export and linked
accounts defined, configuration listed, the tree updated, the step numbering
fixed.
