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
