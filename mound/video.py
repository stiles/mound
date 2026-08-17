"""Download a pitch's broadcast clip from Baseball Savant.

Each pitch's ``pitch_id`` (Statcast's ``play_id``) doubles as the ``playId``
on a Baseball Savant clip page (``/sporty-videos?playId=<pitch_id>``). That
page embeds a direct ``.mp4`` URL for the pitch's default broadcast angle in
a plain ``<video><source src="...">`` tag, so a small regex is enough to
pull it out -- no need for a full HTML parser for one tag.

Only the page's default embedded angle is captured (in practice, the "HOME
Broadcast" feed). The page's "AWAY Broadcast" toggle swaps in a second clip
via client-side JavaScript rather than a second tag present in the initial
HTML, so it isn't available to a plain HTTP fetch.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from mound import config
from mound.http import get_session

if TYPE_CHECKING:
    from mound.models import Pitch
    from mound.pitches import PitchCollection

CLIP_PAGE_URL = f"{config.SAVANT_BASE}/sporty-videos"

_MP4_SOURCE_RE = re.compile(r'<source\s+src="([^"]+\.mp4)"', re.IGNORECASE)


class VideoNotFoundError(RuntimeError):
    """Raised when a pitch has no discoverable broadcast clip."""


def clip_page_url(pitch_id: str) -> str:
    """The Baseball Savant clip page URL for a given ``pitch_id``."""
    return f"{CLIP_PAGE_URL}?playId={pitch_id}"


def _extract_mp4_url(page: str) -> str | None:
    match = _MP4_SOURCE_RE.search(page)
    if match is None:
        return None
    # The URL ends in a base64 blob, and Savant escapes its `=` padding as
    # `&#x3D;` in the attribute. Fetching that literally is a 404.
    return html.unescape(match.group(1))


def resolve_video_url(pitch_id: str) -> str:
    """Return the direct ``.mp4`` URL for a pitch's default broadcast clip.

    Raises :class:`VideoNotFoundError` if the clip page has no embedded
    video (e.g. an invalid ``pitch_id``, or a pitch predating Savant's video
    coverage).
    """
    response = get_session().get(clip_page_url(pitch_id), timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()

    mp4_url = _extract_mp4_url(response.text)
    if mp4_url is None:
        raise VideoNotFoundError(f"No broadcast clip found for pitch_id={pitch_id!r}")
    return mp4_url


def download_video_by_id(pitch_id: str, out: str | Path | None = None) -> Path:
    """Download a broadcast clip directly from its ``pitch_id``, with no ``Pitch`` needed.

    Useful when you already have a ``pitch_id`` on hand (e.g. from an earlier
    export) and don't want to re-retrieve the pitcher/game just to look up
    the same pitch again. Defaults to ``videos/<pitch_id>.mp4`` when ``out``
    is omitted.
    """
    if not pitch_id:
        raise VideoNotFoundError("No pitch_id given to look up a clip for")

    out_path = Path(out) if out is not None else Path("videos") / f"{pitch_id}.mp4"
    mp4_url = resolve_video_url(pitch_id)

    response = get_session().get(mp4_url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path


def download_video(pitch: Pitch, out: str | Path | None = None) -> Path:
    """Download one pitch's broadcast clip, returning the path it was saved to.

    Defaults to ``videos/<pitch_id>.mp4`` when ``out`` is omitted.
    """
    if not pitch.pitch_id:
        raise VideoNotFoundError("Pitch has no pitch_id to look up a clip for")

    return download_video_by_id(pitch.pitch_id, out=out)


def download_videos(
    collection: PitchCollection, out_dir: str | Path = "videos", skip_errors: bool = True
) -> list[Path]:
    """Download broadcast clips for every pitch in ``collection`` with a ``pitch_id``.

    Returns the paths successfully saved. Pitches with no ``pitch_id`` are
    silently skipped. By default, a clip that fails to resolve or download
    (e.g. no video coverage for that pitch) is skipped with a printed
    warning rather than aborting the whole batch; pass ``skip_errors=False``
    to raise on the first failure instead.
    """
    out_dir = Path(out_dir)
    saved: list[Path] = []

    for pitch in collection:
        if not pitch.pitch_id:
            continue
        try:
            saved.append(download_video(pitch, out=out_dir / f"{pitch.pitch_id}.mp4"))
        except (VideoNotFoundError, requests.RequestException) as exc:
            if not skip_errors:
                raise
            print(f"Warning: failed to download video for pitch_id={pitch.pitch_id}: {exc}")

    return saved
