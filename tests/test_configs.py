import datetime
import pytest
from pydantic import ValidationError

from acoupi_batdetect2.configuration import (
    BatDetect2_ConfigSchema,
    BatDetect2Config,
    ModelConfig,
)


def test_audio_config_defaults_have_been_overwriten(
    microphone_config,
    messaging_config,
):
    config = BatDetect2_ConfigSchema(
        microphone=microphone_config,
        messaging=messaging_config,
    )

    assert config.recording.schedule_start == datetime.time(hour=19)
    assert config.recording.schedule_end == datetime.time(hour=7)


def test_multi_tier_thresholds_defaults():
    assert BatDetect2Config is ModelConfig

    config = ModelConfig()
    assert config.detection_threshold == 0.3
    assert config.messaging_threshold == 0.5
    assert config.saving_threshold == 0.7


def test_multi_tier_thresholds_custom_and_validation():
    config = ModelConfig(
        detection_threshold=0.25,
        messaging_threshold=0.6,
        saving_threshold=0.85,
    )
    assert config.detection_threshold == 0.25
    assert config.messaging_threshold == 0.6
    assert config.saving_threshold == 0.85

    # Out of range validation (<0.0 or >1.0)
    with pytest.raises(ValidationError):
        ModelConfig(detection_threshold=1.5)

    with pytest.raises(ValidationError):
        ModelConfig(messaging_threshold=-0.1)


def test_schema_with_multi_tier_thresholds(
    microphone_config,
    messaging_config,
):
    schema = BatDetect2_ConfigSchema(
        microphone=microphone_config,
        messaging=messaging_config,
        model=ModelConfig(
            detection_threshold=0.2,
            messaging_threshold=0.4,
            saving_threshold=0.6,
        ),
    )
    assert schema.model.detection_threshold == 0.2
    assert schema.model.messaging_threshold == 0.4
    assert schema.model.saving_threshold == 0.6

