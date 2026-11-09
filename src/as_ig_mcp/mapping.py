"""The canonical instagrapi method per feature.

This is the single table to edit when Instagram moves an endpoint. Every
feature names one method, an optional fallback, its transport and a one-line
summary of what it does.
"""

from __future__ import annotations


def _entry(
    method: str,
    transport: str,
    summary: str,
    fallback: str | None = None,
    read_only: bool = True,
) -> dict:
    entry: dict = {
        "method": method,
        "transport": transport,
        "summary": summary,
        "read_only": read_only,
    }
    if fallback:
        entry["fallback"] = fallback
    return entry


MUTATING_METHODS: frozenset[str] = frozenset(
    """
    user_follow user_unfollow user_block user_unblock user_report user_remove_follower
    mute_posts_from_follow mute_stories_from_follow
    close_friend_add close_friend_remove
    hashtag_follow hashtag_unfollow
    direct_send direct_send_photo direct_send_video direct_send_voice direct_send_file
    direct_send_reaction direct_delete_reaction direct_message_delete direct_message_unsend
    direct_message_seen direct_send_seen direct_indicate_activity
    direct_thread_create direct_thread_add_users direct_thread_remove_users
    direct_thread_update_title direct_thread_hide direct_thread_mute direct_thread_unmute
    direct_thread_mark_unread direct_thread_mark_read direct_thread_mute_video_call
    direct_thread_unmute_video_call direct_pending_approve direct_request_approve
    photo_upload photo_configure video_upload video_configure clip_upload clip_configure
    album_upload album_configure igtv_upload igtv_configure
    photo_upload_to_story photo_upload_to_story_with_music video_upload_to_story
    photo_upload_to_cutout_sticker video_upload_to_cutout_sticker
    photo_configure_to_story photo_configure_to_cutout_sticker
    media_comment comment_like comment_unlike comment_pin comment_unpin
    comment_bulk_delete media_note_create media_note_delete create_note delete_note
    highlight_create highlight_edit highlight_change_title highlight_change_cover
    highlight_add_stories highlight_remove_stories highlight_delete
    account_edit account_set_biography account_set_private account_set_public
    account_change_picture account_set_ai_info account_convert_to_professional
    account_convert_to_business account_convert_to_creator
    set_external_url remove_bio_links media_save media_unsave
    notification_settings notification_likes notification_comments notification_new_follower
    notification_user_tagged notification_disable notification_mute_all
    media_share_to_threads_config media_share_to_fb_unified_config
    """.split()
)


