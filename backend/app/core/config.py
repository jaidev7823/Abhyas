from pathlib import Path

TARGET_SR = 16000

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
WHISPER_MODEL_PATH = str(BACKEND_DIR / "models" / "faster-whisper-large-v3")
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"
