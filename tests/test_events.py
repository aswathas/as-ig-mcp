"""Offline tests for realtime events append, count, and tail."""

from __future__ import annotations

import json
import threading
import time

import pytest

from as_ig_mcp import events, state


@pytest.fixture
def clean_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_append_then_tail_returns_events_in_order(clean_appdata):
    ev1 = {"ts": 1000.0, "event": "message", "thread_id": "t1", "value": {"text": "hello"}}
    ev2 = {"ts": 1001.0, "event": "typing", "thread_id": "t1", "value": True}
    ev3 = {"ts": 1002.0, "event": "seen", "thread_id": "t1", "value": True}

    events.append(ev1)
    events.append(ev2)
    events.append(ev3)

    assert events.count() == 3

    results = events.tail(offset=0)
    assert len(results) == 3
    assert results[0] == ev1
    assert results[1] == ev2
    assert results[2] == ev3


def test_tail_with_a_cursor_returns_only_the_newer_ones(clean_appdata):
    ev1 = {"ts": 1000.0, "event": "message", "thread_id": "t1", "value": "1"}
    ev2 = {"ts": 1001.0, "event": "message", "thread_id": "t1", "value": "2"}
    ev3 = {"ts": 1002.0, "event": "message", "thread_id": "t1", "value": "3"}

    events.append(ev1)
    events.append(ev2)
    events.append(ev3)

    newer = events.tail(offset=2)
    assert len(newer) == 1
    assert newer[0] == ev3

    empty = events.tail(offset=3)
    assert empty == []


def test_filtering_by_kind_works(clean_appdata):
    ev1 = {"ts": 1000.0, "event": "message", "thread_id": "t1", "value": "1"}
    ev2 = {"ts": 1001.0, "event": "typing", "thread_id": "t1", "value": True}
    ev3 = {"ts": 1002.0, "event": "presence", "thread_id": None, "value": {}}
    ev4 = {"ts": 1003.0, "event": "message", "thread_id": "t2", "value": "2"}

    events.append(ev1)
    events.append(ev2)
    events.append(ev3)
    events.append(ev4)

    messages_only = events.tail(offset=0, kinds=["message"])
    assert len(messages_only) == 2
    assert messages_only[0]["value"] == "1"
    assert messages_only[1]["value"] == "2"

    typing_and_presence = events.tail(offset=0, kinds=["typing", "presence"])
    assert len(typing_and_presence) == 2
    assert [x["event"] for x in typing_and_presence] == ["typing", "presence"]


def test_tail_with_a_timeout_returns_what_arrived_and_then_gives_up(clean_appdata):
    # When no events arrive, tail times out quickly
    t0 = time.time()
    res = events.tail(offset=0, timeout_s=0.1)
    elapsed = time.time() - t0
    assert res == []
    assert elapsed >= 0.08

    # When an event arrives mid-wait, it returns that event
    ev = {"ts": 2000.0, "event": "message", "thread_id": "t1", "value": "arrived"}

    def delayed_append():
        time.sleep(0.05)
        events.append(ev)

    thread = threading.Thread(target=delayed_append)
    thread.start()

    t0 = time.time()
    arrived = events.tail(offset=0, timeout_s=0.5)
    thread.join()

    assert len(arrived) == 1
    assert arrived[0] == ev
    assert time.time() - t0 < 0.4


def test_the_file_holds_one_json_object_per_line(clean_appdata):
    ev1 = {"ts": 10.0, "event": "msg", "thread_id": "1", "value": "a"}
    ev2 = {"ts": 20.0, "event": "msg", "thread_id": "2", "value": "b"}

    events.append(ev1)
    events.append(ev2)

    raw_lines = state.events_path().read_text(encoding="utf-8").strip().splitlines()
    assert len(raw_lines) == 2
    for line in raw_lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)
        assert "event" in parsed
