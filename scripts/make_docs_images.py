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

from mound import Batter, PitchCollection, Pitcher
from mound.viz import plot_zone_panels

IMAGES = Path(__file__).resolve().parent.parent / "docs" / "images"
CACHE = Path(__file__).resolve().parent.parent / "cache"

# The four starts behind the README's plots, and the Aug. 13 blown save the
# Díaz walkthrough is built around.
ROKI_WINDOW = {"since": "2026-07-17", "until": "2026-08-07"}
DIAZ_SEASON = {"since": "2026-03-01", "until": "2026-08-13"}
BLOWN_SAVE_GAME = 823915
# Aug. 16, 2026: five pitch types in one start, which is what the pitch-type
# palette needs to show. Every other figure here is one pitch type, and a
# single type draws in the house color instead.
SKUBAL_START = 823912
# Sasaki's July 24 start, whose best tunnel is a forkball and a four-seamer
# to Marcus Semien: three inches apart where he had to commit, seventeen by
# the time they got there.
TUNNEL_GAME = 823601
TUNNEL_AT_BAT = 15
TUNNEL_PITCHES = [2, 3]
# The 40 games behind the Ohtani walkthrough, split into the recent 20 and
# the 20 before them.
OHTANI_WINDOW = {"since": "2026-06-28", "until": "2026-08-16"}
OHTANI_SPLIT = "2026-07-25"
# Everything that isn't a fastball, sinker or cutter, which is the grouping
# the walkthrough's chase splits use.
SPIN = ["slider", "sweeper", "slurve", "curveball", "knuckle curve", "changeup", "splitter"]


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    cache = str(CACHE)

    roki = Pitcher("Roki Sasaki")
    splitters = roki.pitches(**ROKI_WINDOW, pitch_type="splitter", cache=cache)
    print(f"Roki: {len(splitters)} splitters")

    splitters.plot_zone(out=str(IMAGES / "roki_splitter_zone.png"))
    splitters.plot_zone(split_by="stand", out=str(IMAGES / "roki_splitter_zone_by_stand.png"))
    splitters.plot_zone(color_by="stand", out=str(IMAGES / "roki_splitter_zone_color_by_stand.png"))
    splitters.plot_zone(grid=True, out=str(IMAGES / "roki_splitter_zone_grid.png"))

    tunnel_start = roki.pitches(game=TUNNEL_GAME, cache=cache)
    tunnel_pair = tunnel_start.filter(at_bat_number=TUNNEL_AT_BAT).filter(
        pitch_number=TUNNEL_PITCHES
    )
    print(f"Roki tunnel: {len(tunnel_pair)} pitches to {tunnel_pair.pitches[0].batter_name}")
    tunnel_pair.plot_tunnel(out=str(IMAGES / "roki_semien_tunnel.png"))

    skubal = Pitcher("Tarik Skubal").pitches(game=SKUBAL_START, cache=cache)
    print(f"Skubal: {len(skubal)} pitches, {skubal.to_frame()['pitch_type'].nunique()} types")
    skubal.plot_zone(out=str(IMAGES / "skubal_arsenal_zone.png"))

    diaz = Pitcher("Edwin Díaz")
    season_ff = diaz.pitches(**DIAZ_SEASON, pitch_type="fastball", cache=cache)
    print(f"Díaz: {len(season_ff)} fastballs through Aug 13")

    season_ff.plot_zone(kind="heatmap", out=str(IMAGES / "diaz_ff_season_heatmap.png"))
    season_ff.plot_zone(kind="zones", out=str(IMAGES / "diaz_ff_season_zones.png"))
    season_ff.filter(game=BLOWN_SAVE_GAME).plot_zone(out=str(IMAGES / "diaz_ff_aug13_zone.png"))

    # The two-panel figure from the walkthrough's "Going further" section.
    post = season_ff.filter(since="2026-07-29")
    before = post.filter(until="2026-08-10")
    aug13 = post.filter(since="2026-08-13")
    plot_zone_panels(
        [
            (f"Jul 29\u2013Aug 10: {len(before)} fastballs", before),
            (f"Aug 13: {len(aug13)} fastballs", aug13),
        ],
        "Where D\u00edaz's fastball went, before and during the blown save",
        color_by=None,
        out=str(IMAGES / "diaz_ff_panels.png"),
    )
    print(f"Panels: {len(before)} before, {len(aug13)} on Aug 13")

    ohtani = Batter("Shohei Ohtani")
    faced = ohtani.pitches(**OHTANI_WINDOW, cache=cache)
    prior = faced.filter(until="2026-07-24")
    recent = faced.filter(since=OHTANI_SPLIT)
    print(f"Ohtani: {len(faced)} pitches faced, {len(prior)} then {len(recent)}")

    strikeouts = PitchCollection(
        [p for p in recent.filter(ends_at_bat=True) if "Strikeout" in (p.at_bat_result or "")],
        batter=ohtani.player,
    )
    strikeouts.plot_zone(
        grid=True,
        title="The pitches Ohtani struck out on",
        subtitle=f"{len(strikeouts)} strikeouts \u00b7 Jul 25\u2013Aug 16, 2026"
        " \u00b7 catcher's view, so away is left",
        out=str(IMAGES / "ohtani_strikeout_pitches.png"),
    )
    recent.filter(pitch_type=SPIN).plot_zone(
        kind="zones", out=str(IMAGES / "ohtani_spin_zones.png")
    )

    # Swings at spin away and off the plate, this stretch against the one before.
    windows = (("Jun 28\u2013Jul 24", prior), ("Jul 25\u2013Aug 16", recent))
    chase_panels = []
    for label, window in windows:
        chased = PitchCollection(
            [p for p in window.filter(zone=[11, 13], pitch_type=SPIN) if p.is_swing],
            batter=ohtani.player,
        )
        chase_panels.append((f"{label}: {len(chased)} chases", chased))
        print(f"Ohtani chases, {label}: {len(chased)}")
    plot_zone_panels(
        chase_panels,
        "Ohtani's swings at spin away and off the plate",
        color_by=None,
        out=str(IMAGES / "ohtani_chase_panels.png"),
    )


if __name__ == "__main__":
    main()
