from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download
import os

HF_TOKEN = os.getenv("HF_TOKEN")

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

print("Downloading Faster Whisper Large V3...")
snapshot_download(
    repo_id="Systran/faster-whisper-large-v3",
    local_dir=MODELS_DIR / "faster-whisper-large-v3",
    token=HF_TOKEN,
    local_dir_use_symlinks=False,
)

print("Downloading SpeechBrain ECAPA...")
snapshot_download(
    repo_id="speechbrain/spkrec-ecapa-voxceleb",
    local_dir=MODELS_DIR / "spkrec-ecapa-voxceleb",
    token=HF_TOKEN,
    local_dir_use_symlinks=False,
)

print("Downloading Emotion Recognition model...")
snapshot_download(
    repo_id="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
    local_dir=MODELS_DIR / "emotion-recognition",
    token=HF_TOKEN,
    local_dir_use_symlinks=False,
)


print("Done.")

