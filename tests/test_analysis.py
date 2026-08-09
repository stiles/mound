from __future__ import annotations

import pytest

from mound.models import Pitch
from mound.pitches import PitchCollection


def _pitch(pitch_type_code, pitch_type, is_strike, game_date="2025-07-01", **overrides) -> Pitch:
    defaults = dict(
        game_pk=1,
        game_date=game_date,
        pitch_id=None,
        at_bat_number=1,
        pitch_number=1,
        inning=1,
        half_inning="top",
        pitcher_id=808963,
        pitcher_name="Roki Sasaki",
        batter_id=1,
        batter_name="Test Batter",
        batter_stand="R",
        pitch_type_code=pitch_type_code,
        pitch_type=pitch_type,
        velocity=95.0,
        plate_x=0.0,
        plate_z=2.5,
        sz_top=3.4,
        sz_bot=1.6,
        in_zone=True,
        balls=0,
        strikes=0,
        pitch_call="called_strike" if is_strike else "ball",
        call_description=None,
        is_strike=is_strike,
        is_swing=False,
        is_whiff=False,
        at_bat_result=None,
        description=None,
    )
    defaults.update(overrides)
    return Pitch(**defaults)


@pytest.fixture
def sample_collection() -> PitchCollection:
    # 4 fastballs (3 strikes), 3 sliders (2 strikes), 3 splitters (all strikes) = 10 pitches
    pitches = (
        [_pitch("FF", "four-seam fastball", is_strike) for is_strike in [True, True, True, False]]
        + [_pitch("SL", "slider", is_strike) for is_strike in [True, True, False]]
        + [_pitch("FS", "splitter", is_strike) for is_strike in [True, True, True]]
    )
    return PitchCollection(pitches)


def test_pitch_mix_percentages(sample_collection):
    mix = sample_collection.pitch_mix()

    assert mix["four-seam fastball"] == 40.0
    assert mix["slider"] == 30.0
    assert mix["splitter"] == 30.0
    assert mix.sum() == pytest.approx(100.0)


def test_pitch_mix_sorted_descending(sample_collection):
    mix = sample_collection.pitch_mix()

    assert list(mix.index)[0] == "four-seam fastball"


def test_pitch_mix_empty_collection():
    mix = PitchCollection().pitch_mix()

    assert mix.empty


def test_strike_rate_overall(sample_collection):
    # 8 strikes out of 10 pitches
    assert sample_collection.strike_rate() == 80.0


def test_strike_rate_by_pitch_type(sample_collection):
    rates = sample_collection.strike_rate(by_pitch_type=True)

    assert rates["splitter"] == 100.0
    assert rates["four-seam fastball"] == 75.0
    assert rates["slider"] == pytest.approx(66.7, abs=0.1)


def test_strike_rate_empty_collection():
    import math

    rate = PitchCollection().strike_rate()

    assert math.isnan(rate)


def test_swing_rate_overall():
    pitches = [
        _pitch("FF", "four-seam fastball", True, is_swing=False),  # called strike, no swing
        _pitch("FF", "four-seam fastball", True, is_swing=True, is_whiff=False),  # foul
        _pitch("FF", "four-seam fastball", False, is_swing=False),  # ball
        _pitch("FF", "four-seam fastball", True, is_swing=True, is_whiff=True),  # swinging strike
    ]
    collection = PitchCollection(pitches)

    assert collection.swing_rate() == 50.0


def test_swing_rate_by_pitch_type():
    pitches = [
        _pitch("FF", "four-seam fastball", True, is_swing=True, is_whiff=True),
        _pitch("FF", "four-seam fastball", False, is_swing=False),
        _pitch("SL", "slider", True, is_swing=True, is_whiff=False),
        _pitch("SL", "slider", True, is_swing=True, is_whiff=False),
    ]
    collection = PitchCollection(pitches)

    rates = collection.swing_rate(by_pitch_type=True)

    assert rates["four-seam fastball"] == 50.0
    assert rates["slider"] == 100.0


