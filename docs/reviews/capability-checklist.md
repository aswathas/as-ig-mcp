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
| R1 | Profile, own and other | `ig_person username=this_aswath` returns bio and counts | todo |
| R2 | Feed, reels, tagged, saved, collections | `ig_feed` for each kind returns a non-empty list | todo |
| R3 | Followers, following, suggestions | `ig_people` for each kind returns a non-empty list | todo |
| R4 | Follow requests, approve and decline | `ig_people kind=requests` lists or states none | todo |
| R5 | DM thread list and message bodies | `ig_thread` on the known thread returns 4 messages | todo |
| R6 | DM search | `ig_search kind=message` finds a known word | todo |
| R7 | Message requests and spam inbox | `ig_thread kind=requests` and `kind=spam` | todo |
| R8 | Group threads | `ig_thread kind=group` | todo |
| R9 | Presence | `ig_thread` reports presence for a thread | todo |
| R10 | Notifications | `ig_feed kind=notifications` returns likes, comments, followers, tagged | todo |
| R11 | Mentions, inbox notes, on-post notes | `ig_feed` and `ig_write kind=note` | todo |
| R12 | Hashtags: info, top, recent, following | `ig_search kind=hashtag`; `ig_write kind=follow_hashtag` | todo |
| R13 | Places, music, top search | `ig_search` for each kind | todo |
| R14 | Stories: own, others, tray, viewers, likers | `ig_feed kind=tray`, `ig_story` | todo |
| R15 | Highlights: read and write | `ig_story` reads; `ig_write kind=highlight` writes | todo |
| R16 | Comments: read, reply, delete, pin, bulk delete, hold, approve | `ig_feed include=comments`; `ig_write kind=comment` | todo |
| R17 | Insights: media, account, best, compare, demographics | `ig_insight` for each kind | todo |
| R18 | Business DM box | `ig_thread box=general` returns threads | todo |
| R19 | Media download, upload with music, cutout sticker | `ig_write kind=download`; publish kinds | todo |
| R20 | Profile edit, category, professional type, AI label | `ig_write kind=profile\|category\|ai_label` | todo |
| R21 | Close friends, block, mute, report, remove follower | `ig_write` for each kind | todo |
| R22 | Collaboration invite, crosspost to Facebook and Threads | `ig_write kind=collaborate\|crosspost` | todo |
| R23 | Realtime DM push | `ig_digest wait_s=10` returns an event while the socket is alive | todo |
| R24 | Delta digest — what changed | `ig_digest` twice: first reports changes, second reports none | todo |
| R25 | Best-time to post | `ig_insight kind=best` with a chosen window and ordering | todo |
| R26 | Local competitor benchmarking | `ig_person` on another account plus `ig_insight kind=compare` | todo |

## Writes (all behind the confirm gate)

| # | Capability | Check | Status |
|---|---|---|---|
| W1 | Confirm gate blocks | `ig_write kind=send_message` with no code returns `needs_confirm` and sends nothing | todo |
| W2 | One approved write lands once | with the code, exactly one message appears in the owner's own thread | todo |
| W3 | Idempotency | replaying the same idempotency key reports "already done" and sends nothing | todo |
| W4 | Audit journal | `audit.jsonl` holds the rejected attempt, the approved attempt and the target | todo |
| W5 | Publish photo, video, reel, carousel, story | `ig_write kind=publish` for each target | todo |
| W6 | Instagram's own scheduler | `ig_write kind=schedule schedule_at=…` is accepted by Instagram | todo |
| W7 | Local queue and recurrence | `ig_queue` lists, schedules, cancels; recurrence computes | todo |
| W8 | Comment moderation set | `ig_write kind=comment` with hold, approve, ignore, bulk delete | todo |
| W9 | First comment | `ig_write kind=first_comment` | todo |
| W10 | Crosspost and collaboration | `ig_write kind=crosspost`, `kind=collaborate` | todo |

## Platform

| # | Capability | Check | Status |
|---|---|---|---|
| P1 | Health probe | `ig_health` reports every class live | todo |
| P2 | Session status and relogin | `ig_session status`; relogin needs one emailed code | todo |
| P3 | No relogin after restart | restart the server, read a thread, no code needed | todo |
| P4 | Caching | second identical read within 90 s does not hit Instagram | todo |
| P5 | Version pinning | `pyproject.toml` pins `instagrapi==3.2.8` | todo |
| P6 | Presets | `ig_preset` stores and returns a caption and hashtag set | todo |
| P7 | Plugin manifest valid | `claude plugin validate --strict` prints validation passed | todo |
| P8 | PyPI build | the package builds and installs from the built artifact | todo |
| P9 | Registry manifest valid | `server.json` validates against the registry schema | todo |

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
