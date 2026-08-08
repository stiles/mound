"""End-to-end Mound walkthrough, using Roki Sasaki's splitter as the example.

Answers the "definition of done" from the project brief without needing to
know an MLB player ID or API endpoint:

    1. Find Roki Sasaki.
    2. Retrieve pitches from his recent starts.
    3. Isolate his splitter.
    4. Calculate how frequently he threw it.
    5. Calculate its strike rate.
    6. Visualize where he located it.
    7. Save the underlying pitch data locally.

Requires network access (hits the live MLB Stats API and Baseball Savant).
Run with:

    python examples/roki_sasaki_end_to_end.py
"""

from __future__ import annotations

from pathlib import Path

from mound import Pitcher

OUTPUT_DIR = Path(__file__).parent / "output"
LAST_N_STARTS = 4


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Find Roki Sasaki -- no MLB player ID required.
    roki = Pitcher("Roki Sasaki")
    print(f"Found {roki.name} (MLB ID {roki.id})\n")

    # 2. Retrieve pitches from his recent starts.
    recent = roki.pitches(last=LAST_N_STARTS)
    print(f"Retrieved {len(recent)} pitches across his last {LAST_N_STARTS} starts "
          f"({len(recent.games)} games).\n")

    # 3. Isolate his splitter.
    #    Statcast sometimes classifies this pitch as a forkball (FO) instead
    #    of a splitter (FS) -- see the README for details -- so pull both.
    splitters = recent.filter(pitch_type="splitter")
    forkballs = recent.filter(pitch_type="forkball")
    if len(forkballs) > len(splitters):
        print("(Statcast classified this pitch mostly as 'forkball' in these starts.)")
        splitters = forkballs

    # 4. Calculate how frequently he threw it.
    mix = recent.pitch_mix()
    print("Pitch mix over last", LAST_N_STARTS, "starts:")
    print(mix.to_string(), "\n")

    # 5. Calculate its strike rate.
    print(f"Splitter/forkball strike rate: {splitters.strike_rate():.1f}% "
          f"({len(splitters)} pitches)\n")

    # 6. Visualize where he located it.
    zone_path = OUTPUT_DIR / "roki_splitter_zone.png"
    splitters.plot_zone(out=str(zone_path))
    print(f"Saved location plot to {zone_path}")

    # 7. Save the underlying pitch data locally.
    csv_path = OUTPUT_DIR / "roki_last4_pitches.csv"
    recent.to_csv(str(csv_path))
    print(f"Saved {len(recent)} pitches to {csv_path}")


if __name__ == "__main__":
    main()
