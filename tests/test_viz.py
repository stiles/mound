from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pytest

from mound.models import Pitch
from mound.pitches import PitchCollection
from mound.viz import plot_zone


def _pitch(plate_x, plate_z, batter_stand, pitch_type="four-seam fastball") -> Pitch:
    return Pitch(
        game_pk=1,
        game_date="2025-07-01",
        pitch_id=None,
        at_bat_number=1,
        pitch_number=1,
        inning=1,
        half_inning="top",
        pitcher_id=808963,
        pitcher_name="Roki Sasaki",
        batter_id=1,
        batter_name="Test Batter",
        batter_stand=batter_stand,
        pitch_type_code="FF" if pitch_type == "four-seam fastball" else "FS",
        pitch_type=pitch_type,
        velocity=95.0,
        plate_x=plate_x,
        plate_z=plate_z,
        sz_top=3.4,
        sz_bot=1.6,
        in_zone=True,
        balls=0,
        strikes=0,
        pitch_call="called_strike",
        call_description=None,
        is_strike=True,
        at_bat_result=None,
        description=None,
    )


@pytest.fixture
def mixed_stand_collection() -> PitchCollection:
    pitches = (
        [_pitch(-0.3, 2.5, "L") for _ in range(3)]
        + [_pitch(0.4, 2.2, "R") for _ in range(5)]
    )
    return PitchCollection(pitches)


def test_split_by_stand_returns_one_axes_per_side(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, split_by="stand")

    assert len(axes) == 2


def test_split_by_stand_orders_left_before_right(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, split_by="stand")

    titles = [ax.get_title(loc="left") for ax in axes]
    assert "LHB" in titles[0]
    assert "RHB" in titles[1]


def test_split_by_stand_panel_titles_include_pitch_counts(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, split_by="stand")

    titles = [ax.get_title(loc="left") for ax in axes]
    assert "n=3" in titles[0]
    assert "n=5" in titles[1]


def test_split_by_accepts_batter_stand_alias(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, split_by="batter_stand")

    assert len(axes) == 2


def test_split_by_unknown_column_raises(mixed_stand_collection):
    with pytest.raises(ValueError, match="Cannot split_by"):
        plot_zone(mixed_stand_collection, split_by="not_a_real_column")


def test_split_by_with_existing_ax_raises(mixed_stand_collection):
    import matplotlib.pyplot as plt

    _, ax = plt.subplots()
    with pytest.raises(ValueError, match="cannot be combined"):
        plot_zone(mixed_stand_collection, split_by="stand", ax=ax)


def test_plot_zone_without_split_by_still_returns_single_axes(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection)

    assert ax.get_xlim() is not None


@pytest.fixture
def scattered_collection() -> PitchCollection:
    # KDE needs real spread on both axes; a tight cluster in one spot has a
    # singular covariance matrix and would raise inside scipy.
    coords = [(-0.4, 1.8), (-0.1, 2.4), (0.2, 3.0), (0.5, 1.6), (0.0, 2.2)]
    return PitchCollection([_pitch(x, z, "R") for x, z in coords])


def test_kde_requires_scipy_returns_axes(scattered_collection):
    pytest.importorskip("scipy")

    ax = plot_zone(scattered_collection, kind="kde")

    assert ax.get_xlim() is not None


def test_kde_accepts_bw_method(scattered_collection):
    pytest.importorskip("scipy")

    ax = plot_zone(scattered_collection, kind="kde", bw_method=0.5)

    assert ax.get_xlim() is not None


def test_kde_with_split_by_returns_one_axes_per_side():
    pytest.importorskip("scipy")
    pitches = (
        [_pitch(x, z, "L") for x, z in [(-0.4, 1.8), (-0.1, 2.4), (0.2, 3.0)]]
        + [_pitch(x, z, "R") for x, z in [(0.5, 1.6), (0.0, 2.2), (0.3, 2.8)]]
    )
    collection = PitchCollection(pitches)

    axes = plot_zone(collection, kind="kde", split_by="stand")

    assert len(axes) == 2


def test_kde_on_single_point_collection_does_not_raise():
    collection = PitchCollection([_pitch(-0.4, 1.8, "R")])

    ax = plot_zone(collection, kind="kde")

    assert ax.get_xlim() is not None


def test_unknown_kind_raises(mixed_stand_collection):
    with pytest.raises(ValueError, match="Unknown plot kind"):
        plot_zone(mixed_stand_collection, kind="not_a_real_kind")
