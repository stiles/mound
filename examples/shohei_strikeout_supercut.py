"""Stitch every Ohtani strikeout in one window into a single labeled video.

The last step of docs/examples/ohtani-spin-chase.md, taken further: rather
than downloading a clip per pitch and opening them one at a time, this pulls
the pitch each strikeout ended on, labels each clip with who threw it, what
it was and where it went, and concatenates the lot into one file.

Mound handles the data and the downloads. The stitching is ffmpeg, which
has to be on PATH:

    brew install ffmpeg

Each clip is re-encoded before being joined, because Savant's clips share a
resolution but not a frame rate (some 60, some 120), and the concat demuxer
needs its inputs to match. Labels sit bottom-left, since MLB broadcasts put
their score bug bottom-right.

Requires network access (hits the live MLB Stats API and Baseball Savant).
Clips land in examples/output/clips/ and are reused on later runs.

    python examples/shohei_strikeout_supercut.py
    python examples/shohei_strikeout_supercut.py --spin-away   # the 8 chases
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from mound import Batter
from mound.models import Pitch
from mound.video import VideoNotFoundError, download_video
from mound.viz import BACKGROUND, DEFAULT_PITCH_COLOR, FAINT, INK, MUTED, PITCH_TYPE_COLORS

OUTPUT_DIR = Path(__file__).parent / "output"
CLIP_DIR = OUTPUT_DIR / "clips"

GAMES = 20
SPIN = ["slider", "sweeper", "slurve", "curveball", "knuckle curve", "changeup", "splitter"]
AWAY_OFF_PLATE = (11, 13)

WIDTH, HEIGHT, FPS = 1280, 720, 60
TITLE_SECONDS = 3
# The card is paper rather than a dark scrim so the pitch-type colors keep
# their chart meaning: they're chosen to read on white. Bottom-left, because
# MLB broadcasts put their score bug bottom-right -- though which corner
# carries the network logo varies, so nothing goes at the top.
CARD_WIDTH, CARD_HEIGHT = 700, 150
CARD_TOP = HEIGHT - CARD_HEIGHT
PAD = 44


def rgb(hex_color: str) -> str:
    """Video wants 0xRRGGBB where matplotlib wants #RRGGBB."""
    return f"0x{hex_color.lstrip('#')}"


def ffmpeg(*args: str) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        check=True,
    )


def font(weight: str) -> str:
    """A drawtext font option, preferring Inter to match the charts.

    Falls back to whatever fontconfig calls "Sans" when Inter isn't
    installed, so this doesn't hard-code a macOS font path.
    """
    family = f"Inter {weight}" if weight else "Inter"
    if shutil.which("fc-match"):
        matched = subprocess.run(
            ["fc-match", "--format", "%{family}", family],
            capture_output=True,
            text=True,
            check=False,
        )
        if "Inter" in matched.stdout:
            return f"font='{family}'"
    return "font='Sans'"


def pitch_color(pitch_type: str | None) -> str:
    return rgb(PITCH_TYPE_COLORS.get(pitch_type or "", DEFAULT_PITCH_COLOR))


def text_layer(path: Path, *, x: int | str, y: int, size: int, color: str, weight: str) -> str:
    return (
        f"drawtext=textfile='{path}':{font(weight)}:x={x}:y={y}:fontsize={size}:fontcolor={color}"
    )


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def pretty_date(game_date: str | None) -> str:
    if not game_date:
        return ""
    return date.fromisoformat(game_date).strftime("%b %-d")


def label_clip(clip: Path, pitch: Pitch, index: int, total: int, work: Path) -> Path:
    """Re-encode one clip to the shared format, with its pitch written on it."""
    stem = work / f"{index:02d}"
    who = write(stem.with_suffix(".who.txt"), pitch.pitcher_name or "")
    what = write(
        stem.with_suffix(".what.txt"),
        f"{pitch.pitch_type} \u00b7 {pitch.velocity:.1f} mph \u00b7 zone {pitch.zone}",
    )
    meta = write(
        stem.with_suffix(".meta.txt"),
        f"{pretty_date(pitch.game_date)} \u00b7 {(pitch.pitch_call or '').replace('_', ' ')}",
    )
    counter = write(stem.with_suffix(".count.txt"), f"{index} / {total}")

    filters = ",".join(
        [
            f"scale={WIDTH}:{HEIGHT}",
            "setsar=1",
            f"fps={FPS}",
            f"drawbox=x=0:y={CARD_TOP}:w={CARD_WIDTH}:h={CARD_HEIGHT}"
            f":color={rgb(BACKGROUND)}@0.9:t=fill",
            text_layer(who, x=PAD, y=CARD_TOP + 20, size=34, color=rgb(INK), weight="SemiBold"),
            # The pitch type in the color the charts give it.
            text_layer(
                what,
                x=PAD,
                y=CARD_TOP + 64,
                size=26,
                color=pitch_color(pitch.pitch_type),
                weight="Medium",
            ),
            text_layer(meta, x=PAD, y=CARD_TOP + 102, size=21, color=rgb(MUTED), weight=""),
            # Right-aligned inside the card, so it can't land under whichever
            # corner this broadcast puts its logo in.
            text_layer(
                counter,
                x=f"{CARD_WIDTH - PAD}-text_w",
                y=CARD_TOP + 28,
                size=22,
                color=rgb(FAINT),
                weight="Medium",
            ),
            "format=yuv420p",
        ]
    )

    out = stem.with_suffix(".mp4")
    ffmpeg(
        "-i", str(clip),
        "-vf", filters,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        str(out),
    )  # fmt: skip
    return out


