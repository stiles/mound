from __future__ import annotations

from pathlib import Path

from mound.cache import Cache, FileCache, default_cache_dir, resolve_cache


def test_file_cache_miss_returns_none(tmp_path):
    cache = FileCache(tmp_path)

    assert cache.get("gf/123") is None


def test_file_cache_set_then_get_round_trips(tmp_path):
    cache = FileCache(tmp_path)

    cache.set("gf/123", {"game_pk": 123, "home_pitchers": {}})

    assert cache.get("gf/123") == {"game_pk": 123, "home_pitchers": {}}


def test_file_cache_creates_parent_directories(tmp_path):
    cache = FileCache(tmp_path / "nested" / "dir")

    cache.set("gf/123", {"ok": True})

    assert (tmp_path / "nested" / "dir" / "gf" / "123.json").exists()


def test_default_cache_dir_honors_mound_cache_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MOUND_CACHE_DIR", str(tmp_path / "custom"))

    assert default_cache_dir() == tmp_path / "custom"


def test_default_cache_dir_honors_xdg_cache_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MOUND_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    assert default_cache_dir() == tmp_path / "mound"


def test_default_cache_dir_falls_back_to_home_cache(monkeypatch):
    monkeypatch.delenv("MOUND_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    assert default_cache_dir() == Path.home() / ".cache" / "mound"


def test_resolve_cache_false_returns_none():
    assert resolve_cache(False) is None


def test_resolve_cache_none_returns_none():
    assert resolve_cache(None) is None


def test_resolve_cache_true_returns_default_file_cache():
    cache = resolve_cache(True)

    assert isinstance(cache, FileCache)
    assert cache.cache_dir == default_cache_dir()


def test_resolve_cache_path_returns_file_cache_at_that_path(tmp_path):
    cache = resolve_cache(tmp_path)

    assert isinstance(cache, FileCache)
    assert cache.cache_dir == tmp_path


def test_resolve_cache_string_returns_file_cache_at_that_path(tmp_path):
    cache = resolve_cache(str(tmp_path))

    assert isinstance(cache, FileCache)
    assert cache.cache_dir == tmp_path


def test_resolve_cache_passes_through_existing_cache_instance(tmp_path):
    existing = FileCache(tmp_path)

    assert resolve_cache(existing) is existing


def test_resolve_cache_accepts_custom_cache_subclass(tmp_path):
    class InMemoryCache(Cache):
        def __init__(self):
            self.store: dict[str, dict] = {}

        def get(self, key):
            return self.store.get(key)

        def set(self, key, value):
            self.store[key] = value

    cache = InMemoryCache()

    assert resolve_cache(cache) is cache
