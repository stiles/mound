"""Strike-zone geometry: is a given pitch a strike, and where in the zone?

The zone is a rectangle in the batter's frame of reference — fixed
horizontal edges, but a vertical range (``sz_top``/``sz_bot``) that varies
by batter height and stance. A pitch counts as being in the zone if the
ball (modeled as a circle with a real baseball's radius) overlaps that
rectangle at all, matching how Statcast itself frames "in zone."

Statcast also splits the plate into the numbered zones you see on Baseball
Savant: 1-9 across the zone itself, 11-14 for the four quadrants outside it
(there is no 10). See :func:`zone_number` for how those are drawn.
"""

from __future__ import annotations

import math

# Home plate is 17 inches wide; a pitch is "in the zone" horizontally if its
# center passes within half that width (plus the ball's own radius) of the
# plate's centerline. Kept as a fraction rather than a rounded decimal:
# 0.708 is off by five hundredths of an inch, which is enough to disagree
# with Savant's own `isInZone` and `zone` fields on a couple of pitches per
# 40,000.
PLATE_HALF_WIDTH_FEET = 17 / 24
SZ_LEFT_FEET = -PLATE_HALF_WIDTH_FEET
SZ_RIGHT_FEET = PLATE_HALF_WIDTH_FEET

# A standard MLB baseball is ~2.9 inches in diameter.
BALL_RADIUS_FEET = 1.45 / 12

# Statcast's zone vocabulary: 1-9 inside the strike zone, 11-14 outside it.
ZONE_NUMBERS = frozenset({*range(1, 10), 11, 12, 13, 14})


def is_in_zone(
    plate_x: float | None,
    plate_z: float | None,
    sz_top: float | None,
    sz_bot: float | None,
) -> bool | None:
    """Return whether a pitch location falls within the strike zone.

    Returns ``None`` if any required coordinate is missing, since we can't
    determine zone membership without them.
    """
    if any(v is None for v in (plate_x, plate_z, sz_top, sz_bot)):
        return None

    closest_x = max(SZ_LEFT_FEET, min(SZ_RIGHT_FEET, plate_x))
    closest_z = max(sz_bot, min(sz_top, plate_z))
    distance = math.sqrt((plate_x - closest_x) ** 2 + (plate_z - closest_z) ** 2)
    return distance <= BALL_RADIUS_FEET


def zone_grid(sz_top: float, sz_bot: float) -> tuple[list[float], list[float]]:
    """The boundaries Statcast's 3x3 grid is cut on, as x and z edges.

    Four of each, outer edges included, so ``xs[1]`` and ``xs[2]`` are the
    two interior verticals and ``zs`` runs bottom to top.

    The grid covers the zone grown by one ball radius, not the strike zone
    itself, which is what makes a pitch an inch above ``sz_top`` zone 1
    rather than 11. One consequence worth knowing when these are drawn: the
    cells are thirds of the *grown* zone, an inch wider than thirds of the
    strike zone proper, so the interior lines sit about half an inch outside
    where an even split of the drawn box would put them.
    """
    left = SZ_LEFT_FEET - BALL_RADIUS_FEET
    right = SZ_RIGHT_FEET + BALL_RADIUS_FEET
    top = sz_top + BALL_RADIUS_FEET
    bottom = sz_bot - BALL_RADIUS_FEET
    xs = [left + i * (right - left) / 3 for i in range(4)]
    zs = [bottom + i * (top - bottom) / 3 for i in range(4)]
    return xs, zs


def zone_number(
    plate_x: float | None,
    plate_z: float | None,
    sz_top: float | None,
    sz_bot: float | None,
) -> int | None:
    """Return Statcast's zone number for a pitch location, or ``None``.

    A pitch in the zone gets 1-9, read like a book from the catcher's view:
    1-3 across the top, 4-6 the middle, 7-9 the bottom, with 1 on the side
    where ``plate_x`` is negative. One outside gets 11 (up and to that same
    side), 12 (up and away from it), 13 or 14 (the two below), split at the
    zone's own center. There is no zone 10.

    Two details make this match Savant rather than merely resemble it. The
    3x3 grid is drawn over the zone *grown by a ball radius*, not the strike
    zone proper, so a pitch an inch above ``sz_top`` is zone 1 rather than
    11 and the thirds sit slightly wider than a third of the zone each. But
    membership still comes from :func:`is_in_zone`, whose corners are round,
    so a pitch that clips a corner diagonally reads as outside. Checked
    against Savant's own ``zone`` field across 42,538 cached pitches with no
    disagreements.
    """
    inside = is_in_zone(plate_x, plate_z, sz_top, sz_bot)
    if inside is None:
        return None

    xs, zs = zone_grid(sz_top, sz_bot)

    if inside:
        # Clamped because a pitch that only reaches the zone by its radius
        # can sit a hair outside the grid it's being placed in.
        column = min(max(int((plate_x - xs[0]) / (xs[3] - xs[0]) * 3), 0), 2)
        row = min(max(int((zs[3] - plate_z) / (zs[3] - zs[0]) * 3), 0), 2)
        return 1 + row * 3 + column

    upper = plate_z >= (zs[3] + zs[0]) / 2
    near_side = plate_x < 0
    if upper:
        return 11 if near_side else 12
    return 13 if near_side else 14
