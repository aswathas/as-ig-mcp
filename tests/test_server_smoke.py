"""Smoke test: run the server as a child process and speak JSON-RPC to it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from mcp.types import LATEST_PROTOCOL_VERSION as PROTOCOL_VERSION
except Exception:  # pragma: no cover - mcp always ships this
    PROTOCOL_VERSION = "2025-06-18"

EXPECTED_TOOLS = {"ig_status", "ig_health", "ig_session"}


def _send(proc: subprocess.Popen, payload: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
    proc.stdin.flush()


def _read_message(proc: subprocess.Popen) -> dict[str, Any] | None:
    assert proc.stdout is not None
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        text = line.strip()
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue


def _read_until(proc: subprocess.Popen, wanted_id: int) -> dict[str, Any]:
    while True:
        message = _read_message(proc)
        assert message is not None, f"server closed before answering id {wanted_id}"
        if message.get("id") == wanted_id:
            return message


def _call_result_text(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for item in result.get("content", []):
        if item.get("type") == "text":
            return json.loads(item["text"])
    raise AssertionError(f"no structured result in {result!r}")


def test_server_speaks_mcp_and_reports_status(tmp_path):
    env = os.environ.copy()
    env["APPDATA"] = str(tmp_path)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src") + (
        os.pathsep + existing if existing else ""
    )
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, "-m", "as_ig_mcp.server"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    timer = threading.Timer(60, proc.kill)
    timer.start()
    try:
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "as-ig-smoke", "version": "0.0.0"},
                },
            },
        )
        initialized = _read_until(proc, 1)
        assert "result" in initialized, initialized

        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = _read_until(proc, 2)

        tools = listing["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert EXPECTED_TOOLS <= names, names

        for tool in tools:
            if tool["name"] in EXPECTED_TOOLS:
                assert tool["description"].startswith("[AS-IG-MCP]"), tool
                assert len(tool["description"]) < 400, tool

        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "ig_status", "arguments": {}},
            },
        )
        response = _read_until(proc, 3)
        status = _call_result_text(response["result"])

        assert isinstance(status, dict)
        for key in ("session", "account", "cache", "realtime", "health", "version", "quota"):
            assert key in status, (key, status)
        assert status["quota"] == "unknown - instagrapi exposes no quota endpoint"
        assert status["session"]["present"] is False
        assert status["account"] is None
    finally:
        timer.cancel()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def test_health_probe_marks_non_read_only_class_dead_and_does_not_mutate(tmp_path, monkeypatch):
    from as_ig_mcp import client, mapping, session, tools_health

    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake_settings = {
        "cookies": {
            "sessionid": "dummy_sess",
            "csrftoken": "dummy_csrf",
            "ds_user_id": "12345",
        },
        "authorization_data": {"user_id": "12345"},
    }
    session.save_session(fake_settings)

    called_methods = []

    class FakeClient:
        def __getattr__(self, name):
            def handler(**kwargs):
                called_methods.append(name)
                return {}
            return handler

    monkeypatch.setattr(client, "build_client", lambda s: FakeClient())

    orig_spec = mapping.FEATURE_METHODS["hashtag_info"]
    monkeypatch.setitem(
        mapping.FEATURE_METHODS,
        "hashtag_info",
        {**orig_spec, "read_only": False},
    )

    report = tools_health.ig_health()

    assert report["classes"]["discovery"]["status"] == "dead"
    assert report["classes"]["discovery"]["reason"] == "feature is a write"

    for method_name in called_methods:
        assert method_name not in mapping.MUTATING_METHODS
    assert "hashtag_info" not in called_methods
