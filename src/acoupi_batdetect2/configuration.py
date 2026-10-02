import datetime
import json
from pathlib import Path
from typing import Optional, Union

from acoupi.components import MQTTConfig, MicrophoneConfig
from acoupi.programs.templates import (
    AudioConfiguration,
    DetectionProgramConfiguration,
    MessagingConfig,
    PathsConfiguration,
)
from pydantic import BaseModel, Field, SecretStr, field_serializer, field_validator

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


def get_saved_recording_field(field_name: str, fallback=None):
    """Get field value from saved recording configuration or deployment defaults."""
    saved = get_saved_program_config().get("recording", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        val = saved[field_name]
        if field_name in ("schedule_start", "schedule_end") and isinstance(val, str):
            try:
                return datetime.time.fromisoformat(val)
            except Exception:
                pass
        return val
    if field_name in ("latitude", "longitude"):
        try:
            from acoupi_batdetect2.cli import get_defaults

            defaults = get_defaults()
            if field_name in defaults and defaults[field_name] is not None:
                return float(defaults[field_name])
        except Exception:
            pass
    return fallback


def get_saved_model_field(field_name: str, fallback=None):
    """Get field value from saved model configuration."""
    saved = get_saved_program_config().get("model", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return float(saved[field_name])
    return fallback


def get_saved_filter_field(field_name: str, fallback=None):
    """Get field value from saved saving_filters configuration."""
    saved = get_saved_program_config().get("saving_filters", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        val = saved[field_name]
        if field_name in ("starttime", "endtime") and isinstance(val, str):
            try:
                return datetime.time.fromisoformat(val)
            except Exception:
                pass
        return val
    return fallback


def get_saved_manager_field(field_name: str, fallback=None):
    """Get field value from saved saving_managers configuration."""
    saved = get_saved_program_config().get("saving_managers", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return saved[field_name]
    return fallback


def get_saved_summariser_field(field_name: str, fallback=None):
    """Get field value from saved summariser configuration."""
    saved = get_saved_program_config().get("summariser_config", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return saved[field_name]
    return fallback


class BatDetect2_AudioConfig(AudioConfiguration):
    """Audio Configuration schema."""

    duration: float = Field(
        default_factory=lambda: get_saved_recording_field("duration", 3.0),
    )
    """Duration of recording in seconds."""

    interval: float = Field(
        default_factory=lambda: get_saved_recording_field("interval", 10.0),
    )
    """Interval between recordings in seconds."""

    chunksize: int = Field(
        default_factory=lambda: get_saved_recording_field("chunksize", 8192),
    )
    """Chunk size for recording."""

    schedule_start: datetime.time = Field(
        default_factory=lambda: get_saved_recording_field(
            "schedule_start", datetime.time(hour=19, minute=0, second=0)
        ),
    )
    """Start time for recording schedule."""

    schedule_end: datetime.time = Field(
        default_factory=lambda: get_saved_recording_field(
            "schedule_end", datetime.time(hour=7, minute=0, second=0)
        ),
    )
    """End time for recording schedule."""

    use_nocturnal_schedule: bool = Field(
        default_factory=lambda: get_saved_recording_field(
            "use_nocturnal_schedule", True
        ),
        description="Whether to use solar nocturnal schedule (IsNightTime) for recording",
    )
    """Whether to use solar nocturnal schedule."""

    buffer_before_sunset_minutes: int = Field(
        default_factory=lambda: get_saved_recording_field(
            "buffer_before_sunset_minutes", 30
        ),
        description="Minutes before sunset to begin nocturnal recording window",
    )
    """Minutes before sunset to begin recording."""

    buffer_after_sunrise_minutes: int = Field(
        default_factory=lambda: get_saved_recording_field(
            "buffer_after_sunrise_minutes", 30
        ),
        description="Minutes after sunrise to end nocturnal recording window",
    )
    """Minutes after sunrise to end recording."""

    latitude: Optional[float] = Field(
        default_factory=lambda: get_saved_recording_field("latitude", None),
        description="Latitude for astral solar calculations",
    )
    """Latitude coordinate."""

    longitude: Optional[float] = Field(
        default_factory=lambda: get_saved_recording_field("longitude", None),
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

    starttime: datetime.time = Field(
        default_factory=lambda: get_saved_filter_field(
            "starttime", datetime.time(hour=19, minute=0, second=0)
        ),
    )
    """Start time of the interval for which to save recordings."""

    endtime: datetime.time = Field(
        default_factory=lambda: get_saved_filter_field(
            "endtime", datetime.time(hour=7, minute=0, second=0)
        ),
    )
    """End time of the interval for which to save recordings."""

    before_dawndusk_duration: int = Field(
        default_factory=lambda: get_saved_filter_field(
            "before_dawndusk_duration", 0
        ),
    )
    """Optional duration in minutes before dawn/dusk to save recordings."""

    after_dawndusk_duration: int = Field(
        default_factory=lambda: get_saved_filter_field(
            "after_dawndusk_duration", 0
        ),
    )
    """Optional duration in minutes after dawn/dusk to save recordings."""

    frequency_duration: int = Field(
        default_factory=lambda: get_saved_filter_field("frequency_duration", 0),
    )
    """Optional duration in minutes to save recordings using the frequency filter."""

    frequency_interval: int = Field(
        default_factory=lambda: get_saved_filter_field("frequency_interval", 0),
    )
    """Optional periodic interval in minutes to save recordings."""

    saving_threshold: float = Field(
        default_factory=lambda: get_saved_filter_field("saving_threshold", 0.3),
    )
    """Minimum threshold of detections from a recording to save it."""


class SaveRecordingManager(BaseModel):
    """Saving configuration for audio recordings.

    (path to storage, name of files, saving threshold).
    """

    true_dir: str = Field(
        default_factory=lambda: get_saved_manager_field("true_dir", "bats"),
    )
    """Directory for saving recordings with confident detections."""

    false_dir: str = Field(
        default_factory=lambda: get_saved_manager_field("false_dir", "no_bats"),
    )
    """Directory for saving recordings with uncertain detections."""

    timeformat: str = Field(
        default_factory=lambda: get_saved_manager_field(
            "timeformat", "%Y%m%d_%H%M%S"
        ),
    )
    """Time format for naming the audio recording files."""

    bat_threshold: float = Field(
        default_factory=lambda: get_saved_manager_field("bat_threshold", 0.5),
    )
    """Minimum threshold of detections from a recording to save it."""


class Summariser(BaseModel):
    """Summariser configuration."""

    interval: Optional[float] = Field(
        default_factory=lambda: get_saved_summariser_field("interval", 3600.0),
    )
    """Interval (in seconds) for summarising detections."""

    low_band_threshold: Optional[float] = Field(
        default_factory=lambda: get_saved_summariser_field(
            "low_band_threshold", 0.0
        ),
    )
    """Optional low band threshold to summarise detections."""

    mid_band_threshold: Optional[float] = Field(
        default_factory=lambda: get_saved_summariser_field(
            "mid_band_threshold", 0.0
        ),
    )
    """Optional mid band threshold to summarise detections."""

    high_band_threshold: Optional[float] = Field(
        default_factory=lambda: get_saved_summariser_field(
            "high_band_threshold", 0.0
        ),
    )
    """Optional high band threshold to summarise detections."""


def get_saved_mqtt_field(field_name: str, fallback=None):
    """Get field value from saved messaging.mqtt configuration."""
    saved_messaging = get_saved_program_config().get("messaging", {})
    if isinstance(saved_messaging, dict):
        saved_mqtt = saved_messaging.get("mqtt")
        if isinstance(saved_mqtt, dict) and field_name in saved_mqtt and saved_mqtt[field_name] is not None:
            val = saved_mqtt[field_name]
            if field_name == "transport" and isinstance(val, str) and "." in val:
                return val.split(".", 1)[-1].lower()
            return val
    return fallback


def get_saved_messaging_field(field_name: str, fallback=None):
    """Get field value from saved messaging configuration."""
    saved = get_saved_program_config().get("messaging", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return saved[field_name]
    return fallback


def get_saved_mic_field(field_name: str, fallback=None):
    """Get field value from saved microphone configuration."""
    saved = get_saved_program_config().get("microphone", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return saved[field_name]
    return fallback


def get_saved_path_field(field_name: str, fallback=None):
    """Get field value from saved paths configuration."""
    saved = get_saved_program_config().get("paths", {})
    if isinstance(saved, dict) and field_name in saved and saved[field_name] is not None:
        return Path(saved[field_name])
    return fallback


def get_saved_mqtt_password() -> Optional[SecretStr]:
    """Get saved MQTT password as SecretStr."""
    val = get_saved_mqtt_field("password")
    if val is None or val == "**********" or val == "":
        return None
    if isinstance(val, SecretStr):
        return val
    return SecretStr(str(val))


class BatDetect2_MQTTConfig(MQTTConfig):
    """MQTT Configuration schema with persistent defaults."""

    host: str = Field(
        default_factory=lambda: get_saved_mqtt_field("host", "localhost"),
    )
    """MQTT broker host address."""

    port: int = Field(
        default_factory=lambda: int(get_saved_mqtt_field("port", 1883)),
    )
    """MQTT broker port."""

    topic: str = Field(
        default_factory=lambda: get_saved_mqtt_field(
            "topic", "acoupi/batdetect2"
        ),
    )
    """MQTT topic."""

    username: Optional[str] = Field(
        default_factory=lambda: get_saved_mqtt_field("username", None),
    )
    """MQTT broker username."""

    password: Optional[SecretStr] = Field(
        default_factory=get_saved_mqtt_password,
    )
    """MQTT broker password."""

    timeout: int = Field(
        default_factory=lambda: int(get_saved_mqtt_field("timeout", 5)),
    )
    """MQTT connection timeout in seconds."""

    use_message_type: bool = Field(
        default_factory=lambda: bool(
            get_saved_mqtt_field("use_message_type", False)
        ),
    )
    """Use message type as part of the topic."""

    retain_heartbeat: bool = Field(
        default_factory=lambda: bool(
            get_saved_mqtt_field("retain_heartbeat", True)
        ),
    )
    """Send heartbeat messages with MQTT retain flag set to True."""

    @field_validator("transport", mode="before", check_fields=False)
    @classmethod
    def sanitize_transport(cls, v):
        if isinstance(v, str) and "." in v:
            return v.split(".", 1)[-1].lower()
        if hasattr(v, "value"):
            return v.value
        return v

    @field_serializer("password", when_used="json")
    def dump_password(self, value: Optional[SecretStr]):
        if value is None:
            return None
        return value.get_secret_value() if isinstance(value, SecretStr) else str(value)


class BatDetect2_MessagingConfig(MessagingConfig):
    """Messaging Configuration schema with persistent defaults."""

    messages_db: Path = Field(  # type: ignore
        default_factory=lambda: Path(
            get_saved_messaging_field(
                "messages_db", Path.home() / "storages" / "messages.db"
            )
        ),
    )
    """Location of outgoing messages database."""

    message_send_interval: int = Field(
        default_factory=lambda: int(
            get_saved_messaging_field("message_send_interval", 120)
        ),
    )
    """Interval in seconds for message sending task."""

    heartbeat_interval: int = Field(
        default_factory=lambda: int(
            get_saved_messaging_field("heartbeat_interval", 3600)
        ),
    )
    """Interval in seconds for sending heartbeat messages."""

    mqtt: Optional[Union[BatDetect2_MQTTConfig, MQTTConfig]] = Field(  # type: ignore
        default_factory=lambda: BatDetect2_MQTTConfig()
        if get_saved_program_config().get("messaging", {}).get("mqtt")
        else None,
    )
    """MQTT Messaging Configuration."""


class BatDetect2_MicrophoneConfig(MicrophoneConfig):
    """Microphone Configuration schema with persistent defaults."""

    device_name: Optional[str] = Field(
        default_factory=lambda: get_saved_mic_field(
            "device_name", "UltraMic 192K 16 bit r4"
        ),
    )
    """ALSA / PipeWire microphone device name."""

    samplerate: int = Field(
        default_factory=lambda: int(get_saved_mic_field("samplerate", 192000)),
    )
    """Microphone sample rate in Hz."""

    audio_channels: int = Field(
        default_factory=lambda: int(get_saved_mic_field("audio_channels", 1)),
    )
    """Number of audio channels."""


class BatDetect2_PathsConfig(PathsConfiguration):
    """Paths Configuration schema with persistent defaults."""

    tmp_audio: Path = Field(
        default_factory=lambda: get_saved_path_field(
            "tmp_audio",
            Path("/run/shm")
            if Path("/run/shm").exists()
            else Path.home() / ".acoupi" / "tmp",
        ),
    )
    """Temporary audio directory."""

    recordings: Path = Field(
        default_factory=lambda: get_saved_path_field(
            "recordings", Path.home() / "storages" / "recordings"
        ),
    )
    """Permanent recordings storage directory."""

    db_metadata: Path = Field(
        default_factory=lambda: get_saved_path_field(
            "db_metadata", Path.home() / "storages" / "metadata.db"
        ),
    )
    """Metadata SQLite database file path."""


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

    microphone: Union[BatDetect2_MicrophoneConfig, MicrophoneConfig] = Field(  # type: ignore
        default_factory=BatDetect2_MicrophoneConfig,
    )

    paths: Union[BatDetect2_PathsConfig, PathsConfiguration] = Field(  # type: ignore
        default_factory=BatDetect2_PathsConfig,
    )

    messaging: Union[BatDetect2_MessagingConfig, MessagingConfig] = Field(  # type: ignore
        default_factory=BatDetect2_MessagingConfig,
    )

    recording: Union[BatDetect2_AudioConfig, AudioConfiguration] = Field(  # type: ignore
        default_factory=BatDetect2_AudioConfig,
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
