"""Batdetect2 Program Configuration Options."""

import datetime
import json
from pathlib import Path
from typing import Optional

from acoupi.components import MicrophoneConfig
from acoupi.programs.templates import (
    AudioConfiguration,
    DetectionProgramConfiguration,
    MessagingConfig,
    PathsConfiguration,
)
from pydantic import BaseModel, Field

PROGRAM_CONFIG_PATHS = [
    Path.home() / ".acoupi" / "config" / "program.json",
    Path.home() / ".acoupi" / "config" / "program.conf",
]


def get_saved_program_config() -> dict:
    """Retrieve saved program configuration if available."""
    for config_path in PROGRAM_CONFIG_PATHS:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return {}


def get_default_microphone() -> MicrophoneConfig:
    """Get default microphone configuration, using saved values if present."""
    saved = get_saved_program_config().get("microphone")
    if saved:
        try:
            return MicrophoneConfig(**saved)
        except Exception:
            pass
    return MicrophoneConfig(
        samplerate=192000,
        audio_channels=1,
        device_name="default",
    )


def get_default_paths() -> PathsConfiguration:
    """Get default paths configuration, using saved values if present."""
    saved = get_saved_program_config().get("paths")
    if saved:
        try:
            return PathsConfiguration(**saved)
        except Exception:
            pass
    return PathsConfiguration(
        tmp_audio=Path.home() / ".acoupi" / "tmp",
        recordings=Path.home() / ".acoupi" / "recordings",
        db_metadata=Path.home() / ".acoupi" / "metadata.db",
    )


def get_default_messaging() -> MessagingConfig:
    """Get default messaging configuration, using saved values if present."""
    saved = get_saved_program_config().get("messaging")
    if saved:
        try:
            return MessagingConfig(**saved)
        except Exception:
            pass
    return MessagingConfig(
        messages_db=Path.home() / ".acoupi" / "messages.db",
    )


def get_default_recording() -> "BatDetect2_AudioConfig":
    """Get default recording configuration, using saved values if present."""
    saved = get_saved_program_config().get("recording")
    if saved:
        try:
            return BatDetect2_AudioConfig(**saved)
        except Exception:
            pass
    return BatDetect2_AudioConfig()


def get_default_model() -> "ModelConfig":
    """Get default model configuration, using saved values if present."""
    saved = get_saved_program_config().get("model")
    if saved:
        try:
            return ModelConfig(**saved)
        except Exception:
            pass
    return ModelConfig()


def get_default_saving_filters() -> Optional["SaveRecordingFilter"]:
    """Get default saving filters configuration, using saved values if present."""
    saved = get_saved_program_config().get("saving_filters")
    if saved is not None:
        try:
            return SaveRecordingFilter(**saved)
        except Exception:
            pass
    return SaveRecordingFilter()


def get_default_saving_managers() -> "SaveRecordingManager":
    """Get default saving managers configuration, using saved values if present."""
    saved = get_saved_program_config().get("saving_managers")
    if saved:
        try:
            return SaveRecordingManager(**saved)
        except Exception:
            pass
    return SaveRecordingManager()


def get_default_summariser() -> Optional["Summariser"]:
    """Get default summariser configuration, using saved values if present."""
    saved = get_saved_program_config().get("summariser_config")
    if saved is not None:
        try:
            return Summariser(**saved)
        except Exception:
            pass
    return Summariser()


class BatDetect2_AudioConfig(AudioConfiguration):
    """Audio Configuration schema."""

    schedule_start: datetime.time = Field(
        default=datetime.time(hour=19, minute=0, second=0),
    )
    """Start time for recording schedule."""

    schedule_end: datetime.time = Field(
        default=datetime.time(hour=7, minute=0, second=0),
    )
    """End time for recording schedule."""

    use_nocturnal_schedule: bool = Field(
        default=True,
        description="Whether to use solar nocturnal schedule (IsNightTime) for recording",
    )
    """Whether to use solar nocturnal schedule."""

    buffer_before_sunset_minutes: int = Field(
        default=30,
        description="Minutes before sunset to begin nocturnal recording window",
    )
    """Minutes before sunset to begin recording."""

    buffer_after_sunrise_minutes: int = Field(
        default=30,
        description="Minutes after sunrise to end nocturnal recording window",
    )
    """Minutes after sunrise to end recording."""

    latitude: Optional[float] = Field(
        default=None,
        description="Latitude for astral solar calculations",
    )
    """Latitude coordinate."""

    longitude: Optional[float] = Field(
        default=None,
        description="Longitude for astral solar calculations",
    )
    """Longitude coordinate."""


