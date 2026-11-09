# EGM Stage 6 — Comprehension Report

Target: `docs/superpowers/specs/2026-11-10-as-ig-mcp-v1-design.md`
Ranges: FeatureRange 1..414, DetailedRange 415..562
GoldfishContext: empty
Reviewer: `egm-comprehension` (read-only adapter — the parent persisted this report)

## What this proposes

AS-IG-MCP: a local Python MCP server (stdio, server id `as-ig`, package
`as-ig-mcp`) exposing 16 intent-level `ig_*` tools on top of instagrapi 3.2.8,
talking to Instagram's undocumented private API, so one Claude Code session on
one Windows machine can read DMs, feeds, stories, comments and insights, and can
publish, message, comment and manage the account. Every write sits behind a
6-digit confirm code shown to the account owner in a Windows popup and never
returned to the agent, with an idempotency key and an append-only audit
journal. On top of the market read/write surface it adds a "what changed"
digest, live DM push over Instagram's realtime socket, a best-time tool, presets
and local competitor benchmarking, distributed as a PyPI package, an official MCP
registry entry and a Claude plugin marketplace entry. The tool count is fixed at
16 (not 35) by grouping actions behind `kind` parameters, and state lives in
files under `%APPDATA%\as-ig-mcp` so several Claude Code sessions share one
session, cache, digest, event log, journal and queue.

## How the existing system works, per this document

The incumbent is the vendor MCP `everyhand-instagram` (aichargelabs 0.2.7), a
frozen Windows executable bundling instagrapi 3.2.3; that version's
`fetch_fb_dtsg()` scrapes a GraphQL query URL returning JSON with no `__eqmc`
block, so the Facebook CSRF token is always `None` and Instagram refuses 13 of
the vendor's read tools with `RuntimeError: unauthorized use of script
(1:5174)`. The binary cannot be patched because its modules live inside the exe
PYZ archive and `iglib` is pyarmor-obfuscated. The document's measurement table
shows instagrapi 3.2.8 scraping the homepage HTML instead, returning a real
`fb_dtsg` token, and making every previously dead endpoint work on the same
session cookies. The intended end state keeps the vendor daemon present but
sharing one Instagram login with the new server, all state on disk, a 90-second
read cache, and a realtime socket used for events only while writes stay on the
HTTP path.

**Paraphrase result:** every section could be paraphrased. No Blocker on
comprehension.

## Findings

### Blocker
None.

### Major

- **M1. The confirm gate is only described for `ig_write`; other tools can mutate without one.**
  §6 tool table, §6 data-flow step 6, §3 criterion 5, D7. `ig_thread` carries
  "mark seen, react, unsend, mute, hide, title, group members" and `ig_account`
  carries "professional settings, category, AI label" — mutations not in the
  `ig_write` kind list. A reader cannot tell whether those paths are routed
  through `writes.py` or bypass it, so the central safety claim is not provable.
- **M2. The unattended queue runner contradicts "no write without a confirm code".**
  §2, §6 `ig_queue`, §9 phase 6, §3 criterion 5, D8. A Scheduled Task publishing
  every five minutes, unattended. Nothing says whether the queued publish is
  confirmed at enqueue time or gated at publish time. Same question for
  Instagram's native `schedule_at`.
- **M3. "roughly 40 capabilities" contradicts the enumeration in the same section.**
  §2 line 49 against §2 lines 52–70. The list holds about 30 read groups and
  about 40 write groups, plus 8 unique capabilities. The headroom number drives
  the "superset of the market" claim in the same sentence.
- **M4. The acceptance artifact is named three ways and never linked.**
  Header, §2, §6 "Verification depth", §8, D1. "market study", "capability
  matrix" and "capability checklist" are used for two artifacts; no path is
  given for the checklist.
- **M5. Success criterion 17 depends on a mechanism that appears only in the detailed range.**
  §3 criterion 17 versus §10 M14. Nothing in §1–§8 states that the vendor
  daemon keeps running or how two processes share one login. The vendor MCP's
  fate — kept, replaced or uninstalled — is never answered.
- **M6. The mapping table omits three write kinds the spec says it contains.**
  §6 write kinds name IGTV, quicksnap and cutout sticker under `publish`; the
  mapping gives only photo/video/reel/album/story uploads. D6 says they "stay in
  the mapping". Since `mapping.py` is called "the single place to change" and
  the read-only flags are the structural guard, a missing entry is a hole in the
  mechanism the safety story rests on.
- **M7. Two tools claim the same writes; ownership is not assigned.**
  §6 `ig_thread` versus the write kinds. `mark seen`, `react` and `unsend` appear
  in both. The spec does not say which executes them or whether the per-thread
  variants still pass the gate.

### Nit

- **N1.** Duplicate step number "7." in the §6 data flow.
- **N2.** `__eqmc` is never explained — the root-cause argument depends on the
  reader knowing it is the marker carrying the CSRF token in page HTML.
- **N3.** `iglib` is undefined — a vendor-internal module named without
  explanation, so "cannot be patched" is asserted rather than understood.
- **N4.** "our style file" is undefined and unlisted — no path, no format, no
  entry in the §6 source tree or state list.
- **N5.** `ig_manage` is mentioned as a possible split but never exists in the
  16-tool list; the reader cannot tell whether v1 ships 16 or 17 tools.
- **N6.** Undefined jargon: FBNS, MQTT keep-alive, IGTV, cutout sticker, the
  `iris` event kind, Meta's "App Review" and "Advanced Access".
- **N7.** "linked accounts" appears in two tools and is never defined.
- **N8.** The 4,096-character description limit has no stated origin.
- **N9.** "the relogin command" is never named.
- **N10.** `ig_inbox` scope conflicts with §3 criterion 3, which compares
  `ig_inbox`'s last message for "a known thread" while the tool is described as
  showing threads that await a reply.
- **N11.** Realtime is described as always-on in §6 and behind a flag in §10, and
  no flag name or config key is given.
- **N12.** "instagrapi's delay range" is not quantified.
- **N13.** External references are paths, not resolvable links; the market claim
  cannot be checked from the document alone.
- **N14.** Phase 3 checks registration but gives no command.
- **N15.** The referenced checklist uses `ig_thread kind=requests|spam|group`,
  while §6's `ig_thread` description lists no `kind` parameter — the two
  documents disagree on the tool contract.

---

Skipped: no live Instagram call, no audit of the phase briefs or build log against
the spec. Risk: if the matrix and the checklist are one artifact under two names,
M4 drops to a Nit; if `ig_thread` and `ig_account` writes are already routed
through `writes.py` in the brief but unstated in the spec, M1 and M7 drop to Nits.
