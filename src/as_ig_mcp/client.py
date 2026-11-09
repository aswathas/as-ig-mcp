"""instagrapi client construction, fb_dtsg prefetch and feature dispatch."""

from __future__ import annotations

from typing import Any

from instagrapi import Client
from instagrapi.exceptions import ClientError, ClientGraphqlError, ClientJSONDecodeError

from . import mapping

DTSG_ATTRIBUTE = "_asig_dtsg"

_RETRY_ERRORS = (ClientGraphqlError, ClientJSONDecodeError, ClientError)


class DtsgError(RuntimeError):
    """Raised when Instagram does not hand out an fb_dtsg token."""


def build_client(settings: dict[str, Any]) -> Client:
    """Build a client and apply the stored session settings in place."""
    client = Client()
    client.set_settings(dict(settings))
    return client


def ensure_dtsg(client: Client) -> str:
    """Fetch fb_dtsg once per client and cache it on the object."""
    token = getattr(client, DTSG_ATTRIBUTE, None)
    if token:
        return token
    token = client.fetch_fb_dtsg()
    if not token:
        raise DtsgError(
            "Instagram returned no fb_dtsg token; the session may be expired or "
            "the homepage scrape changed. Relogin with ig_session relogin."
        )
    setattr(client, DTSG_ATTRIBUTE, token)
    return token


def call_feature(client: Any, feature: str, **kwargs: Any) -> Any:
    """Call the mapped method for a feature, retrying once on the fallback."""
    try:
        spec = mapping.FEATURE_METHODS[feature]
    except KeyError:
        raise ValueError(f"unknown feature: {feature!r}") from None

    method_name = spec["method"]
    fallback_name = spec.get("fallback")
    try:
        return getattr(client, method_name)(**kwargs)
    except _RETRY_ERRORS as primary_error:
        if not fallback_name:
            raise
        try:
            return getattr(client, fallback_name)(**kwargs)
        except _RETRY_ERRORS as fallback_error:
            raise primary_error from fallback_error
