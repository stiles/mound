"""Is Ohtani chasing spin away? A worked example from the hitter's side.

Companion script to docs/examples/ohtani-spin-chase.md. Walks the same seven
steps as the write-up: pull 40 games from the hitter's side, count plate
appearances, find the pitch each strikeout ended on, settle which side of
the plate is "away", split his chase rate by pitch family and side, compare
the recent 20 games against the 20 before them, and list the video IDs for
the strikeouts that came on spin off the plate.

Reading from a hitter's side is one Savant game feed per game he played, so
caching matters more here than in the pitcher-side examples.

Requires network access (hits the live MLB Stats API and Baseball Savant).
Run with:

    python examples/shohei_spin_chase.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from mound import Batter, PitchCollection, Pitcher
from mound.viz import MOUND_STYLE

OUTPUT_DIR = Path(__file__).parent / "output"

GAMES = 20
SPLIT_DATE = "2026-07-25"  # the recent 20 games start here
# Everything that isn't a fastball, sinker or cutter.
SPIN = ["slider", "sweeper", "slurve", "curveball", "knuckle curve", "changeup", "splitter"]
# The quadrants off the plate on a left-handed hitter's outer half, which
# step 4 establishes from hit-by-pitch locations.
AWAY_OFF_PLATE = [11, 13]


def strikeouts(collection) -> pd.DataFrame:
    """The pitch each strikeout ended on, one row per strikeout.

    Savant repeats an at-bat's result on every pitch of the at-bat, so this
    leans on ``ends_at_bat`` to pick out the pitch that finished it.
    """
    ends = collection.filter(ends_at_bat=True).to_frame()
    return ends[ends.at_bat_result.str.contains("Strikeout", na=False)]


def summarize(window) -> dict[str, float]:
    ends = window.filter(ends_at_bat=True).to_frame()
    struck_out = strikeouts(window)
    chased = window.filter(pitch_type=SPIN, zone=AWAY_OFF_PLATE).to_frame()
    return {
        "plate appearances": len(ends),
        "strikeouts": len(struck_out),
        "strikeout rate": round(100 * len(struck_out) / len(ends), 1),
        "spin away, off the plate": len(chased),
        "swung at": int(chased.is_swing.sum()),
        "chase rate there": round(100 * chased.is_swing.mean(), 1),
        "strikeouts ending there": int(struck_out.zone.isin(AWAY_OFF_PLATE).sum()),
    }


def chases(window, batter) -> PitchCollection:
    """The swings at spin away and off the plate."""
    return PitchCollection(
        [p for p in window.filter(pitch_type=SPIN, zone=AWAY_OFF_PLATE) if p.is_swing],
        batter=batter,
    )


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Start from the hitter. Twice the window, so the recent 20 games have
    #    the 20 before them to be compared against.
    ohtani = Batter("Shohei Ohtani")
    print(f"Found {ohtani.name} (MLB ID {ohtani.id})")
    faced = ohtani.pitches(last=GAMES * 2, cache=True)
    if faced.empty:
        print("No pitches found.")
        return

    dates = faced.to_frame().game_date
    print(f"{faced}: {len(faced.games)} games, {dates.min()} to {dates.max()}\n")

    recent = faced.filter(since=SPLIT_DATE)
    prior = faced.filter(until="2026-07-24")

    # 2. How the last 20 games ended, one row per plate appearance.
    ends = recent.filter(ends_at_bat=True)
    print(f"Plate appearances, last {GAMES} games ({len(ends)} total):")
    print(ends.to_frame().at_bat_result.value_counts().to_string(), "\n")

    # 3. The pitch each strikeout ended on.
    struck_out = strikeouts(recent)
    print(f"How the {len(struck_out)} strikeouts ended:")
    print(struck_out.pitch_call.value_counts().to_string(), "\n")
    print("Every strikeout pitch:")
    print(
        struck_out[
            ["game_date", "pitcher_name", "pitch_type", "velocity", "plate_x", "zone", "pitch_call"]
        ]
        .sort_values(["pitch_type", "plate_x"])
        .to_string(index=False),
        "\n",
    )
    print("Strikeouts by zone:")
    print(struck_out.zone.value_counts().sort_index().to_string(), "\n")

    # 4. Which side of the plate is away? Nothing in the feed says, but a
    #    pitch that hits a batter is on that batter's side of it -- and
    #    Ohtani pitches, so his own hit batters settle the sign.
    thrown = Pitcher("Shohei Ohtani").pitches(season=2026, cache=True)
    hit_batters = thrown.to_frame().query("pitch_call == 'hit_by_pitch'")
    print("Batters Ohtani has hit, by side and location:")
    print(
        hit_batters[["game_date", "batter_name", "batter_stand", "plate_x"]]
        .round(2)
        .to_string(index=False),
        "\n",
    )

    # 5. Chase rate, split by pitch family and side of the plate.
    off_plate = recent.filter(in_zone=False).to_frame()
    off_plate["family"] = off_plate.pitch_type.isin(SPIN).map({True: "spin", False: "fastball"})
    off_plate["side"] = off_plate.plate_x.map(lambda x: "away" if x < 0 else "in")
    splits = off_plate.groupby(["family", "side"]).agg(
        pitches=("is_swing", "size"), swings=("is_swing", "sum")
    )
    splits["chase_rate"] = (100 * splits.swings / splits.pitches).round(1)
    print("Swings at pitches out of the zone:")
    print(splits.to_string(), "\n")
    print("Chase rate by pitch type:")
    print(recent.chase_rate(by_pitch_type=True).round(1).to_string(), "\n")

    spin_zones = OUTPUT_DIR / "ohtani_spin_zones.png"
    recent.filter(pitch_type=SPIN).plot_zone(kind="zones", out=str(spin_zones))
    print(f"Saved the spin he faced, counted into zones, to {spin_zones}\n")

    # 6. Is any of it new?
    print(f"The last {GAMES} games against the {GAMES} before them:")
    windows = {
        f"through {prior.to_frame().game_date.max()}": summarize(prior),
        f"since {SPLIT_DATE}": summarize(recent),
    }
    print(pd.DataFrame(windows).to_string(), "\n")

    panels = OUTPUT_DIR / "ohtani_chase_panels.png"
    with plt.rc_context(MOUND_STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(9, 5.6))
        for ax, (label, window) in zip(
            axes, (("Jun 28\u2013Jul 24", prior), ("Jul 25\u2013Aug 16", recent)), strict=True
        ):
            chased = chases(window, ohtani.player)
            chased.plot_zone(ax=ax, color_by=None, title=f"{label}: {len(chased)} chases")
        fig.savefig(panels, dpi=150, bbox_inches="tight")
    print(f"Saved the chase panels to {panels}")

    plot = OUTPUT_DIR / "ohtani_strikeout_pitches.png"
    PitchCollection(
        [p for p in ends if "Strikeout" in (p.at_bat_result or "")], batter=ohtani.player
    ).plot_zone(
        grid=True,
        title="The pitches Ohtani struck out on",
        subtitle=f"{len(struck_out)} strikeouts \u00b7 last {GAMES} games"
        " \u00b7 catcher's view, so away is left",
        out=str(plot),
    )
    print(f"Saved the strikeout pitches to {plot}\n")

    # 7. The strikeouts that came on spin off the plate, and their clips.
    chase_strikeouts = struck_out[
        struck_out.zone.isin(AWAY_OFF_PLATE) & struck_out.pitch_type.isin(SPIN)
    ]
    print("Strikeouts on spin away and off the plate:")
    print(
        chase_strikeouts[
            ["game_date", "pitcher_name", "pitch_type", "velocity", "pitch_id"]
        ].to_string(index=False),
        "\n",
    )
    print("Download any of them with:")
    for pitch_id in chase_strikeouts.pitch_id:
        print(f"    mound video-id {pitch_id}")


if __name__ == "__main__":
    main()
