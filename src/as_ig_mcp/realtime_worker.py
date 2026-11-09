"""Runs the Instagram realtime socket in its own process.

The socket is Instagram's private transport. It drops, it throws, and it has
been observed to segfault the interpreter while tearing down. Running it
beside the MCP server instead of inside it means a broken socket can never
take the server down.

The two halves talk through files, not pipes: the worker appends every event
to `events.jsonl` and writes its state to `realtime_status.json`; the server
tails the first and reads the second. If the worker dies, the server restarts
it, and Instagram's own sequence id means nothing is missed across a restart.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from typing import Any

from . import realtime, session, state

STATUS_EVERY_SECONDS = 5.0


def _write_status(payload: dict[str, Any]) -> None:
    target = state.realtime_status_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        pass


def main() -> int:
    stopping = threading.Event()

    def _stop(_signum: int, _frame: Any) -> None:
        stopping.set()

    try:
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
    except Exception:
        pass

    try:
        settings = session.load_session()
    except Exception as exc:
        _write_status({"running": False, "last_error": f"{type(exc).__name__}: {exc}"})
        print(f"[realtime-worker] cannot read the session: {exc}", file=sys.stderr)
        return 1
    if not settings:
        _write_status({"running": False, "last_error": "no session"})
        print("[realtime-worker] no session; run: python -m as_ig_mcp session login", file=sys.stderr)
        return 1

    manager = realtime.RealtimeManager()
    manager.start(settings)
    _write_status({"running": True, "started_at": time.time(), **manager.status()})

    def _status_loop() -> None:
        while not stopping.wait(STATUS_EVERY_SECONDS):
            try:
                _write_status({"running": True, **manager.status()})
            except Exception:
                pass

    watcher = threading.Thread(target=_status_loop, daemon=True)
    watcher.start()

    try:
        while not stopping.is_set():
            stopping.wait(1.0)
    finally:
        try:
            manager.stop()
        except Exception:
            pass
        _write_status({"running": False, "stopped_at": time.time(), **manager.status()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
