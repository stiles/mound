from __future__ import annotations

from mound.pitches import Pitcher
from tests.conftest import register_game_log, register_gf, register_person


def _register_roki_with_all_games(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    register_gf(mocked_responses, 1001, "gf_game_1001.json")
    register_gf(mocked_responses, 1002, "gf_game_1002.json")
    register_gf(mocked_responses, 1003, "gf_game_1003.json")


def test_pitcher_resolves_identity(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")

    pitcher = Pitcher(808963)

    assert pitcher.id == 808963
    assert pitcher.name == "Roki Sasaki"


def test_pitches_last_n_selects_most_recent_games(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=2, season=2025)

    # Games 1002 (5 pitches) + 1003 (6 pitches) = 11; game 1001 excluded.
    assert len(collection) == 11
    assert set(collection.games) == {1002, 1003}


def test_pitches_since_until_filters_by_date(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(since="2025-07-15", until="2025-08-10")

    assert set(collection.games) == {1002}


def test_pitches_specific_game(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    collection = Pitcher(808963).pitches(game=1001)

    assert len(collection) == 5
    assert collection.games == [1001]


def test_pitches_pitch_type_shortcut_filters_at_retrieval(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025, pitch_type="splitter")

    assert len(collection) > 0
    assert all(p.pitch_type_code == "FS" for p in collection)


def test_collection_filter_by_pitch_type_is_alias_tolerant(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    splitters = collection.filter(pitch_type="split-finger")

    assert len(splitters) == 5  # 2 + 1 + 2 splitters across games 1001/1002/1003, per fixtures
    assert all(p.pitch_type == "splitter" for p in splitters)


def test_collection_filter_returns_new_collection_and_leaves_original(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    original_len = len(collection)
    filtered = collection.filter(pitch_type="slider")

    assert len(filtered) < original_len
    assert len(collection) == original_len  # original untouched


def test_collection_filter_by_game(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    game_1002_only = collection.filter(game=1002)

    assert game_1002_only.games == [1002]
    assert len(game_1002_only) == 5


def test_pitches_stand_shortcut_filters_at_retrieval(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025, stand="left")

    assert len(collection) == 9  # 3 LHB pitches per game across games 1001/1002/1003
    assert all(p.batter_stand == "L" for p in collection)


def test_collection_filter_by_stand_is_alias_tolerant(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    righties = collection.filter(stand="RHB")

    assert len(righties) == 7  # 2 + 2 + 3 RHB pitches across games 1001/1002/1003
    assert all(p.batter_stand == "R" for p in righties)


def test_empty_collection_has_no_pitches():
    from mound.pitches import PitchCollection

    collection = PitchCollection()

    assert collection.empty
    assert len(collection) == 0
    assert collection.to_frame().empty
