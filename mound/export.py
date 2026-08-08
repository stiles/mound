"""Export pitch data to disk.

Serialization (turning a :class:`~mound.pitches.PitchCollection` into
CSV/JSON/Parquet bytes) is kept separate from *where* those bytes are
written. Today that's always :class:`LocalStorage`, but the split means a
future ``S3Storage`` can be dropped in without touching the format logic or
the core data model.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mound.pitches import PitchCollection

SUPPORTED_FORMATS = ("csv", "json", "parquet")


class Storage(ABC):
    """Destination for exported pitch data."""

    @abstractmethod
    def write(self, path: str, data: bytes) -> None:
        """Persist ``data`` at ``path``."""


class LocalStorage(Storage):
    """Write exported data to the local filesystem, creating parent directories."""

    def write(self, path: str, data: bytes) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)


_default_storage = LocalStorage()


def _resolve_storage(storage: Storage | None) -> Storage:
    return storage if storage is not None else _default_storage


def to_csv(
    collection: PitchCollection, path: str, storage: Storage | None = None, **kwargs
) -> None:
    """Export pitches to CSV."""
    data = collection.to_frame().to_csv(index=False, **kwargs).encode("utf-8")
    _resolve_storage(storage).write(path, data)


def to_json(
    collection: PitchCollection, path: str, storage: Storage | None = None, **kwargs
) -> None:
    """Export pitches to JSON (one record per pitch)."""
    kwargs.setdefault("orient", "records")
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("date_format", "iso")
    data = collection.to_frame().to_json(**kwargs).encode("utf-8")
    _resolve_storage(storage).write(path, data)


def to_parquet(
    collection: PitchCollection, path: str, storage: Storage | None = None, **kwargs
) -> None:
    """Export pitches to Parquet. Requires the optional `pyarrow` dependency."""
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Parquet export requires pyarrow. Install it with: pip install 'mound[parquet]'"
        ) from exc

    buffer = io.BytesIO()
    collection.to_frame().to_parquet(buffer, engine="pyarrow", **kwargs)
    _resolve_storage(storage).write(path, buffer.getvalue())


_FORMAT_HANDLERS = {"csv": to_csv, "json": to_json, "parquet": to_parquet}


def export(
    collection: PitchCollection,
    path: str,
    format: str | None = None,
    storage: Storage | None = None,
) -> None:
    """Export pitches, inferring the format from ``path``'s suffix if not given."""
    fmt = format or Path(path).suffix.lstrip(".").lower()
    handler = _FORMAT_HANDLERS.get(fmt)
    if handler is None:
        raise ValueError(f"Unsupported format: {fmt!r} (expected one of {SUPPORTED_FORMATS})")
    handler(collection, path, storage=storage)
