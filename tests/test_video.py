from __future__ import annotations

from pathlib import Path

import pytest
import responses as responses_lib

from mound.models import Pitch
from mound.pitches import PitchCollection
from mound.video import (
    VideoNotFoundError,
    _extract_mp4_url,
    clip_page_url,
    download_video,
    download_video_by_id,
    download_videos,
    resolve_video_url,
)
from tests.conftest import load_text_fixture

PITCH_ID = "9db90f1b-bd15-31d7-84db-004f6a35379e"
MP4_URL = (
    "https://sporty-clips.mlb.com/"
    "NHl6T09fWGw0TUFRPT1fRDFVRFhWUlNWMUFBV2dZRFV3QUhBRkpSQUZrQkJ3TUFBbFVCVmdWVUFnWldCd3NE.mp4"
)


def _pitch(pitch_id: str | None) -> Pitch:
    return Pitch(
        game_pk=825051,
        game_date="2026-08-07",
        pitch_id=pitch_id,
        at_bat_number=1,
        pitch_number=1,
        inning=1,
        half_inning="bottom",
        pitcher_id=808963,
        pitcher_name="Roki Sasaki",
        batter_id=1,
        batter_name="Geraldo Perdomo",
        batter_stand="L",
        pitch_type_code="FS",
        pitch_type="splitter",
        velocity=90.9,
        plate_x=-1.5,
        plate_z=3.5,
        sz_top=3.3,
        sz_bot=1.6,
        in_zone=False,
        balls=1,
        strikes=2,
        pitch_call="ball",
        call_description="Ball",
        is_strike=False,
        is_swing=False,
        is_whiff=False,
        at_bat_result=None,
        description=None,
    )


def test_clip_page_url_builds_expected_url():
    assert clip_page_url(PITCH_ID) == (
        f"https://baseballsavant.mlb.com/sporty-videos?playId={PITCH_ID}"
    )


def test_extract_mp4_url_finds_source_src():
    html = load_text_fixture("savant_clip_page.html")

    assert _extract_mp4_url(html) == MP4_URL


def test_extract_mp4_url_returns_none_when_absent():
    html = load_text_fixture("savant_clip_page_no_video.html")

    assert _extract_mp4_url(html) is None


def test_resolve_video_url_returns_mp4_url(mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )

    assert resolve_video_url(PITCH_ID) == MP4_URL


def test_resolve_video_url_raises_when_no_clip(mocked_responses):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page_no_video.html"),
        status=200,
    )

    with pytest.raises(VideoNotFoundError):
        resolve_video_url(PITCH_ID)


def test_download_video_saves_mp4_bytes(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET,
        MP4_URL,
        body=b"fake-mp4-bytes",
        status=200,
        content_type="video/mp4",
    )

    out_path = tmp_path / "clip.mp4"
    saved = download_video(_pitch(PITCH_ID), out=out_path)

    assert saved == out_path
    assert out_path.read_bytes() == b"fake-mp4-bytes"


def test_download_video_creates_parent_directories(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )

    out_path = tmp_path / "nested" / "dir" / "clip.mp4"
    download_video(_pitch(PITCH_ID), out=out_path)

    assert out_path.exists()


def test_download_video_without_pitch_id_raises():
    with pytest.raises(VideoNotFoundError):
        download_video(_pitch(None))


def test_download_video_by_id_saves_mp4_bytes(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )

    out_path = tmp_path / "clip.mp4"
    saved = download_video_by_id(PITCH_ID, out=out_path)

    assert saved == out_path
    assert out_path.read_bytes() == b"fake-mp4-bytes"


def test_download_video_by_id_defaults_out_path(mocked_responses, tmp_path, monkeypatch):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )
    monkeypatch.chdir(tmp_path)

    saved = download_video_by_id(PITCH_ID)

    assert saved == Path("videos") / f"{PITCH_ID}.mp4"
    assert saved.resolve() == tmp_path / "videos" / f"{PITCH_ID}.mp4"


def test_download_video_by_id_without_pitch_id_raises():
    with pytest.raises(VideoNotFoundError):
        download_video_by_id("")


def test_download_videos_skips_pitches_without_pitch_id(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )
    collection = PitchCollection([_pitch(None), _pitch(PITCH_ID)])

    saved = download_videos(collection, out_dir=tmp_path)

    assert len(saved) == 1
    assert saved[0] == tmp_path / f"{PITCH_ID}.mp4"


def test_download_videos_skips_failures_by_default(mocked_responses, tmp_path, capsys):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page_no_video.html"),
        status=200,
    )
    collection = PitchCollection([_pitch(PITCH_ID)])

    saved = download_videos(collection, out_dir=tmp_path)

    assert saved == []
    assert "Warning" in capsys.readouterr().out


def test_download_videos_raises_when_skip_errors_false(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page_no_video.html"),
        status=200,
    )
    collection = PitchCollection([_pitch(PITCH_ID)])

    with pytest.raises(VideoNotFoundError):
        download_videos(collection, out_dir=tmp_path, skip_errors=False)


def test_pitch_download_video_delegates(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )

    out_path = tmp_path / "clip.mp4"
    saved = _pitch(PITCH_ID).download_video(out=out_path)

    assert saved == out_path


def test_pitch_collection_download_videos_delegates(mocked_responses, tmp_path):
    mocked_responses.add(
        responses_lib.GET,
        clip_page_url(PITCH_ID),
        body=load_text_fixture("savant_clip_page.html"),
        status=200,
    )
    mocked_responses.add(
        responses_lib.GET, MP4_URL, body=b"fake-mp4-bytes", status=200, content_type="video/mp4"
    )
    collection = PitchCollection([_pitch(PITCH_ID)])

    saved = collection.download_videos(out_dir=tmp_path)

    assert len(saved) == 1
