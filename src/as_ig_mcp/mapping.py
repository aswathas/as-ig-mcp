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
) -> dict:
    entry: dict = {"method": method, "transport": transport, "summary": summary}
    if fallback:
        entry["fallback"] = fallback
    return entry


FEATURE_METHODS: dict[str, dict] = {
    # Profile and relationships
    "profile": _entry("user_info_v1", "rest", "Profile details, bio and counts for one user."),
    "followers": _entry("user_followers_v1", "rest", "Followers of a user, paginated."),
    "following": _entry("user_following_v1", "rest", "Accounts a user follows, paginated."),
    "follow": _entry("user_follow", "rest", "Follow an account."),
    "unfollow": _entry("user_unfollow", "rest", "Unfollow an account."),
    "block": _entry("user_block", "rest", "Block an account."),
    "mute": _entry("mute_posts_from_follow", "rest", "Mute posts from an account."),
    "close_friend": _entry("close_friend_add", "rest", "Add an account to close friends."),
    # Insights
    "best_posts": _entry(
        "insights_media_feed_all", "graphql", "Instagram's own ranked best posts for a window."
    ),
    "post_insights": _entry("insights_media", "graphql", "Per-post reach, impressions and engagement."),
    "account_insights": _entry("insights_account", "graphql", "Account-level insight units and growth."),
    # Stories and highlights
    "stories": _entry("user_stories_web", "graphql", "Active stories for a user."),
    "highlights": _entry("user_highlights_v1", "graphql", "Highlight trays for a user."),
    "highlight_create": _entry("highlight_create", "rest", "Create a highlight from stories."),
    "highlight_edit": _entry("highlight_edit", "rest", "Rename or re-cover a highlight."),
    # Direct messages
    "thread_list": _entry("direct_threads", "graphql", "DM threads for the account, newest first."),
    "business_dm_box": _entry(
        "direct_threads", "graphql", "Business DM box threads, including the general box."
    ),
    "thread_messages": _entry("direct_messages", "rest", "Messages inside one DM thread."),
    "dm_search": _entry("direct_message_search", "graphql", "Search message bodies across threads."),
    "presence": _entry("direct_active_presence", "rest", "Active presence for one or more threads."),
    "send_message": _entry("direct_send", "rest", "Send a text DM."),
    "send_media": _entry("direct_send_photo", "rest", "Send a photo DM."),
    "send_voice": _entry("direct_send_voice", "rest", "Send a voice-note DM."),
    "send_file": _entry("direct_send_file", "rest", "Send a file attachment in a DM."),
    "react": _entry("direct_send_reaction", "rest", "React to a DM."),
    "unsend": _entry("direct_message_unsend", "rest", "Unsend a DM."),
    # Publishing
    "publish_photo": _entry("photo_upload", "rest", "Publish a photo post."),
    "publish_video": _entry("video_upload", "rest", "Publish a video post."),
    "publish_reel": _entry("clip_upload", "rest", "Publish a reel."),
    "publish_album": _entry("album_upload", "rest", "Publish a carousel album."),
    "publish_story": _entry("photo_upload_to_story", "rest", "Publish a photo to stories."),
    "media_download": _entry("photo_download", "rest", "Download media for a post."),
    "save_media": _entry("media_save", "rest", "Save or unsave a post."),
    "crosspost": _entry(
        "media_share_to_threads_config", "graphql", "Crosspost settings to Facebook and Threads."
    ),
    # Posts and comments
    "posts": _entry(
        "user_medias_v1", "rest", "A user's posts, paginated.", fallback="user_medias_gql"
    ),
    "comments": _entry("media_comments", "rest", "Comments on a media item."),
    "comment_reply": _entry("media_comment", "rest", "Post a comment or reply."),
    "comment_bulk_delete": _entry("comment_bulk_delete", "rest", "Delete several comments at once."),
    "comment_pin": _entry("comment_pin", "rest", "Pin or unpin a comment."),
    # Discovery
    "notifications": _entry("notification_likes", "rest", "Recent likes and activity notifications."),
    "notes": _entry("get_notes", "graphql", "Inbox and on-post notes."),
    "note_create": _entry("create_note", "graphql", "Create an inbox note."),
    "hashtag_info": _entry("hashtag_info", "rest", "Hashtag metadata and follower counts."),
    "hashtag_top": _entry("hashtag_medias_top", "graphql", "Top posts for a hashtag."),
    "hashtag_recent": _entry("hashtag_medias_recent", "graphql", "Recent posts for a hashtag."),
    "hashtag_follow": _entry("hashtag_follow", "rest", "Follow or unfollow a hashtag."),
    "place_search": _entry("fbsearch_places", "graphql", "Search places by name."),
    "location_search": _entry("location_search", "rest", "Search Instagram locations."),
    "music_search": _entry("search_music", "graphql", "Search the music catalogue."),
    "top_search": _entry("fbsearch_topsearch_v2", "graphql", "Instagram's blended top search."),
    "user_search": _entry("search_users", "rest", "Search users by name or handle."),
    "suggestions": _entry("user_suggested_profiles", "rest", "Suggested accounts to follow."),
    # Account
    "profile_edit": _entry("account_edit", "rest", "Edit account profile fields."),
    "category": _entry(
        "account_convert_to_professional", "rest", "Professional account type and category."
    ),
    "ai_label": _entry("account_set_ai_info", "rest", "Set the account AI-content label."),
}


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
