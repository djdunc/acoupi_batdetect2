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
    monkeypatch,
):
    from acoupi_batdetect2 import configuration

    monkeypatch.setattr(configuration, "PROGRAM_CONFIG_PATHS", [])
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


def test_saved_program_config_defaults(tmp_path, monkeypatch):
    import json
    from acoupi_batdetect2 import configuration

    mock_config = tmp_path / "program.json"
    saved_data = {
        "timezone": "UTC",
        "microphone": {
            "samplerate": 250000,
            "audio_channels": 1,
            "device_name": "UltraMic 250K 16 bit r4",
        },
        "recording": {
            "duration": 5,
            "interval": 15,
            "latitude": 51.5,
            "longitude": -0.1,
        },
        "model": {
            "detection_threshold": 0.22,
            "messaging_threshold": 0.44,
            "saving_threshold": 0.66,
        },
        "messaging": {
            "message_send_interval": 60,
            "mqtt": {
                "host": "test.mosquitto.org",
                "port": 1883,
                "topic": "test/bats",
                "username": "batuser",
                "password": "secret_password",
            },
        },
    }
    mock_config.write_text(json.dumps(saved_data))

    monkeypatch.setattr(configuration, "PROGRAM_CONFIG_PATHS", [mock_config])

    schema = configuration.BatDetect2_ConfigSchema()
    assert schema.timezone == "UTC"
    assert schema.microphone.samplerate == 250000
    assert schema.microphone.device_name == "UltraMic 250K 16 bit r4"
    assert schema.recording.duration == 5
    assert schema.recording.interval == 15
    assert schema.recording.latitude == 51.5
    assert schema.model.detection_threshold == 0.22
    assert schema.model.messaging_threshold == 0.44
    assert schema.model.saving_threshold == 0.66
    assert schema.messaging.message_send_interval == 60
    assert schema.messaging.mqtt is not None
    assert schema.messaging.mqtt.host == "test.mosquitto.org"
    assert schema.messaging.mqtt.topic == "test/bats"
    assert schema.messaging.mqtt.username == "batuser"
    assert schema.messaging.mqtt.password.get_secret_value() == "secret_password"

