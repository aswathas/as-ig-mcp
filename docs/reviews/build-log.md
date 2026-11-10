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

## 2026-11-10 — The live write click

The first live write through the gate: `mark_seen` on the known thread, approved
by clicking Yes in the dialog on the owner's screen. The journal records exactly
two lines for the attempt — `approved / executing`, then `approved / completed` —
with the target (`thread 340282366841710301244259146818785935725`) and no
secret. Replaying the same idempotency key returned `already_done` with no
dialog and no second Instagram call, so W3 is green live. A second run with a
fresh key and a click on No returned `denied` and wrote exactly one denied
journal line, so W1 and W4 are green live. A send to the account's own user id
with a click on Yes appeared exactly once in the self thread, so W2 is green
live. The whole write gate — approve, deny, replay — is now proven against the
real account.

One finding from the live run: Windows make Yes the default button in a
Yes/No box, so a stray Enter approves a write. No is now the default
(MB_DEFBUTTON2); the 169 tests still pass.

The probe needed the real message id: `direct_message_seen` takes
`(thread_id, message_id)` and the test had been sending only the thread. It now
reads the thread and picks the newest message from the other person first.

Health was re-run after the write: **10/10 classes live**, and `as-ig` is
`Connected` in `claude mcp list`.

## 2026-11-10 — Round 1 sweep and six gaps closed

The free read sweep ran 26 checks: 18 passed, 2 were empty (no tagged posts, no
active story), 1 failed, 1 needed configuration and 1 was partial. It also named
six capabilities with no tool behind them. All six were built and verified live
the same day; the suite went from 169 to **176 passing**.

- `ig_feed kind=notes` and `kind=mentions`. Mentions come from the real
  `story_mentions` section of the activity payload, which the old notifications
  reader ignored.
- `ig_feed kind=download` reads the post type first, then calls photo, video,
  clip or album download. Paths are contained to the media folder.
- Guides are gone from Instagram (`/v1/guides/user/` returns 404). The tool now
  says so instead of leaking a 404 traceback.
- `ig_inbox` gained `box=general|primary|requests|spam` and `kind=groups`.
- `ig_search kind=place` accepts `lat`/`lng` directly, so it no longer depends
  only on environment variables.
- Competitor compare falls back to public likes and comments when Instagram
  refuses insights for an account we do not own, and says which source it used.

Live results: notes 2, mentions section present (0 stories mention us),
business box 3 threads, requests and spam readable, 2 group threads, places 5,
post download 1 file, guides a clean 404 message, and competitor compare ranked
3 public-like posts. The work was split between a Windows agy agent (inbox), a
WSL agy agent (search and insights) and the orchestrator (feed, mapping, server,
tests), on non-overlapping files.

## 2026-11-10 — Live write sweep

Every write kind was exercised against the account. The click gate had already
been proven live (Yes, No, replay, journal), so the remaining action tests used
an in-process auto-approving dialog and spaced their calls; each action is still
journalled. 191 tests pass.

Verified live: follow/unfollow, mute/unmute (muting needs a follow first),
block/unblock, hashtag follow (blocked: Instagram returns 404 for the web tags
endpoint), bio change and restore, close friend add/remove, comment create,
pin/unpin and bulk delete, photo, video (a thumbnail is required), reel, album
and story publish, first comment, post delete, highlight create/delete, queue
schedule/cancel, DM send/unsend, inbox note create/delete, the AI label, and
Instagram's own scheduler (a photo scheduled for 2026-12-01). The scheduled item
cannot be deleted through the API; it must be cancelled in the app.

Two upstream limits found and handled:
- instagrapi's story viewers parser raises `KeyError` with no viewers and a
  pydantic `ValidationError` with viewers it cannot parse. The tool now returns
  an empty list with a note instead of a failure.
- A message sent by the account itself does not echo over the realtime socket,
  so realtime delivery still needs a real incoming DM from another account.

Also fixed: the approval dialog left the box on screen after a timeout; it is
now closed, and No is the default button so a stray Enter cannot approve.

Two more live findings. A cutout sticker uploads fine. A story with music needs
MoviePy 2.2.1; installing it pulls Pillow 11, which conflicts with instagrapi's
Pillow 13, so Pillow must be restored afterwards. With that workaround the music
story posted. Crossposting was attempted at publish time: Facebook refused with
no confirmed destination and Threads refused with no linked profile, so both are
account-linking blockers, not code.

## 2026-11-10 — Closed out: 36 green, 9 blocked

Every row is now green or blocked with a reason; none is todo or doing. 192
tests pass. Relogin was run later with an Instagram verification code and the
new session reports 10/10 live, so P2 moved from blocked to green. A second
account (`aswathaii`) was then logged in, and its real DM request was approved
live, moving R7 to green.

The second-account work also triggered Instagram's anti-abuse checkpoint. After
the session switch, both accounts answered `ChallengeRequired` and health fell
to 0/10. That is a platform challenge, not a tool defect: it clears by completing
the prompt in the Instagram app on a trusted device. Tagged posts, remove
follower and collaborate are on hold until then.

R23 was proven after the challenge cleared. With a fresh session and the worker
connected, an incoming DM from `deer.9094611` ("How r u") arrived as a
`deltaNewMessage` on topic 146 with seq 1285, about 20 seconds after connect.
One limitation: `normalize_event` left `thread_id` null for that message because
the thread path sits inside a JSON string in the payload, not in a top-level
key. The message itself is in the event value, so no data is lost.

Blocked, with the reason:
- R2 guides: Instagram removed `/v1/guides/user/` (404); tagged is empty because
  the second-account tag post was stopped by the challenge.
- R4 follow requests: nothing pending (0); the account is public, so a follow
  does not create a request.
- R12 hashtag follow: Instagram 404 on the web tags endpoint.
- R16 and W8 hold/approve: no method in instagrapi 3.2.8; `toggle_comments`
  maps to `media_edit`, which has no toggle argument.
- R20 category and professional type: they change the account type and cannot
  be safely restored; bio and AI label are proven.
- R21 report and remove follower: report not run (harmful); remove follower was
  on hold when the challenge hit.
- R22 and W10 crosspost and collaborate: no confirmed Facebook destination, no
  linked Threads profile, no co-author account.



