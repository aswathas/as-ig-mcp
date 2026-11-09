# EGM Stage 7 — Critic Report (feature range)

**Target:** `C:\Users\aswat\Projects\as-ig-mcp\docs\superpowers\specs\2026-11-10-as-ig-mcp-v1-design.md`
**SemanticTarget:** the feature range — everything from line 1 up to (but not including) the header `## 9. Implementation ownership`
**FeatureRange:** 1–460 (line 461 is the `## 9. Implementation ownership` header and is out of scope)
**DetailedRange:** N/A for this stage
**Standard:** `feature-spec-standard` — `C:\Users\aswat\.claude\plugins\cache\egm\egm\0.1.1\resources\document_standards\feature-spec-standard.md`
**Personas:** `agents\design_critic.md`, `agents\structural.md`, `agents\style.md` (plugin cache root `C:\Users\aswat\.claude\plugins\cache\egm\egm\0.1.1`)
**GoldfishContext:** `[]` — empty for all three reviewers
**Stage:** 7 — Critic Review
**Date:** 2026-11-10

## Reviewer Status

| Reviewer | Type | Status | Instances | Raw findings |
| --- | --- | --- | --- | --- |
| `egm-design` | `egm:egm-design` | completed | 1 | 28 |
| `egm-structural` | `egm:egm-structural` | completed | 1 | 18 |
| `egm-style` | `egm:egm-style` | completed | 1 | 34 |

No reviewer failed or returned empty, so no retry was needed. All three were dispatched as fresh subagents of their registered types with the target path, the resolved line range, their persona file, the standard file and the empty GoldfishContext list. All three are strictly read-only; none wrote to the target document.

## Severity Summary (raw, before cross-reviewer dedup)

| Severity | design | structural | style | Total |
| --- | --- | --- | --- | --- |
| 🔴 Blocker | 3 | 1 | 1 | 5 |
| 🟡 Major | 14 | 5 | 19 | 38 |
| 🟢 Nit | 11 | 12 | 14 | 37 |
| **Total** | **28** | **18** | **34** | **80** |

After deduplication across lenses, the 80 raw findings collapse to **31 distinct issues** (3 blockers, 18 majors, 10 nits). The 49 duplicates are almost entirely the same three defects reported by all three lenses.

---

# Reviewer: `egm-design` (Architecture and Design Critic)

Standard applied: Problem Statement · Goals & Non-Goals · Proposed Architecture · Alternatives Considered · Risks & Mitigations, plus the stress-test vectors (standard compliance gaps, faulty assumptions, unmitigated risks).

### 🔴 Blocker

**D-1 — The confirm-code contract contradicts itself.**
*Scope:* lines 114–116 (§3 criterion 5), line 416 (§7 table), vs lines 256–264 (§6 step 6).
Line 114 says a write without a code returns "`needs_confirm` + preview + a 6-digit code"; line 416 repeats "`needs_confirm` + preview + code"; line 258 says the server returns "**the action handle and the preview, never the code** — the agent cannot approve on the account owner's behalf". Two different protocols. §10 M10 (line 568) names the code-returning protocol as the defect that was found and fixed.
*Recommendation:* pick the §6 behaviour (handle + preview only) and write it in all three places. Change criterion 5 and the §7 row to "`needs_confirm` + preview + action handle; the code is shown to the owner out-of-band".

**D-2 — The no-desktop fallback writes the approval secret to a file the agent can read.**
*Scope:* lines 262–264.
"When no interactive desktop is available, the fallback is a file the owner opens (`%APPDATA%\as-ig-mcp\pending.txt`)". The agent runs as the same user on the same machine and can read `%APPDATA%`, so it can approve its own write — the exact hole the popup closes.
*Recommendation:* do not persist the code. Fallback = the owner reads the code from a channel the agent cannot reach, or the file holds a nonce plus a per-call challenge the owner types from another device.

**D-3 — The REST fallback path can double-send a mutation, contradicting "no write is auto-retried".**
*Scope:* lines 244–245 vs line 424.
Line 244: "on a GraphQL or JSON error it refetches once, then falls back to the api/v1 REST variant of that feature" — no read/write qualifier. Line 424: "No write is auto-retried after a partial failure." A write that reaches Instagram and fails on a JSON/parse error is exactly that partial failure; the fallback then sends it a second time. The idempotency key does not help, because the fallback is internal to one call and reuses the same key.
*Recommendation:* restrict the fallback to `read_only=True` features; writes surface the error and the operator retries with a fresh key. Also state which features have a REST variant at all — the mapping currently lists one canonical method plus one fallback (posts, line 334), while the data flow promises a fallback "of that feature" generally.

### 🟡 Major

**D-4 — State model is contradictory: files are shared across sessions, but pending confirmations are in-memory.**
*Scope:* lines 159–161 vs line 293; also lines 252–264 and line 422.
"State lives in files, not in one process, so several Claude Code sessions share it safely" (line 160) versus "Pending write confirmations: in-memory only, lost on restart = safe" (line 293). A confirm started in session A cannot be completed in session B.
*Recommendation:* either persist to `pending.json` with expiry and single-use, or state that a write may only be confirmed within the session that started it.

