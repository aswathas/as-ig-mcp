# AS-IG-MCP v1 — Spec

Status: Draft for user review
Date: 2026-11-10
Canonical: `C:\Users\aswat\Projects\as-ig-mcp\docs\superpowers\specs\2026-11-10-as-ig-mcp-v1-design.md`
Research: `docs/study/` and the Obsidian note `AS-IG-MCP/AS-IG-MCP - Capability Matrix.md`

**Name:** AS-IG-MCP
**MCP server id (Claude Code):** `as-ig`
**Package:** `as-ig-mcp` (PyPI-ready), Python module `as_ig_mcp`
**One line:** the Instagram MCP that reads your DMs, measures your posts, tells you what changed, and pushes new messages live — with no Meta app and no company behind it.

---

## 1. Problem & user

Aswath drives Instagram from Claude Code. The vendor MCP (`everyhand-instagram`,
aichargelabs 0.2.7) fails 13 of its read tools with
`RuntimeError: unauthorized use of script (1:5174)`. Measured cause: the frozen
vendor binary bundles instagrapi **3.2.3**, whose `fetch_fb_dtsg()` scrapes
`www.instagram.com/graphql/query/...` — a JSON response with no `__eqmc`
block — so the token is always `None` and Instagram refuses every modern web
endpoint. instagrapi **3.2.8** scrapes the homepage HTML instead, returns a
real token, and every dead endpoint works on the same session cookies. The
vendor binary cannot be patched: modules sit inside the exe PYZ and `iglib` is
pyarmor-obfuscated.

Measured, same account, same session:

| Probe | 3.2.3 (vendor) | 3.2.8 (ours) |
|---|---|---|
| `fb_dtsg` | `None` | `NAfy5kMv8GRdAA2JMQAPCkhvTdjL…` |
| `user_followers` | error | 242 |
| `user_medias` | error | 5 |
| `direct_threads` | error | 10 |
| `explore_page` | error | 16 |
| `direct_messages` (one thread) | error | 4 messages |

The job to be done: read and write Instagram — DMs, feed, followers, stories,
search, publish, comments, insights — from Claude Code, on this machine, for
this one business account, with nothing published or sent without a human
confirm code. And, per the market study, cover every capability the whole
market covers, plus the ones nobody covers.

## 2. Scope — in / out

**In (v1)**

- 16 tools covering roughly 40 capabilities — a superset of every Instagram MCP
  server and every commercial tool's Instagram surface, minus what is
  structurally impossible for a local single-user tool.
- Every read the market has: profile, feed, reels, tagged, saved, collections,
  followers, following, suggestions, follow requests, DM threads and messages,
  message requests, spam box, group threads, presence, notifications, mentions,
  inbox notes, on-post notes, hashtags, places, music, top search, stories
  (own, others, tray, viewers, likers), highlights, comments, insights.
- Every write the market has: DM text/media/voice/file, react, unsend, mark
  seen, share, publish photo/video/reel/carousel/story, IGTV, quicksnap, cutout
  sticker, comment reply/delete/pin/hold/approve/ignore, bulk comment delete,
  comments-enabled toggle, first comment, follow/unfollow/block/mute/report,
  close-friends, hashtag follow, highlight create/edit/cover/delete, inbox note,
  on-post note, profile edit, account category, professional type, AI label,
  crosspost to Facebook/Threads, collaboration invite.
- Scheduling two ways: Instagram's own scheduler (`schedule_at`) for one-off
  posts, and a local queue for drafts and recurring posts.
- **Capabilities nobody in the market has**: a *what changed* delta digest;
  per-post insights compared by age; Instagram's own best-post ranking;
  realtime DM push in a portable MCP (the only competitor uses a Claude Code
  developer channel); a JSONL audit journal of every write attempt; caption and
  hashtag presets; a first-class best-time tool; local competitor benchmarking.
- Safety: a 6-digit confirm code with a preview on every write, an idempotency
  key, and the audit journal.
- Distribution: PyPI package, official MCP registry entry, Claude plugin
  marketplace entry, `claude plugin validate --strict` clean, LICENSE, README,
  tests, a health tool.