def title_card(headline: str, subtitle: str, work: Path) -> Path:
    """A paper slate in the charts' typography, down to the source line."""
    head = write(work / "title.txt", headline)
    sub = write(work / "subtitle.txt", subtitle)
    source = write(
        work / "source.txt", "Source: MLB broadcast clips via Baseball Savant, stitched with Mound"
    )

    filters = ",".join(
        [
            text_layer(
                head, x=88, y=HEIGHT // 2 - 70, size=52, color=rgb(INK), weight="SemiBold"
            ),
            text_layer(sub, x=88, y=HEIGHT // 2 + 10, size=28, color=rgb(MUTED), weight=""),
            text_layer(source, x=88, y=HEIGHT - 70, size=18, color=rgb(FAINT), weight=""),
            "format=yuv420p",
        ]
    )  # fmt: skip

    out = work / "00.mp4"
    ffmpeg(
        "-f", "lavfi", "-i", f"color=c={rgb(BACKGROUND)}:s={WIDTH}x{HEIGHT}:r={FPS}",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(TITLE_SECONDS),
        "-vf", filters,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        str(out),
    )  # fmt: skip
    return out


def concat(parts: list[Path], out: Path, work: Path) -> None:
    listing = work / "parts.txt"
    listing.write_text("".join(f"file '{part}'\n" for part in parts), encoding="utf-8")
    ffmpeg(
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", "-movflags", "+faststart", str(out),
    )  # fmt: skip


def clip_for(pitch: Pitch) -> Path | None:
    """The clip for one pitch, downloaded unless it's already on disk."""
    path = CLIP_DIR / f"{pitch.pitch_id}.mp4"
    if path.exists():
        return path
    try:
        return download_video(pitch, out=path)
    except VideoNotFoundError as exc:
        print(f"  no clip: {pretty_date(pitch.game_date)} {pitch.pitcher_name} -- {exc}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--spin-away",
        action="store_true",
        help="only the strikeouts on breaking or offspeed pitches away and off the plate",
    )
    parser.add_argument("--out", default=None, help="where to write the finished video")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is not on PATH; install it with `brew install ffmpeg`")

    CLIP_DIR.mkdir(parents=True, exist_ok=True)

    ohtani = Batter("Shohei Ohtani")
    faced = ohtani.pitches(last=GAMES, cache=True)
    strikeouts = [
        p
        for p in faced.filter(ends_at_bat=True)
        if "Strikeout" in (p.at_bat_result or "")
        and (not args.spin_away or (p.zone in AWAY_OFF_PLATE and p.pitch_type in SPIN))
    ]
    strikeouts.sort(key=lambda p: (p.game_date or "", p.at_bat_number or 0))
    if not strikeouts:
        print("No strikeouts found.")
        return

    span = f"{pretty_date(strikeouts[0].game_date)}\u2013{pretty_date(strikeouts[-1].game_date)}"
    print(f"{len(strikeouts)} strikeouts, {span}. Fetching clips:")

    clips = [(pitch, clip_for(pitch)) for pitch in strikeouts]
    found = [(pitch, clip) for pitch, clip in clips if clip is not None]
    print(f"  {len(found)} of {len(clips)} clips available")

    out = (
        Path(args.out)
        if args.out
        else OUTPUT_DIR
        / ("ohtani_spin_away_strikeouts.mp4" if args.spin_away else "ohtani_strikeouts.mp4")
    )

    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        headline = "Ohtani, chasing spin away" if args.spin_away else "Ohtani, every strikeout"
        parts = [
            title_card(headline, f"{len(found)} strikeouts \u00b7 {span}, 2026", work),
        ]
        for index, (pitch, clip) in enumerate(found, start=1):
            print(f"  labeling {index}/{len(found)}: {pitch.pitcher_name}, {pitch.pitch_type}")
            parts.append(label_clip(clip, pitch, index, len(found), work))

        concat(parts, out, work)

    print(f"\nSaved {len(found)} clips as one video: {out}")


if __name__ == "__main__":
    main()
