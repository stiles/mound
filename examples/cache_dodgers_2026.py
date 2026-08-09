"""Warm a local Statcast cache for every Dodgers pitcher in 2026.

Demonstrates ``cache=`` at the scale of a whole pitching staff rather than
one pitcher: Savant's game-feed responses are cached per ``game_pk``, not
per pitcher, so any game two Dodgers pitchers both appeared in (which is
most of them) is only ever fetched once. Re-running this script later in
the season only fetches the games that happened since the last run.

Mound doesn't have a dedicated team-roster lookup yet (see ROADMAP.md's
"additional discovery tools" item), so this reaches into the MLB Stats API
directly with the same client mound itself uses internally, exactly as
sandbox/zone_video_check.py does for its own one-off needs.

Caches to a `cache/` directory at the repo root (gitignored), rather than
the default `~/.cache/mound`, so it's easy to find and delete.

Requires network access (hits the live MLB Stats API and Baseball Savant).
Fetching a full pitching staff's season is a lot of games -- expect this to
take a few minutes on a first run. Run with:

    python examples/cache_dodgers_2026.py
"""

from __future__ import annotations

from pathlib import Path

from mound import Pitcher
from mound.config import STATSAPI_V1
from mound.http import get_json

TEAM_ID = 119  # Los Angeles Dodgers
SEASON = 2026
CACHE_DIR = Path(__file__).parent.parent / "cache"


def dodgers_pitchers(season: int) -> list[tuple[int, str]]:
    """Every pitcher who spent time on the Dodgers' roster in ``season``.

    ``rosterType=fullSeason`` (rather than the default active/40-man
    roster) also picks up anyone since optioned to the minors, released, or
    added midseason -- a better match for "every pitcher who threw for this
    team in 2026" than a single point-in-time roster snapshot.
    """
    url = f"{STATSAPI_V1}/teams/{TEAM_ID}/roster"
    data = get_json(url, params={"rosterType": "fullSeason", "season": season})
    return [
        (entry["person"]["id"], entry["person"]["fullName"])
        for entry in data.get("roster", [])
        if entry["position"]["type"] == "Pitcher"
    ]


def main() -> None:
    CACHE_DIR.mkdir(exist_ok=True)

    pitchers = dodgers_pitchers(SEASON)
    print(f"Found {len(pitchers)} pitchers on the Dodgers' {SEASON} roster.\n")

    total_pitches = 0
    for player_id, name in pitchers:
        pitcher = Pitcher(player_id)
        pitches = pitcher.pitches(season=SEASON, cache=str(CACHE_DIR))
        total_pitches += len(pitches)
        print(f"{name:<24} {len(pitches):>5} pitches ({len(pitches.games)} games)")

    cached_games = len(list((CACHE_DIR / "gf").glob("*.json")))
    print(f"\nCached {cached_games} distinct games covering {total_pitches} total pitches.")
    print(f"Cache lives at {CACHE_DIR} (gitignored via the repo's cache/ entry).")
    print("Re-run this script later in the season to fetch only the new games.")


if __name__ == "__main__":
    main()
