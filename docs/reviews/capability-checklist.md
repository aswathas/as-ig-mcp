---
title: AS-IG-MCP — Capability Checklist (definition of done)
type: checklist
status: active
created: 2026-11-10
updated: 2026-11-10
---

# AS-IG-MCP — Capability Checklist

Every capability AS-IG-MCP promises, with the check that proves it. Status is
`todo` until a check has actually printed the expected result. The project is
finished when no row says `todo` and no row says `blocked` without a written
reason in the build log.

Legend: `todo` · `doing` · `green` (check passed) · `red` (check failed) ·
`blocked` (Instagram or account side, reason in build log) · `parked` (user
paused it)

## Reads

| # | Capability | Check | Status |
|---|---|---|---|
| R1 | Profile, own and other | `ig_person username=this_aswath` returns bio and counts | green — verified live 2026-11-10: Aswath AS, 244 followers, 44 following, 67 media, business |
| R2 | Feed, reels, tagged, saved, collections | `ig_feed` for each kind returns a non-empty list | doing — posts, reels, saved, collections verified live; tagged, archive, liked, tray, guides pending |
| R3 | Followers, following, suggestions | `ig_people` for each kind returns a non-empty list | doing — followers and following verified live; suggestions and requests pending |
| R4 | Follow requests, approve and decline | `ig_people kind=requests` lists or states none | todo |
| R5 | DM thread list and message bodies | `ig_thread` on the known thread returns 4 messages | green — verified live: 5 messages, 1 participant, message ids and timestamps |
| R6 | DM search | `ig_search kind=message` finds a known word | doing — the tool exists; not yet verified against a live search |
| R7 | Message requests and spam inbox | `ig_thread kind=requests` and `kind=spam` | doing — pending the write phase, since approving a request is a write |
| R8 | Group threads | `ig_thread kind=group` | doing — instagrapi has no standalone group method; groups are filtered out of the thread list by `thread.is_group` |
| R9 | Presence | `ig_thread` reports presence for a thread | doing — returns null rather than a guess when the call gives nothing |
| R10 | Notifications | `ig_feed kind=notifications` returns likes, comments, followers, tagged | green — verified live, 12 activity items |
| R11 | Mentions, inbox notes, on-post notes | `ig_feed` and `ig_write kind=note` | todo |
| R12 | Hashtags: info, top, recent, following | `ig_search kind=hashtag`; `ig_write kind=follow_hashtag` | doing — search verified live; following is a write, pending the gate |
| R13 | Places, music, top search | `ig_search` for each kind | todo |
| R14 | Stories: own, others, tray, viewers, likers | `ig_feed kind=tray`, `ig_story` | doing — `ig_story` built and returns a clear error without an id; tray and viewers not yet verified live |
| R15 | Highlights: read and write | `ig_story` reads; `ig_write kind=highlight` writes | todo |
| R16 | Comments: read, reply, delete, pin, bulk delete, hold, approve | `ig_feed include=comments`; `ig_write kind=comment` | todo |
| R17 | Insights: media, account, best, compare, demographics | `ig_insight` for each kind | green — all six kinds verified live: media, account, best, best_time, compare, demographics; missing fields come back as null with a note, never a number |
| R18 | Business DM box | `ig_thread box=general` returns threads | doing — the health probe reads it live (3 threads); no tool exposes the box yet |
| R19 | Media download, upload with music, cutout sticker | `ig_feed` and `ig_story` download; `ig_write` publish kinds for upload-with-music and cutout | doing — download is a read, so it belongs to the read tools, not `ig_write` |
| R20 | Profile edit, category, professional type, AI label | `ig_write kind=profile\|category\|ai_label` | todo |
| R21 | Close friends, block, mute, report, remove follower | `ig_write` for each kind | todo |
| R22 | Collaboration invite, crosspost to Facebook and Threads | `ig_write kind=collaborate\|crosspost` | todo |
| R23 | Realtime DM push | `ig_digest wait_s=10` returns an event while the socket is alive | doing — verified live: the socket connects, subscribes (seq_id 1231) and reconnects when Instagram closes it, and the worker runs in its own process so a broken socket cannot take the server down. End-to-end message delivery is proved by the live write test |
| R24 | Delta digest — what changed | `ig_digest` twice: first reports changes, second reports none | green — verified live: first run reports first_run and writes the markers, second reports nothing changed |
| R25 | Best-time to post | `ig_insight kind=best_time` with a chosen window | green — verified live, computed from our own account insights |
| R26 | Local competitor benchmarking | `ig_person` on another account plus `ig_insight kind=compare` | doing — compare works on our own posts; the cross-account part is untested |

