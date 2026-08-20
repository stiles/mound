"""Tests for the command-line interface.

These run the Typer app in-process against the same mocked HTTP responses
the library tests use, so they cover what a user actually sees printed --
column layout included -- rather than only the collection underneath it.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from mound.cli import app
from tests.conftest import register_game_log, register_gf, register_person


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _register_game_1001(mocked_responses) -> None:
    register_person(mocked_responses, 808963, "people_808963.json")
    register_gf(mocked_responses, 1001, "gf_game_1001.json")


def _headline(result) -> str:
    return result.stdout.splitlines()[0]


def _header(result) -> list[str]:
    return result.stdout.splitlines()[1].split()


def test_pitches_table_shows_the_at_bat_and_count(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001"])

    assert result.exit_code == 0
    assert _header(result) == [
        "inn",
        "ab",
        "count",
        "batter",
        "pitch",
        "velo",
        "zone",
        "call",
        "result",
    ]
    assert "0-2" in result.stdout  # the 0-2 splitter that ended at-bat 1
    assert "5 pitch(es) total." in result.stdout


def test_pitches_headline_carries_what_every_row_shares(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001"])

    assert _headline(result) == "Roki Sasaki · 2025-07-10 · game 1001"
    assert "2025-07-10" not in result.stdout.splitlines()[2]  # not repeated per row


def test_pitches_promotes_a_single_pitch_type_out_of_the_rows(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--pitch", "splitter"])

    # Only one batter saw a splitter in this game, and both of them landed in
    # zone 7, so those columns collapse into the headline as well, leaving
    # only what actually differs between the two pitches.
    assert _headline(result) == (
        "Roki Sasaki · to Test Batter 1 · 2025-07-10 · game 1001 · splitter · zone 7"
    )
    assert _header(result) == ["inn", "ab", "count", "velo", "call", "result"]


def test_pitches_promotes_a_single_batter_out_of_the_rows(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--batter", "Batter 2"])

    assert _headline(result) == "Roki Sasaki · to Test Batter 2 · 2025-07-10 · game 1001"
    assert "batter" not in _header(result)


def test_pitches_keeps_the_date_in_the_rows_across_games(mocked_responses, runner):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    for game_pk in (1001, 1002, 1003):
        register_gf(mocked_responses, game_pk, f"gf_game_{game_pk}.json")

    result = runner.invoke(
        app, ["pitches", "808963", "--since", "2025-07-01", "--until", "2025-08-31"]
    )

    assert _headline(result) == "Roki Sasaki · 2025-07-10 to 2025-08-15 · 3 games"
    assert _header(result)[0] == "date"


def test_pitches_season_pulls_every_game_in_that_year(mocked_responses, runner):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    for game_pk in (1001, 1002, 1003):
        register_gf(mocked_responses, game_pk, f"gf_game_{game_pk}.json")

    result = runner.invoke(app, ["pitches", "808963", "--season", "2025"])

    assert result.exit_code == 0
    assert _headline(result) == "Roki Sasaki · 2025-07-10 to 2025-08-15 · 3 games"


def test_pitches_filters_by_zone(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--zone", "7,12"])

    assert result.exit_code == 0
    assert "3 pitch(es) total." in result.stdout  # two in zone 7, one in 12


def test_pitches_rejects_a_zone_that_does_not_exist(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--zone", "10"])

    assert result.exit_code == 1
    assert "there is no 10" in result.output


def test_pitches_says_how_many_rows_it_held_back(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--limit", "2"])

    assert "Showing 2 of 5 pitch(es)." in result.stdout


def test_pitches_table_prints_each_result_once(mocked_responses, runner):
    # The feed repeats "Strikeout" on all three pitches of the at-bat. Only
    # the row that ended it should say so.
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001"])

    assert result.stdout.count("Strikeout") == 1
    assert result.stdout.count("Walk") == 1


def test_pitches_ends_at_bat_prints_one_row_per_at_bat(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--ends-at-bat"])

    assert result.exit_code == 0
    assert "2 pitch(es) total." in result.stdout
    assert result.stdout.count("Strikeout") == 1
    assert result.stdout.count("Walk") == 1


def test_pitches_ends_at_bat_composes_with_other_filters(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(
        app, ["pitches", "808963", "--game", "1001", "--pitch", "fastball", "--ends-at-bat"]
    )

    assert result.exit_code == 0
    assert "1 pitch(es) total." in result.stdout
    assert "Walk" in result.stdout
    assert "Strikeout" not in result.stdout


def test_faced_table_shows_which_pitcher_threw_each_pitch(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(app, ["faced", "500001", "--game", "1004"])

    assert result.exit_code == 0
    assert _headline(result) == "Test Batter 1 · 2025-08-20 · game 1004"
    assert "pitcher" in _header(result)
    assert "4 pitch(es) total." in result.stdout


def test_faced_promotes_a_single_pitcher_out_of_the_rows(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(app, ["faced", "500001", "--game", "1004", "--pitcher", "Roki Sasaki"])

    assert result.exit_code == 0
    assert _headline(result) == "Test Batter 1 · vs Roki Sasaki · 2025-08-20 · game 1004"
    assert "pitcher" not in _header(result)
    assert "2 pitch(es) total." in result.stdout


def test_faced_filters_by_pitch_type(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(app, ["faced", "500001", "--game", "1004", "--pitch", "splitter"])

    assert result.exit_code == 0
    assert "1 pitch(es) total." in result.stdout


def test_faced_season_pulls_every_game_a_batter_played(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_game_log(
        mocked_responses, 500001, "hitting_game_log_2025.json", season=2025, group="hitting"
    )
    for game_pk in (1001, 1003, 1004):
        register_gf(mocked_responses, game_pk, f"gf_game_{game_pk}.json")

    result = runner.invoke(app, ["faced", "500001", "--season", "2025"])

    assert result.exit_code == 0
    assert "3 games" in _headline(result)


def test_games_lists_appearances_without_fetching_pitches(mocked_responses, runner):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    # No `register_gf` calls: a bare game list should never reach Savant.

    result = runner.invoke(app, ["games", "808963", "--season", "2025"])

    assert result.exit_code == 0
    assert _headline(result) == "Roki Sasaki · 3 game(s)"
    assert "1001" in result.stdout
    assert "Arizona Diamondbacks" in result.stdout
    assert "home" in result.stdout
    assert "away" in result.stdout


def test_games_last_n_selects_most_recent(mocked_responses, runner):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)

    result = runner.invoke(app, ["games", "808963", "--last", "2", "--season", "2025"])

    assert result.exit_code == 0
    assert _headline(result) == "Roki Sasaki · 2 game(s)"
    assert "1001" not in result.stdout
    assert "1002" in result.stdout
    assert "1003" in result.stdout


def test_faced_games_lists_appearances_for_a_batter(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_game_log(
        mocked_responses, 500001, "hitting_game_log_2025.json", season=2025, group="hitting"
    )

    result = runner.invoke(app, ["faced-games", "500001", "--season", "2025"])

    assert result.exit_code == 0
    assert _headline(result) == "Test Batter 1 · 3 game(s)"
    assert "1004" in result.stdout


def test_faced_mix_prints_pitch_type_percentages(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(app, ["faced-mix", "500001", "--game", "1004"])

    assert result.exit_code == 0
    # 4 pitches faced: 2 sliders, 1 four-seamer, 1 splitter.
    assert "slider" in result.stdout
    assert "50.0%" in result.stdout


def test_faced_results_breaks_down_by_pitch_type(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(app, ["faced-results", "500001", "--game", "1004"])

    assert result.exit_code == 0
    assert "slider" in result.stdout


def test_faced_arsenal_scopes_to_one_pitcher(mocked_responses, runner):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    result = runner.invoke(
        app, ["faced-arsenal", "500001", "--game", "1004", "--pitcher", "Roki Sasaki"]
    )

    assert result.exit_code == 0
    assert "whiff_rate" in result.stdout
    assert "chase_rate" in result.stdout


def test_faced_zone_writes_a_plot(mocked_responses, runner, tmp_path):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")
    out = tmp_path / "faced_zone.png"

    result = runner.invoke(app, ["faced-zone", "500001", "--game", "1004", "--out", str(out)])

    assert result.exit_code == 0
    assert out.exists()


def test_pitches_reports_no_matches_without_failing(mocked_responses, runner):
    _register_game_1001(mocked_responses)

    result = runner.invoke(app, ["pitches", "808963", "--game", "1001", "--pitch", "curveball"])

    assert result.exit_code == 0
    assert "No pitches found for the given filters." in result.stdout


@pytest.mark.parametrize(
    "options", [["--kind", "zones"], ["--grid"], ["--kind", "zones", "--grid"]]
)
def test_zone_writes_a_plot_for_each_way_of_drawing_the_grid(
    mocked_responses, runner, tmp_path, options
):
    _register_game_1001(mocked_responses)
    out = tmp_path / "zone.png"

    result = runner.invoke(app, ["zone", "808963", "--game", "1001", "--out", str(out), *options])

    assert result.exit_code == 0
    assert out.exists()


def test_zone_names_the_kinds_it_knows_when_given_one_it_does_not(
    mocked_responses, runner, tmp_path
):
    _register_game_1001(mocked_responses)

    result = runner.invoke(
        app,
        ["zone", "808963", "--game", "1001", "--kind", "grid", "--out", str(tmp_path / "zone.png")],
    )

    assert result.exit_code != 0
    assert "'zones'" in result.stderr
