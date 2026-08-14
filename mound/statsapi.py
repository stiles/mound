"""MLB Stats API client: game discovery via a player's game log.

Mound uses the Stats API to discover *which games* a player appeared in
(honoring ``last``/date-range filters at the game level) before asking
Baseball Savant for the actual pitch-level detail of each game. The same
endpoint covers both sides of the ball -- a pitcher's appearances or a
batter's -- via the ``group`` parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from mound import config
from mound.http import get_json


@dataclass
class GameAppearance:
    """A single game a player appeared in, per the Stats API game log."""

    game_pk: int
    game_date: date
    season: int
    team_id: int | None
    team_name: str | None
    opponent_id: int | None
    opponent_name: str | None
    is_home: bool | None
    game_type: str | None
    games_started: int | None
    number_of_pitches: int | None


def _parse_game_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _appearance_from_split(split: dict) -> GameAppearance | None:
    game = split.get("game") or {}
    game_pk = game.get("gamePk")
    game_date_raw = split.get("date")
    if game_pk is None or not game_date_raw:
        return None

    team = split.get("team") or {}
    opponent = split.get("opponent") or {}
    stat = split.get("stat") or {}

    parsed_date = _parse_game_date(game_date_raw)
    season = int(split["season"]) if split.get("season") else parsed_date.year

    return GameAppearance(
        game_pk=int(game_pk),
        game_date=parsed_date,
        season=season,
        team_id=team.get("id"),
        team_name=team.get("name"),
        opponent_id=opponent.get("id"),
        opponent_name=opponent.get("name"),
        is_home=split.get("isHome"),
        game_type=split.get("gameType"),
        games_started=stat.get("gamesStarted"),
        number_of_pitches=stat.get("numberOfPitches"),
    )


def game_log(player_id: int, season: int, group: str = "pitching") -> list[GameAppearance]:
    """Fetch a player's game-by-game log for a single season, oldest first.

    ``group`` picks which side of the ball the log covers: ``"pitching"``
    for games a pitcher appeared in, ``"hitting"`` for games a batter did.
    """
    url = f"{config.STATSAPI_V1}/people/{player_id}/stats"
    data = get_json(
        url,
        params={"stats": "gameLog", "group": group, "season": season},
    )
    stats = data.get("stats") or []
    if not stats:
        return []
    splits = stats[0].get("splits") or []
    appearances = [_appearance_from_split(s) for s in splits]
    appearances = [a for a in appearances if a is not None]
    appearances.sort(key=lambda a: a.game_date)
    return appearances


def game_log_seasons(
    player_id: int, seasons: list[int], group: str = "pitching"
) -> list[GameAppearance]:
    """Fetch and merge a player's game log across multiple seasons, oldest first."""
    all_appearances: list[GameAppearance] = []
    for season in seasons:
        all_appearances.extend(game_log(player_id, season, group=group))
    all_appearances.sort(key=lambda a: a.game_date)
    return all_appearances
