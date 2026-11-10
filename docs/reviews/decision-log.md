# AS-IG-MCP — Decision Log

One entry per real choice, oldest first. The build log holds the chronology; the
checklist holds the state. This file holds the reasoning.

## D1 — Use instagrapi 3.2.8 instead of the vendor's frozen 3.2.3

- Date: 2026-11-10
- Context: the vendor MCP failed 13 read tools with `unauthorized use of script (1:5174)`. Its bundled 3.2.3 reads `fb_dtsg` from a GraphQL page that no longer contains it, so the token is always `None`.
- Options: patch the vendor binary (modules inside the PYZ, `iglib` pyarmor-obfuscated); stay on 3.2.3 with an older endpoint set; pin 3.2.8.
- Chosen: pin `instagrapi==3.2.8`. It reads the homepage HTML and returns a real token on the same session cookies.
- Evidence: `docs/reviews/build-log.md`, measured table: `fb_dtsg` `None` → real token, and 10/10 health classes live.
- Consequence: every read and write depends on the 3.2.8 pin; the mapping test checks each named method exists on the class.

## D2 — One server, 16 kind-based tools

- Date: 2026-11-10
- Context: the vendor exposed 35 narrow tools; every endpoint change meant a new tool.
- Options: mirror 35 tools; one tool per area with a `kind` argument; one giant tool.
- Chosen: 16 area tools (`ig_feed`, `ig_write`, `ig_inbox`, …) with a `kind` argument, and one mapping table from feature to method.
- Evidence: `src/as_ig_mcp/mapping.py`, `server.py`; packaging test lists all 16.
- Consequence: adding an endpoint is one mapping row plus one kind, not a new tool.

## D3 — The write gate is a human click, not a code

- Date: 2026-11-10
- Context: the EGM Stage 8 review showed a confirmation-code gate never proved the owner's consent; a relayed code is still just text.
- Options: six-digit code; OAuth dance; yes/no dialog on the owner's desktop.
- Chosen: `MessageBoxW` Yes/No on the owner's screen. No code exists to relay. No dialog means no write.
- Evidence: W1–W4 in the checklist, live: Yes executed, No denied, replay `already_done`, journal holds both.
- Consequence: the server must run in an interactive desktop session; headless writes fail closed.

## D4 — No is the default button, and the box closes on timeout

- Date: 2026-11-10
- Context: live runs showed Enter approving by accident, and a timed-out dialog stayed on screen while later steps stacked more dialogs.
- Options: leave Windows defaults; change flags only; change flags and close the window thread.
- Chosen: `MB_DEFBUTTON2` plus `EnumThreadWindows` + `WM_CLOSE` when the join times out.
- Evidence: `tests/test_writes.py` passes; live dialog now defaults to No.
- Consequence: a timeout denies the write and leaves no box behind.

## D5 — SQLite (WAL) for cache, digest and queue

- Date: 2026-11-10
- Context: loose JSON state meant a last-writer-wins clobber; the 90-second cache is the main defence against blocks, and a silent clobber switched it off.
- Options: keep JSON with a lock file; per-key files; SQLite.
- Chosen: one `state.db` with WAL and a 10-second busy timeout.
- Evidence: `tests/test_state_db.py`, `test_cache.py`; live cache read succeeded with the network disabled.
- Consequence: one file to back up; two processes can read while one writes.

## D6 — Realtime socket runs in its own process

- Date: 2026-11-10
- Context: the private socket drops with an SSL error and once segfaulted the interpreter during teardown.
- Options: in-process thread; separate process with a file handoff; no realtime.
- Chosen: a worker process appends events to `events.jsonl` and state to `realtime_status.json`; the server supervises and restarts it.
- Evidence: `tests/test_realtime.py`; live `deltaNewMessage` seq 1285 captured while the worker was up.
- Consequence: a broken socket cannot take the server down; consumers read files, not pipes.

## D7 — Read tools may only dispatch read-only features

- Date: 2026-11-10
- Context: a read path could reach a mutating method through a mapped fallback.
- Options: trust the mapping table; guard at dispatch; one test per tool.
- Chosen: a shared guard plus a test that every feature a read tool declares is `read_only` and absent from the mutator list.
- Evidence: `tests/test_read_tools_are_read_only.py`.
- Consequence: a new read kind must be marked read-only and listed in that tool's `FEATURES`.

## D8 — Fill missing capabilities with kinds, not new tools