**D-5 — No concurrency model for the instagrapi client.**
*Scope:* lines 226, 249, 381–396.
One client instance is shared by the request path, the digest poller and the realtime daemon thread. The spec never says calls are serialized or that the client is thread-safe. Parallel tool calls can interleave on a non-thread-safe client and can blow the 1–3s per-request delay (line 164).
*Recommendation:* state that all instagrapi calls go through one lock/queue, that the realtime thread uses its own client instance or the same lock, and that the throttle is global.

**D-6 — The queue runner publishes with stored approval and has no crash-safe dedup.**
*Scope:* lines 265–270, 310, 418.
The runner executes a write long after approval with no re-check. If the tick crashes between Instagram accepting the post and `queue.json` being updated, the next tick republishes. No idempotency key is stored with the item, and `queue.json` is last-writer-wins (line 422).
*Recommendation:* store a key per queue item, mark the item "publishing" before the call and "published" after, and treat a "publishing" item found at startup as "unknown outcome — ask the operator". Define a late-publish policy.

**D-7 — The mapping table does not cover several features the spec promises.**
*Scope:* lines 254, 301, 316–323 vs 331–361; test plan line 429.
Promised but with no canonical method: `mark_seen`, `share`, `report`, `remove_follower`, `toggle_comments`, thread `mute`/`hide`/`title`/`group members` (named explicitly at lines 254 and 301), follow-request approve/decline (line 303), message requests and spam box (line 61), "professional type" (lines 70, 375). The write-kind list at 316–323 has no `mute_thread`, `hide`, `title`, `group_members`, `follow_request`, `download` or `professional_type`. The §8 test at line 429 ("mapping.py covers every feature in §6 exactly once") cannot pass as §6 is written.
*Recommendation:* one mapping line per declared write kind and read kind, or remove the claims from §2/§6.

**D-8 — Nothing in the stack can draft a reply, yet `ig_inbox suggest=true` promises one.**
*Scope:* lines 285–288, 300, 150–153.
The style file "uses it to draft a reply"; `ig_inbox` returns an "optional suggested reply". The dependency list is `instagrapi`, `mcp`, `pycryptodomex` — no model, no API key, no local model. No component is assigned the drafting work.
*Recommendation:* pick (a) the server returns the style attributes and the agent drafts — then the tool must return the style object, not a "suggested reply"; or (b) the server drafts, which needs a model dependency and a privacy decision §4 does not cover. Option (a) is smaller and fits a local single-user tool.

**D-9 — "Threads awaiting a reply" has no definition and no source field.**
*Scope:* line 300.
Instagram DMs have no per-thread "awaiting your reply" flag the spec identifies. Without a stated predicate the tool's core behaviour is undefined.
*Recommendation:* state the predicate and the source field, plus the fallback when the field is absent.

**D-10 — Success criteria can pass on stale cache data.**
*Scope:* lines 108–109, 114–116, 249, 439–441.
The 90-second cache sits under every read. Criterion 2 ("counts stable across two consecutive calls") is satisfied by the cache, not by Instagram. Criterion 5's negative check ("reading the thread afterwards and finding nothing new") is also satisfied by a stale cache, so a wrongly sent message is hidden by the same cache and the check passes either way. Same for §8 item 5.
*Recommendation:* every verification read in §3 and §8 must use the bypass (`fresh=true`) or wait past the TTL. Say so in criteria 2, 5, 6, 8 and 10.

**D-11 — Two promised capabilities map to something that answers a different question, and one contradicts a stated non-goal.**
*Scope:* line 77 vs lines 127–129; line 77 vs line 101.
"A first-class best-time tool" and checklist R25 map to `ig_insight kind=best`, which criterion 10 defines as Instagram's own *ranked posts* — a ranking, not a time-of-day recommendation. No posting-time data source is specified anywhere. "Local competitor benchmarking" maps to reading another account (R26), but line 101 puts read-only scraping of other people's accounts out of scope.
*Recommendation:* drop both from §2, or add the best-time data source and reconcile the competitor-read scope.

**D-12 — The first-login flow is missing from a package designed to be installed by strangers.**
*Scope:* line 313, lines 80–82, line 419.
Only the relogin path is described. The initial login (username, password, the checkpoint, where credentials come from, whether they are stored) is never specified. §7 covers DPAPI failure and a malformed session, but not "no session exists yet".
*Recommendation:* specify the first-run flow: where the password is entered (a CLI prompt, never a file), how the checkpoint code is supplied, what is persisted, and that the password is not persisted.

