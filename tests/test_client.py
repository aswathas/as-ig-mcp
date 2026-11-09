"""Offline tests for client dispatch and fb_dtsg caching."""

from types import SimpleNamespace

import pytest
from instagrapi.exceptions import ClientError, ClientGraphqlError, ClientJSONDecodeError

from as_ig_mcp import client


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
