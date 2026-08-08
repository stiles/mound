"""The normalized ``Pitch`` record and pitch-type vocabulary.

Baseball Savant's raw ``/gf`` payload uses short codes (``FF``, ``FS``, ...)
and inconsistent field names. This module defines the flat schema Mound
normalizes every pitch into, plus the vocabulary that lets users filter by
familiar names like ``"splitter"`` instead of memorizing Statcast codes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from mound.zone import is_in_zone

# Statcast pitch-type code -> canonical human-readable name.
PITCH_TYPE_NAMES: dict[str, str] = {
    "FF": "four-seam fastball",
    "FT": "two-seam fastball",
    "SI": "sinker",
    "FC": "cutter",
    "SL": "slider",
    "ST": "sweeper",
    "SV": "slurve",
    "CU": "curveball",
    "KC": "knuckle curve",
    "CS": "slow curve",
    "CH": "changeup",
    "FS": "splitter",
    "FO": "forkball",
    "SC": "screwball",
    "KN": "knuckleball",
    "EP": "eephus",
    "PO": "pitchout",
    "IN": "intentional ball",
    "UN": "unknown",
    "AB": "automatic ball",
}

# Common aliases users might type, mapped to the Statcast code they resolve
# to. Keys are matched case-insensitively with spaces/hyphens/underscores
# collapsed (see `normalize_pitch_type`).
PITCH_TYPE_ALIASES: dict[str, str] = {
    "fastball": "FF",
    "four seam": "FF",
    "four seam fastball": "FF",
    "4 seam": "FF",
    "two seam": "FT",
    "two seam fastball": "FT",
    "sinker": "SI",
    "cutter": "FC",
    "cut fastball": "FC",
    "slider": "SL",
    "sweeper": "ST",
    "sweeping slider": "ST",
    "slurve": "SV",
    "curveball": "CU",
    "curve": "CU",
    "knuckle curve": "KC",
    "knuckle curveball": "KC",
    "slow curve": "CS",
    "changeup": "CH",
    "change up": "CH",
    "splitter": "FS",
    "split finger": "FS",
    "split finger fastball": "FS",
    "forkball": "FO",
    "screwball": "SC",
    "knuckleball": "KN",
    "knuckler": "KN",
    "eephus": "EP",
}


_STAND_ALIASES: dict[str, str] = {
    "l": "L",
    "left": "L",
    "lhb": "L",
    "lhh": "L",
    "left handed": "L",
    "lefty": "L",
    "r": "R",
    "right": "R",
    "rhb": "R",
    "rhh": "R",
    "right handed": "R",
    "righty": "R",
}


def _normalize_key(text: str) -> str:
    return " ".join(text.strip().lower().replace("-", " ").replace("_", " ").split())


def normalize_stand(stand: str) -> str | None:
    """Resolve a user-supplied batter side to ``"L"``/``"R"``.

    Accepts ``"L"``, ``"lefty"``, ``"LHB"`` and similar variants,
    case-insensitively. Returns ``None`` if nothing matches.
    """
    if not stand:
        return None
    return _STAND_ALIASES.get(_normalize_key(stand))


def normalize_pitch_type(pitch_type: str) -> str | None:
    """Resolve a user-supplied pitch type (name, alias or code) to a Statcast code.

    Returns ``None`` if the input doesn't match anything known. Matching is
    case-insensitive and tolerant of hyphens/underscores/extra whitespace,
    e.g. ``"Four-Seam"``, ``"four_seam"`` and ``"FF"`` all resolve to ``"FF"``.
    """
    if not pitch_type:
        return None

    code = pitch_type.strip().upper()
    if code in PITCH_TYPE_NAMES:
        return code

    key = _normalize_key(pitch_type)
    if key in PITCH_TYPE_ALIASES:
        return PITCH_TYPE_ALIASES[key]

    for statcast_code, name in PITCH_TYPE_NAMES.items():
        if _normalize_key(name) == key:
            return statcast_code

    return None


@dataclass
class Pitch:
    """A single, normalized pitch."""

    game_pk: int
    game_date: str
    pitch_id: str | None
    at_bat_number: int | None
    pitch_number: int | None
    inning: int | None
    half_inning: str | None
    pitcher_id: int
    pitcher_name: str | None
    batter_id: int | None
    batter_name: str | None
    batter_stand: str | None
    pitch_type_code: str | None
    pitch_type: str | None
    velocity: float | None
    plate_x: float | None
    plate_z: float | None
    sz_top: float | None
    sz_bot: float | None
    in_zone: bool | None
    balls: int | None
    strikes: int | None
    pitch_call: str | None
    call_description: str | None
    is_strike: bool | None
    at_bat_result: str | None
    description: str | None

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]


# Savant `pitch_call` values that count as a strike for strike-rate purposes.
# Everything else (ball, hit-by-pitch, etc.) counts as not-a-strike.
STRIKE_CALLS = {
    "called_strike",
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "foul_bunt",
    "missed_bunt",
    "bunt_foul_tip",
    "hit_into_play",
}


def pitch_from_savant(raw: dict) -> Pitch:
    """Build a normalized :class:`Pitch` from one entry of a Savant ``/gf`` pitcher list."""
    pitch_type_code = raw.get("pitch_type")
    plate_x = raw.get("plate_x", raw.get("px"))
    plate_z = raw.get("plate_z", raw.get("pz"))
    sz_top = raw.get("sz_top")
    sz_bot = raw.get("sz_bot")
    pitch_call = raw.get("pitch_call")

    game_pk_raw = raw.get("game_pk")

    return Pitch(
        game_pk=int(game_pk_raw) if game_pk_raw is not None else None,
        game_date=raw.get("game_date") or "",
        pitch_id=raw.get("play_id"),
        at_bat_number=raw.get("ab_number"),
        pitch_number=raw.get("pitch_number"),
        inning=raw.get("inning"),
        half_inning=raw.get("half_inning"),
        pitcher_id=raw.get("pitcher"),
        pitcher_name=raw.get("pitcher_name"),
        batter_id=raw.get("batter"),
        batter_name=raw.get("batter_name"),
        batter_stand=normalize_stand(raw.get("stand")) if raw.get("stand") else None,
        pitch_type_code=pitch_type_code,
        pitch_type=PITCH_TYPE_NAMES.get(pitch_type_code, pitch_type_code),
        velocity=raw.get("start_speed"),
        plate_x=plate_x,
        plate_z=plate_z,
        sz_top=sz_top,
        sz_bot=sz_bot,
        in_zone=is_in_zone(plate_x, plate_z, sz_top, sz_bot),
        balls=raw.get("pre_balls", raw.get("balls")),
        strikes=raw.get("pre_strikes", raw.get("strikes")),
        pitch_call=pitch_call,
        call_description=raw.get("call_name") or raw.get("description"),
        is_strike=(pitch_call in STRIKE_CALLS) if pitch_call is not None else None,
        at_bat_result=raw.get("result"),
        description=raw.get("des"),
    )
