from __future__ import annotations

import pytest

from mound.players import (
    AmbiguousPlayerError,
    PlayerNotFoundError,
    get_player,
    resolve_player,
    search_players,
)
from tests.conftest import register_people_search, register_person


def test_search_players_returns_all_matches(mocked_responses):
    register_people_search(mocked_responses, "people_search_sasaki.json")

    results = search_players("Sasaki")

    assert len(results) == 2
    assert results[0].id == 808963
    assert results[0].full_name == "Roki Sasaki"
    assert results[0].is_pitcher
    assert results[0].team_name == "Los Angeles Dodgers"
    assert not results[1].is_pitcher


def test_get_player_by_id(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")

    player = get_player(808963)

    assert player.id == 808963
    assert player.full_name == "Roki Sasaki"
    assert player.pitch_hand == "R"


def test_resolve_player_with_numeric_id(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")

    player = resolve_player(808963)

    assert player.id == 808963


def test_resolve_player_with_numeric_string_id(mocked_responses):
    register_person(mocked_responses, 808963, "people_808963.json")

    player = resolve_player("808963")

    assert player.id == 808963


def test_resolve_player_single_match(mocked_responses):
    register_people_search(mocked_responses, "people_search_single.json")

    player = resolve_player("Roki Sasaki")

    assert player.id == 808963


def test_resolve_player_prefers_pitcher_when_ambiguous(mocked_responses):
    register_people_search(mocked_responses, "people_search_sasaki.json")

    player = resolve_player("Sasaki")

    assert player.id == 808963
    assert player.is_pitcher


def test_resolve_player_raises_when_truly_ambiguous(mocked_responses):
    register_people_search(mocked_responses, "people_search_two_pitchers.json")

    with pytest.raises(AmbiguousPlayerError) as exc_info:
        resolve_player("Sasaki")

    assert len(exc_info.value.candidates) == 2


def test_resolve_player_not_found(mocked_responses):
    register_people_search(mocked_responses, "people_search_none.json")

    with pytest.raises(PlayerNotFoundError):
        resolve_player("Nobody Real")
