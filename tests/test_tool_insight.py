"""Offline tests for ig_insight with a fake Instagram client."""

from __future__ import annotations

from typing import Any

from as_ig_mcp import client, session, tools_insight


class FakeClient:
    """Records the instagrapi method names the tool calls."""

    def __init__(self, results: dict[str, Any]) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.results = results

    def __getattr__(self, name: str):
        def handler(**kwargs):
            self.calls.append((name, kwargs))
            value = self.results.get(name)
            if isinstance(value, Exception):
                raise value
            if callable(value):
                return value(**kwargs)
            return value

        return handler

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def kwargs_for(self, name: str) -> dict[str, Any]:
        for call_name, kwargs in self.calls:
            if call_name == name:
                return kwargs
        raise AssertionError(f"{name} was not called; called {self.names()}")


def _install(monkeypatch, results: dict[str, Any]) -> FakeClient:
    fake = FakeClient(results)
    monkeypatch.setattr(client, "build_client", lambda settings: fake)
    monkeypatch.setattr(
        session,
        "load_session",
        lambda: {
            "username": "my_biz_account",
            "user_id": "888",
            "cookies": {"sessionid": "888_x", "ds_user_id": "888"},
        },
    )
    return fake


MEDIA_INSIGHTS = {
    "inline_insights_node": {
        "metrics": {
            "reach": 381,
            "impressions": 390,
            "likes": 22,
            "comments": 4,
            "saves": 7,
            "shares": 3,
            "profile_views": 12,
            "follower_gain": 2,
            "hashtag_impressions": 90,
        },
        "impressions_source": {"hashtags": 90, "home": 300},
    }
}


def test_media_dispatch_returns_the_metrics_and_never_invents(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(monkeypatch, {"insights_media": MEDIA_INSIGHTS})

    result = tools_insight.ig_insight(kind="media", media_pk="4024692804391239207")

    assert result["ok"] is True
    assert result["kind"] == "media"
    assert fake.kwargs_for("insights_media")["media_pk"] == "4024692804391239207"
    data = result["data"]
    assert data["reach"] == 381
    assert data["impressions"] == 390
    assert data["likes"] == 22
    assert data["saves"] == 7
    assert data["shares"] == 3
    assert data["profile_views"] == 12
    assert data["follower_gain"] == 2
    assert data["hashtag_impressions"] == 90
    assert data["impressions_source"] == {"hashtags": 90, "home": 300}


def test_media_without_a_pk_resolves_the_newest_post(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {
            "user_medias_v1": [{"pk": "111", "taken_at": None}],
            "insights_media": MEDIA_INSIGHTS,
        },
    )

    result = tools_insight.ig_insight(kind="media")

    assert result["ok"] is True
    posts_kwargs = fake.kwargs_for("user_medias_v1")
    assert posts_kwargs["user_id"] == "888"
    assert posts_kwargs["amount"] == 1
    assert fake.kwargs_for("insights_media")["media_pk"] == "111"


def test_account_dispatch_uses_account_insights(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {
            "insights_account": {
                "profile_visits": 540,
                "follower_growth": 35,
                "stories_count": 12,
                "top_posts": [{"pk": "1"}],
            }
        },
    )

    result = tools_insight.ig_insight(kind="account")

    assert result["ok"] is True
    assert "insights_account" in fake.names()
    data = result["data"]
    assert data["profile_visits"] == 540
    assert data["follower_growth"] == 35
    assert data["story_count"] == 12
    assert data["top_posts"] == [{"pk": "1"}]


def test_best_passes_time_frame_and_order_by_through(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = _install(
        monkeypatch,
        {"insights_media_feed_all": [{"pk": "1"}, {"pk": "2"}, {"pk": "3"}]},
    )

    result = tools_insight.ig_insight(
        kind="best", time_frame="ONE_MONTH", order_by="IMPRESSION_COUNT", limit=2
    )

    assert result["ok"] is True
    kwargs = fake.kwargs_for("insights_media_feed_all")
    assert kwargs["time_frame"] == "ONE_MONTH"
    assert kwargs["data_ordering"] == "IMPRESSION_COUNT"
    assert len(result["items"]) == 2


def test_best_time_states_its_method(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(
        monkeypatch,
        {
            "insights_account": {"profile_visits": 10},
            "user_medias_v1": [],
            "insights_media": MEDIA_INSIGHTS,
        },
    )

    result = tools_insight.ig_insight(kind="best_time", time_frame="ONE_WEEK")

    assert result["ok"] is True
    assert isinstance(result["method"], str) and result["method"]
    assert "method" in result


def test_demographics_returns_null_when_the_payload_has_none(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(monkeypatch, {"insights_account": {"profile_visits": 123, "follower_growth": 4}})

    result = tools_insight.ig_insight(kind="demographics")

    assert result["ok"] is True
    data = result["data"]
    for field in ("age", "gender", "city", "country"):
        assert data[field] is None, (field, data)
    assert any("demographics" in note for note in result["notes"])


def test_compare_groups_posts_by_age_band(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(
        monkeypatch,
        {
            "user_medias_v1": [
                {"pk": "1", "taken_at": 1_700_000_000},
                {"pk": "2", "taken_at": 1_700_500_000},
            ],
            "insights_media": {"metrics": {"reach": 100}},
        },
    )

    result = tools_insight.ig_insight(kind="compare", order_by="REACH_COUNT", limit=5)

    assert result["ok"] is True
    assert result["compared_by_age_band"] is True
    for row in result["items"]:
        assert row["age_band"] in result["bands"]
        assert "rank_in_band" in row


class MediaError(Exception):
    pass


def test_compare_falls_back_to_public_like_count_on_media_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _install(
        monkeypatch,
        {
            "user_medias_v1": [
                {"pk": "1", "taken_at": 1_700_000_000, "like_count": 15, "comment_count": 2},
                {"pk": "2", "taken_at": 1_700_500_000, "like_count": 40, "comment_count": 5},
            ],
            "insights_media": MediaError("not owner"),
        },
    )

    result = tools_insight.ig_insight(kind="compare", order_by="LIKE_COUNT", limit=5)

    assert result["ok"] is True
    assert [row["media_pk"] for row in result["items"]] == ["2", "1"]
    assert [row["value"] for row in result["items"]] == [40, 15]
    assert [row["like_count"] for row in result["items"]] == [40, 15]
    assert [row["comment_count"] for row in result["items"]] == [5, 2]
    assert all(row["metric_source"] == "public" for row in result["items"])
