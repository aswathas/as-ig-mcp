# AS-IG-MCP — Spec

Status: Draft for user review
Date: 2026-11-10

**Name:** AS-IG-MCP
**MCP server id (Claude Code):** `as-ig`
**Package:** `as-ig-mcp` (PyPI-ready), Python module `as_ig_mcp`
**Tools:** 13, all prefixed `ig_`, every description tagged `[AS-IG-MCP]`
**One line:** the Instagram MCP that reads your DMs, measures your posts, and
tells you what changed since last time.

## 1. Problem & user

Aswath drives Instagram from Claude Code through the vendor MCP
`everyhand-instagram` (aichargelabs-instagram-mcp 0.2.7 — a frozen PyInstaller
exe bundling instagrapi 3.2.3). 13 of its read tools fail on every call:

```
RuntimeError: unauthorized use of script (1:5174)
```

Dead: `ig_list_threads`, `ig_read_messages`, `ig_user_media`, `ig_followers`,
`ig_stories tray`, `ig_discover hashtag_top/hashtag_recent/users/music`,
`ig_draft_reply`, `ig_compose`; plus `ig_discover location_search` (Instagram
deleted `www.instagram.com/web/search/topsearch/`, the vendor still calls it)
and `ig_discover places` (needs `IG_PLACES_LAT` / `IG_PLACES_LNG`).

19 read calls still work: `ig_user_info`, `ig_get_thread`, `ig_triage`,
`ig_search`, `ig_presence`, `ig_pending_requests`, `ig_stories list/archive/highlights`,
`ig_notes`, `ig_relationship`, `ig_discover hashtag/explore/hashtags_followed`,
`ig_account`, `ig_status`, and the local reply-style tools.

The job to be done: read and write Instagram (DMs, feed, followers, stories,
search, publish, comments) from Claude Code, on one machine, for one account,
without a vendor build that cannot be patched — and with fewer round trips and
less context burned than the vendor's tool list costs today.

**Root cause (measured).** Instagram's modern web endpoints need a `fb_dtsg`
token that instagrapi scrapes from `www.instagram.com`. instagrapi 3.2.3
scrapes the wrong URL (`www.instagram.com/graphql/query/...`, which returns
JSON with no `__eqmc` block) → `fb_dtsg = None` → Instagram rejects the Relay
requests. instagrapi 3.2.8 scrapes the homepage HTML and gets a real token.

Same account, same session cookies, measured 2026-11-10:

| probe | instagrapi 3.2.3 (vendor) | instagrapi 3.2.8 |
|---|---|---|
| `fb_dtsg` | `None` | `NAfy5kMv8GRdAA2JMQAPCkhvTdjL…` |
| `user_followers` | error | 242 followers |
| `user_medias` | error | 5 media |
| `direct_threads` | error | 10 threads |
| `explore_page` | error | 16 items |
| `user_stories_web` | n/a | ok |

The vendor exe cannot be patched (modules live inside the exe PYZ; `iglib` is
pyarmor-obfuscated). No session change fixes it — mobile session, web session,
fresh session all hit the same broken fetch.

## 2. Scope — in / out

**In**

- A new MCP server `as-ig` that owns the whole Instagram surface:
  every read the vendor has (the 13 dead ones plus the ones that still work)
  and every write (DM send, media send, share, react, unsend, mark seen,
  publish, comments, follow/unfollow/block, stories, highlights, notes,
  account edit, reply-style profile).
- An intent-level tool surface — 13 tools, not 35 — so the agent spends less
  context on tool descriptions, and one call can cover what used to be three.
- instagrapi pinned to 3.2.8 in our own venv. An Instagram-side change is
  answered with one `pip install -U instagrapi`, not a vendor wait.
- One shared Instagram login: our session is injected into the vendor daemon
  (`instagram-mcp.exe login --sessionid-env`), so the account has a single
  live login instead of two.
- Session owned by us, DPAPI-encrypted, reused across restarts.
- `ig_health`: one call reports live/dead per endpoint class, so the next
  breakage is a 5-second check.
- A short cache with an explicit bypass, and a digest that reports what
  changed since the last call.
