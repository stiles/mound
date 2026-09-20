"""Plot pitch locations against a theoretical strike zone.

Kept to matplotlib alone for the default path, to minimize dependencies.
``kind="heatmap"`` bins pitches into hexagons rather than squares, wide
enough to pool pitches thrown inches apart instead of scattering them into
neighboring cells; ``kind="zones"`` counts them into Statcast's numbered
zones instead of arbitrary bins, so the chart speaks the numbering people
already argue in; ``kind="kde"`` trades either kind of binning for a
smoother kernel density surface via the optional ``scipy`` dependency
(``pip install "mound[viz]"``), better suited to larger samples.

Chart chrome (typography, color, spacing) follows a few house rules: let the
strike zone and the pitches carry the visual weight, keep structural
elements (spines, gridlines, ticks) light or absent, and put context in a
headline/dek above the plot and a source line below it rather than in axis
titles or a boxed legend.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize, PowerNorm, to_rgb
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator

from mound.zone import SZ_LEFT_FEET, SZ_RIGHT_FEET, zone_grid

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from mound.pitches import PitchCollection

# Typical strike-zone vertical range, used only as a fallback when a
# collection has no sz_top/sz_bot data to average.
DEFAULT_SZ_TOP = 3.5
DEFAULT_SZ_BOT = 1.5

PLOT_X_RANGE = (-2.5, 2.5)
_X_SPAN = PLOT_X_RANGE[1] - PLOT_X_RANGE[0]

# The frame's floor is fixed -- it's what leaves room for the home plate
# glyph, whose lowest point sits at -0.46 -- but the ceiling is no longer a
# flat constant. A typical outing's highest pitch lands well under a
# uniform 5' top, which used to spend a fifth of every chart's canvas on
# empty air above the real data. ``_z_range`` derives an honest one instead;
# these are its guardrails, not a substitute for one.
PLOT_Z_BOTTOM = -0.5
Z_TOP_PAD = 1.0
Z_TOP_MIN = 3.8
Z_TOP_MAX = 6.5

# The in-plot legend key floats inside the frame's own top-left corner
# (see ``_draw_legend_key``), which is exactly the corner a tightened frame
# now leaves least clear -- the 97th-percentile ceiling that crops the
# frame is, by definition, close to wherever a chart's highest pitches
# already sit. This extra pad is spent only when a legend is actually going
# to be drawn there, so the common single-color chart keeps the full crop.
LEGEND_TOP_PAD = 0.5

# Inches per foot of plate-coordinate space, shared by both axes so
# ``ax.set_aspect("equal")`` never has to letterbox the panel inside its
# own box. Chosen to match this package's original fixed-frame sizing
# (a 5.5' frame in a 4.9"-tall axes box), so a tightened frame shrinks the
# page it's drawn on rather than leaving the same blank canvas behind.
_INCHES_PER_FOOT = 0.9

# Fixed chrome budgets, in inches, independent of how tall a panel's own
# data region ends up. A panel row's title (used by ``split_by`` and
# ``plot_zone_panels``) gets its own allowance on top of the figure-level
# headline/dek, so a faceted figure's per-panel titles don't crowd into it.
CHROME_TOP_IN = 0.95
CHROME_BOTTOM_IN = 0.60
PANEL_TITLE_IN = 0.32
_LEFT_IN = 0.55
_RIGHT_IN = 0.25
_GUTTER_IN = 0.35

INK = "#1A1A1A"
MUTED = "#6E6E6E"
FAINT = "#8E8E8E"
LINE = "#B1B1B1"
BACKGROUND = "#FEFEFE"

# A pitch's color is fixed by its canonical name (not assigned per-plot), so
# the same pitch type reads the same way across different charts.
#
# Which pitch gets which color was settled by measurement rather than by
# taste. Grouping strictly by family (all the fastballs in blues, all the
# breaking balls in reds) put the closest colors on the pitches most likely
# to share a chart: across 620 pitcher-games of cached feeds, a four-seamer
# and a sinker appear together in 286 of them, and a four-seamer and a
# cutter in 205, so three shades of one blue were doing the most important
# separating. The assignment below maximizes perceptual distance (CIEDE2000,
# counting simulated red-green color blindness at half weight) between the
# pairs that co-occur, weighted by how often they do.
#
# What survives of the family idea is the part that costs nothing: a pitch
# still sits in its family's hue where its family-mates are rarely thrown
# alongside it, which is why the two slider variants stay close (a sweeper
# is a slider) and the sinker doesn't (it's a fastball, but it's the one
# pitch a four-seamer must never blur into).
PITCH_TYPE_COLORS: dict[str, str] = {
    "four-seam fastball": "#5194C3",
    "two-seam fastball": "#F18851",
    "sinker": "#F18851",
    "cutter": "#2E6389",
    "slider": "#C52622",
    "sweeper": "#8C1F1C",
    "slurve": "#8C1F1C",
    "curveball": "#4E2E6B",
    "knuckle curve": "#B49AD0",
    "slow curve": "#B49AD0",
    "changeup": "#6FBBA8",
    "splitter": "#2F7367",
    # Statcast's own classifier moves pitches between these two -- Roki
    # Sasaki's splitter is a running example of it, see roki_sasaki_end_to_
    # end.py -- so forkball stays in the same green family as a family cue,
    # but on a different hue (moss rather than teal) rather than a shade of
    # the same one. A shade apart read as barely distinguishable wherever
    # the two are named side by side rather than blended, a table of pitch
    # types being the case that actually turned this up.
    "forkball": "#3E7133",
    "screwball": "#F8C153",
    "knuckleball": "#8E8E8E",
    "eephus": "#8E8E8E",
}
# The color for pitches with nothing to distinguish -- a single-color
# scatter, or a value the active palette doesn't know. Green rather than a
# neutral gray so an uncolored plot still belongs to the same family as the
# density surfaces and the site (--color-grass-700).
DEFAULT_PITCH_COLOR = "#1B6B47"

# Batter handedness runs the house green against a clay orange: grass and
# clay, the same pairing the density ramp is built on. An earthier
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

# Hexagons rather than squares for ``kind="heatmap"``. A square grid fine
# enough to resolve a pitch's own footprint (about 0.24' across) checkers
# into isolated single-count cells scattered well outside any real cluster,
# since that's finer than the spread between two pitches thrown inches
# apart. This target cell width sits a little wider than a ball on purpose,
# so nearby pitches pool into one cell instead of tiling into neighbors that
# read as noise, and hexagons tile that pooling without the seams a coarser
# square grid would show.
HEATMAP_CELL_FEET = 0.32

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


# A drawable cell, as matplotlib's Rectangle takes it: (x, z, width, height).
_Rect = tuple[float, float, float, float]


def _draw_zone_grid(ax: Axes, sz_top: float, sz_bot: float) -> None:
    """Draw the interior lines of Statcast's 3x3 grid inside the zone.

    Light enough to read as chrome under the pitches rather than as data,
    and clipped to the drawn strike zone: the grid's own outer edge sits a
    ball radius outside it, which would look like a second, wrong zone box.
    """
    xs, zs = zone_grid(sz_top, sz_bot)
    for x in xs[1:3]:
        ax.plot([x, x], [sz_bot, sz_top], color=LINE, linewidth=0.7, zorder=2.5)
    for z in zs[1:3]:
        ax.plot([SZ_LEFT_FEET, SZ_RIGHT_FEET], [z, z], color=LINE, linewidth=0.7, zorder=2.5)


def _zone_cells(sz_top: float, sz_bot: float) -> tuple[dict[int, _Rect], dict[int, _Rect]]:
    """Rectangles to shade per zone number, inner cells and outer ones.

    Each is keyed by zone number and valued ``(x, z, width, height)``.
    Zones 1-9 are the grid itself. Zones 11-14 aren't rectangles at all in
    the data -- they're quadrants running out to wherever a pitch landed --
    so they're drawn as quarters of a box one cell deep around the grid, far
    enough out to read as a border and close enough to keep the zone the
    subject. Each overlaps the grid and is meant to be drawn under it, so
    only the outer ring shows. A pitch counted in zone 11 may well have been
    thrown further out than the cell labeling it.
    """
    xs, zs = zone_grid(sz_top, sz_bot)
    cell_w, cell_h = (xs[3] - xs[0]) / 3, (zs[3] - zs[0]) / 3

    inner = {}
    for row in range(3):
        for column in range(3):
            inner[1 + row * 3 + column] = (xs[column], zs[2 - row], cell_w, cell_h)

    left, right = xs[0] - cell_w, xs[3] + cell_w
    bottom, top = zs[0] - cell_h, zs[3] + cell_h
    mid_x, mid_z = (xs[0] + xs[3]) / 2, (zs[0] + zs[3]) / 2
    outer = {
        11: (left, mid_z, mid_x - left, top - mid_z),
        12: (mid_x, mid_z, right - mid_x, top - mid_z),
        13: (left, bottom, mid_x - left, mid_z - bottom),
        14: (mid_x, bottom, right - mid_x, mid_z - bottom),
    }
    return inner, outer


def _corner_of(number: int, rect: _Rect) -> tuple[float, float]:
    """Where to label an outer zone: the corner of the ring it owns."""
    x, z, width, height = rect
    inset_x, inset_z = width / 6, height / 6
    left = number in (11, 13)
    lower = number in (13, 14)
    return (
        x + inset_x if left else x + width - inset_x,
        z + inset_z if lower else z + height - inset_z,
    )


def _draw_zone_counts(ax: Axes, df, sz_top: float, sz_bot: float) -> None:
    """Fill each Statcast zone by how many pitches landed in it.

    Counts come from each pitch's own ``zone``, measured against the batter
    it was thrown to, while the cells are drawn from the panel's average
    zone -- the same averaging every strike zone in these plots already
    does. So a pitch can be counted in a cell its own dot wouldn't sit in.

    The heavy line around the nine cells stands in for the strike zone box
    the other plot kinds draw, and sits a ball radius outside it, because
    that wider edge is the one the numbering is cut on.

    Only the nine are shaded. Zones 11-14 cover unbounded area, so they
    collect more pitches than any one cell almost by definition -- putting
    them on the same ramp would darken the ring, flatten the nine cells that
    are the point of the chart, and imply a comparison that isn't there.
    They carry their counts as numbers instead.
    """
    inner, outer = _zone_cells(sz_top, sz_bot)
    counts = df["zone"].dropna().astype(int).value_counts().to_dict() if not df.empty else {}
    busiest = max((counts.get(n, 0) for n in inner), default=0)

    def cell(rect: _Rect, facecolor, zorder: float) -> None:
        x, z, width, height = rect
        ax.add_patch(
            Rectangle(
                (x, z),
                width,
                height,
                facecolor=facecolor,
                edgecolor=LINE,
                linewidth=0.7,
                zorder=zorder,
            )
        )

    for number, rect in outer.items():
        cell(rect, BACKGROUND, zorder=1)
        x, z = _corner_of(number, rect)
        # Muted, so the ring reads as annotation and the nine cells stay the
        # subject of the chart.
        _label_cell(ax, x, z, number, int(counts.get(number, 0)), MUTED)

    for number, rect in inner.items():
        count = int(counts.get(number, 0))
        # Shade from the same ramp the density surfaces use, but start above
        # its palest stop so an empty cell reads as empty rather than as one
        # pitch. Numbers stay legible either way, so an empty grid is still
        # a labeled diagram of the zone.
        share = count / busiest if busiest else 0.0
        facecolor = DENSITY_CMAP(0.15 + 0.85 * share) if count else BACKGROUND
        cell(rect, facecolor, zorder=1.5)
        x, z, width, height = rect
        ink = _readable_on(facecolor) if count else FAINT
        _label_cell(ax, x + width / 2, z + height / 2, number, count, ink)

    xs, zs = zone_grid(sz_top, sz_bot)
    ax.add_patch(
        Rectangle(
            (xs[0], zs[0]),
            xs[3] - xs[0],
            zs[3] - zs[0],
            fill=False,
            edgecolor=INK,
            linewidth=1.3,
            zorder=3,
        )
    )


def _readable_on(facecolor) -> str:
    """Light or dark label ink, whichever the fill can carry.

    The density ramp runs from near-white yellow to near-black green, so a
    fixed choice loses one end or the other. Weighted for how bright each
    channel looks (green far more than blue), and switched at the midpoint,
    which for this ramp falls inside the green where either color would do.
    """
    red, green, blue = to_rgb(facecolor)
    brightness = 0.299 * red + 0.587 * green + 0.114 * blue
    return INK if brightness > 0.5 else BACKGROUND


def _label_cell(ax: Axes, x: float, z: float, number: int, count: int, ink: str) -> None:
    ax.text(
        x,
        z,
        str(count),
        ha="center",
        va="center",
        fontsize=12 if number < 10 else 10.5,
        fontweight="semibold" if count else "normal",
        color=ink,
        zorder=2,
    )
    # The zone number, small and under the count, so the chart teaches the
    # numbering that --zone and filter(zone=...) take without competing
    # with the counts for the eye.
    ax.text(
        x,
        z - 0.135,
        str(number),
        ha="center",
        va="center",
        fontsize=7.5,
        color=ink,
        alpha=0.6,
        zorder=2,
    )


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


def _draw_legend_key(ax: Axes, column: str, values: list, top: float = 0.97) -> None:
    # A halo (rather than a boxed/framed legend) keeps the key legible over
    # dense clusters of points without adding a hard-edged UI element.
    halo = [path_effects.withStroke(linewidth=3, foreground=BACKGROUND)]
    y = top
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


# Chrome text sits a fixed distance from the figure's own edges, in inches,
# rather than at a fixed fraction of it. A fraction tuned against one
# figure height (the original fixed-frame default) drifts once panels start
# sizing themselves to their data: the same 0.965 that sat a quarter-inch
# under the top edge of a tall figure lands twice as close on a short one.
_HEADLINE_FROM_TOP_IN = 0.30
_SUBTITLE_FROM_TOP_IN = 0.64
_SOURCE_FROM_BOTTOM_IN = 0.20
_CHROME_LEFT_IN = 0.55


def _add_chrome(fig: Figure, headline: str, subtitle: str, source: str) -> None:
    height = fig.get_size_inches()[1]
    left = _CHROME_LEFT_IN / fig.get_size_inches()[0]

    fig.text(
        left,
        1 - _HEADLINE_FROM_TOP_IN / height,
        headline,
        fontsize=17,
        fontweight="bold",
        color=INK,
        ha="left",
        va="top",
    )
    if subtitle:
        fig.text(
            left,
            1 - _SUBTITLE_FROM_TOP_IN / height,
            subtitle,
            fontsize=11.5,
            color=MUTED,
            ha="left",
            va="top",
        )
    if source:
        fig.text(
            left,
            _SOURCE_FROM_BOTTOM_IN / height,
            source,
            fontsize=8.5,
            color=FAINT,
            ha="left",
            va="bottom",
        )


def _draw_kde(ax: Axes, df, bw_method: float | str | None, z_range: tuple[float, float]) -> None:
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
    zs = np.linspace(*z_range, 200)
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
        extent=[*PLOT_X_RANGE, *z_range],
        cmap=DENSITY_CMAP,
        norm=PowerNorm(gamma=KDE_GAMMA, vmin=density.min(), vmax=density.max()),
        aspect="auto",
        zorder=1,
    )
    # No colorbar: a KDE's density values are an arbitrary scale (they
    # integrate to 1 over the plane, not a pitch count), so a numeric or
    # "Fewer"/"More" legend would either be meaningless or redundant with
    # what the color itself already shows -- darker means more pitches.


def _zone_bounds(df) -> tuple[float, float]:
    """The strike zone this panel draws, averaged across whoever it faced.

    Falls back to a typical zone when a collection carries no ``sz_top``/
    ``sz_bot`` at all -- an empty collection, most often.
    """
    sz_top = df["sz_top"].mean() if not df.empty and df["sz_top"].notna().any() else DEFAULT_SZ_TOP
    sz_bot = df["sz_bot"].mean() if not df.empty and df["sz_bot"].notna().any() else DEFAULT_SZ_BOT
    return sz_top, sz_bot


def _z_range(df, sz_top: float, *, legend: bool = False) -> tuple[float, float]:
    """The frame's vertical bounds, cropped to what this panel actually draws.

    The floor is fixed (see :data:`PLOT_Z_BOTTOM`); the ceiling starts a
    fixed pad above the zone and extends only as far as the pitches in
    ``df`` need, so a typical sample doesn't carry a full foot of empty
    canvas above its tallest pitch. Sized off the 97th percentile rather
    than the true max, so a stray one- or two-pitch outlier -- a fastball
    that sailed to the backstop, tracked and real, but not the shape of the
    outing -- doesn't stretch the frame for the other 98% of it; that pitch
    still lands wherever it lands, just possibly off the top of the frame,
    the same trade a boxplot makes with its own whiskers. Rounded up to the
    nearest half foot so the y-axis lands on clean tick values.

    ``legend=True`` adds :data:`LEGEND_TOP_PAD`, for a panel whose in-plot
    key will float in this same top-left corner.
    """
    top = sz_top + Z_TOP_PAD
    if not df.empty and df["plate_z"].notna().any():
        top = max(top, df["plate_z"].quantile(0.97) + 0.4)
    if legend:
        top += LEGEND_TOP_PAD
    top = min(max(top, Z_TOP_MIN), Z_TOP_MAX)
    top = math.ceil(top * 2) / 2
    return PLOT_Z_BOTTOM, top


def _draw_panel(
    ax: Axes,
    df,
    kind: str,
    color_column: str | None,
    sz_top: float,
    sz_bot: float,
    z_range: tuple[float, float],
    bw_method: float | str | None = None,
    grid: bool = False,
) -> list:
    """Draw pitch markers plus home plate and strike zone onto ``ax``.

    ``color_column`` is an already-resolved DataFrame column (see
    :func:`_resolve_column`). Returns the scatter group values, in the order
    they were drawn, for an optional legend key; empty for heatmaps/KDE
    surfaces or single-color scatters.
    """
    group_values: list = []

    if kind == "heatmap":
        if not df.empty:
            # Hexagons, not squares -- see HEATMAP_CELL_FEET. ``mincnt=1``
            # leaves a bin with no pitches in it undrawn entirely, rather
            # than shaded at the palette's own zero, so the surface reads as
            # a figure over the background instead of a wall-to-wall grid.
            gridsize = max(6, round(_X_SPAN / HEATMAP_CELL_FEET))
            hexes = ax.hexbin(
                df["plate_x"],
                df["plate_z"],
                gridsize=gridsize,
                extent=[*PLOT_X_RANGE, *z_range],
                cmap=DENSITY_CMAP,
                mincnt=1,
                linewidths=0.2,
                edgecolors=BACKGROUND,
                zorder=1,
            )
            # No colorbar, matching the KDE branch: darker already reads as
            # more pitches, and a vertical bar cost more than it explained
            # -- it squeezed the panel narrower than every other plot kind,
            # pulling the strike zone and plate off-center.
            counts = hexes.get_array()
            if counts.size:
                hexes.set_norm(Normalize(vmin=0, vmax=counts.max()))
    elif kind == "zones":
        _draw_zone_counts(ax, df, sz_top, sz_bot)
    elif kind == "kde":
        _draw_kde(ax, df, bw_method, z_range)
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
        raise ValueError(
            f"Unknown plot kind: {kind!r} (expected 'scatter', 'heatmap', 'zones' or 'kde')"
        )

    _draw_home_plate(ax)
    # `zones` draws its own cells and its own outer edge, so the grid
    # overlay would double the lines and the zone box would contradict them.
    if kind != "zones":
        if grid:
            _draw_zone_grid(ax, sz_top, sz_bot)
        _draw_strike_zone(ax, sz_top, sz_bot)
    return group_values


def _finish_panel(ax: Axes, z_range: tuple[float, float]) -> None:
    ax.set_xlim(*PLOT_X_RANGE)
    ax.set_ylim(*z_range)
    ax.set_aspect("equal")
    _style_axes(ax)


def _panel_geometry(
    n_cols: int,
    z_range: tuple[float, float],
    *,
    n_rows: int = 1,
    panel_titles: bool = False,
) -> tuple[tuple[float, float], dict]:
    """Figure size and ``subplots_adjust`` kwargs for an ``n_rows``x``n_cols`` grid.

    Every panel shares the same feet-to-inch scale (:data:`_INCHES_PER_FOOT`)
    on both axes, so a tightened ``z_range`` shrinks the figure instead of
    leaving blank canvas behind, and a chart with several panels sits at the
    same physical scale as one with one. Chrome (headline, dek, source, and
    optionally a per-panel title row, repeated for every row of the grid)
    gets a fixed inches budget rather than a fraction of the figure, so it
    doesn't grow or shrink along with it.
    """
    panel_w = _X_SPAN * _INCHES_PER_FOOT
    panel_h = (z_range[1] - z_range[0]) * _INCHES_PER_FOOT
    title_in = PANEL_TITLE_IN if panel_titles else 0

    width = _LEFT_IN + n_cols * panel_w + (n_cols - 1) * _GUTTER_IN + _RIGHT_IN
    content_h = n_rows * (panel_h + title_in) + (n_rows - 1) * _GUTTER_IN
    height = CHROME_TOP_IN + content_h + CHROME_BOTTOM_IN

    rect = {
        "left": _LEFT_IN / width,
        "right": 1 - _RIGHT_IN / width,
        "top": 1 - CHROME_TOP_IN / height,
        "bottom": CHROME_BOTTOM_IN / height,
    }
    if n_cols > 1:
        rect["wspace"] = _GUTTER_IN / panel_w
    if n_rows > 1:
        rect["hspace"] = (_GUTTER_IN + title_in) / panel_h
    return (width, height), rect


def plot_zone(
    collection: PitchCollection,
    kind: str = "scatter",
    color_by: str | None = "pitch_type",
    split_by: str | None = None,
    grid: bool = False,
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
            a hexagonally-binned density plot, ``"zones"`` to count pitches
            into Statcast's numbered zones instead of arbitrary bins, or
            ``"kde"`` for a smoother kernel density estimate (requires the
            optional ``scipy`` dependency; install with
            ``pip install "mound[viz]"``).
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
        grid: draw Statcast's 3x3 grid inside the strike zone, so a scatter
            or heatmap can be read against the same zones ``pitch.zone``
            and ``filter(zone=...)`` use. Redundant with (and ignored by)
            ``kind="zones"``, which draws the cells itself.
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
            collection,
            df,
            kind,
            color_column,
            split_by,
            grid,
            bw_method,
            title,
            subtitle,
            source,
            out,
        )

    owns_figure = ax is None
    sz_top, sz_bot = _zone_bounds(df)
    z_range = _z_range(df, sz_top, legend=color_column is not None)

    with plt.rc_context(MOUND_STYLE):
        if owns_figure:
            figsize, rect = _panel_geometry(1, z_range)
            fig, ax = plt.subplots(figsize=figsize)
            fig.subplots_adjust(**rect)
        else:
            fig = ax.figure

        group_values = _draw_panel(
            ax, df, kind, color_column, sz_top, sz_bot, z_range, bw_method, grid
        )
        if len(group_values) > 1:
            _draw_legend_key(ax, color_column, group_values)
        _finish_panel(ax, z_range)

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
    grid: bool,
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

    # Bounds are drawn from every facet combined, not each one alone, so the
    # strike zone and frame are the same physical size in every panel --
    # comparing spread across two panels only means something if neither one
    # has quietly rescaled to its own subset.
    sz_top, sz_bot = _zone_bounds(df)
    z_range = _z_range(df, sz_top, legend=color_column is not None)

    with plt.rc_context(MOUND_STYLE):
        figsize, rect = _panel_geometry(len(values), z_range, panel_titles=True)
        fig, axes = plt.subplots(1, len(values), figsize=figsize, sharey=True)
        axes = np.atleast_1d(axes)
        fig.subplots_adjust(**rect)

        for i, (value, panel_ax) in enumerate(zip(values, axes, strict=True)):
            subset = df[df[column] == value]
            group_values = _draw_panel(
                panel_ax, subset, kind, color_column, sz_top, sz_bot, z_range, bw_method, grid
            )
            if i == 0 and len(group_values) > 1:
                _draw_legend_key(panel_ax, color_column, group_values)
            _finish_panel(panel_ax, z_range)
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


def plot_zone_panels(
    panels: Sequence[tuple[str, PitchCollection]],
    title: str,
    *,
    ncols: int | None = None,
    kind: str = "scatter",
    color_by: str | None = "pitch_type",
    grid: bool = False,
    bw_method: float | str | None = None,
    subtitle: str = "",
    source: str = "Source: MLB Statcast (Baseball Savant), via Mound",
    out: str | None = None,
) -> np.ndarray:
    """Draw several pitch collections as chrome-complete panels in a grid.

    ``plot_zone`` gives a single chart a headline, a dek and a source line;
    ``split_by`` gives the same to a figure faceted from one collection's
    own column. Neither covers a comparison the caller assembles by hand --
    a before/after, two non-adjacent windows, a grid of pitch type by
    outing -- and every one of those in this package used to get built with
    a bare ``plt.subplots()`` and a ``fig.suptitle()``, which meant no dek,
    no source line, and no shared frame between panels. This is the same
    chrome and the same data-driven, shared vertical range as ``split_by``,
    for panels the caller names instead of ones a column's values name for
    it.

    Args:
        panels: ``(label, collection)`` pairs, one per panel, drawn in
            order, row-major, into a grid ``ncols`` wide.
        title: figure headline. Required, since panels rarely share the one
            subject an auto-generated headline assumes.
        ncols: panels per row; defaults to one row (``len(panels)`` wide).
        kind, color_by, grid, bw_method: passed through to every panel; see
            ``plot_zone``.
        subtitle: dek shown under the headline; omitted if blank.
        source: source line; pass ``""`` to omit it.
        out: if given, save the figure to this path.

    Returns:
        The grid of axes, shaped ``(nrows, ncols)``.
    """
    if not panels:
        raise ValueError("plot_zone_panels needs at least one panel")

    ncols = ncols or len(panels)
    nrows = math.ceil(len(panels) / ncols)

    frames = [c.to_frame().dropna(subset=["plate_x", "plate_z"]) for _, c in panels]
    combined = pd.concat(frames) if frames else pd.DataFrame()

    color_column = _resolve_column(color_by, combined, param="color_by") if color_by else None
    # Same rule plot_zone applies to a single collection: a color that
    # separates nothing across every panel combined isn't worth spending,
    # decided once against the whole figure so one panel can't end up keyed
    # by color while its neighbor, showing only one of the values, isn't.
    if color_column and combined[color_column].nunique() <= 1:
        color_column = None

    sz_top, sz_bot = _zone_bounds(combined)
    z_range = _z_range(combined, sz_top, legend=color_column is not None)

    with plt.rc_context(MOUND_STYLE):
        figsize, rect = _panel_geometry(ncols, z_range, n_rows=nrows, panel_titles=True)
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, sharey=True, squeeze=False)
        fig.subplots_adjust(**rect)

        legend_drawn = False
        for i, ((label, _collection), frame) in enumerate(zip(panels, frames, strict=True)):
            row, col = divmod(i, ncols)
            panel_ax = axes[row, col]
            group_values = _draw_panel(
                panel_ax, frame, kind, color_column, sz_top, sz_bot, z_range, bw_method, grid
            )
            if not legend_drawn and len(group_values) > 1:
                _draw_legend_key(panel_ax, color_column, group_values)
                legend_drawn = True
            _finish_panel(panel_ax, z_range)
            if col > 0:
                panel_ax.tick_params(labelleft=False)
            panel_ax.set_title(label, loc="left", fontsize=11, fontweight="semibold", color=INK)

        # A grid that doesn't fill its last row leaves the remainder blank
        # rather than drawing an empty, misleadingly axed panel.
        for j in range(len(panels), nrows * ncols):
            row, col = divmod(j, ncols)
            axes[row, col].axis("off")

        _add_chrome(fig, title, subtitle, source)

        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.2)

    return axes


# -- tunnel plots ---------------------------------------------------------

# Where the flight path stops being drawn as one line and starts being drawn
# as two. Marking the commit point is what makes a tunnel legible: without
# it, two curves that separate somewhere don't say whether the separation
# arrived in time to be acted on.
_COMMIT_MARKER_SIZE = 46
_PLATE_MARKER_SIZE = 92

# A tunnel plot has to hold the release point as well as the plate, and a
# release is a foot and a half above where `plot_zone` stops. The wider
# frame costs the strike zone some size, which is the right trade here --
# the zone is context in this chart, not its subject.
TUNNEL_Z_RANGE = (-0.5, 7.0)


def _tunnel_pair(collection: PitchCollection):
    """The two pitches a tunnel plot should draw, and why they were chosen."""
    pitches = [p for p in collection if p.trajectory() is not None]
    if len(pitches) == 2:
        return pitches[0], pitches[1], False
    if len(pitches) < 2:
        raise ValueError(
            "plot_tunnel needs two pitches with trajectory data; "
            f"this collection has {len(pitches)}"
        )

    ranked = collection.tunnels()
    if ranked.empty:
        raise ValueError(
            "plot_tunnel found no comparable pitch pair -- filter to two pitches, "
            "or check that this collection spans an at-bat with more than one pitch type"
        )

    top = ranked.iloc[0]
    by_key = {(p.game_pk, p.at_bat_number, p.pitch_number): p for p in pitches}
    first = by_key[(top["game_pk"], top["at_bat_number"], top["first_pitch"])]
    second = by_key[(top["game_pk"], top["at_bat_number"], top["second_pitch"])]
    return first, second, True


def _tunnel_headline(first, second) -> str:
    who = first.pitcher_name or "Pitch"
    return f"{who}: {first.pitch_type} and {second.pitch_type}"


def _tunnel_subtitle(first, second, commit_sep, plate_sep, commit_distance) -> str:
    parts = []
    if first.batter_name:
        parts.append(f"vs. {first.batter_name}")
    if first.game_date:
        parts.append(_format_date(date.fromisoformat(first.game_date)))
    parts.append(
        f"{commit_sep:.0f}\u2033 apart at {commit_distance:g} ft, "
        f"{plate_sep:.0f}\u2033 at the plate"
    )
    return " \u00b7 ".join(parts)


def plot_tunnel(
    collection: PitchCollection,
    *,
    commit_distance: float | None = None,
    commit_time: float | None = None,
    ax: Axes | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    source: str = "Source: MLB Statcast (Baseball Savant), via Mound",
    out: str | None = None,
) -> Axes:
    """Draw two pitches' flight paths as the hitter sees them.

    Both paths are projected onto the plane the hitter looks down, so two
    pitches that tunnel trace nearly the same line until they don't. An open
    marker on each sits at the commit point -- the moment the swing decision
    has to be made -- and a filled one at the plate, which is the whole
    argument in two dots: how close together they were when he had to choose,
    and how far apart they finished.

    Pass a collection of exactly two pitches to draw those. A larger one is
    ranked with :meth:`~mound.pitches.PitchCollection.tunnels` and its best
    pair is drawn, which makes ``roki.pitches(game=...).plot_tunnel()`` a
    reasonable way to find the outing's best sequence.

    Args:
        collection: two pitches, or a larger collection to rank.
        commit_distance: feet from the plate where the hitter commits;
            defaults to :data:`mound.trajectory.DEFAULT_COMMIT_DISTANCE_FEET`.
        commit_time: seconds before the plate instead of a fixed distance,
            measured against each pitch's own arrival.
        ax: existing axes to draw on; a styled figure is made if omitted.
        title: headline; auto-generated if omitted.
        subtitle: dek; auto-generated if omitted, ``""`` to omit.
        source: source line; ``""`` to omit.
        out: if given, save the figure to this path.
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

    first, second, _ranked = _tunnel_pair(collection)
    traj_first = Trajectory.from_pitch(first)
    traj_second = Trajectory.from_pitch(second)

    commit_sep = separation(
        traj_first, traj_second, distance=commit_distance, time_before_plate=commit_time
    )
    plate_sep = separation(traj_first, traj_second, distance=PLATE_MEASUREMENT_Y_FEET)

    tops = [p.sz_top for p in (first, second) if p.sz_top is not None]
    bots = [p.sz_bot for p in (first, second) if p.sz_bot is not None]
    sz_top = sum(tops) / len(tops) if tops else DEFAULT_SZ_TOP
    sz_bot = sum(bots) / len(bots) if bots else DEFAULT_SZ_BOT

    owns_figure = ax is None
    with plt.rc_context(MOUND_STYLE):
        if owns_figure:
            figsize, rect = _panel_geometry(1, TUNNEL_Z_RANGE)
            fig, ax = plt.subplots(figsize=figsize)
            fig.subplots_adjust(**rect)
        else:
            fig = ax.figure

        _draw_home_plate(ax)
        _draw_strike_zone(ax, sz_top, sz_bot)

        for pitch, traj in ((first, traj_first), (second, traj_second)):
            color = PITCH_TYPE_COLORS.get(pitch.pitch_type or "", DEFAULT_PITCH_COLOR)
            points = traj.path(extension=pitch.release_extension)
            if points:
                ax.plot(
                    [p[0] for p in points],
                    [p[2] for p in points],
                    color=color,
                    linewidth=1.9,
                    alpha=0.9,
                    zorder=4,
                    solid_capstyle="round",
                )

            if commit_time is not None:
                commit_point = traj.time_before_plate(commit_time)
            else:
                commit_point = traj.position_at_distance(commit_distance)
            if commit_point:
                ax.scatter(
                    *commit_point,
                    s=_COMMIT_MARKER_SIZE,
                    facecolors=BACKGROUND,
                    edgecolors=color,
                    linewidths=1.6,
                    zorder=5,
                )

            plate_point = traj.plate_location()
            if plate_point:
                ax.scatter(
                    *plate_point,
                    s=_PLATE_MARKER_SIZE,
                    color=color,
                    zorder=6,
                    edgecolors=BACKGROUND,
                    linewidths=1.2,
                )

        # Low and left: the flight paths sweep the upper middle of the frame
        # on their way down, which is exactly where a top-left key would sit.
        _draw_legend_key(ax, "pitch_type", [first.pitch_type, second.pitch_type], top=0.17)
        _finish_panel(ax, TUNNEL_Z_RANGE)

        headline = title if title is not None else _tunnel_headline(first, second)
        if owns_figure:
            if subtitle is not None:
                dek = subtitle
            elif commit_sep is not None and plate_sep is not None:
                label = commit_distance if commit_time is None else commit_time
                dek = _tunnel_subtitle(first, second, commit_sep, plate_sep, label)
            else:
                dek = ""
            _add_chrome(fig, headline, dek, source)
        else:
            ax.set_title(headline, loc="left", fontsize=12, fontweight="semibold", color=INK)

        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.2)

    return ax
