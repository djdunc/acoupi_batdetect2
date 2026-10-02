"""Tests for BatDetect2 Reusable Components."""

import datetime
import zoneinfo

from acoupi import data
from acoupi_batdetect2.components import (
    HasHighConfidenceDetection,
    IsNightTime,
    ModelSeparatedDateFileManager,
)
from acoupi_batdetect2.configuration import BatDetect2_ConfigSchema
from acoupi_batdetect2.program import BatDetect2_Program


def test_is_night_time_midnight_and_noon():
    """Verify should_record() returns True at midnight and False at noon."""
    tz = "Europe/London"
    condition = IsNightTime(
        timezone=tz,
        latitude=51.5074,
        longitude=-0.1278,
        before=datetime.timedelta(minutes=30),
        after=datetime.timedelta(minutes=30),
    )

    # Midnight local time
    midnight = datetime.datetime(2026, 6, 21, 0, 0, 0, tzinfo=zoneinfo.ZoneInfo(tz))
    assert condition.should_record(midnight) is True

    # Noon local time
    noon = datetime.datetime(2026, 6, 21, 12, 0, 0, tzinfo=zoneinfo.ZoneInfo(tz))
    assert condition.should_record(noon) is False

    # Default now (no arguments)
    assert isinstance(condition.should_record(), bool)


def test_is_night_time_buffers():
    """Verify before sunset and after sunrise buffers."""
    tz = "Europe/London"
    condition = IsNightTime(
        timezone=tz,
        latitude=51.5074,
        longitude=-0.1278,
        before=datetime.timedelta(hours=1),
        after=datetime.timedelta(hours=1),
    )

    # 3 AM is night time
    night_time = datetime.datetime(2026, 1, 15, 3, 0, 0, tzinfo=zoneinfo.ZoneInfo(tz))
    assert condition.should_record(night_time) is True

    # 1 PM is day time
    day_time = datetime.datetime(2026, 1, 15, 13, 0, 0, tzinfo=zoneinfo.ZoneInfo(tz))
    assert condition.should_record(day_time) is False


def test_program_get_recording_conditions(
    microphone_config,
    messaging_config,
    celery_app,
):
    """Verify BatDetect2_Program registers IsNightTime condition."""
    schema = BatDetect2_ConfigSchema(
        microphone=microphone_config,
        messaging=messaging_config,
    )
    program = BatDetect2_Program(program_config=schema, app=celery_app)
    conditions = program.get_recording_conditions(schema)

    assert len(conditions) == 1
    assert isinstance(conditions[0], IsNightTime)


def test_has_high_confidence_detection_filter():
    filter_ = HasHighConfidenceDetection(model_name="BatDetect2", threshold=0.6)

    rec = data.Recording(
        path="dummy.wav",
        duration=3.0,
        samplerate=192000,
        created_on=datetime.datetime.now(datetime.timezone.utc),
        deployment=data.Deployment(name="test"),
    )

    # Below threshold detection
    low_output = data.ModelOutput(
        name_model="BatDetect2",
        recording=rec,
        detections=[
            data.Detection(
                prediction_type=getattr(data.PredictionType, "EVENT", "event") if hasattr(data, "PredictionType") else "event",
                detection_score=0.4,
                location=data.BoundingBox.from_coordinates(0.0, 10000.0, 0.1, 20000.0),
                tags=[],
            )
        ],
    )
    assert filter_.should_save_recording(rec, [low_output]) is False

    # Above threshold detection
    high_output = data.ModelOutput(
        name_model="BatDetect2",
        recording=rec,
        detections=[
            data.Detection(
                prediction_type=getattr(data.PredictionType, "EVENT", "event") if hasattr(data, "PredictionType") else "event",
                detection_score=0.8,
                location=data.BoundingBox.from_coordinates(0.0, 10000.0, 0.1, 20000.0),
                tags=[],
            )
        ],
    )
    assert filter_.should_save_recording(rec, [high_output]) is True


def test_model_separated_date_file_manager(tmp_path):
    manager = ModelSeparatedDateFileManager(directory=tmp_path)
    dt = datetime.datetime(2026, 7, 15, 23, 30, 0, tzinfo=datetime.timezone.utc)

    # Bat ultrasonic sample rate
    bat_rec = data.Recording(
        path="orig.wav",
        duration=3.0,
        samplerate=192000,
        created_on=dt,
        deployment=data.Deployment(name="test"),
    )
    bat_path = manager.get_file_path(bat_rec)
    assert str(tmp_path) in str(bat_path)
    assert "bats" in str(bat_path)
    assert "2026/07/15" in str(bat_path)

    # Bird audio sample rate
    bird_rec = data.Recording(
        path="orig.wav",
        duration=3.0,
        samplerate=48000,
        created_on=dt,
        deployment=data.Deployment(name="test"),
    )
    bird_path = manager.get_file_path(bird_rec)
    assert str(tmp_path) in str(bird_path)
    assert "birds" in str(bird_path)
    assert "2026/07/15" in str(bird_path)

    # Also test default directory initialization
    default_manager = ModelSeparatedDateFileManager()
    default_path = default_manager.get_file_path(bat_rec)
    assert "bats" in str(default_path)