class ModelConfig(BaseModel):
    """Model and multi-tier threshold configuration."""

    detection_threshold: float = Field(
        default=0.3,
        description="Threshold used to determine which detections are stored in the local database",
        ge=0.0,
        le=1.0,
    )
    messaging_threshold: float = Field(
        default=0.5,
        description="Threshold used to determine which detections are sent as messages",
        ge=0.0,
        le=1.0,
    )
    saving_threshold: float = Field(
        default=0.7,
        description="Threshold used to determine which recordings should be saved to disk",
        ge=0.0,
        le=1.0,
    )


BatDetect2Config = ModelConfig


class SaveRecordingFilter(BaseModel):
    """Saving Filters for audio recordings configuration."""

    starttime: datetime.time = datetime.time(hour=19, minute=0, second=0)
    """Start time of the interval for which to save recordings."""

    endtime: datetime.time = datetime.time(hour=7, minute=0, second=0)
    """End time of the interval for which to save recordings."""

    before_dawndusk_duration: int = 0
    """Optional duration in minutes before dawn/dusk to save recordings."""

    after_dawndusk_duration: int = 0
    """Optional duration in minutes after dawn/dusk to save recordings."""

    frequency_duration: int = 0
    """Optional duration in minutes to save recordings using the frequency filter."""

    frequency_interval: int = 0
    """Optional periodic interval in minutes to save recordings."""

    saving_threshold: float = 0.3
    """Minimum threshold of detections from a recording to save it."""


class SaveRecordingManager(BaseModel):
    """Saving configuration for audio recordings.

    (path to storage, name of files, saving threshold).
    """

    true_dir: str = "bats"
    """Directory for saving recordings with confident detections."""

    false_dir: str = "no_bats"
    """Directory for saving recordings with uncertain detections."""

    timeformat: str = "%Y%m%d_%H%M%S"
    """Time format for naming the audio recording files."""

    bat_threshold: float = 0.5
    """Minimum threshold of detections from a recording to save it."""


class Summariser(BaseModel):
    """Summariser configuration."""

    interval: Optional[float] = 3600  # interval in seconds
    """Interval (in seconds) for summarising detections."""

    low_band_threshold: Optional[float] = 0.0
    """Optional low band threshold to summarise detections."""

    mid_band_threshold: Optional[float] = 0.0
    """Optional mid band threshold to summarise detections."""

    high_band_threshold: Optional[float] = 0.0
    """Optional high band threshold to summarise detections."""


class BatDetect2_ConfigSchema(DetectionProgramConfiguration):
    """BatDetect2 Program Configuration schema.

    This schema extends the _acoupi_ `DetectionProgramConfiguration` to
    include settings for the BatDetect2 program, such as custom audio recording,
    model setup, file management, messaging, and summarisation.
    """

    timezone: str = Field(
        default_factory=lambda: get_saved_program_config().get(
            "timezone", "Europe/London"
        ),
    )

    microphone: MicrophoneConfig = Field(  # type: ignore
        default_factory=get_default_microphone,
    )

    paths: PathsConfiguration = Field(  # type: ignore
        default_factory=get_default_paths,
    )

    messaging: MessagingConfig = Field(  # type: ignore
        default_factory=get_default_messaging,
    )

    recording: BatDetect2_AudioConfig = Field(  # type: ignore
        default_factory=get_default_recording,
    )

    model: ModelConfig = Field(
        default_factory=get_default_model,
    )

    saving_filters: Optional[SaveRecordingFilter] = Field(
        default_factory=get_default_saving_filters,
    )

    saving_managers: SaveRecordingManager = Field(
        default_factory=get_default_saving_managers,
    )

    summariser_config: Optional[Summariser] = Field(
        default_factory=get_default_summariser,
    )
