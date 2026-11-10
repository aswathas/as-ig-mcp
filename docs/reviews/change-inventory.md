# AS-IG-MCP — Change Inventory

One row per changed file. Every row says what changed, why, and how it was
tested. The decision log explains the choices; the build log explains the order.

| File | What changed | Why | How tested |
|---|---|---|---|
| `src/as_ig_mcp/mapping.py` | Added `media_info`, per-type downloads, `media_delete`, `highlight_delete`, `note_delete`, `dm_request_approve`, `close_friend_remove`, `publish_story_music`, `publish_story_video_music`; added `video_upload_to_story_with_music` to the mutator list | Give every promised read and write a real method, including cleanup | `tests/test_mapping.py` (exact set, area, method existence, mutator consistency) |
| `src/as_ig_mcp/server.py` | Added `lat`/`lng` to `ig_search`, `media_id` to `ig_feed`, `box`/`kind` to `ig_inbox` | Expose the new tool parameters over MCP | `tests/test_server_smoke.py`, full suite import |
| `src/as_ig_mcp/tools_discovery.py` | `ig_search` accepts `lat`/`lng`; env fallback kept | Place search was env-only and unusable | `tests/test_tools_discovery.py`; live place search returned 5 |
| `src/as_ig_mcp/tools_feed.py` | Kinds `notes`, `mentions`, `download`; guides 404 becomes a clear error; `media_id` parameter | Notes, mentions and downloads had no tool; a 404 traceback looked broken | `tests/test_tools_feed.py`; live notes, mentions, download, guides error |
| `src/as_ig_mcp/tools_inbox.py` | `box=general/primary/requests/spam`, `kind=groups`; `FEATURES` widened | Boxes and groups had no listing path | `tests/test_tools_inbox.py`; live 3 general threads, 2 group threads, requests/spam readable |
| `src/as_ig_mcp/tools_insight.py` | `_compare` adds public likes/comments fallback and `metric_source` | Instagram refuses insights for accounts we do not own | `tests/test_tool_insight.py`; live compare on `instagram` ranked 3 public-like posts |
| `src/as_ig_mcp/tools_story.py` | Viewers catches `KeyError`/`ValueError` and returns an empty list with a note | instagrapi cannot parse empty or unexpected viewer payloads | `tests/test_tools_story.py`; live viewers returned `ok: true` with the note |
| `src/as_ig_mcp/tools_write.py` | Added publish variants, `comment_pin`, `save_media`, `mute_stories`, `highlight_edit`, `close_friend_remove`, `publish_igtv`, `cutout_sticker`, `quicksnap`, `note_delete`, `delete_media`, `delete_highlight`, `approve_dm_request`; documented args | Every mutating feature must be reachable through `ig_write` | `tests/test_tool_write.py`; live batches covered each action |
| `src/as_ig_mcp/writes.py` | `MB_DEFBUTTON2`; close the dialog thread's windows on timeout | Enter could approve; a timed-out box stayed on screen | `tests/test_writes.py`, `test_tool_write.py`, `test_queue.py` (46 pass); live deny/approve |
| `tests/test_mapping.py` | Required-feature and area sets updated | Keep the mapping honest as features were added | It is the test; 192 suite passes |
| `tests/test_tool_insight.py` | Compare fallback test with `insights_media` raising | Lock the public-metric behaviour | It is the test |
| `tests/test_tool_write.py` | Dispatch tests for every new write kind | Lock the kind → method mapping | It is the test |
| `tests/test_tools_discovery.py` | Coordinates-as-arguments test | Lock the new place-search path | It is the test |
| `tests/test_tools_feed.py` | Notes, mentions, download, guides-404 tests | Lock the new kinds and the clean error | It is the test |
| `tests/test_tools_inbox.py` | Requests, general box, groups, unknown box tests | Lock the box/group listing | It is the test |
| `tests/test_tools_story.py` | Viewer `KeyError` and `ValueError` tests | Lock the graceful empty-list behaviour | It is the test |
| `README.md` | Status text reflects live gate and write execution; docs pointers added | The old status said live writes were still scheduled | Docs only |
| `docs/reviews/build-log.md` | Chronology: live write sweep, six gaps, blocked reasons, realtime proof, challenge note | Record what was run and what broke | Docs only |
| `docs/reviews/capability-checklist.md` | 36 green, 9 held as `todo — held`; per-row evidence | The definition of done must match reality | Docs only |
| `docs/reviews/decision-log.md` | D1–D24; D24 records the Code Mode decision | The reasoning was scattered or unwritten | Docs only |
| `docs/reviews/change-inventory.md` | New: this file | One place to see every file and its test | Docs only |
| `docs/study/code-mode-evaluation.md` | New: Code Mode evaluation (Cloudflare vs OLX, fit, options, decision, revisit triggers) | Record the reasoning behind D24 | Docs only |

## Outside the repo

- `C:\Users\aswat\.commandcode\skills\aswath-commit\SKILL.md` — new global skill
  that defines this documentation format and the commit procedure.
