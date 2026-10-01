"""Audio recording and PipeWire setup utilities for BatDetect2."""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

PIPEWIRE_RATES_CONF = """context.properties = {
    default.clock.rate = 250000
    default.clock.allowed-rates = [ 32000 48000 96000 192000 250000 384000 ]
}
"""


def setup_pipewire(
    config_dir: Optional[Union[Path, str]] = None,
    restart_service: bool = False,
) -> Path:
    """Ensure PipeWire configuration supports ultrasonic sample rates.

    Auto-generates `~/.config/pipewire/pipewire.conf.d/10-rates.conf` with
    allowed clock rates up to 384kHz (e.g., 192kHz, 250kHz, 384kHz).

    Parameters
    ----------
    config_dir : Path or str, optional
        Base configuration directory. Defaults to `~/.config/pipewire`.
    restart_service : bool, optional
        Whether to attempt restarting user pipewire service via systemctl.

    Returns
    -------
    Path
        Path to the written configuration file.
    """
    if config_dir is None:
        target_dir = Path.home() / ".config" / "pipewire" / "pipewire.conf.d"
    else:
        target_dir = Path(config_dir) / "pipewire.conf.d"

    target_dir.mkdir(parents=True, exist_ok=True)
    conf_path = target_dir / "10-rates.conf"

    needs_write = True
    if conf_path.exists():
        try:
            existing_content = conf_path.read_text()
            if existing_content.strip() == PIPEWIRE_RATES_CONF.strip():
                needs_write = False
        except Exception as e:
            print(
                f"[setup_pipewire] Warning: could not read existing {conf_path}: {e}",
                file=sys.stderr,
            )

    if needs_write:
        conf_path.write_text(PIPEWIRE_RATES_CONF)
        print(
            f"[setup_pipewire] Generated PipeWire rates configuration at {conf_path}",
            file=sys.stderr,
        )

        if restart_service and shutil.which("systemctl"):
            try:
                subprocess.run(
                    ["systemctl", "--user", "restart", "pipewire"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                print(
                    f"[setup_pipewire] Warning: could not restart pipewire service: {e}",
                    file=sys.stderr,
                )

    return conf_path


def trim_wav(
    filepath: Union[Path, str],
    target_samples: Optional[int] = None,
    target_duration: Optional[float] = None,
    samplerate: Optional[int] = None,
) -> None:
    """Trim a WAV file precisely to the target number of samples or duration.

    Parameters
    ----------
    filepath : Path or str
        Path to the WAV file to trim.
    target_samples : int, optional
        Exact number of audio frames to keep.
    target_duration : float, optional
        Target duration in seconds.
    samplerate : int, optional
        Sample rate in Hz (used if target_duration is specified).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with wave.open(str(path), "rb") as reader:
        params = reader.getparams()
        n_frames = reader.getnframes()
        sr = params.framerate

        if target_samples is None:
            if target_duration is not None:
                eff_sr = samplerate if samplerate is not None else sr
                target_samples = int(target_duration * eff_sr)
            else:
                return

        if n_frames <= target_samples:
            return

        frames_to_read = min(n_frames, target_samples)
        audio_data = reader.readframes(frames_to_read)

    with tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False, suffix=".wav"
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        with wave.open(str(tmp_path), "wb") as writer:
            writer.setparams(params)
            writer.setnframes(frames_to_read)
            writer.writeframes(audio_data)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def pw_record(
    output_path: Union[Path, str],
    duration: float,
    samplerate: int = 192000,
    channels: int = 1,
    device_name: Optional[str] = None,
    buffer_seconds: float = 0.5,
) -> Path:
    """Record audio using pw-record with duration buffer and exact sample trimming.

    Parameters
    ----------
    output_path : Path or str
        Destination path for the recorded WAV file.
    duration : float
        Target recording duration in seconds.
    samplerate : int
        Audio sampling rate in Hz (default: 192000).
    channels : int
        Number of audio channels (default: 1).
    device_name : str, optional
        Specific PipeWire target device node name.
    buffer_seconds : float
        Startup latency buffer added to pw-record duration (default: 0.5s).

    Returns
    -------
    Path
        Path to the trimmed audio recording.
    """
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pw-record",
        f"--rate={samplerate}",
        f"--channels={channels}",
        f"--format=s16",
    ]
    if device_name:
        cmd.extend(["--target", device_name])

    cmd.append(str(dest))

    total_duration = duration + buffer_seconds
    try:
        subprocess.run(
            cmd,
            timeout=total_duration + 2.0,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired:
        pass
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        raise RuntimeError(f"pw-record failed ({e.returncode}): {err_msg}") from e

    if dest.exists():
        target_samples = int(duration * samplerate)
        trim_wav(dest, target_samples=target_samples)

    return dest
