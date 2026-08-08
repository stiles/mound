"""Pitch usage and outcome calculations.

Kept intentionally small for the prototype -- pitch mix and strike rate --
but structured so additional Statcast metrics (whiff rate, chase rate, exit
velocity, etc.) can be added as more functions over the same
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