## Writes (all behind the confirm gate)

| # | Capability | Check | Status |
|---|---|---|---|
| W1 | Approval gate blocks | `ig_write kind=send_message` and the human clicks No → the tool returns `denied` and sends nothing | doing — verified offline against a fake client (denied, no desktop, approved, replay); the live click is still owed |
| W2 | One approved write lands once | the human clicks Yes → exactly one message appears in the owner's own thread | doing — verified offline (exactly one call); the live click is still owed |
| W3 | Idempotency | replaying the same idempotency key reports "already done" and sends nothing | doing — verified offline; the live click is still owed |
| W4 | Audit journal | `audit.jsonl` holds the denied attempt, the approved attempt and the target | doing — the journal is written and checked offline; the live click is still owed |
| W5 | Publish photo, video, reel, carousel, story | `ig_write kind=publish` for each target | todo |
| W6 | Instagram's own scheduler | `ig_write kind=schedule schedule_at=…` is accepted by Instagram | todo |
| W7 | Local queue and recurrence | `ig_queue` lists, schedules, cancels; recurrence computes | todo |
| W8 | Comment moderation set | `ig_write kind=comment` with hold, approve, ignore, bulk delete | todo |
| W9 | First comment | `ig_write kind=first_comment` | todo |
| W10 | Crosspost and collaboration | `ig_write kind=crosspost`, `kind=collaborate` | todo |

## Platform

| # | Capability | Check | Status |
|---|---|---|---|
| P1 | Health probe | `ig_health` reports every class live | green — 10/10 classes live through our own client |
| P2 | Session status and relogin | `ig_session status`; relogin needs one emailed code | doing — status reports the session source; the login and relogin flows are built but not yet run against Instagram (a live run needs one emailed code) |
| P3 | No relogin after restart | restart the server, read a thread, no code needed | green — the server has been restarted many times during the build and every read worked with no email code |
| P4 | Caching | second identical read within 90 s does not hit Instagram | doing — the cache is in SQLite with a two-connection test; the live no-second-hit check is not measured yet |
| P5 | Version pinning | `pyproject.toml` pins `instagrapi==3.2.8` | green — pinned and all 55 method names verified to exist on 3.2.8 |
| P6 | Presets | `ig_preset` stores and returns a caption and hashtag set | doing — built and unit tested; not yet exercised through the tool |
| P7 | Plugin manifest valid | `claude plugin validate --strict` prints validation passed | green — verified: `✔ Validation passed` |
| P8 | PyPI build | the package builds and installs from the built artifact | doing — the wheel and sdist build and contain the package; installing from the artifact is not tested yet |
| P9 | Registry manifest valid | `server.json` validates against the registry schema | green — checked against the registry schema in the packaging tests |

## Parked by user, 2026-11-10

| Capability | Design |
|---|---|
| DM auto-reply | captured in the capability matrix note |
| Comment auto-reply | captured in the capability matrix note |
| Multi-account | captured in the capability matrix note |

## Out of v1

Team workspaces, roles and approval chains; cross-network publishing; cloud
media pipeline; ads platforms; billing; white-label; live broadcast; video
editing; DM automation rules; the official Graph API as a second backend.
