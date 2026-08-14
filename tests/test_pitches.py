from __future__ import annotations

from mound.pitches import Batter, Pitcher
from tests.conftest import register_game_log, register_gf, register_person


def _register_roki_with_all_games(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_game_log(mocked_responses, 808963, "game_log_2025.json", season=2025)
    register_gf(mocked_responses, 1001, "gf_game_1001.json")
    register_gf(mocked_responses, 1002, "gf_game_1002.json")
    register_gf(mocked_responses, 1003, "gf_game_1003.json")


def _register_batter_with_all_games(mocked_responses):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_game_log(
        mocked_responses, 500001, "hitting_game_log_2025.json", season=2025, group="hitting"
    )
    register_gf(mocked_responses, 1001, "gf_game_1001.json")
    register_gf(mocked_responses, 1003, "gf_game_1003.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")


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


def test_collection_filter_by_at_bat_number(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    collection = Pitcher(808963).pitches(game=1001)
    at_bat = collection.filter(at_bat_number=1)

    assert len(at_bat) > 0
    assert all(p.at_bat_number == 1 for p in at_bat)


def test_collection_filter_by_at_bat_and_pitch_number_selects_one_pitch(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    collection = Pitcher(808963).pitches(game=1001)
    one_pitch = collection.filter(at_bat_number=1, pitch_number=2)

    assert len(one_pitch) == 1
    assert one_pitch.pitches[0].pitch_id == "1001-1-2"


def test_pitches_at_bat_and_pitch_number_shortcuts_filter_at_retrieval(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_gf(mocked_responses, 1001, "gf_game_1001.json")

    collection = Pitcher(808963).pitches(game=1001, at_bat_number=1, pitch_number=2)

    assert len(collection) == 1
    assert collection.pitches[0].pitch_id == "1001-1-2"


def test_collection_filter_by_batter_id(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    vs_batter = collection.filter(batter=500002)

    assert len(vs_batter) == 7  # 2 + 2 + 3 pitches to batter 500002
    assert all(p.batter_id == 500002 for p in vs_batter)


def test_collection_filter_by_batter_name_is_partial(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    vs_batter = collection.filter(batter="batter 1")

    assert len(vs_batter) == 9  # 3 pitches per game to batter 500001
    assert all(p.batter_name == "Test Batter 1" for p in vs_batter)


def test_collection_filter_by_batter_ignores_accents(mocked_responses):
    from mound.pitches import PitchCollection
    from mound.savant import game_pitches_for_pitcher

    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    collection = PitchCollection(game_pitches_for_pitcher(1004, 700001))

    # The feed spells him "José Ramírez"; plain ASCII should still find him.
    assert len(collection.filter(batter="jose ramirez")) == 1
    assert len(collection.filter(batter="Ramirez")) == 1


def test_collection_filter_by_batter_accepts_a_mixed_list(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025)
    both = collection.filter(batter=[500001, "batter 2"])

    assert len(both) == len(collection)


def test_pitches_batter_shortcut_filters_at_retrieval(mocked_responses):
    _register_roki_with_all_games(mocked_responses)

    collection = Pitcher(808963).pitches(last=3, season=2025, batter="Test Batter 1")

    assert len(collection) == 9
    assert all(p.batter_id == 500001 for p in collection)


def test_batter_resolves_identity(mocked_responses):
    register_person(mocked_responses, 500001, "people_500001.json")

    batter = Batter(500001)

    assert batter.id == 500001
    assert batter.name == "Test Batter 1"


def test_batter_pitches_faced_come_from_every_pitcher(mocked_responses):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    collection = Batter(500001).pitches(game=1004)

    assert len(collection) == 4
    assert {p.pitcher_id for p in collection} == {808963, 700001}
    assert collection.batter.id == 500001
    assert collection.pitcher is None


def test_batter_pitches_last_n_uses_the_hitting_game_log(mocked_responses):
    _register_batter_with_all_games(mocked_responses)

    collection = Batter(500001).pitches(last=2, season=2025)

    # Games 1003 and 1004 -- the batter's two most recent, not the pitcher's.
    assert set(collection.games) == {1003, 1004}


def test_batter_pitches_filtered_to_one_pitcher_is_a_matchup(mocked_responses):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    collection = Batter(500001).pitches(game=1004, pitcher="Roki Sasaki")

    assert len(collection) == 2
    assert all(p.pitcher_id == 808963 for p in collection)


def test_batter_pitches_filter_by_pitcher_id(mocked_responses):
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    collection = Batter(500001).pitches(game=1004, pitcher=700001)

    assert len(collection) == 2
    assert all(p.pitcher_name == "Relief Pitcher" for p in collection)


def test_matchup_from_either_side_returns_the_same_pitches(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")
    register_person(mocked_responses, 500001, "people_500001.json")
    register_gf(mocked_responses, 1004, "gf_game_1004.json")

    from_pitcher = Pitcher(808963).pitches(game=1004, batter=500001)
    from_batter = Batter(500001).pitches(game=1004, pitcher=808963)

    assert [p.pitch_id for p in from_pitcher] == [p.pitch_id for p in from_batter]


def test_empty_collection_has_no_pitches():
    from mound.pitches import PitchCollection

    collection = PitchCollection()

    assert collection.empty
    assert len(collection) == 0
    assert collection.to_frame().empty
