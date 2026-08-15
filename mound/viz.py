"""Plot pitch locations against a theoretical strike zone.

Kept to matplotlib alone for the default path, to minimize dependencies.
``kind="heatmap"`` bins pitches into a plain 2D histogram, a reasonable
tradeoff for a small pitch sample; ``kind="kde"`` trades that simplicity for
a smoother kernel density surface via the optional ``scipy`` dependency
(``pip install "mound[viz]"``), better suited to larger samples.

Chart chrome (typography, color, spacing) follows a few house rules: let the
strike zone and the pitches carry the visual weight, keep structural
elements (spines, gridlines, ticks) light or absent, and put context in a
headline/dek above the plot and a source line below it rather than in axis
titles or a boxed legend.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator

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
# The color for pitches with nothing to distinguish -- a single-color
# scatter, or a value the active palette doesn't know. Green rather than a
# neutral gray so an uncolored plot still belongs to the same family as the
# density surfaces and the site (--color-grass-700).
DEFAULT_PITCH_COLOR = "#1B6B47"

# Batter handedness runs the house green against the splitter's orange:
# grass and clay, the same pairing the density ramp is built on. An earthier
# clay tested better on paper and worse in practice -- green and clay
# collapse into nearly the same olive under red-green color blindness (a 6
# point lightness gap under protanopia), while this pair keeps 20 or more,
# which is what actually separates the two sides for a reader who can't use
# the hue difference.
STAND_COLORS: dict[str, str] = {
    "L": "#1B6B47",
    "R": "#F18851",
}

# Which palette applies to which column. A column with no entry here (or a
# value the palette doesn't know) falls back to DEFAULT_PITCH_COLOR.
_COLUMN_COLORS: dict[str, dict[str, str]] = {
    "pitch_type": PITCH_TYPE_COLORS,
    "batter_stand": STAND_COLORS,
}

# Density surfaces (heatmap/KDE) share one sequential ramp: ColorBrewer's
# 7-class YlGn, which already steps down in even increments of perceived
# lightness (so it reads evenly and survives grayscale), plus one darker
# stop of our own. YlGn ends at a medium-dark green, which left the hottest
# cell short of the punch a peak should have; #0F3D2A is the site's own
# darkest green, so the extra depth also lands the ramp on a color the page
# around an embedded chart already uses. The yellow low end is deliberate --
# it keeps a one-pitch bin visible against the plot background, which a
# green that faint wouldn't be.
DENSITY_CMAP = LinearSegmentedColormap.from_list(
    "mound_density",
    ["#FFFFCC", "#D9F0A3", "#ADDD8E", "#78C679", "#41AB5D", "#238443", "#005A32", "#0F3D2A"],
)

# A KDE's raw density values skew heavily toward the low end (a long, faint
# tail surrounds any real cluster), which is exactly what made early
# versions of this plot look like a diffuse, unfocused cloud. A super-linear
# gamma pushes that tail further toward the background color and reserves
# saturated color for the genuine peak, so the "hot zone" reads clearly at
# a glance instead of the whole plot looking uniformly warm.
KDE_GAMMA = 1.8

# A fixed bandwidth factor (rather than scipy's default n-dependent Scott's
# rule) keeps smoothing consistent across pitch counts. Scott's rule grows
# the bandwidth as a sample shrinks to control estimator variance, which is
# the right call for rigorous density estimation but looks wrong here --
# a 5-pitch pitch type would get smoothed into one shapeless blob covering
# most of the strike zone. This value was chosen by eye against real
# samples ranging from 5 to 90+ pitches as the tightest setting that still
# reads as one smooth surface rather than fragmenting into separate islands.
KDE_DEFAULT_BW = 0.45

# Below this fraction of the peak, a KDE surface is treated as background
# and left transparent, so the home plate/strike zone drawn underneath
# stays visible and the surface's edges look like a defined "figure" rather
# than an amorphous cloud stretching to the plot's corners.
KDE_MASK_FRACTION = 0.10

# Human-readable panel titles and legend labels for known ``split_by``/
# ``color_by`` columns and values. Falls back to ``str(value)`` for anything
# not listed here.
_FACET_LABELS: dict[str, dict[str, str]] = {
    "batter_stand": {"L": "vs LHB", "R": "vs RHB"},
}
_FACET_ORDER: dict[str, dict[str, int]] = {
    "batter_stand": {"L": 0, "R": 1},
}

# Friendlier names users can pass to ``split_by``/``color_by`` in place of
# the underlying column.
_COLUMN_ALIASES: dict[str, str] = {
    "stand": "batter_stand",
}

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


def _color_for(column: str | None, value) -> str:
    palette = _COLUMN_COLORS.get(column or "", {})
    return palette.get(str(value), DEFAULT_PITCH_COLOR)


def _resolve_column(name: str, df, *, param: str) -> str:
    column = _COLUMN_ALIASES.get(name, name)
    if column not in df.columns:
        raise ValueError(f"Cannot {param} unknown column: {name!r}")
    return column


def _facet_label(column: str, value) -> str:
    return _FACET_LABELS.get(column, {}).get(value, str(value))


def _facet_values(column: str, df) -> list:
    values = list(df[column].dropna().unique())
    order = _FACET_ORDER.get(column, {})
    values.sort(key=lambda v: (order.get(v, 99), str(v)))
    return values


def _group_values(column: str, df) -> list:
    """Order the values of a ``color_by`` column, for drawing and the key.

    Columns with a natural order (handedness reads L then R, matching the
    panel order ``split_by`` uses) follow it; everything else falls back to
    most-common-first, so a pitch-type key doubles as a pitch mix and the
    busiest group is drawn first, underneath the rest.
    """
    if column in _FACET_ORDER:
        return _facet_values(column, df)
    return list(df[column].value_counts().index)


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
    pitch_types = df["pitch_type"].dropna().unique() if not df.empty else []
    what = pitch_types[0] if len(pitch_types) == 1 else "pitch"

    # A batter-side collection is about pitches faced, so name the hitter as
    # the target rather than crediting him with throwing them.
    if collection.batter and not collection.pitcher:
        return f"{what.capitalize()} locations to {collection.batter.full_name}"

    who = collection.pitcher.full_name if collection.pitcher else "Pitcher"
    return f"{who}\u2019s {what} locations"


def _default_subtitle(collection: PitchCollection, df) -> str:
    if df.empty:
        return "No pitches with location data"
    parts = [f"{len(df)} pitch{'es' if len(df) != 1 else ''}"]
    if df["is_strike"].notna().any():
        parts.append(f"{df['is_strike'].mean() * 100:.0f}% strikes")

    # A pitcher's plot narrowed to one hitter is a matchup, and worth saying
    # so -- unless the headline already names him, as it does batter-side.
    batters = df["batter_name"].dropna().unique() if "batter_name" in df else []
    if len(batters) == 1 and not collection.batter:
        parts.append(f"vs. {batters[0]}")

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

    y_locator = MaxNLocator(nbins=5, integer=True)
    ax.yaxis.set_major_locator(y_locator)
    # There's no axis label to say these ticks are feet, so mark just the
    # topmost one with a foot mark rather than repeating a unit on every
    # tick (which would compete with the pitch data for attention).
    ylim = ax.get_ylim()
    visible_ticks = [t for t in y_locator.tick_values(*ylim) if ylim[0] <= t <= ylim[1]]
    top_tick = max(visible_ticks) if visible_ticks else None
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _pos: f"{v:g}\u2032" if v == top_tick else f"{v:g}")
    )

    ax.set_xlabel("")
    ax.set_ylabel("")


def _draw_legend_key(ax: Axes, column: str, values: list) -> None:
    # A halo (rather than a boxed/framed legend) keeps the key legible over
    # dense clusters of points without adding a hard-edged UI element.
    halo = [path_effects.withStroke(linewidth=3, foreground=BACKGROUND)]
    y = 0.97
    for value in values:
        text = ax.text(
            0.04,
            y,
            f"\u25cf {_facet_label(column, value)}",
            transform=ax.transAxes,
            fontsize=9.5,
            fontweight="medium",
            color=_color_for(column, value),
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


def _draw_kde(ax: Axes, df, bw_method: float | str | None) -> None:
    # A KDE needs real spread on both axes -- a single point, or points that
    # are collinear on x or z, make gaussian_kde's covariance matrix
    # singular. Fall back to drawing nothing rather than raising, matching
    # the histogram branch's quiet no-op on an empty df.
    if df.empty or len(df) < 2 or df["plate_x"].nunique() < 2 or df["plate_z"].nunique() < 2:
        return

    try:
        from scipy.stats import gaussian_kde
    except ImportError as exc:
        raise ImportError(
            "kind='kde' requires scipy. Install it with: pip install 'mound[viz]'"
        ) from exc

    effective_bw = bw_method if bw_method is not None else KDE_DEFAULT_BW
    kde = gaussian_kde(np.vstack([df["plate_x"], df["plate_z"]]), bw_method=effective_bw)
    xs = np.linspace(*PLOT_X_RANGE, 200)
    zs = np.linspace(*PLOT_Z_RANGE, 200)
    grid_x, grid_z = np.meshgrid(xs, zs)
    density = kde(np.vstack([grid_x.ravel(), grid_z.ravel()])).reshape(grid_x.shape)

    # A KDE surface has no true zeros to mask (unlike the histogram's empty
    # bins), so the home plate/strike zone drawn underneath would otherwise
    # be fully hidden under a wash of low-density color. Masking the faint
    # tail below a fraction of the peak keeps that same "figure over a
    # transparent background" look as the heatmap.
    masked = np.ma.masked_less(density, density.max() * KDE_MASK_FRACTION)
    ax.imshow(
        masked,
        origin="lower",
        extent=[*PLOT_X_RANGE, *PLOT_Z_RANGE],
        cmap=DENSITY_CMAP,
        norm=PowerNorm(gamma=KDE_GAMMA, vmin=density.min(), vmax=density.max()),
        aspect="auto",
        zorder=1,
    )
    # No colorbar: a KDE's density values are an arbitrary scale (they
    # integrate to 1 over the plane, not a pitch count), so a numeric or
    # "Fewer"/"More" legend would either be meaningless or redundant with
    # what the color itself already shows -- darker means more pitches.


def _draw_panel(
    ax: Axes, df, kind: str, color_column: str | None, bw_method: float | str | None = None
) -> list:
    """Draw pitch markers plus home plate and strike zone onto ``ax``.

    ``color_column`` is an already-resolved DataFrame column (see
    :func:`_resolve_column`). Returns the scatter group values, in the order
    they were drawn, for an optional legend key; empty for heatmaps/KDE
    surfaces or single-color scatters.
    """
    sz_top = df["sz_top"].mean() if not df.empty and df["sz_top"].notna().any() else DEFAULT_SZ_TOP
    sz_bot = df["sz_bot"].mean() if not df.empty and df["sz_bot"].notna().any() else DEFAULT_SZ_BOT

    group_values: list = []

    if kind == "heatmap":
        if not df.empty:
            heatmap, _, _ = np.histogram2d(
                df["plate_x"], df["plate_z"], bins=25, range=[PLOT_X_RANGE, PLOT_Z_RANGE]
            )
            masked = np.ma.masked_equal(heatmap, 0)
            # No colorbar, matching the KDE branch: darker means more pitches
            # is legible without one, and the vertical bar cost more than it
            # explained -- it squeezed the panel narrower than every other
            # plot kind, pulling the strike zone and plate off-center.
            ax.imshow(
                masked.T,
                origin="lower",
                extent=[*PLOT_X_RANGE, *PLOT_Z_RANGE],
                cmap=DENSITY_CMAP,
                aspect="auto",
                zorder=1,
            )
    elif kind == "kde":
        _draw_kde(ax, df, bw_method)
    elif kind == "scatter":
        if not df.empty and color_column:
            group_values = _group_values(color_column, df)
            for value in group_values:
                group = df[df[color_column] == value]
                ax.scatter(
                    group["plate_x"],
                    group["plate_z"],
                    color=_color_for(color_column, value),
                    s=44,
                    alpha=0.85,
                    linewidths=0.6,
                    edgecolors=BACKGROUND,
                    zorder=2,
                )
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
        raise ValueError(f"Unknown plot kind: {kind!r} (expected 'scatter', 'heatmap' or 'kde')")

    _draw_home_plate(ax)
    _draw_strike_zone(ax, sz_top, sz_bot)
    return group_values


def _finish_panel(ax: Axes) -> None:
    ax.set_xlim(*PLOT_X_RANGE)
    ax.set_ylim(*PLOT_Z_RANGE)
    ax.set_aspect("equal")
    _style_axes(ax)


def plot_zone(
    collection: PitchCollection,
    kind: str = "scatter",
    color_by: str | None = "pitch_type",
    split_by: str | None = None,
    bw_method: float | str | None = None,
    ax: Axes | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str = "Source: MLB Statcast (Baseball Savant), via Mound",
    out: str | None = None,
) -> Axes:
    """Plot pitch locations against the strike zone.

    Args:
        collection: pitches to plot.
        kind: ``"scatter"`` for individual pitch points, ``"heatmap"`` for
            a 2D-histogram density plot, or ``"kde"`` for a smoother kernel
            density estimate (requires the optional ``scipy`` dependency;
            install with ``pip install "mound[viz]"``).
        color_by: column to color/group scatter points by, either
            ``"pitch_type"`` (the default) or ``"stand"``/``"batter_stand"``
            for a lefties/righties breakdown within one panel, as a lighter
            alternative to ``split_by``'s separate panels. Ignored for
            heatmaps/KDE. Pass ``None`` for a single color, which is also
            what a column with only one value present falls back to. Any
            other column works too, but its values share one color, since
            only these two have a palette.
        split_by: column to facet into side-by-side panels, e.g.
            ``"stand"``/``"batter_stand"`` for a vs-lefties/vs-righties
            breakdown. One panel is drawn per non-null value present, each
            with its own strike zone and pitch count. Cannot be combined
            with an existing ``ax``.
        bw_method: bandwidth passed through to ``scipy.stats.gaussian_kde``
            when ``kind="kde"``; ignored otherwise. Defaults to a fixed
            factor (``KDE_DEFAULT_BW`` in ``mound/viz.py``) tuned for a
            clearly defined "hot zone" rather than scipy's own default
            (Scott's rule), which over-smooths small pitch samples into a
            single shapeless blob.
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
    color_column = _resolve_column(color_by, df, param="color_by") if color_by else None

    # A color that separates nothing isn't worth spending: a plot of one
    # pitch type has no second group to tell it apart from, and the headline
    # already names it. Those fall back to the house color, which is also
    # why no legend key is drawn for a single group. Decided against the
    # whole frame rather than per panel, so a faceted figure can't end up
    # with one panel keyed by color and another ignoring it.
    if color_column and df[color_column].nunique() <= 1:
        color_column = None

    if split_by is not None:
        if ax is not None:
            raise ValueError("split_by cannot be combined with an existing ax")
        return _plot_zone_faceted(
            collection, df, kind, color_column, split_by, bw_method, title, subtitle, source, out
        )

    owns_figure = ax is None

    with plt.rc_context(MOUND_STYLE):
        if owns_figure:
            fig, ax = plt.subplots(figsize=(5.2, 6.4))
            fig.subplots_adjust(top=0.86, bottom=0.09, left=0.1, right=0.96)
        else:
            fig = ax.figure

        group_values = _draw_panel(ax, df, kind, color_column, bw_method)
        if len(group_values) > 1:
            _draw_legend_key(ax, color_column, group_values)
        _finish_panel(ax)

        headline = title if title is not None else _default_headline(collection, df)
        if owns_figure:
            dek = subtitle if subtitle is not None else _default_subtitle(collection, df)
            _add_chrome(fig, headline, dek, source)
        else:
            ax.set_title(headline, loc="left", fontsize=12, fontweight="semibold", color=INK)

        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.2)

    return ax


