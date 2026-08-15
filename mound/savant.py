"""Baseball Savant client: pitch-level data via the `/gf` game-feed endpoint.

`/gf?game_pk={pk}` returns Statcast pitch data for both teams in a game,
organized as `home_pitchers`/`away_pitchers` dicts keyed by pitcher ID. That
means we can go straight to a single pitcher's pitches without scanning
every batter faced. Batter-side retrieval is the inverse: the feed has no
batter index, so pulling one hitter's plate appearances means walking every
pitcher's list and keeping the pitches thrown to them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mound import config
from mound.http import get_json
from mound.models import Pitch, pitch_from_savant

if TYPE_CHECKING:
    from mound.cache import Cache


# Savant reports MLB's own game status codes: "F" (final, plus its variants
# for rain-shortened and forfeited games) and "O" (game over, the brief state
# between the last out and the official final). Anything else -- scheduled,
# in progress, suspended, postponed -- is a game whose feed can still gain
# pitches, and an unrecognized or missing code is treated the same way, so a
# changed API errs toward re-fetching rather than caching a partial game.
FINAL_STATUS_CODES = frozenset({"F", "FR", "FO", "FT", "O"})


def is_final_feed(feed: dict) -> bool:
    """Whether a game feed covers a completed game, and so can't change again."""
    code = str(feed.get("game_status_code") or feed.get("game_status") or "").strip().upper()
    return code in FINAL_STATUS_CODES


def fetch_game_feed(game_pk: int, cache: Cache | None = None) -> dict:
    """Fetch the raw Baseball Savant game-feed payload for one game.

    Only *finished* games are cached, in either direction: a feed fetched
    mid-game is returned but not written, and a cached feed that turns out
    to cover a game still in progress is ignored and re-fetched. So a live
    game costs a request every time, and never leaves a partial inning
    behind for later runs to trust.
    """
    cache_key = f"gf/{game_pk}"
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None and is_final_feed(cached):
            return cached

    data = get_json(config.SAVANT_GAMEFEED_URL, params={"game_pk": game_pk})

    if cache is not None and is_final_feed(data):
        cache.set(cache_key, data)

    return data


def _raw_pitches_for_pitcher(feed: dict, pitcher_id: int) -> list[dict]:
    key = str(pitcher_id)
    for side in ("home_pitchers", "away_pitchers"):
        pitches = (feed.get(side) or {}).get(key)
        if pitches:
            return pitches
    return []


def _raw_pitches_for_batter(feed: dict, batter_id: int) -> list[dict]:
    raw_pitches: list[dict] = []
    for side in ("home_pitchers", "away_pitchers"):
        for pitcher_pitches in (feed.get(side) or {}).values():
            raw_pitches.extend(p for p in pitcher_pitches if p.get("batter") == batter_id)
    return raw_pitches


def _normalize_pitches(raw_pitches: list[dict], game_date: str | None) -> list[Pitch]:
    pitches = []
    for raw in raw_pitches:
        if raw.get("type") != "pitch":
            continue
        enriched = dict(raw)
        enriched.setdefault("game_date", game_date)
        pitches.append(pitch_from_savant(enriched))

    pitches.sort(key=lambda p: (p.at_bat_number or 0, p.pitch_number or 0))
    return pitches


def game_pitches_for_pitcher(
    game_pk: int, pitcher_id: int, cache: Cache | None = None
) -> list[Pitch]:
    """Fetch and normalize every pitch a given pitcher threw in one game."""
    feed = fetch_game_feed(game_pk, cache=cache)
    return _normalize_pitches(_raw_pitches_for_pitcher(feed, pitcher_id), feed.get("game_date"))


def game_pitches_for_batter(
    game_pk: int, batter_id: int, cache: Cache | None = None
) -> list[Pitch]:
    """Fetch and normalize every pitch a given batter faced in one game.

    Pitches come back in at-bat order regardless of which pitchers threw
    them, so a hitter's night reads start to finish across pitching changes.
    """
    feed = fetch_game_feed(game_pk, cache=cache)
    return _normalize_pitches(_raw_pitches_for_batter(feed, batter_id), feed.get("game_date"))
