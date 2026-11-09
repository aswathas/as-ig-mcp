"""stdio MCP server exposing ig_status, ig_health and ig_session."""

from __future__ import annotations

from typing import Any, Callable

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
except ModuleNotFoundError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _Server

from . import tools_health, tools_session, tools_status

mcp = _Server("as-ig")


def _safe(func: Callable[..., dict], *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


@mcp.tool(
    description="[AS-IG-MCP] Session, account, cache, realtime and health in one glance."
)
def ig_status() -> dict[str, Any]:
    return _safe(tools_status.ig_status)


@mcp.tool(
    description="[AS-IG-MCP] Probe each Instagram capability class and report live or dead."
)
def ig_health() -> dict[str, Any]:
    return _safe(tools_health.ig_health)


@mcp.tool(
    description="[AS-IG-MCP] Inspect the session, clear the cache, export redacted settings, or relogin."
)
def ig_session(action: str = "status") -> dict[str, Any]:
    return _safe(tools_session.ig_session, action)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
