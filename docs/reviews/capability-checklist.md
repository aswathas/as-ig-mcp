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
| R2 | Feed, reels, tagged, saved, collections | `ig_feed` for each kind returns a non-empty list | todo — held: every kind passed except guides (Instagram removed the endpoint, 404) and tagged (the account has no tagged posts) |
| R3 | Followers, following, suggestions | `ig_people` for each kind returns a non-empty list | green — verified live: followers, following and suggestions; the follow-request list also works (0 waiting) |
| R4 | Follow requests, approve and decline | `ig_people kind=requests` lists or states none | todo — held: no pending follow requests exist to approve or decline; the list read passed (0 waiting) |
| R5 | DM thread list and message bodies | `ig_thread` on the known thread returns 4 messages | green — verified live: 5 messages, 1 participant, message ids and timestamps |
| R6 | DM search | `ig_search kind=message` finds a known word | green — verified live: DM search returned 5 message results |
| R7 | Message requests and spam inbox | `ig_inbox box=requests` and `box=spam` | green — verified live: a real DM request from a second account was approved, and the pending box then read 0 |
| R8 | Group threads | `ig_inbox kind=groups` returns group threads | green — verified live: 2 group threads |
| R9 | Presence | `ig_thread` reports presence for a thread | green — verified live: presence returned an active state for the known thread, and null when the call gives nothing |
| R10 | Notifications | `ig_feed kind=notifications` returns likes, comments, followers, tagged | green — verified live, 12 activity items |
| R11 | Mentions, inbox notes, on-post notes | `ig_feed kind=mentions\|notes` and `ig_write kind=note` | green — verified live: notes and mentions read, and an inbox note created and deleted |
| R12 | Hashtags: info, top, recent, following | `ig_search kind=hashtag`; `ig_write kind=follow_hashtag` | todo — held: Instagram returns 404 for the web hashtag follow endpoint used by instagrapi 3.2.8; hashtag search passed |
| R13 | Places, music, top search | `ig_search` for each kind | green — verified live: places (with lat/lng) 5, music 5, top search 1 |
| R14 | Stories: own, others, tray, viewers, likers | `ig_feed kind=tray`, `ig_story` | green — verified live: published a story, read its info, likers and viewers (empty list handled cleanly), and the tray |
| R15 | Highlights: read and write | `ig_story` reads; `ig_write kind=highlight` writes | green — verified live: read, create from a story, and delete |
| R16 | Comments: read, reply, delete, pin, bulk delete, hold, approve | `ig_feed include=comments`; `ig_write kind=comment` | todo — held: hold/approve have no instagrapi 3.2.8 method; read, reply, pin/unpin and bulk delete passed |
| R17 | Insights: media, account, best, compare, demographics | `ig_insight` for each kind | green — all six kinds verified live: media, account, best, best_time, compare, demographics; missing fields come back as null with a note, never a number |
| R18 | Business DM box | `ig_inbox box=general` returns threads | green — verified live: 3 threads |
| R19 | Media download, upload with music, cutout sticker | `ig_feed kind=download`; `ig_write` publish kinds for upload-with-music and cutout | green — verified live: post download, story publish, cutout sticker, and a story with music (MoviePy 2.2.1 required) |
| R20 | Profile edit, category, professional type, AI label | `ig_write kind=profile\|category\|ai_label` | todo — held: category and professional type change the account type and cannot be safely restored; bio change/restore and AI label passed |
| R21 | Close friends, block, mute, report, remove follower | `ig_write` for each kind | todo — held: report and remove follower were not run (harmful / irreversible); follow, mute, block and close friend passed |
| R22 | Collaboration invite, crosspost to Facebook and Threads | `ig_write kind=collaborate\|crosspost` | todo — held: no confirmed Facebook destination, no linked Threads profile, no co-author account |
| R23 | Realtime DM push | `ig_digest wait_s=10` returns an event while the socket is alive | green — verified live: an incoming DM ("How r u" from deer.9094611) arrived as a `deltaNewMessage` event, seq 1285, ~20s after the socket connected |
| R24 | Delta digest — what changed | `ig_digest` twice: first reports changes, second reports none | green — verified live: first run reports first_run and writes the markers, second reports nothing changed |
| R25 | Best-time to post | `ig_insight kind=best_time` with a chosen window | green — verified live, computed from our own account insights |
| R26 | Local competitor benchmarking | `ig_person` on another account plus `ig_insight kind=compare` | green — verified live: compare on another account ranked 3 posts using public likes when Instagram refused insights |

