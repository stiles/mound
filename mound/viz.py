"""Plot pitch locations against a theoretical strike zone.

Kept to matplotlib alone (no seaborn/scipy) to minimize dependencies. Heat
maps are built with a plain 2D histogram rather than a kernel density
estimate, which is a reasonable tradeoff for a small pitch sample.

Chart chrome (typography, color, spacing) follows a few house rules: let the
strike zone and the pitches carry the visual weight, keep structural
elements (spines, gridlines, ticks) light or absent, and put context in a
headline/dek above the plot and a source line below it rather than in axis
titles or a boxed legend.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import MaxNLocator

from mound.zone import SZ_LEFT_FEET, SZ_RIGHT_FEET

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from mound.pitches import PitchCollection

# Typical strike-zone vertical range, used only as a fallback when a
# collection has no sz_top/sz_bot data to average.
DEFAULT_SZ_TOP = 3.5
DEFAULT_SZ_BOT = 1.5

PLOT_X_RANGE = (-2.5, 2.5)
PLOT_Z_RANGE = (-0.5, 5.0)

INK = "#1A1A1A"
MUTED = "#6E6E6E"
FAINT = "#8E8E8E"
LINE = "#B1B1B1"
BACKGROUND = "#FEFEFE"

# A pitch's color is fixed by its canonical name (not assigned per-plot), so
# the same pitch type reads the same way across different charts. Grouped
# loosely by family: fastballs (blue), breaking balls (red/purple),
# offspeed (orange/teal).
PITCH_TYPE_COLORS: dict[str, str] = {
    "four-seam fastball": "#5194C3",
    "two-seam fastball": "#7FB2D9",
    "sinker": "#7FB2D9",
    "cutter": "#3D7CA6",
    "slider": "#C52622",
    "sweeper": "#DB6A61",
    "slurve": "#DB6A61",
    "curveball": "#7C4EA5",
    "knuckle curve": "#9B72B0",
    "slow curve": "#9B72B0",
    "changeup": "#53A796",
    "splitter": "#F18851",
    "forkball": "#F0A15C",
    "screwball": "#F8C153",
    "knuckleball": "#8E8E8E",
    "eephus": "#8E8E8E",
}
DEFAULT_PITCH_COLOR = "#4D4D4D"

MOUND_STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "text.color": INK,
    "axes.edgecolor": LINE,
    "axes.labelcolor": FAINT,
    "xtick.color": FAINT,
    "ytick.color": FAINT,
    "figure.facecolor": BACKGROUND,
    "axes.facecolor": BACKGROUND,
    "savefig.facecolor": BACKGROUND,
}


def _color_for(pitch_type: str | None) -> str:
    return PITCH_TYPE_COLORS.get(pitch_type or "", DEFAULT_PITCH_COLOR)


def _format_date(d: date) -> str:
    return d.strftime("%b %d, %Y").replace(" 0", " ")


def _date_range_label(raw_dates) -> str | None:
    parsed = sorted({datetime.strptime(d, "%Y-%m-%d").date() for d in raw_dates.dropna().unique()})
    if not parsed:
        return None
    if len(parsed) == 1:
        return _format_date(parsed[0])
    if parsed[0].year == parsed[-1].year:
        return f"{parsed[0].strftime('%b %d').replace(' 0', ' ')}–{_format_date(parsed[-1])}"
    return f"{_format_date(parsed[0])} – {_format_date(parsed[-1])}"


def _default_headline(collection: PitchCollection, df) -> str:
    who = collection.pitcher.full_name if collection.pitcher else "Pitcher"
    pitch_types = df["pitch_type"].dropna().unique() if not df.empty else []
    if len(pitch_types) == 1:
        return f"{who}\u2019s {pitch_types[0]} locations"
    return f"{who}\u2019s pitch locations"


def _default_subtitle(df) -> str:
    if df.empty:
        return "No pitches with location data"
    parts = [f"{len(df)} pitch{'es' if len(df) != 1 else ''}"]
    if df["is_strike"].notna().any():
        parts.append(f"{df['is_strike'].mean() * 100:.0f}% strikes")
    date_label = _date_range_label(df["game_date"]) if "game_date" in df else None
    if date_label:
        parts.append(date_label)
    return " \u00b7 ".join(parts)


def _draw_home_plate(ax: Axes) -> None:
    # A simplified plate silhouette for ground-level context: the flat edge
    # (where a pitch actually crosses) sits just under the zone, tapering to
    # a point below -- mirroring how Statcast's own zone plots anchor the
    # strike zone to the plate.
    half_width = (SZ_RIGHT_FEET - SZ_LEFT_FEET) / 2
    edge_z, corner_z, point_z = -0.05, -0.24, -0.46
    vertices = [
        (-half_width, edge_z),
        (half_width, edge_z),
        (half_width, corner_z),
        (0.0, point_z),
        (-half_width, corner_z),
    ]
    plate = Polygon(
        vertices, closed=True, facecolor="#ECECEC", edgecolor=LINE, linewidth=0.75, zorder=0
    )
    ax.add_patch(plate)


def _draw_strike_zone(ax: Axes, sz_top: float, sz_bot: float) -> None:
    rect = Rectangle(
        (SZ_LEFT_FEET, sz_bot),
        SZ_RIGHT_FEET - SZ_LEFT_FEET,
        sz_top - sz_bot,
        fill=False,
        edgecolor=INK,
        linewidth=1.3,
        zorder=3,
    )
    ax.add_patch(rect)


def _style_axes(ax: Axes) -> None:
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, labelsize=9, colors=FAINT)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.set_xlabel("")
    ax.set_ylabel("")


def _draw_legend_key(ax: Axes, labels: list[str]) -> None:
    # A halo (rather than a boxed/framed legend) keeps the key legible over
    # dense clusters of points without adding a hard-edged UI element.
    halo = [path_effects.withStroke(linewidth=3, foreground=BACKGROUND)]
    y = 0.97
    for label in labels:
        text = ax.text(
            0.04,
            y,
            f"\u25cf {label}",
            transform=ax.transAxes,
            fontsize=9.5,
            fontweight="medium",
            color=_color_for(label),
            ha="left",
            va="top",
        )
        text.set_path_effects(halo)
        y -= 0.058


def _add_chrome(fig: Figure, headline: str, subtitle: str, source: str) -> None:
    fig.text(
        0.07, 0.965, headline, fontsize=15, fontweight="semibold", color=INK, ha="left", va="top"
    )
    if subtitle:
        fig.text(0.07, 0.918, subtitle, fontsize=10.5, color=MUTED, ha="left", va="top")
    if source:
        fig.text(0.07, 0.02, source, fontsize=8.5, color=FAINT, ha="left", va="bottom")


def plot_zone(
    collection: PitchCollection,
    kind: str = "scatter",
    color_by: str | None = "pitch_type",
    ax: Axes | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str = "Source: MLB Statcast (Baseball Savant), via Mound",
    out: str | None = None,
) -> Axes:
    """Plot pitch locations against the strike zone.

    Args:
        collection: pitches to plot.
        kind: ``"scatter"`` for individual pitch points, or ``"heatmap"``
            for a 2D-histogram density plot.
        color_by: column to color/group scatter points by (e.g.
            ``"pitch_type"``); ignored for heatmaps. Pass ``None`` for a
            single color.
        ax: existing matplotlib axes to draw on. A new, fully styled figure
            (with a headline, dek and source line) is created if omitted;
            when an existing ``ax`` is passed, only a left-aligned title is
            set so the chart behaves as a well-mannered subplot.
        title: headline text; auto-generated from the pitcher and pitch
            type(s) shown if omitted.
        subtitle: dek text shown under the headline (pitch count, strike
            rate, date range); auto-generated if omitted, or pass ``""`` to
            omit it entirely. Ignored when ``ax`` is passed in.
        source: source line shown below the chart; pass ``""`` to omit it.
            Ignored when ``ax`` is passed in.
        out: if given, save the figure to this path.
    """
    df = collection.to_frame().dropna(subset=["plate_x", "plate_z"])
    owns_figure = ax is None

    with plt.rc_context(MOUND_STYLE):
        if owns_figure:
            fig, ax = plt.subplots(figsize=(5.2, 6.4))
            fig.subplots_adjust(top=0.86, bottom=0.09, left=0.1, right=0.96)
        else:
            fig = ax.figure

        sz_top = (
            df["sz_top"].mean() if not df.empty and df["sz_top"].notna().any() else DEFAULT_SZ_TOP
        )
        sz_bot = (
            df["sz_bot"].mean() if not df.empty and df["sz_bot"].notna().any() else DEFAULT_SZ_BOT
        )

        group_labels: list[str] = []

        if kind == "heatmap":
            if not df.empty:
                heatmap, _, _ = np.histogram2d(
                    df["plate_x"], df["plate_z"], bins=25, range=[PLOT_X_RANGE, PLOT_Z_RANGE]
                )
                masked = np.ma.masked_equal(heatmap, 0)
                image = ax.imshow(
                    masked.T,
                    origin="lower",
                    extent=[*PLOT_X_RANGE, *PLOT_Z_RANGE],
                    cmap="YlOrRd",
                    aspect="auto",
                    zorder=1,
                )
                if heatmap.max() > 0:
                    cbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.06, shrink=0.85)
                    cbar.outline.set_visible(False)
                    cbar.set_ticks([1, heatmap.max()])
                    cbar.set_ticklabels(["Fewer", "More"])
                    cbar.ax.tick_params(length=0, labelsize=8.5, colors=FAINT)
        elif kind == "scatter":
            if not df.empty and color_by and color_by in df.columns:
                counts = df[color_by].value_counts()
                for value in counts.index:
                    group = df[df[color_by] == value]
                    ax.scatter(
                        group["plate_x"],
                        group["plate_z"],
                        color=_color_for(str(value)),
                        s=44,
                        alpha=0.85,
                        linewidths=0.6,
                        edgecolors=BACKGROUND,
                        zorder=2,
                    )
                group_labels = [str(v) for v in counts.index]
            elif not df.empty:
                ax.scatter(
                    df["plate_x"],
                    df["plate_z"],
                    color=DEFAULT_PITCH_COLOR,
                    s=44,
                    alpha=0.85,
                    linewidths=0.6,
                    edgecolors=BACKGROUND,
                    zorder=2,
                )
        else:
            raise ValueError(f"Unknown plot kind: {kind!r} (expected 'scatter' or 'heatmap')")

        _draw_home_plate(ax)
        _draw_strike_zone(ax, sz_top, sz_bot)

        if len(group_labels) > 1:
            _draw_legend_key(ax, group_labels)

        ax.set_xlim(*PLOT_X_RANGE)
        ax.set_ylim(*PLOT_Z_RANGE)
        ax.set_aspect("equal")
        _style_axes(ax)

        headline = title if title is not None else _default_headline(collection, df)
        if owns_figure:
            dek = subtitle if subtitle is not None else _default_subtitle(df)
            _add_chrome(fig, headline, dek, source)
        else:
            ax.set_title(headline, loc="left", fontsize=12, fontweight="semibold", color=INK)

        if out:
            fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.2)

    return ax
