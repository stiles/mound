## Changelog

All notable changes to this project will be documented in this file.

Format based on Keep a Changelog.

## [Unreleased]

## [0.13.0] - 2026-09-02

### Added

- Pitch tunneling, measured rather than eyeballed: `PitchCollection.tunnels()` reports how far apart two pitches were where the hitter had to commit and how far apart they finished, and `plot_tunnel()` draws the pair as he'd see it, with an open marker at the commit point and a filled one at the plate. Pairs each pitch with the one that followed it in the same at-bat by default, since tunneling is a question about sequence; `consecutive=False` and `same_type=True` open that up. Handed more than two pitches, `plot_tunnel()` ranks them and draws the best pair, which makes it a way to find an outing's best sequence rather than only to render one already chosen.
- `mound/trajectory.py` and the nine fields behind it. Savant's `/gf` feed has carried Statcast's full trajectory fit all along -- release position, release velocity and a constant acceleration carrying drag and Magnus together -- and Mound was parsing four of the nine and dropping the rest. They describe the whole flight as a quadratic in each axis, so `Trajectory` answers for any point between the hand and the plate in closed form: `position_at_distance()`, `time_before_plate()`, `path()`. Exports gain the columns; `Pitch.trajectory()` is the accessor.
- The commit point is configurable and deliberately so. It defaults to 23.8 feet, which is the distance Baseball Prospectus's tunnel work settled on and therefore the comparable one, but a fixed distance is 162 ms of a 100 mph four-seamer and 200 ms of an 80 mph curveball, and a swing decision is a reaction rather than a place -- so `commit_time` fixes it at a number of seconds before each pitch's own arrival instead. Neither is the right answer for every question, which is why both are there and the README says what each is for.
- `docs/images/roki_semien_tunnel.png`, and its recipe in `scripts/make_docs_images.py`: Sasaki's forkball and four-seamer to Marcus Semien on July 24, three inches apart where Semien had to commit and seventeen by the time they arrived.
- The README is published at moundcli.com/docs rather than only linked to on GitHub, rendered from the same file the package ships to PyPI so the page and the installed version can't disagree about what a command does. The site's "Read the docs" button used to hand the reader to GitHub's UI one click after the landing page, and none of the prose that would answer a search for "chase rate vs whiff rate" lived on the site's own domain.
- Inline code in the site's hand-written prose gets the same tinted treatment the rendered markdown already had, through a shared `.code-inline` class. A flag or command name set in bare green monospace at body size was hard to pick out of a sentence, which is the whole job of marking it as code.
- Repo-relative links in synced markdown now resolve to site routes where the site hosts the file: `README.md` to `/docs`, `CHANGELOG.md` to `/changelog`, and `docs/examples/<name>.md` to `/examples/<name>`, each keeping its anchor. So the Díaz walkthrough's link into the arsenal section lands on `/docs#whiff-rate-chase-rate-and-pitch-metrics` instead of leaving the site mid-sentence. Anything the site doesn't host still falls back to GitHub, which is what `ROADMAP.md` does, deliberately -- a roadmap on a product site reads as a promise.

### Fixed

- Savant measures `plate_x`/`plate_z` at the *middle* of home plate, 17/24 feet from the point, not at its front edge. Fitting the plane empirically against Savant's own numbers across 22,482 cached pitches lands there exactly and nowhere else; the front edge, which is the intuitive guess, is off by a tenth of an inch horizontally and three tenths vertically -- small enough to look like rounding and large enough to move a pitch between zones. Nothing shipped depended on it before now, since nothing reconstructed a trajectory, but every number in `tunnels()` does. It's the same 17/24 that `mound.zone` already uses for half the plate's width, which is a coincidence of the plate being as deep as it is wide.

## [0.12.0] - 2026-08-22

### Added

