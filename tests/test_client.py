"""Offline tests for client dispatch and fb_dtsg caching."""

from types import SimpleNamespace

import pytest
from instagrapi.exceptions import ClientError, ClientGraphqlError, ClientJSONDecodeError

from as_ig_mcp import client, mapping


def test_call_feature_dispatches_to_the_mapped_method():
    seen = []

    def user_medias_v1(**kwargs):
        seen.append(kwargs)
        return ["post"]

    fake = SimpleNamespace(
        user_medias_v1=user_medias_v1,
        user_medias_gql=lambda **kwargs: [],
    )

    assert client.call_feature(fake, "posts", amount=1) == ["post"]
    assert seen == [{"amount": 1}]


def test_fallback_is_used_when_the_primary_raises_client_error():
    def primary(**kwargs):
        raise ClientError("primary failed")

    fake = SimpleNamespace(
        user_medias_v1=primary,
        user_medias_gql=lambda **kwargs: ["from-fallback"],
    )

    assert client.call_feature(fake, "posts") == ["from-fallback"]


def test_original_error_type_is_reraised_when_primary_and_fallback_fail():
    def primary(**kwargs):
        raise ClientGraphqlError("primary failed")

    def fallback(**kwargs):
        raise ClientJSONDecodeError("fallback failed")

    fake = SimpleNamespace(user_medias_v1=primary, user_medias_gql=fallback)

    with pytest.raises(ClientGraphqlError):
        client.call_feature(fake, "posts")


def test_ensure_dtsg_caches_the_token_and_fetches_once():
    calls = {"count": 0}

    def fetch_fb_dtsg():
        calls["count"] += 1
        return "TOKEN"

    fake = SimpleNamespace(fetch_fb_dtsg=fetch_fb_dtsg)

    assert client.ensure_dtsg(fake) == "TOKEN"
    assert client.ensure_dtsg(fake) == "TOKEN"
    assert calls["count"] == 1


def test_calling_read_only_feature_works():
    seen = []

    def user_info_v1(**kwargs):
        seen.append(kwargs)
        return {"pk": "123"}

    fake = SimpleNamespace(user_info_v1=user_info_v1)
    res = client.call_feature(fake, "profile", user_id="123")
    assert res == {"pk": "123"}
    assert seen == [{"user_id": "123"}]


def test_calling_mutating_feature_without_allow_write_raises_and_never_calls():
    calls = []

    def record_call(name):
        def _fn(**kwargs):
            calls.append((name, kwargs))
            return True
        return _fn

    fake = SimpleNamespace(
        user_follow=record_call("user_follow"),
        direct_send=record_call("direct_send"),
    )

    with pytest.raises(client.WriteNotAllowedError) as exc_info:
        client.call_feature(fake, "follow", user_id="123")

    assert "follow" in str(exc_info.value)
    assert "user_follow" in str(exc_info.value)
    assert len(calls) == 0


def test_call_write_does_not_use_the_fallback_when_the_primary_raises(monkeypatch):
    calls = []

    def primary(**kwargs):
        calls.append(("primary", kwargs))
        raise ClientError("primary failed")

    def fallback(**kwargs):
        calls.append(("fallback", kwargs))
        return "from-fallback"

    fake = SimpleNamespace(primary=primary, fallback_method=fallback)
    monkeypatch.setitem(
        mapping.FEATURE_METHODS,
        "write_with_fallback",
        {
            "method": "primary",
            "transport": "rest",
            "summary": "A write with a fallback",
            "fallback": "fallback_method",
            "read_only": False,
        },
    )

    with pytest.raises(ClientError):
        client.call_write(fake, "write_with_fallback", user_id="1")

    assert calls == [("primary", {"user_id": "1"})]


def test_call_feature_with_allow_write_on_a_write_does_not_use_the_fallback(monkeypatch):
    calls = []

    def primary(**kwargs):
        calls.append("primary")
        raise ClientError("primary failed")

    def fallback(**kwargs):
        calls.append("fallback")
        return "from-fallback"

    fake = SimpleNamespace(primary=primary, fallback_method=fallback)
    monkeypatch.setitem(
        mapping.FEATURE_METHODS,
        "write_with_fallback",
        {
            "method": "primary",
            "transport": "rest",
            "summary": "A write with a fallback",
            "fallback": "fallback_method",
            "read_only": False,
        },
    )

    with pytest.raises(ClientError):
        client.call_feature(fake, "write_with_fallback", allow_write=True)

    assert calls == ["primary"]


def test_call_write_on_mutating_feature_does_call_it():
    calls = []

    def user_follow(**kwargs):
        calls.append(kwargs)
        return True

    fake = SimpleNamespace(user_follow=user_follow)
    res = client.call_write(fake, "follow", user_id="456")
    assert res is True
    assert calls == [{"user_id": "456"}]


def test_mutating_feature_with_fallback_still_refuses_without_allow_write(monkeypatch):
    calls = []

    fake = SimpleNamespace(
        primary_mutator=lambda **kw: calls.append("primary"),
        fallback_mutator=lambda **kw: calls.append("fallback"),
    )

    fake_spec = {
        "method": "primary_mutator",
        "transport": "rest",
        "summary": "Mutator with fallback",
        "fallback": "fallback_mutator",
        "read_only": False,
    }
    from as_ig_mcp import mapping
    monkeypatch.setitem(mapping.FEATURE_METHODS, "mutating_test_feature", fake_spec)

    with pytest.raises(client.WriteNotAllowedError) as exc_info:
        client.call_feature(fake, "mutating_test_feature")

    assert "mutating_test_feature" in str(exc_info.value)
    assert "primary_mutator" in str(exc_info.value)
    assert calls == []


def test_read_only_feature_with_mutating_fallback_refuses_fallback_without_allow_write(monkeypatch):
    calls = []

    def primary(**kwargs):
        calls.append("primary")
        raise ClientError("primary failed")

    def fallback(**kwargs):
        calls.append("fallback")
        return True

    fake = SimpleNamespace(primary_reader=primary, fallback_mutator=fallback)

    fake_spec = {
        "method": "primary_reader",
        "transport": "rest",
        "summary": "Reader with mutating fallback",
        "fallback": "fallback_mutator",
        "read_only": True,
    }
    from as_ig_mcp import mapping
    monkeypatch.setitem(mapping.FEATURE_METHODS, "reader_test_feature", fake_spec)
    monkeypatch.setattr(
        mapping,
        "MUTATING_METHODS",
        mapping.MUTATING_METHODS | frozenset({"fallback_mutator"}),
    )

    with pytest.raises(client.WriteNotAllowedError) as exc_info:
        client.call_feature(fake, "reader_test_feature")

    assert "fallback_mutator" in str(exc_info.value)
    assert calls == ["primary"]
