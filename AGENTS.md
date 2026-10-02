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
* **Status Command:** Run `acoupi deployment status` to inspect system services, Celery workers, program, and active deployment metadata.
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

### Completed & Merged into `main` (commit `bcead00`)
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
   - Fixed `IsNightTime.should_record()` to use `datetime.datetime.now(datetime.timezone.utc)` instead of non-existent `data.utc_now()`.
5. **PipeWire Ultrasonic Rates & Setup Defaults (Branch `feat/pipewire-ultrasonic`):**
   - Added `setup_pipewire()` generating `10-rates.conf` (rates: 32k, 48k, 96k, 192k, 250k, 384k) in [`src/acoupi_batdetect2/scripts.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/scripts.py).
   - Implemented `trim_wav()` and `pw_record()` with graceful `SIGINT` shutdown and sample-accurate trimming.
   - Added `PrecisePWRecorder` to `components.py`.
   - Prepend virtualenv `bin` to `PATH` for worker subprocesses in `program.py`.
   - Added `setup_celery()` configuring `worker_max_tasks_per_child=20`.
   - Configured `memory://` broker and `cache+memory://` backend in `tests/conftest.py` for test isolation.
   - Implemented comprehensive persistent setup defaults across all sub-models in [`src/acoupi_batdetect2/configuration.py`](file:///Users/dunc/Dropbox/code/CASA/acoupi/acoupi_batdetect2/src/acoupi_batdetect2/configuration.py).
   - Supported `Union` types for parser compatibility, `SecretStr` for MQTT passwords, and ISO string parsing for schedule times.
6. **Upstream Acoupi Synchronization & Schema Alignment (Commit `5bd1da8`):**
   - **PR 1 (`feat/cli-deployment-defaults`):** Persistent deployment start defaults (`name`, `latitude`, `longitude`) in `acoupi` CLI with dynamic callable defaults and `show_default=True`.
   - **PR 2 (`feat/config-parser-defaults`):** Interactive setup parser defaults, `typing.Literal` click choices, and safe subclass type checks.
   - **PR 3 (`fix/celery-worker-recycling-and-test-isolation`):** Celery worker recycling (`worker_max_tasks_per_child=20`) in `CeleryConfig`.
   - **PR 4 (`feat/pipewire-precise-recording`):** PipeWire startup latency buffer + exact sample trimming (`trim_wav`) in `PWRecorder`.
   - **Staging Branch (`staging/combined-enhancements`):** All 4 PRs integrated and tested end-to-end on live Raspberry Pi 5.
   - **Data Schema Alignment:** Added `prediction_type=getattr(data.PredictionType, "EVENT", "event")` to `Detection` instantiation in `model.py` and `test_components.py`.
   - **UTC Datetimes:** Timezone-aware UTC timestamps across test suite (`datetime.datetime.now(datetime.timezone.utc)`).

---

## 3. Operational Verification & Testing

* **Test Suite:** All 21 tests (`pytest -v`) passing on Raspberry Pi 5 (`pi@33PH-acoupi-bat`) against latest upstream `acoupi`.
* **Live Services:** `acoupi.service` and `acoupi-beat.service` active and healthy.
* **Recording Workers:** `recording` and `default` workers running cleanly with PipeWire audio capture and nocturnal scheduling.
