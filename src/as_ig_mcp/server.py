"""stdio MCP server exposing the AS-IG-MCP tool surface."""

from __future__ import annotations

from typing import Any, Callable

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
except ModuleNotFoundError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _Server

from . import (
    tools_account,
    tools_discovery,
    tools_feed,
    tools_health,
    tools_inbox,
    tools_people,
    tools_session,
    tools_status,
    tools_story,
    tools_threads,
)

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


@mcp.tool(
    description="[AS-IG-MCP] One account's profile, with optional followers, following, posts, stories, highlights, comments, suggestions or about."
)
def ig_person(
    username: str | None = None,
    user_id: str | None = None,
    include: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    return _safe(
        tools_people.ig_person,
        username=username,
        user_id=user_id,
        include=include,
        limit=limit,
    )


@mcp.tool(
    description="[AS-IG-MCP] Followers, following, suggestions or follow requests for an account, paginated."
)
def ig_people(
    username: str | None = None,
    user_id: str | None = None,
    kind: str = "followers",
    cursor: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    return _safe(
        tools_people.ig_people,
        username=username,
        user_id=user_id,
        kind=kind,
        cursor=cursor,
        limit=limit,
    )


@mcp.tool(
    description="[AS-IG-MCP] Search users, hashtags, places, music, posts, DMs or an account handle."
)
def ig_search(kind: str = "user", query: str = "", limit: int = 20) -> dict[str, Any]:
    return _safe(tools_discovery.ig_search, kind=kind, query=query, limit=limit)


@mcp.tool(
    description="[AS-IG-MCP] Feed kind: posts, reels, tagged, saved, archive, notifications, collections, tray, guides or liked."
)
def ig_feed(
    kind: str = "posts",
    username: str | None = None,
    user_id: str | None = None,
    cursor: str | None = None,
    limit: int = 12,
    include: str = "",
) -> dict[str, Any]:
    return _safe(
        tools_feed.ig_feed,
        kind=kind,
        username=username,
        user_id=user_id,
        cursor=cursor,
        limit=limit,
        include=include,
    )


@mcp.tool(
    description="[AS-IG-MCP] Read a DM thread messages, participants, presence, and pagination cursor."
)
def ig_thread(
    thread_id: str,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return _safe(tools_threads.ig_thread, thread_id=thread_id, cursor=cursor, limit=limit)


@mcp.tool(
    description="[AS-IG-MCP] List DM threads awaiting a reply, with optional suggested reply and style draft."
)
def ig_inbox(
    hours: int = 48,
    limit: int = 10,
    suggest: bool = False,
    thread_id: str | None = None,
) -> dict[str, Any]:
    return _safe(
        tools_inbox.ig_inbox,
        hours=hours,
        limit=limit,
        suggest=suggest,
        thread_id=thread_id,
    )


@mcp.tool(
    description="[AS-IG-MCP] Story and highlight details, viewers, likers, or download media to local folder."
)
def ig_story(
    story_id: str | None = None,
    highlight_id: str | None = None,
    action: str = "info",
) -> dict[str, Any]:
    return _safe(
        tools_story.ig_story,
        story_id=story_id,
        highlight_id=highlight_id,
        action=action,
    )


@mcp.tool(
    description="[AS-IG-MCP] Account profile, metrics, insights, and linked switcher accounts."
)
def ig_account() -> dict[str, Any]:
    return _safe(tools_account.ig_account)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
