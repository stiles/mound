## Changelog

All notable changes to this project will be documented in this file.

Format based on Keep a Changelog.

## [0.9.0] - 2026-08-16

### Added

- `ends_at_bat` on every pitch, marking the one each at-bat ended on. Savant repeats `at_bat_result` and `description` on all of an at-bat's pitches, so neither says which pitch produced them and a five-pitch strikeout reads as five strikeouts. Nothing in the feed answers this — `result_code` is pitch-level, and a walk's fourth ball looks like its first three — so it's derived from the highest pitch number in each at-bat, checked against 10,876 at-bats of cached feeds where pitch numbers run 1..n with no earlier pitch ending anything. Exports gain a column.
- `mound pitches --ends-at-bat` and `filter(ends_at_bat=True)`, one row per plate appearance. The flag is computed when the feed is parsed rather than from whatever a filter left behind, so `--pitch changeup --ends-at-bat` returns the changeups that ended at-bats, not each at-bat's last changeup. Two edges: an at-bat still being pitched marks nothing, since a pitcher mid-count hasn't ended anything, and an at-bat ended by a throw rather than a pitch (a runner caught stealing for the third out, about 1 in 500) still marks its last pitch, which is where the record ends even if that pitch didn't decide it.

- `zone` on every pitch: Statcast's numbered zones as Baseball Savant draws them, 1-9 across the strike zone and 11-14 for the quadrants outside it, with no 10. Derived from the pitch's own coordinates rather than read from the feed's `zone` field, the same way `in_zone` already was, so the two can't drift apart. Matching Savant exactly takes three details: the grid is cut from the zone grown by one ball radius (a pitch an inch above `sz_top` is zone 1, not 11), the thirds come from that grown rectangle rather than the strike zone proper, and membership still uses the sphere overlap, whose corners are round, so a pitch clipping a corner diagonally reads as outside. Agrees with Savant's own `zone` on all 42,538 pitches in a local cache of 146 games.
- `mound pitches --zone 5` / `--zone 11,12,13,14`, and `filter(zone=...)` taking a number or a list.

- `plot_zone(kind="zones")` (`mound zone --kind zones`), a heatmap binned into Statcast's numbered zones instead of a 25x25 histogram, with each cell labeled by its count and its number. Only the nine in-zone cells are shaded: 11-14 run out to wherever a pitch landed, so they gather more pitches than any single cell almost by definition, and shading them on the same ramp darkened the border and flattened the nine cells the chart is about. They print their counts instead. In place of the strike zone box the other kinds draw, the grid carries a heavy line one ball radius outside it, since that is the edge the numbering is actually cut on. Counts come from each pitch's own `zone`, measured against the batter it was thrown to, while the cells are drawn from the panel's average zone -- the same averaging every strike zone in these plots already does, so a pitch can be counted in a cell its own dot wouldn't sit in.
- `plot_zone(grid=True)` (`mound zone --grid`), drawing the 3x3 grid under a scatter, heatmap or KDE surface, for reading a plot against the zones `--zone` would return. Clipped to the drawn strike zone rather than to the grid's own outer edge, which sits a ball radius further out and would read as a second, wrong zone box.

### Fixed

- The half-plate constant was rounded to `0.708` feet, five hundredths of an inch short of the true 17/24. Small enough to look harmless and large enough to matter: it put 4 pitches per 42,538 in the wrong zone and disagreed with Savant's own `isInZone` on 2, so the README's "zero mismatches" claim was off by two. Now exact, and `in_zone` matches Savant on all 42,538. Drawn strike zones move by half a thousandth of a foot -- a fraction of a pixel, visible in the committed images only as antialiasing along the box edge.

### Changed

- The `mound pitches` table gained at-bat, count, batter and zone columns, and prints `at_bat_result` only on the pitch that produced it. The inning alone can't separate three at-bats in the same inning, which is what made a repeated result confusing to read in the first place; the count also shows where a pitch-type filter is hiding pitches, since a jump from 0-1 to 1-2 means a slider went by in between.
- The same table pays for that width by stating whatever doesn't vary once, in a headline above the rows, instead of down a column: the pitcher, the date of a single outing, the hitter in a matchup, the type behind `--pitch splitter`. Pitch types show as Statcast codes in the rows and by name in the headline, `zone` replaces `in_zone` because 1-9 versus 11-14 says the same thing in two characters and adds the location, and a truncated table now says `Showing 20 of 77 pitch(es).` rather than reporting a total it isn't showing. What counts as unvarying is read from the whole collection, so a `--limit` landing mid-at-bat can't promote a column that actually differs.