- Writes keep the vendor's safety convention: a 6-digit confirm code, a
  preview, and no mutation until the code comes back.
- Instagram insights: per-post metrics (reach, impressions, likes, comments,
  saves, shares, profile views, hashtag impressions, where impressions came
  from) and account-level metrics (profile visits, follower growth and
  breakdown, top posts, story count). The vendor exposes no insights tool at
  all, so this is new capability and it feeds straight into "read the numbers,
  then post better".
- A publishable package, not just a working script: LICENSE, README, PyPI-ready
  `pyproject.toml`, a Claude plugin marketplace entry, an official MCP
  registry `server.json`, and `claude plugin validate --strict` passing.
- A one-page vendor bug report (instagrapi 3.2.3 `fetch_fb_dtsg` scrapes the
  wrong URL) so aichargelabs can fix their build.

**Out**

- Not a hosted or multi-account product. One account, one machine, one user.
- Not video editing. Posting video is in scope; cutting, caption burning and
  rendering stay with ffmpeg and the video-shotcraft skill — a separate
  product.
- Not the official Instagram Graph API. It cannot read DMs, which is the whole
  point, and it needs a Meta app plus business linking.
- Not a browser-scraping read path. DOM scraping is brittle and needs a
  permanently logged-in browser.
- Not a migration of the vendor's stored reply-style profiles or DM history.
  We re-create what we need; the vendor's store stays as it is.
- Nothing is published, sent, liked or followed on the live account during the
  build. Write tools are verified against the account owner's own DM thread,
  with the owner's approval.

## 3. Success criteria (measurable)

1. `ig_health` reports every endpoint class live, and each of the 13 formerly
   dead reads returns data instead of `unauthorized use of script`. Verified by
   the health output plus one live call per class.
2. Read counts are **> 0 and stable across two consecutive calls** (not pinned
   to a number — Instagram counts move).
3. `ig_thread` last message for a known thread equals `ig_inbox` last message
   for the same thread; `ig_person` profile equals `ig_status` account info.
4. A server restart completes a read with **no email code and no re-login**.
5. Every write without a confirm code returns `needs_confirm` + preview + a
   6-digit code and performs **no** Instagram mutation — verified by reading
   the thread afterwards and finding nothing new.
6. `as-ig-mcp` appears in `claude mcp list` and its tools answer from a
   clean Claude Code session.
7. `ig_digest` twice in a row: the first call reports changes, the second
   reports none, without re-fetching unchanged feeds.
8. `ig_write` with `kind=send_message` and the correct confirm code sends
   exactly one message.
9. The vendor daemon and our server use the same `sessionid` (one Instagram
   login on the account).
10. `ig_search kind=place` either returns results or reports "unsupported" —
    it never raises a raw client error.
11. `ig_insight kind=media` on a known post returns metrics that match the
    values Instagram reports: reach 381, impressions 390, likes 22 on post
    `4024692804391239207` (measured 2026-11-10; if the post ages, the values
    can only grow, so the check is ">=" plus the field set being complete).
12. `ig_insight kind=account` returns `has_insights: true`,
    `account_type: BUSINESS_ACCOUNT`, profile visits, follower growth and top
    posts for this account.

## 4. Constraints & environment

- Windows 11, bash shell, Claude Code on this machine.
- Python 3.14. Our server gets its **own** venv at
  `C:\Users\aswat\Projects\as-ig-mcp\.venv` (deps: `instagrapi==3.2.8`,
  `mcp`, `pycryptodomex`). The shared `whatsapp-mcp-venv` keeps a stray
  `instagrapi 3.2.8` from this investigation — harmless, because the vendor exe
  runs its own bundled copy.
- instagrapi 3.2.8 pinned; its stored session keeps the app profile that
  Instagram accepted at login (`override_app_version=False` is load-bearing:
  the app profile is part of the device trust).
- Transport: stdio MCP server, same tool-naming convention as the vendor
  (`ig_*`), namespaced by server in Claude Code.
- State lives in files, not in one process: session (DPAPI-encrypted), cache,
  digest markers. So several Claude Code sessions share them safely.
- Instagram limits: rate limits, occasional checkpoint challenges. Reads are
  throttled by instagrapi's delay range and cut further by the cache.
