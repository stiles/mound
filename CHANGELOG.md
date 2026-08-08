## Changelog

All notable changes to this project will be documented in this file.

Format based on Keep a Changelog.

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