## [0.8.0] - 2026-08-16

### Added

- `mound zone --color-by {pitch_type,stand,none}`, exposing a `plot_zone()` argument the CLI couldn't reach before, and a color lookup for batter handedness so `color_by="stand"` actually renders lefties and righties as two colors instead of one undifferentiated gray. Handedness draws the house green against the splitter's orange: an earthier clay looked better but collapsed into nearly the same olive as the green under red-green color blindness, where this pair keeps a 20-point lightness gap. It's the one-panel counterpart to `--split-by stand`: color holds both sides against the same axes, splitting gives each its own strike zone.
- The legend key labels handedness as "vs LHB"/"vs RHB", matching what `split_by` already titles its panels, and orders the two the same way (left, then right). Pitch types still read most-common-first, so the key doubles as a pitch mix.
- `scripts/make_docs_images.py` regenerates every plot committed to `docs/images/`, each pinned to the window it was first made from rather than a relative one like `last=4`, so a styling change can be re-rendered without the figures quietly sliding forward to last night's start and contradicting the prose around them.

### Changed

- Density surfaces (`plot_zone(kind="heatmap")` and `kind="kde"`) run yellow-to-green instead of cream-to-red, so a chart embedded on moundcli.com no longer fights the page around it. The ramp is ColorBrewer's 7-class YlGn, whose stops already step down in even increments of perceived lightness, plus one darker stop: YlGn ends at a medium-dark green that left the hottest cell short of the punch a peak wants, and the site's own darkest green supplies it. The yellow low end earns its place by keeping a one-pitch bin visible against the plot background, which a green that faint wouldn't be.
- A single-color scatter (`color_by=None`, or a value the active palette doesn't recognize) draws in green rather than neutral gray, for the same reason.
- A scatter showing only one pitch type now draws in that house green too, instead of that pitch's own color. A color that separates nothing isn't worth spending, and the headline already names the pitch; this is the same reasoning behind drawing no legend key for a single group. The trade is that a splitter is no longer orange in every chart it appears in, only in the ones where the color tells it apart from something. The rule is decided against the whole figure rather than each panel, so a `split_by` pair can't end up keyed by color on one side and not the other.

### Fixed

- `mound zone` no longer dumps a traceback for an unknown `--kind`, `--split-by` or `--color-by` value, matching how the command already handles an unwritable `--out` path.

## [0.7.1] - 2026-08-14

### Added

- A worked example in `docs/examples/diaz-blown-saves.md`, with `examples/diaz_blown_saves.py` as its runnable companion: fact-checking a closer's postgame explanation ("I was throwing my fastball right in the middle") against his pitch locations. Covers the path from a name to an answer -- finding a pitcher's recent games and their IDs, exporting every pitch, breaking down mix and arsenal by game, defining "the middle" against each batter's own zone, and pulling the video for the pitches that got hit.

### Fixed

- Games in progress are no longer cached. Caching keys on `game_pk` alone, on the premise that a finished game's data never changes -- but a game cached while it was still being played kept whatever partial feed existed at that moment, permanently, and a later query would silently come up short (a reliever who pitched the ninth simply missing from a game he appeared in). `fetch_game_feed()` now writes only feeds whose Savant game status reads final, and ignores a cached feed that doesn't, so entries already poisoned by an earlier version repair themselves on the next run once the game is over. A game still in progress re-fetches every time.

### Changed

- `plot_zone(kind="heatmap")` no longer draws a "Fewer"/"More" colorbar, matching `kind="kde"`, which dropped its own in 0.4.0. Darker already reads as more pitches, and the vertical bar shrank the plot area enough to push the strike zone and home plate off-center relative to every other plot kind -- a visible misalignment when heatmap and scatter panels sit side by side, and doubled in a `--split-by` pair.

## [0.7.0] - 2026-08-13

### Added

- Batter filtering, for matchup views from the pitcher's side: `PitchCollection.filter(batter=...)` and `Pitcher.pitches(batter=...)`, plus a `--batter` flag on `mound pitches`, `mix`, `results`, `arsenal`, `zone` and `video`. Takes a name or an MLB player ID, or a list mixing the two; names match any part of the name Savant reports, ignoring case and accents, so `--batter perdomo` is enough. `filter(pitcher=...)` is the same thing for the other side, useful once a collection spans more than one arm.
- `Batter`, the mirror image of `Pitcher`: the pitches a hitter *faced*, discovered from his own game log and pulled from every pitcher who faced him in those games. `Batter("Geraldo Perdomo").pitches(last=5, pitcher="Roki Sasaki")` and `Pitcher("Roki Sasaki").pitches(last=5, batter="Geraldo Perdomo")` return the same matchup from either side; the pitcher's side fetches far fewer games, since a starter appears in a fraction of the games a hitter plays.
- `PitchCollection.chase_rate()` (with the same `by_pitch_type` option as `swing_rate()`/`whiff_rate()`): swings divided by pitches *outside* the zone, so a chase pitch's real job shows up as its own number. Location comes from `in_zone` geometry rather than the `is_strike` ruling, and pitches with no plate coordinates drop out of the denominator instead of counting as strikes. `mound arsenal` gains a `chase_rate` column alongside `whiff_rate`.
- `plot_zone()` labels matchups: a plot narrowed to one hitter notes "vs. <hitter>" in its dek, and a batter-side collection headlines as "Pitch locations to <hitter>" rather than crediting the hitter with throwing them.

### Changed

- `mound.statsapi.pitching_game_log()`/`pitching_game_log_seasons()` are now `game_log()`/`game_log_seasons()` with a `group` argument (`"pitching"` or `"hitting"`), since the same Stats API endpoint serves both sides of the ball. Internal client functions, not part of the documented `Pitcher`/`PitchCollection` API.

## [0.6.1] - 2026-08-13

### Fixed

- `mound zone --out` now creates missing parent directories before saving, matching how `--export` and `video --out-dir` already behave, instead of raising a raw `FileNotFoundError`.
- CLI commands no longer dump a full traceback (including every local variable, e.g. an entire pitch DataFrame) for an unwritable `--out`/`--out-dir`/`--export` path; `zone`, `pitches --export`, `video` and `video-id` now fail with one clear line instead.

## [0.6.0] - 2026-08-13

### Added

- `mound --version` prints the installed CLI's version and exits, so you can check what you have installed without dropping into Python.

## [0.5.1] - 2026-08-13

### Changed

- Consolidated the CLI's repeated `--last`/`--since`/`--until`/`--game`/`--pitch`/`--stand`/`--at-bat`/`--pitch-number`/`--cache`/`--cache-dir` option declarations, previously duplicated across `pitches`, `mix`, `results`, `arsenal`, `zone` and `video`, into shared `Annotated` type aliases in `mound/cli.py` -- each flag's name and help text now live in one place instead of five.
- `_get_pitches()`'s internal helper is now keyword-only, closing off the possibility of a silent argument-order mistake at a call site.
- `video --limit` now goes through a new `PitchCollection.limit()` method instead of constructing a `PitchCollection` directly from another collection's internals.
- `_fail()` is now typed `-> NoReturn`, making explicit (for both readers and type checkers) that it always exits rather than returning.

## [0.5.0] - 2026-08-09

### Added

- `Pitch` gains `spin_rate`, `release_extension`, `release_pos_x`, `release_pos_z`, `horizontal_break` and `induced_vertical_break`, parsed from fields Savant's `/gf` feed already returns but Mound wasn't yet surfacing. All default to `None` rather than raising when a pitch predates or otherwise lacks tracking coverage for them. Flow through automatically to `to_frame()`/CSV/JSON/Parquet export; no new fetch required.
- `Pitch` gains `is_swing` and `is_whiff`, derived from `pitch_call` the same way `is_strike` already is. `PitchCollection.swing_rate()` and `.whiff_rate()` (each with a `by_pitch_type` option, matching `strike_rate()`) calculate the resulting percentages -- whiff rate is misses divided by swings, matching Baseball Savant's own convention, not misses divided by every pitch thrown.
- `PitchCollection.pitch_metrics()` averages velocity, spin rate and movement by pitch type, using the fields above. Combined with `whiff_rate()` in the new `mound arsenal` CLI command, for questions like how nasty a pitch looked in one start (`--game`) versus across a season (`--last`/`--since`).

### Changed

- Adding `is_swing`/`is_whiff` shifts `at_bat_result` and `description` one position later in `Pitch`'s field order; only matters for code constructing a `Pitch` positionally rather than by keyword.

## [0.4.0] - 2026-08-09

### Added

- `mound video --limit N` caps how many clips a run downloads (e.g. `--limit 1` for a single clip), rather than always fetching every pitch matching the other filters.
- `PitchCollection.filter()` / `Pitcher.pitches()` accept `at_bat_number` and `pitch_number`, exposed on the CLI as `--at-bat`/`--pitch-number`, to narrow down to one specific at-bat or one exact pitch (pair with `game`/`--game`, since an at-bat number is only unique within a single game). Useful on its own, and with `mound video` to download the clip for one particular pitch.
- `mound.video.download_video_by_id()` and the `mound video-id <pitch_id>` CLI command download a broadcast clip directly from a known `pitch_id` (e.g. one saved from an earlier export), with no pitcher/game lookup needed first.

### Changed

- Refined `kind="kde"`/`kind="heatmap"` styling in `plot_zone()`: both now share a single on-brand warm gradient instead of matplotlib's generic `YlOrRd`. KDE surfaces default to a fixed bandwidth (rather than scipy's sample-size-dependent Scott's rule, which oversmoothed small pitch samples into one shapeless blob) and a gamma-corrected color scale that keeps the true "hot zone" distinct from its faint tail. The KDE colorbar is removed -- its density values are an arbitrary scale, not a pitch count, so a "Fewer"/"More" legend was either meaningless or redundant with what the color already shows.
- `plot_zone()`'s y-axis now marks its topmost tick with a foot mark (e.g. `4′`), so the plate-height scale reads in feet without needing a full axis label.

## [0.3.0] - 2026-08-08

### Added

- Optional local file cache for Baseball Savant game-feed responses, keyed by `game_pk`. Enable with `Pitcher.pitches(cache=True)` / `--cache` (or a custom directory via `cache="/some/dir"` / `--cache-dir`, defaulting to `~/.cache/mound`). Because a finished game's data never changes, repeat queries automatically fetch only games not already cached, with no separate "update" step needed.
- `plot_zone(kind="kde")` renders a kernel density estimate instead of the plain 2D-histogram heatmap, for a smoother density surface on larger pitch samples. Requires the new optional `scipy` dependency (`pip install "mound[viz]"`); bandwidth is configurable via `bw_method`, exposed on the CLI as `mound zone --kind kde --bw-method`.
- `Pitch.download_video()` / `PitchCollection.download_videos()` and the `mound video` CLI command download a pitch's Baseball Savant broadcast clip, resolved from its `pitch_id`. Captures the clip page's default embedded angle only (in practice, the home broadcast feed).

## [0.2.0] - 2026-08-08

### Added

- `batter_stand` field on `Pitch`, populated from Statcast's `stand`. Filter with `.filter(stand="L")` / `Pitcher.pitches(stand=...)` (accepts `"L"`/`"left"`/`"LHB"`, `"R"`/`"right"`/`"RHB"`, case-insensitive) or the CLI's `--stand` option.
- `plot_zone(split_by="stand")` facets a zone chart into side-by-side vs-LHB/vs-RHB panels (each with its own strike zone and pitch count), exposed via the CLI's `--split-by` option on `mound zone`.

### Changed

- README documents PyPI installation, since `mound` is now published there.

## [0.1.0] - 2026-08-08

### Added

- Initial prototype: resolve a pitcher by name or MLB ID, retrieve Statcast pitch-level data (filterable by game, date range, last-N-starts or pitch type), calculate pitch mix and strike rate, plot pitch locations against the strike zone, and export to CSV/JSON/Parquet.
- `Pitcher`/`PitchCollection` Python API and a `mound` CLI (`search`, `pitches`, `mix`, `results`, `zone`) sharing the same underlying implementation.
- Data sourced directly from the MLB Stats API and Baseball Savant's `/gf` endpoint, no `pybaseball` dependency.
- Pytest suite covering player resolution, game-log/pitch parsing, filtering, analysis and export, run against mocked HTTP fixtures.
- README, ROADMAP and an end-to-end example using Roki Sasaki's splitter.
