"""Mound's command-line interface.

mound search "Roki Sasaki"
mound pitches "Roki Sasaki" --last 4 --pitch splitter
mound pitches "Roki Sasaki" --last 1 --ends-at-bat
mound faced "Shohei Ohtani" --last 5 --pitcher "Roki Sasaki"
mound mix "Roki Sasaki" --last 4
mound faced-mix "Shohei Ohtani" --last 5
mound results "Roki Sasaki" --last 4 --pitch splitter
mound arsenal "Roki Sasaki" --game 825051
mound arsenal "Roki Sasaki" --last 8 --batter "Shohei Ohtani"
mound faced-arsenal "Shohei Ohtani" --last 8 --pitcher "Roki Sasaki"
mound zone "Roki Sasaki" --pitch splitter --last 4 --out zone.png
mound zone "Roki Sasaki" --last 8 --split-by stand --out zone.png
mound zone "Roki Sasaki" --last 8 --color-by stand --out zone.png
mound zone "Roki Sasaki" --last 8 --kind zones --out zone.png
mound faced-zone "Shohei Ohtani" --last 8 --out faced_zone.png
mound video "Roki Sasaki" --pitch splitter --last 4 --out-dir clips
mound video "Roki Sasaki" --pitch splitter --last 1 --limit 1
mound video "Roki Sasaki" --game 717404 --at-bat 34 --pitch-number 3
mound faced-video "Shohei Ohtani" --last 5 --out-dir clips
mound video-id 7468ecb9-0918-3aca-8ef5-6396e6ab80c3
"""

from __future__ import annotations

from typing import Annotated, NoReturn

import pandas as pd
import requests
import typer

from mound import __version__
from mound.pitches import Batter, PitchCollection, Pitcher
from mound.players import AmbiguousPlayerError, PlayerNotFoundError
from mound.zone import ZONE_NUMBERS

app = typer.Typer(
    name="mound",
    help="Retrieve, analyze and visualize MLB pitch-level data.",
    no_args_is_help=True,
    # Don't dump every local variable (e.g. a full pitch DataFrame) into an
    # unhandled exception's traceback -- that's noise for a CLI user, not a
    # helpful debugging aid.
    pretty_exceptions_show_locals=False,
)


def _fail(message: str) -> NoReturn:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mound {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show mound's version and exit.",
        ),
    ] = False,
) -> None:
    pass


# Shared filter options, reused across every pitch-retrieval command below.
# Centralizing each flag's name/help text here means every command stays in
# sync automatically instead of five near-identical `typer.Option(...)` calls
# drifting apart over time.
LastOption = Annotated[int | None, typer.Option("--last", help="Most recent N appearances")]
SinceOption = Annotated[str | None, typer.Option("--since", help="Start date (YYYY-MM-DD)")]
UntilOption = Annotated[str | None, typer.Option("--until", help="End date (YYYY-MM-DD)")]
GameOption = Annotated[int | None, typer.Option("--game", help="A specific MLB game_pk")]
PitchOption = Annotated[str | None, typer.Option("--pitch", help="Pitch type, e.g. 'splitter'")]
StandOption = Annotated[str | None, typer.Option("--stand", help="Batter side ('L' or 'R')")]
BatterOption = Annotated[
    str | None,
    typer.Option("--batter", help="Opposing batter: name (partial is fine) or MLB player ID"),
]
PitcherOption = Annotated[
    str | None,
    typer.Option("--pitcher", help="Opposing pitcher: name (partial is fine) or MLB player ID"),
]
AtBatOption = Annotated[
    int | None,
    typer.Option(
        "--at-bat", help="A specific at-bat number (unique within --game, not across games)"
    ),
]
PitchNumberOption = Annotated[
    int | None,
    typer.Option(
        "--pitch-number",
        help="A specific pitch number within that at-bat, e.g. 3 for the 0-2",
    ),
]
CacheOption = Annotated[
    bool,
    typer.Option(
        "--cache", help="Cache Savant game-feed responses locally to speed up repeat queries"
    ),
]
CacheDirOption = Annotated[
    str | None, typer.Option("--cache-dir", help="Custom cache directory (implies --cache)")
]

