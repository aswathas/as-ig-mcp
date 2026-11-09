"""Offline tests for the on-disk TTL cache."""

from as_ig_mcp.cache import Cache, make_key


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_set_then_get_returns_the_value(tmp_path):
    cache = Cache(tmp_path / "cache.json", clock=FakeClock())
    cache.set("profile:one", {"username": "aswath"}, ttl=30)
    assert cache.get("profile:one") == {"username": "aswath"}


def test_get_returns_none_after_the_ttl(tmp_path):
    clock = FakeClock()
    cache = Cache(tmp_path / "cache.json", clock=clock)
    cache.set("profile:one", "value", ttl=10)
    clock.advance(11)
    assert cache.get("profile:one") is None


def test_stats_counts_live_and_expired(tmp_path):
    clock = FakeClock()
    cache = Cache(tmp_path / "cache.json", clock=clock)
    cache.set("live", "a", ttl=100)
    cache.set("expired", "b", ttl=5)
    clock.advance(10)

    assert cache.stats() == {"total": 2, "live": 1, "expired": 1}


def test_invalidate_removes_one_key(tmp_path):
    cache = Cache(tmp_path / "cache.json", clock=FakeClock())
    cache.set("one", 1)
    cache.set("two", 2)

    assert cache.invalidate("one") == 1
    assert cache.get("one") is None
    assert cache.get("two") == 2


def test_invalidate_with_no_key_clears_everything(tmp_path):
    cache = Cache(tmp_path / "cache.json", clock=FakeClock())
    cache.set("one", 1)
    cache.set("two", 2)

    assert cache.invalidate() == 2
    assert cache.stats() == {"total": 0, "live": 0, "expired": 0}


def test_corrupt_cache_file_is_treated_as_empty(tmp_path):
    path = tmp_path / "cache.json"
    path.write_bytes(b"this is not json")

    cache = Cache(path, clock=FakeClock())
    assert cache.get("anything") is None
    assert cache.stats() == {"total": 0, "live": 0, "expired": 0}

    cache.set("anything", "value")
    assert cache.get("anything") == "value"


def test_two_different_keys_do_not_collide(tmp_path):
    cache = Cache(tmp_path / "cache.json", clock=FakeClock())
    first = make_key("profile", {"user_id": "1"})
    second = make_key("profile", {"user_id": "2"})
    assert first != second

    cache.set(first, "first")
    cache.set(second, "second")
    assert cache.get(first) == "first"
    assert cache.get(second) == "second"


def test_make_key_is_stable_across_param_order():
    assert make_key("profile", {"a": 1, "b": 2}) == make_key("profile", {"b": 2, "a": 1})


def test_invalidate_prefix_removes_only_matching_keys(tmp_path):
    cache = Cache(tmp_path / "cache.json", clock=FakeClock())
    cache.set("profile:user1", {"name": "alice"})
    cache.set("profile:user2", {"name": "bob"})
    cache.set("posts:post1", {"caption": "hello"})
    cache.set("other", 123)

    removed = cache.invalidate_prefix("profile:")
    assert removed == 2
    assert cache.get("profile:user1") is None
    assert cache.get("profile:user2") is None
    assert cache.get("posts:post1") == {"caption": "hello"}
    assert cache.get("other") == 123

    # Invalidate with prefix that does not match anything
    assert cache.invalidate_prefix("nonexistent") == 0
