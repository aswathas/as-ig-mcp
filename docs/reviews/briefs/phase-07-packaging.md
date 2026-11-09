# Phase 7 brief — packaging: license, plugin, registry manifest, tool map

Project root: `C:\Users\aswat\Projects\as-ig-mcp`
Read first: `docs/study/AS-IG-MCP - Capability Matrix.md` (the market facts),
`docs/reviews/capability-checklist.md`, `pyproject.toml`, `README.md`.

Make the project installable by a stranger and recognizable as a Claude Code
plugin and as an MCP registry server. Nothing here may change server behaviour.

## 1. `LICENSE`

MIT, "Copyright (c) 2026 Aswath". The full standard MIT text.

## 2. `pyproject.toml`

- `[project.urls]`: Homepage, Repository, Issues, all pointing at
  `https://github.com/aswathas/as-ig-mcp`.
- `keywords`, `classifiers` (Programming Language :: Python :: 3.11 … 3.14,
  License :: OSI Approved :: MIT License, Topic :: Communications :: Chat).
- `requires-python = ">=3.11,<3.15"` — the server is verified on 3.14 and
  instagrapi 3.2.8 predates 3.15.
- `[project.scripts]`: `as-ig-mcp = "as_ig_mcp.cli:main"` so the package can be
  run as a command.
- Keep `instagrapi==3.2.8` and `mcp>=2.3,<3` exactly as they are.

## 3. `.claude-plugin/plugin.json`

Follow the working example on this machine:
`C:\Users\aswat\.claude\plugins\marketplaces\olx-car-search\.claude-plugin\plugin.json`.

```json
{
  "name": "as-ig-mcp",
  "description": "Instagram for AI agents: DMs, posts, insights, and what changed since last time.",
  "version": "0.1.0",
  "author": {"name": "Aswath"},
  "homepage": "https://github.com/aswathas/as-ig-mcp",
  "repository": "https://github.com/aswathas/as-ig-mcp",
  "license": "MIT",
  "keywords": ["instagram", "mcp", "social", "dm", "insights"],
  "skills": [],
  "mcpServers": {
    "as-ig": {
      "command": "uvx",
      "args": ["--from", "as-ig-mcp==0.1.0", "as-ig-mcp", "serve"]
    }
  }
}
```

The launcher must be **pinned to an exact version**. An unpinned
`uvx --from git+https://…` launcher is a hard block in Anthropic's
pre-submission checklist — the existing `olx-car-search` plugin has that
problem, so do not copy it.

## 4. `.claude-plugin/marketplace.json`

Also follow the `olx-car-search` example:

```json
{
  "name": "as-ig-mcp",
  "owner": {"name": "Aswath", "url": "https://github.com/aswathas"},
  "plugins": [{"name": "as-ig-mcp", "source": "./", "description": "..."}]
}
```

## 5. `server.json` — the official MCP registry manifest

Schema: `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.aswathas/as-ig-mcp",
  "description": "Instagram for AI agents: read and send DMs, read posts and insights, publish, and see what changed since last time.",
  "version": "0.1.0",
  "repository": {"url": "https://github.com/aswathas/as-ig-mcp", "source": "github"},
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "as-ig-mcp",
      "version": "0.1.0",
      "transport": {"type": "stdio"}
    }
  ]
}
```

The `io.github.<user>/` prefix is required when the registry metadata is
published with GitHub authentication.

## 6. The README needs the registry marker and the honest status

- Add this line near the top, hidden in an HTML comment, exactly as the registry
  expects it:

  ```markdown
  <!-- mcp-name: io.github.aswathas/as-ig-mcp -->
  ```

- Keep the install, session, health and write-gate sections that are already
  there, and update the status paragraph to the truth at the time of writing:
  which tools are in, what is verified live, and what is still planned. Do not
  claim anything that is not built.
- Add a "Data and privacy" section, because Anthropic's directory asks: what
  the tool reads (the account you log into), what it stores (an encrypted
  session, a cache, an audit journal, presets), where that lives
  (`%APPDATA%\as-ig-mcp`), how long it is kept (until you delete it), whether
  data goes anywhere else (no — the only network calls are to Instagram), and
  whether it targets under-18s (no).
- Add the licence line and the repository link.

## 7. `docs/tool-map.md`

One table: every tool of the old vendor MCP against ours, so somebody moving
over knows what changed. Cover all 35 vendor tools, including the local
reply-style ones, and say plainly where a vendor tool has no equivalent and why
(for example `ig_daemon` — the vendor's daemon control — and `ig_download_media`,
which becomes `ig_story`/`ig_feed` download).

Also a short section listing the capabilities we have that no market tool has:
the delta digest, realtime push, the insights tool, the approval gate, the audit
journal, presets.

## 8. Checks

- `claude plugin validate --strict ./.claude-plugin/plugin.json` must print
  `✔ Validation passed`. If it does not, fix what it complains about and run it
  again. Report the exact output.
- The package must build: `.venv/Scripts/python.exe -m pip install build` then
  `.venv/Scripts/python.exe -m build`. If `build` cannot be installed, use
  `.venv/Scripts/python.exe -m pip wheel . --no-deps -w dist` and report that
  instead. Report the exact command and its output.
- The built artifact must contain the package: check that `dist/` holds a wheel
  and that the wheel contains `as_ig_mcp/server.py`.

## 9. Tests

- `tests/test_packaging.py`
  - `plugin.json` parses and has the required keys: name, description, version,
    author, license, keywords, mcpServers;
  - the `mcpServers` launcher pins an exact version (the string contains `==`),
    so the "unpinned launcher" block cannot come back;
  - `marketplace.json` parses and its plugin entry name matches `plugin.json`;
  - `server.json` parses, its name starts with `io.github.`, its package is the
    PyPI identifier, and its version matches `pyproject.toml`;
  - the README contains the `mcp-name:` marker line;
  - `pyproject.toml` and `LICENSE` exist and are not empty.

## 10. Check that must pass before you finish

```
.venv/Scripts/python.exe -m pytest -q
claude plugin validate --strict ./.claude-plugin/plugin.json
```

Both clean. Print the pytest summary line and the plugin validation output as
your last output.

## 11. Constraints

- Touch only files under `C:\Users\aswat\Projects\as-ig-mcp`.
- Do not change any behaviour of `src/as_ig_mcp/` — packaging only. If you think
  a behaviour change is needed, say so in your final message instead of making
  it.
- Do not publish anything to PyPI or the registry. Publishing is phase 8 and
  needs the owner's go-ahead.
- Do not run git write commands.
