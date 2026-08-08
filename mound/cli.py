"""Mound's command-line interface.

    mound search "Roki Sasaki"
    mound pitches "Roki Sasaki" --last 4 --pitch splitter
    mound mix "Roki Sasaki" --last 4
    mound results "Roki Sasaki" --last 4 --pitch splitter
    mound zone "Roki Sasaki" --pitch splitter --last 4 --out zone.png
    mound zone "Roki Sasaki" --last 8 --split-by stand --out zone.png
    mound video "Roki Sasaki" --pitch splitter --last 4 --out-dir clips
"""

from __future__ import annotations

import pandas as pd
import typer

from mound.pitches import PitchCollection, Pitcher
from mound.players import AmbiguousPlayerError, PlayerNotFoundError

app = typer.Typer(
    name="mound",
    help="Retrieve, analyze and visualize MLB pitch-level data.",
    no_args_is_help=True,
)


def _fail(message: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


CACHE_OPTION = typer.Option(
    False, "--cache", help="Cache Savant game-feed responses locally to speed up repeat queries"
)
CACHE_DIR_OPTION = typer.Option(
    None, "--cache-dir", help="Custom cache directory (implies --cache)"
)


def _get_pitches(
    name: str,
    last: int | None,
    since: str | None,
    until: str | None,
    game: int | None,
    pitch: str | None,
    stand: str | None = None,
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
    last: int | None = typer.Option(None, "--last", help="Most recent N appearances"),
    since: str | None = typer.Option(None, "--since", help="Start date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    game: int | None = typer.Option(None, "--game", help="A specific MLB game_pk"),
    pitch: str | None = typer.Option(None, "--pitch", help="Pitch type, e.g. 'splitter'"),
    stand: str | None = typer.Option(None, "--stand", help="Batter side ('L' or 'R')"),
    export_path: str | None = typer.Option(None, "--export", help="Path to export results to"),
    export_format: str | None = typer.Option(
        None, "--format", help="Export format (csv/json/parquet); inferred from --export if omitted"
    ),
    limit: int | None = typer.Option(20, "--limit", help="Rows to print (use 0 for all)"),
    cache: bool = CACHE_OPTION,
    cache_dir: str | None = CACHE_DIR_OPTION,
) -> None:
    """Retrieve individual pitch records for a pitcher."""
    collection = _get_pitches(name, last, since, until, game, pitch, stand, cache, cache_dir)

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
        collection.export(export_path, format=export_format)
        typer.echo(f"Exported {len(collection)} pitch(es) to {export_path}")


@app.command()
def mix(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: int | None = typer.Option(None, "--last", help="Most recent N appearances"),
    since: str | None = typer.Option(None, "--since", help="Start date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    game: int | None = typer.Option(None, "--game", help="A specific MLB game_pk"),
    pitch: str | None = typer.Option(None, "--pitch", help="Pitch type, e.g. 'splitter'"),
    stand: str | None = typer.Option(None, "--stand", help="Batter side ('L' or 'R')"),
    cache: bool = CACHE_OPTION,
    cache_dir: str | None = CACHE_DIR_OPTION,
) -> None:
    """Calculate a pitcher's pitch mix (usage percentage by pitch type)."""
    collection = _get_pitches(name, last, since, until, game, pitch, stand, cache, cache_dir)

    if collection.empty:
        typer.echo("No pitches found for the given filters.")
        return

    mix_series = collection.pitch_mix()
    for pitch_type, pct in mix_series.items():
        typer.echo(f"{pitch_type:<24} {pct:>5.1f}%")


@app.command()
def results(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: int | None = typer.Option(None, "--last", help="Most recent N appearances"),
    since: str | None = typer.Option(None, "--since", help="Start date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    game: int | None = typer.Option(None, "--game", help="A specific MLB game_pk"),
    pitch: str | None = typer.Option(None, "--pitch", help="Pitch type, e.g. 'splitter'"),
    stand: str | None = typer.Option(None, "--stand", help="Batter side ('L' or 'R')"),
    cache: bool = CACHE_OPTION,
    cache_dir: str | None = CACHE_DIR_OPTION,
) -> None:
    """Show pitch counts, strikes/balls and strike rate, broken out by pitch type."""
    collection = _get_pitches(name, last, since, until, game, pitch, stand, cache, cache_dir)

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
def zone(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: int | None = typer.Option(None, "--last", help="Most recent N appearances"),
    since: str | None = typer.Option(None, "--since", help="Start date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    game: int | None = typer.Option(None, "--game", help="A specific MLB game_pk"),
    pitch: str | None = typer.Option(None, "--pitch", help="Pitch type, e.g. 'splitter'"),
    stand: str | None = typer.Option(None, "--stand", help="Batter side ('L' or 'R')"),
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
    cache: bool = CACHE_OPTION,
    cache_dir: str | None = CACHE_DIR_OPTION,
) -> None:
    """Plot pitch locations against a theoretical strike zone."""
    collection = _get_pitches(name, last, since, until, game, pitch, stand, cache, cache_dir)

    if collection.empty:
        _fail("No pitches found for the given filters.")

    collection.plot_zone(kind=kind, split_by=split_by, bw_method=bw_method, out=out)
    typer.echo(f"Saved plot of {len(collection)} pitch(es) to {out}")


@app.command()
def video(
    name: str = typer.Argument(..., help="Pitcher name or MLB player ID"),
    last: int | None = typer.Option(None, "--last", help="Most recent N appearances"),
    since: str | None = typer.Option(None, "--since", help="Start date (YYYY-MM-DD)"),
    until: str | None = typer.Option(None, "--until", help="End date (YYYY-MM-DD)"),
    game: int | None = typer.Option(None, "--game", help="A specific MLB game_pk"),
    pitch: str | None = typer.Option(None, "--pitch", help="Pitch type, e.g. 'splitter'"),
    stand: str | None = typer.Option(None, "--stand", help="Batter side ('L' or 'R')"),
    out_dir: str = typer.Option("videos", "--out-dir", help="Directory to save clips to"),
    cache: bool = CACHE_OPTION,
    cache_dir: str | None = CACHE_DIR_OPTION,
) -> None:
    """Download Baseball Savant broadcast clips for a pitcher's pitches.

    Only the clip page's default embedded angle is available this way (in
    practice, the home broadcast feed); pitches with no video coverage are
    skipped with a warning rather than failing the whole batch.
    """
    from mound.video import download_videos

    collection = _get_pitches(name, last, since, until, game, pitch, stand, cache, cache_dir)

    if collection.empty:
        _fail("No pitches found for the given filters.")

    saved = download_videos(collection, out_dir=out_dir)
    typer.echo(f"Saved {len(saved)} of {len(collection)} clip(s) to {out_dir}")


if __name__ == "__main__":
    app()
