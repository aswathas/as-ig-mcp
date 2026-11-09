"""Offline tests for the SQLite state file and the cache backed by it."""

from __future__ import annotations

from as_ig_mcp import state
from as_ig_mcp.cache import Cache


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _tables(path) -> set[str]:
    connection = state.connect(path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row["name"] for row in rows}
    finally:
        connection.close()


def test_init_db_creates_the_three_tables(tmp_path):
    path = state.init_db(tmp_path / "state.db")

    assert path.exists()
    assert {"cache", "digest", "queue"} <= _tables(path)


def test_two_connections_see_each_others_rows(tmp_path):
    path = state.init_db(tmp_path / "state.db")
    first = state.connect(path)
    second = state.connect(path)
    try:
        first.execute(
            "INSERT INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            ("profile:one", '{"username": "aswath"}', 9999.0),
        )
        first.commit()

        row = second.execute(
            "SELECT value FROM cache WHERE key = ?", ("profile:one",)
        ).fetchone()
        assert row is not None
        assert row["value"] == '{"username": "aswath"}'
    finally:
        first.close()
        second.close()


def test_two_cache_instances_share_the_same_database(tmp_path):
    path = tmp_path / "state.db"
    first = Cache(path, clock=FakeClock())
    second = Cache(path, clock=FakeClock())

    first.set("profile:one", {"username": "aswath"})
    assert second.get("profile:one") == {"username": "aswath"}


def test_writing_one_key_does_not_remove_another_key(tmp_path):
    path = tmp_path / "state.db"
    first = Cache(path, clock=FakeClock())
    second = Cache(path, clock=FakeClock())

    first.set("profile:one", "first")
    second.set("profile:two", "second")

    assert first.get("profile:one") == "first"
    assert first.get("profile:two") == "second"
    assert second.stats() == {"total": 2, "live": 2, "expired": 0}


def test_expired_row_is_not_returned_and_is_deleted(tmp_path):
    path = tmp_path / "state.db"
    clock = FakeClock()
    cache = Cache(path, clock=clock)

    cache.set("profile:one", "value", ttl=10)
    clock.advance(11)

    assert cache.get("profile:one") is None
    assert cache.stats() == {"total": 0, "live": 0, "expired": 0}


def test_invalidate_prefix_removes_only_matching_keys(tmp_path):
    path = tmp_path / "state.db"
    cache = Cache(path, clock=FakeClock())
    cache.set("profile:user1", {"name": "alice"})
    cache.set("profile:user2", {"name": "bob"})
    cache.set("posts:post1", {"caption": "hello"})
    cache.set("other", 123)

    assert cache.invalidate_prefix("profile:") == 2
    assert cache.get("profile:user1") is None
    assert cache.get("profile:user2") is None
    assert cache.get("posts:post1") == {"caption": "hello"}
    assert cache.get("other") == 123
    assert cache.invalidate_prefix("nonexistent") == 0


def test_stats_counts_total_live_and_expired(tmp_path):
    path = tmp_path / "state.db"
    clock = FakeClock()
    cache = Cache(path, clock=clock)
    cache.set("live", "a", ttl=100)
    cache.set("expired", "b", ttl=5)
    clock.advance(10)

    assert cache.stats() == {"total": 2, "live": 1, "expired": 1}
