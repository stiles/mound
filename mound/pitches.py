"""The composable, user-facing API: ``Pitcher``, ``Batter`` and ``PitchCollection``.

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

:class:`Batter` is the mirror image of :class:`Pitcher` -- the pitches a
hitter *faced* rather than threw -- so a matchup can be asked from either
side:

    Pitcher("Roki Sasaki").pitches(last=8, batter="Shohei Ohtani")
    Batter("Shohei Ohtani").pitches(last=20, pitcher="Roki Sasaki")
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from mound import statsapi
from mound.cache import Cache, resolve_cache
from mound.models import Pitch, normalize_pitch_type, normalize_stand
from mound.players import Player, resolve_player
from mound.savant import game_pitches_for_batter, game_pitches_for_pitcher

if TYPE_CHECKING:
    from pathlib import Path

    import matplotlib.axes


DateLike = str | date | datetime
PersonLike = int | str | list[int | str]


def _as_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _fold_name(name: str) -> str:
    """Lowercase and strip accents, so "berrios" still matches "Berríos"."""
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _person_criteria(value: PersonLike) -> tuple[set[int], list[str]]:
    """Split a batter/pitcher filter value into MLB player IDs and name fragments."""
    values = value if isinstance(value, list | tuple | set) else [value]
    ids: set[int] = set()
    names: list[str] = []
    for item in values:
        text = str(item).strip()
        if text.isdigit():
            ids.add(int(text))
        elif text:
            names.append(_fold_name(text))
    return ids, names


def _person_matches(
    player_id: int | None, name: str | None, ids: set[int], names: list[str]
) -> bool:
    if player_id is not None and player_id in ids:
        return True
    if not name:
        return False
    # Substring matching so "ohtani" or "judge" lands without having to
    # reproduce the exact full name Savant reports.
    folded = _fold_name(name)
    return any(fragment in folded for fragment in names)


class PitchCollection:
    """An immutable, filterable collection of normalized pitches.

    Backed internally by a pandas DataFrame so it can be composed with
    ordinary pandas/NumPy workflows, while still offering baseball-flavored
    convenience methods.
    """

    def __init__(
        self,
        pitches: list[Pitch] | None = None,
        pitcher: Player | None = None,
        batter: Player | None = None,
    ):
        self._pitches = pitches or []
        # Whichever player the collection was retrieved for, which decides
        # how it reads: a pitcher's pitches thrown, or a batter's faced.
        self.pitcher = pitcher
        self.batter = batter

    def __len__(self) -> int:
        return len(self._pitches)

    def __repr__(self) -> str:
        if self.pitcher and self.batter:
            who = f"{self.pitcher.full_name} to {self.batter.full_name}"
        elif self.batter:
            who = f"to {self.batter.full_name}"
        else:
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
        at_bat_number: int | list[int] | None = None,
        pitch_number: int | list[int] | None = None,
        since: DateLike | None = None,
        until: DateLike | None = None,
        is_strike: bool | None = None,
        in_zone: bool | None = None,
        zone: int | list[int] | None = None,
        ends_at_bat: bool | None = None,
        stand: str | None = None,
        batter: PersonLike | None = None,
        pitcher: PersonLike | None = None,
    ) -> PitchCollection:
        """Return a new :class:`PitchCollection` narrowed by the given criteria.

        ``pitch_type`` accepts familiar names (``"splitter"``), aliases
        (``"split-finger"``) or raw Statcast codes (``"FS"``), case-insensitive.

        ``stand`` filters by batter side, e.g. ``"L"``/``"left"``/``"LHB"``
        or ``"R"``/``"right"``/``"RHB"`` (case-insensitive).

        ``batter`` and ``pitcher`` each take an MLB player ID or a name, or a
        list mixing the two. Names match any part of the name Savant reports,
        ignoring case and accents, so ``batter="ohtani"`` is enough. A name
        loose enough to match two players (``"contreras"``) keeps both; pass
        an ID to be unambiguous.

        ``at_bat_number`` is only unique within a single game, so pair it
        with ``game`` to isolate one at-bat; add ``pitch_number`` on top of
        that to narrow all the way down to one specific pitch.

        ``zone`` takes one Statcast zone number or a list of them: 1-9 inside
        the strike zone, 11-14 outside it (there is no 10). ``zone=5`` is the
        heart of the plate, ``zone=[11, 12, 13, 14]`` everything off it.

        ``ends_at_bat=True`` keeps the pitch each at-bat ended on, one row per
        plate appearance, which is where ``at_bat_result`` and ``description``
        actually apply -- Savant repeats both on every pitch of the at-bat.
        The flag is derived when the feed is parsed, so it survives narrowing:
        filtering to changeups first doesn't promote an at-bat's last changeup
        into its last pitch.
        """
        pitches = self._pitches

        if pitch_type is not None:
            wanted_names = [pitch_type] if isinstance(pitch_type, str) else list(pitch_type)
            wanted_codes = {normalize_pitch_type(name) or name.upper() for name in wanted_names}
            pitches = [p for p in pitches if p.pitch_type_code in wanted_codes]

        if game is not None:
            wanted_games = {game} if isinstance(game, int) else set(game)
            pitches = [p for p in pitches if p.game_pk in wanted_games]

        if at_bat_number is not None:
            wanted_abs = {at_bat_number} if isinstance(at_bat_number, int) else set(at_bat_number)
            pitches = [p for p in pitches if p.at_bat_number in wanted_abs]

        if pitch_number is not None:
            wanted_nums = {pitch_number} if isinstance(pitch_number, int) else set(pitch_number)
            pitches = [p for p in pitches if p.pitch_number in wanted_nums]

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

        if zone is not None:
            wanted_zones = {zone} if isinstance(zone, int) else set(zone)
            pitches = [p for p in pitches if p.zone in wanted_zones]

        if ends_at_bat is not None:
            pitches = [p for p in pitches if p.ends_at_bat == ends_at_bat]

        if stand is not None:
            wanted_stand = normalize_stand(stand) or stand.strip().upper()
            pitches = [p for p in pitches if p.batter_stand == wanted_stand]

        if batter is not None:
            ids, names = _person_criteria(batter)
            pitches = [
                p for p in pitches if _person_matches(p.batter_id, p.batter_name, ids, names)
            ]

        if pitcher is not None:
            ids, names = _person_criteria(pitcher)
            pitches = [
                p for p in pitches if _person_matches(p.pitcher_id, p.pitcher_name, ids, names)
            ]

        return PitchCollection(pitches, pitcher=self.pitcher, batter=self.batter)

    def limit(self, n: int) -> PitchCollection:
        """Return a new :class:`PitchCollection` capped to its first ``n`` pitches."""
        return PitchCollection(self._pitches[:n], pitcher=self.pitcher, batter=self.batter)

    # -- analysis -----------------------------------------------------
    def pitch_mix(self) -> pd.Series:
        from mound.analysis import pitch_mix

        return pitch_mix(self)

    def strike_rate(self, by_pitch_type: bool = False) -> float | pd.Series:
        from mound.analysis import strike_rate

        return strike_rate(self, by_pitch_type=by_pitch_type)

    def swing_rate(self, by_pitch_type: bool = False) -> float | pd.Series:
        from mound.analysis import swing_rate

        return swing_rate(self, by_pitch_type=by_pitch_type)

    def whiff_rate(self, by_pitch_type: bool = False) -> float | pd.Series:
        from mound.analysis import whiff_rate

        return whiff_rate(self, by_pitch_type=by_pitch_type)

    def chase_rate(self, by_pitch_type: bool = False) -> float | pd.Series:
        from mound.analysis import chase_rate

        return chase_rate(self, by_pitch_type=by_pitch_type)

    def pitch_metrics(self, by_pitch_type: bool = True) -> pd.DataFrame | pd.Series:
        from mound.analysis import pitch_metrics

        return pitch_metrics(self, by_pitch_type=by_pitch_type)

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


def _appearances_for_player(
    player_id: int,
    *,
    group: str,
    last: int | None,
    since: DateLike | None,
    until: DateLike | None,
    season: int | None,
) -> list[statsapi.GameAppearance]:
    """Discover which games a player appeared in, oldest first.

    ``group`` is ``"pitching"`` for a pitcher's appearances or ``"hitting"``
    for a batter's; the ``last``/``since``/``until``/``season`` narrowing is
    identical either way. This is the cheap half of retrieval -- one Stats
    API request per season, no Baseball Savant lookup -- which is also why
    it's exposed on its own via :meth:`Pitcher.games`/:meth:`Batter.games`.
    """
    seasons = _seasons_for_query(since, until, season)
    appearances = statsapi.game_log_seasons(player_id, seasons, group=group)

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
            appearances = statsapi.game_log_seasons(player_id, lookback_seasons, group=group)

    if last is not None:
        appearances = appearances[-last:]

    return appearances


def _game_pks_for_player(
    player_id: int,
    *,
    group: str,
    last: int | None,
    since: DateLike | None,
    until: DateLike | None,
    season: int | None,
) -> list[int]:
    """Discover which games to fetch for a player, oldest first."""
    appearances = _appearances_for_player(
        player_id, group=group, last=last, since=since, until=until, season=season
    )
    return [a.game_pk for a in appearances]


_GAME_COLUMNS = ["game_date", "game_pk", "opponent_name", "is_home"]


def _appearances_to_frame(appearances: list[statsapi.GameAppearance]) -> pd.DataFrame:
    if not appearances:
        return pd.DataFrame(columns=_GAME_COLUMNS)
    return pd.DataFrame(
        [
            {
                "game_date": a.game_date,
                "game_pk": a.game_pk,
                "opponent_name": a.opponent_name,
                "is_home": a.is_home,
            }
            for a in appearances
        ],
        columns=_GAME_COLUMNS,
    )


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
        at_bat_number: int | list[int] | None = None,
        pitch_number: int | list[int] | None = None,
        stand: str | None = None,
        batter: PersonLike | None = None,
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

        ``pitch_type``, ``at_bat_number``, ``pitch_number``, ``stand`` and
        ``batter`` are applied as post-retrieval filters (see
        :meth:`PitchCollection.filter`); pair ``game`` with ``at_bat_number``
        (and ``pitch_number``, to land on one exact pitch) since an at-bat
        number is only unique within a single game.

        ``batter`` narrows to one opposing hitter for a matchup view, by name
        or MLB player ID::

            roki.pitches(last=8, batter="Shohei Ohtani").pitch_mix()

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
            game_pks = _game_pks_for_player(
                self.player.id,
                group="pitching",
                last=last,
                since=since,
                until=until,
                season=season,
            )

        all_pitches: list[Pitch] = []
        for game_pk in game_pks:
            all_pitches.extend(
                game_pitches_for_pitcher(game_pk, self.player.id, cache=cache_backend)
            )

        return PitchCollection(all_pitches, pitcher=self.player).filter(
            pitch_type=pitch_type,
            at_bat_number=at_bat_number,
            pitch_number=pitch_number,
            stand=stand,
            batter=batter,
        )

    def games(
        self,
        *,
        last: int | None = None,
        since: DateLike | None = None,
        until: DateLike | None = None,
        season: int | None = None,
    ) -> pd.DataFrame:
        """List this pitcher's games -- date, ``game_pk``, opponent, home/away.

        Same ``last``/``since``/``until``/``season`` selection as
        :meth:`pitches`, but far cheaper: this reads only the Stats API's
        game log (one request per season), with no Baseball Savant lookup,
        so it's the way to answer "which games" without paying for every
        pitch of each one. Pass the resulting ``game_pk`` values straight
        into ``pitches(game=...)`` for the ones you actually want::

            roki.games(last=4)
            roki.pitches(game=roki.games(last=4)["game_pk"].tolist())

        With no arguments, defaults to the current season's appearances.
        """
        appearances = _appearances_for_player(
            self.player.id, group="pitching", last=last, since=since, until=until, season=season
        )
        return _appearances_to_frame(appearances)


class Batter:
    """A batter, resolved from a name or MLB player ID.

    The mirror image of :class:`Pitcher`: :meth:`pitches` returns the pitches
    this hitter *faced*, pulled from the games he played rather than the games
    a pitcher appeared in. Retrieval is lazy, so constructing a ``Batter``
    only resolves identity.
    """

    def __init__(self, name_or_id: str | int):
        self.player = resolve_player(name_or_id)

    def __repr__(self) -> str:
        return f"<Batter {self.player.full_name} ({self.player.id})>"

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
        pitcher: PersonLike | None = None,
        pitch_type: str | list[str] | None = None,
        at_bat_number: int | list[int] | None = None,
        pitch_number: int | list[int] | None = None,
        stand: str | None = None,
        cache: bool | str | Path | Cache | None = False,
    ) -> PitchCollection:
        """Retrieve the pitches this batter faced.

        Game selection (``game``/``last``/``since``/``until``/``season``) and
        the post-retrieval filters work exactly as they do in
        :meth:`Pitcher.pitches`, with ``last`` counting the batter's most
        recent games played. ``pitcher`` narrows to one opposing arm, by name
        or MLB player ID::

            Batter("Shohei Ohtani").pitches(season=2026, pitcher="Roki Sasaki")

        For a single matchup, asking from the pitcher's side
        (``Pitcher(...).pitches(batter=...)``) fetches far fewer games, since
        a starter appears in a fraction of the games a hitter plays. Come at
        it from here when the hitter is the subject -- everything he saw,
        from every pitcher.

        ``stand`` is only meaningful for a switch hitter, who stands on
        whichever side the opposing pitcher's hand dictates.
        """
        cache_backend = resolve_cache(cache)
        if game is not None:
            game_pks = [game] if isinstance(game, int) else list(game)
        else:
            game_pks = _game_pks_for_player(
                self.player.id,
                group="hitting",
                last=last,
                since=since,
                until=until,
                season=season,
            )

        all_pitches: list[Pitch] = []
        for game_pk in game_pks:
            all_pitches.extend(
                game_pitches_for_batter(game_pk, self.player.id, cache=cache_backend)
            )

        return PitchCollection(all_pitches, batter=self.player).filter(
            pitch_type=pitch_type,
            at_bat_number=at_bat_number,
            pitch_number=pitch_number,
            stand=stand,
            pitcher=pitcher,
        )

    def games(
        self,
        *,
        last: int | None = None,
        since: DateLike | None = None,
        until: DateLike | None = None,
        season: int | None = None,
    ) -> pd.DataFrame:
        """List the games this batter played -- date, ``game_pk``, opponent, home/away.

        The mirror image of :meth:`Pitcher.games`, reading only the Stats
        API's game log rather than every pitcher this batter faced. Same
        selection as :meth:`pitches`, with ``last`` counting games played.
        """
        appearances = _appearances_for_player(
            self.player.id, group="hitting", last=last, since=since, until=until, season=season
        )
        return _appearances_to_frame(appearances)
