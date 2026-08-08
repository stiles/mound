"""Baseball Savant client: pitch-level data via the `/gf` game-feed endpoint.

`/gf?game_pk={pk}` returns Statcast pitch data for both teams in a game,
organized as `home_pitchers`/`away_pitchers` dicts keyed by pitcher ID. That
means we can go straight to a single pitcher's pitches without scanning
every batter faced.
"""

from __future__ import annotations

from mound import config
from mound.http import get_json
from mound.models import Pitch, pitch_from_savant


def fetch_game_feed(game_pk: int) -> dict:
    """Fetch the raw Baseball Savant game-feed payload for one game."""
    return get_json(config.SAVANT_GAMEFEED_URL, params={"game_pk": game_pk})


def _raw_pitches_for_pitcher(feed: dict, pitcher_id: int) -> list[dict]:
    key = str(pitcher_id)
    for side in ("home_pitchers", "away_pitchers"):
        pitches = (feed.get(side) or {}).get(key)
        if pitches:
            return pitches
    return []


def game_pitches_for_pitcher(game_pk: int, pitcher_id: int) -> list[Pitch]:
    """Fetch and normalize every pitch a given pitcher threw in one game."""
    feed = fetch_game_feed(game_pk)
    game_date = feed.get("game_date")
    raw_pitches = _raw_pitches_for_pitcher(feed, pitcher_id)

    pitches = []
    for raw in raw_pitches:
        if raw.get("type") != "pitch":
            continue
        enriched = dict(raw)
        enriched.setdefault("game_date", game_date)
        pitches.append(pitch_from_savant(enriched))

    pitches.sort(key=lambda p: (p.at_bat_number or 0, p.pitch_number or 0))
    return pitches