def test_whiff_rate_is_of_swings_not_all_pitches():
    # 4 swings (2 whiffs, 2 contact) + 2 takes -- whiff rate should be
    # 50% (2 of 4 swings), not 33% (2 of 6 pitches).
    pitches = (
        [_pitch("SL", "slider", True, is_swing=True, is_whiff=True) for _ in range(2)]
        + [_pitch("SL", "slider", True, is_swing=True, is_whiff=False) for _ in range(2)]
        + [_pitch("SL", "slider", True, is_swing=False) for _ in range(2)]
    )
    collection = PitchCollection(pitches)

    assert collection.whiff_rate() == 50.0


def test_whiff_rate_by_pitch_type():
    pitches = [
        _pitch("FS", "splitter", True, is_swing=True, is_whiff=True),
        _pitch("FS", "splitter", True, is_swing=True, is_whiff=False),
        _pitch("SL", "slider", True, is_swing=True, is_whiff=False),
        _pitch("SL", "slider", True, is_swing=True, is_whiff=False),
    ]
    collection = PitchCollection(pitches)

    rates = collection.whiff_rate(by_pitch_type=True)

    assert rates["splitter"] == 50.0
    assert rates["slider"] == 0.0


def test_whiff_rate_no_swings_is_nan():
    import math

    pitches = [_pitch("FF", "four-seam fastball", True, is_swing=False)]
    collection = PitchCollection(pitches)

    assert math.isnan(collection.whiff_rate())


def test_swing_rate_empty_collection():
    import math

    assert math.isnan(PitchCollection().swing_rate())


def test_pitch_metrics_by_pitch_type():
    pitches = [
        _pitch(
            "FF",
            "four-seam fastball",
            True,
            velocity=99.0,
            spin_rate=2400.0,
            horizontal_break=10.0,
            induced_vertical_break=16.0,
        ),
        _pitch(
            "FF",
            "four-seam fastball",
            True,
            velocity=97.0,
            spin_rate=2200.0,
            horizontal_break=12.0,
            induced_vertical_break=18.0,
        ),
        _pitch(
            "FS",
            "splitter",
            True,
            velocity=90.0,
            spin_rate=800.0,
            horizontal_break=5.0,
            induced_vertical_break=1.0,
        ),
    ]
    collection = PitchCollection(pitches)

    metrics = collection.pitch_metrics()

    assert metrics.loc["four-seam fastball", "pitches"] == 2
    assert metrics.loc["four-seam fastball", "velocity"] == 98.0
    assert metrics.loc["four-seam fastball", "spin_rate"] == 2300.0
    assert metrics.loc["splitter", "velocity"] == 90.0


def test_pitch_metrics_overall():
    pitches = [
        _pitch("FF", "four-seam fastball", True, velocity=99.0, spin_rate=2400.0),
        _pitch("FS", "splitter", True, velocity=91.0, spin_rate=800.0),
    ]
    collection = PitchCollection(pitches)

    metrics = collection.pitch_metrics(by_pitch_type=False)

    assert metrics["pitches"] == 2.0
    assert metrics["velocity"] == 95.0


def test_pitch_metrics_empty_collection():
    metrics = PitchCollection().pitch_metrics()

    assert metrics.empty


def test_usage_rate_by_game_date():
    pitches = [
        _pitch("FF", "four-seam fastball", True, game_date="2025-07-01"),
        _pitch("FS", "splitter", True, game_date="2025-07-01"),
        _pitch("FF", "four-seam fastball", True, game_date="2025-07-15"),
        _pitch("FF", "four-seam fastball", True, game_date="2025-07-15"),
        _pitch("FS", "splitter", True, game_date="2025-07-15"),
    ]
    collection = PitchCollection(pitches)

    usage = collection.usage_rate(by="game_date")

    assert usage.loc["2025-07-01", "splitter"] == 50.0
    assert usage.loc["2025-07-15", "splitter"] == pytest.approx(33.3, abs=0.1)
