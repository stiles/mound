"""Shared pytest fixtures: fixture loading and HTTP mocking helpers.

Every test in this suite runs against mocked HTTP responses (via the
`responses` library) so the suite doesn't depend on network access or live
MLB endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses as responses_lib

from mound import config

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def load_text_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


@pytest.fixture
def mocked_responses():
    # `assert_all_requests_are_fired=False` because several tests share a
    # helper that registers more games than any single query actually needs.
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


def register_people_search(rsps: responses_lib.RequestsMock, fixture_name: str) -> None:
    rsps.add(
        responses_lib.GET,
        f"{config.STATSAPI_V1}/people/search",
        json=load_fixture(fixture_name),
        status=200,
    )


def register_person(rsps: responses_lib.RequestsMock, player_id: int, fixture_name: str) -> None:
    rsps.add(
        responses_lib.GET,
        f"{config.STATSAPI_V1}/people/{player_id}",
        json=load_fixture(fixture_name),
        status=200,
    )


def register_game_log(
    rsps: responses_lib.RequestsMock, player_id: int, fixture_name: str, season: int
) -> None:
    rsps.add(
        responses_lib.GET,
        f"{config.STATSAPI_V1}/people/{player_id}/stats",
        json=load_fixture(fixture_name),
        status=200,
        match=[
            responses_lib.matchers.query_param_matcher(
                {"stats": "gameLog", "group": "pitching", "season": str(season)}
            )
        ],
    )


def register_gf(rsps: responses_lib.RequestsMock, game_pk: int, fixture_name: str) -> None:
    rsps.add(
        responses_lib.GET,
        config.SAVANT_GAMEFEED_URL,
        json=load_fixture(fixture_name),
        status=200,
        match=[responses_lib.matchers.query_param_matcher({"game_pk": str(game_pk)})],
    )
