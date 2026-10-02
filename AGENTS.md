# Acoupi BatDetect2 - Agent Guide & Workspace Knowledge

## 1. Project Conventions & Environment

### Raspberry Pi 5 Target & SSH Workflow
* **SSH & Command Execution Preference:** Do NOT attempt automated SSH execution directly from the assistant. Always provide clean, copy-pasteable command blocks for the user to execute manually in their SSH session.
* **Pi Environment:** 
  * Host: `pi@33PH-acoupi-bat:~/acoupi_batdetect2`
  * Active Conda Environment: `bat_env` (`miniforge3/envs/bat_env/lib/python3.11`)
* **Local Development Environment:**
  * Mac x86_64 host (uses local `.venv` or conda for linting/formatting).

### Reference Codebases
* **Sibling Acoupi Implementations:** Located at `/Users/dunc/Dropbox/code/CASA/yeo/src/acoupi_yeo_valley/`.

### Deployment & Configuration Files on Raspberry Pi
* **Setup Command:** Run `acoupi setup --program acoupi_batdetect2.program` directly in the active `(bat_env)` conda environment.
* **Configuration Locations:**
  * `~/.acoupi/config/program.json`: Program configuration schema (`BatDetect2_ConfigSchema`) containing microphone settings (UltraMic 192k), recording intervals/schedules, storage paths, and messaging endpoints (e.g., MQTT host/port/topic, HTTP).
  * `~/.acoupi/config/celery.json`: Celery worker and broker configuration.
  * `~/.acoupi/config/name`: Deployment name identifier.
  * `~/.config/systemd/user/acoupi.service`: User systemd unit for worker processes.
  * `~/.config/systemd/user/acoupi-beat.service`: User systemd unit for celery beat scheduler.
* **Security Rule:** Never commit or hardcode credentials, tokens, or passwords into git or agent knowledge files.

### Model & Data Structures
* `acoupi.data.Recording`: Requires `path`, `duration`, `samplerate`, `created_on`, and `deployment` (`data.Deployment(name=...)`) metadata fields.
* `BatDetect2Model`: Alias of `BatDetect2` in `acoupi_batdetect2.model` for naming consistency across Acoupi packages.
* **Type Serialization:** All detection scores, bounding box coordinates, and predicted tag confidence scores must be cast to native Python `float`, and tag values to `str` to avoid NumPy JSON serialization failures.

---

## 2. Implementation Progress & Current State

### Completed & Merged into `main` (commit `7029186`)
1. **NumPy & Type Serialization Fix:**
   - Explicitly cast all detection scores, bounding boxes, and tag scores to native `float` / `str` in [`src/acoupi_batdetect2/model.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/model.py).
2. **Batched Inference & `inference_mode()` (Branch `perf/batched-inference-mode`):**
   - Implemented `get_clips_from_files()`, `adjust_width()`, batched `self.api.model.detector(batch)`, and `torch.inference_mode()` in `model.py`.
   - Added persistent deployment defaults (`~/.acoupi/config/deployment_defaults.json`) in [`src/acoupi_batdetect2/cli.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/cli.py).
   - Verified end-to-end MQTT messaging on live Raspberry Pi 5 (`send-test.py`).
3. **Multi-Tier Sensitivity Thresholds (Branch `feat/multi-tier-thresholds`):**
   - Added `detection_threshold` (0.3), `messaging_threshold` (0.5), and `saving_threshold` (0.7) to `BatDetect2Config` and wired them through `program.py`.
4. **Reusable Components & Astral Nocturnal Schedule (Branch `feat/is-night-time-schedule`):**
   - Created [`src/acoupi_batdetect2/components.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/components.py) with `IsNightTime`, `HasHighConfidenceDetection`, and `ModelSeparatedDateFileManager`.
   - Wired `get_recording_conditions()` in `program.py`.

---

### Active Branch: `feat/pipewire-ultrasonic` (commit `fc9669b`)
1. **PipeWire Ultrasonic Rates Setup ([`src/acoupi_batdetect2/scripts.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/scripts.py)):**
   - Added `setup_pipewire()` to generate `~/.config/pipewire/pipewire.conf.d/10-rates.conf` (rates: 32k, 48k, 96k, 192k, 250k, 384k).
   - Ensured all setup logging prints to `sys.stderr`.
   - Integrated `setup_audio()` into `BatDetect2_Program.setup()`.
2. **Precise Audio Trimming & Recorder:**
   - Implemented `trim_wav()` and `pw_record()` using `Popen` with `SIGINT` graceful shutdown and sample trimming.
   - Added `PrecisePWRecorder` to `components.py`.
3. **Celery Worker Safeguards & Test Fixes:**
   - Prepending virtualenv `bin` to `PATH` for worker subprocesses in `program.py`.
   - Added `setup_celery()` setting `worker_max_tasks_per_child=20`.
   - Configured `memory://` broker and `cache+memory://` backend in `tests/conftest.py` to prevent test collisions with live RabbitMQ daemon.

---

## 3. Test Suite Status & Resumption Plan

### Verification on Pi:
1. Pull branch updates: `git pull origin feat/pipewire-ultrasonic`
2. Run test suite: `pytest -v`
3. Verify all 20 tests pass.
4. Merge `feat/pipewire-ultrasonic` into `main`.
5. Run deployment setup on Pi: `acoupi setup --program acoupi_batdetect2.program`
6. Reload and start systemd units:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart acoupi.service acoupi-beat.service
   ```

