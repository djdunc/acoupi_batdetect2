"""Tests for PipeWire setup and audio trimming scripts."""

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from acoupi_batdetect2.components import PrecisePWRecorder
from acoupi_batdetect2.scripts import (
    PIPEWIRE_RATES_CONF,
    pw_record,
    setup_pipewire,
    trim_wav,
)


def test_setup_pipewire_creates_file(tmp_path):
    conf_file = setup_pipewire(config_dir=tmp_path)
    assert conf_file.exists()
    assert conf_file.read_text().strip() == PIPEWIRE_RATES_CONF.strip()
    assert "250000" in conf_file.read_text()
    assert "384000" in conf_file.read_text()


def test_trim_wav(tmp_path):
    wav_path = tmp_path / "test.wav"
    samplerate = 192000
    channels = 1
    sample_width = 2
    total_frames = 192000 * 2  # 2 seconds
    dummy_data = b"\x00\x00" * total_frames

    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(samplerate)
        w.writeframes(dummy_data)

    assert wav_path.exists()
    with wave.open(str(wav_path), "rb") as r:
        assert r.getnframes() == total_frames

    # Trim to 1 second (192000 samples)
    trim_wav(wav_path, target_samples=192000)

    with wave.open(str(wav_path), "rb") as r:
        assert r.getnframes() == 192000


def test_pw_record_calls_subprocess(tmp_path):
    output_wav = tmp_path / "rec.wav"
    samplerate = 192000
    total_frames = int(1.5 * samplerate)
    dummy_data = b"\x00\x00" * total_frames

    def fake_subprocess_run(cmd, *args, **kwargs):
        with wave.open(str(output_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(samplerate)
            w.writeframes(dummy_data)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fake_subprocess_run) as mock_run:
        res = pw_record(
            output_wav,
            duration=1.0,
            samplerate=samplerate,
            buffer_seconds=0.5,
        )
        assert res == output_wav
        mock_run.assert_called_once()
        # Verify trimmed to 1.0s (192000 frames)
        with wave.open(str(output_wav), "rb") as r:
            assert r.getnframes() == 192000


def test_precise_pw_recorder(tmp_path):
    wav_path = tmp_path / "precise.wav"
    samplerate = 192000

    recorder = PrecisePWRecorder(
        duration=1.0,
        samplerate=samplerate,
        audio_channels=1,
    )

    with patch(
        "acoupi_batdetect2.components.pw_record", return_value=wav_path
    ) as mock_pw:
        result = recorder.record(wav_path)
        assert result == wav_path
        mock_pw.assert_called_once_with(
            output_path=wav_path,
            duration=1.0,
            samplerate=samplerate,
            channels=1,
            device_name=None,
            buffer_seconds=0.5,
        )

