# Roadmap

Sensible next steps beyond the initial prototype, roughly grouped by theme. None of this is committed or sequenced — treat it as a menu, not a backlog.

## More analysis

- **Called-strike breakdown.** A more granular breakdown of `strike_rate()` into called strikes vs. swinging strikes vs. fouls.
- **Game-to-game comparisons.** Build on `usage_rate()` to add e.g. `compare(collection_a, collection_b)` helpers that diff pitch mix, strike rate and location between two periods (the "pre vs. post All-Star break" pattern from the original example question).
- **Automatic pitch-type normalization.** Statcast's own classification can be inconsistent game-to-game for pitches with unusual movement (see the Roki Sasaki splitter/forkball note in the README). A normalization layer could reconcile a pitcher's pitch types across a season using movement/velocity clustering rather than trusting each game's raw label.

## More visualization

- **Color zone plots by outcome.** `color_by` now covers pitch type and batter handedness, but not what happened: a whiff, a called strike, a ball, a ball in play. Needs a palette that reads as a sequence (harmless to damaging) rather than as unordered categories, and a decision about whether the four Savant `pitch_call` families are the right grouping or too granular for one panel.
- **Zone charts by rate, not count.** `kind="zones"` fills each cell with how many pitches landed there; the more interesting question is usually what happened when they did — whiff rate, chase rate, slugging by zone. Needs a rule for cells with too few pitches to rate honestly, and probably a diverging ramp against the pitcher's own average rather than the sequential one counts use.
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
- **Hitter-side metrics.** `chase_rate()` already works on a `Batter` collection, but plate-discipline framing beyond it (zone rate seen, swing decisions by count) and contact quality would make the batter side more than a mirror of the pitcher's numbers.
