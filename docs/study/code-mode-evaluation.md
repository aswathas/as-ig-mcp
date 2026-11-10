# AS-IG-MCP — Code Mode Evaluation

- Date: 2026-11-10
- Status: evaluated, **not adopted**
- Decision: keep the 16 direct tools; add no code-execution sandbox
- Owner: Aswath

## 1. The question

Can Code Mode be added to `as-ig-mcp`, and should it be?

Code Mode means: the model writes a short program that calls tools, instead of
calling one tool at a time. The model gets one tool, usually called `execute` or
`codemode`, whose input is code.

## 2. Two implementations, one name

The name covers two very different builds.

### Cloudflare `@cloudflare/codemode` (2026)

- One outer tool. Input is `{ code: string }`.
- Code runs in a sandbox: a fresh V8 isolate via the Worker Loader API
  (`DynamicWorkerExecutor`), or a hidden iframe (`IframeSandboxExecutor`).
- Tools appear as typed methods, for example `github.list_pull_requests()` or
  `ig.threads()`. Each call crosses back to the host over RPC.
- The sandbox has no direct network. `fetch()` and `connect()` are blocked by
  default (`globalOutbound: null`). A `Fetcher` can be supplied to route outbound
  calls through a controlled service.
- The sandbox never receives credentials. The connector holds the client; the
  sandbox only sees methods and results.
- A durable runtime can pause a run before a tool marked `requiresApproval`,
  show the pending action, and resume by replaying already-applied calls from a
  log.

There are two integration levels:

| Level | API | Approval |
|---|---|---|
| Simple | `createCodeTool({ tools, executor })` | Tools marked `needsApproval` are excluded; no pause |
| Durable | `createCodemodeRuntime({ ctx, connectors, executor })` | Pause, approve, replay, rollback, snippets |

### OLX `olxcars` (this machine's CLI and MCP)

- A Python fluent SDK, not a sandbox: `OlxQuery("i10").city("chennai").fetch(pages=2).top(3)`.
- Runs in the caller's process.
- Fetches directly with `curl_cffi`. There is no network wall.
- No approval layer, no replay, no durable log.
- Returns a compact result, so only a few rows enter the model context.

The OLX README reports the measured effect on a 60-car search: 32,450 tokens
down to 142 (99.5% fewer), and three round trips down to one. Those numbers are
the project's own measurement, not reproduced here.

## 3. What actually saves tokens

In both builds, the saving comes from the same move: loop, join and filter
**before** returning. Only the small result enters the chat.

The sandbox is a safety wrapper, not the source of the saving. OLX proves this:
no sandbox, same order of saving.

## 4. Fit for `as-ig-mcp`

The current surface is 16 tools. Their schemas cost roughly 1.5k tokens, which is
an estimate, not a measurement. There is no context problem to solve.

The shape that fits Code Mode is a read-heavy loop:

- scan many DM threads, keep unread or needs-reply ones
- page a feed, deduplicate, return the top N
- compare insights across several posts or accounts

The shape that does not fit is a write:

- every write already stops at a desktop Yes/No dialog (`MessageBoxW`).
- A script that calls a write would freeze mid-run for up to
  `AS_IG_APPROVE_TIMEOUT` (300 s), with no clean resume.
- A durable pause/replay layer would have to be built from scratch in Python.

Security also differs from OLX. `as-ig-mcp` holds a DPAPI-encrypted session and
runs on the owner's machine. Free-form Python executed in-process could read
`session.enc`, the audit journal, and the filesystem. Cloudflare avoids this by
giving the sandbox no keys and no files; that protection is not free.

## 5. Options considered

| Option | What it adds | Why not chosen |
|---|---|---|
| A. Cloudflare runtime | JS/TS runtime, Worker Loader, durable object storage | Moves the server to a JS stack; requires a hosted runtime; no measured need |
| B. In-process free-form Python (`execute`) | One tool, real Python, direct access | Session and filesystem exposure; approval freeze; no isolation |
| C. Restricted chain tool | `unread(50)`, `thread(id).messages()`, fixed methods only | Viable, but only after a repeated task is named |
| D. Composite read tools | `ig_inbox_digest`, `ig_thread_digest` | Chosen fallback: no runtime, no sandbox, most of the win |
| E. Keep 16 tools | nothing | Current state; adequate for one-off calls |

Option A is the only one that provides real isolation, and it is the most
expensive. Option B is the cheapest to write and the most dangerous. Option D
captures the common read-heavy job without either.

## 6. Decision

**Do not implement Code Mode now.**

Keep the 16-tool surface. If a repeated read-heavy task appears, build the
composite tools first:

1. `ig_inbox_digest` — scan up to N threads, skip read ones, return one line per
   thread plus a needs-reply flag.
2. `ig_thread_digest` — summarise one long thread.

Only if those are insufficient, and the filters vary on every use, add the
restricted chain tool (option C). Free-form code (options A or B) needs a named
reason and a sandbox, not `exec`.

## 7. Risks that drove the decision

| Risk | Why it matters |
|---|---|
| Account challenge | A code loop can hit Instagram faster than a human. This account has already been challenged once. Any runner needs a per-run call cap and a delay between calls. |
| Session exposure | In-process code can read `session.enc`, cookies, and the audit journal. |
| Approval freeze | A write in the middle of a script blocks on a desktop dialog; there is no pause/replay. |
| Maintenance | Generated tool types drift when the tool surface changes. |
| Small payoff | 16 tools do not create the context pressure Code Mode was designed for. |

## 8. Revisit triggers

Revisit this decision when one of these is true:

- A read-heavy task is repeated regularly and needs more than 50 tool calls.
- The same runner is needed for a second MCP server, so the cost is shared.
- The server is hosted for other people, where untrusted code makes a sandbox
  mandatory.

Until then, the 16 tools stay.

## 9. Sources

Primary:

- Code Mode: The better way to use MCP — Cloudflare blog, 2025-09-26.
  <https://blog.cloudflare.com/code-mode/>
- Code Mode — Cloudflare Agents docs.
  <https://developers.cloudflare.com/agents/tools/codemode/>
- How Code Mode works (approvals, replay, rollback, snippets).
  <https://developers.cloudflare.com/agents/tools/codemode/how-it-works/>
- Use MCP tools with Code Mode (`McpConnector`, `requiresApproval`).
  <https://developers.cloudflare.com/agents/tools/codemode/mcp/>
- Code Mode API reference (six entry points, limits).
  <https://developers.cloudflare.com/agents/tools/codemode/api-reference/>
- olxcars — search used cars on OLX India (README, Code Mode section).
  <https://github.com/aswathas/olx-car-search>

## Appendix — what was read

- The Cloudflare blog post, in full.
- The Code Mode overview, how-it-works, MCP, AI SDK, TanStack AI, browser,
  OpenAPI, durable-runtime and API-reference pages, pulled through the context7
  MCP server (60,742 characters).
- The olxcars README, including its measured table.
- The local `as-ig-mcp` surface: `src/as_ig_mcp/server.py`, `writes.py`,
  `session.py`, `realtime.py`.

Not done: no local benchmark, no prototype, and no attempt to run the Cloudflare
package. The comparison is architectural, based on the published behaviour.
