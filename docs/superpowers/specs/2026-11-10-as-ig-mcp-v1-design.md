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
endpoint. `__eqmc` is the marker in Instagram's web page HTML that carries the
Facebook CSRF token (`fb_dtsg`); it exists in the page, never in a JSON
response. instagrapi **3.2.8** scrapes the homepage HTML instead, returns a
real token, and every dead endpoint works on the same session cookies. The
vendor binary cannot be patched: its modules sit inside the exe archive, and
`iglib` — the vendor's own wrapper layer around instagrapi, protected by
pyarmor code obfuscation — cannot be edited either.

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
owner's approval on their screen. And, per the market study, cover every capability the whole
market covers, plus the ones nobody covers.

## 2. Scope — in / out

**In (v1)**

- 16 tools covering the capabilities listed in the acceptance list,
  `docs/reviews/capability-checklist.md` (45 rows, one row per capability, each
  with a check) — a superset of every Instagram MCP server and every commercial
  tool's Instagram surface, minus what is structurally impossible for a local
  single-user tool. The market comparison behind that claim is
  `docs/study/AS-IG-MCP - Capability Matrix.md` (and the same note in the
  Obsidian vault).
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
  per-post insights compared by age; Instagram's own best-post ranking wrapped
  for an agent (Instagram exposes the ranking, nobody exposes it as a tool);
  realtime DM push in a portable MCP (the only competitor uses a Claude Code
  developer channel); a JSONL audit journal of every write attempt; caption and
  hashtag presets; a first-class best-time tool; local competitor benchmarking
  of **public** business profiles, read through the same API — reading another
  account's private data, or scraping a profile the API does not expose, is out
  of scope.
- Safety: every write asks the account owner first — a yes/no dialog on their own
  screen showing the exact action — plus an idempotency key and the audit
  journal. No approval code exists anywhere, so there is nothing for the agent
  to relay or fetch.
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
   for that thread — `ig_inbox` takes an optional `thread_id` so a specific
   thread can be checked; `ig_person` profile equals `ig_status` account info.
4. A server restart completes a read with **no email code and no re-login**.
5. Every write asks the account owner first. `ig_write` shows a yes/no dialog
   with the exact action; if the human says No, Cancel, or the dialog times out,
   **no** Instagram mutation happens — verified by reading the thread afterwards
   and finding nothing new. No approval code exists anywhere: not in the tool
   result, not in a file, not in the agent's context. Only the human's click
   approves the write.
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
16. **No read path can mutate.** Calling a feature whose mapping entry is not
    read-only, without `allow_write=True`, raises and the underlying instagrapi
    method is never called. Verified with a fake client that records calls.
17. **One live login on the account.** The `sessionid` our server holds equals the
    one the vendor daemon holds. Verified by comparing the two session stores.

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
  Reads are throttled by instagrapi's per-request delay range, which we set to
  one to three seconds, and cut further by the 90-second cache.
- Repo: `C:\Users\aswat\Projects\as-ig-mcp` (git, local). The multi-MCP test
  repo `everyhand-tests` stays untouched.
- Secrets: the session cookie is a live credential — DPAPI-encrypted to the
  current Windows user, never in git, never in the transcript.

**Configuration** — environment variables read at call time, all optional:

| Variable | Meaning | Default |
|---|---|---|
| `APPDATA` | where the state lives | the Windows user profile |
| `IG_PLACES_LAT`, `IG_PLACES_LNG` | coordinates for place search | unset — `ig_search kind=place` says so |
| `AS_IG_REALTIME` | `0` turns the realtime socket off | on |
| `AS_IG_REALTIME_TIMEOUT` | seconds the approval dialog waits | 300 |
| `AS_IG_CACHE_TTL` | read cache seconds | 90 |

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
matches on names and descriptions; a mega tool makes matching worse. Claude
Code cuts a server's upfront tool descriptions at 4,096 characters, so a tool
whose description grows past that would stop being discoverable. v1 ships 16
tools and no `ig_manage`; if `ig_write` ever outgrows the limit, it splits into
`ig_write` and `ig_manage` then.