- `mound outing`, one start broken down end to end: the shape of the outing, how each plate appearance ended, and the arsenal table -- in one command instead of running `mix`, `results` and `arsenal` against the same `--game` three times. Selection is built for the question people actually ask -- bare `mound outing "Roki Sasaki"` is the morning-after view, `--date` a particular day, `--season` his last outing of a year, `--game` an exact `game_pk`. There's deliberately no `--last`, since an outing is one game; a window of starts is still what `mix`/`arsenal`/`zone` are for. `--out` adds the zone chart, opt-in rather than writing a file nobody asked for. Section headings are bold, which click strips when the output isn't a terminal, so a piped report stays plain text.
- Two honest limits in that report worth knowing. It counts innings he *appeared* in, not innings pitched: a reliever who enters with two outs still shows up in that inning, and nothing in the feed counts outs, so there's no way to render a box-score line without inventing one. And everything but `--game` goes through the Stats API game log, which is where the opponent in the headline comes from -- a bare `game_pk` can't be looked up there without guessing which season's log to read, so `--game` reports the date and the game and stops. A doubleheader is the one case where `--date` doesn't name an outing, and it says so, listing both `game_pk` values rather than silently taking the nightcap.
- `plate_appearances()` on `PitchCollection`: how the at-bats in a collection ended, counted by result. Read only from the pitch each at-bat ended on, since Savant stamps `at_bat_result` on every pitch of the at-bat and counting every row scores a five-pitch strikeout five times. Inherits `ends_at_bat`'s edges, including the one that makes a filtered count a narrower question than it looks -- `filter(pitch_type="splitter").plate_appearances()` counts the at-bats that *ended* on a splitter, not every at-bat containing one.
- `first_pitch_strike_rate()` on `PitchCollection`, with the same `by_pitch_type` option as the other rates. Split out from `strike_rate()` because the count a pitcher spends the rest of an at-bat working from is mostly settled by pitch one, and a starter who can't get it over runs up a pitch count regardless of how his stuff looks.

### Changed

- `mound arsenal`/`mound faced-arsenal` gained usage rate and strike rate, and lost about 45 columns of width. The old table ran past 130 characters and wrapped in a normal terminal, most of it spent on `release_extension` and on spelling out `horizontal_break`/`induced_vertical_break`; those two shorten to `hb`/`ivb` and extension is gone, since it barely moves between one pitcher's own pitches. It's still one `pitch_metrics()` call away in Python, along with the full-length names. What the width bought is the two columns the table was missing: usage rate, and the strike rate that previously meant running `mound results` against the same query to see. The whole repertoire now fits one screen at 85 characters.
- A missing number in that table reads as `-` rather than `NaN`, which looked like a bug where it was actually information: a pitch type that never left the zone has no chase rate, and one nobody swung at has no whiff rate, neither of which is a rate of zero. Spin also loses its decimal, which was precision the tracking doesn't have.
- Building `outing` is what turned this up. Composing the existing commands verbatim gave two tables keyed on the same pitch types, each spending a line on the `pitch_type` index name and repeating the pitch counts, to add two columns each -- which was a sign the arsenal table itself was carrying the wrong columns, not that the report needed a third one of its own.
- Every published copy of the old arsenal table was re-run against the cached games rather than hand-edited, so the numbers stay real: the README's `mound arsenal "Roki Sasaki" --game 825051`, both tables in the Díaz walkthrough, and moundcli.com's landing-page hero, which is that same command. Each number the two versions share came back identical -- velocity, whiff rate and chase rate to the tenth -- so what moved is which columns are there, not the data behind them. The styled arsenal table beside the hero drops spin's decimal to match the terminal's.
- The README gained a "One outing" section, and its arsenal section now says what the short column names stand for and where the full-length ones still live. The `mound arsenal` sample no longer needs a sentence explaining `NaN`.
- The CLI's player lookup collapsed into one helper per side, replacing four copies of the same two-branch `try`/`except` around `Pitcher(name)`/`Batter(name)`. `outing` is what forced it: unlike every other command it needs the resolved `Pitcher` itself, not just the collection that comes out of it.
- moundcli.com covers `outing` now, with the report as printed and the four ways to name a start. The landing page also stopped advertising "eight commands and one Python object," which was true up to 0.10.0 and is now ten commands, seven of them mirrored on the batter's side, over `Pitcher` and `Batter`.

### Fixed

- Three README examples paired Shohei Ohtani with Roki Sasaki, who are teammates -- a matchup that cannot appear in any feed. Replaced with Logan Henderson, checked against the data rather than guessed: he faced Ohtani in both the last-5 and last-8 windows the examples use, so `--last 5` and `--last 8` each return pitches as written. Every other pairing in the docs was checked and is cross-team.
- The site's pitch-type colors were the palette from before 0.9.0 reassigned them for perceptual distance, so a chart screenshot and the page around it disagreed on what a pitch looks like -- the splitter worst of all, drawn in what is now the sinker's clay orange while every committed figure and every terminal render it dark green. The forkball sat next to it, and the cutter, sweeper, curveball and changeup were each a shade off. All nine now come from `PITCH_TYPE_COLORS` unchanged, and the file that holds them says so.
- The Open Graph card had the same drift. Its illustrated pitches below the zone are changeups rather than splitters, because the splitter's green is 2.2:1 against that card's dark background and disappears -- the same shape of pitch in a color that survives being printed on it.
- Three boolean filters no longer emit a pandas `FutureWarning` about downcasting an object column, which is the shape those columns take whenever a feed leaves the flag unset on a pitch: `plate_appearances()` and the `mound pitches` result column both on `ends_at_bat`, and `whiff_rate()` on `is_swing`. All three now cast to the nullable `boolean` dtype before filling, the idiom `chase_rate()` already used for `in_zone`. The masks are identical for every shape those columns arrive in -- real bools, objects carrying `None`, all-missing and empty -- so this moves no number in any table.

