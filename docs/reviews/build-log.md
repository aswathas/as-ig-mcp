---
title: AS-IG-MCP — Build Log
type: log
created: 2026-11-10
updated: 2026-11-10
---

# AS-IG-MCP — Build Log

One entry per phase: what ran, what the check printed, what broke, what was
decided and why.

## 2026-11-10 — setup

**Decisions.** Route A (patch the vendor) is impossible: the defect
(`fetch_fb_dtsg` scraping the graphql URL) sits inside the frozen exe, so no
session change helps. Route B confirmed: our own MCP on instagrapi 3.2.8.
v1 is the full reachable superset, built in phases. Private API only. Realtime
behind a flag with polling as the default. DM auto-reply, comment auto-reply
and multi-account parked by the user.

**Measured (2026-11-10, before the build).** Same account, same session:
`fb_dtsg` None on 3.2.3, real token on 3.2.8; followers 242; media 5; threads
10; explore 16; one thread 4 messages. Insights on post
`4024692804391239207`: reach 381, impressions 390, likes 22, profile views 17.
Account insights: `has_insights: true`, `BUSINESS_ACCOUNT`, profile visits 54,
followers +5 last week, 67 posts. Live probes also confirmed: business DM box,
follow suggestions, notifications, inbox notes, saved collections, presence,
music trending, hashtag search, linked accounts. `user_about_v1` has no data on
this account; `user_guides_v1` 404s because Instagram removed the endpoint.

**Files.** Spec `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md`;
matrix `docs/study/`; checklist `docs/reviews/capability-checklist.md`;
orchestrator skill `.claude/skills/as-ig-orchestrator/SKILL.md`.

**Workers confirmed available.** `cmd` (Command Code) on Windows; `agy` on
Windows and in WSL Ubuntu (WSL prints a harmless `networkingMode` warning).

**Next.** Phase 1 — package skeleton, dedicated venv, `session.py` (DPAPI),
`client.py`, `mapping.py`, `state.py`, offline tests.

## 2026-11-10 — Phase 1: foundation

**Ran.** Command Code worker (`cmd.cmd -p`, the npm binary — bare `cmd` is
Windows cmd.exe and silently opened a shell instead of working; fixed and
recorded in the orchestrator skill).

**Built.** `pyproject.toml` (pins `instagrapi==3.2.8`, `mcp`, `pycryptodomex`),
`src/as_ig_mcp/{__init__,state,session,client,mapping}.py`, three test files,
and the project venv at `.venv/`.

**Check the orchestrator ran itself** (the worker's claim was not accepted as
evidence): `13 passed in 0.59s`, then an independent inspection — 55 features
in `FEATURE_METHODS`, zero malformed entries, nine capability areas, DPAPI
`CryptProtectData`/`CryptUnprotectData` present with the `as-ig-mcp` entropy
label, `os.replace` used for atomic writes, fallback dispatch present in
`client.py`. Commit `962e584`.

**Closed early.** All 55 instagrapi method names in the mapping table were
verified to exist on `instagrapi 3.2.8` (Python 3.12, WSL, 0 missing). A typo in
the mapping cannot ship.

**Orchestrator decision.** The spec's build order put "register in Claude Code"
after the read tools, but registration needs at least one tool. Phase 2 was
therefore split: Phase 2 builds the server skeleton with `ig_status`,
`ig_health` and `ig_session` plus the cache and a session-import CLI, Phase 3
adds the read tools and registers. No scope changed, so the spec still stands.

**Next.** Phase 2, then the session import, then registration, then the read
tools.

## 2026-11-10 — Phase 2: server, status, health, session import

**Built.** `cache.py` (TTL cache on disk), `tools_status.py`, `tools_health.py`,
`tools_session.py`, `server.py` (stdio MCP server), `cli.py` with
`session import|status`, `status`, `health`, `__main__.py`, and a smoke test
that spawns the server and does the real JSON-RPC handshake.

**Verified by the orchestrator.** 22 tests pass; session imported from the probe
file into `%APPDATA%\as-ig-mcp\session.enc` (DPAPI); `python -m as_ig_mcp
health` ran against the live account and reported **8/10 classes live**.

## 2026-11-10 — Incident: our own read path muted our notifications

**What happened.** The first live health probe called the `notifications`
class. The mapping listed instagrapi's `notification_likes` as a reader. It is
not: its signature is `notification_likes(setting_value="off")` and it POSTs to
`notifications/change_notification_settings/`. The probe muted the like
notifications on the real account. The earlier research probe had already
muted likes, comments, new-follower and user-tagged the same way.

