# Roadmap

Sensible next steps beyond the initial prototype, roughly grouped by theme. None of this is committed or sequenced — treat it as a menu, not a backlog.

## More analysis

- **Called-strike breakdown.** A more granular breakdown of `strike_rate()` into called strikes vs. swinging strikes vs. fouls.
- **Game-to-game comparisons.** Build on `usage_rate()` to add e.g. `compare(collection_a, collection_b)` helpers that diff pitch mix, strike rate and location between two periods (the "pre vs. post All-Star break" pattern from the original example question).
- **Automatic pitch-type normalization.** Statcast's own classification can be inconsistent game-to-game for pitches with unusual movement (see the Roki Sasaki splitter/forkball note in the README). A normalization layer could reconcile a pitcher's pitch types across a season using movement/velocity clustering rather than trusting each game's raw label.

## Reports and workflows

- **Scouting reports.** A one-glance summary of a pitcher's recent form: how he's been getting outs, an arsenal breakdown, and how velocity/spin/whiff rate are trending over his last several starts. Worth deciding whether a batter-side mirror (plate discipline, chase tendencies, performance by pitch type faced) belongs alongside it.
- **An `outing` command.** An end-to-end breakdown of one start — length, pitch mix, arsenal table, zone charts — as a single report, instead of composing `mix`/`arsenal`/`zone` by hand for the same game.

## More visualization

- **Color zone plots by outcome.** `color_by` now covers pitch type and batter handedness, but not what happened: a whiff, a called strike, a ball, a ball in play. Needs a palette that reads as a sequence (harmless to damaging) rather than as unordered categories, and a decision about whether the four Savant `pitch_call` families are the right grouping or too granular for one panel.
- **Zone charts by rate, not count.** `kind="zones"` fills each cell with how many pitches landed there; the more interesting question is usually what happened when they did — whiff rate, chase rate, slugging by zone. Needs a rule for cells with too few pitches to rate honestly, and probably a diverging ramp against the pitcher's own average rather than the sequential one counts use.
- Movement plots (horizontal/vertical break) alongside location plots.
- Release-point consistency plots across a start or season.
- Overlaying multiple periods (e.g. pre/post All-Star break) on a single zone plot for direct comparison.
- **Mound branding on charts.** A logo, wordmark or credit line on `plot_zone()` output, beyond the plain source-line footer it has now, for site and social use.
- **SVG output.** `plot_zone(out="foo.svg")` alongside PNG, for the site and any print use that wants a vector file.
- Continued aesthetic refinement as an open-ended line item — spacing, typography, color choices — as more real-world charts accumulate and reveal what's still off.

## Data and performance

- **Bulk retrieval.** Efficient season- or team-wide retrieval (e.g. every pitch thrown by every Dodgers pitcher in 2025) rather than one pitcher at a time.
- **S3 and other remote-storage targets.** `mound/export.py` already separates serialization from the `Storage` interface; adding `S3Storage` (or similar) should require no changes to the core data model.
- **DataFrame/GeoDataFrame-friendly outputs.** `PitchCollection.to_frame()` already returns a pandas DataFrame; consider a GeoDataFrame variant for spatial analysis of pitch location.
- **Shell-friendly output formats.** Plain-text/TSV output modes for `mound pitches`/`mound mix`/`mound results` that pipe cleanly into `awk`, `jq`, etc.

## More discovery

- **Team and league-wide discovery tools.** `games()` (`mound games`/`mound faced-games`) covers a single player's own appearances; team rosters, schedules, and box-score lookups that aren't scoped to one player already known to Mound are still their own gap.
- **Hitter-side metrics.** `chase_rate()` already works on a `Batter` collection, but plate-discipline framing beyond it (zone rate seen, swing decisions by count) and contact quality would make the batter side more than a mirror of the pitcher's numbers.

## Docs

- **Revamp doc structure where needed.** The README reads more like a chronological feature log than a reference; worth restructuring around how someone actually looks things up, not the order features shipped in.
- **Rethink entry points for first-time users.** What does someone reach for on their very first command or import, before they know any of this exists? Worth designing the Quickstart around that path rather than an exhaustive option list.
- **Docs on the site, not just the README.** `site/content` mirrors the README and CHANGELOG today; publish more of the documentation (this roadmap, worked walkthroughs) directly on moundcli.com instead of only linking back to the repo.
- **More worked examples.** Candidates: Alex Vesia's recent struggles (is his spin rate down, is it a location issue?); a season-overview example naming Roki Sasaki's "best" outing so far; why Chris Sale is still this good.
