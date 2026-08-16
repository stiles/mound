from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from dataclasses import replace

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_hex

from mound.models import Pitch
from mound.pitches import PitchCollection
from mound.players import Player
from mound.viz import (
    DEFAULT_PITCH_COLOR,
    PITCH_TYPE_COLORS,
    STAND_COLORS,
    _default_headline,
    _default_subtitle,
    plot_zone,
)
from mound.zone import zone_number

SZ_TOP, SZ_BOT = 3.4, 1.6


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
        sz_top=SZ_TOP,
        sz_bot=SZ_BOT,
        in_zone=True,
        balls=0,
        strikes=0,
        pitch_call="called_strike",
        call_description=None,
        is_strike=True,
        is_swing=False,
        is_whiff=False,
        at_bat_result=None,
        description=None,
        zone=zone_number(plate_x, plate_z, SZ_TOP, SZ_BOT),
    )


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


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


def _scatter_colors(ax) -> list[str]:
    """The color of each scatter series drawn on ``ax``, in draw order."""
    return [to_hex(collection.get_facecolor()[0]) for collection in ax.collections]


def _key_labels(ax) -> list[str]:
    return [text.get_text() for text in ax.texts]


def test_color_by_stand_draws_a_series_per_side(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, color_by="stand")

    assert _scatter_colors(ax) == [
        to_hex(STAND_COLORS["L"]),
        to_hex(STAND_COLORS["R"]),
    ]


def test_color_by_stand_labels_the_key_by_handedness(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, color_by="stand")

    assert _key_labels(ax) == ["\u25cf vs LHB", "\u25cf vs RHB"]


def test_color_by_accepts_batter_stand_alias(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, color_by="batter_stand")

    assert len(_scatter_colors(ax)) == 2


def test_color_by_none_draws_one_series_and_no_key(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, color_by=None)

    assert _scatter_colors(ax) == [to_hex(DEFAULT_PITCH_COLOR)]
    assert _key_labels(ax) == []


def test_color_by_unknown_column_raises(mixed_stand_collection):
    with pytest.raises(ValueError, match="Cannot color_by"):
        plot_zone(mixed_stand_collection, color_by="not_a_real_column")


def test_color_by_pitch_type_orders_the_key_by_usage():
    pitches = [_pitch(0.0, 2.0, "R", pitch_type="splitter") for _ in range(2)] + [
        _pitch(0.1, 2.1, "R") for _ in range(5)
    ]

    ax = plot_zone(PitchCollection(pitches))

    assert _key_labels(ax) == ["\u25cf four-seam fastball", "\u25cf splitter"]
    assert _scatter_colors(ax) == [
        to_hex(PITCH_TYPE_COLORS["four-seam fastball"]),
        to_hex(PITCH_TYPE_COLORS["splitter"]),
    ]


def test_color_by_a_column_with_no_palette_draws_every_group_in_one_color(mixed_stand_collection):
    pitches = mixed_stand_collection.pitches
    pitches[0] = replace(pitches[0], batter_id=2, batter_name="Another Batter")

    ax = plot_zone(PitchCollection(pitches), color_by="batter_name")

    assert _scatter_colors(ax) == [to_hex(DEFAULT_PITCH_COLOR)] * 2


def test_a_lone_pitch_type_drops_back_to_the_house_color(mixed_stand_collection):
    # Every pitch here is a four-seamer, so its color would separate it from
    # nothing; the headline already says what it is.
    ax = plot_zone(mixed_stand_collection, color_by="pitch_type")

    assert _scatter_colors(ax) == [to_hex(DEFAULT_PITCH_COLOR)]
    assert _key_labels(ax) == []


def test_a_lone_pitch_type_stays_in_the_house_color_when_faceted(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, color_by="pitch_type", split_by="stand")

    for ax in axes:
        assert _scatter_colors(ax) == [to_hex(DEFAULT_PITCH_COLOR)]


def test_a_pitch_type_missing_from_one_panel_keeps_its_color_in_the_other():
    # The frame as a whole has two pitch types, so color is doing work even
    # in the panel that only shows one of them.
    pitches = [_pitch(-0.3, 2.5, "L") for _ in range(3)] + [
        _pitch(0.4, 2.2, "R", pitch_type="splitter") for _ in range(2)
    ]

    axes = plot_zone(PitchCollection(pitches), color_by="pitch_type", split_by="stand")

    assert _scatter_colors(axes[0]) == [to_hex(PITCH_TYPE_COLORS["four-seam fastball"])]
    assert _scatter_colors(axes[1]) == [to_hex(PITCH_TYPE_COLORS["splitter"])]


def test_color_by_stand_within_split_by_stand_skips_a_redundant_key(mixed_stand_collection):
    axes = plot_zone(mixed_stand_collection, color_by="stand", split_by="stand")

    assert [_scatter_colors(ax) for ax in axes] == [
        [to_hex(STAND_COLORS["L"])],
        [to_hex(STAND_COLORS["R"])],
    ]
    assert _key_labels(axes[0]) == []


