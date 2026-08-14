"""Pitch usage and outcome calculations.

Kept intentionally small -- mix, strike rate, swing/whiff/chase rate and
pitch shape -- but structured so additional Statcast metrics (exit velocity,
expected outcomes, etc.) can be added as more functions over the same
:class:`~mound.pitches.PitchCollection` shape.
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
        df = df[df["is_swing"].fillna(False).astype(bool)]

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
