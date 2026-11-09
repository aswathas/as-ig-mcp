# AS-IG-MCP

An Instagram MCP server for AI agents. Reads DMs, measures posts, tells you what
changed since last time, and pushes new messages live. Built on instagrapi
3.2.8, pinned.

**Status: in build.** Nine of thirteen tools are in and verified live against a
real account; the write gate, the insights tool, the queue and the realtime
socket are still to come. See `docs/reviews/capability-checklist.md` for the
per-capability state and `docs/reviews/build-log.md` for what ran and what broke.

## Why it exists

The vendor Instagram MCP (`everyhand-instagram`) fails 13 of its read tools with
`RuntimeError: unauthorized use of script (1:5174)`. Its frozen binary bundles
instagrapi 3.2.3, whose `fetch_fb_dtsg()` reads the token from a page that does
not contain it, so the token is always empty and Instagram refuses the call.
instagrapi 3.2.8 reads it from the right page and the same session then works.
The full diagnosis is in `docs/study/`.

## Install

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

Then register it with Claude Code:

```bash
claude mcp add as-ig --scope user -- .venv\Scripts\python.exe -m as_ig_mcp serve
```

## Get a session

The session is a real Instagram login, encrypted with DPAPI for your Windows
user and never written to git.

```bash
.venv\Scripts\python.exe -m as_ig_mcp session login
```

It asks for the username and password on the terminal (the password is never
echoed), then for the login code Instagram sends by email or SMS. Later:

```bash
.venv\Scripts\python.exe -m as_ig_mcp session status
.venv\Scripts\python.exe -m as_ig_mcp session relogin
```

## Check it works

```bash
.venv\Scripts\python.exe -m as_ig_mcp health
```

Ten endpoint classes, live: profile, followers, posts, per-post insights,
account insights, DM threads, presence, notifications, discovery, business DM
box.

## Writing is gated

Every write shows the account owner a yes/no dialog on their own screen with
the exact action, and waits. Yes, it happens. No, Cancel, or five minutes of
silence, and nothing happens. There is no approval code anywhere, so there is
nothing for an agent to relay or fetch. On a machine with no interactive
desktop, writes are refused rather than approved by the agent.

## Configuration

| Variable | Meaning | Default |
|---|---|---|
| `APPDATA` | where the state lives | your Windows profile |
| `IG_PLACES_LAT`, `IG_PLACES_LNG` | coordinates for place search | unset |
| `AS_IG_REALTIME` | `0` turns the realtime socket off | on |
| `AS_IG_APPROVE_TIMEOUT` | seconds the approval dialog waits | 300 |
| `AS_IG_CACHE_TTL` | read cache seconds | 90 |

## Layout

```
src/as_ig_mcp/     the server
docs/superpowers/  the approved spec
docs/study/        the market study and the capability matrix
docs/reviews/      the capability checklist, the build log, the review reports
```

## Licence

MIT.
