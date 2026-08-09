"""Kernel-density heat maps of Roki Sasaki's most recent start, by pitch type.

A smaller, more focused companion to roki_sasaki_end_to_end.py: rather than
a multi-start splitter deep-dive, this pulls just his latest outing and
saves one `kind="kde"` heat map per pitch type he threw, so location
tendencies are easy to compare pitch-to-pitch (fastball up, slider down and
away, etc.) without cluttering a single scatter plot.

Requires the optional `scipy` dependency for KDE plots:

    pip install "mound[viz]"

Requires network access (hits the live MLB Stats API and Baseball Savant).
Run with:

    python examples/roki_last_game_heatmaps.py
"""

from __future__ import annotations

import re
from pathlib import Path

from mound import Pitcher

OUTPUT_DIR = Path(__file__).parent / "output"


def _slug(pitch_type: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", pitch_type.lower()).strip("_")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    roki = Pitcher("Roki Sasaki")
    print(f"Found {roki.name} (MLB ID {roki.id})\n")

    last_game = roki.pitches(last=1)
    if last_game.empty:
        print("No recent pitches found.")
        return

    game_date = last_game.pitches[0].game_date
    pitch_types = last_game.pitch_mix()
    print(f"Most recent start: {game_date} ({len(last_game)} pitches)")
    print(pitch_types.to_string(), "\n")

    for pitch_type in pitch_types.index:
        subset = last_game.filter(pitch_type=pitch_type)
        out_path = OUTPUT_DIR / f"roki_last_game_{_slug(pitch_type)}_kde.png"
        try:
            subset.plot_zone(kind="kde", out=str(out_path))
        except ImportError as exc:
            print(f"Skipping {pitch_type}: {exc}")
            continue
        print(f"Saved {len(subset)}-pitch {pitch_type} heat map to {out_path}")


if __name__ == "__main__":
    main()
