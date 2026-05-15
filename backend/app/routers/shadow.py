import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.feature_service import extract_features
from app.services.whisper_service import transcribe_words
from app.services.scoring_service import calculate_score

router = APIRouter()

TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp"
)
os.makedirs(TEMP_DIR, exist_ok=True)


def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(TEMP_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return filepath


def cleanup(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@router.post("/analyze-master")
async def analyze_master(audio: UploadFile = File(...)):
    path = save_upload(audio)
    try:
        features = extract_features(path)
        words = transcribe_words(path)
        return {
            "words": words,
            "times": features["times"],
            "rms": features["rms"],
            "pitch": features["pitch"],
            "pause_mask": features["pause_mask"],
            "pause_regions": features["pause_regions"],
            "cps": features["cps"],
            "duration": features["duration"],
            "sample_rate": features["sample_rate"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cleanup(path)


@router.post("/compare-attempt")
async def compare_attempt(
    master_audio: UploadFile = File(...),
    user_audio: UploadFile = File(...),
):
    master_path = save_upload(master_audio)
    user_path = save_upload(user_audio)
    try:
        m_feat = extract_features(master_path)
        u_feat = extract_features(user_path)
        return calculate_score(m_feat, u_feat)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cleanup(master_path)
        cleanup(user_path)