def _plot_zone_faceted(
    collection: PitchCollection,
    df,
    kind: str,
    color_column: str | None,
    split_by: str,
    bw_method: float | str | None,
    title: str | None,
    subtitle: str | None,
    source: str,
    out: str | None,
):
    column = _resolve_column(split_by, df, param="split_by")
    values = _facet_values(column, df)
    if not values:
        raise ValueError(f"No non-null values found for split_by={split_by!r}")

    with plt.rc_context(MOUND_STYLE):
        fig, axes = plt.subplots(1, len(values), figsize=(5.0 * len(values), 6.4), sharey=True)
        axes = np.atleast_1d(axes)
        fig.subplots_adjust(top=0.84, bottom=0.09, left=0.08, right=0.96, wspace=0.12)

        for i, (value, panel_ax) in enumerate(zip(values, axes, strict=True)):
            subset = df[df[column] == value]
            group_values = _draw_panel(panel_ax, subset, kind, color_column, bw_method)
            if i == 0 and len(group_values) > 1:
                _draw_legend_key(panel_ax, color_column, group_values)
            _finish_panel(panel_ax)
            if i > 0:
                panel_ax.tick_params(labelleft=False)

            panel_title = f"{_facet_label(column, value)} (n={len(subset)})"
            panel_ax.set_title(
                panel_title, loc="left", fontsize=11, fontweight="semibold", color=INK
            )

        headline = title if title is not None else _default_headline(collection, df)
        dek = subtitle if subtitle is not None else _default_subtitle(collection, df)
        _add_chrome(fig, headline, dek, source)

        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.2)

    return axes