# Shared across `zone`/`faced-zone`.
KindOption = Annotated[
    str,
    typer.Option("--kind", help="'scatter', 'heatmap', 'zones', or 'kde' (requires mound[viz])"),
]
ColorByOption = Annotated[
    str,
    typer.Option("--color-by", help="Color scatter points by 'pitch_type', 'stand' or 'none'"),
]
SplitByOption = Annotated[
    str | None, typer.Option("--split-by", help="Facet into side-by-side panels, e.g. 'stand'")
]
GridOption = Annotated[
    bool, typer.Option("--grid", help="Draw the 3x3 zone grid inside the strike zone")
]
BwMethodOption = Annotated[
    float | None,
    typer.Option("--bw-method", help="Bandwidth for --kind kde (default: scipy's own heuristic)"),
]
OutOption = Annotated[str, typer.Option("--out", help="Output image path")]

# Shared across `video`/`faced-video`.
OutDirOption = Annotated[str, typer.Option("--out-dir", help="Directory to save clips to")]
VideoLimitOption = Annotated[
    int | None,
    typer.Option("--limit", help="Download at most N clips (e.g. --limit 1 for a single video)"),
]


def _count(balls, strikes) -> str:
    if pd.isna(balls) or pd.isna(strikes):
        return ""
    return f"{int(balls)}-{int(strikes)}"


def _parse_zones(raw: str | None) -> list[int] | None:
    """Read ``--zone 5`` or ``--zone 1,2,3`` into zone numbers."""
    if not raw:
        return None
    zones = []
    for piece in raw.replace(" ", "").split(","):
        if not piece:
            continue
        if not piece.isdigit() or int(piece) not in ZONE_NUMBERS:
            _fail(
                f"Unknown zone: {piece!r}. Statcast zones are 1-9 inside the "
                "strike zone and 11-14 outside it (there is no 10)."
            )
        zones.append(int(piece))
    return zones or None


def _values(df: pd.DataFrame, column: str) -> list:
    return sorted({value for value in df[column] if value is not None and not pd.isna(value)})


