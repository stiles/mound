from __future__ import annotations

import math

import pytest

from mound.models import Pitch
from mound.pitches import PitchCollection
from mound.trajectory import (
    DEFAULT_COMMIT_DISTANCE_FEET,
    PLATE_MEASUREMENT_Y_FEET,
    Trajectory,
    TrajectoryError,
    separation,
)

# Roki Sasaki's four-seamer and splitter to Carson Benge, game 823601, at-bat
# 12, as Savant reported them. Kept verbatim rather than rounded: the point of
# these two is that the fit reproduces Savant's own `plate_x`/`plate_z` to the
# digit, which is what pins the measurement plane to the middle of the plate.
FOUR_SEAM = dict(
    release_pos_x=-1.4781575010266894,
    release_pos_y=50.00185921495908,
    release_pos_z=5.983820239275561,
    release_velocity_x=11.124282154472668,
    release_velocity_y=-144.47646051604016,
    release_velocity_z=-9.96906037856956,
    acceleration_x=-15.39965391289501,
    acceleration_y=34.06034608487707,
    acceleration_z=-11.6903998737297,
    release_extension=7.243858374289166,
)
FOUR_SEAM_PLATE = (1.5070191824964785, 1.6920896842302806)

SPLITTER = dict(
    release_pos_x=-1.6926408415757412,
    release_pos_y=50.00068494949097,
    release_pos_z=6.323566194002078,
    release_velocity_x=3.1928758744512584,
    release_velocity_y=-130.5961687612958,
    release_velocity_z=-0.9080548462000941,
    acceleration_x=-1.3670216350680031,
    acceleration_y=27.21416074007794,
    acceleration_z=-32.81790593335609,
    release_extension=7.055705240416995,
)
SPLITTER_PLATE = (-0.5418655053592505, 3.4243278067881113)


def _pitch(**overrides) -> Pitch:
    defaults = dict(
        game_pk=1,
        game_date="2026-07-24",
        pitch_id=None,
        at_bat_number=12,
        pitch_number=1,
        inning=1,
        half_inning="top",
        pitcher_id=808963,
        pitcher_name="Roki Sasaki",
        batter_id=1,
        batter_name="Carson Benge",
        batter_stand="L",
        pitch_type_code="FF",
        pitch_type="four-seam fastball",
        velocity=99.7,
        plate_x=FOUR_SEAM_PLATE[0],
        plate_z=FOUR_SEAM_PLATE[1],
        sz_top=3.4,
        sz_bot=1.6,
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
    )
    defaults.update(overrides)
    return Pitch(**defaults)


def test_trajectory_reproduces_savants_plate_location():
    traj = Trajectory.from_pitch(_pitch(**FOUR_SEAM))

    x, z = traj.plate_location()

    assert x == pytest.approx(FOUR_SEAM_PLATE[0], abs=1e-6)
    assert z == pytest.approx(FOUR_SEAM_PLATE[1], abs=1e-6)


def test_trajectory_reproduces_plate_location_for_offspeed():
    traj = Trajectory.from_pitch(_pitch(**SPLITTER))

    x, z = traj.plate_location()

    assert x == pytest.approx(SPLITTER_PLATE[0], abs=1e-6)
    assert z == pytest.approx(SPLITTER_PLATE[1], abs=1e-6)


def test_plate_plane_is_the_middle_of_the_plate():
    # The front edge (17/12) is the intuitive guess and the wrong one; it
    # misses Savant's own number by enough to see. Guards the constant
    # against being "simplified" back to the front edge.
    traj = Trajectory.from_pitch(_pitch(**FOUR_SEAM))

    assert PLATE_MEASUREMENT_Y_FEET == pytest.approx(17 / 24)

    front_edge_z = traj.position_at_distance(17 / 12)[1]
    assert abs(front_edge_z - FOUR_SEAM_PLATE[1]) > 0.05


def test_position_at_time_follows_the_quadratic():
    traj = Trajectory(
        x0=0.0, y0=50.0, z0=6.0, vx0=1.0, vy0=-130.0, vz0=-5.0, ax=-2.0, ay=30.0, az=-15.0
    )

    x, y, z = traj.position_at_time(0.1)

    assert x == pytest.approx(0.0 + 1.0 * 0.1 + 0.5 * -2.0 * 0.01)
    assert y == pytest.approx(50.0 + -130.0 * 0.1 + 0.5 * 30.0 * 0.01)
    assert z == pytest.approx(6.0 + -5.0 * 0.1 + 0.5 * -15.0 * 0.01)


def test_time_at_distance_inverts_position():
    traj = Trajectory.from_pitch(_pitch(**FOUR_SEAM))

    t = traj.time_at_distance(30.0)

    assert traj.position_at_time(t)[1] == pytest.approx(30.0)


def test_time_at_distance_is_negative_behind_the_fits_origin():
    # Statcast anchors the fit 50 feet from the plate, but the ball leaves
    # the hand in front of that, so reaching release means going backwards.
    traj = Trajectory.from_pitch(_pitch(**FOUR_SEAM))

    assert traj.release_time(FOUR_SEAM["release_extension"]) < 0