- Repo for the implementation: `C:\Users\aswat\Downloads\Projects\everyhand-tests`
  (git repo `aswathas/everyhand-tests`, private). New top-level component
  `mcp/as-ig-mcp/`.
- Secrets: the session cookie is a live credential — DPAPI-encrypted to the
  current Windows user, never in git, never in the transcript.

## 5. Approach — chosen, with rejected alternatives and why

**Chosen: our own MCP server on instagrapi 3.2.8, with an intent-level tool
surface, one shared login, file-backed state.**

It is the only option that fixes the dead tools, fixes `location_search`, lets
us bump the Instagram client in seconds, and gives a tool surface that costs
less context and fewer round trips than the vendor's flat 35 tools.

**Rejected: vendor re-login as the fix (route A).** Feeding the daemon a web
`sessionid` cannot help: the vendor's instagrapi 3.2.3 computes `fb_dtsg = None`
whatever session it holds. The defect is inside the frozen exe, not in the
session. (We still inject our session into the vendor, for the single-login
reason in §2 — not to fix its endpoints.)

**Rejected: thin shim for the 13 dead tools only.** Two servers each owning part
of the account, with the user having to remember which. We are rebuilding the
writes and reads anyway; splitting ownership across two servers saves nothing
real and confuses the agent.

**Rejected: browser or CDP as the read path.** Instagram's own web UI is
fragile to scrape, needs a logged-in browser running permanently, and gives
worse data than the API. Kept only as a credential fallback when a checkpoint
forces a browser login.

**Rejected: official Graph API.** Durable against private-API drift, but no DM
read plus Meta app and business-linking setup.

**Rejected: wait for a vendor release.** Free, but they must notice a bug in a
dependency, rebuild a frozen exe and ship it. We file the report; we do not
wait.

**Rejected: a separate long-running daemon for v1.** A daemon would own the
session, the confirm store and the rate-limit budget across Claude Code
sessions. With session, cache and digest state kept in files, the stdio server
gets the same behaviour with less machinery. Revisit if two concurrent sessions
start colliding on Instagram's rate limits.

## 6. Architecture, components & data flow

```
mcp/as-ig-mcp/
  pyproject.toml              # instagrapi==3.2.8, mcp, pycryptodomex (pinned)
  README.md                   # run, relogin, health check, what each tool does
  src/as_ig_mcp/
    __init__.py
    server.py                 # stdio MCP server: 13 tools, thin
    client.py                 # instagrapi wrapper: fb_dtsg prefetch, canonical method per feature
    session.py                # DPAPI load/save, relogin
    cache.py                  # TTL cache on disk, fresh= bypass
    digest.py                 # last-seen markers, change detection
    writes.py                 # write kinds + confirm gate + idempotency
    health.py                 # endpoint-class probe
    state.py                  # paths under %APPDATA%\as-ig-mcp
  tests/                      # offline tests (no Instagram calls)
```

**Data flow**

1. Claude Code starts `as-ig-mcp` (stdio) → `server.py` reads the session
   from `%APPDATA%\as-ig-mcp\session.enc` (DPAPI-decrypted) and builds the
   instagrapi client with the pinned app profile.
2. `client.py` prefetches `fb_dtsg` via instagrapi 3.2.8's homepage scrape and
   caches it in-process; on a GraphQL/JSON error it refetches once, then falls
   back to the api/v1 REST variant of that feature.
3. A tool call resolves to **one canonical instagrapi method per feature**
   (fixed in a mapping table, so behaviour does not depend on fallback luck),
   converts the result to plain JSON, and returns it as MCP content.
4. Reads go through `cache.py` (default TTL 90 s; `fresh=true` bypasses).
5. `ig_digest` compares current state against `digest.json` markers and writes
   the new markers.
6. Writes go through `writes.py`: first call stores the pending action, returns
   `needs_confirm` + a preview + a 6-digit code, and performs nothing. The
   second call with the matching code executes it once; an idempotency key
   prevents a repeat from double-posting.

**State**

- Session: `%APPDATA%\as-ig-mcp\session.enc` (DPAPI, current Windows
  user). Written only by an explicit login/relogin.