## [0.11.0] - 2026-08-20

### Added

- `Pitcher.games()`/`Batter.games()` and the `mound games`/`mound faced-games` CLI commands: a plain list of a player's games -- date, opponent, home/away, `game_pk` -- for the last N appearances or a whole season. Reads only the Stats API's game log, which Mound already fetched internally to decide which games to pull pitches from; exposing it directly answers "which games" without paying for a Baseball Savant round trip per game just to find out. Returns a DataFrame, so the `game_pk` column feeds straight into `pitches(game=...)` once you've picked which games are worth the fetch.
- `--season` on `pitches`, `faced`, `mix`, `faced-mix`, `results`, `faced-results`, `arsenal`, `faced-arsenal`, `zone`, `faced-zone`, `video` and `faced-video`. `Pitcher.pitches(season=...)`/`Batter.pitches(season=...)` have taken a season since the beginning, but the CLI only exposed `--last`/`--since`/`--until` until `games`/`faced-games` added `--season` -- now every command that selects games shares the same four options.

## [0.10.0] - 2026-08-20

### Added

- `mound faced`, the CLI counterpart to `Batter`: the pitches a hitter faced, from every arm he saw, or narrowed to one matchup with `--pitcher`. Previously the batter side was only reachable in Python (`Batter(...).pitches()`) or indirectly through `--batter` on the pitcher-side commands. Shares the same table as `mound pitches`, which now names the batter and (when it varies) a `pitcher` column, rather than assuming every query is pitcher-first.
- `mound faced-mix`, `faced-results`, `faced-arsenal`, `faced-zone` and `faced-video`, closing out the rest of the CLI's batter-side surface: the same pitch mix, strike-rate breakdown, velocity/spin/whiff/chase table, zone plot and video download that the pitcher-side commands already had, each built on a batter's own game log instead of a pitcher's starts.
- `docs/images/skubal_arsenal_zone.png`, a five-pitch-type start, so the README can show the pitch-type palette. Every other committed figure is a single pitch type or a density surface, none of which use it.
- A second worked example in `docs/examples/ohtani-spin-chase.md`, with `examples/shohei_spin_chase.py` as its runnable companion: testing a hunch from watching games ("he's striking out a lot lately by chasing sliders and changeups away") against 40 games from the hitter's side. Covers what the pitcher-side walkthrough can't -- `Batter` and its per-game fetch cost, one row per plate appearance via `ends_at_bat`, the pitch each strikeout ended on, and chase rate split by pitch family and side of the plate. Also settles which sign of `plate_x` is the outer half, which nothing in the feed states: Ohtani's own hit batters put a lefty's body at +2.1 feet and a righty's at -1.3 to -2.9, so for a left-handed hitter away is negative, and Statcast zones 11 and 13.
- `examples/shohei_strikeout_supercut.py`, which turns the walkthrough's last step into one file: a clip per strikeout, each labeled with the pitcher, the pitch type in its chart color, the velocity, the zone and how the at-bat ended, joined in order behind a title card. Downloads are Mound's; the stitching is ffmpeg, which has to be on `PATH`. Savant's clips share a resolution but not a frame rate, so each one is re-encoded before being concatenated. `--spin-away` cuts it down to the strikeouts on breaking or offspeed pitches off the plate.

### Changed

- Reassigned the pitch-type colors. The old palette grouped them by family -- fastballs in blues, breaking balls in reds and purples -- which put the closest colors on the pitches most likely to share a chart: across 620 pitcher-games of cached feeds, a four-seamer and a sinker appear together in 286 of them and were 9.8 apart in CIEDE2000, where about 20 is the floor for telling two scatter dots apart; a four-seamer and a cutter, together in 205, were 8.8 apart. The new assignment maximizes distance between pairs that actually co-occur, weighted by frequency and counting simulated red-green color blindness at half weight, which cuts the total penalty by about two thirds. The sinker moves to orange, the cutter to a dark blue, the splitter and forkball into the teals alongside the changeup (they share a chart with it twice in 620 games), the sweeper to a dark red and the curveball to a darker purple. The two slider variants stay close on purpose, since a sweeper is a slider. Nothing about `color_by` or the single-pitch-type house color changes.

### Fixed

- Broadcast clips whose URL ends in base64 `=` padding could never be downloaded. Savant writes the padding into the page as the HTML entity `&#x3D;`, and `resolve_video_url` returned the attribute verbatim, so the request went out with the entity still in it and came back 404. Found while pulling clips for the Ohtani walkthrough, where two of eight pitches failed. The URL is now unescaped before it's fetched.

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
