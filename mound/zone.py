"""Strike-zone geometry: is a given pitch location a strike?

The zone is a rectangle in the batter's frame of reference — fixed
horizontal edges, but a vertical range (``sz_top``/``sz_bot``) that varies
by batter height and stance. A pitch counts as being in the zone if the
ball (modeled as a circle with a real baseball's radius) overlaps that
rectangle at all, matching how Statcast itself frames "in zone."
"""

from __future__ import annotations

import math

# Home plate is 17 inches wide; a pitch is "in the zone" horizontally if its
# center passes within half that width (plus the ball's own radius) of the
# plate's centerline.
SZ_LEFT_FEET = -0.708
SZ_RIGHT_FEET = 0.708

# A standard MLB baseball is ~2.9 inches in diameter.
BALL_RADIUS_FEET = 1.45 / 12


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
