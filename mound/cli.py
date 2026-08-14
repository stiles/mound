"""Mound's command-line interface.

    mound search "Roki Sasaki"
    mound pitches "Roki Sasaki" --last 4 --pitch splitter
    mound mix "Roki Sasaki" --last 4
    mound results "Roki Sasaki" --last 4 --pitch splitter
    mound arsenal "Roki Sasaki" --game 825051
    mound arsenal "Roki Sasaki" --last 8 --batter "Shohei Ohtani"
    mound zone "Roki Sasaki" --pitch splitter --last 4 --out zone.png
    mound zone "Roki Sasaki" --last 8 --split-by stand --out zone.png
    mound video "Roki Sasaki" --pitch splitter --last 4 --out-dir clips
    mound video "Roki Sasaki" --pitch splitter --last 1 --limit 1
    mound video "Roki Sasaki" --game 717404 --at-bat 34 --pitch-number 3
    mound video-id 7468ecb9-0918-3aca-8ef5-6396e6ab80c3
"""

from __future__ import annotations

from typing import Annotated, NoReturn

import pandas as pd
import requests
import typer

from mound import __version__
from mound.pitches import PitchCollection, Pitcher
from mound.players import AmbiguousPlayerError, PlayerNotFoundError

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

    if collection.empty:
        typer.echo("No pitches found for the given filters.")
    else:
        df = collection.to_frame()
        display_cols = [
            "game_date",
            "inning",
            "pitch_type",
            "velocity",
            "pitch_call",
            "at_bat_result",
        ]
        display_df = df[display_cols]
        if limit:
            display_df = display_df.head(limit)
        typer.echo(display_df.to_string(index=False))
        typer.echo(f"\n{len(collection)} pitch(es) total.")

    if export_path:
        try:
            collection.export(export_path, format=export_format)
        except OSError as exc:
            _fail(f"Could not export to {export_path!r}: {exc.strerror or exc}")
        typer.echo(f"Exported {len(collection)} pitch(es) to {export_path}")


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

    if collection.empty:
        typer.echo("No pitches found for the given filters.")
        return

    mix_series = collection.pitch_mix()
    for pitch_type, pct in mix_series.items():
        typer.echo(f"{pitch_type:<24} {pct:>5.1f}%")


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
    kind: str = typer.Option(
        "scatter", "--kind", help="'scatter', 'heatmap', or 'kde' (requires mound[viz])"
    ),
    split_by: str | None = typer.Option(
        None, "--split-by", help="Facet into side-by-side panels, e.g. 'stand'"
    ),
    bw_method: float | None = typer.Option(
        None, "--bw-method", help="Bandwidth for --kind kde (default: scipy's own heuristic)"
    ),
    out: str = typer.Option("zone.png", "--out", help="Output image path"),
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

    if collection.empty:
        _fail("No pitches found for the given filters.")

    try:
        collection.plot_zone(kind=kind, split_by=split_by, bw_method=bw_method, out=out)
    except OSError as exc:
        _fail(f"Could not save plot to {out!r}: {exc.strerror or exc}")
    typer.echo(f"Saved plot of {len(collection)} pitch(es) to {out}")


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
    out_dir: str = typer.Option("videos", "--out-dir", help="Directory to save clips to"),
    limit: int | None = typer.Option(
        None, "--limit", help="Download at most N clips (e.g. --limit 1 for a single video)"
    ),
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
    from mound.video import download_videos

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

    if collection.empty:
        _fail("No pitches found for the given filters.")

    if limit is not None:
        collection = collection.limit(limit)

    try:
        saved = download_videos(collection, out_dir=out_dir)
    except OSError as exc:
        _fail(f"Could not save clips to {out_dir!r}: {exc.strerror or exc}")
    typer.echo(f"Saved {len(saved)} of {len(collection)} clip(s) to {out_dir}")


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