- Cache: `%APPDATA%\as-ig-mcp\cache.json` (TTL entries, atomic write).
- Digest markers: `%APPDATA%\as-ig-mcp\digest.json`.
- Pending write confirmations: in-memory only (lost on restart = safe).
- Nothing secret in the repo or the transcript.

**Tool surface — 13 intent-level tools**

| tool | replaces (vendor tools) | notes |
|---|---|---|
| `ig_status` | `ig_status`, `ig_account` (read) | session, account, quota, cache state, one-line health |
| `ig_inbox` | `ig_triage`, `ig_draft_reply`, `ig_compose` | threads awaiting a reply, last message, optional suggested reply from our style profile |
| `ig_thread` | `ig_get_thread`, `ig_read_messages`, `ig_mark_seen`, `ig_react`, `ig_unsend` | full thread + paginated messages; `cursor` for more |
| `ig_person` | `ig_user_info`, `ig_relationship` (read), `ig_followers`, `ig_stories` (list/highlights), `ig_media`, `ig_comments` (read) | one profile call with `include=` for followers/following/posts/stories/highlights/comments |
| `ig_people` | `ig_followers` (following, suggested) | paginated lists for any account |
| `ig_search` | `ig_discover` (all kinds), `ig_search`, `ig_search_messages` | `kind=user\|hashtag\|place\|music\|post\|message`; returns ids and links so follow-up calls are cheap |
| `ig_feed` | `ig_user_media` (posts/reels/tagged/saved/archive), `ig_stories tray` | paginated feed for any account or our own; `include=comments` |
| `ig_story` | `ig_stories` (info/viewers/likers/download), `ig_highlights` (read) | story + highlight detail |
| `ig_digest` | — (new) | what changed since the last call: new DMs, new followers, new posts, story updates |
| `ig_insight` | — (new) | `kind=media` (one post's metrics), `kind=account` (profile visits, follower growth, top posts), `kind=compare` (rank the last N posts by a chosen metric) |
| `ig_write` | `ig_send_message`, `ig_send_media`, `ig_share`, `ig_publish`, `ig_comments` (post/delete/like/pin), `ig_relationship` (writes), `ig_notes`, `ig_highlights`, `ig_account` (edit), `ig_set_profile` | `kind=` selects the action; confirm gate + preview + idempotency |
| `ig_health` | — (new) | live/dead per endpoint class |
| `ig_session` | — (new) | status, relogin (email code), cache clear, export session |

Why this beats the vendor's 35: the agent loads 13 tool schemas instead of 35
(~1300 tokens of context per session); one call often does what three vendor
calls did (`ig_inbox` = triage + draft + thread lookup; `ig_person` = profile +
followers + posts; `ig_write` = all nine write tools behind one gate); every
search kind is one tool with a `kind` parameter instead of seven `ig_discover`
variants; `ig_digest` removes the "what is new" polling loop; and `ig_insight`
adds performance data the vendor cannot read at all.

Cost of this shape, stated plainly: our names stop matching the vendor's, so
habits break (fix: `docs/as-ig-mcp/tool-map.md` maps every old name to
the new one); one tool can return a big payload (fix: `include=` and `limit`
parameters); and the agent has fewer names to choose from (fix: every tool
description leads with one line saying what it is for).

**Both servers stay registered.** The vendor keeps its 19 working reads and its
local reply-style tools; our server covers everything. Every one of our tool
descriptions starts with `[AS-IG-MCP]` so the agent never mixes the two
sets. Nothing is unregistered.

**Feature layers, bottom-up** — the order the code is written, and the order
the pieces depend on each other:

| layer | feature | why it sits here |
|---|---|---|
| 0 | session (DPAPI store, relogin in one command) | nothing works without a login |
| 1 | read one thing | proves session → token → Instagram → answer |
| 2 | `ig_inbox` | the daily need: who wrote, what they wrote, suggested reply |
| 3 | `ig_health` | catches upstream breakage in one call instead of in days |
| 4 | remaining reads (`ig_status`, `ig_thread`, `ig_person`, `ig_people`, `ig_search`, `ig_feed`, `ig_story`) plus `ig_insight` | broadens coverage once the chain is proven |
| 5 | writes + confirm gate (`ig_write`) | highest risk, so it comes after the reads are proven |
| 6 | digest + cache (`ig_digest`) | fewer Instagram calls, "what changed" in one call |
| 7 | share the session with the vendor | one Instagram login on the account |

Each layer is checkable alone: layer 1 returns one profile, layer 2 returns the
inbox, layer 3 returns a health table.

**Canonical instagrapi method per feature** (3.2.8, one method each — the
mapping table is the single place to change when Instagram moves):

| feature | method |
|---|---|
| profile | `user_info_v1` |
| followers / following | `user_followers_v1`, `user_following_v1` |
| posts / reels / tagged | `user_medias_v1` (fallback `user_medias_gql`) |
| stories of a user | `user_stories_web` |
| story tray | following list → `user_stories_web` per user |
| thread list | `direct_threads` |
| thread messages | `direct_messages` |
| DM search | `direct_message_search` |
| user search | `search_users` (fallback `fbsearch_accounts_v2`) |
| hashtag top / recent | `hashtag_medias_top`, `hashtag_medias_recent` |
| places | `fbsearch_places` (needs lat/lng) |
| top search | `fbsearch_topsearch_v2` |
| music | `search_music` |
| explore | `explore_page` |
| send DM | `direct_send` / `direct_send_photo` |
| publish | `photo_upload` / `video_upload` / `clip_upload` |
| insights for one post | `insights_media` |
| insights for the account | `insights_account` |

## 7. Failure modes & error handling

| failure | detection | user sees | system does next |
|---|---|---|---|
| IG session expired or revoked | first call raises `LoginRequired`/`Unauthorized`, or `fb_dtsg` fetch returns None | "session expired" plus the relogin command | stops using the cached session, does not retry blindly |
| IG kills the session remotely / device fingerprint mismatch | `ChallengeRequired` on any call | "checkpoint needed" and what to do | surfaces the challenge; asks for a code once; browser-cookie fallback documented |
| An endpoint breaks upstream again | `ig_health` shows that class dead | health report naming the class | bump instagrapi; no code change |
| `fb_dtsg` stale mid-process | `ClientGraphqlError` / `ClientJSONDecodeError` | normal result (recovered) | refetch once, then use the REST variant |
| Rate limited | HTTP 429 | status and retry-after | backoff, then report |
| Write called without / with wrong confirm code | confirm check | `needs_confirm` + preview + code, no mutation | nothing sent; wrong code is refused |
| Same write submitted twice | idempotency key | second call reports "already done" | no second message, no second post |
| DPAPI decrypt fails (different Windows user) | decrypt error at startup | "session belongs to another Windows user" | starts with no session, asks for relogin |
| Malformed session file | load error | error plus relogin command | refuses to start rather than half-working |
| Two Claude Code sessions write state at once | file lock/atomic rename | none (silent) | last writer wins for cache; digest markers merge by timestamp |
| Insights requested on a personal (non-business) account | instagrapi raises, or the payload has no `inline_insights_node` | "no insights on this account type" | returns a clear message, not a raw client error |

No write is retried automatically after a partial failure. The operator decides.

## 8. Test plan

1. **Offline unit tests** (`tests/`): DPAPI round-trip; the canonical-method
   mapping table covers every feature in §6 exactly once; cache TTL and
   `fresh=true`; digest marker update; confirm-code validation (wrong code,
   expired code, single use); idempotency key replay.
2. **Live health test** (`ig_health`): every class live; counts > 0 and stable
   across two calls.
3. **Cross-check**: `ig_thread` last message == `ig_inbox` last message;
   `ig_person` profile == `ig_status` account info.
4. **Persistence test**: stop the server, start it again, read a thread — no
   email code.
5. **Write-gate test**: `ig_write kind=send_message` without confirm →
   `needs_confirm`; read the thread → no new message; with the code → exactly
   one message.
6. **Digest test**: `ig_digest` twice → second call reports no changes.
7. **Single-login check**: compare the `sessionid` in our DPAPI session with
   the one the vendor daemon loads.
8. **Negative test**: corrupt the session file → server reports it and does not
   crash.
9. **Insights test**: `ig_insight kind=media` on post `4024692804391239207`
   returns reach, impressions, likes, comments, shares, profile views and
   hashtag data; `ig_insight kind=account` returns the account units; and
   `ig_insight kind=compare` ranks the last 5 posts by reach.

Passing = all 13 dead reads return data, health all green, write gate holds,
digest is quiet on the second call, restart needs no code.

## 9. Implementation ownership — agent implements + build order

Agent implements. Each step ends with a runnable check.

1. **Vendor bug report** (one page: wrong URL, repro, fix). Free, and if
   aichargelabs ships 3.2.8 the whole project can shrink to a config change.
2. Package skeleton, dedicated venv, `session.py` (DPAPI) + `client.py`
   (fb_dtsg prefetch, canonical methods). Check: offline tests pass.
3. Read tools (`ig_status`, `ig_inbox`, `ig_thread`, `ig_person`, `ig_people`,
   `ig_search`, `ig_feed`, `ig_story`, `ig_insight`) + `ig_health`. Check: the
   13 dead reads return data; health green; insights return metrics for a
   known post.
4. Register the server in Claude Code. Check: `claude mcp list` shows it; a
   clean session calls a tool.
5. `ig_write` with confirm gate + idempotency, then `ig_session` (relogin).
   Check: write-gate test passes; relogin works.
6. `cache.py`, `digest.py`, `ig_digest`. Check: digest test passes.
7. Inject our session into the vendor daemon (one command) so the account has
   one login. Check: single-login test passes.
8. README (run, relogin, health check, tool list) + repo commit.
9. Publish: PyPI package `as-ig-mcp`, official registry `server.json`, Claude
   plugin marketplace entry, then `claude plugin validate --strict` clean.
   Check: `uvx as-ig-mcp` starts on a clean machine, and
   `claude plugin install as-ig-mcp@as-ig-mcp` works.

The market study, the capability inventory and the adoption checklist behind
this spec live in the Obsidian note
`Aswaths Obsidian Den/Aswaths Mountain Den/Project Ideas/AS-IG-MCP - Deep Study and Build Blueprint.md`
(Markdown and PDF).

## 10. Risks, assumptions, and what would invalidate this spec

**Assumptions**

- A1. Instagram keeps serving instagrapi 3.2.8's endpoint set. If it changes
  again, the fix is a version bump — the client layer with its mapping table
  exists precisely to absorb that.
- A2. The session stays valid for weeks. The session obtained 2026-11-10
  worked for every probe right after login. Recovery when it ends: one emailed
  code through `ig_session relogin`, or a browser login if a checkpoint blocks
  the scripted path.
- A3. `fb_dtsg` scraping from `www.instagram.com` keeps working while the
  graphql-URL scrape does not. Observed 2026-11-10.
- A4. DPAPI through `ctypes` is enough to protect the session cookie; no
  third-party crypto dependency needed.
- A5. The 12-tool surface is better than the vendor's 35 for our own use.
  Reasoning, not measured: fewer schemas to load, fewer round trips, one
  search tool instead of seven. If tool-name muscle memory turns out to
  matter more, the mapping table in §6 makes splitting a tool back out cheap.
- A6. Realistic maintenance: a handful of touchpoints a month — mostly
  re-login with one code, occasionally a browser challenge. Reasoning, not
  measured over time. Keep the recovery path to one command.
- A7. Insights stay available on the private API for this account. Measured
  2026-11-10: `has_insights: true`, `account_type: BUSINESS_ACCOUNT`, per-post
  and per-account units returned. If Instagram moves insights to Graph-only,
  `ig_insight` is the one tool that needs a fallback.
- A8. Insights metrics are partial and lag. The account units are weekly
  snapshots; per-post counts keep growing after publication. Any comparison
  must therefore compare posts of similar age, not "best post ever" against
  "post from yesterday".

**Questions asked, and the answers given (2026-11-10)**

- Q1. Which route? → A first (vendor re-login), B (own MCP) if A fails. A was
  then proven impossible by the `fb_dtsg` defect; this spec is route B.
- Q2. Where does the session come from? → our own instagrapi login with one
  emailed code. Done 2026-11-10; session saved.
- Q3. Scope? → reads **and** writes.
- Q4. Where does the implementation live? → the existing `everyhand-tests`
  repo.
- Q5. Which coordinates for `ig_discover places`? → **not answered.** The
  server reads `IG_PLACES_LAT` / `IG_PLACES_LNG` from the environment and
  reports "coordinates not configured" until they are set. Does not block
  anything else.
- Q6. Which write tools? → **all of them in our server.**
- Q7. One login or two on the account? → **one — inject our session into the
  vendor daemon.**
- Q8. Fix the vendor, or build something better? → **better** — intent-level
  tools, one search tool, digest, cache.
- Q9. Which tool shape? → **12 intent tools**, one per job, after a walkthrough
  of the same task done three ways (inbox: 3 vendor calls vs 1 call; profile +
  followers + posts: 3 vs 1; DM send + publish + comment: 3 tools vs 1 gated
  tool).
- Q10. What happens to the vendor MCP once ours works? → **keep both
  registered.** Our tools carry an `[AS-IG-MCP]` tag in their
  descriptions so the agent never mixes the sets.
- Q11. Which half first? → **read side first**: session, one read,
  `ig_inbox`, `ig_health`, then register, then writes, then digest and cache.
- Q12. Add Instagram insights? → **yes**, because the account is a business
  account and the private API already returns the metrics (measured
  2026-11-10). The agent reads the numbers and posts better.
- Q13. Video editing? → **no, separate product.** Posting video stays in
  scope; making it stays with ffmpeg and the video-shotcraft skill.

**Risks**

- M1. Instagram could block scripted access after repeated probing. Mitigation:
  `ig_health` is manual, reads are throttled and cached.
- M2. Two servers with similar tool names can confuse the agent about which to
  call. Mitigation: our server is registered as the primary; the vendor stays
  as a documented fallback with the same session.
- M3. instagrapi 3.2.8's public/anonymous `user_followers_gql` failed in
  testing (`ClientJSONDecodeError` — Instagram served HTML). The authenticated
  path works, so this only constrains anonymous lookups.
- M4. The story tray has no single instagrapi call in 3.2.8 (no `reels_tray`);
  it is built from the following list plus per-user story fetches, so it costs
  more calls than the other reads.
- M5. `fbsearch_topsearch_v2` exists but was never observed returning results.
  Criterion 10 accepts "does not error, or reports unsupported" instead of
  promising results.
- M6. Rebuilding all writes means owning the confirm-gate semantics for
  publish, comments, follows, highlights, notes and account edits. Mitigation:
  one shared gate with a preview; no write without the code.
- M7. Publishing with an unpinned launcher (`uvx --from git+…`) fails Anthropic's
  pre-submission checklist. Our own `olx-car-search` plugin would fail it too.
  Mitigation: publish to PyPI and pin exact versions in the plugin manifest.
- M8. Smithery's MCP Proxy and managed identity shut down on 2026-10-31 and its
  CLI and SDKs are deprecated. Do not depend on it; it survives only as a
  directory.
- M9. `ig_write` with a `kind` parameter is the one place that could drift
  toward a mega-tool, which measurably hurts tool-search matching. Mitigation:
  split into `ig_write` and `ig_manage` if its description or payload grows
  past the 4,096-character upfront limit.

**What would invalidate this spec**

- Instagram stops serving the `fb_dtsg` scrape too (the homepage no longer
  contains `__eqmc`) — the script-endpoint approach dies and the Graph API
  becomes the only remaining option for public reads.
- The account is a personal (non-business) account in a region where the
  private API is fully blocked — then no client-side fix exists.
- The user decides DM reading does not matter: the server shrinks to public
  reads plus a Graph API fallback.

## Exit condition

The spec is complete only when all ten sections above are filled with concrete
content, no section contains `TBD`/`TODO`/an empty placeholder, and the user
has said "approved" in response to seeing this file. An agent may not declare
the spec complete on its own judgement. If a section cannot be filled, write
the assumption explicitly in section 10 and ask the user about it.