def _pitch_table(collection: PitchCollection, limit: int | None) -> str:
    """Render pitch rows as a table that reads one at-bat at a time.

    The at-bat number and count are here because the inning alone can't tell
    three at-bats in the same inning apart, which is what makes a repeated
    result confusing to read.

    Any field that never varies across the query is stated once in a headline
    rather than repeated down a column -- the date of a single outing, the
    hitter in a matchup, the pitch type behind `--pitch splitter`. That buys
    the width for the batter and `in_zone`, and it's why pitch types appear
    as Statcast codes in the rows but by name in the headline. `--export` is
    where the full names and the other 25 fields live.

    What's constant is read from the whole collection, not the rows being
    printed, so a `--limit` that happens to cut off inside one at-bat can't
    promote a column that actually varies.
    """
    full = collection.to_frame()
    dates, batters, pitchers, pitch_types, zones = (
        _values(full, "game_date"),
        _values(full, "batter_name"),
        _values(full, "pitcher_name"),
        _values(full, "pitch_type"),
        _values(full, "zone"),
    )
    games = collection.games

    # A pitcher-sourced collection always has exactly one pitcher (and, in
    # the same way, a batter-sourced one always has exactly one batter), so
    # whichever side the query came from names itself in the headline and
    # the other side's column collapses into it below when it's constant.
    if collection.pitcher:
        headline = [collection.pitcher.full_name]
        if len(batters) == 1:
            headline.append(f"to {batters[0]}")
    elif collection.batter:
        headline = [collection.batter.full_name]
        if len(pitchers) == 1:
            headline.append(f"vs {pitchers[0]}")
    else:
        headline = []
    headline.append(dates[0] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}")
    headline.append(f"game {games[0]}" if len(games) == 1 else f"{len(games)} games")
    if len(pitch_types) == 1:
        headline.append(pitch_types[0])
    if len(zones) == 1:
        headline.append(f"zone {int(zones[0])}")

    df = full.head(limit) if limit else full
    ended = df["ends_at_bat"].fillna(False).astype(bool)

    columns: dict[str, object] = {}
    # Several dates have to stay in the rows: they're what tells one
    # appearance from the next, and they carry the at-bat numbers, which
    # restart every game.
    if len(dates) > 1:
        columns["date"] = df["game_date"]
    columns |= {
        "inn": df["inning"],
        "ab": df["at_bat_number"],
        "count": [
            _count(balls, strikes)
            for balls, strikes in zip(df["balls"], df["strikes"], strict=True)
        ],
    }
    if len(batters) != 1:
        columns["batter"] = df["batter_name"]
    # Only a batter-sourced collection needs this: a pitcher-sourced one is
    # always one arm, already named in the headline above.
    if not collection.pitcher and len(pitchers) != 1:
        columns["pitcher"] = df["pitcher_name"]
    if len(pitch_types) != 1:
        columns["pitch"] = df["pitch_type_code"]
    columns["velo"] = df["velocity"]
    # Statcast's zone number says both where the pitch was and whether it was
    # a strike by location -- 1-9 in, 11-14 out -- in two characters, which
    # is why it's here instead of `in_zone`. A missing coordinate leaves it
    # blank rather than showing an integer as 5.0.
    if len(zones) != 1:
        columns["zone"] = ["" if pd.isna(z) else str(int(z)) for z in df["zone"]]
    columns |= {
        "call": df["pitch_call"],
        # Savant stamps an at-bat's outcome on every pitch of the at-bat.
        # Printing it only on the pitch that ended the at-bat keeps one
        # strikeout spread over five rows from reading as five strikeouts.
        "result": df["at_bat_result"].where(ended, "").fillna(""),
    }

    table = pd.DataFrame(columns).to_string(index=False)
    return f"{' · '.join(headline)}\n{table}"


def _get_pitches(
    name: str,
    *,
    last: int | None,
    since: str | None,
    until: str | None,
    game: int | None,
    pitch: str | None,
    stand: str | None = None,
    batter: str | None = None,
    at_bat_number: int | None = None,
    pitch_number: int | None = None,
    cache: bool = False,
    cache_dir: str | None = None,
) -> PitchCollection:
    try:
        pitcher = Pitcher(name)
    except PlayerNotFoundError as exc:
        _fail(str(exc))
    except AmbiguousPlayerError as exc:
        _fail(str(exc))

    try:
        return pitcher.pitches(
            last=last,
            since=since,
            until=until,
            game=game,
            pitch_type=pitch,
            stand=stand,
            batter=batter,
            at_bat_number=at_bat_number,
            pitch_number=pitch_number,
            cache=cache_dir if cache_dir else cache,
        )
    except Exception as exc:  # surface retrieval failures without a traceback
        _fail(f"Failed to retrieve pitches for {pitcher.name}: {exc}")


def _get_faced_pitches(
    name: str,
    *,
    last: int | None,
    since: str | None,
    until: str | None,
    game: int | None,
    pitch: str | None,
    stand: str | None = None,
    pitcher: str | None = None,
    at_bat_number: int | None = None,
    pitch_number: int | None = None,
    cache: bool = False,
    cache_dir: str | None = None,
) -> PitchCollection:
    try:
        batter = Batter(name)
    except PlayerNotFoundError as exc:
        _fail(str(exc))
    except AmbiguousPlayerError as exc:
        _fail(str(exc))

    try:
        return batter.pitches(
            last=last,
            since=since,
            until=until,
            game=game,
            pitch_type=pitch,
            stand=stand,
            pitcher=pitcher,
            at_bat_number=at_bat_number,
            pitch_number=pitch_number,
            cache=cache_dir if cache_dir else cache,
        )
    except Exception as exc:  # surface retrieval failures without a traceback
        _fail(f"Failed to retrieve pitches faced by {batter.name}: {exc}")