## Writes (all behind the confirm gate)

| # | Capability | Check | Status |
|---|---|---|---|
| W1 | Approval gate blocks | `ig_write kind=send_message` and the human clicks No → the tool returns `denied` and sends nothing | green — verified live 2026-11-10: clicking No returned `denied` and wrote one denied journal line, with no Instagram call |
| W2 | One approved write lands once | the human clicks Yes → exactly one message appears in the owner's own thread | green — verified live 2026-11-10: one approved send to the account's own user id appeared exactly once in the self thread |
| W3 | Idempotency | replaying the same idempotency key reports "already done" and sends nothing | green — verified live 2026-11-10: replaying the same key returned `already_done`, showed no dialog, and made no second write |
| W4 | Audit journal | `audit.jsonl` holds the denied attempt, the approved attempt and the target | green — verified live 2026-11-10: the journal holds the denied attempt, the approved attempt and the target |
| W5 | Publish photo, video, reel, carousel, story | `ig_write kind=publish` for each target | green — verified live: photo, video (with a thumbnail), reel, album and story all published; each post was deleted after the test |
| W6 | Instagram's own scheduler | `ig_write kind=schedule schedule_at=…` is accepted by Instagram | green — verified live: Instagram accepted a photo scheduled for 2026-12-01; instagrapi exposes no cancel and `media_delete` reports the scheduled item as unavailable, so it must be cancelled in the app |
| W7 | Local queue and recurrence | `ig_queue` lists, schedules, cancels; recurrence computes | green — verified live: list, schedule and cancel through the tool; recurrence is covered by unit tests |
| W8 | Comment moderation set | `ig_write kind=comment` with hold, approve, ignore, bulk delete | todo — held: hold/approve have no instagrapi 3.2.8 method; toggle_comments maps to media_edit (no toggle argument); pin/unpin and bulk delete passed |
| W9 | First comment | `ig_write kind=first_comment` | green — verified live: first comment posted on a new post |
| W10 | Crosspost and collaboration | `ig_write kind=crosspost`, `kind=collaborate` | todo — held: no confirmed Facebook destination, no linked Threads profile, no co-author account |

## Platform

| # | Capability | Check | Status |
|---|---|---|---|
| P1 | Health probe | `ig_health` reports every class live | green — 10/10 classes live through our own client |
| P2 | Session status and relogin | `ig_session status`; relogin needs one emailed code | green — verified live: relogin completed with one Instagram verification code, and health is 10/10 on the new session |
| P3 | No relogin after restart | restart the server, read a thread, no code needed | green — the server has been restarted many times during the build and every read worked with no email code |
| P4 | Caching | second identical read within 90 s does not hit Instagram | green — verified live: the second read succeeded with the network disabled in-process |
| P5 | Version pinning | `pyproject.toml` pins `instagrapi==3.2.8` | green — pinned and all 55 method names verified to exist on 3.2.8 |
| P6 | Presets | `ig_preset` stores and returns a caption and hashtag set | green — verified live: set, get and delete through the tool |
| P7 | Plugin manifest valid | `claude plugin validate --strict` prints validation passed | green — verified: `✔ Validation passed` |
| P8 | PyPI build | the package builds and installs from the built artifact | green — verified: a fresh venv installed the wheel, the `as-ig-mcp` entry point exists, and all 16 tools import |
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
