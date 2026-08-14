## Changelog

All notable changes to this project will be documented in this file.

Format based on Keep a Changelog.

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
