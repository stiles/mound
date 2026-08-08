"""A local file cache for Baseball Savant game-feed responses.

Keyed by ``game_pk`` since a finished game's Statcast data doesn't change --
a cache hit is never stale. The Stats API game-log lookup (which discovers
*which* ``game_pk``s exist) is cheap and always re-fetched fresh; only
already-cached game feeds get skipped, so repeat queries automatically fetch
just what's new since the last run without any separate "update" flag.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

DEFAULT_CACHE_DIRNAME = "mound"


class Cache(ABC):
    """Key-value storage for cached API responses."""

    @abstractmethod
    def get(self, key: str) -> dict | None:
        """Return the cached value for ``key``, or ``None`` if not cached."""

    @abstractmethod
    def set(self, key: str, value: dict) -> None:
        """Persist ``value`` under ``key``."""


def default_cache_dir() -> Path:
    """Resolve the default cache directory.

    Honors ``MOUND_CACHE_DIR`` if set, then ``XDG_CACHE_HOME``, falling back
    to ``~/.cache/mound``.
    """
    override = os.environ.get("MOUND_CACHE_DIR")
    if override:
        return Path(override)

    xdg_base = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_base) if xdg_base else Path.home() / ".cache"
    return base / DEFAULT_CACHE_DIRNAME


class FileCache(Cache):
    """Cache backed by one JSON file per key under a cache directory."""

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def set(self, key: str, value: dict) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))


def resolve_cache(cache: bool | str | Path | Cache | None) -> Cache | None:
    """Resolve a user-facing ``cache`` argument to a :class:`Cache` or ``None``.

    ``False``/``None`` (the default) disables caching entirely, preserving
    existing behavior. ``True`` enables a :class:`FileCache` at the default
    location; a string or :class:`~pathlib.Path` enables one at that
    location. An existing :class:`Cache` instance is passed through as-is.
    """
    if cache is None or cache is False:
        return None
    if isinstance(cache, Cache):
        return cache
    if cache is True:
        return FileCache()
    return FileCache(cache)
