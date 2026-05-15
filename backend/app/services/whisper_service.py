from faster_whisper import WhisperModel

from app.core.config import (
    WHISPER_MODEL_PATH,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)

_model = None


def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL_PATH,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _model


def transcribe_words(audio_path):
    model = get_model()
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    for segment in segments:
        for word in segment.words:
            words.append(
                {
                    "word": word.word.strip(),
                    "start": float(word.start),
                    "end": float(word.end),
                }
            )

    return words
