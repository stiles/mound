"""Regenerate every plot committed to docs/images/.

Each figure is pinned to the window it was first made from, rather than to a
relative one like ``last=4``, so re-running this after a styling change
redraws the same pitches the surrounding prose describes instead of
quietly sliding forward to last night's start.

    python scripts/make_docs_images.py

Requires network access on first run; game feeds are cached under ./cache,
so later runs only fetch games that have since been played.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from mound import Pitcher
from mound.viz import MOUND_STYLE

IMAGES = Path(__file__).resolve().parent.parent / "docs" / "images"
CACHE = Path(__file__).resolve().parent.parent / "cache"

# The four starts behind the README's plots, and the Aug. 13 blown save the
# Díaz walkthrough is built around.
ROKI_WINDOW = {"since": "2026-07-17", "until": "2026-08-07"}
DIAZ_SEASON = {"since": "2026-03-01", "until": "2026-08-13"}
BLOWN_SAVE_GAME = 823915


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    cache = str(CACHE)

    roki = Pitcher("Roki Sasaki")
    splitters = roki.pitches(**ROKI_WINDOW, pitch_type="splitter", cache=cache)
    print(f"Roki: {len(splitters)} splitters")

    splitters.plot_zone(out=str(IMAGES / "roki_splitter_zone.png"))
    splitters.plot_zone(
        split_by="stand", out=str(IMAGES / "roki_splitter_zone_by_stand.png")
    )
    splitters.plot_zone(
        color_by="stand", out=str(IMAGES / "roki_splitter_zone_color_by_stand.png")
    )
    splitters.plot_zone(grid=True, out=str(IMAGES / "roki_splitter_zone_grid.png"))

    diaz = Pitcher("Edwin Díaz")
    season_ff = diaz.pitches(**DIAZ_SEASON, pitch_type="fastball", cache=cache)
    print(f"Díaz: {len(season_ff)} fastballs through Aug 13")

    season_ff.plot_zone(kind="heatmap", out=str(IMAGES / "diaz_ff_season_heatmap.png"))
    season_ff.plot_zone(kind="zones", out=str(IMAGES / "diaz_ff_season_zones.png"))
    season_ff.filter(game=BLOWN_SAVE_GAME).plot_zone(
        out=str(IMAGES / "diaz_ff_aug13_zone.png")
    )

    # The two-panel figure from the walkthrough's "Going further" section.
    post = season_ff.filter(since="2026-07-29")
    before = post.filter(until="2026-08-10")
    aug13 = post.filter(since="2026-08-13")
    with plt.rc_context(MOUND_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(9, 5.6))
        before.plot_zone(ax=axes[0], title=f"Jul 29\u2013Aug 10: {len(before)} fastballs")
        aug13.plot_zone(ax=axes[1], title=f"Aug 13: {len(aug13)} fastballs")
        fig.suptitle(
            "Where D\u00edaz's fastball went, before and during the blown save",
            fontsize=14,
            fontweight="semibold",
            x=0.02,
            ha="left",
        )
        fig.savefig(IMAGES / "diaz_ff_panels.png", dpi=150, bbox_inches="tight")
    print(f"Panels: {len(before)} before, {len(aug13)} on Aug 13")


if __name__ == "__main__":
    main()
