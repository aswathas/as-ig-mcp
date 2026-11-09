"""Offline tests for the feature -> instagrapi method table."""

from instagrapi import Client

from as_ig_mcp.mapping import (
    FEATURES_BY_AREA,
    FEATURE_METHODS,
    MUTATING_FEATURES,
    MUTATING_METHODS,
)

REQUIRED_FEATURES = {
    "profile",
    "user_by_username",
    "about",
    "guides",
    "followers",
    "following",
    "followers_page",
    "following_page",
    "requests_page",
    "posts",
    "posts_page",
    "reels",
    "reels_page",
    "tagged",
    "tagged_page",
    "saved_collections",
    "saved_media",
    "liked",
    "archived",
    "best_posts",
    "post_insights",
    "account_insights",
    "stories",
    "story_info",
    "story_viewers",
    "story_likers",
    "story_download",
    "highlight_info",
    "thread_list",
    "business_dm_box",
    "thread_detail",
    "thread_messages",
    "pending_requests",
    "spam_inbox",
    "dm_search",
    "presence",
    "users_presence",
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
    "account_info",
    "linked_accounts",
    "account_family",
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


def test_every_entry_has_read_only_boolean():
    for feature, entry in FEATURE_METHODS.items():
        assert "read_only" in entry, feature
        assert isinstance(entry["read_only"], bool), feature


def test_mutating_features_matches_entries_whose_method_is_in_mutator_list():
    expected = {
        feature
        for feature, entry in FEATURE_METHODS.items()
        if entry["method"] in MUTATING_METHODS
    }
    assert MUTATING_FEATURES == expected
    assert set(MUTATING_FEATURES) == {
        feature
        for feature, entry in FEATURE_METHODS.items()
        if not entry["read_only"]
    }


def test_notifications_feature_maps_to_news_inbox_v1_and_is_read_only():
    entry = FEATURE_METHODS["notifications"]
    assert entry["method"] == "news_inbox_v1"
    assert entry["transport"] == "rest"
    assert entry["read_only"] is True
    assert "activity feed" in entry["summary"].lower()


def test_no_read_only_feature_maps_to_a_method_from_the_mutator_list():
    for feature, entry in FEATURE_METHODS.items():
        if entry["read_only"]:
            assert entry["method"] not in MUTATING_METHODS, (feature, entry["method"])
            if entry.get("fallback"):
                assert entry["fallback"] not in MUTATING_METHODS, (feature, entry["fallback"])