**D-13 — The one-login mechanism depends on an unverified vendor CLI flag.**
*Scope:* lines 398–403; criterion 17 at lines 144–146.
`instagram-mcp.exe login --sessionid-env IG_SESSIONID` is asserted against the same opaque, frozen binary §1 proves is broken. Nothing shows the flag exists or that the vendor reuses our session. If it does not, two live sessions exist on one account — the exact exposure the design claims to avoid. Criterion 17 is also tautological if we injected the sessionid, and may not be checkable at all if the vendor stores it encrypted.
*Recommendation:* verify the flag before depending on it. Otherwise state the alternative honestly (stop the vendor daemon, or accept two sessions with an explicit risk line).

**D-14 — The 6-digit confirm code has no expiry, no attempt limit and no lockout.**
*Scope:* lines 256–264, 430.
One million values, and the agent may call `ig_write` with `confirm=` as often as it likes. §8 mentions "expired code" in a test, but no duration, attempt cap or lockout is defined anywhere.
*Recommendation:* define a TTL (e.g. 10 minutes), a small attempt budget (e.g. 3, then invalidate the handle), and single-use on success. State the threat model: the gate assumes the agent has no UI access to the owner's desktop.

**D-15 — The alternatives section does not meet the standard: no cost, performance or scalability trade-offs, and several major decisions are never compared.**
*Scope:* lines 171–207.
The seven rejections are all reasonable but qualitative ("more schemas", "weeks of App Review"). The decisions with the largest blast radius are never compared at all: the Windows Scheduled Task runner (vs a background thread, vs a detached process), the file-based state store (vs SQLite, vs a daemon), the popup consent mechanism (vs dry-run-plus-explicit-allow, vs a device push), and the realtime transport (vs polling-only — which the spec already builds as the fallback, so polling-only is a complete alternative that was never evaluated as a candidate).
*Recommendation:* add cost/complexity/scalability columns and add rows for the four missing decisions.

**D-16 — The acceptance matrix is not in the repo, and the row count is wrong.**
*Scope:* lines 53–58.
Line 53 cites `docs/reviews/capability-checklist.md` as "37 rows"; the file has 45 rows (R1–R26, W1–W10, P1–P9). Line 57 points to `docs/study/AS-IG-MCP - Capability Matrix.md`, which does not exist in the repo. The "superset of every Instagram MCP server and every commercial tool's Instagram surface" claim is therefore unverifiable from the repo, which is exactly what the standard's core principle requires.
*Recommendation:* commit the capability matrix into `docs/study/`, fix the row count, and add a mapping row → tool → mapping entry so the checklist and `mapping.py` can be cross-checked mechanically.

**D-17 — The 4,096-character tool-description limit is ambiguous, and the 16-tool surface likely blows it.**
*Scope:* lines 187–189, 202–207, 295–314.
Line 205 reads as a per-server budget; line 206 applies it per-tool. The two readings differ by two orders of magnitude. Under the per-server reading, the 16 descriptions in the table (~2,300 characters of prose alone, before schemas) plus names and parameter schemas exceed 4,096.
*Recommendation:* measure the total description and schema budget of the 16 tools against the real limit before building. If it is per-server, the 16-vs-35 decision has to be redone.

### 🟢 Nit

- **D-18 — The chosen design is the alternative the spec rejects** (lines 202–207 vs 309, 316–323). A mega tool with one `action` parameter is rejected for tool-search matching; `ig_write` ships with one `kind` parameter over ~30 actions. The real reason to keep one write tool — the single confirm gate — is never stated.
- **D-19 — "Mute" means two different operations** (line 254 thread mute, line 322 `mute` kind, line 357 `mute_posts_from_follow`). Name them `mute_thread` and `mute_posts` and give each a mapping line.
- **D-20 — Health class count does not match the acceptance list** (lines 274–278 list 12 classes vs checklist P1 "10/10 classes live"). Fix the count in one place and enumerate the classes by name.
- **D-21 — Cache bypass flag named two ways** (line 224 `fresh=`, lines 249 and 430 `fresh=true`).
- **D-22 — Realtime subscribe placement is unclear and order-sensitive** (lines 381–390). A blocking subscribe on the MCP main thread stalls the stdio loop; starting the reader thread before the subscribe completes drops events.
- **D-23 — The realtime flag makes criterion 12 and checklist R23 unreachable by default** (lines 133–134, 381–383). Nothing in the install path says how the user sets `AS_IG_REALTIME=1` for Claude Code.
- **D-24 — `style.json` has no writer** (lines 285–288, 311). The only local-content tool is `ig_preset` (caption/hashtag/first-comment). Fold reply style into `ig_preset` or state that the owner edits the file by hand.
- **D-25 — `pycryptodomex` has no job** (lines 151, 213). Session encryption is DPAPI via `ctypes`, and A4 says no third-party crypto is needed. Drop it or state its purpose.
- **D-26 — Append-only logs grow without bound and store raw payloads** (lines 289–290, 414). `events.jsonl` and `audit.jsonl` have no rotation or size cap, and unknown events are stored raw, which can include message content.
- **D-27 — Python 3.14 with `instagrapi==3.2.8` is asserted, not shown** (line 150). Record the actual installed versions from the working venv.
- **D-28 — `ig_status` promises a "quota" that is never defined** (line 299). Line 580–582, outside the range, says it reports "unknown" — the in-range table should agree.