def _print_pitches(
    collection: PitchCollection,
    *,
    zone: str | None,
    ends_at_bat: bool,
    limit: int | None,
    export_path: str | None,
    export_format: str | None,
) -> None:
    """Shared tail end of `pitches`/`faced`: narrow, print the table, export."""
    zones = _parse_zones(zone)
    if zones:
        collection = collection.filter(zone=zones)
    if ends_at_bat:
        collection = collection.filter(ends_at_bat=True)

    if collection.empty:
        typer.echo("No pitches found for the given filters.")
    else:
        typer.echo(_pitch_table(collection, limit))
        shown = min(limit, len(collection)) if limit else len(collection)
        if shown < len(collection):
            typer.echo(f"\nShowing {shown} of {len(collection)} pitch(es).")
        else:
            typer.echo(f"\n{len(collection)} pitch(es) total.")

    if export_path:
        try:
            collection.export(export_path, format=export_format)
        except OSError as exc:
            _fail(f"Could not export to {export_path!r}: {exc.strerror or exc}")
        typer.echo(f"Exported {len(collection)} pitch(es) to {export_path}")


def _print_mix(collection: PitchCollection) -> None:
    """Shared body of `mix`/`faced-mix`."""
    if collection.empty:
        typer.echo("No pitches found for the given filters.")
        return

    mix_series = collection.pitch_mix()
    for pitch_type, pct in mix_series.items():
        typer.echo(f"{pitch_type:<24} {pct:>5.1f}%")


def _print_results(collection: PitchCollection) -> None:
    """Shared body of `results`/`faced-results`."""
    if collection.empty:
        typer.echo("No pitches found for the given filters.")
        return

    df = collection.to_frame()
    summary = df.groupby("pitch_type").agg(
        pitches=("pitch_type", "count"),
        strikes=("is_strike", "sum"),
    )
    summary["balls"] = summary["pitches"] - summary["strikes"]
    summary["strike_rate"] = (summary["strikes"] / summary["pitches"] * 100).round(1)
    summary["usage_rate"] = (summary["pitches"] / summary["pitches"].sum() * 100).round(1)
    summary = summary.sort_values("pitches", ascending=False)
    summary = summary[["pitches", "strikes", "balls", "strike_rate", "usage_rate"]]

    with pd.option_context("display.float_format", "{:.1f}".format):
        typer.echo(summary.to_string())


def _print_arsenal(collection: PitchCollection) -> None:
    """Shared body of `arsenal`/`faced-arsenal`."""
    if collection.empty:
        typer.echo("No pitches found for the given filters.")
        return

    summary = collection.pitch_metrics()
    summary["whiff_rate"] = collection.whiff_rate(by_pitch_type=True)
    # NaN where a pitch type never landed outside the zone, which is the
    # honest answer: there were no chances to chase it.
    summary["chase_rate"] = collection.chase_rate(by_pitch_type=True)

    with pd.option_context("display.float_format", "{:.1f}".format):
        typer.echo(summary.to_string())


def _save_zone_plot(
    collection: PitchCollection,
    *,
    kind: str,
    color_by: str,
    split_by: str | None,
    grid: bool,
    bw_method: float | None,
    out: str,
) -> None:
    """Shared body of `zone`/`faced-zone`."""
    if collection.empty:
        _fail("No pitches found for the given filters.")

    try:
        collection.plot_zone(
            kind=kind,
            color_by=None if color_by.lower() == "none" else color_by,
            split_by=split_by,
            grid=grid,
            bw_method=bw_method,
            out=out,
        )
    except ValueError as exc:
        _fail(str(exc))
    except OSError as exc:
        _fail(f"Could not save plot to {out!r}: {exc.strerror or exc}")
    typer.echo(f"Saved plot of {len(collection)} pitch(es) to {out}")


def _save_videos(collection: PitchCollection, *, out_dir: str, limit: int | None) -> None:
    """Shared body of `video`/`faced-video`."""
    from mound.video import download_videos

    if collection.empty:
        _fail("No pitches found for the given filters.")

    if limit is not None:
        collection = collection.limit(limit)

    try:
        saved = download_videos(collection, out_dir=out_dir)
    except OSError as exc:
        _fail(f"Could not save clips to {out_dir!r}: {exc.strerror or exc}")
    typer.echo(f"Saved {len(saved)} of {len(collection)} clip(s) to {out_dir}")


