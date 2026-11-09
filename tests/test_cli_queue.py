"""Offline tests for the ``python -m as_ig_mcp queue`` commands."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from as_ig_mcp import cli, queue
from as_ig_mcp.queue import Queue


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def _approve(preview):
    return True


def test_queue_list_prints_the_items(appdata, capsys):
    Queue().schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/listed.jpg",
        caption="listed post",
        dialog=_approve,
    )

    code = cli.main(["queue", "list"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert len(payload["items"]) == 1
    assert payload["items"][0]["summary"] == "listed post"
    assert payload["items"][0]["state"] == "pending"


def test_queue_tick_with_no_due_items_does_nothing_and_says_so(appdata, capsys):
    Queue().schedule_item(
        kind="photo",
        when="2030-01-02T03:04:05",
        media_path="C:/media/future.jpg",
        caption="future",
        dialog=_approve,
    )

    code = cli.main(["queue", "tick"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["published"] == []
    assert payload["possibly_published"] == []
    assert payload["message"] == "nothing due"
    assert Queue().list_items()[0]["state"] == "pending"


def test_install_task_builds_the_exact_schtasks_command():
    command = queue.build_install_task_command(
        python_exe=r"C:\project\.venv\Scripts\python.exe",
        interval_minutes=5,
    )

    assert command[:2] == ["schtasks", "/create"]
    assert command[command.index("/tn") + 1] == "AS-IG-MCP queue"
    assert command[command.index("/sc") + 1] == "minute"
    assert command[command.index("/mo") + 1] == "5"
    assert command[command.index("/tr") + 1] == (
        r'"C:\project\.venv\Scripts\python.exe" -m as_ig_mcp queue tick'
    )


def test_install_task_reports_the_command_without_running_schtasks():
    calls: list[list[str]] = []

    def runner(argv, capture_output=True, text=True):
        calls.append(argv)
        return SimpleNamespace(
            returncode=0,
            stdout="SUCCESS: The scheduled task was created.",
            stderr="",
        )

    result = queue.install_task(runner=runner)

    assert result["ok"] is True
    assert calls and calls[0][0] == "schtasks"
    assert "AS-IG-MCP queue" in result["command"]
    assert "-m as_ig_mcp queue tick" in result["command"]
    assert result["returncode"] == 0


def test_install_task_reports_a_clear_error_when_schtasks_fails():
    result = queue.install_task(
        runner=lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="Access is denied."
        )
    )

    assert result["ok"] is False
    assert result["returncode"] == 1
    assert "elevation" in result["error"]


def test_an_unknown_queue_command_is_usage_error(appdata, capsys):
    assert cli.main(["queue", "dance"]) == 2
    assert "unknown queue command" in capsys.readouterr().err
