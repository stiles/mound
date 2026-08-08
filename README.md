# Mound

A CLI and Python toolkit for retrieving, analyzing and visualizing MLB pitch-level data — without needing to know MLB player IDs or the underlying API structures.

```
> How many splitters did Roki Sasaki throw against the Diamondbacks last night?
> How often has he thrown it relative to his other pitches over his last four starts?
> What does its location look like over that period?
```

Mound answers questions like these with a few CLI commands or a few lines of Python.

## Install

```bash
pip install mound

# Parquet export support:
pip install "mound[parquet]"
```

Or from a local checkout (editable):

```bash
git clone https://github.com/stiles/mound.git
cd mound
pip install -e .
```

Requires Python 3.10+.

## Quickstart

### CLI

```bash
# Find a player and their MLB ID
mound search "Roki Sasaki"

# Retrieve pitches from his last 4 starts
mound pitches "Roki Sasaki" --last 4

# Isolate one pitch type
mound pitches "Roki Sasaki" --last 4 --pitch splitter

# Pitch mix and results by pitch type
mound mix "Roki Sasaki" --last 4
mound results "Roki Sasaki" --last 4 --pitch splitter

# Plot pitch locations against the strike zone
mound zone "Roki Sasaki" --pitch splitter --last 4 --out splitter_zone.png

# Export the underlying data
mound pitches "Roki Sasaki" --last 4 --export roki_last4.csv
```

Run `mound --help` or `mound <command> --help` for the full option list.

### Python

```python
from mound import Pitcher

roki = Pitcher("Roki Sasaki")

pitches = roki.pitches(last=4)
splitters = pitches.filter(pitch_type="splitter")

splitters.pitch_mix()
splitters.strike_rate()
splitters.plot_zone(out="splitter_zone.png")

pitches.to_csv("roki_last4.csv")
```

`Pitcher.pitches()` and `PitchCollection.filter()` both accept:

| Argument | Meaning |
|---|---|
| `last` | most recent N appearances |
| `since` / `until` | date range (`"YYYY-MM-DD"` or `date`), inclusive |
| `game` | one or more MLB `game_pk` values |
| `pitch_type` | a pitch name, alias, or Statcast code (see below) |
| `stand` | batter side: `"L"`/`"left"`/`"LHB"` or `"R"`/`"right"`/`"RHB"` |

Filtering a `PitchCollection` always returns another `PitchCollection`, so any combination of `.filter()`, `.pitch_mix()`, `.strike_rate()`, `.plot_zone()` and export methods composes freely.

## Plots

`plot_zone()` renders a headline, a dek (pitch count, strike rate, date range) and a source line around the strike-zone chart itself, rather than relying on axis titles or a boxed legend:

![Roki Sasaki splitter locations](docs/images/roki_splitter_zone.png)

All three are auto-generated but overridable:

```python
splitters.plot_zone(
    title="Sasaki leans on the splitter",
    subtitle="134 pitches since the All-Star break",
    source="Source: Baseball Savant",
    kind="heatmap",  # or "scatter" (default)
    out="splitter_zone.png",
)
```

Pass `subtitle=""` or `source=""` to omit either. Passing your own `ax` (e.g. for a multi-panel figure) skips the dek/source and falls back to a plain left-aligned title, so `plot_zone()` behaves as a well-mannered subplot.

Pitch location isn't mirrored for batter handedness, so mixing lefties and righties in one panel can blur the picture — pass `split_by="stand"` to break it into a vs-LHB / vs-RHB pair, each with its own strike zone and pitch count:

![Roki Sasaki splitter locations, split by batter handedness](docs/images/roki_splitter_zone_by_stand.png)

```python
splitters.plot_zone(split_by="stand", out="splitter_zone_by_stand.png")
```

```bash
mound zone "Roki Sasaki" --last 4 --pitch splitter --split-by stand --out splitter_zone_by_stand.png
```

## Pitch types

Statcast tags every pitch with a short code. Mound normalizes these into human-readable names and accepts common aliases when filtering, so `pitch_type="four-seam"`, `"fastball"` and `"FF"` are all equivalent.

| Code | Name | Common aliases |
|---|---|---|
| `FF` | four-seam fastball | fastball, four-seam |
| `FT` | two-seam fastball | two-seam |
| `SI` | sinker | |
| `FC` | cutter | cut fastball |
| `SL` | slider | |
| `ST` | sweeper | sweeping slider |
| `SV` | slurve | |
| `CU` | curveball | curve |
| `KC` | knuckle curve | |
| `CH` | changeup | change-up |
| `FS` | splitter | split-finger |
| `FO` | forkball | |
| `SC` | screwball | |
| `KN` | knuckleball | knuckler |
| `EP` | eephus | |

**Note on Roki Sasaki's signature pitch:** Statcast classifies it inconsistently start-to-start — sometimes as a splitter (`FS`), sometimes as a forkball (`FO`), depending on its movement profile in a given game. If a `pitch_type="splitter"` query looks incomplete, check `pitch_type="forkball"` too, or filter using both.

## Data sources

Mound calls two unofficial, public MLB data services directly:

- **[MLB Stats API](https://statsapi.mlb.com)** — player search/lookup and game logs, used to resolve a pitcher's identity and discover which games to pull.
- **[Baseball Savant](https://baseballsavant.mlb.com)** — the `/gf` game-feed endpoint, used for pitch-by-pitch Statcast data (location, velocity, pitch type, count, outcome).

Both are unofficial and undocumented; endpoints or response shapes could change without notice. Mound sends a descriptive `User-Agent` and retries transient failures, but does not currently cache responses, so repeated queries re-fetch data from these services.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Tests run entirely against mocked HTTP fixtures in `tests/fixtures/` (via the `responses` library) and don't require network access.

## Known limitations

- No caching yet — every call re-fetches from the MLB Stats API / Baseball Savant.
- Pitch classification comes from Statcast's own model and can be inconsistent for pitches with unusual movement (see the Roki Sasaki note above).
- Only pitchers are supported as the primary retrieval unit; there's no batter-vs-pitcher matchup view yet (see [ROADMAP.md](ROADMAP.md)).
- Historical data availability depends on Statcast/Savant coverage, which is generally reliable from 2015 onward.
- All requests are synchronous and unthrottled beyond basic retry/backoff; heavy bulk retrieval (e.g. a full season) will be slow.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned enhancements beyond this prototype.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
