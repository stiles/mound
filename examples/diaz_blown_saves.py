"""Did Edwin Díaz miss "right in the middle"? A worked example.

Companion script to docs/examples/diaz-blown-saves.md. Walks the same seven
steps as the write-up: find the pitcher, list his recent appearances, pull
every pitch, break down the mix by game, compare the arsenal's swing/whiff/
chase rates, test a quote against pitch locations, and pull the video.

Requires network access (hits the live MLB Stats API and Baseball Savant).
Run with:

    python examples/diaz_blown_saves.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from mound import Pitcher

OUTPUT_DIR = Path(__file__).parent / "output"
BLOWN_SAVE_GAME = 823915  # Aug 13, 2026 vs. Milwaukee
PLATE_HALF_FT = 17 / 2 / 12  # home plate is 17 inches wide


def height_bands(frame: pd.DataFrame) -> pd.DataFrame:
    """Label each pitch by where it crossed the zone, vertically.

    Mound reports the batter-specific zone top and bottom for every pitch, so
    "the middle" can be defined per batter rather than as one fixed height:
    the middle third of that hitter's zone, with anything Statcast's geometry
    puts outside the zone set aside as its own bucket.
    """
    f = frame.dropna(subset=["plate_x", "plate_z"]).copy()
    f["height_pct"] = (f["plate_z"] - f["sz_bot"]) / (f["sz_top"] - f["sz_bot"]) * 100
    f["band"] = pd.cut(
        f["height_pct"],
        [-float("inf"), 100 / 3, 200 / 3, float("inf")],
        labels=["low", "middle", "high"],
    ).astype(str)
    f.loc[~f["in_zone"].astype(bool), "band"] = "out of zone"
    # Middle third vertically *and* horizontally -- true middle-middle.
    f["middle_middle"] = (f["plate_x"].abs() <= PLATE_HALF_FT / 3) & (f["band"] == "middle")
    return f


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Find the pitcher.
    diaz = Pitcher("Edwin Díaz")
    print(f"Found {diaz.name} (MLB ID {diaz.id})\n")

    # 2. Pull his last four appearances. Caching keeps repeat runs cheap.
    last4 = diaz.pitches(last=4, cache=True)
    frame = last4.to_frame()
    print(f"{len(last4)} pitches across {len(last4.games)} games: {last4.games}")
    print(frame.groupby(["game_date", "game_pk"]).size().to_string(), "\n")

    # 3. Pitch mix, overall and game by game.
    print("Pitch mix, last four appearances:")
    print(last4.pitch_mix().to_string(), "\n")
    print("Pitch mix by game:")
    print(last4.usage_rate(by="game_date").round(1).to_string(), "\n")

    # 4. The arsenal: how hitters responded to each pitch.
    print("Arsenal, last four appearances:")
    arsenal = last4.pitch_metrics().round(1)
    arsenal["swing_rate"] = last4.swing_rate(by_pitch_type=True).round(1)
    arsenal["whiff_rate"] = last4.whiff_rate(by_pitch_type=True).round(1)
    arsenal["chase_rate"] = last4.chase_rate(by_pitch_type=True).round(1)
    print(arsenal.to_string(), "\n")

    # 5. Test the quote: were the fastballs really in the middle?
    season = diaz.pitches(season=2026, cache=True)
    season_ff = height_bands(season.to_frame().query("pitch_type == 'four-seam fastball'"))
    blown_save_ff = season_ff[season_ff["game_date"] == "2026-08-13"]

    print("Four-seam location, Aug 13 vs. the season:")
    comparison = pd.DataFrame(
        {
            "Aug 13": blown_save_ff["band"].value_counts(normalize=True).mul(100),
            "2026 season": season_ff["band"].value_counts(normalize=True).mul(100),
        }
    ).round(1)
    print(comparison.to_string(), "\n")

    # 6. Does a middle-third fastball actually cost him? Split the season's
    #    four-seamers by band and look at what hitters did with each.
    print("What hitters did with the four-seamer, by band (2026):")
    grouped = season_ff.groupby("band")
    outcomes = pd.DataFrame(
        {
            "pitches": grouped.size(),
            "swing_rate": 100 * grouped["is_swing"].mean(),
            "whiffs": grouped["is_whiff"].sum(),
            "balls_in_play": grouped["pitch_call"].apply(lambda s: (s == "hit_into_play").sum()),
        }
    ).round(1)
    print(outcomes.to_string(), "\n")

    # 7. The pitches that actually got hit, and the video for them.
    contact = height_bands(frame)
    contact = contact[contact["pitch_call"] == "hit_into_play"]
    print("Balls in play, last four appearances:")
    print(
        contact[
            ["game_date", "batter_name", "pitch_type", "velocity", "plate_x",
             "height_pct", "band", "at_bat_result"]
        ].round(2).to_string(index=False),
        "\n",
    )

    blown_save = last4.filter(game=BLOWN_SAVE_GAME)
    zone_path = OUTPUT_DIR / "diaz_ff_aug13_zone.png"
    blown_save.filter(pitch_type="fastball").plot_zone(out=str(zone_path))
    print(f"Saved location plot to {zone_path}")

    clips = blown_save.filter(at_bat_number=68, pitch_number=5).download_videos(
        out_dir=OUTPUT_DIR / "clips"
    )
    print(f"Saved {len(clips)} clip(s) to {OUTPUT_DIR / 'clips'}")

    csv_path = OUTPUT_DIR / "diaz_last4_pitches.csv"
    last4.to_csv(str(csv_path))
    print(f"Saved {len(last4)} pitches to {csv_path}")


if __name__ == "__main__":
    main()
