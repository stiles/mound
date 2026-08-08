"""Resolve pitchers by name or MLB player ID using the MLB Stats API.

Baseball language first: users should be able to pass a familiar name like
"Roki Sasaki" rather than needing to know his MLB player ID (808963) ahead
of time.
"""

from __future__ import annotations

from dataclasses import dataclass

from mound import config
from mound.http import get_json


class PlayerNotFoundError(Exception):
    """Raised when no player matches the given name or ID."""


class AmbiguousPlayerError(Exception):
    """Raised when a name matches multiple players and none is an exact match."""

    def __init__(self, name: str, candidates: list[Player]):
        self.name = name
        self.candidates = candidates
        names = ", ".join(f"{p.full_name} ({p.id})" for p in candidates)
        super().__init__(f"Multiple players match '{name}': {names}. Try an MLB player ID instead.")


@dataclass
class Player:
    """A resolved MLB person, e.g. a pitcher."""

    id: int
    full_name: str
    primary_position: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    pitch_hand: str | None = None
    active: bool | None = None

    @property
    def is_pitcher(self) -> bool:
        return self.primary_position == "Pitcher"


def _player_from_person(person: dict) -> Player:
    team = person.get("currentTeam") or {}
    position = (person.get("primaryPosition") or {}).get("name")
    pitch_hand = (person.get("pitchHand") or {}).get("code")
    return Player(
        id=person["id"],
        full_name=person.get("fullName", ""),
        primary_position=position,
        team_id=team.get("id"),
        team_name=team.get("name"),
        pitch_hand=pitch_hand,
        active=person.get("active"),
    )


def search_players(name: str) -> list[Player]:
    """Search the MLB Stats API for people matching ``name``.

    Returns an empty list if nothing matches. Matching is handled server-side
    by the Stats API and tends to be forgiving of partial names.
    """
    url = f"{config.STATSAPI_V1}/people/search"
    data = get_json(url, params={"names": name, "hydrate": "currentTeam"})
    people = data.get("people", [])
    return [_player_from_person(p) for p in people]


def get_player(player_id: int) -> Player:
    """Fetch a single player by MLB player ID, hydrated with their current team."""
    url = f"{config.STATSAPI_V1}/people/{player_id}"
    data = get_json(url, params={"hydrate": "currentTeam"})
    people = data.get("people", [])
    if not people:
        raise PlayerNotFoundError(f"No player found with ID {player_id}")
    return _player_from_person(people[0])


def resolve_player(name_or_id: str | int) -> Player:
    """Resolve a pitcher from a name or an MLB player ID.

    - If ``name_or_id`` is (or looks like) an integer, it's treated as an MLB
      player ID and fetched directly.
    - Otherwise it's treated as a name. An exact (case-insensitive) full-name
      match is preferred; if there's exactly one candidate, that is used;
      multiple ambiguous matches raise :class:`AmbiguousPlayerError`.
    """
    looks_like_id = isinstance(name_or_id, str) and name_or_id.strip().isdigit()
    if isinstance(name_or_id, int) or looks_like_id:
        return get_player(int(name_or_id))

    name = str(name_or_id).strip()
    candidates = search_players(name)
    if not candidates:
        raise PlayerNotFoundError(f"No player found matching '{name}'")

    exact = [p for p in candidates if p.full_name.lower() == name.lower()]
    if len(exact) == 1:
        return exact[0]

    if len(candidates) == 1:
        return candidates[0]

    # Prefer pitchers when the name is otherwise ambiguous (e.g. multiple
    # "Sasaki"s, only one of whom pitches).
    pitchers = [p for p in candidates if p.is_pitcher]
    if len(pitchers) == 1:
        return pitchers[0]

    raise AmbiguousPlayerError(name, candidates)
