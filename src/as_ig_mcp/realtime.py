"""Realtime socket reader and event normaliser."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Callable

from . import client, events, session

EVENT_NAMES = (
    "receive",
    "message",
    "thread_update",
    "iris",
    "direct",
    "typing",
    "seen",
    "presence",
    "send_response",
    "iris_sub_response",
    "realtime_sub",
)

BACKOFF_STEPS = (1, 2, 4, 8, 16, 32, 60)
# Instagram closes the MQTT socket quickly when idle. Keep the ping well
# under the 20 second transport keep-alive so the connection survives.
PING_INTERVAL = 5.0


def _thread_id_from_path(path: str) -> str | None:
    prefix = "/direct_v2/threads/"
    if path.startswith(prefix):
        return path[len(prefix) :].split("/", 1)[0]
    prefix = "/direct_v2/inbox/threads/"
    if path.startswith(prefix):
        return path[len(prefix) :].split("/", 1)[0]
    return None


def extract_thread_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("thread_id", "threadId"):
        if payload.get(key) is not None:
            return str(payload[key])
    msg = payload.get("message")
    if isinstance(msg, dict):
        for key in ("thread_id", "threadId"):
            if msg.get(key) is not None:
                return str(msg[key])
        path = msg.get("path")
        if path:
            tid = _thread_id_from_path(str(path))
            if tid:
                return tid
    path = payload.get("path")
    if path:
        tid = _thread_id_from_path(str(path))
        if tid:
            return tid
    return None


def classify_message_patch(payload: Any) -> tuple[bool, Any]:
    """Classify a message patch into a reaction or other value.

    Returns (is_reaction, value_payload).
    """
    if not isinstance(payload, dict):
        return False, {"raw": payload}

    target = payload.get("message") if isinstance(payload.get("message"), dict) else payload

    # 1. Explicit item_type == "reaction"
    item_type = target.get("item_type")
    if item_type == "reaction":
        reaction_info = {
            "emoji": target.get("emoji") or target.get("reaction_type") or "like",
            "reaction_type": target.get("reaction_type", "like"),
            "reaction_status": target.get("reaction_status", "created"),
            "user_id": str(target.get("user_id")) if target.get("user_id") is not None else None,
            "target_item_id": target.get("target_item_id") or target.get("item_id"),
        }
        return True, {"reaction": reaction_info}

    path = str(target.get("path") or payload.get("path") or "").lower()
    if "/reactions" in path or "/reaction" in path:
        raw_val = target.get("value") if "value" in target else target
        return True, {"reaction": raw_val}

    if "reaction" in target and target["reaction"] is not None:
        return True, {"reaction": target["reaction"]}

    if "reactions" in target and target["reactions"] is not None:
        return True, {"reaction": target["reactions"]}

    # Known message format with text
    if "text" in target:
        return False, {"text": target.get("text"), "id": target.get("id") or target.get("item_id")}

    # Unclassifiable message patch -> raw
    return False, {"raw": payload}


def jsonable(value: Any) -> Any:
    """Make a value safe to serialise as JSON.

    Instagram's realtime payload carries raw bytes in places (the socket frame
    before it is decoded, or a binary blob inside a patch). One bytes value
    used to kill the reader thread, so everything is coerced here: bytes are
    decoded as UTF-8 with replacement, and anything else unknown becomes its
    string form.
    """
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def normalize_event(event_name: str, payload: Any) -> dict[str, Any]:
    """Normalise an event to {"ts": epoch, "event": name, "thread_id": str|None, "value": any}."""
    tid = extract_thread_id(payload)
    if event_name == "message":
        _, val = classify_message_patch(payload)
    else:
        val = payload

    return {
        "ts": time.time(),
        "event": str(event_name),
        "thread_id": tid,
        "value": jsonable(val),
    }


class RealtimeManager:
    """Manages the background realtime socket connection and event ingest."""

    def __init__(self) -> None:
        self.rt: Any = None
        self._enabled: bool = True
        self._connected: bool = False
        self._connected_at: float | None = None
        self._last_event_at: float | None = None
        self._last_error: str | None = None
        self._subscribe_state: Any = None
        self._event_count: int = 0

        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None
        self._ping_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _do_subscribe(self) -> Any:
        if hasattr(self.rt, "direct_subscribe"):
            return self.rt.direct_subscribe()
        if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "direct_subscribe"):
            return self.rt.realtime.direct_subscribe()
        return None

    def _do_connect(self) -> Any:
        if hasattr(self.rt, "realtime_connect"):
            return self.rt.realtime_connect()
        if hasattr(self.rt, "connect"):
            return self.rt.connect()
        if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "connect"):
            return self.rt.realtime.connect()
        return None

    def _do_disconnect(self) -> Any:
        if hasattr(self.rt, "realtime_disconnect"):
            return self.rt.realtime_disconnect()
        if hasattr(self.rt, "disconnect"):
            return self.rt.disconnect()
        if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "disconnect"):
            return self.rt.realtime.disconnect()
        return None

    def _do_read_once(self) -> Any:
        if hasattr(self.rt, "realtime_read_once"):
            return self.rt.realtime_read_once()
        if hasattr(self.rt, "read_once"):
            return self.rt.read_once()
        if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "read_once"):
            return self.rt.realtime.read_once()
        return None

    def _do_ping(self) -> Any:
        if hasattr(self.rt, "realtime_ping"):
            return self.rt.realtime_ping()
        if hasattr(self.rt, "ping"):
            return self.rt.ping()
        if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "ping"):
            return self.rt.realtime.ping()
        return None

    def _on_event(self, event_name: str, payload: Any) -> None:
        normalized = normalize_event(event_name, payload)
        with self._lock:
            self._last_event_at = normalized["ts"]
            self._event_count += 1
        events.append(normalized)

    def _setup_handlers(self) -> None:
        for ev in EVENT_NAMES:
            cb = (lambda name: lambda data: self._on_event(name, data))(ev)
            if hasattr(self.rt, "realtime_on"):
                self.rt.realtime_on(ev, cb)
            elif hasattr(self.rt, "on"):
                self.rt.on(ev, cb)
            if hasattr(self.rt, "realtime") and hasattr(self.rt.realtime, "on"):
                self.rt.realtime.on(ev, cb)

    def start(
        self,
        settings: dict[str, Any] | None = None,
        client_instance: Any = None,
    ) -> None:
        """Start the realtime manager.

        Builds its own client from settings (or uses client_instance),
        calls direct_subscribe() once on the calling thread,
        and starts daemon reader and ping threads.
        """
        if os.environ.get("AS_IG_REALTIME", "1") == "0":
            self._enabled = False
            return

        self._enabled = True
        self._stop_event.clear()

        if client_instance is not None:
            self.rt = client_instance
        else:
            loaded_settings = settings or session.load_session()
            if not loaded_settings:
                self._last_error = "no session settings"
                return
            self.rt = client.build_client(loaded_settings)

        self._setup_handlers()

        # Connect if needed
        try:
            self._do_connect()
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"

        # Call direct_subscribe() ONCE on calling thread before reader starts
        try:
            self._subscribe_state = self._do_subscribe()
            self._connected = True
            self._connected_at = time.time()
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            self._connected = False

        # Start daemon threads
        self._reader_thread = threading.Thread(
            target=self._reader_loop, name="as-ig-realtime-reader", daemon=True
        )
        self._reader_thread.start()

        self._ping_thread = threading.Thread(
            target=self._ping_loop, name="as-ig-realtime-ping", daemon=True
        )
        self._ping_thread.start()

    def _reader_loop(self) -> None:
        backoff_idx = 0
        while not self._stop_event.is_set():
            try:
                res = self._do_read_once()
                backoff_idx = 0
                if res is not None:
                    # If read_once returned an event dict directly rather than via handlers
                    if isinstance(res, dict) and "event" in res and "ts" not in res:
                        self._on_event(res.get("event", "message"), res.get("payload", res))
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self._last_error = f"{type(exc).__name__}: {exc}"
                self._connected = False
                delay = BACKOFF_STEPS[min(backoff_idx, len(BACKOFF_STEPS) - 1)]
                backoff_idx += 1
                if self._stop_event.wait(delay):
                    break
                try:
                    self._do_connect()
                    self._subscribe_state = self._do_subscribe()
                    self._connected = True
                    self._connected_at = time.time()
                except Exception as conn_exc:
                    self._last_error = f"{type(conn_exc).__name__}: {conn_exc}"

    def _ping_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._stop_event.wait(PING_INTERVAL):
                break
            if self._connected:
                try:
                    self._do_ping()
                except Exception as exc:
                    self._last_error = f"ping error: {exc}"

    def status(self) -> dict[str, Any]:
        """Return connected or not, connected_at, last_event_at, last_error, subscribe_state, event_count."""
        return {
            "enabled": self._enabled,
            "connected": self._connected,
            "connected_at": self._connected_at,
            "last_event_at": self._last_event_at,
            "last_error": self._last_error,
            "subscribe_state": self._subscribe_state,
            "event_count": self._event_count,
        }

    def stop(self) -> None:
        """Close the socket and join the reader and ping threads."""
        self._stop_event.set()
        try:
            self._do_disconnect()
        except Exception:
            pass
        self._connected = False
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        if self._ping_thread and self._ping_thread.is_alive():
            self._ping_thread.join(timeout=1.0)


_GLOBAL_MANAGER: RealtimeManager | None = None


def get_manager() -> RealtimeManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = RealtimeManager()
    return _GLOBAL_MANAGER


def start(
    settings: dict[str, Any] | None = None,
    client_instance: Any = None,
) -> RealtimeManager:
    manager = get_manager()
    manager.start(settings=settings, client_instance=client_instance)
    return manager


def stop() -> None:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is not None:
        _GLOBAL_MANAGER.stop()


def worker_status() -> dict[str, Any]:
    """The realtime worker's state, read from the file it writes.

    The socket lives in its own process, so the server never touches it; it
    reads this file instead.
    """
    from . import state

    try:
        payload = json.loads(state.realtime_status_path().read_text(encoding="utf-8"))
    except Exception:
        return {
            "enabled": os.environ.get("AS_IG_REALTIME", "1") != "0",
            "running": False,
            "connected": False,
            "last_error": "the realtime worker has not reported yet",
        }
    payload.setdefault("enabled", os.environ.get("AS_IG_REALTIME", "1") != "0")
    return payload


def status() -> dict[str, Any]:
    if _GLOBAL_MANAGER is None:
        return {
            "enabled": os.environ.get("AS_IG_REALTIME", "1") != "0",
            "connected": False,
            "connected_at": None,
            "last_event_at": None,
            "last_error": None,
            "subscribe_state": None,
            "event_count": 0,
        }
    return _GLOBAL_MANAGER.status()