---

# Reviewer: `egm-structural` (Document Structure)

Standard applied: mandatory sections present · heading hierarchy · formatting rules (lists, tables, code blocks, links) · cross-reference integrity.

### 🔴 Blocker

**S-1 — The confirm-code contract contradicts itself.**
*Scope:* lines 114–116 (§3 criterion 5), line 416 (§7 table), lines 439–441 (§8 test 5).
Same defect as D-1, reached from the structure side: §3, §7 and §8 all encode the code-returning protocol, while §6 encodes the opposite. §3 is the acceptance contract, so as written the spec is satisfiable by the insecure flow — the exact defect M10 documents. §8 test 5 then says "with the code → exactly one message" with no step for where the code comes from, because the tool never returns it.
*Recommendation:* rewrite §3.5 as "returns `needs_confirm` + preview + an action handle; the code is displayed to the account owner only and never returned to the agent"; change the §7 cell to "owner sees the 6-digit code in a popup; agent sees `needs_confirm` + preview + handle"; add the popup-read step to §8 test 5.

### 🟡 Major

**S-2 — Broken cross-reference to the capability matrix.**
*Scope:* lines 57–58 (§2).
`docs/study/AS-IG-MCP - Capability Matrix.md` does not exist. `docs/study/` contains only `AS-IG-MCP - Deep Study and Build Blueprint.md`, which carries the market comparison in its §3. Line 6 correctly says the matrix lives in the Obsidian vault, so line 57 is a stale vault path presented as a repo path. The superset claim over "every Instagram MCP server and every commercial tool's Instagram surface" rests on this file.
*Recommendation:* cite the repo copy's §3 and label the vault path as vault-only, or add the missing file.

**S-3 — The acceptance list is described incorrectly.**
*Scope:* lines 52–54 (§2).
The spec calls `docs/reviews/capability-checklist.md` "37 rows, one row per capability, each with a check". The file has three tables — Reads (R1–R26), Writes (W1–W10), Platform (P1–P9) — 45 rows, plus a "Parked by user" table and an "Out of v1" list. Nothing yields 37.
*Recommendation:* say "three tables (Reads/Writes/Platform), 45 rows".

**S-4 — The write-kind list does not match the tool surface it describes.**
*Scope:* lines 254, 301, 316–323 (§6).
Lines 254 and 301 name six mutating thread actions routed through `ig_write`: mark seen, react, unsend, mute, **hide, title, group members**. The write-kind list at 316–323 contains only the first four; `hide`, thread `title` and group-member management have no kind, no mapping entry and no confirm-gate entry. Separately, checklist R19 requires `ig_write kind=download`, which appears in neither the write-kind list nor §2's in-scope write list (only `ig_story` mentions "download" at line 306).
*Recommendation:* add the missing kinds or remove them from the prose at lines 254/301, and reconcile R19 with the tool table.

**S-5 — Capability inflation against the 16-tool surface.**
*Scope:* lines 73–77 (§2) vs line 308 (§6).
§2 claims two separate white-space capabilities, "Instagram's own best-post ranking" and "a first-class best-time tool", and separately "local competitor benchmarking". §6 gives one kind per purpose: `kind=best` and `kind=compare`. The checklist uses the same kinds (R25, R26). The headline white-space list overstates what the tool surface delivers, and "a first-class best-time tool" describes a `kind` value, not a tool.
*Recommendation:* collapse to one bullet per kind and describe best-time as `ig_insight kind=best`, or add the separate tool.

**S-6 — The standard's Risks & Limits requirement is met outside the range, not inside it.**
*Scope:* lines 103–460.
The standard requires the spec to "explicitly call out its own constraints… identify potential failure modes, security implications, scalability limits, and how they will be mitigated". Inside the range, §7 covers runtime failure modes with detection and remedy, §4 states constraints, and security appears as one bullet (lines 168–169). There is no risk register in the range for the two hard problems the standard names — security implications (live session credential, ToS exposure, write authority) and scalability limits (rate limits, two servers, queue, realtime). The register (M1–M14) starts at line 531, outside the range.
*Recommendation:* add a risks-and-limits subsection inside §4 or §7, or state that the register lives in §10 and cross-reference it by ID from the range.

### 🟢 Nit