**Out (v1) — named, not hidden**

- The official Graph API as a second backend. It needs a Meta app, App Review
  and a linked Facebook Page; DM read alone needs Advanced Access, which is
  weeks of review with common rejection. Our session path needs none of that
  and also reaches personal accounts. Revisit only if the private API dies.
- Multi-user workspaces, roles, approval chains, cross-network publishing,
  cloud media hosting and transcoding, ads platforms, billing, white-label —
  all structurally impossible for a local single-user tool.
- DM auto-reply, comment auto-reply, multi-account. **Paused by user on
  2026-11-10.** Designs are captured in the capability matrix note, ready to
  build.
- Video editing. Posting video is in scope; making it stays with ffmpeg and
  video-shotcraft.
- Live broadcast. `media_create_livestream` returns a stream key — a
  credential, not a reading.
- Browser automation and browser-scraped reads. The private API is our surface.
- Agent-reach style read-only scraping of other people's accounts.

## 3. Success criteria (measurable)

1. `ig_health` reports every endpoint class live, and each of the 13 formerly
   dead reads returns data instead of `unauthorized use of script`. Verified by
   the health output plus one live call per class.
2. Read counts are **> 0 and stable across two consecutive calls** (never
   pinned to a number — Instagram counts move).
3. `ig_thread` last message for a known thread equals `ig_inbox` last message
   for that thread; `ig_person` profile equals `ig_status` account info.
4. A server restart completes a read with **no email code and no re-login**.
5. Every write without a confirm code returns `needs_confirm` + preview + a
   6-digit code and performs **no** Instagram mutation — verified by reading the
   thread afterwards and finding nothing new.
6. `ig_write` with the correct code sends exactly one message; replaying the
   same idempotency key reports "already done" and sends nothing.
7. `ig_digest` twice in a row: the first reports changes, the second reports
   none, without re-fetching unchanged feeds.
8. `ig_insight kind=media` on a known post returns metrics matching
   Instagram's own numbers (post `4024692804391239207` measured 2026-11-10:
   reach 381, impressions 390, likes 22 — the values can only grow, so the
   check is ">=" plus a complete field set).
9. `ig_insight kind=account` returns `has_insights: true`,
   `account_type: BUSINESS_ACCOUNT`, profile visits, follower growth, top posts.
10. `ig_insight kind=best` returns Instagram's own ranked posts for a chosen
    window and ordering key (verified live: `insights_media_feed_all` with
    `ONE_WEEK` and `REACH_COUNT` returns top-post edges).
11. `ig_queue` schedules a post and the scheduled post appears in the queue
    with a future time; a native `schedule_at` publish is accepted by
    Instagram.
12. `ig_digest wait_s=5` returns realtime events when the socket is alive, and
    falls back to polling without error when it is not.
13. Every write attempt — approved, rejected or failed — lands in
    `audit.jsonl` with the action, the target, the outcome and the timestamp.
14. `instagram-fixed`/`as-ig` appears in `claude mcp list` and its tools answer
    from a clean Claude Code session.
15. `ig_search kind=place` either returns results or reports "unsupported" — it
    never raises a raw client error.

## 4. Constraints & environment

- Windows 11, bash shell, Claude Code on this machine.
- Python 3.14 in a **dedicated venv** at `C:\Users\aswat\Projects\as-ig-mcp\.venv`
  (deps: `instagrapi==3.2.8`, `mcp`, `pycryptodomex`). The shared
  `whatsapp-mcp-venv` keeps a stray `instagrapi 3.2.8` from the investigation —
  harmless, because the vendor exe runs its own bundled copy.
- instagrapi 3.2.8 pinned. The stored session keeps the app profile Instagram
  accepted at login (`override_app_version=False` is load-bearing: the app
  profile is part of the device trust).
- Transport: stdio MCP server, same `ig_` naming convention as the vendor, so
  Claude Code namespaces them by server.
