import datetime
import json
import shutil
import tempfile
from pathlib import Path
from celery import Celery
from acoupi import data
from acoupi_batdetect2.configuration import BatDetect2_ConfigSchema
from acoupi_batdetect2.program import BatDetect2_Program
config_file = Path("/home/pi/.acoupi/config/program.json")
with open(config_file) as f:
    config_dict = json.load(f)
config = BatDetect2_ConfigSchema(**config_dict)
print(f"Loaded config. MQTT host: {config.messaging.mqtt.host}, Topic: {config.messaging.mqtt.topic}")
app = Celery("acoupi")
program = BatDetect2_Program(program_config=config, app=app)
name_file = Path("/home/pi/.acoupi/config/name")
deployment_name = name_file.read_text().strip() if name_file.exists() else "33PH-acoupi-bat"
# Create unique copy of the audio file to avoid UNIQUE constraint collisions
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
unique_audio_path = Path(tempfile.gettempdir()) / f"test_recording_{ts}.wav"
shutil.copy("tests/data/audiofile_test1_myomys.wav", unique_audio_path)
rec = data.Recording(
    path=unique_audio_path,
    duration=3.0,
    samplerate=192000,
    created_on=datetime.datetime.now(),
    deployment=data.Deployment(name=deployment_name),
)
print("\n1. Running Detection Task...")
program.tasks["detection_task"](rec)
unsent = program.message_store.get_unsent_messages()
print(f"Queued {len(unsent)} message(s) in {config.messaging.messages_db}")
print("\n2. Running Send Messages Task (Publishing to MQTT)...")
program.tasks["send_messages_task"]()
remaining = program.message_store.get_unsent_messages()
print(f"Remaining unsent messages: {len(remaining)} (0 means sent successfully to MQTT).")
# Cleanup temp wav
unique_audio_path.unlink(missing_ok=True)