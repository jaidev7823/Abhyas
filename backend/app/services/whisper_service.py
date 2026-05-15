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
    return transcribe_audio(audio_path)["words"]


def make_sentence(words, index):
    text = " ".join(word["word"] for word in words).strip()
    return {
        "id": index,
        "index": index,
        "text": text,
        "start": words[0]["start"],
        "end": words[-1]["end"],
    }


def transcribe_audio(audio_path):
    model = get_model()
    segments, _info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    sentences = []
    sentence_words = []
    sentence_index = 0
    previous_end = None

    for segment in segments:
        for word in segment.words or []:
            clean_word = word.word.strip()
            if not clean_word:
                continue

            item = {
                "word": clean_word,
                "start": float(word.start),
                "end": float(word.end),
            }

            gap = item["start"] - previous_end if previous_end is not None else 0
            if sentence_words and gap >= 0.9:
                sentences.append(make_sentence(sentence_words, sentence_index))
                sentence_index += 1
                sentence_words = []

            words.append(item)
            sentence_words.append(item)
            previous_end = item["end"]

            sentence_duration = sentence_words[-1]["end"] - sentence_words[0]["start"]
            ends_sentence = clean_word.endswith((".", "?", "!"))
            if ends_sentence or sentence_duration >= 14:
                sentences.append(make_sentence(sentence_words, sentence_index))
                sentence_index += 1
                sentence_words = []

    if sentence_words:
        sentences.append(make_sentence(sentence_words, sentence_index))

    return {
        "words": words,
        "sentences": sentences,
    }
