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

## 2. Planned Implementation Roadmap

### A. PipeWire Ultrasonic Support
* **Target:** Setup utilities / audio recording configuration.
* **Source Reference:** [`src/acoupi_yeo_valley/scripts.py:setup_pipewire`](file:///Users/dunc/Dropbox/code/CASA/yeo/src/acoupi_yeo_valley/scripts.py#L93-L133)
* **What to add:**
  * Auto-generate `~/.config/pipewire/pipewire.conf.d/10-rates.conf`:
    ```conf
    context.properties = {
        default.clock.rate = 250000
        default.clock.allowed-rates = [ 32000 48000 96000 192000 250000 384000 ]
    }
    ```
  * Ensure all import-time and setup logs output to `sys.stderr` to prevent corrupting Celery JSON parsing in `acoupi deployment status`.

### B. Precise Audio Trimming (`pw-record` wrapper)
* **Target:** Audio recording execution layer.
* **Source Reference:** [`src/acoupi_yeo_valley/scripts.py:pw_record`](file:///Users/dunc/Dropbox/code/CASA/yeo/src/acoupi_yeo_valley/scripts.py#L10-L84)
* **What to add:**
  * Add duration buffer (0.5s) to handle PipeWire startup latency.
  * Post-process WAV file to truncate exactly to `sample_count` frames (`wave.readframes` / `wave.writeframes`).

### C. Guano RAM Disk OOM Prevention
* **Target:** Audio saving / metadata tagging pipeline.
* **Source Reference:** [`src/acoupi_yeo_valley/program.py`](file:///Users/dunc/Dropbox/code/CASA/yeo/src/acoupi_yeo_valley/program.py)
* **What to add:**
  * Disable backup creation on `guano.GuanoFile.write()` (pass `make_backup=False`) so temporary RAM disks (`/run/shm`) do not fill up with `.backup` files.

### D. Reusable Components (`acoupi.components`)
* **Target:** `acoupi.components`
* **Source Reference:** [`src/acoupi_yeo_valley/components.py`](file:///Users/dunc/Dropbox/code/CASA/yeo/src/acoupi_yeo_valley/components.py)
* **What to add:**
  * `IsNightTime(RecordingCondition)`: Astral sunrise/sunset calculator with configurable `before` and `after` offsets.
  * `HasHighConfidenceDetection(RecordingSavingFilter)`: Filter to save audio only when model detection exceeds threshold.
  * `ModelSeparatedDateFileManager(DateFileManager)`: Date and model/category-partitioned storage (`category/YYYY/MM/DD/`).

### E. Resilient Network & Transport Startup
* **Target:** `acoupi.program` / messenger initialization.
* **What to add:**
  * Wrap messenger `open()` and `join()` in `try...except` so offline/boot radio failures do not halt the core recording scheduler.
