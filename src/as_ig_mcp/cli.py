"""Command line entry: ``python -m as_ig_mcp <command>``."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import session, tools_health, tools_session, tools_status
from .session import settings_identity

USAGE = """usage: python -m as_ig_mcp <command>

commands:
  session import <settings.json>   validate and save a settings file
  session status                   show the session and cache state
  status                           show the ig_status report
  health                           probe every capability class
"""


def _emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _import(path_text: str) -> tuple[dict[str, Any], int]:
    path = Path(path_text)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1

    try:
        settings = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"settings is not valid JSON: {exc}"}, 1

    if not isinstance(settings, dict):
        return {"ok": False, "error": "settings must be a JSON object"}, 1

    cookies = settings.get("cookies")
    if not isinstance(cookies, dict) or not cookies.get("sessionid"):
        return {
            "ok": False,
            "error": "settings must contain a cookies object with a sessionid",
        }, 1

    try:
        session.save_session(settings)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 1

    identity = settings_identity(settings)
    return {
        "ok": True,
        "username": identity["username"],
        "user_id": identity["user_id"],
    }, 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE, file=sys.stderr)
        return 2

    command = args[0].strip().lower()

    if command == "status":
        _emit(tools_status.ig_status())
        return 0

    if command == "serve":
        from .server import main as serve_main

        serve_main()
        return 0

    if command == "health":
        _emit(tools_health.ig_health())
        return 0

    if command == "session":
        action = args[1].strip().lower() if len(args) > 1 else ""
        if action == "status":
            _emit(tools_session.ig_session("status"))
            return 0
        if action == "import":
            if len(args) < 3:
                print("usage: python -m as_ig_mcp session import <settings.json>", file=sys.stderr)
                return 2
            payload, code = _import(args[2])
            _emit(payload)
            return code

    print(f"unknown command\n\n{USAGE}", file=sys.stderr)
    return 2
