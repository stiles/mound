"""Pitch flight paths, reconstructed from Statcast's nine-parameter fit.

Savant's ``/gf`` feed reports each pitch as a release point (``x0``/``y0``/
``z0``), a release velocity (``vx0``/``vy0``/``vz0``) and a constant
acceleration (``ax``/``ay``/``az``) that carries drag and Magnus force
together. Those nine numbers describe the whole flight as a quadratic in
each axis, so any point between the pitcher's hand and the plate is
available in closed form rather than by interpolation.

Coordinates are Statcast's: ``y`` is distance from the plate in feet,
counting down from the mound; ``x`` is horizontal, positive toward the
catcher's right (a right-handed batter's inside is negative); ``z`` is
height. Note the sign convention on ``x`` is the catcher's view, which is
also how :mod:`mound.zone` reads it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mound.models import Pitch

# Savant reports `plate_x`/`plate_z` at the middle of home plate, not its
# front edge: the plate is 17 inches front to back at its widest, so its
# midpoint sits 17/24 feet from the point. Fitting the plane empirically
# across 22,482 cached pitches reproduces Savant's own numbers exactly
# there, and nowhere else -- the front edge (17/12) is off by about nine
# hundredths of an inch horizontally and three tenths vertically. It's the
# same 17/24 that `mound.zone` uses for half the plate's width, which is a
# coincidence of the plate being as deep as it is wide.
PLATE_MEASUREMENT_Y_FEET = 17 / 24

# Where a hitter has to commit. Baseball Prospectus's tunnel work fixes this
# at a distance rather than a time, and 23.8 feet is the figure that
# literature settled on, so it's the default here for comparability. The
# case for a fixed *time* is better physiology -- the swing decision is a
# reaction, and 23.8 feet is 162 ms of a 100 mph four-seamer but 200 ms of
# an 80 mph curveball -- so `commit_time` is available as an alternative.
DEFAULT_COMMIT_DISTANCE_FEET = 23.8

# The rubber, for turning Savant's `extension` into a release distance.
RUBBER_DISTANCE_FEET = 60.5


class TrajectoryError(ValueError):
    """Raised when a pitch has no usable trajectory fit."""


@dataclass(frozen=True)
class Trajectory:
    """One pitch's flight path as a constant-acceleration fit.

    Built from :meth:`from_pitch`; every method is closed-form, so asking
    for a hundred points along the path costs no more than asking for one.
    """

    x0: float
    y0: float
    z0: float
    vx0: float
    vy0: float
    vz0: float
    ax: float
    ay: float
    az: float

    @classmethod
    def from_pitch(cls, pitch: Pitch) -> Trajectory | None:
        """Build a trajectory from a :class:`~mound.models.Pitch`.

        Returns ``None`` when the pitch predates or otherwise lacks the
        tracking fields, which is the same way the rest of Mound treats a
        missing measurement -- a pitch without them isn't an error, it just
        can't answer this question.
        """
        values = (
            pitch.release_pos_x,
            pitch.release_pos_y,
            pitch.release_pos_z,
            pitch.release_velocity_x,
            pitch.release_velocity_y,
            pitch.release_velocity_z,
            pitch.acceleration_x,
            pitch.acceleration_y,
            pitch.acceleration_z,
        )
        if any(v is None for v in values):
            return None
        return cls(*(float(v) for v in values))  # type: ignore[arg-type]

    def position_at_time(self, t: float) -> tuple[float, float, float]:
        """``(x, y, z)`` in feet at ``t`` seconds after the fit's origin."""
        return (
            self.x0 + self.vx0 * t + 0.5 * self.ax * t * t,
            self.y0 + self.vy0 * t + 0.5 * self.ay * t * t,
            self.z0 + self.vz0 * t + 0.5 * self.az * t * t,
        )

    def time_at_distance(self, y: float) -> float | None:
        """Seconds until the ball reaches ``y`` feet from the plate.

        ``None`` if the ball never gets there. Times before the fit's origin
        come back negative, which is how :meth:`release_time` reaches back to
        the pitcher's hand -- Statcast anchors the fit at 50 feet, in front
        of where anyone actually releases the ball.
        """
        a, b, c = 0.5 * self.ay, self.vy0, self.y0 - y
        if abs(a) < 1e-12:
            if abs(b) < 1e-12:
                return None
            return -c / b

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        root = math.sqrt(discriminant)
        candidates = sorted(((-b - root) / (2 * a), (-b + root) / (2 * a)))
        # The ball is moving toward the plate, so the first crossing is the
        # real one; the second is the parabola's fictional return trip.
        return candidates[0] if candidates[0] > -1.0 else candidates[-1]

    def position_at_distance(self, y: float) -> tuple[float, float] | None:
        """``(x, z)`` in feet where the ball crosses ``y`` feet from the plate."""
        t = self.time_at_distance(y)
        if t is None:
            return None
        x, _, z = self.position_at_time(t)
        return x, z

    def plate_location(self) -> tuple[float, float] | None:
        """``(x, z)`` at the plane Savant measures ``plate_x``/``plate_z`` on."""
        return self.position_at_distance(PLATE_MEASUREMENT_Y_FEET)

    def release_time(self, extension: float | None) -> float:
        """Seconds (negative) from the fit's origin back to the ball leaving the hand."""
        if extension is None:
            return 0.0
        t = self.time_at_distance(RUBBER_DISTANCE_FEET - extension)
        return t if t is not None else 0.0

    def time_before_plate(self, seconds: float) -> tuple[float, float] | None:
        """``(x, z)`` at ``seconds`` before the ball reaches the plate."""
        t_plate = self.time_at_distance(PLATE_MEASUREMENT_Y_FEET)
        if t_plate is None:
            return None
        x, _, z = self.position_at_time(t_plate - seconds)
        return x, z

    def path(
        self,
        *,
        extension: float | None = None,
        steps: int = 60,
    ) -> list[tuple[float, float, float]]:
        """Sample the flight path from release to the plate, as ``(x, y, z)``.

        Starts at the ball's release when ``extension`` is given, and at the
        fit's own 50-foot origin otherwise.
        """
        start = self.release_time(extension)
        end = self.time_at_distance(PLATE_MEASUREMENT_Y_FEET)
        if end is None:
            return []
        return [
            self.position_at_time(start + (end - start) * i / steps) for i in range(steps + 1)
        ]


def separation(
    a: Trajectory,
    b: Trajectory,
    *,
    distance: float | None = None,
    time_before_plate: float | None = None,
) -> float | None:
    """Distance in **inches** between two pitches at the same point of flight.

    Give either a ``distance`` from the plate in feet, or a
    ``time_before_plate`` in seconds. Two pitches compared by time are each
    measured against their own plate arrival, so a slow curveball and a fast
    fastball are compared at the same point in the hitter's reaction rather
    than the same point in space.
    """
    if (distance is None) == (time_before_plate is None):
        raise TrajectoryError("pass exactly one of distance or time_before_plate")

    if distance is not None:
        pos_a = a.position_at_distance(distance)
        pos_b = b.position_at_distance(distance)
    else:
        pos_a = a.time_before_plate(time_before_plate)  # type: ignore[arg-type]
        pos_b = b.time_before_plate(time_before_plate)  # type: ignore[arg-type]

    if pos_a is None or pos_b is None:
        return None
    return math.hypot(pos_a[0] - pos_b[0], pos_a[1] - pos_b[1]) * 12
