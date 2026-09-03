"""Pitch usage and outcome calculations.

Kept intentionally small -- mix, strike rate, swing/whiff/chase rate, pitch
shape and how plate appearances ended -- but structured so additional
Statcast metrics (exit velocity, expected outcomes, etc.) can be added as
more functions over the same :class:`~mound.pitches.PitchCollection` shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from mound.pitches import PitchCollection


def pitch_mix(collection: PitchCollection) -> pd.Series:
    """Percentage of pitches thrown, by pitch type, sorted descending.

        >>> roki.pitches(last=4).pitch_mix()
        splitter               31.2
        four-seam fastball     28.4
        slider                 19.1
        ...
    """
    df = collection.to_frame()
    if df.empty:
        return pd.Series(dtype=float, name="pitch_mix")

    counts = df["pitch_type"].value_counts()
    pct = (counts / counts.sum() * 100).round(1)
    pct.name = "pitch_mix"
    pct.index.name = "pitch_type"
    return pct


def strike_rate(collection: PitchCollection, by_pitch_type: bool = False) -> float | pd.Series:
    """Strike rate (percentage of pitches that were strikes).

    With ``by_pitch_type=True``, returns a :class:`pandas.Series` broken out
    per pitch type instead of a single overall rate.
    """
    df = collection.to_frame()
    if df.empty:
        return pd.Series(dtype=float, name="strike_rate") if by_pitch_type else float("nan")

    if by_pitch_type:
        rates = df.groupby("pitch_type")["is_strike"].mean() * 100
        rates = rates.round(1).sort_values(ascending=False)
        rates.name = "strike_rate"
        return rates

    return round(df["is_strike"].mean() * 100, 1)


def first_pitch_strike_rate(
    collection: PitchCollection, by_pitch_type: bool = False
) -> float | pd.Series:
    """Strike rate on the first pitch of a plate appearance.

    Broken out from :func:`strike_rate` because the count a pitcher spends
    the rest of an at-bat working from is largely settled here: 0-1 and 1-0
    lead to different pitches, and a starter who can't get pitch one over
    tends to run up a pitch count regardless of how his stuff looks.

    Counted from ``pitch_number``, so it follows the at-bat rather than the
    collection -- narrowing to one pitch type first gives the strike rate on
    the first pitches *of that type*, which is only the same question if he
    opened every hitter with it.
    """
    df = collection.to_frame()
    if not df.empty:
        df = df[df["pitch_number"] == 1]

    if df.empty:
        return (
            pd.Series(dtype=float, name="first_pitch_strike_rate")
            if by_pitch_type
            else float("nan")
        )

    if by_pitch_type:
        rates = df.groupby("pitch_type")["is_strike"].mean() * 100
        rates = rates.round(1).sort_values(ascending=False)
        rates.name = "first_pitch_strike_rate"
        return rates

    return round(df["is_strike"].mean() * 100, 1)


def plate_appearances(collection: PitchCollection) -> pd.Series:
    """How the plate appearances in this collection ended, counted by result.

        >>> roki.pitches(game=825051).plate_appearances()
        at_bat_result
        Strikeout    8
        Groundout    5
        Walk         2
        ...

    Read only from the pitch each at-bat ended on, since Savant stamps
    ``at_bat_result`` onto every pitch of the at-bat -- counting every row
    would score a five-pitch strikeout five times. So this follows
    ``ends_at_bat`` and inherits its edges: an at-bat still being pitched has
    no ending to count, and an at-bat whose final pitch an earlier filter
    removed drops out entirely, which is what makes a pitch-type-filtered
    count a narrower question than it looks.
    """
    df = collection.to_frame()
    if not df.empty:
        df = df[df["ends_at_bat"].astype("boolean").fillna(False)]

    if df.empty:
        return pd.Series(dtype=int, name="plate_appearances")

    counts = df["at_bat_result"].dropna().value_counts()
    counts.name = "plate_appearances"
    counts.index.name = "at_bat_result"
    return counts


def swing_rate(collection: PitchCollection, by_pitch_type: bool = False) -> float | pd.Series:
    """Swing rate (percentage of pitches the batter swung at, contact or miss).

    With ``by_pitch_type=True``, returns a :class:`pandas.Series` broken out
    per pitch type instead of a single overall rate.
    """
    df = collection.to_frame()
    if df.empty:
        return pd.Series(dtype=float, name="swing_rate") if by_pitch_type else float("nan")

    if by_pitch_type:
        rates = df.groupby("pitch_type")["is_swing"].mean() * 100
        rates = rates.round(1).sort_values(ascending=False)
        rates.name = "swing_rate"
        return rates

    return round(df["is_swing"].mean() * 100, 1)


def whiff_rate(collection: PitchCollection, by_pitch_type: bool = False) -> float | pd.Series:
    """Percentage of *swings* that missed the ball entirely.

    Matches Baseball Savant's own whiff-rate convention: misses divided by
    swings, not by every pitch thrown -- a pitch type rarely swung at can
    still have a high whiff rate on the swings it does draw. With
    ``by_pitch_type=True``, returns a :class:`pandas.Series` per pitch type.
    """
    df = collection.to_frame()
    if not df.empty:
        df = df[df["is_swing"].astype("boolean").fillna(False)]

    if df.empty:
        return pd.Series(dtype=float, name="whiff_rate") if by_pitch_type else float("nan")

    if by_pitch_type:
        rates = df.groupby("pitch_type")["is_whiff"].mean() * 100
        rates = rates.round(1).sort_values(ascending=False)
        rates.name = "whiff_rate"
        return rates

    return round(df["is_whiff"].mean() * 100, 1)


def chase_rate(collection: PitchCollection, by_pitch_type: bool = False) -> float | pd.Series:
    """Percentage of pitches *outside the zone* that drew a swing.

    The out-of-zone counterpart to :func:`swing_rate`: chases divided by
    pitches a batter could have simply taken for a ball. A pitch's location
    is judged by ``in_zone`` (geometry), not ``is_strike`` (the ruling), so
    a called strike on the corner counts as in the zone even if the umpire
    would have been generous about it. With ``by_pitch_type=True``, returns
    a :class:`pandas.Series` per pitch type.
    """
    df = collection.to_frame()
    if not df.empty:
        # Cast to nullable "boolean" rather than bool so a pitch with no plate
        # coordinates stays missing instead of collapsing to False: there's no
        # way to know whether it was a chase opportunity, so it drops out of
        # the denominator instead of counting as one.
        outside_zone = df["in_zone"].astype("boolean").eq(False).fillna(False)
        df = df[outside_zone]

    if df.empty:
        return pd.Series(dtype=float, name="chase_rate") if by_pitch_type else float("nan")

    if by_pitch_type:
        rates = df.groupby("pitch_type")["is_swing"].mean() * 100
        rates = rates.round(1).sort_values(ascending=False)
        rates.name = "chase_rate"
        return rates

    return round(df["is_swing"].mean() * 100, 1)


# Columns pitch_metrics() averages -- movement/release fields that may be
# None for pitches predating (or otherwise lacking) Statcast's full
# tracking coverage; pandas' mean() already skips those by default.
_PITCH_METRIC_COLUMNS = [
    "velocity",
    "spin_rate",
    "release_extension",
    "horizontal_break",
    "induced_vertical_break",
]


def pitch_metrics(
    collection: PitchCollection, by_pitch_type: bool = True
) -> pd.DataFrame | pd.Series:
    """Average velocity, spin rate and movement (a pitch's "shape"), by pitch type.

    Useful for comparing a pitch's characteristics across starts or against
    a season, e.g. whether a four-seamer's spin rate in one outing is
    unusually high relative to a pitcher's other starts:

        >>> roki.pitches(game=825051).pitch_metrics()["spin_rate"]
        pitch_type
        four-seam fastball    2450.1
        splitter              1200.3
        ...

    Pass ``by_pitch_type=False`` to collapse to a single overall row
    (returned as a :class:`pandas.Series` instead of a DataFrame).
    """
    df = collection.to_frame()
    columns = [c for c in _PITCH_METRIC_COLUMNS if c in df.columns]
    if columns:
        # A column may be all-None (e.g. no tracking coverage at all in this
        # sample), which pandas stores as object dtype -- coerce to float so
        # mean()/round() work rather than erroring on "object" dtype.
        df[columns] = df[columns].astype(float)

    if by_pitch_type:
        if df.empty:
            return pd.DataFrame(columns=["pitches", *columns])
        counts = df.groupby("pitch_type").size().rename("pitches")
        means = df.groupby("pitch_type")[columns].mean().round(1)
        return counts.to_frame().join(means).sort_values("pitches", ascending=False)

    if df.empty:
        return pd.Series(dtype=float, index=["pitches", *columns])
    result = df[columns].mean().round(1)
    result["pitches"] = float(len(df))
    return result[["pitches", *columns]]


def tunnels(
    collection: PitchCollection,
    *,
    consecutive: bool = True,
    commit_distance: float | None = None,
    commit_time: float | None = None,
    same_type: bool = False,
) -> pd.DataFrame:
    """How closely pairs of pitches travel together before diverging.

    Two pitches "tunnel" when they look identical for as long as the hitter
    has to decide, then finish somewhere else. This measures that directly
    off Statcast's trajectory fit: how far apart the two balls are at the
    commit point, and how far apart they are at the plate.

        >>> roki.pitches(game=825051).tunnels().head(3)

    By default it pairs each pitch with the one that followed it in the same
    at-bat, since tunneling is a question about sequence -- what the hitter
    had just seen. Pass ``consecutive=False`` to compare every pair within
    an at-bat instead. Pairs of the same pitch type are skipped unless
    ``same_type=True``.

    The commit point defaults to
    :data:`~mound.trajectory.DEFAULT_COMMIT_DISTANCE_FEET` (23.8 feet).
    Pass ``commit_time`` instead to fix it at a number of seconds before
    each pitch reaches the plate, which compares a curveball and a fastball
    at the same point in the hitter's reaction rather than the same point in
    space.

    ``ratio`` is plate separation over commit separation. Read it with the
    tracking's own precision in mind: a pair a tenth of an inch apart at the
    commit point is not meaningfully closer than one three tenths apart, so
    the very largest ratios say more about the denominator than the pitches.
    """
    from mound.trajectory import (
        DEFAULT_COMMIT_DISTANCE_FEET,
        PLATE_MEASUREMENT_Y_FEET,
        Trajectory,
        separation,
    )

    if commit_distance is not None and commit_time is not None:
        raise ValueError("pass at most one of commit_distance or commit_time")
    if commit_time is None and commit_distance is None:
        commit_distance = DEFAULT_COMMIT_DISTANCE_FEET

    columns = [
        "game_pk",
        "game_date",
        "batter_name",
        "at_bat_number",
        "first_pitch",
        "second_pitch",
        "first_type",
        "second_type",
        "first_velocity",
        "second_velocity",
        "commit_separation",
        "plate_separation",
        "ratio",
    ]

    by_at_bat: dict[tuple, list] = {}
    for pitch in collection:
        if pitch.at_bat_number is None or pitch.pitch_number is None:
            continue
        by_at_bat.setdefault((pitch.game_pk, pitch.at_bat_number), []).append(pitch)

    rows = []
    for pitches in by_at_bat.values():
        pitches = sorted(pitches, key=lambda p: p.pitch_number)
        pairs = (
            zip(pitches, pitches[1:], strict=False)
            if consecutive
            else ((a, b) for i, a in enumerate(pitches) for b in pitches[i + 1 :])
        )
        for first, second in pairs:
            if not same_type and first.pitch_type == second.pitch_type:
                continue
            traj_a = Trajectory.from_pitch(first)
            traj_b = Trajectory.from_pitch(second)
            if traj_a is None or traj_b is None:
                continue

            commit = separation(
                traj_a, traj_b, distance=commit_distance, time_before_plate=commit_time
            )
            plate = separation(traj_a, traj_b, distance=PLATE_MEASUREMENT_Y_FEET)
            if commit is None or plate is None:
                continue

            rows.append(
                {
                    "game_pk": first.game_pk,
                    "game_date": first.game_date,
                    "batter_name": first.batter_name,
                    "at_bat_number": first.at_bat_number,
                    "first_pitch": first.pitch_number,
                    "second_pitch": second.pitch_number,
                    "first_type": first.pitch_type,
                    "second_type": second.pitch_type,
                    "first_velocity": first.velocity,
                    "second_velocity": second.velocity,
                    "commit_separation": round(commit, 1),
                    "plate_separation": round(plate, 1),
                    "ratio": round(plate / commit, 1) if commit else float("nan"),
                }
            )

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("ratio", ascending=False)
        .reset_index(drop=True)
    )


def usage_rate(collection: PitchCollection, by: str = "game_date") -> pd.DataFrame:
    """Pitch usage percentage by pitch type, grouped by ``by`` (e.g. per game or date).

    Useful for comparing how a pitch's usage has changed across outings,
    e.g. ``roki.pitches(last=8).usage_rate(by="game_date")``.
    """
    df = collection.to_frame()
    if df.empty:
        return pd.DataFrame()

    counts = df.groupby([by, "pitch_type"]).size().rename("count")
    totals = df.groupby(by).size().rename("total")
    result = counts.reset_index().merge(totals.reset_index(), on=by)
    result["usage_rate"] = (result["count"] / result["total"] * 100).round(1)
    return result.pivot(index=by, columns="pitch_type", values="usage_rate").fillna(0.0)