@app.command()
def search(
    name: str = typer.Argument(..., help="Player name to search for, e.g. 'Roki Sasaki'"),
) -> None:
    """Find a player's MLB ID and basic info by name."""
    from mound.players import search_players

    matches = search_players(name)
    if not matches:
        _fail(f"No player found matching '{name}'")

    for player in matches:
        role = player.primary_position or "?"
        team = player.team_name or "no current team"
        typer.echo(f"{player.id}\t{player.full_name}\t{role}\t{team}")


@app.command()
def pitches(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    zone: str | None = typer.Option(
        None,
        "--zone",
        help="Statcast zone numbers: 1-9 in the strike zone, 11-14 outside, e.g. '5' or '11,12'",
    ),
    ends_at_bat: bool = typer.Option(
        False,
        "--ends-at-bat",
        help="Only the pitch each at-bat ended on, one row per plate appearance",
    ),
    export_path: str | None = typer.Option(None, "--export", help="Path to export results to"),
    export_format: str | None = typer.Option(
        None, "--format", help="Export format (csv/json/parquet); inferred from --export if omitted"
    ),
    limit: int | None = typer.Option(20, "--limit", help="Rows to print (use 0 for all)"),
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Retrieve individual pitch records for a pitcher."""
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )

    _print_pitches(
        collection,
        zone=zone,
        ends_at_bat=ends_at_bat,
        limit=limit,
        export_path=export_path,
        export_format=export_format,
    )


@app.command()
def faced(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    zone: str | None = typer.Option(
        None,
        "--zone",
        help="Statcast zone numbers: 1-9 in the strike zone, 11-14 outside, e.g. '5' or '11,12'",
    ),
    ends_at_bat: bool = typer.Option(
        False,
        "--ends-at-bat",
        help="Only the pitch each at-bat ended on, one row per plate appearance",
    ),
    export_path: str | None = typer.Option(None, "--export", help="Path to export results to"),
    export_format: str | None = typer.Option(
        None, "--format", help="Export format (csv/json/parquet); inferred from --export if omitted"
    ),
    limit: int | None = typer.Option(20, "--limit", help="Rows to print (use 0 for all)"),
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Retrieve the pitches a batter faced, from every pitcher who threw them.

    The mirror image of `mound pitches`, from the other side of the plate:
    game selection follows the batter's own game log rather than a pitcher's
    starts, so it costs one Savant response per game *played* rather than
    per start. Add --pitcher to narrow to one matchup -- for a single
    matchup, `mound pitches --batter` is the cheaper way to ask the same
    question, since a starter appears in a fraction of the games a hitter
    plays.
    """
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )

    _print_pitches(
        collection,
        zone=zone,
        ends_at_bat=ends_at_bat,
        limit=limit,
        export_path=export_path,
        export_format=export_format,
    )