**Fixed.** All four categories set back to `"everyone"` (the enabled value in
instagrapi's `SETTING_VALUE_ITEMS`, which are `off`, `following_only`,
`everyone`).

**Root cause and permanent fix.** instagrapi mixes readers and mutators under
similar names, and nobody read the source before copying the names. Phase 2b
made it structural: every mapping entry now declares `read_only`, and
`client.call_feature` refuses a non-read-only feature unless the caller passes
`allow_write=True`. Only the write module may do that. The `notifications`
feature now maps to `news_inbox_v1`, a real reader. The orchestrator verified
the guard with a fake client that records calls: a mutating feature raises and
the underlying method is never called.

**The reviewer who caught the pattern.** The EGM Stage 5 review had already
flagged this as a Blocker before the probe ran — the same defect, found from the
source rather than from the symptom.

**Also fixed in Phase 2b.** `ig_status` no longer prints an invented quota
(instagrapi has no quota endpoint); the cache gained `invalidate_prefix`.

**Probe bug found by the orchestrator.** Two classes were dead for our own
reasons, not Instagram's: `user_medias_v1` with `amount=0` asks for everything
and comes back as a generic error, and the insights probe needed an integer
media pk. After the fix, the live health probe reports **10/10 classes live**
through our own client — every class the vendor could not read.

**Registered.** `claude mcp add as-ig --scope user -- .venv\Scripts\python.exe
-m as_ig_mcp serve` → `claude mcp list` shows `as-ig … Connected`. The tools
appear in Claude Code from the next session onward.

**Next.** Phase 3: the read tools.

## 2026-11-10 — Phases 3a, 3b, 4: the read tools and the write gate

**3a.** `ig_person`, `ig_people`, `ig_search`, `ig_feed`. Verified live: profile
(244 followers, 44 following, 67 media, business), followers and following,
hashtag and user search, posts, reels, saved, 12 activity notifications. One
bug the live check caught: `ig_feed kind=posts` filtered reels out, and every one
of this account's 67 posts is a reel, so it returned zero. Fixed with a
regression test.

**3b.** `ig_thread`, `ig_inbox`, `ig_story`, `ig_account`. Verified live: 5
messages in a thread with ids and timestamps, both waiting threads listed, the
account block and the insights units. Presence returns null rather than a
guess.

**4.** The write gate. After Stage 8 showed the code gate never proved consent,
the design changed: the account owner approves by clicking Yes in a dialog on
their own screen. No code exists anywhere. Verified with a fake client: denied
calls nothing, no desktop calls nothing, approved calls exactly once, a
replayed idempotency key returns already_done, and no six-digit code appears in
the result.

## 2026-11-10 — Phases 5a, 5b, 6: state, insights, queue, realtime

**5a.** State moved to SQLite (WAL, 10s busy timeout) because loose JSON meant
the last writer clobbered the whole cache — the 90-second cache is the main
defence against an account block, and a silent clobber switched it off.
`ig_insight` landed with six kinds, all verified live; where Instagram did not
return a field the tool says so instead of inventing a number. `session login`
and `session relogin` give a stranger a way in.

**5b.** The publish queue, presets, and a crash-safe tick runner: an item is
marked `publishing` before Instagram is called, so a crash leaves it reported as
possibly published rather than republished.

**6.** The digest and the realtime socket. Two live bugs, both found only by
running against the real socket: Instagram's payload carries raw bytes, which
killed the reader thread when the event was written as JSON; and the private
socket closed on us with an SSL error and then segfaulted the interpreter during
teardown. Events are now coerced to JSON-safe values, and the socket runs in its
own worker process that writes events to `events.jsonl` and its state to
`realtime_status.json`. The server supervises and restarts that worker and
reads the state file instead of touching the socket, so a broken socket cannot
take the server down. Verified live: the socket connects, subscribes with
seq_id 1231, and reconnects when Instagram closes it. The digest reports
first_run and then nothing changed.

**One login on the account.** The vendor daemon was pointed at our sessionid
(`instagram-mcp.exe login --sessionid-env IG_SESSIONID`). It reports
`session_source: browser`, connection open, no errors, and its triage still
returns the same two threads — so both servers now share one Instagram login
instead of the account carrying two.

**Next.** Phase 7 packaging, then the live write test, then publishing.



