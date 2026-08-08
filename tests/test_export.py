from __future__ import annotations

import json

import pandas as pd
import pytest

from mound.models import Pitch
from mound.pitches import PitchCollection


def _sample_collection() -> PitchCollection:
    pitch = Pitch(
        game_pk=1001,
        game_date="2025-07-10",
        pitch_id="abc-123",
        at_bat_number=1,
        pitch_number=1,
        inning=1,
        half_inning="top",
        pitcher_id=808963,
        pitcher_name="Roki Sasaki",
        batter_id=1,
        batter_name="Test Batter",
        batter_stand="L",
        pitch_type_code="FS",
        pitch_type="splitter",
        velocity=89.0,
        plate_x=-0.5,
        plate_z=1.8,
        sz_top=3.4,
        sz_bot=1.6,
        in_zone=True,
        balls=0,
        strikes=1,
        pitch_call="swinging_strike",
        call_description="Swinging Strike",
        is_strike=True,
        at_bat_result=None,
        description=None,
    )
    return PitchCollection([pitch])


def test_to_csv_round_trip(tmp_path):
    collection = _sample_collection()
    out_path = tmp_path / "pitches.csv"

    collection.to_csv(str(out_path))

    assert out_path.exists()
    df = pd.read_csv(out_path)
    assert len(df) == 1
    assert df.loc[0, "pitch_type"] == "splitter"


def test_to_json_round_trip(tmp_path):
    collection = _sample_collection()
    out_path = tmp_path / "pitches.json"

    collection.to_json(str(out_path))

    records = json.loads(out_path.read_text())
    assert len(records) == 1
    assert records[0]["pitch_type_code"] == "FS"


def test_to_parquet_round_trip(tmp_path):
    pytest.importorskip("pyarrow")
    collection = _sample_collection()
    out_path = tmp_path / "pitches.parquet"

    collection.to_parquet(str(out_path))

    df = pd.read_parquet(out_path)
    assert len(df) == 1
    assert df.loc[0, "pitch_type"] == "splitter"


def test_export_infers_format_from_extension(tmp_path):
    collection = _sample_collection()
    out_path = tmp_path / "pitches.csv"

    collection.export(str(out_path))

    assert out_path.exists()


def test_export_unsupported_format_raises(tmp_path):
    collection = _sample_collection()

    with pytest.raises(ValueError):
        collection.export(str(tmp_path / "pitches.xyz"))


def test_export_creates_parent_directories(tmp_path):
    collection = _sample_collection()
    nested_path = tmp_path / "nested" / "dir" / "pitches.csv"

    collection.to_csv(str(nested_path))

    assert nested_path.exists()