- Date: 2026-11-10
- Context: notes, mentions, downloads, boxes, groups and requests had methods but no tool.
- Options: add tools per capability; widen existing `kind` sets.
- Chosen: widen `ig_feed` (`notes`, `mentions`, `download`), `ig_inbox` (`box`, `kind=groups`), `ig_search` (`lat`/`lng`), `ig_story` (viewers).
- Evidence: `tests/test_tools_feed.py`, `test_tools_inbox.py`, `test_tools_discovery.py`.
- Consequence: the surface stays at 16 tools.

## D9 — Mentions come from `story_mentions`, not `notification_user_tagged`

- Date: 2026-11-10
- Context: `notification_user_tagged` looks like a reader but is a setting toggle (`off`/`following_only`/`everyone`).
- Options: use the toggle (wrong); filter the activity feed; use the `story_mentions` section of `news_inbox_v1`.
- Chosen: `story_mentions.reels` + `product_stories_reels`, plus the count string.
- Evidence: live probe of `news_inbox_v1` showed the section; `ig_feed kind=mentions` returned the section.
- Consequence: mentions follow Instagram's own mention section; a change there is a mapping fix, not a new endpoint.

## D10 — Guides 404 is reported, not hidden

- Date: 2026-11-10
- Context: `/v1/guides/user/` returns 404; a raw traceback made a valid call look broken.
- Options: drop the kind; return an empty list; return a clear unavailable error.
- Chosen: clear error naming the removed endpoint.
- Evidence: live `ig_feed kind=guides` returns "Instagram removed the user guides endpoint (404)".
- Consequence: R2 stays held; the tool never pretends guides work.

## D11 — Place search accepts coordinates directly

- Date: 2026-11-10
- Context: place search needed `IG_PLACES_LAT`/`LNG`; `location_search` takes no query.
- Options: env only; args only; args with env fallback.
- Chosen: optional `lat`/`lng` arguments, env fallback, same error when neither is present.
- Evidence: live place search returned 5 results with Chennai coordinates.
- Consequence: callers can place-search without process env.

## D12 — Downloads pick the method by media type

- Date: 2026-11-10
- Context: photo, video, reel and album need different instagrapi download methods; a single `photo_download` mapping was wrong for three of them.
- Options: force photo download; expose four kinds; inspect the media and pick.
- Chosen: `ig_feed kind=download media_id=…` reads `media_info` and calls photo/video/clip/album download, with path containment.
- Evidence: live download of a post wrote one file inside the media folder.
- Consequence: one kind covers all four types; unknown types fall back to photo.

## D13 — Competitor compare falls back to public likes/comments

- Date: 2026-11-10
- Context: Instagram refuses `insights_media` for accounts we do not own; the compare returned rows with no values.
- Options: return failure; invent reach; rank by public likes/comments.
- Chosen: public likes/comments fallback, with `metric_source` naming the source and reach left null for other accounts.
- Evidence: live compare on `instagram` ranked 3 posts with `metric_source=public`.
- Consequence: cross-account comparison is engagement-based, never a guessed reach.

## D14 — Story viewer parse failures return an empty list with a note

- Date: 2026-11-10
- Context: instagrapi raises `KeyError('viewers')` with zero viewers and a pydantic `ValidationError` when it cannot parse a viewer record.
- Options: let it fail; patch instagrapi; catch parse errors in the tool.
- Chosen: catch `KeyError`/`ValueError`, return `viewers: []` plus a note explaining the payload.
- Evidence: live viewers call now returns `ok: true` with the note; `tests/test_tools_story.py`.
- Consequence: a valid story never looks broken; viewers may be empty even when Instagram has some.

## D15 — Expose every mutating feature, including deletes

- Date: 2026-11-10
- Context: coverage showed `media_delete`, `highlight_delete`, `note_delete` and several publish variants had methods but no kind, so tests could not clean up.
- Options: leave them unreachable; expose only the ones tests need; expose all mutators.
- Chosen: add kinds for the missing mutators and keep the coverage script as the check.
- Evidence: `write_coverage.py` now reports only `first_comment` (reachable via `comment_reply`).
- Consequence: every promised write is reachable through `ig_write` or the queue.

## D16 — Video and reel require a thumbnail or MoviePy

- Date: 2026-11-10
- Context: `video_upload`/`clip_upload` cannot generate a cover without MoviePy.
- Options: add MoviePy as a hard dependency; require a thumbnail; skip video.
- Chosen: document `thumbnail` as an optional argument; tests pass one.
- Evidence: video and reel published with `thumbnail=…`, then deleted.
- Consequence: video publishing works without a heavy dependency if the caller supplies a cover.

## D17 — Story music uses Instagram's own catalogue