FEATURE_METHODS: dict[str, dict] = {
    # Profile and relationships
    "profile": _entry("user_info_v1", "rest", "Profile details, bio and counts for one user."),
    "followers": _entry("user_followers_v1", "rest", "Followers of a user, paginated."),
    "following": _entry("user_following_v1", "rest", "Accounts a user follows, paginated."),
    "follow": _entry("user_follow", "rest", "Follow an account.", read_only=False),
    "unfollow": _entry("user_unfollow", "rest", "Unfollow an account.", read_only=False),
    "block": _entry("user_block", "rest", "Block an account.", read_only=False),
    "mute": _entry("mute_posts_from_follow", "rest", "Mute posts from an account.", read_only=False),
    "close_friend": _entry("close_friend_add", "rest", "Add an account to close friends.", read_only=False),
    # Insights
    "best_posts": _entry(
        "insights_media_feed_all", "graphql", "Instagram's own ranked best posts for a window."
    ),
    "post_insights": _entry("insights_media", "graphql", "Per-post reach, impressions and engagement."),
    "account_insights": _entry("insights_account", "graphql", "Account-level insight units and growth."),
    # Stories and highlights
    "stories": _entry("user_stories_web", "graphql", "Active stories for a user."),
    "highlights": _entry("user_highlights_v1", "graphql", "Highlight trays for a user."),
    "highlight_create": _entry("highlight_create", "rest", "Create a highlight from stories.", read_only=False),
    "highlight_edit": _entry("highlight_edit", "rest", "Rename or re-cover a highlight.", read_only=False),
    # Direct messages
    "thread_list": _entry("direct_threads", "graphql", "DM threads for the account, newest first."),
    "business_dm_box": _entry(
        "direct_threads", "graphql", "Business DM box threads, including the general box."
    ),
    "thread_messages": _entry("direct_messages", "rest", "Messages inside one DM thread."),
    "dm_search": _entry("direct_message_search", "graphql", "Search message bodies across threads."),
    "presence": _entry("direct_active_presence", "rest", "Active presence for one or more threads."),
    "send_message": _entry("direct_send", "rest", "Send a text DM.", read_only=False),
    "send_media": _entry("direct_send_photo", "rest", "Send a photo DM.", read_only=False),
    "send_voice": _entry("direct_send_voice", "rest", "Send a voice-note DM.", read_only=False),
    "send_file": _entry("direct_send_file", "rest", "Send a file attachment in a DM.", read_only=False),
    "react": _entry("direct_send_reaction", "rest", "React to a DM.", read_only=False),
    "unsend": _entry("direct_message_unsend", "rest", "Unsend a DM.", read_only=False),
    # Publishing
    "publish_photo": _entry("photo_upload", "rest", "Publish a photo post.", read_only=False),
    "publish_video": _entry("video_upload", "rest", "Publish a video post.", read_only=False),
    "publish_reel": _entry("clip_upload", "rest", "Publish a reel.", read_only=False),
    "publish_album": _entry("album_upload", "rest", "Publish a carousel album.", read_only=False),
    "publish_story": _entry("photo_upload_to_story", "rest", "Publish a photo to stories.", read_only=False),
    "media_download": _entry("photo_download", "rest", "Download media for a post."),
    "save_media": _entry("media_save", "rest", "Save or unsave a post.", read_only=False),
    "crosspost": _entry(
        "media_share_to_threads_config", "graphql", "Crosspost settings to Facebook and Threads.", read_only=False
    ),
    # Posts and comments
    "posts": _entry(
        "user_medias_v1", "rest", "A user's posts, paginated.", fallback="user_medias_gql"
    ),
    "comments": _entry("media_comments", "rest", "Comments on a media item."),
    "comment_reply": _entry("media_comment", "rest", "Post a comment or reply.", read_only=False),
    "comment_bulk_delete": _entry("comment_bulk_delete", "rest", "Delete several comments at once.", read_only=False),
    "comment_pin": _entry("comment_pin", "rest", "Pin or unpin a comment.", read_only=False),
    # Discovery
    "notifications": _entry(
        "news_inbox_v1", "rest", "Activity feed (old and new stories).", read_only=True
    ),
    "notes": _entry("get_notes", "graphql", "Inbox and on-post notes."),
    "note_create": _entry("create_note", "graphql", "Create an inbox note.", read_only=False),
    "hashtag_info": _entry("hashtag_info", "rest", "Hashtag metadata and follower counts."),
    "hashtag_top": _entry("hashtag_medias_top", "graphql", "Top posts for a hashtag."),
    "hashtag_recent": _entry("hashtag_medias_recent", "graphql", "Recent posts for a hashtag."),
    "hashtag_follow": _entry("hashtag_follow", "rest", "Follow or unfollow a hashtag.", read_only=False),
    "place_search": _entry("fbsearch_places", "graphql", "Search places by name."),
    "location_search": _entry("location_search", "rest", "Search Instagram locations."),
    "music_search": _entry("search_music", "graphql", "Search the music catalogue."),
    "top_search": _entry("fbsearch_topsearch_v2", "graphql", "Instagram's blended top search."),
    "user_search": _entry("search_users", "rest", "Search users by name or handle."),
    "suggestions": _entry("user_suggested_profiles", "rest", "Suggested accounts to follow."),
    # Account
    "profile_edit": _entry("account_edit", "rest", "Edit account profile fields.", read_only=False),
    "category": _entry(
        "account_convert_to_professional", "rest", "Professional account type and category.", read_only=False
    ),
    "ai_label": _entry("account_set_ai_info", "rest", "Set the account AI-content label.", read_only=False),
}


MUTATING_FEATURES: frozenset[str] = frozenset(
    feature
    for feature, spec in FEATURE_METHODS.items()
    if spec["method"] in MUTATING_METHODS
)


FEATURES_BY_AREA: dict[str, list[str]] = {
    "profile": [
        "profile",
        "followers",
        "following",
        "follow",
        "unfollow",
        "block",
        "mute",
        "close_friend",
    ],
    "dm": [
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
    ],
    "publish": [
        "publish_photo",
        "publish_video",
        "publish_reel",
        "publish_album",
        "publish_story",
        "crosspost",
    ],
    "comments": [
        "comments",
        "comment_reply",
        "comment_bulk_delete",
        "comment_pin",
    ],
    "stories": [
        "stories",
        "highlights",
        "highlight_create",
        "highlight_edit",
    ],
    "discovery": [
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
    ],
    "insights": [
        "best_posts",
        "post_insights",
        "account_insights",
    ],
    "account": [
        "profile_edit",
        "category",
        "ai_label",
    ],
    "media": [
        "posts",
        "media_download",
        "save_media",
    ],
}
