from __future__ import annotations

from mound.savant import game_pitches_for_pitcher
from tests.conftest import register_gf


def test_game_pitches_for_pitcher_normalizes_fields(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    assert len(pitches) == 5
    first = pitches[0]
    assert first.game_pk == 1001
    assert first.game_date == "2025-07-10"
    assert first.pitcher_id == 808963
    assert first.pitch_type_code == "FF"
    assert first.pitch_type == "four-seam fastball"
    assert first.velocity == 99.1
    assert first.is_strike is True  # called_strike counts as a strike


def test_game_pitches_for_pitcher_normalizes_batter_stand(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    assert [p.batter_stand for p in pitches[:3]] == ["L", "L", "L"]
    assert [p.batter_stand for p in pitches[3:]] == ["R", "R"]


def test_game_pitches_computes_in_zone(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    # First pitch: plate_x=-0.2, plate_z=2.5, sz_top=3.4, sz_bot=1.6 -> inside the zone
    assert pitches[0].in_zone is True


def test_game_pitches_for_pitcher_sorted_by_at_bat_and_pitch_number(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    order = [(p.at_bat_number, p.pitch_number) for p in pitches]
    assert order == sorted(order)


def test_game_pitches_for_unknown_pitcher_returns_empty(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 999999)

    assert pitches == []


def test_game_pitches_reads_from_away_pitchers(mocked_responses):
    register_gf(mocked_responses, 1002, "gf_game_1002.json")

    pitches = game_pitches_for_pitcher(1002, 808963)

    assert len(pitches) == 5
    assert all(p.game_pk == 1002 for p in pitches)
