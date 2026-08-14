from __future__ import annotations

from mound.cache import FileCache
from mound.savant import fetch_game_feed, game_pitches_for_batter, game_pitches_for_pitcher
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
    assert first.is_swing is False  # ...but a take, not a swing
    assert first.is_whiff is False


def test_game_pitches_for_pitcher_normalizes_swing_and_whiff(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    assert pitches[1].pitch_call == "swinging_strike"
    assert pitches[1].is_swing is True
    assert pitches[1].is_whiff is True  # missed the ball entirely

    assert pitches[3].pitch_call == "foul"
    assert pitches[3].is_swing is True
    assert pitches[3].is_whiff is False  # contact, just foul

    assert pitches[2].pitch_call == "ball"
    assert pitches[2].is_swing is False
    assert pitches[2].is_whiff is False


def test_game_pitches_for_pitcher_normalizes_movement_fields(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    pitches = game_pitches_for_pitcher(1001, 808963)

    first = pitches[0]
    assert first.spin_rate == 2450
    assert first.release_extension == 6.7
    assert first.release_pos_x == -1.6
    assert first.release_pos_z == 5.9
    assert first.horizontal_break == 5.1
    assert first.induced_vertical_break == 16.2

    # Fixtures without these keys should parse fine, just leaving them None
    # rather than raising or defaulting to 0 -- e.g. older/untracked pitches.
    second = pitches[1]
    assert second.spin_rate is None
    assert second.release_extension is None


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


def test_game_pitches_for_batter_spans_pitching_changes(mocked_responses):
    # Game 1004's feed lists the reliever before the starter, so this also
    # covers ordering by at-bat rather than by whichever arm the feed
    # happened to index first.
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    pitches = game_pitches_for_batter(1004, 500001)

    assert len(pitches) == 4
    assert all(p.batter_id == 500001 for p in pitches)
    assert [p.pitcher_id for p in pitches] == [808963, 808963, 700001, 700001]
    order = [(p.at_bat_number, p.pitch_number) for p in pitches]
    assert order == sorted(order)


def test_game_pitches_for_batter_who_did_not_play_returns_empty(mocked_responses):
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    assert game_pitches_for_batter(1004, 999999) == []


def test_fetch_game_feed_second_call_hits_cache_not_network(mocked_responses, tmp_path):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")
    cache = FileCache(tmp_path)

    fetch_game_feed(1001, cache=cache)
    assert len(mocked_responses.calls) == 1

    fetch_game_feed(1001, cache=cache)
    assert len(mocked_responses.calls) == 1  # second call served from cache


def test_fetch_game_feed_without_cache_hits_network_every_time(mocked_responses):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    fetch_game_feed(1001)
    fetch_game_feed(1001)

    assert len(mocked_responses.calls) == 2


def test_game_pitches_for_pitcher_uses_cache(mocked_responses, tmp_path):
    register_gf(mocked_responses, 1001, "gf_game_1001.json")
    cache = FileCache(tmp_path)

    first = game_pitches_for_pitcher(1001, 808963, cache=cache)
    second = game_pitches_for_pitcher(1001, 808963, cache=cache)

    assert len(mocked_responses.calls) == 1
    assert len(first) == len(second) == 5
