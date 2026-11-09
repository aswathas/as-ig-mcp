"""Offline tests for turning instagrapi objects into plain data."""

from __future__ import annotations

import json
from datetime import datetime

from instagrapi.types import UserShort

from as_ig_mcp.serialize import plain, plain_list


def test_pydantic_model_becomes_a_dict():
    user = UserShort(pk="1", username="alice", full_name="Alice", is_private=False)

    result = plain(user)

    assert isinstance(result, dict)
    assert result["pk"] == "1"
    assert result["username"] == "alice"
    assert result["is_private"] is False
    json.dumps(result)


def test_datetime_becomes_isoformat():
    moment = datetime(2026, 11, 10, 12, 30, 45)

    assert plain(moment) == moment.isoformat()
    json.dumps(plain(moment))


def test_list_and_tuple_are_mapped():
    result = plain([1, datetime(2026, 1, 2, 3, 4, 5), ("a", "b")])

    assert result == [1, "2026-01-02T03:04:05", ["a", "b"]]
    json.dumps(result)


def test_dict_values_are_mapped():
    result = plain({"at": datetime(2026, 1, 2, 3, 4, 5), "ok": True})

    assert result == {"at": "2026-01-02T03:04:05", "ok": True}
    json.dumps(result)


def test_nested_structures_are_json_serialisable():
    result = plain(
        {
            "users": [UserShort(pk="1", username="alice")],
            "when": [datetime(2026, 1, 2, 3, 4, 5)],
            "deep": {"items": ({"at": datetime(2026, 5, 6, 7, 8, 9)},)},
        }
    )

    json.dumps(result)
    assert result["users"][0]["username"] == "alice"
    assert result["deep"]["items"][0]["at"] == "2026-05-06T07:08:09"


def test_plain_string_passes_through():
    assert plain("hello") == "hello"
    json.dumps(plain("hello"))


def test_plain_list_truncates_to_limit():
    assert plain_list([1, 2, 3], 2) == [1, 2]
    assert plain_list(None) == []
