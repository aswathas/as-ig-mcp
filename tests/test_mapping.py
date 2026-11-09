"""Offline tests for the feature -> instagrapi method table."""

from instagrapi import Client

from as_ig_mcp.mapping import FEATURES_BY_AREA, FEATURE_METHODS

REQUIRED_FEATURES = {
    "profile",
    "followers",
    "following",
    "posts",
    "best_posts",
    "post_insights",
    "account_insights",
    "stories",
    "thread_list",
    "business_dm_box",
    "thread_messages",
    "dm_search",
    "presence",
    "send_message",
    "send_media",
    "send_voice",
    "send_file",
    "react",
    "unsend",
    "publish_photo",
    "publish_video",
    "publish_reel",
    "publish_album",
    "publish_story",
    "comments",
    "comment_reply",
    "comment_bulk_delete",
    "comment_pin",
    "notifications",
    "notes",
    "note_create",
    "hashtag_info",
    "hashtag_top",
    "hashtag_recent",
    "hashtag_follow",
    "place_search",
    "location_search",
    "music_search",
    "top_search",
    "user_search",
    "suggestions",
    "highlights",
    "highlight_create",
    "highlight_edit",
    "follow",
    "unfollow",
    "block",
    "mute",
    "close_friend",
    "crosspost",
    "profile_edit",
    "category",
    "ai_label",
    "media_download",
    "save_media",
}

KNOWN_AREAS = {
    "profile",
    "dm",
    "publish",
    "comments",
    "stories",
    "discovery",
    "insights",
    "account",
    "media",
}


def test_every_required_feature_exists():
    assert REQUIRED_FEATURES <= set(FEATURE_METHODS)
    assert set(FEATURE_METHODS) == REQUIRED_FEATURES


def test_every_entry_has_method_transport_and_summary():
    for feature, entry in FEATURE_METHODS.items():
        assert isinstance(entry["method"], str) and entry["method"], feature
        assert entry["transport"] in {"rest", "graphql"}, feature
        assert isinstance(entry["summary"], str) and entry["summary"].strip(), feature


def test_every_feature_is_in_exactly_one_area():
    seen: dict[str, str] = {}
    for area, features in FEATURES_BY_AREA.items():
        assert area in KNOWN_AREAS, area
        for feature in features:
            assert feature not in seen, f"{feature} is in {seen.get(feature)} and {area}"
            seen[feature] = area
    assert set(seen) == set(FEATURE_METHODS)
    assert set(FEATURES_BY_AREA) == KNOWN_AREAS


def test_every_named_method_exists_on_the_client_class():
    for feature, entry in FEATURE_METHODS.items():
        assert hasattr(Client, entry["method"]), (feature, entry["method"])
        if entry.get("fallback"):
            assert hasattr(Client, entry["fallback"]), (feature, entry["fallback"])