- State lives in files, not in one process, so several Claude Code sessions
  share it safely: session (DPAPI-encrypted), cache, digest markers, event
  log, audit journal, queue, presets.
- Instagram limits: rate limits, checkpoint challenges, and the 24-hour reply
  window of the official API (which does not apply to our private-API path).
  Reads are throttled by instagrapi's delay range and cut further by the cache.
- Repo: `C:\Users\aswat\Projects\as-ig-mcp` (git, local). The multi-MCP test
  repo `everyhand-tests` stays untouched.
- Secrets: the session cookie is a live credential — DPAPI-encrypted to the
  current Windows user, never in git, never in the transcript.

## 5. Approach — chosen, with rejected alternatives and why

**Chosen: one local MCP server on instagrapi 3.2.8, private API only, 16
intent-level tools, covering the union of every market capability plus the
white space.**

**Rejected: the Graph API as the backend.** It cannot do realtime, story
viewers, hashtag following, follow requests, close friends or notifications —
the exact surfaces this tool exists for. It also adds weeks of App Review and
a linked Page. The private API is the only surface that gives DMs + posts +
insights + stories in one place, and it works on personal accounts.

**Rejected: a shim over the vendor server.** The vendor is frozen and its
`iglib` is obfuscated, so nothing can be fixed in place, and the dead endpoints
cannot be intercepted from outside.

**Rejected: 35 tools mirroring the vendor's list.** More schemas to load every
session, and the same one-call-three-tools problem. Intent-level tools with
`kind` parameters do the same work with fewer round trips.

**Rejected: a separate long-running daemon for v1.** Session, cache, digest,
events and confirmations live in files, so several Claude Code sessions share
them without a second process, a port and a health check. Revisit only if
concurrent sessions collide on rate limits.

**Rejected: writing over the realtime socket.** Keep using the HTTP write path;
the socket is for reading events only.

**Rejected: browser automation.** Needs a permanently running logged-in
Chrome, breaks when Instagram changes a button, and cannot produce clean data.

**Rejected: one mega tool with a single `action` parameter.** Tool search
matches on names and descriptions; a mega tool makes matching worse. Where a
tool grows past the 4,096-character description limit, split it — `ig_write`
and `ig_manage` — rather than letting one grow.

## 6. Architecture, components & data flow

```
as-ig-mcp/
  pyproject.toml              # instagrapi==3.2.8, mcp, pycryptodomex (pinned)
  README.md                   # install, relogin, health check, tool list
  LICENSE                     # MIT
  .claude-plugin/plugin.json  # Claude plugin manifest
  server.json                 # official MCP registry manifest
  src/as_ig_mcp/
    __init__.py
    server.py                 # stdio MCP server: 16 tools
    client.py                 # instagrapi wrapper: fb_dtsg prefetch, canonical method per feature
    mapping.py                # THE table: feature -> canonical instagrapi method
    session.py                # DPAPI load/save, relogin
    cache.py                  # TTL cache on disk, fresh= bypass
    digest.py                 # last-seen markers, change detection
    realtime.py               # socket thread, direct_subscribe, ping watchdog
    events.py                 # events.jsonl, tail with cursor + timeout
    queue.py                  # local publish queue, recurrence, native schedule
    presets.py                # caption / hashtag / first-comment presets
    writes.py                 # write kinds, confirm gate, idempotency
    audit.py                  # audit.jsonl journal
    health.py                 # endpoint-class probe
    state.py                  # paths under %APPDATA%\as-ig-mcp
  tests/                      # offline tests, no Instagram calls
```

**Data flow**

1. Claude Code starts `as-ig` (stdio) → `server.py` reads the DPAPI session from
   `%APPDATA%\as-ig-mcp\session.enc` and builds the instagrapi client with the
   pinned app profile.
