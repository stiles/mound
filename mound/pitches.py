"""The composable, user-facing API: ``Pitcher`` and ``PitchCollection``.

    from mound import Pitcher

    roki = Pitcher("Roki Sasaki")
    pitches = roki.pitches(last=4)
    splitters = pitches.filter(pitch_type="splitter")

    splitters.pitch_mix()
    splitters.strike_rate()
    splitters.plot_zone()

Filtering a :class:`PitchCollection` always returns another
:class:`PitchCollection`, so analysis, plotting and export methods work the
same way regardless of how the data was narrowed down.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from mound import statsapi
from mound.cache import Cache, resolve_cache
from mound.models import Pitch, normalize_pitch_type, normalize_stand
from mound.players import Player, resolve_player
from mound.savant import game_pitches_for_pitcher

if TYPE_CHECKING:
    from pathlib import Path

    import matplotlib.axes


DateLike = str | date | datetime


def _as_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


class PitchCollection:
    """An immutable, filterable collection of normalized pitches.

    Backed internally by a pandas DataFrame so it can be composed with
    ordinary pandas/NumPy workflows, while still offering baseball-flavored
    convenience methods.
    """

    def __init__(self, pitches: list[Pitch] | None = None, pitcher: Player | None = None):
        self._pitches = pitches or []
        self.pitcher = pitcher

    def __len__(self) -> int:
        return len(self._pitches)

    def __repr__(self) -> str:
        who = self.pitcher.full_name if self.pitcher else "unknown pitcher"
        return f"<PitchCollection {who}: {len(self)} pitches>"

    def __iter__(self):
        return iter(self._pitches)

    @property
    def empty(self) -> bool:
        return len(self._pitches) == 0

    @property
    def pitches(self) -> list[Pitch]:
        return list(self._pitches)

    @property
    def records(self) -> list[dict[str, Any]]:
        return [p.__dict__.copy() for p in self._pitches]

    @property
    def games(self) -> list[int]:
        return sorted({p.game_pk for p in self._pitches if p.game_pk is not None})

    def to_frame(self) -> pd.DataFrame:
        """Return the underlying pitch data as a pandas DataFrame."""
        columns = Pitch.field_names()
        if not self._pitches:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(self.records, columns=columns)

    def filter(
        self,
        *,
        pitch_type: str | list[str] | None = None,
        game: int | list[int] | None = None,
        since: DateLike | None = None,
        until: DateLike | None = None,
        is_strike: bool | None = None,
        in_zone: bool | None = None,
        stand: str | None = None,
    ) -> PitchCollection:
        """Return a new :class:`PitchCollection` narrowed by the given criteria.

        ``pitch_type`` accepts familiar names (``"splitter"``), aliases
        (``"split-finger"``) or raw Statcast codes (``"FS"``), case-insensitive.

        ``stand`` filters by batter side, e.g. ``"L"``/``"left"``/``"LHB"``
        or ``"R"``/``"right"``/``"RHB"`` (case-insensitive).
        """
        pitches = self._pitches

        if pitch_type is not None:
            wanted_names = [pitch_type] if isinstance(pitch_type, str) else list(pitch_type)
            wanted_codes = {normalize_pitch_type(name) or name.upper() for name in wanted_names}
            pitches = [p for p in pitches if p.pitch_type_code in wanted_codes]

        if game is not None:
            wanted_games = {game} if isinstance(game, int) else set(game)
            pitches = [p for p in pitches if p.game_pk in wanted_games]

        if since is not None:
            since_date = _as_date(since)
            pitches = [p for p in pitches if p.game_date and _as_date(p.game_date) >= since_date]

        if until is not None:
            until_date = _as_date(until)
            pitches = [p for p in pitches if p.game_date and _as_date(p.game_date) <= until_date]

        if is_strike is not None:
            pitches = [p for p in pitches if p.is_strike == is_strike]

        if in_zone is not None:
            pitches = [p for p in pitches if p.in_zone == in_zone]

        if stand is not None:
            wanted_stand = normalize_stand(stand) or stand.strip().upper()
            pitches = [p for p in pitches if p.batter_stand == wanted_stand]

        return PitchCollection(pitches, pitcher=self.pitcher)

    # -- analysis -----------------------------------------------------
    def pitch_mix(self) -> pd.Series:
        from mound.analysis import pitch_mix

        return pitch_mix(self)

    def strike_rate(self, by_pitch_type: bool = False) -> float | pd.Series:
        from mound.analysis import strike_rate

        return strike_rate(self, by_pitch_type=by_pitch_type)

    def usage_rate(self, by: str = "game_date") -> pd.DataFrame:
        from mound.analysis import usage_rate

        return usage_rate(self, by=by)

    # -- visualization --------------------------------------------------
    def plot_zone(self, **kwargs) -> matplotlib.axes.Axes:
        from mound.viz import plot_zone

        return plot_zone(self, **kwargs)

    # -- video ------------------------------------------------------------
    def download_videos(self, out_dir: str | Path = "videos", **kwargs) -> list[Path]:
        from mound.video import download_videos

        return download_videos(self, out_dir=out_dir, **kwargs)

    # -- export -----------------------------------------------------------
    def to_csv(self, path: str, **kwargs) -> None:
        from mound.export import to_csv

        to_csv(self, path, **kwargs)

    def to_json(self, path: str, **kwargs) -> None:
        from mound.export import to_json

        to_json(self, path, **kwargs)

    def to_parquet(self, path: str, **kwargs) -> None:
        from mound.export import to_parquet

        to_parquet(self, path, **kwargs)

    def export(self, path: str, format: str | None = None) -> None:
        from mound.export import export

        export(self, path, format=format)


def _seasons_for_query(
    since: DateLike | None, until: DateLike | None, season: int | None
) -> list[int]:
    if season is not None:
        return [season]
    if since is not None or until is not None:
        start_year = _as_date(since).year if since is not None else date.today().year
        end_year = _as_date(until).year if until is not None else date.today().year
        return list(range(start_year, end_year + 1))
    return [date.today().year]


class Pitcher:
    """A pitcher, resolved from a name or MLB player ID.

    Retrieval is lazy: constructing a ``Pitcher`` only resolves identity.
    Pitch data is fetched on demand via :meth:`pitches`.
    """

    def __init__(self, name_or_id: str | int):
        self.player = resolve_player(name_or_id)

    def __repr__(self) -> str:
        return f"<Pitcher {self.player.full_name} ({self.player.id})>"

    @property
    def id(self) -> int:
        return self.player.id

    @property
    def name(self) -> str:
        return self.player.full_name

    def pitches(
        self,
        *,
        last: int | None = None,
        since: DateLike | None = None,
        until: DateLike | None = None,
        game: int | list[int] | None = None,
        season: int | None = None,
        pitch_type: str | list[str] | None = None,
        stand: str | None = None,
        cache: bool | str | Path | Cache | None = False,
    ) -> PitchCollection:
        """Retrieve this pitcher's pitches.

        Exactly which games are fetched depends on the arguments given:

        - ``game``: one or more specific ``game_pk`` values.
        - ``last``: the pitcher's N most recent appearances (optionally
          scoped further by ``since``/``until``/``season``).
        - ``since``/``until``: a date range (inclusive), given as
          ``"YYYY-MM-DD"`` strings or :class:`datetime.date` objects.
        - ``season``: a single MLB season, if no explicit dates are given.

        ``pitch_type`` and ``stand`` are applied as post-retrieval filters
        (see :meth:`PitchCollection.filter`).

        ``cache`` enables a local file cache of Savant's per-game responses
        (disabled by default): ``True`` uses the default cache location,
        or pass a directory path to use a custom one. Because a finished
        game's data never changes, repeat calls automatically skip
        re-fetching any ``game_pk`` already cached -- so caching a pitcher
        now and calling again later only fetches their new starts.

        With no arguments, defaults to the current season's appearances.
        """
        cache_backend = resolve_cache(cache)
        if game is not None:
            game_pks = [game] if isinstance(game, int) else list(game)
        else:
            seasons = _seasons_for_query(since, until, season)
            appearances = statsapi.pitching_game_log_seasons(self.player.id, seasons)

            if since is not None:
                since_date = _as_date(since)
                appearances = [a for a in appearances if a.game_date >= since_date]
            if until is not None:
                until_date = _as_date(until)
                appearances = [a for a in appearances if a.game_date <= until_date]

            # If we need the last N appearances but this season doesn't have
            # enough games yet (e.g. early April), fall back to prior seasons.
            if last is not None and since is None and until is None and season is None:
                lookback_seasons = list(seasons)
                while len(appearances) < last and min(lookback_seasons) > 2015:
                    lookback_seasons = [min(lookback_seasons) - 1, *lookback_seasons]
                    appearances = statsapi.pitching_game_log_seasons(
                        self.player.id, lookback_seasons
                    )

            if last is not None:
                appearances = appearances[-last:]

            game_pks = [a.game_pk for a in appearances]

        all_pitches: list[Pitch] = []
        for game_pk in game_pks:
            all_pitches.extend(
                game_pitches_for_pitcher(game_pk, self.player.id, cache=cache_backend)
            )

        collection = PitchCollection(all_pitches, pitcher=self.player)
        if pitch_type is not None:
            collection = collection.filter(pitch_type=pitch_type)
        if stand is not None:
            collection = collection.filter(stand=stand)
        return collection