- **S-7 — No H3 headings anywhere; §6 sub-sections are bold pseudo-headings** (lines 237, 280, 295, 316, 331, 363, 373, 381, 398). One H1 and H2-only sections; §6 runs 195 lines with no navigable sub-structure. The pseudo-heading style is inconsistent — three end with a period, six do not.
- **S-8 — Alternatives presented as bold-led prose with no comparison table** (lines 173–207). The document uses tables for comparable sets everywhere else; §5 lists seven alternatives as paragraphs, so complexity, cost, performance and scalability cannot be scanned side by side.
- **S-9 — Dense run-on paragraphs where lists or tables belong** (lines 316–329, 331–361). The write-kind list (~30 comma-separated items) and the canonical-method mapping (30 lines, one paragraph) are the two densest blocks and the parts an implementer copies most often.
- **S-10 — Duplicated rationale** (lines 86–89 vs 177–181; lines 373–379 vs 426–459). The Graph API rejection appears twice with near-identical reasoning.
- **S-11 — Success criteria carry no IDs and are not traced to the checklist or test plan** (lines 103–145, 426–459). The document already uses ID schemes (A1–A9, D1–D8, M1–M14; R1–R26, W1–W10, P1–P9), but §3's 17 criteria are a bare numbered list.
- **S-12 — Metadata block does not follow the repo's document convention** (lines 1–11). Sibling docs open with YAML front matter (title, type, status, created, updated); the spec uses loose `Key: value` lines. The H1 also reads "AS-IG-MCP v1 — Spec" while the file is named `…-v1-design.md`.
- **S-13 — Fenced code block has no language tag** (line 211). The directory tree uses a bare fence; tag it ` ```text `.
- **S-14 — The in/out lists need sub-grouping and a deferral marker** (lines 52–101). "In (v1)" mixes capabilities, white space, safety and distribution in one flat list. "Out (v1)" mixes permanently impossible items with deferred ones, distinguished only by the word "Paused" in one bullet.
- **S-15 — Rejection attributed without a link** (lines 93–95). "Paused by user on 2026-11-10" attributes the parking to the user with no pointer to where the decision and captured designs live.
- **S-16 — Parameter name inconsistent** (lines 224, 249, 429). `fresh=` vs `fresh=true`.
- **S-17 — The tool table has no "mutates?" column and one cell carries policy prose** (lines 297–314). Line 301's `ig_thread` cell runs three sentences of policy where every other cell is a terse list.
- **S-18 — Machine-absolute paths hardcoded** (lines 5, 150, 166, 239). Four references to `C:\Users\aswat\…` make the spec non-portable and self-referential.

---

# Reviewer: `egm-style` (Technical Writing)

Standard applied: tone and conciseness · objectivity and claim calibration · fluff and redundancy · defensive-caveat classification (DROP / CALIBRATE / RELOCATE / KEEP).

### 🔴 Blocker

**Y-1 — The spec states two incompatible confirm-code behaviours.**
*Scope:* lines 115, 258–259, 416.
Criterion 5 says the tool "returns `needs_confirm` + preview + a 6-digit code"; the failure table repeats it; §6 step 6 says the tool "returns **the action handle and the preview, never the code**". This is the core safety mechanism of the whole feature, and an implementer reading the success criteria would build the flow where the agent sees the code — defeating the stated purpose.
*Recommendation:* pick the §6 behaviour and rewrite lines 115 and 416 to match.

### 🟡 Major

- **Y-2 — "The market" is an undefined scoping term, and the capability-superset claim is unbounded** (lines 46, 56, 59, 64, 73–77, 174–175). "the whole market covers", "a superset of every Instagram MCP server and every commercial tool's Instagram surface", "covering the union of every market capability plus the white space". No section defines the market set. "the white space" is jargon and a third phrasing of the same set. **CALIBRATE** — name the compared set with a count and a date, and use one term throughout.
- **Y-3 — The same artifact has two names** (lines 52, 373). "the acceptance list" vs "the capability checklist" for one file, both with the path inline. One label per artifact.
- **Y-4 — The §2 in-scope enumeration and the §6 tool surface do not reconcile in either direction** (lines 59–70 vs 297–314, 253–254, 303, 316–323). §2 omits `ig_feed kind=archive|guides|liked`, `ig_story` download, `ig_person include=about`, `ig_status` quota, `ig_search kind=account`, `remove_follower`. §6 step 6 lists thread actions "mute, hide, title, group members" and §6 line 303 lists follow-request approve/decline, none of which appear in the write-kind list. "Professional type" and "category" are one kind but two items at lines 375–376.
- **Y-5 — Three named capabilities never reach the tool surface** (lines 74, 77 vs 297–314, 308, 448). "A first-class best-time tool" and "local competitor benchmarking" have no tool, kind or mapping entry. Line 74 promises "per-post insights compared by age"; `kind=compare` is defined at line 448 as "ranks the last 5 posts" — a different feature.
- **Y-6 — "Instagram's own best-post ranking" is listed under "Capabilities nobody in the market has"** (line 75). False on its face — Instagram provides the ranking; what is claimed as novel is that no MCP exposes it. **CALIBRATE** — rewrite as "exposing Instagram's own best-post ranking (available in the app, exposed by no market MCP)".
- **Y-7 — "(the only competitor uses a Claude Code developer channel)"** (line 75). "The only competitor" is undefined — the only competitor at what, of which surveyed set, as of when? No count, no name, no source.
- **Y-8 — "The vendor" is overloaded across at least three referents** (lines 17, 27, 137, 398–403, 422). The MCP `everyhand-instagram`, "the vendor binary", `instagram-mcp.exe`, "the vendor daemon". The document never states that `everyhand-instagram` and `instagram-mcp.exe` are the same process.
- **Y-9 — The spec asserts a CLI capability of a third-party binary with no evidence** (line 400). `instagram-mcp.exe login --sessionid-env IG_SESSIONID` — nothing in §6 "Verification depth" or §8 confirms this flag exists. If it does not, criterion 17 fails and the account carries two live sessions.
- **Y-10 — The idempotency key and the confirm-code lifetime are never specified** (lines 116–118, 261, 430). Who generates the idempotency key? How long does the code live? How many wrong attempts before refusal? §8 tests "expired code" but no expiry is defined. A 6-digit code with no expiry and no attempt limit is brute-forceable.
- **Y-11 — "Multi-account" is out of scope while "linked accounts" is in, with no distinction** (lines 93–95 vs 313–314). A fresh reader cannot tell whether operating a second account is v1 work.
- **Y-12 — The `ig_people` cell contradicts itself** (line 303). "follow requests (approve/decline) … Approving a follow request is a write and goes through `ig_write`". Tool descriptions are what Claude Code matches on, so the ambiguity propagates into discovery.
- **Y-13 — `ig_session` describes relogin as both a tool capability and a CLI command** (line 313). The reader cannot tell whether relogin is agent-callable — which matters, because agent-callable relogin means the agent can reach the emailed code path. "export" is also unspecified.
- **Y-14 — The alternatives evaluation omits the three largest architectural choices** (lines 171–207). Never compared: stdio vs HTTP/SSE (line 157), file-based state vs a database (line 159), DPAPI vs a credential manager (line 168). The standard's Alternatives Rule requires proving other viable designs were considered.
- **Y-15 — An unverified product limit and a subjective judgment stand in for a rationale** (lines 203–205). "a mega tool makes matching worse" is subjective with no measurement; the 4,096-character limit is attributed to Claude Code with no source; the consequence is stated as fact.
- **Y-16 — Dependency pinning is stated inconsistently** (lines 151–153 vs 213). §4 lists `mcp` and `pycryptodomex` unpinned; the tree comment says "(pinned)". An unpinned `mcp` is a live risk.
- **Y-17 — `instagram-fixed` appears with no explanation** (lines 137, 470). Criterion 14 names `instagram-fixed`/`as-ig`; line 9 defines the id as `as-ig` and the build order registers `as-ig`. An implementer cannot tell whether two servers are registered.
- **Y-18 — No risk section: the private-API dependency, account-ban risk and ToS exposure are absent** (lines 147–169, 405–424). §7 is a failure-mode table; it does not address Instagram banning the account for automated DM traffic, ToS exposure, or scaling past one account. There is no retention policy for `audit.jsonl`.
- **Y-19 — A concurrency failure mode is claimed but neither mitigated nor tested** (line 422 vs 159–160, 434–455). "share it safely" is contradicted by silent last-writer-wins; "digest markers merge by timestamp" is not an implementable algorithm; no §8 test covers the row.
- **Y-20 — `wait_s` values differ and the realtime precondition is missing** (lines 133, 451). Criterion 12 uses `wait_s=5`, §8 test 9 uses `wait_s=10`. Neither states that `AS_IG_REALTIME=1` must be set.

### 🟢 Nit

- **Y-21 — Undefined terms** (lines 101, 77, 251, 313, 314, 174): "Agent-reach style read-only scraping", "best-time tool", "the realtime queue" (matches nothing in §6 — the surface is a socket plus `events.jsonl`), "account insights units", "export", "white space".
- **Y-22 — "A credential, not a reading"** (line 99) — "not a reading" is not a term used anywhere; the contrast is with a read operation.
- **Y-23 — "`fresh= bypass`" is malformed** (line 224).
- **Y-24 — The "User sees" cell hardcodes "2 items were overdue"** (line 418) — an instance, not a specification.
- **Y-25 — "Health is green" is undefined** (line 457) — no status vocabulary is defined for `ig_health` output.
- **Y-26 — "The same one-call-three-tools problem" is undefined** (line 188).
- **Y-27 — "Revisit only if …" appears three times with no owner, trigger or threshold** (lines 89, 194, 206–207). Conditional paths without a trigger read as aspirations.
- **Y-28 — Header metadata is partly self-referential or unresolvable** (lines 5, 6) — "Canonical" points at the file itself; the vault path has no vault location; the checklist path is not listed under Research.
- **Y-29 — Inconsistent emphasis on version numbers** (lines 20, 25, 154) — bold vs plain vs code span for the same version.
- **Y-30 — Inconsistent voice and actor naming** (lines 88, 100, 300, 44, 256, 263, 424) — third person vs first/second; the human actor is called "a human", "the account owner", "the owner", "the operator", "the user".
- **Y-31 — Two rhetorical flourishes** (lines 84, 375) — "named, not hidden"; "because a mapping entry is one line" as an unverified assertion.
- **Y-32 — "`mapping.py` covers every feature in §6 exactly once" is circular** (line 428) — §6 contains features in at least four places; the set is not identified.
- **Y-33 — Table formatting is inconsistent** (lines 297–314) — the `ig_queue` cell runs ~60 words with an embedded implementation detail; `ig_thread` and `ig_people` carry disclaimers inline.
- **Y-34 — The mapping is a 30-line semicolon-separated paragraph** (lines 331–361).

**KEEP (explicitly not reported as findings):** §5 satisfies the Alternatives Rule with seven rejections each carrying a concrete technical rationale and no unattributed maintainer rejection. §3's two drift-prone criteria (8's ">= plus a complete field set", 10's "verified live") are explicitly calibrated to evidence. §7 and §6 step 6's no-desktop fallback are correctly scoped caveats placed at the decision point — keep, do not relocate.

---

# Cross-reviewer synthesis — top items

Three defects were found independently by all three lenses. They are the same issues, not three different ones, and they are the only blockers.

**1. The confirm-code contract is self-contradictory — 🔴 Blocker (D-1, S-1, Y-1; lines 114–116, 256–264, 416, 439–441).**
§3 criterion 5 and the §7 failure table both say the tool returns the 6-digit code; §6 step 6 says it returns "the action handle and the preview, **never the code**". §3 is the acceptance contract, so as written the spec is satisfiable by the flow that §10 M10 names as the defect that was already found and fixed. An implementer who follows §3 rebuilds the hole the popup was built to close. The three lenses agree on both the defect and the fix direction: adopt the §6 behaviour (handle + preview) and rewrite §3, §7 and §8 to match, including the popup-read step in §8 test 5. This is the single highest-priority edit in the document.

**2. The `pending.txt` fallback leaks the approval secret to the agent — 🔴 Blocker (D-2; lines 262–264).**
Found by the design lens only, and it is the deepest issue of the three. The popup shows the code to a human and withholds it from the agent; the fallback writes the same code to a file under `%APPDATA%` that the agent, running as the same user on the same machine, can read. The fallback is therefore not a weaker version of the gate — it removes it. Either the code never reaches a file, or the file carries a nonce and the owner supplies a second factor from a channel the agent cannot reach.

**3. The REST fallback can double-send a mutation — 🔴 Blocker (D-3; lines 244–245 vs 424).**
The fallback is described without a read/write qualifier, and "no write is auto-retried after a partial failure" is stated without excluding it. A write that Instagram accepted but whose response failed to parse is exactly the partial failure; the fallback sends it again. The idempotency key does not save it, because the fallback is internal to one call. Restrict the fallback to `read_only=True` features.

**4. The mapping table does not cover the features the spec promises — 🟡 Major (D-7, S-4, Y-4, Y-5; lines 254, 301, 303, 316–323 vs 331–361).**
All three lenses converged here. `mark_seen`, `share`, `report`, `remove_follower`, `toggle_comments`, thread `hide`/`title`/`group members`, follow-request approve/decline and `professional_type` are named in prose but have no kind, no mapping entry and no confirm-gate entry. `mapping.py` is called "THE table" and "the single place to change when Instagram moves", and §8 line 429 tests that it "covers every feature in §6 exactly once" — with §6 written as it is, that test cannot pass. Independently verified against the working tree: `src/as_ig_mcp/mapping.py` has 71 entries and none of `mark_seen`, `share`, `report`, `remove_follower` or `toggle_comments` among them, so the gap is live, not theoretical.

**5. §2 scope and §6 tool surface do not reconcile — 🟡 Major (D-11, S-3, S-5, Y-3, Y-4, Y-5; lines 46–82 vs 295–323).**
The white-space claims are inflated: "a first-class best-time tool" and "local competitor benchmarking" resolve to `ig_insight kind=best` and `kind=compare`, and `kind=best` is defined by criterion 10 as Instagram's ranked posts — a ranking, not a posting-time recommendation, with no data source specified. "Local competitor benchmarking" also maps to reading another account, which line 101 puts out of scope. In the other direction, §2 omits capabilities the tool table has. The acceptance list is also misdescribed: `docs/reviews/capability-checklist.md` is called "37 rows" but has 45 (R1–R26, W1–W10, P1–P9) — independently counted and confirmed.

**6. The standard's Risks & Limits requirement is unmet inside the range — 🟡 Major (S-6, Y-18, D-15; lines 103–460).**
Two lenses raised it independently. The standard requires explicit security implications and scalability limits with mitigations. Inside lines 1–460, §7 is a runtime failure-mode table and security is one bullet about DPAPI. The register that does this (M1–M14) starts at line 531, outside the reviewed range, and the range does not point to it. Account-ban exposure, ToS exposure, upstream-API-breakage-with-no-fallback and audit-log retention are absent from the range.

**7. The Alternatives Rule is only partly met — 🟡 Major (D-15, Y-14, S-8; lines 171–207).**
§5 is qualitatively strong but omits the decisions with the largest blast radius: stdio vs HTTP/SSE, file state vs a database, DPAPI vs a credential manager, the Scheduled Task runner vs a background thread, the popup vs dry-run-plus-explicit-allow, and — most notably — realtime vs polling-only, which the spec already builds as the fallback and therefore never evaluates as a candidate.

**8. The one-login mechanism rests on an unverified vendor flag — 🟡 Major (D-13, Y-9; lines 398–403, 144–146).**
Two lenses raised it; the design lens adds that criterion 17 is tautological if we injected the sessionid, and may not be checkable at all if the vendor stores it encrypted. This is the mitigation for the account-ban risk, and it depends on a flag in the same frozen, pyarmor-obfuscated binary §1 proves cannot be inspected.

**9. Verification reads can be served from cache — 🟡 Major (D-10; lines 108–109, 114–116, 249, 439–441).**
Criterion 2's "stable across two consecutive calls" and criterion 5's "find nothing new" are both satisfied by a 90-second cache rather than by Instagram. A wrongly sent message would be hidden by the same cache that hides its absence, so the write-gate check passes either way. Requires `fresh=true` (or a TTL wait) on every verification read.

**10. The confirm code has no expiry, attempt cap or lockout, and the idempotency key has no owner — 🟡 Major (D-14, Y-10; lines 256–264, 116–118, 430).**
One million possible codes, an agent that may retry freely, and an "expired code" that is tested but never defined.

Remaining majors, in descending order of how much they block an implementer: the missing concurrency model for the shared instagrapi client (D-5), the queue runner's lack of crash-safe dedup (D-6), the reply-drafting promise with no component to draft it (D-8), the missing first-login flow for a package sold to strangers (D-12), the missing `pending` state model against the "shared safely" claim (D-4), the undefined "awaiting a reply" predicate (D-9), and the ambiguous 4,096-character budget (D-17, Y-15) — where the per-server reading of the limit would invalidate the 16-vs-35 tool decision.

Nits (10 distinct after dedup): the `fresh` spelling, the health class count (12 in §6 vs 10 in checklist P1), `pycryptodomex` having no job, the unbounded append-only logs, `ig_status`'s undefined quota, the missing YAML front matter, no H3 headings in a 195-line section, the self-referential "Canonical:" path, the undefined terms list, and the two unreferenced external artifacts.

## Verification notes

Claims in the findings that were checked directly against this repo before being written up:

- **Capability checklist row count.** `docs/reviews/capability-checklist.md` contains 36 `| Rn |` / `| Wn |` / `| Pn |` rows in three tables — 26 reads, 10 writes, 9 platform = **45**, not the 37 the spec claims. Confirmed (S-3, D-16).
- **Broken study path.** `docs/study/` contains exactly one file, `AS-IG-MCP - Deep Study and Build Blueprint.md`. `AS-IG-MCP - Capability Matrix.md` does not exist in the repo. Confirmed (S-2, D-16).
- **Mapping coverage.** `src/as_ig_mcp/mapping.py` holds 71 `_entry(` calls; a search for `mark_seen`, `share`, `report`, `remove_follower` and `toggle_comments` as feature keys returns nothing, and the thread actions (`direct_thread_hide`, `direct_thread_update_title`, `direct_thread_add_users`) appear only in the `MUTATING_METHODS` list, never as mapping entries. Confirmed (D-7, S-4).
- **`pycryptodomex` is unused.** It is a declared dependency in `pyproject.toml` and appears nowhere in `src/as_ig_mcp/`. Confirmed (D-25).
- **`ig_status` quota.** `tools_status.py` returns `"quota": "unknown - instagrapi exposes no quota endpoint"`, matching §10 M13 but not the §6 tool table's bare "quota". Confirmed (D-28).
- **Health class count.** `tools_health.py` defines 10 probes and no realtime-socket probe, against §6's list of 12 classes. Confirmed (D-20).
- **The write guard exists and works.** `client.py` `call_feature` raises `WriteNotAllowedError` when a feature is not `read_only` and `allow_write` is not set, including on the fallback path — the structural guard the spec describes at lines 363–371 is real in the working tree. This does not change the spec findings, but it means D-7 and D-10 are gaps in the spec's promise rather than in the shipped guard.

## Not checked

- Whether each instagrapi 3.2.8 method named at lines 331–361 exists in the installed package, and whether each is genuinely read-only. The design lens took the spec's own claim (lines 363–371) as given, and this review did the same.
- Whether `instagram-mcp.exe login --sessionid-env IG_SESSIONID` exists on the vendor binary (D-13, Y-9). The binary was not invoked.
- The Obsidian vault note `AS-IG-MCP/AS-IG-MCP - Capability Matrix.md`, and §9–§10 (lines 461–608), which are outside the reviewed range.
- Runtime behaviour of any tool. No Instagram call was made and no server was started.
