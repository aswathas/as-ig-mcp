# AS-IG-MCP — Tool Migration Map

This document maps all 35 tools from the incumbent vendor MCP (`everyhand-instagram` / aichargelabs 0.2.7) to their AS-IG-MCP equivalents, explaining where tools moved, merged, or were omitted.

## Vendor tool mapping (all 35 tools)

| # | Vendor Tool | AS-IG-MCP Tool | Notes & Migration Details |
|---|---|---|---|
| 1 | `ig_status` | `ig_status` | Session validity, account name, cache state, realtime worker status, and health in one glance. |
| 2 | `ig_list_threads` | `ig_inbox` / `ig_thread` | Lists direct message threads with message previews, unread indicators, and timestamps. |
| 3 | `ig_get_thread` | `ig_thread(thread_id=...)` | Returns full message bodies, participant lists, and message IDs. |
| 4 | `ig_search` | `ig_search` | Unified search supporting `kind="user"`, `kind="hashtag"`, `kind="place"`, and `kind="music"`. |
| 5 | `ig_user_info` | `ig_person(username=...)` | Returns bio, follower/following counts, media counts, and business/creator verification flags. |
| 6 | `ig_presence` | `ig_thread` / `ig_status` | Thread-level presence indicator. Returns `null` when Instagram does not provide presence rather than inventing status. |
| 7 | `ig_read_messages` | `ig_thread(thread_id=...)` | Reads messages in a conversation. |
| 8 | `ig_search_messages` | `ig_search(kind="message", query=...)` | Searches conversation history for keywords. |
| 9 | `ig_pending_requests` | `ig_inbox(folder="requests")` | Lists incoming DM requests; `folder="spam"` inspects the filtered spam inbox. |
| 10 | `ig_send_message` | `ig_write(kind="send_message", ...)` | Sends a direct message. Gated by an interactive desktop confirmation dialog on the owner's screen. |
| 11 | `ig_send_media` | `ig_write(kind="send_media", ...)` | Sends photo/video via DM behind the confirmation gate. |
| 12 | `ig_share` | `ig_write(kind="share", ...)` | Shares a post or profile to a direct message thread behind the confirmation gate. |
| 13 | `ig_react` | `ig_write(kind="react", ...)` | Sends an emoji reaction to a message behind the confirmation gate. |
| 14 | `ig_unsend` | `ig_write(kind="unsend", ...)` | Unsends/deletes an outbound message behind the confirmation gate. |
| 15 | `ig_mark_seen` | `ig_write(kind="mark_seen", ...)` | Marks messages or a thread as seen. |
| 16 | `ig_thread` | `ig_thread` | Conversation details, participants, mute status, and thread administration. |
| 17 | `ig_download_media` | `ig_feed` / `ig_story` | **No separate tool.** Downloading media is a read operation: media URLs are included directly in feed and story responses. |
| 18 | `ig_triage` | *(Native LLM)* | **No tool needed.** The vendor provided a local heuristic triage prompt. LLM agents using AS-IG-MCP perform superior triage natively using `ig_thread` and `ig_digest`. |
| 19 | `ig_draft_reply` | *(Native LLM)* | **No tool needed.** Vendor-side reply drafting helper; in MCP, drafting replies is the connected AI model's native capability. |
| 20 | `ig_compose` | *(Native LLM)* | **No tool needed.** Vendor-side formatting helper; LLM models compose messages directly before calling `ig_write`. |
| 21 | `ig_get_profile` | `ig_account` / `ig_person` | `ig_account` views the logged-in user's account details; `ig_person` views public profiles. |
| 22 | `ig_set_profile` | `ig_write(kind="profile", ...)` | Updates profile bio, links, and category behind the confirmation gate. |
| 23 | `ig_list_profiles` | *(Omitted)* | **No equivalent.** Vendor managed multiple profile files. AS-IG-MCP v1 strictly isolates a single user session encrypted with Windows DPAPI (multi-account is parked). |
| 24 | `ig_daemon` | *(Automatic)* | **No command needed.** Vendor required manual start/stop/status of an external daemon. AS-IG-MCP runs via standard stdio, supervising its realtime MQTT socket worker transparently. |
| 25 | `ig_account` | `ig_account` | Inspects own account settings, professional account tier, and linked accounts. |
| 26 | `ig_user_media` | `ig_feed(username=...)` | Reads user posts, reels, and feeds. |
| 27 | `ig_media` | `ig_feed` | Reads media items, saved collections (`kind="saved"`), tagged media (`kind="tagged"`), and reels (`kind="reels"`). |
| 28 | `ig_comments` | `ig_feed` / `ig_write(kind="comment")` | Reading comments is supported via `ig_feed(include="comments")`; comment mutations (post, reply, pin, delete, bulk delete) run through `ig_write`. |
| 29 | `ig_publish` | `ig_write(kind="publish", ...)` | Publishes photos, videos, reels, carousels, or stories behind the confirmation gate. Also supports Instagram's native scheduler via `schedule_at`. |
| 30 | `ig_relationship` | `ig_people` / `ig_write` | Reads follower relationships via `ig_people`; mutations (`follow`, `unfollow`, `block`, `mute`, `close_friend`) run through `ig_write`. |
| 31 | `ig_followers` | `ig_people(kind="followers")` | Lists followers (and `kind="following"` for following). |
| 32 | `ig_stories` | `ig_story` / `ig_feed(kind="tray")` | Inspects own stories, user stories, viewers, and the stories tray. |
| 33 | `ig_highlights` | `ig_story(kind="highlights")` / `ig_write` | Reads highlights via `ig_story`; creates/edits highlights via `ig_write(kind="highlight")`. |
| 34 | `ig_notes` | `ig_feed(kind="notes")` / `ig_write(kind="note")` | Reads inbox and on-post notes; publishes notes via `ig_write`. |
| 35 | `ig_discover` | `ig_search` / `ig_people(kind="suggestions")` | User suggestions, explore feeds, and hashtag/place discovery. |

