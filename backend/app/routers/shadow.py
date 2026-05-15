import os
import shutil
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.feature_service import extract_features
from app.services.whisper_service import transcribe_audio
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
        transcription = transcribe_audio(path)
        return {
            "words": transcription["words"],
            "sentences": transcription["sentences"],
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
    master_start: float = Form(0.0),
    master_end: Optional[float] = Form(None),
):
    master_path = save_upload(master_audio)
    user_path = save_upload(user_audio)
    try:
        master_duration = None
        if master_end is not None and master_end > master_start:
            master_duration = master_end - master_start
        m_feat = extract_features(master_path, offset=master_start, duration=master_duration)
        u_feat = extract_features(user_path)
        score = calculate_score(m_feat, u_feat)
        return {
            **score,
            "attempt": {
                "words": [],
                "times": u_feat["times"],
                "rms": u_feat["rms"],
                "pitch": u_feat["pitch"],
                "pause_mask": u_feat["pause_mask"],
                "pause_regions": u_feat["pause_regions"],
                "cps": u_feat["cps"],
                "duration": u_feat["duration"],
                "sample_rate": u_feat["sample_rate"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cleanup(master_path)
        cleanup(user_path)
