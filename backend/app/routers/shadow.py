import os
import shutil
import uuid

from fastapi import (
    APIRouter,
    UploadFile,
    File
)

from app.services.feature_service import (
    extract_features
)

from app.services.whisper_service import (
    transcribe_words
)

from app.services.graph_service import (
    build_reference_payload
)

from app.services.scoring_service import (
    calculate_score
)

router = APIRouter()


TEMP_DIR = "temp"

os.makedirs(
    TEMP_DIR,
    exist_ok=True
)


def save_upload(file: UploadFile):

    filename = f"{uuid.uuid4()}.wav"

    filepath = os.path.join(
        TEMP_DIR,
        filename
    )

    with open(filepath, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    return filepath


@router.post("/analyze-master")
async def analyze_master(
    audio: UploadFile = File(...)
):

    audio_path = save_upload(audio)

    features = extract_features(
        audio_path
    )

    words = transcribe_words(
        audio_path
    )

    return build_reference_payload(
        features,
        words
    )


@router.post("/compare-attempt")
async def compare_attempt(
    master_audio: UploadFile = File(...),
    user_audio: UploadFile = File(...)
):

    master_path = save_upload(
        master_audio
    )

    user_path = save_upload(
        user_audio
    )

    master_features = extract_features(
        master_path
    )

    user_features = extract_features(
        user_path
    )

    score = calculate_score(
        master_features,
        user_features
    )

    return {
        "score": score
    }

