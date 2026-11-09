"""Safety net: every feature a read tool can dispatch to must be read-only."""

from __future__ import annotations

from as_ig_mcp import (
    mapping,
    tools_account,
    tools_discovery,
    tools_feed,
    tools_inbox,
    tools_insight,
    tools_people,
    tools_story,
    tools_threads,
)

READ_TOOL_FEATURES = (
    set(tools_people.FEATURES)
    | set(tools_discovery.FEATURES)
    | set(tools_feed.FEATURES)
    | set(tools_threads.FEATURES)
    | set(tools_inbox.FEATURES)
    | set(tools_insight.FEATURES)
    | set(tools_story.FEATURES)
    | set(tools_account.FEATURES)
)


def test_read_tools_declare_features():
    assert READ_TOOL_FEATURES


def test_every_read_tool_feature_exists_in_the_mapping():
    missing = sorted(READ_TOOL_FEATURES - set(mapping.FEATURE_METHODS))
    assert missing == []


def test_every_read_tool_feature_is_read_only():
    mutating = sorted(
        feature
        for feature in READ_TOOL_FEATURES
        if mapping.FEATURE_METHODS[feature]["read_only"] is not True
    )
    assert mutating == []


def test_no_read_tool_feature_maps_to_a_known_mutator():
    offending = sorted(
        feature
        for feature in READ_TOOL_FEATURES
        if mapping.FEATURE_METHODS[feature]["method"] in mapping.MUTATING_METHODS
    )
    assert offending == []
