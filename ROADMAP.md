# Roadmap

Sensible next steps beyond the initial prototype, roughly grouped by theme. None of this is committed or sequenced — treat it as a menu, not a backlog.

## More analysis

- **Called-strike breakdown.** A more granular breakdown of `strike_rate()` into called strikes vs. swinging strikes vs. fouls.
- **Game-to-game comparisons.** Build on `usage_rate()` to add e.g. `compare(collection_a, collection_b)` helpers that diff pitch mix, strike rate and location between two periods (the "pre vs. post All-Star break" pattern from the original example question).
- **Automatic pitch-type normalization.** Statcast's own classification can be inconsistent game-to-game for pitches with unusual movement (see the Roki Sasaki splitter/forkball note in the README). A normalization layer could reconcile a pitcher's pitch types across a season using movement/velocity clustering rather than trusting each game's raw label.

## More visualization

- **Color zone plots by pitch type or batter handedness.** `plot_zone()` already takes a `color_by` column internally, but the CLI has no `--color-by` flag to reach it, and `_color_for()` only recognizes pitch-type names -- pass `color_by="stand"` today and every point renders in the same default gray. Add a `mound zone --color-by {pitch_type,stand,none}` option (alongside the existing `--split-by`) plus a stand-aware color lookup, so lefties/righties can render as two distinct colors within one panel, as a lighter-weight alternative to `--split-by stand`'s separate side-by-side panels. Color choices to settle on: reuse two of the six categorical colors already backing `PITCH_TYPE_COLORS` (e.g. blue/orange) so pitch-type and stand coloring read as one consistent house palette, or pull a dedicated pair from a ColorBrewer categorical scheme (e.g. `Set2`/`Paired`) if stand should read as its own visually distinct family instead.
- Movement plots (horizontal/vertical break) alongside location plots.
- Release-point consistency plots across a start or season.
- Overlaying multiple periods (e.g. pre/post All-Star break) on a single zone plot for direct comparison.

## Data and performance

- **Bulk retrieval.** Efficient season- or team-wide retrieval (e.g. every pitch thrown by every Dodgers pitcher in 2025) rather than one pitcher at a time.
- **S3 and other remote-storage targets.** `mound/export.py` already separates serialization from the `Storage` interface; adding `S3Storage` (or similar) should require no changes to the core data model.
- **DataFrame/GeoDataFrame-friendly outputs.** `PitchCollection.to_frame()` already returns a pandas DataFrame; consider a GeoDataFrame variant for spatial analysis of pitch location.
- **Shell-friendly output formats.** Plain-text/TSV output modes for `mound pitches`/`mound mix`/`mound results` that pipe cleanly into `awk`, `jq`, etc.

## More discovery

- **Additional player and game discovery tools.** Team rosters, schedules, and box-score lookups as their own CLI commands/Python functions, rather than only being usable indirectly through `Pitcher`.
- **A CLI surface for the batter side.** `Batter` covers pitches faced in Python, but the CLI only reaches matchups from the pitcher's side (`--batter`). A `mound faced "Geraldo Perdomo" --last 5` (or a `mound matchup PITCHER BATTER` that prints mix, results and whiff/chase in one table) would close the gap. Worth settling first: whether a hitter's every-pitch-faced query is worth the fetch cost, since it means one Savant response per game played rather than per start.
- **Hitter-side metrics.** `chase_rate()` and friends already work on a `Batter` collection, but plate-discipline framing (zone rate seen, swing decisions by count) and contact quality would make the batter side more than a mirror of the pitcher's numbers.
