from __future__ import annotations

import pytest

from mound.zone import (
    BALL_RADIUS_FEET,
    SZ_RIGHT_FEET,
    ZONE_NUMBERS,
    is_in_zone,
    zone_number,
)

# A two-foot-tall zone, so the thirds are easy to reason about by eye.
TOP, BOT = 3.5, 1.5


def _zone(plate_x: float, plate_z: float) -> int | None:
    return zone_number(plate_x, plate_z, TOP, BOT)


@pytest.mark.parametrize(
    ("plate_x", "plate_z", "expected"),
    [
        (-0.55, 3.2, 1),
        (0.0, 3.2, 2),
        (0.55, 3.2, 3),
        (-0.55, 2.5, 4),
        (0.0, 2.5, 5),
        (0.55, 2.5, 6),
        (-0.55, 1.7, 7),
        (0.0, 1.7, 8),
        (0.55, 1.7, 9),
    ],
)
def test_zone_numbers_read_like_a_book_from_the_catchers_view(plate_x, plate_z, expected):
    assert _zone(plate_x, plate_z) == expected


@pytest.mark.parametrize(
    ("plate_x", "plate_z", "expected"),
    [
        (-2.0, 4.0, 11),
        (2.0, 4.0, 12),
        (-2.0, 1.0, 13),
        (2.0, 1.0, 14),
    ],
)
def test_pitches_off_the_plate_get_the_outer_quadrants(plate_x, plate_z, expected):
    assert _zone(plate_x, plate_z) == expected


def test_a_pitch_just_above_the_zone_is_still_in_it():
    # Statcast draws the grid over the zone grown by a ball radius, so a
    # pitch whose center clears sz_top by less than that is zone 2, not 11.
    assert _zone(0.0, TOP + 0.05) == 2
    assert _zone(-0.1, TOP + 0.5) == 11


def test_a_pitch_clipping_a_corner_diagonally_reads_as_outside():
    # The corners are round, because the ball is: missing by 0.09 feet on
    # both axes at once is 0.127 away from the corner, past the radius, even
    # though a squared-off zone would have called it zone 1.
    assert _zone(-0.798, TOP + 0.09) == 11
    assert _zone(-0.780, TOP + 0.07) == 1


def test_the_plate_edge_is_seventeen_inches_not_a_rounded_decimal():
    assert SZ_RIGHT_FEET == 17 / 24

    # A pitch that reaches a 17-inch plate but not a 0.708-foot one. Savant
    # calls this a strike by location; rounding the constant doesn't.
    borderline = 0.708 + BALL_RADIUS_FEET + 0.0002
    assert is_in_zone(borderline, 2.5, TOP, BOT) is True
    assert is_in_zone(SZ_RIGHT_FEET + BALL_RADIUS_FEET + 0.001, 2.5, TOP, BOT) is False


def test_every_location_lands_on_a_real_zone_number():
    # Statcast has no zone 10, and nothing should fall between the grid and
    # the quadrants around it.
    numbers = {
        _zone(x / 10, z / 10) for x in range(-25, 26) for z in range(0, 61)
    }
    assert numbers <= ZONE_NUMBERS
    assert 10 not in numbers
    assert numbers == ZONE_NUMBERS  # a wide enough sweep hits all of them


@pytest.mark.parametrize(
    ("plate_x", "plate_z", "sz_top", "sz_bot"),
    [
        (None, 2.5, TOP, BOT),
        (0.0, None, TOP, BOT),
        (0.0, 2.5, None, BOT),
        (0.0, 2.5, TOP, None),
    ],
)
def test_a_missing_coordinate_leaves_the_zone_unknown(plate_x, plate_z, sz_top, sz_bot):
    assert zone_number(plate_x, plate_z, sz_top, sz_bot) is None
    assert is_in_zone(plate_x, plate_z, sz_top, sz_bot) is None