def test_path_runs_from_release_to_the_plate():
    pitch = _pitch(**FOUR_SEAM)
    traj = Trajectory.from_pitch(pitch)

    points = traj.path(extension=pitch.release_extension)

    assert points[0][1] == pytest.approx(60.5 - pitch.release_extension, abs=1e-6)
    assert points[-1][1] == pytest.approx(PLATE_MEASUREMENT_Y_FEET, abs=1e-6)
    # Monotonically toward the plate, never doubling back.
    ys = [p[1] for p in points]
    assert ys == sorted(ys, reverse=True)


def test_from_pitch_returns_none_without_tracking_fields():
    assert Trajectory.from_pitch(_pitch()) is None


def test_pitch_trajectory_accessor_matches_module():
    pitch = _pitch(**FOUR_SEAM)

    assert pitch.trajectory().plate_location() == Trajectory.from_pitch(pitch).plate_location()


def test_separation_at_the_plate_matches_the_reported_locations():
    a = Trajectory.from_pitch(_pitch(**FOUR_SEAM))
    b = Trajectory.from_pitch(_pitch(**SPLITTER))

    gap = separation(a, b, distance=PLATE_MEASUREMENT_Y_FEET)

    expected = (
        math.hypot(
            FOUR_SEAM_PLATE[0] - SPLITTER_PLATE[0],
            FOUR_SEAM_PLATE[1] - SPLITTER_PLATE[1],
        )
        * 12
    )
    assert gap == pytest.approx(expected, abs=1e-4)


def test_separation_grows_toward_the_plate():
    a = Trajectory.from_pitch(_pitch(**FOUR_SEAM))
    b = Trajectory.from_pitch(_pitch(**SPLITTER))

    far = separation(a, b, distance=40.0)
    commit = separation(a, b, distance=DEFAULT_COMMIT_DISTANCE_FEET)
    plate = separation(a, b, distance=PLATE_MEASUREMENT_Y_FEET)

    assert far < commit < plate


def test_separation_by_time_compares_each_pitch_to_its_own_arrival():
    a = Trajectory.from_pitch(_pitch(**FOUR_SEAM))
    b = Trajectory.from_pitch(_pitch(**SPLITTER))

    # The splitter is 10 mph slower, so a fixed distance and a fixed time
    # land on different points of its flight -- the whole reason both exist.
    by_distance = separation(a, b, distance=DEFAULT_COMMIT_DISTANCE_FEET)
    by_time = separation(a, b, time_before_plate=0.167)

    assert by_distance != pytest.approx(by_time)


def test_separation_requires_exactly_one_reference():
    a = Trajectory.from_pitch(_pitch(**FOUR_SEAM))
    b = Trajectory.from_pitch(_pitch(**SPLITTER))

    with pytest.raises(TrajectoryError):
        separation(a, b)
    with pytest.raises(TrajectoryError):
        separation(a, b, distance=20.0, time_before_plate=0.167)


def _tunnel_collection() -> PitchCollection:
    return PitchCollection(
        [
            _pitch(pitch_number=1, **FOUR_SEAM),
            _pitch(
                pitch_number=2,
                pitch_type_code="FS",
                pitch_type="splitter",
                velocity=89.7,
                plate_x=SPLITTER_PLATE[0],
                plate_z=SPLITTER_PLATE[1],
                **SPLITTER,
            ),
        ]
    )


def test_tunnels_reports_both_separations():
    df = _tunnel_collection().tunnels()

    assert len(df) == 1
    row = df.iloc[0]
    assert row["first_type"] == "four-seam fastball"
    assert row["second_type"] == "splitter"
    assert row["commit_separation"] < row["plate_separation"]
    assert row["ratio"] == pytest.approx(
        row["plate_separation"] / row["commit_separation"], abs=0.1
    )


def test_tunnels_skips_same_pitch_type_by_default():
    collection = PitchCollection(
        [_pitch(pitch_number=1, **FOUR_SEAM), _pitch(pitch_number=2, **FOUR_SEAM)]
    )

    assert collection.tunnels().empty
    assert len(collection.tunnels(same_type=True)) == 1


def test_tunnels_pairs_only_consecutive_pitches_by_default():
    collection = PitchCollection(
        [
            _pitch(pitch_number=1, **FOUR_SEAM),
            _pitch(pitch_number=2, pitch_type_code="FS", pitch_type="splitter", **SPLITTER),
            _pitch(pitch_number=3, **FOUR_SEAM),
        ]
    )

    assert len(collection.tunnels()) == 2
    assert len(collection.tunnels(consecutive=False)) == 2  # the 1-3 pair is same-type


def test_tunnels_skips_pitches_without_tracking_data():
    collection = PitchCollection(
        [_pitch(pitch_number=1, **FOUR_SEAM), _pitch(pitch_number=2, pitch_type="slider")]
    )

    assert collection.tunnels().empty


def test_tunnels_on_empty_collection_returns_named_columns():
    df = PitchCollection([]).tunnels()

    assert df.empty
    assert "commit_separation" in df.columns
    assert "plate_separation" in df.columns


def test_tunnels_rejects_two_commit_references():
    with pytest.raises(ValueError):
        _tunnel_collection().tunnels(commit_distance=23.8, commit_time=0.167)
