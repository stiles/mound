"""Compare four specified Edwin Díaz outings, two in August and two in September.

    python examples/diaz_two_windows.py

Fetches MLB/Savant data, prints per-game and pooled comparisons, and writes
CSV tables, a text report and paired location charts to
examples/output/diaz_two_windows/. Use --out-dir or --cache-dir to override.

These are the two requested pairs, not a claim about his first appearances
following an IL stint. Counts accompany rates because two outings are a
small sample. Results describe pitches and plate appearances, not a full
box score or proof that a mechanical change caused any difference.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from mound import Pitcher
from mound.viz import MOUND_STYLE

GAMES = [
    ("August", "2026-08-14", "Milwaukee Brewers", "home", 823913),
    ("August", "2026-08-17", "Colorado Rockies", "away", 824320),
    ("September", "2026-09-18", "San Francisco Giants", "home", 823898),
    ("September", "2026-09-19", "San Francisco Giants", "home", 823899),
]
ROOT = Path(__file__).resolve().parents[1]


def rate(numerator: int, denominator: int) -> float:
    return 100 * numerator / denominator if denominator else float("nan")


def summarize(frame: pd.DataFrame) -> dict:
    """Count known observations explicitly; missing tracking is never zero."""
    swings = frame.is_swing.astype("boolean")
    whiffs = frame.is_whiff.astype("boolean")
    in_zone = frame.in_zone.astype("boolean")
    swing_mask = swings.eq(True).fillna(False)
    whiff_opportunities = swing_mask & whiffs.notna()
    chase_opportunities = in_zone.eq(False).fillna(False) & swings.notna()
    n_whiffs = int(whiffs[whiff_opportunities].sum())
    n_chases = int(swings[chase_opportunities].sum())
    located = frame.dropna(subset=["plate_x", "plate_z", "sz_bot", "sz_top", "in_zone"])
    located = located[located.sz_top > located.sz_bot]
    relative_height = (located.plate_z - located.sz_bot) / (located.sz_top - located.sz_bot)
    middle = relative_height.gt(1 / 3) & relative_height.le(2 / 3) & located.in_zone.eq(True)
    row = {
        "pitches": len(frame),
        "swings": int(swings.sum()),
        "swing_known": int(swings.notna().sum()),
        "swing_pct": rate(int(swings.sum()), int(swings.notna().sum())),
        "whiffs": n_whiffs,
        "whiff_opportunities": int(whiff_opportunities.sum()),
        "whiff_pct": rate(n_whiffs, int(whiff_opportunities.sum())),
        "chases": n_chases,
        "chase_opportunities": int(chase_opportunities.sum()),
        "chase_pct": rate(n_chases, int(chase_opportunities.sum())),
        "in_zone": int(in_zone.sum()),
        "zone_known": int(in_zone.notna().sum()),
        "zone_pct": rate(int(in_zone.sum()), int(in_zone.notna().sum())),
        "middle_third": int(middle.sum()),
        "located": len(located),
        "middle_third_pct": rate(int(middle.sum()), len(located)),
        "balls_in_play": int(frame.pitch_call.eq("hit_into_play").sum()),
    }
    for field in [
        "velocity",
        "spin_rate",
        "horizontal_break",
        "induced_vertical_break",
        "release_extension",
        "release_pos_x",
        "release_pos_z",
    ]:
        values = pd.to_numeric(frame[field], errors="coerce")
        row[field] = values.mean()
        row[f"{field}_n"] = int(values.notna().sum())
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "examples/output/diaz_two_windows")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "cache")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    diaz = Pitcher(621242)
    pitches = diaz.pitches(game=[game[4] for game in GAMES], cache=args.cache_dir)
    frame = pitches.to_frame()
    for _, expected_date, _, _, game_pk in GAMES:
        dates = set(frame.loc[frame.game_pk == game_pk, "game_date"])
        if dates != {expected_date}:
            raise ValueError(
                f"Game {game_pk}: expected Díaz pitches on {expected_date}, got {dates}"
            )

    metadata = pd.DataFrame(GAMES, columns=["window", "game_date", "opponent", "venue", "game_pk"])
    frame = frame.merge(metadata, on=["game_pk", "game_date"], validate="many_to_one")
    frame["pitch_type"] = frame.pitch_type.fillna("unknown")
    frame = frame.sort_values(["game_date", "at_bat_number", "pitch_number"])
    frame.to_csv(args.out_dir / "pitches.csv", index=False)

    per_game = pd.DataFrame(
        [
            {
                **dict(zip(metadata.columns, game, strict=True)),
                **summarize(frame[frame.game_pk == game[4]]),
            }
            for game in GAMES
        ]
    )
    pooled = pd.DataFrame(
        [
            {"window": window, **summarize(group)}
            for window, group in frame.groupby("window", sort=False)
        ]
    )
    arsenal = pd.DataFrame(
        [
            {
                "window": window,
                "pitch_type": pitch_type,
                "usage_pct": rate(len(group), int(frame.window.eq(window).sum())),
                **summarize(group),
            }
            for (window, pitch_type), group in frame.groupby(["window", "pitch_type"], sort=False)
        ]
    )
    per_game_arsenal = pd.DataFrame(
        [
            {
                "game_date": game_date,
                "game_pk": game_pk,
                "pitch_type": pitch_type,
                **summarize(group),
            }
            for (game_date, game_pk, pitch_type), group in frame.groupby(
                ["game_date", "game_pk", "pitch_type"], sort=False
            )
        ]
    )
    ends = frame[frame.ends_at_bat.astype("boolean").fillna(False)]
    outcomes = pd.crosstab(ends.window, ends.at_bat_result).reindex(
        ["August", "September"], fill_value=0
    )
    handedness = pd.crosstab(frame.window, frame.batter_stand.fillna("unknown"))
    for name, table in [
        ("per_game", per_game),
        ("pooled", pooled),
        ("arsenal", arsenal),
        ("per_game_arsenal", per_game_arsenal),
    ]:
        table.to_csv(args.out_dir / f"{name}.csv", index=False)
    outcomes.to_csv(args.out_dir / "outcomes.csv")
    handedness.to_csv(args.out_dir / "handedness.csv")
    end_columns = [
        "game_date",
        "batter_name",
        "batter_stand",
        "pitch_type",
        "velocity",
        "zone",
        "at_bat_result",
    ]
    ends[end_columns].to_csv(args.out_dir / "plate_appearances.csv", index=False)

    delta_fields = [
        "usage_pct",
        "velocity",
        "spin_rate",
        "horizontal_break",
        "induced_vertical_break",
        "release_extension",
        "whiff_pct",
        "chase_pct",
        "zone_pct",
        "middle_third_pct",
    ]
    delta = (
        arsenal[arsenal.window == "September"].set_index("pitch_type")[delta_fields]
        - arsenal[arsenal.window == "August"].set_index("pitch_type")[delta_fields]
    )
    delta.to_csv(args.out_dir / "september_minus_august.csv")
    display_fields = [
        "pitches",
        "velocity",
        "whiffs",
        "whiff_opportunities",
        "whiff_pct",
        "chases",
        "chase_opportunities",
        "chase_pct",
        "zone_pct",
        "middle_third_pct",
    ]
    sections = [
        ("Requested games", metadata),
        ("Per game", per_game[["game_date", "opponent", *display_fields]]),
        ("Pooled windows (all pitch types)", pooled[["window", *display_fields]]),
        (
            "Pitch mix and shape",
            arsenal[
                [
                    "window",
                    "pitch_type",
                    "pitches",
                    "usage_pct",
                    "velocity",
                    "spin_rate",
                    "horizontal_break",
                    "induced_vertical_break",
                    "release_extension",
                ]
            ],
        ),
        ("Hitter responses and location", arsenal[["window", "pitch_type", *display_fields]]),
        ("September minus August (rates in percentage points)", delta.reset_index()),
        (
            "Per-game pitch shape (check the Colorado outing before pooling movement)",
            per_game_arsenal[
                [
                    "game_date",
                    "pitch_type",
                    "pitches",
                    "velocity",
                    "horizontal_break",
                    "induced_vertical_break",
                ]
            ],
        ),
        ("Plate-appearance outcomes", outcomes.reset_index()),
        ("Batter handedness (pitches faced)", handedness.reset_index()),
        ("Every plate appearance's final pitch", ends[end_columns]),
    ]
    report = "Edwin Díaz: Aug. 14/17 vs. Sept. 18/19, 2026\n\n"
    report += "\n\n".join(
        title + "\n" + table.round(2).to_string(index=False, na_rep="—")
        for title, table in sections
    )
    report += (
        "\n\nWhiff rate = misses / swings with known whiff status. "
        "Chase rate = swings / outside-zone pitches with known swing status.\n"
        "Middle third = in-zone pitches in the middle vertical third of each hitter's zone; "
        "denominator is pitches with valid location and zone bounds.\n"
        "Velocity: mph; spin: rpm; break: inches; release/extension: feet. "
        "CSV columns ending _n show tracking coverage.\n"
        "Two games per window, different opponents, and one August game in Colorado. "
        "Movement is not adjusted for park/altitude. These comparisons do not isolate a cause.\n"
        "Plate-appearance endings are feed-derived, not an official innings/runs/saves line.\n"
    )
    (args.out_dir / "report.txt").write_text(report)
    print(report)

    pitch_types = list(frame.pitch_type.unique())
    with plt.rc_context(MOUND_STYLE):
        fig, axes = plt.subplots(
            len(pitch_types), 2, figsize=(10, 5 * len(pitch_types)), squeeze=False
        )
        for row, pitch_type in enumerate(pitch_types):
            for col, window in enumerate(["August", "September"]):
                ids = [game[4] for game in GAMES if game[0] == window]
                subset = pitches.filter(game=ids, pitch_type=pitch_type)
                subset.plot_zone(
                    ax=axes[row, col],
                    title=(
                        f"{'Aug. 14 & 17' if window == 'August' else 'Sept. 18 & 19'}"
                        f" · {len(subset)} pitches\n{pitch_type}"
                    ),
                    grid=True,
                )
        fig.suptitle("Edwin Díaz: two August outings, two September outings", fontsize=16)
        fig.text(
            0.05,
            0.02,
            "2026 · Catcher's view · Zone reflects each panel's hitters\n"
            "Source: MLB Statcast (Baseball Savant), via Mound",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.06, 1, 0.95), h_pad=2.5)
        fig.savefig(args.out_dir / "locations.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"\nSaved tables, report and chart to {args.out_dir}")


if __name__ == "__main__":
    main()
