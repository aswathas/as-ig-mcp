"""stdio MCP server exposing the AS-IG-MCP tool surface."""

from __future__ import annotations

import os
import time
from typing import Any, Callable

try:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
except ModuleNotFoundError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer as _Server

from mcp.types import ToolAnnotations

from . import (
    realtime,
    tools_account,
    tools_digest,
    tools_discovery,
    tools_feed,
    tools_health,
    tools_inbox,
    tools_insight,
    tools_people,
    tools_preset,
    tools_queue,
    tools_session,
    tools_status,
    tools_story,
    tools_threads,
    tools_write,
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
def ig_search(
    kind: str = "user",
    query: str = "",
    limit: int = 20,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    return _safe(
        tools_discovery.ig_search,
        kind=kind,
        query=query,
        limit=limit,
        lat=lat,
        lng=lng,
    )


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
    media_id: str | None = None,
) -> dict[str, Any]:
    return _safe(
        tools_feed.ig_feed,
        kind=kind,
        username=username,
        user_id=user_id,
        cursor=cursor,
        limit=limit,
        include=include,
        media_id=media_id,
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
    box: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    return _safe(
        tools_inbox.ig_inbox,
        hours=hours,
        limit=limit,
        suggest=suggest,
        thread_id=thread_id,
        box=box,
        kind=kind,
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


@mcp.tool(
    description="[AS-IG-MCP] Insights: one media post, account units, Instagram's best ranking, best posting time, age-matched comparison, or demographics."
)
def ig_insight(
    kind: str = "media",
    media_pk: str | None = None,
    username: str | None = None,
    user_id: str | None = None,
    time_frame: str = "ONE_WEEK",
    order_by: str = "REACH_COUNT",
    limit: int = 10,
) -> dict[str, Any]:
    return _safe(
        tools_insight.ig_insight,
        kind=kind,
        media_pk=media_pk,
        username=username,
        user_id=user_id,
        time_frame=time_frame,
        order_by=order_by,
        limit=limit,
    )


@mcp.tool(
    description=tools_write.IG_WRITE_DESCRIPTION,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
    meta={"anthropic/requiresUserInteraction": True},
)
def ig_write(
    kind: str,
    idempotency_key: str | None = None,
    **args: Any,
) -> dict[str, Any]:
    return _safe(
        tools_write.ig_write,
        kind=kind,
        idempotency_key=idempotency_key,
        **args,
    )


@mcp.tool(
    description="[AS-IG-MCP] List, schedule, cancel or natively schedule queued posts; recurrences included."
)
def ig_queue(
    action: str = "list",
    kind: str | None = None,
    when: str | None = None,
    text: str | None = None,
    media_path: str | None = None,
    caption: str | None = None,
    schedule_at: str | None = None,
    recurrence: str | None = None,
    item_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    return _safe(
        tools_queue.ig_queue,
        action=action,
        kind=kind,
        when=when,
        text=text,
        media_path=media_path,
        caption=caption,
        schedule_at=schedule_at,
        recurrence=recurrence,
        item_id=item_id,
        idempotency_key=idempotency_key,
    )


@mcp.tool(
    description="[AS-IG-MCP] List, get, save or delete caption, hashtag, first-comment and DM-reply presets."
)
def ig_preset(
    action: str = "list",
    name: str | None = None,
    content: str | None = None,
    kind: str = "caption",
) -> dict[str, Any]:
    return _safe(
        tools_preset.ig_preset,
        action=action,
        name=name,
        content=content,
        kind=kind,
    )


@mcp.tool(
    description="[AS-IG-MCP] Delta digest: what changed since last call (messages, followers, posts, stories, events)."
)
def ig_digest(
    since: str = "last",
    timeout_s: float = 0.0,
    kinds: list[str] | None = None,
) -> dict[str, Any]:
    return _safe(tools_digest.ig_digest, since=since, timeout_s=timeout_s, kinds=kinds)


def _start_realtime_worker() -> Any:
    """Run the realtime socket in its own process.

    The socket is Instagram's private transport and has been observed to drop
    and even to segfault the interpreter. Kept beside the server, a broken
    socket cannot take the server down; the supervisor restarts it and
    Instagram's own sequence id means no message is lost across a restart.
    """
    import subprocess
    import sys
    import threading

    def _spawn() -> Any:
        return subprocess.Popen(
            [sys.executable, "-m", "as_ig_mcp", "realtime_worker"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    try:
        proc = _spawn()
    except Exception:
        return None

    def _supervise(proc: Any) -> None:
        while True:
            try:
                proc.wait()
            except Exception:
                return
            time.sleep(5.0)
            try:
                proc = _spawn()
            except Exception:
                return

    threading.Thread(target=_supervise, args=(proc,), daemon=True).start()
    return proc


def main() -> None:
    worker = None
    if os.environ.get("AS_IG_REALTIME", "1") != "0":
        worker = _start_realtime_worker()
    try:
        mcp.run()
    finally:
        if worker is not None:
            try:
                worker.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