## 6. Architecture, components & data flow

```
as-ig-mcp/
  pyproject.toml              # instagrapi==3.2.8, mcp (pinned); no pycryptodomex
  README.md                   # install, relogin, health check, tool list
  LICENSE                     # MIT
  .claude-plugin/plugin.json  # Claude plugin manifest
  server.json                 # official MCP registry manifest
  src/as_ig_mcp/
    __init__.py
    __main__.py               # python -m as_ig_mcp
    cli.py                    # status, health, session import, pending, serve
    server.py                 # stdio MCP server: 16 tools
    client.py                 # instagrapi wrapper: fb_dtsg prefetch, read-only guard, call_write
    mapping.py                # THE table: feature -> canonical method + read_only
    serialize.py              # instagrapi objects -> plain JSON
    session.py                # DPAPI load/save, relogin
    state.py                  # paths under %APPDATA%\as-ig-mcp, SQLite state
    cache.py                  # TTL cache in SQLite, fresh= bypass
    digest.py                 # last-seen markers, change detection
    realtime.py               # socket thread, direct_subscribe, ping watchdog
    events.py                 # events.jsonl, tail with cursor + timeout
    queue.py                  # local publish queue, recurrence, native schedule
    presets.py                # caption / hashtag / first-comment presets
    writes.py                 # write kinds, approval dialog, idempotency
    audit.py                  # audit.jsonl journal
    tools_status.py           # ig_status
    tools_health.py           # ig_health
    tools_session.py          # ig_session
    tools_people.py           # ig_person, ig_people
    tools_discovery.py        # ig_search
    tools_feed.py             # ig_feed
    tools_threads.py          # ig_thread
    tools_inbox.py            # ig_inbox
    tools_story.py            # ig_story
    tools_account.py          # ig_account
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
6. **Every mutation on the account goes through `writes.py`, whatever tool the
   agent calls.** `ig_write` is the direct path; `ig_thread` (mark seen, react,
   unsend, mute, hide, title, group members) and `ig_account` (professional
   settings, category, AI label) delegate to it rather than mutating on their
   own.

   **The human approves by clicking, not by typing a code.** `ig_write` builds a
   one-line preview of the exact action, shows the account owner a Windows
   yes/no dialog (MessageBox through `ctypes`, on its own thread) with that
   preview, and waits. Yes = the write happens. No, Cancel, or a five-minute
   timeout = nothing happens. There is no code anywhere: none in the tool
   result, none in the agent's context, none in a file. The agent cannot relay
   an approval it does not have, because the approval is a click on the owner's
   screen that the agent never sees.

   The tool returns the result of the write, or `{"ok": False, "denied": true,
   "preview": ...}` when the human declined. Every attempt is journalled to
   `audit.jsonl` with the state: requested, approved, denied, timeout, failed.

   On a machine with no interactive desktop session there is no way to ask a
   human, so the write is refused with a clear message. A write needs a person
   at the keyboard; that is the price of not letting the agent approve itself.

   Claude Code's own permission prompt is used as a second, coarser gate: the
   `ig_write` tool declares `_meta["anthropic/requiresUserInteraction"]`, so
   the harness also asks before the call runs. The dialog is the fine-grained
   check — it shows what will actually happen.

   `ig_write` also carries the standard tool annotations: `readOnlyHint=false`,
   `destructiveHint` per kind, `idempotentHint` true for kinds that accept an
   idempotency key, `openWorldHint=true`.
7. **Scheduled work is approved at enqueue time.** `ig_queue` and Instagram's
   native `schedule_at` are writes, so they go through the same dialog: the
   owner approves the queued post once, when they queue it, and the item
   carries that approval. The five-minute runner publishes an already-approved
   item rather than creating a new one. The rule "no mutation without the
   owner's approval" therefore holds for scheduled posts too — the approval is
   given once, by the human, at the moment they queue the post.
8. Any write clears the cache entries it touched (`cache.invalidate_prefix`), and
   the digest compares against live state, never against the cache — otherwise
   a digest could report "nothing changed" from stale cached reads.
9. **A write never falls back to another method.** The REST↔GraphQL fallback
   exists for reads, where a second attempt costs nothing. For a write, a
   failed response is reported to the owner and not retried by us, because
   Instagram may have accepted it before the response failed to parse. One
   attempt, one outcome, and the audit journal records which.
10. `ig_health` calls one representative method per endpoint class (REST
    profile, GraphQL feed, GraphQL followers, GraphQL threads, GraphQL search,
    GraphQL stories, DM read, DM write preview, insights, business DM box,
    notifications, realtime socket) and reports live or dead, naming the remedy
    when dead.
11. **State lives in one SQLite file, not loose JSON.** `cache.json`,
    `digest.json` and `queue.json` become tables in `%APPDATA%\as-ig-mcp\state.db`,
    so the MCP server, the queue runner and a second Claude Code session can
    write at the same time without one clobbering the other's work. Loose JSON
    with a whole-file rewrite meant the last writer silently discarded the
    rest of the cache — and the 90-second cache is the main defence against an
    account block. SQLite is in the standard library, so this costs no
    dependency.

**State**

- Session: `%APPDATA%\as-ig-mcp\session.enc` (DPAPI, current Windows user).
- Cache, digest markers and the publish queue: tables in
  `%APPDATA%\as-ig-mcp\state.db` (SQLite, stdlib), so several processes can write
  at once without clobbering each other.
- Reply style: `%APPDATA%\as-ig-mcp\style.json` — one object per contact or
  account holding `relationship`, `language`, `formality`, `personality_notes`,
  `topics` and `response_style`. `ig_inbox suggest=true` uses it to draft a
  reply. It is local memory, not Instagram data.
- Realtime events: `events.jsonl` (append-only, with a cursor).
- Audit journal: `audit.jsonl` (append-only, every write attempt).
- There is no pending-approval store: a write is approved in one call, so there
  is nothing to keep between calls.
- Presets: `presets.json` (caption, hashtag and first-comment templates).
- Pending write confirmations: in-memory only, lost on restart = safe.

**Tool surface — 16 tools**

| Tool | Capabilities |
|---|---|
| `ig_status` | session state, account details, cache state, realtime state, one-line health. It reports **no quota**: instagrapi has no quota endpoint, so any number would be invented. |
| `ig_inbox` | threads awaiting a reply, last message, optional suggested reply from our style file |
| `ig_thread` | thread messages (paginated), presence, and read-only thread detail. Mutating thread actions (mark seen, react, unsend, mute, hide, title, group members) are **not** its own; they are `ig_write` kinds and `ig_thread` only points at them. |
| `ig_person` | profile with `include=` followers, following, posts, stories, highlights, comments, suggestions, about |
| `ig_people` | followers, following, suggestions, follow requests (approve/decline) — paginated. Approving a follow request is a write and goes through `ig_write`. |
| `ig_search` | `kind=user\|hashtag\|place\|music\|post\|message\|account` |
| `ig_feed` | `kind=posts\|reels\|tagged\|saved\|archive\|notifications\|collections\|tray\|guides\|liked` |
| `ig_story` | story and highlight detail, viewers, likers, download |
| `ig_digest` | what changed since the last call; `wait_s` long-polls realtime events |
| `ig_insight` | `kind=media\|account\|best\|best_time\|compare\|demographics`. `best` is Instagram's own ranked posts for a window and ordering key. `best_time` is the posting-window recommendation computed from our own account insights — the thing Metricool sells. `compare` ranks our posts against each other by a chosen metric, and combined with `ig_person` on another account it is the local competitor comparison. |
| `ig_write` | every write below, behind one confirm gate. This is the only path that mutates. |
| `ig_queue` | list, schedule, cancel, recurring posts, native Instagram schedule. The local queue needs a runner: a Windows Scheduled Task that runs `python -m as_ig_mcp queue tick` every five minutes, installed once by the user. Instagram's own `schedule_at` stays the server-independent path, so a scheduled post survives our machine being off. |
| `ig_preset` | caption, hashtag and first-comment presets — local, product-only everywhere else |
| `ig_health` | live/dead per endpoint class, with the remedy named |
| `ig_session` | status, relogin with the emailed code, cache clear, and `export` — the session settings as JSON with `sessionid` and `csrftoken` replaced by `"<redacted>"`, so the owner can back it up without the tool leaking a live cookie. Relogin is `python -m as_ig_mcp session relogin`, which prompts for the emailed code and then rewrites `session.enc`. |
| `ig_account` | account insights units, linked accounts (Instagram's own account switcher — accounts linked to this login), and the professional settings that `ig_write` can change |

**Write kinds behind `ig_write`** — `send_message`, `send_media`, `send_voice`,
`send_file`, `react`, `unsend`, `mark_seen`, `share`, `publish` (photo, video,
reel, carousel, story, IGTV, quicksnap, cutout sticker), `schedule`,
`first_comment`, `comment` (reply, delete, pin, hold, approve, ignore),
`bulk_delete_comments`, `toggle_comments`, `follow`, `unfollow`, `block`,
`mute`, `report`, `remove_follower`, `close_friend`, `follow_hashtag`,
`highlight`, `note`, `profile`, `category`, `ai_label`, `crosspost`,
`collaborate`, plus the ones the prose names elsewhere: `share`, `report`,
`remove_follower`, `toggle_comments`, `thread_hide`, `thread_title`,
`thread_group_members`, `follow_request_approve`, `follow_request_decline`,
`mute_stories`, `unblock`.

In that list: **IGTV** is Instagram's long-form video format, a separate upload
endpoint from a reel. **Quicksnap** is Instagram's disappearing photo, sent to
mutual followers only. A **cutout sticker** is a photo with the background
removed, uploaded as a sticker. All three exist as separate instagrapi upload
methods, and all three are in the mapping with `read_only=False`.

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
`clip_upload` / `album_upload` / `photo_upload_to_story` / `igtv_upload` /
`quicksnap_send` / `photo_upload_to_cutout_sticker` /
`video_upload_to_cutout_sticker`; native schedule the
same upload methods with `schedule_at`; comments `media_comments` /
`media_comment` /
`comment_bulk_delete` / `comment_pin`; notifications `news_inbox_v1` — **not**
`notification_likes` and its siblings, which are settings mutators that POST to
`notifications/change_notification_settings/` with a default of `"off"`;
notes `get_notes`, `create_note`, `media_note_create`; hashtag
`hashtag_info`, `hashtag_medias_top`, `hashtag_medias_recent`, `hashtag_follow`;
place `fbsearch_places`, `location_search`; music `search_music`, `music_trending`;
top search `fbsearch_topsearch_v2`; users `search_users`; suggestions
`user_suggested_profiles`; highlights `user_highlights_v1`, `highlight_create`,
`highlight_edit`, `highlight_change_cover`, `highlight_delete`; follow
`user_follow` / `user_unfollow`; block `user_block`; mute
`mute_posts_from_follow` and `mute_stories_from_follow`; close friends
`close_friend_add`; report `user_report`; remove follower
`user_remove_follower`; unblock `user_unblock`; share `direct_media_share` /
`direct_profile_share` / `direct_story_share`; thread hide `direct_thread_hide`;
thread title `direct_thread_update_title`; group members
`direct_thread_add_users` / `direct_thread_remove_users`; follow requests
`user_follow_request_approve` / `user_follow_request_decline`; crosspost
`media_share_to_threads_config`, `media_share_to_fb_unified_config`;
collaboration `coauthor_user_ids` on the upload methods; profile edit
`account_edit`, `account_set_biography`, `set_external_url`; category
`account_convert_to_professional`; AI label `account_set_ai_info`.

**Read-only is a property of the mapping, not a promise.** Every entry in
`mapping.py` declares `read_only: True` or `False`, decided by reading the
installed instagrapi source. `client.call_feature` refuses a non-read-only
feature unless the caller passes `allow_write=True`, and only the write module
does that. A read path therefore cannot mutate the account — the guard is
structural, not a code-review habit. Anything ambiguous is treated as a write.
This exists because instagrapi mixes readers and mutators under similar names:
`notification_likes(setting_value="off")` reads like a getter and silently
turns notifications off.

**Verification depth.** The core capabilities (everything in the capability
checklist) are verified with a live call. The exotic write kinds — IGTV,
quicksnap, cutout sticker, collaboration invite, crosspost, category
conversion, professional type, AI label — stay in the mapping, because a
mapping entry is one line, but they are verified by unit test only: the method
exists and is callable with the documented arguments. No live call is made for
them.

**Realtime** — one daemon thread per server run. It is **on by default**; set
`AS_IG_REALTIME=0` to turn it off, in which case `ig_digest` polls and
everything else behaves identically. On the main thread `rt.direct_subscribe()`
runs once (it reads `seq_id` and `snapshot_at_ms` from `client.direct_threads()`
and subscribes to the message-sync stream — without it the socket connects and
no message ever arrives). The thread loops `realtime_read_once()`, pings every
15 seconds (MQTT is the message protocol Instagram speaks on this socket, and
its keep-alive is 20 seconds), and reconnects with backoff because instagrapi
has no reconnect logic. Events (`receive`, `message`, `thread_update`, `iris`,
`direct`, `typing`, `seen`, `presence`) are normalised to
`{"ts","event","thread_id","value"}` and appended to `events.jsonl`. `iris` is
Instagram's name for the non-thread part of the realtime payload. There is
**no** reaction event — reactions arrive as message patches and are classified
by us. FBNS (Facebook's separate push-notification channel, different host and
device authentication) is skipped. Sending stays on the HTTP path. The socket
belongs to one account and one process; a second Claude Code session opens its
own socket, and every event carries the account it came from.

**One login, two servers.** The vendor daemon keeps running as a fallback, and
both servers use the same Instagram login: our `sessionid` is injected into the
vendor with `instagram-mcp.exe login --sessionid-env IG_SESSIONID`, so the
account never carries two live sessions. The vendor's dead tools stay dead —
its instagrapi is frozen — but it keeps its working reads and its local
reply-style store.

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
| Write called and the human says No, Cancel, or the dialog times out | the dialog's return value | the tool returns `{"ok": False, "denied": true, "preview": ...}` | nothing is sent; the attempt is journalled as denied |
| Write called on a machine with no interactive desktop | the dialog call fails | "no interactive desktop — a write needs a person at the keyboard" | nothing is sent; the attempt is journalled as failed |
| A write's response fails to parse | the exception after a POST | "the request may have gone through — check before retrying" | never retried automatically, never fallen back to another method; the owner decides |
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
5. **Write-gate test**: `ig_write kind=send_message` → a yes/no dialog appears
   with the preview; the human answers No → the tool returns `denied` and the
   thread is unchanged; the human answers Yes → exactly one message appears;
   replaying the same idempotency key → "already done" and no second message.
   The dialog is faked in the test, so no test ever touches the real desktop.
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

Agent implements. Each phase ends with a runnable check. The loop itself —
which worker takes a phase, how the orchestrator verifies it, who commits, and
when a review runs — is `docs/reviews/loop.md`. Two rules matter most here:
the orchestrator runs the phase check itself and never accepts a worker's claim
as evidence, and workers never commit.

| Phase | Files it may touch | Check (command) | Status |
|---|---|---|---|
| 01 | `pyproject.toml`, `src/as_ig_mcp/{__init__,state,session,client,mapping}.py`, `tests/` | `.venv/Scripts/python.exe -m pytest -q` → 13 passed | done |
| 02 | `src/as_ig_mcp/{cache,cli,__main__,server,tools_status,tools_health,tools_session}.py`, `tests/` | `pytest -q` → 22 passed; `python -m as_ig_mcp health` → 8/10 live | done |
| 02b | `src/as_ig_mcp/{mapping,client,cache,tools_health,tools_status}.py`, `tests/` | `pytest -q` → 33 passed; a mutating feature raises and the method is never called | done |
| 03a | `src/as_ig_mcp/{serialize,tools_people,tools_discovery,tools_feed,server}.py`, `tests/` | `pytest -q` → 59 passed; live: profile, followers, following, search, posts, reels, saved, notifications | done |
| 03b | `src/as_ig_mcp/{tools_threads,tools_inbox,tools_story,tools_account,server}.py`, `tests/` | `pytest -q` → 73 passed; live: a thread, the inbox, the account block and insights | done |
| 04 | `src/as_ig_mcp/{writes,audit,client,server}.py`, `tests/test_writes.py`, `tests/test_tool_write.py` | `pytest -q` → all pass; a denied write makes no Instagram call; the journal has one line per attempt | running |
| 05a | `src/as_ig_mcp/{state,cache,digest,session,cli,server,tools_insight}.py`, `tests/` | `pytest -q` → all pass; two connections to the same database see each other's rows | next |
| 05b | `src/as_ig_mcp/{queue,presets,tools_queue,tools_preset}.py`, `tests/` | `pytest -q` → all pass; a queued item fires once and never twice | planned |
| 06 | `src/as_ig_mcp/{realtime,events,tools_digest}.py`, `tests/` | `pytest -q` → all pass; `ig_digest wait_s=10` returns an event while the socket is alive | planned |
| 07 | `README.md`, `LICENSE`, `pyproject.toml`, `.claude-plugin/plugin.json`, `server.json`, `docs/` | `claude plugin validate --strict` → validation passed; the package builds and installs | planned |
| 08 | public repo, PyPI publish, registry publish, marketplace entry | a stranger installs and runs it in one command | planned |

Two checks above need a human and are marked as such when they run: the first
live write (the owner clicks Approve on their own screen) and the final
install test on a clean machine.

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
- D6. The exotic write kinds (IGTV, quicksnap, cutout sticker, collaboration
  invite, crosspost, category conversion, professional type, AI label) stay in
  the mapping but are verified by unit test only — no live call, no live
  account mutation.
- D7. The human approves by clicking, not by typing a code. `ig_write` shows a
  yes/no dialog with the exact action and waits; Yes executes it, No, Cancel or
  a five-minute timeout does not. No approval code exists in the tool result, in
  a file, or in the agent's context, so the agent cannot relay an approval it
  does not have. The harness's own permission prompt is a second, coarser gate.
  On a machine with no interactive desktop, writes are refused rather than
  approved by the agent.
- D8. The local publish queue is ticked by a Windows Scheduled Task every five
  minutes; Instagram's native `schedule_at` is the server-independent path.

**Risks**

- M1. **standing risk** Instagram blocks the account for scripted use. Mitigation: 90-second
  cache, throttled reads, confirm gate on every write, `ig_health`, and the
  option to stop using the tool.

- M2. **planned — phase 06** Realtime is the most fragile surface in the server. Mitigation: flag
  plus polling fallback, ping watchdog, reconnect with backoff, socket probe in
  `ig_health`.

- M3. **done — phases 02, 03** Two servers with similar tool names can confuse the agent. Mitigation:
  every tool description starts with `[AS-IG-MCP]`; the ownership map is in the
  README.

- M4. **done — 16 tools, kinds by parameter** `ig_write` with many `kind` values could drift toward a mega-tool, which
  hurts tool-search matching. Mitigation: split into `ig_write` and
  `ig_manage` if its description passes 4,096 characters.

- M5. **planned — phases 04, 05b** The audit journal and presets hold user content on disk. Mitigation:
  under `%APPDATA%`, never in git, documented in the README's data-handling
  section, with a clear-and-delete command.

- M6. **planned — phases 07, 08** Publishing to the registry without trust signals. Mitigation: the
  Anthropic pre-submission checklist — LICENSE, README over 40 words, pinned
  exact-version launcher, secrets via `userConfig` with `sensitive: true`,
  `claude plugin validate --strict` clean, tests, health tool.

- M7. **done — recorded as a decision** Smithery's MCP Proxy and managed identity shut down 2026-10-31 and its
  CLI and SDKs are deprecated. Do not depend on it; it survives only as a
  directory.

- M8. **standing risk** The private API is the ToS-violating path the commercial vendors warn
  about. That liability is ours, and it is the main reason for the confirm
  gate, the cache, the throttling and the health tool.

- M9. **done — phase 02b** **Found by the EGM Stage 5 review and fixed.** instagrapi mixes readers
  and mutators under similar names. `notification_likes`, `notification_comments`,
  `notification_new_follower` and `notification_user_tagged` are settings
  mutators that default to `"off"`. The first version of the mapping table
  listed them as readers, and a live health probe muted those four notification
  categories on the real account. The account was repaired by setting all four
  back to `"everyone"`. The permanent fix is the `read_only` flag on every
  mapping entry plus the `allow_write` guard in `client.call_feature`, so a read
  path cannot mutate anything. This is the failure mode most likely to bite an
  agent that trusts method names.

- M10. **spec done — code in phase 04** **Found by the EGM Stage 5 review, then sharpened by Stage 8.** A confirm
  code returned in the tool result proves a two-step flow, not human consent,
  because the same agent receives the code — and the owner typing the code into
  chat puts it in the agent's context anyway. There is no code now: the
  account owner approves by clicking Yes in a dialog that shows the exact
  action, and the write happens only if they do. The agent never holds an
  approval.

- M11. **planned — phase 05b** **Found by the EGM Stage 5 review.** A local publish queue with no runner
  only fires while someone has Claude Code open. Fixed by a Windows Scheduled
  Task that ticks the queue every five minutes, with Instagram's native
  scheduler as the server-independent path.

- M12. **planned — phases 04, 05a** **Found by the EGM Stage 5 review.** The cache was never invalidated by a
  write and the digest read through the cache, so the success criteria could
  pass with no live Instagram call at all. Fixed: writes invalidate the affected
  cache entries, and the digest always compares against live state.

- M13. **done — phase 02b** **Found by the EGM Stage 5 review.** `ig_status` promised a quota that
  instagrapi has no endpoint for, which would have meant printing an invented
  number. Fixed: it reports "unknown" instead.

- M14. **planned — phase 05a** **Found by the EGM Stage 5 review.** Moving the repo out of the
  multi-product test repo dropped the one-login rule, which would have left two
  live Instagram sessions on one account — the exact exposure risk M1 names.
  Fixed by injecting our sessionid into the vendor daemon, so both servers share
  one login.

- M15. **planned — phase 05a** **Found by the EGM Stage 8 review.** Loose JSON state meant the last
  writer clobbered the whole cache, which silently disabled the 90-second
  cache — the main defence against an account block. State moved to one
  SQLite file (standard library), so the MCP server, the queue runner and a
  second session can write at once.

- M16. **planned — phase 04** **Found by the EGM Stage 8 review.** The modal approval dialog blocked
  the calling thread, and the documented fallback let the agent fetch the code
  itself. Fixed: the dialog runs on its own thread with a five-minute timeout,
  and the CLI fallback is gone — on a machine with no desktop, writes are
  refused rather than approved by the agent.

- M17. **accepted by the owner** **Accepted, not fixed.** The v1 scope is market parity — every
  capability the whole market covers, plus the white space — and it includes
  public distribution. The reviews flagged this repeatedly as more than one
  user and one account need. The owner chose the superset on purpose, so this
  stands as a decision, with the cost named: a larger surface, a longer
  build, and a private-API client that needs maintenance.

- M18. **spec done — code in phase 06** **Accepted.** Realtime ships on by default (`AS_IG_REALTIME=0` turns it
  off) so the acceptance criteria can actually be met by the documented install
  command, and the polling digest stays as the fallback when the socket is
  down.

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