- Date: 2026-11-10
- Context: attaching an external audio file is not how Instagram stories carry music.
- Options: upload audio with the video; use `music_search` and attach a track.
- Chosen: search the catalogue, attach the `Track`, publish with `publish_story_music` or `publish_story_video_music`.
- Evidence: live "Scenuke Scene" and "How r u" story tests; `find_song.py` output.
- Consequence: tracks are region- and licence-limited; Instagram can refuse one.

## D18 — MoviePy 2.2.1 for music stories, Pillow restored to 13

- Date: 2026-11-10
- Context: music story rendering requires MoviePy; installing it pins Pillow <12, while instagrapi requires Pillow ≥13.
- Options: add MoviePy as a dependency (breaks the Pillow pin); require a manual install; skip music.
- Chosen: manual `moviepy==2.2.1` install, then restore `pillow==13.0.0`. Noted in the build log.
- Evidence: music story posted after the restore.
- Consequence: music stories need a documented workaround until the pins reconcile.

## D19 — Real clicks for the gate, an auto-approve stub for action coverage

- Date: 2026-11-10
- Context: the gate was proven with real Yes/No/replay clicks. Covering every write action with dozens of clicks is error-prone and slow.
- Options: click every action; stub the dialog for all; skip action coverage.
- Chosen: keep the real dialog for W1–W4, then use an in-process `dialog=lambda: True` for the remaining action tests, spaced and journalled.
- Evidence: `live_writes_auto.py` batches r/c/d/m/s/p/f/n/w/e/t.
- Consequence: the gate and the actions are proven separately; the stub is test-only and never wired into `server.py`.

## D20 — Realtime is proven with an external DM and a fresh worker

- Date: 2026-11-10
- Context: self-sent DMs do not echo, and earlier attempts sent before the socket was up.
- Options: trust connect/subscribe; use a real second account's DM; skip.
- Chosen: open a worker, wait for a fresh `connected_at`, then have `deer.9094611` send one DM.
- Evidence: `realtime_window.json` holds a `deltaNewMessage`, topic 146, seq 1285, text "How r u", ~20s after connect.
- Consequence: R23 is green; the normalized event still has `thread_id: null` because the path is inside a JSON string in the payload.

## D21 — Held rows are marked `todo — held`, not deleted

- Date: 2026-11-10
- Context: nine rows cannot pass on this account: removed endpoints, missing methods, account-type risk, harmful actions, no linked destinations, no pending requests.
- Options: delete them; mark blocked; mark todo with the reason.
- Chosen: `todo — held`, with each reason in the checklist and the build log.
- Evidence: `docs/reviews/capability-checklist.md`, `build-log.md`.
- Consequence: 36 green, 9 held; nothing is silently dropped.

## D22 — The second-account session was deleted

- Date: 2026-11-10
- Context: rapid session switching triggered Instagram's anti-abuse challenge on both accounts; the owner asked for only `this_aswath`.
- Options: keep the second session for later; delete it.
- Chosen: delete `session.second.enc`; keep only `this_aswath` sessions.
- Evidence: `%APPDATA%\as-ig-mcp` now holds `session.enc`, `session.main.enc`, `session.this_aswath.enc`.
- Consequence: second-account tests stay held; they need the owner to log in again.

## D23 — Documentation is a decision log plus a change inventory

- Date: 2026-11-10
- Context: a chronological build log records what happened, but not why each choice beat its alternatives.
- Options: one long summary; a decision log and a file-by-file inventory.
- Chosen: two structured files, no mass dump; the `aswath-commit` skill defines the format.
- Evidence: this file and `change-inventory.md`.
- Consequence: future changes append entries D24+ and add one inventory row per file.

## D24 — Code Mode is not adopted

- Date: 2026-11-10
- Context: Cloudflare's Code Mode (one code-execution tool plus an isolated sandbox, with pause/approve/replay) and OLX's in-process variant were evaluated for `as-ig-mcp`.
- Options: Cloudflare runtime; in-process free-form Python; restricted chain tool; composite read tools; keep the 16-tool surface.
- Chosen: keep the 16 tools and add no code-execution sandbox. If a repeated read-heavy task appears, build composite read tools (`ig_inbox_digest`, `ig_thread_digest`) first; a restricted chain tool only if filters vary every time.
- Evidence: `docs/study/code-mode-evaluation.md`; Cloudflare docs and blog, olxcars README.
- Consequence: no new runtime or JS layer; writes stay behind the desktop gate; revisit only on a named repeated task, a second server sharing the runner, or multi-user hosting.