---

## Capabilities unique to AS-IG-MCP

No other Instagram MCP server or commercial connector in the market exposes these capabilities through MCP:

1. **Delta digest (`ig_digest`)**
   Tells an AI agent exactly what changed since the last invocation (new DMs, new comments, follower changes). Agents do not need to poll and re-download entire thread lists or feeds.

2. **Realtime push without server crashes**
   A dedicated worker process manages an MQTT socket connection to Instagram's realtime message broker. Incoming DMs and typing events are appended to a local event log. Because the socket runs in an isolated worker, private socket disconnections or SSL drops never crash the MCP server.

3. **Multi-mode insights tool (`ig_insight`)**
   Provides 6 analysis modes:
   - `kind="media"`: Per-post impressions, reach, engagement, and profile visits.
   - `kind="account"`: Account-level reach, impressions, follower delta over 7/30 days.
   - `kind="best"`: Ranked top posts over selectable time windows (1 week to 2 years).
   - `kind="best_time"`: Statistically computed optimal posting times from account audience data.
   - `kind="demographics"`: Follower age, gender, and geographic breakdowns.
   - `kind="compare"`: Metric comparisons between posts.
   Missing metrics return `null` with explicit notes rather than fabricated zeros.

4. **Physical confirmation gate (`ig_write`)**
   Every mutating action displays an interactive confirmation dialog directly on the user's desktop display showing the exact proposed action. There are no 6-digit confirmation codes for an AI model to guess, hallucinate, or relay. If unapproved or ignored for 5 minutes, the action is rejected.

5. **JSONL audit journal (`audit.jsonl`)**
   Every mutation attempt — whether approved, denied, or timed out — is permanently appended to a local JSONL audit file with timestamps, target parameters, and human response.

6. **Local caption and hashtag presets (`ig_preset`)**
   Stores reusable caption templates, hashtag sets, and first-comment presets locally in `%APPDATA%\as-ig-mcp\presets.json` without requiring cloud databases or external SaaS subscriptions.

7. **Local queue & recurrence (`ig_queue`)**
   Enables scheduling posts with local recurrence rules and crash-safe state updates, independent of external scheduling platforms.
