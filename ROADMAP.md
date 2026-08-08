# Roadmap

Sensible next steps beyond the initial prototype, roughly grouped by theme. None of this is committed or sequenced — treat it as a menu, not a backlog.

## More analysis

- **Batter filtering and matchups.** Filter a pitcher's pitches by opposing batter, and support the inverse (a batter's pitches faced from a given pitcher) for pitcher-vs-batter matchup views.
- **Velocity, spin, movement and release-point analysis.** Mound already captures `velocity`, `sz_top`/`sz_bot` and raw Statcast fields aren't currently normalized (spin rate, horizontal/vertical break, extension, release point). Surface these as first-class `Pitch` fields and add summary functions (e.g. average spin by pitch type).
- **Swing, whiff and chase rates.** Savant's raw pitch data includes swing/contact info; add derived rate metrics beyond strike rate (whiff rate, chase rate on pitches outside the zone, contact rate).
- **Called-strike and whiff rate.** A more granular breakdown of `strike_rate()` into called strikes vs. swinging strikes vs. fouls.
- **Game-to-game comparisons.** Build on `usage_rate()` to add e.g. `compare(collection_a, collection_b)` helpers that diff pitch mix, strike rate and location between two periods (the "pre vs. post All-Star break" pattern from the original example question).
- **Automatic pitch-type normalization.** Statcast's own classification can be inconsistent game-to-game for pitches with unusual movement (see the Roki Sasaki splitter/forkball note in the README). A normalization layer could reconcile a pitcher's pitch types across a season using movement/velocity clustering rather than trusting each game's raw label.

## More visualization

- Movement plots (horizontal/vertical break) alongside location plots.
- Release-point consistency plots across a start or season.
- Overlaying multiple periods (e.g. pre/post All-Star break) on a single zone plot for direct comparison.

## Data and performance

- **Caching.** Every call currently re-fetches from the MLB Stats API and Baseball Savant. A local cache (SQLite, on-disk JSON, or similar) keyed by `game_pk` would make repeated queries much faster and reduce load on both APIs.
- **Bulk retrieval.** Efficient season- or team-wide retrieval (e.g. every pitch thrown by every Dodgers pitcher in 2025) rather than one pitcher at a time.
- **S3 and other remote-storage targets.** `mound/export.py` already separates serialization from the `Storage` interface; adding `S3Storage` (or similar) should require no changes to the core data model.
- **DataFrame/GeoDataFrame-friendly outputs.** `PitchCollection.to_frame()` already returns a pandas DataFrame; consider a GeoDataFrame variant for spatial analysis of pitch location.
- **Shell-friendly output formats.** Plain-text/TSV output modes for `mound pitches`/`mound mix`/`mound results` that pipe cleanly into `awk`, `jq`, etc.

## More discovery

- **Additional player and game discovery tools.** Team rosters, schedules, and box-score lookups as their own CLI commands/Python functions, rather than only being usable indirectly through `Pitcher`.
- Batter-side equivalents of `Pitcher`/`PitchCollection` for hitters.
