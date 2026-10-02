"""Reusable Acoupi components for BatDetect2."""

import datetime
import zoneinfo
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from acoupi import data
from acoupi.components import DateFileManager
from acoupi.components.types import (
    RecordingCondition,
    RecordingSavingFilter,
    RecordingSavingManager,
)
from astral import LocationInfo
from astral.sun import sun

from acoupi_batdetect2.scripts import pw_record, trim_wav

__all__ = [
    "HasHighConfidenceDetection",
    "IsNightTime",
    "ModelSeparatedDateFileManager",
    "PrecisePWRecorder",
]




@dataclass
class IsNightTime(RecordingCondition):
    """Solar nocturnal recording condition.

    Determines whether the current time is between sunset and sunrise
    (with optional buffer offsets before sunset and after sunrise) using
    the observer's location coordinates and timezone.

    Attributes
    ----------
    timezone : datetime.tzinfo or str
        Timezone for local time calculation.
    before : float, int, or datetime.timedelta
        Buffer duration before sunset to start recording (default 0).
    after : float, int, or datetime.timedelta
        Buffer duration after sunrise to stop recording (default 0).
    latitude : float, optional
        Latitude of the deployment.
    longitude : float, optional
        Longitude of the deployment.
    """

    timezone: Union[datetime.tzinfo, str] = "Europe/London"
    before: Union[float, int, datetime.timedelta] = 0
    after: Union[float, int, datetime.timedelta] = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __post_init__(self):
        if isinstance(self.timezone, str):
            self.timezone = zoneinfo.ZoneInfo(self.timezone)

        if isinstance(self.before, (int, float)):
            self.before = datetime.timedelta(seconds=self.before)

        if isinstance(self.after, (int, float)):
            self.after = datetime.timedelta(seconds=self.after)

        if self.latitude is None or self.longitude is None:
            location_info = LocationInfo(
                timezone=str(self.timezone),
            )
        else:
            location_info = LocationInfo(
                timezone=str(self.timezone),
                latitude=self.latitude,
                longitude=self.longitude,
            )

        self.location_info = location_info

    def should_record(self, now: Optional[datetime.datetime] = None) -> bool:
        """Check whether recording should occur at the given time.

        Parameters
        ----------
        now : datetime.datetime, optional
            Timestamp to evaluate. Defaults to current UTC time.

        Returns
        -------
        bool
            True if within the nocturnal recording window, False otherwise.
        """
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)

        local_now = now.astimezone(self.timezone)

        sun_info = sun(
            self.location_info.observer,
            date=local_now.date(),
            tzinfo=self.timezone,
        )

        sunrise = sun_info["sunrise"]
        sunset = sun_info["sunset"]

        return (
            local_now <= sunrise + self.after
            or local_now >= sunset - self.before
        )


@dataclass
class HasHighConfidenceDetection(RecordingSavingFilter):
    """Filter to save audio only when model detection meets a threshold."""

    model_name: str
    threshold: float = 0.5

    def should_save_recording(
        self,
        recording: data.Recording,
        model_outputs: Optional[list[data.ModelOutput]] = None,
    ) -> bool:
        if not model_outputs:
            return False

        for output in model_outputs:
            if output.name_model != self.model_name:
                continue

            if any(
                detection.detection_score >= self.threshold
                for detection in output.detections
            ):
                return True

        return False


class ModelSeparatedDateFileManager(DateFileManager):
    """Date- and model-partitioned audio file storage manager."""

    def __init__(self, directory: Union[Path, str] = Path(".")):
        super().__init__(directory=directory)

    def get_file_path(self, recording: data.Recording) -> Path:
        category = "birds" if recording.samplerate < 90000 else "bats"
        date = recording.created_on
        filename = (
            f"{category}_{date.strftime('%Y%m%d_%H%M%S')}_{recording.id}.wav"
        )

        directory = (
            self.directory
            / Path(category)
            / Path(str(date.year))
            / Path(f"{date.month:02d}")
            / Path(f"{date.day:02d}")
        )
        return directory / Path(filename)


@dataclass
class PrecisePWRecorder:
    """PipeWire audio recorder with precise sample count truncation.

    Records with an additional duration buffer to avoid PipeWire startup
    latency truncation, then trims the recorded WAV to the exact requested
    sample count.
    """

    duration: float = 3.0
    samplerate: int = 192000
    audio_channels: int = 1
    device_name: Optional[str] = None
    audio_dir: Path = Path("/tmp")
    buffer_seconds: float = 0.5

    def record(self, output_path: Union[Path, str]) -> Path:
        """Record and trim audio output."""
        return pw_record(
            output_path=output_path,
            duration=self.duration,
            samplerate=self.samplerate,
            channels=self.audio_channels,
            device_name=self.device_name,
            buffer_seconds=self.buffer_seconds,
        )

    def check(self) -> None:
        """Check recorder prerequisites."""
        import shutil

        if not shutil.which("pw-record"):
            raise RuntimeError("pw-record command not found in PATH")



