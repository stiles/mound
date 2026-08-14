from __future__ import annotations

from datetime import date

from mound.statsapi import game_log, game_log_seasons
from tests.conftest import register_game_log


def test_pitching_game_log_parses_splits(mocked_responses):
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)

    appearances = game_log(808963, 2025)

    assert len(appearances) == 3
    first = appearances[0]
    assert first.game_pk == 1001
    assert first.game_date == date(2025, 7, 10)
    assert first.season == 2025
    assert first.team_name == "Los Angeles Dodgers"
    assert first.opponent_name == "Arizona Diamondbacks"
    assert first.is_home is True


def test_pitching_game_log_sorted_oldest_first(mocked_responses):
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)

    appearances = game_log(808963, 2025)

    dates = [a.game_date for a in appearances]
    assert dates == sorted(dates)


def test_pitching_game_log_empty_season(mocked_responses):
    register_game_log(mocked_responses, 808963, "game_log_empty.json", season=2024)

    appearances = game_log(808963, 2024)

    assert appearances == []


def test_game_log_seasons_merges_and_sorts(mocked_responses):
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    register_game_log(mocked_responses, 808963, "game_log_empty.json", season=2024)

    appearances = game_log_seasons(808963, [2025, 2024])

    assert len(appearances) == 3
    assert [a.game_pk for a in appearances] == [1001, 1002, 1003]


def test_hitting_game_log_requests_the_hitting_group(mocked_responses):
    # Registered to match `group=hitting` only, so a request for the pitching
    # log would 404 instead of quietly returning a hitter's games.
    register_game_log(
        mocked_responses, 500001, "hitting_game_log_2025.json", season=2025, group="hitting"
    )

    appearances = game_log(500001, 2025, group="hitting")

    assert [a.game_pk for a in appearances] == [1001, 1003, 1004]
    assert appearances[0].game_date == date(2025, 7, 10)