def test_unknown_kind_raises(mixed_stand_collection):
    with pytest.raises(ValueError, match="Unknown plot kind"):
        plot_zone(mixed_stand_collection, kind="not_a_real_kind")


def _zone_lines(ax) -> list:
    """The grid lines drawn inside the strike zone, if any."""
    return list(ax.lines)


def test_grid_draws_the_four_interior_lines_of_the_zone(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, grid=True)

    assert len(_zone_lines(ax)) == 4


def test_no_grid_unless_asked_for(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection)

    assert _zone_lines(ax) == []


def test_grid_reaches_the_edges_of_the_drawn_strike_zone(mixed_stand_collection):
    ax = plot_zone(mixed_stand_collection, grid=True)

    verticals = [line for line in _zone_lines(ax) if len(set(line.get_xdata())) == 1]
    for line in verticals:
        assert list(line.get_ydata()) == [SZ_BOT, SZ_TOP]


def _labeled_counts(ax) -> dict[int, int]:
    """Read a ``kind="zones"`` panel back as ``{zone number: count}``.

    Each cell is labeled with its count first and its zone number second,
    so the texts pair off in draw order.
    """
    counts, numbers = ax.texts[::2], ax.texts[1::2]
    return {
        int(number.get_text()): int(count.get_text())
        for count, number in zip(counts, numbers, strict=True)
    }


@pytest.fixture
def zoned_collection() -> PitchCollection:
    # Zones 4, 6, 5, 12 and 13 respectively, against this batter's zone.
    coords = [(-0.3, 2.5), (-0.3, 2.5), (0.4, 2.2), (0.0, 2.5), (1.5, 3.2), (-1.2, 1.0)]
    return PitchCollection([_pitch(x, z, "R") for x, z in coords])


def test_zones_labels_all_thirteen_cells(zoned_collection):
    ax = plot_zone(zoned_collection, kind="zones")

    assert sorted(_labeled_counts(ax)) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14]


def test_zones_counts_each_pitch_into_the_zone_it_was_assigned(zoned_collection):
    ax = plot_zone(zoned_collection, kind="zones")

    counts = _labeled_counts(ax)
    assert counts[4] == 2
    assert counts[5] == 1
    assert counts[6] == 1
    assert counts[12] == 1
    assert counts[13] == 1
    assert counts[1] == 0


def test_zones_draws_no_grid_lines_of_its_own(zoned_collection):
    # The cells are patches; asking for the overlay too would double them.
    ax = plot_zone(zoned_collection, kind="zones", grid=True)

    assert _zone_lines(ax) == []


def test_zones_with_split_by_counts_each_side_separately():
    pitches = [_pitch(0.0, 2.5, "L")] + [_pitch(-0.3, 2.5, "R") for _ in range(3)]

    axes = plot_zone(PitchCollection(pitches), kind="zones", split_by="stand")

    assert _labeled_counts(axes[0])[5] == 1
    assert _labeled_counts(axes[1])[4] == 3


def test_zones_on_an_empty_collection_still_draws_the_diagram():
    collection = PitchCollection([])

    ax = plot_zone(collection, kind="zones")

    assert set(_labeled_counts(ax).values()) == {0}


def _roki() -> Player:
    return Player(id=808963, full_name="Roki Sasaki", primary_position="Pitcher")


def _hitter() -> Player:
    return Player(id=1, full_name="Test Batter", primary_position="Shortstop")


def test_headline_names_the_pitcher(mixed_stand_collection):
    collection = PitchCollection(mixed_stand_collection.pitches, pitcher=_roki())

    headline = _default_headline(collection, collection.to_frame())

    assert headline == "Roki Sasaki\u2019s four-seam fastball locations"


def test_headline_for_pitches_faced_names_the_hitter_as_the_target(mixed_stand_collection):
    collection = PitchCollection(mixed_stand_collection.pitches, batter=_hitter())

    headline = _default_headline(collection, collection.to_frame())

    assert headline == "Four-seam fastball locations to Test Batter"


def test_subtitle_flags_a_one_batter_matchup(mixed_stand_collection):
    collection = PitchCollection(mixed_stand_collection.pitches, pitcher=_roki())

    subtitle = _default_subtitle(collection, collection.to_frame())

    assert "vs. Test Batter" in subtitle


def test_subtitle_leaves_out_the_batter_when_several_were_faced(mixed_stand_collection):
    pitches = mixed_stand_collection.pitches
    pitches[0] = replace(pitches[0], batter_id=2, batter_name="Another Batter")
    collection = PitchCollection(pitches, pitcher=_roki())

    subtitle = _default_subtitle(collection, collection.to_frame())

    assert "vs." not in subtitle


def test_subtitle_does_not_repeat_a_hitter_already_in_the_headline(mixed_stand_collection):
    collection = PitchCollection(mixed_stand_collection.pitches, batter=_hitter())

    subtitle = _default_subtitle(collection, collection.to_frame())

    assert "vs." not in subtitle