@app.command()
def mix(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Calculate a pitcher's pitch mix (usage percentage by pitch type)."""
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_mix(collection)


@app.command(name="faced-mix")
def faced_mix(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Calculate what pitch mix a batter faced (usage percentage by pitch type)."""
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_mix(collection)


@app.command()
def results(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Show pitch counts, strikes/balls and strike rate, broken out by pitch type."""
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_results(collection)


@app.command(name="faced-results")
def faced_results(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Show pitch counts, strikes/balls and strike rate a batter faced, by pitch type."""
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_results(collection)


@app.command()
def arsenal(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Show each pitch type's velocity, spin, movement, whiff and chase rate side by side.

    Meant for "how did this pitch look" questions -- run it once for a single
    outing (--game) and once for a wider range (--last/--since) to see what
    changed, e.g. a splitter's whiff rate or a four-seamer's spin rate. Add
    --batter to scope the whole table to one matchup.
    """
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_arsenal(collection)


@app.command(name="faced-arsenal")
def faced_arsenal(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Show velocity, spin, movement, whiff and chase rate for what a batter faced.

    The batter-side counterpart to `mound arsenal` -- add --pitcher to scope
    the whole table to one matchup, seen from the hitter's side.
    """
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _print_arsenal(collection)


@app.command()
def zone(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    kind: KindOption = "scatter",
    color_by: ColorByOption = "pitch_type",
    split_by: SplitByOption = None,
    grid: GridOption = False,
    bw_method: BwMethodOption = None,
    out: OutOption = "zone.png",
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Plot pitch locations against a theoretical strike zone."""
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _save_zone_plot(
        collection,
        kind=kind,
        color_by=color_by,
        split_by=split_by,
        grid=grid,
        bw_method=bw_method,
        out=out,
    )


@app.command(name="faced-zone")
def faced_zone(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    kind: KindOption = "scatter",
    color_by: ColorByOption = "pitch_type",
    split_by: SplitByOption = None,
    grid: GridOption = False,
    bw_method: BwMethodOption = None,
    out: OutOption = "zone.png",
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Plot the pitch locations a batter faced against a theoretical strike zone."""
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _save_zone_plot(
        collection,
        kind=kind,
        color_by=color_by,
        split_by=split_by,
        grid=grid,
        bw_method=bw_method,
        out=out,
    )


@app.command()
def video(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    batter: BatterOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    out_dir: OutDirOption = "videos",
    limit: VideoLimitOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Download Baseball Savant broadcast clips for a pitcher's pitches.

    Only the clip page's default embedded angle is available this way (in
    practice, the home broadcast feed); pitches with no video coverage are
    skipped with a warning rather than failing the whole batch. Narrow to
    one at-bat with --game/--at-bat, or to one exact pitch by adding
    --pitch-number on top of that.
    """
    collection = _get_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        batter=batter,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _save_videos(collection, out_dir=out_dir, limit=limit)


@app.command(name="faced-video")
def faced_video(
    name: str = typer.Argument(..., help="Batter name or MLB player ID"),
    last: LastOption = None,
    since: SinceOption = None,
    until: UntilOption = None,
    game: GameOption = None,
    pitch: PitchOption = None,
    stand: StandOption = None,
    pitcher: PitcherOption = None,
    at_bat: AtBatOption = None,
    pitch_number: PitchNumberOption = None,
    out_dir: OutDirOption = "videos",
    limit: VideoLimitOption = None,
    cache: CacheOption = False,
    cache_dir: CacheDirOption = None,
) -> None:
    """Download Baseball Savant broadcast clips for the pitches a batter faced.

    Same coverage caveats as `mound video`: only the clip page's default
    embedded angle is available, and pitches with no video coverage are
    skipped with a warning rather than failing the whole batch.
    """
    collection = _get_faced_pitches(
        name,
        last=last,
        since=since,
        until=until,
        game=game,
        pitch=pitch,
        stand=stand,
        pitcher=pitcher,
        at_bat_number=at_bat,
        pitch_number=pitch_number,
        cache=cache,
        cache_dir=cache_dir,
    )
    _save_videos(collection, out_dir=out_dir, limit=limit)


@app.command(name="video-id")
def video_id(
    pitch_id: str = typer.Argument(..., help="A pitch_id/play_id, e.g. from a prior export"),
    out: str | None = typer.Option(
        None, "--out", help="Output file path (default: videos/<pitch_id>.mp4)"
    ),
) -> None:
    """Download a single broadcast clip directly from its pitch_id, no pitcher lookup needed."""
    from mound.video import VideoNotFoundError, download_video_by_id

    try:
        saved = download_video_by_id(pitch_id, out=out)
    except (VideoNotFoundError, requests.RequestException) as exc:
        _fail(f"Failed to download clip for pitch_id={pitch_id!r}: {exc}")
    except OSError as exc:
        _fail(f"Could not save clip to {out!r}: {exc.strerror or exc}")

    typer.echo(f"Saved clip to {saved}")


if __name__ == "__main__":
    app()