2. `client.py` prefetches `fb_dtsg` from the Instagram homepage (instagrapi
   3.2.8's `fetch_fb_dtsg`) and caches it per process; on a GraphQL or JSON
   error it refetches once, then falls back to the api/v1 REST variant of that
   feature.
3. A tool call resolves to **one canonical instagrapi method per feature**
   (`mapping.py`), converts the result to plain JSON, and returns it as MCP
   content.
4. Reads pass through `cache.py` (default TTL 90 seconds, `fresh=true` bypasses).
5. `ig_digest` compares current state against `digest.json` and rewrites the
   markers; with `wait_s` it also long-polls the realtime queue.
6. Writes pass through `writes.py`: the first call stores the pending action,
   returns `needs_confirm` + a preview + a 6-digit code, and performs nothing.
   The second call with the matching code executes once; an idempotency key
   makes a repeat a no-op. Every attempt is journalled to `audit.jsonl`.
7. `ig_health` calls one representative method per endpoint class (REST
   profile, GraphQL feed, GraphQL followers, GraphQL threads, GraphQL search,
   GraphQL stories, DM read, DM write preview, insights, business DM box,
   notifications, realtime socket) and reports live or dead, naming the remedy
   when dead.

**State**

- Session: `%APPDATA%\as-ig-mcp\session.enc` (DPAPI, current Windows user).
- Cache: `cache.json` (TTL entries, atomic write).
- Digest markers: `digest.json`.
- Realtime events: `events.jsonl` (append-only, with a cursor).
- Audit journal: `audit.jsonl` (append-only, every write attempt).
- Queue: `queue.json` (scheduled and recurring posts).
- Presets: `presets.json` (caption, hashtag and first-comment templates).
- Pending write confirmations: in-memory only, lost on restart = safe.

**Tool surface — 16 tools**

| Tool | Capabilities |
|---|---|
| `ig_status` | session state, account, quota, cache state, realtime state, one-line health |
| `ig_inbox` | threads awaiting a reply, last message, optional suggested reply from our style file |
| `ig_thread` | thread messages (paginated), presence, per-thread actions (mark seen, react, unsend, mute, hide, title, group members) |
| `ig_person` | profile with `include=` followers, following, posts, stories, highlights, comments, suggestions, about |
| `ig_people` | followers, following, suggestions, follow requests (approve/decline) — paginated |
| `ig_search` | `kind=user\|hashtag\|place\|music\|post\|message\|account` |
| `ig_feed` | `kind=posts\|reels\|tagged\|saved\|archive\|notifications\|collections\|tray\|guides\|liked` |
| `ig_story` | story and highlight detail, viewers, likers, download |
| `ig_digest` | what changed since the last call; `wait_s` long-polls realtime events |
| `ig_insight` | `kind=media\|account\|best\|compare\|demographics` |
| `ig_write` | every write below, behind one confirm gate |
| `ig_queue` | list, schedule, cancel, recurring posts, native Instagram schedule |
| `ig_preset` | caption, hashtag and first-comment presets — local, product-only everywhere else |
| `ig_health` | live/dead per endpoint class, with the remedy named |
| `ig_session` | status, relogin with the emailed code, cache clear, export, linked accounts |
| `ig_account` | account insights units, professional settings, category, AI label, linked accounts |

**Write kinds behind `ig_write`** — `send_message`, `send_media`, `send_voice`,
`send_file`, `react`, `unsend`, `mark_seen`, `share`, `publish` (photo, video,
reel, carousel, story, IGTV, quicksnap, cutout sticker), `schedule`,
`first_comment`, `comment` (reply, delete, pin, hold, approve, ignore),
`bulk_delete_comments`, `toggle_comments`, `follow`, `unfollow`, `block`,
`mute`, `report`, `remove_follower`, `close_friend`, `follow_hashtag`,
`highlight`, `note`, `profile`, `category`, `ai_label`, `crosspost`,
`collaborate`.

**Canonical instagrapi method per feature** (`mapping.py`, the single place to
change when Instagram moves) — profile `user_info_v1`; followers
`user_followers_v1`; following `user_following_v1`; posts `user_medias_v1`
(fallback `user_medias_gql`); best posts `insights_media_feed_all`; per-post
insights `insights_media`; account insights `insights_account`; stories
`user_stories_web`; story tray following list then `user_stories_web` per user;
thread list `direct_threads`; business DM box `direct_threads(box="general")`;
thread messages `direct_messages`; DM search `direct_message_search`; presence
`direct_active_presence`; send `direct_send` / `direct_send_photo` /
`direct_send_voice` / `direct_send_file`; reactions `direct_send_reaction`;
unsend `direct_message_unsend`; publish `photo_upload` / `video_upload` /
`clip_upload` / `album_upload` / `photo_upload_to_story`; native schedule the
same methods with `schedule_at`; comments `media_comments` / `media_comment` /
`comment_bulk_delete` / `comment_pin`; notifications `notification_likes`,
`notification_comments`, `notification_new_follower`, `notification_user_tagged`;
notes `get_notes`, `create_note`, `media_note_create`; hashtag
`hashtag_info`, `hashtag_medias_top`, `hashtag_medias_recent`, `hashtag_follow`;
place `fbsearch_places`, `location_search`; music `search_music`, `music_trending`;
top search `fbsearch_topsearch_v2`; users `search_users`; suggestions
`user_suggested_profiles`; highlights `user_highlights_v1`, `highlight_create`,
`highlight_edit`, `highlight_change_cover`, `highlight_delete`; follow
`user_follow` / `user_unfollow`; block `user_block`; mute
`mute_posts_from_follow`; close friends `close_friend_add`; crosspost
`media_share_to_threads_config`, `media_share_to_fb_unified_config`;
collaboration `coauthor_user_ids` on the upload methods; profile edit
`account_edit`, `account_set_biography`, `set_external_url`; category
`account_convert_to_professional`; AI label `account_set_ai_info`.

**Realtime** — one daemon thread per server run. On the main thread
`rt.direct_subscribe()` runs once (it reads `seq_id` and `snapshot_at_ms` from
`client.direct_threads()` and subscribes to the message-sync stream — without
it the socket connects and no message ever arrives). The thread loops
`realtime_read_once()`, pings every 15 seconds (MQTT keep-alive is 20), and
reconnects with backoff because instagrapi has no reconnect logic. Events
(`receive`, `message`, `thread_update`, `iris`, `direct`, `typing`, `seen`,
`presence`) are normalised to `{"ts","event","thread_id","value"}` and appended
to `events.jsonl`. There is **no** reaction event — reactions arrive as
message patches and are classified by us. FBNS is skipped (separate host and
device auth). Sending stays on the HTTP path.

## 7. Failure modes & error handling

| Failure | Detection | User sees | System does next |
|---|---|---|---|
| IG session expired or revoked | first call raises `LoginRequired`/`Unauthorized`, or `fb_dtsg` fetch returns None | "session expired" plus the relogin command | stops using the cached session; no blind retries |
| IG kills the session remotely / device fingerprint mismatch | `ChallengeRequired` on any call | "checkpoint needed" and what to do | surfaces the challenge; asks for a code once |
| Endpoint breaks upstream again | `ig_health` shows the class dead | health report naming the class | bump instagrapi; no code change |
| `fb_dtsg` stale mid-process | `ClientGraphqlError` / `ClientJSONDecodeError` | normal result (recovered) | refetch once, then use the REST variant |
| Realtime socket dies or Instagram closes it | reader thread raises, or `ig_health` socket probe fails | realtime state shows disconnected | reconnect with backoff; fall back to polling |
| Realtime payload shape changes | unknown event kind | event recorded as `unknown` with the raw payload | keep serving; the digest still works |
| Rate limited | HTTP 429 | status and retry-after | backoff, then report |
| Write called without or with a wrong confirm code | confirm check | `needs_confirm` + preview + code, no mutation | nothing sent; a wrong code is refused |
| Same write submitted twice | idempotency key | "already done" | no second message, no second post |
| Queue item fires while the machine is asleep | item overdue at next start | "2 items were overdue" | publishes late, marks them, and tells the user |
| DPAPI decrypt fails (different Windows user) | decrypt error at startup | "session belongs to another Windows user" | starts with no session and asks for a relogin |
| Malformed session file | load error | error plus the relogin command | refuses to start rather than half-working |
| Insights requested on a personal account | payload has no insights node | "no insights on this account type" | clear message, not a raw client error |
| Two Claude Code sessions write state at once | atomic writes | none (silent) | last writer wins for the cache; digest markers merge by timestamp |

No write is auto-retried after a partial failure. The operator decides.

## 8. Test plan

1. **Offline unit tests** (`tests/`): DPAPI round-trip; `mapping.py` covers
   every feature in §6 exactly once; cache TTL and `fresh=true`; digest marker
   update; confirm-code validation (wrong code, expired code, single use);
   idempotency replay; audit journal entries written for approved, rejected and
   failed writes; queue recurrence maths; preset CRUD.
2. **Live health test** (`ig_health`): every class live; counts > 0 and stable
   across two calls.
3. **Cross-check**: `ig_thread` last message == `ig_inbox` last message;
   `ig_person` profile == `ig_status` account info.
4. **Persistence test**: stop the server, start it again, read a thread — no
   email code.
5. **Write-gate test**: `ig_write kind=send_message` without confirm →
   `needs_confirm`; read the thread → no new message; with the code → exactly
   one message; replay the same idempotency key → "already done".
6. **Audit test**: `audit.jsonl` contains the rejected attempt, the approved
   attempt, and the target thread id.
7. **Digest test**: `ig_digest` twice → the second reports no changes.
8. **Insights test**: `ig_insight kind=media` on post `4024692804391239207`
   returns reach, impressions, likes, comments, shares, profile views and
   hashtag data; `kind=account` returns the account units; `kind=best` ranks
   the last week by reach; `kind=compare` ranks the last 5 posts.
9. **Realtime test**: `ig_digest wait_s=10` returns a typing or seen event when
   someone is active in a thread; with the socket stopped it returns without
   error.
10. **Queue test**: schedule a post one hour out, confirm it sits in
    `queue.json`, then cancel it.
11. **Negative test**: corrupt the session file → the server reports it and does
    not crash.

Passing = all 13 dead reads return data, health is green, the write gate
holds, the digest is quiet on the second call, restart needs no code, and every
write attempt is journalled.

## 9. Implementation ownership — agent implements + build order

Agent implements. Each phase ends with a runnable check.

| Phase | Build | Check |
|---|---|---|
| 0 | Vendor bug report (wrong URL, repro, fix) | exists in the repo; if aichargelabs ships 3.2.8 the project can shrink to a config change |
| 1 | Package skeleton, dedicated venv, `session.py` (DPAPI), `client.py`, `mapping.py`, `state.py` | offline tests pass |
| 2 | Read tools (`ig_status`, `ig_person`, `ig_people`, `ig_feed`, `ig_search`, `ig_story`, `ig_thread`, `ig_inbox`) + `ig_health` | the 13 dead reads return data; health green |
| 3 | Register in Claude Code | `claude mcp list` shows it; a clean session calls a tool |
| 4 | `ig_write` + confirm gate + idempotency + `audit.py` | write-gate, audit and idempotency tests pass |
| 5 | `ig_session` relogin, `ig_account`, `ig_insight` | relogin works; insights match Instagram's numbers |
| 6 | `ig_queue`, `ig_preset`, native `schedule_at` | queue test passes; native schedule accepted |
| 7 | `realtime.py`, `events.py`, `ig_digest wait_s` | realtime test passes; polling fallback intact |
| 8 | README, `tool-map.md`, LICENSE, plugin manifest, `server.json`, `claude plugin validate --strict`, PyPI publish, registry publish, marketplace entry | a stranger can install and run it in one command |

## 10. Risks, assumptions, and what would invalidate this spec

**Assumptions**

- A1. Instagram keeps serving instagrapi 3.2.8's endpoint set. If it changes
  again the fix is a version bump — `mapping.py` exists precisely so that
  absorbing a change is one file.
- A2. The session stays valid for weeks; recovery is one emailed code through
  `ig_session relogin`, or a browser-cookie fallback if a checkpoint blocks the
  scripted path.
- A3. `fb_dtsg` scraping from the homepage keeps working. Observed
  2026-11-10.
- A4. DPAPI through `ctypes` is enough to protect the session cookie; no
  third-party crypto dependency needed.
- A5. The 16-tool intent surface beats 35 action tools for our use. Reasoning,
  not measured: fewer schemas to load, fewer round trips, one search tool
  instead of seven. If tool-name muscle memory matters more, `mapping.py`
  makes splitting a tool back out cheap.
- A6. Realistic maintenance: a handful of touchpoints a month — mostly one
  emailed code to log in again, rarely a browser challenge. Reasoning, not
  measured over time. The recovery path stays one command.
- A7. Insights stay available on the private API for this account. Measured
  2026-11-10: `has_insights: true`, `account_type: BUSINESS_ACCOUNT`. If
  Instagram moves insights to Graph-only, `ig_insight` is the one tool needing
  a fallback.
- A8. Insights metrics are partial and lag. Account units are weekly
  snapshots; per-post counts keep growing. Comparisons must match posts of
  similar age, never "best ever" against "posted yesterday".
- A9. The realtime transport keeps working and its payload shape stays stable.
  It is Instagram-private and explicitly may change without notice, so it
  ships behind a flag with polling as the default fallback.

**Decisions baked into this spec** (user may flip any of them)

- D1. v1 carries the full reachable superset, built in phases. The capability
  matrix is the acceptance list.
- D2. Scheduling is both: Instagram's own `schedule_at` for one-off posts, and
  a local queue for drafts and recurring posts.
- D3. Realtime ships behind a flag, with the polling digest as the default;
  `ig_health` probes the socket.
- D4. Private API only for v1. The Graph API is a later project, if the
  private API dies.
- D5. DM auto-reply, comment auto-reply and multi-account are parked, with
  designs captured.

**Risks**

- M1. Instagram blocks the account for scripted use. Mitigation: 90-second
  cache, throttled reads, confirm gate on every write, `ig_health`, and the
  option to stop using the tool.
- M2. Realtime is the most fragile surface in the server. Mitigation: flag
  plus polling fallback, ping watchdog, reconnect with backoff, socket probe in
  `ig_health`.
- M3. Two servers with similar tool names can confuse the agent. Mitigation:
  every tool description starts with `[AS-IG-MCP]`; the ownership map is in the
  README.
- M4. `ig_write` with many `kind` values could drift toward a mega-tool, which
  hurts tool-search matching. Mitigation: split into `ig_write` and
  `ig_manage` if its description passes 4,096 characters.
- M5. The audit journal and presets hold user content on disk. Mitigation:
  under `%APPDATA%`, never in git, documented in the README's data-handling
  section, with a clear-and-delete command.
- M6. Publishing to the registry without trust signals. Mitigation: the
  Anthropic pre-submission checklist — LICENSE, README over 40 words, pinned
  exact-version launcher, secrets via `userConfig` with `sensitive: true`,
  `claude plugin validate --strict` clean, tests, health tool.
- M7. Smithery's MCP Proxy and managed identity shut down 2026-10-31 and its
  CLI and SDKs are deprecated. Do not depend on it; it survives only as a
  directory.
- M8. The private API is the ToS-violating path the commercial vendors warn
  about. That liability is ours, and it is the main reason for the confirm
  gate, the cache, the throttling and the health tool.

**What would invalidate this spec**

- Instagram stops serving the `fb_dtsg` scrape too — then the script endpoints
  die for everyone and the Graph API becomes the only remaining option for
  public reads.
- The account becomes a personal (non-business) account in a region where the
  private API is fully blocked — then no client-side fix exists.
- The user decides DM reading does not matter — then the server shrinks to
  public reads plus publishing.

---

## Exit condition

The spec is complete only when all ten sections above are filled with concrete
content, no section contains `TBD`/`TODO`/an empty placeholder, and the user
has said "approved" in response to seeing this file. An agent may not declare
the spec complete on its own judgement. If a section cannot be filled, write
the assumption explicitly in section 10 and ask the user about it.
